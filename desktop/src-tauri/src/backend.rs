use crate::job::Job;
use crate::protocol::{launch_token, readiness_payload_valid};
use crate::runtime::RuntimeSpec;
use std::collections::VecDeque;
use std::io::{BufRead, BufReader, ErrorKind, Read, Write};
use std::net::{TcpListener, TcpStream};
use std::path::Path;
use std::process::{Child, Command, Stdio};
use std::sync::{mpsc, Arc, Mutex};
use std::thread;
use std::time::{Duration, Instant};

const MIGRATION_TIMEOUT: Duration = Duration::from_secs(120);
const READINESS_TIMEOUT: Duration = Duration::from_secs(30);
const READINESS_POLL_INTERVAL: Duration = Duration::from_millis(500);
const SHUTDOWN_TIMEOUT: Duration = Duration::from_secs(8);
const FORCED_SHUTDOWN_TIMEOUT: Duration = Duration::from_secs(1);
const RESTORE_TIMEOUT: Duration = Duration::from_secs(120);
const MAX_LOG_LINES: usize = 200;
const MAX_ONE_SHOT_OUTPUT_BYTES: usize = 16 * 1024;
const SANITIZED_ENVIRONMENT: [&str; 28] = [
    "PYTHONPATH",
    "PYTHONHOME",
    "VIRTUAL_ENV",
    // canonical ARCHEAXIS_* (AXW-RUN-205) and legacy COGNITIVE_* are both
    // stripped from the inherited environment; the launcher sets its own.
    "ARCHEAXIS_HOST",
    "ARCHEAXIS_PORT",
    "ARCHEAXIS_DATA_DIR",
    "ARCHEAXIS_DB_PATH",
    "ARCHEAXIS_CAPABILITY_ROOT",
    "ARCHEAXIS_DESKTOP_CONTROL",
    "ARCHEAXIS_DESKTOP_LAUNCH_TOKEN",
    "ARCHEAXIS_DESKTOP_WRITE_SCOPES",
    "ARCHEAXIS_EXTERNAL_DEV",
    "ARCHEAXIS_EXTERNAL_DEV_ACTIVE",
    "ARCHEAXIS_RUNTIME_PROFILE",
    "ARCHEAXIS_TEST_WORKSPACE_ROOT",
    "ARCHEAXIS_LAUNCHER_DATA_DIR",
    "ARCHEAXIS_PORTABLE_ROOT",
    "COGNITIVE_PORTABLE_ROOT",
    "COGNITIVE_DATA_DIR",
    "COGNITIVE_DB_PATH",
    "COGNITIVE_HOST",
    "COGNITIVE_PORT",
    "COGNITIVE_DESKTOP_CONTROL",
    "COGNITIVE_DESKTOP_LAUNCH_TOKEN",
    "HERMES_PROJECT_RUNTIME_ROOT",
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "ALL_PROXY",
];

/// The Python backend's readiness route, which reports its own identity.
const DESKTOP_READY_PATH: &str = "/workspace/api/_desktop/ready";

/// The canonical Core's version route, which answers once the launch document has
/// been accepted and the router is serving.
const CORE_VERSION_PATH: &str = "/api/v1/system/version";

/// The exact protocol string the Core requires for a launch that carries a machine
/// token. A near miss is refused rather than defaulted.
pub const CORE_LAUNCH_PROTOCOL: &str = "archeaxis.desktop-launch/v2";

/// Non-secret owner-selected configuration; no provider or model defaults.
#[derive(serde::Deserialize, serde::Serialize)]
#[serde(deny_unknown_fields)]
struct DocumentCheckConfig {
    provider: String,
    model: String,
    credential_ref: String,
    endpoint: Option<String>,
    max_tokens: u64,
    timeout_seconds: u64,
    search_limit: u64,
}
fn config_reparse(metadata: &std::fs::Metadata) -> bool {
    if metadata.file_type().is_symlink() {
        return true;
    }
    #[cfg(windows)]
    {
        use std::os::windows::fs::MetadataExt;
        return metadata.file_attributes() & 0x400 != 0;
    }
    #[cfg(not(windows))]
    {
        false
    }
}
fn config_same_file(left: &std::fs::Metadata, right: &std::fs::Metadata) -> bool {
    if left.len() != right.len() || left.modified().ok() != right.modified().ok() {
        return false;
    }
    #[cfg(windows)]
    {
        use std::os::windows::fs::MetadataExt;
        return left.creation_time() == right.creation_time()
            && left.file_attributes() == right.file_attributes();
    }
    #[cfg(unix)]
    {
        use std::os::unix::fs::MetadataExt;
        return left.dev() == right.dev() && left.ino() == right.ino();
    }
    #[cfg(not(any(windows, unix)))]
    {
        true
    }
}
fn document_check_config(data_dir: &Path) -> (Option<serde_json::Value>, Option<&'static str>) {
    fn load(data_dir: &Path) -> Result<Option<serde_json::Value>, ()> {
        let root = data_dir.canonicalize().map_err(|_| ())?;
        let folder = root.join("config");
        match std::fs::symlink_metadata(&folder) {
            Ok(metadata) if config_reparse(&metadata) || !metadata.is_dir() => return Err(()),
            Ok(_) => {}
            Err(error) if error.kind() == ErrorKind::NotFound => return Ok(None),
            Err(_) => return Err(()),
        }
        let folder_identity = folder.canonicalize().map_err(|_| ())?;
        if !folder_identity.starts_with(&root) {
            return Err(());
        }
        let path = folder.join("document-check.json");
        let before = match std::fs::symlink_metadata(&path) {
            Ok(metadata) => metadata,
            Err(error) if error.kind() == ErrorKind::NotFound => return Ok(None),
            Err(_) => return Err(()),
        };
        if !before.is_file() || config_reparse(&before) || before.len() > 16 * 1024 {
            return Err(());
        }
        let identity = path.canonicalize().map_err(|_| ())?;
        if identity.parent() != Some(folder_identity.as_path()) || !identity.starts_with(&root) {
            return Err(());
        }
        let file = std::fs::File::open(&path).map_err(|_| ())?;
        let opened = file.metadata().map_err(|_| ())?;
        if !config_same_file(&before, &opened) {
            return Err(());
        }
        let mut bytes = Vec::new();
        (&file)
            .take(16 * 1024 + 1)
            .read_to_end(&mut bytes)
            .map_err(|_| ())?;
        let after = std::fs::symlink_metadata(&path).map_err(|_| ())?;
        let final_opened = file.metadata().map_err(|_| ())?;
        if bytes.len() > 16 * 1024
            || config_reparse(&after)
            || !config_same_file(&opened, &after)
            || !config_same_file(&opened, &final_opened)
            || path.canonicalize().map_err(|_| ())? != identity
            || folder.canonicalize().map_err(|_| ())? != folder_identity
            || config_reparse(&std::fs::symlink_metadata(&folder).map_err(|_| ())?)
        {
            return Err(());
        }
        let config: DocumentCheckConfig = serde_json::from_slice(&bytes).map_err(|_| ())?;
        if config.provider.is_empty()
            || config.provider.len() > 64
            || !config
                .provider
                .bytes()
                .all(|byte| byte.is_ascii_alphanumeric() || byte == b'_')
            || config.model.len() > 256
            || config.credential_ref.len() != 41
            || !config.credential_ref.starts_with("aak_cred_")
            || !config.credential_ref[9..]
                .bytes()
                .all(|byte| byte.is_ascii_digit() || (b'a'..=b'f').contains(&byte))
            || !config.model.starts_with(&format!("{}/", config.provider))
            || config
                .model
                .split_once('/')
                .is_none_or(|(_, name)| name.trim().is_empty())
            || !(128..=4096).contains(&config.max_tokens)
            || !(1..=120).contains(&config.timeout_seconds)
            || !(1..=3).contains(&config.search_limit)
        {
            return Err(());
        }
        if let Some(endpoint) = &config.endpoint {
            if !endpoint.starts_with("https://")
                || endpoint.len() > 2048
                || endpoint.contains(['@', '?', '#'])
                || endpoint.chars().any(char::is_whitespace)
            {
                return Err(());
            }
            let parsed = url::Url::parse(endpoint).map_err(|_| ())?;
            if parsed.host_str().is_none()
                || !parsed.username().is_empty()
                || parsed.password().is_some()
            {
                return Err(());
            }
        }
        Ok(Some(serde_json::to_value(config).map_err(|_| ())?))
    }
    match load(data_dir) {
        Ok(value) => (value, None),
        Err(()) => (None, Some("invalid_config")),
    }
}

// Backend manifests contain a complete runtime inventory and can be
// several MiB. Bound the optional provider read without imposing a startup
// requirement on older candidates, which do not carry the Node worker.
const MAX_BACKEND_MANIFEST_BYTES: u64 = 16 * 1024 * 1024;
const OPENMAIC_NODE: &str = "workers/openmaic/node.exe";
const OPENMAIC_NODE_LICENSE: &str = "workers/openmaic/NODE-LICENSE";
const OPENMAIC_SCRIPT: &str = "workers/openmaic/scene-build-worker.mjs";
const OPENMAIC_FIXED_MEMBERS: [(&str, u64, &str); 5] = [
    (
        OPENMAIC_SCRIPT,
        7315,
        "c4a2dad9c96ebd13aa20827410227d2650cda0dac80e3a3927968d1e024779e9",
    ),
    (
        "workers/openmaic/vendor/generation-0.3.28/scene-builder.ts",
        3082,
        "e550ed528f9a017ea0fa1f9cc4a01f7eb22d541d5ada067967d3434393d1bf0a",
    ),
    (
        "workers/openmaic/vendor/generation-0.3.28/nanoid.mjs",
        389,
        "d5d678dfcecc9a4c0f4dae6555c30b4d0ef41a87b00d4d16d744f31ddae6c16e",
    ),
    (
        "workers/openmaic/vendor/generation-0.3.28/LICENSE",
        1065,
        "ba252563743227138231604c9138dd400faca5a10c3cf206b466e5466c565a19",
    ),
    (
        "workers/openmaic/vendor/generation-0.3.28/UPSTREAM.md",
        1134,
        "83962cee94daba3596fba378867756981c87a8bd7839ced586510643c113d579",
    ),
];

#[derive(serde::Deserialize)]
#[serde(deny_unknown_fields)]
struct OpenMaicBundleEntry {
    status: String,
    // Value makes this field required even when its value is JSON null.
    node_sha256: serde_json::Value,
}

#[derive(serde::Deserialize)]
#[serde(deny_unknown_fields)]
struct OpenMaicFileEntry {
    bytes: u64,
    sha256: String,
}

struct OpenMaicFiles(std::collections::HashMap<String, OpenMaicFileEntry>);

impl<'de> serde::Deserialize<'de> for OpenMaicFiles {
    fn deserialize<D>(deserializer: D) -> Result<Self, D::Error>
    where
        D: serde::Deserializer<'de>,
    {
        struct FilesVisitor;
        impl<'de> serde::de::Visitor<'de> for FilesVisitor {
            type Value = OpenMaicFiles;

            fn expecting(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
                formatter.write_str("a backend runtime files object")
            }

            fn visit_map<A>(self, mut map: A) -> Result<Self::Value, A::Error>
            where
                A: serde::de::MapAccess<'de>,
            {
                let mut members = std::collections::HashMap::new();
                while let Some(name) = map.next_key::<String>()? {
                    if name == OPENMAIC_NODE
                        || name == OPENMAIC_NODE_LICENSE
                        || OPENMAIC_FIXED_MEMBERS
                            .iter()
                            .any(|(path, _, _)| *path == name.as_str())
                    {
                        let entry = map.next_value::<OpenMaicFileEntry>()?;
                        if members.insert(name, entry).is_some() {
                            return Err(serde::de::Error::custom("duplicate OpenMAIC member"));
                        }
                    } else {
                        map.next_value::<serde::de::IgnoredAny>()?;
                    }
                }
                Ok(OpenMaicFiles(members))
            }
        }
        deserializer.deserialize_map(FilesVisitor)
    }
}

struct BackendManifestSelection {
    schema: Option<String>,
    openmaic_scene_build: Option<OpenMaicBundleEntry>,
    files: Option<OpenMaicFiles>,
}

