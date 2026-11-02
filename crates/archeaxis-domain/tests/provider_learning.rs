//! Synthetic local persistence tests; no provider, model or human trial is run.
use archeaxis_domain::{
    backup, document,
    provider_learning::{
        self as learning, Activity, Cancel, Provider, Question, Start, Submission,
    },
    provider_material_grant::Snapshot,
};
use rusqlite::Connection;
use serde_json::{Value, json};

fn snap(value: &Value) -> Snapshot {
    Snapshot {
        document_id: value["document_id"].as_str().unwrap().into(),
        version: value["version"].as_i64().unwrap(),
        content_sha256: value["content_sha256"].as_str().unwrap().into(),
    }
}
fn material(c: &mut Connection) -> Value {
    document::create_optional(c,None,None,"SYNTHETIC practice material",json!({"type":"doc","content":[{"type":"paragraph","content":[{"type":"text","text":"practice"}]}]})).unwrap()
}
fn grant(c: &mut Connection, material: &Value) -> Value {
    document::create_optional(c,None,None,"SYNTHETIC provider grant",json!({"type":"doc","content":[],"attrs":{"archeaxis_provider_material_grant":{
        "schema":"archeaxis.provider-material-grant/v1","purpose":"practice","consumer":"deeptutor","operations":["practice"],
        "material":snap(material),"authorization_basis":"SYNTHETIC explicit human authorization","expires_at":null,"state":"granted"
    }}})).unwrap()
}
fn activity(id: &str, material: &Value, g: Option<&Value>) -> Activity {
    Activity {
        activity_id: id.into(),
        material: snap(material),
        provider: Provider {
            id: (if g.is_some() { "deeptutor" } else { "openmaic" }).into(),
            version: (if g.is_some() { "1.7.1" } else { "1.3.0" }).into(),
        },
        question: Question {
            question_id: "question_1".into(),
            question_version: "caller_declared_v1".into(),
        },
        grant: g.map(snap),
    }
}
fn submission(id: &str) -> Submission {
    Submission {
        client_event_id: id.into(),
        answer: "SYNTHETIC answer".into(),
        provider_correct: None,
        self_report: true,
        rating: None,
    }
}

#[test]
fn local_attempt_is_idempotent_and_never_becomes_an_fsrs_review() {
    let dir = tempfile::tempdir().unwrap();
    let path = dir.path().join("practice.sqlite");
    let mut c = archeaxis_store_sqlite::init_workspace(path.to_str().unwrap()).unwrap();
    let source = material(&mut c);
    let a = activity("local_activity", &source, None);
    assert_eq!(learning::create(&mut c, &a).unwrap()["duplicate"], false);
    assert_eq!(learning::create(&mut c, &a).unwrap()["duplicate"], true);
    let mut changed = a.clone();
    changed.question.question_version = "caller_declared_v2".into();
    assert!(matches!(
        learning::create(&mut c, &changed),
        Err(learning::Error::Conflict(_))
    ));
    learning::start(
        &mut c,
        &a.activity_id,
        &Start {
            attempt_id: "try_1".into(),
        },
    )
    .unwrap();
    let body = submission("event_1");
    let first = learning::submit(&mut c, &a.activity_id, "try_1", &body).unwrap();
    assert_eq!(first["independent_mastery"], "not_established");
    assert_eq!(first["question_binding"], "client_declared_unverified");
    assert_eq!(
        first["provider_result_verification"],
        "unverified_client_report"
    );
    assert_eq!(
        learning::submit(&mut c, &a.activity_id, "try_1", &body).unwrap()["duplicate"],
        true
    );
    let mut different = body.clone();
    different.answer = "different".into();
    assert!(matches!(
        learning::submit(&mut c, &a.activity_id, "try_1", &different),
        Err(learning::Error::Conflict(_))
    ));
    assert_eq!(
        c.query_row("SELECT count(*) FROM learning_events", [], |r| r
            .get::<_, i64>(0))
            .unwrap(),
        0
    );
    assert_eq!(
        c.query_row("SELECT count(*) FROM learning_provider_attempts", [], |r| r
            .get::<_, i64>(0))
            .unwrap(),
        1
    );
    drop(c);
    let c = archeaxis_store_sqlite::init_workspace(path.to_str().unwrap()).unwrap();
    let read = learning::read(&c, &a.activity_id, None).unwrap();
    assert_eq!(
        read["activity"]["material"]["content_sha256"],
        source["content_sha256"]
    );
    assert_eq!(read["attempts"][0]["result"]["answer"], "SYNTHETIC answer");
}

