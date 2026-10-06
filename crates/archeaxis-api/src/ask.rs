//! G2's Ask: an answer that carries the citations a reader can check.
//!
//! The golden path requires "Reader / Ask with citation", and the reason it says *with citation* is
//! that an answer without one cannot be checked. So this module is built around a single rule: the
//! answer is a **selection of the workspace's own accepted bodies that matched the question**, and
//! every sentence of it is attributed to a knowledge item, its anchor and the source file the anchor
//! points at. A model may summarise that material, but the citations are produced here rather than
//! by the model, so an unverifiable answer cannot masquerade as a grounded one.
//!
//! Two limits are stated rather than smoothed over:
//!
//! * No match means **no answer**, not an empty one. `answered` is false and `answer` is `null`, with
//!   the query echoed, because an empty string would read as "the workspace has nothing to say" when
//!   the truth is "it did not find anything for that question".
//! * Nothing here writes knowledge. An answer is a projection of what was already accepted.

use rusqlite::{Connection, OptionalExtension};
use serde_json::json;

use archeaxis_domain::search;

/// One citation: the knowledge item, the anchor it came from, and the source file behind it.
///
/// The whole chain is carried because a citation that stops at the knowledge id is not checkable -
/// the reader needs the file and the position inside it.
fn citation(conn: &Connection, knowledge_id: &str, status: &str, body: &str) -> serde_json::Value {
    let chain = conn
        .query_row(
            "SELECT k.anchor_id, a.source_id, a.source_revision, a.position, s.original_name
             FROM knowledge k
             LEFT JOIN anchors a ON a.anchor_id = k.anchor_id
             LEFT JOIN sources s ON s.source_id = a.source_id
             WHERE k.knowledge_id = ?1",
            [knowledge_id],
            |row| {
                Ok((
                    row.get::<_, Option<String>>(0)?,
                    row.get::<_, Option<String>>(1)?,
                    row.get::<_, Option<String>>(2)?,
                    row.get::<_, Option<String>>(3)?,
                    row.get::<_, Option<String>>(4)?,
                ))
            },
        )
        .optional()
        .unwrap_or(None);
    let (anchor_id, source_id, source_revision, position, original_name) =
        chain.unwrap_or((None, None, None, None, None));

    // A body that is not tied to an anchor is said to be unattached rather than given invented
    // provenance: personal notes legitimately have none, and pretending otherwise would be worse
    // than admitting it.
    let attached = anchor_id.is_some() && source_id.is_some();
    json!({
        "knowledge_id": knowledge_id,
        "status": status,
        "excerpt": excerpt(body, 240),
        "anchor": {
            "anchor_id": anchor_id,
            "source_id": source_id,
            "source_revision": source_revision,
            "position": position,
        },
        "source": { "original_name": original_name },
        "attached_to_a_source": attached,
        "attachment_note": if attached {
            "this knowledge item is anchored to a position in a source file"
        } else {
            "this knowledge item has no anchor, so its provenance is the author rather than a file"
        },
    })
}

/// A bounded excerpt, cut on a word boundary where one is near enough to be worth respecting.
fn excerpt(body: &str, limit: usize) -> String {
    let trimmed = body.trim();
    if trimmed.chars().count() <= limit {
        return trimmed.to_string();
    }
    let cut: String = trimmed.chars().take(limit).collect();
    match cut.rfind(char::is_whitespace) {
        Some(at) if at > limit / 2 => format!("{}…", cut[..at].trim_end()),
        _ => format!("{cut}…"),
    }
}

/// The answer to one question, with its citations.
pub fn ask(conn: &Connection, question: &str, limit: i64) -> rusqlite::Result<serde_json::Value> {
    if question.trim().is_empty() {
        // Refused by the caller as a 422; this guard exists so the function is safe on its own.
        return Ok(json!({
            "schema": "archeaxis.ask/v1",
            "question": question,
            "answered": false,
            "answer": serde_json::Value::Null,
            "citations": [],
            "count": 0,
            "note": "a question is required",
        }));
    }

    // The domain search already owns query semantics, so the same matcher answers a question as
    // answers a search: two matchers would disagree, and a reader could not tell which one ran.
    let rows = search::search(conn, question, limit)?;
    let mut citations = Vec::with_capacity(rows.len());
    for (knowledge_id, status, _head) in &rows {
        // The full body, not the search row's 60-character head: an excerpt cut at 60 characters is
        // not enough to check an answer against.
        let body: Option<String> = conn
            .query_row(
                "SELECT body FROM knowledge WHERE knowledge_id = ?1",
                [knowledge_id],
                |row| row.get(0),
            )
            .optional()?;
        let body = body.unwrap_or_default();
        // Inactive (superseded) knowledge is offered as a citation but marked, rather than hidden:
        // a reader asking about something that was replaced needs to see that it was.
        let active =
            archeaxis_domain::knowledge::is_knowledge_active(conn, knowledge_id).unwrap_or(false);
        let mut entry = citation(conn, knowledge_id, status, &body);
        entry["active"] = json!(active);
        entry["active_note"] = json!(if active {
            "this is the current version of the item"
        } else {
            "this item has been superseded; a newer version exists"
        });
        citations.push(entry);
    }

    let count = citations.len();
    let attached = citations
        .iter()
        .filter(|entry| entry["attached_to_a_source"] == true)
        .count();
    // The answer is the material itself, not a paraphrase of it. Anything the Core composed would be
    // a claim with no citation, which is exactly what this route exists to avoid.
    let answer = if citations.is_empty() {
        serde_json::Value::Null
    } else {
        serde_json::Value::String(
            citations
                .iter()
                .filter_map(|entry| entry["excerpt"].as_str())
                .collect::<Vec<_>>()
                .join("\n\n"),
        )
    };

    Ok(json!({
        "schema": "archeaxis.ask/v1",
        "question": question,
        "answered": count > 0,
        "answer": answer,
        "citations": citations,
        "count": count,
        "citations_attached_to_a_source": attached,
        "note": if count == 0 {
            "no accepted material matched this question, so there is no answer rather than an empty \
             one"
        } else {
            "the answer is the matching accepted material itself; every part of it is cited, and \
             nothing here was written to the workspace"
        },
        "authority": "projection_of_accepted_knowledge",
    }))
}

#[cfg(test)]
mod tests {
    use super::excerpt;

    #[test]
    fn a_short_body_is_returned_whole() {
        assert_eq!(excerpt("short body", 240), "short body");
    }

    #[test]
    fn a_long_body_is_cut_on_a_word_boundary_and_marked() {
        let body = "alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu";
        let cut = excerpt(body, 20);
        assert!(cut.ends_with('…'), "{cut}");
        // the cut does not end mid-word, so a citation does not read as a typo
        assert!(!cut.trim_end_matches('…').ends_with("gam"), "{cut}");
    }
}
