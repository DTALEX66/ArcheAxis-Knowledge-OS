# DOT 云端审计与当前 AAOS 实现对应

状态：PARTIAL。来源为用户指定的 `D:/All projects/Record/AAOS-WORK-DESIGN-cloud-audit-20261011.zip`，完整性记录见 `docs/current/receipts/AAOS-DOT-CLOUD-AUDIT-INTAKE-20261012.json`。原 ZIP 保留；43 个相关成员在项目本地归档，包含只读复核发现首次遗漏的 `evidence/probes/AuditRecovery.test.tsx`，已按 ZIP manifest 核验补保全。本文不替换活动指针，不激活报告里的提示词或跨项目操作。

报告测试基线为 `d6c2bbeef722f82a02a3f18e1b4296ad5e37c58b`。当前同一 HEAD 上存在未提交增量，不能据相同 HEAD 假定当前源码等于云端测试源码。原报告与 Linux 补充应一起读取：补充将选定 Rust 测试更新为 76 PASS，并确认 Linux API 重复建稿，但未覆盖 Windows 桌面、实际模型或安装态。

| 来源问题 | 当前源码对应 | 证据与剩余边界 |
| --- | --- | --- |
| A01：原件建稿丢 ACK 后无稳定请求身份，重试重复落盘 | `CanonicalLibrarySpace.tsx` 的 `noteAttempt` 冻结请求，持久化 pending_original，重试复用身份 | 当前恢复测试及 Windows 原生 ACK 故障验收分别核对；不得用历史 Linux 双落盘宣称当前修复失败，也不得以源码存在就宣称全部导入入口幂等完成 |
| A02：知识审阅失败后刷新丢失备注 | `CanonicalKnowledgeSpace.tsx` 的 `noteOwner` 只在切换对象时清空；失败保留，成功只清空本次提交值 | 对应 `KnowledgeReviewRecovery.test.tsx`；组件测试为模拟桥接，不能替代用户实际操作验收 |
| A03：正文前 1000 字符作为检索词，外发告知不足 | `document_check.py` 使用独立 `search_query`；CheckPanel 展示材料、目的地及检索范围；SafeHTTP 在调用前校验授权 | 安全回归与回执为受控测试；真实云检索仍未测。原报告明确没有证明已泄露用户数据 |
| A04：兼容联邦服务同幂等键换正文或提交者返回旧回执 | `app/federation/service.py` 比较 items_hash 与原 submitter，冲突拒绝；`tests/test_federation_v1.py` 覆盖两种变化 | 这是兼容 Python 服务，不能当作 Rust Core 闭环或三项目实连证据 |

最新 Windows 隔离原生证据为 `docs/current/receipts/AAOS-NATIVE-INVENTORY-CLEANUP-20261012.json`：正式 UI 的本机清单探测、4B 实际回答/复测、保存、完整重启及 ACK 恢复已通过，材料为合成测试。清单可读不等于模型已加载或完成推理；费用未知不记为零。

2026-10-12 定向重验：通过 `scripts/runtime/dev.py` 执行 `pytest tests/test_federation_v1.py -q`，退出 0；原始日志为 `.project-local/runs/be268a2d33/4e544725f1ba/logs/execution.log`。此前沙箱运行 `ba22ea395ef9` 在 pytest 初始化的路径规范化阶段遭 WinError 5，未执行测试；依 Owner 已授予的本轮限定非沙箱权限完成重验，未修改 ACL 或系统配置。此结果仅证明兼容服务的定向行为，不是三项目实连。

业务差距仍包括任务级模型选择与冻结身份绑定的完整资格、27B 本机推理和性能资格、真实云研究及定位引用、安装态验证、持续运行与 Owner 验收。多轮对话提案不因报告出现而自动解除六项核心能力冻结。其他项目缺陷只保留共享背景，不在本项目写入修复。

2026-10-12 已逐张查看 5 张 AAOS 截图：blueprint/light 为宽屏工作台，browser-no-core/cosmic 为窄窗口，palette 为全局命令弹层。可见旧名称“星环知识平台”、浏览器开发模式及本地后端不可用提示；未见截图中页面整体横向溢出。浅色截图中多个控件对比较低，属于该历史画面的视觉观察，未据静态截图判定当前控件是否禁用或可交互。截图证明的是云端旧前端 shell 的呈现，不能证明 Windows 原生 Core、当前命名、全部屏宽或可访问性已通过。


补充来源保全：共享 `evidence/bs4-install.log` 已核验 ZIP manifest 与原始字节 SHA-256 并保全；43 个保全成员均重验字节数与哈希。该日志只证明云端 Linux 曾安装 beautifulsoup4 4.15.0 与 soupsieve 3.0.1，不证明初次全部失败的根因，也不代表本机安装或版本决定。本轮没有执行安装。