impl<'de> serde::Deserialize<'de> for BackendManifestSelection {
    fn deserialize<D>(deserializer: D) -> Result<Self, D::Error>
    where
        D: serde::Deserializer<'de>,
    {
        struct ManifestVisitor;
        impl<'de> serde::de::Visitor<'de> for ManifestVisitor {
            type Value = BackendManifestSelection;

            fn expecting(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
                formatter.write_str("a backend runtime manifest object")
            }

            fn visit_map<A>(self, mut map: A) -> Result<Self::Value, A::Error>
            where
                A: serde::de::MapAccess<'de>,
            {
                let mut seen = std::collections::HashSet::new();
                let mut schema = None;
                let mut openmaic_scene_build = None;
                let mut files = None;
                while let Some(field) = map.next_key::<String>()? {
                    if !seen.insert(field.clone()) {
                        return Err(serde::de::Error::custom("duplicate backend manifest field"));
                    }
                    match field.as_str() {
                        "schema" => schema = Some(map.next_value::<String>()?),
                        "openmaic_scene_build" => {
                            openmaic_scene_build = Some(map.next_value::<OpenMaicBundleEntry>()?);
                        }
                        "files" => files = Some(map.next_value::<OpenMaicFiles>()?),
                        _ => {
                            map.next_value::<serde::de::IgnoredAny>()?;
                        }
                    }
                }
                Ok(BackendManifestSelection {
                    schema,
                    openmaic_scene_build,
                    files,
                })
            }
        }
        deserializer.deserialize_map(ManifestVisitor)
    }
}

