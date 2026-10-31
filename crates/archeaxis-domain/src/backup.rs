//! Backup/restore via the SQLite Online Backup API (rusqlite `backup`).
use archeaxis_store_sqlite::raw_objects;
use rusqlite::Connection;
use sha2::{Digest, Sha256};
use std::path::{Path, PathBuf};

fn io_error(error: std::io::Error) -> rusqlite::Error {
    rusqlite::Error::ToSqlConversionFailure(Box::new(error))
}

/// Consistent snapshot of `src` into `dst_path` using the Online Backup API.
pub fn backup(conn: &Connection, dst_path: &str) -> rusqlite::Result<()> {
    validate_workspace(conn)?;
    let target = Path::new(dst_path);
    raw_objects::reject_links(target)?;
    raw_objects::reject_links(Path::new(conn.path().ok_or(rusqlite::Error::InvalidQuery)?))?;
    let final_objects = PathBuf::from(format!("{dst_path}.objects"));
    raw_objects::reject_links(&final_objects)?;
    if target.exists() || final_objects.exists() {
        return Err(rusqlite::Error::InvalidPath(target.to_owned()));
    }
    let parent = target
        .parent()
        .filter(|p| !p.as_os_str().is_empty())
        .unwrap_or(Path::new("."));
    let staging = tempfile::tempdir_in(parent).map_err(io_error)?;
    // Canonicalize the existing internal staging directory: Windows SQLite's
    // native file API needs its extended path for filenames beyond MAX_PATH.
    // This is an IO-only path, never a launch-document or worker protocol value.
    let staged = staging
        .path()
        .canonicalize()
        .map_err(io_error)?
        .join("snapshot.sqlite");
    let mut dst = Connection::open(&staged)?;
    {
        let bk = rusqlite::backup::Backup::new(conn, &mut dst)?;
        // Yield between bounded chunks without imposing the documentation
        // example's 250ms pause for every five pages of a large library.
        bk.run_to_completion(128, std::time::Duration::from_millis(10), None)?;
    }
    // Read the snapshot's source set, not a potentially newer live source set.
    let digests = {
        let mut sources = dst.prepare("SELECT sha256 FROM sources")?;
        sources
            .query_map([], |r| r.get::<_, String>(0))?
            .collect::<rusqlite::Result<Vec<_>>>()?
    };
    for digest in &digests {
        raw_objects::persist(&dst, &raw_objects::read(conn, digest)?)?;
    }
    let staged_objects = raw_objects::root(&dst)?;
    dst.execute_batch("PRAGMA wal_checkpoint(TRUNCATE); PRAGMA journal_mode=DELETE;")?;
    drop(dst);
    std::fs::OpenOptions::new()
        .read(true)
        .write(true)
        .open(&staged)
        .map_err(io_error)?
        .sync_all()
        .map_err(io_error)?;
    // Publish originals first and database last, never overwrite a prior backup.
    // A crash can leave an object-only directory; preserve it for manual recovery.
    std::fs::create_dir(&final_objects).map_err(io_error)?;
    let mut publication = Publication {
        directory: final_objects.clone(),
        files: Vec::new(),
        committed: false,
    };
    for digest in digests {
        let path = final_objects.join(&digest);
        publish_backup_file_noclobber(&staged_objects.join(digest), &path)?;
        publication.files.push(path);
    }
    publish_backup_file_noclobber(&staged, target)?;
    publication.committed = true;
    Ok(())
}

/// Publish an owned, fully synced backup staging file without replacing a target.
/// After path validation, a failed final publication cleans the owned staging file.
/// Existing parent canonicalization preserves Windows extended-path support.
/// Locked tempfile 3.27.0 uses Windows MoveFileExW without replacement/copy flags;
/// a cross-volume destination fails instead of becoming a partial copy.
pub fn publish_backup_file_noclobber(staged: &Path, target: &Path) -> rusqlite::Result<()> {
    raw_objects::publish_owned_file_noclobber(staged, target)
}

struct Publication {
    directory: PathBuf,
    files: Vec<PathBuf>,
    committed: bool,
}
impl Drop for Publication {
    fn drop(&mut self) {
        if !self.committed {
            for path in &self.files {
                let _ = std::fs::remove_file(path);
            }
            let _ = std::fs::remove_dir(&self.directory);
        }
    }
}

