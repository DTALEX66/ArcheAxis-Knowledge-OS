//! SYNTHETIC owned-workspace fixtures. After integration, exercise actual Document append.
use archeaxis_domain::{document, knowledge, learning, template_binding};
use rusqlite::{Connection, params};
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
fn workspace() -> (tempfile::TempDir, Connection) {
    let dir = tempfile::tempdir().unwrap();
    let conn = archeaxis_store_sqlite::init_workspace(
        dir.path().join("workspace.sqlite").to_str().unwrap(),
    )
    .unwrap();
    (dir, conn)
}
fn template() -> Value {
    json!({"schema":"archeaxis.template/v1","template_id":"T1","discipline_id":"math","fields":{},"references":[],"learning_item_key":null})
}
fn editor(value: Value) -> Value {
    json!({"type":"doc","attrs":{"archeaxis_template":value,"unknown_unrelated":{"command":"never execute","keep":[null,1,true]}},"content":[]})
}
fn create(conn: &mut Connection, key: &str, value: Value) -> Value {
    document::create_optional_with_request(
        conn,
        None,
        None,
        "SYNTHETIC owned template",
        editor(value),
        Some(key),
    )
    .unwrap()
}
fn reference(id: &str, version: i64, block: Option<&str>) -> Value {
    json!({"document_id":id,"version":version,"block_id":block,"relation":"","x":-20.25,"y":40.5})
}
fn counts(conn: &Connection) -> (i64, i64) {
    (
        conn.query_row("SELECT count(*) FROM documents", [], |r| r.get(0))
            .unwrap(),
        conn.query_row("SELECT count(*) FROM document_versions", [], |r| r.get(0))
            .unwrap(),
    )
}
// Seed an archived pre-validator version only in this disposable owned fixture.
// Production has no endpoint which bypasses validation or mutates old versions.
fn archived_legacy(conn: &Connection, id: &str, value: Value) -> Value {
    let payload = editor(value);
    let encoded = payload.to_string();
    let digest = hex::encode(Sha256::digest(encoded.as_bytes()));
    conn.execute("INSERT INTO documents(document_id,title,current_version) VALUES(?1,'SYNTHETIC archived legacy',1)",[id]).unwrap();
    conn.execute("INSERT INTO document_versions(document_id,version,editor_json,text_projection,content_sha256) VALUES(?1,1,?2,'',?3)",params![id,encoded,digest]).unwrap();
    document::read(conn, id, Some(1)).unwrap()
}
#[test]
fn all_28_existing_disciplines_share_three_templates_and_incomplete_fields_remain_allowed() {
    let (_dir, mut conn) = workspace();
    let schema: Value = serde_json::from_str(include_str!(
        "../../../packages/contracts/v2/template-binding.schema.json"
    ))
    .unwrap();
    let disciplines = schema["properties"]["discipline_id"]["enum"]
        .as_array()
        .unwrap();
    assert_eq!(disciplines.len(), 28);
    for (index, discipline) in disciplines.iter().enumerate() {
        for kind in ["T1", "T2", "T3"] {
            let mut value = template();
            value["template_id"] = json!(kind);
            value["discipline_id"] = discipline.clone();
            value["fields"] =
                json!({"status":"unevaluated","空白草稿":"","额外描述":"inert eval('never run')"});
            let saved = create(&mut conn, &format!("owned-{index}-{kind}"), value.clone());
            assert_eq!(
                saved["editor_json"]["attrs"][template_binding::NAMESPACE],
                value
            );
            assert_eq!(
                saved["editor_json"]["attrs"]["unknown_unrelated"]["keep"],
                json!([null, 1, true])
            );
        }
    }
    assert_eq!(counts(&conn), (84, 84));
    assert_eq!(
        conn.query_row("SELECT count(*) FROM learning_events", [], |r| r
            .get::<_, i64>(0))
            .unwrap(),
        0
    );
}
#[test]
fn ordinary_document_without_template_namespace_keeps_unknown_attrs_and_no_new_tables() {
    let (_dir, mut conn) = workspace();
    let before: i64 = conn
        .query_row(
            "SELECT count(*) FROM sqlite_master WHERE type='table'",
            [],
            |r| r.get(0),
        )
        .unwrap();
    let body = json!({"type":"doc","attrs":{"future_namespace":{"keep":true}},"content":[]});
    let saved = document::create_optional(
        &mut conn,
        None,
        None,
        "ordinary incomplete note",
        body.clone(),
    )
    .unwrap();
    let next = document::save(
        &mut conn,
        saved["document_id"].as_str().unwrap(),
        1,
        body.clone(),
    )
    .unwrap();
    assert_eq!(next["editor_json"], body);
    let after: i64 = conn
        .query_row(
            "SELECT count(*) FROM sqlite_master WHERE type='table'",
            [],
            |r| r.get(0),
        )
        .unwrap();
    assert_eq!(before, after);
}
#[test]
fn pinned_document_version_block_and_coordinates_survive_target_edit_and_workspace_restart() {
    let (dir, mut conn) = workspace();
    let path = dir.path().join("workspace.sqlite");
    let target=document::create_optional(&mut conn,None,None,"target",json!({"type":"doc","content":[{"type":"paragraph","attrs":{"block_id":"stable-block"},"content":[{"type":"text","text":"v1 original"}]}]})).unwrap();
    let target_id = target["document_id"].as_str().unwrap();
    let mut value = template();
    value["references"] = json!([reference(target_id, 1, Some("stable-block"))]);
    let saved = create(&mut conn, "pinned-reference", value.clone());
    let saved_id = saved["document_id"].as_str().unwrap().to_owned();
    document::save(&mut conn,target_id,1,json!({"type":"doc","content":[{"type":"paragraph","attrs":{"block_id":"stable-block"},"content":[{"type":"text","text":"v2 changed"}]}]})).unwrap();
    let next = document::save(&mut conn, &saved_id, 1, saved["editor_json"].clone()).unwrap();
    drop(conn);
    let conn = archeaxis_store_sqlite::init_workspace(path.to_str().unwrap()).unwrap();
    let reread = document::read(&conn, &saved_id, None).unwrap();
    assert_eq!(reread["editor_json"], next["editor_json"]);
    assert_eq!(reread["content_sha256"], next["content_sha256"]);
    assert_eq!(
        reread["editor_json"]["attrs"]["archeaxis_template"]["references"][0]["version"],
        1
    );
    assert_eq!(
        document::read(&conn, target_id, Some(1)).unwrap()["blocks"][0]["text_projection"],
        "v1 original"
    );
}
#[test]
fn absent_document_version_block_malformed_identity_and_bad_geometry_fail_before_any_version_write()
{
    let (_dir, mut conn) = workspace();
    let target = document::create_optional(
        &mut conn,
        None,
        None,
        "target",
        json!({"type":"doc","content":[{"type":"paragraph","attrs":{"block_id":"block"}}]}),
    )
    .unwrap();
    let id = target["document_id"].as_str().unwrap();
    let mut variants = vec![
        reference("missing", 1, None),
        reference(id, 99, None),
        reference(id, 1, Some("absent")),
        reference(id, 0, None),
        reference("../outside", 1, None),
    ];
    let mut null_x = reference(id, 1, None);
    null_x["x"] = Value::Null;
    variants.push(null_x);
    let mut wrong_y = reference(id, 1, None);
    wrong_y["y"] = json!("40");
    variants.push(wrong_y);
    for (index, reference) in variants.into_iter().enumerate() {
        let before = counts(&conn);
        let mut value = template();
        value["references"] = json!([reference]);
        assert!(
            document::create_optional_with_request(
                &mut conn,
                None,
                None,
                "invalid ref",
                editor(value),
                Some(&format!("bad-ref-{index}"))
            )
            .is_err()
        );
        assert_eq!(counts(&conn), before);
    }
}
#[test]
fn nonempty_reference_limits_duplicates_missing_null_field_and_unrecognized_shape_are_not_silently_normalized()
 {
    let (_dir, mut conn) = workspace();
    let target = document::create_optional(
        &mut conn,
        None,
        None,
        "target",
        json!({"type":"doc","content":[]}),
    )
    .unwrap();
    let id = target["document_id"].as_str().unwrap();
    let mut cases = Vec::new();
    let mut v = template();
    v["references"] = json!(vec![reference(id, 1, None); 101]);
    cases.push(v);
    let mut v = template();
    v["references"] = json!([reference(id, 1, None), reference(id, 1, None)]);
    cases.push(v);
    let mut r = reference(id, 1, None);
    r.as_object_mut().unwrap().remove("block_id");
    let mut v = template();
    v["references"] = json!([r]);
    cases.push(v);
    let mut v = template();
    v.as_object_mut().unwrap().remove("learning_item_key");
    cases.push(v);
    let mut v = template();
    v["fields"] = json!({"status":true});
    cases.push(v);
    let mut v = template();
    v["schema"] = json!("archeaxis.template/v99");
    cases.push(v);
    let mut v = template();
    v["future_extension"] = json!({"keep":true});
    cases.push(v);
    let mut v = template();
    v["discipline_id"] = json!("made-up-discipline");
    cases.push(v);
    let mut v = template();
    v["template_id"] = json!("T99");
    cases.push(v);
    for (index, v) in cases.into_iter().enumerate() {
        let before = counts(&conn);
        assert!(
            document::create_optional_with_request(
                &mut conn,
                None,
                None,
                "bad shape",
                editor(v),
                Some(&format!("bad-shape-{index}"))
            )
            .is_err()
        );
        assert_eq!(counts(&conn), before);
    }
}
#[test]
fn learning_key_must_exist_and_missing_state_projection_cannot_authorize_a_binding() {
    let (_dir, mut conn) = workspace();
    let mut invalid = template();
    invalid["learning_item_key"] = json!("never-existed-but-state-returns-200");
    assert!(
        document::create_optional(
            &mut conn,
            None,
            None,
            "missing learning item",
            editor(invalid)
        )
        .is_err()
    );
    let mut blank = template();
    blank["learning_item_key"] = json!("  ");
    assert!(document::create_optional(&mut conn, None, None, "blank key", editor(blank)).is_err());
    let count: i64 = conn
        .query_row("SELECT count(*) FROM learning_events", [], |r| r.get(0))
        .unwrap();
    assert_eq!(count, 0);
    learning::record_learning_event(
        &mut conn,
        "actual owned item:一",
        "review",
        r#"{"outcome":"unmeasured"}"#,
        0,
    )
    .unwrap();
    let mut valid = template();
    valid["learning_item_key"] = json!("actual owned item:一");
    let saved = create(&mut conn, "event-backed-item", valid);
    assert_eq!(
        saved["editor_json"]["attrs"]["archeaxis_template"]["learning_item_key"],
        "actual owned item:一"
    );
    assert_eq!(
        conn.query_row("SELECT count(*) FROM learning_events", [], |r| r
            .get::<_, i64>(0))
            .unwrap(),
        1
    );
}
#[test]
fn learning_reference_and_assessment_are_existing_queue_items_without_requiring_review_or_mastery()
{
    let (_dir, mut conn) = workspace();
    let k = knowledge::create_knowledge(
        &mut conn,
        "PERSONAL_DEFINITION",
        "owned SYNTHETIC definition",
        "accepted",
        None,
        None,
        "human",
    )
    .unwrap();
    learning::record_card_reference(&mut conn, "reference-only", &k, None).unwrap();
    let mut reference_only = template();
    reference_only["learning_item_key"] = json!("reference-only");
    create(&mut conn, "ref-only", reference_only);
    learning::record_card_reference(&mut conn, "assessment-only", &k, None).unwrap();
    learning::create_assessment(&mut conn, "assessment-only", &k).unwrap();
    // The assessment remains an actual item even if its old card-reference projection disappears.
    conn.execute(
        "DELETE FROM card_references WHERE item_key='assessment-only'",
        [],
    )
    .unwrap();
    let mut assessment_only = template();
    assessment_only["learning_item_key"] = json!("assessment-only");
    create(&mut conn, "assessment-only", assessment_only);
    assert_eq!(
        conn.query_row("SELECT count(*) FROM learning_events", [], |r| r
            .get::<_, i64>(0))
            .unwrap(),
        0
    );
}
#[test]
fn known_and_extra_unknown_legacy_metadata_is_preserved_read_only_during_body_edits() {
    let (_dir, mut conn) = workspace();
    for (index, raw) in [
        json!({"schema":"legacy/template-x","payload":{"never":"execute","numbers":[1,null]}}),
        {
            let mut v = template();
            v["future_extension"] = json!({"preserve":[true,"原始"]});
            v
        },
    ]
    .into_iter()
    .enumerate()
    {
        let id = format!("legacy-owned-{index}");
        let initial = archived_legacy(&conn, &id, raw.clone());
        let original_hash = initial["content_sha256"].clone();
        let mut body = initial["editor_json"].clone();
        body["content"] = json!([{"type":"paragraph","attrs":{"block_id":"stable"},"content":[{"type":"text","text":"ordinary revised body"}]}]);
        let next = document::save(&mut conn, &id, 1, body.clone()).unwrap();
        assert_eq!(next["editor_json"]["attrs"]["archeaxis_template"], raw);
        assert_eq!(
            document::read(&conn, &id, Some(1)).unwrap()["content_sha256"],
            original_hash
        );
        let before = counts(&conn);
        let mut modified = body.clone();
        modified["attrs"]["archeaxis_template"] = template();
        assert!(document::save(&mut conn, &id, 2, modified).is_err());
        let mut removed = body.clone();
        removed["attrs"]
            .as_object_mut()
            .unwrap()
            .remove("archeaxis_template");
        assert!(document::save(&mut conn, &id, 2, removed).is_err());
        let mut changed = body;
        changed["attrs"]["archeaxis_template"]["schema"] = json!("different-legacy");
        assert!(document::save(&mut conn, &id, 2, changed).is_err());
        assert_eq!(counts(&conn), before);
    }
}
#[test]
fn known_template_namespace_cannot_be_silently_removed_and_wrong_expected_version_keeps_original() {
    let (_dir, mut conn) = workspace();
    let saved = create(&mut conn, "stable-template", template());
    let id = saved["document_id"].as_str().unwrap();
    let mut removed = saved["editor_json"].clone();
    removed["attrs"]
        .as_object_mut()
        .unwrap()
        .remove("archeaxis_template");
    assert!(document::save(&mut conn, id, 1, removed).is_err());
    assert!(matches!(
        document::save(&mut conn, id, 0, saved["editor_json"].clone()),
        Err(document::Error::Conflict(1))
    ));
    assert_eq!(document::read(&conn, id, None).unwrap(), saved);
}
#[test]
fn idempotent_creation_returns_original_normalized_ack_without_rechecking_current_learning_existence()
 {
    let (_dir, mut conn) = workspace();
    learning::record_learning_event(
        &mut conn,
        "bound-item",
        "review",
        r#"{"outcome":"unmeasured"}"#,
        0,
    )
    .unwrap();
    let mut raw = template();
    raw["learning_item_key"] = json!("bound-item");
    let mut payload = editor(raw);
    // The existing codec assigns stable block IDs on create; retry compares normalized v1.
    payload["content"] = json!([{"type":"paragraph","content":[{"type":"text","text":"SYNTHETIC existing sample"}]}]);
    let first = document::create_optional_with_request(
        &mut conn,
        None,
        None,
        "frozen first title",
        payload.clone(),
        Some("frozen-create"),
    )
    .unwrap();
    let id = first["document_id"].as_str().unwrap();
    assert!(
        first["blocks"][0]["block_id"]
            .as_str()
            .unwrap()
            .starts_with("blk_")
    );
    let mut changed = first["editor_json"].clone();
    changed["attrs"]["archeaxis_template"]["fields"] = json!({"note":"later saved v2"});
    document::save(&mut conn, id, 1, changed).unwrap();
    conn.execute(
        "DELETE FROM learning_events WHERE item_key='bound-item'",
        [],
    )
    .unwrap();
    let before = counts(&conn);
    let retry = document::create_optional_with_request(
        &mut conn,
        None,
        None,
        "frozen first title",
        payload.clone(),
        Some("frozen-create"),
    )
    .unwrap();
    assert_eq!(retry, first);
    assert_eq!(counts(&conn), before);
    assert!(
        document::create_optional_with_request(
            &mut conn,
            None,
            None,
            "different title",
            payload,
            Some("frozen-create")
        )
        .is_err()
    );
    let current = document::read(&conn, id, None).unwrap();
    assert_eq!(current["version"], 2);
    assert!(document::save(&mut conn, id, 2, current["editor_json"].clone()).is_err());
    assert_eq!(counts(&conn), before);
}