fn local_runtime_path_shape(path: &Path) -> bool {
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

fn unlinked_runtime_file(path: &Path) -> bool {
    if !local_runtime_path_shape(path) {
        return false;
    }
    for ancestor in path.ancestors() {
        let Ok(metadata) = std::fs::symlink_metadata(ancestor) else {
            return false;
        };
        if config_reparse(&metadata) {
            return false;
        }
        if ancestor == path && !metadata.is_file() {
            return false;
        }
    }
    true
}

// Match the existing Win32 handle identity strategy in the Recovery module.
// No file content is read before the handle reports a single regular file.
#[cfg(windows)]
#[repr(C)]
#[derive(Default)]
struct RuntimeFileTime {
    low: u32,
    high: u32,
}

#[cfg(windows)]
#[repr(C)]
#[derive(Default)]
struct RuntimeFileInformation {
    attributes: u32,
    creation_time: RuntimeFileTime,
    last_access_time: RuntimeFileTime,
    last_write_time: RuntimeFileTime,
    volume_serial: u32,
    size_high: u32,
    size_low: u32,
    number_of_links: u32,
    file_index_high: u32,
    file_index_low: u32,
}

#[cfg(windows)]
#[link(name = "Kernel32")]
unsafe extern "system" {
    fn GetFileInformationByHandle(
        file: *mut std::ffi::c_void,
        information: *mut RuntimeFileInformation,
    ) -> i32;
}

#[derive(Clone, Copy, PartialEq, Eq)]
struct RuntimeFileIdentity {
    volume: u64,
    file: u64,
}

#[cfg(windows)]
fn runtime_file_identity(file: &std::fs::File) -> Option<RuntimeFileIdentity> {
    use std::os::windows::io::AsRawHandle;
    let mut info = RuntimeFileInformation::default();
    // SAFETY: `file` owns a live handle and `info` has the Win32 ABI layout.
    let success = unsafe { GetFileInformationByHandle(file.as_raw_handle().cast(), &mut info) };
    if success == 0 || info.number_of_links != 1
        || info.attributes & (0x10 | 0x400) != 0 // directory or reparse point
        || !file.metadata().ok()?.is_file()
    {
        return None;
    }
    let index = ((info.file_index_high as u64) << 32) | info.file_index_low as u64;
    if index == 0 {
        return None;
    }
    Some(RuntimeFileIdentity {
        volume: info.volume_serial as u64,
        file: index,
    })
}

#[cfg(unix)]
fn runtime_file_identity(file: &std::fs::File) -> Option<RuntimeFileIdentity> {
    use std::os::unix::fs::MetadataExt;
    let metadata = file.metadata().ok()?;
    if !metadata.is_file() || metadata.nlink() != 1 {
        return None;
    }
    Some(RuntimeFileIdentity {
        volume: metadata.dev(),
        file: metadata.ino(),
    })
}

#[cfg(not(any(windows, unix)))]
fn runtime_file_identity(_file: &std::fs::File) -> Option<RuntimeFileIdentity> {
    None
}

fn open_runtime_handle(path: &Path) -> Option<std::fs::File> {
    let mut options = std::fs::OpenOptions::new();
    options.read(true);
    #[cfg(windows)]
    {
        use std::os::windows::fs::OpenOptionsExt;
        // Reject a replaced final-component reparse point on the handle, and
        // keep write/delete sharing closed while this identity is inspected.
        options.custom_flags(0x0020_0000).share_mode(0x0000_0001);
    }
    options.open(path).ok()
}

fn runtime_file_is_current(
    path: &Path,
    file: &std::fs::File,
    identity: RuntimeFileIdentity,
) -> bool {
    if !unlinked_runtime_file(path) || runtime_file_identity(file) != Some(identity) {
        return false;
    }
    let Some(current) = open_runtime_handle(path) else {
        return false;
    };
    runtime_file_identity(&current) == Some(identity)
}

fn open_single_link_runtime_file(path: &Path) -> Option<(std::fs::File, RuntimeFileIdentity)> {
    if !unlinked_runtime_file(path) {
        return None;
    }
    let file = open_runtime_handle(path)?;
    let identity = runtime_file_identity(&file)?;
    if !runtime_file_is_current(path, &file, identity) {
        return None;
    }
    Some((file, identity))
}

fn read_backend_manifest(path: &Path, limit: u64) -> Option<Vec<u8>> {
    let (file, identity) = open_single_link_runtime_file(path)?;
    let before = file.metadata().ok()?;
    if before.len() > limit {
        return None;
    }
    let mut bytes = Vec::new();
    (&file)
        .take(limit.checked_add(1)?)
        .read_to_end(&mut bytes)
        .ok()?;
    let final_opened = file.metadata().ok()?;
    if bytes.len() as u64 > limit
        || !runtime_file_is_current(path, &file, identity)
        || !config_same_file(&before, &final_opened)
    {
        return None;
    }
    Some(bytes)
}

/// Select only the staged fixed paths. The manifest digest binds bytes that
/// Core checks again; it is not proof of the executable's origin or version.
fn openmaic_node_worker_for(root: &Path) -> Option<serde_json::Value> {
    let node = root.join(OPENMAIC_NODE);
    let script = root.join(OPENMAIC_SCRIPT);
    let (node_file, node_identity) = open_single_link_runtime_file(&node)?;
    let (script_file, script_identity) = open_single_link_runtime_file(&script)?;
    let manifest = read_backend_manifest(
        &root.join("backend-runtime-manifest.json"),
        MAX_BACKEND_MANIFEST_BYTES,
    )?;
    let selection: BackendManifestSelection = serde_json::from_slice(&manifest).ok()?;
    if selection.schema.as_deref() != Some("archeaxis.backend-runtime/v1") {
        return None;
    }
    let entry = selection.openmaic_scene_build?;
    let sha = entry.node_sha256.as_str()?;
    if entry.status != "INCLUDED"
        || sha.len() != 64
        || !sha
            .bytes()
            .all(|c| c.is_ascii_digit() || (b'a'..=b'f').contains(&c))
    {
        return None;
    }
    let members = selection.files?.0;
    for (path, size, expected_sha) in OPENMAIC_FIXED_MEMBERS {
        let member = members.get(path)?;
        if member.bytes != size || member.sha256.as_str() != expected_sha {
            return None;
        }
    }
    if members.get(OPENMAIC_NODE)?.sha256.as_str() != sha {
        return None;
    }
    let mut targets = vec![
        (OPENMAIC_NODE, 512 * 1024 * 1024_u64),
        (OPENMAIC_NODE_LICENSE, 1_000_000_u64),
    ];
    targets.extend(
        OPENMAIC_FIXED_MEMBERS
            .iter()
            .map(|(path, _, _)| (*path, 1_000_000_u64)),
    );
    let mut node_handle = Some((node_file, node_identity));
    let mut script_handle = Some((script_file, script_identity));
    let mut opened = Vec::with_capacity(targets.len());
    for (relative, limit) in targets {
        let member = members.get(relative)?;
        if member.bytes == 0
            || member.bytes > limit
            || member.sha256.len() != 64
            || !member
                .sha256
                .bytes()
                .all(|c| c.is_ascii_digit() || (b'a'..=b'f').contains(&c))
        {
            return None;
        }
        let path = root.join(relative);
        let (file, identity) = if relative == OPENMAIC_NODE {
            node_handle.take()?
        } else if relative == OPENMAIC_SCRIPT {
            script_handle.take()?
        } else {
            open_single_link_runtime_file(&path)?
        };
        if file.metadata().ok()?.len() != member.bytes {
            return None;
        }
        opened.push((path, file, identity, member.bytes));
    }
    for (path, file, identity, size) in &opened {
        if !runtime_file_is_current(path, file, *identity) || file.metadata().ok()?.len() != *size {
            return None;
        }
    }
    Some(serde_json::json!({
        "executable": contract_path(&node),
        "executable_sha256": sha,
        "script": contract_path(&script),
    }))
}

fn configured_core_launch_document(
    token: &str,
    machine_token: &str,
    session_id: &str,
    spec: &CoreSpec,
) -> String {
    let mut document: serde_json::Value = serde_json::from_str(&core_launch_document(
        token,
        machine_token,
        session_id,
        spec.text_worker.as_ref(),
    ))
    .expect("generated launch document");
    if spec.text_worker.is_some() {
        if let Some(core_dir) = spec.executable.parent() {
            if core_dir.file_name() == Some(std::ffi::OsStr::new("core"))
                && spec.executable.file_name() == Some(std::ffi::OsStr::new("archeaxis-api.exe"))
            {
                if let Some(provider) = core_dir.parent().and_then(openmaic_node_worker_for) {
                    document["openmaic_node_worker"] = provider;
                }
            }
        }
    }
    let (config, error) = document_check_config(&spec.data_dir);
    if let Some(config) = config {
        document["document_check_config"] = config;
    }
    if let Some(error) = error {
        document["document_check_config_error"] = serde_json::json!(error);
    }
    document.to_string()
}

/// The canonical Core's launch inputs.
///
/// Unlike the legacy Python entrypoint, which reads its identity from environment
/// variables, the Core takes only its workspace database path and port as arguments
/// and reads a JSON launch document from stdin. The launch token it is given here is
/// the same one the frontend must present, so the host keeps ownership of it.
#[derive(Clone, Debug)]
pub struct CoreSpec {
    pub executable: std::path::PathBuf,
    pub workspace_db: std::path::PathBuf,
    pub cwd: std::path::PathBuf,
    pub data_dir: std::path::PathBuf,
    /// The worker declaration, when the candidate carries one.
    pub text_worker: Option<serde_json::Value>,
}

/// Build the launch document the Core reads from stdin.
///
/// The two credentials must differ: the Core refuses a machine token equal to the
/// launch token, and it requires the launch actor to be exactly `human` under the v2
/// protocol.
pub fn core_launch_document(
    token: &str,
    machine_token: &str,
    session_id: &str,
    text_worker: Option<&serde_json::Value>,
) -> String {
    let mut document = serde_json::json!({
        "launch_token": token,
        "session_id": session_id,
        "protocol": CORE_LAUNCH_PROTOCOL,
        "machine_token": machine_token,
        "actor": "human",
    });
    // Without a worker the Core mounts only its projections table. Declaring one is
    // what makes the runtime table - and with it the capability routes - reachable.
    if let Some(worker) = text_worker {
        document["text_worker"] = worker.clone();
    }
    document.to_string()
}

/// The worker declaration the Core needs before it will mount its runtime routes.
///
/// Paths are absolute: the Core resolves a relative path against a declared root and
/// refuses one that has no root, so deriving them here keeps that rule out of reach.
/// A canonical Windows path carries an extended-length prefix, `\\?\`, that the launch
/// contract does not expect: the Core refuses such a path in the worker profile. Paths here
/// are derived from a canonicalised root, so the prefix is removed as they cross into the
/// document. Comparison still uses the canonical form; only the published text changes.
fn contract_path(path: &Path) -> String {
    let text = path.to_string_lossy();
    let trimmed = text
        .strip_prefix(r"\\?\")
        .or_else(|| text.strip_prefix(r"\\.\"))
        .unwrap_or(&text);
    trimmed.to_owned()
}

fn text_worker_for(root: &Path, python: &Path, data_dir: &Path) -> Option<serde_json::Value> {
    let workers = root.join("workers");
    let script = workers.join("transport").join("text_ndjson.py");
    if !script.is_file() {
        return None;
    }
    let mut worker = serde_json::json!({
        "python": contract_path(python),
        "script": contract_path(&script),
        "staging": contract_path(&data_dir.join("worker-staging")),
    });
    // The single-source manifest names each capability and the worker that implements
    // it. Reading it here rather than embedding a copy keeps one source of truth.
    if let Ok(raw) = std::fs::read_to_string(workers.join("routes.json")) {
        if let Ok(parsed) = serde_json::from_str::<serde_json::Value>(&raw) {
            if let Some(map) = parsed.get("routes").and_then(serde_json::Value::as_object) {
                let mut routes = Vec::new();
                for (capability, scripts) in map {
                    let Some(relative) = scripts
                        .as_array()
                        .and_then(|entries| entries.first())
                        .and_then(serde_json::Value::as_str)
                    else {
                        continue;
                    };
                    routes.push(serde_json::json!({
                        "capability": capability,
                        "script": contract_path(&workers.join(relative.replace('/', "\\"))),
                    }));
                }
                worker["routes"] = serde_json::Value::Array(routes);
            }
        }
    }
    Some(worker)
}

impl CoreSpec {
    /// Find the canonical Core beside the runtime the resolver chose.
    ///
    /// The resolver accepts `<root>/runtime/python.exe` and
    /// `<root>/runtime/python/python.exe`. Both use the one corresponding
    /// `<root>/core/archeaxis-api.exe`; unrelated ancestors are never searched.
    pub fn beside_runtime(runtime: &RuntimeSpec) -> Option<Self> {
        if runtime.python.file_name() != Some(std::ffi::OsStr::new("python.exe")) {
            return None;
        }
        let parent = runtime.python.parent()?;
        let runtime_dir = if parent.file_name() == Some(std::ffi::OsStr::new("python")) {
            parent.parent()?
        } else {
            parent
        };
        if runtime_dir.file_name() != Some(std::ffi::OsStr::new("runtime")) {
            return None;
        }
        let root = runtime_dir.parent()?;
        let executable = root.join("core").join("archeaxis-api.exe");
        if !executable.is_file() {
            return None;
        }
        let workspace_db = runtime.data_dir.join("archeaxis.sqlite");
        Some(Self {
            executable,
            workspace_db,
            cwd: runtime.data_dir.clone(),
            data_dir: runtime.data_dir.clone(),
            text_worker: text_worker_for(root, &runtime.python, &runtime.data_dir),
        })
    }
}

type LogBuffer = Arc<Mutex<VecDeque<String>>>;

/// Process observations only; a reaped process alone is not a graceful shutdown.
#[derive(Clone, Debug, serde::Serialize)]
pub struct ShutdownReport {
    pub pid: u32,
    pub method: &'static str,
    pub outcome: &'static str,
    pub request_acknowledged: bool,
    pub forced_attempted: bool,
    pub return_code: Option<i32>,
    pub wait_reaped: bool,
    pub elapsed_ms: u64,
}

fn request_core_shutdown(
    port: u16,
    token: &str,
    session: &str,
    deadline: Instant,
) -> Result<(), ()> {
    let remaining = || {
        deadline
            .checked_duration_since(Instant::now())
            .filter(|d| !d.is_zero())
            .ok_or(())
    };
    let mut stream = TcpStream::connect_timeout(
        &([127, 0, 0, 1], port).into(),
        remaining()?.min(Duration::from_millis(300)),
    )
    .map_err(|_| ())?;
    stream
        .set_write_timeout(Some(remaining()?))
        .map_err(|_| ())?;
    let body = serde_json::json!({"session_id":session}).to_string();
    write!(stream, "POST /api/v1/system/shutdown HTTP/1.0\r\nHost: 127.0.0.1:{port}\r\nX-ArcheAxis-Launch-Token: {token}\r\nContent-Type: application/json\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{body}", body.len()).map_err(|_| ())?;
    let mut bytes = Vec::new();
    loop {
        stream
            .set_read_timeout(Some(remaining()?))
            .map_err(|_| ())?;
        let mut chunk = [0u8; 1024];
        let n = stream.read(&mut chunk).map_err(|_| ())?;
        if n == 0 {
            break;
        }
        bytes.extend_from_slice(&chunk[..n]);
        if bytes.len() > 4096 {
            return Err(());
        }
    }
    shutdown_ack_valid(&bytes, session).then_some(()).ok_or(())
}

fn shutdown_ack_valid(bytes: &[u8], session: &str) -> bool {
    let Ok(raw) = std::str::from_utf8(bytes) else {
        return false;
    };
    let Some((headers, body)) = raw.split_once("\r\n\r\n") else {
        return false;
    };
    if !matches!(
        headers.lines().next(),
        Some("HTTP/1.0 202 Accepted" | "HTTP/1.1 202 Accepted")
    ) {
        return false;
    }
    let sizes: Vec<_> = headers
        .lines()
        .filter_map(|line| {
            line.to_ascii_lowercase()
                .strip_prefix("content-length: ")
                .map(str::to_owned)
        })
        .collect();
    if sizes.len() != 1 || sizes[0].parse::<usize>().ok() != Some(body.len()) {
        return false;
    }
    let Ok(value) = serde_json::from_str::<serde_json::Value>(body) else {
        return false;
    };
    value["schema"] == "archeaxis.session-shutdown/v1"
        && value["session_id"] == session
        && value["state"] == "draining"
}

pub struct BackendProcess {
    pub port: u16,
    pub token: String,
    child: Child,
    job: Option<Job>,
    logs: LogBuffer,
    canonical_session: Option<String>,
    shutdown_report: Option<ShutdownReport>,
    shutdown_report_path: Option<std::path::PathBuf>,
}

impl BackendProcess {
    pub fn launch(runtime: &RuntimeSpec) -> Result<Self, String> {
        std::fs::create_dir_all(&runtime.data_dir)
            .map_err(|error| format!("failed to create desktop data directory: {error}"))?;
        let job = Job::new()?;
        let migration_logs = new_log_buffer();
        run_migration(runtime, &job, Arc::clone(&migration_logs))?;

        let port = choose_loopback_port()?;
        let token = launch_token()?;
        let logs = new_log_buffer();
        let mut command = runtime_command(runtime);
        command
            .args(["-m", "app.runtime_entrypoint", "core"])
            .env("ARCHEAXIS_HOST", "127.0.0.1")
            .env("ARCHEAXIS_PORT", port.to_string())
            .env("ARCHEAXIS_DESKTOP_CONTROL", "stdio-v1")
            .env("ARCHEAXIS_DESKTOP_LAUNCH_TOKEN", &token)
            .env("ARCHEAXIS_DESKTOP_WRITE_SCOPES", "workspace:write")
            // legacy COGNITIVE_* mirrors keep two stable releases readable
            // (AXW-RUN-205); Python prefers ARCHEAXIS_* when both exist.
            .env("COGNITIVE_HOST", "127.0.0.1")
            .env("COGNITIVE_PORT", port.to_string())
            .env("COGNITIVE_DESKTOP_CONTROL", "stdio-v1")
            .env("COGNITIVE_DESKTOP_LAUNCH_TOKEN", &token)
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::piped());
        let mut child = command
            .spawn()
            .map_err(|error| format!("failed to start desktop Core: {error}"))?;
        if let Err(error) = job.assign(&child) {
            let _ = child.kill();
            let _ = child.wait();
            return Err(error);
        }
        drain_child_output(&mut child, Arc::clone(&logs), "core");
        if let Err(error) = wait_for_readiness(&mut child, port, &token, &logs, DESKTOP_READY_PATH)
        {
            let _ = child.kill();
            let _ = child.wait();
            return Err(error);
        }
        Ok(Self {
            port,
            token,
            child,
            job: Some(job),
            logs,
            canonical_session: None,
            shutdown_report: None,
            shutdown_report_path: None,
        })
    }

    /// Launch the canonical Rust Core in place of the legacy Python entrypoint.
    ///
    /// The Core's contract differs from the entrypoint's in three ways, and all three
    /// are load-bearing: it takes its workspace database and port as arguments rather
    /// than through the environment; it reads its launch identity as a JSON document on
    /// stdin and refuses the launch if that document is absent or malformed; and it
    /// signals readiness by serving HTTP rather than by printing. Because this host
    /// chooses the port itself, readiness is probed on the Core's own version route.
    pub fn launch_core(spec: &CoreSpec) -> Result<Self, String> {
        std::fs::create_dir_all(&spec.data_dir)
            .map_err(|error| format!("failed to create desktop data directory: {error}"))?;
        let job = Job::new()?;
        let port = choose_loopback_port()?;
        let token = launch_token()?;
        // A second, distinct credential: the Core refuses a machine token equal to the
        // launch token. The session identifier is the first half of it, which is already
        // the thirty-two hex characters the Core requires.
        let machine_token = launch_token()?;
        let session_id = machine_token[..32].to_owned();
        let document = configured_core_launch_document(&token, &machine_token, &session_id, spec);
        let logs = new_log_buffer();
        let mut command = Command::new(&spec.executable);
        command
            .arg(&spec.workspace_db)
            .arg(port.to_string())
            .current_dir(&spec.cwd)
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::piped());
        for name in SANITIZED_ENVIRONMENT {
            command.env_remove(name);
        }
        let mut child = command
            .spawn()
            .map_err(|error| format!("failed to start canonical Core: {error}"))?;
        if let Err(error) = job.assign(&child) {
            let _ = child.kill();
            let _ = child.wait();
            return Err(error);
        }
        // Deliver the launch document, then close stdin: the Core reads to end of input
        // before it validates anything, so leaving the pipe open would hang the launch.
        match child.stdin.take() {
            Some(mut stdin) => {
                if stdin.write_all(document.as_bytes()).is_err() {
                    let _ = child.kill();
                    let _ = child.wait();
                    return Err("failed to deliver the Core launch document".to_owned());
                }
            }
            None => {
                let _ = child.kill();
                let _ = child.wait();
                return Err("Core launch input pipe is unavailable".to_owned());
            }
        }
        drain_child_output(&mut child, Arc::clone(&logs), "core");
        if let Err(error) = wait_for_readiness(&mut child, port, &token, &logs, CORE_VERSION_PATH) {
            let _ = child.kill();
            let _ = child.wait();
            // A Core that starts and then disappears leaves no evidence anywhere else: what it
            // said went into the log buffer, which normally only reaches the window. Writing it
            // beside the data it was launched with is what makes that failure diagnosable after
            // the fact, and it changes nothing about what the launch itself does.
            let captured = logs
                .lock()
                .map(|lines| lines.iter().cloned().collect::<Vec<_>>().join("\n"))
                .unwrap_or_default();
            let _ = std::fs::write(spec.data_dir.join("core-launch-failure.log"), captured);
            // Redacted: the document carries two credentials, and a diagnostic file is not a
            // place to leave them. What matters for diagnosis is every other field.
            let document = document
                .replace(&token, "<launch-token>")
                .replace(&machine_token, "<machine-token>");
            let _ = std::fs::write(spec.data_dir.join("core-launch-document.json"), document);
            return Err(error);
        }
        Ok(Self {
            port,
            token,
            child,
            job: Some(job),
            logs,
            canonical_session: Some(session_id),
            shutdown_report: None,
            shutdown_report_path: Some(spec.data_dir.join("core-shutdown-result.json")),
        })
    }

    pub fn shutdown(&mut self) -> ShutdownReport {
        self.shutdown_with_timeout(SHUTDOWN_TIMEOUT)
    }

    pub fn shutdown_with_timeout(&mut self, graceful_timeout: Duration) -> ShutdownReport {
        if let Some(report) = &self.shutdown_report {
            return report.clone();
        }
        let started = Instant::now();
        let mut report = ShutdownReport {
            pid: self.child.id(),
            method: if self.canonical_session.is_some() {
                "session_http"
            } else {
                "legacy_stdio"
            },
            outcome: "UNKNOWN",
            request_acknowledged: false,
            forced_attempted: false,
            return_code: None,
            wait_reaped: false,
            elapsed_ms: 0,
        };
        if let Ok(Some(status)) = self.child.try_wait() {
            report.return_code = status.code();
            report.wait_reaped = true;
            report.outcome = "ALREADY_EXITED";
        } else if self.job.is_some() {
            if let Some(session) = &self.canonical_session {
                report.request_acknowledged = request_core_shutdown(
                    self.port,
                    &self.token,
                    session,
                    started + graceful_timeout,
                )
                .is_ok();
            } else if let Some(mut stdin) = self.child.stdin.take() {
                let _ = stdin.write_all(b"shutdown\n");
                let _ = stdin.flush();
            }
            let (status, forced) = shutdown_job_owned_child(
                &mut self.child,
                &mut self.job,
                graceful_timeout.saturating_sub(started.elapsed()),
                FORCED_SHUTDOWN_TIMEOUT,
            );
            report.forced_attempted = forced;
            if let Some(status) = status {
                report.return_code = status.code();
                report.wait_reaped = true;
                report.outcome = if forced {
                    "FORCED"
                } else if report.request_acknowledged && status.code() == Some(0) {
                    "GRACEFUL"
                } else if status.code() != Some(0) {
                    "ERROR"
                } else {
                    "UNKNOWN"
                };
            }
        }
        report.elapsed_ms = started.elapsed().as_millis() as u64;
        if let Some(path) = &self.shutdown_report_path {
            if let Ok(bytes) = serde_json::to_vec_pretty(&report) {
                let _ = std::fs::write(path, bytes);
            }
        }
        self.shutdown_report = Some(report.clone());
        report
    }

    pub fn log_tail(&self) -> String {
        format_logs(&self.logs)
    }

    pub fn exit_diagnostic(&mut self) -> Result<Option<String>, String> {
        self.child
            .try_wait()
            .map(|status| {
                status
                    .map(|status| format!("desktop Core exited with {status}\n{}", self.log_tail()))
            })
            .map_err(|error| format!("failed to inspect desktop Core: {error}"))
    }
}

impl Drop for BackendProcess {
    fn drop(&mut self) {
        self.shutdown();
        let _ = &self.job;
    }
}

fn shutdown_job_owned_child(
    child: &mut Child,
    job: &mut Option<Job>,
    graceful_timeout: Duration,
    forced_timeout: Duration,
) -> (Option<std::process::ExitStatus>, bool) {
    if let Ok(status) = wait_for_exit(child, graceful_timeout) {
        return (Some(status), false);
    }
    if job.take().is_none() {
        let _ = child.kill();
    }
    (wait_for_exit(child, forced_timeout).ok(), true)
}

struct BoundedOutput {
    bytes: Vec<u8>,
    truncated: bool,
}

fn read_bounded_output<R: Read>(mut reader: R) -> BoundedOutput {
    let mut bytes = Vec::with_capacity(MAX_ONE_SHOT_OUTPUT_BYTES);
    let mut truncated = false;
    let mut chunk = [0_u8; 4096];
    loop {
        let Ok(size) = reader.read(&mut chunk) else {
            break;
        };
        if size == 0 {
            break;
        }
        let remaining = MAX_ONE_SHOT_OUTPUT_BYTES.saturating_sub(bytes.len());
        let retained = remaining.min(size);
        bytes.extend_from_slice(&chunk[..retained]);
        truncated |= retained != size;
    }
    BoundedOutput { bytes, truncated }
}

fn spawn_bounded_output_reader<R: Read + Send + 'static>(
    reader: R,
) -> mpsc::Receiver<BoundedOutput> {
    let (sender, receiver) = mpsc::sync_channel(1);
    thread::spawn(move || {
        let output = read_bounded_output(reader);
        let _ = sender.send(output);
    });
    receiver
}

fn receive_bounded_output(
    receiver: &mpsc::Receiver<BoundedOutput>,
    deadline: Instant,
    label: &str,
) -> Result<BoundedOutput, String> {
    let remaining = deadline.saturating_duration_since(Instant::now());
    receiver
        .recv_timeout(remaining)
        .map_err(|_| format!("offline restore {label} reader did not finish before timeout"))
}

fn restore_receipt_valid(output: &[u8], truncated: bool) -> bool {
    if truncated {
        return false;
    }
    matches!(
        std::str::from_utf8(output),
        Ok("{\"status\":\"restored\"}")
            | Ok("{\"status\":\"restored\"}\n")
            | Ok("{\"status\":\"restored\"}\r\n")
    )
}

pub fn run_restore_backup(runtime: &RuntimeSpec, backup_path: &Path) -> Result<(), String> {
    let core = CoreSpec::beside_runtime(runtime);
    run_selected_restore_backup(runtime, core.as_ref(), backup_path)
}

/// Restore with the already selected canonical Core, without rediscovery or
/// falling back to the Python compatibility entrypoint if that Core disappears.
pub fn run_canonical_restore_backup(
    runtime: &RuntimeSpec,
    core: &CoreSpec,
    backup_path: &Path,
) -> Result<(), String> {
    run_selected_restore_backup(runtime, Some(core), backup_path)
}

fn run_selected_restore_backup(
    runtime: &RuntimeSpec,
    core: Option<&CoreSpec>,
    backup_path: &Path,
) -> Result<(), String> {
    let job = Job::new()?;
    let deadline = Instant::now() + RESTORE_TIMEOUT;
    let mut command = restore_command(runtime, backup_path, core);
    command
        .stdin(Stdio::null())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped());
    let mut child = command
        .spawn()
        .map_err(|error| format!("failed to start offline restore: {error}"))?;
    if let Err(error) = job.assign(&child) {
        let _ = child.kill();
        return Err(error);
    }
    let stdout = child
        .stdout
        .take()
        .ok_or_else(|| "offline restore stdout was unavailable".to_owned())?;
    let stderr = child
        .stderr
        .take()
        .ok_or_else(|| "offline restore stderr was unavailable".to_owned())?;
    let stdout_reader = spawn_bounded_output_reader(stdout);
    let stderr_reader = spawn_bounded_output_reader(stderr);
    let status = wait_for_exit(
        &mut child,
        deadline.saturating_duration_since(Instant::now()),
    );
    // Closing this KILL_ON_JOB_CLOSE handle terminates every assigned descendant.
    // That also closes inherited pipe handles before we attempt bounded collection.
    drop(job);
    let status = status.map_err(|error| format!("offline restore timed out: {error}"))?;
    let stdout = receive_bounded_output(&stdout_reader, deadline, "stdout")?;
    let stderr = receive_bounded_output(&stderr_reader, deadline, "stderr")?;
    if !status.success() {
        return Err(format!(
            "offline restore failed with {status}: {}",
            String::from_utf8_lossy(&stderr.bytes)
        ));
    }
    let receipt_valid = match core {
        Some(core) => core_restore_receipt_valid(
            &stdout.bytes,
            stdout.truncated,
            &core.workspace_db,
            backup_path,
        ),
        None => restore_receipt_valid(&stdout.bytes, stdout.truncated),
    };
    if !receipt_valid {
        return Err(format!(
            "offline restore returned an invalid receipt: {}",
            String::from_utf8_lossy(&stdout.bytes)
        ));
    }
    Ok(())
}