/// Restore a snapshot file into `dst` (the destination workspace connection).
/// The snapshot is opened read-only; content is copied via the Online Backup API.
pub fn restore(snapshot_path: &str, dst: &mut Connection) -> rusqlite::Result<()> {
    raw_objects::reject_links(Path::new(snapshot_path))?;
    let internal_snapshot = Path::new(snapshot_path).canonicalize().map_err(io_error)?;
    let src = Connection::open_with_flags(
        &internal_snapshot,
        rusqlite::OpenFlags::SQLITE_OPEN_READ_ONLY,
    )?;
    // Keep validation and Online Backup on one SQLite read snapshot.
    let read_snapshot = src.unchecked_transaction()?;
    validate_workspace(&src)?;
    // Validate every original before overwriting any destination database page.
    // Hold only one object's payload at a time, not the entire library. Immutable
    // CAS publications before a late validation failure are harmless orphans;
    // the destination SQLite references/authorization still remain unchanged.
    let mut sources = src.prepare("SELECT sha256 FROM sources ORDER BY sha256")?;
    for digest in sources.query_map([], |r| r.get::<_, String>(0))? {
        let bytes = raw_objects::read(&src, &digest?)?;
        raw_objects::persist(dst, &bytes)?;
    }
    drop(sources);
    {
        let bk = rusqlite::backup::Backup::new(&src, dst)?;
        bk.run_to_completion(128, std::time::Duration::from_millis(10), None)?;
    }
    read_snapshot.commit()?;
    Ok(())
}

