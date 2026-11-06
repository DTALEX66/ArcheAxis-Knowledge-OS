//! Trusted, bounded JSON adapters. No executable path is accepted from HTTP.
use super::*;
use serde_json::{Value, json};
use sha2::{Digest, Sha256};

const MAX_INPUT: usize = 256_000;
const MAX_OUTPUT: usize = 1_000_000;
const MAX_ERROR: usize = 8192;
const MAX_OPENMAIC_SOURCE: u64 = 1_000_000;

pub(super) fn supported(capability: &str) -> bool {
    matches!(
        capability,
        "course.general"
            | "search.semantic"
            | "course.openmaic.scene-build"
            | "course.openmaic.outline-model"
    )
}

fn local_path_shape_allowed(path: &Path) -> bool {
    #[cfg(windows)]
    if !matches!(path.components().next(),
        Some(std::path::Component::Prefix(prefix))
            if matches!(prefix.kind(), std::path::Prefix::Disk(_) | std::path::Prefix::VerbatimDisk(_)))
    {
        return false;
    }
    let normalized = path
        .to_string_lossy()
        .replace('\\', "/")
        .to_ascii_lowercase();
    let normalized = normalized.strip_prefix("//?/").unwrap_or(&normalized);
    path.is_absolute()
        && !normalized.starts_with("e:")
        && !normalized.starts_with("f:")
        && !normalized.starts_with("//")
        && !normalized.starts_with("unc/")
        && !path
            .components()
            .any(|part| matches!(part, std::path::Component::ParentDir))
}

pub(super) fn safe_local_file(path: &Path) -> bool {
    if !local_path_shape_allowed(path) {
        return false;
    }
    let mut part = PathBuf::new();
    for component in path.components() {
        // A Windows verbatim prefix such as `\\?\D:` is not a complete
        // filesystem root. Query the root only after its separator has been
        // appended, then retain the link check for every remaining component.
        let prefix_only = matches!(component, std::path::Component::Prefix(_));
        part.push(component);
        if prefix_only {
            continue;
        }
        if archeaxis_store_sqlite::raw_objects::reject_links(&part).is_err() {
            return false;
        }
    }
    file_usable(path)
}

#[cfg(all(test, windows))]
mod windows_local_path_tests {
    use super::*;

    #[test]
    fn existing_verbatim_file_is_checked_from_root_and_unc_is_refused() {
        let path = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("src/executor/derived.rs");
        let canonical = path.canonicalize().unwrap();
        assert!(safe_local_file(&path));
        assert!(safe_local_file(&canonical));
        assert!(!local_path_shape_allowed(Path::new(r"E:\worker.py")));
        assert!(!local_path_shape_allowed(Path::new(r"\\?\F:\worker.py")));
        assert!(!local_path_shape_allowed(Path::new(
            r"\\server\share\worker.py"
        )));
        assert!(!local_path_shape_allowed(Path::new(
            r"\\?\UNC\server\share\worker.py"
        )));
        assert!(!local_path_shape_allowed(Path::new(
            r"\\?\Volume{12345678-1234-1234-1234-123456789abc}\worker.py"
        )));
        let dir = tempfile::tempdir().unwrap();
        let link = dir.path().join("linked.rs");
        if std::os::windows::fs::symlink_file(&path, &link).is_ok() {
            assert!(!safe_local_file(&link));
        }
    }
}

/// Bind a trusted launch manifest to the executable's actual bytes, with bounded
/// streaming IO. The digest does not by itself qualify the Node version.
pub(super) fn executable_matches(path: &Path, expected: &str) -> bool {
    if expected.len() != 64
        || !expected
            .bytes()
            .all(|c| c.is_ascii_digit() || (b'a'..=b'f').contains(&c))
        || !safe_local_file(path)
    {
        return false;
    }
    let Ok(mut file) = std::fs::File::open(path) else {
        return false;
    };
    let Ok(meta) = file.metadata() else {
        return false;
    };
    if !meta.is_file() || meta.len() == 0 || meta.len() > 512 * 1024 * 1024 {
        return false;
    }
    let mut hash = Sha256::new();
    let mut buffer = [0_u8; 64 * 1024];
    let mut total = 0_u64;
    loop {
        match file.read(&mut buffer) {
            Ok(0) => break,
            Ok(count) => {
                total += count as u64;
                if total > 512 * 1024 * 1024 {
                    return false;
                }
                hash.update(&buffer[..count]);
            }
            Err(_) => return false,
        }
    }
    total == meta.len() && hex::encode(hash.finalize()) == expected
}

/// Hash no more than the observed size plus one byte. The extra byte detects
/// growth after metadata without reading an unbounded file into memory.
fn bounded_openmaic_source_matches<R: Read>(reader: &mut R, observed: u64, expected: &str) -> bool {
    if observed > MAX_OPENMAIC_SOURCE {
        return false;
    }
    let mut hash = Sha256::new();
    let mut buffer = [0_u8; 64 * 1024];
    let mut total = 0_u64;
    loop {
        let allowed = ((observed + 1 - total) as usize).min(buffer.len());
        let count = match reader.read(&mut buffer[..allowed]) {
            Ok(count) => count,
            Err(_) => return false,
        };
        if count == 0 {
            break;
        }
        total += count as u64;
        if total > observed {
            return false;
        }
        hash.update(&buffer[..count]);
    }
    total == observed && hex::encode(hash.finalize()) == expected
}

/// Fixed source files from OpenMAIC 1.3.0 / generation 0.3.28. A script name
/// alone is not enough to select or upgrade a provider. Checking the opened
/// handle reduces drift but does not lock the later Node import path.
pub(super) fn openmaic_worker_matches(script: &Path) -> bool {
    fn matches(path: &Path, expected: &str) -> bool {
        if !safe_local_file(path) {
            return false;
        }
        let Ok(mut file) = std::fs::File::open(path) else {
            return false;
        };
        let Ok(meta) = file.metadata() else {
            return false;
        };
        if !meta.is_file() || !bounded_openmaic_source_matches(&mut file, meta.len(), expected) {
            return false;
        }
        let Ok(after) = file.metadata() else {
            return false;
        };
        after.is_file() && after.len() == meta.len()
    }
    if script.file_name().and_then(|name| name.to_str()) != Some("scene-build-worker.mjs") {
        return false;
    }
    let Some(root) = script.parent() else {
        return false;
    };
    matches(
        script,
        "c4a2dad9c96ebd13aa20827410227d2650cda0dac80e3a3927968d1e024779e9",
    ) && matches(
        &root.join("vendor/generation-0.3.28/scene-builder.ts"),
        "e550ed528f9a017ea0fa1f9cc4a01f7eb22d541d5ada067967d3434393d1bf0a",
    ) && matches(
        &root.join("vendor/generation-0.3.28/nanoid.mjs"),
        "d5d678dfcecc9a4c0f4dae6555c30b4d0ef41a87b00d4d16d744f31ddae6c16e",
    )
}

/// The fixed OpenMAIC Node adapters one launch may own. The scene builder keeps
/// its existing profile; every other script is resolved by its fixed name only
/// as a sibling of that configured script, so an HTTP caller cannot name a script
/// or a directory.
#[derive(Clone, Copy, PartialEq, Eq)]
enum OpenMaicScript {
    Scene,
    Outline,
    SlidePrompt,
    SlideReply,
    SlideNormalize,
    QuizReplay,
    QuizActions,
}

impl OpenMaicScript {
    /// The fixed name of a sibling adapter; `None` is the configured scene script itself.
    fn sibling_name(self) -> Option<&'static str> {
        match self {
            Self::Scene => None,
            Self::Outline => Some("outline-replay-worker.mjs"),
            Self::SlidePrompt => Some("slide-prompt-worker.mjs"),
            Self::SlideReply => Some("slide-reply-worker.mjs"),
            Self::SlideNormalize => Some("slide-normalize-worker.mjs"),
            Self::QuizReplay => Some("quiz-replay-worker.mjs"),
            Self::QuizActions => Some("quiz-actions-replay-worker.mjs"),
        }
    }

    /// The stage label a named unavailability reports.
    pub(super) fn stage(self) -> &'static str {
        match self {
            Self::Scene => "scene_build",
            Self::Outline => "outline",
            Self::SlidePrompt => "slide_prompt",
            Self::SlideReply => "slide_reply",
            Self::SlideNormalize => "slide_normalize",
            Self::QuizReplay => "quiz_replay",
            Self::QuizActions => "quiz_actions",
        }
    }
}

