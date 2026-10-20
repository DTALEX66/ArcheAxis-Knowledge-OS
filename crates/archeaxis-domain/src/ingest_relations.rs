//! Original-CAS link adapter into existing versioned Document relations.
//! No vault registry, filesystem walk, knowledge admission or worker execution.
use crate::{
    document, ingest_batches as batches,
    object_reference::{self, Reference},
    research, vault,
};
use rusqlite::{Connection, OptionalExtension};
use serde::{Deserialize, Serialize};
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::collections::{BTreeMap, BTreeSet};

#[derive(Debug)]
pub enum Error {
    Invalid(&'static str),
    NotFound,
    Conflict(i64),
    ScopeConflict,
    Sql(rusqlite::Error),
}
impl From<rusqlite::Error> for Error {
    fn from(error: rusqlite::Error) -> Self {
        Self::Sql(error)
    }
}
impl From<document::Error> for Error {
    fn from(error: document::Error) -> Self {
        match error {
            document::Error::Invalid(m) => Self::Invalid(m),
            document::Error::NotFound => Self::NotFound,
            document::Error::Conflict(v) => Self::Conflict(v),
            document::Error::Sql(e) => Self::Sql(e),
        }
    }
}

#[derive(Clone, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct DocumentBinding {
    pub document_id: String,
    pub version: i64,
    pub content_sha256: String,
}
#[derive(Clone, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct Target {
    pub ordinal: i64,
    pub source_id: String,
    pub source_revision: String,
    pub document: Option<DocumentBinding>,
}
#[derive(Clone, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct Apply {
    pub workspace_id: String,
    pub restore_epoch: String,
    pub source_id: String,
    pub source_revision: String,
    pub document_id: String,
    pub expected_version: i64,
    pub content_sha256: String,
    pub targets: Vec<Target>,
}
fn digest(bytes: &[u8]) -> String {
    hex::encode(Sha256::digest(bytes))
}
fn batch_error(e: batches::Error) -> Error {
    match e {
        batches::Error::Invalid(m) => Error::Invalid(m),
        batches::Error::Conflict => Error::ScopeConflict,
        batches::Error::NotFound => Error::NotFound,
        batches::Error::Sql(e) => Error::Sql(e),
    }
}
fn note(path: &str) -> bool {
    path.to_lowercase().ends_with(".md") || path.to_lowercase().ends_with(".markdown")
}

fn bound_member(
    conn: &Connection,
    batch: &str,
    ordinal: i64,
    source: &str,
    revision: &str,
    total: &mut usize,
) -> Result<batches::StoredMember, Error> {
    let member = batches::executable_member(conn, batch, ordinal).map_err(batch_error)?;
    if member.source_id.as_deref() != Some(source) || member.revision.as_deref() != Some(revision) {
        return Err(Error::Invalid(
            "source binding differs from imported batch member",
        ));
    }
    object_reference::validate(
        conn,
        &Reference::Source {
            source_id: source.into(),
            sha256: revision.into(),
        },
    )?;
    if member.byte_length < 0 || member.byte_length > 2 * 1024 * 1024 {
        return Err(Error::Invalid("relation input asset exceeds byte budget"));
    }
    *total += member.byte_length as usize;
    if *total > 8 * 1024 * 1024 {
        return Err(Error::Invalid(
            "relation input aggregate exceeds byte budget",
        ));
    }
    let bytes = archeaxis_store_sqlite::raw_objects::read_bounded(
        conn,
        revision,
        member.byte_length as usize,
    )?;
    if bytes.len() as i64 != member.byte_length || digest(&bytes) != revision {
        return Err(Error::Invalid("original CAS identity mismatch"));
    }
    // Raw Markdown can be consumed without scheduling a worker. An existing
    // note conversion must not be pending/failed or bound to another source.
    if note(&member.path) {
        if let Some(job) = &member.job_id {
            let row: Option<(String, String)> = conn
                .query_row(
                    "SELECT state,input_ref FROM jobs WHERE job_id=?1",
                    [job],
                    |r| Ok((r.get(0)?, r.get(1)?)),
                )
                .optional()?;
            if row
                .as_ref()
                .is_none_or(|(state, input)| state != "succeeded" || input != source)
            {
                return Err(Error::Invalid(
                    "bound note conversion is incomplete or has a different input",
                ));
            }
        }
    }
    Ok(member)
}
fn bound_document(
    conn: &Connection,
    binding: &DocumentBinding,
    source: &str,
    revision: &str,
) -> Result<Value, Error> {
    object_reference::validate_shape(&Reference::Document {
        document_id: binding.document_id.clone(),
        version: binding.version,
        block_id: None,
    })?;
    let doc = document::read(conn, &binding.document_id, Some(binding.version))?;
    if doc["source_id"] != source
        || doc["source_revision"] != revision
        || doc["content_sha256"] != binding.content_sha256
    {
        return Err(Error::Invalid(
            "document snapshot does not match source and content identity",
        ));
    }
    Ok(doc)
}

