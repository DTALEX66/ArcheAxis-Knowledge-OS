//! Single owned desktop session. Credentials arrive on inherited stdin only.
//! This is not a multi-user role service or protection against same-user memory access.
use archeaxis_store_sqlite::writer::{Store, StoreError};
use axum::{
    Json, Router,
    extract::{Request, State},
    http::{Method, StatusCode},
    middleware::{self, Next},
    response::{IntoResponse, Response},
};
use serde::Deserialize;
use std::{io::Read, sync::mpsc, time::Duration};

#[derive(Clone, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Launch {
    launch_token: String,
    session_id: String,
    #[serde(default, deserialize_with = "present_string")]
    pub actor: Option<String>,
    pub text_worker: Option<TextWorker>,
    pub document_check_config: Option<archeaxis_application::executor::DocumentCheckConfig>,
    pub document_check_config_error: Option<String>,
    #[serde(default, deserialize_with = "present_string")]
    protocol: Option<String>,
    #[serde(default, deserialize_with = "present_string")]
    machine_token: Option<String>,
}
fn present_string<'de, D: serde::Deserializer<'de>>(value: D) -> Result<Option<String>, D::Error> {
    String::deserialize(value).map(Some)
}
#[derive(Clone, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct TextWorker {
    pub python: std::path::PathBuf,
    pub script: std::path::PathBuf,
    pub staging: std::path::PathBuf,
    /// Additional capability routes, declared by whoever built the launch.
    ///
    /// The default `script` serves `text.extract`. Each entry here registers one
    /// more capability against the worker that implements it, so a PDF or OCR job
    /// reaches its own engine. The list is declared rather than guessed: the Core
    /// does not assume a checkout layout, and an absent list keeps the previous
    /// single-route behaviour exactly.
    #[serde(default)]
    pub routes: Vec<WorkerRoute>,
    /// One directory the other paths may be written relative to.
    ///
    /// A launch that names every worker absolutely pays for the install prefix on every route: a
    /// thirteen-route profile measured 2741 bytes from a short root and 4405 from a deep one. One
    /// declared root plus relative paths keeps the document small however deep the install sits.
    /// Absolute paths are unchanged, and a relative path with no root is refused rather than guessed.
    #[serde(default)]
    pub root: Option<std::path::PathBuf>,
}

/// One declared capability route: which script serves which capability.
#[derive(Clone, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct WorkerRoute {
    pub capability: String,
    pub script: std::path::PathBuf,
}

impl TextWorker {
    /// The additional `(capability, script)` routes this launch declares.
    pub fn extra_routes(&self) -> Vec<(String, std::path::PathBuf)> {
        self.routes
            .iter()
            .map(|route| (route.capability.clone(), route.script.clone()))
            .collect()
    }

    fn absolutize(root: &std::path::Path, path: &mut std::path::PathBuf) {
        if !path.is_absolute() {
            let resolved = root.join(path.as_path());
            *path = resolved;
        }
    }

    /// Resolves every relative worker path against the declared root, in place.
    pub fn resolve_root(&mut self) -> Result<(), &'static str> {
        let Some(root) = self.root.clone() else {
            let absolute = [&self.python, &self.script, &self.staging]
                .iter()
                .all(|path| path.is_absolute())
                && self.routes.iter().all(|route| route.script.is_absolute());
            return if absolute {
                Ok(())
            } else {
                Err("worker path is relative and the launch declares no root")
            };
        };
        Self::validate_path(&root)?;
        Self::absolutize(&root, &mut self.python);
        Self::absolutize(&root, &mut self.script);
        Self::absolutize(&root, &mut self.staging);
        for route in &mut self.routes {
            Self::absolutize(&root, &mut route.script);
        }
        Ok(())
    }

    fn validate_path(path: &std::path::Path) -> Result<(), &'static str> {
        let text = path
            .to_string_lossy()
            .replace('\\', "/")
            .to_ascii_lowercase();
        // A `\\?\D:\...` verbatim prefix names the same local drive path; it is what
        // `canonicalize` returns on Windows. Strip it so an absolute local path is not
        // refused merely for how it was spelled, while a real UNC share still is.
        let text = text.strip_prefix("//?/").unwrap_or(&text).to_string();
        if !path.is_absolute()
            || text.starts_with("e:")
            || text.starts_with("//")
            || path
                .components()
                .any(|p| matches!(p, std::path::Component::ParentDir))
        {
            return Err("invalid worker profile path");
        }
        let mut part = std::path::PathBuf::new();
        for component in path.components() {
            part.push(component);
            archeaxis_store_sqlite::raw_objects::reject_links(&part)
                .map_err(|_| "invalid worker profile path")?;
        }
        Ok(())
    }

    pub fn validate(&self) -> Result<(), &'static str> {
        for path in [&self.python, &self.script, &self.staging] {
            Self::validate_path(path)?;
        }
        if !self.python.is_file() || !self.script.is_file() {
            return Err("worker profile file missing");
        }
        for route in &self.routes {
            // An empty or duplicated capability would silently shadow a route
            // rather than fail, so it is refused here instead.
            let capability = route.capability.trim();
            if capability.is_empty() {
                return Err("worker route capability must not be empty");
            }
            if capability == "text.extract" {
                return Err("worker route must not redeclare text.extract");
            }
            Self::validate_path(&route.script)?;
            if !route.script.is_file() {
                return Err("worker route script missing");
            }
        }
        let mut seen = std::collections::HashSet::new();
        for route in &self.routes {
            if !seen.insert(route.capability.trim()) {
                return Err("duplicate worker route capability");
            }
        }
        Ok(())
    }
}
/// Hard bound on the launch document a parent may write to this process's stdin.
///
/// The bound exists because the parent is a separate process: the child must never read an
/// unbounded stream just because someone started it by hand. It was 4096, which a shipped
/// product profile now nearly fills on its own - a 13-route launch with absolute worker paths
/// measures 2741 bytes from a short install root and 4405 bytes from a deep one, so the deep
/// install failed with exit code 2 and the desktop reported only "Core 未就绪". 64 KiB keeps a
/// hard bound with roughly an order of magnitude of headroom for a legitimate profile.
const MAX_LAUNCH_BYTES: usize = 65536;

