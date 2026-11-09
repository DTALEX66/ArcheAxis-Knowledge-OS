//! Authored research structure and relations on immutable Document snapshots.
//! These fields record claims and provenance; they never assert truth or run search.
use crate::{
    document::Error,
    object_reference::{self, Reference},
};
use rusqlite::Connection;
use serde::{Deserialize, Serialize};
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::collections::BTreeSet;

pub const SCHEMA: &str = "archeaxis.research/v1";
pub const RELATION_SCHEMA: &str = "archeaxis.relations/v1";
#[derive(Debug, Clone, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct Research {
    pub schema: String,
    pub question: String,
    pub materials: Vec<Material>,
    pub hypotheses: Vec<Entry>,
    pub methods: Vec<Entry>,
    pub experiments: Vec<Entry>,
    pub counterevidence: Vec<Entry>,
    pub conclusions: Vec<Conclusion>,
    pub unresolved: Vec<Entry>,
}
#[derive(Debug, Clone, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct Material {
    pub id: String,
    pub note: String,
    pub reference: Reference,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub citation: Option<Citation>,
}
/// A captured raw UTF-8 quote bound to the existing immutable Core anchor.
/// Saving an authored note does not rerun current location or read source bytes.
#[derive(Debug, Clone, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct Citation {
    pub schema: String,
    pub anchor_id: String,
    pub source_sha256: String,
    pub anchor_position_sha256: String,
    pub quote: String,
    pub quote_sha256: String,
    pub read_snapshot_sha256: String,
}
fn digest(bytes: &[u8]) -> String {
    hex::encode(Sha256::digest(bytes))
}
fn citation(conn: &Connection, material: &Material, captured: &Citation) -> Result<(), Error> {
    let Reference::Source { source_id, sha256 } = &material.reference else {
        return Err(invalid("raw citation requires a pinned source reference"));
    };
    if captured.schema != "archeaxis.research-citation/v1"
        || captured.quote.is_empty()
        || captured.quote.len() > 16_384
        || captured.source_sha256 != *sha256
        || captured.read_snapshot_sha256 != *sha256
        || captured.quote_sha256 != digest(captured.quote.as_bytes())
    {
        return Err(invalid("research citation snapshot identity mismatch"));
    }
    let (stored_source, revision, position) = crate::anchor::get_anchor(conn, &captured.anchor_id)?
        .ok_or(invalid("research citation anchor is missing"))?;
    let locator: Value = serde_json::from_str(&position)
        .map_err(|_| invalid("research citation anchor is invalid"))?;
    let span = locator["end"]
        .as_u64()
        .zip(locator["start"].as_u64())
        .and_then(|(end, start)| end.checked_sub(start));
    if stored_source != *source_id
        || revision != *sha256
        || captured.anchor_position_sha256 != digest(position.as_bytes())
        || locator["type"] != "text"
        || locator["location_status"] != "located"
        || locator["checksum"] != captured.quote_sha256
        || span != Some(captured.quote.len() as u64)
    {
        return Err(invalid(
            "research citation does not match captured Core anchor",
        ));
    }
    Ok(())
}
#[derive(Debug, Clone, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct Entry {
    pub id: String,
    pub text: String,
    pub references: Vec<Reference>,
}
#[derive(Debug, Clone, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct Conclusion {
    pub id: String,
    pub text: String,
    pub sources: Vec<Reference>,
    pub basis: Vec<Reference>,
}
#[derive(Debug, Clone, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct Relations {
    pub schema: String,
    pub relations: Vec<Relation>,
}
#[derive(Debug, Clone, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct Relation {
    pub id: String,
    pub kind: RelationKind,
    pub label: String,
    pub target: Reference,
    #[serde(
        default,
        skip_serializing_if = "Option::is_none",
        deserialize_with = "deserialize_relation_presentation"
    )]
    pub presentation: Option<RelationPresentation>,
}
#[derive(Debug, Clone, Deserialize, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum RelationPresentation {
    Embed,
}
fn deserialize_relation_presentation<'de, D>(
    deserializer: D,
) -> Result<Option<RelationPresentation>, D::Error>
where
    D: serde::Deserializer<'de>,
{
    // Missing is legacy ordinary-link metadata; explicit null is not an enum.
    RelationPresentation::deserialize(deserializer).map(Some)
}
#[derive(Debug, Clone, Deserialize, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum RelationKind {
    Related,
    Supports,
    Contradicts,
    DependsOn,
}
fn invalid(message: &'static str) -> Error {
    Error::Invalid(message)
}
fn id(s: &str, seen: &mut BTreeSet<String>) -> Result<(), Error> {
    if s.is_empty()
        || s.len() > 128
        || !s
            .bytes()
            .all(|b| b.is_ascii_alphanumeric() || matches!(b, b'_' | b'-'))
        || !seen.insert(s.to_owned())
    {
        return Err(invalid(
            "research item IDs must be unique bounded ASCII tokens",
        ));
    }
    Ok(())
}
fn text(s: &str) -> Result<(), Error> {
    if s.len() > 16_384 {
        Err(invalid("research text exceeds UTF-8 byte limit"))
    } else {
        Ok(())
    }
}
fn references(conn: &Connection, refs: &[Reference], count: &mut usize) -> Result<(), Error> {
    *count += refs.len();
    if *count > 256 {
        return Err(invalid("research reference count exceeds limit"));
    }
    for reference in refs {
        object_reference::validate(conn, reference)?;
    }
    Ok(())
}
/// Share relation rules while keeping live writes distinct from historical
/// projections. Validate each target in order so the first error stays stable.
pub(crate) fn validate_relations_with(
    relations: &Relations,
    mut validate_target: impl FnMut(&Reference) -> Result<(), Error>,
) -> Result<(), Error> {
    if relations.schema != RELATION_SCHEMA || relations.relations.len() > 256 {
        return Err(invalid("relation schema or count is unsupported"));
    }
    let mut seen = BTreeSet::new();
    for relation in &relations.relations {
        id(&relation.id, &mut seen)?;
        if relation.label.len() > 1024 {
            return Err(invalid("relation label exceeds UTF-8 byte limit"));
        }
        validate_target(&relation.target)?;
    }
    Ok(())
}
pub fn validate_editor(conn: &Connection, editor: &Value) -> Result<(), Error> {
    if let Some(raw) = editor["attrs"].get("archeaxis_research") {
        let r: Research = serde_json::from_value(raw.clone())
            .map_err(|_| invalid("research metadata shape is invalid or unsupported"))?;
        if r.schema != SCHEMA {
            return Err(invalid("research schema is unsupported for new writes"));
        }
        text(&r.question)?;
        let count = r.materials.len()
            + r.hypotheses.len()
            + r.methods.len()
            + r.experiments.len()
            + r.counterevidence.len()
            + r.conclusions.len()
            + r.unresolved.len();
        if count > 256 {
            return Err(invalid("research item count exceeds limit"));
        }
        let mut seen = BTreeSet::new();
        let mut refs = 0;
        for m in &r.materials {
            id(&m.id, &mut seen)?;
            text(&m.note)?;
            references(conn, std::slice::from_ref(&m.reference), &mut refs)?;
            if let Some(captured) = &m.citation {
                citation(conn, m, captured)?;
            }
        }
        for entry in r
            .hypotheses
            .iter()
            .chain(&r.methods)
            .chain(&r.experiments)
            .chain(&r.counterevidence)
            .chain(&r.unresolved)
        {
            id(&entry.id, &mut seen)?;
            text(&entry.text)?;
            references(conn, &entry.references, &mut refs)?;
        }
        for c in &r.conclusions {
            id(&c.id, &mut seen)?;
            text(&c.text)?;
            references(conn, &c.sources, &mut refs)?;
            references(conn, &c.basis, &mut refs)?;
        }
    }
    if let Some(raw) = editor["attrs"].get("archeaxis_relations") {
        let r: Relations = serde_json::from_value(raw.clone())
            .map_err(|_| invalid("relation metadata shape is invalid or unsupported"))?;
        validate_relations_with(&r, |reference| object_reference::validate(conn, reference))?;
    }
    Ok(())
}

