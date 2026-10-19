# AXR-060-404 Evidence 长列表分页交接（2026-08-24）

## 本次已落地

- EvidenceAnchor 新增限界游标页读取：每页为 1–100 条，按不可变插入顺序读取，
  游标为编码后的版本化值，不返回 SQLite `rowid`。
- `/workspace/api/evidence/anchors` 新增 `cursor`，响应新增 `next_cursor`；非法游标
  与越界 page size 返回 422，不回退到整表读取。
- Evidence Space 每次只渲染服务端返回的一页，并提供可达的“上一页 / 下一页”按钮；
  翻页只使用后端提供的不透明游标，不把内部 ID 写入浏览器存储。

## 验证边界

- 后端合同覆盖游标读回、顺序、非法游标拒绝以及 HTTP 422。
- 前端合同覆盖下一页、上一页、页替换与末页禁用；TypeScript/Vite production build
  随此变更运行。
- 这是代码级长列表保护，不是 10,000 条真实设备帧率、高 DPI、读屏或安装态证据；
  后者仍需按 AXW-UI-804 的独立设备 receipt 执行。
