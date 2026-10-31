# v3.1 补件独立复核

日期：2026-11-01。审计时本地 HEAD `0ed5bcbf5bda828ebd7f2ad3c196e6046a8e31f6`。范围为指定补件、原 v3、相关历史 Git 对象及当前两份检测器源码；没有重演云端运行、执行附件脚本或修改产品。

判定：`ACCEPT_AS_SCOPED_SUPPLEMENT_EVIDENCE`。原件身份和候选源码可核，定向日志支持相应范围；不能升级成当前本地实施、Core 端到端、Windows 原生或 Owner 接受。原 v3 审计作为历史记录保留，本页说明补件后的关闭程度。

## 原问题逐项复核

| 原编号 | 补件后结论 | 核验及仍有限制 |
| --- | --- | --- |
| V3-F01：当前补丁适用性 | `OPEN_LOCAL_APPLICABILITY`；补丁角色说明已补齐 | 主 patch 仍为原基线 31 路径＋2 新测试，6 份中间制品不可叠加。12 次云端 apply 记录均为 0，输出 hash 匹配原 v3 最终清单；本次未重演这些 apply。本地 13 路径不适用是原审计时点结果，未被此说明解决。 |
| V3-F02：实际模型与回执绑定 | 云端候选可接收；当前产品未修复 | 真实 ORT 反例日志支持旧版本确有 caller/env 模型与回执错绑。两候选文件可从历史对象＋v3＋v3.1 patch 在内存精确重建，4 份前后像 SHA 全匹配。实际 model/config 同份 bytes、缓存身份和 RLock 语义合理；42 tests＋47 subtests 为有范围的云端结果，不是本机实跑。 |
| V3-F03：full-suite 覆盖原证据/失败后用旧输入 | 云端控制流候选可接收；本地未应用 | 新 run、partial 导出、非空校验、独立 venv 和必要前置失败停止均已体现。8 个故障/成功场景的逐步退出码与结果表一致；交付脚本 SHA 匹配最终被测字节记录。root 另用自写内存解析器从原 v3 脚本应用文本差异，结果逐字节等于交付候选；未执行脚本。 |
| V3-F04：环境同一性 | `PARTIAL_CANDIDATE_ONLY` | 新 full-suite 候选避免旧 venv 和 system-site 继承；旧顶层 `reproduce.sh` 的 `--system-site-packages` 与固定输出风险仍在，补件明确未修。控制流 stub、真实 venv/config 解析不等于全业务或完整机器环境重现。 |
| V3-F05：两份 stdout 缺失 | 索引勘误可接受；原日志仍 `MISSING` | 补件未造空 stdout，也未把新运行冒充旧日志；4 份 exit/stderr 旁证与原 v3 字节一致。历史 stdout 是否生成/是否为空仍 `UNVERIFIED`。独立 errata 解释悬空引用，不覆盖原索引；退出 0 不能恢复 stdout 内容。 |
| V3-F06：22/37 原 template 缺件 | `CLOSED_ORIGINAL_TEMPLATE_IDENTITY` | 两 CSV 的字节 SHA 精确匹配早于本补件的 v3 登记。格式 22/22、平台 37/37 的身份文本及顺序与最终映射一致。原模板结果为 `NOT_RUN`，其他多数栏为空；最终新增说明与有限 `PARTIAL` 不声称原表每个值都未变，更不构成全面运行验收。 |

## 原件和源码身份

补件 728,330B、1,245 文件、展开逻辑大小 2,154,265B；所有成员 CRC/SHA 和内部 1,244 项清单一致，无漏列。原包绑定实算匹配，补件里的 v3 输入清单/命令索引副本与原 v3 对应成员逐字节相同。内部校验只证明字节关系，不是来源签名或第三方执行认证。

| 补交原模板 | 大小/数据行 | SHA-256 |
| --- | --- | --- |
| `05-format-results-template.csv` | 814B / 22 | `ebd1180d8fbd702405becf55576e947affefd5c8386af35f5a604c6050bdb502` |
| `06-interop-results-template.csv` | 1,276B / 37 | `c33fa9c6c34bf22a2171bd07df751754c7851c0c57977d6fe93076a82a7ce213` |

