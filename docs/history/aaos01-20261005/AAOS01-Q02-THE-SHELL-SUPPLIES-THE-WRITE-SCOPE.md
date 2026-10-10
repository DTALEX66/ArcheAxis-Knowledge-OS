historical: true
superseded-by: AAOS01-Q00-Q15-LEDGER-FINAL-20261005.md
说明：仅当前状态声明由上述主表替代；本文历史正文与原始证据保留，不能作为当前验收结论。

> 归档（2026-10-08 文档收敛，批次 d-docs-20261008）：本文件自 `docs/current/` 原样移入 `docs/history/aaos01-20261005/`，正文、日期与原始证据未改写；该主题的当前入口是 `docs/current/AAOS01-Q00-Q15-LEDGER-FINAL-20261005.md`。

# AAOS-01 Q02: the root shell supplies exactly the write scope the backend requires

## 1. The chain, verified on the Rust side

| hop | evidence |
| --- | --- |
| the root shell's backend info carries scopes | src-tauri/src/main.rs:325 struct BackendInfo, :328 scopes: Vec<String> |
| the value it hands out | :462, :488, :536 all set scopes: vec![workspace:write] |
| what the backend demands | app/workspace/router.py requires the workspace:write scope in the x-archeaxis-scopes header |

So the scope the shell advertises is exactly the scope the backend requires for a desktop write. They
agree by value, not merely by shape.

This is the opposite of the recovery shell, whose backend info has no scopes field at all - consistent
with the recovery shell not being the write-capable product surface.

## 2. What I could and could not verify on the frontend side

I searched the frontend TypeScript for the credential header names - the scopes header, the launch token
header, and the idempotency key header. I did not find any of them as literals in frontend/src.

I am recording that as a limit of this check, not as a defect. The frontend reads scopes out of the backend
info and passes them into its API client constructor, so the headers are likely assembled inside the client
rather than written as literals where I searched. I have not located that assembly, so I cannot yet claim
the header is actually sent with the expected name and value.

## 3. Why this matters for the objective

This is the Q02 bridge question in its most consequential form. If the shell supplies no scope, no UI write
can ever be authorized; if it supplies the right one, the write path is wired. The Rust half now reads as
wired. The frontend half is unverified.

## 4. Ledger update

| task | code present | reported | tested | installed qualified | owner accepted |
| --- | --- | --- | --- | --- | --- |
| Q02 | bridge exists; Rust supplies workspace:write; frontend header assembly not located | this document | NOT_RUN | NOT_RUN | NOT_RUN |

## 5. What I do NOT claim

| not claimed | reason |
| --- | --- |
| the header is actually sent with that name and value | the assembly was not located |
| a UI write has been observed to succeed | no desktop-token write has been performed |

## 6. What changed this round

Nothing but this document. Read-only inspection.
No repository file was changed; nothing in the green directory was created, modified or deleted;
the official green data and libraries were untouched; nothing was installed.
