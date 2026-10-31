//! Edited JSON Canvas export: immutable CAS structure plus explicit current block identities.
//! File/link/background declarations are preserved, never opened or rewritten.
use crate::document::Error;
use rusqlite::{Connection, OptionalExtension};
use serde_json::{Value, json};
use std::collections::{BTreeMap, HashSet};

fn invalid(message: &'static str) -> Error {
    Error::Invalid(message)
}

fn string<'a>(value: &'a Value, key: &str) -> Result<&'a str, Error> {
    value[key]
        .as_str()
        .ok_or(invalid("canvas string field is missing or invalid"))
}

fn color(value: &Value) -> bool {
    value.as_str().is_some_and(|s| {
        matches!(s, "1" | "2" | "3" | "4" | "5" | "6")
            || (s.len() == 7 && s.starts_with('#') && s[1..].bytes().all(|b| b.is_ascii_hexdigit()))
    })
}

fn optional_choice(value: &Value, key: &str, choices: &[&str]) -> Result<(), Error> {
    if let Some(v) = value.get(key) {
        if !v.as_str().is_some_and(|s| choices.contains(&s)) {
            return Err(invalid("invalid canvas optional enum"));
        }
    }
    Ok(())
}

fn validate(canvas: &Value) -> Result<(), Error> {
    if !canvas.is_object() {
        return Err(invalid("canvas root must be an object"));
    }
    let empty = Vec::new();
    let nodes = match canvas.get("nodes") {
        Some(v) => v
            .as_array()
            .ok_or(invalid("canvas nodes must be an array"))?,
        None => &empty,
    };
    let edges = match canvas.get("edges") {
        Some(v) => v
            .as_array()
            .ok_or(invalid("canvas edges must be an array"))?,
        None => &empty,
    };
    if nodes.len() > 5000 || edges.len() > 10000 {
        return Err(invalid("canvas export node or edge budget exceeded"));
    }
    let mut ids = HashSet::new();
    for node in nodes {
        let id = string(node, "id")?;
        if id.is_empty() || !ids.insert(id) {
            return Err(invalid("canvas node IDs must be unique and nonempty"));
        }
        for field in ["x", "y", "width", "height"] {
            let n = node[field]
                .as_i64()
                .ok_or(invalid("canvas geometry must be integer"))?;
            if matches!(field, "width" | "height") && n < 1 {
                return Err(invalid("canvas size must be positive"));
            }
        }
        if node.get("color").is_some_and(|v| !color(v)) {
            return Err(invalid("invalid canvas color"));
        }
        match string(node, "type")? {
            "text" => {
                string(node, "text")?;
            }
            "file" => {
                string(node, "file")?;
                if node
                    .get("subpath")
                    .is_some_and(|v| !v.as_str().is_some_and(|s| s.starts_with('#')))
                {
                    return Err(invalid("canvas file subpath must begin with #"));
                }
            }
            "link" => {
                string(node, "url")?;
            }
            "group" => {
                for field in ["label", "background"] {
                    if node.get(field).is_some() {
                        string(node, field)?;
                    }
                }
                optional_choice(node, "backgroundStyle", &["cover", "ratio", "repeat"])?;
            }
            _ => return Err(invalid("unsupported canvas node type")),
        }
    }
    let mut edge_ids = HashSet::new();
    for edge in edges {
        let id = string(edge, "id")?;
        if id.is_empty() || !edge_ids.insert(id) {
            return Err(invalid("canvas edge IDs must be unique and nonempty"));
        }
        if !ids.contains(string(edge, "fromNode")?) || !ids.contains(string(edge, "toNode")?) {
            return Err(invalid("canvas edge target is missing"));
        }
        for field in ["fromSide", "toSide"] {
            optional_choice(edge, field, &["top", "right", "bottom", "left"])?;
        }
        for field in ["fromEnd", "toEnd"] {
            optional_choice(edge, field, &["none", "arrow"])?;
        }
        if edge.get("color").is_some_and(|v| !color(v)) {
            return Err(invalid("invalid canvas edge color"));
        }
        if edge.get("label").is_some() {
            string(edge, "label")?;
        }
    }
    Ok(())
}

