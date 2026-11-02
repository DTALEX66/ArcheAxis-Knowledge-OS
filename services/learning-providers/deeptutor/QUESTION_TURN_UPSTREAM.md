# DeepTutor 1.7.1 offline question-step replay

This worker executes the selected original `QuestionPipeline._quiz_one` method
and its pure prompt/rendering helpers from the retained
`upstream/question_pipeline.py`. It reads the original English or Chinese
question pipeline prompt and the original language-directive functions. The
already existing `question_normalizer.py` supplies the selected original
question parser, normalizer and validator; this worker pins that adapter too,
instead of maintaining a second copy of those rules.

The Owner-provided archive is
`.project-local/archives/owner-inputs/20261101-learning-platform-sources/DeepTutor-1.7.1.zip`,
SHA-256 `9614f50cfe2cef476c25ad378631f5a5d15a7c0f3f54ef1fa3180c8f41286262`.
Original members are preserved byte-for-byte:

| Retained member | Original archive member | Bytes | SHA-256 |
| --- | --- | ---: | --- |
| `upstream/question_pipeline.py` | `deeptutor/agents/question/pipeline.py` | 93,738 | `b0e11748806225b286cff92a2dbf2f5722aa4538c8dc42138fa81def42cc392f` |
| `upstream/question_pipeline.en.yaml` | `deeptutor/agents/question/prompts/en/pipeline.yaml` | 25,482 | `148ccde0f60f2d96724e1cbaa3db1f4bc676e87ed086bda1dac1bcdc27f2ae89` |
| `upstream/question_pipeline.zh.yaml` | `deeptutor/agents/question/prompts/zh/pipeline.yaml` | 22,946 | `ef14102e36f9c156528336b48112a3e8336269fdea5a3517119c651707a8ae58` |
| `upstream/question_language.py` | `deeptutor/services/prompt/language.py` | 4,860 | `7ef192bca1cc8d91c838a4601847a2b40d09becca704e5f74ed65af855f55ce3` |

The shared upstream Apache-2.0 `LICENSE` and
`upstream/THIRD_PARTY_NOTICES.md` are retained alongside this slice. The
local adapter `question_normalizer.py` is additionally pinned at SHA-256
`dc60e865e27bb9316dce09bf94ec55a0420503acd2aa31c577557693a81a92a3`.
Changing a pinned source makes the worker unavailable until deliberately
reviewed and repinned. It verifies bounded bytes and observed file identities;
this is not a claim that every concurrent filesystem replacement is impossible.

The worker consumes one UTF-8 JSON request and requires stdin to close. Its
caller owns the process deadline. The exact schema is
`archeaxis.deeptutor-question-turn-replay/v1`. Both modes require
`request_id`, `language` (`en` or `zh`), `plan`
(`analysis` and 1–10 `templates`), one-based `question_number`,
`exploration_trace`, and `previous_questions`. Each template has exactly
`question_id`, `topic`, `question_type`, `difficulty`, `source`,
`reference_question`, and `reference_answer`. A `custom` template cannot
carry a reference; a `mimic` template may. Plans, exploration and prior
questions are caller-supplied and unverified.

* `mode: "capture"` reaches the original method's agentic-loop call using a
  local stub and returns the original system/user prompt pair and its SHA-256.
* `mode: "replay"` adds `expected_prompt_sha256` and `response_body`, a
  caller-supplied JSON object representing the final body **after** any
  upstream protocol label has been handled. The prompt is rebuilt and compared
  before the supplied body reaches the original parser and validator. The
  returned candidate contains the question and options, not answer or
  explanation fields.

The digest binds only the canonical JSON representation of those two prompt
messages. It is unkeyed, may be guessable for low-entropy content, is not
authentication or authorization, and is not a binding to the original input
bytes or workspace version. Different caller inputs can produce the same
prompt; for example, the upstream mimic reference renderer strips surrounding
whitespace. The capture result includes caller-supplied material and possibly a
reference answer. Neither it nor the candidate is privacy-filtered or safe to
log by default; ordinary question text and options may themselves disclose an
answer. No source input is persisted by this worker and there is no loss
receipt.

This is a narrower, stricter replay than the full upstream pipeline. It does
not run exploration, planning, the actual agentic loop, a model, tools,
retrieval, images, repair, or a database. The native prompt still describes
upstream protocol labels and tools, but the stub accepts only one caller-given
final JSON body and never dispatches a tool. It rejects duplicate keys,
non-finite values, Markdown fences/prose, unknown fields, template/type
mismatch, invalid options, the original literal placeholders
`[Generation failed]` and `N/A` (after trimming), and invalid blank counts.
Other placeholder spellings are not automatically detected. Upstream
normally tolerates some of these via fallback parsing or normalization; this
worker deliberately does not. It does not verify factual grounding, answer
correctness, novelty, provider origin or independent mastery. A later actual
Core bridge must independently bind source versions, authorization, cancellation,
owned-process lifecycle and result admission.

For choice questions it also rejects aliases that identify more than one
option under the original practice grader's case/whitespace folding and its
four accepted forms: key, option text, `key. text`, and `key) text`. The
upstream question validator does not itself check this. This finite check
does not establish that options are visually or semantically distinct under
other normalization, rendering or grading systems.

The non-choice replay candidate has `options: null`; the existing
`grade_worker.py` requires an options dictionary and rejects that DTO if
passed unchanged. The synthetic test explicitly maps `null` to `{}` and
supplies the caller's reference answer separately. With empty options, the
original practice grader returns `provider_correct: null`, meaning
**ungraded** rather than a correct or incorrect result. This test conversion
does not constitute a Core bridge or bind the answer key to a trusted question.

The worker uses the project's already available PyYAML safe loader for the
pinned YAML. A missing loader or source is `UNAVAILABLE`; it does not download,
install or use an alternative. A suitable isolated invocation uses the
project's Python with `-I -B`, a restricted environment and a caller-managed
timeout. This is process isolation, not an OS sandbox.
