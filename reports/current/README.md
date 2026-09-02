# Current report boundary

This tracked directory is an entry point only. Historical execution snapshots
were moved without deletion to
`reports/history/pre-v0.6.7-current-snapshots/`; they must not be treated as
the current Git, CI, Release, installed-runtime, or product-capability state.

Live source/capability reports are generated from the checked-out Git state:

```powershell
python scripts/generate_current_reports.py
```

The default output is the ignored project-local directory
`.hermes/task-artifacts/current-reports/`. This prevents a checked-in report
from claiming that it contains its own commit SHA. It also intentionally makes
no Release claim by default: pass a specific immutable receipt only when that
receipt is the exact historical or current Release evidence being reported.

```powershell
python scripts/generate_current_reports.py --release-evidence <immutable-receipt.json>
```

Do not use a retained historical receipt as an implicit substitute for the
current public Release.

Evidence layers remain separate:

- Git source HEAD/tree and `origin/main` equality are structural facts;
- the v0.6.8 receipt proves exact-SHA CI, three Windows lifecycles,
  publication, and downloaded-asset readback;
- each product capability remains `PARTIAL` or `NOT_EXECUTED` until its own
  executable journey produces a SHA-bound receipt.