fn restore_command(runtime: &RuntimeSpec, backup_path: &Path, core: Option<&CoreSpec>) -> Command {
    if let Some(core) = core {
        let mut command = Command::new(&core.executable);
        command
            .args(["--maintenance-restore"])
            .arg(&core.workspace_db)
            .arg(backup_path)
            .current_dir(&core.cwd);
        #[cfg(windows)]
        {
            use std::os::windows::process::CommandExt;
            command.creation_flags(0x08000000);
        }
        for name in SANITIZED_ENVIRONMENT {
            command.env_remove(name);
        }
        command
    } else {
        let mut command = runtime_command(runtime);
        command
            .args(["-m", "app.runtime_entrypoint", "restore-backup"])
            .arg(backup_path);
        command
    }
}

fn core_restore_receipt_valid(
    output: &[u8],
    truncated: bool,
    database: &Path,
    backup: &Path,
) -> bool {
    if truncated {
        return false;
    }
    let Ok(value) = serde_json::from_slice::<serde_json::Value>(output) else {
        return false;
    };
    let Some(object) = value.as_object() else {
        return false;
    };
    if object.len() != 8
        || value.get("ok") != Some(&serde_json::json!(true))
        || value.get("verified") != Some(&serde_json::json!(true))
        || value.get("authorization_requires_new_grants") != Some(&serde_json::json!(true))
        || value.get("action").and_then(|v| v.as_str()) != Some("restore")
    {
        return false;
    }
    let same_file = |key: &str, expected: &Path| {
        value
            .get(key)
            .and_then(|v| v.as_str())
            .map(Path::new)
            .and_then(|p| p.canonicalize().ok())
            .zip(expected.canonicalize().ok())
            .is_some_and(|(actual, expected)| actual == expected)
    };
    if !same_file("database", database) || !same_file("backup", backup) {
        return false;
    }
    let Some(preserved) = value
        .get("preserved_previous")
        .and_then(|v| v.as_str())
        .map(Path::new)
        .and_then(|p| p.canonicalize().ok())
    else {
        return false;
    };
    let Ok(database) = database.canonicalize() else {
        return false;
    };
    let expected_prefix = format!(
        "{}.pre-restore-",
        database.file_name().unwrap_or_default().to_string_lossy()
    );
    preserved.parent() == database.parent()
        && preserved.is_file()
        && preserved.file_name().is_some_and(|name| {
            name.to_string_lossy().starts_with(&expected_prefix)
                && name.to_string_lossy().ends_with(".sqlite")
        })
        && value
            .get("preserved_objects_directory")
            .and_then(|v| v.as_str())
            == Some(format!("{}.objects", preserved.display()).as_str())
}

fn runtime_command(runtime: &RuntimeSpec) -> Command {
    let mut command = Command::new(&runtime.python);
    // Hide the console window on Windows so the Python backend
    // runs silently without a visible CMD window.
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        command.creation_flags(0x08000000); // CREATE_NO_WINDOW
    }
    command.arg("-B");
    if runtime.isolated {
        command.arg("-I");
    }
    command.current_dir(&runtime.cwd);
    for name in SANITIZED_ENVIRONMENT {
        command.env_remove(name);
    }
    command
        .env("ARCHEAXIS_DATA_DIR", &runtime.data_dir)
        .env("COGNITIVE_DATA_DIR", &runtime.data_dir)
        .env("ARCHEAXIS_RUNTIME_PROFILE", runtime.profile)
        .env("ARCHEAXIS_LAUNCHER_DATA_DIR", &runtime.data_dir)
        .env("ARCHEAXIS_DB_PATH", "data/archeaxis.sqlite")
        .env(
            "ARCHEAXIS_CAPABILITY_ROOT",
            runtime.data_dir.join("capabilities"),
        )
        .env("HERMES_PROJECT_RUNTIME_ROOT", &runtime.data_dir)
        .env("PYTHONDONTWRITEBYTECODE", "1")
        .env("PYTHONNOUSERSITE", "1")
        .env("NO_PROXY", "127.0.0.1")
        .env("no_proxy", "127.0.0.1");
    if runtime.external_dev {
        command
            .env("ARCHEAXIS_EXTERNAL_DEV_ACTIVE", "1")
            .env("ARCHEAXIS_TEST_WORKSPACE_ROOT", &runtime.data_dir);
    }
    command
}

fn run_migration(runtime: &RuntimeSpec, job: &Job, logs: LogBuffer) -> Result<(), String> {
    let mut command = runtime_command(runtime);
    command
        .args(["-m", "app.runtime_entrypoint", "migrate"])
        .stdin(Stdio::null())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped());
    let mut child = command
        .spawn()
        .map_err(|error| format!("failed to start desktop migration: {error}"))?;
    if let Err(error) = job.assign(&child) {
        let _ = child.kill();
        let _ = child.wait();
        return Err(error);
    }
    drain_child_output(&mut child, Arc::clone(&logs), "migration");
    let status = wait_for_exit(&mut child, MIGRATION_TIMEOUT).map_err(|error| {
        let _ = child.kill();
        let _ = child.wait();
        format!("{error}\n{}", format_logs(&logs))
    })?;
    if !status.success() {
        return Err(format!(
            "desktop migration failed with {status}\n{}",
            format_logs(&logs)
        ));
    }
    Ok(())
}

fn choose_loopback_port() -> Result<u16, String> {
    let listener = TcpListener::bind(("127.0.0.1", 0))
        .map_err(|error| format!("failed to allocate desktop port: {error}"))?;
    listener
        .local_addr()
        .map(|address| address.port())
        .map_err(|error| format!("failed to inspect desktop port: {error}"))
}

fn wait_for_readiness(
    child: &mut Child,
    port: u16,
    token: &str,
    logs: &LogBuffer,
    path: &str,
) -> Result<(), String> {
    let deadline = Instant::now() + READINESS_TIMEOUT;
    loop {
        if let Some(status) = child
            .try_wait()
            .map_err(|error| format!("failed to inspect desktop Core: {error}"))?
        {
            return Err(format!(
                "desktop Core exited before readiness with {status}\n{}",
                format_logs(logs)
            ));
        }
        if probe_readiness(port, token, path).is_ok() {
            return Ok(());
        }
        if Instant::now() >= deadline {
            return Err(format!(
                "desktop Core readiness timed out\n{}",
                format_logs(logs)
            ));
        }
        thread::sleep(READINESS_POLL_INTERVAL);
    }
}

