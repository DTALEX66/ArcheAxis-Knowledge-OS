# ArcheAxis 清理与交接（2026-10-01，持续更新）

## 状态与授权

PARTIAL，目标仍 active。用户授权审计后删除无用项目输出、迁移有用资产到归属目录；禁止访问E/F，保护C/D系统软件、私人Agent状态及用户修改。完成条件是没有剩余已确认可清理项、项目关联性与所需验证通过、全部允许上传的源码/摘要/交接提交并回读远端SHA。本文件不是完成声明。

## 当前已执行结果

累计净逻辑文件载荷减少58,021,000,876 B（58.02 GB），含本报告执行链50,245,032,550 B及此前两轮7,775,968,326 B。删除源58,278,093,724 B，保留恢复载荷8,033,061,174 B，二者差额是本报告执行链净值。不是物理磁盘回收统计；少量审计收据和脚本不计。

最新元数据可访问范围：Formal25,169,438,491 B/348276files；Green8,957,443,149 B/114508files。分别491/40读取错误，private/Git与链接排除，不能等同Explorer全目录体积。

最新三项实际清理：历史mono候选1195文件净169,743,568 B；历史worker Lib7548文件净182,288,299 B；runtime-copy2 17948文件净363,612,342 B。完整ZIP CRC/SHA、精确集合与fresh源核对后删除，原根不存在，恢复和保留证据SHA读回通过。

另有Green SDK5577文件/814目录807,336,133 B迁到 `D:\All projects\OS External Configuration\10-toolchains\dotnet-sdk-10.0.401`，全量哈希相同，原副本不存在。SDK10.0.401/Runtime10.0.12读回，既有10.0.400保留。只迁所有权，净磁盘载荷减少0。没有改变PATH、ACL、注册表或系统服务。

## 恢复边界

恢复载荷和详细收据保留于 Formal `.project-local/mig/storage-cleanup-current-20260930`，不得上传缓存或私有运行时正文。

- 新候选增量恢复依赖父包 `ui-history-direct-packed-20261001.zip` 与 `staging-ui-delta-packed-20261001.zip`、proof、helper及zip_cas边界依赖；父包仍有引用，不得删除。
- 历史mono使用 `aaos-ui-theme-candidate-packed-20261001.zip` 与manifest。
- worker Lib使用 `worker-bootstrap-lib-20261001.zip` 与manifest；三个支持元信息原件保留。
- runtime-copy2使用 `runtime-readonly-copy2-recovery-20261001.zip` 与mapping，按精确source映射还原，不将邻runtime-copy当完整等价副本。
- 其他批次恢复方式见历史清理报告；原始执行收据保持原SHA和原失败/dirty语义。

任何恢复都禁止覆盖现有文件，逐文件SHA核对；先恢复依赖对象库再重建旧ZIP。若回读不完整，保留恢复包并停止该范围继续删除。

## 验证与未完成

项目既有开发路径、外部工具链、Green manifest、scheduler launcher定向synthetic契约：首次34pass/2fail/9subtests，2项WinError206长路径；短run-id重跑失败两项2pass。两次收据保留。SDK CLI不是产品运行验证。实际安装态产品启动、用户数据库健康、全部源码受影响验证、最终上传/远端回读仍未完成。

剩余大缓存与历史构建正在逐项确认。三个alternate pytest目录约713MB缺整体原始结束收据并包含排除的私人命名项/链接，不具整根删除资格。未知归属All/WAL/SHM/lock、C/D END、历史数据库世代、当前默认及注册worktree输出、具有依赖引用的缓存保留。三个批准执行身份仍拒绝的WinError5范围约29.43MB保留，不改ACL。无引用搜索不能单独证明可删除。

本次继续清理复核：历史138 PDB、212 EXE、872 ZIP-backed精确删除集均已不存在；没有发现这些已批准集合中漏删项。223旧Desktop集合剩余4个mutable canonical DLL（1,566,064 B）原收据未授予当前删除资格；96generated集合剩余7个canonical硬链接（61,312,685 B）原收据明确KEEP，删除名称亦不等于回收其载荷。当前默认be268、注册53、现役dotnet routing及索引va5/va647继续保留。这是有限编译输出审计收敛，不代表所有剩余目录无用或产品验证完成。

## Git交付

本地分支codex/Audit，当前HEAD43c2cafa1bfe57a862e90c5a77dc16832264babd；2026-10-01远端main只读回读df1a0d59961d0ced18c99dc3e31a5c5bee4a4eac，codex/Audit远端未发现。正常Git访问路径已连通，本轮尚未commit/push，不声称双端一致。

既有19项tracked修改及此前未跟踪成果保护。本轮新增共享SDK路径索引、SDK迁移交接及本清理交接；OS External只最小增补忽略规则和项目工具注册表。上传应按精确任务文件集合进行，排除恢复包、缓存、运行数据库、日志、凭据与私人状态。最终必须分别记录本地提交SHA、远端分支SHA与验证范围。

追加已执行：a04历史构建净79,236,022 B；872个精确ZIP恢复成员重复生成文件净522,935,811 B。两项root readback PASS。新恢复依赖包括a04归档及872项allowlist引用的原va5/vhead ZIP，不能当旧包删除。上述体积已由两项删除后的最新metadata收据回读。

第八合成1728case和Green历史缓存508分发文件现已归档后删除，净510,306,036 B，root readback PASS。恢复依赖见历史报告最新条目。缓存failures/未知venv/索引原件保留，未执行whole cache clean。

第九合成1296case（3960文件）已删除，净61,314,716 B；Green三个已迁移包的3157个重复文件已删除，原根不存在，Formal归属副本全量SHA/集合一致。该项账本净83,247,641 B；独立复核另计722 B回读收据时净83,246,919 B。累计账本采用前者并统一排除审计收据，不混用口径。四批独立复核见本地cleanup-selected-batches-independent-readback.json，恢复ZIP逐成员CRC/SHA及原执行收据保留通过。没有把仍有引用的恢复包当缓存删除。

前端源码契约批次c2为275pass/49fail；c3复核49项仍失败，不能宣称项目已健康。已最小修复直接进入复习时首次加载被跳过，Formal c5及Green c6各1pass；这是源码契约证据，产品构建/原生运行尚未验证。其他失败包含旧断言和待核实实现问题，未统一豁免。

继续交付验证：命令面板补齐证据库、原创、人类学习、机器学习及工作区路由，旧名称作为alias保留；c7先失败、c8定向2pass。SDK10.0.401经现役build/dotnet项目命名输出根，cc的MSBuild /t:Build退出0并生成Debug/net10.0/ArcheAxis.Desktop.dll。c9/ca因缺恢复清单、cb因参数解析失败收据保留，不隐藏。编译通过不等于产品启动或安装态健康；其余源码/原生验收仍未完成。

2026-10-01 最新Git只读与fetch核对：当前HEAD是origin/main祖先，left/right=0/27；远端包含新增backend和文档整合，不能把当前dirty源码直接覆盖远端。tracked改动与远端变动的交集为docs/DOCUMENTATION_AUTHORITY_INDEX.md；交付需保留远端新backend及本地UI/清理成果，解决该文档真实三方差异。尚未merge/reset/commit/push，原工作文件未改变。最新元数据已在第八批/508缓存删除后回读。
