//! Synthetic Core document candidates; no provider or model is invoked.
use archeaxis_domain::{backup, document, portable_document, provider_material_grant::{self as grant, Snapshot}, provider_question, source::{self, ImportOutcome}};
use base64::{Engine as _, engine::general_purpose::STANDARD};
use rusqlite::Connection;
use serde_json::{Value, json};
use sha2::{Digest, Sha256};

fn snap(value: &Value) -> Snapshot {
    Snapshot {
        document_id: value["document_id"].as_str().unwrap().into(),
        version: value["version"].as_i64().unwrap(),
        content_sha256: value["content_sha256"].as_str().unwrap().into(),
    }
}

fn material(conn: &mut Connection) -> Value {
    document::create_optional(conn, None, None, "SYNTHETIC material", json!({
        "type":"doc", "content":[{"type":"paragraph","content":[{"type":"text","text":"material"}]}]
    })).unwrap()
}

fn editor(source: &Value) -> Value {
    json!({"type":"doc", "content":[], "attrs":{"archeaxis_deeptutor_question":{
        "schema":"archeaxis.deeptutor-question/v1", "source_material":snap(source),
        "origin":"user_import_unverified", "upstream_entry_id":"SENTINEL_ENTRY",
        "question":{"question_id":"local_question_1", "question":"Which option?",
            "question_type":"single_choice", "options":{"A":"first","B":"second"},
            "correct_answer":"SENTINEL_ANSWER", "explanation":"SENTINEL_EXPLANATION"}
    }}})
}

fn question(conn: &mut Connection, source: &Value) -> Value {
    document::create_optional(conn, None, None, "SYNTHETIC question", editor(source)).unwrap()
}

fn permission(conn: &mut Connection, source: &Value) -> Value {
    document::create_optional(conn,None,None,"SYNTHETIC permission",json!({"type":"doc","content":[],"attrs":{
        "archeaxis_provider_material_grant":{"schema":"archeaxis.provider-material-grant/v1",
            "purpose":"practice","consumer":"deeptutor","operations":["practice"],"material":snap(source),
            "authorization_basis":"SYNTHETIC human authorization","expires_at":null,"state":"granted"}
    }})).unwrap()
}

#[test]
fn view_binds_full_content_but_projects_only_question_and_options() {
    let dir=tempfile::tempdir().unwrap();
    let mut conn=archeaxis_store_sqlite::init_workspace(dir.path().join("db.sqlite").to_str().unwrap()).unwrap();
    let source=material(&mut conn); let question=question(&mut conn,&source);
    let view=provider_question::read_view(&conn,&snap(&question)).unwrap();
    assert_eq!(view["source_snapshot_status"],"current");
    assert_eq!(view["question_status"],"current");
    assert_eq!(view["source_reference"],"declared_unverified");
    assert_eq!(view["question_document_origin"],"unverified");
    assert_eq!(view["authorization_effect"],"none");
    assert_eq!(view["origin"],"user_import_unverified");
    assert_eq!(view["provider_identity"],"unverified");
    assert_eq!(view["provider_executed"],false);
    assert_eq!(view["question"]["options"],json!({"A":"first","B":"second"}));
    assert!(!view.to_string().contains("SENTINEL_"));
    let version=view["question_version"].as_str().unwrap();
    assert!(version.starts_with("sha256:") && version.len()==71);
    assert_eq!(provider_question::read_view(&conn,&snap(&question)).unwrap()["question_version"],version);
    assert!(provider_question::assert_selected_snapshot_matches_candidate(&conn,&snap(&question),&snap(&source),"local_question_1",version).is_ok());
    assert!(provider_question::assert_selected_snapshot_matches_candidate(&conn,&snap(&question),&snap(&source),"wrong",version).is_err());
    assert!(provider_question::assert_selected_snapshot_matches_candidate(&conn,&snap(&question),&snap(&source),"local_question_1","caller_claim").is_err());
    let other_source=material(&mut conn);
    assert!(provider_question::assert_selected_snapshot_matches_candidate(&conn,&snap(&question),&snap(&other_source),"local_question_1",version).is_err());

    let mut changed=question["editor_json"].clone();
    changed["attrs"]["archeaxis_deeptutor_question"]["question"]["correct_answer"]=json!("a different answer");
    let next=document::save(&mut conn,question["document_id"].as_str().unwrap(),1,changed).unwrap();
    let next_view=provider_question::read_view(&conn,&snap(&next)).unwrap();
    assert_ne!(next_view["question_version"],view["question_version"]);
    assert_eq!(next_view["visible_sha256"],view["visible_sha256"]);
    assert_eq!(provider_question::read_view(&conn,&snap(&question)).unwrap()["question_status"],"historical");
    assert!(provider_question::assert_selected_snapshot_matches_candidate(&conn,&snap(&question),&snap(&source),"local_question_1",version).is_err());
}

