# DeepTutor / OpenMAIC 接入与全部未完事项交接

2026-11-01（Asia/Shanghai）。Owner要求拆分后续任务，尽快将指定目录内两个平台源码并入AAOS，提供新会话完整提示词，并明确“还有未完成的任务”。这是本轮实现工作的选定来源，不替代既有产品身份V2.3、唯一闭环V3或原CL/J/X任务身份。

- [新会话完整执行提示词](新会话完整执行提示词.txt)：复制到新的本地Codex会话执行。
- [全部后续工作拆分与验收](FOLLOWUP-WORKBREAKDOWN.md)：两个供体的接线工作和15组既有欠账；是交接时点拆分，不是第二实时队列或进度源。
- [原件绑定](MANIFEST.json)：两份ZIP已在本仓`.project-local/archives/owner-inputs/20261101-learning-platform-sources/`，不依赖外部“新建文件夹 (2)”继续存在。原件Git忽略，迁移本地完整项目必须带归档目录。

| 源码 | 本仓原件SHA-256 | 文件数 | 本轮资格 |
| --- | --- | ---: | --- |
| DeepTutor 1.7.1 | `9614f50cfe2cef476c25ad378631f5a5d15a7c0f3f54ef1fa3180c8f41286262` | 4471 | 原字节/SHA/全部成员CRC通过；选定源码静态审读；未安装/运行/并入 |
| OpenMAIC 1.3.0 | `7cea2a5850083bdc261114d8433daa6ea24c1c0157beae3939a2e9fac3a98f40` | 3830 | 原字节/SHA/全部成员CRC通过；选定源码静态审读；未安装/运行/并入 |

原件共134,466,253B；未整包展开或引入node_modules、模型、第二知识库。源码主许可证分别为Apache-2.0与MIT，已对照精确本地成员及[DeepTutor v1.7.1官方LICENSE](https://raw.githubusercontent.com/HKUDS/DeepTutor/v1.7.1/LICENSE)、[OpenMAIC v1.3.0官方LICENSE](https://raw.githubusercontent.com/THU-MAIC/OpenMAIC/v1.3.0/LICENSE)。上游发布页为[DeepTutor](https://github.com/HKUDS/DeepTutor/releases/tag/v1.7.1)、[OpenMAIC](https://github.com/THU-MAIC/OpenMAIC/releases/tag/v1.3.0)。主许可证身份不代表全部依赖、字体、媒体和模型权利已审清，选用时保留适用声明与修改记录。

接入以现有Core对象/任务、正式Tauri/React宿主及隔离provider/worker为基础。DeepTutor现有C013及1.5.17桥是历史候选起点，旧Python/SQLite写入资格、Avalonia说明和`.hermes`路径不得复活。OpenMAIC已有quiz-only/v1导入链；优先吸收generation/DSL/renderer并保留v1 reader，不以整站Next/Postgres/Agent系统替换AAOS。模块实际API、约束和验收见拆分表。

最新定义继续读取根[AUTHORITY](../../../AUTHORITY.md)、[13组对照](../../../docs/history/owner-dialogue-20261101-current-goals/README.md)、[身份V2.3](../../../docs/truth/PRODUCT_IDENTITY_V2.md)及[唯一闭环V3](../../../docs/truth/CLOSED_LOOP_DEFINITION.md)。当前控制沿[活动指针](../../../docs/current/AAOS-ACTIVE-EXECUTION.json)，实际进展只记[唯一执行记录](../../../docs/current/AAOS-UI-FIRST-EXECUTION-20261009.md)。新请求选定两源码接入及未完项的接续拆分；UI全面重排、监控、发布、Green替换和真实库覆盖不随此自动恢复。

本轮完成归档、静态接缝核查、任务拆分与提示词；产品实现须由后继会话实际落地，不能以本页或ZIP归档宣称并入已完成。131治理测试、878本地来源定位、45近期包和125恢复成员均为此前各自回执，不是新供体产品资格。

## 2026-11-05 Owner 指令：全量吸收并全量融入

Owner 明确：“两个项目先全量吸收进来，全量融入进来”。这条指令覆盖此前“只选适用能力”的窄解释，但保留以下产品边界：

- Rust Core 仍是 SQLite/CAS 唯一 canonical writer；不新增第二业务库、第二调度器或通用 Agent Runtime。
- 全量吸收指**完整上游源码快照**进入本仓；不等于两套平台整站替换 AAOS，也不等于功能已完成。
- 全量融入按 `FOLLOWUP-WORKBREAKDOWN.md` 的 INT-DT-01—03、INT-MAIC-01—05、INT-QUAL 逐项推进，每项仍按真实 Core、真实 worker、安装态与 Owner 接受分层记录。

### 已完成的源码吸收

| 源码 | 快照目录 | 文件数 | 逐文件身份 |
| --- | --- | ---: | --- |
| DeepTutor 1.7.1 | `services/learning-providers/deeptutor/upstream/DeepTutor-1.7.1/` | 4,471 | `DeepTutor-1.7.1-SOURCE-MANIFEST.json` |
| OpenMAIC 1.3.0 | `services/learning-providers/openmaic/upstream/OpenMAIC-1.3.0/` | 3,830 | `OpenMAIC-1.3.0-SOURCE-MANIFEST.json` |

- 两份快照均从本仓归档 ZIP 解包，归档 SHA-256 与 `MANIFEST.json` 一致；没有引入 `node_modules`、模型权重、运行数据库或第二知识库。
- 每个快照附 `README.md` 与逐文件 SHA-256 清单；清单绑定归档哈希、许可证成员与文件计数。
- OpenMAIC 上游 `.gitattributes` 会把 3 个 CRLF Markdown 归一化为 LF；清单记录仓库快照哈希并单列该归一化，归档仍保留原始字节。
- 上游源码默认不参与普通文本搜索（见根 `.ignore`）；需要时按精确路径读取。

**仍未完成**：两套平台的完整功能接线、跨消费者资格、同候选安装态与 Owner 接受。源码在仓内只表示“已吸收”，不表示“已融入”或“已验收”。
