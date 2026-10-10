//! Existing archeaxis_template metadata on canonical immutable Document versions.
//! No DB, schema migration, runtime execution, qualification or read normalization.
use crate::document::{self, Error};
use rusqlite::Connection;
use serde::{Deserialize, Deserializer};
use serde_json::Value;
use std::{collections::{BTreeMap, BTreeSet}, sync::OnceLock};

pub const NAMESPACE: &str = "archeaxis_template";
pub const SCHEMA: &str = "archeaxis.template/v1";
const CONTRACT: &str = include_str!("../../../packages/contracts/v2/template-binding.schema.json");
#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct Binding {
    schema: String, template_id: String, discipline_id: String,
    fields: BTreeMap<String,String>, references: Vec<BoundReference>,
    learning_item_key: Option<String>,
}
#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct BoundReference {
    document_id: String, #[serde(deserialize_with="positive_version")] version: i64, block_id: Option<String>,
    relation: String, x: f64, y: f64,
}
fn positive_version<'de,D:Deserializer<'de>>(deserializer:D)->Result<i64,D::Error> {
    let value=Value::deserialize(deserializer)?;
    let parsed=value.as_i64().or_else(||value.as_f64().and_then(|number| {
        // JSON Schema integer admits 1.0 too. Float-encoded versions are only
        // accepted within exact IEEE754 integer range; canonical i64 literals retain full range.
        if number.is_finite() && number.fract()==0.0 && (1.0..=9007199254740991.0).contains(&number) {Some(number as i64)} else {None}
    }));
    parsed.filter(|version|*version>0).ok_or_else(||serde::de::Error::custom("positive exact document version required"))
}
fn bad(message: &'static str) -> Error { Error::Invalid(message) }
fn contract() -> &'static Value {
    static VALUE: OnceLock<Value> = OnceLock::new();
    VALUE.get_or_init(|| serde_json::from_str(CONTRACT).expect("compiled template contract must be valid JSON"))
}
fn allowed(key: &str, id: &str) -> bool {
    contract()["properties"][key]["enum"].as_array()
        .is_some_and(|values| values.iter().any(|value| value.as_str()==Some(id)))
}
fn raw(editor: &Value) -> Option<&Value> { editor.get("attrs").and_then(|attrs|attrs.get(NAMESPACE)) }
/// Structural admission only. Unknown legacy values never become a new recognized template.
fn shape(value: &Value) -> Result<Binding, Error> {
    if value.get("learning_item_key").is_none() { return Err(bad("template learning_item_key must be present, null allows an incomplete draft")); }
    let binding: Binding = serde_json::from_value(value.clone())
        .map_err(|_|bad("template shape or fields unsupported; preserve historical metadata unchanged"))?;
    if binding.schema!=SCHEMA || !allowed("template_id",&binding.template_id) || !allowed("discipline_id",&binding.discipline_id) {
        return Err(bad("template schema, template identity or discipline is unsupported"));
    }
    // Fields are descriptive strings, may be empty and may contain arbitrary inert text.
    // The existing Document codec owns the total 1 MiB envelope limit. No enum implies mastery.
    if binding.references.len()>100 { return Err(bad("template references exceed existing 100-reference limit")); }
    let mut seen=BTreeSet::new();
    for (index,reference) in binding.references.iter().enumerate() {
        if value["references"][index].get("block_id").is_none() {
            return Err(bad("template block_id must be present, null pins the whole document"));
        }
        if !reference.x.is_finite() || !reference.y.is_finite() { return Err(bad("template coordinates must be finite numbers")); }
        // Match the existing template and Document contracts, including valid legacy UTF8 IDs.
        // A block ID is bounded by the codec, but is not required to be an ASCII token.
        if reference.document_id.is_empty() || reference.version<1 {
            return Err(bad("template document identity must be nonempty and version positive"));
        }
        if reference.block_id.as_ref().is_some_and(|id|id.is_empty() || id.len()>128) {
            return Err(bad("template block identity must satisfy the existing Document codec UTF8 byte limit"));
        }
        if !seen.insert((&reference.document_id,reference.version,&reference.block_id,&reference.relation)) {
            return Err(bad("duplicate template reference relation"));
        }
    }
    if binding.learning_item_key.as_ref().is_some_and(|key|key.trim().is_empty()) {
        return Err(bad("template learning key must be null or a nonblank existing item identity"));
    }
    Ok(binding)
}
/// Same identity set as learning_items, without ensure/create helpers or any write.
/// All SQL identifiers are fixed Core constants, never user input.
fn learning_exists(conn: &Connection, key: &str) -> Result<bool,Error> {
    for (table,sql) in [
        ("card_references","SELECT EXISTS(SELECT 1 FROM card_references WHERE item_key=?1)"),
        ("learning_assessments","SELECT EXISTS(SELECT 1 FROM learning_assessments WHERE item_key=?1)"),
        ("learning_events","SELECT EXISTS(SELECT 1 FROM learning_events WHERE item_key=?1)"),
    ] {
        let exists:bool=conn.query_row("SELECT EXISTS(SELECT 1 FROM sqlite_master WHERE type='table' AND name=?1)",[table],|row|row.get(0))?;
        if exists && conn.query_row(sql,[key],|row|row.get::<_,bool>(0))? { return Ok(true); }
    }
    Ok(false)
}
fn validate(conn: &Connection, binding: &Binding) -> Result<(),Error> {
    for reference in &binding.references {
        let snapshot=document::read(conn,&reference.document_id,Some(reference.version))?;
        if snapshot["document_id"]!=reference.document_id || snapshot["version"]!=reference.version {
            return Err(bad("template immutable reference identity mismatch"));
        }
        if let Some(id)=&reference.block_id {
            if !snapshot["blocks"].as_array().is_some_and(|blocks|blocks.iter().any(|block|block["block_id"].as_str()==Some(id.as_str()))) {
                return Err(bad("template immutable block reference not found"));
            }
        }
    }
    if let Some(key)=&binding.learning_item_key {
        if !learning_exists(conn,key)? { return Err(bad("template learning item identity not present in the canonical learning queue")); }
    }
    let _=&binding.fields; // Descriptive fields are carried unchanged, never evaluated.
    Ok(())
}
/// Called inside Document append's existing transaction, after expected_version check.
/// expected=0 is the actual initial write. Idempotent creation replays never call append.
/// Read/export paths keep all historical JSON and do not call this validator.
/// A historical unsupported payload may accompany ordinary body edits verbatim;
/// its namespace is read-only: removing, repairing or replacing it is not implicit migration.
// JS JSON.parse/stringify may encode a mathematically integral f64 as an
// integer. Accept only representation changes within the exact JS integer
// range; the caller restores the old Value before the new version is encoded.
fn exact_js_integer(number: &serde_json::Number) -> Option<i64> {
    const MAX: i64 = 9_007_199_254_740_991;
    if let Some(value) = number.as_i64() { return (-MAX..=MAX).contains(&value).then_some(value); }
    if let Some(value) = number.as_u64() { return (value <= MAX as u64).then_some(value as i64); }
    number.as_f64().filter(|value| value.is_finite() && value.fract() == 0.0 && value.abs() <= MAX as f64)
        .map(|value| value as i64)
}
fn lossless_js_carry(old: &Value, next: &Value) -> bool {
    if old == next { return true; }
    match (old, next) {
        (Value::Number(old), Value::Number(next)) => {
            let original = exact_js_integer(old);
            original.is_some() && original == exact_js_integer(next)
        }
        (Value::Array(old), Value::Array(next)) => old.len() == next.len()
            && old.iter().zip(next).all(|(old, next)| lossless_js_carry(old, next)),
        (Value::Object(old), Value::Object(next)) => old.len() == next.len()
            && old.iter().all(|(key, old)| next.get(key).is_some_and(|next| lossless_js_carry(old, next))),
        _ => false,
    }
}

pub fn validate_transition(conn: &Connection, id: &str, expected: i64, editor: &mut Value) -> Result<(),Error> {
    let previous=if expected>0 {Some(document::read(conn,id,Some(expected))?)} else {None};
    let old=previous.as_ref().and_then(|snapshot|raw(&snapshot["editor_json"]));
    let next=raw(editor);
    if let Some(old)=old {
        if shape(old).is_err() {
            if next.is_some_and(|next| lossless_js_carry(old, next)) {
                // Do not persist the browser's normalized representation. This
                // writes only a new body version, carrying the original opaque
                // metadata exactly as it was read from the pinned prior version.
                editor["attrs"].as_object_mut().expect("namespace requires attrs object")
                    .insert(NAMESPACE.to_owned(), old.clone());
                return Ok(());
            }
            return Err(bad("historical unsupported template metadata is read-only and must remain unchanged"));
        }
        if next.is_none() { return Err(bad("template namespace cannot be silently removed from an existing template object")); }
    }
    if let Some(next)=next {
        if editor.to_string().len()>1024*1024 { return Err(bad("template document envelope exceeds existing codec budget")); }
        validate(conn,&shape(next)?)?;
    }
    Ok(())
}
