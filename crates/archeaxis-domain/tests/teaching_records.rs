use archeaxis_domain::{
    anchor,
    course::{self, CourseBinding},
    knowledge, learning,
    source::{self, ImportOutcome},
    teaching::*,
};
use archeaxis_store_sqlite::init_workspace;
use rusqlite::Connection;
use serde_json::json;
struct Fixture {
    conn: Connection,
    _dir: Option<tempfile::TempDir>,
}
impl std::ops::Deref for Fixture {
    type Target = Connection;
    fn deref(&self) -> &Connection {
        &self.conn
    }
}
impl std::ops::DerefMut for Fixture {
    fn deref_mut(&mut self) -> &mut Connection {
        &mut self.conn
    }
}
fn open(path: &str) -> Fixture {
    // Canonical workspace owns filesystem locking; use an isolated real SQLite file, not :memory:.
    let dir = if path == ":memory:" {
        Some(tempfile::tempdir().unwrap())
    } else {
        None
    };
    let actual = dir.as_ref().map(|d| d.path().join("fixture.sqlite"));
    let name = actual.as_ref().and_then(|p| p.to_str()).unwrap_or(path);
    Fixture {
        conn: init_workspace(name).unwrap(),
        _dir: dir,
    }
}
fn knowledge_fixture(conn: &mut Connection, name: &str) -> String {
    let sid =
        match source::import_source(conn, name.as_bytes(), &format!("{name}.md"), None).unwrap() {
            ImportOutcome::Imported { source_id, .. } => source_id,
            _ => unreachable!(),
        };
    let revision: String = conn
        .query_row(
            "SELECT sha256 FROM sources WHERE source_id=?1",
            [&sid],
            |r| r.get(0),
        )
        .unwrap();
    let aid = anchor::add_anchor(conn, &sid, &revision, r#"{"line":1}"#).unwrap();
    knowledge::create_knowledge(
        conn,
        "FACTUAL_CLAIM",
        name,
        "accepted",
        None,
        Some(&aid),
        "human",
    )
    .unwrap()
}
fn row(kind: RecordKind, id: &str, parent: Option<&str>, kid: &str) -> TeachingRecord {
    TeachingRecord {
        schema: RECORD_SCHEMA.into(),
        record_id: id.into(),
        kind,
        knowledge_id: kid.into(),
        knowledge_version: kid.into(),
        course_id: None,
        parent_id: parent.map(str::to_owned),
        purpose: "人工教学交换与复述".into(),
        scope: RecordScope::ManualExchange,
        privacy: RecordPrivacy::AuthorizedExport,
        content: "中文原文 <script>inert</script> 与未知含义保留。".into(),
        feedback_class: None,
        assessment_id: None,
        rubric_version: None,
        assisted: false,
        producer_kind: ProducerKind::HumanAuthored,
    }
}
fn chain(conn: &mut Connection, kid: &str) -> Vec<TeachingRecord> {
    let rows = vec![
        row(RecordKind::Observation, "obs", None, kid),
        row(RecordKind::Requirement, "req", Some("obs"), kid),
        row(RecordKind::Proposal, "prop", Some("req"), kid),
        row(RecordKind::Delivery, "delivery", Some("prop"), kid),
        row(RecordKind::TeachBack, "tb", Some("delivery"), kid),
        row(RecordKind::Feedback, "feedback", Some("delivery"), kid),
        row(RecordKind::Revision, "revision", Some("feedback"), kid),
    ];
    for r in &rows {
        put(conn, r).unwrap();
    }
    rows
}
fn count(conn: &Connection) -> i64 {
    conn.query_row("SELECT COUNT(*) FROM teaching_records", [], |r| r.get(0))
        .unwrap()
}
fn bundle(records: Vec<TeachingRecord>) -> ExchangeBundle {
    ExchangeBundle {
        schema: EXCHANGE_SCHEMA.into(),
        package_sha256: package_hash(&records).unwrap(),
        records,
    }
}
fn course_fixture(conn: &mut Connection, kid: &str, id: &str) -> String {
    let (sid,revision):(String,String)=conn.query_row("SELECT a.source_id,a.source_revision FROM knowledge k JOIN anchors a ON a.anchor_id=k.anchor_id WHERE k.knowledge_id=?1",[kid],|r|Ok((r.get(0)?,r.get(1)?))).unwrap();
    let manifest = json!({"schema":"archeaxis.course-manifest/v1","manifest_id":id,"title":"Fixture lesson","domain_pack_id":"general","status":"candidate",
 "knowledge_components":[{"schema":"archeaxis.knowledge-component/v1","component_id":"kc1","kind":"concept","title":"Fixture","statement":"Fixture source","source_ids":[sid],"prerequisite_ids":[]}],
 "learning_objectives":[{"schema":"archeaxis.learning-objective/v1","objective_id":"obj1","title":"Explain","statement":"Explain fixture","knowledge_component_ids":["kc1"]}],
 "artifacts":[{"schema":"archeaxis.courseware-artifact/v1","artifact_id":format!("lesson-{id}"),"artifact_type":"lesson","title":"Fixture","domain_pack_id":"general","source_ids":[sid],"knowledge_ids":["kc1"],"renderer":"native-lesson","renderer_version":"1.0.0","status":"candidate","interactive":false,"derived_only":true,"human_review_required":true}]});
    course::create_candidate(
        conn,
        &manifest,
        &[CourseBinding {
            component_id: "kc1".into(),
            knowledge_id: kid.into(),
            knowledge_version: kid.into(),
            source_id: sid,
            source_revision: revision,
        }],
    )
    .unwrap();
    id.into()
}
#[test]
fn duplicate_conflict_and_database_triggers_preserve_exact_original() {
    let mut conn = open(":memory:");
    let kid = knowledge_fixture(&mut conn, "one");
    let r = row(RecordKind::Observation, "o", None, &kid);
    let first = put(&mut conn, &r).unwrap();
    assert!(!first.duplicate);
    assert_eq!(first.item.scoring_status, "not_scored");
    let replay = put(&mut conn, &r).unwrap();
    assert!(replay.duplicate);
    assert_eq!(replay.item, first.item);
    let mut changed = r.clone();
    changed.content.push(' ');
    assert!(matches!(
        put(&mut conn, &changed),
        Err(TeachingError::Conflict(_))
    ));
    assert!(
        conn.execute("UPDATE teaching_records SET record_json='{}'", [])
            .is_err()
    );
    assert!(conn.execute("DELETE FROM teaching_records", []).is_err());
    assert_eq!(get(&conn, "o").unwrap().unwrap(), first.item);
    assert_eq!(count(&conn), 1);
}
#[test]
fn strict_dto_rejects_actor_paths_unknown_fields_and_enum_claims() {
    let mut conn = open(":memory:");
    let kid = knowledge_fixture(&mut conn, "one");
    let r = row(RecordKind::Requirement, "r", None, &kid);
    for field in ["actor", "verified", "truth", "path", "provider", "mastery"] {
        let mut v = serde_json::to_value(&r).unwrap();
        v[field] = json!("human");
        assert!(serde_json::from_value::<TeachingRecord>(v).is_err());
    }
    let mut v = serde_json::to_value(&r).unwrap();
    v["producer_kind"] = json!("privileged_actor");
    assert!(serde_json::from_value::<TeachingRecord>(v).is_err());
    let mut bad = r.clone();
    bad.record_id = "../private".into();
    assert!(put(&mut conn, &bad).is_err());
    bad = r.clone();
    bad.content = " ".into();
    assert!(put(&mut conn, &bad).is_err());
    bad = r.clone();
    bad.content = "中".repeat(22000);
    assert!(put(&mut conn, &bad).is_err());
    bad = r.clone();
    bad.knowledge_version = "review-hash".into();
    assert!(put(&mut conn, &bad).is_err());
    assert_eq!(count(&conn), 0);
    let mut envelope = serde_json::to_value(bundle(vec![r.clone()])).unwrap();
    envelope["file_path"] = json!("C:/secret");
    assert!(serde_json::from_value::<ExchangeBundle>(envelope).is_err());
    let withdrawal = json!({"schema":WITHDRAWAL_SCHEMA,"withdrawal_id":"w","record_id":"r","reason":"reason","actor":"human"});
    assert!(serde_json::from_value::<Withdrawal>(withdrawal).is_err());
}
#[test]
fn lineage_rules_reject_missing_parent_wrong_kind_and_self_parent() {
    let mut conn = open(":memory:");
    let kid = knowledge_fixture(&mut conn, "one");
    assert!(put(&mut conn, &row(RecordKind::Proposal, "p", None, &kid)).is_err());
    assert!(matches!(
        put(
            &mut conn,
            &row(RecordKind::Requirement, "r", Some("missing"), &kid)
        ),
        Err(TeachingError::NotFound(_))
    ));
    assert!(
        put(
            &mut conn,
            &row(RecordKind::Observation, "o", Some("o"), &kid)
        )
        .is_err()
    );
    let rows = chain(&mut conn, &kid);
    assert!(
        put(
            &mut conn,
            &row(RecordKind::Proposal, "bad", Some("delivery"), &kid)
        )
        .is_err()
    );
    let other = knowledge_fixture(&mut conn, "other");
    assert!(
        put(
            &mut conn,
            &row(RecordKind::Feedback, "mixed", Some("delivery"), &other)
        )
        .is_err()
    );
    assert_eq!(count(&conn), rows.len() as i64);
}
#[test]
fn real_course_and_assessment_bindings_are_verified_without_fsrs_mutation() {
    let mut conn = open(":memory:");
    let kid = knowledge_fixture(&mut conn, "one");
    let other = knowledge_fixture(&mut conn, "other");
    let cid = course_fixture(&mut conn, &kid, "course-one");
    for mut record in [row(RecordKind::Requirement, "req", None, &kid),
        row(RecordKind::Proposal, "prop", Some("req"), &kid),
        row(RecordKind::Delivery, "delivery", Some("prop"), &kid)] {
        if record.kind == RecordKind::Delivery {record.course_id = Some(cid.clone());}
        put(&mut conn, &record).unwrap();
    }
    let wrong = course_fixture(&mut conn, &other, "course-other");
    let key = format!("course:{cid}:artifact:lesson-{cid}");
    learning::record_card_reference(&mut conn, &key, &kid, None).unwrap();
    let a = learning::create_assessment(&mut conn, &key, &kid).unwrap();
    let mut t = row(RecordKind::TeachBack, "attempt", Some("delivery"), &kid);
    t.course_id = Some(cid.clone());
    t.assessment_id = Some(a.assessment_id.clone());
    t.assisted = true;
    t.producer_kind = ProducerKind::ExternalMaterial;
    put(&mut conn, &t).unwrap();
    assert_eq!(get(&conn, "attempt").unwrap().unwrap().record, t);
    t.record_id = "wrong-course".into();
    t.course_id = Some(wrong);
    assert!(put(&mut conn, &t).is_err());
    t.record_id = "missing-assessment".into();
    t.course_id = Some(cid.clone());
    t.assessment_id = Some("nonexistent".into());
    assert!(matches!(
        put(&mut conn, &t),
        Err(TeachingError::NotFound(_))
    ));
    let before = course::read_candidate(&conn, &cid).unwrap().unwrap();
    conn.execute("UPDATE sources SET sha256=sha256||'.changed'", [])
        .unwrap();
    let mut d = row(RecordKind::Delivery, "stale-delivery", Some("prop"), &kid);
    d.course_id = Some(cid.clone());
    assert!(matches!(
        put(&mut conn, &d),
        Err(TeachingError::Conflict(_))
    ));
    assert_eq!(
        course::read_candidate(&conn, &cid).unwrap().unwrap()["manifest"],
        before["manifest"]
    );
    let event_count: i64 = conn
        .query_row("SELECT COUNT(*) FROM learning_events", [], |r| r.get(0))
        .unwrap();
    assert_eq!(event_count, 0);
}
#[test]
fn withdrawal_is_append_only_idempotent_and_propagates_without_revival() {
    let mut conn = open(":memory:");
    let kid = knowledge_fixture(&mut conn, "one");
    let rows = chain(&mut conn, &kid);
    let saved = get(&conn, "delivery").unwrap().unwrap();
    let exported = export_bundle(&conn, "tb").unwrap();
    let w = Withdrawal {
        schema: WITHDRAWAL_SCHEMA.into(),
        withdrawal_id: "withdraw-req".into(),
        record_id: "req".into(),
        reason: "撤回授权".into(),
    };
    let first = withdraw(&mut conn, &w).unwrap();
    assert!(!first.duplicate);
    assert!(first.affected_record_ids.contains(&"tb".to_owned()));
    assert!(withdraw(&mut conn, &w).unwrap().duplicate);
    let mut changed = w.clone();
    changed.reason = "different".into();
    assert!(matches!(
        withdraw(&mut conn, &changed),
        Err(TeachingError::Conflict(_))
    ));
    assert!(
        conn.execute("DELETE FROM teaching_withdrawals", [])
            .is_err()
    );
    let after = get(&conn, "delivery").unwrap().unwrap();
    assert!(after.withdrawn);
    assert_eq!(after.record, saved.record);
    assert_eq!(after.content_sha256, saved.content_sha256);
    assert!(!get(&conn, "obs").unwrap().unwrap().withdrawn);
    assert!(matches!(
        export_bundle(&conn, "tb"),
        Err(TeachingError::Withdrawn(_))
    ));
    assert!(matches!(
        put(
            &mut conn,
            &row(RecordKind::Proposal, "new", Some("req"), &kid)
        ),
        Err(TeachingError::Withdrawn(_))
    ));
    let replay = import_bundle(&mut conn, &exported).unwrap();
    assert_eq!(replay.duplicate_count, exported.records.len());
    assert!(replay.items.last().unwrap().withdrawn);
    assert_eq!(count(&conn), rows.len() as i64);
    let mut newer = exported.records.clone();
    newer.push(row(RecordKind::TeachBack, "new-tb", Some("delivery"), &kid));
    assert!(matches!(
        preview_import(&conn, &bundle(newer)),
        Err(TeachingError::Withdrawn(_))
    ));
}
#[test]
fn export_includes_ancestors_and_refuses_local_only_ancestor() {
    let mut conn = open(":memory:");
    let kid = knowledge_fixture(&mut conn, "one");
    chain(&mut conn, &kid);
    let b = export_bundle(&conn, "delivery").unwrap();
    assert_eq!(
        b.records
            .iter()
            .map(|r| r.record_id.as_str())
            .collect::<Vec<_>>(),
        vec!["obs", "req", "prop", "delivery"]
    );
    assert_eq!(b.package_sha256, package_hash(&b.records).unwrap());
    let mut root = row(RecordKind::Requirement, "private-root", None, &kid);
    root.privacy = RecordPrivacy::LocalOnly;
    put(&mut conn, &root).unwrap();
    put(
        &mut conn,
        &row(
            RecordKind::Proposal,
            "export-child",
            Some("private-root"),
            &kid,
        ),
    )
    .unwrap();
    assert!(matches!(
        export_bundle(&conn, "export-child"),
        Err(TeachingError::Conflict(_))
    ));
}
#[test]
fn import_preview_is_read_only_all_refs_checked_and_topology_order_independent() {
    let mut conn = open(":memory:");
    let kid = knowledge_fixture(&mut conn, "one");
    let r = row(RecordKind::Requirement, "r", None, &kid);
    let p = row(RecordKind::Proposal, "p", Some("r"), &kid);
    let b = bundle(vec![p, r]);
    let preview = preview_import(&conn, &b).unwrap();
    assert!(preview.valid);
    assert_eq!(preview.record_count, 2);
    assert_eq!(preview.duplicate_count, 0);
    assert_eq!(count(&conn), 0);
    let imported = import_bundle(&mut conn, &b).unwrap();
    assert_eq!(imported.duplicate_count, 0);
    assert_eq!(imported.items.len(), 2);
    assert_eq!(count(&conn), 2);
    assert_eq!(preview_import(&conn, &b).unwrap().duplicate_count, 2);
    assert_eq!(import_bundle(&mut conn, &b).unwrap().duplicate_count, 2);
    let mut broken = b.clone();
    broken.package_sha256 = "0".repeat(64);
    assert!(preview_import(&conn, &broken).is_err());
    assert!(import_bundle(&mut conn, &broken).is_err());
    assert_eq!(count(&conn), 2);
}
#[test]
fn import_late_invalid_reference_and_conflict_leave_no_partial_rows() {
    let mut conn = open(":memory:");
    let kid = knowledge_fixture(&mut conn, "one");
    let good = row(RecordKind::Observation, "good", None, &kid);
    let missing = row(RecordKind::Observation, "missing", None, "k_nonexistent");
    assert!(matches!(
        import_bundle(&mut conn, &bundle(vec![good.clone(), missing])),
        Err(TeachingError::NotFound(_))
    ));
    assert_eq!(count(&conn), 0);
    put(&mut conn, &good).unwrap();
    let mut conflict = good.clone();
    conflict.content = "different".into();
    let new = row(RecordKind::Observation, "new", None, &kid);
    assert!(matches!(
        import_bundle(&mut conn, &bundle(vec![new, conflict])),
        Err(TeachingError::Conflict(_))
    ));
    assert_eq!(count(&conn), 1);
    let missing_parent = row(RecordKind::Proposal, "missing-parent", Some("absent"), &kid);
    assert!(import_bundle(&mut conn, &bundle(vec![missing_parent])).is_err());
    assert_eq!(count(&conn), 1);
}
#[test]
fn import_rejects_cycles_and_duplicate_ids_before_writes() {
    let mut conn = open(":memory:");
    let kid = knowledge_fixture(&mut conn, "one");
    let cycle = vec![
        row(RecordKind::Revision, "r", Some("f"), &kid),
        row(RecordKind::Feedback, "f", Some("d"), &kid),
        row(RecordKind::Delivery, "d", Some("r"), &kid),
    ];
    assert!(preview_import(&conn, &bundle(cycle.clone())).is_err());
    assert!(import_bundle(&mut conn, &bundle(cycle)).is_err());
    assert_eq!(count(&conn), 0);
    let r = row(RecordKind::Observation, "o", None, &kid);
    assert!(import_bundle(&mut conn, &bundle(vec![r.clone(), r])).is_err());
    assert_eq!(count(&conn), 0);
}
#[test]
fn explicit_new_knowledge_revision_keeps_old_records_and_courses_bound() {
    let mut conn = open(":memory:");
    let kid = knowledge_fixture(&mut conn, "one");
    chain(&mut conn, &kid);
    let cid = course_fixture(&mut conn, &kid, "old-course");
    let original = course::read_candidate(&conn, &cid).unwrap().unwrap();
    let new = knowledge::review_checked(
        &mut conn,
        &kid,
        "modified",
        "fixture-owner",
        None,
        Some("revised knowledge"),
        None,
    )
    .unwrap();
    let mut revision = row(RecordKind::Revision, "new-revision", Some("feedback"), &new);
    put(&mut conn, &revision).unwrap();
    revision.record_id = "hidden-upgrade".into();
    revision.course_id = Some(cid.clone());
    assert!(put(&mut conn, &revision).is_err());
    assert!(
        put(
            &mut conn,
            &row(
                RecordKind::Delivery,
                "premature",
                Some("new-revision"),
                &new
            )
        )
        .is_err()
    );
    knowledge::review_checked(
        &mut conn,
        &new,
        "accepted",
        "fixture-owner",
        None,
        None,
        None,
    )
    .unwrap();
    put(
        &mut conn,
        &row(
            RecordKind::Delivery,
            "new-delivery",
            Some("new-revision"),
            &new,
        ),
    )
    .unwrap();
    assert_eq!(
        get(&conn, "delivery").unwrap().unwrap().record.knowledge_id,
        kid
    );
    let after = course::read_candidate(&conn, &cid).unwrap().unwrap();
    assert_eq!(after["manifest"], original["manifest"]);
    assert_eq!(after["bindings"][0]["knowledge_version"], kid);
    assert_eq!(after["stale"], true);
}
#[test]
fn pagination_has_no_duplicates_and_invalid_cursor_cannot_be_a_path() {
    let mut conn = open(":memory:");
    let kid = knowledge_fixture(&mut conn, "one");
    for index in 0..25 {
        put(
            &mut conn,
            &row(
                RecordKind::Observation,
                &format!("r-{index:02}"),
                None,
                &kid,
            ),
        )
        .unwrap();
    }
    let first = list(&conn, None).unwrap();
    assert_eq!(first.items.len(), 20);
    let next = list(&conn, first.next_cursor.as_deref()).unwrap();
    assert_eq!(next.items.len(), 5);
    assert!(next.next_cursor.is_none());
    assert!(next.items.iter().all(|r| {
        !first
            .items
            .iter()
            .any(|a| a.record.record_id == r.record.record_id)
    }));
    assert!(list(&conn, Some("../private")).is_err());
}
#[test]
fn restart_preserves_records_hashes_withdrawal_and_external_objects() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("teaching.sqlite");
    let mut conn = open(db.to_str().unwrap());
    let kid = knowledge_fixture(&mut conn, "one");
    chain(&mut conn, &kid);
    let before = list(&conn, None).unwrap();
    let b = export_bundle(&conn, "delivery").unwrap();
    let body: String = conn
        .query_row(
            "SELECT body FROM knowledge WHERE knowledge_id=?1",
            [&kid],
            |r| r.get(0),
        )
        .unwrap();
    withdraw(
        &mut conn,
        &Withdrawal {
            schema: WITHDRAWAL_SCHEMA.into(),
            withdrawal_id: "w".into(),
            record_id: "delivery".into(),
            reason: "withdraw".into(),
        },
    )
    .unwrap();
    let withdrawn = list(&conn, None).unwrap();
    drop(conn);
    let mut conn = open(db.to_str().unwrap());
    assert_eq!(list(&conn, None).unwrap(), withdrawn);
    assert_eq!(count(&conn), before.items.len() as i64);
    assert_eq!(import_bundle(&mut conn, &b).unwrap().duplicate_count, 4);
    assert!(get(&conn, "delivery").unwrap().unwrap().withdrawn);
    assert_eq!(
        conn.query_row(
            "SELECT body FROM knowledge WHERE knowledge_id=?1",
            [&kid],
            |r| r.get::<_, String>(0)
        )
        .unwrap(),
        body
    );
    assert_eq!(
        conn.query_row("SELECT COUNT(*) FROM learning_events", [], |r| r
            .get::<_, i64>(0))
            .unwrap(),
        0
    );
}

