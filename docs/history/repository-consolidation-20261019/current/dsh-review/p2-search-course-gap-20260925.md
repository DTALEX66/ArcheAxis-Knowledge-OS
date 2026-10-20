# DP-NF-04 · P2 Search / General Course gap audit

- task_id: `DP-NF-04`
- baseline_sha: `a9ead3e1597808ca751c6ccec1dba27bcfff5b4b`
- baseline_tree: `ce69abf1493481591534979be1223b1a447fc9bb`
- branch: `codex/dp-nf-04-20260925`
- status: **`PROPOSAL / NOT_IMPLEMENTED`** — the read-only conservation below is complete; the deeper
  contract-gap hunt was **`NOT_EXECUTED`** (reason in §4)
- evidence class: `STRUCTURAL / READ-ONLY`

## 1. Scope actually covered

I read `crates/archeaxis-domain/src/search.rs` in full and enumerated the search tests. That is the
part of this card that could be completed inside the time available; the General Course half was not
opened. This section is a conservation note, not the full audit the card asks for.

## 2. Verified current state of Search (read from source)

`crates/archeaxis-domain/src/search.rs` (165 lines) implements exactly **two** retrieval paths, both
FTS5, both rebuilt per query:

| Surface | Index | Returned tuple | Notes |
| --- | --- | --- | --- |
| `search()` (knowledge) | `knowledge_fts(body, knowledge_id UNINDEXED, status UNINDEXED)` | `(knowledge_id, status, substr(body,1,60))` | `reindex(conn)?` runs on **every** query — the source comment says "Day-0: rebuild before query (small data; triggers land in a later slice)" |
| `search_transforms()` (extracted text) | `transform_fts(text, transform_id UNINDEXED, source_id UNINDEXED, engine UNINDEXED)` | `(transform_id, source_id, engine, substr(text,1,60))` | `reindex_transforms(conn)?` on every query, same Day-0 pattern |

Both use `WHERE … MATCH ?1 ORDER BY rank LIMIT ?2`.

**Boundary statements that must be preserved:**

1. **This is FTS only.** There is no embedding, no vector index, no reranker, no graph, no hybrid
   path anywhere in this module. Any P2 claim resting on "search works" must be read as *lexical*
   retrieval only.
2. **The module documents its own non-claim.** The `search_transforms` doc comment states the result
   is "retrieval of *extracted text*, not a claim that the text is knowledge: type, evidence and
   qualification remain separate semantics."
3. **`ORDER BY rank` is FTS5's BM25-derived rank**, not a calibrated relevance score, and the returned
   field is a 60-character snippet head (`substr(text,1,60)`), not a scored document. No score is
   exposed to callers at all.
4. **Rebuild-per-query is an O(index) cost on every search.** Correct for small data, explicitly
   acknowledged as a Day-0 placeholder; it is a scalability debt, not a correctness bug.

## 3. Test coverage observed (file-level; not executed here)

`crates/archeaxis-domain/tests/search_transforms.rs` is the only dedicated search test file
(1,873 bytes, i.e. small). The DP-NF-05 subagent independently ran the domain suite in its own
worktree and reported `search_transforms` **1 passed**. I did not re-run it; treat that as second-hand.

## 4. Why the deeper hunt is `NOT_EXECUTED`

The card asks to find "one query/course contract gap that can be closed by narrow, locally
verifiable RED→GREEN work", and explicitly permits stopping with a `PROPOSAL/NOT_IMPLEMENTED` note
when no uncontroversial small loop exists. Two honest reasons for stopping here:

1. **Budget**: I did not open `CourseManifest` / General-course implementation or its tests, so I
   cannot claim any finding about them. Reporting a course gap without reading the course code would
   be exactly the inference this task pack forbids.
2. **The one Search gap already in evidence is not a code bug to fix here.** At the committed
   baseline, `backup_safety`'s `verify_counts_rejects_sqlite_integrity_failure_even_when_counts_match`
   documents a contract the implementation does not honour (see the NF handoff, finding
   **NF-F1**). That is a *documented-vs-implemented mismatch*, and it sits in the backup path, not in
   search. Closing it needs an owner decision about which side is wrong — precisely the situation the
   card says to hand back as a proposal rather than implement.

## 5. Non-claims

- No FTS hit is described here as embedding, reranker, vector or graph quality.
- No static fixture is described as a running course.
- No model or provider was added, no embedding/reranker code written, no learning UI touched, no
  `CourseManifest` field invented.
- P2 remains **`TESTED_LOCAL_PARTIAL`**; this note does not change it.
- No test was executed for this note.
