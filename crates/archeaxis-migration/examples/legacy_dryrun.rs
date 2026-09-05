//! Example: read-only legacy migration dry-run.
//!
//! cargo run -p archeaxis-migration --example legacy_dryrun -- <legacy-db> <out-dir>
//!
//! Opens the legacy database READ-ONLY, inventories its tables, exports user
//! tables to JSONL + sha256 manifest in out-dir, and prints a dry-run summary.
//! Never writes to the legacy database.

use archeaxis_migration::{export_jsonl, inventory};

fn main() {
    let args: Vec<String> = std::env::args().collect();
    if args.len() < 3 {
        eprintln!("usage: legacy_dryrun <legacy-db> <out-dir>");
        std::process::exit(2);
    }
    let db = &args[1];
    let out = &args[2];

    match inventory(db) {
        Ok(tables) => {
            println!("inventory: {} user tables", tables.len());
            for t in &tables {
                println!("  {}: {} rows, {} cols", t.name, t.row_count, t.columns.len());
            }
            match export_jsonl(db, out) {
                Ok(manifest) => {
                    println!("export manifest_sha256={}", manifest.manifest_sha256);
                    println!("tables exported: {}", manifest.tables.len());
                    for (name, tf) in &manifest.tables {
                        println!("  {}: {} rows sha256={}", name, tf.rows, &tf.sha256[..12]);
                    }
                    std::process::exit(0);
                }
                Err(e) => {
                    eprintln!("export failed: {e}");
                    std::process::exit(1);
                }
            }
        }
        Err(e) => {
            eprintln!("inventory failed: {e}");
            std::process::exit(1);
        }
    }
}
