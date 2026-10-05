# AAOS-01: which shell my builds produced - resolved

## 1. The question I left open last round

I said I was not claiming which of the two Tauri shells my earlier builds produced, because I had not
re-checked. Checking now resolves it.

## 2. Evidence

| signal | value |
| --- | --- |
| bundle artifacts present | ArcheAxis Knowledge_0.6.14_x64-setup.exe (16.38 MiB), ArcheAxis Knowledge_0.6.14_x64_en-US.msi (24.06 MiB) |
| binary in the target | ArcheAxis.exe, 21.25 MiB |
| cargo fingerprint directories | archeaxis-desktop-... (five of them) |
| root src-tauri/Cargo.toml crate name | archeaxis-desktop |
| desktop/src-tauri/Cargo.toml crate name | archeaxis-desktop-shell |

The fingerprint directories name the crate that was actually compiled: archeaxis-desktop. That is the root
src-tauri/ crate. The desktop/src-tauri/ crate is a different one, archeaxis-desktop-shell. The bundle
artifacts carry the product name ArcheAxis Knowledge, which is the root shell's product name, not
ArcheAxis Knowledge Recovery.

So my builds produced the root shell - the main product - and not the recovery shell.

## 3. One honest qualification

I have earlier evidence that desktop/src-tauri/Cargo.lock had been rewritten at some point, which is what a
build run from that directory would do. Those two facts can both be true: an attempt from the desktop
directory may have happened earlier, and the artifacts that survive in the target are from the root crate.
I am recording what the surviving artifacts and fingerprints show, not reconstructing every command I ran.

## 4. What this changes

| item | before | now |
| --- | --- | --- |
| Q12 artifacts | produced, provenance unchecked | produced from the root product crate |
| my earlier uncertainty | not claimed | resolved: the root shell |
| the two-shell question | open | still open - which shell is the product remains your call |

It does not close the two-shell question. It removes one uncertainty I had noted and it strengthens the
provenance of the Q12 artifacts, which now trace to the main product crate rather than to the recovery
shell.

## 5. Ledger update

| task | code present | reported | tested | installed qualified | owner accepted |
| --- | --- | --- | --- | --- | --- |
| Q12 | artifacts produced from the root product crate | this document | NOT_RUN (26 assertions not executed) | NOT_RUN | NOT_RUN |

## 6. What I do NOT claim

| not claimed | reason |
| --- | --- |
| the installers have been installed and exercised | the journey still needs your approval |
| no build was ever attempted from the desktop directory | its lock churn suggests otherwise |

## 7. What changed this round

Nothing but this document. Read-only inspection of build artifacts and two crate manifests.
No repository file was changed; nothing in the green directory was created, modified or deleted;
the official green data and libraries were untouched; nothing was installed.
