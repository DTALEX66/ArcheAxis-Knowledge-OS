//! A user's search text must never reach FTS5 as syntax.
//!
//! `search` and `search_transforms` passed the query straight into `MATCH`, so ordinary user
//! text was parsed as an FTS5 expression: a hyphen produced `no such column: no`, a space in
//! `zzz OR` produced a syntax error, an unbalanced quote produced `unterminated string`, and
//! an empty query produced `fts5: syntax error near ""`. All of them were answered as errors
//! carrying the raw engine message. The published contract promises the opposite - `200` with
//! `count=0` is a successful empty state - so any query a person might type must either match
//! or match nothing, never fail.
//!
//! These tests drive the real functions against a real FTS5 table, so the escaping is proven
//! by the engine rather than by a stand-in for it.

use archeaxis_domain::search;
use archeaxis_domain::source::{self, ImportOutcome};
use archeaxis_store_sqlite::init_workspace;

fn workspace() -> (tempfile::TempDir, rusqlite::Connection) {
    let dir = tempfile::tempdir().unwrap();
    let conn = init_workspace(dir.path().join("s.sqlite").to_str().unwrap()).unwrap();
    (dir, conn)
}

fn seeded(text: &str) -> (tempfile::TempDir, rusqlite::Connection) {
    let (dir, mut conn) = workspace();
    let source_id =
        match source::import_source(&mut conn, b"%PDF-1.4 payload", "report.pdf", None).unwrap() {
            ImportOutcome::Imported { source_id, .. } => source_id,
            ImportOutcome::Duplicate { source_id, .. } => source_id,
        };
    source::record_transform(
        &mut conn,
        &source_id,
        "pymupdf-native-pdf",
        text,
        Some("no transform applied"),
    )
    .unwrap();
    (dir, conn)
}

/// Every one of these is something a person can type, and none may be an error.
const ORDINARY_USER_TEXT: &[&str] = &[
    "radius",
    "6371",
    "zzz-no-such-term",     // a hyphen: read as a column filter when unquoted
    "zzz OR",               // a trailing operator
    "AND OR NOT",           // only operators
    "\"unterminated quote", // an unbalanced quote
    "quote\"inside",        // a quote in the middle
    "100% * !",             // characters with FTS5 meaning
    "  ",                   // whitespace only
    "",                     // empty
    "知识点",               // non-Latin text
];

#[test]
fn transform_search_never_fails_on_ordinary_user_text() {
    let (_dir, conn) = seeded("the extracted radius is 6371 km");
    for query in ORDINARY_USER_TEXT {
        let result = search::search_transforms(&conn, query, 10);
        assert!(
            result.is_ok(),
            "query {query:?} must not be an error: {:?}",
            result.err()
        );
    }
}

#[test]
fn knowledge_search_never_fails_on_ordinary_user_text() {
    let (_dir, conn) = workspace();
    for query in ORDINARY_USER_TEXT {
        let result = search::search(&conn, query, 10);
        assert!(
            result.is_ok(),
            "query {query:?} must not be an error: {:?}",
            result.err()
        );
    }
}

#[test]
fn a_matching_query_still_matches() {
    let (_dir, conn) = seeded("the extracted radius is 6371 km");
    assert_eq!(
        search::search_transforms(&conn, "radius", 10)
            .unwrap()
            .len(),
        1,
        "escaping must not stop a plain word from matching"
    );
    assert_eq!(
        search::search_transforms(&conn, "6371", 10).unwrap().len(),
        1
    );
    // multi-word: tokens are combined, so a search over both words still finds the text
    assert_eq!(
        search::search_transforms(&conn, "radius 6371", 10)
            .unwrap()
            .len(),
        1
    );
}

#[test]
fn a_hyphenated_search_is_text_not_a_column_filter() {
    let (_dir, conn) = seeded("the radius is 6371 km");

    // A hyphen is FTS5's column-filter syntax when unquoted, which is what failed before.
    // Quoted, it becomes a separator inside one phrase, so `radius-6371` asks for `radius`
    // immediately followed by `6371` - and the text has a word in between, so this must be
    // an empty result rather than an error or a wrong match.
    let hits = search::search_transforms(&conn, "radius-6371", 10).unwrap();
    assert!(
        hits.is_empty(),
        "an adjacent-phrase search must not match non-adjacent words: {hits:?}"
    );

    // And when the two parts really are adjacent, the same query finds them, which shows the
    // hyphen is being read as a separator and not as a filter or a literal character.
    let (_dir2, adjacent) = seeded("the radius-6371 datum is fixed");
    assert_eq!(
        search::search_transforms(&adjacent, "radius-6371", 10)
            .unwrap()
            .len(),
        1,
        "a hyphenated phrase must match when the parts are adjacent"
    );
}

#[test]
fn a_query_that_matches_nothing_is_empty_not_an_error() {
    let (_dir, conn) = seeded("the extracted radius is 6371 km");
    for query in ["zzzznosuchterm", "zzz-no-such-term", "100% * !"] {
        let hits = search::search_transforms(&conn, query, 10).unwrap();
        assert!(hits.is_empty(), "{query:?} unexpectedly matched: {hits:?}");
    }
    // and the empty states, which used to be the loudest errors of all
    for query in ["", "   ", "AND OR NOT"] {
        let hits = search::search_transforms(&conn, query, 10).unwrap();
        assert!(hits.is_empty(), "{query:?} must match nothing: {hits:?}");
    }
}
