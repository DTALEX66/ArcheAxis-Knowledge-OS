# 具体参考提炼（非供体安装声明）

来源是仓库已保留的格式/协议实践；本轮不声称读过或复制了全部上游源码。
原上游仓库名、匹配依据与原始行见 `OSS-REUSE-CROSSWALK-20261008.json`。

| 参考 | 提炼结果 | 本项目映射与可运行样例 |
|---|---|---|
| JSON Canvas | 卡片以节点 ID 建边；端点必须存在；file/link 引用保留为引用，不把引用对象复制成第二份知识真值。布局是投影。 | `shared/json_canvas.py`、`services/python-workers/document/worker_canvas.py`；`tests/fixtures/golden/golden-canvas-anchor.canvas` 经 Core 作业执行与重启读回。模板 `ObjectReference` 保存真实 Document ID、不可变版本、可选 Block ID 与位置；解析时按版本读取。 |
| JSON Schema | 内容合同采用明确类型、必需字段与版本；未知枚举或错类型不能通过一个“对象存在”检查。 | `packages/contracts/`、`frontend/src/api/generated/core-contract.ts`；`tests/test_worker_route_contract.py` 和 `tests/test_capability_absorption_registry.py` 实测通过。模板元数据另有有限字段校验，仍是现有 Document 的属性，不增加状态数据库。 |
| OpenAPI | 业务 API 采用有限动作和版本化 DTO；协议文件描述路径，运行时测试证明路径实际可调用，二者分别保留。 | `packages/contracts/v1/openapi-outline.yaml`、`src-tauri/src/core_bridge.rs`；`crates/archeaxis-api/tests/oss_template_reuse.rs` 从真实导入 API 到 worker 结果，再关闭写者并重开读回。Tauri 原生桥接与安装态验收本轮尚未运行。 |

不能据此给其他知识软件（Logseq、Notion、AFFiNE 等）标记“已参考吸收”。它们仍需固定来源、具体差异和样例。fsrs 的使用映射到 py-fsrs，不能把 fsrs4anki 整个应用当作同一实现；同理 PyMuPDF 不等于 PyMuPDF4LLM。

模板的反向引用、集合汇总与局部关系视图是从最多 100 个当前 Document 快照重建的有限投影；不宣称全库图服务、全平台同步或通用关系数据库。引用正文按绑定版本读取，目标不存在或 Block ID 不匹配就明确报错，保留原引用以待重新定位。
