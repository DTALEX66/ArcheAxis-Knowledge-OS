# Qoder / AAOS 缺失来源恢复清单

日期：2026-10-07

## 结论

- A01、A02、A06：原始 Markdown 文件已恢复，实际 SHA-256 与 2026-10-06 AAOS 母版附录登记值一致，可从 `SOURCE_MISSING` 改为 `VERIFIED_MATCH`（在 Qoder 将文件复制到目标 `sources/` 后再次本机计算确认）。
- U01、U02：历史上是“会话来源”，母版明确记载“未作为原始聊天全文导出”。本包提供规范化 `RECOVERED_CANONICAL_EXPORT`，可登记本次导出哈希与 provenance；不要伪称其哈希与不存在的原始聊天文件匹配。

## 建议落位

- `sources/AAOS_快速重构与多格式闭环_完整方案_20261004.md`
- `sources/AAOS_未来延展与可持续架构_完整方案_20261004.md`
- `sources/CONTENT-COPY-V2.md`
- `records/U01_2026-10-06_最新保存_证据_双学习规则_RECOVERED.md`
- `records/U02_2026-10-06_AAOS图谱_双链研究增量_RECOVERED.md`

也可将 U01/U02 同步放入 `D:\All projects\Record`，但仓库内仍建议保留一个受版本控制的记录副本或索引指针。

## 附录登记的预期源哈希

- A01 `7ecda3e3f9d22834d65df663ba4f42a3ac62e31d215ab5e7c59c08bfaf08441e`
- A02 `771b189740e94dfeaf65e363b919745c2a69bb795d461e2b2fbcc9c95b15e1e1`
- A06 `7d475862fd307be46371ceeaead3407d6bbe939b429c37df1c28c4c6760fbeb2`