impl Launch {
    pub fn from_stdin() -> Result<Self, &'static str> {
        // A std thread (not the async blocking pool) lets main exit on a parent
        // that holds stdin open. Never include input or parse details in errors.
        let (send, receive) = mpsc::channel();
        std::thread::spawn(move || {
            let mut bytes = Vec::new();
            let result = std::io::stdin()
                .take(MAX_LAUNCH_BYTES as u64 + 1)
                .read_to_end(&mut bytes);
            let _ = send.send(result.map(|_| bytes));
        });
        let bytes = receive
            .recv_timeout(Duration::from_secs(5))
            .map_err(|_| "launch input timed out")?
            .map_err(|_| "launch input failed")?;
        if bytes.len() > MAX_LAUNCH_BYTES {
            return Err("launch input exceeds limit");
        }
        // Bounded *and* valid UTF-8: the two are named separately so a caller can tell an oversized
        // document from an encoding mistake without the bytes ever appearing in an error.
        if std::str::from_utf8(&bytes).is_err() {
            return Err("launch input is not utf-8");
        }
        let mut launch: Self =
            serde_json::from_slice(&bytes).map_err(|_| "invalid launch input")?;
        if !hex(&launch.launch_token, 64) || !hex(&launch.session_id, 32) {
            return Err("invalid launch identity");
        }
        if launch
            .document_check_config_error
            .as_deref()
            .is_some_and(|value| value != "invalid_config")
            || (launch.document_check_config_error.is_some()
                && launch.document_check_config.is_some())
        {
            return Err("invalid document check error contract");
        }
        if let Some(config) = &launch.document_check_config {
            if config.validate().is_err()
                || !launch.text_worker.as_ref().is_some_and(|worker| {
                    worker
                        .routes
                        .iter()
                        .any(|route| route.capability == "machine.answer")
                })
            {
                launch.document_check_config = None;
                launch.document_check_config_error = Some("invalid_config".into());
            }
        }
        // Legacy preserves its single actor; v2 gives one owned session two
        // distinct credentials. Unknown/null/partial v2 claims never downgrade.
        match launch.protocol.as_deref() {
            None => {
                if launch.machine_token.is_some() {
                    return Err("machine token requires v2");
                }
                if !matches!(
                    launch.actor.as_deref(),
                    None | Some("human") | Some("machine")
                ) {
                    return Err("invalid launch actor");
                }
            }
            Some("archeaxis.desktop-launch/v2") => {
                if launch.actor.as_deref() != Some("human") {
                    return Err("invalid v2 launch actor");
                }
                let machine = launch
                    .machine_token
                    .as_deref()
                    .ok_or("missing machine identity")?;
                if !hex(machine, 64) || machine.eq_ignore_ascii_case(&launch.launch_token) {
                    return Err("invalid machine identity");
                }
            }
            Some(_) => return Err("unsupported launch protocol"),
        }
        if let Some(profile) = &mut launch.text_worker {
            profile.resolve_root()?;
            profile.validate()?;
        }
        Ok(launch)
    }
}
fn hex(s: &str, n: usize) -> bool {
    s.len() == n && s.bytes().all(|b| b.is_ascii_hexdigit())
}

#[cfg(test)]
mod tests {
    use super::*;

