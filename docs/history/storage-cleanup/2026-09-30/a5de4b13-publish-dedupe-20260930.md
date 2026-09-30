# a5de4b13 独立 publish 展开副本去重及剩余 desktop-publish 审计

时间：2026-09-30T01:03:42.8402831+08:00

状态：PASS（精确去重及存储回读）；产品测试 NOT_EXECUTED。

## 已执行的精确操作

仅删除 `D:\All projects\ArcheAxis-Knowledge-OS\.project-local\build\desktop-publish\a5de4b13`，225 文件 / 217,420,057 逻辑字节。没有新增归档。

保留的恢复 ZIP：`D:\All projects\ArcheAxis-Knowledge-OS\.project-local\build\green-candidates\ArcheAxis.Knowledge.Green-va5de4b13-x64.zip`；314,318,323 字节；SHA-256 `b103452dfabdf86f54d833eedf7e55bb7a72a44544ec76ba7fc324db869faa4e`。

删除前该目录与候选 manifest 中 desktop/*、候选现有展开 desktop/、ZIP 的 desktop/ 子树四方逐文件路径/长度/SHA-256 完全相同；ZIP 子树成员 CRC 通过，源树重算通过。源清单 SHA-256：`3f2e0683a8a085a112a90aa44e716650479a7d01c2ab5024c02988f10104a8fe`。删除后源目录不存在，完整 ZIP SHA 回读相同，候选目录仍存在。

恢复时仅将 ZIP 内 `ArcheAxis.Knowledge.Green-va5de4b13-x64/desktop/` 下的成员映射到已删的独立 publish 目录；或者从保留候选的 desktop/ 恢复；再对照 preflight.json 逐文件核验。

## 保留与边界

- `docs/SHARED_RESOURCE_PATH_INDEX.md:53–54` 仍将 va5de4b13 候选及 ZIP 列为 aaos_current_candidate。该完整候选、ZIP、manifest、运行时均保留；删除对象仅为另一路径上的精确 publish 副本。
- vheadd1bb2b99 候选包含另加的 .project-local/runs/green-smoke-current-20260916/workspace.sqlite、WAL、SHM、writer.lock；仅文件名/长度盘点，内容未读，整个候选保持原样。
- 当前源码/current-source 路径、最新正式产物、DB、E/F、其他智能体负责的 Cargo R6 与缓存目录没有改动。
- 可见 dotnet、ArcheAxis.Desktop、cargo、rustc 进程阴性；没有宣称已检查受保护进程的全部句柄。

## 剩余 desktop-publish

剩余 22 个目录 / 4,984 文件 / 4,798,503,361 逻辑字节，逐文件完整清单已保存在 remaining-desktop-publish-inventory.json。逐项判断 KEEP：在本次扫描 build/green-candidates、build/green-candidates-r6、staging 的 ArcheAxis 候选 ZIP 时，没有发现与其 ArcheAxis.Desktop.dll 相同的 ZIP desktop 成员，因此不能以现有候选 ZIP 证明整树可恢复。此结论限于该扫描范围。

R6-EXECUTION 保留 current-p3-v3/v6、多个 ui-final-pass 哈希目录的运行记录；AAOS-UI-COMMERCIAL-AUDIT 引用 ui-commercial-pass-2；R5 引用 win-x64。须先建立对应归档和恢复映射后再考虑折叠。

| 目录 | 字节 | 文件 | 完整清单 SHA-256 |
|---|---:|---:|---|
| `current-p3-v7` | 222796476 | 230 | `86130a63fc163defb82f27cba32b59f61ecf25fefbdd3908773502c983d9ff77` |
| `current-p3-v6` | 222794012 | 230 | `e0d8802667857b32d6183272668a0363d5089338483b3ad9eeeb0cea11c18b17` |
| `current-p3-v5` | 222792968 | 230 | `dae864801f7a0ed454172bd7da4983f95387472ccb5a6bce88f5db0a05866bcd` |
| `current-p3-v4` | 222789432 | 230 | `2b45c750feeb9921684032a7c12123d9fc3b9353475fb8c8612c3752e67105e7` |
| `current-p3-v3` | 222786404 | 230 | `a44d493a0c4e585adfe76ba5ce82910f3dd640abc0cd4b67d19fa9a45d2a6663` |
| `current-p3` | 222779676 | 230 | `c3232eae7b7e471a7fcc918afdd994543f37d0091e3abb8a134cfd34af9bd0b7` |
| `current-p3-v2` | 216936764 | 229 | `74c84a61be39746c02c28190c81b45abd5ceb7eb007376d29248e8cb033482af` |
| `ui-final-pass-8156be8c` | 216465215 | 225 | `2dd385057dc87261bea4b3b48d5f7278601b7a1f3fa7350b87258f1c86167c37` |
| `ui-final-pass-9185186a` | 216465151 | 225 | `beb73aa2bd8890a32955a6129d6aa18a0a4b50e86540e7b55051ad274a9fc54c` |
| `ui-final-pass-1534a881` | 216464527 | 225 | `b1fa327dcd6d939de05702d96eaf844fdeb6f95d0171267755f5d7292069edf7` |
| `ui-final-pass-80a12126` | 216463975 | 225 | `1b6c90ed4ad37824f4f38d6b4a8cb9ac035aef8110c95a9da34c38e201985b56` |
| `ui-final-pass-16f0935e` | 216463935 | 225 | `6c028a389b1f84611f67f383818cffa0ec9ecfdd690f8da56cbc40b344567d70` |
| `ui-final-pass-2d9fbb75` | 216463915 | 225 | `d12601373dff350a92892a8026e3e6f2c5a221f92f256fb4d0a4cf7321951e6f` |
| `ui-final-pass-74f658d7` | 216462099 | 225 | `6facb3b37c3894b2d81cf95c6c4cdcea3c64fc4566c4126f7b4467ee7569dd37` |
| `ui-final-pass-38f44985` | 216460803 | 225 | `c163f07aeb8e7a4d5bc3205498fdd7394d4c4f7a1a7b6a0f7dab91ff845b713e` |
| `ui-final-pass-9468a08e` | 216460247 | 225 | `6d3e39e6b7e6a11c387a93732d2f7f6e069899a45948559b4be85be6078fccc8` |
| `ui-final-pass-2a9b31f4` | 216460211 | 225 | `c9c47fa22b02a229cd2a1f16d0ecd9911bc358af1ce45d0648215df02483695f` |
| `ui-final-pass` | 216459599 | 225 | `a0a7f2dc5cab95d524215b82cf359bc6f3b7b1d64781fe776b618d5507f44355` |
| `ui-commercial-pass-2` | 216452039 | 225 | `9d9f1cc552dbe4d8f5b42e129f893982c6a30a7a9bab0f9e40ec6cf2566aac84` |
| `ui-commercial-pass` | 216450779 | 225 | `8f7b5cef04fd96e459d4bb27867e59bf7684f18e970080dd141021c0219a3af7` |
| `ui-current` | 215546067 | 225 | `3fde404ab036ee76e54b86ad6a993140a6f7951ac0e8f0298f2b8beee14467cd` |
| `win-x64` | 215289067 | 225 | `3cbdeaca52b9a6399794ba64a76991d258106e1bd75aa21a3b166a7822ae463f` |

## 证据

`.project-local/mig/a5de4b13-publish-dedupe-20260930/preflight.json` 包含225条源文件清单与四方一致性结果；`final.json` 保存删除后状态；`remaining-desktop-publish-inventory.json` 保存剩余4984条源文件清单。清单摘要按相对路径排序后，以 path + TAB + decimal size + TAB + lowercase file SHA + LF 的 UTF-8 字节计算 SHA-256。

没有运行编译、GUI或产品测试；此清理不构成当前 runtime/CI/release PASS。