/// Prepare and verify the new authorization epoch on an independent snapshot.
/// The only live database publication is the SQLite Online Backup transaction
/// containing both the restored rows and their fence. An interrupted preparation
/// leaves the old workspace; an interrupted publication cannot commit raw grants.
/// Raw `restore` remains available for exact rollback without altering old rights.
pub fn restore_authorized(snapshot_path: &str, dst: &mut Connection) -> rusqlite::Result<bool> {
    restore_authorized_checked(snapshot_path, dst, |_, _| Ok(()))
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum RestorePhase {
    BeforeFence,
    BeforePublish,
    AfterPublish,
}

#[cfg(test)]
mod restore_interruption_tests {
    use super::*;
    use crate::{
        context_grant::{self, Consumption, Operation},
        document, knowledge,
    };
    use serde_json::json;

    #[test]
    fn failures_before_fence_before_publication_and_after_publication_never_revive_old_grants() {
        let dir = tempfile::tempdir().unwrap();
        let mut original = archeaxis_store_sqlite::init_workspace(
            dir.path().join("original.sqlite").to_str().unwrap(),
        )
        .unwrap();
        let kid = knowledge::create_knowledge(
            &mut original,
            "NOTE",
            "synthetic accepted",
            "accepted",
            None,
            None,
            "owner",
        )
        .unwrap();
        let grant = document::create_optional_with_request(&mut original, None, None, "grant",
            json!({"type":"doc","content":[],"attrs":{"archeaxis_context_grant":{
                "schema":"archeaxis.context-grant/v1","purpose":"interruption fixture","consumer":"local-machine",
                "operations":["answer"],"knowledge_id":kid,"provenance":[],"authorization_basis":"SYNTHETIC trusted human grant",
                "expires_at":null,"state":"granted"}}}),Some("interrupt-original-grant")).unwrap();
        let input = Consumption {
            document_id: grant["document_id"].as_str().unwrap().into(),
            version: 1,
            content_sha256: grant["content_sha256"].as_str().unwrap().into(),
            purpose: "interruption fixture".into(),
        };
        context_grant::consume(&original, &input, Operation::Answer, &kid, 1).unwrap();
        let old = dir.path().join("old-granted.sqlite");
        backup(&original, old.to_str().unwrap()).unwrap();
        let mut editor = grant["editor_json"].clone();
        editor["attrs"]["archeaxis_context_grant"]["state"] = json!("revoked");
        let revoked = document::save(
            &mut original,
            grant["document_id"].as_str().unwrap(),
            1,
            editor,
        )
        .unwrap();
        let before = dir.path().join("before-revoked.sqlite");
        backup(&original, before.to_str().unwrap()).unwrap();
        let frozen =
            Connection::open_with_flags(&old, rusqlite::OpenFlags::SQLITE_OPEN_READ_ONLY).unwrap();
        let current =
            Connection::open_with_flags(&before, rusqlite::OpenFlags::SQLITE_OPEN_READ_ONLY)
                .unwrap();
        let backup_bytes = std::fs::read(&old).unwrap();
        for (index, failure) in [
            RestorePhase::BeforeFence,
            RestorePhase::BeforePublish,
            RestorePhase::AfterPublish,
        ]
        .into_iter()
        .enumerate()
        {
            let path = dir.path().join(format!("target-{index}.sqlite"));
            let mut target =
                archeaxis_store_sqlite::init_workspace(path.to_str().unwrap()).unwrap();
            restore(before.to_str().unwrap(), &mut target).unwrap();
            let result =
                restore_authorized_checked(old.to_str().unwrap(), &mut target, |phase, visible| {
                    // Every actual live state sampled at the three deterministic
                    // failure boundaries must refuse the historical grant.
                    assert!(
                        context_grant::consume(visible, &input, Operation::Answer, &kid, 1)
                            .is_err()
                    );
                    if phase == RestorePhase::AfterPublish {
                        assert_eq!(
                            document::read(visible, &input.document_id, None).unwrap(),
                            grant
                        );
                        assert!(verify_restored_authorization(&frozen, visible).unwrap());
                    } else {
                        assert_eq!(
                            document::read(visible, &input.document_id, None).unwrap(),
                            revoked
                        );
                        assert!(verify_counts(&current, visible).unwrap());
                    }
                    if phase == failure {
                        Err(rusqlite::Error::InvalidQuery)
                    } else {
                        Ok(())
                    }
                });
            assert!(result.is_err());
            drop(target);
            let reopened = archeaxis_store_sqlite::init_workspace(path.to_str().unwrap()).unwrap();
            assert!(context_grant::consume(&reopened, &input, Operation::Answer, &kid, 1).is_err());
            if failure == RestorePhase::AfterPublish {
                assert!(verify_restored_authorization(&frozen, &reopened).unwrap());
            } else {
                assert!(verify_counts(&current, &reopened).unwrap());
            }
            assert_eq!(std::fs::read(&old).unwrap(), backup_bytes);
        }
    }

    #[test]
    fn no_unwind_process_exit_at_restore_boundaries_never_revives_old_grants() {
        const CHILD_ROOT: &str = "ARCHEAXIS_RESTORE_EXIT_TEST_ROOT";
        const CHILD_PHASE: &str = "ARCHEAXIS_RESTORE_EXIT_TEST_PHASE";
        if let Some(root) = std::env::var_os(CHILD_ROOT) {
            let root = PathBuf::from(root);
            let phase = std::env::var(CHILD_PHASE).unwrap();
            let mut target = archeaxis_store_sqlite::init_workspace(
                root.join("target.sqlite").to_str().unwrap(),
            )
            .unwrap();
            restore_authorized_checked(
                root.join("old-granted.sqlite").to_str().unwrap(),
                &mut target,
                |visible_phase, _| {
                    if format!("{visible_phase:?}") == phase {
                        // Process exit skips Rust connection/transaction and
                        // TempDir destructors. This is not a physical power cut.
                        std::process::exit(91);
                    }
                    Ok(())
                },
            )
            .unwrap();
            panic!("the requested restore boundary was not reached");
        }

        let dir = tempfile::tempdir().unwrap();
        let mut original = archeaxis_store_sqlite::init_workspace(
            dir.path().join("original.sqlite").to_str().unwrap(),
        )
        .unwrap();
        let kid = knowledge::create_knowledge(
            &mut original,
            "NOTE",
            "synthetic crash-recovery fixture",
            "accepted",
            None,
            None,
            "owner",
        )
        .unwrap();
        let grant = document::create_optional_with_request(&mut original, None, None, "grant",
            json!({"type":"doc","content":[],"attrs":{"archeaxis_context_grant":{
                "schema":"archeaxis.context-grant/v1","purpose":"process exit fixture","consumer":"local-machine",
                "operations":["answer"],"knowledge_id":kid,"provenance":[],"authorization_basis":"SYNTHETIC trusted human grant",
                "expires_at":null,"state":"granted"}}}),Some("exit-original-grant")).unwrap();
        let input = Consumption {
            document_id: grant["document_id"].as_str().unwrap().into(),
            version: 1,
            content_sha256: grant["content_sha256"].as_str().unwrap().into(),
            purpose: "process exit fixture".into(),
        };
        context_grant::consume(&original, &input, Operation::Answer, &kid, 1).unwrap();
        let old = dir.path().join("old-granted.sqlite");
        backup(&original, old.to_str().unwrap()).unwrap();
        let backup_bytes = std::fs::read(&old).unwrap();
        let mut editor = grant["editor_json"].clone();
        editor["attrs"]["archeaxis_context_grant"]["state"] = json!("revoked");
        let revoked = document::save(&mut original, &input.document_id, 1, editor).unwrap();
        let before = dir.path().join("before-revoked.sqlite");
        backup(&original, before.to_str().unwrap()).unwrap();
        let frozen =
            Connection::open_with_flags(&old, rusqlite::OpenFlags::SQLITE_OPEN_READ_ONLY).unwrap();
        let current =
            Connection::open_with_flags(&before, rusqlite::OpenFlags::SQLITE_OPEN_READ_ONLY)
                .unwrap();

        for phase in [
            RestorePhase::BeforeFence,
            RestorePhase::BeforePublish,
            RestorePhase::AfterPublish,
        ] {
            let target_path = dir.path().join("target.sqlite");
            let mut target =
                archeaxis_store_sqlite::init_workspace(target_path.to_str().unwrap()).unwrap();
            restore(before.to_str().unwrap(), &mut target).unwrap();
            drop(target);
            let output = std::process::Command::new(std::env::current_exe().unwrap())
                .args([
                    "--exact",
                    "backup::restore_interruption_tests::no_unwind_process_exit_at_restore_boundaries_never_revives_old_grants",
                    "--nocapture",
                    "--test-threads=1",
                ])
                .env(CHILD_ROOT, dir.path())
                .env(CHILD_PHASE, format!("{phase:?}"))
                .output()
                .unwrap();
            assert_eq!(
                output.status.code(),
                Some(91),
                "{phase:?}: {} {}",
                String::from_utf8_lossy(&output.stdout),
                String::from_utf8_lossy(&output.stderr)
            );
            let reopened =
                archeaxis_store_sqlite::init_workspace(target_path.to_str().unwrap()).unwrap();
            assert!(context_grant::consume(&reopened, &input, Operation::Answer, &kid, 1).is_err());
            if phase == RestorePhase::AfterPublish {
                assert_eq!(
                    document::read(&reopened, &input.document_id, None).unwrap(),
                    grant
                );
                assert!(verify_restored_authorization(&frozen, &reopened).unwrap());
            } else {
                assert_eq!(
                    document::read(&reopened, &input.document_id, None).unwrap(),
                    revoked
                );
                assert!(verify_counts(&current, &reopened).unwrap());
            }
            assert_eq!(std::fs::read(&old).unwrap(), backup_bytes);
            eprintln!(
                "RESTORE_NO_UNWIND_EXIT_REOPEN_PASS={phase:?}; old_grant_refused=true; source_backup_unchanged=true"
            );
        }
    }
}

fn restore_authorized_checked(
    snapshot_path: &str,
    dst: &mut Connection,
    mut checkpoint: impl FnMut(RestorePhase, &Connection) -> rusqlite::Result<()>,
) -> rusqlite::Result<bool> {
    let source_path = Path::new(snapshot_path);
    raw_objects::reject_links(source_path)?;
    let source = Connection::open_with_flags(
        source_path.canonicalize().map_err(io_error)?,
        rusqlite::OpenFlags::SQLITE_OPEN_READ_ONLY,
    )?;
    let owner = Path::new(dst.path().ok_or(rusqlite::Error::InvalidQuery)?);
    raw_objects::reject_links(owner)?;
    let parent = owner.parent().ok_or(rusqlite::Error::InvalidQuery)?;
    let staging = tempfile::tempdir_in(parent).map_err(io_error)?;
    let staged = staging
        .path()
        .canonicalize()
        .map_err(io_error)?
        .join("restore.sqlite");
    let staged_text = staged.to_str().ok_or(rusqlite::Error::InvalidQuery)?;
    let mut prepared = archeaxis_store_sqlite::init_workspace(staged_text)?;
    restore(snapshot_path, &mut prepared)?;
    checkpoint(RestorePhase::BeforeFence, dst)?;
    if !finalize_restore_authorization(&source, &mut prepared)? {
        return Ok(false);
    }
    checkpoint(RestorePhase::BeforePublish, dst)?;
    // Both source views have already been validated, including every CAS object.
    // No raw historical-authorization database is ever installed in the live path.
    restore(staged_text, dst)?;
    checkpoint(RestorePhase::AfterPublish, dst)?;
    verify_restored_authorization(&source, dst)
}

/// Verify a snapshot/restored db: compare schema and canonical row-content
/// digests for every table, and validate persisted source object hashes.
pub fn verify_counts(a: &Connection, b: &Connection) -> rusqlite::Result<bool> {
    // Hold each database on one read view for the entire comparison. Otherwise
    // a writer could commit between table digests and make one database appear
    // internally inconsistent even though each query is individually valid.
    let snapshot_a = a.unchecked_transaction()?;
    let snapshot_b = b.unchecked_transaction()?;
    let result = (|| -> rusqlite::Result<bool> {
        validate_workspace(&snapshot_a)?;
        validate_workspace(&snapshot_b)?;
        verify_source_objects(&snapshot_a)?;
        verify_source_objects(&snapshot_b)?;
        if schema_objects(&snapshot_a)? != schema_objects(&snapshot_b)? {
            return Ok(false);
        }
        let tables_a = table_names(&snapshot_a)?;
        let tables_b = table_names(&snapshot_b)?;
        if tables_a != tables_b {
            return Ok(false);
        }
        for table in tables_a {
            if table_content_digest(&snapshot_a, &table)?
                != table_content_digest(&snapshot_b, &table)?
            {
                return Ok(false);
            }
        }
        Ok(true)
    })()?;
    snapshot_a.commit()?;
    snapshot_b.commit()?;
    Ok(result)
}

/// Verify the complete raw restored DB/CAS before installing a fresh authorization
/// fence. Keep raw restore available for an exact failure rollback; it is not a
/// successful user restore until this function returns true.
pub fn finalize_restore_authorization(
    source: &Connection,
    target: &mut Connection,
) -> rusqlite::Result<bool> {
    if !verify_counts(source, target)? {
        return Ok(false);
    }
    let source_view = source.unchecked_transaction()?;
    let transaction = target.transaction()?;
    archeaxis_store_sqlite::authorization_fence::install_after_restore(&transaction)?;
    // The raw restore was compared exactly above. Upgrade only this verified
    // owned destination; never open the original backup as a writer.
    let version: String = source_view.query_row(
        "SELECT value FROM workspace_meta WHERE key='schema_version'",
        [],
        |r| r.get(0),
    )?;
    if version == "13" {
        archeaxis_store_sqlite::upgrade_capability_settings_v14(&transaction)?;
        transaction.execute(
            "UPDATE workspace_meta SET value=?1 WHERE key='schema_version'",
            [archeaxis_store_sqlite::SCHEMA_VERSION.to_string()],
        )?;
    }
    if !verify_restored_authorization_views(&source_view, &transaction)? {
        return Ok(false); // Transaction drop rolls back the unverified fence.
    }
    transaction.commit()?;
    source_view.commit()?;
    Ok(true)
}

/// Explicit post-restore verifier. The general exact verify_counts remains
/// unchanged and deliberately reports false after a successful fenced restore.
pub fn verify_restored_authorization(
    source: &Connection,
    target: &Connection,
) -> rusqlite::Result<bool> {
    let source_view = source.unchecked_transaction()?;
    let target_view = target.unchecked_transaction()?;
    let result = verify_restored_authorization_views(&source_view, &target_view)?;
    source_view.commit()?;
    target_view.commit()?;
    Ok(result)
}

fn verify_restored_authorization_views(
    source: &Connection,
    target: &Connection,
) -> rusqlite::Result<bool> {
    use archeaxis_store_sqlite::authorization_fence::{KEY, SCHEMA};
    use rusqlite::OptionalExtension;
    validate_workspace(source)?;
    validate_workspace(target)?;
    verify_source_objects(source)?;
    verify_source_objects(target)?;
    let source_version: String = source.query_row(
        "SELECT value FROM workspace_meta WHERE key='schema_version'",
        [],
        |r| r.get(0),
    )?;
    let target_version: String = target.query_row(
        "SELECT value FROM workspace_meta WHERE key='schema_version'",
        [],
        |r| r.get(0),
    )?;
    let upgrading = source_version == "13" && target_version == "14";
    let schema = |conn: &Connection| -> rusqlite::Result<Vec<_>> {
        Ok(schema_objects(conn)?
            .into_iter()
            .filter(|(kind, name, _, _)| {
                !upgrading || kind != "table" || name != "capability_settings"
            })
            .collect())
    };
    if schema(source)? != schema(target)? || table_names(source)? != table_names(target)? {
        return Ok(false);
    }
    for table in table_names(source)? {
        let equal = if table == "workspace_meta" {
            metadata_content_without_fence(source, upgrading)?
                == metadata_content_without_fence(target, upgrading)?
        } else if table == "capability_settings" && upgrading {
            legacy_capability_upgrade_equal(source, target)?
        } else {
            table_content_digest(source, &table)? == table_content_digest(target, &table)?
        };
        if !equal {
            return Ok(false);
        }
    }
    let raw: Option<String> = target
        .query_row(
            "SELECT value FROM workspace_meta WHERE key=?1",
            [KEY],
            |r| r.get(0),
        )
        .optional()?;
    let Some(raw) = raw else {
        return Ok(false);
    };
    let Ok(fence) = serde_json::from_str::<serde_json::Value>(&raw) else {
        return Ok(false);
    };
    let Some(object) = fence.as_object() else {
        return Ok(false);
    };
    let Some(epoch) = fence["epoch"].as_str() else {
        return Ok(false);
    };
    if object.len() != 3
        || fence["schema"] != SCHEMA
        || epoch.len() != 32
        || !epoch
            .bytes()
            .all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b))
    {
        return Ok(false);
    }
    let prior: Option<String> = source
        .query_row(
            "SELECT value FROM workspace_meta WHERE key=?1",
            [KEY],
            |r| r.get(0),
        )
        .optional()?;
    if let Some(prior) = prior {
        if prior == raw {
            return Ok(false);
        }
        if let Ok(old) = serde_json::from_str::<serde_json::Value>(&prior) {
            if old["epoch"].as_str() == Some(epoch) {
                return Ok(false);
            }
        }
    }
    let expected = source
        .prepare(
            "SELECT DISTINCT document_id FROM document_versions
        WHERE json_type(editor_json,'$.attrs.archeaxis_context_grant') IS NOT NULL
           OR json_type(editor_json,'$.attrs.archeaxis_asset_context_grant') IS NOT NULL
        ORDER BY document_id",
        )?
        .query_map([], |r| r.get::<_, String>(0))?
        .collect::<rusqlite::Result<Vec<_>>>()?;
    let Some(actual) = fence["blocked_grant_ids"].as_array() else {
        return Ok(false);
    };
    if actual.len() != expected.len()
        || actual
            .iter()
            .zip(expected.iter())
            .any(|(a, b)| a.as_str() != Some(b.as_str()))
    {
        return Ok(false);
    }
    Ok(true)
}

