//! G2: the Obsidian-style link graph in a Markdown note, parsed rather than guessed.
//!
//! `crates/archeaxis-archive/tests/obsidian_vault_roundtrip.rs` states, as a fact rather than a
//! silence, that importing a vault writes no anchors and that no table stores a link or embed
//! relationship: the link text survives inside the note's extracted text, and the **graph** is not
//! absorbed. This module is the parsing half of closing that gap.
//!
//! It is a pure function over text on purpose. It reads no file and touches no store, so it cannot
//! widen the Core's ingestion boundary, which is stated as "Core file ingestion reads only inside the
//! project root". Whatever walks a vault directory does so outside the Core, and the Core's job is to
//! say precisely what a note contains.
//!
//! What is parsed, all of it Obsidian 1.x syntax:
//!
//! * `[[Target]]` - a wiki-link
//! * `[[Target|label]]` - a link with a display label
//! * `[[Target#Heading]]` - a link to a heading inside the target
//! * `[[Target#^block]]` - a link to a block reference
//! * `[[Target#Heading|label]]` - both at once
//! * `![[Target]]` - an embed, which is a different relationship from a link
//! * `![[image.png]]` - an embed of an attachment
//! * `[text](Target.md)` - a Markdown link, kept because a vault may mix the two
//!
//! Deliberately **not** parsed, and named so a reader does not assume them: block references
//! (`^id` on their own line) as *targets they define*, tags, and front-matter fields. A link to a
//! block is recorded as a link whose fragment is a block id; the definition side is not resolved here.

use serde_json::json;

/// One relationship a note declares.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Link {
    /// Whether this is an embed (`![[...]]`) rather than a link. They are different relationships:
    /// a link says "see also", an embed says "this content is part of me".
    pub embed: bool,
    /// The target as written, before any heading or block fragment is separated.
    pub target: String,
    /// The display label, when the link carries one.
    pub label: Option<String>,
    /// A heading name or `^block-id`, when the link points inside the target.
    pub fragment: Option<String>,
    /// Whether the fragment is a block reference rather than a heading.
    pub fragment_is_block: bool,
    /// The syntax that produced it, so a reader can tell a wiki-link from a Markdown one.
    pub syntax: &'static str,
}

impl Link {
    fn to_json(&self) -> serde_json::Value {
        json!({
            "embed": self.embed,
            "target": self.target,
            "label": self.label,
            "fragment": self.fragment,
            "fragment_is_block": self.fragment_is_block,
            "syntax": self.syntax,
            // A vault link is a note-to-note reference, and nothing here claims the target exists:
            // resolving a target is a different job from reading one.
            "resolved": false,
        })
    }
}

/// Parse one `[[...]]` body into its parts. The body is everything between the double brackets.
fn parse_wiki_body(body: &str) -> (String, Option<String>, Option<String>, bool) {
    // `[[Target|label]]`: the label is everything after the first pipe.
    let (head, label) = match body.split_once('|') {
        Some((head, label)) => (head, Some(label.trim().to_string())),
        None => (body, None),
    };
    // `[[Target#fragment]]`: the fragment is everything after the first hash.
    let (target, fragment) = match head.split_once('#') {
        Some((target, fragment)) => {
            let fragment = fragment.trim();
            let is_block = fragment.starts_with('^');
            let value = fragment.trim_start_matches('^').trim().to_string();
            (target.trim().to_string(), Some((value, is_block)))
        }
        None => (head.trim().to_string(), None),
    };
    match fragment {
        Some((value, is_block)) if !value.is_empty() => (target, label, Some(value), is_block),
        _ => (target, label, None, false),
    }
}