struct LocatedReference<'a> {
    entry_kind: &'static str,
    entry_id: &'a str,
    field: &'static str,
    index: usize,
    reference: &'a Reference,
}

// Historical metadata must remain readable even when a target has disappeared.
// Validate its bounded shape here; resolving targets is a separate observation.
fn located_references(r: &Research) -> Result<Vec<LocatedReference<'_>>, Error> {
    let item_count = r.materials.len()
        + r.hypotheses.len()
        + r.methods.len()
        + r.experiments.len()
        + r.counterevidence.len()
        + r.conclusions.len()
        + r.unresolved.len();
    if r.schema != SCHEMA || item_count > 256 {
        return Err(invalid(
            "research projection schema or item count is unsupported",
        ));
    }
    let mut seen = BTreeSet::new();
    let mut located = Vec::new();
    for material in &r.materials {
        id(&material.id, &mut seen)?;
        located.push(LocatedReference {
            entry_kind: "material",
            entry_id: &material.id,
            field: "reference",
            index: 0,
            reference: &material.reference,
        });
    }
    for (kind, entries) in [
        ("hypothesis", &r.hypotheses),
        ("method", &r.methods),
        ("experiment", &r.experiments),
        ("counterevidence", &r.counterevidence),
        ("unresolved", &r.unresolved),
    ] {
        for entry in entries {
            id(&entry.id, &mut seen)?;
            for (index, reference) in entry.references.iter().enumerate() {
                located.push(LocatedReference {
                    entry_kind: kind,
                    entry_id: &entry.id,
                    field: "references",
                    index,
                    reference,
                });
                if located.len() > 256 {
                    return Err(invalid("research reference count exceeds limit"));
                }
            }
        }
    }
    for conclusion in &r.conclusions {
        id(&conclusion.id, &mut seen)?;
        for (field, references) in [
            ("sources", &conclusion.sources),
            ("basis", &conclusion.basis),
        ] {
            for (index, reference) in references.iter().enumerate() {
                located.push(LocatedReference {
                    entry_kind: "conclusion",
                    entry_id: &conclusion.id,
                    field,
                    index,
                    reference,
                });
                if located.len() > 256 {
                    return Err(invalid("research reference count exceeds limit"));
                }
            }
        }
    }
    if located.len() > 256 {
        return Err(invalid("research reference count exceeds limit"));
    }
    for item in &located {
        object_reference::validate_shape(item.reference)?;
    }
    Ok(located)
}