fn table_content_digest(conn: &Connection, table: &str) -> rusqlite::Result<(u64, String)> {
    let quoted = format!("\"{}\"", table.replace('"', "\"\""));
    let column_count = conn
        .prepare(&format!("SELECT * FROM {quoted} LIMIT 0"))?
        .column_count();
    let order = (1..=column_count)
        .map(|ordinal| ordinal.to_string())
        .collect::<Vec<_>>()
        .join(", ");
    let mut stmt = conn.prepare(&format!("SELECT * FROM {quoted} ORDER BY {order}"))?;
    let mut rows = stmt.query([])?;
    let mut digest = Sha256::new();
    digest.update((column_count as u64).to_le_bytes());
    let mut row_count = 0u64;
    while let Some(row) = rows.next()? {
        digest.update([0xA1]);
        for column in 0..column_count {
            match row.get_ref(column)? {
                rusqlite::types::ValueRef::Null => digest.update([0]),
                rusqlite::types::ValueRef::Integer(value) => {
                    digest.update([1]);
                    digest.update(value.to_le_bytes());
                }
                rusqlite::types::ValueRef::Real(value) => {
                    digest.update([2]);
                    digest.update(value.to_bits().to_le_bytes());
                }
                rusqlite::types::ValueRef::Text(value) => {
                    digest.update([3]);
                    digest.update((value.len() as u64).to_le_bytes());
                    digest.update(value);
                }
                rusqlite::types::ValueRef::Blob(value) => {
                    digest.update([4]);
                    digest.update((value.len() as u64).to_le_bytes());
                    digest.update(value);
                }
            }
        }
        digest.update([0xAF]);
        row_count += 1;
    }
    digest.update(row_count.to_le_bytes());
    Ok((row_count, hex::encode(digest.finalize())))
}