fn probe_readiness(port: u16, token: &str, path: &str) -> Result<(), &'static str> {
    let address = ([127, 0, 0, 1], port).into();
    let Ok(mut stream) = TcpStream::connect_timeout(&address, Duration::from_millis(300)) else {
        return Err("connect");
    };
    let _ = stream.set_read_timeout(Some(Duration::from_secs(3)));
    let request = format!(
        "GET {path} HTTP/1.0\r\nHost: 127.0.0.1:{port}\r\nX-ArcheAxis-Launch-Token: {token}\r\nConnection: close\r\n\r\n"
    );
    if stream.write_all(request.as_bytes()).is_err() {
        return Err("write");
    }
    let mut response = Vec::new();
    let mut buffer = [0_u8; 4096];
    loop {
        match stream.read(&mut buffer) {
            Ok(0) => break,
            Ok(size) => response.extend_from_slice(&buffer[..size]),
            Err(error) if matches!(error.kind(), ErrorKind::TimedOut | ErrorKind::WouldBlock) => {
                break;
            }
            Err(_) if !response.is_empty() => break,
            Err(_) => return Err("read-before-response"),
        }
    }
    let Ok(response) = String::from_utf8(response) else {
        return Err("utf8");
    };
    let Some((headers, body)) = response.split_once("\r\n\r\n") else {
        return Err("headers");
    };
    let payload = response_body(headers, body).or_else(|| json_body(body));
    if !headers
        .lines()
        .next()
        .is_some_and(|line| line == "HTTP/1.1 200 OK" || line == "HTTP/1.0 200 OK")
    {
        return Err("status");
    }
    let Some(payload) = payload else {
        return Err("body");
    };
    // The route answers for whichever backend was launched, and the two report different
    // identities. The Python entrypoint publishes its readiness document; the Core answers
    // its version route with its runtime name and a numeric schema version. Accepting the
    // Core's route with the Python document would never succeed, so a Core that had started
    // perfectly would still time out here.
    let identified = if path == CORE_VERSION_PATH {
        core_version_identity_valid(&payload)
    } else {
        readiness_payload_valid(&payload)
    };
    if !identified {
        return Err("identity");
    }
    Ok(())
}

/// Whether a response from the Core's version route identifies the canonical Core.
///
/// The route is the one the Core itself special-cases, so a payload naming the runtime is
/// the Core answering. The schema version is required to be a number because that is what
/// the Core reports and what the Python document, which carries it as a string, does not.
fn core_version_identity_valid(payload: &str) -> bool {
    let Ok(value) = serde_json::from_str::<serde_json::Value>(payload) else {
        return false;
    };
    value.get("runtime").and_then(serde_json::Value::as_str) == Some("archeaxis-api")
        && value
            .get("schema_version")
            .is_some_and(serde_json::Value::is_number)
}

fn response_body(headers: &str, body: &str) -> Option<String> {
    let chunked = headers.lines().any(|line| {
        line.split_once(':').is_some_and(|(name, value)| {
            name.eq_ignore_ascii_case("transfer-encoding")
                && value.trim().eq_ignore_ascii_case("chunked")
        })
    });
    if !chunked {
        return json_body(body);
    }

    let mut remaining = body;
    let mut decoded = String::new();
    loop {
        let (size_line, after_size) = remaining.split_once("\r\n")?;
        let size = usize::from_str_radix(size_line.split(';').next()?.trim(), 16).ok()?;
        if size == 0 {
            return json_body(&decoded);
        }
        let (chunk, after_chunk) = after_size.split_at_checked(size)?;
        let after_chunk = after_chunk.strip_prefix("\r\n")?;
        decoded.push_str(chunk);
        remaining = after_chunk;
    }
}

fn json_body(body: &str) -> Option<String> {
    let trimmed = body.trim();
    let start = trimmed.find('{')?;
    let end = trimmed.rfind('}')?;
    (start <= end).then(|| trimmed[start..=end].to_owned())
}

fn wait_for_exit(child: &mut Child, timeout: Duration) -> Result<std::process::ExitStatus, String> {
    let deadline = Instant::now() + timeout;
    loop {
        if let Some(status) = child
            .try_wait()
            .map_err(|error| format!("failed to wait for child process: {error}"))?
        {
            return Ok(status);
        }
        if Instant::now() >= deadline {
            return Err("child process did not exit before timeout".to_owned());
        }
        thread::sleep(Duration::from_millis(50));
    }
}

fn new_log_buffer() -> LogBuffer {
    Arc::new(Mutex::new(VecDeque::with_capacity(MAX_LOG_LINES)))
}

fn drain_child_output(child: &mut Child, logs: LogBuffer, label: &'static str) {
    if let Some(stdout) = child.stdout.take() {
        spawn_log_drain(stdout, Arc::clone(&logs), label, "stdout");
    }
    if let Some(stderr) = child.stderr.take() {
        spawn_log_drain(stderr, logs, label, "stderr");
    }
}

fn spawn_log_drain<R: Read + Send + 'static>(
    reader: R,
    logs: LogBuffer,
    label: &'static str,
    stream: &'static str,
) {
    thread::spawn(move || {
        for line in BufReader::new(reader).lines().map_while(Result::ok) {
            let Ok(mut buffer) = logs.lock() else {
                return;
            };
            if buffer.len() == MAX_LOG_LINES {
                buffer.pop_front();
            }
            buffer.push_back(format!("[{label}:{stream}] {line}"));
        }
    });
}

fn format_logs(logs: &LogBuffer) -> String {
    logs.lock()
        .map(|buffer| buffer.iter().cloned().collect::<Vec<_>>().join("\n"))
        .unwrap_or_else(|_| "desktop log buffer unavailable".to_owned())
}

#[cfg(test)]
mod tests {
    use super::{
        readiness_payload_valid, response_body, restore_receipt_valid, run_restore_backup,
        runtime_command, shutdown_job_owned_child,
    };
    use crate::backend::contract_path;
    use crate::backend::core_launch_document;
    use crate::backend::core_version_identity_valid;
    use crate::backend::CoreSpec;
    use crate::backend::CORE_LAUNCH_PROTOCOL;
    use crate::runtime::RuntimeSpec;
    use std::ffi::OsStr;
    use std::fs;
    use std::path::Path as TestPath;
    use std::path::PathBuf;
    use std::process::{Command, Stdio};
    use std::thread;
    use std::time::{Duration, Instant};
    use tempfile::tempdir;

    #[test]
    fn installed_runtime_never_writes_bytecode_into_the_bundle() {
        let runtime = RuntimeSpec {
            python: PathBuf::from("runtime/python/python.exe"),
            cwd: PathBuf::from("writable-data"),
            data_dir: PathBuf::from("writable-data"),
            isolated: true,
            external_dev: false,
            profile: "installed-stable",
        };

        let command = runtime_command(&runtime);
        let setting = command
            .get_envs()
            .find(|(name, _)| *name == OsStr::new("PYTHONDONTWRITEBYTECODE"))
            .and_then(|(_, value)| value);
        let arguments = command.get_args().collect::<Vec<_>>();

        assert_eq!(setting, Some(OsStr::new("1")));
        assert_eq!(arguments, [OsStr::new("-B"), OsStr::new("-I")]);
    }

    #[cfg(windows)]
    #[test]
    fn owner_document_check_config_rejects_owned_parent_junction() {
        let root = tempfile::tempdir().unwrap();
        let data = root.path().join("data");
        let donor = root.path().join("donor");
        std::fs::create_dir_all(&data).unwrap();
        std::fs::create_dir_all(&donor).unwrap();
        let status = std::process::Command::new("cmd")
            .args(["/C", "mklink", "/J"])
            .arg(data.join("config"))
            .arg(&donor)
            .stdout(std::process::Stdio::null())
            .stderr(std::process::Stdio::null())
            .status()
            .unwrap();
        assert!(status.success());
        assert_eq!(
            super::document_check_config(&data),
            (None, Some("invalid_config"))
        );
        std::fs::remove_dir(data.join("config")).unwrap();
    }
    #[test]
    fn owner_document_check_config_is_optional_bounded_and_nonsecret() {
        let root = tempfile::tempdir().unwrap();
        assert_eq!(super::document_check_config(root.path()), (None, None));
        std::fs::create_dir(root.path().join("config")).unwrap();
        let path = root.path().join("config/document-check.json");
        let valid = serde_json::json!({"provider":"fixture","model":"fixture/exact-v1","credential_ref":"aak_cred_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","endpoint":"https://fixture.invalid/v1","max_tokens":128,"timeout_seconds":10,"search_limit":1});
        std::fs::write(&path, serde_json::to_vec(&valid).unwrap()).unwrap();
        assert!(super::document_check_config(root.path()).0.is_some());
        for bad in [
            serde_json::json!({}),
            {
                let mut c = valid.clone();
                c["provider"] = serde_json::json!("fixture-");
                c
            },
            {
                let mut c = valid.clone();
                c["endpoint"] = serde_json::json!("https://fixture.invalid/ bad");
                c
            },
            {
                let mut c = valid.clone();
                c["endpoint"] =
                    serde_json::json!("https://fixture.invalid/".to_owned() + &"a".repeat(2048));
                c
            },
            {
                let mut c = valid.clone();
                c["credential_ref"] = serde_json::json!("synthetic-raw-key");
                c
            },
            {
                let mut c = valid.clone();
                c["credential_ref"] = serde_json::json!(format!("aak_cred_{}界", "a".repeat(29)));
                c
            },
            {
                let mut c = valid.clone();
                c["api_key"] = serde_json::json!("synthetic-forbidden");
                c
            },
            {
                let mut c = valid.clone();
                c["endpoint"] = serde_json::json!("https://user:secret@fixture.invalid/v1");
                c
            },
            {
                let mut c = valid.clone();
                c["model"] = serde_json::json!("default");
                c
            },
        ] {
            std::fs::write(&path, serde_json::to_vec(&bad).unwrap()).unwrap();
            assert_eq!(
                super::document_check_config(root.path()),
                (None, Some("invalid_config"))
            );
        }
        std::fs::write(&path, vec![b' '; 16 * 1024 + 1]).unwrap();
        assert_eq!(
            super::document_check_config(root.path()),
            (None, Some("invalid_config"))
        );
    }
    #[test]
    fn core_launch_document_carries_exactly_the_contract_the_core_enforces() {
        // These are the rules the Core refuses a launch for, so the host must satisfy
        // all of them: sixty-four hex characters for each credential, thirty-two for the
        // session, the exact protocol string, a human actor, and two differing tokens.
        let token = "a".repeat(64);
        let machine = "b".repeat(64);
        let session = machine[..32].to_owned();
        let document = core_launch_document(&token, &machine, &session, None);
        let parsed: serde_json::Value =
            serde_json::from_str(&document).expect("the launch document is valid JSON");
        assert_eq!(parsed["protocol"], CORE_LAUNCH_PROTOCOL);
        assert_eq!(parsed["actor"], "human");
        assert_eq!(parsed["launch_token"].as_str().map(str::len), Some(64));
        assert_eq!(parsed["machine_token"].as_str().map(str::len), Some(64));
        assert_eq!(parsed["session_id"].as_str().map(str::len), Some(32));
        assert_ne!(parsed["launch_token"], parsed["machine_token"]);
        // With no worker declared the document must not contain the field at all: an
        // absent worker is what keeps the Core on its projections-only router.
        assert!(parsed.get("text_worker").is_none());
    }

    #[test]
    fn core_discovery_accepts_both_interpreter_layouts() {
        // The dependency stager writes a flat interpreter and an earlier packaging pass
        // nested it. Discovery that assumes one depth finds nothing for the other layout,
        // and the shell then silently falls back to the legacy entrypoint - the outcome the
        // migration exists to replace, with no error to notice. So both are exercised.
        for interpreter in ["runtime/python/python.exe", "runtime/python.exe"] {
            let root = tempdir().expect("a temporary root");
            let python = root.path().join(interpreter.replace('/', "\\"));
            std::fs::create_dir_all(python.parent().expect("a parent")).expect("python dir");
            std::fs::write(&python, b"").expect("python file");
            let core = root.path().join("core").join("archeaxis-api.exe");
            std::fs::create_dir_all(core.parent().expect("a parent")).expect("core dir");
            std::fs::write(&core, b"").expect("core file");
            let runtime = RuntimeSpec {
                python,
                cwd: root.path().to_path_buf(),
                data_dir: root.path().to_path_buf(),
                isolated: true,
                external_dev: false,
                profile: "installed-stable",
            };
            let spec = CoreSpec::beside_runtime(&runtime)
                .unwrap_or_else(|| panic!("the Core beside a {interpreter} runtime was not found"));
            assert_eq!(spec.executable, core, "{interpreter}");
        }
    }

    fn discovery_runtime(python: PathBuf, data_dir: &TestPath, external_dev: bool) -> RuntimeSpec {
        RuntimeSpec {
            python,
            cwd: data_dir.to_path_buf(),
            data_dir: data_dir.to_path_buf(),
            isolated: !external_dev,
            external_dev,
            profile: if external_dev {
                "external-dev"
            } else {
                "installed-stable"
            },
        }
    }

    fn write_discovery_marker(path: &TestPath) {
        fs::create_dir_all(path.parent().unwrap()).unwrap();
        fs::write(path, b"synthetic marker, never executed").unwrap();
    }