#[test]
fn invalid_material_provider_grade_and_late_submissions_fail_closed() {
    let dir = tempfile::tempdir().unwrap();
    let mut c =
        archeaxis_store_sqlite::init_workspace(dir.path().join("db.sqlite").to_str().unwrap())
            .unwrap();
    let source = material(&mut c);
    let a = activity("activity", &source, None);
    let mut bad = a.clone();
    bad.material.content_sha256 = "0".repeat(64);
    assert!(learning::create(&mut c, &bad).is_err());
    bad = a.clone();
    bad.provider.id = "deeptutor".into();
    bad.provider.version = "1.7.1".into();
    assert!(learning::create(&mut c, &bad).is_err());
    learning::create(&mut c, &a).unwrap();
    learning::start(
        &mut c,
        "activity",
        &Start {
            attempt_id: "first".into(),
        },
    )
    .unwrap();
    let mut grade = submission("event");
    grade.provider_correct = Some(true);
    assert!(learning::submit(&mut c, "activity", "first", &grade).is_err());
    let cancelled = Cancel {
        client_cancel_id: "cancel_1".into(),
    };
    assert_eq!(
        learning::cancel(&mut c, "activity", "first", &cancelled).unwrap()["duplicate"],
        false
    );
    assert_eq!(
        learning::cancel(&mut c, "activity", "first", &cancelled).unwrap()["duplicate"],
        true
    );
    assert!(matches!(
        learning::submit(&mut c, "activity", "first", &submission("late")),
        Err(learning::Error::Conflict(_))
    ));
    assert!(matches!(
        learning::cancel(
            &mut c,
            "activity",
            "first",
            &Cancel {
                client_cancel_id: "other".into()
            }
        ),
        Err(learning::Error::Conflict(_))
    ));
}

#[test]
fn revoked_grant_denies_pending_retry_and_late_publication_but_allows_cancel() {
    let dir = tempfile::tempdir().unwrap();
    let mut c =
        archeaxis_store_sqlite::init_workspace(dir.path().join("db.sqlite").to_str().unwrap())
            .unwrap();
    let source = material(&mut c);
    let g = grant(&mut c, &source);
    let a = activity("provider_activity", &source, Some(&g));
    learning::create(&mut c, &a).unwrap();
    let start = Start {
        attempt_id: "try_1".into(),
    };
    learning::start(&mut c, &a.activity_id, &start).unwrap();
    let mut revoked = g["editor_json"].clone();
    revoked["attrs"]["archeaxis_provider_material_grant"]["state"] = json!("revoked");
    document::save(&mut c, g["document_id"].as_str().unwrap(), 1, revoked).unwrap();
    assert!(learning::start(&mut c, &a.activity_id, &start).is_err());
    assert!(learning::submit(&mut c, &a.activity_id, "try_1", &submission("late")).is_err());
    assert!(
        document::save(
            &mut c,
            g["document_id"].as_str().unwrap(),
            2,
            g["editor_json"].clone()
        )
        .is_err()
    );
    learning::cancel(
        &mut c,
        &a.activity_id,
        "try_1",
        &Cancel {
            client_cancel_id: "cancel".into(),
        },
    )
    .unwrap();
}

#[test]
fn restore_fences_pending_attempts_and_old_provider_grants_without_replay() {
    let dir = tempfile::tempdir().unwrap();
    let mut c =
        archeaxis_store_sqlite::init_workspace(dir.path().join("source.sqlite").to_str().unwrap())
            .unwrap();
    let source = material(&mut c);
    let g = grant(&mut c, &source);
    let a = activity("provider_activity", &source, Some(&g));
    learning::create(&mut c, &a).unwrap();
    let start = Start {
        attempt_id: "pending".into(),
    };
    learning::start(&mut c, &a.activity_id, &start).unwrap();
    let backup_path = dir.path().join("backup.sqlite");
    backup::backup(&c, backup_path.to_str().unwrap()).unwrap();
    let mut restored = archeaxis_store_sqlite::init_workspace(
        dir.path().join("restored.sqlite").to_str().unwrap(),
    )
    .unwrap();
    assert!(backup::restore_authorized(backup_path.to_str().unwrap(), &mut restored).unwrap());
    assert_eq!(
        learning::read(&restored, &a.activity_id, None).unwrap()["attempts"][0]["state"],
        "pending"
    );
    assert!(learning::start(&mut restored, &a.activity_id, &start).is_err());
    assert!(
        learning::submit(
            &mut restored,
            &a.activity_id,
            "pending",
            &submission("replayed")
        )
        .is_err()
    );
    assert!(
        learning::start(
            &mut restored,
            &a.activity_id,
            &Start {
                attempt_id: "new".into()
            }
        )
        .is_err()
    );
    assert_eq!(
        restored
            .query_row("SELECT count(*) FROM learning_provider_attempts", [], |r| r
                .get::<_, i64>(0))
            .unwrap(),
        1
    );
}

