//! Read-only first-release plans. Configuration identity is not an artifact hash or a grant.
use crate::model_configuration::{self, Configuration};
use serde::Serialize;
use sha2::{Digest, Sha256};

#[derive(Debug, Serialize)]
pub struct Module {
    pub capability: String,
    pub enabled: Option<bool>,
    pub runtime_qualification: &'static str,
}
#[derive(Debug, Serialize)]
pub struct Plan {
    pub plan_id: String,
    pub profile_id: String,
    pub model: String,
    pub mode: &'static str,
    pub source: Option<String>,
    pub version: Option<String>,
    pub artifact_sha256: Option<String>,
    pub size_bytes: Option<u64>,
    pub executable: bool,
    pub reason_code: &'static str,
    pub risk_scope: &'static str,
    pub rollback: &'static str,
}
#[derive(Debug, Serialize)]
pub struct Catalog {
    pub schema: &'static str,
    pub workspace_id: String,
    pub restore_epoch: String,
    pub configuration_revision: u64,
    pub configuration_sha256: String,
    pub modules: Vec<Module>,
    pub plans: Vec<Plan>,
    pub remote_service_support: &'static str,
    pub installer_available: bool,
    pub requires_formal_plan_and_grant: bool,
    pub execution_grant: Option<String>,
    pub network_performed: bool,
    pub storage_changed: bool,
    pub worker_started: bool,
}
pub fn catalog(configuration: Configuration, modules: Vec<Module>) -> rusqlite::Result<Catalog> {
    model_configuration::validate(&configuration)?;
    let raw = serde_json::to_vec(&configuration)
        .map_err(|_| rusqlite::Error::InvalidParameterName("CONFIGURATION_PLAN_INVALID".into()))?;
    let digest = format!("{:x}", Sha256::digest(&raw));
    let mut plans = Vec::new();
    for (profile_id, profile) in &configuration.profiles {
        for mode in ["existing_service", "local_download"] {
            let id = format!(
                "{:x}",
                Sha256::digest(format!("{digest}:{profile_id}:{mode}"))
            );
            let existing = mode == "existing_service";
            plans.push(Plan {
                plan_id: id,
                profile_id: profile_id.clone(),
                model: profile.model.clone(),
                mode,
                source: existing.then(|| profile.endpoint.clone()),
                version: None,
                artifact_sha256: None,
                size_bytes: None,
                executable: false,
                reason_code: if existing {
                    "SERVICE_NOT_PROBED_PLAN_ONLY"
                } else {
                    "INSTALLER_AND_APPROVED_SOURCE_UNAVAILABLE"
                },
                risk_scope: if existing {
                    "LOOPBACK_SERVICE_CONNECTION_REQUIRES_SEPARATE_EXECUTION"
                } else {
                    "LOCAL_DISK_AND_PROCESS_CHANGES_NOT_AUTHORIZED_BY_READ"
                },
                rollback: if existing {
                    "RETAIN_CURRENT_BINDINGS_NO_CONNECTION_PERFORMED"
                } else {
                    "NO_ARTIFACT_CREATED_NO_ROLLBACK_REQUIRED"
                },
            });
        }
    }
    Ok(Catalog {
        schema: "archeaxis.configuration-plans/v1",
        workspace_id: configuration.workspace_id,
        restore_epoch: configuration.restore_epoch,
        configuration_revision: configuration.revision,
        configuration_sha256: digest,
        modules,
        plans,
        remote_service_support: "UNSUPPORTED_BY_CURRENT_LOOPBACK_CONTRACT",
        installer_available: false,
        requires_formal_plan_and_grant: true,
        execution_grant: None,
        network_performed: false,
        storage_changed: false,
        worker_started: false,
    })
}