#[test]
fn source_revisions_and_invalid_snapshots_cannot_be_relabelled_current() {
    let dir=tempfile::tempdir().unwrap();
    let mut conn=archeaxis_store_sqlite::init_workspace(dir.path().join("db.sqlite").to_str().unwrap()).unwrap();
    let source=material(&mut conn); let question=question(&mut conn,&source);
    let view=provider_question::read_view(&conn,&snap(&question)).unwrap();
    let mut revised=source["editor_json"].clone();
    revised["content"][0]["content"][0]["text"]=json!("new source version");
    document::save(&mut conn,source["document_id"].as_str().unwrap(),1,revised).unwrap();
    assert_eq!(provider_question::read_view(&conn,&snap(&question)).unwrap()["source_snapshot_status"],"historical");
    assert!(provider_question::assert_selected_snapshot_matches_candidate(&conn,&snap(&question),&snap(&source),"local_question_1",view["question_version"].as_str().unwrap()).is_err());
    let mut wrong=snap(&question); wrong.content_sha256="0".repeat(64);
    assert!(provider_question::read_view(&conn,&wrong).is_err());
    conn.execute("UPDATE document_versions SET text_projection='changed' WHERE document_id=?1 AND version=1",[source["document_id"].as_str().unwrap()]).unwrap();
    assert_eq!(provider_question::read_view(&conn,&snap(&question)).unwrap()["source_snapshot_status"],"unavailable");
}

#[test]
fn malformed_candidate_remains_an_ordinary_document_without_claiming_provider_origin() {
    let dir=tempfile::tempdir().unwrap();
    let mut conn=archeaxis_store_sqlite::init_workspace(dir.path().join("db.sqlite").to_str().unwrap()).unwrap();
    let source=material(&mut conn);
    for case in ["origin","unknown_field","question_id","too_many_options"] {
        let mut value=editor(&source);
        let candidate=&mut value["attrs"]["archeaxis_deeptutor_question"];
        match case {
            "origin" => candidate["origin"]=json!("provider_verified"),
            "unknown_field" => candidate["provider_verified"]=json!(true),
            "question_id" => candidate["question"]["question_id"]=json!("import:untrusted"),
            "too_many_options" => {
                let options=candidate["question"]["options"].as_object_mut().unwrap();
                for n in 0..65 { options.insert(format!("option_{n}"),json!("value")); }
            }
            _ => unreachable!(),
        }
        let doc=document::create_optional(&mut conn,None,None,"ordinary",value).unwrap();
        assert!(provider_question::read_view(&conn,&snap(&doc)).is_err(),"fixture {case}");
        let saved=document::save(&mut conn,doc["document_id"].as_str().unwrap(),1,doc["editor_json"].clone()).unwrap();
        assert_eq!(saved["version"],2,"fixture {case}");
    }
}