fn block_text(node: &Value, depth: usize) -> Result<String, Error> {
    if depth > 32 {
        return Err(invalid("canvas text nesting exceeds budget"));
    }
    match node["type"].as_str() {
        Some("text") => Ok(string(node, "text")?.to_owned()),
        Some("hardBreak") => Ok("\n".to_owned()),
        Some("paragraph" | "codeBlock") => {
            let mut result = String::new();
            if let Some(content) = node.get("content") {
                for child in content
                    .as_array()
                    .ok_or(invalid("canvas text block content must be an array"))?
                {
                    if !matches!(child["type"].as_str(), Some("text" | "hardBreak")) {
                        return Err(invalid(
                            "canvas mapped text block contains unsupported rich content",
                        ));
                    }
                    result.push_str(&block_text(child, depth + 1)?);
                }
            }
            Ok(result)
        }
        _ => Err(invalid(
            "canvas text mapping requires a paragraph or code block",
        )),
    }
}

/// `attrs.canvas_node_id` on every current top-level text block is mandatory.
/// A missing/deleted/duplicate/extra mapping fails instead of reverting old text.
pub fn rebuild(mut canvas: Value, editor: &Value) -> Result<Value, Error> {
    validate(&canvas)?;
    let mut replacements = BTreeMap::new();
    for block in editor["content"]
        .as_array()
        .ok_or(invalid("canvas export requires document content"))?
    {
        let id = block["attrs"]["canvas_node_id"]
            .as_str()
            .filter(|s| !s.is_empty())
            .ok_or(invalid(
                "every canvas document block requires an explicit canvas_node_id",
            ))?;
        if replacements
            .insert(id.to_owned(), block_text(block, 0)?)
            .is_some()
        {
            return Err(invalid("duplicate canvas text node mapping"));
        }
    }
    if let Some(nodes) = canvas.get_mut("nodes").and_then(Value::as_array_mut) {
        for node in nodes {
            if node["type"] == "text" {
                let text = replacements
                    .remove(node["id"].as_str().unwrap())
                    .ok_or(invalid("canvas text node has no current document mapping"))?;
                node["text"] = json!(text);
            }
        }
    }
    if !replacements.is_empty() {
        return Err(invalid(
            "canvas mapping does not identify an original text node",
        ));
    }
    Ok(canvas)
}

pub fn export(conn: &Connection, snapshot: &Value) -> Result<Value, Error> {
    let source_id = snapshot["source_id"]
        .as_str()
        .ok_or(invalid("canvas export requires an immutable source"))?;
    let source: Option<(String, String)> = conn
        .query_row(
            "SELECT sha256,original_name FROM sources WHERE source_id=?1",
            [source_id],
            |r| Ok((r.get(0)?, r.get(1)?)),
        )
        .optional()?;
    let (digest, name) = source.ok_or(Error::NotFound)?;
    if snapshot["source_revision"] != digest || !name.to_lowercase().ends_with(".canvas") {
        return Err(invalid(
            "canvas export requires the matching .canvas source revision",
        ));
    }
    let raw = archeaxis_store_sqlite::raw_objects::read_bounded(conn, &digest, 8 * 1024 * 1024)?;
    let original =
        serde_json::from_slice::<Value>(raw.strip_prefix(&[0xef, 0xbb, 0xbf]).unwrap_or(&raw))
            .map_err(|_| invalid("original canvas is not valid JSON"))?;
    let rebuilt = rebuild(original, &snapshot["editor_json"])?;
    let content = serde_json::to_string_pretty(&rebuilt)
        .map_err(|_| invalid("canvas serialization failed"))?;
    use sha2::{Digest, Sha256};
    let digest = format!("{:x}", Sha256::digest(content.as_bytes()));
    let manifest = json!({"schema":"archeaxis-canvas-export/v1","document":snapshot,"canvas_sha256":digest,
        "reconstruction_scope":"TEXT_NODE_PLAIN_TEXT_ONLY",
        "basis":"immutable_source_structure_with_current_explicit_text_node_mappings",
        "loss":[{"code":"json_serialization","message":"JSON whitespace and key ordering may differ; node and edge array order and unknown fields are preserved."},
            {"code":"text_node_plain_projection","message":"Mapped paragraph/code-block visible text and hard breaks replace Canvas Markdown text; link hrefs, bold/other rich-text marks and code-block language are not serialized as Markdown formatting. Exact editor JSON is retained in this manifest."},
            {"code":"references_only","message":"File, link and background declarations are preserved without opening targets or packaging attachments."}]});
    Ok(
        json!({"document_id":snapshot["document_id"],"version":snapshot["version"],"source_revision":snapshot["source_revision"],
        "format":"canvas","files":[{"path":"document.canvas","media_type":"application/json","content":content},
            {"path":"manifest.json","media_type":"application/json","content":serde_json::to_string_pretty(&manifest).unwrap()}]}),
    )
}

