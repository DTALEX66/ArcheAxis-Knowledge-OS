//! Drive the selective legacy migration over a real fidelity export and print its receipt.
//!
//! Usage: cargo run -p archeaxis-migration --example selective_stage -- <export_dir> <staging_db>
//! The export directory is produced by `export_jsonl` (read-only on the legacy library); this
//! driver writes only into the staging database, never into the source library.

use archeaxis_migration::stage_legacy_library_selectively;

fn main() {
    let args: Vec<String> = std::env::args().collect();
    if args.len() != 3 {
        eprintln!("usage: selective_stage <export_dir> <staging_db>");
        std::process::exit(2);
    }
    match stage_legacy_library_selectively(&args[1], &args[2]) {
        Ok(result) => println!(
            "{}",
            serde_json::to_string_pretty(&result).expect("a serializable stage result")
        ),
        Err(error) => {
            eprintln!("selective_stage failed: {error}");
            std::process::exit(1);
        }
    }
}
