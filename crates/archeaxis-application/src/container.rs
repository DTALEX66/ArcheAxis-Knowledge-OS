//! R15/F15 second half: a container's members become sources of their own.
//!
//! The archive worker extracts the members it could read and declares each one with
//! its digest. This module is the Core half: it verifies every declared member against
//! the bytes in the transfer area, imports each one as its own source **recording that
//! it came from this container**, and enqueues a job for each member whose name the
//! Core can resolve to a route.
//!
//! Two things are deliberately explicit:
//!
//! * the relation is recorded with the existing origin mechanism
//!   (`origin_kind = "archive-member"`, `origin_ref = "<container source_id>#<member>"`),
//!   so a member can be traced back to its container without a schema change and
//!   without inventing a second store of relations;
//! * a member whose name resolves to no route is imported anyway and reported as
//!   custody-only, because "we kept it but could not read it" is a fact, whereas
//!   dropping it would be a loss nobody can see.

use crate::attempts;
use crate::jobs::JobError;
use archeaxis_domain::source::{self, ImportOutcome, OriginInfo};
use rusqlite::{Connection, OptionalExtension};
use serde::Deserialize;
use sha2::{Digest, Sha256};
use std::io::Read;
use std::path::{Path, PathBuf};

/// The origin kind recorded for a member. The store's vocabulary is fixed
/// (`path`, `url`, `import`, `manual`), so the relation rides in the reference:
/// `"<container source_id>#<member path>"`. Inventing a kind outside that vocabulary
/// is NOT an option: `import_source_with_origin` uses `INSERT OR IGNORE`, so an
/// out-of-vocabulary kind would be dropped in silence, which is exactly what this
/// module must not allow - `expand_members` therefore verifies the relation landed.
pub const ORIGIN_KIND: &str = "import";
const MEMBER_LIMIT: usize = 50;
const MEMBER_BYTES_LIMIT: u64 = 64 * 1024 * 1024;

/// Transfer artifacts belong to one claimed attempt, never the shared members root.
pub fn attempt_root(staging: &Path, job_id: &str, attempt: u64) -> PathBuf {
    staging
        .join("archive-attempts")
        .join(sha256_hex(job_id.as_bytes()))
        .join(attempt.to_string())
}

/// The same absolute path in a form the Windows API opens at any depth.
///
/// `attempt_root` carries a 64-character job digest as one component, so a member path passes
/// MAX_PATH inside an ordinary worktree rather than only in an exotic one. Windows answers such
/// an open with ERROR_FILE_NOT_FOUND, which `expand_members` would otherwise report as a member
/// the worker failed to write. The worker writes those bytes through the same prefix
/// (`worker_archive._long_path`), so this is the read half of one contract, not a second path
/// space. Non-Windows and already-verbatim paths are returned unchanged.
fn verbatim(path: &Path) -> PathBuf {
    #[cfg(windows)]
    {
        let text = path.as_os_str().to_string_lossy();
        if path.is_absolute() && !text.starts_with(r"\\?\") {
            return PathBuf::from(format!(r"\\?\{text}"));
        }
    }
    path.to_path_buf()
}

/// One member the archive worker offered as a source.
#[derive(Debug, Clone, Deserialize)]
pub struct ArchiveMember {
    pub name: String,
    pub file: String,
    pub bytes: u64,
    pub sha256: String,
}

/// What one expansion produced.
#[derive(Debug, Default)]
pub struct Expansion {
    /// Sources imported for members, in declaration order.
    pub sources: Vec<String>,
    /// Members whose name resolved to a route, with the job that now reads them.
    pub jobs: Vec<String>,
    /// Members kept as sources but with no route that can read their bytes.
    pub custody_only: Vec<String>,
    /// Member containers kept as sources whose own expansion stopped at the nesting budget.
    /// They are not custody-only - the route exists - so a reader must not see them as unread.
    pub depth_limited: Vec<String>,
}

fn sha256_hex(bytes: &[u8]) -> String {
    let mut hasher = Sha256::new();
    hasher.update(bytes);
    hex::encode(hasher.finalize())
}

/// Preserve existing interoperable IDs; hash only filenames/parents that exceed
/// the runtime job-ID grammar. The member's real name stays in its source origin.
pub fn member_job_id(archive_job_id: &str, member_file: &str) -> String {
    let legacy = format!("{archive_job_id}-member-{member_file}");
    if legacy.len() <= 200
        && legacy
            .bytes()
            .all(|byte| byte.is_ascii_alphanumeric() || b"-_.".contains(&byte))
    {
        legacy
    } else {
        let identity = format!("archeaxis.archive-member/v1\0{archive_job_id}\0{member_file}");
        format!("member-{}", sha256_hex(identity.as_bytes()))
    }
}

