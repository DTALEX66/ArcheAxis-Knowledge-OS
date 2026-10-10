# AAOS-01: the two release scripts check different things under the same name

## 1. The sharper statement of last round's finding

Last round I recorded that the private-name rule blocks the declared dependencies. Reading the second
release script sharpens it: the two scripts do not implement the same check, and the difference in scope is
what actually blocks the staging.

## 2. The two implementations

| | stage_backend_runtime.py (backend stager) | assemble_green_candidate.py (product assembler) |
| --- | --- | --- |
| what it rejects | path safety, private names, dot-env prefixes, parent traversal, UNC, drive e, agents dir | reparse points only |
| does it check private names | yes | no, not at all |
| scope | shallow over its arguments, then recursive over runtime, workers and the dependency source | shallow only, on desktop, core, runtime and workers |
| error text | protected staging path / linked staging path rejected | reparse point is not allowed in candidate input |

The recursion in the stager is deliberate and its comment says so: preflight all recursive donors before
producing even a partial output root. So the intent is to fail before writing anything.

## 3. Why this is the mechanism, not just a detail

The product assembler - the one that produces the shipped candidate - checks only reparse points. It does
not look at private names at all. The backend stager does, and it recurses into the dependency source.

That recursion is exactly what refuses the declared dependencies, because fastapi ships a directory named
dot-agents and litellm ships directories named auth, and both names are in the protected set. Remove the
recursion and the staging would proceed; remove the private-name check and likewise. Neither is true of
the other script.

So a legitimate dependency set is stageable by one script and not by the other, and the difference was not
visible from reading either rule in isolation.

## 4. What I am not concluding

I am not concluding that the private-name recursion is wrong. Refusing to ship agent-private state or
credentials is a real requirement, and checking donors before writing anything is sound. The collision is
between that good rule and the names upstream projects chose.

I am also not concluding which script is authoritative for this purpose. The receipt treats the backend
stager as the instrument for putting dependencies into a candidate, so I use it as intended and record what
happens.

## 5. What would resolve it, for a governed decision

Two options, neither mine to choose. Match on location and role rather than on a bare component name, so an
upstream package directory is distinguishable from private state, and adjust the scope of the recursion
over the dependency source. That is a change to a security-relevant check and belongs in a reviewed change
with its own tests, not in an executor workaround.

## 6. What changed this round

Nothing but this document. Read-only reading of both scripts and the rule's test file.
No repository file was changed; nothing in the green directory was created, modified or deleted;
the official green data and libraries were untouched; nothing was installed.
