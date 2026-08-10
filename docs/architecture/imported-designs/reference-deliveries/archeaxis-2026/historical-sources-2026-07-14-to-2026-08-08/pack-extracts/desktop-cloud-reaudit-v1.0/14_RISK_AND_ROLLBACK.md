# 风险与回滚

## 风险 1：远端基线漂移

处理：

- 执行前 fetch；
- 不强推；
- 在新 HEAD 重放；
- 基线不一致时先审差异；
- 记录实际 SHA。

## 风险 2：视觉重构破坏真实动作

处理：

- 先写浏览器 RED；
- 保留 data-action / API；
- 逐页面迁移；
- 真实 closed-loop 作为最终门禁。

## 风险 3：大规模框架迁移破坏 Wheel/Tauri

处理：

- A1 保持静态 HTML/CSS/JS；
- 不增加 CDN；
- 不增加 Node Runtime；
- React 迁移另开 TaskPack。

## 风险 4：紫色过度使用

处理：

- 遵循 70/15/10/5；
- 状态使用绿/蓝/琥珀/红；
- 阅读模式降低发光。

## 风险 5：UI 暗示不存在的 Agent 能力

处理：

- Activity Dock 使用 Job/Delivery；
- 名称为后台活动；
- 不显示 Agent 实例；
- 多 Agent 等待后端。

## 风险 6：内部 ID 泄漏

处理：

- 保留 DTO exact-key validation；
- Browser test 扫描敏感字段；
- Inspector A1 只使用公开聚合字段。

## 回滚策略

A1 仅改静态 UI 和测试：

1. 每个 checkpoint 可单独 revert；
2. 不需要数据库回滚；
3. UI 失败可恢复到上一个 commit；
4. 不删除现有 API；
5. 不修改持久化数据；
6. 不修改 Release 状态。

任何需要 Schema 迁移的修改立即停止，转入 A2 独立高风险 TaskPack。
