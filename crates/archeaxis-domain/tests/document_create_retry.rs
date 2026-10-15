use archeaxis_domain::document;
use archeaxis_store_sqlite::init_workspace;
use serde_json::json;

#[test]
fn pinned_preparation_blocks_preserve_blank_lines_and_cas_across_restart() {
    let dir = tempfile::tempdir().unwrap();
    let path = dir.path().join("preparation.sqlite");
    let mut conn = init_workspace(path.to_str().unwrap()).unwrap();
    let editor = json!({"type":"doc","content":[
        {"type":"paragraph","attrs":{"block_id":"prep_first"},"content":[{"type":"text","text":"准备 😀"}]},
        {"type":"paragraph","attrs":{"block_id":"prep_blank"}},
        {"type":"paragraph","attrs":{"block_id":"prep_last"},"content":[{"type":"text","text":"尚无知识绑定"}]}
    ]});
    let first = document::create_optional_with_request(
        &mut conn,
        None,
        None,
        "教学准备草稿",
        editor.clone(),
        Some("preparation_frozen_fixture"),
    )
    .unwrap();
    let id = first["document_id"].as_str().unwrap().to_owned();
    assert_eq!(first["editor_json"], editor);
    assert_eq!(first["text_projection"], "准备 😀\n尚无知识绑定");
    assert_eq!(first["blocks"].as_array().unwrap().len(), 3);
    assert_eq!(first["blocks"][1]["block_id"], "prep_blank");
    assert_eq!(first["blocks"][1]["text_projection"], "");
    let mut revised = editor.clone();
    revised["content"][2]["content"][0]["text"] = json!("当前修订");
    let saved = document::save(&mut conn, &id, 1, revised.clone()).unwrap();
    assert_eq!(saved["version"], 2);
    assert_eq!(saved["editor_json"], revised);
    assert!(matches!(
        document::save(&mut conn, &id, 1, editor.clone()),
        Err(document::Error::Conflict(2))
    ));
    drop(conn);
    let mut conn = init_workspace(path.to_str().unwrap()).unwrap();
    assert_eq!(document::read(&conn, &id, Some(1)).unwrap(), first);
    assert_eq!(document::read(&conn, &id, None).unwrap(), saved);
    assert_eq!(
        document::create_optional_with_request(
            &mut conn,
            None,
            None,
            "教学准备草稿",
            editor,
            Some("preparation_frozen_fixture")
        )
        .unwrap(),
        first
    );
    assert_eq!(document::read(&conn, &id, None).unwrap(), saved);
}

#[test]
fn initial_create_retry_survives_restart_without_duplicate_or_overwriting_newer_draft() {
    let dir = tempfile::tempdir().unwrap();
    let path = dir.path().join("retry.sqlite");
    let mut conn = init_workspace(path.to_str().unwrap()).unwrap();
    let editor = json!({"type":"doc","content":[{"type":"paragraph","content":[{"type":"text","text":"不完整教学正文"}]}]});
    let first = document::create_optional_with_request(
        &mut conn,
        None,
        None,
        "草稿",
        editor.clone(),
        Some("client_attempt_1"),
    )
    .unwrap();
    let id = first["document_id"].as_str().unwrap();
    document::save(&mut conn,id,1,json!({"type":"doc","content":[{"type":"paragraph","content":[{"type":"text","text":"随后更新"}]}]})).unwrap();
    drop(conn);
    let mut conn = init_workspace(path.to_str().unwrap()).unwrap();
    let retry = document::create_optional_with_request(
        &mut conn,
        None,
        None,
        "草稿",
        editor.clone(),
        Some("client_attempt_1"),
    )
    .unwrap();
    assert_eq!(first, retry);
    assert_eq!(
        document::read(&conn, id, None).unwrap()["text_projection"],
        "随后更新"
    );
    assert!(matches!(
        document::create_optional_with_request(
            &mut conn,
            None,
            None,
            "different",
            editor,
            Some("client_attempt_1")
        ),
        Err(document::Error::Conflict(_))
    ));
    let count: i64 = conn
        .query_row("SELECT COUNT(*) FROM documents", [], |r| r.get(0))
        .unwrap();
    assert_eq!(count, 1);
    let versions: i64 = conn
        .query_row("SELECT COUNT(*) FROM document_versions", [], |r| r.get(0))
        .unwrap();
    assert_eq!(versions, 2);
}

#[test]
fn create_request_rejects_paths_and_keeps_unkeyed_creation_compatible() {
    let dir = tempfile::tempdir().unwrap();
    let mut conn = init_workspace(dir.path().join("retry.sqlite").to_str().unwrap()).unwrap();
    let editor = json!({"type":"doc","content":[]});
    for request in ["", "../a", "E:\\private", "dot.id"] {
        assert!(
            document::create_optional_with_request(
                &mut conn,
                None,
                None,
                "",
                editor.clone(),
                Some(request)
            )
            .is_err()
        );
    }
    let a = document::create_optional(&mut conn, None, None, "", editor.clone()).unwrap();
    let b = document::create_optional(&mut conn, None, None, "", editor).unwrap();
    assert_ne!(a["document_id"], b["document_id"]);
}
