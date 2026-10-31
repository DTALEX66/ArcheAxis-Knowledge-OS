# 云端整合 v3 独立审计

审计日期：2026-10-31至2026-11-01。范围为指定 ZIP 的完整性、日志与计数、源码身份、映射保留、补丁当前适用性及复现脚本静态检查。没有独立重演云端运行，没有执行包内代码或运行产品测试；包内日志的一致性不等同第三方执行认证。

**判定：`ARCHIVE_VERIFIED_EVIDENCE_SUPPORTED_WITH_LIMITS`。当前本地候选和整体产品仍为 `PARTIAL`。** 原包内部一致，核心测试数量有依据；“同源码不无差别重跑”的建议合理，但前提是相关源码、合同、依赖和环境确实相同。本地已经发生较大变化，不能直接继承成当前版本的 PASS。

## 1. 原件与当前源码身份

- ZIP 为 10,410,545B、1,874 个文件，展开逻辑大小 47,377,388B；未批量展开。各成员读取时 CRC 与 SHA 均已核验，内部 manifest 的 1,873 项全部匹配，无悬空或漏列文件。内部校验证明字节一致性，不证明来源签名或运行真实性。
- 云端基线 `8d367bac4a85bebfbb523503678ade0838faa73e`；审计时本地 HEAD `70dfc397857f20c6eba5facc87e14cf55dcd3f6e`。
- 云端最终清单 5,129 个文件与本地跟踪文件逐字节比对：4,690 相同、437 不同、2 个新增前端测试不在本地跟踪集。主补丁涉及的 31 个路径均不等于云端最终字节；这不表示全部冲突，只表示不能声称当前已具有云端最终实现。
- 31 个路径中，本地 17 个相对云端原基线已有变化、14 个未变。只读 `git apply --check -` 退出 1，13 个路径不适用；未实际 apply、checkout、reset 或替换文件。

## 2. 测试主张核验

以下是对历史云端证据的交叉核验，不是本机重新执行。

| 报告主张 | 核验依据与边界 |
| --- | --- |
| Python 5,780 passed、105 skipped、4 deselected、379 subtests | `logs/full/python-delivery.stdout:221` 与 JUnit 一致。普通 testcase 5,885 个，其中 105 skip；另 379 subtests。不能把 XML 的 6,264 当作普通测试通过数。 |
| Rust 208 组、1,025 passed | `logs/full/cargo-workspace-qualified.stdout:45–2064` 的 208 条汇总独立加总一致；是 Linux workspace，不能代表 Tauri/Windows。 |
| 前端 1,983 passed、4 skipped | `logs/full/frontend-delivery.stdout:263–264` 一致；是 jsdom，不能代表浏览器视觉或原生窗口。 |
| 生产组件连接真 Core 8 项 | `logs/full/frontend-real-delivery.stdout:4–8` 与两组 HTTP 回执相互支持；仍是归档的 HTTP/jsdom 运行，未在本次重演。 |
| 105 个 skip 中 42 项窄补、63 项条件保留 | skip 台账与 XML 的 105 个唯一测试键逐项一致；补测分组日志支持所列结果，不把 42 重复加到 5,780。 |

最终 5,129 文件相对 Python 主套件候选恰有 6 项晚改：CI workflow、4 个 Core probe、`tests/test_live_chain_probes.py`；其余 5,123 项相同。附件明确披露 CI 87 项、Core 7 项和静态门的补验，不能转述成“最终每个文件都重新跑过全量”。实际执行回执绑定历史 dirty patch，不能改绑为本地 HEAD。

## 3. 具体问题与处理建议

