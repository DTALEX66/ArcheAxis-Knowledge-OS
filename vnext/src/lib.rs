//! ArcheAxis vNext authoritative Core (Rust, sole SQLite writer).
//!
//! Language/authority contract (repo-seed PROJECT_CONTRACT.yaml + ADR-0001):
//! - Rust is the ONLY business writer to the vNext SQLite database.
//! - C#/Avalonia = desktop layer (later); Python = capability worker (no DB handle).
//! - Prohibited: dual-write, worker/agent direct SQL, copy live WAL/SHM.
//!
//! Day-0 scope implements the data layer of the v0.1 twelve-step closed loop:
//! workspace init -> source import (sha256 idempotent) -> anchor ->
//! personal definition + machine candidate -> accept/reject (immutable
//! receipts) -> FTS5 retrieval -> learning event -> restart read-back ->
//! online backup -> restore into a fresh workspace.

pub mod anchor;
pub mod backup;
pub mod knowledge;
pub mod learning;
pub mod schema;
pub mod search;
pub mod source;

pub use schema::init_workspace;
pub use source::ImportOutcome;