/// Read-only observation of references actually stored in a research snapshot.
/// Target state is observed in the same SQLite snapshot but is not part of the
/// immutable document digest and does not assert factual or source verification.
pub fn reference_projection(
    conn: &Connection,
    id: &str,
    version: Option<i64>,
) -> Result<Value, Error> {
    let tx = conn.unchecked_transaction()?;
    let document = crate::document::read(&tx, id, version)?;
    let snapshot = json!({"document_id":document["document_id"],"version":document["version"],
        "content_sha256":document["content_sha256"]});
    let raw = document["editor_json"]["attrs"].get("archeaxis_research");
    let (status, references) = if let Some(raw) = raw {
        match serde_json::from_value::<Research>(raw.clone()) {
            Ok(research) => match located_references(&research) {
                Ok(located) => {
                    let mut results = Vec::with_capacity(located.len());
                    for item in located {
                        let object = match object_reference::resolve(&tx, item.reference) {
                            Ok(object) => Some(object),
                            Err(Error::NotFound | Error::Invalid(_)) => None,
                            Err(error) => return Err(error),
                        };
                        let mut projected = json!({"entry_kind":item.entry_kind,"entry_id":item.entry_id,
                            "field":item.field,"index":item.index,"reference":item.reference,
                            "status":if object.is_some(){"resolved"}else{"unavailable"},"object":object});
                        for field in ["version_relation", "current_version", "currentness"] {
                            if let Some(state) = projected["object"].get(field).cloned() {
                                projected[field] = state;
                            }
                        }
                        results.push(projected);
                    }
                    ("supported", results)
                }
                Err(_) => ("unsupported", Vec::new()),
            },
            Err(_) => ("unsupported", Vec::new()),
        }
    } else {
        ("absent", Vec::new())
    };
    tx.commit()?;
    Ok(
        json!({"schema":"archeaxis.research-reference-projection/v1","document":snapshot,
        "metadata_status":status,"references":references}),
    )
}

pub fn text_projection(editor: &Value) -> Option<String> {
    let raw = editor["attrs"].get("archeaxis_research")?;
    let r: Research = serde_json::from_value(raw.clone()).ok()?;
    if r.schema != SCHEMA {
        return None;
    }
    let mut parts = vec![r.question];
    parts.extend(r.materials.into_iter().map(|m| m.note));
    parts.extend(
        r.hypotheses
            .into_iter()
            .chain(r.methods)
            .chain(r.experiments)
            .chain(r.counterevidence)
            .chain(r.unresolved)
            .map(|e| e.text),
    );
    parts.extend(r.conclusions.into_iter().map(|c| c.text));
    Some(
        parts
            .into_iter()
            .filter(|s| !s.trim().is_empty())
            .collect::<Vec<_>>()
            .join("\n"),
    )
}
