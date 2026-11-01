# 十月以前历史过程记录归档：第三批

已将31份明确属于2026年9月及更早的公开过程记录，532,759原字节无损保存在[ZIP](preoct-public-records.zip)（145,973B）。现行合同、原始任务包与输入、10月及以后补注继续保留。没有执行旧脚本或删除Git历史。

[集中恢复映射](MANIFEST.json)列出每份原`path`、`bytes`、`sha256`及`git_blob`，ZIP成员名严格等于`path`。原文日期、原措辞和失败状态保持不变。`source_contracts`绑定旧消费者元数据原字节；固定旧行及其长度/SHA要求继续校验，不由新成员表决定检查范围。前两批档案不改写。

恢复时按`archive.path`读取对应`files[].path`成员，先核长度/SHA再写回原路径，拒绝链接、覆盖和跨批重复。也可在独立checkout中通过`source_commit:path`恢复并核验。项目本地恢复工具为`.project-local/runs/be268a2d33/gov-history-batch3-20261101/batch3_archive.py restore`。压缩差额不是物理磁盘释放量。

当前读取通过`scripts/maintenance/authority_routes.py`的严格归档身份读取器；单有索引或缺失路径不构成验证成功。历史相对链接按原位置解释，历史指令不授予当前执行权限。

规划归档旧清单的3个supporting行记录了不同的LF/CRLF及末尾换行表示。普通读取仍返回本批保全的canonical原Git字节；仅这3个固定消费者行先核原Git长度/SHA/blob，再按已证明的精确换行规则重建，并核旧行原长度/SHA。两种运输表示分开验证，不能把canonical字节冒充旧清单字节，也不允许内容改动、缺成员或任意哈希容错。