    fn profile(root: Option<&str>) -> TextWorker {
        TextWorker {
            python: std::path::PathBuf::from("python.exe"),
            script: std::path::PathBuf::from("workers/transport/text_ndjson.py"),
            staging: std::path::PathBuf::from("data/worker-staging"),
            routes: vec![WorkerRoute {
                capability: "pdf.extract".into(),
                script: std::path::PathBuf::from("workers/document/worker_pdf.py"),
            }],
            root: root.map(std::path::PathBuf::from),
        }
    }

    #[test]
    fn a_declared_root_resolves_every_relative_path() {
        let mut worker = profile(Some("C:/install"));
        worker.resolve_root().unwrap();
        assert_eq!(
            worker.python,
            std::path::PathBuf::from("C:/install/python.exe")
        );
        assert_eq!(
            worker.script,
            std::path::PathBuf::from("C:/install/workers/transport/text_ndjson.py")
        );
        assert_eq!(
            worker.staging,
            std::path::PathBuf::from("C:/install/data/worker-staging")
        );
        assert_eq!(
            worker.routes[0].script,
            std::path::PathBuf::from("C:/install/workers/document/worker_pdf.py")
        );
    }

    #[test]
    fn an_absolute_path_is_left_alone_even_with_a_root() {
        let mut worker = profile(Some("C:/install"));
        worker.python = std::path::PathBuf::from("C:/other/python.exe");
        worker.resolve_root().unwrap();
        assert_eq!(
            worker.python,
            std::path::PathBuf::from("C:/other/python.exe")
        );
    }

    #[test]
    fn a_relative_path_with_no_root_is_refused_rather_than_guessed() {
        let mut worker = profile(None);
        assert_eq!(
            worker.resolve_root().unwrap_err(),
            "worker path is relative and the launch declares no root"
        );
    }

    #[test]
    fn absolute_paths_with_no_root_keep_the_previous_behaviour() {
        let mut worker = profile(None);
        worker.python = std::path::PathBuf::from("C:/install/python.exe");
        worker.script = std::path::PathBuf::from("C:/install/workers/transport/text_ndjson.py");
        worker.staging = std::path::PathBuf::from("C:/install/data/worker-staging");
        worker.routes[0].script =
            std::path::PathBuf::from("C:/install/workers/document/worker_pdf.py");
        assert!(worker.resolve_root().is_ok());
    }

    #[test]
    fn a_root_that_climbs_outward_is_refused() {
        let mut worker = profile(Some("C:/install/../secrets"));
        assert_eq!(
            worker.resolve_root().unwrap_err(),
            "invalid worker profile path"
        );
    }
}
#[derive(Clone)]
struct Session {
    launch: Launch,
    workspace_db: String,
    sqlite_version: String,
}

/// Wrap every route, including fallbacks, before binding the production listener.
pub async fn protect(router: Router, store: &Store, launch: Launch) -> Result<Router, StoreError> {
    let workspace_db = store
        .submit(|conn| {
            conn.query_row(
                "SELECT file FROM pragma_database_list WHERE name='main'",
                [],
                |r| r.get::<_, String>(0),
            )
        })
        .await??;
    let sqlite_version = store
        .submit(|conn| conn.query_row("SELECT sqlite_version()", [], |r| r.get::<_, String>(0)))
        .await??;
    Ok(router.layer(middleware::from_fn_with_state(
        Session {
            launch,
            workspace_db,
            sqlite_version,
        },
        authenticate,
    )))
}
fn error(status: StatusCode, code: &str, message: &str) -> Response {
    (
        status,
        Json(serde_json::json!({"code":code,"message":message,"retryable":false})),
    )
        .into_response()
}
async fn authenticate(State(session): State<Session>, request: Request, next: Next) -> Response {
    let values = request.headers().get_all("x-archeaxis-launch-token");
    let mut values = values.iter();
    let value = values.next().map(|v| v.as_bytes()).unwrap_or_default();
    let expected = session.launch.launch_token.as_bytes();
    let matches = |expected: &[u8]| {
        value.len() == expected.len()
            && value
                .iter()
                .zip(expected)
                .fold(0u8, |diff, (a, b)| diff | (a ^ b))
                == 0
    };
    let primary = matches(expected);
    let machine = session
        .launch
        .machine_token
        .as_ref()
        .map(|token| matches(token.as_bytes()))
        .unwrap_or(false);
    if !(primary || machine) || values.next().is_some() {
        return error(
            StatusCode::UNAUTHORIZED,
            "AAK-AUTH-001",
            "invalid launch credentials",
        );
    }
    let actor = if machine || session.launch.actor.as_deref() == Some("machine") {
        "machine"
    } else {
        "human"
    };
    // Formal desktop is a native client. Do not allow browser origins to turn
    // this localhost API into a credentialed cross-origin write surface.
    if request.headers().contains_key("origin") {
        return error(
            StatusCode::FORBIDDEN,
            "AAK-AUTH-002",
            "browser origin not allowed",
        );
    }
    if request.method() == Method::GET && request.uri().path() == "/api/v1/system/version" {
        let mut version = serde_json::json!({"runtime":"archeaxis-api","contract":"0.1.0-outline",
            "schema_version":archeaxis_store_sqlite::SCHEMA_VERSION,
            "sqlite_version":session.sqlite_version,
            "session_id":session.launch.session_id,"workspace_db":session.workspace_db});
        if let Some(protocol) = &session.launch.protocol {
            version["launch_protocol"] = serde_json::json!(protocol);
            version["actor"] = serde_json::json!(actor);
        }
        return Json(version).into_response();
    }
    // Overwrite self-reported identity with the role of the matched bootstrap
    // credential, including for machine requests to the same human-owned Core.
    let (mut parts, body) = request.into_parts();
    parts.headers.insert(
        "x-archeaxis-actor",
        axum::http::header::HeaderValue::from_static(if actor == "machine" {
            "machine"
        } else {
            "human"
        }),
    );
    next.run(axum::http::Request::from_parts(parts, body)).await
}

