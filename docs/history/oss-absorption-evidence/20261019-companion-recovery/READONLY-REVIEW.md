# 接续评审快照 · 2026-10-19

范围：本轮明确授权的并行只读评审；root 是唯一 writer。以下是当时源码观察和后续实现建议，不建立另一队列，不是运行证据。路径相对项目根；行号可能随修改漂移。执行仍先读取活动指针、当前决定和原合同。

## 小栖恢复代码评审

未发现本轮恢复修复新增的确定缺陷。确认回执独立投影不改 Core 历史，completed 事件到达后停止 fallback；对应确认回执优先于陈旧 EXECUTING 显示合理。pause/detach 递增 generation，迟到 execute/status/history 写状态前核对。工作区身份变化由 Provider 更换 Session。建议额外覆盖 failed/cancelled 的历史失败；status 自身迟到时 pause 的覆盖已由 root 补入最终测试。

## 原生材料/陪伴用途缺口

- `scripts/probes/aaos01_tauri_webdriver_loop.py` 的 `--grouped-save-deep-binding` 历史旅程只保存 answer/retest；主要逻辑在 `scripts/probes/aaos01_grouped_owner_loop.py`。现有 `save_deep_model_binding`、`run_ai_stage`、`run_grouped_loop`、`read_saved_model_configuration` 可复用。
- 新增有限 opt-in 时，一次保存 answer/retest/material/companion 四用途，避免中途提高配置 revision 使旧冻结请求失效；默认保持旧入口语义。真实调用须显式 `--actual-model`，使用本轮合成隔离 workspace 和最新候选；不能读写用户实际模型配置。
- 材料入口在已有文档阅读页 `.reader-material-tools`，scope 是 `固定版本材料问答`：选 DEEP、填写问题/用途、预览、核对固定 document/version/hash/selection/模型绑定后确认。陪伴 page14 scope `正式陪伴会话`：新建本地会话、选 DEEP、填写问题、预览、确认。
- 只读核对 `material_question_status`、`conversation_status`、`conversation_history`；成功分别为 outcome=succeeded/state=completed，最终回答非空、原 request/session/plan 哈希一致、实际模型可核对、authority=candidate、grants_knowledge_acceptance=false。普通冷重开通过“恢复最近同版本材料请求”和选择原会话读历史核对，不再次确认来冒充读回。
- **conversation 只写会话 journal，不创建 machine task**。`machine_tasks()` 总数不变不能证明会话零推理。需要有限只读 bridge observer 分别统计 `material_question`/`conversation_request` 的 preview true/false，再核原请求 journal。配置、预览、历史和冷重开不得增加执行调用。
- 取消是独立 opt-in 旅程，等待真实终态再重开；取消 ACK 不证明 provider 停止，`provider_stop_state` 保持 UNKNOWN。保留已有 save-deep 与 machine-cancel 不能混用的边界。
- 新前端需重建宿主，并由现行探针对 source patch、host/Core hash 核验。旧 native candidate 不包含本轮恢复和能力/课程新界面。共用驱动、Edge 版本和 LM Studio 运行状态先按现行共享索引动态核对；不能从本快照猜运行状态。

## BE10 合同与只读接入缺口

原任务 `docs/authority/taskpack-20261013-backend-host/TASKPACK.md` 的 BE10 首期要求 handshake/capability discovery/object reference/status/只读关联，包含 namespace、协议版本、身份、对象修订、新鲜度和 deeplink。后续 context/task proposal 等先合同，真实写入另行资格。

目前 `packages/contracts/v2/ui-host.schema.json` 的 project.handshake/project.objects.read/project.handoff.preview 为 null，`frontend/src/api/uiHost.ts` 和 `src-tauri/src/ui_host_bridge.rs` 主要是无输入读取，不能表达有限对象版本。不能直接放开任意 dict/URL。

最小切片应有版本化有限合同、Rust 只读 producer 与实际 consumer、明确过期/不兼容/断连结果；桥接 schema/DTO/校验贯通。尤其桌面启动凭据默认 human actor，不能把该 token 交给 Observer 便宣称只读：需要独立只读 admission 或受限 adapter，并证明 mutation 不可达。两个合成隔离 workspace 的实际 Rust 请求/adapter 与身份版本验证可以形成集成证据；模拟 invoke 和结构校验不够，外部 WORK-LAB/DESIGN-LAB 真实互通仍须单列 UNVERIFIED。
