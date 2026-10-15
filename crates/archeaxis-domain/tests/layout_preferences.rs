use archeaxis_domain::layout::{self, Bounds, Dock, Recover, Write};
use archeaxis_store_sqlite::init_workspace;
use std::collections::BTreeMap;

#[test]
fn v2_instances_grouped_floats_empty_lock_and_foreign_session() {
    let dir = tempfile::tempdir().unwrap();
    let mut conn = init_workspace(dir.path().join("layout-v2.sqlite").to_str().unwrap()).unwrap();
    let base = layout::read(&mut conn, "device_v2").unwrap();
    let mut value = serde_json::json!({"schema_version":2,"preset_id":"reading","registered_panels":["document.doc_a","03"],"dock_tree":{"kind":"empty"},"floating_bounds":{},"instance_bindings":{"document.doc_a":{"page_id":"03","object_id":"doc_a","session_key":format!("{}:{}:document:doc_a",base.workspace_id,base.restore_epoch)}},"floating_groups":[{"tree":{"kind":"tabs","panels":["document.doc_a","03"],"active":"document.doc_a"},"bounds":{"x":10,"y":20,"width":400,"height":300}}],"locked":true});
    let mut input = Write {
        workspace_id: base.workspace_id.clone(),
        device_id: base.device_id.clone(),
        restore_epoch: base.restore_epoch.clone(),
        expected_revision: 0,
        layout: serde_json::from_value(value.clone()).unwrap(),
    };
    let saved = layout::write(&mut conn, input.clone()).unwrap();
    assert!(saved.layout.locked);
    assert_eq!(
        serde_json::to_value(layout::read(&mut conn, "device_v2").unwrap()).unwrap(),
        serde_json::to_value(&saved).unwrap()
    );
    assert!(layout::write(&mut conn, input.clone()).is_err());
    input.expected_revision = 1;
    value["instance_bindings"]["document.doc_a"]["session_key"] =
        "foreign:initial:document:doc_a".into();
    input.layout = serde_json::from_value(value.clone()).unwrap();
    assert!(layout::write(&mut conn, input.clone()).is_err());
    value["instance_bindings"]["document.doc_a"]["page_id"] = "05".into();
    assert!(layout::validate(&serde_json::from_value(value).unwrap()).is_err());
    input.layout=serde_json::from_value(serde_json::json!({"schema_version":2,"preset_id":"default","registered_panels":[],"dock_tree":{"kind":"empty"},"floating_bounds":{},"locked":false})).unwrap();
    let empty = layout::write(&mut conn, input).unwrap();
    assert_eq!(empty.revision, 2);
    assert_eq!(
        conn.query_row("SELECT count(*) FROM document_versions", [], |r| r
            .get::<_, i64>(0))
            .unwrap(),
        0
    );
}

#[test]
fn v2_restore_explicitly_rebases_instance_sessions_and_retains_raw_until_confirmed() {
    let dir = tempfile::tempdir().unwrap();
    let mut conn = init_workspace(dir.path().join("v2-restore.sqlite").to_str().unwrap()).unwrap();
    let first = layout::read(&mut conn, "restore_device").unwrap();
    let prefs=serde_json::from_value(serde_json::json!({"schema_version":2,"preset_id":"reading","registered_panels":["document.doc_a"],"dock_tree":{"kind":"tabs","panels":["document.doc_a"],"active":"document.doc_a"},"floating_bounds":{},"instance_bindings":{"document.doc_a":{"page_id":"03","object_id":"doc_a","session_key":format!("{}:{}:document:doc_a",first.workspace_id,first.restore_epoch)}},"locked":true})).unwrap();
    layout::write(
        &mut conn,
        Write {
            workspace_id: first.workspace_id,
            device_id: first.device_id,
            restore_epoch: first.restore_epoch,
            expected_revision: 0,
            layout: prefs,
        },
    )
    .unwrap();
    let raw: String = conn
        .query_row(
            "SELECT value FROM workspace_meta WHERE key='ui_layout_v1:restore_device'",
            [],
            |r| r.get(0),
        )
        .unwrap();
    let tx = conn.transaction().unwrap();
    archeaxis_store_sqlite::authorization_fence::install_after_restore(&tx).unwrap();
    tx.commit().unwrap();
    let read = layout::read(&mut conn, "restore_device").unwrap();
    assert_eq!(
        read.recovery_reason.as_deref(),
        Some("LAYOUT_RESTORE_CONFIRMATION_REQUIRED")
    );
    assert_eq!(
        conn.query_row(
            "SELECT value FROM workspace_meta WHERE key='ui_layout_v1:restore_device'",
            [],
            |r| r.get::<_, String>(0)
        )
        .unwrap(),
        raw
    );
    let recovered = layout::recover(
        &mut conn,
        Recover {
            workspace_id: read.workspace_id,
            device_id: read.device_id,
            restore_epoch: read.restore_epoch,
            expected_revision: read.revision,
            viewport_width: 800.0,
            viewport_height: 600.0,
        },
    )
    .unwrap();
    assert_eq!(
        recovered.layout.instance_bindings["document.doc_a"].session_key,
        format!(
            "{}:{}:document:doc_a",
            recovered.workspace_id, recovered.restore_epoch
        )
    );
    assert!(recovered.layout.locked);
}