/// The three donor slide adapters this chain drives.
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum OpenMaicSlideStage {
    Prompt,
    Reply,
    Normalize,
}

impl From<OpenMaicSlideStage> for OpenMaicScript {
    fn from(value: OpenMaicSlideStage) -> Self {
        match value {
            OpenMaicSlideStage::Prompt => Self::SlidePrompt,
            OpenMaicSlideStage::Reply => Self::SlideReply,
            OpenMaicSlideStage::Normalize => Self::SlideNormalize,
        }
    }
}

/// Resolve a fixed sibling adapter next to the configured scene builder script.
/// No path is guessed: a missing, non-regular or linked sibling means the
/// capability is unavailable rather than an alternate provider.
fn openmaic_script(scene: &Path, kind: OpenMaicScript) -> Option<PathBuf> {
    let Some(name) = kind.sibling_name() else {
        return Some(scene.to_owned());
    };
    let script = scene.parent()?.join(name);
    safe_local_file(&script).then_some(script)
}

/// The outline replay worker next to the configured scene builder script.
pub(super) fn outline_worker_script(scene: &Path) -> Option<PathBuf> {
    openmaic_script(scene, OpenMaicScript::Outline)
}

impl Executor {
    /// Capture the current OpenMAIC admission generation before doing work.
    /// A capability disable/re-enable advances this value, so a caller can
    /// reject an old result at the later Core write boundary.
    pub async fn openmaic_admission_generation(&self) -> Result<u64, String> {
        if self.openmaic_node.is_none() {
            return Err("OpenMAIC Node worker not configured".into());
        }
        let generation = self.openmaic_admission.lock().await;
        if *generation == u64::MAX {
            return Err("OpenMAIC admission exhausted".into());
        }
        let enabled = self
            .store
            .submit_wait(|conn| {
                capability_settings::is_enabled(conn, "course.openmaic.scene-build")
            })
            .await
            .map_err(|_| "capability settings unavailable")?
            .map_err(|_| "capability settings unavailable")?;
        if !enabled {
            return Err("OpenMAIC capability is disabled".into());
        }
        Ok(*generation)
    }

