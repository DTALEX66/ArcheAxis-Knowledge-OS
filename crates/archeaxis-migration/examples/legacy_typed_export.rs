//! Typed preservation export only, never a semantic migration.
use archeaxis_migration::{
    export_typed_document_content_jsonl, export_typed_intake_content_jsonl, export_typed_jsonl,
    validate_typed_export_output,
};
use std::path::Path;
fn main() {
    let args: Vec<String> = std::env::args().collect();
    if args.len() != 4
        && !(args.len() == 5
            && ["--document-content", "--intake-content"].contains(&args[4].as_str()))
    {
        eprintln!(
            "usage: legacy_typed_export <project-root> <authorized-snapshot> <fresh-output> [--document-content|--intake-content]"
        );
        std::process::exit(2);
    }
    let result =
        validate_typed_export_output(Path::new(&args[1]), Path::new(&args[3])).and_then(|_| {
            if args.len() == 5 && args[4] == "--intake-content" {
                export_typed_intake_content_jsonl(&args[2], &args[3])
            } else if args.len() == 5 {
                export_typed_document_content_jsonl(&args[2], &args[3])
            } else {
                export_typed_jsonl(&args[2], &args[3])
            }
        });
    match result {
        Ok(manifest) => {
            println!(
                "{} tables={} schema_only_tables={}",
                manifest.disposition,
                manifest.tables.len(),
                manifest.unqueried_tables.len()
            );
        }
        Err(_) => {
            eprintln!("typed export failed; no semantic migration performed");
            std::process::exit(1);
        }
    }
}
