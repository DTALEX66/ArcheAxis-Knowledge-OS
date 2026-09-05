# Knowledge, evidence and verification authority

## Core rule

Evidence is not the admission ticket for knowledge. Personal notes,
definitions, opinions, questions, observations, hypotheses, rumor reports and
forecasts may be saved immediately. The system evaluates them on independent
axes and never collapses those axes into a synthetic `truth_score`.

Machine processing cannot promise zero errors. A worker emits candidates only.
High-precision modes may abstain; an unreviewed candidate never becomes
user-accepted knowledge.

The closed Contract v1 `knowledge_type` vocabulary is:

`PERSONAL_DEFINITION | NOTE | OBSERVATION | OPINION | QUESTION | HYPOTHESIS |
RUMOR_REPORT | FORECAST | FACTUAL_CLAIM`

Law, standards and policies are scoped factual claims whose source version,
issuer, jurisdiction and effective dates carry authority; they are not a tenth
knowledge type. The machine authority for every enum in this document is
`packages/contracts/v1/assessment-vocabulary.schema.json`.

## Objects and invariants

- `KnowledgeItem` / immutable `KnowledgeRevision`: user-visible content.
- `AtomicClaim` / immutable `ClaimRevision`: optional, separately assessable
  statements extracted from a revision.
- `SourceRecord` / immutable `SourceSnapshot`: source identity versus what was
  actually observed at a time.
- `Anchor`: exact position in a snapshot, not merely a changeable URL.
- `TransformRun`: model/tool/prompt/config/input/output hashes for a conversion.
- `EvidenceLink`: SUPPORTS, REFUTES, QUALIFIES, CONTEXTUALIZES,
  REPORTS_ASSERTION, TESTS, MENTIONS or NO_BEARING.
- `VerificationRun` and immutable `CoverageReceipt`: what was searched, what
  failed, how results were deduplicated and why the run stopped.
- `Assessment`: a scoped conclusion for one ClaimRevision and one run.
- `HumanDecision`: accept, reject, edit or override; separate from evidence.
- `MetricDefinition` / `MetricMeasurement`: versioned formula versus an actual
  measurement on a named gold set.

Evidence binds to `ClaimRevision + SourceSnapshot + Anchor`. Source authority
is claim-relative: a company release is primary evidence that the company made
an announcement, not independent proof that its performance claim is true.

## Orthogonal status vocabularies

`review_status`:

`DRAFT | MACHINE_CANDIDATE | NEEDS_REVIEW | USER_ACCEPTED | USER_REJECTED | SUPERSEDED`

`evidence_status`:

`NOT_APPLICABLE | UNASSESSED | UNSOURCED | SEARCHED_NO_DECISIVE_EVIDENCE | PARTIALLY_SUPPORTED | SUPPORTED | CONFLICTED | REFUTED | INCONCLUSIVE | STALE`

`test_status`:

`NOT_APPLICABLE | NOT_TESTED | TEST_PLAN_EXISTS | IN_PROGRESS | PASSED | FAILED | MIXED | INCONCLUSIVE | NON_REPRODUCIBLE | OBSERVATIONAL_ONLY`

`rumor_status`:

`NOT_APPLICABLE | REPORTED_UNVERIFIED | SAME_ORIGIN_REPEATED | INDEPENDENTLY_CORROBORATED | OFFICIALLY_DENIED | DISPUTED | DEBUNKED | EVENT_CONFIRMED | UNRESOLVED`

`forecast_status`:

`NOT_APPLICABLE | OPEN | CONDITIONAL | DUE_FOR_RESOLUTION | RESOLVED_TRUE | RESOLVED_FALSE | PARTIALLY_RESOLVED | VOIDED | EXPIRED_UNRESOLVABLE`

`use_status`:

`INBOX | DRAFT | REVIEWED | DECISION_GRADE | PUBLISHED`

USER_ACCEPTED is a retention/review decision. NOT_TESTED is not a rumor.
OFFICIALLY_DENIED is evidence, not automatic refutation. Before its resolution
window closes, a forecast is OPEN, not true or false.