| 编号 | 等级 | 事实、影响与后续处理 |
| --- | --- | --- |
| V3-F01 | P1：集成前阻断 | 当前主补丁检查有 13 个路径不适用，涉及现有导航、课程错误诊断、资源目录和测试。应按功能选择、重基并保护当前成果；不能整文件覆盖解决冲突。`patches/aaos-isolated.patch` 已包含 detector、资源重绑和安全锁候选，不能再叠加三份子补丁。 |
| V3-F02 | P2：模型回执绑定待验证 | 候选检测器从 worker 安装位置加载实现，但 `worker_detect.detect` 仍用 caller `repo_root` 下的模型计算回执 hash；实际 detector 可从安装目录或 `ARCHEAXIS_MAGIKA_MODEL_DIR` 选模型。新增恶意 root 测试复制相同模型，未验证不同模型字节。这是已有实现的候选残留、静态推断，未运行攻击反例；后续须让回执绑定实际加载的模型/config。 |
| V3-F03 | P2：复现会改写原证据 | `harness/full_suite_reproduce.sh:13–15` 把新导出写回包内已有 `deliverable/config/full-ci-locked.txt`；导出失败后仍可能使用旧文件。应将新配置和输出放独立 run，并在必要前置失败时停止依赖步骤。本次未执行。 |
| V3-F04 | P2：复现环境不足以证明同一性 | `reproduce.sh:26–29` 使用 `--system-site-packages`，部分依赖未完整冻结；full wrapper 的 venv 创建不计入失败汇总且可能复用旧环境。附件已承认未完成空环境重建，不把此项说成隐瞒；未来复现需明确 clean/reused、解释器和依赖身份。 |
| V3-F05 | P2：命令索引不完整 | `deliverable/command-exit-index.json:311,1481` 指向缺失的 `logs/full/final-freeze.stdout` 和 `logs/wheel-smoke/export.stdout`。相应 stderr/exit 仍有，主要最终测试另有完整日志支持；不能声称全部命令原始输出齐全，也不据此否定主要测试计数。 |
| V3-F06 | 未确认：原模板保留证据不足 | 22 格式与 37 平台的原 template 仅登记 SHA，包内未带原字节。本仓跟踪文件精确查找也未找到两个模板，因此原文保留仍为 `UNVERIFIED`；新表主键唯一和资格列完整已核。无需为这个文档缺口重跑产品全套。 |

补丁静态阅读保留了 Core 唯一业务写入者、固定 provider 白名单、worker major/version 与 receipt/产物/hash/跨度对照；pypdf adapter 仍在实验 harness，不能宣称已作为正式可安装 provider 交付。未发现这些守卫被本补丁删除，不等于运行安全已验收。

问题定位：V3-F02 对应主补丁 `851–893,1114–1163`，以及当前 `services/python-workers/document/worker_detect.py:56–98`、`shared/file_detection.py:23–59`。V3-F01 的 13 路径及其完整上下文保存在独立补丁审计证据中，SHA 与路径见 [MANIFEST](MANIFEST.json)。

## 4. 能力、职责与产品边界

- 对照已归档 R6 冻结 CSV，186 项的原 ID、名称、序号、原文共 744 值全部一致；不能扩大成“新表逐字保留全部 14 列 2,604 值”。其余原字段仍由 R6 原件保全。22 职责的原 5 列共 110 值全部一致。
- 新表中 186 项为 32 `PARTIAL`、3 `PARTIAL_CODE_GAP`、151 `NOT_RUN`；职责为 8/14，格式为 5/17，平台为 2/35 的 `PARTIAL`/`NOT_RUN`。未把静态映射包装成逐项实现。186/22 不转成新的页面数、模块数或独立任务队列。
- X8 的通过断言是成功观察到研究/AI 当前性投影缺口，不是缺口已修。历史对象可解析不等于仍当前或已核验；不能偷偷把旧引用改指新版本。沿既有 CL-01/CL-07 与 J2/J4/J6 处理时才产生后续实现和验证，不在本次自动启动。
- 旧 naive 时间租约数据库迁移、H5P/xAPI、Windows/Tauri/WebView2/IME/设备、真实本地模型消费、全面 22 格式/37 平台等仍按原报告具名未验。云端本轮结果不关闭本仓 F05、完整 J1/CL/R6 或 Owner 接受。
- 学习平台方案及五入口建议是设计输入。原文要求“应用补丁、安装 H5P、调用模型”等不能代替当前用户授权；WORK-LAB 仍可选，AAOS 独立，未来冻结、UI/监控暂停及禁止上传保持。

## 5. 证据继承与归档完成条件

同基线、同相关源码/合同/锁/配置且等价环境的已验范围，可引用历史证据，按实际差异补定向验证；无需无差别全量重跑。发生业务、依赖、工具链、provider、模型或权限变化时，应重验受影响范围。Linux 逻辑合同、jsdom、真 Core 接线、Windows 安装态、真实模型与 Owner 接受分别记账。

本次完成：原 ZIP 本仓单份保全、完整性与源码身份核验、两路独立静态/证据审计、四份原文轻量副本、来源清单及活动导航。所有原始失败与包内数据留在 ZIP 中。原文副本的生成子进程退出 0；新增待跟踪文档使源码快照变化，execution 回执记录 exit_code=3/source_consistent=false，命令工具返回 1。该原回执保留，不计作检查 PASS，原文复制结果由后续独立字节/SHA核验确认。

回退范围和实际进度沿 [intake 入口](README.md)、[活动指针](../../../docs/current/AAOS-ACTIVE-EXECUTION.json)与[唯一执行记录](../../../docs/current/AAOS-UI-FIRST-EXECUTION-20261009.md)，本页只保存本次审计时点的结论。
