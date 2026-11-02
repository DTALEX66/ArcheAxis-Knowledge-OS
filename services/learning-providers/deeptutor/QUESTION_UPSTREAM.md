# DeepTutor 1.7.1 question normalization source

The Owner-supplied `DeepTutor-1.7.1.zip` has SHA-256
`9614f50cfe2cef476c25ad378631f5a5d15a7c0f3f54ef1fa3180c8f41286262`.
Its `deeptutor/agents/question/pipeline.py` member is preserved byte-for-byte as
`upstream/question_pipeline.py` (93,738 bytes, SHA-256
`b0e11748806225b286cff92a2dbf2f5722aa4538c8dc42138fa81def42cc392f`).
The accompanying upstream Apache-2.0 `LICENSE` has SHA-256
`cd2f54e1e5066644023203dcbd956776a9f4ef6eb8b6225afe1ffa2d380fede4`.
`upstream/THIRD_PARTY_NOTICES.md` preserves the archive's notice file unchanged
(SHA-256 `d59dc01b43d1916db9418bc1ebcc213a4859047dc07e2766c4234391f9db033c`).

`question_normalizer.py` is an ArcheAxis adapter. It verifies the complete
upstream member, first rejects symlink/reparse ancestors and hard-linked source
files, checks the opened file identity, parses it without importing it, and compiles only the original
`QuestionType`, `_CHOICE_KEYS`, `_FILL_IN_BLANK_TOKEN`, `_CONCEPT_ANSWERS`, and
three `QuestionPipeline` methods: `_parse_quiz_payload`,
`_normalize_quiz_payload`, `_collect_quiz_issues`. A minimal template object
provides the only required template field, `question_type`. No other upstream
top-level statement, provider configuration, tool or model is executed.

The adapter deliberately adds bounded input and strict object fields, rejects
duplicate JSON members and non-finite values, rejects upstream-reported issues
and known failure placeholders, and emits only learner-facing question fields.
It selects one question, normalizes options using the upstream rules, and drops
unselected or unknown fields. It does not preserve the original input and does
not create a loss receipt. Any future Core importer must separately preserve
the original input and record its omissions; this projection is not lossless.
The private in-process candidate contains the answer key and is not a learner
view. Existing Document reads/exports and small answer spaces remain outside
any answer-secrecy guarantee. A submitted result is caller-declared and its
origin is unverified; parsing it is not provider execution, inference, Core
admission, grading, or evidence of independent mastery.