    /// Serialize a short Core write with OpenMAIC capability changes. Once
    /// queued, the closure owns the admission guard until the writer finishes,
    /// even if its HTTP caller disconnects; callers must use an idempotent
    /// request ID because a disconnected caller may not know the outcome.
    pub async fn commit_openmaic_if_current<T: Send + 'static>(
        &self,
        expected_generation: u64,
        operation: impl FnOnce(&mut rusqlite::Connection) -> T + Send + 'static,
    ) -> Result<T, String> {
        if self.openmaic_node.is_none() {
            return Err("OpenMAIC Node worker not configured".into());
        }
        let guard = self.openmaic_admission.clone().lock_owned().await;
        if *guard != expected_generation || *guard == u64::MAX {
            return Err("OpenMAIC capability was withdrawn".into());
        }
        self.store
            .submit_wait(move |conn| {
                let _guard = guard;
                let enabled = capability_settings::is_enabled(conn, "course.openmaic.scene-build")
                    .map_err(|_| "capability settings unavailable")?;
                if !enabled {
                    return Err("OpenMAIC capability is disabled");
                }
                Ok(operation(conn))
            })
            .await
            .map_err(|_| "capability settings unavailable".to_string())?
            .map_err(|reason| reason.to_owned())
    }

    /// Preserves declared worker outcomes, including PARTIAL/UNAVAILABLE exit 2.
    pub async fn derived_json(
        &self,
        capability: &str,
        request: Value,
        timeout: Duration,
    ) -> Result<Value, String> {
        self.derived_json_checked(capability, request, timeout, None)
            .await
    }

    /// Dispatch against the same admission generation captured by the caller
    /// before preparing persistence. A disable/re-enable must not allow an old
    /// request to send material under a newly captured generation.
    pub async fn openmaic_scene_with_generation(
        &self,
        expected_generation: u64,
        request: Value,
        timeout: Duration,
    ) -> Result<Value, String> {
        self.derived_json_checked(
            "course.openmaic.scene-build",
            request,
            timeout,
            Some(expected_generation),
        )
        .await
    }

    /// The outline replay adapter shares the scene launch: same Node executable,
    /// same frame budget, timeout and cleanup, but the sibling outline worker.
    pub async fn openmaic_outline_with_generation(
        &self,
        expected_generation: u64,
        request: Value,
        timeout: Duration,
    ) -> Result<Value, String> {
        self.derived_json_checked_script(
            "course.openmaic.scene-build",
            request,
            timeout,
            Some(expected_generation),
            OpenMaicScript::Outline,
        )
        .await
    }

    /// Whether the configured scene builder has a usable sibling outline worker.
    pub fn openmaic_outline_script(&self) -> Option<PathBuf> {
        self.openmaic_node
            .as_ref()
            .and_then(|node| outline_worker_script(&node.script))
    }

    /// One of the three donor slide adapters, dispatched under the shared OpenMAIC
    /// admission generation. Each stage keeps its own fixed script; a missing
    /// sibling names that stage instead of falling back to another adapter.
    pub async fn openmaic_slide_with_generation(
        &self,
        stage: OpenMaicSlideStage,
        expected_generation: u64,
        request: Value,
        timeout: Duration,
    ) -> Result<Value, String> {
        self.derived_json_checked_script(
            "course.openmaic.scene-build",
            request,
            timeout,
            Some(expected_generation),
            stage.into(),
        )
        .await
    }

    /// Whether the configured scene builder has a usable sibling slide adapter.
    pub fn openmaic_slide_script(&self, stage: OpenMaicSlideStage) -> Option<PathBuf> {
        self.openmaic_node
            .as_ref()
            .and_then(|node| openmaic_script(&node.script, stage.into()))
    }

    /// The single sibling quiz adapter drives both the capture and replay stages
    /// under the shared OpenMAIC admission generation.
    pub async fn openmaic_quiz_with_generation(
        &self,
        expected_generation: u64,
        request: Value,
        timeout: Duration,
    ) -> Result<Value, String> {
        self.derived_json_checked_script(
            "course.openmaic.scene-build",
            request,
            timeout,
            Some(expected_generation),
            OpenMaicScript::QuizReplay,
        )
        .await
    }

    /// Whether the configured scene builder has a usable sibling quiz adapter.
    pub fn openmaic_quiz_script(&self) -> Option<PathBuf> {
        self.openmaic_node
            .as_ref()
            .and_then(|node| openmaic_script(&node.script, OpenMaicScript::QuizReplay))
    }

    /// The sibling quiz-action adapter drives the narration stage's capture and
    /// replay under the shared OpenMAIC admission generation.
    pub async fn openmaic_quiz_actions_with_generation(
        &self,
        expected_generation: u64,
        request: Value,
        timeout: Duration,
    ) -> Result<Value, String> {
        self.derived_json_checked_script(
            "course.openmaic.scene-build",
            request,
            timeout,
            Some(expected_generation),
            OpenMaicScript::QuizActions,
        )
        .await
    }

    /// Whether the configured scene builder has a usable sibling action adapter.
    pub fn openmaic_quiz_actions_script(&self) -> Option<PathBuf> {
        self.openmaic_node
            .as_ref()
            .and_then(|node| openmaic_script(&node.script, OpenMaicScript::QuizActions))
    }

    async fn derived_json_checked(
        &self,
        capability: &str,
        request: Value,
        timeout: Duration,
        expected_generation: Option<u64>,
    ) -> Result<Value, String> {
        self.derived_json_checked_script(
            capability,
            request,
            timeout,
            expected_generation,
            OpenMaicScript::Scene,
        )
        .await
    }

    async fn derived_json_checked_script(
        &self,
        capability: &str,
        request: Value,
        timeout: Duration,
        expected_generation: Option<u64>,
        script_kind: OpenMaicScript,
    ) -> Result<Value, String> {
        let deadline = Instant::now() + timeout.min(Duration::from_secs(120));
        if !supported(capability) {
            return Err("unsupported derived capability".into());
        }
        let node = if capability == "course.openmaic.scene-build" {
            Some(
                self.openmaic_node
                    .clone()
                    .ok_or("OpenMAIC Node worker not configured")?,
            )
        } else {
            None
        };
        let generation = if node.is_some() {
            let guard = tokio::time::timeout(
                deadline.saturating_duration_since(Instant::now()),
                self.openmaic_admission.lock(),
            )
            .await
            .map_err(|_| "derived worker admission timed out")?;
            if *guard == u64::MAX {
                return Err("OpenMAIC admission exhausted".into());
            }
            if expected_generation.is_some_and(|expected| *guard != expected) {
                return Err("OpenMAIC capability was withdrawn".into());
            }
            Some(*guard)
        } else {
            None
        };
        let disabled = self
            .store
            .submit_wait(|conn| capability_settings::disabled_capabilities(conn))
            .await
            .map_err(|_| "capability settings unavailable")?
            .map_err(|_| "capability settings unavailable")?;
        if disabled.iter().any(|name| name == capability) {
            return Err("derived capability is disabled".into());
        }
        let mut bytes = serde_json::to_vec(&request).map_err(|_| "invalid JSON request")?;
        bytes.push(b'\n');
        if bytes.len() > MAX_INPUT {
            return Err("derived input exceeds bound".into());
        }
        let timeout = deadline.saturating_duration_since(Instant::now());
        let permit = tokio::time::timeout(timeout, self.derived_slots.clone().acquire_owned())
            .await
            .map_err(|_| "derived worker admission timed out")?
            .map_err(|_| "derived worker unavailable")?;
        // Settings may change while all four process slots are occupied.
        let disabled = self
            .store
            .submit_wait(|conn| capability_settings::disabled_capabilities(conn))
            .await
            .map_err(|_| "capability settings unavailable")?
            .map_err(|_| "capability settings unavailable")?;
        if disabled.iter().any(|name| name == capability) {
            return Err("derived capability was disabled while queued".into());
        }
        let (worker, site, program) = if let Some(node) = &node {
            let worker = match script_kind {
                OpenMaicScript::Scene => node.script.clone(),
                other => openmaic_script(&node.script, other)
                    .ok_or_else(|| format!("OpenMAIC {} worker unavailable", other.stage()))?,
            };
            (worker, false, node.executable.clone())
        } else {
            let (worker, site) = self
                .worker_for(capability)
                .ok_or("derived worker is not registered")?;
            (worker, site, self.python.clone())
        };
        let input_sha = hex::encode(Sha256::digest(&bytes));
        let staging = self.staging.clone();
        let store = self.store.clone();
        let admission = self.openmaic_admission.clone();
        let capability = capability.to_owned();
        let runtime = tokio::runtime::Handle::current();
        tokio::task::spawn_blocking(move || {
            let _permit = permit;
            // The blocking pool can queue after semaphore admission. Recheck
            // through the same SQLite owner before creating any process.
            let check_capability = capability.clone();
            let enabled = runtime.block_on(async {
                tokio::time::timeout(
                    deadline.saturating_duration_since(Instant::now()),
                    store.submit_wait(move |conn| {
                        capability_settings::is_enabled(conn, &check_capability)
                    }),
                )
                .await
                .map_err(|_| "derived worker timed out before spawn")?
                .map_err(|_| "capability settings unavailable")?
                .map_err(|_| "capability settings unavailable")
            })?;
            if !enabled {
                return Err("derived capability was disabled before spawn".into());
            }
            let timeout = deadline.saturating_duration_since(Instant::now());
            if timeout.is_zero() {
                return Err("derived worker timed out before spawn".into());
            }
            if node.as_ref().is_some_and(|configured| {
                !executable_matches(&program, &configured.executable_sha256)
                    || match script_kind {
                        OpenMaicScript::Scene => !openmaic_worker_matches(&worker),
                        other => {
                            openmaic_script(&configured.script, other).as_deref()
                                != Some(worker.as_path())
                        }
                    }
            }) {
                return Err("OpenMAIC Node worker unavailable or identity mismatch".into());
            }
            // Serialize the final spawn decision with capability changes. A
            // disable followed by a re-enable does not revive older work.
            let spawn_guard = if let Some(expected) = generation {
                Some(runtime.block_on(async {
                    let guard = tokio::time::timeout(
                        deadline.saturating_duration_since(Instant::now()),
                        admission.clone().lock_owned(),
                    )
                    .await
                    .map_err(|_| "derived worker admission timed out")?;
                    if *guard != expected {
                        return Err("derived capability was withdrawn");
                    }
                    let check_capability = capability.clone();
                    let enabled = tokio::time::timeout(
                        deadline.saturating_duration_since(Instant::now()),
                        store.submit_wait(move |conn| {
                            capability_settings::is_enabled(conn, &check_capability)
                        }),
                    )
                    .await
                    .map_err(|_| "derived worker admission timed out")?
                    .map_err(|_| "capability settings unavailable")?
                    .map_err(|_| "capability settings unavailable")?;
                    if !enabled {
                        return Err("derived capability was disabled before spawn");
                    }
                    Ok::<_, &str>(guard)
                })?)
            } else {
                None
            };
            let timeout = deadline.saturating_duration_since(Instant::now());
            if timeout.is_zero() {
                return Err("derived worker timed out before spawn".into());
            }
            let result = if node.is_some() {
                run_node(&staging, &program, &worker, bytes, timeout, spawn_guard)?
            } else if capability == "course.openmaic.outline-model" {
                // The local-model route is the one derived route whose operator
                // endpoint override must reach the worker; every other derived
                // route keeps the cleared environment.
                run_local_model(&staging, &program, &worker, site, Some(bytes), timeout)?
            } else {
                run(&staging, &program, &worker, site, Some(bytes), timeout)?
            };
            if let Some(expected) = generation {
                let _guard = runtime.block_on(async {
                    let guard = tokio::time::timeout(
                        deadline.saturating_duration_since(Instant::now()),
                        admission.lock_owned(),
                    )
                    .await
                    .map_err(|_| "derived worker admission timed out")?;
                    if *guard != expected {
                        return Err("derived capability was withdrawn");
                    }
                    let enabled = tokio::time::timeout(
                        deadline.saturating_duration_since(Instant::now()),
                        store.submit_wait(move |conn| {
                            capability_settings::is_enabled(conn, &capability)
                        }),
                    )
                    .await
                    .map_err(|_| "derived worker admission timed out")?
                    .map_err(|_| "capability settings unavailable")?
                    .map_err(|_| "capability settings unavailable")?;
                    if !enabled {
                        return Err("derived capability was disabled before result admission");
                    }
                    Ok::<_, &str>(guard)
                })?;
                match script_kind {
                    OpenMaicScript::Scene => {
                        validate_openmaic_result(&result, &request, &input_sha)?
                    }
                    OpenMaicScript::Outline => {
                        validate_openmaic_outline_result(&result, &request, &input_sha)?
                    }
                    OpenMaicScript::QuizReplay => validate_openmaic_quiz_result(&result, &request)?,
                    OpenMaicScript::QuizActions => {
                        validate_openmaic_quiz_actions_result(&result, &request)?
                    }
                    other => validate_openmaic_slide_result(&result, other)?,
                }
            }
            Ok(result)
        })
        .await
        .map_err(|_| "derived worker task failed")?
    }
}

fn validate_openmaic_outline_result(
    result: &Value,
    request: &Value,
    input_sha: &str,
) -> Result<(), String> {
    let doc = &result["document"];
    // The prompt-contract result (`stage: capture|replay`) has its own receipt
    // shape; the offline replay receipt below keeps its original checks.
    if doc["schema"] == "archeaxis.openmaic-outline-prompt-result/v1" {
        return validate_openmaic_outline_prompt_result(result, request);
    }
    if doc["schema"] != "archeaxis.openmaic-outline-replay-result/v1"
        || doc["model_call"] != "NOT_INVOKED"
        || doc["network_performed"] != false
        || doc["canonical_bindings_verified"] != false
    {
        return Err("invalid OpenMAIC outline worker receipt".into());
    }
    // Every non-candidate outcome keeps the worker's own status and reason. It
    // is never rewritten into a candidate, and the caller answers 422 with them.
    if doc["status"] != "CANDIDATE" {
        return if result["exit_code"] == 2
            && doc["status"]
                .as_str()
                .is_some_and(|status| !status.trim().is_empty())
        {
            Ok(())
        } else {
            Err("invalid OpenMAIC outline failure receipt".into())
        };
    }
    if result["exit_code"] != 0
        || doc["input_sha256"] != input_sha
        || doc["input"] != *request
        || doc["response_origin_verification"] != "CALLER_DECLARED_UNVERIFIED"
        || doc["human_review_required"] != true
        || doc["active_content_executed"] != false
    {
        return Err("OpenMAIC outline candidate does not match input".into());
    }
    let outlines = doc["data"]["outlines"]
        .as_array()
        .filter(|items| (1..=30).contains(&items.len()))
        .ok_or("OpenMAIC outline candidate list is unsupported")?;
    if outlines.iter().any(|outline| {
        !outline.is_object()
            || !outline["id"]
                .as_str()
                .is_some_and(|id| id.len() <= 128 && !id.is_empty())
            || !["slide", "quiz"].contains(&outline["type"].as_str().unwrap_or(""))
            || !outline["title"]
                .as_str()
                .is_some_and(|title| !title.trim().is_empty() && title.chars().count() <= 240)
            || !outline["description"]
                .as_str()
                .is_some_and(|description| description.chars().count() <= 16_000)
            || !outline["keyPoints"].as_array().is_some_and(|points| {
                (0..=200).contains(&points.len())
                    && points.iter().all(|point| {
                        point
                            .as_str()
                            .is_some_and(|value| value.chars().count() <= 2_000)
                    })
            })
    }) {
        return Err("OpenMAIC outline candidate entry is unsupported".into());
    }
    Ok(())
}