#[cfg(test)]
mod route_declaration_tests {
    use super::*;
    use std::fs;

    /// A profile whose three required paths exist, so `validate` reaches the routes.
    fn worker(dir: &std::path::Path, routes: Vec<WorkerRoute>) -> TextWorker {
        let python = dir.join("python.exe");
        let script = dir.join("text_ndjson.py");
        let staging = dir.join("staging");
        for path in [&python, &script] {
            fs::write(path, b"stub").unwrap();
        }
        fs::create_dir_all(&staging).unwrap();
        TextWorker {
            python,
            script,
            staging,
            routes,
            root: None,
        }
    }

    fn route(dir: &std::path::Path, capability: &str, name: &str, exists: bool) -> WorkerRoute {
        let script = dir.join(name);
        if exists {
            fs::write(&script, b"stub").unwrap();
        }
        WorkerRoute {
            capability: capability.to_string(),
            script,
        }
    }

    #[test]
    fn absent_routes_keep_the_single_text_route() {
        let dir = tempfile::tempdir().unwrap();
        let profile = worker(dir.path(), Vec::new());
        assert!(profile.validate().is_ok());
        assert!(profile.extra_routes().is_empty());
    }

    #[test]
    fn a_declared_route_is_returned_as_capability_and_script() {
        let dir = tempfile::tempdir().unwrap();
        let profile = worker(
            dir.path(),
            vec![route(dir.path(), "pdf.extract", "worker_pdf.py", true)],
        );
        assert!(profile.validate().is_ok());
        let extra = profile.extra_routes();
        assert_eq!(extra.len(), 1);
        assert_eq!(extra[0].0, "pdf.extract");
        assert!(extra[0].1.is_file());
    }

    #[test]
    fn a_route_script_that_does_not_exist_is_refused() {
        let dir = tempfile::tempdir().unwrap();
        let profile = worker(
            dir.path(),
            vec![route(dir.path(), "pdf.extract", "absent.py", false)],
        );
        assert_eq!(profile.validate(), Err("worker route script missing"));
    }

    #[test]
    fn redeclaring_text_extract_is_refused() {
        let dir = tempfile::tempdir().unwrap();
        let profile = worker(
            dir.path(),
            vec![route(dir.path(), "text.extract", "other.py", true)],
        );
        assert_eq!(
            profile.validate(),
            Err("worker route must not redeclare text.extract")
        );
    }

    #[test]
    fn an_empty_capability_is_refused() {
        let dir = tempfile::tempdir().unwrap();
        let profile = worker(dir.path(), vec![route(dir.path(), "   ", "other.py", true)]);
        assert_eq!(
            profile.validate(),
            Err("worker route capability must not be empty")
        );
    }

    #[test]
    fn a_duplicate_capability_is_refused_rather_than_silently_shadowed() {
        let dir = tempfile::tempdir().unwrap();
        let profile = worker(
            dir.path(),
            vec![
                route(dir.path(), "pdf.extract", "a.py", true),
                route(dir.path(), "pdf.extract", "b.py", true),
            ],
        );
        assert_eq!(profile.validate(), Err("duplicate worker route capability"));
    }

    #[test]
    fn a_route_script_may_not_escape_through_a_parent_component() {
        let dir = tempfile::tempdir().unwrap();
        let mut profile = worker(dir.path(), Vec::new());
        profile.routes = vec![WorkerRoute {
            capability: "pdf.extract".into(),
            script: dir.path().join("..").join("outside.py"),
        }];
        assert_eq!(profile.validate(), Err("invalid worker profile path"));
    }
}
