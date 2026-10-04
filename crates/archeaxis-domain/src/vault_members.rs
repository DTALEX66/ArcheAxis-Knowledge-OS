//! G2: which parts of a vault are the user's knowledge, and which are the application's own state.
//!
//! A vault is not just notes. It carries an `.obsidian/` directory holding the app's configuration,
//! its workspace layout, its plugin cache and its theme; attachments that are content; and files that
//! are neither. Nothing in the repository distinguishes them today, so a directory walk treats all of
//! it as importable material — and `.obsidian/workspace.json` is the file that records which notes a
//! person had open, with **absolute paths on that person's disk**. Importing it would put a private
//! path into the canonical store as if it were knowledge.
//!
//! This module classifies the members of a vault **without reading any of them**. It takes relative
//! paths and answers what each one is and what should happen to it. That is deliberate:
//!
//! * the Core does not walk a directory (its ingestion reads only inside the project root), so
//!   whatever enumerates a vault does so outside the Core and hands the list over;
//! * a classifier over names cannot leak the contents of the files it classifies;
//! * and the safety rules below are checkable without a filesystem, so they are checked here rather
//!   than hoped for in a walker.
//!
//! What is **not** done here, and is named rather than left as a silence: nothing here reads
//! `.obsidian/app.json` to learn a person's settings, and nothing resolves a vault's attachment
//! folder setting. Classification is about names, not about interpreting the vault's configuration.

use serde_json::json;

/// What a vault member is.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Role {
    /// A Markdown note: the user's knowledge, and the only thing links are parsed from.
    Note,
    /// The application's own configuration directory and its contents.
    AppConfig,
    /// A file the user attached: images, audio, PDFs and the like.
    Attachment,
    /// A JSON Canvas document.
    Canvas,
    /// Something in the vault that this classifier does not claim to know.
    Unknown,
}

impl Role {
    fn as_str(self) -> &'static str {
        match self {
            Role::Note => "note",
            Role::AppConfig => "app_config",
            Role::Attachment => "attachment",
            Role::Canvas => "canvas",
            Role::Unknown => "unknown",
        }
    }

    /// Whether the Core should take this member in as material.
    fn disposition(self) -> &'static str {
        match self {
            Role::Note => "import_as_knowledge",
            // Not a judgement about value - the user's own settings are theirs. It is that this is the
            // application's state, not the user's knowledge, and importing it would file a workspace
            // layout as a claim about the world.
            Role::AppConfig => "exclude_application_state",
            Role::Attachment => "import_as_source",
            Role::Canvas => "import_as_source",
            // Named rather than guessed: a classifier that called an unrecognised file "attachment"
            // would quietly import whatever it did not understand.
            Role::Unknown => "needs_a_human_decision",
        }
    }
}

/// One member of a vault, classified.
fn classify_one(path: &str) -> (Role, Option<&'static str>) {
    let lower = path.to_ascii_lowercase();
    let segments: Vec<&str> = lower.split('/').collect();
    // Obsidian's own directory. Checked anywhere in the path, because a vault may be nested inside
    // another directory and the config directory travels with it.
    if segments.iter().any(|segment| *segment == ".obsidian") {
        return (
            Role::AppConfig,
            Some("this is the application's own configuration directory"),
        );
    }
    // `.trash` is where Obsidian moves deleted notes. They are the user's, but they are deleted ones,
    // and importing them would resurrect material the person removed.
    if segments.iter().any(|segment| *segment == ".trash") {
        return (
            Role::AppConfig,
            Some("this is the vault's trash, whose contents the person deleted"),
        );
    }
    if let Some(name) = segments.last() {
        if name.ends_with(".md") || name.ends_with(".markdown") {
            // A file inside the config directory was already returned above.
            return (Role::Note, None);
        }
        if name.ends_with(".canvas") {
            return (Role::Canvas, None);
        }
        if is_attachment(name) {
            return (Role::Attachment, None);
        }
    }
    (Role::Unknown, None)
}

/// Extensions this project already has a route for, so calling one an attachment is a statement about
/// the pipeline rather than a guess about the file.
fn is_attachment(name: &str) -> bool {
    const KNOWN: &[&str] = &[
        // images, the OCR and caption routes
        "png", "jpg", "jpeg", "gif", "bmp", "webp", "tif", "tiff", "heic",
        // documents, the pdf and office routes
        "pdf", "docx", "doc", "xlsx", "xls", "pptx", "ppt", "odt", "ods", "odp",
        // archive and web
        "zip", "tar", "gz", "7z", "rar", "html", "htm", "mhtml",
        // media, the probe and transcribe routes
        "mp3", "wav", "m4a", "flac", "ogg", "mp4", "mov", "mkv", "webm", "avi",
        // subtitles
        "srt", "vtt", "ass", "ssa",
        // plain text is material too, and the text route serves it
        "txt", "csv", "tsv", "json", "yaml", "yml", "rtf",
    ];
    match name.rsplit_once('.') {
        Some((_, extension)) => KNOWN.contains(&extension),
        None => false,
    }
}

