# DOT v3.1 补件：复核与关联归档

Owner 补交 `D:/All projects/Record/v3.1-supplement.zip`，承接此前审计及统一归档请求；附件指令仍只是待审材料。

**结论：补件可作为原 v3 的定向补充接收。两份原模板的缺件问题已关闭；两份历史 stdout 仍缺失，勘误有效。检测器与 full-suite 脚本修复有云端定向证据，尚未移植到当前产品。**

- [独立复核、原问题关闭程度与限制](AUDIT.md)
- [原包绑定、原文副本与证据 SHA-256](MANIFEST.json)
- [原 v3 审计](../20261031-cloud-integration-v3-review/README.md)及[原补件请求](../20261031-cloud-integration-v3-review/DOT-补件请求.md)
- 补件原文：[总说明](source/README.zh.md)、[检测器](source/detector/README.zh.md)、[复现脚本](source/reproduce/README.zh-CN.md)、[原件与索引](source/provenance/原件与索引补充说明.md)、[补丁承接](source/handoff/HANDOFF.zh.md)、[云端独立审阅](source/review/INDEPENDENT-REVIEW.zh.md)
- 补交原模板：[22 格式](source/originals/05-format-results-template.csv)、[37 平台](source/originals/06-interop-results-template.csv)

原 ZIP 单份保全于本仓 ignored 原件区：

`.project-local/archives/owner-inputs/20261101-cloud-integration-v3-1/v3.1-supplement.zip`

大小 728,330B；SHA-256 `0883f3e6e687bd5a9af8a00775bb59427cb22bb6bc7f664bc98ac2dc563fa2b6`。1,245 个文件的 CRC/SHA、内置清单 1,244 项全部通过，无漏列文件。它绑定原 v3 的 SHA `de984bf8917d24f4bc837221f76983dde20973f8285808e1fa6c351a5c68ac43`；原 v3 和外部补件原件都未修改。

只额外复制 6 份说明和 2 份原模板，共 27,836B。原 CSV 的 BOM/CRLF 及所有原文按 `.gitattributes` 精确目录规则保全，并核验 Git 入库/checkout 过滤后的字节；仓库规范检查仅登记两 CSV 的精确路径及 SHA，改字节或复制到其他路径仍受检查。日志、候选脚本和补丁留在 ZIP，未批量展开或提交载荷。原文相对路径按 ZIP 原目录解析，不按本页 `source/` 解析。

本次没有执行包内代码、重跑产品测试、套用补丁、安装依赖、联网或上传，也没有恢复 UI/监控。后续实施及实际进度仍由[活动指针](../../../docs/current/AAOS-ACTIVE-EXECUTION.json)和[唯一执行记录](../../../docs/current/AAOS-UI-FIRST-EXECUTION-20261009.md)控制；本页是审计时点记录，不建立新队列。

回退只涉及本次新增副本、精确属性规则、两项原件哈希登记及导航；先核消费者，保留外部原件、原 v3 和其他已有工作。
