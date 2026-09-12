//! Archive round-trip: build a populated vNext workspace, export, restore into
//! a fresh DB, verify counts + a content sample.
use archeaxis_application::jobs::{self, LossReceipt};
use archeaxis_domain::{anchor, knowledge, search, source};
use archeaxis_store_sqlite::init_workspace;
use rusqlite::Connection;

fn count(conn: &Connection, table: &str) -> i64 {
    conn.query_row(&format!("SELECT count(*) FROM {table}"), [], |r| r.get(0))
        .unwrap()
}

#[test]
fn archive_roundtrip() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("ws.sqlite");
    let archive = dir.path().join("archive").to_str().unwrap().to_string();

    // populate
    let mut conn = init_workspace(db.to_str().unwrap()).unwrap();
    let o = source::import_source(&mut conn, b"archive note body", "a.txt", None).unwrap();
    let sid = match o {
        source::ImportOutcome::Imported { source_id, .. } => source_id,
        _ => panic!("import"),
    };
    source::record_transform(
        &mut conn,
        &sid,
        "python-worker",
        "archive note body (clean)",
        Some("stripped"),
    )
    .unwrap();
    let aid = anchor::add_anchor(&mut conn, &sid, "r1", r#"{"start":0,"end":5}"#).unwrap();
    let kid = knowledge::create_knowledge(
        &mut conn,
        "PERSONAL_DEFINITION",
        "进步本定义",
        "candidate",
        None,
        Some(&aid),
        "owner",
    )
    .unwrap();
    knowledge::review(&mut conn, &kid, "accepted", "owner", Some("ok"), None).unwrap();
    learning::record(&mut conn, "k-1", "quiz", r#"{"ok":true}"#, 2)
        .unwrap_or_else(|_| unreachable!());
    jobs::enqueue(&mut conn, "job-a", "transform", &sid).unwrap();
    jobs::complete(
        &mut conn,
        "job-a",
        "python-worker",
        "archive note body (clean)",
        Some(&LossReceipt {
            engine: "python-worker".into(),
            engine_version: "0.1".into(),
            params: serde_json::json!({}),
            loss_note: None,
            losses: None, covered: None, total: None, coverage: None,
        }),
    )
    .unwrap();
    conn.execute("INSERT INTO job_attempts(job_id,attempt,request_id,request_json,state) VALUES('job-a',1,'archive-r','{}','succeeded')",[]).unwrap();
    conn.execute("INSERT INTO job_outputs(job_id,attempt,kind,metadata_json,content) VALUES('job-a',1,'document_structure','{}',?1)",
        ["非空结构😀\r\n原始字节"]).unwrap();
    drop(conn);

    // export
    let m = archeaxis_archive::export_workspace(db.to_str().unwrap(), &archive).unwrap();
    assert_eq!(m.tables["sources"].rows, 1);
    assert!(
        m.tables["transforms"].rows >= 2,
        "transform receipts: {:?}",
        m.tables["transforms"]
    );
    assert_eq!(m.manifest_sha256.len(), 64);

    // restore into a fresh DB
    let db2 = dir.path().join("ws2.sqlite");
    let m2 = archeaxis_archive::restore_workspace(&archive, db2.to_str().unwrap()).unwrap();
    assert_eq!(m.manifest_sha256, m2.manifest_sha256);

    let conn2 = Connection::open(db2.to_str().unwrap()).unwrap();
    assert_eq!(count(&conn2, "sources"), 1);
    assert_eq!(count(&conn2, "knowledge"), 1);
    assert_eq!(count(&conn2, "review_events"), 1);
    assert_eq!(count(&conn2, "jobs"), 1);
    assert_eq!(count(&conn2, "job_attempts"), 1);
    assert_eq!(conn2.query_row("SELECT content FROM job_outputs",[],|r|r.get::<_,String>(0)).unwrap(),"非空结构😀\r\n原始字节");
    // content survived
    let text: String = conn2
        .query_row(
            "SELECT text FROM transforms ORDER BY transform_id DESC LIMIT 1",
            [],
            |r| r.get(0),
        )
        .unwrap();
    assert!(text.contains("archive note body"));
}

mod learning {
    use rusqlite::Connection;
    pub fn record(
        conn: &mut Connection,
        key: &str,
        kind: &str,
        outcome: &str,
        days: i64,
    ) -> rusqlite::Result<i64> {
        let next = if days > 0 {
            Some(format!("+{days} day"))
        } else {
            None
        };
        conn.execute(
            "INSERT INTO learning_events(item_key, kind, outcome, next_review) VALUES(?1,?2,?3,?4)",
            rusqlite::params![key, kind, outcome, next],
        )?;
        Ok(conn.last_insert_rowid())
    }
}