fn metadata_content_without_fence(
    conn: &Connection,
    upgrading: bool,
) -> rusqlite::Result<(u64, String)> {
    let table = "workspace_meta";
    let quoted = format!("\"{}\"", table.replace('"', "\"\""));
    let column_count = conn
        .prepare(&format!("SELECT * FROM {quoted} LIMIT 0"))?
        .column_count();
    let order = (1..=column_count)
        .map(|ordinal| ordinal.to_string())
        .collect::<Vec<_>>()
        .join(", ");
    let mut stmt = conn.prepare(&format!(
        "SELECT * FROM {quoted} WHERE key != ?1 AND key != ?2 ORDER BY {order}"
    ))?;
    let mut rows = stmt.query([
        archeaxis_store_sqlite::authorization_fence::KEY,
        if upgrading {
            "schema_version"
        } else {
            archeaxis_store_sqlite::authorization_fence::KEY
        },
    ])?;
    let mut digest = Sha256::new();
    digest.update((column_count as u64).to_le_bytes());
    let mut row_count = 0u64;
    while let Some(row) = rows.next()? {
        digest.update([0xA1]);
        for column in 0..column_count {
            match row.get_ref(column)? {
                rusqlite::types::ValueRef::Null => digest.update([0]),
                rusqlite::types::ValueRef::Integer(value) => {
                    digest.update([1]);
                    digest.update(value.to_le_bytes());
                }
                rusqlite::types::ValueRef::Real(value) => {
                    digest.update([2]);
                    digest.update(value.to_bits().to_le_bytes());
                }
                rusqlite::types::ValueRef::Text(value) => {
                    digest.update([3]);
                    digest.update((value.len() as u64).to_le_bytes());
                    digest.update(value);
                }
                rusqlite::types::ValueRef::Blob(value) => {
                    digest.update([4]);
                    digest.update((value.len() as u64).to_le_bytes());
                    digest.update(value);
                }
            }
        }
        digest.update([0xAF]);
        row_count += 1;
    }
    digest.update(row_count.to_le_bytes());
    Ok((row_count, hex::encode(digest.finalize())))
}

