//! Owned SYNTHETIC asset/rubric material; canonical writer tests after integration.
use archeaxis_domain::{
    ai_asset::{self, Snapshot},
    asset_context_grant::{self, Consumer, Operation, PacketRequest},
    document,
    machine_evaluation::{self, Criterion, Rubric},
};
use serde_json::{Value, json};
fn workspace() -> (tempfile::TempDir, rusqlite::Connection) {
    let d = tempfile::tempdir().unwrap();
    let c =
        archeaxis_store_sqlite::init_workspace(d.path().join("workspace.sqlite").to_str().unwrap())
            .unwrap();
    (d, c)
}
fn asset(kind: &str) -> Value {
    json!({"schema":"archeaxis.ai-asset/v1","kind":kind,"content":{"inert_text":"SYNTHETIC material","unknown_nested":{"command":"never executed"}},"purpose":"",
    "scope":[],"provenance":[],"expires_at":null,"state":"candidate","members":[],"conflicts":[],"revises":null,"review":null,"source_payload":{"dialect":"unknown","original":"preserved"}})
}
fn envelope(a: Value) -> Value {
    json!({"type":"doc","content":[],"attrs":{"archeaxis_ai_asset":a,"unknown_future":{"keep":"exact"}}})
}
fn create(c: &mut rusqlite::Connection, key: &str, a: Value) -> Value {
    document::create_optional_with_request(c, None, None, "owned AI asset", envelope(a), Some(key))
        .unwrap()
}
fn rubric(c: &mut rusqlite::Connection) -> Snapshot {
    let r = machine_evaluation::create_rubric(
        c,
        "human",
        &Rubric {
            schema: machine_evaluation::RUBRIC_SCHEMA.into(),
            request_id: "asset-fixed-rubric".into(),
            title: "owned rubric".into(),
            purpose: "asset usefulness".into(),
            criteria: vec![Criterion {
                criterion_id: "c1".into(),
                label: "fit".into(),
                expectation: "human observed fit".into(),
            }],
            sources: vec![],
        },
    )
    .unwrap();
    ai_asset::snapshot(&r).unwrap()
}
fn adopt(c: &mut rusqlite::Connection, key: &str, kind: &str, mut a: Value) -> Value {
    a["purpose"] = json!("owned purpose");
    let candidate = create(c, key, a);
    let mut e = candidate["editor_json"].clone();
    e["attrs"]["archeaxis_ai_asset"]["state"] = json!("adopted");
    e["attrs"]["archeaxis_ai_asset"]["review"] = json!({"asset":ai_asset::snapshot(&candidate).unwrap(),"rubric":rubric(c),"reviewer":"owner annotation","basis":"SYNTHETIC observed criterion",
        "judgments":[{"criterion_id":"c1","outcome":"passed","basis":"observed fit"}],"outcome":"passed"});
    let result = document::save(c, candidate["document_id"].as_str().unwrap(), 1, e).unwrap();
    assert_eq!(
        result["editor_json"]["attrs"]["archeaxis_ai_asset"]["kind"],
        kind
    );
    result
}
fn grant(c: &mut rusqlite::Connection, a: &Value, expiry: Option<u64>) -> Value {
    document::create_optional_with_request(c,None,None,"human asset grant",json!({"type":"doc","content":[],"attrs":{"archeaxis_asset_context_grant":{
        "schema":"archeaxis.asset-context-grant/v1","asset":ai_asset::snapshot(a).unwrap(),"purpose":"owned purpose","consumer":"manual-context-packet","operations":["read_packet"],"authorization_basis":"explicit SYNTHETIC human grant","expires_at":expiry,"state":"granted"}}}),Some("owned-packet-grant")).unwrap()
}
fn request(a: &Value, g: &Value) -> PacketRequest {
    PacketRequest {
        request_id: "owned-frozen-packet".into(),
        asset: ai_asset::snapshot(a).unwrap(),
        grant: ai_asset::snapshot(g).unwrap(),
        purpose: "owned purpose".into(),
        consumer: Consumer::ManualContextPacket,
        operation: Operation::ReadPacket,
    }
}
#[test]
fn five_inert_candidates_save_without_purpose_or_evaluation_and_preserve_unknown_payload() {
    let (_dir, mut c) = workspace();
    for kind in ["memory", "knowledge_package", "rule", "skill", "experience"] {
        let raw = asset(kind);
        let d = create(&mut c, &format!("asset-{kind}"), raw.clone());
        assert_eq!(d["editor_json"]["attrs"]["archeaxis_ai_asset"], raw);
        assert_eq!(d["editor_json"]["attrs"]["unknown_future"]["keep"], "exact");
        assert!(ai_asset::packet_items(&c, &ai_asset::snapshot(&d).unwrap(), 1).is_err());
    }
}
#[test]
fn adopting_without_fixed_review_and_reusing_pass_after_content_edit_are_rejected() {
    let (_dir, mut c) = workspace();
    let candidate = create(&mut c, "unreviewed", asset("rule"));
    let mut e = candidate["editor_json"].clone();
    e["attrs"]["archeaxis_ai_asset"]["state"] = json!("adopted");
    assert!(document::save(&mut c, candidate["document_id"].as_str().unwrap(), 1, e).is_err());
    let adopted = adopt(&mut c, "reviewed", "rule", asset("rule"));
    let mut changed = adopted["editor_json"].clone();
    changed["attrs"]["archeaxis_ai_asset"]["content"] = json!("changed after review");
    assert!(document::save(&mut c, adopted["document_id"].as_str().unwrap(), 2, changed).is_err());
    assert_eq!(
        document::read(&c, adopted["document_id"].as_str().unwrap(), None).unwrap(),
        adopted
    );
}
#[test]
fn finite_packet_retry_is_exact_and_new_purpose_or_consumer_is_not_cached_authority() {
    let (_dir, mut c) = workspace();
    let a = adopt(&mut c, "packet-memory", "memory", asset("memory"));
    let g = grant(&mut c, &a, None);
    let mut r = request(&a, &g);
    let first =
        asset_context_grant::prepare_packet(&mut c, &r, Consumer::ManualContextPacket, 1).unwrap();
    assert_eq!(first["duplicate"], false);
    assert_eq!(first["packet"]["private_session_access"], false);
    assert_eq!(
        first["receipt"]["delivery_status"],
        "PREPARED_NOT_SENT_TO_PEER"
    );
    assert_eq!(first["packet_sha256"], ai_asset::hash(&first["packet"]));
    let again =
        asset_context_grant::prepare_packet(&mut c, &r, Consumer::ManualContextPacket, 1).unwrap();
    assert_eq!(again["duplicate"], true);
    assert_eq!(first["receipt"], again["receipt"]);
    assert!(asset_context_grant::prepare_packet(&mut c, &r, Consumer::LocalMachine, 1).is_err());
    r.purpose = "other purpose".into();
    assert!(
        asset_context_grant::prepare_packet(&mut c, &r, Consumer::ManualContextPacket, 1).is_err()
    );
}
#[test]
fn revoke_or_expiry_denies_even_replayed_prepared_packet() {
    let (_dir, mut c) = workspace();
    let a = adopt(&mut c, "expires-memory", "memory", asset("memory"));
    let g = grant(&mut c, &a, Some(5));
    let r = request(&a, &g);
    asset_context_grant::prepare_packet(&mut c, &r, Consumer::ManualContextPacket, 4).unwrap();
    assert!(
        asset_context_grant::prepare_packet(&mut c, &r, Consumer::ManualContextPacket, 5).is_err()
    );
    let mut revoked = g["editor_json"].clone();
    revoked["attrs"]["archeaxis_asset_context_grant"]["state"] = json!("revoked");
    document::save(&mut c, g["document_id"].as_str().unwrap(), 1, revoked).unwrap();
    assert!(
        asset_context_grant::prepare_packet(&mut c, &r, Consumer::ManualContextPacket, 4).is_err()
    );
    assert!(
        document::save(
            &mut c,
            g["document_id"].as_str().unwrap(),
            2,
            g["editor_json"].clone()
        )
        .is_err()
    );
}
#[test]
fn package_member_withdrawal_and_restore_fence_prevent_packet_replay() {
    let (_dir, mut c) = workspace();
    let member = adopt(&mut c, "member-rule", "rule", asset("rule"));
    let mut p = asset("knowledge_package");
    p["members"] = json!([ai_asset::snapshot(&member).unwrap()]);
    let package = adopt(&mut c, "package", "knowledge_package", p);
    let g = grant(&mut c, &package, None);
    let r = request(&package, &g);
    let packet =
        asset_context_grant::prepare_packet(&mut c, &r, Consumer::ManualContextPacket, 1).unwrap();
    assert_eq!(packet["packet"]["items"].as_array().unwrap().len(), 2);
    let tx = c.transaction().unwrap();
    archeaxis_store_sqlite::authorization_fence::install_after_restore(&tx).unwrap();
    tx.commit().unwrap();
    assert!(
        asset_context_grant::prepare_packet(&mut c, &r, Consumer::ManualContextPacket, 1).is_err()
    );
    let mut withdrawn = member["editor_json"].clone();
    withdrawn["attrs"]["archeaxis_ai_asset"]["state"] = json!("withdrawn");
    document::save(
        &mut c,
        member["document_id"].as_str().unwrap(),
        2,
        withdrawn,
    )
    .unwrap();
    assert!(ai_asset::packet_items(&c, &ai_asset::snapshot(&package).unwrap(), 1).is_err());
    assert!(
        document::save(
            &mut c,
            member["document_id"].as_str().unwrap(),
            3,
            member["editor_json"].clone()
        )
        .is_err()
    );
}
#[test]
fn unsupported_shape_or_fake_reference_rejected_without_partial_version() {
    let (_dir, mut c) = workspace();
    let d = create(&mut c, "shape", asset("experience"));
    let mut e = d["editor_json"].clone();
    e["attrs"]["archeaxis_ai_asset"]["unknown_field"] = json!("preserve readonly import");
    assert!(document::save(&mut c, d["document_id"].as_str().unwrap(), 1, e).is_err());
    let mut e = d["editor_json"].clone();
    e["attrs"]["archeaxis_ai_asset"]["provenance"] =
        json!([{"kind":"knowledge","knowledge_id":"not_real"}]);
    assert!(document::save(&mut c, d["document_id"].as_str().unwrap(), 1, e).is_err());
    assert_eq!(
        document::read(&c, d["document_id"].as_str().unwrap(), None).unwrap(),
        d
    );
}