#[test]
fn canonical_hash_preserves_content_array_order_and_authority_metadata() {
    let mut conn = open(":memory:");
    let kid = knowledge_fixture(&mut conn, "one");
    let r = row(RecordKind::Observation, "o", None, &kid);
    let h = package_hash(&[r.clone()]).unwrap();
    for change in 0..6 {
        let mut other = r.clone();
        match change {
            0 => other.content.push(' '),
            1 => other.purpose.push(' '),
            2 => other.assisted = true,
            3 => other.privacy = RecordPrivacy::LocalOnly,
            4 => other.producer_kind = ProducerKind::MachineGenerated,
            _ => other.rubric_version = Some("declared-v1".into()),
        };
        assert_ne!(h, package_hash(&[other]).unwrap());
    }
    let second = row(RecordKind::Observation, "second", None, &kid);
    assert_ne!(
        package_hash(&[r.clone(), second.clone()]).unwrap(),
        package_hash(&[second, r.clone()]).unwrap()
    );
    let b = bundle(vec![r]);
    let changes = conn.total_changes();
    preview_import(&conn, &b).unwrap();
    assert_eq!(conn.total_changes(), changes);
}

#[test]
fn personal_scope_ancestor_cannot_escape_through_exportable_child() {
    let mut conn = open(":memory:"); let kid = knowledge_fixture(&mut conn, "scope");
    let mut root = row(RecordKind::Requirement, "personal", None, &kid);
    root.scope = RecordScope::Personal;
    put(&mut conn, &root).unwrap();
    let child = row(RecordKind::Proposal, "shared-child", Some("personal"), &kid);
    put(&mut conn, &child).unwrap();
    assert!(matches!(export_bundle(&conn, "shared-child"), Err(TeachingError::Conflict(_))));
    assert!(matches!(export_bundle(&conn, "personal"), Err(TeachingError::Conflict(_))));
}
#[test]
fn feedback_keeps_original_delivery_course_until_explicit_revision() {
    let mut conn = open(":memory:"); let kid = knowledge_fixture(&mut conn, "course-context");
    let a = course_fixture(&mut conn, &kid, "course-context-a");
    let b = course_fixture(&mut conn, &kid, "course-context-b");
    for mut record in [row(RecordKind::Requirement, "req-a", None, &kid),
        row(RecordKind::Proposal, "prop-a", Some("req-a"), &kid),
        row(RecordKind::Delivery, "delivery-a", Some("prop-a"), &kid)] {
        record.course_id=Some(a.clone()); put(&mut conn,&record).unwrap();
    }
    let before=count(&conn);
    for kind in [RecordKind::TeachBack,RecordKind::Feedback] {
        let mut changed=row(kind,"wrong-context",Some("delivery-a"),&kid);
        changed.course_id=Some(b.clone()); assert!(put(&mut conn,&changed).is_err());
        changed.course_id=None; assert!(put(&mut conn,&changed).is_err());
    }
    let mut wrong=row(RecordKind::Delivery,"delivery-b",Some("prop-a"),&kid);
    wrong.course_id=Some(b.clone()); assert!(put(&mut conn,&wrong).is_err());
    assert_eq!(count(&conn),before);
    let mut feedback=row(RecordKind::Feedback,"feedback-a",Some("delivery-a"),&kid);
    feedback.course_id=Some(a.clone());put(&mut conn,&feedback).unwrap();
    let mut revised=row(RecordKind::Revision,"revision-b",Some("feedback-a"),&kid);
    revised.course_id=Some(b.clone());put(&mut conn,&revised).unwrap();
    wrong.parent_id=Some("revision-b".into());put(&mut conn,&wrong).unwrap();
    assert_eq!(get(&conn,"delivery-a").unwrap().unwrap().record.course_id,Some(a));
    assert_eq!(get(&conn,"delivery-b").unwrap().unwrap().record.course_id,Some(b));
}