fn schema_objects(
    conn: &Connection,
) -> rusqlite::Result<Vec<(String, String, String, Option<String>)>> {
    conn.prepare(
        "SELECT type, name, tbl_name, sql FROM sqlite_master
         WHERE name NOT LIKE 'sqlite_%' ORDER BY type, name",
    )?
    .query_map([], |row| {
        Ok((row.get(0)?, row.get(1)?, row.get(2)?, row.get(3)?))
    })?
    .collect()
}

fn table_names(conn: &Connection) -> rusqlite::Result<Vec<String>> {
    conn.prepare(
        "SELECT name FROM sqlite_master WHERE type='table'
         AND (name NOT LIKE 'sqlite_%' OR name='sqlite_sequence') ORDER BY name",
    )?
    .query_map([], |row| row.get(0))?
    .collect()
}

fn validate_workspace(conn: &Connection) -> rusqlite::Result<()> {
    let version: String = conn.query_row(
        "SELECT value FROM workspace_meta WHERE key='schema_version'",
        [],
        |row| row.get(0),
    )?;
    let integrity: Vec<String> = conn
        .prepare("PRAGMA integrity_check")?
        .query_map([], |row| row.get(0))?
        .collect::<rusqlite::Result<Vec<_>>>()?;
    if integrity.as_slice() != ["ok"]
        || !(version == "13" || version == archeaxis_store_sqlite::SCHEMA_VERSION.to_string())
        || conn.prepare("PRAGMA foreign_key_check")?.exists([])?
    {
        return Err(rusqlite::Error::InvalidQuery);
    }
    Ok(())
}

