# 2026-09-30 持续清理执行记录

<!-- CURRENT-CLEANUP-SUMMARY-BEGIN -->
## 当前摘要（2026-10-01：清理收敛复核）

状态 **PARTIAL，目标仍 active**；清理完毕并确认项目安全后才整理上传。本摘要替代正文历史阶段汇总。

- 前续轮净减少 **1,147,330,589 B**：历史候选 ZIP 无损增量归档净268,291,825 B；第六批1243个合成目录净505,759,358 B；89个历史生成EXE/PDB净286,712,384 B；第七批260个合成目录净86,567,022 B。精确源删除后不存在，恢复载荷哈希与保留执行收据读回通过。
- 本报告执行链净减少50,245,032,550 B，加此前两轮7,775,968,326 B，累计 **58,021,000,876 B（58.02 GB）**。口径是逻辑文件载荷扣恢复包和清单，不等于物理磁盘释放，不计少量审计收据。
- Green 原10.0.401 SDK的5577文件、814子目录、807,336,133 B迁至 `D:\All projects\OS External Configuration\10-toolchains\dotnet-sdk-10.0.401`。完整哈希/集合一致，原副本已删除，目标SDK版本读回10.0.401；现有10.0.400保持。此为同盘归属迁移，净磁盘载荷减少0，不计入上述56.05 GB。详见 `docs/current/SDK-OWNER-MIGRATION-20261001.md`。
- 最新可访问元数据：Formal **25,169,438,491 B /348,276 files**；Green **8,957,443,149 B /114,508 files**。读取错误仍491/40；private/Git及链接排除，不能当Explorer全目录体积。Green用户data只统计元数据，不读取正文或删除。
- 新候选ZIP恢复必须同时保留 `ui-history-direct-packed-20261001.zip` 和 `staging-ui-delta-packed-20261001.zip`、proof及 `pack-staging-ui-delta.py` / `zip_cas.py`。父包仍被增量包引用，不得当旧缓存删除。第六/七批恢复分别使用 `synthetic-sixth-fixtures-20261001.zip`、`synthetic-seventh-fixtures-20261001.zip` 和对应manifest；89文件使用 `historical-generated-sixth-20261001.zip` 和manifest。均精确原路径恢复、禁止覆盖。
- 既有Formal/Build CAS恢复包及清单仍保留。当前默认输出、已注册工作树输出、索引候选、用户数据、不同数据库世代与有依赖的NuGet包保留。未改PATH、ACL、服务、注册表或系统配置，E/F未访问。
- 未完成：剩余大目录生产者/引用审计、未知归属运行副本、三处WinError5、无结束收据、混合private/data、当前缓存和环境。不能据名称判断删除。产品构建、运行及上传/双端一致性 **NOT_EXECUTED**；现有定向 synthetic 契约测试首次34pass/2fail（WinError206），短run-id重跑失败两项2pass；SDK CLI读回不是产品安全验收。当前20项tracked变化包含本轮共享路径索引新增，其余既有工作保持。

- 本续轮实际再清理1195文件旧mono候选，净169,743,568 B；全部源absent与恢复SHA、9项兄弟证据SHA读回通过。历史worker Lib和runtime-copy2现已完整归档后删除，分别净182,288,299 B和363,612,342 B；本续轮三项合计715,644,209 B已计入净值。上述体积已由三项删除后的最新metadata收据回读。

- 本最新续轮另已删除a04历史构建及872个精确ZIP成员重复生成文件，净602,171,833 B；源absent、恢复和保留证据SHA均root readback PASS。详细恢复映射与收据见正文最新条目。
- 最新第八合成批与508个历史分发缓存文件已删除，净510,306,036 B，所有精确源absent、恢复SHA及保留执行收据保持；细节与恢复边界见正文最新条目。
- 第九合成1296case与Green三个已迁移包3157个重复文件已删除，账本净144,562,357 B；独立复核恢复ZIP及Formal归属副本完整。Green净值排除722 B审计回读收据，与本摘要统一口径一致。当前交接见docs/current/STORAGE-CLEANUP-HANDOFF-20261001.md；剩余大项复核与产品验证仍未完成。
<!-- CURRENT-CLEANUP-SUMMARY-END -->
状态：限定清理 readback PASS；总体目标 PARTIAL。本文记录真实文件操作，不代表产品构建、运行、发布或双端仓库一致。