#[test]
fn portable_question_stays_historical_even_if_source_id_already_exists_and_after_save() {
    let dir=tempfile::tempdir().unwrap();
    let mut conn=archeaxis_store_sqlite::init_workspace(dir.path().join("db.sqlite").to_str().unwrap()).unwrap();
    let source=material(&mut conn); let original=question(&mut conn,&source);
    let package=portable_document::export(&conn,original["document_id"].as_str().unwrap()).unwrap();
    // Import into the same workspace deliberately makes the source ID, version
    // and digest coincide; portable history still must not become a binding.
    let imported=portable_document::import(&mut conn,package,"question_portable").unwrap();
    let doc=&imported["document"];
    assert_eq!(doc["editor_json"],original["editor_json"]);
    let view=provider_question::read_view(&conn,&snap(doc)).unwrap();
    assert_eq!(view["source_snapshot_status"],"not_compared");
    assert_eq!(view["source_reference"],"declared_unverified");
    assert_eq!(view["question_document_origin"],"portable_historical");
    assert_eq!(view["authorization_effect"],"none");
    assert!(!view.to_string().contains("SENTINEL_"));
    let version=view["question_version"].as_str().unwrap();
    assert!(provider_question::assert_selected_snapshot_matches_candidate(&conn,&snap(doc),&snap(&source),"local_question_1",version).is_err());
    let saved=document::save(&mut conn,doc["document_id"].as_str().unwrap(),1,doc["editor_json"].clone()).unwrap();
    let after=provider_question::read_view(&conn,&snap(&saved)).unwrap();
    assert_eq!(after["question_document_origin"],"portable_historical");
    assert!(provider_question::assert_selected_snapshot_matches_candidate(&conn,&snap(&saved),&snap(&source),"local_question_1",version).is_err());

    // If that independent metadata is lost, a coincident local snapshot may
    // be compared, but this never upgrades the declaration or grants access.
    conn.execute("UPDATE document_versions SET revision_basis=NULL WHERE document_id=?1 AND version=1",[doc["document_id"].as_str().unwrap()]).unwrap();
    let unproven=provider_question::read_view(&conn,&snap(&saved)).unwrap();
    assert_eq!(unproven["source_snapshot_status"],"current");
    assert_eq!(unproven["question_document_origin"],"unverified");
    assert_eq!(unproven["source_reference"],"declared_unverified");
    assert_eq!(unproven["authorization_effect"],"none");
    assert_eq!(unproven["provider_identity"],"unverified");
    assert!(provider_question::assert_selected_snapshot_matches_candidate(&conn,&snap(&saved),&snap(&source),"local_question_1",version).is_ok());
}

#[test]
fn requested_document_id_does_not_itself_mean_portable_or_grant_access() {
    let dir=tempfile::tempdir().unwrap();
    let mut conn=archeaxis_store_sqlite::init_workspace(dir.path().join("db.sqlite").to_str().unwrap()).unwrap();
    let source=material(&mut conn);
    let question=document::create_optional_with_request(&mut conn,None,None,"ordinary requested question",editor(&source),Some("question_request")).unwrap();
    assert!(question["document_id"].as_str().unwrap().starts_with("doc_req_"));
    let view=provider_question::read_view(&conn,&snap(&question)).unwrap();
    assert_eq!(view["source_snapshot_status"],"current");
    assert_eq!(view["question_document_origin"],"unverified");
    assert_eq!(view["source_reference"],"declared_unverified");
    assert_eq!(view["authorization_effect"],"none");
    assert!(provider_question::assert_selected_snapshot_matches_candidate(&conn,&snap(&question),&snap(&source),"local_question_1",view["question_version"].as_str().unwrap()).is_ok());
}

