# OpenMAIC 1.3.0 interactive URL mapping: finite prototype

`interactive-url-map-worker.mjs` calls the original `mapInteractiveLibraryUrl`
from the preserved OpenMAIC generation 0.3.28 sources. It does not import the
separately unresolved `interactive-post-processor.ts`, parse HTML, execute
input scripts, request a model, register a product route, or write a Core task.
The source-only OpenMAIC copy and each npm `SOURCE.json` retain their original
licenses and member identities. Source-map-js also retains the Closure Compiler
Authors' BSD notice in its original `lib/base64-vlq.js` header.

The worker accepts one UTF-8 JSON object with exactly the string keys `schema`,
`request_id`, and `url`; the schema is
`archeaxis.openmaic-interactive-url-map/v1`. Input and output are bounded. It
uses the upstream fixed library table and an explicit `/vendor/interactive`
base. Unknown references remain unmapped; the wrapper separately rejects paths
outside its allowed lexical patterns. For Three.js `build/` and `examples/jsm/`,
and KaTeX `dist/fonts/`, those patterns allow matching descendants by prefix
and suffix, rather than checking an inventory of individual files. `MAPPED`
therefore does not prove the specific file is listed upstream or exists;
consumers must separately verify the actual asset inventory. No raw invalid
input is echoed. The receipt's SHA-256 fields are unkeyed comparisons;
they do not authenticate inputs and can reveal low-entropy values by guessing.
Even a successful mapped path is derived from caller input and is a private
result; this worker does not provide general privacy filtering or log safety.

Exit code 0 only indicates that protocol processing ended; `REJECTED` and
`UNMAPPED` are also returned as JSON with exit 0. The caller must validate the
response and inspect its `status`; the exit code alone cannot establish that a
mapping succeeded. `expected_source_sha256` is a fixed expected identity, not
itself proof of a read; `source_verification` distinguishes selected source
members verified during this invocation from `NOT_ASSERTED` on early failures.

In the original function, the input
`/vendor/interactive/../../escape` is returned unchanged through the existing
local-prefix shortcut. The wrapper records that a value was returned and its
SHA-256, but reports `UNSAFE_UPSTREAM_PATH` and emits no usable `path`.
Upstream also maps some older, unversioned, or `latest` URLs to its pinned
version: `changed` records string replacement, not equivalence of resources.

The process checks the exact Node 24.21.0 executable bytes and preflights the
original sources and eight fixed package manifests and members. Its synchronous
resolver only admits the pinned package edges, including PostCSS's nanoid 3
and parse5's entities 8. The owning launcher must clear environment variables
**before** starting Node, especially `NODE_OPTIONS`, `NODE_PATH`, and
`INTERACTIVE_ASSET_BASE_URL`; rejecting them inside the worker cannot undo a
startup option already applied by Node. A future host must also bind the worker
file's own trusted identity before launch; checking Node and dependencies inside
the worker does not establish that identity. Tests use a fresh, task-owned
package layout and a fixed, explicitly supplied executable; no install or
package script is run.

The mapped paths are not proof that page assets are installed. Hash-before-load,
the resolver, the input cap, and a parent deadline are not an OS sandbox: path
replacement races, ancestor reparse points, process descendants and network
isolation are not closed here. Loading the trusted dependency modules is still
code execution; this limited call does not parse CSS or run source-map sorting.
If later code expands to source maps, source-map-js contains a `new Function`
path that needs its own review. This prototype is not an HTML sanitizer,
network or offline guarantee, independent provider verification, Core
authorization, persistence, or installed product qualification.