// Append to CURRENT crates/archeaxis-domain/tests/ai_assets.rs; reuse its real helpers.
fn review_updated_candidate(c: &mut rusqlite::Connection, candidate: &Value) -> Value {
    let mut e = candidate["editor_json"].clone();
    e["attrs"]["archeaxis_ai_asset"]["state"] = json!("adopted");
    e["attrs"]["archeaxis_ai_asset"]["review"] = json!({"asset":ai_asset::snapshot(candidate).unwrap(),"rubric":rubric(c),"reviewer":"owner annotation","basis":"SYNTHETIC renewed observation",
        "judgments":[{"criterion_id":"c1","outcome":"passed","basis":"observed revised fit"}],"outcome":"passed"});
    document::save(
        c,
        candidate["document_id"].as_str().unwrap(),
        candidate["version"].as_i64().unwrap(),
        e,
    )
    .unwrap()
}
#[test]
fn declared_conflict_cannot_be_consumed_and_clearing_it_cannot_reuse_old_review() {
    let (_dir, mut c) = workspace();
    let other = adopt(&mut c, "conflict-other", "experience", asset("experience"));
    let mut a = asset("rule");
    a["conflicts"] = json!([ai_asset::snapshot(&other).unwrap()]);
    let conflicted = adopt(&mut c, "conflicted-rule", "rule", a);
    assert!(ai_asset::packet_items(&c, &ai_asset::snapshot(&conflicted).unwrap(), 1).is_err());
    let mut cleared = conflicted["editor_json"].clone();
    cleared["attrs"]["archeaxis_ai_asset"]["conflicts"] = json!([]);
    assert!(
        document::save(
            &mut c,
            conflicted["document_id"].as_str().unwrap(),
            2,
            cleared.clone()
        )
        .is_err()
    );
    assert_eq!(
        document::read(&c, conflicted["document_id"].as_str().unwrap(), Some(2)).unwrap(),
        conflicted
    );
    cleared["attrs"]["archeaxis_ai_asset"]["state"] = json!("candidate");
    cleared["attrs"]["archeaxis_ai_asset"]["review"] = Value::Null;
    let candidate = document::save(
        &mut c,
        conflicted["document_id"].as_str().unwrap(),
        2,
        cleared,
    )
    .unwrap();
    let renewed = review_updated_candidate(&mut c, &candidate);
    assert_eq!(
        ai_asset::packet_items(&c, &ai_asset::snapshot(&renewed).unwrap(), 1)
            .unwrap()
            .len(),
        1
    );
    assert_eq!(
        document::read(&c, other["document_id"].as_str().unwrap(), Some(2)).unwrap(),
        other
    );
}
#[test]
fn removing_package_member_invalidates_old_grant_and_new_review_and_human_grant_use_only_new_members()
 {
    let (_dir, mut c) = workspace();
    let child = adopt(&mut c, "removable-child", "memory", asset("memory"));
    let mut a = asset("knowledge_package");
    a["members"] = json!([ai_asset::snapshot(&child).unwrap()]);
    let package = adopt(&mut c, "remove-package", "knowledge_package", a);
    let old_grant = grant(&mut c, &package, None);
    let old = request(&package, &old_grant);
    let prepared =
        asset_context_grant::prepare_packet(&mut c, &old, Consumer::ManualContextPacket, 1)
            .unwrap();
    assert_eq!(prepared["packet"]["items"].as_array().unwrap().len(), 2);
    let mut e = package["editor_json"].clone();
    e["attrs"]["archeaxis_ai_asset"]["members"] = json!([]);
    assert!(
        document::save(
            &mut c,
            package["document_id"].as_str().unwrap(),
            2,
            e.clone()
        )
        .is_err()
    );
    e["attrs"]["archeaxis_ai_asset"]["state"] = json!("candidate");
    e["attrs"]["archeaxis_ai_asset"]["review"] = Value::Null;
    let candidate = document::save(&mut c, package["document_id"].as_str().unwrap(), 2, e).unwrap();
    let current = review_updated_candidate(&mut c, &candidate);
    assert!(
        asset_context_grant::prepare_packet(&mut c, &old, Consumer::ManualContextPacket, 1)
            .is_err()
    );
    let new_grant=document::create_optional_with_request(&mut c,None,None,"new explicit human package grant",json!({"type":"doc","content":[],"attrs":{"archeaxis_asset_context_grant":{
        "schema":"archeaxis.asset-context-grant/v1","asset":ai_asset::snapshot(&current).unwrap(),"purpose":"owned purpose","consumer":"manual-context-packet","operations":["read_packet"],
        "authorization_basis":"explicit owner review of changed membership","expires_at":null,"state":"granted"}}}),Some("revised-package-new-grant")).unwrap();
    let mut fresh = request(&current, &new_grant);
    fresh.request_id = "revised-package-new-packet".into();
    let prepared =
        asset_context_grant::prepare_packet(&mut c, &fresh, Consumer::ManualContextPacket, 1)
            .unwrap();
    assert_eq!(prepared["packet"]["items"].as_array().unwrap().len(), 1);
    assert_eq!(
        document::read(&c, package["document_id"].as_str().unwrap(), Some(2)).unwrap(),
        package
    );
    assert_eq!(
        document::read(&c, child["document_id"].as_str().unwrap(), None).unwrap(),
        child,
        "removing membership does not rewrite the independent child"
    );
}
#[test]
fn revision_is_a_new_identity_with_immutable_original_link_and_cannot_copy_original_review() {
    let (_dir, mut c) = workspace();
    let original = adopt(&mut c, "revision-original", "skill", asset("skill"));
    let mut next = asset("skill");
    next["content"] = json!("new revised inert skill material");
    next["revises"] = json!(ai_asset::snapshot(&original).unwrap());
    let revised = create(&mut c, "revision-new", next);
    assert_ne!(revised["document_id"], original["document_id"]);
    let mut copied = revised["editor_json"].clone();
    copied["attrs"]["archeaxis_ai_asset"]["purpose"] = json!("owned purpose");
    copied["attrs"]["archeaxis_ai_asset"]["state"] = json!("adopted");
    copied["attrs"]["archeaxis_ai_asset"]["review"] =
        original["editor_json"]["attrs"]["archeaxis_ai_asset"]["review"].clone();
    assert!(document::save(&mut c, revised["document_id"].as_str().unwrap(), 1, copied).is_err());
    let mut purpose = revised["editor_json"].clone();
    purpose["attrs"]["archeaxis_ai_asset"]["purpose"] = json!("owned purpose");
    let saved =
        document::save(&mut c, revised["document_id"].as_str().unwrap(), 1, purpose).unwrap();
    let adopted = review_updated_candidate(&mut c, &saved);
    assert_eq!(
        adopted["editor_json"]["attrs"]["archeaxis_ai_asset"]["revises"],
        json!(ai_asset::snapshot(&original).unwrap())
    );
    assert_eq!(
        document::read(&c, original["document_id"].as_str().unwrap(), Some(2)).unwrap(),
        original
    );
    assert_eq!(
        ai_asset::packet_items(&c, &ai_asset::snapshot(&adopted).unwrap(), 1)
            .unwrap()
            .len(),
        1
    );
}
