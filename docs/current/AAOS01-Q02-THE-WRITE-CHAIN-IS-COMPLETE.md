historical: true
superseded-by: AAOS01-Q00-Q15-LEDGER-FINAL-20261005.md
说明：仅当前状态声明由上述主表替代；本文历史正文与原始证据保留，不能作为当前验收结论。

# AAOS-01 Q02: the desktop write chain is complete, and I correct my own previous document

## 1. Correction first

In the document committed immediately before this one I wrote that I had not located the frontend's
credential header assembly. That was wrong, and the same round's own search found it. My search pattern was
case-sensitive and the headers are written as X-ArcheAxis-Launch-Token and X-ArcheAxis-Scopes, so the
pattern missed them. They are in frontend/src/api/client.ts, and a test file asserts them.

So the conclusion flips from unverified to verified, statically, end to end.

## 2. The complete chain

| hop | where | what |
| --- | --- | --- |
| 1 | workspace.ts:330 | invoke backend_info |
| 2 | src-tauri/src/main.rs:325,328 | BackendInfo carries port, token and scopes |
| 3 | src-tauri/src/main.rs:462,488,536 | the root shell sets scopes to workspace:write |
| 4 | client.ts:105 | createApiClient receives baseUrl, token and scopes |
| 5 | client.ts:112 | every request carries X-ArcheAxis-Launch-Token |
| 6 | client.ts:138 | every write carries X-ArcheAxis-Scopes, space-joined |
| 7 | client.ts:139 | every write carries Idempotency-Key |
| 8 | app/workspace/router.py:99-139 | the backend requires the launch token, a scopes header containing workspace:write, and an idempotency key |

Every header the backend requires is sent, with the required name and a value that satisfies it. The scope
handed out in step 3 is exactly the scope required in step 8.

## 3. A fail-closed guard on the client as well

Before issuing a write the client checks that it has a token and that the scope list contains the write
scope, and otherwise throws a 403 locally without sending anything. That mirrors the server's rule on the
client side, so a UI that somehow lost its scope refuses to attempt the write rather than attempting it and
being refused.

## 4. What this establishes and what it does not

Established: the write path is wired correctly from the shell's advertised scope through the client's
headers to the backend's guard, and both ends agree on the value.

Not established: that a write has actually been performed through the desktop shell. That would require the
shell's live token, which an external probe cannot obtain and must not attempt. Static agreement is not an
observed success.

## 5. Ledger update

| task | code present | reported | tested | installed qualified | owner accepted |
| --- | --- | --- | --- | --- | --- |
| Q02 | bridge complete and statically consistent | this document | NOT_RUN (no live desktop write) | NOT_RUN | NOT_RUN |

## 6. What changed this round

Two documents. Read-only inspection only.
No repository file was changed; nothing in the green directory was created, modified or deleted;
the official green data and libraries were untouched; nothing was installed.
