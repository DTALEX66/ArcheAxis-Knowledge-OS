//! Backup/restore via the SQLite Online Backup API (rusqlite `backup`).
use rusqlite::Connection;
use archeaxis_store_sqlite::raw_objects;
use std::path::{Path, PathBuf};

fn io_error(error: std::io::Error) -> rusqlite::Error {
    rusqlite::Error::ToSqlConversionFailure(Box::new(error))
}

/// Consistent snapshot of `src` into `dst_path` using the Online Backup API.
pub fn backup(conn: &Connection, dst_path: &str) -> rusqlite::Result<()> {
    let target = Path::new(dst_path);
    raw_objects::reject_links(target)?;
    raw_objects::reject_links(Path::new(conn.path().ok_or(rusqlite::Error::InvalidQuery)?))?;
    let final_objects = PathBuf::from(format!("{dst_path}.objects"));
    raw_objects::reject_links(&final_objects)?;
    if target.exists() || final_objects.exists() {
        return Err(rusqlite::Error::InvalidPath(target.to_owned()));
    }
    let parent = target.parent().filter(|p| !p.as_os_str().is_empty()).unwrap_or(Path::new("."));
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
        sources.query_map([], |r| r.get::<_, String>(0))?.collect::<rusqlite::Result<Vec<_>>>()?
    };
    for digest in &digests { raw_objects::persist(&dst, &raw_objects::read(conn, digest)?)?; }
    let staged_objects = raw_objects::root(&dst)?;
    dst.execute_batch("PRAGMA wal_checkpoint(TRUNCATE); PRAGMA journal_mode=DELETE;")?;
    drop(dst);
    std::fs::OpenOptions::new().read(true).write(true).open(&staged)
        .map_err(io_error)?.sync_all().map_err(io_error)?;
    // Publish originals first and database last, never overwrite a prior backup.
    // A crash can leave an object-only directory; preserve it for manual recovery.
    std::fs::create_dir(&final_objects).map_err(io_error)?;
    let mut publication = Publication { directory: final_objects.clone(), files: Vec::new(), committed: false };
    for digest in digests {
        let path = final_objects.join(&digest);
        std::fs::hard_link(staged_objects.join(digest), &path).map_err(io_error)?;
        publication.files.push(path);
    }
    std::fs::hard_link(&staged, target).map_err(io_error)?;
    publication.committed = true;
    Ok(())
}

struct Publication { directory: PathBuf, files: Vec<PathBuf>, committed: bool }
impl Drop for Publication {
    fn drop(&mut self) {
        if !self.committed {
            for path in &self.files { let _ = std::fs::remove_file(path); }
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
    let version: String = src.query_row(
        "SELECT value FROM workspace_meta WHERE key='schema_version'", [], |r| r.get(0),
    )?;
    if version != archeaxis_store_sqlite::SCHEMA_VERSION.to_string()
        || src.prepare("PRAGMA foreign_key_check")?.exists([])? {
        return Err(rusqlite::Error::InvalidQuery);
    }
    let objects = {
        let mut sources = src.prepare("SELECT sha256 FROM sources")?;
        sources.query_map([], |r| r.get::<_, String>(0))?
            .map(|digest| raw_objects::read(&src, &digest?))
            .collect::<rusqlite::Result<Vec<_>>>()?
    };
    // Validate every original before overwriting any destination database page.
    // Persisted immutable objects can safely precede the atomic SQLite backup.
    for bytes in objects { raw_objects::persist(dst, &bytes)?; }
    {
        let bk = rusqlite::backup::Backup::new(&src, dst)?;
        bk.run_to_completion(5, std::time::Duration::from_millis(250), None)?;
    }
    read_snapshot.commit()?;
    Ok(())
}

/// Verify a snapshot/restored db: compare object counts between two databases.
pub fn verify_counts(a: &Connection, b: &Connection) -> rusqlite::Result<bool> {
    let tables = [
        "sources",
        "transforms",
        "anchors",
        "knowledge",
        "learning_events",
    ];
    for t in tables {
        let na: i64 = a.query_row(&format!("SELECT count(*) FROM {t}"), [], |r| r.get(0))?;
        let nb: i64 = b.query_row(&format!("SELECT count(*) FROM {t}"), [], |r| r.get(0))?;
        if na != nb {
            return Ok(false);
        }
    }
    Ok(true)
}