#[test]
fn every_attempt_has_a_reachable_bounded_history_page() {
    let dir = tempfile::tempdir().unwrap();
    let mut c =
        archeaxis_store_sqlite::init_workspace(dir.path().join("db.sqlite").to_str().unwrap())
            .unwrap();
    let source = material(&mut c);
    let a = activity("activity", &source, None);
    learning::create(&mut c, &a).unwrap();
    for n in 0..105 {
        learning::start(
            &mut c,
            "activity",
            &Start {
                attempt_id: format!("attempt_{n:03}"),
            },
        )
        .unwrap();
    }
    let first = learning::read(&c, "activity", None).unwrap();
    assert_eq!(first["attempts"].as_array().unwrap().len(), 100);
    let cursor = first["next_cursor"].as_str().unwrap();
    let second = learning::read(&c, "activity", Some(cursor)).unwrap();
    assert_eq!(second["attempts"].as_array().unwrap().len(), 5);
    assert!(second["next_cursor"].is_null());
}

#[test]
fn event_id_cannot_be_reused_across_activities_or_attempts() {
    let dir = tempfile::tempdir().unwrap();
    let mut c =
        archeaxis_store_sqlite::init_workspace(dir.path().join("db.sqlite").to_str().unwrap())
            .unwrap();
    let source = material(&mut c);
    for id in ["a", "b"] {
        let a = activity(id, &source, None);
        learning::create(&mut c, &a).unwrap();
        learning::start(
            &mut c,
            id,
            &Start {
                attempt_id: "first".into(),
            },
        )
        .unwrap();
    }
    learning::start(
        &mut c,
        "a",
        &Start {
            attempt_id: "second".into(),
        },
    )
    .unwrap();
    learning::submit(&mut c, "a", "first", &submission("globally_unique")).unwrap();
    assert!(matches!(
        learning::submit(&mut c, "a", "second", &submission("globally_unique")),
        Err(learning::Error::Conflict(_))
    ));
    assert!(matches!(
        learning::submit(&mut c, "b", "first", &submission("globally_unique")),
        Err(learning::Error::Conflict(_))
    ));
    assert_eq!(
        c.query_row(
            "SELECT count(*) FROM learning_provider_attempts WHERE state='submitted'",
            [],
            |r| r.get::<_, i64>(0)
        )
        .unwrap(),
        1
    );
}