## 本轮实绩

本轮删除文件载荷 16,716,136,816 B；新增保留恢复载荷 2,473,113,449 B；净减少 **14,243,023,367 B**。前两轮独立净减少 7,775,968,326 B，三轮合计 **22,018,991,693 B**。这些是逻辑文件载荷，未计少量工具、清单与报告开销，不等于物理磁盘释放量。

| 清理内容 | 本轮净减少 B |
|---|---:|
| 当前候选 run 的 Cargo 中间目录 | 852,622,883 |
| vcurrent8、vcurrent13、final 当前候选展开副本 | 2,568,509,603 |
| 旧 ASR Python runtime 展开目录，保留完整 ZIP | 330,488,081 |
| 八组 Cargo 直接 rlib/rmeta 中间文件 | 3,408,806,290 |
| vcurrent6 展开目录，保留原 ZIP 和唯一额外载荷 | 866,875,066 |
| Green Desktop Debug 展开目录，保留完整 ZIP | 396,179,570 |
| 七个相同 Core PDB 副本及 run 的 rlib/rmeta | 595,786,608 |
| Green 旧工作树 obj | 2,177,034 |
| 18 个相同 x64 Skia PDB 副本，保留恢复 ZIP | 1,491,253,009 |
| Green 三组错误嵌套生成目录，保留完整 ZIP | 1,526,733,802 |
| 八个按架构严格匹配的 native PDB 副本 | 237,659,631 |
| Formal .NET obj | 31,262,285 |
| Green 三组旧预览构建，保留完整 ZIP | 1,934,669,505 |

执行前检查精确路径、链接、归属及引用；删除后检查不存在和保留文件哈希。归档均逐成员核对路径、长度和 SHA-256；vcurrent6 的 1,308 个唯一额外文件完整保留。Cargo 清理保留最终程序和调试符号；rlib/rmeta 清理的 586 个程序/DLL/PDB 保留哈希一致。旧 UI 工作树存在独有修改，保留源码及资产。

## 恢复位置

以下全部是本地恢复材料，不上传。相对路径均以对应根为基准。

- Formal 根：`D:\All projects\ArcheAxis-Knowledge-OS`。原候选 ZIP 保留在 `.project-local/build/green-candidates/` 或 `.project-local/staging/` 的原父目录。重新解压才能复用历史展开路径。
- vcurrent6：原 sibling ZIP 加同目录 `vcurrent6-extra-payload-20260930.zip`；先解压原 ZIP，再将额外 ZIP 覆盖到恢复出的内层根。额外文件清单为 `vcurrent6-extra-payload-20260930.manifest.json`。
- Green 根：`D:\All projects\ArcheAxis.Knowledge.Green-x64`。ASR 恢复 ZIP 是 `backups/archives/inplace-asr-pipeline-20260902.zip`，解压到 `backups/inplace-asr-pipeline-20260902`。
- Green mainline 根：`.ui-task-tree/ArcheAxis-Knowledge-OS-mainline`。其 `.project-local/mig/storage-cleanup-20260930/desktop-debug.zip` 恢复到 `.project-local/build/dotnet/ArcheAxis.Desktop/bin/Debug`。
- 同一 mainline 的 `.project-local/mig/nested-build-output-compaction-20260930/mainline-app-local.zip` 恢复到 `apps/ArcheAxis.Desktop/.project-local`；`mainline-nested-apps.zip` 恢复到 `apps/ArcheAxis.Desktop/apps`；`old-app-local.zip` 恢复到 Green 旧树 `.ui-task-tree/ArcheAxis-Knowledge-OS/apps/ArcheAxis.Desktop/.project-local`。
- 同一 mainline 的 `.project-local/mig/retired-ui-builds-20260930/` 下 `aaos-ui-preview.zip`、`8af23851c3.zip`、`aaos-ui-home-master-20260929.zip` 分别恢复到 `.project-local/build/` 下同名目录。历史报告的构建路径引用仍是历史证据；重跑前需恢复。
- 重复 native 符号恢复材料位于 Formal `.project-local/mig/storage-cleanup-current-20260930/libSkiaSharp-symbol-recovery.zip` 和 `native-symbol-recovery.zip`。按 readback 中相同 SHA/架构映射恢复，不能跨架构替换。

