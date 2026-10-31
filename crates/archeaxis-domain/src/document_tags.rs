//! Read-only, version-bound metadata projection. Original editor/CAS bytes remain authoritative.
//! Markdown parsing does not render HTML, execute YAML tags or fetch links.
use pulldown_cmark::{Event, Parser, Tag, TagEnd};
use serde_json::{Value, json};
use std::{collections::HashSet, ops::Range};
use unicode_general_category::{GeneralCategory, get_general_category};

const MAX_TAGS: usize = 256;
const MAX_FRONTMATTER: usize = 64 * 1024;

fn tag_char(c: char) -> bool {
    c.is_alphanumeric()
        || matches!(c, '_' | '-' | '/' | '\u{200d}')
        || matches!(
            get_general_category(c),
            GeneralCategory::NonspacingMark
                | GeneralCategory::SpacingMark
                | GeneralCategory::EnclosingMark
                | GeneralCategory::MathSymbol
                | GeneralCategory::CurrencySymbol
                | GeneralCategory::ModifierSymbol
                | GeneralCategory::OtherSymbol
        )
}

fn issue(issues: &mut Vec<&'static str>, code: &'static str) {
    if !issues.contains(&code) {
        issues.push(code);
    }
}

fn add_tag(
    name: &str,
    tags: &mut Vec<Value>,
    seen: &mut HashSet<String>,
    issues: &mut Vec<&'static str>,
) {
    let name = name.strip_prefix('#').unwrap_or(name);
    if name.is_empty()
        || name.len() > 512
        || !name.chars().all(tag_char)
        || name.chars().all(char::is_numeric)
        || name.split('/').any(str::is_empty)
    {
        issue(issues, "INVALID_TAG");
        return;
    }
    let key = name.to_lowercase();
    if seen.contains(&key) {
        return;
    }
    if tags.len() >= MAX_TAGS {
        issue(issues, "TAG_LIMIT");
        return;
    }
    seen.insert(key.clone());
    tags.push(json!({"name":name,"key":key}));
}

fn inline_tags(
    text: &str,
    allowed: Range<usize>,
    blocked: &[Range<usize>],
    tags: &mut Vec<Value>,
    seen: &mut HashSet<String>,
    issues: &mut Vec<&'static str>,
) {
    for (relative, _) in text[allowed.clone()].match_indices('#') {
        let pos = allowed.start + relative;
        if blocked.iter().any(|range| range.contains(&pos)) {
            continue;
        }
        let previous = text[..pos].chars().next_back();
        if previous.is_some_and(|c| {
            !c.is_whitespace() && !matches!(c, '(' | '[' | '{' | '"' | '\'' | '*' | '>')
        }) {
            continue;
        }
        let rest = &text[pos + 1..allowed.end];
        let end = rest
            .char_indices()
            .find(|(_, c)| !tag_char(*c))
            .map_or(rest.len(), |(i, _)| i);
        if end == 0 {
            continue;
        }
        let name = &rest[..end];
        // Numeric headings/anchors are ordinary text, not malformed tag assertions.
        if name.chars().all(char::is_numeric) {
            continue;
        }
        add_tag(name, tags, seen, issues);
    }
}

fn node_text(node: &Value, output: &mut String, depth: usize, issues: &mut Vec<&'static str>) {
    if depth > 32 {
        issue(issues, "EDITOR_DEPTH");
        return;
    }
    let kind = node["type"].as_str().unwrap_or("");
    if kind == "codeBlock"
        || node["marks"].as_array().is_some_and(|marks| {
            marks
                .iter()
                .any(|m| m["type"] == "code" || m["type"] == "link")
        })
    {
        output.push(' ');
        return;
    }
    if kind == "text" {
        output.push_str(node["text"].as_str().unwrap_or(""));
        return;
    }
    if kind == "hardBreak" {
        output.push('\n');
        return;
    }
    if ![
        "doc",
        "paragraph",
        "heading",
        "blockquote",
        "bulletList",
        "orderedList",
        "listItem",
        "taskList",
        "taskItem",
        "horizontalRule",
        "table",
        "tableRow",
        "tableCell",
        "tableHeader",
        "image",
        "evidenceReference",
    ]
    .contains(&kind)
    {
        issue(issues, "UNSUPPORTED_EDITOR_NODE");
        output.push('\n');
        return;
    }
    if let Some(children) = node["content"].as_array() {
        for child in children {
            node_text(child, output, depth + 1, issues);
        }
    }
    if kind != "doc" {
        output.push('\n');
    }
}