#[test]
fn grant_expiry_is_exclusive_and_prior_submission_remains_readable_after_revocation() {
    use archeaxis_domain::provider_material_grant;
    let dir = tempfile::tempdir().unwrap();
    let mut c =
        archeaxis_store_sqlite::init_workspace(dir.path().join("db.sqlite").to_str().unwrap())
            .unwrap();
    let source = material(&mut c);
    let expiring=document::create_optional(&mut c,None,None,"expiring",json!({"type":"doc","content":[],"attrs":{"archeaxis_provider_material_grant":{
        "schema":"archeaxis.provider-material-grant/v1","purpose":"practice","consumer":"deeptutor","operations":["practice"],"material":snap(&source),"authorization_basis":"SYNTHETIC human grant","expires_at":2000,"state":"granted"}}})).unwrap();
    assert!(provider_material_grant::consume(&c, &snap(&expiring), &snap(&source), 1999).is_ok());
    assert!(provider_material_grant::consume(&c, &snap(&expiring), &snap(&source), 2000).is_err());
    let g = grant(&mut c, &source);
    let a = activity("provider_activity", &source, Some(&g));
    learning::create(&mut c, &a).unwrap();
    learning::start(
        &mut c,
        &a.activity_id,
        &Start {
            attempt_id: "try".into(),
        },
    )
    .unwrap();
    let answer = submission("saved");
    learning::submit(&mut c, &a.activity_id, "try", &answer).unwrap();
    let mut revised = source["editor_json"].clone();
    revised["content"][0]["content"][0]["text"] = json!("newer version");
    document::save(&mut c, source["document_id"].as_str().unwrap(), 1, revised).unwrap();
    let mut revoked = g["editor_json"].clone();
    revoked["attrs"]["archeaxis_provider_material_grant"]["state"] = json!("revoked");
    document::save(&mut c, g["document_id"].as_str().unwrap(), 1, revoked).unwrap();
    let replay = learning::submit(&mut c, &a.activity_id, "try", &answer).unwrap();
    assert_eq!(replay["duplicate"], true);
    assert_eq!(replay["material_status"], "current");
    assert_eq!(replay["material_status_now"], "historical");
    assert_eq!(
        learning::read(&c, &a.activity_id, None).unwrap()["attempts"][0]["state"],
        "submitted"
    );
    assert!(
        learning::start(
            &mut c,
            &a.activity_id,
            &Start {
                attempt_id: "new".into()
            }
        )
        .is_err()
    );
}

#[test]
fn concurrent_cancel_and_submit_have_exactly_one_terminal_winner() {
    use std::sync::{Arc, Barrier};
    let dir = tempfile::tempdir().unwrap();
    let path = dir.path().join("race.sqlite");
    let mut c = archeaxis_store_sqlite::init_workspace(path.to_str().unwrap()).unwrap();
    let source = material(&mut c);
    let a = activity("race", &source, None);
    learning::create(&mut c, &a).unwrap();
    learning::start(
        &mut c,
        "race",
        &Start {
            attempt_id: "one".into(),
        },
    )
    .unwrap();
    let mut first = archeaxis_store_sqlite::init_workspace(path.to_str().unwrap()).unwrap();
    let mut second = archeaxis_store_sqlite::init_workspace(path.to_str().unwrap()).unwrap();
    let barrier = Arc::new(Barrier::new(2));
    let other = barrier.clone();
    let t1 = std::thread::spawn(move || {
        barrier.wait();
        learning::submit(&mut first, "race", "one", &submission("event")).is_ok()
    });
    let t2 = std::thread::spawn(move || {
        other.wait();
        learning::cancel(
            &mut second,
            "race",
            "one",
            &Cancel {
                client_cancel_id: "cancel".into(),
            },
        )
        .is_ok()
    });
    assert_eq!(
        u8::from(t1.join().unwrap()) + u8::from(t2.join().unwrap()),
        1
    );
    let state:String=c.query_row("SELECT state FROM learning_provider_attempts WHERE activity_id='race' AND attempt_id='one'",[],|r|r.get(0)).unwrap();
    assert!(matches!(state.as_str(), "submitted" | "cancelled"));
    assert_eq!(
        c.query_row("SELECT count(*) FROM learning_events", [], |r| r
            .get::<_, i64>(0))
            .unwrap(),
        0
    );
}

#[test]
fn updated_document_blocks_deeptutor_but_local_history_is_labeled_historical() {
    let dir = tempfile::tempdir().unwrap();
    let mut c =
        archeaxis_store_sqlite::init_workspace(dir.path().join("db.sqlite").to_str().unwrap())
            .unwrap();
    let source = material(&mut c);
    let g = grant(&mut c, &source);
    let remote = activity("remote", &source, Some(&g));
    let local = activity("local", &source, None);
    learning::create(&mut c, &remote).unwrap();
    learning::create(&mut c, &local).unwrap();
    learning::start(
        &mut c,
        "remote",
        &Start {
            attempt_id: "pending".into(),
        },
    )
    .unwrap();
    learning::start(
        &mut c,
        "local",
        &Start {
            attempt_id: "local_try".into(),
        },
    )
    .unwrap();
    let mut changed = source["editor_json"].clone();
    changed["content"][0]["content"][0]["text"] = json!("new document version");
    document::save(&mut c, source["document_id"].as_str().unwrap(), 1, changed).unwrap();
    assert!(
        learning::start(
            &mut c,
            "remote",
            &Start {
                attempt_id: "pending".into()
            }
        )
        .is_err()
    );
    assert!(learning::submit(&mut c, "remote", "pending", &submission("remote_event")).is_err());
    assert_eq!(
        learning::read(&c, "remote", None).unwrap()["material_status"],
        "historical"
    );
    let local_result =
        learning::submit(&mut c, "local", "local_try", &submission("local_event")).unwrap();
    assert_eq!(local_result["material_status"], "historical");
    assert_eq!(
        learning::read(&c, "local", None).unwrap()["material_status"],
        "historical"
    );
}