/// The safety problems a member path can have, checked before anything is read.
///
/// These are the rules that keep a walk inside the directory a person chose. They are checked here
/// because a walker that had to re-derive them would eventually get one wrong, and the consequence of
/// getting one wrong is reading a file the person did not offer.
pub fn path_problems(path: &str) -> Vec<&'static str> {
    let mut problems = Vec::new();
    if path.trim().is_empty() {
        problems.push("empty path");
        return problems;
    }
    // An absolute path is not a member of anything; it is a location.
    if path.starts_with('/') || path.starts_with('\\') {
        problems.push("absolute path");
    }
    // Windows drive and UNC forms.
    let bytes: Vec<char> = path.chars().collect();
    if bytes.len() >= 2 && bytes[1] == ':' && bytes[0].is_ascii_alphabetic() {
        problems.push("absolute path with a drive letter");
    }
    if path.starts_with("//") || path.starts_with("\\\\") {
        problems.push("UNC path");
    }
    // A traversal segment. Checked per segment rather than by substring, so a file legitimately named
    // `..notes.md` is not refused for containing dots.
    for segment in path.split(['/', '\\']) {
        if segment == ".." {
            problems.push("parent-directory traversal");
            break;
        }
    }
    if path.contains('\0') {
        problems.push("NUL byte in path");
    }
    problems
}

/// Classify a vault's members.
///
/// `members` are relative paths as the walker found them. Every member is reported, including one
/// whose path is unsafe, so a caller can see what it offered rather than only what was refused.
pub fn classify_members(members: &[String]) -> serde_json::Value {
    let mut classified = Vec::new();
    let mut counts: std::collections::BTreeMap<String, i64> = std::collections::BTreeMap::new();
    let mut unsafe_members = Vec::new();

    for member in members {
        let problems = path_problems(member);
        let (role, reason) = if problems.is_empty() {
            classify_one(member)
        } else {
            // An unsafe path is not classified at all: deciding what an out-of-tree path *is* would
            // suggest it might be read, and it will not be.
            (Role::Unknown, Some("the path itself is not safe to read"))
        };
        if !problems.is_empty() {
            unsafe_members.push(json!({"member": member, "problems": problems}));
        }
        *counts.entry(role.as_str().to_string()).or_insert(0) += 1;
        classified.push(json!({
            "member": member,
            "role": role.as_str(),
            "disposition": if problems.is_empty() { role.disposition() } else { "refuse" },
            "reason": reason,
            "problems": problems,
        }));
    }

    let importable = classified
        .iter()
        .filter(|entry| {
            matches!(
                entry["disposition"].as_str(),
                Some("import_as_knowledge") | Some("import_as_source")
            )
        })
        .count();
    let excluded = classified
        .iter()
        .filter(|entry| entry["disposition"] == "exclude_application_state")
        .count();
    let undecided = classified
        .iter()
        .filter(|entry| entry["disposition"] == "needs_a_human_decision")
        .count();

    json!({
        "schema": "archeaxis.vault-members/v1",
        "count": classified.len(),
        "counts": counts,
        "importable": importable,
        "excluded_as_application_state": excluded,
        "needing_a_human_decision": undecided,
        "unsafe": unsafe_members,
        "members": classified,
        "not_done_here": [
            "reading .obsidian/app.json or any other configuration: classification is about names, so nothing here interprets a person's settings",
            "walking a directory: these are paths the caller enumerated, handed over as text",
            "resolving a vault's attachment-folder setting, which would change how a target is found but not what a member is",
            "deciding what any unrecognised member is: it is reported, not guessed",
        ],
    })
}

#[cfg(test)]
mod classifier_tests {
    use super::*;

    fn members(paths: &[&str]) -> serde_json::Value {
        classify_members(&paths.iter().map(|p| p.to_string()).collect::<Vec<_>>())
    }

    fn role_of(document: &serde_json::Value, member: &str) -> String {
        document["members"]
            .as_array()
            .unwrap()
            .iter()
            .find(|entry| entry["member"] == member)
            .unwrap_or_else(|| panic!("{member} was not reported"))["role"]
            .as_str()
            .unwrap()
            .to_string()
    }

    #[test]
    fn a_note_is_knowledge_and_a_markdown_file_elsewhere_is_still_a_note() {
        let document = members(&["notes/atomic.md", "README.markdown"]);
        assert_eq!(role_of(&document, "notes/atomic.md"), "note");
        assert_eq!(role_of(&document, "README.markdown"), "note");
        assert_eq!(document["importable"], 2);
    }

