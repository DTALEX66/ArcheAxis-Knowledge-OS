use archeaxis_domain::ui_state::{
    self, ClearSaved, Draft, Error, Recover, RecoveryAction, State, Write,
};
use rusqlite::Connection;
use serde_json::{Value, json};
use std::collections::BTreeMap;

fn fixture(path: &std::path::Path) -> Connection {
    let conn = Connection::open(path).unwrap();
    conn.execute_batch("CREATE TABLE IF NOT EXISTS workspace_meta(key TEXT PRIMARY KEY,value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS documents(document_id TEXT PRIMARY KEY);
        CREATE TABLE IF NOT EXISTS document_versions(document_id TEXT,version INTEGER,editor_json TEXT);
        INSERT OR IGNORE INTO documents VALUES('doc_a');").unwrap();
    if conn
        .query_row("SELECT count(*) FROM document_versions", [], |r| {
            r.get::<_, i64>(0)
        })
        .unwrap()
        == 0
    {
        conn.execute(
            "INSERT INTO document_versions VALUES('doc_a',1,?1)",
            [body("original").to_string()],
        )
        .unwrap();
    }
    conn
}
fn body(text: &str) -> Value {
    json!({"type":"doc","content":[{"type":"paragraph","attrs":{"block_id":"block_a"},"content":[{"type":"text","text":text}]}]})
}

#[test]
fn job_journal_reopens_refuses_old_client_omission_and_requires_exact_clearance() {
    let dir = tempfile::tempdir().unwrap();
    let path = dir.path().join("jobs.sqlite");
    let mut conn = fixture(&path);
    conn.execute_batch("CREATE TABLE sources(source_id TEXT PRIMARY KEY,sha256 TEXT);
        CREATE TABLE jobs(job_id TEXT PRIMARY KEY,input_ref TEXT,kind TEXT);
        CREATE TABLE job_attempts(job_id TEXT,request_id TEXT,state TEXT,request_json TEXT);
        INSERT INTO sources VALUES('source',printf('%064d',0));
        INSERT INTO jobs VALUES('job','source','text');").unwrap();
    let basis = ui_state::read(&mut conn).unwrap();
    let entry = json!({"source_id":"source","source_revision":"0".repeat(64),"job_id":"job","request_id":"frozen",
        "kind":"text","body":{"deadline_ms":60000,"split":false,"words":false},"surface":"manual","mode":"single","origin_restore_epoch":"initial","relative":null});
    let mut payload = json!({"workspace_id":basis["workspace_id"],"restore_epoch":"initial","state_revision":basis["state_revision"],
        "state":{"drafts":{},"opened_documents":[],"active_document":null,"page_id":"03","pending_original":null,"pending_jobs":{"frozen":entry}}});
    let written = ui_state::write(&mut conn,serde_json::from_value(payload.clone()).unwrap()).unwrap();
    drop(conn);
    let mut conn = fixture(&path);
    assert_eq!(ui_state::read(&mut conn).unwrap()["state"]["pending_jobs"]["frozen"],entry);
    payload["state_revision"] = written["state_revision"].clone();
    payload["state"].as_object_mut().unwrap().remove("pending_jobs");
    assert!(ui_state::write(&mut conn,serde_json::from_value(payload.clone()).unwrap()).is_err());
    payload["state"]["pending_jobs"] = json!({"frozen":entry});
    // Any different binding cannot replace the stored identity.
    payload["state"]["pending_jobs"]["frozen"]["body"]["deadline_ms"] = json!(1);
    assert!(ui_state::write(&mut conn,serde_json::from_value(payload).unwrap()).is_err());
    let clear = |action:&str| serde_json::from_value(json!({"workspace_id":written["workspace_id"],"restore_epoch":"initial","state_revision":written["state_revision"],"request_id":"frozen","action":action})).unwrap();
    assert!(ui_state::clear_job(&mut conn,clear("terminal")).is_err());
    conn.execute("INSERT INTO job_attempts VALUES('another','frozen','succeeded','{}')",[]).unwrap();
    assert!(ui_state::clear_job(&mut conn,clear("abandon_unadmitted")).is_err());
    assert!(ui_state::clear_job(&mut conn,clear("terminal")).is_err());
    conn.execute("DELETE FROM job_attempts",[]).unwrap();
    let cleared = ui_state::clear_job(&mut conn,clear("abandon_unadmitted")).unwrap();
    assert!(cleared["state"].get("pending_jobs").is_none());
    assert!(ui_state::job_abandoned(&conn,"frozen").unwrap());
    assert!(!ui_state::job_abandoned(&conn,"other").unwrap());
    let mut restore_entry=entry.clone();restore_entry["request_id"]=json!("restore_frozen");
    let staged=ui_state::write(&mut conn,serde_json::from_value(json!({"workspace_id":cleared["workspace_id"],"restore_epoch":"initial","state_revision":cleared["state_revision"],"state":{"drafts":{},"opened_documents":[],"active_document":null,"page_id":"03","pending_jobs":{"restore_frozen":restore_entry}}})).unwrap()).unwrap();
    let tombstone_raw: String=conn.query_row("SELECT value FROM workspace_meta WHERE key='ui_job_abandonments_v1'",[],|r|r.get(0)).unwrap();
    let clear_staged=|| serde_json::from_value(json!({"workspace_id":staged["workspace_id"],"restore_epoch":"initial","state_revision":staged["state_revision"],"request_id":"restore_frozen","action":"abandon_unadmitted"})).unwrap();
    let full: BTreeMap<String,String>=(0..256).map(|i|(format!("abandoned_{i}"),"0".repeat(64))).collect();
    conn.execute("UPDATE workspace_meta SET value=?1 WHERE key='ui_job_abandonments_v1'",[serde_json::to_string(&full).unwrap()]).unwrap();
    assert!(ui_state::clear_job(&mut conn,clear_staged()).is_err(),"full tombstones must reject clearance without forgetting any identity");
    assert_eq!(ui_state::read(&mut conn).unwrap(),staged,"failed clearance retains the exact journal and revision");
    assert!(ui_state::job_abandoned(&conn,"abandoned_0").unwrap());
    assert!(ui_state::job_abandoned(&conn,"abandoned_255").unwrap());
    conn.execute("UPDATE workspace_meta SET value='corrupt' WHERE key='ui_job_abandonments_v1'",[]).unwrap();
    assert!(ui_state::job_abandoned(&conn,"unknown").is_err(),"corrupt record cannot prove an identity reusable");
    assert!(ui_state::clear_job(&mut conn,clear_staged()).is_err());
    assert_eq!(ui_state::read(&mut conn).unwrap(),staged);
    conn.execute("UPDATE workspace_meta SET value=?1 WHERE key='ui_job_abandonments_v1'",[tombstone_raw]).unwrap();
    conn.execute("INSERT INTO workspace_meta VALUES('authorization_restore_fence',?1)",[json!({"schema":"archeaxis.authorization-restore-fence/v1","epoch":"b".repeat(32),"blocked_grant_ids":[]}).to_string()]).unwrap();
    let candidate=ui_state::read(&mut conn).unwrap();
    assert_eq!(candidate["recovery_requires_confirmation"],true);
    assert!(candidate["state"].get("pending_jobs").is_none());
    assert_eq!(candidate["recovery_candidates"]["pending_jobs"]["restore_frozen"],restore_entry);
    let recovered=ui_state::recover(&mut conn,serde_json::from_value(json!({"workspace_id":candidate["workspace_id"],"restore_epoch":candidate["restore_epoch"],"state_revision":staged["state_revision"],"action":"preserve"})).unwrap()).unwrap();
    assert!(ui_state::clear_job(&mut conn,serde_json::from_value(json!({"workspace_id":recovered["workspace_id"],"restore_epoch":recovered["restore_epoch"],"state_revision":recovered["state_revision"],"request_id":"restore_frozen","action":"abandon_unadmitted"})).unwrap()).is_err(),"current backup absence cannot prove a pre-restore request never executed");
}
fn request(receipt: &Value, text: &str) -> Write {
    Write {
        workspace_id: receipt["workspace_id"].as_str().unwrap().into(),
        restore_epoch: receipt["restore_epoch"].as_str().unwrap().into(),
        state_revision: receipt["state_revision"].as_i64().unwrap(),
        state: State {
            drafts: BTreeMap::from([(
                "doc_a".into(),
                Draft {
                    base_version: 1,
                    editor_json: body(text),
                },
            )]),
            opened_documents: vec!["doc_a".into()],
            active_document: Some("doc_a".into()),
            page_id: Some("03".into()),
            pending_original: None,
            pending_jobs: BTreeMap::new(),
        },
    }
}
#[test]
fn state_survives_reopen_and_stale_cas_cannot_replace_newer_draft() {
    let dir = tempfile::tempdir().unwrap();
    let path = dir.path().join("db.sqlite");
    let mut conn = fixture(&path);
    let initial = ui_state::read(&mut conn).unwrap();
    let stale = request(&initial, "late old content");
    let saved = ui_state::write(&mut conn, request(&initial, "new 中文 draft")).unwrap();
    assert!(matches!(
        ui_state::write(&mut conn, stale),
        Err(Error::Conflict)
    ));
    drop(conn);
    let mut conn = fixture(&path);
    let reopened = ui_state::read(&mut conn).unwrap();
    assert_eq!(reopened, saved);
    assert_eq!(
        conn.query_row("SELECT count(*) FROM document_versions", [], |r| r
            .get::<_, i64>(0))
            .unwrap(),
        1,
        "working draft is not a committed document version"
    );
}
#[test]
fn invalid_identity_fields_size_and_unknown_types_are_rejected_without_write() {
    let dir = tempfile::tempdir().unwrap();
    let mut conn = fixture(&dir.path().join("db.sqlite"));
    let initial = ui_state::read(&mut conn).unwrap();
    let mut foreign = request(&initial, "x");
    foreign.workspace_id = "foreign".into();
    assert!(matches!(
        ui_state::write(&mut conn, foreign),
        Err(Error::Conflict)
    ));
    let mut absent = request(&initial, "x");
    absent.state.drafts.get_mut("doc_a").unwrap().base_version = 99;
    assert!(ui_state::write(&mut conn, absent).is_err());
    let mut too_large = request(&initial, "x");
    too_large.state.drafts.get_mut("doc_a").unwrap().editor_json = body(&"x".repeat(262_144));
    assert!(ui_state::write(&mut conn, too_large).is_err());
    let mut wrong_type = request(&initial, "x");
    wrong_type
        .state
        .drafts
        .get_mut("doc_a")
        .unwrap()
        .editor_json = json!("not a document");
    assert!(ui_state::write(&mut conn, wrong_type).is_err());
    let mut extra = serde_json::to_value(request(&initial, "x")).unwrap();
    extra["state"]["credentials"] = json!("not accepted");
    assert!(serde_json::from_value::<Write>(extra).is_err());
    assert_eq!(ui_state::read(&mut conn).unwrap(), initial);
}
#[test]
fn clear_saved_requires_the_real_version_digest_and_never_clears_late_edit() {
    let dir = tempfile::tempdir().unwrap();
    let mut conn = fixture(&dir.path().join("db.sqlite"));
    let initial = ui_state::read(&mut conn).unwrap();
    let saved = ui_state::write(&mut conn, request(&initial, "draft")).unwrap();
    let clear = |v: &Value| ClearSaved {
        workspace_id: v["workspace_id"].as_str().unwrap().into(),
        restore_epoch: v["restore_epoch"].as_str().unwrap().into(),
        state_revision: v["state_revision"].as_i64().unwrap(),
        document_id: "doc_a".into(),
        base_version: 1,
        content_sha256: saved["draft_digests"]["doc_a"].as_str().unwrap().into(),
        saved_version: 2,
    };
    assert!(
        matches!(
            ui_state::clear_saved(&mut conn, clear(&saved)),
            Err(Error::Conflict)
        ),
        "client ACK cannot invent a committed version"
    );
    conn.execute(
        "INSERT INTO document_versions VALUES('doc_a',2,?1)",
        [body("draft").to_string()],
    )
    .unwrap();
    let latest = ui_state::write(&mut conn, request(&saved, "newer unsaved text")).unwrap();
    assert!(matches!(
        ui_state::clear_saved(&mut conn, clear(&saved)),
        Err(Error::Conflict)
    ));
    assert!(
        matches!(
            ui_state::clear_saved(&mut conn, clear(&latest)),
            Err(Error::Conflict)
        ),
        "even current revision cannot clear a different digest"
    );
    let same = ui_state::write(&mut conn, request(&latest, "draft")).unwrap();
    let cleared = ui_state::clear_saved(&mut conn, clear(&same)).unwrap();
    assert_eq!(cleared["state"]["drafts"], json!({}));
    assert_eq!(cleared["state"]["active_document"], "doc_a");
}
#[test]
fn restore_quarantines_working_state_until_explicit_human_recovery() {
    let dir = tempfile::tempdir().unwrap();
    let mut conn = fixture(&dir.path().join("db.sqlite"));
    let initial = ui_state::read(&mut conn).unwrap();
    let saved = ui_state::write(&mut conn, request(&initial, "preserved")).unwrap();
    conn.execute("INSERT INTO workspace_meta(key,value) VALUES('authorization_restore_fence',?1)",[json!({"schema":"archeaxis.authorization-restore-fence/v1","epoch":"a".repeat(32),"blocked_grant_ids":[]}).to_string()]).unwrap();
    let preview = ui_state::read(&mut conn).unwrap();
    assert_eq!(preview["recovery_requires_confirmation"], true);
    assert_eq!(preview["state"]["drafts"], json!({}));
    assert_eq!(
        preview["recovery_candidates"]["drafts"]["doc_a"]["editor_json"],
        body("preserved")
    );
    assert!(matches!(
        ui_state::write(&mut conn, request(&saved, "late pre-restore request")),
        Err(Error::Conflict)
    ));
    let recovered = ui_state::recover(
        &mut conn,
        Recover {
            workspace_id: preview["workspace_id"].as_str().unwrap().into(),
            restore_epoch: preview["restore_epoch"].as_str().unwrap().into(),
            state_revision: preview["state_revision"].as_i64().unwrap(),
            action: RecoveryAction::Preserve,
        },
    )
    .unwrap();
    assert_eq!(recovered["recovery_requires_confirmation"], false);
    assert_eq!(
        recovered["state"]["drafts"]["doc_a"]["editor_json"],
        body("preserved")
    );
    assert_eq!(
        conn.query_row("SELECT count(*) FROM document_versions", [], |r| r
            .get::<_, i64>(0))
            .unwrap(),
        1,
        "recovery never writes over committed content"
    );
}

#[test]
fn pending_original_request_is_preserved_before_any_document_exists_and_is_frozen() {
    let dir = tempfile::tempdir().unwrap();
    let path = dir.path().join("db.sqlite");
    let mut conn = fixture(&path);
    let initial = ui_state::read(&mut conn).unwrap();
    let mut pending = request(&initial, "existing draft");
    pending.state.pending_original = Some(ui_state::OriginalAttempt {
        create_request_id: "create_fixed_1".into(),
        title: "new note".into(),
        editor_json: body("frozen creation body"),
    });
    let stored = ui_state::write(&mut conn, pending).unwrap();
    assert!(
        stored["pending_document_id"]
            .as_str()
            .unwrap()
            .starts_with("doc_req_")
    );
    let mut changed = request(&stored, "existing draft");
    changed.state.pending_original = Some(ui_state::OriginalAttempt {
        create_request_id: "create_fixed_1".into(),
        title: "changed".into(),
        editor_json: body("modified after UNKNOWN"),
    });
    assert!(ui_state::write(&mut conn, changed).is_err());
    drop(conn);
    let mut conn = fixture(&path);
    assert_eq!(ui_state::read(&mut conn).unwrap(), stored);
}

#[test]
fn restoring_a_backup_that_predates_ui_identity_rejects_the_old_session() {
    let dir = tempfile::tempdir().unwrap();
    let mut conn = fixture(&dir.path().join("db.sqlite"));
    let original = ui_state::read(&mut conn).unwrap();
    // Models the meta state in an older backup, not a write to a live product DB.
    conn.execute("DELETE FROM workspace_meta WHERE key IN ('ui_workspace_identity_v1','ui_working_state_v1')",[]).unwrap();
    conn.execute("INSERT INTO workspace_meta(key,value) VALUES('authorization_restore_fence',?1)",[json!({"schema":"archeaxis.authorization-restore-fence/v1","epoch":"b".repeat(32),"blocked_grant_ids":[]}).to_string()]).unwrap();
    let restored = ui_state::read(&mut conn).unwrap();
    assert_ne!(restored["workspace_id"], original["workspace_id"]);
    assert_eq!(restored["state"]["drafts"], json!({}));
    assert!(matches!(
        ui_state::write(&mut conn, request(&original, "late old session")),
        Err(Error::Conflict)
    ));
}
