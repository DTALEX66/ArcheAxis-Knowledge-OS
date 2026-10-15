use archeaxis_domain::ui_state::{
    self, ClearSaved, Draft, Error, LearningDraft, Recover, RecoveryAction, State, Write,
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

fn learning_draft(id: &str, item: &str, version: &str, answer: &str) -> LearningDraft {
    LearningDraft {
        item_key: item.into(),
        assessment_id: id.into(),
        knowledge_version: version.into(),
        question_version: None,
        answer: answer.into(),
        checked_correct: None,
        rating: None,
        answer_revealed: false,
    }
}

fn teaching_draft(page: &str, context: Option<&str>, content: &str) -> ui_state::TeachingDraft {
    serde_json::from_value(json!({"page_id":page,"context_item_key":context,
        "form":{"kind":if page=="11" {"teach_back"} else {"feedback"},"purpose":"未提交总结","content":content,
            "scope":"personal","privacy":"local_only","assisted":false,"feedback_class":null,"rubric_version":"","producer_kind":"human_authored"},
        "knowledge_id":null,"course_id":null,"item_key":null,"assessment_id":null,"parent":null,
        "preparation":null,"saved_preparation":"","pending_record":null})).unwrap()
}

#[test]
fn teaching_drafts_reopen_as_inert_input_with_page_object_cas_and_utf8_boundaries() {
    let dir = tempfile::tempdir().unwrap();
    let path = dir.path().join("teaching-drafts.sqlite");
    let mut conn = fixture(&path);
    let initial = ui_state::read(&mut conn).unwrap();
    let a = teaching_draft("11", Some("course:a"), "  未提交复述\n第二行  ");
    let b = teaching_draft("12", None, "反馈与总结原文");
    let mut write = request(&initial, "independent document");
    write.state.teaching_drafts =
        BTreeMap::from([("11:course:a".into(), a.clone()), ("12:".into(), b.clone())]);
    let saved = ui_state::write(&mut conn, write.clone()).unwrap();
    assert!(matches!(
        ui_state::write(&mut conn, write),
        Err(Error::Conflict)
    ));
    drop(conn);
    let mut conn = fixture(&path);
    let reopened = ui_state::read(&mut conn).unwrap();
    assert_eq!(reopened, saved);
    let state: State = serde_json::from_value(reopened["state"].clone()).unwrap();
    assert_eq!(state.teaching_drafts["11:course:a"], a);
    assert_eq!(state.teaching_drafts["12:"], b);
    // No knowledge/assessment/teaching tables are needed to preserve unfinished ordinary text.
    let mut malformed = request(&reopened, "document");
    malformed
        .state
        .teaching_drafts
        .insert("wrong-object".into(), a.clone());
    assert!(matches!(
        ui_state::write(&mut conn, malformed),
        Err(Error::Invalid(_))
    ));
    let mut oversized = request(&reopened, "document");
    oversized.state.teaching_drafts.insert(
        "11:course:a".into(),
        teaching_draft("11", Some("course:a"), &"中".repeat(21_846)),
    );
    assert!(matches!(
        ui_state::write(&mut conn, oversized),
        Err(Error::Invalid(_))
    ));
    let mut unknown = serde_json::to_value(a).unwrap();
    unknown["form"]["unexpected_truth"] = json!(true);
    assert!(serde_json::from_value::<ui_state::TeachingDraft>(unknown).is_err());
    assert_eq!(ui_state::read(&mut conn).unwrap(), saved);
}

#[test]
fn frozen_teaching_draft_requires_exact_saved_record_before_clearance() {
    let dir = tempfile::tempdir().unwrap();
    let mut conn = fixture(&dir.path().join("teaching-frozen.sqlite"));
    conn.execute_batch(
        "CREATE TABLE teaching_records(record_id TEXT PRIMARY KEY,record_json TEXT);",
    )
    .unwrap();
    let initial = ui_state::read(&mut conn).unwrap();
    let mut entry = teaching_draft("11", None, "冻结的复述正文");
    entry.knowledge_id = Some("knowledge_v1".into());
    entry.pending_record=Some(serde_json::from_value(json!({"schema":"archeaxis.teaching-record/v2","record_id":"teaching_a","kind":"teach_back",
        "knowledge_id":"knowledge_v1","knowledge_version":"knowledge_v1","course_id":null,"parent_id":null,
        "purpose":entry.form.purpose,"content":entry.form.content,"scope":"personal","privacy":"local_only","feedback_class":null,
        "assessment_id":null,"rubric_version":null,"assisted":false,"producer_kind":"human_authored"})).unwrap());
    let mut write = request(&initial, "document");
    write
        .state
        .teaching_drafts
        .insert("11:".into(), entry.clone());
    let saved = ui_state::write(&mut conn, write).unwrap();
    let clear = request(&saved, "document");
    assert!(matches!(
        ui_state::write(&mut conn, clear.clone()),
        Err(Error::Invalid(_))
    ));
    let mut replacement = clear.clone();
    let mut changed = entry.clone();
    changed.form.content = "changed".into();
    replacement
        .state
        .teaching_drafts
        .insert("11:".into(), changed);
    assert!(matches!(
        ui_state::write(&mut conn, replacement),
        Err(Error::Invalid(_))
    ));
    let mut wrong = entry.pending_record.clone().unwrap();
    wrong.content = "wrong canonical body".into();
    conn.execute(
        "INSERT INTO teaching_records VALUES('teaching_a',?1)",
        [serde_json::to_string(&wrong).unwrap()],
    )
    .unwrap();
    assert!(matches!(
        ui_state::write(&mut conn, clear.clone()),
        Err(Error::Invalid(_))
    ));
    conn.execute(
        "UPDATE teaching_records SET record_json=?1",
        [serde_json::to_string(&entry.pending_record).unwrap()],
    )
    .unwrap();
    let cleared = ui_state::write(&mut conn, clear).unwrap();
    assert!(cleared["state"].get("teaching_drafts").is_none());
}

#[test]
fn independent_learning_drafts_reopen_without_review_and_refuse_stale_cas_or_rebinding() {
    let dir = tempfile::tempdir().unwrap();
    let path = dir.path().join("learning-drafts.sqlite");
    let mut conn = fixture(&path);
    conn.execute_batch("CREATE TABLE learning_assessments(assessment_id TEXT PRIMARY KEY,item_key TEXT,knowledge_version TEXT); CREATE TABLE learning_events(event_id TEXT,item_key TEXT); INSERT INTO learning_assessments VALUES('assessment_a','item-a','v1'),('assessment_b','item-b','v2');").unwrap();
    let initial = ui_state::read(&mut conn).unwrap();
    let a = learning_draft("assessment_a", "item-a", "v1", "  未提交 A\n第二行  ");
    let mut b = learning_draft("assessment_b", "item-b", "v2", "");
    // An unfinished check is a draft, not an admissible learning review.
    b.checked_correct = Some(false);
    b.rating = Some(3);
    b.answer_revealed = true;
    let mut write = request(&initial, "document remains independent");
    write.state.learning_drafts = BTreeMap::from([
        ("assessment_a".into(), a.clone()),
        ("assessment_b".into(), b.clone()),
    ]);
    let saved = ui_state::write(&mut conn, write.clone()).unwrap();
    assert!(matches!(
        ui_state::write(&mut conn, write),
        Err(Error::Conflict)
    ));
    drop(conn);
    let mut conn = fixture(&path);
    assert_eq!(ui_state::read(&mut conn).unwrap(), saved);
    assert_eq!(
        saved["state"]["learning_drafts"]["assessment_a"],
        serde_json::to_value(&a).unwrap()
    );
    assert_eq!(
        saved["state"]["learning_drafts"]["assessment_b"],
        serde_json::to_value(&b).unwrap()
    );
    assert_eq!(
        conn.query_row("SELECT count(*) FROM learning_events", [], |r| r
            .get::<_, i64>(0))
            .unwrap(),
        0
    );
    let next = || {
        let mut value = request(&saved, "document remains independent");
        value.state.learning_drafts = BTreeMap::from([
            ("assessment_a".into(), a.clone()),
            ("assessment_b".into(), b.clone()),
        ]);
        value
    };
    for change in ["item", "version", "question", "map-key", "oversize"] {
        let mut invalid = next();
        let draft = invalid
            .state
            .learning_drafts
            .get_mut("assessment_a")
            .unwrap();
        match change {
            "item" => draft.item_key = "item-b".into(),
            "version" => draft.knowledge_version = "v2".into(),
            "question" => draft.question_version = Some("changed-question".into()),
            "oversize" => draft.answer = "中".repeat(21_846),
            _ => {
                let draft = invalid
                    .state
                    .learning_drafts
                    .remove("assessment_a")
                    .unwrap();
                invalid
                    .state
                    .learning_drafts
                    .insert("wrong_key".into(), draft);
            }
        }
        assert!(
            ui_state::write(&mut conn, invalid).is_err(),
            "{change} should be rejected"
        );
        assert_eq!(ui_state::read(&mut conn).unwrap(), saved);
    }
    for field in ["checked_correct", "rating"] {
        let mut value = serde_json::to_value(&a).unwrap();
        value.as_object_mut().unwrap().remove(field);
        assert!(serde_json::from_value::<LearningDraft>(value).is_err());
    }
    let mut updated = next();
    updated
        .state
        .learning_drafts
        .get_mut("assessment_a")
        .unwrap()
        .answer = "new answer A".into();
    let updated = ui_state::write(&mut conn, updated).unwrap();
    assert_eq!(
        updated["state"]["learning_drafts"]["assessment_b"],
        serde_json::to_value(&b).unwrap()
    );
}

#[test]
fn learning_draft_restore_requires_explicit_choice_and_valid_assessment_binding() {
    let dir = tempfile::tempdir().unwrap();
    let mut conn = fixture(&dir.path().join("learning-restore.sqlite"));
    conn.execute_batch("CREATE TABLE learning_assessments(assessment_id TEXT PRIMARY KEY,item_key TEXT,knowledge_version TEXT); INSERT INTO learning_assessments VALUES('assessment','item','v1');").unwrap();
    let basis = ui_state::read(&mut conn).unwrap();
    let mut write = request(&basis, "document");
    write.state.learning_drafts.insert(
        "assessment".into(),
        learning_draft("assessment", "item", "v1", "answer retained"),
    );
    let saved = ui_state::write(&mut conn, write).unwrap();
    conn.execute("INSERT INTO workspace_meta VALUES('authorization_restore_fence',?1)",[json!({"schema":"archeaxis.authorization-restore-fence/v1","epoch":"b".repeat(32),"blocked_grant_ids":[]}).to_string()]).unwrap();
    let candidate = ui_state::read(&mut conn).unwrap();
    assert_eq!(candidate["recovery_requires_confirmation"], true);
    assert!(candidate["state"].get("learning_drafts").is_none());
    assert_eq!(
        candidate["recovery_candidates"]["learning_drafts"],
        saved["state"]["learning_drafts"]
    );
    let recover = |action| Recover {
        workspace_id: candidate["workspace_id"].as_str().unwrap().into(),
        restore_epoch: candidate["restore_epoch"].as_str().unwrap().into(),
        state_revision: candidate["state_revision"].as_i64().unwrap(),
        action,
    };
    conn.execute("DELETE FROM learning_assessments", [])
        .unwrap();
    assert!(ui_state::recover(&mut conn, recover(RecoveryAction::Preserve)).is_err());
    assert_eq!(ui_state::read(&mut conn).unwrap(), candidate);
    conn.execute(
        "INSERT INTO learning_assessments VALUES('assessment','item','v1')",
        [],
    )
    .unwrap();
    let preserved = ui_state::recover(&mut conn, recover(RecoveryAction::Preserve)).unwrap();
    assert_eq!(
        preserved["state"]["learning_drafts"],
        saved["state"]["learning_drafts"]
    );
    conn.execute("UPDATE workspace_meta SET value=?1 WHERE key='authorization_restore_fence'",[json!({"schema":"archeaxis.authorization-restore-fence/v1","epoch":"c".repeat(32),"blocked_grant_ids":[]}).to_string()]).unwrap();
    let candidate = ui_state::read(&mut conn).unwrap();
    let discarded = ui_state::recover(
        &mut conn,
        Recover {
            workspace_id: candidate["workspace_id"].as_str().unwrap().into(),
            restore_epoch: candidate["restore_epoch"].as_str().unwrap().into(),
            state_revision: candidate["state_revision"].as_i64().unwrap(),
            action: RecoveryAction::Discard,
        },
    )
    .unwrap();
    assert!(discarded["state"].get("learning_drafts").is_none());
    assert_eq!(discarded["recovery_requires_confirmation"], false);
}

#[test]
fn job_journal_reopens_refuses_old_client_omission_and_requires_exact_clearance() {
    let dir = tempfile::tempdir().unwrap();
    let path = dir.path().join("jobs.sqlite");
    let mut conn = fixture(&path);
    conn.execute_batch(
        "CREATE TABLE sources(source_id TEXT PRIMARY KEY,sha256 TEXT);
        CREATE TABLE jobs(job_id TEXT PRIMARY KEY,input_ref TEXT,kind TEXT);
        CREATE TABLE job_attempts(job_id TEXT,request_id TEXT,state TEXT,request_json TEXT);
        INSERT INTO sources VALUES('source',printf('%064d',0));
        INSERT INTO jobs VALUES('job','source','text');",
    )
    .unwrap();
    let basis = ui_state::read(&mut conn).unwrap();
    let entry = json!({"source_id":"source","source_revision":"0".repeat(64),"job_id":"job","request_id":"frozen",
        "kind":"text","body":{"deadline_ms":60000,"split":false,"words":false},"surface":"manual","mode":"single","origin_restore_epoch":"initial","relative":null});
    let mut payload = json!({"workspace_id":basis["workspace_id"],"restore_epoch":"initial","state_revision":basis["state_revision"],
        "state":{"drafts":{},"opened_documents":[],"active_document":null,"page_id":"03","pending_original":null,"pending_jobs":{"frozen":entry}}});
    let written =
        ui_state::write(&mut conn, serde_json::from_value(payload.clone()).unwrap()).unwrap();
    drop(conn);
    let mut conn = fixture(&path);
    assert_eq!(
        ui_state::read(&mut conn).unwrap()["state"]["pending_jobs"]["frozen"],
        entry
    );
    payload["state_revision"] = written["state_revision"].clone();
    payload["state"]
        .as_object_mut()
        .unwrap()
        .remove("pending_jobs");
    assert!(ui_state::write(&mut conn, serde_json::from_value(payload.clone()).unwrap()).is_err());
    payload["state"]["pending_jobs"] = json!({"frozen":entry});
    // Any different binding cannot replace the stored identity.
    payload["state"]["pending_jobs"]["frozen"]["body"]["deadline_ms"] = json!(1);
    assert!(ui_state::write(&mut conn, serde_json::from_value(payload).unwrap()).is_err());
    let clear = |action: &str| {
        serde_json::from_value(json!({"workspace_id":written["workspace_id"],"restore_epoch":"initial","state_revision":written["state_revision"],"request_id":"frozen","action":action})).unwrap()
    };
    assert!(ui_state::clear_job(&mut conn, clear("terminal")).is_err());
    conn.execute(
        "INSERT INTO job_attempts VALUES('another','frozen','succeeded','{}')",
        [],
    )
    .unwrap();
    assert!(ui_state::clear_job(&mut conn, clear("abandon_unadmitted")).is_err());
    assert!(ui_state::clear_job(&mut conn, clear("terminal")).is_err());
    conn.execute("DELETE FROM job_attempts", []).unwrap();
    let cleared = ui_state::clear_job(&mut conn, clear("abandon_unadmitted")).unwrap();
    assert!(cleared["state"].get("pending_jobs").is_none());
    assert!(ui_state::job_abandoned(&conn, "frozen").unwrap());
    assert!(!ui_state::job_abandoned(&conn, "other").unwrap());
    let mut restore_entry = entry.clone();
    restore_entry["request_id"] = json!("restore_frozen");
    let staged=ui_state::write(&mut conn,serde_json::from_value(json!({"workspace_id":cleared["workspace_id"],"restore_epoch":"initial","state_revision":cleared["state_revision"],"state":{"drafts":{},"opened_documents":[],"active_document":null,"page_id":"03","pending_jobs":{"restore_frozen":restore_entry}}})).unwrap()).unwrap();
    let tombstone_raw: String = conn
        .query_row(
            "SELECT value FROM workspace_meta WHERE key='ui_job_abandonments_v1'",
            [],
            |r| r.get(0),
        )
        .unwrap();
    let clear_staged = || {
        serde_json::from_value(json!({"workspace_id":staged["workspace_id"],"restore_epoch":"initial","state_revision":staged["state_revision"],"request_id":"restore_frozen","action":"abandon_unadmitted"})).unwrap()
    };
    let full: BTreeMap<String, String> = (0..256)
        .map(|i| (format!("abandoned_{i}"), "0".repeat(64)))
        .collect();
    conn.execute(
        "UPDATE workspace_meta SET value=?1 WHERE key='ui_job_abandonments_v1'",
        [serde_json::to_string(&full).unwrap()],
    )
    .unwrap();
    assert!(
        ui_state::clear_job(&mut conn, clear_staged()).is_err(),
        "full tombstones must reject clearance without forgetting any identity"
    );
    assert_eq!(
        ui_state::read(&mut conn).unwrap(),
        staged,
        "failed clearance retains the exact journal and revision"
    );
    assert!(ui_state::job_abandoned(&conn, "abandoned_0").unwrap());
    assert!(ui_state::job_abandoned(&conn, "abandoned_255").unwrap());
    conn.execute(
        "UPDATE workspace_meta SET value='corrupt' WHERE key='ui_job_abandonments_v1'",
        [],
    )
    .unwrap();
    assert!(
        ui_state::job_abandoned(&conn, "unknown").is_err(),
        "corrupt record cannot prove an identity reusable"
    );
    assert!(ui_state::clear_job(&mut conn, clear_staged()).is_err());
    assert_eq!(ui_state::read(&mut conn).unwrap(), staged);
    conn.execute(
        "UPDATE workspace_meta SET value=?1 WHERE key='ui_job_abandonments_v1'",
        [tombstone_raw],
    )
    .unwrap();
    conn.execute("INSERT INTO workspace_meta VALUES('authorization_restore_fence',?1)",[json!({"schema":"archeaxis.authorization-restore-fence/v1","epoch":"b".repeat(32),"blocked_grant_ids":[]}).to_string()]).unwrap();
    let candidate = ui_state::read(&mut conn).unwrap();
    assert_eq!(candidate["recovery_requires_confirmation"], true);
    assert!(candidate["state"].get("pending_jobs").is_none());
    assert_eq!(
        candidate["recovery_candidates"]["pending_jobs"]["restore_frozen"],
        restore_entry
    );
    let recovered=ui_state::recover(&mut conn,serde_json::from_value(json!({"workspace_id":candidate["workspace_id"],"restore_epoch":candidate["restore_epoch"],"state_revision":staged["state_revision"],"action":"preserve"})).unwrap()).unwrap();
    assert!(ui_state::clear_job(&mut conn,serde_json::from_value(json!({"workspace_id":recovered["workspace_id"],"restore_epoch":recovered["restore_epoch"],"state_revision":recovered["state_revision"],"request_id":"restore_frozen","action":"abandon_unadmitted"})).unwrap()).is_err(),"current backup absence cannot prove a pre-restore request never executed");
}
fn request(receipt: &Value, text: &str) -> Write {
    Write {
        workspace_id: receipt["workspace_id"].as_str().unwrap().into(),
        restore_epoch: receipt["restore_epoch"].as_str().unwrap().into(),
        state_revision: receipt["state_revision"].as_i64().unwrap(),
        state: State {
            pending_machine: BTreeMap::new(),
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
            pending_reviews: BTreeMap::new(),
            learning_drafts: BTreeMap::new(),
            teaching_drafts: BTreeMap::new(),
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
        source_id: None,
        source_revision: None,
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
        source_id: None,
        source_revision: None,
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
fn recovery_discard_cannot_erase_unconfirmed_machine_or_review_candidate() {
    for kind in ["machine", "review", "draft_only"] {
        let dir = tempfile::tempdir().unwrap();
        let mut conn = fixture(&dir.path().join("candidate.sqlite"));
        if kind == "review" {
            conn.execute_batch("CREATE TABLE learning_assessments(assessment_id TEXT,item_key TEXT,knowledge_version TEXT); INSERT INTO learning_assessments VALUES('assessment','item','v1');").unwrap();
        }
        let basis = ui_state::read(&mut conn).unwrap();
        let mut write = request(&basis, "synthetic candidate");
        if kind == "machine" {
            write.state.pending_machine.insert("frozen".into(),serde_json::from_value(json!({"journal_id":"frozen","owner_knowledge_id":"k1","operation":"answer","origin_restore_epoch":"initial","body":{"knowledge_id":"k1","question":"Synthetic unknown","max_tokens":2048,"timeout_s":120,"client_request_id":"frozen"}})).unwrap());
        }
        if kind == "review" {
            write.state.pending_reviews.insert("frozen".into(),serde_json::from_value(json!({"item_key":"item","client_event_id":"frozen","origin_restore_epoch":"initial","body":{"item_key":"item","client_event_id":"frozen","answer":"Synthetic unknown","assessment_id":"assessment","knowledge_version":"v1","correct":true,"rating":3}})).unwrap());
        }
        ui_state::write(&mut conn, write).unwrap();
        conn.execute("INSERT INTO workspace_meta(key,value) VALUES('authorization_restore_fence',?1)",[json!({"schema":"archeaxis.authorization-restore-fence/v1","epoch":"b".repeat(32),"blocked_grant_ids":[]}).to_string()]).unwrap();
        let preview = ui_state::read(&mut conn).unwrap();
        let recovery = |action| Recover {
            workspace_id: preview["workspace_id"].as_str().unwrap().into(),
            restore_epoch: preview["restore_epoch"].as_str().unwrap().into(),
            state_revision: preview["state_revision"].as_i64().unwrap(),
            action,
        };
        if kind == "draft_only" {
            let discarded =
                ui_state::recover(&mut conn, recovery(RecoveryAction::Discard)).unwrap();
            assert_eq!(discarded["state"]["drafts"], json!({}));
            assert_eq!(discarded["recovery_requires_confirmation"], false);
        } else {
            assert!(matches!(
                ui_state::recover(&mut conn, recovery(RecoveryAction::Discard)),
                Err(Error::Invalid(_))
            ));
            assert_eq!(ui_state::read(&mut conn).unwrap(), preview);
            let kept = ui_state::recover(&mut conn, recovery(RecoveryAction::Preserve)).unwrap();
            assert_eq!(kept["state"], preview["recovery_candidates"]);
            assert_eq!(kept["recovery_requires_confirmation"], false);
        }
        assert_eq!(
            conn.query_row("SELECT count(*) FROM document_versions", [], |r| r
                .get::<_, i64>(0))
                .unwrap(),
            1
        );
    }
}

#[test]
fn source_creation_journal_reopens_and_refuses_source_substitution() {
    let dir = tempfile::tempdir().unwrap();
    let path = dir.path().join("source-create.sqlite");
    let mut conn = fixture(&path);
    let read = ui_state::read(&mut conn).unwrap();
    let mut pending = request(&read, "existing draft");
    pending.state.pending_original = Some(ui_state::OriginalAttempt {
        source_id: Some("source_a".into()),
        source_revision: Some("a".repeat(64)),
        create_request_id: "source_create_fixed".into(),
        title: "source draft".into(),
        editor_json: body("synthetic source text"),
    });
    let stored = ui_state::write(&mut conn, pending).unwrap();
    drop(conn);
    let mut conn = fixture(&path);
    assert_eq!(ui_state::read(&mut conn).unwrap(), stored);
    let mut changed = request(&stored, "existing draft");
    changed.state.pending_original =
        serde_json::from_value(stored["state"]["pending_original"].clone()).unwrap();
    changed
        .state
        .pending_original
        .as_mut()
        .unwrap()
        .source_revision = Some("b".repeat(64));
    assert!(ui_state::write(&mut conn, changed).is_err());
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

#[test]
fn frozen_review_survives_reopen_and_rejects_replacement_or_unconfirmed_clear() {
    let dir = tempfile::tempdir().unwrap();
    let path = dir.path().join("review.sqlite");
    let mut conn = fixture(&path);
    conn.execute_batch("CREATE TABLE learning_assessments(assessment_id TEXT,item_key TEXT,knowledge_version TEXT); CREATE TABLE learning_event_keys(event_key TEXT,item_key TEXT,payload_hash TEXT,event_id TEXT); CREATE TABLE learning_events(event_id TEXT,item_key TEXT); INSERT INTO learning_assessments VALUES('assessment','course:card','version');").unwrap();
    let basis = ui_state::read(&mut conn).unwrap();
    let entry = json!({"item_key":"course:card","client_event_id":"event","origin_restore_epoch":"initial","body":{"item_key":"course:card","client_event_id":"event","answer":"answer","assessment_id":"assessment","knowledge_version":"version","correct":true,"rating":3}});
    let mut write = request(&basis, "draft");
    write.state.learning_drafts.insert(
        "assessment".into(),
        learning_draft("assessment", "course:card", "version", "  answer  "),
    );
    write.state.pending_reviews.insert(
        "event".into(),
        serde_json::from_value(entry.clone()).unwrap(),
    );
    ui_state::write(&mut conn, write).unwrap();
    drop(conn);
    let mut conn = fixture(&path);
    let read = ui_state::read(&mut conn).unwrap();
    assert_eq!(read["state"]["pending_reviews"]["event"], entry);
    assert_eq!(
        read["state"]["learning_drafts"]["assessment"]["answer"],
        "  answer  "
    );
    let mut changed = request(&read, "draft");
    let mut altered = entry.clone();
    altered["body"]["answer"] = json!("different");
    changed
        .state
        .pending_reviews
        .insert("event".into(), serde_json::from_value(altered).unwrap());
    assert!(matches!(
        ui_state::write(&mut conn, changed),
        Err(Error::Invalid(_))
    ));
    assert!(matches!(
        ui_state::write(&mut conn, request(&read, "draft")),
        Err(Error::Invalid(_))
    ));
    assert_eq!(
        ui_state::read(&mut conn).unwrap()["state"]["pending_reviews"]["event"],
        entry
    );
    conn.execute(
        "INSERT INTO learning_event_keys VALUES('event','course:card',?1,'committed')",
        ["bbd700a6dd8934edc2695a5a4d882dfd1a54042eb4c1ebb083b4ee5771a704f8"],
    )
    .unwrap();
    // A key without the actual committed event cannot clear the frozen request.
    assert!(matches!(
        ui_state::write(&mut conn, request(&read, "draft")),
        Err(Error::Invalid(_))
    ));
    conn.execute(
        "INSERT INTO learning_events VALUES('committed','other-card')",
        [],
    )
    .unwrap();
    assert!(matches!(
        ui_state::write(&mut conn, request(&read, "draft")),
        Err(Error::Invalid(_))
    ));
    conn.execute(
        "UPDATE learning_events SET item_key='course:card' WHERE event_id='committed'",
        [],
    )
    .unwrap();
    let cleared = ui_state::write(&mut conn, request(&read, "draft")).unwrap();
    assert!(cleared["state"].get("pending_reviews").is_none());
    assert!(cleared["state"].get("learning_drafts").is_none());
}
#[test]
fn machine_journal_reopens_and_old_client_cannot_drop_or_change_it() {
    let dir = tempfile::tempdir().unwrap();
    let path = dir.path().join("machine.sqlite");
    let mut conn = fixture(&path);
    let basis = ui_state::read(&mut conn).unwrap();
    let entry = json!({"journal_id":"machine_fixed","owner_knowledge_id":"k1","operation":"answer","origin_restore_epoch":"initial","body":{"knowledge_id":"k1","question":"Synthetic question","max_tokens":2048,"timeout_s":120,"client_request_id":"machine_fixed"}});
    let mut payload = json!({"workspace_id":basis["workspace_id"],"restore_epoch":basis["restore_epoch"],"state_revision":basis["state_revision"],"state":{"drafts":{},"opened_documents":[],"active_document":null,"page_id":null,"pending_machine":{"machine_fixed":entry}}});
    let written =
        ui_state::write(&mut conn, serde_json::from_value(payload.clone()).unwrap()).unwrap();
    drop(conn);
    let mut conn = fixture(&path);
    assert_eq!(
        ui_state::read(&mut conn).unwrap()["state"]["pending_machine"]["machine_fixed"],
        entry
    );
    payload["state_revision"] = written["state_revision"].clone();
    payload["state"]["pending_machine"]["machine_fixed"]["body"]["question"] = json!("Changed");
    assert!(ui_state::write(&mut conn, serde_json::from_value(payload.clone()).unwrap()).is_err());
    payload["state"]
        .as_object_mut()
        .unwrap()
        .remove("pending_machine");
    assert!(ui_state::write(&mut conn, serde_json::from_value(payload).unwrap()).is_err());
    conn.execute_batch("CREATE TABLE machine_tasks(task_id TEXT PRIMARY KEY,scope TEXT,conditions TEXT,retest_of TEXT)").unwrap();
    use sha2::{Digest, Sha256};
    let task_id = format!(
        "answer_req_{}",
        hex::encode(Sha256::digest(b"machine_fixed"))
    );
    let clear = || ui_state::ClearMachine {
        workspace_id: written["workspace_id"].as_str().unwrap().into(),
        restore_epoch: "initial".into(),
        state_revision: written["state_revision"].as_i64().unwrap(),
        journal_id: "machine_fixed".into(),
        task_id: task_id.clone(),
    };
    assert!(ui_state::clear_machine(&mut conn, clear()).is_err());
    let mut doc = json!({"schema":"archeaxis.machine-answer/v1","authority":"candidate","answer_id":task_id,"client_request_id":"machine_fixed","knowledge_id":"k1","question":"Synthetic question","answer":{"answer":"SYNTHETIC"},"request":entry["body"]});
    doc["request"]["max_tokens"] = json!(4096);
    conn.execute(
        "INSERT INTO machine_tasks(task_id,scope,conditions) VALUES(?1,'runtime.answer',?2)",
        rusqlite::params![task_id, doc.to_string()],
    )
    .unwrap();
    assert!(ui_state::clear_machine(&mut conn, clear()).is_err());
    assert_eq!(
        ui_state::read(&mut conn).unwrap()["state"]["pending_machine"]["machine_fixed"],
        entry
    );
    doc["request"]["max_tokens"] = json!(2048);
    conn.execute("UPDATE machine_tasks SET conditions=?1", [doc.to_string()])
        .unwrap();
    let cleared = ui_state::clear_machine(&mut conn, clear()).unwrap();
    assert!(cleared["state"].get("pending_machine").is_none());
}

#[test]
fn machine_journal_rejects_malformed_or_wrong_operation_grants_before_persistence() {
    let dir = tempfile::tempdir().unwrap();
    let mut conn = fixture(&dir.path().join("bounded-machine.sqlite"));
    let basis = ui_state::read(&mut conn).unwrap();
    let entry = json!({"journal_id":"bounded","owner_knowledge_id":"k1","operation":"answer","origin_restore_epoch":"initial","body":{"knowledge_id":"k1","question":"Synthetic question","max_tokens":2048,"timeout_s":120,"client_request_id":"bounded"}});
    let payload = json!({"workspace_id":basis["workspace_id"],"restore_epoch":basis["restore_epoch"],"state_revision":basis["state_revision"],"state":{"drafts":{},"opened_documents":[],"active_document":null,"page_id":null,"pending_machine":{"bounded":entry}}});
    let snapshot = json!({"document_id":"grant","version":1,"content_sha256":"a".repeat(64)});
    for bad in [
        json!(null),
        json!({"unknown":"private"}),
        json!({"document_id":"grant","version":0,"content_sha256":"a".repeat(64),"purpose":"synthetic"}),
    ] {
        let mut attempt = payload.clone();
        attempt["state"]["pending_machine"]["bounded"]["body"]["context_grant"] = bad;
        assert!(ui_state::write(&mut conn, serde_json::from_value(attempt).unwrap()).is_err());
        assert_eq!(
            ui_state::read(&mut conn).unwrap()["state_revision"],
            basis["state_revision"]
        );
    }
    let mut attempt = payload.clone();
    attempt["state"]["pending_machine"]["bounded"]["body"]["asset_context_grant"] = json!({"request_id":"packet","grant":snapshot,"asset":snapshot,"purpose":"synthetic","consumer":"local-machine","operation":"retest"});
    attempt["state"]["pending_machine"]["bounded"]["body"]["context_grant"] = json!({"document_id":"context","version":1,"content_sha256":"b".repeat(64),"purpose":"synthetic"});
    assert!(ui_state::write(&mut conn, serde_json::from_value(attempt.clone()).unwrap()).is_err());
    attempt["state"]["pending_machine"]["bounded"]["body"]["asset_context_grant"]["operation"] =
        json!("answer");
    for (field, bad) in [
        ("document_id", json!("x".repeat(129))),
        ("version", json!(9_007_199_254_740_992_i64)),
    ] {
        let mut invalid = attempt.clone();
        invalid["state"]["pending_machine"]["bounded"]["body"]["asset_context_grant"]["asset"]
            [field] = bad;
        assert!(ui_state::write(&mut conn, serde_json::from_value(invalid).unwrap()).is_err());
        assert_eq!(
            ui_state::read(&mut conn).unwrap()["state_revision"],
            basis["state_revision"]
        );
    }
    ui_state::write(&mut conn, serde_json::from_value(attempt).unwrap()).unwrap();
}

#[test]
fn withheld_clear_requires_exact_frozen_fingerprint_and_preserves_terminal_history() {
    let dir = tempfile::tempdir().unwrap();
    let mut conn = fixture(&dir.path().join("withheld-journal.sqlite"));
    conn.execute_batch("CREATE TABLE machine_tasks(task_id TEXT PRIMARY KEY,scope TEXT,conditions TEXT,retest_of TEXT)").unwrap();
    let basis = ui_state::read(&mut conn).unwrap();
    let entry = json!({"journal_id":"withheld_fixed","owner_knowledge_id":"k1","operation":"answer","origin_restore_epoch":"initial","body":{"knowledge_id":"k1","question":"Synthetic withheld","max_tokens":2048,"timeout_s":120,"client_request_id":"withheld_fixed"}});
    let payload = json!({"workspace_id":basis["workspace_id"],"restore_epoch":basis["restore_epoch"],"state_revision":basis["state_revision"],"state":{"drafts":{},"opened_documents":[],"active_document":null,"page_id":null,"pending_machine":{"withheld_fixed":entry}}});
    let written = ui_state::write(&mut conn, serde_json::from_value(payload).unwrap()).unwrap();
    let task = "withheld_audit";
    let mut doc = json!({"schema":"archeaxis.machine-execution-withheld/v1","audit_task_id":task,"execution_state":"EXECUTED_BUT_WITHHELD","operation":"answer","knowledge_id":"k1","client_request_id":"withheld_fixed","retest_of":null,"answer_published":false,"authority":"historical_execution_audit"});
    let clear = || ui_state::ClearMachine {
        workspace_id: written["workspace_id"].as_str().unwrap().into(),
        restore_epoch: "initial".into(),
        state_revision: written["state_revision"].as_i64().unwrap(),
        journal_id: "withheld_fixed".into(),
        task_id: task.into(),
    };
    conn.execute("INSERT INTO machine_tasks(task_id,scope,conditions) VALUES(?1,'runtime.execution.withheld',?2)",rusqlite::params![task,doc.to_string()]).unwrap();
    // A historical audit lacking the new input fingerprint cannot retire unknown execution.
    assert!(ui_state::clear_machine(&mut conn, clear()).is_err());
    doc["admission_request_sha256"] = json!(ui_state::machine_request_fingerprint(
        "answer",
        &entry["body"]
    ));
    doc["client_request_id"] = json!("other");
    conn.execute("UPDATE machine_tasks SET conditions=?1", [doc.to_string()])
        .unwrap();
    assert!(ui_state::clear_machine(&mut conn, clear()).is_err());
    doc["client_request_id"] = json!("withheld_fixed");
    conn.execute("UPDATE machine_tasks SET conditions=?1", [doc.to_string()])
        .unwrap();
    let cleared = ui_state::clear_machine(&mut conn, clear()).unwrap();
    assert!(cleared["state"].get("pending_machine").is_none());
    let after: String = conn
        .query_row(
            "SELECT conditions FROM machine_tasks WHERE task_id=?1",
            [task],
            |r| r.get(0),
        )
        .unwrap();
    assert_eq!(after, doc.to_string());
}

#[test]
fn retest_journal_owner_is_bound_to_real_failed_journey() {
    let dir = tempfile::tempdir().unwrap();
    let mut conn = fixture(&dir.path().join("retest-owner.sqlite"));
    conn.execute_batch("CREATE TABLE machine_tasks(task_id TEXT PRIMARY KEY,scope TEXT,conditions TEXT,retest_of TEXT)").unwrap();
    let prior = json!({"knowledge_id":"original","question":"Synthetic retest"});
    conn.execute("INSERT INTO machine_tasks(task_id,scope,conditions) VALUES('failed','runtime.evaluation.failed',?1)",[prior.to_string()]).unwrap();
    let basis = ui_state::read(&mut conn).unwrap();
    let entry = json!({"journal_id":"retest_fixed","owner_knowledge_id":"other","operation":"retest","origin_restore_epoch":"initial","body":{"knowledge_id":"corrected","question":"Synthetic retest","max_tokens":2048,"timeout_s":120,"retest_of":"failed"}});
    let mut payload = json!({"workspace_id":basis["workspace_id"],"restore_epoch":basis["restore_epoch"],"state_revision":basis["state_revision"],"state":{"drafts":{},"opened_documents":[],"active_document":null,"page_id":null,"pending_machine":{"retest_fixed":entry}}});
    assert!(ui_state::write(&mut conn, serde_json::from_value(payload.clone()).unwrap()).is_err());
    assert_eq!(
        ui_state::read(&mut conn).unwrap()["state_revision"],
        basis["state_revision"]
    );
    payload["state"]["pending_machine"]["retest_fixed"]["owner_knowledge_id"] = json!("original");
    let written =
        ui_state::write(&mut conn, serde_json::from_value(payload.clone()).unwrap()).unwrap();
    let doc = json!({"schema":"archeaxis.machine-retest/v1","authority":"candidate","answer_id":"result","knowledge_id":"corrected","question":"Synthetic retest","answer":{"answer":"SYNTHETIC"},"retest_of":"failed","request":entry["body"],"execution_request":{"timeout_s":120}});
    conn.execute(
        "INSERT INTO machine_tasks VALUES('result','runtime.retest',?1,'failed')",
        [doc.to_string()],
    )
    .unwrap();
    let clear = || ui_state::ClearMachine {
        workspace_id: written["workspace_id"].as_str().unwrap().into(),
        restore_epoch: "initial".into(),
        state_revision: written["state_revision"].as_i64().unwrap(),
        journal_id: "retest_fixed".into(),
        task_id: "result".into(),
    };
    conn.execute(
        "UPDATE machine_tasks SET conditions=?1 WHERE task_id='failed'",
        [json!({"knowledge_id":"changed-owner","question":"Synthetic retest"}).to_string()],
    )
    .unwrap();
    assert!(ui_state::clear_machine(&mut conn, clear()).is_err());
    conn.execute(
        "UPDATE machine_tasks SET conditions=?1 WHERE task_id='failed'",
        [prior.to_string()],
    )
    .unwrap();
    assert!(
        ui_state::clear_machine(&mut conn, clear()).unwrap()["state"]
            .get("pending_machine")
            .is_none()
    );
}

#[test]
fn failed_machine_status_and_clear_require_current_attempt_after_reopen() {
    use sha2::{Digest, Sha256};
    let dir = tempfile::tempdir().unwrap();
    let path = dir.path().join("failed-status.sqlite");
    let mut conn = fixture(&path);
    conn.execute_batch("CREATE TABLE machine_tasks(task_id TEXT PRIMARY KEY,scope TEXT,conditions TEXT,retest_of TEXT)").unwrap();
    let basis = ui_state::read(&mut conn).unwrap();
    let body = json!({"knowledge_id":"k1","question":"Synthetic failure","max_tokens":2048,"timeout_s":120,"client_request_id":"fixed"});
    let entry = json!({"journal_id":"fixed","owner_knowledge_id":"k1","operation":"answer","origin_restore_epoch":"initial","body":body});
    let payload = json!({"workspace_id":basis["workspace_id"],"restore_epoch":basis["restore_epoch"],"state_revision":basis["state_revision"],"state":{"drafts":{},"opened_documents":[],"active_document":null,"page_id":null,"pending_machine":{"fixed":entry,"other": {"journal_id":"other","owner_knowledge_id":"k2","operation":"answer","origin_restore_epoch":"initial","body":{"knowledge_id":"k2","question":"Other synthetic","max_tokens":2048,"timeout_s":120,"client_request_id":"other"}}}}});
    let written = ui_state::write(&mut conn, serde_json::from_value(payload).unwrap()).unwrap();
    let status = || ui_state::MachineStatus {
        workspace_id: written["workspace_id"].as_str().unwrap().into(),
        restore_epoch: "initial".into(),
        state_revision: written["state_revision"].as_i64().unwrap(),
        journal_id: "fixed".into(),
    };
    assert!(
        ui_state::machine_admission_guard(
            &conn,
            "k1",
            "answer",
            &ui_state::machine_request_fingerprint("answer", &body)
        )
        .is_ok()
    );
    assert!(
        ui_state::machine_admission_guard(&conn, "k1", "answer", "new-client-fingerprint").is_err()
    );
    assert!(
        ui_state::machine_admission_guard(&conn, "k1", "retest", "new-operation-fingerprint")
            .is_err()
    );
    assert_eq!(
        ui_state::machine_status(&conn, status()).unwrap()["status"],
        "UNKNOWN"
    );
    let claim_id = format!("answer_req_{}", hex::encode(Sha256::digest(b"fixed")));
    let key = format!(
        "machine_execution_claim_{}",
        hex::encode(Sha256::digest(claim_id.as_bytes()))
    );
    let claim = json!({"schema":"archeaxis.machine-execution-claim/v1","state":"KNOWN_FAILURE","attempt":2,"max_attempts":3,"request_sha256":"actual-frozen-digest","terminal_task_id":"failure_current"});
    conn.execute(
        "INSERT INTO workspace_meta(key,value) VALUES(?1,?2)",
        rusqlite::params![key, claim.to_string()],
    )
    .unwrap();
    let mut doc = json!({"schema":"archeaxis.machine-execution-failed/v1","execution_state":"UNVERIFIED","audit_task_id":"failure_current","operation":"answer","knowledge_id":"k1","client_request_id":"fixed","retest_of":null,"answer_published":false,"authority":"historical_execution_audit","admission_request_sha256":ui_state::machine_request_fingerprint("answer",&body),"attempt":1,"max_attempts":3,"request_sha256":"actual-frozen-digest"});
    conn.execute(
        "INSERT INTO machine_tasks VALUES('failure_current','runtime.execution.failed',?1,NULL)",
        [doc.to_string()],
    )
    .unwrap();
    let clear = || ui_state::ClearMachine {
        workspace_id: written["workspace_id"].as_str().unwrap().into(),
        restore_epoch: "initial".into(),
        state_revision: written["state_revision"].as_i64().unwrap(),
        journal_id: "fixed".into(),
        task_id: "failure_current".into(),
    };
    assert_eq!(
        ui_state::machine_status(&conn, status()).unwrap()["can_clear"],
        false
    );
    assert!(ui_state::clear_machine(&mut conn, clear()).is_err());
    doc["attempt"] = json!(2);
    doc["admission_request_sha256"] = json!("wrong");
    conn.execute("UPDATE machine_tasks SET conditions=?1", [doc.to_string()])
        .unwrap();
    assert!(ui_state::clear_machine(&mut conn, clear()).is_err());
    doc["admission_request_sha256"] = json!(ui_state::machine_request_fingerprint("answer", &body));
    conn.execute("UPDATE machine_tasks SET conditions=?1", [doc.to_string()])
        .unwrap();
    let mut inflight = claim.clone();
    inflight["state"] = json!("IN_FLIGHT");
    conn.execute(
        "UPDATE workspace_meta SET value=?1 WHERE key=?2",
        rusqlite::params![inflight.to_string(), key],
    )
    .unwrap();
    assert_eq!(
        ui_state::machine_status(&conn, status()).unwrap()["status"],
        "UNKNOWN"
    );
    assert!(ui_state::clear_machine(&mut conn, clear()).is_err());
    conn.execute(
        "UPDATE workspace_meta SET value=?1 WHERE key=?2",
        rusqlite::params![claim.to_string(), key],
    )
    .unwrap();
    drop(conn);
    let mut conn = fixture(&path);
    let read = ui_state::machine_status(&conn, status()).unwrap();
    assert_eq!(read["status"], "FAILED");
    assert_eq!(read["attempt"], 2);
    assert_eq!(
        ui_state::read(&mut conn).unwrap()["state_revision"],
        written["state_revision"]
    );
    let cleared = ui_state::clear_machine(&mut conn, clear()).unwrap();
    assert!(cleared["state"]["pending_machine"].get("fixed").is_none());
    assert_eq!(
        cleared["state"]["pending_machine"]["other"]["journal_id"],
        "other"
    );
    let after: String = conn
        .query_row(
            "SELECT value FROM workspace_meta WHERE key=?1",
            [key],
            |r| r.get(0),
        )
        .unwrap();
    assert_eq!(after, claim.to_string());
    let audit: String = conn
        .query_row(
            "SELECT conditions FROM machine_tasks WHERE task_id='failure_current'",
            [],
            |r| r.get(0),
        )
        .unwrap();
    assert_eq!(audit, doc.to_string());
}
