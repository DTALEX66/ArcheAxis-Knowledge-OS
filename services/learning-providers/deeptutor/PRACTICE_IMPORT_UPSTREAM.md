# DeepTutor 1.7.1 practice import preview

`upstream/importing.py` is the original byte-for-byte member
`DeepTutor-1.7.1/deeptutor/services/practice/importing.py` from the Owner-provided
ZIP. Its SHA-256 is
`9ee4dd1abfa150fd81c3e3e31e2321761bab05509f6e4a5fca555ede2bbfd260`.
The shared `LICENSE` retains the upstream Apache-2.0 license. The archived
source ZIP has SHA-256
`9614f50cfe2cef476c25ad378631f5a5d15a7c0f3f54ef1fa3180c8f41286262`.

`practice_import.py` verifies that source and selects only its constants and
the original `_cell`, `parse_rows`, and `normalize_question` definitions. It
does not import the original module or run its top-level code. Its AST removes
the `.xlsx` branch for CSV, TSV, and JSON. For XLSX, it retains the original
branch and replaces only its exact `from openpyxl import load_workbook` with a
previously checked callable in that invocation's separate namespace; the
original ZIP checks and `parse_rows` then execute. The entry point accepts only
bounded CSV, TSV, JSON, or XLSX bytes and a format label, never a supplied file
path. JSON rejects duplicate names, non-finite
numbers, and oversized structures. The adapter also rejects empty CSV headers
and nonblank rows with a different column count, and uses strict CSV parsing to
reject unclosed quotes, so the upstream `zip` cannot silently discard extra
fields or merge records on malformed input. Both the upstream and precheck
reject duplicate strip/lower headers; other distinct headers are retained.
CSV/TSV record numbers count logical records including the header, and need not
equal physical line numbers when a quoted field contains a newline. JSON row
numbers are one-based array indices. Blank CSV record numbers are reported as
`skipped_source_rows`. These checks are additional guards,
not a claim of byte-for-byte equivalence for every rejected input.

XLSX is a conservative preview, not a general spreadsheet importer. The raw
input is at most 5 MiB; ZIP has at most 2,000 parts and at most 30 MiB declared
expanded size. All non-directory parts must be UTF-8 XML or relationships;
XML is parsed with DTD, entity and external references forbidden, with an
aggregate 150,000-node and depth-64 bound. Duplicate or ambiguous ZIP paths,
encryption, unsupported compression, links, external relationships, external
workbook links, embedded objects and binary parts are refused. There must be
exactly one active, visible worksheet and exactly one worksheet XML part.
Hidden rows or columns, rows hidden by the worksheet's `zeroHeight` default,
merged cells, formulas, date/time/duration cells, Excel
errors, non-finite numbers, blank or duplicate normalized headers are refused.
The row/column `hidden` and default `zeroHeight` flags accept only missing,
`0`, or `false`; other representations and duplicate worksheet defaults are
refused, even where a spreadsheet reader might tolerate them. Explicit row
heights, column widths, and corresponding worksheet defaults must be finite and
positive if present; zero and invalid values are refused conservatively. Other
styles, sizes and host rendering can still affect visibility, so the preview
does not establish that every imported value was visible in a spreadsheet UI.
The worksheet coordinates must be unique, ordered, within 501 rows and 64
columns, and agree with the declared dimensions. A preflight independently
reads worksheet cell values and compares them with the result returned by the
original XLSX branch; a disagreement fails closed. These extra checks reject
some files accepted by the upstream version, including images, harmless DTD
text, and some valid but noncanonical worksheet layouts. They do not imply
that all XLSX features are implemented. XLSX row numbers are one-based
worksheet row numbers including the header; blank rows are listed in
`skipped_source_rows`.

The public XLSX preview starts a separate `-I -B` Python process using the
current interpreter. It forwards source bytes only through stdin; the child's
private stdout is read solely by the parent and can contain answers and other
private values. It must not be connected to a terminal, application log, or
public caller. The private child mode is an internal protocol, not a public
API. The parent accepts at most 40 MiB of that private output, checks the source
digest and response shape, and independently reruns the pinned normalizer on
each returned row to compare the candidate, unselected fields, and recorded
option changes. It keeps the private result only in memory. These are
consistency checks: a forged but internally consistent child reply can still
repeat the source digest without proving that it read or parsed those bytes.
They are not child-process or source authentication. Stderr is drained
without retaining its bytes, and any diagnostic output or more than 64 KiB of
diagnostics rejects the result. Missing dependencies, malformed child output,
timeout, and uncertain cleanup report `UNAVAILABLE`; no automatic replay is
attempted. Direct in-process execution of `_private_preview_in_process` is for
synthetic tests only: openpyxl warnings may include workbook content, so it is
not an acceptable host interface for private input.

The child gets a small allowlisted environment: OS startup variables and
project-owned paths for home and temporary-directory variables. These paths are
not claimed to be empty. Existing `OPENPYXL_DEFUSEDXML` and `OPENPYXL_LXML`
values are passed only when they are recognized boolean forms. The 30-second
timeout bounds the initial wait, not every subsequent cleanup operation. The
code terminates only the direct child; it does not establish Windows Job
containment, descendant termination, immediate stopping of pipe threads, or an
OS memory quota. A timeout or unconfirmed cleanup remains UNKNOWN. This is
process separation and diagnostic containment, not a sandbox or secure erasure.

This slice requires the locally reviewed `openpyxl` 3.1.5 and `defusedxml`
0.7.1, and verifies that openpyxl has actually enabled and bound the
defusedxml `iterparse`; missing, different, or disabled protection reports
`UNAVAILABLE` rather than falling back. The project environment also contains
`et_xmlfile` 2.0.0 and optional `lxml` 6.1.1; installed metadata identifies
openpyxl and et_xmlfile as MIT, defusedxml as PSFL, and lxml as BSD-3-Clause.
This is not a complete packaging or redistribution license audit. The XLSX
subprocess requires the environment's site packages, so `-I -B` may be used but
`-S` prevents those dependencies from being loaded. The checks are not an OS
sandbox and do not authenticate the Python interpreter or its installed
libraries. Non-cell workbook content such as formatting, annotations, metadata,
drawings, and unselected fields is not preserved by the displayed projection;
where accepted, only the full original bytes and parsed unselected cell values
are retained privately in memory for the life of the call.

The private result holds the exact input bytes, raw parsed rows, per-row
unselected top-level fields, observed option replacements, normalized
candidates, original upstream import IDs, and source SHA-256 only in memory.
Nothing persists them, and they cannot be recovered after restart. A future
Core import must explicitly preserve the source and any intended unmapped
values before claiming lossless storage. Public previews include a random
ephemeral preview identifier, record number, unselected top-level field count,
known option changes, skipped record numbers, and fields omitted from display.
The private result keeps original values and associates those counts with that
record while alive; the random identifier is not a content binding. The option
comparison catches named option collisions and column overrides, but other
selected values are not exhaustively compared. The displayed count is not a
complete count of all normalization changes.

The display does not return the `correct_answer`, `user_answer`, explanation,
original source length or digest, or upstream `import:` question ID. The source digest
and ID can reveal a low-entropy answer by enumeration; both are private
in-memory metadata and neither proves origin. A display projection is not an
access-control or encryption boundary. Ordinary question text and options are
user-supplied content and can themselves contain an answer. No
request is authorized, no Core document, SQLite/FSRS state, model inference,
network operation, provider execution, or independent mastery is established.