fn normalized(base: &str, target: &str) -> Option<String> {
    if target.is_empty() || target.starts_with('/') || target.contains(['\\', ':', '\0', '?', '%'])
    {
        return None;
    }
    let mut parts: Vec<&str> = base.split('/').filter(|p| !p.is_empty()).collect();
    for part in target.split('/') {
        match part {
            "" | "." => {}
            ".." => {
                parts.pop()?;
            }
            _ => parts.push(part),
        }
    }
    if parts.is_empty() {
        None
    } else {
        Some(parts.join("/"))
    }
}
fn candidates(path: &str) -> Vec<String> {
    let mut names = vec![path.to_owned()];
    if !path.rsplit('/').next().unwrap_or("").contains('.') {
        names.push(format!("{path}.md"));
        names.push(format!("{path}.markdown"));
    }
    names
}
fn resolve(
    link: &vault::Link,
    source_path: &str,
    paths: &BTreeMap<i64, String>,
) -> Result<i64, &'static str> {
    let target = &link.target;
    // This adapter does not parse Markdown titles or angle destinations. Do not
    // mistake their literal syntax for an existing member with a similar name.
    if link.syntax == "markdown"
        && (target.chars().any(char::is_whitespace) || target.contains(['<', '>', '\"', '\'']))
    {
        return Err("unsafe_or_unsupported_target");
    }
    if target.contains(':') || target.starts_with("//") {
        return Err("external_reference_not_followed");
    }
    let parent = source_path.rsplit_once('/').map(|(p, _)| p).unwrap_or("");
    let relative = normalized(parent, target).ok_or("unsafe_or_unsupported_target")?;
    let bare = !target.contains('/');
    let names = if link.syntax == "wiki" && !bare {
        let root = normalized("", target).ok_or("unsafe_or_unsupported_target")?;
        let root_names = candidates(&root);
        if paths
            .values()
            .any(|p| root_names.iter().any(|n| n.eq_ignore_ascii_case(p)))
        {
            root_names
        } else {
            candidates(&relative)
        }
    } else if link.syntax == "wiki" && bare {
        candidates(target)
    } else {
        candidates(&relative)
    };
    // Case-only collisions and basename collisions are ambiguous even on a
    // case-sensitive machine. Never choose whichever row happened to come first.
    let matches: Vec<_> = paths
        .iter()
        .filter(|(_, p)| {
            let p = if link.syntax == "wiki" && bare {
                p.rsplit('/').next().unwrap_or(p)
            } else {
                p.as_str()
            };
            names.iter().any(|n| n.to_lowercase() == p.to_lowercase())
        })
        .map(|(i, _)| *i)
        .collect();
    if matches.len() > 1 {
        Err("ambiguous_target")
    } else {
        matches.first().copied().ok_or("missing_target")
    }
}

