# AAOS-01 §六 删除清理 · 本轮已执行与我自己的待清清单（2026-10-05）

## 本轮精确 Cargo 缓存清理：已执行并读回

已删除旧 `C:\Windows\Temp\aaos-target` 与 `C:\Windows\Temp\aaos-msvc-target` 下 `debug`、`release` 各自的 `.fingerprint`、`build`、`incremental`：共 **12 个精确子目录 / 14,060 文件 / 4,241,169,479 字节**。两项 release/incremental 为空，计入已移除路径数，字节为零。该数只计本批成功删除的逻辑文件载荷，不叠加历史清理累计，也不代表 NTFS 空闲增量。

删除前检查 cargo/rustc/rustfmt 的实际进程路径与命令，未发现旧两目标上的构建消费者；逐目录验证绝对 exact 路径及祖先、全部子项无 reparse、无读取错误。保存所有待删文件的相对路径、长度与 SHA-256 后，每项重新核对文件集合和哈希，再使用 PowerShell `Remove-Item -LiteralPath` 删除并读回不存在。独立复核 **12/12 absent**。

证据在本工作树 `.project-local/task-runtime/aaos01-tools/`：

- `temp-cargo-twelve-predelete-manifest.json`：3,243,204 字节；SHA-256 `626dbfe964833b3a9463535e2df4b6636df64648a42d56c2724d6c0619bf394a`。
- `temp-cargo-twelve-prune-receipt.json`：逐项成功、文件数和本批载荷；SHA-256 `d3dcc2dcfd5bfd3ec4dac2e5aeb6200635a1b595315690ea34ddcb1812e32ad2`。
- `temp-cargo-twelve-independent-readback.json`：独立 absent 与保留对象检查；旧 `volume-history-readback.json` 保持原观察，未把先前候选清单改写成删除证据。

本批只删除可由保留源码/锁文件重新编译的缓存，**不承诺恢复旧 dirty 构建的相同字节**。重新构建应使用 `scripts/runtime/dev.py` 的项目内注册 target；当前 D 盘候选不是旧历史二进制的字节替代证明。

## 仍待与明确保留

- `C:\Windows\Temp\aaos-target` 父目录、deps/runtime/历史宿主保留；复核时 PID `28404` 仍执行其 `release\runtime\python\python.exe`，未终止。
- `C:\Windows\Temp\aaos-msvc-target` 父目录及 deps、`release\data`、`release\ArcheAxis.exe` 保留；历史候选/数据需独立归属与恢复清单，不能整根删除。
- `C:\Windows\Temp\aaos-cand1` 及其 data 保留；它仍承载旧候选身份和历史引用，未以新候选运行通过代替其原始证据。
- 历史存储审计的合格未执行列表为空；28 个待归属数据库当前仍存在，独立审查为 `OWNERSHIP_PROOF_INSUFFICIENT_KEEP_PENDING_ATTESTATION`。恢复包哈希正确不证明原库是可删 fixture。Green data/backups/reports/runtime 与当前程序保留；新增或未审计输出仍为 UNKNOWN。

## 三份历史候选 runtime：已证明可恢复后去重

本工作树 `.project-local/a8/runtime`、`a9/runtime`、`a10/runtime` 已删除，独立 **3/3 absent**：共 **58,401 文件 / 1,876,721,160 字节**。三个原树各 19,467 文件、625,573,720 字节，包含空目录的完整集合相同，树摘要 `75696f7cd649c5575f76effd8b207135fb09cc74333be071b1a9ef5227e88a55`。

首次直接整树比较非零 KEEP 的原记录保留：a3 donor 多 363 文件及 51 目录，a11 多 47 文件及 8 目录（包含 pycache），因此不能直接复制 donor 超集并声称原样恢复。随后按原始逐文件/目录清单从保留的 `.project-local/a3-python-input/runtime/python` **真实构造一份全量恢复样本**，三个原树另行 fresh SHA 核验；恢复样本完整集合、长度与 SHA 全部匹配原树，donor 额外项复制数为零。验证后移除临时 proof，再次核进程、无 reparse 后只删除三个旧 runtime 子树。108 个候选 Core/workers/shared/元数据文件删除前后 SHA 一致；候选父目录、数据、原回执、a3 donor、当前 rt/a11 与注册构建 target 保留，未新增重复 ZIP。

