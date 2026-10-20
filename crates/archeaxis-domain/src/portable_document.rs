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
/// Only declared business-reference fields are visited; unknown editor data is
/// opaque and must not become an implicit source-read permission.
fn research_refs(editor: &Value) -> Vec<&Value> {
    let research = &editor["attrs"]["archeaxis_research"];
    let mut values = Vec::new();
    if let Some(materials) = research["materials"].as_array() {
        values.extend(materials.iter().map(|material| &material["reference"]));
    }
    for section in [
        "hypotheses",
        "methods",
        "experiments",
        "counterevidence",
        "unresolved",
    ] {
        if let Some(entries) = research[section].as_array() {
            for entry in entries {
                if let Some(references) = entry["references"].as_array() {
                    values.extend(references);
                }
            }
        }
    }
    if let Some(conclusions) = research["conclusions"].as_array() {
        for entry in conclusions {
            for field in ["sources", "basis"] {
                if let Some(references) = entry[field].as_array() {
                    values.extend(references);
                }
            }
        }
    }
    values
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
    for reference in research_refs(&snapshot["editor_json"]) {
        if reference["kind"] == "source" {
            let id = reference["source_id"]
                .as_str()
                .ok_or(bad("missing research source"))?;
            let sha = reference["sha256"]
                .as_str()
                .ok_or(bad("missing research source hash"))?;
            if refs
                .insert(id.to_owned(), sha.to_owned())
                .is_some_and(|old| old != sha)
            {
                return Err(bad("conflicting research source identity"));
            }
        }
    }
    Ok(refs)
}
fn research_quote(material: &Value) -> Option<Value> {
    material.get("citation").map(|citation| {
        json!({"kind":"research_citation","material_id":material["id"],
        "source_id":material["reference"]["source_id"],"citation":citation})
    })
}
/// Only the declared historical citation shape grants a source dependency.
/// Unknown historical metadata stays opaque and cannot request local CAS bytes.
fn historical_refs(
    references: &mut BTreeMap<String, String>,
    anchors: &[Value],
) -> Result<(), Error> {
    for anchor in anchors {
        if anchor["kind"] != "research_citation" {
            continue;
        }
        let id = anchor["source_id"]
            .as_str()
            .filter(|id| !id.is_empty())
            .ok_or(bad("missing historical source identity"))?;
        let citation = &anchor["citation"];
        let digest = citation["source_sha256"]
            .as_str()
            .ok_or(bad("missing historical source hash"))?;
        if citation["schema"] != "archeaxis.research-citation/v1"
            || digest.len() != 64
            || !digest.bytes().all(|byte| byte.is_ascii_hexdigit())
            || citation["read_snapshot_sha256"] != digest
        {
            return Err(bad("historical source snapshot identity invalid"));
        }
        if references
            .insert(id.to_owned(), digest.to_owned())
            .is_some_and(|old| old != digest)
        {
            return Err(bad("conflicting historical source identity"));
        }
    }
    Ok(())
}
pub fn export(conn: &Connection, id: &str) -> Result<Package, Error> {
    let snapshot = document::read(conn, id, None)?;
    let mut historical_anchors = if let Some(source) = snapshot["source_id"].as_str() {
        let mut stmt=conn.prepare("SELECT anchor_id,source_revision,position FROM anchors WHERE source_id=?1 ORDER BY anchor_id LIMIT 5001")?;
        let rows=stmt.query_map([source],|r| Ok(json!({"anchor_id":r.get::<_,String>(0)?,"source_revision":r.get::<_,String>(1)?,"position":r.get::<_,String>(2)?})))?.collect::<Result<Vec<_>,_>>()?;
        if rows.len() > 5000 {
            return Err(bad("anchor budget exceeded"));
        }
        rows
    } else {
        Vec::new()
    };
    if let Some(materials) =
        snapshot["editor_json"]["attrs"]["archeaxis_research"]["materials"].as_array()
    {
        historical_anchors.extend(materials.iter().filter_map(research_quote));
    }
    // Imported locations remain historical. Carry them through subsequent
    // exchanges without promoting them to this workspace's active anchors.
    if let Some(inherited) =
        snapshot["revision_basis"]["portable_import"]["historical_anchors"].as_array()
    {
        historical_anchors.extend(inherited.iter().cloned());
    }
    // Ordinary saves intentionally have no inherited revision/authorization
    // basis. The immutable import origin is v1 of this same document; inspect
    // only its historical locations, never export arbitrary prior versions.
    let initial_basis: Option<String> = conn.query_row(
        "SELECT revision_basis FROM document_versions WHERE document_id=?1 AND version=1",
        [id],
        |row| row.get(0),
    )?;
    let basis: Value = initial_basis
        .map(|raw| serde_json::from_str(&raw).map_err(|_| bad("invalid initial revision basis")))
        .transpose()?
        .unwrap_or(Value::Null);
    if let Some(inherited) = basis["portable_import"]["historical_anchors"].as_array() {
        historical_anchors.extend(inherited.iter().cloned());
    }
    let mut unique = BTreeSet::new();
    historical_anchors.retain(|value| unique.insert(value.to_string()));
    if historical_anchors.len() > 5000 {
        return Err(bad("anchor budget exceeded"));
    }
    let mut references = refs(&snapshot)?;
    historical_refs(&mut references, &historical_anchors)?;
    if references.len() > 128 {
        return Err(bad("source count limit exceeded"));
    }
    let mut objects = Vec::new();
    let mut total = 0usize;
    for (source_id, digest) in references {
        // Imported historical IDs remain provenance, not active locators. Resolve
        // their bytes only through this document's immutable explicit import map.
        let local_id = match basis["portable_import"]["source_mapping"].get(&source_id) {
            Some(value) => value
                .as_str()
                .ok_or(bad("invalid historical source mapping"))?,
            None => &source_id,
        };
        let (stored, name): (String, String) = conn.query_row(
            "SELECT sha256,original_name FROM sources WHERE source_id=?1",
            [local_id],
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
pub fn import(
    conn: &mut Connection,
    mut package: Package,
    request_id: &str,
) -> Result<Value, Error> {
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
    let mut expected = refs(&package.document)?;
    historical_refs(&mut expected, &package.historical_anchors)?;
    if expected.len() > 128 {
        return Err(bad("source count limit exceeded"));
    }
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
    // Document/Knowledge identities are workspace-local. This package only
    // transfers hash-bound Source objects, so never resolve a foreign ID against
    // an unrelated object that happens to exist in the destination workspace.
    if research_refs(&original_editor)
        .iter()
        .any(|reference| reference["kind"] != "source")
    {
        return Err(bad(
            "portable research requires hash-bound source references; document and knowledge dependencies are not bundled",
        ));
    }
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
    if let Some(research) = editor
        .get_mut("attrs")
        .and_then(|v| v.get_mut("archeaxis_research"))
    {
        fn remap(reference: &mut Value, mapping: &BTreeMap<String, String>) -> Result<(), Error> {
            if reference["kind"] == "source" {
                let old = reference["source_id"]
                    .as_str()
                    .ok_or(bad("missing research source identity"))?;
                reference["source_id"] = json!(
                    mapping
                        .get(old)
                        .ok_or(bad("missing research source mapping"))?
                );
            }
            Ok(())
        }
        if let Some(materials) = research.get_mut("materials").and_then(Value::as_array_mut) {
            for material in materials {
                // Captured source locations are historical in a new workspace.
                // Preserve the complete quote in the import receipt, without
                // minting a current Core anchor or losing its original identity.
                if let Some(quote) = research_quote(material) {
                    if !package.historical_anchors.contains(&quote) {
                        package.historical_anchors.push(quote);
                    }
                    material
                        .as_object_mut()
                        .ok_or(bad("invalid research material"))?
                        .remove("citation");
                }
                remap(&mut material["reference"], &mapping)?;
            }
        }
        for section in [
            "hypotheses",
            "methods",
            "experiments",
            "counterevidence",
            "unresolved",
        ] {
            if let Some(entries) = research.get_mut(section).and_then(Value::as_array_mut) {
                for entry in entries {
                    if let Some(references) =
                        entry.get_mut("references").and_then(Value::as_array_mut)
                    {
                        for reference in references {
                            remap(reference, &mapping)?;
                        }
                    }
                }
            }
        }
        if let Some(conclusions) = research
            .get_mut("conclusions")
            .and_then(Value::as_array_mut)
        {
            for entry in conclusions {
                for field in ["sources", "basis"] {
                    if let Some(references) = entry.get_mut(field).and_then(Value::as_array_mut) {
                        for reference in references {
                            remap(reference, &mapping)?;
                        }
                    }
                }
            }
        }
        if package.historical_anchors.len() > 5000 {
            return Err(bad("anchor budget exceeded"));
        }
    }
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
