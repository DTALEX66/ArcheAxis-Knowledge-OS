use archeaxis_domain::{document, knowledge, source, teaching};
use archeaxis_store_sqlite::init_workspace;
use rusqlite::Connection;
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
fn expression() -> Value {
    json!({"schema":"archeaxis.expression/v1","nodes":[{"id":"left","type":"text","x":-20,"y":40,"width":200,"height":80,"text":"原文😀 <script>inert</script>"},{"id":"right","type":"text","x":400,"y":120,"width":200,"height":80,"text":"第二节点"}],"edges":[{"id":"edge","fromNode":"left","toNode":"right","label":"原因"}],"capability_metadata":{"animation":{"status":"NOT_EXECUTED","engine":null}}})
}
fn editor(e: Value) -> Value {
    json!({"type":"doc","attrs":{"archeaxis_expression":e,"other_preserved":{"future":true}},"content":[{"type":"paragraph","content":[{"type":"text","text":"独立表达正文"}]}]})
}
fn create(c: &mut Connection, e: Value) -> Result<Value, document::Error> {
    document::create_optional_with_request(
        c,
        None,
        None,
        "Expression",
        editor(e),
        Some("expression-request"),
    )
}
fn count(c: &Connection, t: &str) -> i64 {
    c.query_row(&format!("SELECT count(*) FROM {t}"), [], |r| r.get(0))
        .unwrap()
}
fn teaching_row(
    kid: &str,
    id: &str,
    kind: teaching::RecordKind,
    parent: Option<&str>,
) -> teaching::TeachingRecord {
    teaching::TeachingRecord {
        schema: teaching::RECORD_SCHEMA.into(),
        record_id: id.into(),
        kind,
        knowledge_id: kid.into(),
        knowledge_version: kid.into(),
        course_id: None,
        parent_id: parent.map(str::to_owned),
        purpose: "表达关联".into(),
        scope: teaching::RecordScope::Personal,
        privacy: teaching::RecordPrivacy::LocalOnly,
        content: "人工准备材料".into(),
        feedback_class: None,
        assessment_id: None,
        rubric_version: None,
        assisted: false,
        producer_kind: teaching::ProducerKind::HumanAuthored,
    }
}
#[test]
fn expression_revision_reopens_exact_geometry_media_and_context_without_mutation() {
    let d = tempfile::tempdir().unwrap();
    let db = d.path().join("core.sqlite");
    let mut c = init_workspace(db.to_str().unwrap()).unwrap();
    let bytes = include_bytes!("../../../tests/fixtures/golden/golden-screenshot-ocr.png");
    let digest = hex::encode(Sha256::digest(bytes));
    let sid = match source::import_source(&mut c, bytes, "wrong-extension.txt", None).unwrap() {
        source::ImportOutcome::Imported { source_id, .. } => source_id,
        _ => panic!("source"),
    };
    let kid = knowledge::create_knowledge(
        &mut c,
        "PERSONAL_DEFINITION",
        "知识原文",
        "accepted",
        None,
        None,
        "human",
    )
    .unwrap();
    teaching::put(
        &mut c,
        &teaching_row(&kid, "req", teaching::RecordKind::Requirement, None),
    )
    .unwrap();
    teaching::put(
        &mut c,
        &teaching_row(
            &kid,
            "proposal",
            teaching::RecordKind::Proposal,
            Some("req"),
        ),
    )
    .unwrap();
    let mut e = expression();
    e["context"] = json!({"knowledge_id":kid,"teaching_record_id":"proposal"});
    e["nodes"].as_array_mut().unwrap().push(json!({"id":"image","type":"media","x":-100,"y":200,"width":100,"height":100,"text":"原件说明","media":{"source_id":sid,"sha256":digest,"media_type":"image/png"}}));
    let first = create(&mut c, e.clone()).unwrap();
    assert_eq!(create(&mut c, e.clone()).unwrap(), first);
    let id = first["document_id"].as_str().unwrap().to_owned();
    e["nodes"][0]["x"] = json!(-300);
    e["edges"][0]["label"] = json!("明确修订");
    let second = document::save(&mut c, &id, 1, editor(e.clone())).unwrap();
    assert_eq!(second["version"], 2);
    drop(c);
    let mut c = init_workspace(db.to_str().unwrap()).unwrap();
    let read = document::read(&c, &id, None).unwrap();
    assert_eq!(read, second);
    assert_eq!(
        document::read(&c, &id, Some(1)).unwrap()["editor_json"],
        first["editor_json"]
    );
    assert_eq!(read["editor_json"]["attrs"]["archeaxis_expression"], e);
    assert!(
        read["text_projection"]
            .as_str()
            .unwrap()
            .contains("原件说明")
    );
    assert!(
        read["text_projection"]
            .as_str()
            .unwrap()
            .contains("明确修订")
    );
    assert_eq!(
        archeaxis_store_sqlite::raw_objects::read(&c, &digest).unwrap(),
        bytes
    );
    assert_eq!(
        c.query_row(
            "SELECT body FROM knowledge WHERE knowledge_id=?1",
            [&kid],
            |r| r.get::<_, String>(0)
        )
        .unwrap(),
        "知识原文"
    );
    teaching::withdraw(
        &mut c,
        &teaching::Withdrawal {
            schema: teaching::WITHDRAWAL_SCHEMA.into(),
            withdrawal_id: "w".into(),
            record_id: "proposal".into(),
            reason: "撤回关联".into(),
        },
    )
    .unwrap();
    assert!(document::save(&mut c, &id, 2, editor(e)).is_err());
    assert_eq!(document::read(&c, &id, None).unwrap(), second);
    assert_eq!(count(&c, "document_versions"), 2);
}
#[test]
fn malformed_expression_creation_is_atomic_and_fails_closed() {
    let mutations: Vec<(&str, Box<dyn Fn(&mut Value)>)> = vec![
        ("unknown", Box::new(|v| v["execute"] = json!("provider"))),
        (
            "schema",
            Box::new(|v| v["schema"] = json!("archeaxis.expression/v999")),
        ),
        (
            "duplicate",
            Box::new(|v| v["nodes"][1]["id"] = json!("left")),
        ),
        (
            "endpoint",
            Box::new(|v| v["edges"][0]["toNode"] = json!("absent")),
        ),
        (
            "coordinate",
            Box::new(|v| v["nodes"][0]["x"] = json!(100001)),
        ),
        ("size", Box::new(|v| v["nodes"][0]["width"] = json!(0))),
        (
            "byte-limit",
            Box::new(|v| v["nodes"][0]["text"] = json!("中".repeat(5462))),
        ),
        (
            "metadata-depth",
            Box::new(|v| v["capability_metadata"] = json!({"a":{"b":{"c":{"d":{"e":1}}}}})),
        ),
        (
            "missing-knowledge",
            Box::new(|v| v["context"] = json!({"knowledge_id":"missing"})),
        ),
        (
            "missing-course",
            Box::new(|v| v["context"] = json!({"course_id":"missing"})),
        ),
        (
            "missing-teaching",
            Box::new(|v| v["context"] = json!({"teaching_record_id":"missing"})),
        ),
    ];
    for (name, mutate) in mutations {
        let d = tempfile::tempdir().unwrap();
        let mut c = init_workspace(d.path().join("invalid.sqlite").to_str().unwrap()).unwrap();
        let mut e = expression();
        mutate(&mut e);
        assert!(create(&mut c, e).is_err(), "{name}");
        assert_eq!(count(&c, "documents"), 0, "{name}");
        assert_eq!(count(&c, "document_versions"), 0, "{name}");
    }
}
#[test]
fn media_bytes_and_type_are_bound_to_cas_not_filename() {
    let d = tempfile::tempdir().unwrap();
    let mut c = init_workspace(d.path().join("core.sqlite").to_str().unwrap()).unwrap();
    let bytes = b"<svg onload='do-not-run'>inert unknown source</svg>";
    let hash = hex::encode(Sha256::digest(bytes));
    let sid = match source::import_source(&mut c, bytes, "pretend.png", None).unwrap() {
        source::ImportOutcome::Imported { source_id, .. } => source_id,
        _ => panic!(),
    };
    let mut e = expression();
    e["nodes"][0]["type"] = json!("media");
    e["nodes"][0]["media"] = json!({"source_id":sid,"sha256":hash,"media_type":"image/png"});
    assert!(create(&mut c, e.clone()).is_err());
    assert_eq!(count(&c, "documents"), 0);
    e["nodes"][0]["media"]["sha256"] = json!("a".repeat(64));
    assert!(create(&mut c, e).is_err());
    assert_eq!(count(&c, "document_versions"), 0);
}
#[test]
fn historical_unknown_expression_is_readable_but_cannot_be_newly_written() {
    let d = tempfile::tempdir().unwrap();
    let mut c = init_workspace(d.path().join("core.sqlite").to_str().unwrap()).unwrap();
    let first = create(&mut c, expression()).unwrap();
    let id = first["document_id"].as_str().unwrap();
    let old = editor(
        json!({"schema":"archeaxis.expression/legacy-unknown","original_payload":{"preserved":true}}),
    );
    let encoded = old.to_string();
    let checksum = hex::encode(Sha256::digest(encoded.as_bytes()));
    // Fixture raw historical row: simulate a pre-validation persisted unknown schema; no read-path rewrite.
    c.execute("UPDATE document_versions SET editor_json=?1,content_sha256=?2 WHERE document_id=?3 AND version=1",rusqlite::params![encoded,checksum,id]).unwrap();
    assert_eq!(document::read(&c, id, Some(1)).unwrap()["editor_json"], old);
    assert!(document::save(&mut c, id, 1, old.clone()).is_err());
    assert_eq!(document::read(&c, id, None).unwrap()["editor_json"], old);
    assert_eq!(count(&c, "document_versions"), 1);
}
#[test]
fn context_cannot_substitute_teaching_kind_knowledge_or_course() {
    let d = tempfile::tempdir().unwrap();
    let mut c = init_workspace(d.path().join("core.sqlite").to_str().unwrap()).unwrap();
    let one = knowledge::create_knowledge(
        &mut c,
        "PERSONAL_DEFINITION",
        "one",
        "accepted",
        None,
        None,
        "human",
    )
    .unwrap();
    let two = knowledge::create_knowledge(
        &mut c,
        "PERSONAL_DEFINITION",
        "two",
        "accepted",
        None,
        None,
        "human",
    )
    .unwrap();
    teaching::put(
        &mut c,
        &teaching_row(&one, "req", teaching::RecordKind::Requirement, None),
    )
    .unwrap();
    teaching::put(
        &mut c,
        &teaching_row(&one, "prop", teaching::RecordKind::Proposal, Some("req")),
    )
    .unwrap();
    let mut e = expression();
    e["context"] = json!({"teaching_record_id":"req"});
    assert!(create(&mut c, e.clone()).is_err());
    e["context"] = json!({"knowledge_id":two,"teaching_record_id":"prop"});
    assert!(create(&mut c, e.clone()).is_err());
    e["context"] =
        json!({"knowledge_id":one,"teaching_record_id":"prop","course_id":"nonexistent-course"});
    assert!(create(&mut c, e.clone()).is_err());
    assert_eq!(count(&c, "documents"), 0);
    e["context"] = json!({"knowledge_id":one,"teaching_record_id":"prop"});
    assert!(create(&mut c, e).is_ok());
}
#[test]
fn stale_revision_and_missing_media_preserve_saved_expression() {
    let d = tempfile::tempdir().unwrap();
    let mut c = init_workspace(d.path().join("core.sqlite").to_str().unwrap()).unwrap();
    let first = create(&mut c, expression()).unwrap();
    let id = first["document_id"].as_str().unwrap();
    let mut e = expression();
    e["nodes"][0]["x"] = json!(50);
    let second = document::save(&mut c, id, 1, editor(e.clone())).unwrap();
    assert!(document::save(&mut c, id, 1, editor(e.clone())).is_err());
    e["nodes"][0]["type"] = json!("media");
    e["nodes"][0]["media"] =
        json!({"source_id":"missing","sha256":"a".repeat(64),"media_type":"image/png"});
    assert!(document::save(&mut c, id, 2, editor(e)).is_err());
    assert_eq!(document::read(&c, id, None).unwrap(), second);
    assert_eq!(count(&c, "document_versions"), 2);
}
fn bound_knowledge(c: &mut Connection, name: &str) -> String {
    let bytes = format!("Canonical evidence {name}");
    let sid =
        match source::import_source(c, bytes.as_bytes(), &format!("{name}.txt"), None).unwrap() {
            source::ImportOutcome::Imported { source_id, .. } => source_id,
            _ => panic!(),
        };
    let rev: String = c
        .query_row(
            "SELECT sha256 FROM sources WHERE source_id=?1",
            [&sid],
            |r| r.get(0),
        )
        .unwrap();
    let aid = archeaxis_domain::anchor::add_anchor(c, &sid, &rev, r#"{"line":1}"#).unwrap();
    knowledge::create_knowledge(
        c,
        "FACTUAL_CLAIM",
        name,
        "accepted",
        None,
        Some(&aid),
        "human",
    )
    .unwrap()
}
fn bound_course(c: &mut Connection, kid: &str, id: &str) {
    let(sid,rev):(String,String)=c.query_row("SELECT a.source_id,a.source_revision FROM knowledge k JOIN anchors a ON a.anchor_id=k.anchor_id WHERE k.knowledge_id=?1",[kid],|r|Ok((r.get(0)?,r.get(1)?))).unwrap();
    let m = json!({"schema":"archeaxis.course-manifest/v1","manifest_id":id,"title":"Expression fixture course","domain_pack_id":"general","status":"candidate","knowledge_components":[{"schema":"archeaxis.knowledge-component/v1","component_id":"kc","kind":"concept","title":"Fixture","statement":"Evidence","source_ids":[sid],"prerequisite_ids":[]}],"learning_objectives":[{"schema":"archeaxis.learning-objective/v1","objective_id":"obj","title":"Explain","statement":"Explain","knowledge_component_ids":["kc"]}],"artifacts":[{"schema":"archeaxis.courseware-artifact/v1","artifact_id":format!("lesson-{id}"),"artifact_type":"lesson","title":"Fixture","domain_pack_id":"general","source_ids":[sid],"knowledge_ids":["kc"],"renderer":"native-lesson","renderer_version":"1.0.0","status":"candidate","interactive":false,"derived_only":true,"human_review_required":true}]});
    archeaxis_domain::course::create_candidate(
        c,
        &m,
        &[archeaxis_domain::course::CourseBinding {
            component_id: "kc".into(),
            knowledge_id: kid.into(),
            knowledge_version: kid.into(),
            source_id: sid,
            source_revision: rev,
        }],
    )
    .unwrap();
}
#[test]
fn pre_course_proposal_can_link_later_same_knowledge_course_without_mutating_proposal() {
    let d = tempfile::tempdir().unwrap();
    let mut c = init_workspace(d.path().join("core.sqlite").to_str().unwrap()).unwrap();
    let one = bound_knowledge(&mut c, "one");
    let two = bound_knowledge(&mut c, "two");
    teaching::put(
        &mut c,
        &teaching_row(&one, "req", teaching::RecordKind::Requirement, None),
    )
    .unwrap();
    let proposal = teaching_row(&one, "prop", teaching::RecordKind::Proposal, Some("req"));
    teaching::put(&mut c, &proposal).unwrap();
    bound_course(&mut c, &one, "course-one");
    bound_course(&mut c, &two, "course-two");
    bound_course(&mut c, &one, "other-one-course");
    let mut e = expression();
    e["context"] = json!({"knowledge_id":one,"course_id":"course-one","teaching_record_id":"prop"});
    let first = create(&mut c, e.clone()).unwrap();
    let id = first["document_id"].as_str().unwrap();
    assert_eq!(teaching::get(&c, "prop").unwrap().unwrap().record, proposal);
    assert!(proposal.course_id.is_none());
    e["context"] = json!({"course_id":"course-two","teaching_record_id":"prop"});
    assert!(document::save(&mut c, id, 1, editor(e.clone())).is_err());
    e["context"] = json!({"knowledge_id":two,"course_id":"course-two","teaching_record_id":"prop"});
    assert!(document::save(&mut c, id, 1, editor(e.clone())).is_err());
    let mut r = teaching_row(&one, "bound-req", teaching::RecordKind::Requirement, None);
    r.course_id = Some("other-one-course".into());
    teaching::put(&mut c, &r).unwrap();
    let mut p = teaching_row(
        &one,
        "bound-prop",
        teaching::RecordKind::Proposal,
        Some("bound-req"),
    );
    p.course_id = Some("other-one-course".into());
    teaching::put(&mut c, &p).unwrap();
    e["context"] =
        json!({"knowledge_id":one,"course_id":"course-one","teaching_record_id":"bound-prop"});
    assert!(document::save(&mut c, id, 1, editor(e)).is_err());
    assert_eq!(count(&c, "document_versions"), 1);
    assert_eq!(document::read(&c, id, None).unwrap(), first);
}
#[test]
fn expression_caption_and_edge_projection_preserves_order_and_plain_documents() {
    let d = tempfile::tempdir().unwrap();
    let mut c = init_workspace(d.path().join("core.sqlite").to_str().unwrap()).unwrap();
    let e = expression();
    let doc = create(&mut c, e.clone()).unwrap();
    assert_eq!(
        doc["text_projection"],
        "独立表达正文\n原文😀 <script>inert</script>\n第二节点\n原因"
    );
    assert_eq!(doc["editor_json"]["attrs"]["archeaxis_expression"], e);
    let ordinary = json!({"type":"doc","attrs":{"unrelated":{"text":"do not project"}},"content":[{"type":"paragraph","content":[{"type":"text","text":" ordinary exact "}]}]});
    let plain = document::create_optional(&mut c, None, None, "Plain", ordinary).unwrap();
    assert_eq!(plain["text_projection"], " ordinary exact ");
    assert_eq!(
        archeaxis_domain::expression::text_projection(&editor(
            json!({"schema":"future","nodes":[{"text":"unknown semantics"}]})
        )),
        None
    );
}
