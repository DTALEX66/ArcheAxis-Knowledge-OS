//! Backup/restore via the SQLite Online Backup API (rusqlite `backup`).
use archeaxis_store_sqlite::raw_objects;
use rusqlite::Connection;
use sha2::{Digest, Sha256};
use std::path::{Path, PathBuf};

fn io_error(error: std::io::Error) -> rusqlite::Error {
    rusqlite::Error::ToSqlConversionFailure(Box::new(error))
}

/// Consistent snapshot of `src` into `dst_path` using the Online Backup API.
pub fn backup(conn: &Connection, dst_path: &str) -> rusqlite::Result<()> {
    validate_workspace(conn)?;
    let target = Path::new(dst_path);
    raw_objects::reject_links(target)?;
    raw_objects::reject_links(Path::new(conn.path().ok_or(rusqlite::Error::InvalidQuery)?))?;
    let final_objects = PathBuf::from(format!("{dst_path}.objects"));
    raw_objects::reject_links(&final_objects)?;
    if target.exists() || final_objects.exists() {
        return Err(rusqlite::Error::InvalidPath(target.to_owned()));
    }
    let parent = target
        .parent()
        .filter(|p| !p.as_os_str().is_empty())
        .unwrap_or(Path::new("."));
    let staging = tempfile::tempdir_in(parent).map_err(io_error)?;
    let staged = staging.path().join("snapshot.sqlite");
    let mut dst = Connection::open(&staged)?;
    {
        let bk = rusqlite::backup::Backup::new(conn, &mut dst)?;
        bk.run_to_completion(5, std::time::Duration::from_millis(250), None)?;
    }
    // Read the snapshot's source set, not a potentially newer live source set.
    let digests = {
        let mut sources = dst.prepare("SELECT sha256 FROM sources")?;
        sources
            .query_map([], |r| r.get::<_, String>(0))?
            .collect::<rusqlite::Result<Vec<_>>>()?
    };
    for digest in &digests {
        raw_objects::persist(&dst, &raw_objects::read(conn, digest)?)?;
    }
    let staged_objects = raw_objects::root(&dst)?;
    dst.execute_batch("PRAGMA wal_checkpoint(TRUNCATE); PRAGMA journal_mode=DELETE;")?;
    drop(dst);
    std::fs::OpenOptions::new()
        .read(true)
        .write(true)
        .open(&staged)
        .map_err(io_error)?
        .sync_all()
        .map_err(io_error)?;
    // Publish originals first and database last, never overwrite a prior backup.
    // A crash can leave an object-only directory; preserve it for manual recovery.
    std::fs::create_dir(&final_objects).map_err(io_error)?;
    let mut publication = Publication {
        directory: final_objects.clone(),
        files: Vec::new(),
        committed: false,
    };
    for digest in digests {
        let path = final_objects.join(&digest);
        std::fs::hard_link(staged_objects.join(digest), &path).map_err(io_error)?;
        publication.files.push(path);
    }
    std::fs::hard_link(&staged, target).map_err(io_error)?;
    publication.committed = true;
    Ok(())
}

struct Publication {
    directory: PathBuf,
    files: Vec<PathBuf>,
    committed: bool,
}
impl Drop for Publication {
    fn drop(&mut self) {
        if !self.committed {
            for path in &self.files {
                let _ = std::fs::remove_file(path);
            }
            let _ = std::fs::remove_dir(&self.directory);
        }
    }
}

/// Restore a snapshot file into `dst` (the destination workspace connection).
/// The snapshot is opened read-only; content is copied via the Online Backup API.
pub fn restore(snapshot_path: &str, dst: &mut Connection) -> rusqlite::Result<()> {
    raw_objects::reject_links(Path::new(snapshot_path))?;
    let src =
        Connection::open_with_flags(snapshot_path, rusqlite::OpenFlags::SQLITE_OPEN_READ_ONLY)?;
    // Keep validation and Online Backup on one SQLite read snapshot.
    let read_snapshot = src.unchecked_transaction()?;
    validate_workspace(&src)?;
    let objects = {
        let mut sources = src.prepare("SELECT sha256 FROM sources")?;
        sources
            .query_map([], |r| r.get::<_, String>(0))?
            .map(|digest| raw_objects::read(&src, &digest?))
            .collect::<rusqlite::Result<Vec<_>>>()?
    };
    // Validate every original before overwriting any destination database page.
    // Persisted immutable objects can safely precede the atomic SQLite backup.
    for bytes in objects {
        raw_objects::persist(dst, &bytes)?;
    }
    {
        let bk = rusqlite::backup::Backup::new(&src, dst)?;
        bk.run_to_completion(5, std::time::Duration::from_millis(250), None)?;
    }
    read_snapshot.commit()?;
    Ok(())
}