#[test]
fn same_document_id_in_another_workspace_does_not_bind_different_content() {
    let dir=tempfile::tempdir().unwrap();
    let mut first=archeaxis_store_sqlite::init_workspace(dir.path().join("first.sqlite").to_str().unwrap()).unwrap();
    let mut second=archeaxis_store_sqlite::init_workspace(dir.path().join("second.sqlite").to_str().unwrap()).unwrap();
    let source_a=document::create_optional_with_request(&mut first,None,None,"source",json!({"type":"doc","content":[{"type":"paragraph","content":[{"type":"text","text":"source A"}]}]}),Some("same_source_id")).unwrap();
    let source_b=document::create_optional_with_request(&mut second,None,None,"source",json!({"type":"doc","content":[{"type":"paragraph","content":[{"type":"text","text":"source B"}]}]}),Some("same_source_id")).unwrap();
    assert_eq!(source_a["document_id"],source_b["document_id"]);
    assert_ne!(source_a["content_sha256"],source_b["content_sha256"]);
    let original=question(&mut first,&source_a);
    let package=portable_document::export(&first,original["document_id"].as_str().unwrap()).unwrap();
    let imported=portable_document::import(&mut second,package,"foreign_question").unwrap();
    let doc=&imported["document"];
    conn_clear_portable_basis(&second,doc);
    let view=provider_question::read_view(&second,&snap(doc)).unwrap();
    assert_eq!(view["source_snapshot_status"],"unavailable");
    assert_eq!(view["source_reference"],"declared_unverified");
    assert_eq!(view["question_document_origin"],"unverified");
    assert_eq!(view["authorization_effect"],"none");
    assert!(provider_question::assert_selected_snapshot_matches_candidate(&second,&snap(doc),&snap(&source_b),"local_question_1",view["question_version"].as_str().unwrap()).is_err());
}

fn conn_clear_portable_basis(conn: &Connection, document: &Value) {
    conn.execute("UPDATE document_versions SET revision_basis=NULL WHERE document_id=?1 AND version=1",[document["document_id"].as_str().unwrap()]).unwrap();
}

#[test]
fn restore_keeps_candidate_readable_but_fences_both_old_grants() {
    let dir=tempfile::tempdir().unwrap();
    let mut conn=archeaxis_store_sqlite::init_workspace(dir.path().join("source.sqlite").to_str().unwrap()).unwrap();
    let source=material(&mut conn); let question=question(&mut conn,&source);
    let source_grant=permission(&mut conn,&source); let question_grant=permission(&mut conn,&question);
    assert!(grant::consume(&conn,&snap(&source_grant),&snap(&source),1).is_ok());
    assert!(grant::consume(&conn,&snap(&question_grant),&snap(&question),1).is_ok());
    let backup_path=dir.path().join("backup.sqlite"); backup::backup(&conn,backup_path.to_str().unwrap()).unwrap();
    let mut restored=archeaxis_store_sqlite::init_workspace(dir.path().join("restored.sqlite").to_str().unwrap()).unwrap();
    assert!(backup::restore_authorized(backup_path.to_str().unwrap(),&mut restored).unwrap());
    let view=provider_question::read_view(&restored,&snap(&question)).unwrap();
    assert_eq!(view["origin"],"user_import_unverified");
    assert!(grant::consume(&restored,&snap(&source_grant),&snap(&source),1).is_err());
    assert!(grant::consume(&restored,&snap(&question_grant),&snap(&question),1).is_err());
}

// These tests construct the exact bounded worker reply, but do not execute a
// Python worker or claim that the reply originated from a trusted process.
fn imported_practice(conn: &mut Connection, raw: &[u8], material: &Value, create: &str) -> provider_question::PracticeImportRequest {
    let (source_id, source_sha256, source_duplicate) = match source::import_source(conn, raw, "synthetic.json", None).unwrap() {
        ImportOutcome::Imported { source_id, sha256 } => (source_id, sha256, false),
        ImportOutcome::Duplicate { source_id, sha256 } => (source_id, sha256, true),
    };
    provider_question::PracticeImportRequest {
        request_id: "synthetic_practice_request".into(), source_id, source_sha256, source_duplicate,
        source_format: "json".into(), source_row: 1, material_snapshot: snap(material),
        question_id: "local_question_1".into(), create_request_id: create.into(), title: "SYNTHETIC question".into(),
    }
}