#[test]
fn preferences_restart_cas_and_device_isolation_do_not_write_business_drafts() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("workspace.sqlite");
    let mut conn = init_workspace(db.to_str().unwrap()).unwrap();
    let initial = layout::read(&mut conn, "device_a").unwrap();
    let input = Write {
        workspace_id: initial.workspace_id.clone(),
        device_id: initial.device_id.clone(),
        restore_epoch: initial.restore_epoch.clone(),
        expected_revision: initial.revision,
        layout: initial.layout.clone(),
    };
    let saved = layout::write(&mut conn, input.clone()).unwrap();
    assert_eq!(saved.revision, 1);
    assert!(layout::write(&mut conn, input).is_err());
    assert_eq!(layout::read(&mut conn, "device_b").unwrap().revision, 0);
    assert_eq!(
        conn.query_row("SELECT count(*) FROM document_versions", [], |row| row
            .get::<_, i64>(0))
            .unwrap(),
        0
    );
    assert_eq!(
        conn.query_row(
            "SELECT count(*) FROM workspace_meta WHERE key='ui_working_state_v1'",
            [],
            |row| row.get::<_, i64>(0)
        )
        .unwrap(),
        0
    );
    drop(conn);
    let mut conn = init_workspace(db.to_str().unwrap()).unwrap();
    assert_eq!(
        serde_json::to_value(layout::read(&mut conn, "device_a").unwrap()).unwrap(),
        serde_json::to_value(saved).unwrap()
    );
}
#[test]
fn unknown_panels_read_fallback_without_overwriting_then_explicitly_recover() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("workspace.sqlite");
    let mut conn = init_workspace(db.to_str().unwrap()).unwrap();
    let first = layout::read(&mut conn, "desktop").unwrap();
    let saved = layout::write(
        &mut conn,
        Write {
            workspace_id: first.workspace_id.clone(),
            device_id: first.device_id.clone(),
            restore_epoch: first.restore_epoch.clone(),
            expected_revision: 0,
            layout: first.layout,
        },
    )
    .unwrap();
    let mut raw = serde_json::to_value(&saved).unwrap();
    raw["layout"]["registered_panels"] = serde_json::json!(["99"]);
    raw["layout"]["dock_tree"]["panels"] = serde_json::json!(["99"]);
    raw["layout"]["dock_tree"]["active"] = "99".into();
    let original = raw.to_string();
    conn.execute(
        "UPDATE workspace_meta SET value=?1 WHERE key='ui_layout_v1:desktop'",
        [&original],
    )
    .unwrap();
    let fallback = layout::read(&mut conn, "desktop").unwrap();
    assert_eq!(
        fallback.recovery_reason.as_deref(),
        Some("LAYOUT_COMPONENT_OR_SCHEMA_UNSUPPORTED")
    );
    assert_eq!(
        conn.query_row(
            "SELECT value FROM workspace_meta WHERE key='ui_layout_v1:desktop'",
            [],
            |r| r.get::<_, String>(0)
        )
        .unwrap(),
        original
    );
    let restored = layout::recover(
        &mut conn,
        Recover {
            workspace_id: saved.workspace_id,
            device_id: saved.device_id,
            restore_epoch: saved.restore_epoch,
            expected_revision: 1,
            viewport_width: 800.0,
            viewport_height: 600.0,
        },
    )
    .unwrap();
    assert_eq!(restored.revision, 2);
    assert_eq!(restored.recovery_reason, None);
}
#[test]
fn floating_recovery_clamps_bounds_and_rejects_secrets_and_invalid_devices() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("workspace.sqlite");
    let mut conn = init_workspace(db.to_str().unwrap()).unwrap();
    assert!(layout::read(&mut conn, "../other").is_err());
    let base = layout::read(&mut conn, "desktop").unwrap();
    let mut prefs = base.layout.clone();
    prefs.registered_panels = vec!["01".into(), "05".into()];
    prefs.dock_tree = Dock::Tabs {
        panels: vec!["01".into()],
        active: "01".into(),
    };
    prefs.floating_bounds = BTreeMap::from([(
        "05".into(),
        Bounds {
            x: 2000.0,
            y: 1800.0,
            width: 1000.0,
            height: 900.0,
        },
    )]);
    let saved = layout::write(
        &mut conn,
        Write {
            workspace_id: base.workspace_id,
            device_id: base.device_id,
            restore_epoch: base.restore_epoch,
            expected_revision: 0,
            layout: prefs,
        },
    )
    .unwrap();
    let recovered = layout::recover(
        &mut conn,
        Recover {
            workspace_id: saved.workspace_id,
            device_id: saved.device_id,
            restore_epoch: saved.restore_epoch,
            expected_revision: 1,
            viewport_width: 800.0,
            viewport_height: 600.0,
        },
    )
    .unwrap();
    let bounds = &recovered.layout.floating_bounds["05"];
    assert_eq!(
        (bounds.x, bounds.y, bounds.width, bounds.height),
        (0.0, 0.0, 800.0, 600.0)
    );
    let mut injected = serde_json::to_value(&recovered.layout).unwrap();
    injected["credential"] = "synthetic secret".into();
    assert!(serde_json::from_value::<layout::Layout>(injected).is_err());
}