/// JSON-compatible YAML mapping only. Unsupported/invalid metadata never prevents ordinary saving.
pub(crate) fn project(editor: &Value, source_is_markdown: bool) -> Value {
    let mut tags = Vec::new();
    let mut seen = HashSet::new();
    let mut issues = Vec::new();
    let mut properties = json!({});
    let mut text = String::new();
    node_text(editor, &mut text, 0, &mut issues);
    let markdown = source_is_markdown || editor["attrs"]["archeaxis_markup"] == "markdown";
    let normalized = text.trim_start_matches('\u{feff}').replace("\r\n", "\n");
    let mut body = normalized.as_str();
    if markdown && body.starts_with("---\n") {
        let mut end = None;
        let mut offset = 4;
        for line in body[4..].split_inclusive('\n') {
            if matches!(line.trim_end_matches('\n'), "---" | "...") {
                end = Some((offset, offset + line.len()));
                break;
            }
            offset += line.len();
        }
        if let Some((end, start)) = end {
            if end > MAX_FRONTMATTER {
                issue(&mut issues, "FRONTMATTER_LIMIT");
            } else {
                // YAML's Value rejects duplicate mapping keys; direct JSON deserialization could silently overwrite them.
                match serde_yaml_ng::from_str::<serde_yaml_ng::Value>(&body[4..end])
                    .and_then(serde_yaml_ng::from_value::<Value>)
                {
                    Ok(Value::Object(map))
                        if map.len() <= 64
                            && serde_json::to_vec(&map)
                                .is_ok_and(|bytes| bytes.len() <= MAX_FRONTMATTER) =>
                    {
                        properties = Value::Object(map);
                        if let Some(value) = properties.get("tags") {
                            match value {
                                Value::Array(items) => {
                                    for item in items {
                                        if let Some(name) = item.as_str() {
                                            add_tag(name, &mut tags, &mut seen, &mut issues);
                                        } else {
                                            issue(&mut issues, "NON_TEXT_TAG");
                                        }
                                    }
                                }
                                Value::Null => (),
                                _ => issue(&mut issues, "TAGS_PROPERTY_REQUIRES_LIST"),
                            }
                        }
                    }
                    Ok(Value::Null) => (),
                    Ok(_) => issue(&mut issues, "PROPERTIES_MAPPING_REQUIRED_OR_LIMIT"),
                    Err(_) => issue(&mut issues, "INVALID_OR_UNSUPPORTED_YAML"),
                }
            }
            body = &body[start..];
        } else {
            issue(&mut issues, "UNTERMINATED_FRONTMATTER");
            // Do not reinterpret unclosed property text as body tags.
            body = "";
        }
    }
    if markdown && body.contains('#') {
        let mut blocked = Vec::new();
        let mut offset = 0;
        while let Some(start) = body[offset..].find("[[") {
            let start = offset + start;
            if let Some(end) = body[start + 2..].find("]]") {
                offset = start + 2 + end + 2;
                blocked.push(start..offset);
            } else {
                break;
            }
        }
        let mut suppress = 0usize;
        for (event, range) in Parser::new(body).into_offset_iter() {
            match event {
                Event::Start(Tag::CodeBlock(_) | Tag::Link { .. } | Tag::Image { .. }) => {
                    suppress += 1
                }
                Event::End(TagEnd::CodeBlock | TagEnd::Link | TagEnd::Image) => {
                    suppress = suppress.saturating_sub(1)
                }
                Event::Text(_) if suppress == 0 => {
                    inline_tags(body, range, &blocked, &mut tags, &mut seen, &mut issues)
                }
                _ => (),
            }
        }
    } else if !markdown {
        inline_tags(body, 0..body.len(), &[], &mut tags, &mut seen, &mut issues);
    }
    json!({"tags":tags,"properties":properties,"metadata_status":if issues.is_empty(){"COMPLETE"}else{"PARTIAL"},"metadata_issues":issues})
}
