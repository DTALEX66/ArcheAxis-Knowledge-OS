//! R15: an Obsidian vault round-trip with real samples, and an honest statement of
//! what the round-trip does *not* cover.
//!
//! The fixture (`tests/fixtures/obsidian-vault`, see its PROVENANCE.txt) is a small
//! real vault: two markdown notes whose wiki-links, aliased links, heading anchor,
//! block reference and embed all resolve inside the fixture, one PNG attachment
//! whose bytes are not valid UTF-8, and a JSON Canvas 1.0 document.
//!
//! The test proves three things and refuses to imply a fourth:
//!   1. bytes and names survive an export/restore into a *fresh* workspace;
//!   2. the fixture is a genuine vault, because every internal link, heading anchor
//!      and block reference in it is resolved here, not assumed;
//!   3. the links survive *as text* in the extracted text of the note;
//!   4. nothing in this test shows that vNext absorbed the link graph: importing a
//!      vault writes no anchors, no table stores a link or embed relationship, and
//!      `.canvas` has no ingest route at all. Those are asserted as facts rather
//!      than left as silences, so the gap cannot be mistaken for coverage.

use archeaxis_application::attempts;
use archeaxis_domain::source::{self, ImportOutcome};
use archeaxis_store_sqlite::{init_workspace, raw_objects};
use rusqlite::Connection;
use std::collections::{BTreeMap, BTreeSet};
use std::path::{Path, PathBuf};

const EXPECTED_FILES: &[&str] = &[
    "PROVENANCE.txt",
    "attachments/diagram.png",
    "notes/atomic.md",
    "notes/index.md",
    "vault.canvas",
];

fn vault_root() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join("tests/fixtures/obsidian-vault")
}

fn collect(dir: &Path, prefix: &str, out: &mut Vec<(String, Vec<u8>)>) {
    let mut entries: Vec<_> = std::fs::read_dir(dir)
        .unwrap_or_else(|e| panic!("cannot read {}: {e}", dir.display()))
        .map(|entry| entry.unwrap().path())
        .collect();
    entries.sort();
    for path in entries {
        if path.is_dir() {
            let name = path.file_name().unwrap().to_string_lossy().to_string();
            let nested = if prefix.is_empty() {
                name
            } else {
                format!("{prefix}/{name}")
            };
            collect(&path, &nested, out);
        } else {
            let name = path.file_name().unwrap().to_string_lossy().to_string();
            let relative = if prefix.is_empty() {
                name
            } else {
                format!("{prefix}/{name}")
            };
            out.push((relative, std::fs::read(&path).unwrap()));
        }
    }
}

fn vault_files() -> Vec<(String, Vec<u8>)> {
    let mut out = Vec::new();
    collect(&vault_root(), "", &mut out);
    out
}

fn text_of(bytes: &[u8]) -> String {
    String::from_utf8(bytes.to_vec()).expect("markdown fixture must be UTF-8")
}

/// Wiki-links including embeds: the inner text of every `[[...]]`, verbatim.
fn wiki_links(text: &str) -> Vec<String> {
    let mut found = Vec::new();
    let mut rest = text;
    while let Some(start) = rest.find("[[") {
        let after = &rest[start + 2..];
        match after.find("]]") {
            Some(end) => {
                found.push(after[..end].to_string());
                rest = &after[end + 2..];
            }
            None => break,
        }
    }
    found
}

/// Markdown-style link targets: the inside of `](...)`.
fn markdown_links(text: &str) -> Vec<String> {
    let mut found = Vec::new();
    let mut rest = text;
    while let Some(start) = rest.find("](") {
        let after = &rest[start + 2..];
        match after.find(')') {
            Some(end) => {
                found.push(after[..end].to_string());
                rest = &after[end + 1..];
            }
            None => break,
        }
    }
    found
}

/// Split `target#anchor` into its parts; for `[[target|alias]]` the alias goes away.
fn split_target(raw: &str) -> (&str, Option<&str>) {
    let without_alias = raw.split('|').next().unwrap_or(raw);
    match without_alias.split_once('#') {
        Some((target, anchor)) => (target, Some(anchor)),
        None => (without_alias, None),
    }
}

/// Resolve a vault target the way Obsidian does: by relative path, then by basename
/// with or without its extension, then by file stem.
fn resolve(files: &[(String, Vec<u8>)], target: &str) -> Option<usize> {
    let target = target.trim();
    let basename = target.rsplit('/').next().unwrap_or(target);
    files
        .iter()
        .position(|(name, _)| name == target)
        .or_else(|| files.iter().position(|(name, _)| name.rsplit('/').next() == Some(basename)))
        .or_else(|| {
            files.iter().position(|(name, _)| {
                let file = name.rsplit('/').next().unwrap_or(name);
                file.rsplit_once('.').map(|(stem, _)| stem) == Some(basename)
            })
        })
}

fn has_heading(text: &str, heading: &str) -> bool {
    text.lines().any(|line| {
        let trimmed = line.trim_start();
        trimmed.starts_with('#') && trimmed.trim_start_matches('#').trim() == heading.trim()
    })
}

fn count(conn: &Connection, table: &str) -> i64 {
    conn.query_row(&format!("SELECT count(*) FROM {table}"), [], |r| r.get(0))
        .unwrap()
}

fn source_names(conn: &Connection) -> BTreeSet<String> {
    let mut stmt = conn.prepare("SELECT original_name FROM sources").unwrap();
    let rows = stmt
        .query_map([], |r| r.get::<_, String>(0))
        .unwrap()
        .map(|r| r.unwrap())
        .collect();
    rows
}