/// The members the newest finished attempt of `archive_job_id` declared.
pub fn declared_members(
    conn: &Connection,
    archive_job_id: &str,
) -> Result<Vec<ArchiveMember>, JobError> {
    let content: Option<String> = conn
        .query_row(
            "SELECT content FROM job_outputs WHERE job_id=?1 AND kind='loss_report'
             ORDER BY attempt DESC LIMIT 1",
            [archive_job_id],
            |row| row.get(0),
        )
        .optional()?;
    let Some(content) = content else {
        return Ok(Vec::new());
    };
    let payload: serde_json::Value = serde_json::from_str(&content)
        .map_err(|_| JobError::InvalidReceipt("loss report is not JSON"))?;
    let declared = payload
        .get("params")
        .and_then(|params| params.get("structure"))
        .and_then(|structure| structure.get("extractable_members"))
        .and_then(|value| value.as_array())
        .cloned()
        .unwrap_or_default();
    let mut members: Vec<ArchiveMember> = Vec::new();
    for item in declared {
        members.push(
            serde_json::from_value(item)
                .map_err(|_| JobError::InvalidReceipt("a declared member is malformed"))?,
        );
    }
    Ok(members)
}

/// The route a member's own name selects, if any: (job kind, expected media type).
fn route_for_member(name: &str) -> Option<(&'static str, &'static str)> {
    // MIME alone cannot distinguish .canvas from ordinary .json.
    // Reuse only currently supported member routes. A nested container is selected here like
    // any other member: the bound on nesting is a property of the recorded chain, not of the
    // name, and is applied in `expand_members` (`CONTAINER_DEPTH_LIMIT`).
    let extension = Path::new(name)
        .extension()
        .and_then(|value| value.to_str())
        .unwrap_or("")
        .to_ascii_lowercase();
    let preferred = match extension.as_str() {
        "docx" | "pptx" | "xlsx" => Some("office"),
        "html" | "htm" | "xhtml" => Some("html"),
        "canvas" => Some("canvas"),
        "srt" | "vtt" => Some("subtitles"),
        "zip" | "tar" => Some("archive"),
        _ => None,
    };
    if let Some(kind) = preferred {
        return attempts::resolve_media_type(kind, name)
            .ok()
            .map(|media| (kind, media));
    }
    for kind in ["text", "pdf", "image"] {
        if let Ok(media) = attempts::resolve_media_type(kind, name) {
            return Some((kind, media));
        }
    }
    None
}

/// How far a member container may itself be expanded. Each level costs one worker run and its
/// own count and byte budgets, so an archive nested inside archives is bounded rather than
/// trusted: past this depth a member container is still imported and kept, and only its own
/// expansion stops.
pub const CONTAINER_DEPTH_LIMIT: usize = 2;
/// The origin chain is walked, never trusted; a chain this long is already past the limit.
const ORIGIN_WALK_CAP: usize = 16;

/// What the Core will do with a member it has imported.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum MemberLane {
    /// A job of this kind reads the member's own bytes.
    Routed(&'static str),
    /// The member is a container and the nesting budget is already spent, so its own
    /// expansion stops. It is not unread - the route exists - and saying so is the point.
    NestingLimited,
    /// No route names this member's bytes; it is kept as custody only.
    Unrouted,
}

/// The single decision every caller reports on: does this member of this container get a job?
pub fn member_lane(
    conn: &Connection,
    container_source_id: &str,
    name: &str,
) -> Result<MemberLane, JobError> {
    let Some((kind, _media)) = route_for_member(name) else {
        return Ok(MemberLane::Unrouted);
    };
    if kind == "archive" && nesting_depth(conn, container_source_id)? >= CONTAINER_DEPTH_LIMIT {
        return Ok(MemberLane::NestingLimited);
    }
    Ok(MemberLane::Routed(kind))
}

/// How many containers `source_id` was taken out of, following the recorded member relation.
///
/// The relation is `"<container source_id>#<member>"` under `ORIGIN_KIND`, so a source that is
/// itself a member names its container. A reference that is not shaped like that, or names a
/// source that does not exist, ends the walk: the depth is what the chain really records, not
/// what a string looks like.
fn nesting_depth(conn: &Connection, source_id: &str) -> Result<usize, JobError> {
    let mut depth = 0usize;
    let mut current = source_id.to_string();
    while depth < ORIGIN_WALK_CAP {
        let origins = source::list_origins(conn, &current)?;
        let mut parent: Option<String> = None;
        for (kind, reference, _, _) in origins {
            if kind != ORIGIN_KIND {
                continue;
            }
            let Some((candidate, _)) = reference.rsplit_once('#') else {
                continue;
            };
            let exists: i64 = conn.query_row(
                "SELECT EXISTS(SELECT 1 FROM sources WHERE source_id=?1)",
                [candidate],
                |row| row.get(0),
            )?;
            if exists == 1 {
                parent = Some(candidate.to_string());
                break;
            }
        }
        let Some(next) = parent else {
            return Ok(depth);
        };
        depth += 1;
        current = next;
    }
    Ok(depth)
}