detector 增量 patch SHA 为 `49d86411104b3beb885a925b491d5cb7d37201fbc34163ad9efc773c2002d35b`，只改 `shared/file_detection.py` 与 `services/python-workers/document/worker_detect.py`。候选 SHA 分别为 `bc06fb8e2ee5175a0952957bd906f7021439833afac2cc5cb344435033f33bdc`、`4d08f83570042606ad88d72c7c94b851612d573057d29ec179bccc1649b76f56`；独立内存重建与 source-binding 相符。

当前这两文件仍等原 8d367bac 基线；shared 恰等 v3 前像，worker 尚无 v3 的固定安装目录加载修正。因此 v3.1 增量不能直接作为当前树的完整修复；未来需选择性承接 v3 那项定位修正及 v3.1 身份绑定，保留本地其他成果，不整包覆盖。

## 定向证据的实际含义

- `detector/logs/baseline-confirmed.*`：真实 ONNX 计算图仅更改 metadata 形成不同有效字节，另用 config 的标签映射观察模型选择；原反例退出 0 表示错绑已被观察，不表示原实现正确。不是模型准确率实验。
- `detector/logs/final-scope.*`：42 testcase，分为新身份 9＋worker 7＋shared 10＋transport 16；另 47 subtests，XML 的 89 为两者相加。前轮 15/16/26 或独立 2 项是重叠记录，不重复累计。
- 修复让同份 model bytes 进入 ORT、同份 config bytes 进入 JSON 解析，再从相同 bytes 记录双 hash。旧 session 在同路径文件替换后继续返回旧身份是已声明的缓存策略；不同路径/新进程才加载新会话。坏模型不冒充成功；模型 profile 不因 hash 自动获得上游认证。
- `reproduce/evidence-final`：export 失败 23、空导出 1、venv 失败 31、缺解释器 127、安装失败 42 都阻止后续；单 gate 失败保留其他 8 门并最终退出 1；两次成功为不同 run。缺 repo 启动另验，不造业务成绩。
- 1,914 项前后 hash 清单一致，是云端保存记录的独立比对；本机没有持有并再次计量这 1,914 个原文件。full-suite 候选 SHA `f8b62fed9f12986298fc0e27cdba1df2e8a2ba3e967d95a11e397138338ee3a9`，patch SHA `fbca2ba7560590531d7856719b3fae9c3b743927ada07049029a33f85e6094b3` 均匹配交付绑定。

## 保留的证据限制

**S31-E01：日志生成器版本未绑定。** `detector/run_logged.py:3,6` 当前代码用 UTC `isoformat()`，应直接输出 `+00:00`；历史 `final-scope.command.json`、`patch-readback.command.json` 却为 `+08:00`。可能是历史 wrapper 修订或显示转换，目前缺版本/转换说明，不能断定原因。XML 的 `-07:00` 与 JSON 的 `+08:00` 换算为同一 UTC 时刻，没有已证实的执行时刻矛盾，也没有据此认定伪造。候选源码/patch 的 SHA 与计数仍成立；不能声称全部 command 记录由当前随包 wrapper 原样生成。补说明即可，不因此要求无差别重跑全套。

新 receipt 字段的 Core 端到端、正式 worker 安装、Windows/ORT、真实模型质量、H5P、完整 J1/CL/R6 及 Owner 接受不在本次新增资格内。最终测试与代码的运行时绑定依赖近邻 source-binding/patch-readback，不是防篡改 attestation。本次没有运行补件脚本、安装依赖、联网或上传；产品源码不变。

证据路径/原 SHA/两路审计见 [MANIFEST](MANIFEST.json)。归档和原模板补齐已完成；本地实现及产品进度仍沿[活动指针](../../../docs/current/AAOS-ACTIVE-EXECUTION.json)和[唯一执行记录](../../../docs/current/AAOS-UI-FIRST-EXECUTION-20261009.md)，原 v3 历史结论不覆盖改写。