#[cfg(test)]
mod tests {
    use super::*;
    fn canvas() -> Value {
        json!({"plugin:root":{"keep":true},"nodes":[
        {"id":"a","type":"text","x":-4,"y":2,"width":100,"height":50,"text":"旧文","plugin:data":[1,2]},
        {"id":"f","type":"file","x":0,"y":0,"width":30,"height":40,"file":"../asset.png","subpath":"#块"},
        {"id":"l","type":"link","x":0,"y":0,"width":30,"height":40,"url":"plugin://kept"},
        {"id":"g","type":"group","x":0,"y":0,"width":300,"height":400,"background":"local.png","backgroundStyle":"ratio"}],
        "edges":[{"id":"e","fromNode":"a","toNode":"f","fromEnd":"none","toEnd":"arrow","plugin:edge":true}]})
    }
    fn editor() -> Value {
        json!({"type":"doc","content":[{"type":"paragraph","attrs":{"canvas_node_id":"a","block_id":"b"},"content":[{"type":"text","text":"新中文🙂"},{"type":"hardBreak"},{"type":"text","text":"第二行"}]}]})
    }
    #[test]
    fn only_current_text_changes_and_original_declarations_survive() {
        let old = canvas();
        let mut expected = old.clone();
        expected["nodes"][0]["text"] = json!("新中文🙂\n第二行");
        assert_eq!(rebuild(old, &editor()).unwrap(), expected);
        assert_eq!(
            rebuild(json!({}), &json!({"type":"doc","content":[]})).unwrap(),
            json!({})
        );
    }
    #[test]
    fn refuse_missing_duplicate_extra_nontext_mapping_and_unsupported_body() {
        for change in 0..5 {
            let mut e = editor();
            match change {
                0 => e["content"] = json!([]),
                1 => {
                    let b = e["content"][0].clone();
                    e["content"].as_array_mut().unwrap().push(b);
                }
                2 => e["content"][0]["attrs"]["canvas_node_id"] = json!("f"),
                3 => e["content"]
                    .as_array_mut()
                    .unwrap()
                    .push(json!({"type":"paragraph","content":[]})),
                _ => {
                    e["content"][0]["content"][0] =
                        json!({"type":"image","attrs":{"src":"https://example.invalid"}})
                }
            }
            assert!(rebuild(canvas(), &e).is_err(), "case {change}");
        }
    }
    #[test]
    fn refuse_invalid_canvas_without_guessing_or_dropping_fields() {
        for change in 0..5 {
            let mut c = canvas();
            match change {
                0 => c["nodes"][0]["width"] = json!(-1),
                1 => c["nodes"][1]["id"] = json!("a"),
                2 => c["edges"][0]["toNode"] = json!("missing"),
                3 => c["edges"][0]["toSide"] = json!("middle"),
                _ => c["nodes"][1]["subpath"] = json!("wrong"),
            };
            assert!(rebuild(c, &editor()).is_err());
        }
    }
}