/// One member as the store knows it after expansion.
#[derive(Debug, Clone)]
pub struct MemberRow {
    pub source_id: String,
    pub member: String,
    pub origin_ref: String,
    pub original_name: Option<String>,
    pub sha256: String,
    /// True when a transform exists, i.e. a route read the member's bytes.
    pub readable: bool,
    /// The job queued for this member, when its name resolved to a route.
    pub job_id: Option<String>,
}

/// The members imported from one container, in the order they were recorded.
///
/// This answers "what is inside this container and which parts could be read" from the
/// relation recorded at import time, without a second table of relations. The member
/// name is recovered from the origin reference, and the readability of a member is the
/// presence of a transform rather than a promise.
pub fn members_of(
    conn: &Connection,
    container_source_id: &str,
) -> Result<Vec<MemberRow>, JobError> {
    let prefix = format!("{container_source_id}#");
    let mut statement = conn.prepare(
        "SELECT o.source_id, o.origin_ref, s.original_name, s.sha256,
                EXISTS(SELECT 1 FROM transforms t WHERE t.source_id=o.source_id),
                (SELECT j.job_id FROM jobs j WHERE j.input_ref=o.source_id ORDER BY j.rowid LIMIT 1)
         FROM source_origins o JOIN sources s ON s.source_id=o.source_id
         WHERE o.origin_kind=?1 AND o.origin_ref LIKE ?2
         ORDER BY o.imported_at, o.rowid",
    )?;
    let rows = statement.query_map(
        rusqlite::params![ORIGIN_KIND, format!("{prefix}%")],
        |row| {
            let reference: String = row.get(1)?;
            Ok(MemberRow {
                source_id: row.get(0)?,
                member: reference
                    .strip_prefix(&prefix)
                    .unwrap_or(&reference)
                    .to_string(),
                origin_ref: reference,
                original_name: row.get(2)?,
                sha256: row.get(3)?,
                readable: row.get::<_, i64>(4)? == 1,
                job_id: row.get(5)?,
            })
        },
    )?;
    rows.collect::<rusqlite::Result<Vec<_>>>()
        .map_err(JobError::from)
}

