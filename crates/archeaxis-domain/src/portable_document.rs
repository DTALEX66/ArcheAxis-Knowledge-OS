//! Bounded document exchange, not workspace restore or knowledge approval.
use crate::{
    document::{self, Error},
    source::{self, ImportOutcome},
};
use rusqlite::{Connection, OptionalExtension};
use serde::{Deserialize, Serialize};
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::collections::{BTreeMap, BTreeSet};

pub const MAX_BYTES: usize = 2 * 1024 * 1024;
#[derive(Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Object {
    pub source_id: String,
    pub sha256: String,
    pub original_name: String,
    pub bytes: Vec<u8>,
}
#[derive(Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Package {
    pub schema: String,
    pub document: Value,
    pub objects: Vec<Object>,
    pub historical_anchors: Vec<Value>,
}
fn bad(message: &'static str) -> Error {
    Error::Invalid(message)
}
fn hash(bytes: &[u8]) -> String {
    hex::encode(Sha256::digest(bytes))
}
fn refs(snapshot: &Value) -> Result<BTreeMap<String, String>, Error> {
    let mut refs = BTreeMap::new();
    if let Some(id) = snapshot["source_id"].as_str() {
        refs.insert(
            id.to_owned(),
            snapshot["source_revision"]
                .as_str()
                .ok_or(bad("missing source revision"))?
                .to_owned(),
        );
    }
    if let Some(nodes) =
        snapshot["editor_json"]["attrs"]["archeaxis_expression"]["nodes"].as_array()
    {
        for node in nodes {
            if let Some(media) = node.get("media").filter(|v| !v.is_null()) {
                let id = media["source_id"]
                    .as_str()
                    .ok_or(bad("missing media source"))?;
                let digest = media["sha256"].as_str().ok_or(bad("missing media hash"))?;
                if refs
                    .insert(id.to_owned(), digest.to_owned())
                    .is_some_and(|old| old != digest)
                {
                    return Err(bad("conflicting source identity"));
                }
            }
        }
    }
    Ok(refs)
}
pub fn export(conn: &Connection, id: &str) -> Result<Package, Error> {
    let snapshot = document::read(conn, id, None)?;
    let mut objects = Vec::new();
    let mut total = 0usize;
    let references = refs(&snapshot)?;
    if references.len() > 128 {
        return Err(bad("source count limit exceeded"));
    }
    for (source_id, digest) in references {
        let (stored, name): (String, String) = conn.query_row(
            "SELECT sha256,original_name FROM sources WHERE source_id=?1",
            [&source_id],
            |r| Ok((r.get(0)?, r.get(1)?)),
        )?;
        if stored != digest {
            return Err(bad("source identity changed"));
        }
        let bytes =
            archeaxis_store_sqlite::raw_objects::read_bounded(conn, &digest, MAX_BYTES - total)?;
        total += bytes.len();
        objects.push(Object {
            source_id,
            sha256: digest,
            original_name: name,
            bytes,
        });
    }
    let historical_anchors = if let Some(source) = snapshot["source_id"].as_str() {
        let mut stmt=conn.prepare("SELECT anchor_id,source_revision,position FROM anchors WHERE source_id=?1 ORDER BY anchor_id LIMIT 5001")?;
        let rows=stmt.query_map([source],|r| Ok(json!({"anchor_id":r.get::<_,String>(0)?,"source_revision":r.get::<_,String>(1)?,"position":r.get::<_,String>(2)?})))?.collect::<Result<Vec<_>,_>>()?;
        if rows.len() > 5000 {
            return Err(bad("anchor budget exceeded"));
        }
        rows
    } else {
        Vec::new()
    };
    let package = Package {
        schema: "archeaxis.document-package/v1".into(),
        document: snapshot,
        objects,
        historical_anchors,
    };
    if serde_json::to_vec(&package)
        .map_err(|_| bad("package serialization failed"))?
        .len()
        > 16 * 1024 * 1024
    {
        return Err(bad("serialized package budget exceeded"));
    }
    Ok(package)
}
pub fn import(conn: &mut Connection, package: Package, request_id: &str) -> Result<Value, Error> {
    if serde_json::to_vec(&package)
        .map_err(|_| bad("package serialization failed"))?
        .len()
        > 16 * 1024 * 1024
    {
        return Err(bad("serialized package budget exceeded"));
    }
    if package.schema != "archeaxis.document-package/v1"
        || package.objects.len() > 128
        || package.historical_anchors.len() > 5000
    {
        return Err(bad("unsupported or oversized package"));
    }
    let expected = refs(&package.document)?;
    let mut seen = BTreeSet::new();
    let mut total = 0usize;
    for object in &package.objects {
        total = total
            .checked_add(object.bytes.len())
            .ok_or(bad("byte budget exceeded"))?;
        if total > MAX_BYTES
            || object.original_name.len() > 1024
            || !seen.insert(object.source_id.clone())
            || expected.get(&object.source_id) != Some(&object.sha256)
            || hash(&object.bytes) != object.sha256
        {
            return Err(bad("object identity or byte budget invalid"));
        }
    }
    if seen.len() != expected.len() {
        return Err(bad("package objects incomplete"));
    }
    let original_editor = package.document["editor_json"].clone();
    for namespace in [
        "archeaxis_context_grant",
        "archeaxis_asset_context_grant",
        "archeaxis_ai_asset",
        "archeaxis_machine_evaluation",
        "archeaxis_machine_rubric",
    ] {
        if original_editor["attrs"].get(namespace).is_some() {
            return Err(bad(
                "authorization and machine governance documents are not portable imports",
            ));
        }
    }
    if hash(original_editor.to_string().as_bytes())
        != package.document["content_sha256"]
            .as_str()
            .ok_or(bad("missing editor hash"))?
    {
        return Err(bad("editor hash mismatch"));
    }
    let title = package.document["title"]
        .as_str()
        .ok_or(bad("missing title"))?;
    // Scope the caller's identity by the package digest, and separately bind it
    // in existing metadata so a retry cannot silently substitute another package.
    if request_id.is_empty()
        || request_id.len() > 96
        || !request_id
            .bytes()
            .all(|b| b.is_ascii_alphanumeric() || b == b'_' || b == b'-')
    {
        return Err(bad("invalid import request identity"));
    }
    let digest = hash(
        serde_json::to_vec(&package)
            .map_err(|_| bad("package serialization failed"))?
            .as_slice(),
    );
    let receipt_key = format!("portable_import_{request_id}");
    let target_id = format!("doc_req_{}", hash(receipt_key.as_bytes()));
    let tx = conn.transaction_with_behavior(rusqlite::TransactionBehavior::Immediate)?;
    if tx
        .query_row(
            "SELECT document_id FROM documents WHERE document_id=?1",
            [&target_id],
            |r| r.get::<_, String>(0),
        )
        .optional()?
        .is_some()
    {
        let saved = document::read(&tx, &target_id, Some(1))?;
        let basis = &saved["revision_basis"]["portable_import"];
        if basis["package_sha256"] != digest {
            return Err(bad("import request already bound to another package"));
        }
        return Ok(
            json!({"schema":"archeaxis.document-package-import/v1","package_sha256":digest,"document":saved,"source_mapping":basis["source_mapping"],"historical_anchors":basis["historical_anchors"],"anchor_registration":"NOT_EXECUTED","knowledge_admission":"NOT_EXECUTED"}),
        );
    }
    let mut mapping = BTreeMap::new();
    for object in &package.objects {
        let outcome = source::import_source_tx(&tx, &object.bytes, &object.original_name, None)?;
        let id = match outcome {
            ImportOutcome::Imported { source_id, .. }
            | ImportOutcome::Duplicate { source_id, .. } => source_id,
        };
        mapping.insert(object.source_id.clone(), id);
    }
    let mut editor = original_editor;
    if let Some(nodes) = editor
        .get_mut("attrs")
        .and_then(|v| v.get_mut("archeaxis_expression"))
        .and_then(|v| v.get_mut("nodes"))
        .and_then(Value::as_array_mut)
    {
        for node in nodes {
            if let Some(media) = node.get_mut("media").filter(|v| !v.is_null()) {
                let old = media["source_id"]
                    .as_str()
                    .ok_or(bad("missing media identity"))?;
                media["source_id"] = json!(mapping.get(old).ok_or(bad("missing source mapping"))?);
            }
        }
    }
    let source = package.document["source_id"]
        .as_str()
        .map(|old| {
            mapping
                .get(old)
                .cloned()
                .ok_or(bad("missing source mapping"))
        })
        .transpose()?;
    let revision = package.document["source_revision"].as_str();
    let saved = document::create_optional_tx(
        &tx,
        source.as_deref(),
        revision,
        title,
        editor,
        Some(&receipt_key),
    )?;
    let basis = json!({"portable_import":{"package_sha256":digest,"source_mapping":mapping,"historical_anchors":package.historical_anchors,"origin_document":{"document_id":package.document["document_id"],"version":package.document["version"],"source_id":package.document["source_id"],"source_revision":package.document["source_revision"],"content_sha256":package.document["content_sha256"]}}});
    tx.execute(
        "UPDATE document_versions SET revision_basis=?1 WHERE document_id=?2 AND version=1",
        rusqlite::params![basis.to_string(), saved["document_id"].as_str()],
    )?;
    let saved = document::read(&tx, &target_id, Some(1))?;
    let receipt = json!({"schema":"archeaxis.document-package-import/v1","package_sha256":digest,"document":saved,"source_mapping":mapping,"historical_anchors":package.historical_anchors,"anchor_registration":"NOT_EXECUTED","knowledge_admission":"NOT_EXECUTED"});
    tx.commit()?;
    Ok(receipt)
}