// Insert malformed restored rows into a fresh fixture. Production append-only
// triggers remain enabled; no UPDATE/DELETE bypass is used.
fn restored_row(conn: &Connection, record: &TeachingRecord, sql_parent: Option<&str>, sql_kind: &str) {
    use sha2::{Digest, Sha256};
    fn sorted(value: serde_json::Value) -> serde_json::Value {
        match value {
            serde_json::Value::Object(map) => {
                let mut fields: Vec<_> = map.into_iter().collect();
                fields.sort_by(|a,b| a.0.cmp(&b.0));
                serde_json::Value::Object(fields.into_iter().map(|(k,v)| (k,sorted(v))).collect())
            }
            serde_json::Value::Array(items) => serde_json::Value::Array(items.into_iter().map(sorted).collect()),
            other => other,
        }
    }
    let json = serde_json::to_string(&sorted(serde_json::to_value(record).unwrap())).unwrap();
    let checksum = hex::encode(Sha256::digest(json.as_bytes()));
    conn.execute("INSERT INTO teaching_records(record_id,parent_id,kind,record_json,content_sha256) VALUES(?1,?2,?3,?4,?5)",
        rusqlite::params![record.record_id,sql_parent,sql_kind,json,checksum]).unwrap();
}

#[test]
fn restored_sql_parent_cannot_hide_withdrawn_json_ancestor() {
    let mut conn = open(":memory:");
    let kid = knowledge_fixture(&mut conn,"restore-parent");
    let root = row(RecordKind::Requirement,"root",None,&kid);
    put(&mut conn,&root).unwrap();
    withdraw(&mut conn,&Withdrawal {schema:WITHDRAWAL_SCHEMA.into(),withdrawal_id:"withdraw-root".into(),record_id:"root".into(),reason:"withdraw".into()}).unwrap();
    let damaged = row(RecordKind::Proposal,"damaged",Some("root"),&kid);
    restored_row(&conn,&damaged,None,"proposal");
    let child = row(RecordKind::Delivery,"descendant",Some("damaged"),&kid);
    restored_row(&conn,&child,Some("damaged"),"delivery");
    for id in ["damaged","descendant"] {
        assert!(matches!(get(&conn,id),Err(TeachingError::Invalid(_))));
        assert!(export_bundle(&conn,id).is_err());
    }
    let before = conn.total_changes();
    assert!(withdraw(&mut conn,&Withdrawal {schema:WITHDRAWAL_SCHEMA.into(),withdrawal_id:"withdraw-damaged".into(),record_id:"damaged".into(),reason:"withdraw".into()}).is_err());
    assert_eq!(conn.total_changes(),before);
}