    #[test]
    fn flat_core_discovery_never_uses_a_parent_directory_candidate() {
        let temp = tempdir().unwrap();
        let bundle = temp.path().join("bundle");
        let python = bundle.join("runtime/python.exe");
        let other_core = temp.path().join("core/archeaxis-api.exe");
        let expected_core = bundle.join("core/archeaxis-api.exe");
        write_discovery_marker(&python);
        write_discovery_marker(&other_core);
        let runtime = discovery_runtime(python, &bundle, false);

        assert!(CoreSpec::beside_runtime(&runtime).is_none());
        write_discovery_marker(&expected_core);
        assert_eq!(
            CoreSpec::beside_runtime(&runtime).unwrap().executable,
            expected_core
        );
        fs::remove_file(&expected_core).unwrap();
        assert!(CoreSpec::beside_runtime(&runtime).is_none());
    }

    #[test]
    fn nested_core_discovery_never_uses_a_runtime_subdirectory_candidate() {
        let temp = tempdir().unwrap();
        let bundle = temp.path().join("bundle");
        let python = bundle.join("runtime/python/python.exe");
        let other_core = bundle.join("runtime/core/archeaxis-api.exe");
        let expected_core = bundle.join("core/archeaxis-api.exe");
        write_discovery_marker(&python);
        write_discovery_marker(&other_core);
        let runtime = discovery_runtime(python, &bundle, false);

        assert!(CoreSpec::beside_runtime(&runtime).is_none());
        write_discovery_marker(&expected_core);
        assert_eq!(
            CoreSpec::beside_runtime(&runtime).unwrap().executable,
            expected_core
        );
        fs::remove_file(&expected_core).unwrap();
        assert!(CoreSpec::beside_runtime(&runtime).is_none());
    }

    #[test]
    fn unrelated_development_interpreter_does_not_select_an_ancestor_core() {
        let temp = tempdir().unwrap();
        let root = temp.path();
        let python = root.join(".project-local/build/venv/Scripts/python.exe");
        write_discovery_marker(&python);
        write_discovery_marker(&root.join(".project-local/build/venv/core/archeaxis-api.exe"));
        write_discovery_marker(&root.join(".project-local/build/core/archeaxis-api.exe"));
        let runtime = discovery_runtime(python, root, true);

        assert!(CoreSpec::beside_runtime(&runtime).is_none());
    }

    #[test]
    fn canonical_restore_does_not_rediscover_or_fall_back_after_core_disappears() {
        let temp = tempdir().unwrap();
        let root = temp.path();
        let python = root.join("runtime/python.exe");
        let executable = root.join("core/archeaxis-api.exe");
        let backup = root.join("synthetic-backup.sqlite");
        write_discovery_marker(&python);
        write_discovery_marker(&executable);
        let mut runtime = discovery_runtime(python, root, false);
        let selected = CoreSpec::beside_runtime(&runtime).unwrap();
        fs::remove_file(&executable).unwrap();

        // If this path incorrectly falls back, the test executable is a real
        // program; the missing Core itself cannot be spawned.
        runtime.python = std::env::current_exe().unwrap();
        let command = super::restore_command(&runtime, &backup, Some(&selected));
        assert_eq!(command.get_program(), selected.executable.as_os_str());
        let args = command.get_args().collect::<Vec<_>>();
        assert_eq!(
            args,
            [
                OsStr::new("--maintenance-restore"),
                selected.workspace_db.as_os_str(),
                backup.as_os_str(),
            ]
        );
        let error = super::run_canonical_restore_backup(&runtime, &selected, &backup).unwrap_err();
        assert!(
            error.starts_with("failed to start offline restore:"),
            "{error}"
        );
        assert!(!selected.workspace_db.exists());
    }

    #[test]
    fn a_declared_worker_is_carried_into_the_launch_document() {
        let worker = serde_json::json!({
            "python": "C:/root/runtime/python/python.exe",
            "script": "C:/root/workers/transport/text_ndjson.py",
            "staging": "C:/data/worker-staging",
            "routes": [{"capability": "pdf.extract", "script": "C:/root/workers/document/worker_pdf.py"}],
        });
        let document = core_launch_document(
            &"a".repeat(64),
            &"b".repeat(64),
            &"c".repeat(32),
            Some(&worker),
        );
        let parsed: serde_json::Value = serde_json::from_str(&document).expect("valid JSON");
        assert_eq!(
            parsed["text_worker"]["routes"][0]["capability"],
            "pdf.extract"
        );
    }

    fn synthetic_openmaic_manifest() -> serde_json::Value {
        let mut files = serde_json::Map::new();
        for (name, size, sha) in super::OPENMAIC_FIXED_MEMBERS {
            files.insert(
                name.to_owned(),
                serde_json::json!({"bytes":size,"sha256":sha}),
            );
        }
        files.insert(
            super::OPENMAIC_NODE.to_owned(),
            serde_json::json!({"bytes":17,"sha256":"a".repeat(64)}),
        );
        files.insert(
            super::OPENMAIC_NODE_LICENSE.to_owned(),
            serde_json::json!({"bytes":17,"sha256":"b".repeat(64)}),
        );
        serde_json::json!({"schema":"archeaxis.backend-runtime/v1", "files":files,
            "openmaic_scene_build":{"status":"INCLUDED","node_sha256":"a".repeat(64)}})
    }

    fn write_synthetic_openmaic_members(root: &TestPath) {
        let manifest = synthetic_openmaic_manifest();
        for (name, row) in manifest["files"].as_object().unwrap() {
            let path = root.join(name);
            fs::create_dir_all(path.parent().unwrap()).unwrap();
            // These bytes match the declared lengths, not the declared hashes.
            // Core and release verification, not this host test, check hashes.
            fs::write(path, vec![b'x'; row["bytes"].as_u64().unwrap() as usize]).unwrap();
        }
    }

    fn synthetic_openmaic_runtime() -> (tempfile::TempDir, RuntimeSpec) {
        let root = tempdir().unwrap();
        for relative in [
            "runtime/python.exe",
            "core/archeaxis-api.exe",
            "workers/transport/text_ndjson.py",
        ] {
            let path = root.path().join(relative);
            fs::create_dir_all(path.parent().unwrap()).unwrap();
            fs::write(path, b"synthetic fixture").unwrap();
        }
        write_synthetic_openmaic_members(root.path());
        let manifest = synthetic_openmaic_manifest();
        fs::write(
            root.path().join("backend-runtime-manifest.json"),
            serde_json::to_vec(&manifest).unwrap(),
        )
        .unwrap();
        let runtime = RuntimeSpec {
            python: root.path().join("runtime/python.exe"),
            cwd: root.path().to_path_buf(),
            data_dir: root.path().to_path_buf(),
            isolated: true,
            external_dev: false,
            profile: "installed-stable",
        };
        (root, runtime)
    }

    fn synthetic_openmaic_document(runtime: &RuntimeSpec) -> serde_json::Value {
        let spec = CoreSpec::beside_runtime(runtime).unwrap();
        serde_json::from_str(&super::configured_core_launch_document(
            &"a".repeat(64),
            &"b".repeat(64),
            &"c".repeat(32),
            &spec,
        ))
        .unwrap()
    }

    #[test]
    fn openmaic_launch_uses_fixed_paths_and_preserves_the_text_worker() {
        let (root, runtime) = synthetic_openmaic_runtime();
        let document = synthetic_openmaic_document(&runtime);
        assert!(document.get("text_worker").is_some());
        assert_eq!(document["actor"], "human");
        let provider = &document["openmaic_node_worker"];
        assert_eq!(provider.as_object().unwrap().len(), 3);
        assert_eq!(
            provider["executable"],
            contract_path(&root.path().join("workers/openmaic/node.exe"))
        );
        assert_eq!(
            provider["script"],
            contract_path(&root.path().join("workers/openmaic/scene-build-worker.mjs"))
        );
        assert_eq!(provider["executable_sha256"], "a".repeat(64));
    }

    #[test]
    fn openmaic_manifest_is_optional_bounded_and_cannot_select_paths() {
        let (root, runtime) = synthetic_openmaic_runtime();
        let path = root.path().join("backend-runtime-manifest.json");
        let sha = "a".repeat(64);
        let files = serde_json::to_string(&synthetic_openmaic_manifest()["files"]).unwrap();
        let invalid = [
            "{}".to_string(),
            format!(
                r#"{{"schema":"other","files":{files},"openmaic_scene_build":{{"status":"INCLUDED","node_sha256":"{sha}"}}}}"#
            ),
            format!(
                r#"{{"schema":"archeaxis.backend-runtime/v1","files":{files},"openmaic_scene_build":{{"status":"NOT_INCLUDED","node_sha256":null}}}}"#
            ),
            format!(
                r#"{{"schema":"archeaxis.backend-runtime/v1","files":{files},"openmaic_scene_build":{{"status":"INCLUDED","node_sha256":null}}}}"#
            ),
            format!(
                r#"{{"schema":"archeaxis.backend-runtime/v1","files":{files},"openmaic_scene_build":{{"status":"INCLUDED","node_sha256":"{}"}}}}"#,
                "A".repeat(64)
            ),
            format!(
                r#"{{"schema":"archeaxis.backend-runtime/v1","files":{files},"openmaic_scene_build":{{"status":"INCLUDED","node_sha256":"{sha}","script":"C:/untrusted.mjs"}}}}"#
            ),
            format!(
                r#"{{"schema":"archeaxis.backend-runtime/v1","files":{files},"openmaic_scene_build":{{"status":"INCLUDED","node_sha256":"{sha}","\u006eode_sha256":"{sha}"}}}}"#
            ),
            format!(
                r#"{{"schema":"archeaxis.backend-runtime/v1","files":{files},"openmaic_scene_build":{{"status":"INCLUDED","node_sha256":"{sha}"}},"openmaic_scene_build":{{"status":"INCLUDED","node_sha256":"{sha}"}}}}"#
            ),
            "{invalid JSON".to_string(),
        ];
        for manifest in invalid {
            fs::write(&path, manifest).unwrap();
            let document = synthetic_openmaic_document(&runtime);
            assert!(document.get("openmaic_node_worker").is_none());
            assert!(document.get("text_worker").is_some());
        }
        fs::write(&path, vec![b' '; 129]).unwrap();
        assert!(super::read_backend_manifest(&path, 128).is_none());
        fs::remove_file(&path).unwrap();
        assert!(synthetic_openmaic_document(&runtime)
            .get("openmaic_node_worker")
            .is_none());

        let valid = synthetic_openmaic_manifest();
        fs::write(&path, serde_json::to_vec(&valid).unwrap()).unwrap();
        for relative in [
            "workers/openmaic/node.exe",
            "workers/openmaic/scene-build-worker.mjs",
        ] {
            let file = root.path().join(relative);
            let length = fs::metadata(&file).unwrap().len();
            fs::remove_file(&file).unwrap();
            assert!(synthetic_openmaic_document(&runtime)
                .get("openmaic_node_worker")
                .is_none());
            fs::write(file, vec![b'x'; length as usize]).unwrap();
        }
        fs::remove_file(root.path().join("workers/transport/text_ndjson.py")).unwrap();
        let without_text_worker = synthetic_openmaic_document(&runtime);
        assert!(without_text_worker.get("text_worker").is_none());
        assert!(without_text_worker.get("openmaic_node_worker").is_none());
    }

    #[test]
    fn openmaic_requires_all_fixed_members_and_matching_declared_sizes() {
        let (root, runtime) = synthetic_openmaic_runtime();
        let path = root.path().join("backend-runtime-manifest.json");
        let valid = synthetic_openmaic_manifest();
        let check_disabled = |manifest: &serde_json::Value| {
            fs::write(&path, serde_json::to_vec(manifest).unwrap()).unwrap();
            let document = synthetic_openmaic_document(&runtime);
            assert!(document.get("openmaic_node_worker").is_none());
            assert!(document.get("text_worker").is_some());
        };
        let mut missing_files = valid.clone();
        missing_files.as_object_mut().unwrap().remove("files");
        check_disabled(&missing_files);
        for name in valid["files"].as_object().unwrap().keys() {
            let mut missing_member = valid.clone();
            missing_member["files"]
                .as_object_mut()
                .unwrap()
                .remove(name);
            check_disabled(&missing_member);
        }
        let mut wrong_size = valid.clone();
        wrong_size["files"][super::OPENMAIC_SCRIPT]["bytes"] = serde_json::json!(7316);
        check_disabled(&wrong_size);
        let mut wrong_fixed_sha = valid.clone();
        wrong_fixed_sha["files"][super::OPENMAIC_SCRIPT]["sha256"] =
            serde_json::json!("f".repeat(64));
        check_disabled(&wrong_fixed_sha);
        let mut wrong_node_sha = valid.clone();
        wrong_node_sha["files"][super::OPENMAIC_NODE]["sha256"] = serde_json::json!("c".repeat(64));
        check_disabled(&wrong_node_sha);
        let mut bad_node_size = valid.clone();
        bad_node_size["files"][super::OPENMAIC_NODE]["bytes"] =
            serde_json::json!(512_u64 * 1024 * 1024 + 1);
        check_disabled(&bad_node_size);
        let mut bad_license_size = valid.clone();
        bad_license_size["files"][super::OPENMAIC_NODE_LICENSE]["bytes"] =
            serde_json::json!(1_000_001);
        check_disabled(&bad_license_size);
        let mut bad_license_sha = valid.clone();
        bad_license_sha["files"][super::OPENMAIC_NODE_LICENSE]["sha256"] =
            serde_json::json!("z".repeat(64));
        check_disabled(&bad_license_sha);
        let mut extra_field = valid.clone();
        extra_field["files"][super::OPENMAIC_SCRIPT]["path"] =
            serde_json::json!("ignored-is-unsafe");
        check_disabled(&extra_field);

        fs::write(&path, serde_json::to_vec(&valid).unwrap()).unwrap();
        let license = root.path().join(super::OPENMAIC_NODE_LICENSE);
        fs::remove_file(&license).unwrap();
        assert!(synthetic_openmaic_document(&runtime)
            .get("openmaic_node_worker")
            .is_none());
        fs::write(&license, vec![b'x'; 17]).unwrap();
        let script = root.path().join(super::OPENMAIC_SCRIPT);
        fs::write(&script, b"same path, wrong actual length").unwrap();
        assert!(synthetic_openmaic_document(&runtime)
            .get("openmaic_node_worker")
            .is_none());
    }