/// Every relationship the note declares, in the order they appear.
///
/// Order is kept because a citation that names "the third link" has to mean something.
pub fn links_in(markdown: &str) -> Vec<Link> {
    let bytes: Vec<char> = markdown.chars().collect();
    let mut links = Vec::new();
    let mut index = 0usize;
    while index < bytes.len() {
        // `![[` or `[[`
        let embed = bytes[index] == '!'
            && index + 2 < bytes.len()
            && bytes[index + 1] == '['
            && bytes[index + 2] == '[';
        let plain = bytes[index] == '[' && index + 1 < bytes.len() && bytes[index + 1] == '[';
        if !embed && !plain {
            // A Markdown link `[text](target)`; skipped when it is the head of a wiki-link.
            if bytes[index] == '[' && index + 1 < bytes.len() && bytes[index + 1] != '[' {
                if let Some((link, next)) = markdown_link(&bytes, index) {
                    links.push(link);
                    index = next;
                    continue;
                }
            }
            index += 1;
            continue;
        }
        let start = if embed { index + 3 } else { index + 2 };
        // The body ends at the first `]]`. A nested `[[` inside is not a thing Obsidian writes, and
        // treating it as one would invent structure.
        let mut end = start;
        let mut found = None;
        while end + 1 < bytes.len() {
            if bytes[end] == ']' && bytes[end + 1] == ']' {
                found = Some(end);
                break;
            }
            // A newline inside is not a valid wiki-link; stopping prevents a stray `[[` early in a
            // long file from swallowing everything after it.
            if bytes[end] == '\n' {
                break;
            }
            end += 1;
        }
        let Some(end) = found else {
            index += 1;
            continue;
        };
        let body: String = bytes[start..end].iter().collect();
        let (target, label, fragment, fragment_is_block) = parse_wiki_body(&body);
        if !target.is_empty() {
            links.push(Link {
                embed,
                target,
                label,
                fragment,
                fragment_is_block,
                syntax: "wiki",
            });
        }
        index = end + 2;
    }
    links
}

/// A Markdown inline link starting at `index`, which points at `[`.
fn markdown_link(bytes: &[char], index: usize) -> Option<(Link, usize)> {
    let mut cursor = index + 1;
    let mut depth = 1usize;
    while cursor < bytes.len() && depth > 0 {
        match bytes[cursor] {
            '[' => depth += 1,
            ']' => depth -= 1,
            '\n' => return None,
            _ => {}
        }
        cursor += 1;
    }
    if depth != 0 || cursor >= bytes.len() || bytes[cursor] != '(' {
        return None;
    }
    let label: String = bytes[index + 1..cursor - 1].iter().collect();
    let open = cursor;
    cursor += 1;
    let mut close = None;
    while cursor < bytes.len() {
        if bytes[cursor] == ')' {
            close = Some(cursor);
            break;
        }
        if bytes[cursor] == '\n' {
            return None;
        }
        cursor += 1;
    }
    let close = close?;
    let target: String = bytes[open + 1..close].iter().collect();
    let target = target.trim().to_string();
    // An external URL is not a vault relationship, so it is not a vault link.
    if target.is_empty() || target.contains("://") || target.starts_with("mailto:") {
        return None;
    }
    Some((
        Link {
            embed: false,
            target,
            label: Some(label.trim().to_string()).filter(|value| !value.is_empty()),
            fragment: None,
            fragment_is_block: false,
            syntax: "markdown",
        },
        close + 1,
    ))
}

