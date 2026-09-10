//! FTS5 retrieval across sources, personal knowledge and accepted candidates.
use rusqlite::Connection;

const FTS_SQL: &str = r#"
CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_fts USING fts5(
    body, knowledge_id UNINDEXED, status UNINDEXED
);
"#;

/// Ensure the FTS table exists.
pub fn ensure_fts(conn: &Connection) -> rusqlite::Result<()> {
    conn.execute_batch(FTS_SQL)?;
    Ok(())
}

/// Refresh FTS from the knowledge table (backfill after ensure).
pub fn reindex(conn: &Connection) -> rusqlite::Result<()> {
    ensure_fts(conn)?;
    conn.execute_batch("DELETE FROM knowledge_fts;")?;
    conn.execute_batch(
        "INSERT INTO knowledge_fts(rowid, body, knowledge_id, status)
         SELECT rowid, body, knowledge_id, status FROM knowledge;",
    )?;
    Ok(())
}

/// Full-text search returns (knowledge_id, status, snippet-head).
pub fn search(
    conn: &Connection,
    query: &str,
    limit: i64,
) -> rusqlite::Result<Vec<(String, String, String)>> {
    reindex(conn)?; // Day-0: rebuild before query (small data; triggers land in a later slice)
    let mut stmt = conn.prepare(
        "SELECT knowledge_id, status, substr(body,1,60) FROM knowledge_fts WHERE knowledge_fts MATCH ?1 ORDER BY rank LIMIT ?2")?;
    let rows = stmt.query_map(rusqlite::params![query, limit], |r| {
        Ok((r.get(0)?, r.get(1)?, r.get(2)?))
    })?;
    let mut out = Vec::new();
    for row in rows {
        out.push(row?);
    }
    Ok(out)
}

const TRANSFORM_FTS_SQL: &str = r#"
CREATE VIRTUAL TABLE IF NOT EXISTS transform_fts USING fts5(
    text, transform_id UNINDEXED, source_id UNINDEXED, engine UNINDEXED
);
"#;

/// Ensure the extracted-text index exists.
pub fn ensure_transform_fts(conn: &Connection) -> rusqlite::Result<()> {
    conn.execute_batch(TRANSFORM_FTS_SQL)?;
    Ok(())
}

/// Refresh the extracted-text index from `transforms` (rebuilt per query, the
/// same Day-0 pattern the knowledge index uses).
pub fn reindex_transforms(conn: &Connection) -> rusqlite::Result<()> {
    ensure_transform_fts(conn)?;
    conn.execute_batch("DELETE FROM transform_fts;")?;
    conn.execute_batch(
        "INSERT INTO transform_fts(rowid, text, transform_id, source_id, engine)
         SELECT rowid, text, transform_id, source_id, engine FROM transforms;",
    )?;
    Ok(())
}

/// R08: search the text extracted by the conversion routes.
///
/// Returns (transform_id, source_id, engine, snippet-head) so a hit can be
/// attributed to its original file and to the engine that produced it. This is
/// retrieval of *extracted text*, not a claim that the text is knowledge: type,
/// evidence and qualification remain separate semantics.
pub fn search_transforms(
    conn: &Connection,
    query: &str,
    limit: i64,
) -> rusqlite::Result<Vec<(i64, String, String, String)>> {
    reindex_transforms(conn)?;
    let mut stmt = conn.prepare(
        "SELECT transform_id, source_id, engine, substr(text,1,60) FROM transform_fts
         WHERE transform_fts MATCH ?1 ORDER BY rank LIMIT ?2",
    )?;
    let rows = stmt.query_map(rusqlite::params![query, limit], |r| {
        Ok((r.get(0)?, r.get(1)?, r.get(2)?, r.get(3)?))
    })?;
    let mut out = Vec::new();
    for row in rows {
        out.push(row?);
    }
    Ok(out)
}