    #[test]
    fn openmaic_rejects_duplicate_fixed_members_and_member_fields() {
        let (root, runtime) = synthetic_openmaic_runtime();
        let path = root.path().join("backend-runtime-manifest.json");
        let valid = synthetic_openmaic_manifest();
        let selected = serde_json::to_string(&valid["openmaic_scene_build"]).unwrap();
        let fixed_name = serde_json::to_string(super::OPENMAIC_SCRIPT).unwrap();
        let row = serde_json::to_string(&valid["files"][super::OPENMAIC_SCRIPT]).unwrap();
        let mut duplicate_member = serde_json::to_string(&valid["files"]).unwrap();
        duplicate_member.pop();
        duplicate_member.push_str(&format!(",{fixed_name}:{row}"));
        duplicate_member.push('}');

        let mut remaining = valid["files"].as_object().unwrap().clone();
        remaining.remove(super::OPENMAIC_SCRIPT);
        let mut duplicate_field = serde_json::to_string(&remaining).unwrap();
        duplicate_field.pop();
        let mut duplicate_row = row;
        duplicate_row.pop();
        duplicate_row.push_str(",\"bytes\":7315}");
        duplicate_field.push_str(&format!(",{fixed_name}:{duplicate_row}"));
        duplicate_field.push('}');

        for files in [duplicate_member, duplicate_field] {
            let manifest = format!(
                r#"{{"schema":"archeaxis.backend-runtime/v1","files":{files},"openmaic_scene_build":{selected}}}"#
            );
            fs::write(&path, manifest).unwrap();
            let document = synthetic_openmaic_document(&runtime);
            assert!(document.get("openmaic_node_worker").is_none());
            assert!(document.get("text_worker").is_some());
        }
    }

    #[test]
    fn openmaic_launch_rejects_hard_linked_manifest_and_all_members() {
        for relative in [
            "backend-runtime-manifest.json",
            "workers/openmaic/node.exe",
            "workers/openmaic/NODE-LICENSE",
            "workers/openmaic/scene-build-worker.mjs",
            "workers/openmaic/vendor/generation-0.3.28/scene-builder.ts",
            "workers/openmaic/vendor/generation-0.3.28/nanoid.mjs",
            "workers/openmaic/vendor/generation-0.3.28/LICENSE",
            "workers/openmaic/vendor/generation-0.3.28/UPSTREAM.md",
        ] {
            let (root, runtime) = synthetic_openmaic_runtime();
            assert!(synthetic_openmaic_document(&runtime)
                .get("openmaic_node_worker")
                .is_some());
            let input = root.path().join(relative);
            let alias = root.path().join("synthetic-hard-link");
            fs::hard_link(&input, &alias).unwrap();
            assert!(
                super::open_single_link_runtime_file(&input).is_none(),
                "{relative}"
            );
            if relative == "backend-runtime-manifest.json" {
                assert!(
                    super::read_backend_manifest(&input, super::MAX_BACKEND_MANIFEST_BYTES)
                        .is_none()
                );
            }
            let document = synthetic_openmaic_document(&runtime);
            assert!(document.get("openmaic_node_worker").is_none(), "{relative}");
            assert!(document.get("text_worker").is_some());
            fs::remove_file(alias).unwrap();
            assert!(synthetic_openmaic_document(&runtime)
                .get("openmaic_node_worker")
                .is_some());
        }
    }

    #[test]
    fn openmaic_handle_id_distinguishes_identical_file_contents() {
        let (root, _runtime) = synthetic_openmaic_runtime();
        let first = root.path().join("workers/openmaic/node.exe");
        let second = root.path().join("workers/openmaic/NODE-LICENSE");
        let (file, identity) = super::open_single_link_runtime_file(&first).unwrap();
        assert!(super::runtime_file_is_current(&first, &file, identity));
        assert!(!super::runtime_file_is_current(&second, &file, identity));
    }

    #[cfg(windows)]
    #[test]
    fn openmaic_launch_rejects_nonlocal_or_escaping_paths() {
        for path in [
            r"E:\bundle\worker",
            r"F:\bundle\worker",
            r"\\server\share\worker",
            r"\\?\UNC\server\share\worker",
            r"C:\bundle\..\worker",
            r"C:relative\worker",
        ] {
            assert!(
                !super::local_runtime_path_shape(TestPath::new(path)),
                "{path}"
            );
        }
        assert!(super::local_runtime_path_shape(TestPath::new(
            r"C:\bundle\worker"
        )));
        assert!(super::local_runtime_path_shape(TestPath::new(
            r"\\?\C:\bundle\worker"
        )));
    }

    #[cfg(windows)]
    #[test]
    fn openmaic_launch_rejects_a_provider_directory_junction() {
        let fixture = tempdir().unwrap();
        let root = fixture.path().join("bundle");
        let provider = root.join("workers/openmaic");
        let donor_root = fixture.path().join("donor");
        let donor = donor_root.join("workers/openmaic");
        fs::create_dir_all(provider.parent().unwrap()).unwrap();
        write_synthetic_openmaic_members(&donor_root);
        fs::write(
            root.join("backend-runtime-manifest.json"),
            serde_json::to_vec(&synthetic_openmaic_manifest()).unwrap(),
        )
        .unwrap();
        let status = Command::new("cmd")
            .args(["/C", "mklink", "/J"])
            .arg(&provider)
            .arg(&donor)
            .stdout(Stdio::null())
            .stderr(Stdio::null())
            .status()
            .unwrap();
        assert!(status.success());
        assert!(super::openmaic_node_worker_for(&root).is_none());
        fs::remove_dir(provider).unwrap();
    }

    #[test]
    fn the_launch_contract_never_carries_a_verbatim_path_prefix() {
        // A canonicalised Windows path starts with the extended-length prefix, and the Core
        // refuses it in the worker profile. Every published path is stripped.
        assert_eq!(
            contract_path(TestPath::new(r"\\?\C:\bundle\runtime\python.exe")),
            r"C:\bundle\runtime\python.exe",
        );
        assert_eq!(
            contract_path(TestPath::new(r"C:\bundle\runtime\python.exe")),
            r"C:\bundle\runtime\python.exe",
        );
    }

    #[test]
    fn the_two_backends_are_identified_by_their_own_documents() {
        // A Core that answered perfectly must not be judged against the Python document,
        // and the Python document must not be mistaken for a Core.
        let core = r#"{"runtime":"archeaxis-api","contract":"0.1.0-outline","schema_version":6,"session_id":"c","workspace_db":"d"}"#;
        assert!(core_version_identity_valid(core));
        let python = r#"{"schema_version":"v1","product":"ArcheAxis Knowledge","workspace":"x"}"#;
        // The Python document is not required to pass its own validator here - that is pinned
        // by its own test - only that it is never mistaken for a Core.
        assert!(!core_version_identity_valid(python));
    }

    #[test]
    fn readiness_decodes_chunked_http_json_before_validation() {
        let headers = "HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked";
        let body = "63\r\n{\"schema_version\":\"v1\",\"product\":\"ArcheAxis Knowledge\",\"workspace\":\"Human–AI Learning Workspace\"}\r\n0\r\n\r\n";

        let decoded = response_body(headers, body).expect("chunked body");
        assert!(readiness_payload_valid(&decoded));
    }

    #[test]
    fn runtime_command_sets_canonical_and_legacy_data_dir() {
        let runtime = RuntimeSpec {
            python: PathBuf::from("runtime/python/python.exe"),
            cwd: PathBuf::from("writable-data"),
            data_dir: PathBuf::from("writable-data"),
            isolated: true,
            external_dev: false,
            profile: "installed-stable",
        };

        let command = runtime_command(&runtime);
        let envs = command.get_envs().collect::<Vec<_>>();
        let canonical = envs
            .iter()
            .find(|(name, _)| *name == OsStr::new("ARCHEAXIS_DATA_DIR"))
            .and_then(|(_, value)| *value);
        let legacy = envs
            .iter()
            .find(|(name, _)| *name == OsStr::new("COGNITIVE_DATA_DIR"))
            .and_then(|(_, value)| *value);
        assert_eq!(canonical, Some(OsStr::new("writable-data")));
        assert_eq!(legacy, Some(OsStr::new("writable-data")));
    }

    #[test]
    fn runtime_command_owns_external_dev_activation() {
        let installed = RuntimeSpec {
            python: PathBuf::from("runtime/python/python.exe"),
            cwd: PathBuf::from("writable-data"),
            data_dir: PathBuf::from("writable-data"),
            isolated: true,
            external_dev: false,
            profile: "installed-stable",
        };
        let development = RuntimeSpec {
            external_dev: true,
            isolated: false,
            profile: "external-dev",
            ..installed.clone()
        };

        let installed_command = runtime_command(&installed);
        let installed_envs = installed_command.get_envs().collect::<Vec<_>>();
        let development_command = runtime_command(&development);
        let development_envs = development_command.get_envs().collect::<Vec<_>>();
        let installed_external_request = installed_envs
            .iter()
            .find(|(key, _)| *key == OsStr::new("ARCHEAXIS_EXTERNAL_DEV"))
            .map(|(_, value)| *value);
        let installed_external_active = installed_envs
            .iter()
            .find(|(key, _)| *key == OsStr::new("ARCHEAXIS_EXTERNAL_DEV_ACTIVE"))
            .map(|(_, value)| *value);
        let development_external_request = development_envs
            .iter()
            .find(|(key, _)| *key == OsStr::new("ARCHEAXIS_EXTERNAL_DEV"))
            .map(|(_, value)| *value);
        let development_external_active = development_envs
            .iter()
            .find(|(key, _)| *key == OsStr::new("ARCHEAXIS_EXTERNAL_DEV_ACTIVE"))
            .map(|(_, value)| *value);
        let installed_profile = installed_envs
            .iter()
            .find(|(key, _)| *key == OsStr::new("ARCHEAXIS_RUNTIME_PROFILE"))
            .map(|(_, value)| *value);
        let development_profile = development_envs
            .iter()
            .find(|(key, _)| *key == OsStr::new("ARCHEAXIS_RUNTIME_PROFILE"))
            .map(|(_, value)| *value);
        let installed_test_root = installed_envs
            .iter()
            .find(|(key, _)| *key == OsStr::new("ARCHEAXIS_TEST_WORKSPACE_ROOT"))
            .map(|(_, value)| *value);
        let development_test_root = development_envs
            .iter()
            .find(|(key, _)| *key == OsStr::new("ARCHEAXIS_TEST_WORKSPACE_ROOT"))
            .map(|(_, value)| *value);
        let installed_launcher_root = installed_envs
            .iter()
            .find(|(key, _)| *key == OsStr::new("ARCHEAXIS_LAUNCHER_DATA_DIR"))
            .map(|(_, value)| *value);
        let development_launcher_root = development_envs
            .iter()
            .find(|(key, _)| *key == OsStr::new("ARCHEAXIS_LAUNCHER_DATA_DIR"))
            .map(|(_, value)| *value);
        let installed_database_path = installed_envs
            .iter()
            .find(|(key, _)| *key == OsStr::new("ARCHEAXIS_DB_PATH"))
            .map(|(_, value)| *value);
        let installed_legacy_database_path = installed_envs
            .iter()
            .find(|(key, _)| *key == OsStr::new("COGNITIVE_DB_PATH"))
            .map(|(_, value)| *value);
        let installed_capability_root = installed_envs
            .iter()
            .find(|(key, _)| *key == OsStr::new("ARCHEAXIS_CAPABILITY_ROOT"))
            .map(|(_, value)| *value);
        let installed_hermes_runtime_root = installed_envs
            .iter()
            .find(|(key, _)| *key == OsStr::new("HERMES_PROJECT_RUNTIME_ROOT"))
            .map(|(_, value)| *value);

        assert_eq!(installed_external_request, Some(None));
        assert_eq!(installed_external_active, Some(None));
        assert_eq!(development_external_request, Some(None));
        assert_eq!(development_external_active, Some(Some(OsStr::new("1"))));
        assert_eq!(
            installed_profile,
            Some(Some(OsStr::new("installed-stable")))
        );
        assert_eq!(development_profile, Some(Some(OsStr::new("external-dev"))));
        assert_eq!(installed_test_root, Some(None));
        assert_eq!(
            development_test_root,
            Some(Some(OsStr::new("writable-data")))
        );
        assert_eq!(
            installed_launcher_root,
            Some(Some(OsStr::new("writable-data")))
        );
        assert_eq!(
            development_launcher_root,
            Some(Some(OsStr::new("writable-data")))
        );
        assert_eq!(
            installed_database_path,
            Some(Some(OsStr::new("data/archeaxis.sqlite")))
        );
        assert_eq!(installed_legacy_database_path, Some(None));
        let expected_capability_root = PathBuf::from("writable-data").join("capabilities");
        assert_eq!(
            installed_capability_root,
            Some(Some(expected_capability_root.as_os_str()))
        );
        assert_eq!(
            installed_hermes_runtime_root,
            Some(Some(OsStr::new("writable-data")))
        );
    }

