//! R7/G1: the capability enable/disable record.
//!
//! The master taskpack's section 42 asks the first version for a registry, **enable/disable**,
//! health, default and fallback. Registry, health and resolution are already served by
//! `archeaxis-api::capabilities`; this is the write side that was missing.
//!
//! Two decisions are encoded here rather than left to a caller:
//!
//! * **An absent row means enabled.** A capability the launch registered and nobody disabled is
//!   what the Core serves, so only a decision is written. The alternative - writing a row per
//!   registered route - would make the table a copy of the launch document that could drift from
//!   it.
//! * **The record is the Rust Core's**, like everything else canonical. A plugin or a UI asks
//!   through the Core; it never reaches this table directly.

use rusqlite::{Connection, OptionalExtension};

/// Whether a capability is currently enabled. Unknown capabilities read as enabled, because this
/// table records decisions and knows nothing about registration; the registry is what decides
/// whether a capability exists at all.
pub fn is_enabled(conn: &Connection, capability: &str) -> rusqlite::Result<bool> {
    let stored: Option<i64> = conn
        .query_row(
            "SELECT enabled FROM capability_settings WHERE capability=?1",
            [capability],
            |row| row.get(0),
        )
        .optional()?;
    // Absent means enabled. A row saying 0 is the only way to be disabled.
    Ok(stored.unwrap_or(1) == 1)
}

/// The capabilities this workspace has explicitly turned off, so a registry can report decisions
/// without querying once per capability.
pub fn disabled_capabilities(conn: &Connection) -> rusqlite::Result<Vec<String>> {
    let mut statement = conn.prepare(
        "SELECT capability FROM capability_settings WHERE enabled=0 ORDER BY capability",
    )?;
    let rows = statement.query_map([], |row| row.get::<_, String>(0))?;
    rows.collect()
}

/// Record a decision. `changed_at` is refreshed on every write so the row says when it was last
/// changed rather than when it was first written.
pub fn set_enabled(conn: &Connection, capability: &str, enabled: bool) -> rusqlite::Result<()> {
    conn.execute(
        "INSERT INTO capability_settings(capability, enabled, changed_at)
         VALUES(?1, ?2, datetime('now'))
         ON CONFLICT(capability) DO UPDATE SET enabled=excluded.enabled,
                                               changed_at=excluded.changed_at",
        rusqlite::params![capability, if enabled { 1 } else { 0 }],
    )?;
    Ok(())
}
