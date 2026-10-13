//! Device-local preferences, separate from author drafts and frozen requests.
use crate::ui_state::{self, Error};
use rusqlite::{Connection, OptionalExtension, TransactionBehavior};
use serde::{Deserialize, Serialize};
use std::collections::{BTreeMap, HashSet};

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(tag = "kind", rename_all = "snake_case", deny_unknown_fields)]
pub enum Dock {
    Tabs {
        panels: Vec<String>,
        active: String,
    },
    Split {
        axis: Axis,
        ratio: f64,
        first: Box<Dock>,
        second: Box<Dock>,
    },
}
#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum Axis {
    Horizontal,
    Vertical,
}
#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct Bounds {
    pub x: f64,
    pub y: f64,
    pub width: f64,
    pub height: f64,
}
#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct Layout {
    pub schema_version: u32,
    pub preset_id: String,
    pub registered_panels: Vec<String>,
    pub dock_tree: Dock,
    pub floating_bounds: BTreeMap<String, Bounds>,
}
#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct Snapshot {
    pub workspace_id: String,
    pub device_id: String,
    pub restore_epoch: String,
    pub revision: i64,
    pub layout: Layout,
    pub recovery_reason: Option<String>,
}
#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct Write {
    pub workspace_id: String,
    pub device_id: String,
    pub restore_epoch: String,
    pub expected_revision: i64,
    pub layout: Layout,
}
#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct Recover {
    pub workspace_id: String,
    pub device_id: String,
    pub restore_epoch: String,
    pub expected_revision: i64,
    pub viewport_width: f64,
    pub viewport_height: f64,
}
fn device(id: &str) -> Result<(), Error> {
    if id.is_empty()
        || id.len() > 64
        || !id
            .bytes()
            .all(|b| b.is_ascii_alphanumeric() || b == b'-' || b == b'_')
    {
        return Err(Error::Invalid("invalid layout device identity"));
    }
    Ok(())
}
fn default_layout() -> Layout {
    Layout {
        schema_version: 1,
        preset_id: "default".into(),
        registered_panels: vec!["01".into()],
        dock_tree: Dock::Tabs {
            panels: vec!["01".into()],
            active: "01".into(),
        },
        floating_bounds: BTreeMap::new(),
    }
}
fn panel(id: &str) -> bool {
    id.len() == 2
        && id.parse::<u8>().is_ok_and(|v| (1..=22).contains(&v))
        && id.bytes().all(|b| b.is_ascii_digit())
}
fn valid_tree(
    tree: &Dock,
    depth: usize,
    nodes: &mut usize,
    found: &mut HashSet<String>,
) -> Result<(), Error> {
    *nodes += 1;
    if depth > 16 || *nodes > 128 {
        return Err(Error::Invalid("layout tree exceeds bound"));
    }
    match tree {
        Dock::Tabs { panels, active } => {
            if panels.is_empty() || panels.len() > 22 || !panels.contains(active) {
                return Err(Error::Invalid("invalid layout tab selection"));
            }
            for id in panels {
                if !panel(id) || !found.insert(id.clone()) {
                    return Err(Error::Invalid("unknown or duplicate layout panel"));
                }
            }
        }
        Dock::Split {
            ratio,
            first,
            second,
            ..
        } => {
            if !ratio.is_finite() || !(0.1..=0.9).contains(ratio) {
                return Err(Error::Invalid("invalid layout split ratio"));
            }
            valid_tree(first, depth + 1, nodes, found)?;
            valid_tree(second, depth + 1, nodes, found)?;
        }
    }
    Ok(())
}
pub fn validate(layout: &Layout) -> Result<(), Error> {
    if layout.schema_version != 1
        || !["default", "reading", "research", "learning"].contains(&layout.preset_id.as_str())
    {
        return Err(Error::Invalid("unsupported layout schema or preset"));
    }
    let bytes = serde_json::to_vec(layout).map_err(|_| Error::Invalid("invalid layout JSON"))?;
    if bytes.len() > 32768 {
        return Err(Error::Invalid("layout exceeds byte bound"));
    }
    let declared: HashSet<_> = layout.registered_panels.iter().cloned().collect();
    if declared.len() != layout.registered_panels.len()
        || declared.is_empty()
        || declared.len() > 22
        || !declared.iter().all(|id| panel(id))
    {
        return Err(Error::Invalid("invalid registered layout panels"));
    }
    let mut docked = HashSet::new();
    valid_tree(&layout.dock_tree, 0, &mut 0, &mut docked)?;
    for (id, bounds) in &layout.floating_bounds {
        if !panel(id)
            || !docked.insert(id.clone())
            || ![bounds.x, bounds.y, bounds.width, bounds.height]
                .iter()
                .all(|v| v.is_finite())
            || bounds.x < 0.0
            || bounds.y < 0.0
            || !(160.0..=16000.0).contains(&bounds.width)
            || !(120.0..=16000.0).contains(&bounds.height)
            || bounds.x > 32000.0
            || bounds.y > 32000.0
        {
            return Err(Error::Invalid("invalid floating layout bounds"));
        }
    }
    if docked != declared {
        return Err(Error::Invalid("layout panel registry mismatch"));
    }
    Ok(())
}
fn stored(
    conn: &Connection,
    id: &str,
    current_epoch: &str,
    device_id: &str,
) -> Result<Snapshot, Error> {
    device(device_id)?;
    let key = format!("ui_layout_v1:{device_id}");
    let raw: Option<String> = conn
        .query_row(
            "SELECT value FROM workspace_meta WHERE key=?1",
            [&key],
            |r| r.get(0),
        )
        .optional()?;
    let Some(raw) = raw else {
        return Ok(Snapshot {
            workspace_id: id.into(),
            device_id: device_id.into(),
            restore_epoch: current_epoch.into(),
            revision: 0,
            layout: default_layout(),
            recovery_reason: None,
        });
    };
    if raw.len() > 65536 {
        return Err(Error::Invalid("layout storage envelope exceeds bound"));
    }
    #[derive(Deserialize)]
    #[serde(deny_unknown_fields)]
    struct Envelope {
        workspace_id: String,
        device_id: String,
        restore_epoch: String,
        revision: i64,
        layout: serde_json::Value,
        recovery_reason: Option<String>,
    }
    let envelope: Envelope =
        serde_json::from_str(&raw).map_err(|_| Error::Invalid("corrupt layout record retained"))?;
    if envelope.workspace_id != id
        || envelope.device_id != device_id
        || !(1..=9_007_199_254_740_991).contains(&envelope.revision)
        || !(envelope.restore_epoch == "initial"
            || (envelope.restore_epoch.len() == 32
                && envelope
                    .restore_epoch
                    .bytes()
                    .all(|b| b.is_ascii_hexdigit())))
    {
        return Err(Error::Invalid("corrupt layout identity retained"));
    }
    let parsed = serde_json::from_value::<Layout>(envelope.layout);
    let (layout, recovery_reason) = match parsed {
        Ok(layout) if validate(&layout).is_ok() => {
            let reason = if envelope.restore_epoch != current_epoch {
                Some("LAYOUT_RESTORE_CONFIRMATION_REQUIRED".into())
            } else {
                envelope.recovery_reason
            };
            (layout, reason)
        }
        _ => (
            default_layout(),
            Some("LAYOUT_COMPONENT_OR_SCHEMA_UNSUPPORTED".into()),
        ),
    };
    let record = Snapshot {
        workspace_id: id.into(),
        device_id: device_id.into(),
        restore_epoch: current_epoch.into(),
        revision: envelope.revision,
        layout,
        recovery_reason,
    };
    Ok(record)
}
fn save(conn: &Connection, record: &Snapshot) -> Result<(), Error> {
    let raw = serde_json::to_string(record).map_err(|_| Error::Invalid("invalid layout JSON"))?;
    conn.execute("INSERT INTO workspace_meta(key,value) VALUES(?1,?2) ON CONFLICT(key) DO UPDATE SET value=excluded.value", [format!("ui_layout_v1:{}", record.device_id), raw])?;
    Ok(())
}
pub fn read(conn: &mut Connection, device_id: &str) -> Result<Snapshot, Error> {
    device(device_id)?;
    let tx = conn.transaction_with_behavior(TransactionBehavior::Immediate)?;
    let id = ui_state::workspace_id(&tx)?;
    let epoch = ui_state::epoch(&tx)?;
    let record = stored(&tx, &id, &epoch, device_id)?;
    tx.commit()?;
    Ok(record)
}
fn compare(
    record: &Snapshot,
    id: &str,
    epoch: &str,
    request_id: &str,
    request_epoch: &str,
    revision: i64,
) -> Result<(), Error> {
    if request_id != id || request_epoch != epoch || record.revision != revision {
        return Err(Error::Conflict);
    }
    Ok(())
}
pub fn write(conn: &mut Connection, input: Write) -> Result<Snapshot, Error> {
    device(&input.device_id)?;
    validate(&input.layout)?;
    let tx = conn.transaction_with_behavior(TransactionBehavior::Immediate)?;
    let id = ui_state::workspace_id(&tx)?;
    let epoch = ui_state::epoch(&tx)?;
    let old = stored(&tx, &id, &epoch, &input.device_id)?;
    compare(
        &old,
        &id,
        &epoch,
        &input.workspace_id,
        &input.restore_epoch,
        input.expected_revision,
    )?;
    if old.recovery_reason.is_some() || old.restore_epoch != epoch {
        return Err(Error::Conflict);
    }
    let record = Snapshot {
        workspace_id: id,
        device_id: input.device_id,
        restore_epoch: epoch,
        revision: old
            .revision
            .checked_add(1)
            .filter(|value| *value <= 9_007_199_254_740_991)
            .ok_or(Error::Invalid("layout revision exhausted"))?,
        layout: input.layout,
        recovery_reason: None,
    };
    save(&tx, &record)?;
    tx.commit()?;
    Ok(record)
}
pub fn recover(conn: &mut Connection, input: Recover) -> Result<Snapshot, Error> {
    device(&input.device_id)?;
    if !input.viewport_width.is_finite()
        || !input.viewport_height.is_finite()
        || !(320.0..=16000.0).contains(&input.viewport_width)
        || !(240.0..=16000.0).contains(&input.viewport_height)
    {
        return Err(Error::Invalid("invalid recovery viewport"));
    }
    let tx = conn.transaction_with_behavior(TransactionBehavior::Immediate)?;
    let id = ui_state::workspace_id(&tx)?;
    let epoch = ui_state::epoch(&tx)?;
    let mut record = stored(&tx, &id, &epoch, &input.device_id)?;
    compare(
        &record,
        &id,
        &epoch,
        &input.workspace_id,
        &input.restore_epoch,
        input.expected_revision,
    )?;
    for bounds in record.layout.floating_bounds.values_mut() {
        bounds.width = bounds.width.min(input.viewport_width);
        bounds.height = bounds.height.min(input.viewport_height);
        bounds.x = bounds.x.min(input.viewport_width - bounds.width);
        bounds.y = bounds.y.min(input.viewport_height - bounds.height);
    }
    record.revision = record
        .revision
        .checked_add(1)
        .filter(|value| *value <= 9_007_199_254_740_991)
        .ok_or(Error::Invalid("layout revision exhausted"))?;
    record.restore_epoch = epoch;
    record.recovery_reason = None;
    validate(&record.layout)?;
    save(&tx, &record)?;
    tx.commit()?;
    Ok(record)
}