#[test]
fn future_layouts_preserve_raw_and_require_explicit_recovery() {
    for mutation in ["kind", "axis", "field"] {
        let dir = tempfile::tempdir().unwrap();
        let db = dir.path().join("workspace.sqlite");
        let mut conn = init_workspace(db.to_str().unwrap()).unwrap();
        let first = layout::read(&mut conn, "desktop").unwrap();
        let saved = layout::write(
            &mut conn,
            Write {
                workspace_id: first.workspace_id,
                device_id: first.device_id,
                restore_epoch: first.restore_epoch,
                expected_revision: 0,
                layout: first.layout,
            },
        )
        .unwrap();
        let mut raw = serde_json::to_value(&saved).unwrap();
        match mutation {
            "kind" => raw["layout"]["dock_tree"]["kind"] = "future_kind".into(),
            "axis" => {
                raw["layout"]["dock_tree"] = serde_json::json!({"kind":"split","axis":"future","ratio":0.5,"first":{"kind":"tabs","panels":["01"],"active":"01"},"second":{"kind":"tabs","panels":["02"],"active":"02"}})
            }
            _ => raw["layout"]["future_field"] = true.into(),
        }
        let original = raw.to_string();
        conn.execute(
            "UPDATE workspace_meta SET value=?1 WHERE key='ui_layout_v1:desktop'",
            [&original],
        )
        .unwrap();
        let read = layout::read(&mut conn, "desktop").unwrap();
        assert_eq!(
            read.recovery_reason.as_deref(),
            Some("LAYOUT_COMPONENT_OR_SCHEMA_UNSUPPORTED")
        );
        assert!(
            layout::write(
                &mut conn,
                Write {
                    workspace_id: read.workspace_id.clone(),
                    device_id: read.device_id.clone(),
                    restore_epoch: read.restore_epoch.clone(),
                    expected_revision: read.revision,
                    layout: read.layout.clone()
                }
            )
            .is_err()
        );
        assert_eq!(
            conn.query_row(
                "SELECT value FROM workspace_meta WHERE key='ui_layout_v1:desktop'",
                [],
                |r| r.get::<_, String>(0)
            )
            .unwrap(),
            original
        );
        assert_eq!(
            layout::recover(
                &mut conn,
                Recover {
                    workspace_id: read.workspace_id,
                    device_id: read.device_id,
                    restore_epoch: read.restore_epoch,
                    expected_revision: read.revision,
                    viewport_width: 800.0,
                    viewport_height: 600.0
                }
            )
            .unwrap()
            .revision,
            2
        );
    }
}
#[test]
fn restored_workspace_requires_current_epoch_and_explicit_cas_recovery() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("workspace.sqlite");
    let mut conn = init_workspace(db.to_str().unwrap()).unwrap();
    let first = layout::read(&mut conn, "desktop").unwrap();
    let saved = layout::write(
        &mut conn,
        Write {
            workspace_id: first.workspace_id,
            device_id: first.device_id,
            restore_epoch: first.restore_epoch,
            expected_revision: 0,
            layout: first.layout,
        },
    )
    .unwrap();
    let original: String = conn
        .query_row(
            "SELECT value FROM workspace_meta WHERE key='ui_layout_v1:desktop'",
            [],
            |r| r.get(0),
        )
        .unwrap();
    let tx = conn.transaction().unwrap();
    archeaxis_store_sqlite::authorization_fence::install_after_restore(&tx).unwrap();
    tx.commit().unwrap();
    let read = layout::read(&mut conn, "desktop").unwrap();
    assert_ne!(read.restore_epoch, saved.restore_epoch);
    assert_eq!(
        read.recovery_reason.as_deref(),
        Some("LAYOUT_RESTORE_CONFIRMATION_REQUIRED")
    );
    let mut recover = Recover {
        workspace_id: read.workspace_id.clone(),
        device_id: read.device_id.clone(),
        restore_epoch: saved.restore_epoch,
        expected_revision: 1,
        viewport_width: 800.0,
        viewport_height: 600.0,
    };
    assert!(layout::recover(&mut conn, recover.clone()).is_err());
    assert!(
        layout::write(
            &mut conn,
            Write {
                workspace_id: read.workspace_id.clone(),
                device_id: read.device_id.clone(),
                restore_epoch: read.restore_epoch.clone(),
                expected_revision: 1,
                layout: read.layout
            }
        )
        .is_err()
    );
    assert_eq!(
        conn.query_row(
            "SELECT value FROM workspace_meta WHERE key='ui_layout_v1:desktop'",
            [],
            |r| r.get::<_, String>(0)
        )
        .unwrap(),
        original
    );
    recover.restore_epoch = read.restore_epoch;
    let recovered = layout::recover(&mut conn, recover.clone()).unwrap();
    assert_eq!(recovered.recovery_reason, None);
    assert!(layout::recover(&mut conn, recover).is_err());
    assert_eq!(
        layout::write(
            &mut conn,
            Write {
                workspace_id: recovered.workspace_id,
                device_id: recovered.device_id,
                restore_epoch: recovered.restore_epoch,
                expected_revision: 2,
                layout: recovered.layout
            }
        )
        .unwrap()
        .revision,
        3
    );
}

