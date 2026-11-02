# 十月以前历史记录归档：第二批

已将14份明确属于2026年9月及更早的历史donor记录、交接和索引移出日常正文，96,158原字节无损保全为[ZIP](preoct-public-records.zip)（41,458B）。原代码、依赖、许可和原始输入继续保留。没有执行旧指令或删除Git历史。

[集中恢复映射](MANIFEST.json)逐项列出`files[].path`、长度、SHA-256及Git blob；ZIP成员名严格等于`path`。独立恢复核验、最终14旧路径缺失后验和全部成员SHA/CRC核验通过。`source_contracts`锁定2个旧消费者元数据的原长度/SHA，旧冻结清单和前批141档案保持原字节；消费者仍须核原成员身份。

恢复时读取`archive.path`中对应`path`成员，核`bytes`和`sha256`后写回同一原路径，拒绝覆盖；也可通过`source_commit:path`从Git历史恢复。历史原文仅供回查，不授予执行权限。压缩差额不是物理磁盘释放量。
