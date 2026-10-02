//! R7/G1: the capability surface the UI reads to tell a capability apart from a promise.
//!
//! Section 42 of the master taskpack asks the first version for a registry, enable/disable, health,
//! default and fallback, and section 33 names `AAOS_CAPABILITY_REGISTRY_V1`. This module is the
//! read side of that, and it is deliberately narrow about what it claims.
//!
//! The honesty rules it follows, because a capability surface is exactly where a project starts
//! lying to itself:
//!
//! * It reports the routes the Core actually registered, not the routes a checkout happens to
//!   contain. The launch declares routes, so the launch is the source of truth.
//! * `health` describes what is checkable from here - whether the worker script exists and whether
//!   the interpreter does. It does **not** claim a capability is working, because that requires
//!   running a job, and a registry cannot substitute for a job.
//! * `enabled` is reported as the Core's own registration state rather than as a setting, because
//!   enable/disable is not implemented yet. Saying `true` there without saying that would read as a
//!   feature that does not exist.
//! * `/api/v1/capabilities` needs no store, so it answers even when the database is unavailable -
//!   which matters, because "which capabilities exist" is the question a broken workspace asks.

use std::path::Path;

use axum::Json;
use axum::http::StatusCode;
use axum::response::{IntoResponse, Response};
use serde_json::json;

use archeaxis_application::executor::Executor;

/// Whether a path exists as a regular file. Health is a fact about the filesystem, so it is checked
/// rather than assumed from configuration.
fn file_exists(path: &Path) -> bool {
    std::fs::metadata(path)
        .map(|meta| meta.is_file())
        .unwrap_or(false)
}

fn capability_record(
    capability: &str,
    worker: &Path,
    site_packages: bool,
    python: &Path,
) -> serde_json::Value {
    let worker_present = file_exists(worker);
    let python_present = file_exists(python);
    let health = if !worker_present {
        // A declared capability whose worker is absent is not "unhealthy"; it is unusable, and the
        // difference matters to whoever has to fix it.
        "worker_missing"
    } else if !python_present {
        "interpreter_missing"
    } else {
        "declared"
    };
    json!({
        "capability": capability,
        "provider": {
            // The provider is the worker script. Naming it is what lets a UI say which process
            // would answer, instead of implying a capability is built into the Core.
            "kind": "python-worker",
            "worker": worker.to_string_lossy(),
            "worker_present": worker_present,
            "interpreter": python.to_string_lossy(),
            "interpreter_present": python_present,
            "uses_site_packages": site_packages,
        },
        "enabled": true,
        "enabled_basis": "registered by the launch; enable/disable is not implemented yet",
        "health": health,
        "health_basis": "file existence only - a job has to run before anything may be called \
                         working",
        "is_default": true,
        "fallback": serde_json::Value::Null,
        "fallback_note": "no second provider exists for any capability yet",
    })
}

fn registry_document(executor: &Executor) -> serde_json::Value {
    let routes = executor.registered_routes();
    let python = executor.python_path();
    let capabilities: Vec<serde_json::Value> = routes
        .iter()
        .map(|(capability, worker, site_packages)| {
            capability_record(capability, worker, *site_packages, python)
        })
        .collect();
    let unhealthy = capabilities
        .iter()
        .filter(|record| record["health"] != "declared")
        .count();
    json!({
        "schema": "archeaxis.capabilities/v1",
        "source": "capability routes declared at launch and registered by the Core",
        "count": capabilities.len(),
        "unhealthy": unhealthy,
        "declared_only": true,
        "declared_only_note": "this surface reports registration and file health; it is not proof \
                               a capability works, and a passing entry here must not be read as one",
        "capabilities": capabilities,
    })
}

/// The whole registry. No store and no database read: a workspace whose database will not open still
/// has to be able to answer which capabilities exist.
pub fn list(executor: &Executor) -> Response {
    Json(registry_document(executor)).into_response()
}

/// One capability by its exact dot-separated name. A near miss is a 404 rather than the nearest
/// match, because a registry that guesses is worse than one that says it does not know.
pub fn read(executor: &Executor, capability: &str) -> Response {
    let routes = executor.registered_routes();
    match routes.iter().find(|(name, _, _)| *name == capability) {
        Some((name, worker, site_packages)) => {
            let python = executor.python_path();
            Json(json!({
                "schema": "archeaxis.capability/v1",
                "capability": capability_record(name, worker, *site_packages, python),
            }))
            .into_response()
        }
        None => (
            StatusCode::NOT_FOUND,
            format!("no capability is registered as {capability}"),
        )
            .into_response(),
    }
}