/// The donor quiz adapter keeps its own fixed receipt for both stages. This
/// checks the schema, the declared outcome and the fixed non-authority claims;
/// Core re-checks every field it consumes before persisting anything.
fn validate_openmaic_quiz_result(result: &Value, request: &Value) -> Result<(), String> {
    let doc = &result["document"];
    if doc["schema"] != "archeaxis.openmaic-quiz-prompt-result/v1"
        || doc["model_call"] != "NOT_INVOKED"
        || doc["network_performed"] != false
        || doc["core_task"] != "NOT_CONNECTED"
        || doc["core_authorization"] != "NOT_ESTABLISHED"
        || doc["canonical_bindings_verified"] != false
        || doc["active_content_executed"] != false
        || doc["persisted"] != false
        || doc["stage"] != request["stage"]
        || doc["request_id"] != request["request_id"]
    {
        return Err("invalid OpenMAIC quiz worker receipt".into());
    }
    let status = doc["status"].as_str().unwrap_or("");
    if status != "CANDIDATE" && status != "PROMPT_CAPTURED" {
        // Every named non-candidate outcome keeps the worker's own status and
        // reason; the caller answers 422 with it and Core writes nothing.
        return if result["exit_code"] == 2 && !status.trim().is_empty() {
            Ok(())
        } else {
            Err("invalid OpenMAIC quiz failure receipt".into())
        };
    }
    if result["exit_code"] != 0 {
        return Err("OpenMAIC quiz worker exit code".into());
    }
    if status == "PROMPT_CAPTURED" {
        let binding = &doc["binding"];
        if binding["schema"] != "archeaxis.openmaic-quiz-prompt-binding/v1"
            || ["system", "user"].iter().any(|key| {
                binding[*key]
                    .as_str()
                    .is_none_or(|text| text.as_bytes().len() > 200_000)
            })
        {
            return Err("OpenMAIC quiz prompt binding is unsupported".into());
        }
    } else if doc["human_review_required"] != true
        || doc["response_origin"] != "CALLER_SUPPLIED_UNVERIFIED"
    {
        return Err("invalid OpenMAIC quiz replay candidate receipt".into());
    }
    Ok(())
}

/// The quiz-action adapter keeps the same two-stage receipt family: the schema,
/// the declared stage and the fixed non-authority claims are checked here, and
/// Core re-checks every action it consumes before persisting anything.
fn validate_openmaic_quiz_actions_result(result: &Value, request: &Value) -> Result<(), String> {
    let doc = &result["document"];
    if doc["schema"] != "archeaxis.openmaic-quiz-actions-prompt-result/v1"
        || doc["model_call"] != "NOT_INVOKED"
        || doc["network_performed"] != false
        || doc["core_task"] != "NOT_CONNECTED"
        || doc["core_authorization"] != "NOT_ESTABLISHED"
        || doc["canonical_bindings_verified"] != false
        || doc["active_content_executed"] != false
        || doc["persisted"] != false
        || doc["rendering_authorized"] != false
        || doc["action_execution"] != "NOT_PERFORMED"
        || doc["stage"] != request["stage"]
        || doc["request_id"] != request["request_id"]
    {
        return Err("invalid OpenMAIC quiz-action worker receipt".into());
    }
    let status = doc["status"].as_str().unwrap_or("");
    if status != "CANDIDATE" && status != "PROMPT_CAPTURED" {
        return if result["exit_code"] == 2 && !status.trim().is_empty() {
            Ok(())
        } else {
            Err("invalid OpenMAIC quiz-action failure receipt".into())
        };
    }
    if result["exit_code"] != 0 {
        return Err("OpenMAIC quiz-action worker exit code".into());
    }
    if status == "PROMPT_CAPTURED" {
        let binding = &doc["binding"];
        if binding["schema"] != "archeaxis.openmaic-quiz-actions-prompt-binding/v1"
            || ["system", "user"].iter().any(|key| {
                binding[*key]
                    .as_str()
                    .is_none_or(|text| text.as_bytes().len() > 200_000)
            })
        {
            return Err("OpenMAIC quiz-action prompt binding is unsupported".into());
        }
    } else if doc["human_review_required"] != true
        || doc["response_origin"] != "CALLER_SUPPLIED_UNVERIFIED"
    {
        return Err("invalid OpenMAIC quiz-action replay candidate receipt".into());
    }
    Ok(())
}

/// The prompt-contract receipt (`stage: capture` or `stage: replay`). Every non-
/// candidate outcome keeps the worker's own status and reason so the caller can
/// answer 422 with them; a candidate additionally keeps its origin declaration.
fn validate_openmaic_outline_prompt_result(result: &Value, request: &Value) -> Result<(), String> {
    let doc = &result["document"];
    if doc["model_call"] != "NOT_INVOKED"
        || doc["network_performed"] != false
        || doc["core_task"] != "NOT_CONNECTED"
        || doc["canonical_bindings_verified"] != false
        || doc["active_content_executed"] != false
        || doc["persisted"] != false
        || doc["stage"] != request["stage"]
        || doc["request_id"] != request["request_id"]
    {
        return Err("invalid OpenMAIC outline prompt receipt".into());
    }
    let status = doc["status"].as_str().unwrap_or("");
    if status != "CANDIDATE" && status != "PROMPT_CAPTURED" {
        return if result["exit_code"] == 2 && !status.trim().is_empty() {
            Ok(())
        } else {
            Err("invalid OpenMAIC outline prompt failure receipt".into())
        };
    }
    if result["exit_code"] != 0 {
        return Err("OpenMAIC outline prompt receipt exit code".into());
    }
    if status == "PROMPT_CAPTURED" {
        let binding = &doc["binding"];
        if binding["schema"] != "archeaxis.openmaic-outline-prompt-binding/v1"
            || ["system", "user"].iter().any(|key| {
                binding[*key]
                    .as_str()
                    .is_none_or(|text| text.as_bytes().len() > 200_000)
            })
        {
            return Err("OpenMAIC outline prompt binding is unsupported".into());
        }
    } else if doc["human_review_required"] != true {
        return Err("invalid OpenMAIC outline prompt candidate receipt".into());
    }
    Ok(())
}