#[test]
fn grant_expiry_is_required_even_when_null_is_permitted() {
    let dir = tempfile::tempdir().unwrap();
    let mut c =
        archeaxis_store_sqlite::init_workspace(dir.path().join("db.sqlite").to_str().unwrap())
            .unwrap();
    let source = material(&mut c);
    let valid = grant(&mut c, &source);
    assert!(
        valid["editor_json"]["attrs"]["archeaxis_provider_material_grant"]["expires_at"].is_null()
    );
    let mut missing = valid["editor_json"].clone();
    missing["attrs"]["archeaxis_provider_material_grant"]
        .as_object_mut()
        .unwrap()
        .remove("expires_at");
    assert!(document::create_optional(&mut c, None, None, "missing expiry", missing).is_err());
}

#[test]
fn persisted_submission_digest_binds_the_original_material_status() {
    let dir = tempfile::tempdir().unwrap();
    let mut c =
        archeaxis_store_sqlite::init_workspace(dir.path().join("db.sqlite").to_str().unwrap())
            .unwrap();
    let source = material(&mut c);
    let a = activity("activity", &source, None);
    learning::create(&mut c, &a).unwrap();
    learning::start(
        &mut c,
        "activity",
        &Start {
            attempt_id: "try".into(),
        },
    )
    .unwrap();
    let answer = submission("event");
    learning::submit(&mut c, "activity", "try", &answer).unwrap();
    let (raw,sha):(String,String)=c.query_row("SELECT result_json,result_sha256 FROM learning_provider_attempts WHERE activity_id='activity' AND attempt_id='try'",[],|r|Ok((r.get(0)?,r.get(1)?))).unwrap();
    c.execute("UPDATE learning_provider_attempts SET result_json=json_set(result_json,'$.material_status_at_submission','historical') WHERE activity_id='activity' AND attempt_id='try'",[]).unwrap();
    assert!(learning::read(&c, "activity", None).is_err());
    assert!(learning::submit(&mut c, "activity", "try", &answer).is_err());
    c.execute("UPDATE learning_provider_attempts SET result_json=?1,result_sha256=?2 WHERE activity_id='activity' AND attempt_id='try'",rusqlite::params![raw,sha]).unwrap();
    c.execute("UPDATE learning_provider_attempts SET result_sha256=?1 WHERE activity_id='activity' AND attempt_id='try'",["0".repeat(64)]).unwrap();
    assert!(learning::read(&c, "activity", None).is_err());
    assert!(learning::submit(&mut c, "activity", "try", &answer).is_err());
}

#[test]
fn broken_current_document_pointer_cannot_publish_an_unreadable_result() {
    let dir = tempfile::tempdir().unwrap();
    let mut c =
        archeaxis_store_sqlite::init_workspace(dir.path().join("db.sqlite").to_str().unwrap())
            .unwrap();
    let source = material(&mut c);
    let a = activity("activity", &source, None);
    learning::create(&mut c, &a).unwrap();
    learning::start(
        &mut c,
        "activity",
        &Start {
            attempt_id: "try".into(),
        },
    )
    .unwrap();
    c.execute(
        "UPDATE documents SET current_version=999 WHERE document_id=?1",
        [source["document_id"].as_str().unwrap()],
    )
    .unwrap();
    assert!(learning::submit(&mut c, "activity", "try", &submission("event")).is_err());
    assert_eq!(c.query_row("SELECT state FROM learning_provider_attempts WHERE activity_id='activity' AND attempt_id='try'",[],|r|r.get::<_,String>(0)).unwrap(),"pending");
}

