//! FTS5 retrieval across sources, personal knowledge and accepted candidates.
use rusqlite::Connection;

/// Turn text a person typed into an FTS5 query that means what they typed.
///
/// The query string used to be handed to `MATCH` verbatim, which made FTS5 syntax out of
/// ordinary text: `zzz-no-such-term` became a column filter and failed with `no such column`,
/// `zzz OR` and `""` were syntax errors, and an unbalanced quote was `unterminated string`.
/// Every one of those surfaced to the caller as a failure, while the contract says a search
/// that finds nothing is `200` with `count=0`.
///
/// FTS5 has no escape sequence for a query term, but it reads a double-quoted string as a
/// phrase and accepts a doubled `""` inside it as one literal quote. So each whitespace token
/// becomes one quoted phrase with its quotes doubled.
///
/// The tokens are joined with `OR`, matching FTS5's own default for space-separated terms and
/// keeping a wide lexical net: a hit on any typed word is a hit. `AND` was tried first and
/// rejected because it made the obvious case worse - someone typing two words that both
/// appear in separate sentences got nothing - and because this index has no vector or
/// reranker behind it to recover recall. Ranking still orders the results, so a row matching
/// more of the query sorts above one matching less.
///
/// Returns `None` when nothing searchable is left, which the caller turns into an empty
/// result rather than a query that cannot be parsed.
fn fts_query(user_text: &str) -> Option<String> {
    let terms: Vec<String> = user_text
        .split_whitespace()
        .map(|term| format!("\"{}\"", term.replace('"', "\"\"")))
        .collect();
    if terms.is_empty() {
        return None;
    }
    Some(terms.join(" OR "))
}

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
    let Some(query) = fts_query(query) else {
        return Ok(Vec::new());
    };
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
    let Some(query) = fts_query(query) else {
        return Ok(Vec::new());
    };
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