/// Verify a snapshot/restored db: compare schema and canonical row-content
/// digests for every table, and validate persisted source object hashes.
pub fn verify_counts(a: &Connection, b: &Connection) -> rusqlite::Result<bool> {
    // Hold each database on one read view for the entire comparison. Otherwise
    // a writer could commit between table digests and make one database appear
    // internally inconsistent even though each query is individually valid.
    let snapshot_a = a.unchecked_transaction()?;
    let snapshot_b = b.unchecked_transaction()?;
    let result = (|| -> rusqlite::Result<bool> {
        validate_workspace(&snapshot_a)?;
        validate_workspace(&snapshot_b)?;
        verify_source_objects(&snapshot_a)?;
        verify_source_objects(&snapshot_b)?;
        if schema_objects(&snapshot_a)? != schema_objects(&snapshot_b)? {
            return Ok(false);
        }
        let tables_a = table_names(&snapshot_a)?;
        let tables_b = table_names(&snapshot_b)?;
        if tables_a != tables_b {
            return Ok(false);
        }
        for table in tables_a {
            if table_content_digest(&snapshot_a, &table)?
                != table_content_digest(&snapshot_b, &table)?
            {
                return Ok(false);
            }
        }
        Ok(true)
    })()?;
    snapshot_a.commit()?;
    snapshot_b.commit()?;
    Ok(result)
}

fn table_content_digest(conn: &Connection, table: &str) -> rusqlite::Result<(u64, String)> {
    let quoted = format!("\"{}\"", table.replace('"', "\"\""));
    let column_count = conn
        .prepare(&format!("SELECT * FROM {quoted} LIMIT 0"))?
        .column_count();
    let order = (1..=column_count)
        .map(|ordinal| ordinal.to_string())
        .collect::<Vec<_>>()
        .join(", ");
    let mut stmt = conn.prepare(&format!("SELECT * FROM {quoted} ORDER BY {order}"))?;
    let mut rows = stmt.query([])?;
    let mut digest = Sha256::new();
    digest.update((column_count as u64).to_le_bytes());
    let mut row_count = 0u64;
    while let Some(row) = rows.next()? {
        digest.update([0xA1]);
        for column in 0..column_count {
            match row.get_ref(column)? {
                rusqlite::types::ValueRef::Null => digest.update([0]),
                rusqlite::types::ValueRef::Integer(value) => {
                    digest.update([1]);
                    digest.update(value.to_le_bytes());
                }
                rusqlite::types::ValueRef::Real(value) => {
                    digest.update([2]);
                    digest.update(value.to_bits().to_le_bytes());
                }
                rusqlite::types::ValueRef::Text(value) => {
                    digest.update([3]);
                    digest.update((value.len() as u64).to_le_bytes());
                    digest.update(value);
                }
                rusqlite::types::ValueRef::Blob(value) => {
                    digest.update([4]);
                    digest.update((value.len() as u64).to_le_bytes());
                    digest.update(value);
                }
            }
        }
        digest.update([0xAF]);
        row_count += 1;
    }
    digest.update(row_count.to_le_bytes());
    Ok((row_count, hex::encode(digest.finalize())))
}

fn schema_objects(
    conn: &Connection,
) -> rusqlite::Result<Vec<(String, String, String, Option<String>)>> {
    conn.prepare(
        "SELECT type, name, tbl_name, sql FROM sqlite_master
         WHERE name NOT LIKE 'sqlite_%' ORDER BY type, name",
    )?
    .query_map([], |row| {
        Ok((row.get(0)?, row.get(1)?, row.get(2)?, row.get(3)?))
    })?
    .collect()
}

fn table_names(conn: &Connection) -> rusqlite::Result<Vec<String>> {
    conn.prepare(
        "SELECT name FROM sqlite_master WHERE type='table'
         AND (name NOT LIKE 'sqlite_%' OR name='sqlite_sequence') ORDER BY name",
    )?
    .query_map([], |row| row.get(0))?
    .collect()
}

fn validate_workspace(conn: &Connection) -> rusqlite::Result<()> {
    let version: String = conn.query_row(
        "SELECT value FROM workspace_meta WHERE key='schema_version'",
        [],
        |row| row.get(0),
    )?;
    let integrity: Vec<String> = conn
        .prepare("PRAGMA integrity_check")?
        .query_map([], |row| row.get(0))?
        .collect::<rusqlite::Result<Vec<_>>>()?;
    if integrity.as_slice() != ["ok"]
        || version != archeaxis_store_sqlite::SCHEMA_VERSION.to_string()
        || conn.prepare("PRAGMA foreign_key_check")?.exists([])?
    {
        return Err(rusqlite::Error::InvalidQuery);
    }
    Ok(())
}

fn verify_source_objects(conn: &Connection) -> rusqlite::Result<()> {
    let mut sources = conn.prepare("SELECT sha256 FROM sources")?;
    for digest in sources.query_map([], |row| row.get::<_, String>(0))? {
        raw_objects::read(conn, &digest?)?;
    }
    Ok(())
}
