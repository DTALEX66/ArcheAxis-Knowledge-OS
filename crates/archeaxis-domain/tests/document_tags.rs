use archeaxis_domain::document;
use archeaxis_store_sqlite::init_workspace;
use serde_json::{Value, json};

fn markdown(text: &str) -> Value {
    json!({"type":"doc","attrs":{"archeaxis_markup":"markdown","foreign":{"keep":true}},"content":[{"type":"paragraph","content":[{"type":"text","text":text}]}]})
}

#[test]
fn saved_tags_properties_and_history_share_the_document_version() {
    let dir = tempfile::tempdir().unwrap();
    let path = dir.path().join("tags.sqlite");
    let mut conn = init_workspace(path.to_str().unwrap()).unwrap();
    let editor = markdown(
        "---\ntags: [Read/Next, 中文, '🧠/练习']\nscore: 2\ndone: false\naliases: ['其他名称']\ncomment: '#not_a_tag'\n---\n#read/next #Learn #1984 #y1984",
    );
    let first = document::create_optional(&mut conn, None, None, "标签笔记", editor).unwrap();
    assert_eq!(
        first["tags"],
        json!([
            {"name":"Read/Next","key":"read/next"},{"name":"中文","key":"中文"},
            {"name":"🧠/练习","key":"🧠/练习"},{"name":"Learn","key":"learn"},{"name":"y1984","key":"y1984"}
        ])
    );
    assert_eq!(first["metadata_status"], "COMPLETE");
    assert_eq!(first["properties"]["score"], 2);
    assert_eq!(first["properties"]["done"], false);
    let id = first["document_id"].as_str().unwrap();
    let list = document::list_page(&mut conn, None).unwrap().0;
    assert_eq!(list[0]["tags"], first["tags"]);
    assert_eq!(list[0]["version"], first["version"]);
    assert!(list[0].get("properties").is_none());
    let revised = document::save(&mut conn, id, 1, markdown("#Updated/中文")).unwrap();
    assert_eq!(
        revised["tags"],
        json!([{"name":"Updated/中文","key":"updated/中文"}])
    );
    assert_eq!(document::read(&conn, id, Some(1)).unwrap(), first);
    let id = id.to_owned();
    drop(conn);
    let conn = init_workspace(path.to_str().unwrap()).unwrap();
    assert_eq!(document::read(&conn, &id, None).unwrap(), revised);
    assert_eq!(document::read(&conn, &id, Some(1)).unwrap(), first);
}

#[test]
fn markdown_syntax_does_not_create_phantom_tags() {
    let dir = tempfile::tempdir().unwrap();
    let mut conn = init_workspace(dir.path().join("syntax.sqlite").to_str().unwrap()).unwrap();
    let text = "# Heading\n`#code` \\#escaped <https://x/#fragment> https://x/#url [#label](https://x/#dest) [[#Wiki]]\n<!-- #comment -->\n```md\n#fenced\n```\n\n    #indented\n\n#real **#bold** #中文 #🧠";
    let saved = document::create_optional(&mut conn, None, None, "syntax", markdown(text)).unwrap();
    assert_eq!(
        saved["tags"],
        json!([{"name":"real","key":"real"},{"name":"bold","key":"bold"},{"name":"中文","key":"中文"},{"name":"🧠","key":"🧠"}])
    );
}

#[test]
fn malformed_properties_preserve_content_and_report_partial_without_blocking_save() {
    let dir = tempfile::tempdir().unwrap();
    let mut conn = init_workspace(dir.path().join("bad.sqlite").to_str().unwrap()).unwrap();
    for text in [
        "---\ntags: [broken\n---\n#body",
        "---\ntags: scalar\n---\n#body",
        "---\ntags: [first]\ntags: [second]\n---\n#body",
        "---\ntags: [hidden]\n#unterminated",
    ] {
        let saved =
            document::create_optional(&mut conn, None, None, "bad", markdown(text)).unwrap();
        assert_eq!(saved["text_projection"], text);
        assert_eq!(saved["metadata_status"], "PARTIAL");
        assert!(!saved["metadata_issues"].as_array().unwrap().is_empty());
    }
}