/// This is the only cross-version exception: every legacy capability value
/// must match and every additive field must equal its migration default.
fn legacy_capability_upgrade_equal(
    source: &Connection,
    target: &Connection,
) -> rusqlite::Result<bool> {
    // Compare the exact DDL produced by the same additive migration. Merely
    // comparing column names would hide removed constraints or altered defaults.
    let table_sql = |conn: &Connection| -> rusqlite::Result<String> {
        conn.query_row(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='capability_settings'",
            [],
            |r| r.get(0),
        )
    };
    let expected = Connection::open_in_memory()?;
    expected.execute_batch(&table_sql(source)?)?;
    archeaxis_store_sqlite::upgrade_capability_settings_v14(&expected)?;
    if table_sql(&expected)? != table_sql(target)? {
        return Ok(false);
    }
    let columns = |conn: &Connection| -> rusqlite::Result<Vec<String>> {
        conn.prepare("SELECT name FROM pragma_table_info('capability_settings') ORDER BY cid")?
            .query_map([], |r| r.get(0))?
            .collect()
    };
    if columns(source)? != ["capability","enabled","changed_at"]
        || columns(target)? != ["capability","enabled","changed_at","installed","definition_version","state_epoch"]
        || target.query_row("SELECT EXISTS(SELECT 1 FROM capability_settings WHERE installed!=1 OR definition_version!=1 OR state_epoch!=0)",[],|r|r.get::<_,bool>(0))? {
        return Ok(false);
    }
    let rows = |conn: &Connection| -> rusqlite::Result<Vec<(String, i64, String)>> {
        conn.prepare(
            "SELECT capability,enabled,changed_at FROM capability_settings ORDER BY capability",
        )?
        .query_map([], |r| Ok((r.get(0)?, r.get(1)?, r.get(2)?)))?
        .collect()
    };
    Ok(rows(source)? == rows(target)?)
}