pub fn apply(
    conn: &mut Connection,
    batch: &str,
    ordinal: i64,
    input: Apply,
) -> Result<Value, Error> {
    if input.targets.len() > 200 || input.expected_version < 1 {
        return Err(Error::Invalid("invalid relation binding budget or version"));
    }
    let tx = conn.transaction_with_behavior(rusqlite::TransactionBehavior::Immediate)?;
    batches::guard(&tx, &input.workspace_id, &input.restore_epoch).map_err(batch_error)?;
    let mut total = 0;
    let member = bound_member(
        &tx,
        batch,
        ordinal,
        &input.source_id,
        &input.source_revision,
        &mut total,
    )?;
    if !note(&member.path) || member.byte_length > 256 * 1024 {
        return Err(Error::Invalid("bounded original Markdown member required"));
    }
    let current = document::read(&tx, &input.document_id, None)?;
    if current["version"] != input.expected_version {
        return Err(Error::Conflict(current["version"].as_i64().unwrap()));
    }
    bound_document(
        &tx,
        &DocumentBinding {
            document_id: input.document_id.clone(),
            version: input.expected_version,
            content_sha256: input.content_sha256.clone(),
        },
        &input.source_id,
        &input.source_revision,
    )?;
    let bytes =
        archeaxis_store_sqlite::raw_objects::read_bounded(&tx, &input.source_revision, 256 * 1024)?;
    let markdown = std::str::from_utf8(&bytes)
        .map_err(|_| Error::Invalid("original Markdown must be UTF-8"))?;
    let mut targets = BTreeMap::new();
    for target in &input.targets {
        if targets.contains_key(&target.ordinal) {
            return Err(Error::Invalid("duplicate target ordinal"));
        }
        let m = bound_member(
            &tx,
            batch,
            target.ordinal,
            &target.source_id,
            &target.source_revision,
            &mut total,
        )?;
        if let Some(binding) = &target.document {
            bound_document(&tx, binding, &target.source_id, &target.source_revision)?;
        }
        targets.insert(target.ordinal, (target, m));
    }
    let paths = {
        let mut stmt = tx.prepare("SELECT ordinal,relative_path FROM ingest_batch_members WHERE batch_id=?1 ORDER BY ordinal")?;
        stmt.query_map([batch], |r| {
            Ok((r.get::<_, i64>(0)?, r.get::<_, String>(1)?))
        })?
        .collect::<Result<BTreeMap<_, _>, _>>()?
    };
    let links = vault::links_with_external(markdown);
    if links.len() > 256 {
        return Err(Error::Invalid(
            "original link count exceeds relation budget",
        ));
    }
    let mut editor = current["editor_json"].clone();
    research::validate_editor(&tx, &editor)?;
    let mut relations = editor["attrs"]["archeaxis_relations"]["relations"]
        .as_array()
        .cloned()
        .unwrap_or_default();
    let mut reports = Vec::new();
    let mut added = 0;
    let mut seen_ids = BTreeSet::new();
    for (index, link) in links.iter().enumerate() {
        if link.target.len() > 1024
            || link.label.as_ref().is_some_and(|v| v.len() > 1024)
            || link.fragment.as_ref().is_some_and(|v| v.len() > 1024)
        {
            return Err(Error::Invalid(
                "parsed link exceeds bounded response fields",
            ));
        }
        let mut report = json!({"ordinal":index,"target":link.target,"label":link.label,"syntax":link.syntax,"embed":link.embed,"fragment":link.fragment,"fragment_is_block":link.fragment_is_block,"status":"unresolved","reason":null,"relation_id":null,"target_ordinal":null});
        let target_ordinal = match resolve(link, &member.path, &paths) {
            Ok(id) => id,
            Err(reason) => {
                report["reason"] = json!(reason);
                reports.push(report);
                continue;
            }
        };
        report["target_ordinal"] = json!(target_ordinal);
        if link.fragment.is_some() {
            report["reason"] = json!("fragment_resolution_not_supported");
            reports.push(report);
            continue;
        }
        let Some((target, target_member)) = targets.get(&target_ordinal) else {
            report["reason"] = json!("target_binding_required");
            reports.push(report);
            continue;
        };
        let reference = if note(&target_member.path) {
            let Some(binding) = &target.document else {
                report["reason"] = json!("note_document_binding_required");
                reports.push(report);
                continue;
            };
            Reference::Document {
                document_id: binding.document_id.clone(),
                version: binding.version,
                block_id: None,
            }
        } else {
            Reference::Source {
                source_id: target.source_id.clone(),
                sha256: target.source_revision.clone(),
            }
        };
        let id = format!(
            "ingest_{}",
            digest(
                format!(
                    "{batch}|{ordinal}|{}|{}|{index}",
                    input.source_id, input.source_revision
                )
                .as_bytes()
            )
        );
        if !seen_ids.insert(id.clone()) {
            return Err(Error::Invalid("duplicate generated relation identity"));
        }
        let label = format!(
            "Original CAS {} · {}{}{}",
            input.source_revision,
            if link.embed {
                "embed reference (not rendered): "
            } else {
                "link: "
            },
            link.target,
            link.label
                .as_ref()
                .map(|s| format!(" | {s}"))
                .unwrap_or_default()
        );
        if label.len() > 1024 {
            return Err(Error::Invalid(
                "original link label exceeds relation budget",
            ));
        }
        let relation = json!({"id":id,"kind":"related","label":label,"target":reference});
        if let Some(existing) = relations.iter().find(|r| r["id"] == id) {
            if existing != &relation {
                return Err(Error::Conflict(input.expected_version));
            }
        } else {
            relations.push(relation);
            added += 1;
        }
        report["status"] = json!("resolved_reference");
        report["relation_id"] = json!(id);
        if link.embed {
            report["reason"] = json!("embed_rendering_not_supported");
        }
        reports.push(report);
    }
    if relations.len() > 256 {
        return Err(Error::Invalid("combined relation count exceeds budget"));
    }
    if added > 0 {
        let attrs = editor
            .as_object_mut()
            .ok_or(Error::Invalid("invalid editor"))?
            .entry("attrs")
            .or_insert_with(|| json!({}))
            .as_object_mut()
            .ok_or(Error::Invalid("invalid editor attributes"))?;
        attrs.insert(
            "archeaxis_relations".into(),
            json!({"schema":"archeaxis.relations/v1","relations":relations}),
        );
        document::save_tx(
            &tx,
            &input.document_id,
            input.expected_version,
            editor,
            None,
        )?;
    }
    let saved = document::read(&tx, &input.document_id, None)?;
    let receipt = json!({"schema":"archeaxis.ingest-relations/v1","workspace_id":input.workspace_id,"restore_epoch":input.restore_epoch,"batch_id":batch,"ordinal":ordinal,
        "input_kind":"immutable_original_markdown","source_id":input.source_id,"source_revision":input.source_revision,"relative_path":member.path,
        "document":saved,"added_relations":added,"links":reports,
        "loss":["original_source_links_not_current_document_body","markdown_subset_not_full_vault_compatibility","no_worker_conversion_or_knowledge_admission"]});
    tx.commit()?;
    Ok(receipt)
}
