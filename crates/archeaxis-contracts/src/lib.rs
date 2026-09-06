//! Shared vNext contracts. Vocabulary is generated from the canonical JSON
//! Schemas, not hand-maintained copies. Run generate_vocabulary.py --check
//! to detect drift; shared JSON cases exercise actual language parsers.
pub mod loss_receipt;

#[path = "generated/vocabulary.rs"]
mod vocabulary;
pub use vocabulary::*;
