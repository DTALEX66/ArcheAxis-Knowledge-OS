//! ArcheAxis vNext domain Core (sole business writer, via the store crate).
//!
//! Language/authority contract (repo-seed PROJECT_CONTRACT.yaml + ADR-0001):
//! - Rust is the ONLY business writer to the vNext SQLite database.
//! - C#/Avalonia = desktop layer (later); Python = capability worker (no DB handle).
//! - Prohibited: dual-write, worker/agent direct SQL, copy live WAL/SHM.

pub mod ai_asset;
pub mod anchor;
pub mod asset_context_grant;
pub mod backup;
pub mod bounded_formula;
pub mod collection;
pub mod context_grant;
pub mod course;
pub mod document;
mod document_tags;
pub mod expression;
pub mod external_context;
pub mod ingest_batches;
pub mod ingest_relations;
pub mod knowledge;
pub mod layout;
pub mod learning;
pub mod machine;
pub mod machine_evaluation;
pub mod object_reference;
pub mod relation_projection;
pub mod research;
pub mod search;
pub mod source;
pub mod teaching;
pub mod template_binding;
pub mod template_definition;
pub mod ui_state;
pub mod vault;
pub mod vault_members;

pub use source::ImportOutcome;
pub mod portable_document;

pub mod configuration_plans;
pub mod material_question;
pub mod model_configuration;

pub mod character_memory;

pub mod public_research;
pub mod readiness;
