use archeaxis_domain::character_memory::*;
use archeaxis_store_sqlite::init_workspace;
fn command(c: &mut rusqlite::Connection, op: Operation) -> serde_json::Value {
    let p = read(c).unwrap();
    apply(
        c,
        Write {
            workspace_id: p.workspace_id,
            restore_epoch: p.restore_epoch,
            expected_revision: p.revision,
            command: op,
        },
    )
    .unwrap()
}
#[test]
fn explicit_memory_reopens_corrects_forgets_and_disables_real_store() {
    let d = tempfile::tempdir().unwrap();
    let path = d.path().join("db");
    let mut c = init_workspace(path.to_str().unwrap()).unwrap();
    command(
        &mut c,
        Operation::Profile {
            preferences: "calm tone".into(),
            learning_goals: "math".into(),
        },
    );
    command(
        &mut c,
        Operation::Remember {
            memory: Memory {
                id: "m1".into(),
                text: "synthetic preference".into(),
                provenance: "human explicitly entered test".into(),
            },
        },
    );
    assert_eq!(
        context(&c).unwrap()["approved_memories"],
        serde_json::json!([])
    );
    command(&mut c, Operation::Enable);
    drop(c);
    let mut c = init_workspace(path.to_str().unwrap()).unwrap();
    assert_eq!(
        context(&c).unwrap()["approved_memories"][0]["text"],
        "synthetic preference"
    );
    command(
        &mut c,
        Operation::Correct {
            memory: Memory {
                id: "m1".into(),
                text: "corrected".into(),
                provenance: "human correction".into(),
            },
        },
    );
    assert_eq!(read(&c).unwrap().memories[0].text, "corrected");
    let receipt = command(&mut c, Operation::Forget { id: "m1".into() });
    assert_eq!(receipt["live_store_deleted"], true);
    let raw: String = c
        .query_row(
            "SELECT value FROM workspace_meta WHERE key='character_memory_v1'",
            [],
            |r| r.get(0),
        )
        .unwrap();
    assert!(!raw.contains("corrected"));
    assert!(read(&c).unwrap().memories.is_empty());
    command(&mut c, Operation::Disable);
    assert_eq!(context(&c).unwrap()["enabled"], false);
    assert_eq!(
        c.query_row("SELECT COUNT(*) FROM knowledge", [], |r| r.get::<_, i64>(0))
            .unwrap(),
        0
    );
}
#[test]
fn stale_identity_restore_and_invalid_input_do_not_replace_live_state() {
    let d = tempfile::tempdir().unwrap();
    let mut c = init_workspace(d.path().join("a").to_str().unwrap()).unwrap();
    let p = read(&c).unwrap();
    command(&mut c, Operation::Enable);
    assert!(
        apply(
            &mut c,
            Write {
                workspace_id: p.workspace_id.clone(),
                restore_epoch: p.restore_epoch.clone(),
                expected_revision: 0,
                command: Operation::Disable
            }
        )
        .is_err()
    );
    let p = read(&c).unwrap();
    let tx = c.transaction().unwrap();
    archeaxis_store_sqlite::authorization_fence::install_after_restore(&tx).unwrap();
    tx.commit().unwrap();
    assert_eq!(context(&c).unwrap()["enabled"], false);
    assert!(
        apply(
            &mut c,
            Write {
                workspace_id: p.workspace_id,
                restore_epoch: p.restore_epoch,
                expected_revision: p.revision,
                command: Operation::Enable
            }
        )
        .is_err()
    );
    let p = read(&c).unwrap();
    assert!(
        apply(
            &mut c,
            Write {
                workspace_id: p.workspace_id,
                restore_epoch: p.restore_epoch,
                expected_revision: p.revision,
                command: Operation::Remember {
                    memory: Memory {
                        id: "x".into(),
                        text: "x".into(),
                        provenance: "".into()
                    }
                }
            }
        )
        .is_err()
    );
    assert!(read(&c).unwrap().memories.is_empty());
}
#[test]
fn consumer_never_reuses_forgotten_or_cross_workspace_snapshot() {
    let d = tempfile::tempdir().unwrap();
    let mut c = init_workspace(d.path().join("a").to_str().unwrap()).unwrap();
    let mut other = init_workspace(d.path().join("b").to_str().unwrap()).unwrap();
    command(&mut c, Operation::Enable);
    command(
        &mut c,
        Operation::Remember {
            memory: Memory {
                id: "m".into(),
                text: "fixture memory".into(),
                provenance: "explicit approval fixture".into(),
            },
        },
    );
    let frozen = context(&c).unwrap();
    assert_context_current(&c, &frozen).unwrap();
    assert!(assert_context_current(&other, &frozen).is_err());
    let p = read(&c).unwrap();
    assert!(
        apply(
            &mut other,
            Write {
                workspace_id: p.workspace_id,
                restore_epoch: p.restore_epoch,
                expected_revision: p.revision,
                command: Operation::ForgetAll
            }
        )
        .is_err()
    );
    command(&mut c, Operation::ForgetAll);
    assert!(assert_context_current(&c, &frozen).is_err());
    assert_eq!(
        context(&c).unwrap()["approved_memories"],
        serde_json::json!([])
    );
}
