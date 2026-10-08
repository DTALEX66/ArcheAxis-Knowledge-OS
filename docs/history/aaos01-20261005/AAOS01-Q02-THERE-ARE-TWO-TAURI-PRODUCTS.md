historical: true
superseded-by: AAOS01-Q00-Q15-LEDGER-FINAL-20261005.md
说明：仅当前状态声明由上述主表替代；本文历史正文与原始证据保留，不能作为当前验收结论。

> 归档（2026-10-08 文档收敛，批次 d-docs-20261008）：本文件自 `docs/current/` 原样移入 `docs/history/aaos01-20261005/`，正文、日期与原始证据未改写；该主题的当前入口是 `docs/current/AAOS01-Q00-Q15-LEDGER-FINAL-20261005.md`。

# AAOS-01 Q02: there are two Tauri products, not one product and one duplicate

## 1. The two shells, side by side

| | root src-tauri/ | desktop/src-tauri/ |
| --- | --- | --- |
| productName | ArcheAxis Knowledge | ArcheAxis Knowledge Recovery |
| identifier | com.archeaxis.workspace | com.archeaxis.workspace.recovery |
| frontendDist | ../.project-local/build/frontend-dist | ../bootstrap |
| beforeBuildCommand | npm --prefix ../frontend run build | (empty) |
| rust source size | main.rs, 871 lines | lib.rs, 189 lines |
| scopes mentioned | 4 times | 0 times |
| IPC commands registered | the full set, at main.rs:739 | backend_info only, at lib.rs:67 |

They differ in product name, in bundle identifier, in which UI they embed, and in IPC surface. So they
are two products rather than one product and a redundant copy.

## 2. What I got wrong twice, in order

First I read the frontend's recovery calls and the desktop shell's single registered command and called
it a mismatch - the frontend asks for six recovery commands while the shell registers one.

Then I looked for those six commands and found them all in the ROOT src-tauri, registered at main.rs:739.
So there is no mismatch: the frontend's recovery surface corresponds to the root shell, which provides it.
The desktop shell is a separate, smaller product with its own bootstrap UI, and it does not need that
surface to provide backend endpoint information.

I then also corrected a second framing error: I had described the pair as a complete shell and a minimal
duplicate. They are not duplicates. They have different product names and different bundle identifiers,
which is a deliberate separation, not an accident.

## 3. What this means for the objective's verbs

This is directly a merge-or-freeze question, which is exactly what the objective names.

| verb | candidate here |
| --- | --- |
| freeze | one of the two shells, once it is settled which is the product |
| merge | nothing to merge if they are genuinely two products; merging them would be wrong |
| migrate | the frontend's recovery calls already target the root shell |

The material fact for a decision: they carry different bundle identifiers, so an installer built from one
does not overwrite the other. They can coexist.

I am not recommending which to freeze. The prompt names Tauri as the chosen stack but does not, in the
text I have read, say which of these two shells is the product. That is a question for you.

## 4. Also worth recording

The root shell provides scopes, and the desktop shell does not. The frontend reads scopes from the backend
info and passes them to the API client. Since the backend's write authorization requires a scope to be
present, a shell that does not supply scopes cannot produce authorized writes. The root shell does supply
them, which is consistent with it being the product.

## 5. Ledger update

Q02 (limited type bridge) moves from NOT_RUN to a first recorded finding:

| task | code present | reported | tested | installed qualified | owner accepted |
| --- | --- | --- | --- | --- | --- |
| Q02 | PARTIAL (bridge exists; two candidate shells) | this document | NOT_RUN | NOT_RUN | NOT_RUN |

## 6. What I do NOT claim

| not claimed | reason |
| --- | --- |
| which shell my earlier builds produced | I did not re-check that here |
| that the desktop shell is obsolete | it has its own identity and UI |

## 7. What changed this round

Nothing but this document. Read-only inspection plus one configuration comparison.
No repository file was changed; nothing in the green directory was created, modified or deleted;
the official green data and libraries were untouched; nothing was installed.