/// The three donor slide adapters keep their own fixed receipts. This checks the
/// schema, the declared outcome and the fixed non-authority claims; Core re-checks
/// every field it consumes before persisting anything.
fn validate_openmaic_slide_result(result: &Value, stage: OpenMaicScript) -> Result<(), String> {
    let doc = &result["document"];
    let expected = match stage {
        OpenMaicScript::SlidePrompt => "archeaxis.openmaic-slide-prompt-result/v1",
        OpenMaicScript::SlideReply => "archeaxis.openmaic-slide-reply-result/v1",
        OpenMaicScript::SlideNormalize => "archeaxis.openmaic-slide-normalize-result/v1",
        _ => return Err("invalid OpenMAIC slide worker stage".into()),
    };
    if doc["schema"] != expected {
        return Err("invalid OpenMAIC slide worker receipt".into());
    }
    // The normalize adapter states its non-authority in its own fields; the
    // prompt and reply adapters also declare that no model was invoked.
    let fixed = match stage {
        OpenMaicScript::SlideNormalize => {
            doc["core_authorization"] != "NOT_ESTABLISHED"
                || doc["canonical_persistence"] != "NOT_PERFORMED"
                || doc["rendering_authorized"] != false
                || doc["full_scene_generation"] != false
        }
        _ => doc["model_call"] != "NOT_INVOKED" || doc["core_authorization"] != "NOT_ESTABLISHED",
    };
    if fixed {
        return Err("invalid OpenMAIC slide worker receipt".into());
    }
    let status = doc["status"].as_str().unwrap_or("");
    let accepted = match stage {
        OpenMaicScript::SlidePrompt => matches!(status, "BUILT" | "REJECTED"),
        OpenMaicScript::SlideReply => matches!(status, "CANDIDATE" | "QUARANTINED" | "REJECTED"),
        OpenMaicScript::SlideNormalize => matches!(status, "CANDIDATE" | "REJECTED"),
        _ => false,
    };
    if !accepted {
        return Err("invalid OpenMAIC slide worker outcome".into());
    }
    if status == "CANDIDATE" && result["exit_code"] != 0 {
        return Err("OpenMAIC slide candidate exit code".into());
    }
    Ok(())
}

fn validate_openmaic_result(
    result: &Value,
    request: &Value,
    input_sha: &str,
) -> Result<(), String> {
    let doc = &result["document"];
    if doc["schema"] != "archeaxis.openmaic-scene-build-result/v1"
        || doc["model_call"] != "NOT_INVOKED"
        || doc["canonical_bindings_verified"] != false
        || doc["human_review_required"] != true
        || doc["active_content_executed"] != false
    {
        return Err("invalid OpenMAIC worker receipt".into());
    }
    if result["exit_code"] == 2 {
        return if matches!(
            doc["status"].as_str(),
            Some("INVALID_REQUEST" | "UPSTREAM_NULL")
        ) && doc["scene"].is_null()
        {
            Ok(())
        } else {
            Err("invalid OpenMAIC failure receipt".into())
        };
    }
    let scene = &doc["scene"];
    if result["exit_code"] != 0
        || doc["status"] != "CANDIDATE"
        || doc["request_id"] != request["request_id"]
        || doc["attempt"] != request["attempt"]
        || doc["input_sha256"] != input_sha
        || doc["source"] != request["source"]
        || doc["source_binding"] != "client_declared_unverified"
        || doc["provider"] != "openmaic"
        || doc["provider_version"] != "1.3.0"
        || doc["generation_version"] != "0.3.28"
        || doc["authority_effect"] != "candidate_only"
        || doc["rendering_authorized"] != false
        || doc["retry_bytes_stable"] != false
        || scene["id"] != request["scene_id"]
        || scene["stageId"] != request["stage_id"]
        || scene["outlineId"] != request["outline"]["id"]
        || scene["type"] != request["outline"]["type"]
        || scene["title"] != request["outline"]["title"]
        || scene["order"] != request["outline"]["order"]
        || scene["actions"] != request["actions"]
        || scene["content"]["type"] != scene["type"]
    {
        return Err("OpenMAIC candidate identity mismatch".into());
    }
    let content_matches = match scene["type"].as_str() {
        Some("quiz") => scene["content"]["questions"] == request["content"]["questions"],
        Some("slide") => {
            scene["content"]["canvas"]["elements"] == request["content"]["elements"]
                && scene["content"]["canvas"]["background"] == request["content"]["background"]
        }
        Some("interactive") => {
            scene["content"]["html"] == request["content"]["html"]
                && scene["content"]["widgetType"] == request["content"]["widgetType"]
                && scene["content"]["widgetConfig"] == request["content"]["widgetConfig"]
        }
        Some("pbl") => scene["content"]["projectV2"] == request["content"]["projectV2"],
        _ => false,
    };
    if !content_matches {
        return Err("OpenMAIC candidate content mismatch".into());
    }
    Ok(())
}

pub(super) fn run(
    staging: &Path,
    python: &Path,
    worker: &Path,
    site: bool,
    input: Option<Vec<u8>>,
    timeout: Duration,
) -> Result<Value, String> {
    run_mode(
        staging,
        python,
        worker,
        input,
        timeout,
        DerivedMode::Python {
            site,
            inventory: false,
            profile: None,
            machine_env: false,
        },
    )
}

/// One bounded Python dispatch that also receives the operator's explicit local
/// model endpoint/model/protocol overrides. Those variables are read only by the
/// local-model route; no request body can name an endpoint.
fn run_local_model(
    staging: &Path,
    python: &Path,
    worker: &Path,
    site: bool,
    input: Option<Vec<u8>>,
    timeout: Duration,
) -> Result<Value, String> {
    run_mode(
        staging,
        python,
        worker,
        input,
        timeout,
        DerivedMode::Python {
            site,
            inventory: false,
            profile: None,
            machine_env: true,
        },
    )
}

fn run_node(
    staging: &Path,
    node: &Path,
    worker: &Path,
    input: Vec<u8>,
    timeout: Duration,
    spawn_admission: Option<tokio::sync::OwnedMutexGuard<u64>>,
) -> Result<Value, String> {
    run_mode(
        staging,
        node,
        worker,
        Some(input),
        timeout,
        DerivedMode::Node { spawn_admission },
    )
}

pub(super) fn node_hello(
    staging: &Path,
    node: &Path,
    worker: &Path,
    timeout: Duration,
) -> Result<Value, String> {
    run_mode(
        staging,
        node,
        worker,
        None,
        timeout,
        DerivedMode::Node {
            spawn_admission: None,
        },
    )
}

pub(super) fn inventory(
    staging: &Path,
    python: &Path,
    worker: &Path,
    site: bool,
    timeout: Duration,
) -> Result<Value, String> {
    run_mode(
        staging,
        python,
        worker,
        None,
        timeout,
        DerivedMode::Python {
            site,
            inventory: true,
            profile: None,
            machine_env: false,
        },
    )
}

pub(super) fn configured_inventory(
    staging: &Path,
    python: &Path,
    worker: &Path,
    site: bool,
    timeout: Duration,
    profile: &archeaxis_domain::model_configuration::Profile,
) -> Result<Value, String> {
    run_mode(
        staging,
        python,
        worker,
        None,
        timeout,
        DerivedMode::Python {
            site,
            inventory: true,
            profile: Some(profile),
            machine_env: false,
        },
    )
}

enum DerivedMode<'a> {
    Python {
        site: bool,
        inventory: bool,
        profile: Option<&'a archeaxis_domain::model_configuration::Profile>,
        /// Forward the operator's explicit local-model endpoint overrides.
        machine_env: bool,
    },
    Node {
        spawn_admission: Option<tokio::sync::OwnedMutexGuard<u64>>,
    },
}