#[test]
fn missing_or_mismatched_fixed_version_is_not_reported_as_historical() {
    let dir = tempfile::tempdir().unwrap();
    let mut c =
        archeaxis_store_sqlite::init_workspace(dir.path().join("db.sqlite").to_str().unwrap())
            .unwrap();
    let source = material(&mut c);
    let a = activity("activity", &source, None);
    learning::create(&mut c, &a).unwrap();
    learning::start(
        &mut c,
        "activity",
        &Start {
            attempt_id: "try".into(),
        },
    )
    .unwrap();
    let mut revised = source["editor_json"].clone();
    revised["content"][0]["content"][0]["text"] = json!("current version");
    let id = source["document_id"].as_str().unwrap();
    document::save(&mut c, id, 1, revised).unwrap();
    assert_eq!(
        learning::read(&c, "activity", None).unwrap()["material_status"],
        "historical"
    );
    c.execute(
        "UPDATE document_versions SET content_sha256=?1 WHERE document_id=?2 AND version=1",
        rusqlite::params!["0".repeat(64), id],
    )
    .unwrap();
    assert_eq!(
        learning::read(&c, "activity", None).unwrap()["material_status"],
        "unavailable"
    );
    assert!(learning::submit(&mut c, "activity", "try", &submission("event")).is_err());
}

#[test]
fn provider_access_rejects_material_that_cannot_be_verified() {
    for (case, sql) in [
        (
            "editor",
            "UPDATE document_versions SET editor_json=json_set(editor_json,'$.content[0].content[0].text','changed') WHERE document_id=?1 AND version=1",
        ),
        (
            "projection",
            "UPDATE document_versions SET text_projection='different projection' WHERE document_id=?1 AND version=1",
        ),
        (
            "block",
            "UPDATE document_blocks SET text_projection='different block' WHERE document_id=?1 AND version=1",
        ),
    ] {
        let dir = tempfile::tempdir().unwrap();
        let mut c =
            archeaxis_store_sqlite::init_workspace(dir.path().join("db.sqlite").to_str().unwrap())
                .unwrap();
        let source = material(&mut c);
        let g = grant(&mut c, &source);
        let local = activity("local", &source, None);
        let remote = activity("remote", &source, Some(&g));
        learning::create(&mut c, &local).unwrap();
        learning::create(&mut c, &remote).unwrap();
        let pending = Start {
            attempt_id: "pending".into(),
        };
        learning::start(&mut c, "local", &pending).unwrap();
        learning::start(&mut c, "remote", &pending).unwrap();
        let id = source["document_id"].as_str().unwrap();
        assert_eq!(c.execute(sql, [id]).unwrap(), 1, "fixture {case}");
        for name in ["local", "remote"] {
            assert_eq!(
                learning::read(&c, name, None).unwrap()["material_status"],
                "unavailable",
                "fixture {case}"
            );
            assert!(
                learning::start(&mut c, name, &pending).is_err(),
                "fixture {case}"
            );
            assert!(
                learning::submit(&mut c, name, "pending", &submission("event")).is_err(),
                "fixture {case}"
            );
            let state:String=c.query_row("SELECT state FROM learning_provider_attempts WHERE activity_id=?1 AND attempt_id='pending'",[name],|r|r.get(0)).unwrap();
            assert_eq!(state, "pending", "fixture {case}");
        }
        assert!(
            learning::create(&mut c, &activity("new_remote", &source, Some(&g))).is_err(),
            "fixture {case}"
        );
    }
}

#[test]
fn changed_grant_metadata_without_matching_digest_cannot_authorize() {
    let dir = tempfile::tempdir().unwrap();
    let mut c =
        archeaxis_store_sqlite::init_workspace(dir.path().join("db.sqlite").to_str().unwrap())
            .unwrap();
    let source = material(&mut c);
    let g = grant(&mut c, &source);
    let a = activity("remote", &source, Some(&g));
    learning::create(&mut c, &a).unwrap();
    let pending = Start {
        attempt_id: "pending".into(),
    };
    learning::start(&mut c, "remote", &pending).unwrap();
    let grant_id = g["document_id"].as_str().unwrap();
    c.execute("UPDATE document_versions SET editor_json=json_set(editor_json,'$.attrs.archeaxis_provider_material_grant.authorization_basis','changed') WHERE document_id=?1 AND version=1",[grant_id]).unwrap();
    assert_eq!(
        learning::read(&c, "remote", None).unwrap()["material_status"],
        "current"
    );
    assert!(learning::start(&mut c, "remote", &pending).is_err());
    assert!(learning::submit(&mut c, "remote", "pending", &submission("event")).is_err());
    assert!(learning::create(&mut c, &activity("new_remote", &source, Some(&g))).is_err());
}