#[test]
fn existing_unicode_block_identity_is_valid_and_never_replaced_by_a_title_or_ascii_alias() {
    let (_dir, mut conn) = workspace();
    let target=document::create_optional(&mut conn,None,None,"Readable title",json!({"type":"doc","content":[{"type":"paragraph","attrs":{"block_id":"真实 块标识"},"content":[{"type":"text","text":"owned original body"}]}]})).unwrap();
    let id = target["document_id"].as_str().unwrap();
    let mut value = template();
    value["references"] = json!([reference(id, 1, Some("真实 块标识"))]);
    let saved = create(&mut conn, "unicode-block", value);
    assert_eq!(
        saved["editor_json"]["attrs"]["archeaxis_template"]["references"][0]["block_id"],
        "真实 块标识"
    );
    let mut wrong = template();
    wrong["references"] = json!([reference("Readable title", 1, Some("真实 块标识"))]);
    assert!(
        document::create_optional(&mut conn, None, None, "wrong identity", editor(wrong)).is_err()
    );
}

#[test]
fn mathematical_integral_version_is_admitted_without_normalizing_original_reference_payload() {
    let (_dir, mut conn) = workspace();
    let target = document::create_optional(
        &mut conn,
        None,
        None,
        "target",
        json!({"type":"doc","content":[]}),
    )
    .unwrap();
    let id = target["document_id"].as_str().unwrap();
    let mut r = reference(id, 1, None);
    r["version"] = json!(1.0);
    let mut value = template();
    value["references"] = json!([r]);
    let saved = create(&mut conn, "mathematical-version", value.clone());
    assert_eq!(saved["editor_json"]["attrs"]["archeaxis_template"], value);
    let mut invalid = template();
    let mut r = reference(id, 1, None);
    r["version"] = json!(1.5);
    invalid["references"] = json!([r]);
    assert!(
        document::create_optional(&mut conn, None, None, "fractional version", editor(invalid))
            .is_err()
    );
}

