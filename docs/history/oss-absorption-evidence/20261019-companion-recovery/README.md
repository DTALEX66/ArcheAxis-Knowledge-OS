# 小栖原请求恢复修复 · 2026-10-19

这是当前项目的限定实现与验证快照，不是新权威或第二份进度台账。当前决定、路径和队列从[活动指针](../../../current/AAOS-ACTIVE-EXECUTION.json)进入，实际进度见其 `active_progress`。本轮总回执为[小栖恢复回执](../../../current/receipts/AAOS-COMPANION-RECOVERY-20261019.json)。

丢失执行响应后查询原请求，即使回执已完成，界面原先也只更新人物状态，不显示回答；已加载的请求列表仍可能显示“结果待确认”。现在终态回执独立显示回答，随后只读同步历史并按原会话/序号合并。历史失败明确提示暂未同步，不把已核对终态降回 UNKNOWN；历史到达后按 request_id 去重，不伪造 Core 事件、不再次推理。工作区退出/恢复屏障与迟到响应隔离保留。

`red-*` 保留修复前30项中6项失败的证据；`green-*` 是首轮修复；`final-*` 是5个测试文件46项 PASS。测试使用真实 React/jsdom 和模拟 Core，不等于真实模型或原生宿主。`frontend-build.json` 记录 TypeScript/Vite PASS，与最终定向测试绑定同一 dirty patch `420773b590aa27dd9f2ce2ca102187e3c3948c17e1d85ea53275a5089c30f742`。没有重跑该 patch 的前端全套。

`build_invalid_path-execution.json` 保留首轮构建命令失败：receipt 被指定到不允许的 audits 目录，路由器在编译前拒绝；改到已有规则要求的 `.project-local/runs/.../artifacts/` 后通过，没有削弱路径限制。完整日志/JSON 留在回执指定的项目内 `.project-local`，此处保存命令、时间、退出码和逐项测试名称/结果。`MANIFEST.json` 校验本目录成员；源码四文件哈希保存在总回执。

`verify_frontend.py` 是实际执行测试入口脚本的字节快照，复用项目依赖，无安装。例：从项目根用 `.venv/Scripts/python.exe scripts/runtime/dev.py --run-id <新的唯一ID> -- .venv/Scripts/python.exe docs/history/oss-absorption-evidence/20261019-companion-recovery/verify_frontend.py src/__tests__/ConversationPanel.test.tsx src/__tests__/CompanionSession.test.tsx`。Node 路径是当时核实的观察，换机器须按[共享路径索引](../../../SHARED_RESOURCE_PATH_INDEX.md)重新核对；不要把快照当全局配置。

本轮没有启动产品/浏览器/模型服务、修改共享配置、触碰用户 workspace 或写入真实业务数据。新前端尚未编进原生候选；材料/会话原生模型、取消和冷重开仍待验证。只读评审对后续入口的核对见[评审快照](READONLY-REVIEW.md)，不是实现或 PASS。本地归档尚未 commit/push，不等于云端备份。