#[test]
fn obsidian_vault_roundtrip_keeps_bytes_names_and_links_and_states_the_gaps() {
    let files = vault_files();
    let names: BTreeSet<String> = files.iter().map(|(name, _)| name.clone()).collect();
    assert_eq!(
        names,
        EXPECTED_FILES.iter().map(|n| n.to_string()).collect::<BTreeSet<_>>(),
        "the fixture changed; update this test and its PROVENANCE together"
    );

    // (2) the fixture is a real vault: every internal link resolves inside it
    let mut internal = 0;
    let mut external = 0;
    for (name, bytes) in files.iter().filter(|(name, _)| name.ends_with(".md")) {
        let text = text_of(bytes);
        for raw in wiki_links(&text) {
            let (target, anchor) = split_target(&raw);
            let index = resolve(&files, target)
                .unwrap_or_else(|| panic!("[[{raw}]] in {name} does not resolve inside the vault"));
            let (resolved_name, resolved_bytes) = &files[index];
            match anchor {
                Some(block) if block.starts_with('^') => {
                    let needle = block.to_string();
                    assert!(
                        text_of(resolved_bytes).contains(&needle),
                        "[[{raw}]] in {name} points at block {needle} which is not in {resolved_name}"
                    );
                }
                Some(heading) if !heading.is_empty() => {
                    assert!(
                        has_heading(&text_of(resolved_bytes), heading),
                        "[[{raw}]] in {name} points at heading '{heading}' which is not in {resolved_name}"
                    );
                }
                _ => {}
            }
            internal += 1;
        }
        for target in markdown_links(&text) {
            if target.starts_with("http://") || target.starts_with("https://") {
                external += 1;
                continue;
            }
            assert!(
                resolve(&files, &target).is_some(),
                "markdown link '{target}' in {name} does not resolve inside the vault"
            );
            internal += 1;
        }
    }
    assert!(internal >= 8, "the fixture must exercise real samples, saw {internal} internal links");
    assert_eq!(
        external, 1,
        "exactly one external link must stay in the fixture to prove external targets are not required to resolve"
    );

    // (1) import, export, restore into a fresh workspace
    let dir = tempfile::tempdir().unwrap();
    let db = dir.path().join("vault.sqlite");
    let archive = dir.path().join("archive");
    let mut conn = init_workspace(db.to_str().unwrap()).unwrap();
    let mut digests: BTreeMap<String, String> = BTreeMap::new();
    for (name, bytes) in &files {
        match source::import_source(&mut conn, bytes, name, None).unwrap() {
            ImportOutcome::Imported { sha256, .. } => {
                digests.insert(name.clone(), sha256);
            }
            ImportOutcome::Duplicate { .. } => panic!("{name} collided with another fixture file"),
        }
    }
    assert_eq!(digests.len(), files.len(), "every vault file is its own source");
    assert_eq!(source_names(&conn), names, "the vault paths are what the source names say");
    drop(conn);

    let manifest = archeaxis_archive::export_workspace(db.to_str().unwrap(), archive.to_str().unwrap()).unwrap();
    assert_eq!(manifest.tables["sources"].rows as usize, files.len());
    let restored_db = dir.path().join("restored.sqlite");
    archeaxis_archive::restore_workspace(archive.to_str().unwrap(), restored_db.to_str().unwrap()).unwrap();
    let restored = init_workspace(restored_db.to_str().unwrap()).unwrap();

    assert_eq!(source_names(&restored), names, "names survive the archive round-trip");
    for (name, bytes) in &files {
        let digest = &digests[name];
        let after = raw_objects::read(&restored, digest)
            .unwrap_or_else(|e| panic!("{name} did not survive the round-trip: {e}"));
        assert_eq!(&after, bytes, "{name} is not byte-identical after the round-trip");
        assert_eq!(after.len(), bytes.len(), "{name} changed length");
    }

    // (3) links survive as text: the extracted text is the note itself, so an
    // extractor may later re-parse it, but nothing here resolves the graph
    let index_bytes = raw_objects::read(&restored, &digests["notes/index.md"]).unwrap();
    let index_text = text_of(&index_bytes);
    for sample in ["[[atomic]]", "[[atomic#Why this matters]]", "[[atomic#^why-block]]", "![[diagram.png]]"] {
        assert!(index_text.contains(sample), "the link sample {sample} was lost");
    }
    // and the canvas is still a parseable JSON Canvas document
    let canvas: serde_json::Value =
        serde_json::from_slice(&raw_objects::read(&restored, &digests["vault.canvas"]).unwrap()).unwrap();
    assert_eq!(canvas["nodes"].as_array().unwrap().len(), 4);
    assert_eq!(canvas["edges"].as_array().unwrap().len(), 2);

    // (4) the honest half: this round-trip says nothing about the link graph
    assert_eq!(
        count(&restored, "anchors"),
        0,
        "importing a vault must not invent anchors it did not parse"
    );
    let mut stmt = restored
        .prepare(
            "SELECT name FROM sqlite_master WHERE type='table'
             AND (lower(name) LIKE '%link%' OR lower(name) LIKE '%embed%')",
        )
        .unwrap();
    let link_tables: Vec<String> = stmt
        .query_map([], |r| r.get::<_, String>(0))
        .unwrap()
        .map(|r| r.unwrap())
        .collect();
    assert!(
        link_tables.is_empty(),
        "if a link or embed table lands, replace this with a real graph check instead of deleting it: {link_tables:?}"
    );
    assert_eq!(
        attempts::route_for_kind("markdown").map(|route| route.0),
        None,
        "markdown has no dedicated route yet: it travels through the text route"
    );
    assert_eq!(
        attempts::route_for_kind("text").map(|route| route.0),
        Some("text.extract")
    );
    assert_eq!(
        attempts::route_for_kind("canvas").map(|route| route.0),
        None,
        "a canvas has no ingest route: its bytes are custody only"
    );
}
