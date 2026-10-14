//! Bounded material identity. Reading material never promotes it to knowledge.
use rusqlite::{Connection, OptionalExtension};
use serde::{Deserialize, Serialize};
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(tag = "kind", rename_all = "snake_case", deny_unknown_fields)]
pub enum Material {
    Document {
        document_id: String,
        version: i64,
        content_sha256: String,
        block_id: Option<String>,
    },
    Transform {
        source_id: String,
        raw_sha256: String,
        job_id: String,
        transform_id: i64,
        transform_sha256: String,
    },
}
#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct Selection {
    pub start_utf16: usize,
    pub end_utf16: usize,
    pub quote_sha256: String,
}
pub fn hash(bytes: &[u8]) -> String {
    hex::encode(Sha256::digest(bytes))
}
fn offset(text: &str, wanted: usize) -> Option<usize> {
    let mut n = 0;
    for (i, c) in text.char_indices() {
        if n == wanted {
            return Some(i);
        }
        n += c.len_utf16();
        if n > wanted {
            return None;
        }
    }
    (n == wanted).then_some(text.len())
}
pub fn prepare(
    conn: &Connection,
    material: &Material,
    selection: Option<&Selection>,
) -> Result<(String, Value), String> {
    let (text, provenance) = match material {
        Material::Document {
            document_id,
            version,
            content_sha256,
            block_id,
        } => {
            let d = crate::document::read(conn, document_id, Some(*version))
                .map_err(|_| "material_document_missing")?;
            if d["content_sha256"] != *content_sha256 {
                return Err("material_revision_mismatch".into());
            }
            let text = if let Some(id) = block_id {
                d["blocks"]
                    .as_array()
                    .and_then(|a| a.iter().find(|b| b["block_id"] == *id))
                    .and_then(|b| b["text_projection"].as_str())
                    .ok_or("material_block_missing")?
            } else {
                d["text_projection"]
                    .as_str()
                    .ok_or("material_text_missing")?
            };
            (
                text.to_owned(),
                json!({"source_id":d["source_id"],"source_revision":d["source_revision"]}),
            )
        }
        Material::Transform {
            source_id,
            raw_sha256,
            job_id,
            transform_id,
            transform_sha256,
        } => {
            let row:Option<(String,String)>=conn.query_row("SELECT s.sha256,t.text FROM jobs j JOIN sources s ON s.source_id=j.input_ref JOIN transforms t ON t.transform_id=j.transform_id AND t.source_id=s.source_id WHERE j.job_id=?1 AND j.input_ref=?2 AND j.transform_id=?3 AND j.state='succeeded'",rusqlite::params![job_id,source_id,transform_id],|r|Ok((r.get(0)?,r.get(1)?))).optional().map_err(|_|"material_read_failed")?;
            let (raw, text) = row.ok_or("material_extraction_missing")?;
            if raw != *raw_sha256 || hash(text.as_bytes()) != *transform_sha256 {
                return Err("material_revision_mismatch".into());
            }
            (
                text,
                json!({"source_id":source_id,"source_revision":raw,"job_id":job_id,"transform_id":transform_id}),
            )
        }
    };
    let text = if let Some(s) = selection {
        if s.end_utf16 <= s.start_utf16 {
            return Err("material_selection_invalid".into());
        }
        let a = offset(&text, s.start_utf16).ok_or("material_selection_invalid")?;
        let b = offset(&text, s.end_utf16).ok_or("material_selection_invalid")?;
        let quote = &text[a..b];
        if hash(quote.as_bytes()) != s.quote_sha256 {
            return Err("material_quote_mismatch".into());
        }
        quote.to_owned()
    } else {
        text
    };
    if text.trim().is_empty() || text.len() > 128000 {
        return Err("material_context_bound".into());
    }
    let proof = json!({"material":material,"selection":selection,"provenance":provenance,"context_sha256":hash(text.as_bytes()),"bytes":text.len(),"authority":"unverified_material"});
    Ok((text, proof))
}