## 保留与未完成

历史 ZIP 的内容寻址去重工具通过人工恢复自测，修复了 Green 深路径的 recipe 文件名长度问题。18 个 Formal 历史 ZIP 共 5,331,573,143 B 仍在构建恢复存储，原 ZIP 未删除，不计释放量。

后续完成 Green 七档 ZIP 去重：原 ZIP 共 2,189,807,073 B，完整独立恢复存储 403,838,911 B，根执行器再验证七档重构原 SHA、源 SHA 与长度后删除原 ZIP，readback 七个原路径均不存在，净减少 **1,785,968,162 B**。本轮合计已增至 **16,028,991,529 B**，三轮合计 **23,804,959,855 B**。上表是此前阶段，追加实绩单列以免重复。

Green 恢复存储在 mainline `.project-local/mig/ui-build-zip-cas-20260930/`，包含 `zip_cas.py`、`store/objects`、七份 `store/recipes` 及 `source-recipe-readback.json`。上节所列 Debug、三组嵌套产物、三组旧预览 ZIP 现已由此存储替代。需先调用该目录工具 `restore --store <该目录/store> --recipe <对应recipe>` 恢复原 ZIP，再按上节解压。工具默认只恢复 recipe 记录的原 ZIP 精确路径并拒绝覆盖；全部恢复材料留在 Green 内，不依赖 Formal 的数据存储。helper 是标准库 Python 脚本，执行时需要可用 Python。

访问受限 run 目录无法完整审计；测试 SQLite/WAL/SHM、当前离线 NuGet/UV 缓存、不同载荷的当前 audit-final、旧 UI 独有修改、验收图片、源码资产和私有状态均保留。不能把未知内容当作无用数据。

本轮曾在 private 名称预检前生成 maintenance 备份 ZIP。后续校验发现 `.hermes`，立即删除本轮新生成的 ZIP，保留原 `backups/inplace-maintenance-wal-20260902`，停止该目录清理。未打印或上传私有正文。后续归档已先做 private/数据库/链接边界预检。

E/F 未访问。没有修改 Windows 配置、ACL、系统服务或其他软件安装；本记录不能证明 C/D 所有软件健康。没有执行产品重建、运行验收、commit、push。

## 证据

### 后续目标回合：新增中间件清理

再追加完成第三批 152 个 synthetic testcase：源 782,302,057 B、恢复 ZIP+manifest 13,613,175 B，净减少 **768,688,882 B**，152 源目录全部不存在。恢复 ZIP `synthetic-pytest-third-fixtures-20260930.zip`，SHA `e48b770a44496ea51b4c4c309dfeee3dcb6d746a934a027696a47220a24c0f4b`，解压根仍是 `.project-local/runs/be268a2d33/`，不得强制覆盖。对应 `synthetic-third-fixtures-*` 保存完整集合/SHA和删除读回。

两组历史 Cargo deps 的 48 个测试 PDB（2,173,304,832 B）已完整 ZIP 归档后删除展开符号，恢复 ZIP+allowlist 434,578,780 B，净减少 **1,738,726,052 B**；48 配套 EXE 哈希前后相同。归档 `historical-test-pdb-20260930.zip`，SHA `123857d185d2ac3bbef60cbdbb7d160ec238f1f33075b345d83d6d138018cb0f`；解压到 Formal 项目根恢复 `.project-local/build/<id>/cargo/debug/deps/` 原相对路径，不得强制覆盖。该阶段仅处理 `32a18f7418` 与 `4260083704` 的测试符号，未删顶层 API 符号或当前候选。配套 `historical-test-pdb-*` 收据证明源/配套 EXE、CRC/SHA、源删除读回。

上述追加后，后续目标回合新增净减少 **9,146,251,682 B**；本报告阶段累计 **26,162,024,372 B**；连同之前两轮累计 **33,937,992,698 B**。全部为有界逻辑载荷净值，不是整个磁盘物理释放量。