#[test]
fn restored_sql_kind_must_agree_with_hashed_record() {
    let mut conn = open(":memory:");
    let kid = knowledge_fixture(&mut conn,"restore-kind");
    let record = row(RecordKind::Requirement,"wrong-kind",None,&kid);
    restored_row(&conn,&record,None,"observation");
    assert!(matches!(get(&conn,"wrong-kind"),Err(TeachingError::Invalid(_))));
    assert!(list(&conn,None).is_err());
}

#[test]
fn corrupt_withdrawal_target_cannot_return_a_false_duplicate_receipt() {
    use sha2::{Digest,Sha256};
    let mut conn=open(":memory:");let kid=knowledge_fixture(&mut conn,"withdraw-target");
    for id in ["intended","other"] {put(&mut conn,&row(RecordKind::Requirement,id,None,&kid)).unwrap();}
    let request=Withdrawal {schema:WITHDRAWAL_SCHEMA.into(),withdrawal_id:"restored-withdraw".into(),record_id:"intended".into(),reason:"withdraw".into()};
    let json=serde_json::to_string(&serde_json::to_value(&request).unwrap()).unwrap();
    let checksum=hex::encode(Sha256::digest(json.as_bytes()));
    conn.execute("INSERT INTO teaching_withdrawals(withdrawal_id,record_id,request_json,content_sha256) VALUES(?1,'other',?2,?3)",rusqlite::params![request.withdrawal_id,json,checksum]).unwrap();
    let before=conn.total_changes();
    assert!(matches!(withdraw(&mut conn,&request),Err(TeachingError::Invalid(_))));
    assert!(get(&conn,"other").is_err());assert_eq!(conn.total_changes(),before);
}