fn synthetic_worker_reply(plan: &provider_question::PracticeImportPlan) -> Value {
    let frame: Value = serde_json::from_slice(&plan.worker_frame()[..plan.worker_frame().len()-1]).unwrap();
    let attrs = json!({"schema":"archeaxis.deeptutor-question/v1", "source_material":frame["material_snapshot"],
        "origin":"user_import_unverified", "question":{"question_id":frame["question_id"],
            "question":"Which option?", "question_type":"single_choice", "options":{"A":"first","B":"second"},
            "correct_answer":"SENTINEL_ANSWER", "explanation":"SENTINEL_EXPLANATION"}});
    let content: Vec<Value> = ["Which option?", "A. first", "B. second"].into_iter().map(|text|
        json!({"type":"paragraph","content":[{"type":"text","text":text}]})).collect();
    json!({"schema":"archeaxis.deeptutor-practice-host-worker/v1","request_id":frame["request_id"],
        "status":"PRIVATE_CANDIDATE","input_sha256":hex::encode(Sha256::digest(plan.worker_frame())),
        "document_create_request":{"create_request_id":frame["create_request_id"],
            "source_id":frame["import_receipt"]["source_id"],"source_revision":frame["source"]["sha256"],
            "title":frame["title"],"editor_json":{"type":"doc","content":content,
                "attrs":{"archeaxis_deeptutor_question":attrs}}},
        "source_link":"PINNED_PARSER_OF_CALLER_BYTES_NOT_AUTHENTICATED",
        "import_receipt":"CALLER_SUPPLIED_NOT_AUTHENTICATED", "material_snapshot":"CALLER_DECLARED_NOT_AUTHENTICATED",
        "row_and_loss_receipt":"NOT_RETURNED_OR_PERSISTED_BY_WORKER", "core_write":"NOT_EXECUTED",
        "provider_execution":"NOT_INVOKED", "output_privacy_filter":"NOT_APPLIED"})
}

fn private_line(value: &Value) -> Vec<u8> {
    let mut bytes = serde_json::to_vec(value).unwrap(); bytes.push(b'\n'); bytes
}