Formal CAS 原构建在子智能体容量错误后已确认进程不存在（`candidate-cas-process-readback.json`）；保留 15 个 recipe，根执行器只接续剩余三源，未重复启动并发 writer、未删任一源 ZIP。优化原工具减少冗余读取后人工恢复自测 PASS；运行中的已启动 helper未热替。

随后完成两批精确 synthetic pytest testcase 的恢复归档与展开清理：第一批 253 目录、1,372,527,461 B，ZIP+完整恢复 manifest 26,245,266 B，净减少 **1,346,282,195 B**；第二批 966 目录、3,498,944,644 B，ZIP+manifest 79,187,771 B，净减少 **3,419,756,873 B**。合计 1,219 目录、14,812 文件。独立审查指出归档后必须再核对完整目录集合，根执行器已补做全部文件集合/长度/SHA、空目录集合、ZIP 成员集合一致检查后删除，readback 全部源目录不存在。没有删除整棵 pytest 根、私有或 junction 测例；源 execution 收据和非选中 testcase 留在原处。

恢复档位于 Formal `.project-local/mig/storage-cleanup-current-20260930/`：`synthetic-pytest-selected-fixtures-20260930.zip`（SHA `c362e972e6c14ba662dc753f46aebdf244e41a1d40632e14677b95efd0349dfb`）及 `synthetic-pytest-second-fixtures-20260930.zip`（SHA `8ff33a0b30c19c8043fe002225f3a865caff44ca2080d7045e8c592f6517cebd`）。解压到 Formal `.project-local/runs/be268a2d33/` 恢复原相对目录，不加覆盖参数；如有现存同名内容先停止确认。配套 `synthetic-fixtures-*`、`synthetic-second-fixtures-*` manifest/preflight/readback/total 提供全部恢复路径和 SHA。历史 committed producer 只是 dirty 执行树的佐证，不冒充精确执行源码；全字节恢复保存用于避免凭这一佐证丢失数据。

该后续目标回合目前新增净减少 **6,638,836,748 B**；本报告覆盖阶段累计 **23,654,609,438 B**；连同此前两轮累计 **31,430,577,764 B**。后续 Formal CAS 尚未删除源，不计入净减少。

追加删除 9 组 deps 的 **直属** `.rlib/.rmeta`（1,533,915,120 B、1,218 文件）及 10 个同架构/同 SHA 原生 PDB 副本（338,882,560 B）。共 **1,872,797,680 B**、1,228 文件，全部路径 readback 不存在；保留的 65 个程序/符号及 10 个 canonical 哈希回读一致。依据 `cargo-deps-additional-allowlist.json`、`native-pdb-additional-allowlist.json`、`additional-intermediates-preflight.json`、`additional-intermediates-readback.json`。本报告覆盖阶段累计净载荷减少 **18,888,570,370 B**；连同此前两轮累计 **26,664,538,696 B**，仍不包含活跃 Formal CAS 的暂存增长或小型记录开销。

Green 官方 UV 维护完成，两处 exact cache 均 `No unused entries found`、exit 0；新增释放 0 B。两棵树的缓存有开发消费者；NuGet 与 UV/venv 存在大量硬链接，不能按每个路径载荷推算释放占盘。只使用现有 `uv.exe --no-config` 公开命令，没有读取或改动 Hermes 私有配置/状态。证据在 Green mainline `.project-local/mig/green-uv-prune-20260930.json`。

修正体积审计方法：按 `(volume, NTFS file identity)` 去除同一根内硬链接重复载荷；实际分配量查询使用属性句柄的 `GetFileInformationByHandleEx(FileStandardInfo)`。此前 `GetCompressedFileSizeW` 对普通未压缩文件返回的长度不能冒充按簇分配量，因此已替换。私有、权限受限、其他根的硬链接归属及并发 CAS 变化仍构成统计限制。

最新属性句柄盘点：Formal 路径逻辑载荷 56,202,706,184 B、去重载荷 55,119,664,239 B、可查询独立分配量 55,586,563,080 B；Green 路径逻辑载荷 10,452,256,383 B、去重载荷 8,259,907,159 B、可查询独立分配量 8,422,453,344 B。各根有 1 次 allocation 查询失败，另有 Formal 491/Green 40 个目录或文件权限错误，私有边界仍排除，Formal CAS 仍在写入。因此这些是本次可读取范围的有界观测，不能当作 Explorer 全目录或整个磁盘使用量；也不是从前一次 Explorer 大小直接相减得到的释放量。