#[test]
fn unverified_legacy_projection_does_not_block_ordinary_document_read_or_save() {
    let dir = tempfile::tempdir().unwrap();
    let mut c =
        archeaxis_store_sqlite::init_workspace(dir.path().join("db.sqlite").to_str().unwrap())
            .unwrap();
    let source = material(&mut c);
    let a = activity("local", &source, None);
    learning::create(&mut c, &a).unwrap();
    learning::start(
        &mut c,
        "local",
        &Start {
            attempt_id: "pending".into(),
        },
    )
    .unwrap();
    let id = source["document_id"].as_str().unwrap();
    // Model a projection from a different codec version; this is not an actual legacy database fixture.
    c.execute("UPDATE document_versions SET text_projection='legacy projection' WHERE document_id=?1 AND version=1",[id]).unwrap();
    let old = document::read(&c, id, Some(1)).unwrap();
    assert_eq!(old["text_projection"], "legacy projection");
    let mut editor = old["editor_json"].clone();
    editor["content"][0]["content"][0]["text"] = json!("ordinary revision");
    assert_eq!(document::save(&mut c, id, 1, editor).unwrap()["version"], 2);
    assert_eq!(
        document::read(&c, id, Some(1)).unwrap()["text_projection"],
        "legacy projection"
    );
    assert_eq!(
        learning::read(&c, "local", None).unwrap()["material_status"],
        "unavailable"
    );
    assert!(learning::submit(&mut c, "local", "pending", &submission("event")).is_err());
}

fn unix_seconds() -> u64 {
    std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap()
        .as_secs()
}

// Hold the actual SQLite mutation until after the grant expires. The temporary
// trigger and collation exist only on this synthetic test connection.
fn assert_expiry_during_mutation_rolls_back(phase: &'static str) {
    use std::sync::mpsc;
    use std::time::{Duration, Instant};

    let dir = tempfile::tempdir().unwrap();
    let mut c =
        archeaxis_store_sqlite::init_workspace(dir.path().join("db.sqlite").to_str().unwrap())
            .unwrap();
    let source = material(&mut c);
    let expiry = unix_seconds() + 8;
    let g=document::create_optional(&mut c,None,None,"expiring",json!({"type":"doc","content":[],"attrs":{"archeaxis_provider_material_grant":{
        "schema":"archeaxis.provider-material-grant/v1","purpose":"practice","consumer":"deeptutor","operations":["practice"],
        "material":snap(&source),"authorization_basis":"SYNTHETIC human grant","expires_at":expiry,"state":"granted"
    }}})).unwrap();
    let a = activity("activity", &source, Some(&g));
    if phase != "create" {
        learning::create(&mut c, &a).unwrap();
    }
    if phase == "submit" {
        learning::start(
            &mut c,
            "activity",
            &Start {
                attempt_id: "try".into(),
            },
        )
        .unwrap();
    }

    let (entered_tx, entered_rx) = mpsc::channel();
    let (release_tx, release_rx) = mpsc::channel();
    c.create_collation("expiry_gate", move |left, right| {
        let _ = entered_tx.send(());
        let _ = release_rx.recv_timeout(Duration::from_secs(20));
        left.cmp(right)
    })
    .unwrap();
    let trigger = match phase {
        "create" => {
            "CREATE TEMP TRIGGER test_expiry_gate AFTER INSERT ON learning_provider_activities BEGIN SELECT CASE WHEN NEW.activity_id COLLATE expiry_gate = 'never' THEN RAISE(ABORT,'unexpected comparison') END; END;"
        }
        "start" => {
            "CREATE TEMP TRIGGER test_expiry_gate AFTER INSERT ON learning_provider_attempts BEGIN SELECT CASE WHEN NEW.attempt_id COLLATE expiry_gate = 'never' THEN RAISE(ABORT,'unexpected comparison') END; END;"
        }
        "submit" => {
            "CREATE TEMP TRIGGER test_expiry_gate AFTER UPDATE OF state ON learning_provider_attempts BEGIN SELECT CASE WHEN NEW.attempt_id COLLATE expiry_gate = 'never' THEN RAISE(ABORT,'unexpected comparison') END; END;"
        }
        _ => panic!("unsupported test phase"),
    };
    c.execute_batch(trigger).unwrap();
    let worker = std::thread::spawn(move || {
        let result = match phase {
            "create" => learning::create(&mut c, &a),
            "start" => learning::start(
                &mut c,
                "activity",
                &Start {
                    attempt_id: "try".into(),
                },
            ),
            "submit" => learning::submit(&mut c, "activity", "try", &submission("event")),
            _ => unreachable!(),
        };
        (c, result)
    });
    let entered = entered_rx.recv_timeout(Duration::from_secs(12)).is_ok();
    let deadline = Instant::now() + Duration::from_secs(15);
    if entered {
        while unix_seconds() < expiry && Instant::now() < deadline {
            std::thread::sleep(Duration::from_millis(10));
        }
    }
    let expired = unix_seconds() >= expiry;
    let _ = release_tx.send(());
    let (c, result) = worker.join().unwrap();
    assert!(
        entered,
        "the mutation did not reach the controlled SQLite gate"
    );
    assert!(expired, "the test clock did not reach the grant expiry");
    assert!(
        matches!(
            &result,
            Err(learning::Error::Invalid(
                "provider grant unavailable or revoked"
            ))
        ),
        "{result:?}"
    );
    match phase {
        "create" => assert_eq!(c.query_row("SELECT count(*) FROM learning_provider_activities WHERE activity_id='activity'",[],|r|r.get::<_,i64>(0)).unwrap(),0),
        "start" => assert_eq!(c.query_row("SELECT count(*) FROM learning_provider_attempts WHERE activity_id='activity' AND attempt_id='try'",[],|r|r.get::<_,i64>(0)).unwrap(),0),
        "submit" => {
            let row:(String,Option<String>,Option<String>,Option<String>)=c.query_row(
                "SELECT state,client_event_id,result_json,result_sha256 FROM learning_provider_attempts WHERE activity_id='activity' AND attempt_id='try'",[],
                |r|Ok((r.get(0)?,r.get(1)?,r.get(2)?,r.get(3)?))).unwrap();
            assert_eq!(row,("pending".into(),None,None,None));
        }
        _ => unreachable!(),
    }
}

