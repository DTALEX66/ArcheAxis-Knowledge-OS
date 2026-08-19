# 剩余人工门禁（REMAINING HUMAN GATES）· 2026-08-19

> 无法由 Agent 自动完成、必须人工决策/执行的门禁清单。

| # | 门禁 | 说明 | 阻塞 |
| --- | --- | --- | --- |
| G1 | Tauri 桌面构建 | 本机无 Rust/cargo 工具链；需安装后执行 src-tauri 构建（脚手架已就位后） | R5 |
| G2 | Windows 安装版/便携版发布 | 需干净机器验证 + 升级保留验证 | R6 |
| G3 | 四库位置人工确认 | 首次启动时用户选择四库位置（快速/高级模式） | R1 UX |
| G4 | React 工作台人工验收 | 六空间真实数据流走查（当前 Library/Evidence/AI Assets 刚接 API，需人工看） | R4 |
| G5 | 联邦知识 API 对外契约评审 | WORK-LAB 侧调用方确认契约形状/错误码/版本协商 | E2E-003 后 |
| G6 | 迁移试点正式数据放行 | 试点使用样例对象；真实 WORK-LAB/DESIGN-LAB 数据迁移需授权 | §12 |
| G7 | 证据等级提升 | candidate→verified 必须人工批准（已实现为强制门槛） | 持续 |
| G8 | commit/push 授权 | 本批次后续提交需用户批准（TP §16） | 全部 |