fn run_mode(
    staging: &Path,
    python: &Path,
    worker: &Path,
    input: Option<Vec<u8>>,
    timeout: Duration,
    mode: DerivedMode<'_>,
) -> Result<Value, String> {
    let (site, inventory, profile, machine_env, node, spawn_admission) = match mode {
        DerivedMode::Python {
            site,
            inventory,
            profile,
            machine_env,
        } => (site, inventory, profile, machine_env, false, None),
        DerivedMode::Node { spawn_admission } => (false, false, None, false, true, spawn_admission),
    };
    let dir = tempfile::tempdir_in(staging).map_err(|_| "derived staging unavailable")?;
    let mut command = Command::new(python);
    command.env_clear();
    if inventory || machine_env {
        for key in [
            "ARCHEAXIS_MACHINE_ENDPOINT",
            "ARCHEAXIS_MACHINE_MODEL",
            "ARCHEAXIS_MACHINE_PROTOCOL",
        ] {
            if let Some(value) = std::env::var_os(key) {
                command.env(key, value);
            }
        }
    }
    if let Some(p) = profile {
        command
            .env("ARCHEAXIS_MACHINE_ENDPOINT", &p.endpoint)
            .env("ARCHEAXIS_MACHINE_MODEL", &p.model)
            .env("ARCHEAXIS_MACHINE_PROTOCOL", &p.protocol);
    }
    for key in ["SystemRoot", "WINDIR", "SYSTEMDRIVE"] {
        if let Some(value) = std::env::var_os(key) {
            command.env(key, value);
        }
    }
    for key in [
        "TEMP",
        "TMP",
        "TMPDIR",
        "HOME",
        "USERPROFILE",
        "APPDATA",
        "LOCALAPPDATA",
    ] {
        command.env(key, dir.path());
    }
    // Node gets only its fixed script; Python retains its isolated launch exactly.
    if !node {
        command.arg("-I").arg("-B").arg("-X").arg("utf8");
        if !site {
            command.arg("-S");
        }
    }
    command.arg(worker);
    if input.is_none() {
        command.arg(if inventory { "--probe" } else { "--hello" });
    }
    command
        .current_dir(dir.path())
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped());
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        command.creation_flags(0x08000000);
    }
    let mut child = OwnedChild(command.spawn().map_err(|_| "derived worker spawn failed")?);
    // A capability change can now proceed; it invalidates this generation's result.
    drop(spawn_admission);
    let mut stdin = child.0.stdin.take().ok_or("derived stdin unavailable")?;
    let writer = thread::spawn(move || -> std::io::Result<()> {
        if let Some(bytes) = input {
            stdin.write_all(&bytes)?;
        }
        Ok(())
    });
    let overflow = Arc::new(AtomicBool::new(false));
    fn reader(
        stream: impl Read + Send + 'static,
        limit: usize,
        overflow: Arc<AtomicBool>,
    ) -> thread::JoinHandle<std::io::Result<Vec<u8>>> {
        thread::spawn(move || {
            let mut data = Vec::new();
            stream.take((limit + 1) as u64).read_to_end(&mut data)?;
            if data.len() > limit {
                overflow.store(true, Ordering::Relaxed);
            }
            Ok(data)
        })
    }
    let out_stream = child.0.stdout.take().ok_or("derived stdout unavailable")?;
    let err_stream = child.0.stderr.take().ok_or("derived stderr unavailable")?;
    #[cfg(windows)]
    let pipe_cancel_handles = {
        use std::os::windows::io::AsHandle;
        if inventory {
            Some((
                out_stream
                    .as_handle()
                    .try_clone_to_owned()
                    .map_err(|_| "inventory stdout cancellation handle unavailable")?,
                err_stream
                    .as_handle()
                    .try_clone_to_owned()
                    .map_err(|_| "inventory stderr cancellation handle unavailable")?,
            ))
        } else {
            None
        }
    };
    let stdout = reader(out_stream, MAX_OUTPUT, overflow.clone());
    let stderr = reader(err_stream, MAX_ERROR, overflow.clone());
    let started = Instant::now();
    let status = loop {
        if overflow.load(Ordering::Relaxed) {
            break Err("derived worker output exceeds bound");
        }
        if started.elapsed() >= timeout {
            break Err("derived worker timed out");
        }
        match child.0.try_wait() {
            Ok(Some(status)) => break Ok(status),
            Ok(None) => thread::sleep(Duration::from_millis(5)),
            Err(_) => break Err("derived process status unavailable"),
        }
    };
    drop(child);
    {
        let drain_deadline = Instant::now() + Duration::from_secs(1);
        while !(writer.is_finished() && stdout.is_finished() && stderr.is_finished()) {
            if Instant::now() >= drain_deadline {
                #[cfg(windows)]
                {
                    use std::os::windows::io::AsRawHandle;
                    unsafe extern "system" {
                        fn CancelSynchronousIo(thread: *mut std::ffi::c_void) -> i32;
                        fn GetThreadId(thread: *mut std::ffi::c_void) -> u32;
                        fn OpenThread(access: u32, inherit: i32, id: u32) -> *mut std::ffi::c_void;
                        fn CloseHandle(handle: *mut std::ffi::c_void) -> i32;
                        fn CancelIoEx(
                            file: *mut std::ffi::c_void,
                            overlapped: *mut std::ffi::c_void,
                        ) -> i32;
                    }
                    if let Some((out_handle, err_handle)) = &pipe_cancel_handles {
                        unsafe {
                            CancelIoEx(out_handle.as_raw_handle(), std::ptr::null_mut());
                            CancelIoEx(err_handle.as_raw_handle(), std::ptr::null_mut());
                        }
                    }
                    for handle in [
                        writer.as_raw_handle(),
                        stdout.as_raw_handle(),
                        stderr.as_raw_handle(),
                    ] {
                        // JoinHandle may not carry THREAD_TERMINATE, required for
                        // CancelSynchronousIo. Open only this owned thread's handle.
                        unsafe {
                            let id = GetThreadId(handle);
                            if id != 0 {
                                let cancellable = OpenThread(0x0001, 0, id);
                                if !cancellable.is_null() {
                                    CancelSynchronousIo(cancellable);
                                    CloseHandle(cancellable);
                                }
                            }
                        }
                    }
                }
                let cancel_deadline = Instant::now() + Duration::from_millis(100);
                while !(writer.is_finished() && stdout.is_finished() && stderr.is_finished())
                    && Instant::now() < cancel_deadline
                {
                    thread::sleep(Duration::from_millis(5));
                }
                let all_finished =
                    writer.is_finished() && stdout.is_finished() && stderr.is_finished();
                if writer.is_finished() {
                    let _ = writer.join();
                }
                if stdout.is_finished() {
                    let _ = stdout.join();
                }
                if stderr.is_finished() {
                    let _ = stderr.join();
                }
                if !all_finished {
                    return Err(if inventory {
                        "inventory reader cleanup unverified"
                    } else {
                        "derived reader cleanup unverified"
                    }
                    .into());
                }
                return Err(if inventory {
                    "inventory worker pipe drain timed out"
                } else {
                    "derived worker pipe drain timed out"
                }
                .into());
            }
            thread::sleep(Duration::from_millis(5));
        }
    }
    let written = writer.join();
    let out = stdout.join();
    let err = stderr.join();
    let status = status?;
    written
        .map_err(|_| "derived stdin task failed")?
        .map_err(|_| "derived stdin write failed")?;
    let out = out
        .map_err(|_| "derived stdout task failed")?
        .map_err(|_| "derived stdout read failed")?;
    let err = err
        .map_err(|_| "derived stderr task failed")?
        .map_err(|_| "derived stderr read failed")?;
    if out.len() > MAX_OUTPUT || err.len() > MAX_ERROR {
        return Err("derived worker output exceeds bound".into());
    }
    let document: Value =
        serde_json::from_slice(&out).map_err(|_| "derived worker returned invalid JSON")?;
    if !document.is_object() {
        return Err("derived worker returned non-object JSON".into());
    }
    let exit_code = status
        .code()
        .ok_or("derived worker terminated without exit code")?;
    if !matches!(exit_code, 0 | 2) {
        return Err("derived worker failed with unexpected exit code".into());
    }
    Ok(json!({"exit_code":exit_code,"document":document}))
}

#[cfg(test)]
mod openmaic_source_bound_tests {
    use super::*;

    const ABC_SHA: &str = "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad";
    const EMPTY_SHA: &str = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855";
    const MILLION_A_SHA: &str = "cdc76e5c9914fb9281a1c7e284d73e67f1809a48a497200e046d39ccc7112cd0";

    struct ShortReader {
        bytes: std::io::Cursor<Vec<u8>>,
        max_chunk: usize,
        largest_request: usize,
        calls: usize,
    }

    impl Read for ShortReader {
        fn read(&mut self, output: &mut [u8]) -> std::io::Result<usize> {
            self.calls += 1;
            self.largest_request = self.largest_request.max(output.len());
            let length = output.len().min(self.max_chunk);
            self.bytes.read(&mut output[..length])
        }
    }

    #[test]
    fn short_reads_reach_eof_and_match_the_fixed_digest() {
        let mut reader = ShortReader {
            bytes: std::io::Cursor::new(b"abc".to_vec()),
            max_chunk: 2,
            largest_request: 0,
            calls: 0,
        };
        assert!(bounded_openmaic_source_matches(&mut reader, 3, ABC_SHA));
        assert_eq!(reader.calls, 3);
        assert!(reader.largest_request <= 64 * 1024);
        let mut short = std::io::Cursor::new(b"ab".to_vec());
        assert!(!bounded_openmaic_source_matches(&mut short, 3, ABC_SHA));
        let mut wrong_digest = std::io::Cursor::new(b"abc".to_vec());
        assert!(!bounded_openmaic_source_matches(
            &mut wrong_digest,
            3,
            &"0".repeat(64)
        ));
    }

    #[test]
    fn growth_is_rejected_after_at_most_one_extra_byte() {
        let mut bytes = b"abc".to_vec();
        bytes.extend(std::iter::repeat_n(b'x', 100_000));
        let mut reader = std::io::Cursor::new(bytes);
        assert!(!bounded_openmaic_source_matches(&mut reader, 3, ABC_SHA));
        assert_eq!(reader.position(), 4);
    }