#[test]
fn malformed_layouts_and_identity_records_are_rejected_without_overwrite() {
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("workspace.sqlite");
    let mut conn = init_workspace(db.to_str().unwrap()).unwrap();
    let first = layout::read(&mut conn, "desktop").unwrap();
    for ratio in [0.0, 0.95, f64::NAN] {
        let mut prefs = first.layout.clone();
        prefs.registered_panels = vec!["01".into(), "02".into()];
        prefs.dock_tree = Dock::Split {
            axis: layout::Axis::Horizontal,
            ratio,
            first: Box::new(Dock::Tabs {
                panels: vec!["01".into()],
                active: "01".into(),
            }),
            second: Box::new(Dock::Tabs {
                panels: vec!["02".into()],
                active: "02".into(),
            }),
        };
        assert!(layout::validate(&prefs).is_err());
    }
    let mut prefs = first.layout.clone();
    prefs.floating_bounds.insert(
        "01".into(),
        Bounds {
            x: 0.0,
            y: 0.0,
            width: 500.0,
            height: 300.0,
        },
    );
    assert!(layout::validate(&prefs).is_err());
    prefs = first.layout.clone();
    prefs.registered_panels.push("02".into());
    assert!(layout::validate(&prefs).is_err());
    let saved = layout::write(
        &mut conn,
        Write {
            workspace_id: first.workspace_id,
            device_id: first.device_id,
            restore_epoch: first.restore_epoch,
            expected_revision: 0,
            layout: first.layout,
        },
    )
    .unwrap();
    for (key, value) in [
        ("workspace_id", serde_json::json!("b".repeat(32))),
        ("device_id", serde_json::json!("other")),
        ("revision", serde_json::json!(-1)),
        ("revision", serde_json::json!(9007199254740992i64)),
    ] {
        let mut raw = serde_json::to_value(&saved).unwrap();
        raw[key] = value;
        let original = raw.to_string();
        conn.execute(
            "UPDATE workspace_meta SET value=?1 WHERE key='ui_layout_v1:desktop'",
            [&original],
        )
        .unwrap();
        assert!(layout::read(&mut conn, "desktop").is_err());
        assert_eq!(
            conn.query_row(
                "SELECT value FROM workspace_meta WHERE key='ui_layout_v1:desktop'",
                [],
                |r| r.get::<_, String>(0)
            )
            .unwrap(),
            original
        );
    }
}