#[test]
fn activity_create_rolls_back_if_grant_expires_during_mutation() {
    assert_expiry_during_mutation_rolls_back("create");
}

#[test]
fn attempt_start_rolls_back_if_grant_expires_during_mutation() {
    assert_expiry_during_mutation_rolls_back("start");
}

#[test]
fn observation_submit_rolls_back_if_grant_expires_during_mutation() {
    assert_expiry_during_mutation_rolls_back("submit");
}

#[test]
fn provider_pending_and_terminal_retries_keep_their_existing_semantics() {
    let dir = tempfile::tempdir().unwrap();
    let mut c =
        archeaxis_store_sqlite::init_workspace(dir.path().join("db.sqlite").to_str().unwrap())
            .unwrap();
    let source = material(&mut c);
    let g = grant(&mut c, &source);
    let a = activity("activity", &source, Some(&g));
    assert_eq!(learning::create(&mut c, &a).unwrap()["duplicate"], false);
    assert_eq!(learning::create(&mut c, &a).unwrap()["duplicate"], true);
    let start = Start {
        attempt_id: "try".into(),
    };
    assert_eq!(
        learning::start(&mut c, "activity", &start).unwrap()["duplicate"],
        false
    );
    assert_eq!(
        learning::start(&mut c, "activity", &start).unwrap()["duplicate"],
        true
    );
    let answer = submission("event");
    assert_eq!(
        learning::submit(&mut c, "activity", "try", &answer).unwrap()["duplicate"],
        false
    );
    assert_eq!(
        learning::submit(&mut c, "activity", "try", &answer).unwrap()["duplicate"],
        true
    );
    let cancel_start = Start {
        attempt_id: "other".into(),
    };
    learning::start(&mut c, "activity", &cancel_start).unwrap();
    let cancel = Cancel {
        client_cancel_id: "cancel".into(),
    };
    assert_eq!(
        learning::cancel(&mut c, "activity", "other", &cancel).unwrap()["duplicate"],
        false
    );
    assert_eq!(
        learning::cancel(&mut c, "activity", "other", &cancel).unwrap()["duplicate"],
        true
    );
    assert!(matches!(
        learning::submit(&mut c, "activity", "other", &submission("late")),
        Err(learning::Error::Conflict(_))
    ));
}