    #[test]
    fn empty_source_still_checks_for_growth() {
        let mut empty = std::io::Cursor::new(Vec::<u8>::new());
        assert!(bounded_openmaic_source_matches(&mut empty, 0, EMPTY_SHA));
        let mut grown = std::io::Cursor::new(vec![b'x']);
        assert!(!bounded_openmaic_source_matches(&mut grown, 0, EMPTY_SHA));
        assert_eq!(grown.position(), 1);
    }

    #[test]
    fn exact_size_limit_is_allowed_and_oversize_never_reads() {
        let mut exact = ShortReader {
            bytes: std::io::Cursor::new(vec![b'a'; 1_000_000]),
            max_chunk: 4096,
            largest_request: 0,
            calls: 0,
        };
        assert!(bounded_openmaic_source_matches(
            &mut exact,
            MAX_OPENMAIC_SOURCE,
            MILLION_A_SHA
        ));
        assert!(exact.largest_request <= 64 * 1024);
        let mut oversized = std::io::Cursor::new(b"abc".to_vec());
        assert!(!bounded_openmaic_source_matches(
            &mut oversized,
            MAX_OPENMAIC_SOURCE + 1,
            ABC_SHA
        ));
        assert_eq!(oversized.position(), 0);
    }

    #[test]
    fn read_error_is_rejected() {
        struct Failing;
        impl Read for Failing {
            fn read(&mut self, _: &mut [u8]) -> std::io::Result<usize> {
                Err(std::io::Error::new(
                    std::io::ErrorKind::Other,
                    "synthetic read failure",
                ))
            }
        }
        assert!(!bounded_openmaic_source_matches(&mut Failing, 3, ABC_SHA));

        struct PartialThenFail(bool);
        impl Read for PartialThenFail {
            fn read(&mut self, output: &mut [u8]) -> std::io::Result<usize> {
                if self.0 {
                    return Err(std::io::Error::new(
                        std::io::ErrorKind::Other,
                        "synthetic read failure",
                    ));
                }
                self.0 = true;
                output[0] = b'a';
                Ok(1)
            }
        }
        assert!(!bounded_openmaic_source_matches(
            &mut PartialThenFail(false),
            3,
            ABC_SHA
        ));
    }
}

#[cfg(test)]
mod openmaic_receipt_tests {
    use super::*;

    fn pair() -> (Value, Value) {
        let request = json!({"request_id":"req", "attempt":1, "source":{"document_id":"doc", "version":1, "content_sha256":"a".repeat(64)},
            "stage_id":"stage", "scene_id":"scene", "outline":{"id":"outline", "type":"quiz", "title":"T", "order":0},
            "content":{"questions":[{"id":"q", "question":"Q"}]}, "actions":[]});
        let result = json!({"exit_code":0, "document":{"schema":"archeaxis.openmaic-scene-build-result/v1", "status":"CANDIDATE",
            "request_id":"req", "attempt":1, "input_sha256":"input-sha", "source":request["source"],
            "source_binding":"client_declared_unverified", "provider":"openmaic", "provider_version":"1.3.0", "generation_version":"0.3.28",
            "authority_effect":"candidate_only", "model_call":"NOT_INVOKED", "canonical_bindings_verified":false,
            "human_review_required":true, "active_content_executed":false, "rendering_authorized":false, "retry_bytes_stable":false,
            "scene":{"id":"scene", "stageId":"stage", "outlineId":"outline", "type":"quiz", "title":"T", "order":0,
                "actions":[], "content":{"type":"quiz", "questions":[{"id":"q", "question":"Q"}]}}}});
        (request, result)
    }

    #[test]
    fn candidate_receipt_must_bind_input_version_identity_and_content() {
        let (request, result) = pair();
        assert!(validate_openmaic_result(&result, &request, "input-sha").is_ok());
        for field in ["input", "source", "scene", "content", "model", "authority"] {
            let mut bad = result.clone();
            match field {
                "input" => bad["document"]["input_sha256"] = json!("other"),
                "source" => bad["document"]["source"]["version"] = json!(2),
                "scene" => bad["document"]["scene"]["id"] = json!("other"),
                "content" => {
                    bad["document"]["scene"]["content"]["questions"][0]["question"] =
                        json!("changed")
                }
                "model" => bad["document"]["model_call"] = json!("INVOKED"),
                _ => bad["document"]["canonical_bindings_verified"] = json!(true),
            }
            assert!(
                validate_openmaic_result(&bad, &request, "input-sha").is_err(),
                "{field}"
            );
        }
    }

    #[test]
    fn upstream_null_is_preserved_as_a_failure_not_a_candidate() {
        let (request, _) = pair();
        let failure = json!({"exit_code":2, "document":{"schema":"archeaxis.openmaic-scene-build-result/v1",
            "status":"UPSTREAM_NULL", "scene":null, "model_call":"NOT_INVOKED", "canonical_bindings_verified":false,
            "human_review_required":true, "active_content_executed":false}});
        assert!(validate_openmaic_result(&failure, &request, "unused").is_ok());
        let mut fake = failure.clone();
        fake["document"]["status"] = json!("CANDIDATE");
        assert!(validate_openmaic_result(&fake, &request, "unused").is_err());
    }
}

#[cfg(test)]
mod withdrawal_tests {
    use super::*;
    use std::{future::Future, task::Poll};

    #[tokio::test]
    async fn openmaic_persistence_rejects_a_withdrawn_generation() {
        let dir = tempfile::tempdir().unwrap();
        let node = dir
            .path()
            .join(if cfg!(windows) { "node.exe" } else { "node" });
        let fake = b"synthetic non-executable";
        std::fs::write(&node, fake).unwrap();
        let worker = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
            .join("../../services/learning-providers/openmaic/scene-build-worker.mjs")
            .canonicalize()
            .unwrap();
        let ex = Executor::open(
            &dir.path().join("db"),
            &dir.path().join("staging"),
            &dir.path().join("unused-python"),
            &dir.path().join("unused-worker"),
        )
        .await
        .unwrap()
        .with_openmaic_node(&node, &hex::encode(Sha256::digest(fake)), &worker)
        .unwrap();
        let old = ex.openmaic_admission_generation().await.unwrap();
        ex.set_openmaic_enabled(false).await.unwrap();
        assert!(ex.openmaic_admission_generation().await.is_err());
        ex.set_openmaic_enabled(true).await.unwrap();
        assert_eq!(
            ex.openmaic_scene_with_generation(old, json!({}), Duration::from_secs(2))
                .await
                .unwrap_err(),
            "OpenMAIC capability was withdrawn"
        );
        let called = Arc::new(AtomicBool::new(false));
        let observed = called.clone();
        assert!(
            ex.commit_openmaic_if_current(old, move |_| {
                observed.store(true, Ordering::SeqCst);
            })
            .await
            .is_err()
        );
        assert!(!called.load(Ordering::SeqCst));
        let current = ex.openmaic_admission_generation().await.unwrap();
        assert_eq!(
            ex.commit_openmaic_if_current(current, |_| 17)
                .await
                .unwrap(),
            17
        );
    }

    #[tokio::test]
    async fn openmaic_queued_persistence_holds_admission_after_caller_disconnects() {
        let dir = tempfile::tempdir().unwrap();
        let node = dir
            .path()
            .join(if cfg!(windows) { "node.exe" } else { "node" });
        let fake = b"synthetic non-executable";
        std::fs::write(&node, fake).unwrap();
        let worker = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
            .join("../../services/learning-providers/openmaic/scene-build-worker.mjs")
            .canonicalize()
            .unwrap();
        let ex = Executor::open(
            &dir.path().join("db"),
            &dir.path().join("staging"),
            &dir.path().join("unused-python"),
            &dir.path().join("unused-worker"),
        )
        .await
        .unwrap()
        .with_openmaic_node(&node, &hex::encode(Sha256::digest(fake)), &worker)
        .unwrap();
        let generation = ex.openmaic_admission_generation().await.unwrap();
        let (started_tx, started_rx) = tokio::sync::oneshot::channel();
        let (release_tx, release_rx) = mpsc::channel();
        let writer = ex.clone();
        let task = tokio::spawn(async move {
            writer
                .commit_openmaic_if_current(generation, move |_| {
                    let _ = started_tx.send(());
                    release_rx.recv_timeout(Duration::from_secs(2)).unwrap();
                })
                .await
        });
        started_rx.await.unwrap();
        task.abort();
        let withdrawing = ex.clone();
        let mut disable =
            tokio::spawn(async move { withdrawing.set_openmaic_enabled(false).await });
        assert!(
            tokio::time::timeout(Duration::from_millis(30), &mut disable)
                .await
                .is_err()
        );
        release_tx.send(()).unwrap();
        assert!(
            tokio::time::timeout(Duration::from_secs(2), disable)
                .await
                .unwrap()
                .unwrap()
                .is_ok()
        );
    }