#[test]
fn rich_text_code_and_links_are_excluded_and_adjacent_marks_share_tag_text() {
    let dir = tempfile::tempdir().unwrap();
    let mut conn = init_workspace(dir.path().join("rich.sqlite").to_str().unwrap()).unwrap();
    let editor = json!({"type":"doc","content":[
        {"type":"paragraph","content":[{"type":"text","text":"#Re"},{"type":"text","text":"ad/中文","marks":[{"type":"bold"}]},{"type":"text","text":" #code","marks":[{"type":"code"}]},{"type":"text","text":" #link","marks":[{"type":"link","attrs":{"href":"https://example.org"}}]}]},
        {"type":"codeBlock","content":[{"type":"text","text":"#block"}]}
    ]});
    let saved = document::create_optional(&mut conn, None, None, "rich", editor).unwrap();
    assert_eq!(
        saved["tags"],
        json!([{"name":"Read/中文","key":"read/中文"}])
    );
    assert_eq!(saved["properties"], json!({}));
}

#[test]
fn empty_properties_unicode_sequences_and_projection_limits_are_explicit() {
    let dir = tempfile::tempdir().unwrap();
    let mut conn = init_workspace(dir.path().join("limits.sqlite").to_str().unwrap()).unwrap();
    let saved = document::create_optional(
        &mut conn,
        None,
        None,
        "unicode",
        markdown("\u{feff}---\r\n---\r\n#👩\u{200d}💻 #e\u{301}"),
    )
    .unwrap();
    assert_eq!(saved["metadata_status"], "COMPLETE");
    assert_eq!(saved["tags"].as_array().unwrap().len(), 2);
    let text = (0..257)
        .map(|i| format!("#tag{i}"))
        .collect::<Vec<_>>()
        .join(" ");
    let saved =
        document::create_optional(&mut conn, None, None, "bounded", markdown(&text)).unwrap();
    assert_eq!(saved["tags"].as_array().unwrap().len(), 256);
    assert_eq!(saved["metadata_status"], "PARTIAL");
    assert_eq!(saved["metadata_issues"], json!(["TAG_LIMIT"]));
    assert!(
        saved["text_projection"]
            .as_str()
            .unwrap()
            .ends_with("#tag256")
    );
    let bad = document::create_optional(
        &mut conn,
        None,
        None,
        "recursive",
        markdown("---\na: &a [*a]\n---\n#body"),
    )
    .unwrap();
    assert_eq!(bad["metadata_status"], "PARTIAL");
    assert_eq!(bad["tags"], json!([{"name":"body","key":"body"}]));
}

#[test]
fn list_metadata_stays_below_the_host_response_budget_without_discarding_saved_tags() {
    let dir = tempfile::tempdir().unwrap();
    let mut conn = init_workspace(dir.path().join("list-budget.sqlite").to_str().unwrap()).unwrap();
    let text = (0..40)
        .map(|i| format!("#tag{i}{}", "x".repeat(490)))
        .collect::<Vec<_>>()
        .join(" ");
    let saved =
        document::create_optional(&mut conn, None, None, "long-tags", markdown(&text)).unwrap();
    assert_eq!(saved["tags"].as_array().unwrap().len(), 40);
    let rows = document::list_page(&mut conn, None).unwrap().0;
    assert!(serde_json::to_vec(&rows[0]["tags"]).unwrap().len() <= 16 * 1024);
    assert_eq!(rows[0]["metadata_status"], "PARTIAL");
    assert_eq!(saved["metadata_status"], "COMPLETE");
    assert_eq!(
        document::read(&conn, saved["document_id"].as_str().unwrap(), None).unwrap(),
        saved
    );
}
