//! T3 lifecycle in the existing capability record. Only bundled inert data may
//! authorize a new application; a historical snapshot never authorizes code.
use crate::document::Error;
use archeaxis_store_sqlite::capability_settings::{self, TemplateState};
use rusqlite::Connection;
use serde::Deserialize;
use serde_json::{Value, json};
use sha2::{Digest, Sha256};

pub const CAPABILITY: &str = "template.T3";
const DEFINITIONS: &str =
    include_str!("../../../packages/contracts/v2/first-party-t3-definitions.json");

pub fn definition(version: i64) -> Option<Value> {
    let manifest: Value = serde_json::from_str(DEFINITIONS).expect("bundled definition JSON");
    let snapshot = manifest["definitions"]
        .as_array()?
        .iter()
        .find(|d| d["version"] == version)?
        .clone();
    let sha256 = hex::encode(Sha256::digest(snapshot.to_string().as_bytes()));
    Some(json!({"version":version,"sha256":sha256,"snapshot":snapshot}))
}

pub fn record(conn: &Connection) -> Result<Value, Error> {
    let state = capability_settings::template_state(conn)?;
    let selected = definition(state.version)
        .ok_or(Error::Invalid("template selected definition unavailable"))?;
    let available: Vec<_> = [1, 2].into_iter().filter_map(definition).collect();
    Ok(
        json!({"capability":CAPABILITY,"provider":{"kind":"first-party-data-only"},
        "registered":true,"enabled":state.enabled,"installed":state.installed,
        "state_epoch":state.epoch,"definition":selected,"available_definitions":available,
        "health":"bundled_data","health_basis":"bundled first-party data; no worker or external package executed",
        "execution_verified":false,"required_dependencies":[],"optional_dependencies":["course.general"],
        "license":"MIT","license_basis":"repository LICENSE; only this first-party definition",
        "legacy_binding_policy":"existing unversioned T3 edits remain compatible; new legacy applications require enabled installed v1, new pinned applications require the current definition and epoch"}),
    )
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Change {
    pub expected_epoch: i64,
    pub action: String,
    pub version: i64,
    pub sha256: String,
}

pub fn change(conn: &mut Connection, request: &Change) -> Result<Value, Error> {
    let tx = conn.transaction()?;
    let mut state = capability_settings::template_state(&tx)?;
    if state.epoch != request.expected_epoch {
        return Err(Error::Conflict(state.epoch));
    }
    let target = definition(request.version)
        .ok_or(Error::Invalid("unknown first-party template version"))?;
    if target["sha256"].as_str() != Some(request.sha256.as_str()) {
        return Err(Error::Invalid("first-party template hash mismatch"));
    }
    match request.action.as_str() {
        "enable" if state.installed && request.version == state.version => state.enabled = true,
        "disable" if state.installed && request.version == state.version => state.enabled = false,
        "update" if state.installed && request.version > state.version => {
            state.version = request.version
        }
        "rollback" if state.installed && request.version < state.version => {
            state.version = request.version
        }
        "uninstall" if state.installed && request.version == state.version => {
            state.installed = false;
            state.enabled = false;
        }
        "install" if !state.installed => {
            state.installed = true;
            state.enabled = true;
            state.version = request.version;
        }
        _ => {
            return Err(Error::Invalid(
                "template lifecycle transition not applicable",
            ));
        }
    }
    commit_state(tx, state)
}

pub fn set_enabled(conn: &mut Connection, enabled: bool) -> Result<Value, Error> {
    let tx = conn.transaction()?;
    let mut state = capability_settings::template_state(&tx)?;
    if enabled && !state.installed {
        return Err(Error::Invalid("template is uninstalled"));
    }
    state.enabled = enabled;
    commit_state(tx, state)
}

/// Both entry points commit through the same state/epoch/readback transaction;
/// their lifecycle and compatibility preconditions remain separate above.
fn commit_state(tx: rusqlite::Transaction<'_>, mut state: TemplateState) -> Result<Value, Error> {
    state.epoch = state
        .epoch
        .checked_add(1)
        .ok_or(Error::Invalid("template epoch exhausted"))?;
    capability_settings::write_template_state(&tx, &state)?;
    let result = record(&tx)?;
    tx.commit()?;
    Ok(result)
}

/// Readable history is self-contained. New applications must additionally match
/// the bundled selected definition AND the current persisted permission epoch.
pub fn validate_new_pin(conn: &Connection, pin: &Value) -> Result<(), Error> {
    let TemplateState {
        enabled,
        installed,
        version,
        epoch,
    } = capability_settings::template_state(conn)?;
    if !enabled || !installed {
        return Err(Error::Invalid(
            "template application disabled or uninstalled",
        ));
    }
    let mut expected =
        definition(version).ok_or(Error::Invalid("template definition unavailable"))?;
    expected["application_epoch"] = json!(epoch);
    if pin != &expected {
        return Err(Error::Invalid(
            "template definition or application epoch changed; refresh before applying",
        ));
    }
    Ok(())
}

pub fn validate_legacy_application(conn: &Connection) -> Result<(), Error> {
    let state = capability_settings::template_state(conn)?;
    if !state.enabled || !state.installed || state.version != 1 {
        return Err(Error::Invalid(
            "legacy T3 application requires enabled installed definition v1; refresh template definition",
        ));
    }
    Ok(())
}

pub fn valid_historical_pin(pin: &Value) -> bool {
    let Some(map) = pin.as_object() else {
        return false;
    };
    map.len() == 4
        && ["version", "sha256", "snapshot", "application_epoch"]
            .iter()
            .all(|k| map.contains_key(*k))
        && pin["version"].as_i64().is_some_and(|v| v > 0)
        && pin["application_epoch"].as_i64().is_some_and(|v| v >= 0)
        && pin["snapshot"].is_object()
        && pin["snapshot"]["template_id"] == "T3"
        && pin["snapshot"]["version"] == pin["version"]
        && pin["sha256"].as_str().is_some_and(|hash| {
            hash == hex::encode(Sha256::digest(pin["snapshot"].to_string().as_bytes()))
        })
}