## Source snapshots and anchors

A snapshot records request/final/canonical URI, capture and observed times,
media type, language, HTTP metadata, body and normalized-text hashes, storage
reference, rights basis and fetcher version. Storage mode is one of:

`FULL | EXCERPT_ONLY | METADATA_ONLY | HASH_ONLY | BLOCKED`

Personal noncommercial research does not cancel copyright, site terms, robots
policy, model licences or redistribution restrictions. When full retention is
not allowed, preserve lawful metadata, hashes, limited excerpts and location.

Text anchors combine exact/prefix/suffix with `[start,end)` code-point offsets
over NFC/LF text. PDF adds a zero-based page, normalized quads and page-text
hash. Resolution is explicit: `UNRESOLVED | EXACT | RELOCATED | AMBIGUOUS |
ORPHANED`. `FUZZY_TEXT` is a versioned resolution method, not a result state;
no fuzzy relocation is silently presented as exact.

## v0.2 verification pipeline

1. Atomize and scope the claim (time, place, version, subject, conditions).
2. Generate evidence needs and query families.
3. Search original records, independent checks and disconfirming evidence.
4. Snapshot lawful representations and extract anchored passages.
5. Deduplicate canonical URL and content.
6. Group `DocumentCluster`, `AssertionOriginGroup` and
   `EvidenceGenerationGroup`; provider count is not evidence independence.
7. Classify relation, directness and scope fit; surface conflicts.
8. Emit a CoverageReceipt and require human review for consequential claims.

The receipt lists providers/index families, languages, time windows, planned
and executed query families, raw/retrieved/blocked/failed counts, inaccessible
sources, unresolved gaps, dedup counts, independent-generation counts, model
and prompt hashes, snapshots and stop reason. It may say
`PLANNED_COMPLETE | PARTIAL | INSUFFICIENT`; it must not emit an opaque
`coverage_score=87` or claim to have searched "the whole web".

`receipt_payload_sha256` is the SHA-256 of RFC 8785 canonical JSON with only the
`receipt_payload_sha256` member omitted. This exclusion is part of schema v1
and avoids a self-referential digest; the full profile is `AAK-JCS-1`.

## Accuracy and abstention

Measure every transformation separately. At minimum:

| Stage | Metrics |
|---|---|
| byte fidelity | SHA-256 and byte round-trip |
| OCR | CER, WER and error classes |
| anchor | exact/relocated/ambiguous/orphaned rate, method and PDF bbox IoU |
| claim extraction | span exact match, precision, recall, F1 |
| search | Recall@k, MRR, nDCG@k, primary-record recall |
| stance | per-class precision/recall/F1 |
| citations | citation precision and evidence-completeness recall |
| forecast | Brier score and calibration after resolution |
| selective automation | precision-at-coverage and abstention rate |

Every displayed measurement includes task definition, gold-set version,
sample size, language/file/domain slice, model/config/prompt versions, date,
point estimate, 95% interval and error categories. Without a labelled gold set,
the UI says `UNMEASURED`; model confidence never substitutes for accuracy.

## Version boundary

v0.1 implements the objects, orthogonal statuses, immutable snapshot/anchor,
manual evidence links, candidate review, transformation receipts, FTS,
restart/export/restore and a reserved CoverageReceipt schema/table. It does not
automatically crawl or decide truth.

v0.2 adds Provider Registry, claim-aware query planning, original/independent/
disconfirming search, rights-aware snapshots, origin/independence grouping,
stance/conflict/staleness analysis, CoverageReceipt and a versioned quality
dashboard.

Before v0.2 implementation, run three bounded spikes: real PDF/Markdown/dynamic
page anchor resolution; 30–50 real claims for provider/origin dedup; and the
first human-labelled gold set for baseline precision/recall.

Semantic references: W3C Web Annotation and PROV-O, W3C Data Quality
Vocabulary, RFC 3986 URI normalization, RFC 8785 JSON canonicalization and the
NIST AI RMF measurement guidance.
