//! One knowledge revision must be reported consistently by every projection that
//! carries reference state: the resolver, the relation projection, the learning
//! card reference, the AI asset packet and the course binding. A successor is
//! named, never substituted, and the historical identity is never rewritten.

use archeaxis_domain::{
    ai_asset, anchor,
    course::{self, CourseBinding},
    document, knowledge, learning,
    machine_evaluation::{self, Criterion, Rubric},
    object_reference::{self, Reference},
    relation_projection,
    source::{self, ImportOutcome},
};
use archeaxis_store_sqlite::init_workspace;
use rusqlite::Connection;
use serde_json::{Value, json};

fn relation_envelope(target: &str) -> Value {
    json!({"type":"doc","content":[],"attrs":{"archeaxis_relations":{"schema":"archeaxis.relations/v1",
        "relations":[{"id":"rel-1","kind":"supports","label":"依据",
        "target":{"kind":"knowledge","knowledge_id":target}}]}}})
}

fn seed_anchored_knowledge(conn: &mut Connection) -> String {
    let source_id = match source::import_source(
        conn,
        b"An anchor locates evidence.",
        "cross-consumer.md",
        None,
    )
    .unwrap()
    {
        ImportOutcome::Imported { source_id, .. } => source_id,
        _ => unreachable!(),
    };
    let revision: String = conn
        .query_row(
            "SELECT sha256 FROM sources WHERE source_id=?1",
            [&source_id],
            |r| r.get(0),
        )
        .unwrap();
    let anchor_id = anchor::add_anchor(conn, &source_id, &revision, r#"{"line":1}"#).unwrap();
    knowledge::create_knowledge(
        conn,
        "FACTUAL_CLAIM",
        "An anchor locates evidence.",
        "accepted",
        None,
        Some(&anchor_id),
        "human",
    )
    .unwrap()
}

fn create_relation_document(conn: &mut Connection, target: &str) -> String {
    document::create_optional(conn, None, None, "关系来源", relation_envelope(target)).unwrap()
        ["document_id"]
        .as_str()
        .unwrap()
        .to_owned()
}

fn create_adopted_asset(conn: &mut Connection, target: &str) -> Value {
    let candidate = document::create_optional_with_request(
        conn,
        None,
        None,
        "owned asset",
        json!({"type":"doc","content":[],"attrs":{"archeaxis_ai_asset":{
            "schema":"archeaxis.ai-asset/v1","kind":"rule",
            "content":"SYNTHETIC rule","purpose":"owned purpose",
            "scope":[],"provenance":[{"kind":"knowledge","knowledge_id":target}],
            "expires_at":null,"state":"candidate","members":[],"conflicts":[],
            "revises":null,"review":null,"source_payload":null}}}),
        Some("cross-consumer-asset"),
    )
    .unwrap();
    let rubric = machine_evaluation::create_rubric(
        conn,
        "human",
        &Rubric {
            schema: machine_evaluation::RUBRIC_SCHEMA.into(),
            request_id: "cross-consumer-rubric".into(),
            title: "fixed rubric".into(),
            purpose: "owned purpose".into(),
            sources: vec![],
            criteria: vec![Criterion {
                criterion_id: "fit".into(),
                label: "fit".into(),
                expectation: "owned observed fit".into(),
            }],
        },
    )
    .unwrap();
    let mut editor = candidate["editor_json"].clone();
    editor["attrs"]["archeaxis_ai_asset"]["state"] = json!("adopted");
    editor["attrs"]["archeaxis_ai_asset"]["review"] = json!({
        "asset": ai_asset::snapshot(&candidate).unwrap(),
        "rubric": ai_asset::snapshot(&rubric).unwrap(),
        "reviewer": "owner annotation",
        "basis": "SYNTHETIC observed criterion",
        "judgments": [{"criterion_id":"fit","basis":"observed fit","outcome":"passed"}],
        "outcome": "passed"
    });
    document::save(conn, candidate["document_id"].as_str().unwrap(), 1, editor).unwrap()
}

fn create_course(conn: &mut Connection, target: &str) -> String {
    let source_id: String = conn
        .query_row(
            "SELECT source_id FROM anchors a JOIN knowledge k ON k.anchor_id=a.anchor_id WHERE k.knowledge_id=?1",
            [target],
            |r| r.get(0),
        )
        .unwrap();
    let revision: String = conn
        .query_row(
            "SELECT sha256 FROM sources WHERE source_id=?1",
            [&source_id],
            |r| r.get(0),
        )
        .unwrap();
    let manifest = json!({"schema":"archeaxis.course-manifest/v1","manifest_id":"course-cross",
        "title":"Evidence","domain_pack_id":"general","status":"candidate",
        "knowledge_components":[{"component_id":"kc-1","kind":"fact","title":"Anchor",
            "statement":"An anchor locates evidence.","source_ids":[source_id],
            "prerequisite_ids":[]}],
        "learning_objectives":[{"objective_id":"obj-1","title":"Find evidence",
            "statement":"Locate an anchor.","knowledge_component_ids":["kc-1"]}],
        "artifacts":[{"schema":"archeaxis.courseware-artifact/v1","artifact_id":"lesson-1",
            "artifact_type":"lesson","title":"Evidence lesson","domain_pack_id":"general",
            "source_ids":[source_id],"knowledge_ids":["kc-1"],"renderer":"native-lesson",
            "renderer_version":"1.0.0","status":"candidate","interactive":false,
            "derived_only":true,"human_review_required":true}]});
    let binding = CourseBinding {
        component_id: "kc-1".into(),
        knowledge_id: target.into(),
        knowledge_version: target.into(),
        source_id,
        source_revision: revision,
    };
    course::create_candidate(conn, &manifest, &[binding]).unwrap();
    "course-cross".to_owned()
}

fn relation_state(conn: &Connection, document_id: &str) -> Value {
    let projection = relation_projection::query(conn, document_id, Some(1), None).unwrap();
    projection["nodes"]
        .as_array()
        .unwrap()
        .iter()
        .find(|node| node["reference"]["kind"] == "knowledge")
        .expect("knowledge node")
        .clone()
}

fn asset_state(conn: &Connection, asset: &Value) -> Value {
    let items = ai_asset::packet_items(conn, &ai_asset::snapshot(asset).unwrap(), 1).unwrap();
    items[0]["reference_states"][0].clone()
}

fn course_state(conn: &Connection) -> Value {
    course::read_candidate(conn, "course-cross")
        .unwrap()
        .unwrap()["bindings"][0]["knowledge_state"]
        .clone()
}

#[test]
fn one_revision_is_reported_consistently_by_every_reference_projection() {
    let dir = tempfile::tempdir().unwrap();
    let mut conn = init_workspace(dir.path().join("cross.sqlite").to_str().unwrap()).unwrap();
    let kid = seed_anchored_knowledge(&mut conn);
    let relation_doc = create_relation_document(&mut conn, &kid);
    let asset = create_adopted_asset(&mut conn, &kid);
    let course_id = create_course(&mut conn, &kid);
    assert_eq!(course_id, "course-cross");
    learning::record_card_reference(&mut conn, "card-cross", &kid, None).unwrap();

    // Before the revision: every projection reports the same current state.
    let resolved = object_reference::resolve(
        &conn,
        &Reference::Knowledge {
            knowledge_id: kid.clone(),
        },
    )
    .unwrap();
    assert_eq!(resolved["currentness"], "current");
    assert_eq!(resolved["identity"], "immutable_knowledge_id");
    assert_eq!(
        relation_state(&conn, &relation_doc)["currentness"],
        "current"
    );
    assert_eq!(asset_state(&conn, &asset)["currentness"], "current");
    assert_eq!(course_state(&conn)["currentness"], "current");
    assert_eq!(
        learning::references_for_card(&conn, "card-cross").unwrap(),
        vec![(kid.clone(), true)]
    );

    // One reviewed correction creates a successor. Every consumer must now say
    // superseded and name the successor; none may rewrite the historical id.
    let successor = knowledge::review(
        &mut conn,
        &kid,
        "modified",
        "owner",
        Some("fixed synthetic statement"),
        Some("An anchor locates evidence."),
    )
    .unwrap();
    let resolved = object_reference::resolve(
        &conn,
        &Reference::Knowledge {
            knowledge_id: kid.clone(),
        },
    )
    .unwrap();
    assert_eq!(resolved["currentness"], "superseded");
    assert_eq!(resolved["superseded_by"], json!(successor));
    assert_eq!(resolved["reference"]["knowledge_id"], kid);

    let relation = relation_state(&conn, &relation_doc);
    assert_eq!(relation["currentness"], "superseded");
    assert_eq!(relation["object"]["superseded_by"], json!(successor));
    assert_eq!(relation["reference"]["knowledge_id"], kid);

    let asset = asset_state(&conn, &asset);
    assert_eq!(asset["currentness"], "superseded");
    assert_eq!(asset["superseded_by"], json!(successor));
    assert_eq!(asset["reference"]["knowledge_id"], kid);

    let course = course_state(&conn);
    assert_eq!(course["currentness"], "superseded");
    assert_eq!(course["superseded_by"], json!(successor));

    let card = learning::references_for_card(&conn, "card-cross").unwrap();
    assert_eq!(card.len(), 1);
    assert_eq!(
        card[0].0, kid,
        "the learning card keeps its original identity"
    );
    assert_eq!(card[0].1, false, "the superseded revision is not current");
}