    #[test]
    fn node_disable_then_reenable_does_not_revive_queued_work() {
        tokio::runtime::Builder::new_current_thread()
            .enable_time()
            .max_blocking_threads(1)
            .build()
            .unwrap()
            .block_on(async {
                let dir = tempfile::tempdir().unwrap();
                let node = dir
                    .path()
                    .join(if cfg!(windows) { "node.exe" } else { "node" });
                let fake = b"synthetic non-executable";
                std::fs::write(&node, fake).unwrap();
                let worker = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
                    .join("../../services/learning-providers/openmaic/scene-build-worker.mjs")
                    .canonicalize()
                    .unwrap();
                let ex = Executor::open(
                    &dir.path().join("db"),
                    &dir.path().join("staging"),
                    &dir.path().join("unused-python"),
                    &dir.path().join("unused-worker"),
                )
                .await
                .unwrap()
                .with_openmaic_node(&node, &hex::encode(Sha256::digest(fake)), &worker)
                .unwrap();
                let (started_send, started_receive) = mpsc::channel();
                let (release_send, release_receive) = mpsc::channel();
                let blocker = tokio::task::spawn_blocking(move || {
                    started_send.send(()).unwrap();
                    release_receive
                        .recv_timeout(Duration::from_secs(10))
                        .unwrap();
                });
                started_receive
                    .recv_timeout(Duration::from_secs(2))
                    .unwrap();
                let mut request = Box::pin(ex.derived_json(
                    "course.openmaic.scene-build",
                    json!({}),
                    Duration::from_secs(5),
                ));
                let end = Instant::now() + Duration::from_secs(2);
                loop {
                    std::future::poll_fn(|cx| {
                        assert!(request.as_mut().poll(cx).is_pending());
                        Poll::Ready(())
                    })
                    .await;
                    if ex.derived_slots.available_permits() == 3 {
                        ex.store.submit_wait(|_| ()).await.unwrap();
                        std::future::poll_fn(|cx| {
                            assert!(request.as_mut().poll(cx).is_pending());
                            Poll::Ready(())
                        })
                        .await;
                        break;
                    }
                    assert!(Instant::now() < end, "request never reached slot admission");
                    tokio::time::sleep(Duration::from_millis(5)).await;
                }
                ex.set_openmaic_enabled(false).await.unwrap();
                ex.set_openmaic_enabled(true).await.unwrap();
                release_send.send(()).unwrap();
                blocker.await.unwrap();
                let result = tokio::time::timeout(Duration::from_secs(3), request)
                    .await
                    .unwrap();
                assert_eq!(result.unwrap_err(), "derived capability was withdrawn");
            });
    }

    fn blocking_queue_withdrawal(capability: &'static str) {
        tokio::runtime::Builder::new_current_thread()
            .enable_time()
            .max_blocking_threads(1)
            .build()
            .unwrap()
            .block_on(async {
                let dir = tempfile::tempdir().unwrap();
                let worker = dir.path().join("worker.py");
                std::fs::write(&worker, "from pathlib import Path\nPath(__file__).with_suffix('.started').touch()\nprint('{}')\n").unwrap();
                let python: PathBuf = std::env::var_os("ARCHEAXIS_PYTHON").unwrap().into();
                let ex = Executor::open_routes(
                    &dir.path().join("db"), &dir.path().join("staging"),
                    &python, &worker, &[(capability, worker.clone())],
                ).await.unwrap();
                let (started_send, started_receive) = mpsc::channel();
                let (release_send, release_receive) = mpsc::channel();
                let blocker = tokio::task::spawn_blocking(move || {
                    started_send.send(()).unwrap();
                    release_receive.recv_timeout(Duration::from_secs(10)).unwrap();
                });
                started_receive.recv_timeout(Duration::from_secs(2)).unwrap();
                let mut request = Box::pin(ex.derived_json(capability, json!({}), Duration::from_secs(5)));
                let end = Instant::now() + Duration::from_secs(2);
                loop {
                    std::future::poll_fn(|cx| {
                        assert!(request.as_mut().poll(cx).is_pending());
                        Poll::Ready(())
                    }).await;
                    if ex.derived_slots.available_permits() == 3 {
                        // The second settings read is already submitted. Drain it,
                        // then poll once to reach the blocked spawn_blocking join.
                        ex.store.submit_wait(|_| ()).await.unwrap();
                        std::future::poll_fn(|cx| {
                            assert!(request.as_mut().poll(cx).is_pending());
                            Poll::Ready(())
                        }).await;
                        break;
                    }
                    assert!(Instant::now() < end, "request never reached slot admission");
                    tokio::time::sleep(Duration::from_millis(5)).await;
                }
                ex.store.submit_wait(move |conn| capability_settings::set_enabled(conn, capability, false))
                    .await.unwrap().unwrap();
                release_send.send(()).unwrap();
                blocker.await.unwrap();
                let result = tokio::time::timeout(Duration::from_secs(3), request).await.unwrap();
                assert!(!worker.with_extension("started").exists(), "withdrawn queued worker was spawned");
                assert_eq!(result.unwrap_err(), "derived capability was disabled before spawn");
                ex.store.submit_wait(move |conn| capability_settings::set_enabled(conn, capability, true))
                    .await.unwrap().unwrap();
                ex.derived_json(capability, json!({}), Duration::from_secs(3)).await.unwrap();
                assert!(worker.with_extension("started").exists(), "enabled control worker did not execute");
            });
    }

    #[test]
    fn search_disabled_in_blocking_queue_never_spawns() {
        blocking_queue_withdrawal("search.semantic");
    }

    #[test]
    fn course_disabled_in_blocking_queue_never_spawns() {
        blocking_queue_withdrawal("course.general");
    }
}

#[cfg(all(test, windows))]
mod inventory_pipe_tests {
    use super::*;

    #[test]
    fn held_descendant_pipes_cancel_and_join_owned_readers() {
        let dir = tempfile::tempdir().unwrap();
        let worker = dir.path().join("inventory.py");
        let holder = dir.path().join("holder.py");
        // Owned fixture descendant exits by itself; never touches a shared process.
        std::fs::write(&holder, "import time\nfrom pathlib import Path\nPath(__file__).with_suffix('.ready').write_text('ready')\ntime.sleep(4)\nPath(__file__).with_suffix('.done').write_text('done')\n").unwrap();
        std::fs::write(&worker, "import subprocess,sys,time,json\nfrom pathlib import Path\np=Path(__file__).with_name('holder.py')\nsubprocess.Popen([sys.executable,'-I','-B',str(p)],stdout=sys.stdout,stderr=sys.stderr,creationflags=0x08000000)\ndeadline=time.monotonic()+2\nwhile not p.with_suffix('.ready').exists():\n assert time.monotonic()<deadline\n time.sleep(.005)\nprint(json.dumps({'synthetic':'candidate'}))\n").unwrap();
        let python: PathBuf = std::env::var_os("ARCHEAXIS_PYTHON")
            .expect("canonical Python required")
            .into();
        let started = Instant::now();
        let result = inventory(dir.path(), &python, &worker, false, Duration::from_secs(3));
        let completed_before_holder = !holder.with_extension("done").exists();
        let deadline = Instant::now() + Duration::from_secs(6);
        while !holder.with_extension("done").exists() && Instant::now() < deadline {
            thread::sleep(Duration::from_millis(10));
        }
        assert!(
            holder.with_extension("ready").exists(),
            "holder never started"
        );
        assert!(
            holder.with_extension("done").exists(),
            "owned holder did not finish"
        );
        assert!(
            completed_before_holder,
            "fixture must hold pipes beyond inventory return"
        );
        assert!(started.elapsed() < Duration::from_secs(7));
        assert_eq!(
            result.unwrap_err(),
            "inventory worker pipe drain timed out",
            "this outcome requires cancellation and joining of every owned reader"
        );
    }
}