#[test]
fn historical_unknown_template_idempotent_initial_ack_remains_compatible_without_a_new_write() {
    let (_dir, mut conn) = workspace();
    let request = "old-owned-create";
    let id = format!(
        "doc_req_{}",
        hex::encode(Sha256::digest(request.as_bytes()))
    );
    let unknown = json!({"schema":"archeaxis.template/future-old","raw_payload":{"preserve":[null,"原字节语义"]}});
    let initial = archived_legacy(&conn, &id, unknown.clone());
    let before = counts(&conn);
    let retry = document::create_optional_with_request(
        &mut conn,
        None,
        None,
        "SYNTHETIC archived legacy",
        editor(unknown.clone()),
        Some(request),
    )
    .unwrap();
    assert_eq!(retry, initial);
    assert_eq!(counts(&conn), before);
    assert!(
        document::create_optional_with_request(
            &mut conn,
            None,
            None,
            "SYNTHETIC archived legacy",
            editor(template()),
            Some(request)
        )
        .is_err()
    );
    assert_eq!(counts(&conn), before);
}

#[test]
fn unsupported_history_js_number_roundtrip_saves_only_body_and_carries_exact_original_namespace() {
    let (_dir, mut conn) = workspace();
    // Actual Node24 JSON.parse/stringify fixture captured in owned scratch:
    // the stored unknown payload has 1.0 while the browser request has 1.
    let old: Value = serde_json::from_str(
        r#"{"schema":"archeaxis.template/future-old","raw_payload":{"value":1.0}}"#,
    )
    .unwrap();
    let submitted: Value = serde_json::from_str(
        r#"{"schema":"archeaxis.template/future-old","raw_payload":{"value":1}}"#,
    )
    .unwrap();
    assert_ne!(old, submitted);
    let initial = archived_legacy(&conn, "unknown-number-body", old.clone());
    let mut body = initial["editor_json"].clone();
    body["attrs"]["archeaxis_template"] = submitted;
    body["content"] = json!([{"type":"paragraph","attrs":{"block_id":"body"},"content":[{"type":"text","text":"ordinary revised body"}]}]);
    let next = document::save(&mut conn, "unknown-number-body", 1, body).unwrap();
    assert_eq!(next["version"], 2);
    assert_eq!(next["editor_json"]["attrs"]["archeaxis_template"], old);
    assert!(next["editor_json"]["attrs"]["archeaxis_template"]["raw_payload"]["value"].is_f64());
    assert_eq!(
        document::read(&conn, "unknown-number-body", Some(1)).unwrap(),
        initial
    );
    assert_eq!(
        next["blocks"][0]["text_projection"],
        "ordinary revised body"
    );
}

