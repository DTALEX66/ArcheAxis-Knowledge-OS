//! SYNTHETIC packets, real canonical SQLite/Document persistence; no external provider.
use archeaxis_domain::{
    document,
    external_context::{self as ext, *},
};
use serde_json::{Value, json};
fn packet() -> Value {
    json!({"schema_version":1,"candidate_id":"fix-1","knowledge_kind":"verified_fix",
        "title":"Version-bound repair","summary":"Check the actual failure",
        "problem":"Synthetic compile error","root_cause":"UNKNOWN","failed_attempts":[],
        "resolution":"UNRESOLVED","applicability":"fixture-only","contraindications":"unknown versions",
        "evidence_refs":[],"verification":{"status":"PASS","command":null,"exit_code":null,
        "artifact_hash":null,"diff_ref":null},"source":{"provider_id":"fixture-provider",
        "project_id":"future-project-125","source_app":"fixture-agent","source_ref":"opaque:case-1",
        "auth_scope":"knowledge_candidate:import","fetch_status":"AVAILABLE","provenance":[],
        "updated_at":"2026-10-23T00:00:00Z"}})
}
fn admission() -> Admission<'static> {
    Admission {
        provider_id: "fixture-provider",
        project_id: "future-project-125",
        auth_scope: "knowledge_candidate:import",
        material_authorized: true,
        redaction_confirmed: true,
    }
}
fn workspace() -> (tempfile::TempDir, rusqlite::Connection) {
    let d = tempfile::tempdir().unwrap();
    let c =
        archeaxis_store_sqlite::init_workspace(d.path().join("workspace.sqlite").to_str().unwrap())
            .unwrap();
    (d, c)
}
#[test]
fn receive_idempotent_restart_and_no_automatic_promotion() {
    let (dir, mut c) = workspace();
    let p: Candidate = serde_json::from_value(packet()).unwrap();
    let before: i64 = c
        .query_row(
            "SELECT count(*) FROM sqlite_master WHERE type='table'",
            [],
            |r| r.get(0),
        )
        .unwrap();
    let d = ext::receive(&mut c, &p, &admission()).unwrap();
    assert_eq!(ext::receive(&mut c, &p, &admission()).unwrap(), d);
    let mut changed = p.clone();
    changed.summary = "different payload same identity".into();
    assert!(ext::receive(&mut c, &changed, &admission()).is_err());
    assert_eq!(
        before,
        c.query_row::<i64, _, _>(
            "SELECT count(*) FROM sqlite_master WHERE type='table'",
            [],
            |r| r.get(0)
        )
        .unwrap()
    );
    let id = d["document_id"].as_str().unwrap();
    let mut e = d["editor_json"].clone();
    e["attrs"]["archeaxis_ai_asset"]["state"] = json!("adopted");
    assert!(document::save(&mut c, id, 1, e).is_err());
    drop(c);
    let reopened = archeaxis_store_sqlite::init_workspace(
        dir.path().join("workspace.sqlite").to_str().unwrap(),
    )
    .unwrap();
    let read = ext::read(&reopened, id, &admission(), FetchStatus::Available).unwrap();
    assert_eq!(read["state"], "candidate");
    assert_eq!(read["candidate"]["verification"]["status"], "PASS");
    assert_eq!(read["evidence_assessment"], "UNVERIFIED_EXTERNAL");
    assert_eq!(read["candidate"]["root_cause"], "UNKNOWN");
}
#[test]
fn same_candidate_id_is_namespaced_and_cannot_cross_read() {
    let (_d, mut c) = workspace();
    let mut p: Candidate = serde_json::from_value(packet()).unwrap();
    let first = ext::receive(&mut c, &p, &admission()).unwrap();
    p.source.project_id = "another-new-project".into();
    let a = Admission {
        project_id: "another-new-project",
        ..admission()
    };
    let second = ext::receive(&mut c, &p, &a).unwrap();
    assert_ne!(first["document_id"], second["document_id"]);
    assert!(
        ext::read(
            &c,
            first["document_id"].as_str().unwrap(),
            &a,
            FetchStatus::Available
        )
        .is_err()
    );
    let wrong = Admission {
        provider_id: "another-provider",
        ..admission()
    };
    assert!(
        ext::read(
            &c,
            first["document_id"].as_str().unwrap(),
            &wrong,
            FetchStatus::Available
        )
        .is_err()
    );
}
#[test]
fn unavailable_or_revoked_never_new_import_and_existing_packet_preserved() {
    let (_d, mut c) = workspace();
    let mut p: Candidate = serde_json::from_value(packet()).unwrap();
    let d = ext::receive(&mut c, &p, &admission()).unwrap();
    let id = d["document_id"].as_str().unwrap();
    for status in [
        FetchStatus::Offline,
        FetchStatus::Timeout,
        FetchStatus::Revoked,
        FetchStatus::Missing,
        FetchStatus::Deleted,
        FetchStatus::Unknown,
    ] {
        p.source.fetch_status = status.clone();
        assert!(ext::receive(&mut c, &p, &admission()).is_err());
        let response = ext::read(&c, id, &admission(), status.clone()).unwrap();
        assert_eq!(
            response["fetch_status"],
            serde_json::to_value(status).unwrap()
        );
        assert!(response["candidate"].is_null());
        assert_eq!(document::read(&c, id, None).unwrap(), d);
    }
    let revoked = Admission {
        material_authorized: false,
        ..admission()
    };
    assert!(ext::read(&c, id, &revoked, FetchStatus::Available).is_err());
}
#[test]
fn strict_whitelist_rejects_context_logs_governance_and_unknown_nested_fields() {
    for field in [
        "raw_context",
        "messages",
        "tool_logs",
        "governance",
        "session_history",
    ] {
        let mut v = packet();
        v[field] = json!(["must not be stored"]);
        assert!(serde_json::from_value::<Candidate>(v).is_err());
    }
    let mut v = packet();
    v["source"]["raw_prompt"] = json!("not admitted");
    assert!(serde_json::from_value::<Candidate>(v).is_err());
    let mut v = packet();
    v["verification"]["approved"] = json!(true);
    assert!(serde_json::from_value::<Candidate>(v).is_err());
}
#[test]
fn schema_bounds_and_explicit_material_authorization() {
    let mut p: Candidate = serde_json::from_value(packet()).unwrap();
    let unredacted = Admission {
        redaction_confirmed: false,
        ..admission()
    };
    assert!(ext::validate(&p, &unredacted).is_err());
    p.schema_version = 2;
    assert!(ext::validate(&p, &admission()).is_err());
    p.schema_version = 1;
    p.summary = "x".repeat(4097);
    assert!(ext::validate(&p, &admission()).is_err());
    assert_eq!(ext::PROVIDER_STATE, "NOT_CONNECTED");
}
#[test]
fn private_paths_and_credential_bearing_references_rejected() {
    let mut p: Candidate = serde_json::from_value(packet()).unwrap();
    for reference in [
        "C:/Users/private/session.json",
        "file:///private/session",
        "https://user:password@host/log",
        "https://host/log?token=secret",
        "/private/session",
    ] {
        p.source.source_ref = reference.into();
        assert!(ext::validate(&p, &admission()).is_err());
    }
}
#[test]
fn diff_and_hash_claims_do_not_make_authoritative_repair() {
    let (_d, mut c) = workspace();
    let mut p: Candidate = serde_json::from_value(packet()).unwrap();
    p.verification.command = Some("synthetic command".into());
    p.verification.exit_code = Some(0);
    p.verification.diff_ref = Some("opaque:claimed-diff".into());
    p.verification.artifact_hash = Some("0".repeat(64));
    p.failed_attempts
        .push("counterexample: failed on other version".into());
    let d = ext::receive(&mut c, &p, &admission()).unwrap();
    assert_eq!(
        d["editor_json"]["attrs"]["archeaxis_ai_asset"]["state"],
        "candidate"
    );
    assert_eq!(
        d["editor_json"]["attrs"]["archeaxis_ai_asset"]["content"]["evidence_assessment"],
        "UNVERIFIED_EXTERNAL"
    );
}