#[test]
fn practice_import_uses_real_source_and_is_atomic_idempotent_and_private() {
    let dir=tempfile::tempdir().unwrap();
    let path=dir.path().join("practice.sqlite");
    let mut conn=archeaxis_store_sqlite::init_workspace(path.to_str().unwrap()).unwrap();
    let selected=material(&mut conn);
    let original=b"[{\"question\":\"synthetic source\"}]";
    let request=imported_practice(&mut conn,original,&selected,"practice_create_once");
    let plan=provider_question::prepare_practice_import(&mut conn,&request).unwrap();
    let frame: Value=serde_json::from_slice(&plan.worker_frame()[..plan.worker_frame().len()-1]).unwrap();
    assert_eq!(STANDARD.decode(frame["source"]["content_base64"].as_str().unwrap()).unwrap().as_slice(),original.as_slice());
    assert_eq!(frame["import_receipt"]["source_id"],request.source_id);
    assert_eq!(frame["source"]["sha256"],request.source_sha256);
    assert_eq!(frame["material_snapshot"],json!(snap(&selected)));
    let body=synthetic_worker_reply(&plan);
    let first=provider_question::finish_practice_import(&mut conn,&plan,&private_line(&body)).unwrap();
    assert_eq!(first["duplicate"],false);
    assert_eq!(first["provider_execution"],"NOT_INVOKED");
    assert_eq!(first["question_view"]["question"]["question"],"Which option?");
    assert!(!first.to_string().contains("SENTINEL_ANSWER"));
    assert!(!first.to_string().contains("SENTINEL_EXPLANATION"));
    let first_snapshot: Snapshot=serde_json::from_value(first["question_document"].clone()).unwrap();
    let stored=document::read(&conn,&first_snapshot.document_id,None).unwrap();
    assert_eq!(stored["source_id"],request.source_id);
    assert_eq!(stored["source_revision"],request.source_sha256);
    assert!(stored.to_string().contains("SENTINEL_ANSWER"));
    let again=provider_question::finish_practice_import(&mut conn,&plan,&private_line(&body)).unwrap();
    assert_eq!(again["duplicate"],true);
    assert_eq!(again["question_document"],first["question_document"]);
    assert_eq!(conn.query_row("SELECT count(*) FROM documents",[],|r|r.get::<_,i64>(0)).unwrap(),2);

    let mut different=body.clone();
    different["document_create_request"]["editor_json"]["attrs"]["archeaxis_deeptutor_question"]["question"]["correct_answer"]=json!("different");
    assert!(matches!(provider_question::finish_practice_import(&mut conn,&plan,&private_line(&different)),Err(document::Error::Conflict(_))));
    assert_eq!(conn.query_row("SELECT count(*) FROM documents",[],|r|r.get::<_,i64>(0)).unwrap(),2);

    // A retry never overwrites a later human revision; the same initial
    // version is returned with an explicit historical question status.
    document::save(&mut conn,&first_snapshot.document_id,1,stored["editor_json"].clone()).unwrap();
    let historical=provider_question::finish_practice_import(&mut conn,&plan,&private_line(&body)).unwrap();
    assert_eq!(historical["duplicate"],true);
    assert_eq!(historical["question_view"]["question_status"],"historical");
    drop(conn);
    let conn=archeaxis_store_sqlite::init_workspace(path.to_str().unwrap()).unwrap();
    let reopened=provider_question::read_view(&conn,&first_snapshot).unwrap();
    assert_eq!(reopened["question_status"],"historical");
}

#[test]
fn private_practice_reply_rejects_mismatches_and_duplicate_or_invalid_frames() {
    let dir=tempfile::tempdir().unwrap();
    let mut conn=archeaxis_store_sqlite::init_workspace(dir.path().join("db.sqlite").to_str().unwrap()).unwrap();
    let selected=material(&mut conn);
    let request=imported_practice(&mut conn,b"synthetic row",&selected,"reject_bad_reply");
    let plan=provider_question::prepare_practice_import(&mut conn,&request).unwrap();
    let good=synthetic_worker_reply(&plan);
    for case in ["request", "input_hash", "source_id", "source_hash", "material", "question_id", "visible_text", "extra_attribute", "worker_flag"] {
        let mut bad=good.clone();
        match case {
            "request" => bad["request_id"]=json!("other"),
            "input_hash" => bad["input_sha256"]=json!("0".repeat(64)),
            "source_id" => bad["document_create_request"]["source_id"]=json!("other_source"),
            "source_hash" => bad["document_create_request"]["source_revision"]=json!("0".repeat(64)),
            "material" => bad["document_create_request"]["editor_json"]["attrs"]["archeaxis_deeptutor_question"]["source_material"]["content_sha256"]=json!("0".repeat(64)),
            "question_id" => bad["document_create_request"]["editor_json"]["attrs"]["archeaxis_deeptutor_question"]["question"]["question_id"]=json!("other_question"),
            "visible_text" => bad["document_create_request"]["editor_json"]["content"][0]["content"][0]["text"]=json!("SENTINEL_ANSWER"),
            "extra_attribute" => bad["document_create_request"]["editor_json"]["attrs"]["other"]=json!(true),
            "worker_flag" => bad["provider_execution"]=json!("CLAIMED"),
            _ => unreachable!(),
        }
        assert!(provider_question::finish_practice_import(&mut conn,&plan,&private_line(&bad)).is_err(),"{case}");
        assert_eq!(conn.query_row("SELECT count(*) FROM documents",[],|r|r.get::<_,i64>(0)).unwrap(),1,"{case}");
    }
    let valid=private_line(&good);
    let duplicate=String::from_utf8(valid.clone()).unwrap().replace(
        "\"correct_answer\":\"SENTINEL_ANSWER\"",
        "\"correct_answer\":\"SENTINEL_ANSWER\",\"correct_answer\":\"OTHER\"");
    assert_ne!(duplicate.as_bytes(),valid.as_slice());
    for bad in [valid[..valid.len()-1].to_vec(), [valid.clone(),b"extra\n".to_vec()].concat(),
        duplicate.into_bytes(), vec![0xff,b'\n'], vec![b' ';1_114_113]] {
        assert!(provider_question::finish_practice_import(&mut conn,&plan,&bad).is_err());
    }
    assert_eq!(conn.query_row("SELECT count(*) FROM documents",[],|r|r.get::<_,i64>(0)).unwrap(),1);
    assert_eq!(archeaxis_store_sqlite::raw_objects::read_bounded(&conn,&request.source_sha256,5*1024*1024).unwrap().as_slice(),b"synthetic row");
}

