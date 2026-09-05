//! ArcheAxis vNext domain Core (sole business writer, via the store crate).
//!
//! Language/authority contract (repo-seed PROJECT_CONTRACT.yaml + ADR-0001):
//! - Rust is the ONLY business writer to the vNext SQLite database.
//! - C#/Avalonia = desktop layer (later); Python = capability worker (no DB handle).
//! - Prohibited: dual-write, worker/agent direct SQL, copy live WAL/SHM.

pub mod anchor;
pub mod backup;
pub mod knowledge;
pub mod learning;
pub mod search;
pub mod source;

pub use source::ImportOutcome;
