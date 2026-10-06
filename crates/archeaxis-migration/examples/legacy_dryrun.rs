//! Example: read-only legacy migration dry-run.
//!
//! cargo run -p archeaxis-migration --example legacy_dryrun -- <legacy-db> <out-dir>
//!
//! Opens the legacy database READ-ONLY, inventories its tables, exports user
//! tables to JSONL + sha256 manifest in out-dir, and prints a dry-run summary.
//! Never writes to the legacy database.
//!
//! Exit codes distinguish three outcomes a caller scripts on: 0 preserved whole, 3 preserved with
//! named unqueried tables, 1 failed. A partial preservation is a real result — the real legacy
//! store has one `sqlite-vec` table this build cannot open — and reporting it as either "done" or
//! "failed" would hide which of the three happened.

use archeaxis_migration::{export_jsonl, inventory_reporting_unreadable};

fn main() {
    let args: Vec<String> = std::env::args().collect();
    if args.len() < 3 {
        eprintln!("usage: legacy_dryrun <legacy-db> <out-dir>");
        std::process::exit(2);
    }
    let db = &args[1];
    let out = &args[2];

    match inventory_reporting_unreadable(db) {
        Ok((tables, unreadable)) => {
            println!("inventory: {} readable user tables", tables.len());
            for t in &tables {
                println!(
                    "  {}: {} rows, {} cols",
                    t.name,
                    t.row_count,
                    t.columns.len()
                );
            }
            // Named, not swallowed: a table this build cannot read is a fact about the engine, and
            // the export below will be short by exactly these tables.
            for (name, reason) in &unreadable {
                println!("  UNREADABLE {name}: {reason}");
            }
            match export_jsonl(db, out) {
                Ok(manifest) => {
                    println!("export manifest_sha256={}", manifest.manifest_sha256);
                    println!("tables exported: {}", manifest.tables.len());
                    for (name, tf) in &manifest.tables {
                        println!("  {}: {} rows sha256={}", name, tf.rows, &tf.sha256[..12]);
                    }
                    if manifest.unqueried_tables.is_empty() {
                        println!("preserved whole: every readable table was exported");
                        std::process::exit(0);
                    }
                    println!(
                        "preserved with a named gap — {} table(s) not exported:",
                        manifest.unqueried_tables.len()
                    );
                    for (name, reason) in &manifest.unqueried_tables {
                        println!("  UNQUERIED {name}: {reason}");
                    }
                    std::process::exit(3);
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
