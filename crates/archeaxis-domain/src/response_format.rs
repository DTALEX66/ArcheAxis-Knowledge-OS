//! Bounded request-level output shape. No expected values, prompts, references or truth claims.
use serde::de::{MapAccess, Visitor};
use serde::{Deserialize, Deserializer};
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::collections::BTreeMap;

const INVALID: &str = "invalid bounded response_format";
const OUTPUT: &str = "machine worker returned invalid structured output";

fn keys(value: &Value, names: &[&str]) -> bool {
    value.as_object().is_some_and(|map| {
        map.len() == names.len() && names.iter().all(|name| map.contains_key(*name))
    })
}
fn field_name(name: &str) -> bool {
    !name.is_empty()
        && name.len() <= 64
        && name.as_bytes()[0].is_ascii_alphabetic()
        && name.bytes().all(|b| b.is_ascii_alphanumeric() || b == b'_')
}

/// Required order is normalized; objects serialize in sorted key order. The format contains
/// ASCII strings/booleans/arrays only, so Python sort_keys/separators yields identical SHA bytes.
pub fn normalize(raw: &Value) -> Result<Value, &'static str> {
    if raw.to_string().len() > 8192
        || !keys(raw, &["type", "json_schema"])
        || raw["type"] != "json_schema"
    {
        return Err(INVALID);
    }
    let spec = &raw["json_schema"];
    let schema = &spec["schema"];
    if !keys(spec, &["name", "strict", "schema"])
        || spec["name"] != "archeaxis_response"
        || spec["strict"] != true
        || !keys(
            schema,
            &["type", "properties", "required", "additionalProperties"],
        )
        || schema["type"] != "object"
        || schema["additionalProperties"] != false
    {
        return Err(INVALID);
    }
    let properties = schema["properties"].as_object().ok_or(INVALID)?;
    if properties.is_empty() || properties.len() > 32 {
        return Err(INVALID);
    }
    for (name, field) in properties {
        if !field_name(name)
            || !keys(field, &["type"])
            || !field["type"]
                .as_str()
                .is_some_and(|t| ["string", "boolean", "integer", "number"].contains(&t))
        {
            return Err(INVALID);
        }
    }
    let required = schema["required"].as_array().ok_or(INVALID)?;
    if required.len() != properties.len() {
        return Err(INVALID);
    }
    let mut names = required
        .iter()
        .map(|v| v.as_str().ok_or(INVALID))
        .collect::<Result<Vec<_>, _>>()?;
    names.sort_unstable();
    if names
        .iter()
        .copied()
        .ne(properties.keys().map(String::as_str))
    {
        return Err(INVALID);
    }
    let mut normalized = raw.clone();
    normalized["json_schema"]["schema"]["required"] = json!(names);
    Ok(normalized)
}

pub fn optional(raw: Option<&Value>) -> Result<Option<Value>, &'static str> {
    raw.filter(|v| !v.is_null()).map(normalize).transpose()
}

pub fn equivalent(left: Option<&Value>, right: Option<&Value>) -> bool {
    matches!((optional(left), optional(right)), (Ok(a), Ok(b)) if a == b)
}

pub fn fingerprint(format: &Value) -> String {
    hex::encode(Sha256::digest(format.to_string().as_bytes()))
}

struct UniqueObject(BTreeMap<String, Value>);
impl<'de> Deserialize<'de> for UniqueObject {
    fn deserialize<D: Deserializer<'de>>(deserializer: D) -> Result<Self, D::Error> {
        struct ObjectVisitor;
        impl<'de> Visitor<'de> for ObjectVisitor {
            type Value = UniqueObject;
            fn expecting(&self, f: &mut std::fmt::Formatter) -> std::fmt::Result {
                f.write_str("a unique-key object")
            }
            fn visit_map<A: MapAccess<'de>>(self, mut map: A) -> Result<Self::Value, A::Error> {
                let mut values = BTreeMap::new();
                while let Some((key, value)) = map.next_entry::<String, Value>()? {
                    if values.insert(key, value).is_some() {
                        return Err(serde::de::Error::custom("duplicate output key"));
                    }
                }
                Ok(UniqueObject(values))
            }
        }
        deserializer.deserialize_map(ObjectVisitor)
    }
}