fn verify_source_objects(conn: &Connection) -> rusqlite::Result<()> {
    let mut sources = conn.prepare("SELECT sha256 FROM sources")?;
    for digest in sources.query_map([], |row| row.get::<_, String>(0))? {
        raw_objects::read(conn, &digest?)?;
    }
    Ok(())
}

/// Read-only preflight. Opens no writer, creates no workspace and validates CAS.
pub fn preview(snapshot_path: &Path) -> rusqlite::Result<()> {
    raw_objects::reject_links(snapshot_path)?;
    let source = Connection::open_with_flags(
        snapshot_path.canonicalize().map_err(io_error)?,
        rusqlite::OpenFlags::SQLITE_OPEN_READ_ONLY,
    )?;
    let view = source.unchecked_transaction()?;
    validate_workspace(&view)?;
    verify_source_objects(&view)?;
    view.commit()
}

#[cfg(test)]
mod publication_tests {
    use super::*;

    #[test]
    fn database_publication_collision_cleans_owned_objects_without_replacing_target() {
        let dir = tempfile::tempdir().unwrap();
        let objects = dir.path().join("backup.sqlite.objects");
        std::fs::create_dir(&objects).unwrap();
        let mut publication = Publication {
            directory: objects.clone(),
            files: Vec::new(),
            committed: false,
        };
        let staged_object = dir.path().join("staged-object");
        let object = objects.join("owned-object");
        std::fs::write(&staged_object, b"original").unwrap();
        publish_backup_file_noclobber(&staged_object, &object).unwrap();
        publication.files.push(object);
        let staged_db = dir.path().join("staged.sqlite");
        let database = dir.path().join("backup.sqlite");
        std::fs::write(&staged_db, b"new snapshot").unwrap();
        std::fs::write(&database, b"concurrently published backup").unwrap();
        assert!(publish_backup_file_noclobber(&staged_db, &database).is_err());
        drop(publication);
        assert!(!objects.exists());
        assert!(!staged_db.exists());
        assert_eq!(
            std::fs::read(database).unwrap(),
            b"concurrently published backup"
        );
    }
}