#[test]
fn practice_import_rechecks_restore_material_and_rolls_back_a_bad_created_view() {
    let dir=tempfile::tempdir().unwrap();
    let mut conn=archeaxis_store_sqlite::init_workspace(dir.path().join("db.sqlite").to_str().unwrap()).unwrap();
    let selected=material(&mut conn);
    let request=imported_practice(&mut conn,b"synthetic source",&selected,"after_restore");
    let plan=provider_question::prepare_practice_import(&mut conn,&request).unwrap();
    let body=synthetic_worker_reply(&plan);
    let backup_path=dir.path().join("snapshot.sqlite");
    backup::backup(&conn,backup_path.to_str().unwrap()).unwrap();
    let mut restored=archeaxis_store_sqlite::init_workspace(dir.path().join("restored.sqlite").to_str().unwrap()).unwrap();
    assert!(backup::restore_authorized(backup_path.to_str().unwrap(),&mut restored).unwrap());
    assert!(provider_question::finish_practice_import(&mut restored,&plan,&private_line(&body)).is_err());
    assert_eq!(restored.query_row("SELECT count(*) FROM documents",[],|r|r.get::<_,i64>(0)).unwrap(),1);

    // A changed current version is still a valid explicit historical snapshot.
    let mut changed=selected["editor_json"].clone();
    changed["content"][0]["content"][0]["text"]=json!("new material revision");
    document::save(&mut conn,selected["document_id"].as_str().unwrap(),1,changed).unwrap();
    let historical=provider_question::finish_practice_import(&mut conn,&plan,&private_line(&body)).unwrap();
    assert_eq!(historical["question_view"]["source_snapshot_status"],"historical");

    let other=imported_practice(&mut conn,b"another synthetic source",&selected,"rollback_created_view");
    let other_plan=provider_question::prepare_practice_import(&mut conn,&other).unwrap();
    let other_body=synthetic_worker_reply(&other_plan);
    let expected_id=format!("doc_req_{}",hex::encode(Sha256::digest(b"rollback_created_view")));
    conn.execute_batch("CREATE TRIGGER synthetic_corrupt_question AFTER INSERT ON document_versions WHEN NEW.document_id LIKE 'doc_req_%' BEGIN UPDATE document_versions SET content_sha256='invalid' WHERE document_id=NEW.document_id AND version=NEW.version; END;").unwrap();
    assert!(provider_question::finish_practice_import(&mut conn,&other_plan,&private_line(&other_body)).is_err());
    assert_eq!(conn.query_row("SELECT count(*) FROM documents WHERE document_id=?1",[&expected_id],|r|r.get::<_,i64>(0)).unwrap(),0);
    assert_eq!(archeaxis_store_sqlite::raw_objects::read_bounded(&conn,&other.source_sha256,5*1024*1024).unwrap().as_slice(),b"another synthetic source");
}
