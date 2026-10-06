//! Typed preservation export only, never a semantic migration.
use archeaxis_migration::{export_typed_jsonl, validate_typed_export_output};
use std::path::Path;
fn main() {
    let args: Vec<String> = std::env::args().collect();
    if args.len() != 4 {
        eprintln!("usage: legacy_typed_export <project-root> <authorized-snapshot> <fresh-output>");
        std::process::exit(2);
    }
    let result = validate_typed_export_output(Path::new(&args[1]), Path::new(&args[3]))
        .and_then(|_| export_typed_jsonl(&args[2], &args[3]));
    match result {
        Ok(manifest) => {
            println!(
                "PRESERVED_NOT_SEMANTICALLY_MIGRATED tables={}",
                manifest.tables.len()
            );
        }
        Err(_) => {
            eprintln!("typed export failed; no semantic migration performed");
            std::process::exit(1);
        }
    }
}