剩余 be268a2d33 的数百 MB 子 run 经定位多为 pytest 生成 SQLite fixtures，不能误称重复 runtime。全 tmp 根含 `.git` fixtures 和 junction 测例，因此禁止整根打包/删除。正在逐个核实明确 synthetic producer 的 testcase 子目录，未知外部数据、私有和链接路径排除。

追加执行：17 个已审计 Cargo `debug/release/build` 构建脚本目录，1,966 文件，共 **986,781,161 B**，动态复核全部长度/文件数、无链接或保护内容、EXE/PDB 仅构建脚本命名后已删除，17 路径均不存在。最终程序、deps 和锁在范围外。本轮累计净文件载荷减少 **17,015,772,690 B**；三轮累计 **24,791,741,016 B**。新增 `cargo-build-allowlist.json`、`cargo-build-prune-preflight.json`、`cargo-build-prune-readback.json`。

Formal 历史 ZIP 的 CAS 构建仍在执行，已有恢复 recipe 但尚未完成全部 18 档，原 ZIP 均保留。其新增对象暂时占用空间，未计入上述已实现净减少；后续必须完成完整验证才允许删除原 ZIP。不能用本轮清理载荷合计推算当前文件夹完整体积。

完成上述清理后的最新有界元数据盘点：Formal 可读取载荷 58,602,572,065 B（58.60 GB），437,824 文件，491 个权限错误，跳过 86 个链接和 2,025 项私有边界；Green 可读取载荷 12,238,223,795 B（12.24 GB），118,372 文件，40 个权限错误，跳过 32 项私有边界。这是下限统计，不能冒充 Explorer 全目录体积；`.git` 等排除部分未计入。随后 CAS 新建期间体积会变化，需完成后再次盘点。

Formal `.project-local/mig/storage-cleanup-current-20260930/` 内保存 `round-total.json`、各 `*-preflight.json`、`*-verified.json`、`*-readback.json`，以及有跳过和错误统计的 `storage-final-metadata.json`。体积统计跳过私有边界和链接，存在权限错误时只能作为可读取范围下限。

恢复需要上述保留 ZIP及清单；已直接删掉的纯构建中间文件需按原工具链重建。整体清理仍在继续，未声明“清理干净”。

## 续轮实执行读回（2026-09-30）

- 26 个旧测试 PDB：删除源 1,137,795,072 B，恢复 ZIP/清单 230,124,963 B，净减少 907,670,109 B；26 个配对 EXE SHA 未变。
- 220 个已结束且失败的 synthetic pytest case：删除源 951,147,781 B，恢复 ZIP/清单 19,851,298 B，净减少 931,296,483 B；保留原始失败执行收据并归档七份收据副本，未将失败改写为成功。
- 18 个 staging 历史 ZIP：独立校验所有 CAS 对象 SHA 与逐版原 ZIP 全字节 SHA 后，fresh source SHA 校验并删除精确 allowlist 源文件。源 5,331,573,143 B，完整恢复库 585,506,912 B，净减少 4,746,066,231 B；18 源路径读回不存在。
- 本报告执行链净减少 32,747,057,195 B；加此前两轮累计 40,523,025,521 B（约 40.52 GB / 37.74 GiB）。此数为逻辑文件净减少，扣除了恢复库，不冒充物理磁盘空闲变化。
- CAS 恢复：使用 `.project-local/mig/candidate-zip-cas-20260930/zip_cas.py` 的 restore 子命令，指定同目录 store 与 `source-recipe-index.json` 对应 recipe；仅恢复到 recipe 原路径，拒绝覆盖现有文件。整个 store 必须一起保留。
- 失败 fixture ZIP 含现存执行收据副本，恢复应按 manifest 选择缺失 case 文件并逐文件验证 SHA；禁止盲目 Force 覆盖。
- 并行复核另找到 13 档历史 build ZIP 共 3,803,606,722 B，可进入下一批恢复校验；尚未删除，未计入节省。四档仍有消费/资格引用，保留原位。
- 17 项 fixture 缺结束收据：历史 synthetic producer 已核实，仍不满足删源条件；另三项已结束失败的小批次约 29.43 MB 尚未执行。
- 清理状态 PARTIAL；保留当前构建、源码修改、Green data、私有 Agent 状态及归属不明数据。未执行产品构建/测试、提交或推送。