/// Import every declared member as its own source and enqueue the readable ones.
pub fn expand_members(
    conn: &mut Connection,
    staging_root: &Path,
    archive_job_id: &str,
) -> Result<Expansion, JobError> {
    let members = declared_members(conn, archive_job_id)?;
    let mut expansion = Expansion::default();
    if members.is_empty() {
        return Ok(expansion);
    }
    if members.len() > MEMBER_LIMIT {
        return Err(JobError::UnverifiableInput {
            job: archive_job_id.to_string(),
            reason: "declared archive members exceed the count budget".into(),
        });
    }
    let mut remaining = MEMBER_BYTES_LIMIT;
    let container_source: String = conn
        .query_row(
            "SELECT j.input_ref FROM jobs j WHERE j.job_id=?1",
            [archive_job_id],
            |row| row.get(0),
        )
        .optional()?
        .unwrap_or_default();

    for member in members {
        if member.bytes > remaining {
            return Err(JobError::UnverifiableInput {
                job: archive_job_id.to_string(),
                reason: "declared archive members exceed the byte budget".into(),
            });
        }
        // a declared file may not leave the transfer area, whatever it contains
        if Path::new(&member.file).components().count() != 1
            || member.file.contains("..")
            || member.file.contains(['/', '\\'])
        {
            return Err(JobError::UnverifiableInput {
                job: archive_job_id.to_string(),
                reason: format!("declared member file {:?} is not a plain name", member.file),
            });
        }
        let path: PathBuf = staging_root.join("members").join(&member.file);
        let mut bytes = Vec::new();
        std::fs::File::open(verbatim(&path))
            .and_then(|file| file.take(member.bytes + 1).read_to_end(&mut bytes))
            .map_err(|error| JobError::UnverifiableInput {
                job: archive_job_id.to_string(),
                reason: format!("declared member {:?} is unreadable: {error}", member.name),
            })?;
        if bytes.len() as u64 != member.bytes || sha256_hex(&bytes) != member.sha256 {
            return Err(JobError::UnverifiableInput {
                job: archive_job_id.to_string(),
                reason: format!(
                    "declared member {:?} does not match its digest and size",
                    member.name
                ),
            });
        }
        remaining -= member.bytes;
        let origin_ref = format!("{container_source}#{}", member.name);
        let origin = OriginInfo {
            kind: ORIGIN_KIND,
            origin_ref: &origin_ref,
            original_name: Some(&member.name),
            received_at: None,
        };
        let source_id = match source::import_source_with_origin(
            conn,
            &bytes,
            &member.name,
            None,
            Some(origin),
        )? {
            ImportOutcome::Imported { source_id, .. } => source_id,
            ImportOutcome::Duplicate { source_id, .. } => source_id,
        };
        // The origin insert is an INSERT OR IGNORE: verify the relation really landed
        // rather than assuming it did, because a member whose provenance was silently
        // dropped is worse than a refused member.
        let recorded = source::list_origins(conn, &source_id)?
            .into_iter()
            .any(|(kind, reference, _, _)| kind == ORIGIN_KIND && reference == origin_ref);
        if !recorded {
            return Err(JobError::UnverifiableInput {
                job: archive_job_id.to_string(),
                reason: format!(
                    "the container relation for member {:?} was not recorded (origin {ORIGIN_KIND}:{origin_ref})",
                    member.name
                ),
            });
        }
        expansion.sources.push(source_id.clone());
        match member_lane(conn, &container_source, &member.name)? {
            MemberLane::Routed(kind) => {
                let job_id = member_job_id(archive_job_id, &member.file);
                let existed: bool = conn.query_row(
                    "SELECT EXISTS(SELECT 1 FROM jobs WHERE job_id=?1)",
                    [&job_id],
                    |row| row.get(0),
                )?;
                crate::jobs::enqueue(conn, &job_id, kind, &source_id)?;
                if !existed {
                    expansion.jobs.push(job_id);
                }
            }
            MemberLane::NestingLimited => expansion.depth_limited.push(member.name.clone()),
            MemberLane::Unrouted => expansion.custody_only.push(member.name.clone()),
        }
    }
    Ok(expansion)
}

#[cfg(test)]
mod supported_member_route_tests {
    use super::route_for_member;
    #[test]
    fn existing_routes_are_selected_without_json_collision_or_recursive_media() {
        for (name, expected) in [
            ("a.docx", "office"),
            ("a.pptx", "office"),
            ("a.xlsx", "office"),
            ("a.html", "html"),
            ("a.htm", "html"),
            ("a.xhtml", "html"),
            ("a.CANVAS", "canvas"),
            ("a.json", "text"),
            ("a.srt", "subtitles"),
            ("a.vtt", "subtitles"),
            // a nested container is a member like any other: the bound on nesting is decided
            // from the recorded chain in `member_lane`, not from the name
            ("nested.zip", "archive"),
            ("nested.tar", "archive"),
        ] {
            assert_eq!(route_for_member(name).unwrap().0, expected, "{name}");
        }
        for name in ["video.mp4", "audio.wav", "audio.mp3", "unknown.bin"] {
            assert!(route_for_member(name).is_none(), "{name}");
        }
    }
}

#[cfg(test)]
mod verbatim_path_tests {
    use super::verbatim;
    use std::path::Path;

    #[cfg(windows)]
    #[test]
    fn an_absolute_member_path_is_named_verbatim_and_only_once() {
        let deep = Path::new(r"D:\work\archive-attempts\0123456789abcdef\1\members\0001-a.csv");
        let text = verbatim(deep).to_string_lossy().to_string();
        assert_eq!(text, format!(r"\\?\{deep}"));
        // a second pass must not add a second prefix: an already-verbatim path is returned as is
        assert_eq!(verbatim(Path::new(&text)).to_string_lossy(), text);
    }

    #[cfg(windows)]
    #[test]
    fn a_relative_path_is_left_alone() {
        // The verbatim form of a relative path is meaningless, and would then name a file under
        // whatever the process working directory happens to be rather than the caller's.
        let relative = Path::new(r"members\0001-a.csv");
        assert_eq!(verbatim(relative), relative.to_path_buf());
    }

    #[cfg(not(windows))]
    #[test]
    fn the_prefix_is_never_added_off_windows() {
        for path in [
            Path::new("/work/members/0001-a.csv"),
            Path::new("members/0001-a.csv"),
        ] {
            assert_eq!(verbatim(path), path.to_path_buf(), "{path:?}");
        }
    }
}
