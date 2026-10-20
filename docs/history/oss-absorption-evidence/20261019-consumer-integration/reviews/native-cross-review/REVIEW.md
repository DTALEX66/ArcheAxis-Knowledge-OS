# Native 独立材料/陪伴交叉复核

**NO_BLOCKING_FINDING_FOR_SERIAL_APPLICATION**。绑定冻结 patch `862b1c10094bf6c821cac75c1d7f7f4e313165f6b20756381b33aaf67d5cfc20`，三成员 after hash、manifest 引用 verification hash 均一致。仅只读审查；未重复运行测试、原生服务、模型或浏览器，未改原提案/产品。

- 新模式在解析期要求独立 mode + actual-model opt-in + 有限 model identity，拒绝互斥旅程/installer/草稿隔离环境。已有 `work.mkdir(parents=True)` 不允许复用已存在 journey，便携数据根固定 owned `work/data`；helper 再验 sources/documents/tasks/config 初态。失败即停止，没有接续旧失败 workspace。
- `create_document` 的新建笔记对应 CanonicalLibrarySpace 的 `createOriginal→onOpenDocument`；真实 page03 Tiptap 使用 GroupedUI.keys（点击元素+原生 value），保存后按 Core version 递增与精确正文/无来源身份读回；不通过桥接写产品。native command 的 pointer/wheel 与 GroupedUI 实际协议匹配，reveal_selector 单参数匹配。
- 首次读取 reader 位于新建/保存后的 page03；保存模型配置会去 page19，但后续 MC helper 自己通过 page02 所选文档再进入 page20。cold/config 回读后新增 `open_reader` 明确先 page02、点击已保存文档，再调用 `restored_reader`。因此不会把 page19 当作 reader。`restored_reader` 同时核对可见正文/版本、诊断 document/source/revision/hash 与 Core 精确对象，未依标题单独认身份。
- cancel-only 直接 `run_cancel`，不调用成功生成 `mc.run`，也不依赖 answer/retest/知识审批。实际 helper 等待持久化 admission UNKNOWN 后取消，核对 cancel ACK、原 plan/hash/request、无 answer/candidate/无知识授权；新断言额外绑定完整 document kind/id/version/hash/block_id 与已保存 model configuration/model/max_tokens/timeout。cold reopen 后继续核对原取消历史；provider stop UNKNOWN、worker start UNVERIFIED 保留，不把取消当推理完成。
- recovery 模式沿用真实 MC 成功结果严断言；失败会抛出，不能继续恢复或写 PASS。cold 与 backup restore 后读回配置/epoch、原 reader 和同一 receipt。machine_tasks 等值只作为无关任务日志不变检查，文档明确未把它当 material/conversation 零调用证明。
- 原 grouped 分支与 full 前提未放宽；新分支单独退出并声明 full_grouped_ai_chain NOT_EXECUTED / closed_loop_verified=false / human_signoff=false。新模式的 PASS 仅为自身 engineering_status；旧全链 FAIL 不被替代。

证据边界：154 tests +145 subtests/18 baseline RED 来自冻结验证回执，本审查未重跑。SIMULATED 回归不能证明真实 Tauri/保存时序/实际取消/冷启动或安装验收成功；这些仍需 root 用原生运行回执另行证明。当前无必须补回归或可复现源码缺陷。

仅新增此 ignored 审阅目录两文件；EVIDENCE.json 记录提案与读取的实际依赖哈希。产品目前观测到的 hash 单独记录，不改写冻结提案当时 NOT_APPLIED 声明。
