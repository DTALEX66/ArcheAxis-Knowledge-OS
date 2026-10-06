//! Core custody for decoded video artifacts; worker observations remain immutable.
use crate::jobs::{JobError, LossReceipt};
use archeaxis_domain::source::{self, ImportOutcome, OriginInfo};
use archeaxis_sidecar_protocol::worker::Request;
use archeaxis_store_sqlite::raw_objects;
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::path::{Component, Path};

pub struct VerifiedArtifact {
    bytes: Vec<u8>,
    sha: String,
    name: String,
    kind: String,
    offset: Option<u64>,
}

/// No writes: validate the entire declared set before any CAS/Source publication.
pub fn prepare(
    root: &Path,
    req: &Request,
    loss: &LossReceipt,
) -> Result<Vec<VerifiedArtifact>, JobError> {
    let fail = || JobError::InvalidReceipt("video artifact declaration is unverifiable");
    raw_objects::reject_links(root)?;
    let canonical_root = root.canonicalize().map_err(|_| fail())?;
    let input = req.inputs.first().ok_or_else(fail)?;
    let output = loss.params.get("worker_output").ok_or_else(fail)?;
    if output["source_sha256"].as_str() != Some(input.sha256.as_str()) {
        return Err(fail());
    }
    let frames = output["frames"].as_array().ok_or_else(fail)?;
    if frames.len() > 3 {
        return Err(fail());
    }
    let mut declarations = Vec::new();
    for (index, frame) in frames.iter().enumerate() {
        let offset = frame["sampling_seek_requested_ms"]
            .as_u64()
            .ok_or_else(fail)?;
        let duration = output["duration_ms"].as_u64().ok_or_else(fail)?;
        if offset >= duration {
            return Err(fail());
        }
        declarations.push((
            frame,
            format!("video-frame-{index}.jpg"),
            "frame",
            Some(offset),
            8 * 1024 * 1024,
        ));
    }
    if let Some(audio) = output.get("audio_wav").filter(|v| !v.is_null()) {
        declarations.push((
            audio,
            "video-audio-16k-mono.wav".into(),
            "audio",
            None,
            128 * 1024 * 1024,
        ));
    }
    let mut verified = Vec::new();
    for (value, name, kind, offset, limit) in declarations {
        let path = Path::new(value["path"].as_str().ok_or_else(fail)?);
        if !path.is_absolute() || path.components().any(|c| matches!(c, Component::ParentDir)) {
            return Err(fail());
        }
        raw_objects::reject_links(path)?;
        let canonical = path.canonicalize().map_err(|_| fail())?;
        if !canonical.starts_with(&canonical_root) || canonical == canonical_root {
            return Err(fail());
        }
        let bytes = raw_objects::read_staged(path, limit)?;
        let sha = hex::encode(Sha256::digest(&bytes));
        if value["sha256"].as_str() != Some(sha.as_str())
            || value
                .get("bytes")
                .is_some_and(|v| v.as_u64() != Some(bytes.len() as u64))
        {
            return Err(fail());
        }
        verified.push(VerifiedArtifact {
            bytes,
            sha,
            name,
            kind: kind.into(),
            offset,
        });
    }
    for item in output["visual_results"].as_array().ok_or_else(fail)? {
        if item["source_sha256"].as_str() != Some(input.sha256.as_str())
            || !verified.iter().any(|a| {
                a.kind == "frame"
                    && item["frame_sha256"].as_str() == Some(a.sha.as_str())
                    && item["sampling_seek_requested_ms"].as_u64() == a.offset
            })
        {
            return Err(fail());
        }
    }
    Ok(verified)
}

/// Same transaction as job completion; references enter the existing backup source set.
pub fn adopt_tx(
    tx: &rusqlite::Transaction<'_>,
    req: &Request,
    artifacts: &[VerifiedArtifact],
) -> Result<Value, JobError> {
    let mut refs = Vec::new();
    for (index, artifact) in artifacts.iter().enumerate() {
        let origin = format!(
            "media.video/{}/attempt/{}/source/{}/artifact/{index}",
            req.job_id, req.attempt, req.inputs[0].sha256
        );
        let source_id = match source::import_source_tx(
            tx,
            &artifact.bytes,
            &artifact.name,
            Some(OriginInfo {
                kind: "import",
                origin_ref: &origin,
                original_name: Some(&artifact.name),
                received_at: None,
            }),
        )? {
            ImportOutcome::Imported { source_id, .. }
            | ImportOutcome::Duplicate { source_id, .. } => source_id,
        };
        refs.push(json!({"source_id": source_id, "sha256": artifact.sha, "bytes": artifact.bytes.len(), "kind": artifact.kind, "sampling_seek_requested_ms": artifact.offset, "origin_ref": origin}));
    }
    Ok(
        json!({"schema":"archeaxis.media-custody/v1","job_id":req.job_id,"attempt":req.attempt,"source_sha256":req.inputs[0].sha256,"authority":"core_verified_derived_custody_not_human_verified","artifacts":refs}),
    )
}