/// Parse the original string without fences/repair. Numbers must be finite; integers are
/// integer lexemes in the shared exact IEEE-754 range, never bool-as-int or rounded decimals.
pub fn validate_output(format: &Value, text: &str) -> Result<(), &'static str> {
    let format = normalize(format)?;
    if text.len() > 128_000 {
        return Err(OUTPUT);
    }
    let mut parser = serde_json::Deserializer::from_str(text);
    let UniqueObject(values) = UniqueObject::deserialize(&mut parser).map_err(|_| OUTPUT)?;
    parser.end().map_err(|_| OUTPUT)?;
    let properties = format["json_schema"]["schema"]["properties"]
        .as_object()
        .ok_or(OUTPUT)?;
    if values.len() != properties.len() {
        return Err(OUTPUT);
    }
    for (key, spec) in properties {
        let value = values.get(key).ok_or(OUTPUT)?;
        let valid = match spec["type"].as_str() {
            Some("string") => value.is_string(),
            Some("boolean") => value.is_boolean(),
            Some("number") => value.as_f64().is_some_and(f64::is_finite),
            Some("integer") => {
                (value.is_i64() || value.is_u64())
                    && value
                        .as_f64()
                        .is_some_and(|n| n.abs() <= 9_007_199_254_740_991.0)
            }
            _ => false,
        };
        if !valid {
            return Err(OUTPUT);
        }
    }
    Ok(())
}

/// The executor independently checks worker provenance and content before Core can publish it.
pub fn validate_worker(format: &Value, answer: &Value) -> Result<(), &'static str> {
    if answer["response_format"] != *format
        || answer["response_format_sha256"] != fingerprint(format)
        || answer["format_validation"] != "VALID"
        || answer["answer_source"] != "content"
        || answer["finish_reason"] != "stop"
        || answer["truncated"] != false
    {
        return Err(OUTPUT);
    }
    validate_output(format, answer["answer"].as_str().ok_or(OUTPUT)?)
}

#[cfg(test)]
mod tests {
    use super::*;
    fn format(kind: &str) -> Value {
        json!({"type":"json_schema","json_schema":{"name":"archeaxis_response","strict":true,"schema":{"type":"object","properties":{"value":{"type":kind}},"required":["value"],"additionalProperties":false}}})
    }
    #[test]
    fn format_only_and_strict_json_preserve_fact_neutrality() {
        let valid = normalize(&format("string")).unwrap();
        assert!(validate_output(&valid, r#"{"value":"a wrong factual answer"}"#).is_ok());
        for text in [
            r#"{"value":true}"#,
            "```json\n{\"value\":\"x\"}\n```",
            r#"{"value":"x","value":"y"}"#,
            r#"{"value":"x"}{}"#,
        ] {
            assert!(validate_output(&valid, text).is_err());
        }
        for key in [
            "const",
            "enum",
            "description",
            "default",
            "$ref",
            "expected",
        ] {
            let mut invalid = valid.clone();
            invalid["json_schema"]["schema"]["properties"]["value"][key] = json!("answer hint");
            assert!(normalize(&invalid).is_err());
        }
    }
    #[test]
    fn finite_numbers_and_exact_integer_range() {
        for text in [
            r#"{"value":true}"#,
            r#"{"value":NaN}"#,
            r#"{"value":1e400}"#,
            r#"{"value":9007199254740992}"#,
            r#"{"value":1.1}"#,
            r#"{"value":1.0}"#,
            r#"{"value":9007199254740991.1}"#,
        ] {
            assert!(validate_output(&format("integer"), text).is_err());
        }
        for text in [r#"{"value":1}"#, r#"{"value":-9007199254740991}"#] {
            assert!(validate_output(&format("integer"), text).is_ok());
        }
        assert!(validate_output(&format("number"), r#"{"value":1.5}"#).is_ok());
        assert!(validate_output(&format("number"), r#"{"value":false}"#).is_err());
    }
}

#[cfg(test)]
mod shared_vectors {
    use super::*;
    #[test]
    fn cross_language_format_sha_and_strict_output_vectors() {
        let vectors: Value = serde_json::from_str(include_str!(
            "../../../tests/fixtures/machine-response-format.json"
        ))
        .unwrap();
        for vector in vectors["formats"].as_array().unwrap() {
            let normalized = normalize(&vector["input"]).unwrap();
            assert_eq!(normalized, vector["normalized"]);
            assert_eq!(fingerprint(&normalized), vector["sha256"]);
            for case in vector["outputs"].as_array().unwrap() {
                assert_eq!(
                    validate_output(&normalized, case["text"].as_str().unwrap()).is_ok(),
                    case["valid"].as_bool().unwrap(),
                    "{}",
                    case["text"]
                );
            }
        }
    }
}