最终本轮元数据读回：Formal 41,891,031,707 B（41.89 GB），Green 10,452,256,383 B（10.45 GB）。排除私有/Git边界且分别491/40项读错误，为可访问范围下界；不等同资源管理器全目录属性，也不代表系统/软件健康验收。

第三批旧测试符号实执行：138 PDB 源 2,814,115,840 B，ZIP/allowlist 634,018,034 B，净减少 2,180,097,806 B。归档逐成员SHA与CRC通过、原源 fresh SHA通过、138源不存在且138配对EXE SHA不变。恢复ZIP historical-test-pdb-third-20260930.zip SHA a1005c95fbd3d2cbe14af3c896c9430703c52fb985e23bf6185e5babbd209844；恢复至Formal原相对路径，拒绝覆盖。进程路径查询排除自身PID后计数0，未做完整open-handle检查。此操作不等同产品运行验证。

13档历史build ZIP实执行：源3,803,606,722 B，完整CAS恢复库491,866,843 B，净减少3,311,739,879 B。独立对象SHA+13版全字节原ZIP恢复SHA通过；fresh源SHA后精确删源，13路径不存在。store .project-local/mig/build-history-cas-20260930 必须整体保留；source-recipe-index.json给出逐版映射，zip_cas.py restore仅原路径且不覆盖。四档仍有消费/恢复引用的源ZIP保留。

Green旧验收r6精确重复生成输出：69文件589,401,256 B，全归档恢复ZIP/allowlist189,971,930 B，净减少399,429,326 B。每个源/保留mainline副本SHA匹配、归档SHA/CRC验证；69源路径不存在且所有canonical副本SHA未变。保留9个不同文件及目录，不删除整个旧bin。恢复ZIP green-r6-generated-duplicates-20260930.zip SHA a5a88a60c1be53df9ff3244df12438763b187cc4e5d10c8aecae84afbcba3846，可恢复至Green原相对路径，不覆盖现存文件。

Formal旧CAS整库打包实执行（覆盖此前散装恢复路径说明）：370,973文件/585,506,912 B被完整ZIP及gzip manifest替代，总551,693,260 B，净减少33,813,652 B。根独立fresh exact成员集合/长度/无reparse与恢复artifact SHA复核通过，原store已不存在。ZIP SHA909c3672d6f8c2f42db60402fd27ec73cf27a9f0fef7de7ee8991c38695175ae；gzip manifest SHA1abe2102ad7e69afd8a1ea95745d967f3e46fed5cd56aefb62772aa122e4b750。恢复18历史原ZIP之前，需将formal-cas-store-packed-20260930.zip全量解压至原 .project-local/mig/candidate-zip-cas-20260930（不覆盖），再按其source-recipe-index.json/zip_cas.py恢复某一原ZIP。直接压缩包重构18原ZIP SHA已全部验证，manifest保全部原文件SHA及目录集合。重点是减少37万散装文件，而非声称释放数GB。
小批3已结束synthetic testcase共29,429,760 B遇WinError5，官方同命令审批后仍拒绝源元数据，保留并记录small-ended-failed-fixtures-blocked.json；未改ACL/绕过软件。17项无结束证据仍保留。

新13版CAS整库打包实执行（覆盖此前build-history散装恢复路径说明）：266,266文件/491,866,843 B由459,041,791 B完整ZIP及11,736,415 B gzip manifest替代，净减少21,088,637 B。Root独立fresh成员集合/长度/无链接+两恢复artifact SHA再次通过，原store不存在。ZIP SHA2f301dd9fb48ea56f5b6c38103af57c1bf3c7be4785c5411df7d860cb307fb94；manifest SHAb635faf64a8aea32b2cbe66409e3ffb3612faf111749a0c85143e5db25878ce8。恢复旧13版ZIP前先将build-history-cas-store-packed-20260930.zip全量解压到原 .project-local/mig/build-history-cas-20260930（不覆盖），再用内含helper/index逐版恢复。两整库替换共删除637,239散装文件、净54,902,289 B；未假称这些文件数代表原始项目净文件减少（这些是本清理生成的恢复对象）。30个精确已空候选父目录也已删除，详empty-candidate-parents-readback.json。