    #[test]
    fn the_obsidian_directory_is_application_state_not_knowledge() {
        // The reason this matters: workspace.json records a person's open panes with absolute paths.
        let document = members(&[
            ".obsidian/workspace.json",
            ".obsidian/app.json",
            ".obsidian/plugins/dataview/main.js",
        ]);
        for member in [".obsidian/workspace.json", ".obsidian/app.json"] {
            assert_eq!(role_of(&document, member), "app_config", "{member}");
        }
        assert_eq!(
            role_of(&document, ".obsidian/plugins/dataview/main.js"),
            "app_config"
        );
        assert_eq!(document["importable"], 0);
        assert_eq!(document["excluded_as_application_state"], 3);
    }

    #[test]
    fn obsidian_config_nested_inside_a_vault_is_still_config() {
        // A vault does not have to be at the top of what a person chose.
        let document = members(&["my-vault/.obsidian/appearance.json"]);
        assert_eq!(
            role_of(&document, "my-vault/.obsidian/appearance.json"),
            "app_config"
        );
    }

    #[test]
    fn the_trash_is_excluded_because_the_person_deleted_it() {
        let document = members(&[".trash/deleted-note.md"]);
        assert_eq!(role_of(&document, ".trash/deleted-note.md"), "app_config");
        assert_eq!(document["excluded_as_application_state"], 1);
    }

    #[test]
    fn plugins_are_not_imported_as_knowledge_even_when_they_are_javascript() {
        // Without the config rule this would be `unknown`; the rule is what makes it excluded.
        let document = members(&[".obsidian/plugins/calendar/main.js"]);
        assert_eq!(
            role_of(&document, ".obsidian/plugins/calendar/main.js"),
            "app_config"
        );
    }

    #[test]
    fn an_attachment_is_a_source_and_a_canvas_is_a_canvas() {
        let document = members(&[
            "attachments/diagram.png",
            "vault.canvas",
            "audio/lesson.mp3",
        ]);
        assert_eq!(role_of(&document, "attachments/diagram.png"), "attachment");
        assert_eq!(role_of(&document, "vault.canvas"), "canvas");
        assert_eq!(role_of(&document, "audio/lesson.mp3"), "attachment");
        assert_eq!(document["importable"], 3);
    }

    #[test]
    fn an_unrecognised_file_is_reported_rather_than_guessed() {
        // Calling this an attachment would import whatever the classifier did not understand.
        let document = members(&["somedir/thing.frobnicate"]);
        assert_eq!(role_of(&document, "somedir/thing.frobnicate"), "unknown");
        assert_eq!(document["needing_a_human_decision"], 1);
        assert_eq!(document["importable"], 0);
    }

    #[test]
    fn an_absolute_path_is_refused_and_not_classified() {
        let document = members(&["C:/Users/somebody/notes.md"]);
        assert_eq!(document["unsafe"].as_array().unwrap().len(), 1);
        let entry = &document["members"][0];
        assert_eq!(entry["disposition"], "refuse");
        assert!(
            entry["problems"]
                .as_array()
                .unwrap()
                .iter()
                .any(|p| p.as_str().unwrap().contains("drive letter"))
        );
    }

    #[test]
    fn a_unix_absolute_path_is_refused() {
        let document = members(&["/etc/passwd"]);
        assert_eq!(document["members"][0]["disposition"], "refuse");
    }

    #[test]
    fn a_traversal_path_is_refused() {
        let document = members(&["notes/../../outside.md"]);
        assert_eq!(document["members"][0]["disposition"], "refuse");
        assert!(
            document["members"][0]["problems"]
                .as_array()
                .unwrap()
                .iter()
                .any(|p| p.as_str().unwrap().contains("traversal"))
        );
    }

    #[test]
    fn a_file_legitimately_named_with_dots_is_not_refused() {
        // The traversal rule is per segment, so a name that merely contains dots still works.
        let document = members(&["notes/..notes.md"]);
        assert_eq!(role_of(&document, "notes/..notes.md"), "note");
        assert_eq!(document["unsafe"].as_array().unwrap().len(), 0);
    }

    #[test]
    fn a_unc_path_is_refused() {
        let document = members(&["//server/share/notes.md"]);
        assert_eq!(document["members"][0]["disposition"], "refuse");
    }

    #[test]
    fn every_member_is_reported_even_the_refused_ones() {
        // A caller has to be able to see what it offered, not only what survived.
        let document = members(&["good.md", "C:/bad.md", "../worse.md"]);
        assert_eq!(document["count"], 3);
        assert_eq!(document["members"].as_array().unwrap().len(), 3);
        assert_eq!(document["unsafe"].as_array().unwrap().len(), 2);
    }

    #[test]
    fn the_document_says_what_it_does_not_do() {
        let document = members(&[".obsidian/app.json"]);
        let gaps = document["not_done_here"].as_array().unwrap();
        assert!(
            gaps.iter()
                .any(|g| g.as_str().unwrap().contains("reading .obsidian/app.json"))
        );
        assert!(
            gaps.iter()
                .any(|g| g.as_str().unwrap().contains("walking a directory"))
        );
    }
}
