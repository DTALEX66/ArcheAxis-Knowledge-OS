//! Authored research structure and relations on immutable Document snapshots.
//! These fields record claims and provenance; they never assert truth or run search.
use crate::{
    document::Error,
    object_reference::{self, Reference},
};
use rusqlite::Connection;
use serde::{Deserialize, Serialize};
use serde_json::Value;
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
        if r.schema != RELATION_SCHEMA || r.relations.len() > 256 {
            return Err(invalid("relation schema or count is unsupported"));
        }
        let mut seen = BTreeSet::new();
        for relation in &r.relations {
            id(&relation.id, &mut seen)?;
            if relation.label.len() > 1024 {
                return Err(invalid("relation label exceeds UTF-8 byte limit"));
            }
            object_reference::validate(conn, &relation.target)?;
        }
    }
    Ok(())
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