当前候选run精准续清：1453项Cargo unused incremental 141,069,874 B，fresh全文件SHA+无编译process+25锁exclusive-read通过后删除，parent EXE/元文件不动。首次目录count guard因51包含root而50child计数差阻止执行；确认口径后修正含root再全部preflight，不通过则无删除。
六publish的1340重复生成展开文件1,293,608,242 B已删除，新增recovery映射allowlist731,573 B，净1,292,876,669 B。保留ZIP中225 desktop成员逐SHA/CRC通过、fresh源SHA及精确集合/no process/no links通过，保留10不同DLL/PDB逐SHA未变。只验证选定desktop成员，不读混合private/data成员、不宣称整ZIP所有成员CRC。恢复时由publish-archive-backed-allowlist.json对应source/archive_member从保留audit-final ZIP恢复缺失文件、不覆盖。保留ZIP SHA107507ddfd226d490f3c3f4fa2d322325e69ad2ac441c971c18ce322c0d63226；全部所删source不存在。

















## 2026-10-01 清理后定向契约验证

通过项目 `scripts/runtime/dev.py --pytest` 运行现有开发路径、外部工具链、Green manifest 与 scheduler launcher 四组测试。首次run `cleanup-boundary-verification-20261001`：34 passed、2 failed、9 subtests passed，exit1；两项为嵌套临时目录 WinError206 长路径。仅改用短run-id `c1` 重跑失败两项：2 passed、exit0。保留两次原执行收据，不改变系统长路径设置。此为 synthetic 契约验证，不证明实际安装态/产品启动/用户数据库健康，后二者 NOT_EXECUTED。

独立 reviewer 重新核对本轮四项释放净1,147,330,589 B、源不存在、恢复包/保留收据/关键DLL SHA通过；SDK迁移5577文件和814目录全量一致，净磁盘释放0。远端只读连接经正常批准执行路径恢复；2026-10-01读回 main=df1a0d59961d0ced18c99dc3e31a5c5bee4a4eac，当前本地HEAD=43c2cafa1bfe57a862e90c5a77dc16832264babd，codex/Audit远端分支未发现。本轮尚未提交或上传，不声称双端一致。

## 2026-10-01 历史 mono 候选实际清理

精确历史 `aaos-ui-theme-20260926-02/artifacts/candidate` 已完整归档后删除，1195源文件/58目录/264,282,128 B；新恢复ZIP+manifest+verified94,538,560 B，净逻辑减少169,743,568 B。prune exit0、原目录absent、恢复SHA及9个原UIA/截图/snapshot/执行等兄弟证据SHA不变。恢复使用 `aaos-ui-theme-candidate-packed-20261001.zip` 与对应manifest，精确原路径且不覆盖，原执行收据保留。累计净逻辑减少56,218,060,009 B；仍需继续审计，尚未最终交付或上传。

## 2026-10-01 历史 worker Lib 与 runtime-copy2 实际清理

- 历史 `r5-ci-worker-bootstrap-network/worker-env/Lib` 7548文件/826子目录/285,210,772 B已完整归档后逐文件删除。原Lib不存在、恢复ZIP和三个支持元信息原SHA保持；恢复ZIP+manifest+verified102,922,473 B，净逻辑减少182,288,299 B。恢复入口 `worker-bootstrap-lib-20261001.zip` + `worker-bootstrap-lib-20261001-manifest.json`，精确原路径且不覆盖。FastAPI `.agents/skills/fastapi/SKILL.md`由distribution RECORD精确长度/hash和无额外文件证明属于安装包静态材料，不作为私人Agent状态；未回显正文。
- 历史 `36a01f79bed8/artifacts/runtime-readonly-copy2` 17948文件/2215目录/573,211,822 B已完整归档后逐文件删除，原根不存在。新恢复ZIP+mapping+verified209,599,480 B，净逻辑减少363,612,342 B。全部ZIP成员CRC/SHA及fresh源集合通过；原execution/snapshot/邻runtime copy/desktop-publish保留。恢复入口 `runtime-readonly-copy2-recovery-20261001.zip` + `runtime-readonly-copy2-recovery-mapping.json`，移除member的runtime-readonly-copy2/前缀后按映射精确原根恢复，禁止覆盖，重核全部SHA。原复制命令仍UNKNOWN，不将公共Python三件套hash一致误写成全树重复。
- 本续轮三项实际净逻辑减少715,644,209 B，累计56,763,960,650 B。物理磁盘回收UNKNOWN；净值包含扣除完整恢复载荷，没有把保留的恢复包当释放。
- 三组alternate pytest目录可访问712,828,385 B；生成布局确认，但artifacts/execution.json均缺失，原始整体结束状态UNKNOWN。私人命名项和junction排除；整根清理资格0，暂保留。详见本地 `alternate-pytest-three-review.json`。未把无进程引用或历史名称当原始结束证明。