    #[test]
    fn restore_receipt_rejects_paths_extra_output_and_truncation() {
        assert!(restore_receipt_valid(b"{\"status\":\"restored\"}\n", false));
        for invalid in [
            b"{\"status\":\"restored\",\"path\":\"private.sqlite\"}".as_slice(),
            b"C:\\private\\backup.sqlite\n{\"status\":\"restored\"}".as_slice(),
            b"{\"status\":\"restored\"}\nextra".as_slice(),
            b"{\"status\":\"failed\"}".as_slice(),
            b"\xff\xfe".as_slice(),
        ] {
            assert!(!restore_receipt_valid(invalid, false));
        }
        assert!(!restore_receipt_valid(b"{\"status\":\"restored\"}", true));
    }

    #[test]
    fn core_restore_selects_canonical_binary_database_and_strict_receipt() {
        let temp = tempdir().expect("temporary directory");
        let root = temp.path();
        fs::create_dir_all(root.join("runtime")).unwrap();
        fs::create_dir_all(root.join("core")).unwrap();
        fs::create_dir_all(root.join("data")).unwrap();
        fs::write(
            root.join("core/archeaxis-api.exe"),
            b"command identity fixture",
        )
        .unwrap();
        let runtime = RuntimeSpec {
            python: root.join("runtime/python.exe"),
            cwd: root.to_path_buf(),
            data_dir: root.join("data"),
            isolated: true,
            external_dev: false,
            profile: "portable",
        };
        let core = CoreSpec::beside_runtime(&runtime).expect("canonical Core selected");
        let backup = root.join("snapshot.sqlite");
        let command = super::restore_command(&runtime, &backup, Some(&core));
        assert_eq!(command.get_program(), core.executable.as_os_str());
        assert_eq!(
            command.get_args().collect::<Vec<_>>(),
            vec![
                std::ffi::OsStr::new("--maintenance-restore"),
                core.workspace_db.as_os_str(),
                backup.as_os_str()
            ]
        );
        let preserved = runtime
            .data_dir
            .join("archeaxis.sqlite.pre-restore-123.sqlite");
        for path in [&backup, &core.workspace_db, &preserved] {
            fs::write(path, b"fixture").unwrap();
        }
        let preserved = preserved.canonicalize().unwrap();
        let good = serde_json::json!({"ok":true,"verified":true,"authorization_requires_new_grants":true,"action":"restore",
            "database":core.workspace_db.canonicalize().unwrap(),"backup":backup.canonicalize().unwrap(),
            "preserved_previous":preserved,"preserved_objects_directory":format!("{}.objects",preserved.display())});
        let bytes = serde_json::to_vec(&good).unwrap();
        let mut legacy = good.clone();
        legacy
            .as_object_mut()
            .unwrap()
            .remove("authorization_requires_new_grants");
        assert!(!super::core_restore_receipt_valid(
            &serde_json::to_vec(&legacy).unwrap(),
            false,
            &core.workspace_db,
            &backup
        ));
        legacy["authorization_requires_new_grants"] = serde_json::json!(false);
        assert!(!super::core_restore_receipt_valid(
            &serde_json::to_vec(&legacy).unwrap(),
            false,
            &core.workspace_db,
            &backup
        ));
        assert!(super::core_restore_receipt_valid(
            &bytes,
            false,
            &core.workspace_db,
            &backup
        ));
        assert!(!super::core_restore_receipt_valid(
            &bytes,
            true,
            &core.workspace_db,
            &backup
        ));
        for (key, invalid) in [
            ("ok", serde_json::json!(false)),
            ("verified", serde_json::json!(false)),
            ("action", serde_json::json!("backup")),
            ("database", serde_json::json!(backup)),
            ("extra", serde_json::json!(true)),
        ] {
            let mut value = good.clone();
            value[key] = invalid;
            assert!(!super::core_restore_receipt_valid(
                &serde_json::to_vec(&value).unwrap(),
                false,
                &core.workspace_db,
                &backup
            ));
        }
        assert!(!super::core_restore_receipt_valid(
            b"{\"status\":\"restored\"}",
            false,
            &core.workspace_db,
            &backup
        ));
        let mut noisy = bytes;
        noisy.extend_from_slice(b"\nextra");
        assert!(!super::core_restore_receipt_valid(
            &noisy,
            false,
            &core.workspace_db,
            &backup
        ));
    }

    #[test]
    fn restore_does_not_wait_for_a_descendant_holding_inherited_pipes() {
        let temp = tempdir().expect("temporary directory");
        let fake_python = temp.path().join("fake-python.cmd");
        fs::write(
            &fake_python,
            concat!(
                "@echo off\r\n",
                "start \"\" /b powershell.exe -NoProfile -NonInteractive ",
                "-Command \"Start-Sleep -Seconds 5\"\r\n",
                "echo {\"status\":\"restored\"}\r\n",
                "exit /b 0\r\n"
            ),
        )
        .expect("write fake runtime");
        let runtime = RuntimeSpec {
            python: fake_python,
            cwd: temp.path().to_path_buf(),
            data_dir: temp.path().join("data"),
            isolated: false,
            external_dev: true,
            profile: "external-dev",
        };
        fs::create_dir(&runtime.data_dir).expect("create runtime data");
        let started = Instant::now();

        let result = run_restore_backup(&runtime, &temp.path().join("staged.sqlite"));

        assert!(result.is_ok(), "fake restore failed: {result:?}");
        assert!(
            started.elapsed() < Duration::from_secs(2),
            "restore waited for a pipe-holding descendant: {:?}",
            started.elapsed()
        );
    }

    #[test]
    fn core_shutdown_drops_the_job_and_bounds_forced_exit_polling() {
        let temp = tempdir().expect("temporary directory");
        let stubborn_core = temp.path().join("stubborn-core.cmd");
        // Development environments need not include Windows system tools on PATH.
        let system_root =
            PathBuf::from(std::env::var_os("SystemRoot").expect("Windows system root"));
        let ping = system_root.join("System32/ping.exe");
        let powershell = system_root.join("System32/WindowsPowerShell/v1.0/powershell.exe");
        assert!(ping.is_file(), "fixture ping executable is missing");
        assert!(
            powershell.is_file(),
            "fixture PowerShell executable is missing"
        );
        fs::write(
            &stubborn_core,
            format!(
                concat!(
                    "@echo off\r\n",
                    "\"{}\" -n 2 127.0.0.1 >nul\r\n",
                    "start \"\" /b \"{}\" -NoProfile -NonInteractive ",
                    "-Command \"Start-Sleep -Seconds 5\"\r\n",
                    "\"{}\" -NoProfile -NonInteractive ",
                    "-Command \"Start-Sleep -Seconds 5\"\r\n"
                ),
                ping.display(),
                powershell.display(),
                powershell.display(),
            ),
        )
        .expect("write stubborn Core fixture");
        let mut child = Command::new(&stubborn_core)
            .stdin(Stdio::null())
            .stdout(Stdio::null())
            .stderr(Stdio::piped())
            .spawn()
            .expect("spawn stubborn Core fixture");
        let mut job = Some(crate::job::Job::new().expect("create Core test job"));
        job.as_ref()
            .expect("Core test job")
            .assign(&child)
            .expect("assign stubborn Core to Job");
        thread::sleep(Duration::from_millis(1200));
        if let Some(status) = child.try_wait().expect("inspect fixture before shutdown") {
            let mut errors = Vec::new();
            std::io::Read::read_to_end(
                &mut child.stderr.take().expect("fixture stderr"),
                &mut errors,
            )
            .expect("read fixture diagnostics");
            panic!("stubborn fixture exited early: {status}: {errors:?}");
        }
        let started = Instant::now();

        let (observed, forced) = shutdown_job_owned_child(
            &mut child,
            &mut job,
            Duration::from_millis(100),
            Duration::from_secs(1),
        );

        assert!(forced, "forced fallback must be reported separately");
        assert!(observed.is_some(), "forced exit must actually be reaped");
        assert!(job.is_none(), "forced shutdown retained the Job handle");
        assert!(
            started.elapsed() < Duration::from_secs(2),
            "forced shutdown exceeded its bounded polling window: {:?}",
            started.elapsed()
        );
        assert!(
            child.try_wait().expect("inspect stubborn Core").is_some(),
            "Job close did not terminate the stubborn Core"
        );
    }

    #[test]
    fn shutdown_ack_requires_complete_response_and_exact_session() {
        let body = serde_json::json!({"schema":"archeaxis.session-shutdown/v1","session_id":"session","state":"draining"}).to_string();
        let response = format!(
            "HTTP/1.1 202 Accepted\r\nContent-Length: {}\r\n\r\n{body}",
            body.len()
        );
        assert!(super::shutdown_ack_valid(response.as_bytes(), "session"));
        assert!(!super::shutdown_ack_valid(response.as_bytes(), "other"));
        assert!(!super::shutdown_ack_valid(
            &response.as_bytes()[..response.len() - 1],
            "session"
        ));
        assert!(!super::shutdown_ack_valid(
            response.replace("202 Accepted", "200 OK").as_bytes(),
            "session"
        ));
        assert!(!super::shutdown_ack_valid(
            response.replace("draining", "graceful").as_bytes(),
            "session"
        ));
    }

    #[test]
    #[ignore = "requires an explicitly built Core path; no installed runtime is inferred"]
    fn canonical_owned_core_shutdown_is_acknowledged_exit_zero_without_forcing() {
        let executable = PathBuf::from(
            std::env::var_os("ARCHEAXIS_TEST_CORE_EXE").expect("explicit built Core"),
        );
        assert!(executable.is_file());
        let dir = tempdir().unwrap();
        let spec = super::CoreSpec {
            executable,
            workspace_db: dir.path().join("workspace.sqlite"),
            cwd: dir.path().to_owned(),
            data_dir: dir.path().to_owned(),
            text_worker: None,
        };
        for _ in 0..2 {
            let mut core = super::BackendProcess::launch_core(&spec).unwrap();
            let report = core.shutdown();
            assert_eq!(report.outcome, "GRACEFUL", "{report:?}");
            assert!(report.request_acknowledged && report.wait_reaped);
            assert!(!report.forced_attempted);
            assert_eq!(report.return_code, Some(0));
            let persisted: serde_json::Value = serde_json::from_slice(
                &fs::read(dir.path().join("core-shutdown-result.json")).unwrap(),
            )
            .unwrap();
            assert_eq!(persisted["pid"], report.pid);
            assert_eq!(persisted["outcome"], "GRACEFUL");
        }
    }

    #[test]
    fn later_core_exit_is_reported_without_exposing_backend_info() {
        let job = crate::job::Job::new().expect("create test job");
        let child = Command::new("cmd.exe")
            .args(["/d", "/c", "exit 7"])
            .stdin(Stdio::null())
            .stdout(Stdio::null())
            .stderr(Stdio::null())
            .spawn()
            .expect("spawn short-lived child");
        job.assign(&child).expect("assign child to test job");
        let mut backend = super::BackendProcess {
            port: 4312,
            token: "test-only".to_owned(),
            child,
            job: Some(job),
            logs: super::new_log_buffer(),
            canonical_session: None,
            shutdown_report: None,
            shutdown_report_path: None,
        };
        let deadline = Instant::now() + Duration::from_secs(2);

        let diagnostic = loop {
            if let Some(diagnostic) = backend.exit_diagnostic().expect("poll child exit") {
                break diagnostic;
            }
            assert!(Instant::now() < deadline, "child exit was not detected");
            thread::sleep(Duration::from_millis(20));
        };

        assert!(diagnostic.contains("exited"));
    }
}
