# DeepTutor 1.7.1 teaching-feedback rules

This is an isolated, finite execution of the original teaching feedback rules.
It updates a caller-provided profile in memory and produces the original
objective-focused teaching guidance. It does not start the DeepTutor server,
ask a model, call a tool, read a conversation archive, open a database, contact
Core, record a review, or award mastery. No state survives worker exit.

## Source manifest

The Owner-provided archive is
`.project-local/archives/owner-inputs/20261101-learning-platform-sources/DeepTutor-1.7.1.zip`,
SHA-256 `9614f50cfe2cef476c25ad378631f5a5d15a7c0f3f54ef1fa3180c8f41286262`.
These members are preserved as exact bytes and checked before use:

| Preserved path | Original archive path | Bytes | SHA-256 |
| --- | --- | ---: | --- |
| `upstream/teaching.py` | `deeptutor/learning/teaching.py` | 8,374 | `79839b2d29c16146ba4ca6eba438941eacdd8cef2920ebca81e8541305013b4b` |
| `upstream/learning_models.py` | `deeptutor/learning/models.py` | 31,784 | `97d4cd701700c31aaf421900fa3b403ac1b5fe334e70d884a5159d998c4b8507` |

The shared `LICENSE` is the upstream Apache-2.0 license, SHA-256
`cd2f54e1e5066644023203dcbd956776a9f4ef6eb8b6225afe1ffa2d380fede4`.
Only the original classes `TeachingPreference`, `TeachingObservation`,
`LearnerProfile`, `TeachingUpdate` and functions `parse_teaching_updates`,
`apply_teaching_updates`, `teaching_guidance` are selected from their AST and
executed. The upstream modules' imports and top-level code are not executed.
The worker checks source length, SHA and observed file/ancestor identities;
these checks are not an OS sandbox or a proof against every filesystem race.

The project declares `pydantic>=2.0`; the locally observed environment has
Pydantic 2.13.4 and pydantic-core 2.46.4, whose installed distribution metadata
declares MIT. A missing or incompatible dependency returns `UNAVAILABLE`;
there is no download or substitute. This is not a complete packaging,
distribution, or license audit.

## Private request and result

Invoke the worker as a dedicated process using the project Python with `-I -B`,
a restricted environment and a caller-owned timeout. It accepts one UTF-8 JSON
request of at most 128 KiB and requires EOF; output is at most 192 KiB. A
missing dependency or source is `UNAVAILABLE`; malformed input or rejected
updates are `INVALID_REQUEST`. Error receipts use fixed codes and do not include
request IDs, input content or Pydantic exception text. The caller must capture
and discard bounded stderr rather than log it, because interpreter or library
diagnostics outside the worker's control can contain private material. A
deadline, process-tree cleanup and OS isolation are responsibilities of the
calling host and are not established by this file.

The request schema is `archeaxis.deeptutor-teaching-feedback/v1` and requires
exactly these fields:

* `request_id`, `session_id`, and `turn_id`: nonempty ASCII identifiers using
  letters, digits, `_` or `-`, at most 128 characters; they are caller claims.
* `profile`: a JSON object containing only the original `LearnerProfile`
  fields. Existing teaching preference and observation records must contain
  their original `updated_at`; other optional original fields may be omitted
  and receive upstream defaults. No supplied field may be silently dropped or
  changed by model validation.
* `current_message`: the specific caller-provided learner message; no earlier
  messages are fetched. At most 16,384 UTF-8 bytes.
* `objective_ids`: 1–128 distinct caller-provided objective IDs, each at most
  200 characters and 800 UTF-8 bytes. `focus_objective_id` must be among them.
* `updates`: 1–6 original teaching updates. `include_history` is a boolean.

A remove update contains exactly `kind`, `op`, and `key`. A preference upsert
contains exactly those three plus `text`, `basis`, and `evidence`; the original
rule requires `basis: "learner_report"` and an evidence quote. An observation
upsert requires those three plus `text` and `knowledge_point_id`, and may add
`basis`, `strategy`, `outcome`, and `evidence`. Unknown fields and update text
that would be changed by the upstream whitespace stripping are rejected rather
than discarded. Existing record objects reject unknown fields as well. The
original rule rejects duplicate `(kind, key)` updates, new observation targets
outside `objective_ids`, unsupported outcomes and capacity overflow. The
original rule does not check the previous objective before deleting an
observation or replacing an existing observation key. This adapter adds a
stricter guard: an existing observation may be deleted or overwritten only if
its current objective is in the caller-supplied `objective_ids`; new targets
must still pass the original rule. Removing a missing key remains an upstream
no-op. These checks use caller-provided scope and do not authenticate it.
A failed batch returns no partial profile. `UNCHANGED` means only that the
selected original rule returned no teaching-field delta after the profile had
been defaulted. For example, an empty profile acquires default fields and a
wall-clock `updated_at` even when removal of a missing key is `UNCHANGED`;
the status does not establish byte equality or cross-call idempotence.

The original rule requires each nonempty evidence field in the current
`updates` to be a literal substring of `current_message`; updates without
evidence, such as tentative observations, have no quote to compare. It does
not recheck evidence already present in the supplied `profile`, even if that
record says `learner_report` or `helped`. Responses distinguish
`update_evidence_verification: "nonempty_literal_match_only"` from
`existing_profile_evidence_verification: "NOT_VERIFIED"`. Neither comparison
establishes that the quoted words support the claimed preference or outcome.
For example, the original rule accepts `examples` as a substring of
`I hate examples` even if the proposed preference is `Use examples`; it does
not perform a semantic consistency check. The comparison also does not
authenticate a human, message, session, objective, material or Core
authorization. The caller can supply a fabricated but internally consistent
request. New records use the worker's wall clock; existing timestamps are
caller claims. Neither is a trusted time or ordering proof. The selected
original rule does not advance the root profile's `updated_at` when it returns
changed fields.

A successful response includes the full resulting `profile`, original
`guidance`, the changed field names, and explicit unverified/no-persistence
labels. The guidance contains profile preferences, evidence and observations;
with `include_history` it can also contain other objective notes. The focus
always selects at most three observations for the chosen objective. Success
output is private, is **not** privacy-filtered, and must not be put in a log or
shown to an unrelated recipient. This worker does not provide access control,
encryption or secure erasure.

The profile has no durable identity, revision, compare-and-swap, cancellation,
or restore fence in this worker. A caller can resubmit an old snapshot and
reintroduce removed information. A future Core integration must bind the
current human event, path/objective and revision, apply authorization and
atomic state changes, and define recovery separately; these tests do not prove
those properties. Do not map the result to existing FSRS reviews or claim that
`helped`, `not_helped` or `unknown` proves an answer, mastery, or teaching
delivery.