## 2026-10-01 a04 历史构建实际清理

a04-v3-399eb0e8/artifacts/desktop-build 的248文件/14目录/138,320,541 B已完整归档后删除，原根不存在，恢复包SHA与原executionSHA保持。新ZIP+manifest+verified59,084,519 B，净逻辑减少79,236,022 B；累计56,843,196,672 B。恢复使用a04-desktop-build-packed-20261001.zip+manifest，精确原路径且不覆盖。先前prepare进程计数1是包含精确source字面量的只读query自身，该命令已终止；最终动态scope读取query计数0，root prune再次fresh进程门禁0。原历史dirty TESTED_LOCAL_BUILD证据保持，不冒充当前安装态验证。

Green mainline36个NuGet版本均有当前依赖/保留SDK引用，completion marker完整，无已证明可删旧版本；uv主缓存有当前dev引用。较小专用缓存另行核验，不将旧版本名称当无用。缓存审计不等于freshrestore或产品启动成功。

## 2026-10-01 872个ZIP成员精确重复项清理

4个已结束历史编译run内872单链接生成库/符号523,732,576 B已逐文件删除；217unique恢复成员CRC/SHA与fresh源逐项一致。两保留原ZIP wholeSHA不变，48个不同/current/registered/API sentinel和4原execution收据SHA不变。只删除清单文件，无整目录删除。恢复allowlist+verified796,765 B，净逻辑减少522,935,811 B；本续轮a04+872共602,171,833 B，累计57,366,132,483 B。

恢复依据ended-compiled-zip-872-20261001-allowlist.json中的archive、archive_member、restore_target；保留原va5de4b13与vheadd1bb2b99 ZIP依赖，不得误当无用重复包删掉。提取到精确原路径，不覆盖，逐文件SHA。历史run重新执行需先恢复，历史receipt保持，不将清理当产品运行PASS。

## 2026-10-01 第八合成批与Green历史缓存实际清理

第八批1728精确合成目录、2124文件519,085,340 B完整归档验证后删除；36原执行收据SHA不变，ZIP/manifest SHA不变，所有源目录absent。恢复ZIP+manifest+verified13,353,397 B，净逻辑减少505,731,943 B。恢复入口synthetic-eighth-fixtures-20261001.zip+manifest，原路径且不覆盖。Current KB测试autouse conftest初始化fresh-empty tmp DB、literal测试数据和exactset仅一个DB文件，是归属依据；全局VectorDB和72个source-shape不符排除项未动。历史成功/失败dirty状态不变。

Green mainline历史uv-ui-audit缓存6个wheel分发节点中的508精确普通文件6,645,613 B已归档后删除，完整RECORD归属SHA/size、ZIP CRC/SHA、fresh源集合、installed env无reparse/.pth cachepointer与当前进程0通过。新ZIP+mapping+verified2,071,520 B，净逻辑减少4,574,093 B。原failures.txt只metadata前后核对，不读正文、不归档、不删；第7未知cached venv、索引/http/msgpack/.lock/scaffolding保留。恢复uv-ui-audit-distributions-recovery-20261001.zip到mapping.source的精确成员原路径，禁止覆盖并逐SHA核对。硬链接/copy模式UNKNOWN，物理节省UNKNOWN；没有whole cache clean或改现用环境。

两项本续轮净逻辑减少510,306,036 B，累计57,876,438,519 B。目标仍PARTIAL；剩余分类、实际产品验证与最终上传尚未完成。
