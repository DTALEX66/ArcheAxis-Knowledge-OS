# DeepTutor practice grading source

This directory retains the objective grading function from HKUDS/DeepTutor
**1.7.1**, under the accompanying Apache License 2.0. The source is the
Owner-supplied `DeepTutor-1.7.1.zip` retained in the project's local archives.

- Archive SHA-256: `9614f50cfe2cef476c25ad378631f5a5d15a7c0f3f54ef1fa3180c8f41286262`.
- Original member: `deeptutor/services/practice/answers.py`.
- Preserved member: `upstream/answers.py`, 1,538 bytes, SHA-256
  `fdfbaee6cd0fa2c0f31de9a792e220e6989434fc1f44359db3e6afc62cd2472f`.
- Original license member: `LICENSE`, SHA-256
  `cd2f54e1e5066644023203dcbd956776a9f4ef6eb8b6225afe1ffa2d380fede4`.

The retained upstream file and license are byte-identical; no upstream code is
modified. `grade_worker.py` is an ArcheAxis-authored bounded adapter. It does
not start DeepTutor, call a model, access a database, or establish mastery.
Its result is a candidate observation; Core admission, source authorization,
task lifecycle and persistence must be separately connected and verified.
On success the worker hashes the exact stdin line it read, including any
newline, so a future Core bridge can compare the bytes it actually sent. That
unsalted digest may be guessable for small answer spaces; it is not a secrecy
or independent-origin proof.