#[test]
fn unsupported_history_nested_safe_number_carry_preserves_opaque_values_but_changes_delete_and_precision_loss_fail()
 {
    let (_dir, mut conn) = workspace();
    let old: Value = serde_json::from_str(r#"{"schema":"archeaxis.template/future-old","raw_payload":{"nested":[1.0,-0.0,9007199254740991.0,1.5],"note":"unchanged"}}"#).unwrap();
    let initial = archived_legacy(&conn, "unknown-number-nested", old.clone());
    let mut carried = initial["editor_json"].clone();
    // Node24 generated this request from the actual serde encode/readback,
    // not from a guessed mathematical MAX literal. serde currently reads the
    // floating MAX spelling as 9007199254740990.0; JS faithfully submits that
    // actual stored value as an integer. Exact Core safety stays unchanged.
    let browser: Value =
        serde_json::from_str(include_str!("fixtures/template-unknown-node-request.json")).unwrap();
    carried["attrs"]["archeaxis_template"] = browser["attrs"]["archeaxis_template"].clone();
    let saved = document::save(&mut conn, "unknown-number-nested", 1, carried).unwrap();
    assert_eq!(saved["editor_json"]["attrs"]["archeaxis_template"], old);
    let before = counts(&conn);
    let mut cases = Vec::new();
    let mut changed = saved["editor_json"].clone();
    changed["attrs"]["archeaxis_template"]["raw_payload"]["note"] = json!("changed");
    cases.push(changed);
    let mut changed = saved["editor_json"].clone();
    changed["attrs"]["archeaxis_template"]["raw_payload"]["nested"][0] = json!(2);
    cases.push(changed);
    let mut changed = saved["editor_json"].clone();
    changed["attrs"]
        .as_object_mut()
        .unwrap()
        .remove("archeaxis_template");
    cases.push(changed);
    let mut changed = saved["editor_json"].clone();
    changed["attrs"]["archeaxis_template"]["raw_payload"]["extra"] = Value::Null;
    cases.push(changed);
    for changed in cases {
        assert!(document::save(&mut conn, "unknown-number-nested", 2, changed).is_err());
        assert_eq!(counts(&conn), before);
        assert_eq!(
            document::read(&conn, "unknown-number-nested", None).unwrap(),
            saved
        );
    }
    // A real whole-payload browser roundtrip loses this unsafe integer. It
    // remains a negative fixture, never hand-preserved inside a positive one.
    let unsafe_old: Value = serde_json::from_str(
        r#"{"schema":"archeaxis.template/future-old","raw_payload":{"large":9007199254740993}}"#,
    )
    .unwrap();
    let unsafe_initial = archived_legacy(&conn, "unknown-number-unsafe", unsafe_old);
    let unsafe_browser: Value = serde_json::from_str(include_str!(
        "fixtures/template-unknown-unsafe-node-request.json"
    ))
    .unwrap();
    let mut changed = unsafe_initial["editor_json"].clone();
    changed["attrs"]["archeaxis_template"] = unsafe_browser["attrs"]["archeaxis_template"].clone();
    assert_ne!(
        changed["attrs"]["archeaxis_template"],
        unsafe_initial["editor_json"]["attrs"]["archeaxis_template"]
    );
    let before = counts(&conn);
    assert!(document::save(&mut conn, "unknown-number-unsafe", 1, changed).is_err());
    assert_eq!(counts(&conn), before);
    assert_eq!(
        document::read(&conn, "unknown-number-unsafe", None).unwrap(),
        unsafe_initial
    );
}
