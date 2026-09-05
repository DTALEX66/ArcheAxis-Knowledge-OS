//! Backup/restore via the SQLite Online Backup API (rusqlite `backup`).
use rusqlite::Connection;

/// Consistent snapshot of `src` into `dst_path` using the Online Backup API.
pub fn backup(conn: &Connection, dst_path: &str) -> rusqlite::Result<()> {
    let mut dst = Connection::open(dst_path)?;
    {
        let mut bk = rusqlite::backup::Backup::new(conn, &mut dst)?;
        bk.run_to_completion(5, std::time::Duration::from_millis(250), None)?;
    }
    dst.execute_batch("PRAGMA wal_checkpoint(TRUNCATE);")?;
    Ok(())
}

/// Restore a snapshot file into `dst` (the destination workspace connection).
/// The snapshot is opened read-only; content is copied via the Online Backup API.
pub fn restore(snapshot_path: &str, dst: &mut Connection) -> rusqlite::Result<()> {
    let src =
        Connection::open_with_flags(snapshot_path, rusqlite::OpenFlags::SQLITE_OPEN_READ_ONLY)?;
    {
        let mut bk = rusqlite::backup::Backup::new(&src, dst)?;
        bk.run_to_completion(5, std::time::Duration::from_millis(250), None)?;
    }
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