/// A note's links, plus what this parse does not do.
pub fn note_links(markdown: &str) -> serde_json::Value {
    let links = links_in(markdown);
    let embeds = links.iter().filter(|link| link.embed).count();
    let markdown_links = links
        .iter()
        .filter(|link| link.syntax == "markdown")
        .count();
    json!({
        "schema": "archeaxis.vault-links/v1",
        "count": links.len(),
        "embeds": embeds,
        "markdown_syntax": markdown_links,
        "links": links.iter().map(Link::to_json).collect::<Vec<_>>(),
        "not_done_here": [
            "resolving a target: nothing checks that the note a link names exists",
            "persisting the graph: no table stores these relationships yet, which is the gap the vault round-trip test names",
            "block reference definitions: a `^id` line is not recorded as a target",
            "tags and front-matter fields, which are neither links nor embeds",
        ],
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn a_plain_wiki_link_is_a_relationship() {
        let links = links_in("see [[Knowledge Version]] for the rest");
        assert_eq!(links.len(), 1);
        assert_eq!(links[0].target, "Knowledge Version");
        assert!(!links[0].embed);
        assert_eq!(links[0].label, None);
        assert_eq!(links[0].fragment, None);
    }

    #[test]
    fn a_label_is_kept_apart_from_the_target() {
        let links = links_in("[[Evidence Anchor|the anchor concept]]");
        assert_eq!(links[0].target, "Evidence Anchor");
        assert_eq!(links[0].label.as_deref(), Some("the anchor concept"));
    }

    #[test]
    fn a_heading_fragment_is_not_a_block_fragment() {
        let heading = links_in("[[Note#Heading]]");
        assert_eq!(heading[0].target, "Note");
        assert_eq!(heading[0].fragment.as_deref(), Some("Heading"));
        assert!(!heading[0].fragment_is_block);

        let block = links_in("[[Note#^abc123]]");
        assert_eq!(block[0].fragment.as_deref(), Some("abc123"));
        assert!(block[0].fragment_is_block);
    }

    #[test]
    fn a_fragment_and_a_label_can_appear_together() {
        let links = links_in("[[Note#Heading|see here]]");
        assert_eq!(links[0].target, "Note");
        assert_eq!(links[0].fragment.as_deref(), Some("Heading"));
        assert_eq!(links[0].label.as_deref(), Some("see here"));
    }

    #[test]
    fn an_embed_is_a_different_relationship_from_a_link() {
        // A link says "see also"; an embed says "this is part of me". Collapsing them would lose the
        // distinction the vault is expressing.
        let links = links_in("![[diagram.png]] and [[diagram.png]]");
        assert_eq!(links.len(), 2);
        assert!(links[0].embed, "the first is an embed");
        assert!(!links[1].embed, "the second is a link");
        assert_eq!(links[0].target, links[1].target);
    }

    #[test]
    fn a_markdown_link_is_kept_because_a_vault_may_mix_the_two() {
        let links = links_in("see [the note](notes/atomic.md) for detail");
        assert_eq!(links.len(), 1);
        assert_eq!(links[0].syntax, "markdown");
        assert_eq!(links[0].target, "notes/atomic.md");
        assert_eq!(links[0].label.as_deref(), Some("the note"));
    }

    #[test]
    fn an_external_url_is_not_a_vault_relationship() {
        let links = links_in("[docs](https://example.com/page) and [mail](mailto:a@b.c)");
        assert!(links.is_empty(), "{links:?}");
    }

    #[test]
    fn order_is_kept_because_a_citation_may_name_the_nth_link() {
        let links = links_in("[[one]] then [[two]] then [[three]]");
        let targets: Vec<&str> = links.iter().map(|link| link.target.as_str()).collect();
        assert_eq!(targets, vec!["one", "two", "three"]);
    }

    #[test]
    fn an_unterminated_bracket_does_not_swallow_the_rest_of_the_file() {
        // A stray `[[` early in a long note must not make everything after it one link.
        let links = links_in("[[unclosed\n\nsome text\n\n[[closed]]");
        assert_eq!(links.len(), 1, "{links:?}");
        assert_eq!(links[0].target, "closed");
    }

    #[test]
    fn an_empty_target_is_not_a_link() {
        assert!(links_in("[[]] and [[|label]]").is_empty());
    }

    #[test]
    fn the_document_says_what_it_does_not_do() {
        let document = note_links("[[a]]");
        assert_eq!(document["count"], 1);
        let gaps = document["not_done_here"].as_array().unwrap();
        // persisting the graph is the named gap, and it must stay named
        assert!(
            gaps.iter()
                .any(|gap| gap.as_str().unwrap().contains("persisting the graph"))
        );
        assert!(
            gaps.iter()
                .any(|gap| gap.as_str().unwrap().contains("resolving a target"))
        );
        // nothing claims a target was resolved
        assert_eq!(document["links"][0]["resolved"], false);
    }
}
