# Open Interop & Adapter Policy — 开放互操作与适配器策略 V1（AXW-1207）

> 权威：任务包 v1 2026-08-11 §4.8/§9.3
> 状态：**binding**。适配器边界、资产许可、复用顺序不可漂移。

## 1. 第一高保真纵切（H3）

Markdown、Properties、Links/Backlinks、Attachments、JSON Canvas、增量变更、expected-hash、原子写、备份、冲突和回滚 → 目标 **C4 安全往返**。

## 2. 永久适配能力池

| 适配目标 | 记录要求 |
|---|---|
| Obsidian 开放格式/URI/Canvas | 只适配器/兼容说明，不写日常 UI |
| Zotero / BibTeX / CSL | 独立版本、许可、读写范围、损失、fixture、往返、升级、回滚、kill switch |
| Anki | 同上 |
| Joplin / Logseq / SiYuan / Readwise | 同上 |
| 其他合法公开导出/API | 同上 |

每个 Adapter 独立记录：版本、许可、读写范围、损失、fixture、往返、升级、回滚、kill switch。

## 3. OSS 吸收边界（更新自 SUPPLY_CHAIN_LEDGER v2）

区分：**登记 / 依赖 / sidecar / fork-vendor / 行为参考 / 隔离实验**。

- "研究过"或"可导入一次" ≠ "已集成"
- 无已审查资产进入 bundle
- 每个 Adapter 有损失和回滚边界
- 视觉/3D/动画/字体/图标/模型/纹理/HDRI/音频/数据集：独立资产许可字段

## 4. 复用顺序（严格）

```text
开放格式 → 成熟依赖 → SDK/API/CLI → sidecar → 合规 fork/vendor → 行为/fixture 参考 → 自研
```

每项组件、模型、数据、字体、图标、资产记录：exact revision、许可证、NOTICE/SBOM、网络边界、升级、rollback/kill switch。

## 5. 第三方品牌边界

- Obsidian 等第三方只可在适配器/兼容说明中出现
- 不把第三方品牌写进日常 UI
- 不锁死未来依赖版本；用 capability probe、adapter contract 和替换方案保持可迁移

## 6. 修订记录

| 版本 | 日期 | 变更 | 授权 |
|---|---|---|---|
| V1 | 2026-08-12 | 互操作策略冻结（AXW-1207） | Owner 任务包 |