这些历史候选已冻结，**必须先按恢复 recipe 重建 Python 才能重新运行**，不能继续宣称现有完整候选可启动。证据在同一 ignored 目录：`old-candidate-runtime-donor-full-manifest.json`（25,794,079 字节，SHA `88da8ef084de6c692f0ad7c5099c1c953f9c411267c90900d18e86146140e792`）、原差异记录、`old-candidate-runtime-filtered-recovery-proof.json`、`old-candidate-runtime-filtered-prune-receipt.json`、`old-candidate-runtime-filtered-independent-readback.json`，以及可执行 `restore-old-candidate-runtime.py`（SHA `e56ed8cb14910564e9ea69f8595e80e4c9cd16f60271324911b9a24e3eadcf3c`）。recipe 拒绝已有目标与三处 exact 原路径之外的输出，只按清单读取 donor、验证每个原文件 SHA，再核完整恢复集合。

恢复时先核清单和 recipe 的上述 SHA，保留现存用户改动；从本工作树执行所需的对应命令，不能直接复制整个 donor：

```powershell
& 'D:\All projects\OS External Configuration\ArcheAxis-Knowledge-OS-ci-venv\Scripts\python.exe' -B .project-local/task-runtime/aaos01-tools/restore-old-candidate-runtime.py restore --target .project-local/a8/runtime
& 'D:\All projects\OS External Configuration\ArcheAxis-Knowledge-OS-ci-venv\Scripts\python.exe' -B .project-local/task-runtime/aaos01-tools/restore-old-candidate-runtime.py restore --target .project-local/a9/runtime
& 'D:\All projects\OS External Configuration\ArcheAxis-Knowledge-OS-ci-venv\Scripts\python.exe' -B .project-local/task-runtime/aaos01-tools/restore-old-candidate-runtime.py restore --target .project-local/a10/runtime
```

此代理两项新增成功清理载荷合计 **6,117,890,639 字节**；本批13份 ignored 清单/recipe/读回文件共29,106,016字节，统计时点扣除此证据成本为6,088,784,623字节。少量更新的既有文档/元数据增量另计，未将临时 proof 的创建后删除重复计为历史释放，也未混入旧69GB累计。该统计只涵盖本批精确清单，**未全量测量当前项目/Green 的物理大小**；用户所述100GB或数十GB及旧可读下界不能由此确认为当前整树体积。

以下保留前阶段原记录，其时间、大小与“当前”仅指该阶段，不再作为清理后容量快照。

## 前阶段已删除（19 个目录 / 5.9 MiB）

**全部是我为探针创建的临时目录**，位于 `C:\Windows\Temp`，**可再生成**，且**每个删除前都做了绝对路径校验**（必须 `StartsWith('C:\Windows\Temp\')`）：

`pdfroot-*` · `legacy-copy-*`（旧库**副本**，真实数据根未动）· `dbview-*` · `mf-*` · `mf3-*` · `mf-samples-*` ·
`ext-*` · `err-*` · `cr-*` · `pb-*` · `fresh-*` · `aaos-fresh-*` · `aaos-core-probe-*` · `aaos-cwd-*` · `aaos-tw-*` · `aaos-t2-*`

## 前阶段待清清单（历史原始大小；本批状态见上）

| 路径 | 大小 | 为何暂缓 |
| --- | --- | --- |
| `C:\Windows\Temp\aaos-target` | **6786 MiB** | 含较早构建产物；**重建约需数分钟**，而我仍可能需要对照 |
| `C:\Windows\Temp\aaos-msvc-target` | **6967 MiB** | **当前应用与单测的构建目录**；删除后需完整重建（约 2 分钟） |
| `C:\Windows\Temp\aaos-cand1` | 272 MiB | **权威候选**，被本批记录引用为证据来源 |

**合计可回收约 14 GB。** 三者**都是我创建的、可再生成的**，**但删除会带走我在引用的构建产物与候选** ⇒
**按 §六「消费者归零、替代实现通过后才进入删除清单」的精神，先列清单、暂缓删除** ✓。

## 明确保留（归属未确立）

`C:\Windows\Temp\aaos-bind-7a69a8ac`（1 MiB，创建于 10-03）· `C:\Windows\Temp\aaos-port-467e8bbd`（0.3 MiB，创建于 10-03）
**创建时间在本会话之前，且仓库代码中搜索不到这两个名字** ⇒ **归属不明 ⇒ 保留并标为未决，不删不移** ✓。
