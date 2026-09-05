# Intake 2026-09-05 — Green v0.6.14 在线备份缺陷修复（运行时工件排除）

## 发现（在现有绿色版实测）
`POST /api/v1/workspace/api/backup/create`（快照整个 data 根目录）在桌面 core **在线运行**时必然失败：

- core 通过 `shared/backup.py::_open_runtime_lock` 以 `msvcrt.locking` 对
  `.archeaxis.sqlite.runtime.lock` 首字节加**字节区排他锁**；
- `app/exchange/backup.py::_iter_files` 原先把该文件纳入快照扫描并 `_sha256_file`
  读取 → 另一句柄读取被锁字节区 → `PermissionError [Errno 13]` → 500；
- 同步存在的 `.migration_operator_locks.lockdb`（迁移算子租约账本）同样不应进入快照。

## 修复（legacy 维护化改动，最小可回退）
`app/exchange/backup.py`：`_iter_files` 排除名称以
`.runtime.lock` / `.lockdb` 结尾的运行时工件；同步打补丁到绿色版捆绑
`runtime\python\Lib\site-packages\app\exchange\backup.py`。

## 验证
- `tests/test_axw094b_backup.py` 11/11 绿，含两个新回归用例：
  - 快照跳过 `.runtime.lock` / `.lockdb` 且保留普通内容；
  - Windows 下真实 `msvcrt.LK_NBLCK` 字节锁场景下 `create_backup` 成功。
- Green v0.6.14 副本在线实测：core 运行（持有运行锁）状态下
  `backup create` → HTTP 200 / 25 文件；`verify` → `valid:true`；
  manifest 断言：0 条 `runtime.lock`/`lockdb` 条目，`archeaxis.sqlite` 已包含；
  对非空在线目标 `restore` dry-run → 422（设计语义：拒绝混入快照）。
- 写路径三件套（launch token + scope + idempotency-key）与
  `ARCHEAXIS_BROWSER_SMOKE_WRITE_BYPASS` 均为设计内授权门。

## 说明
- 桌面写授权门（403/422/503 无凭据响应）为设计安全，非缺陷。
- 本地验证需在受控副本上进行；Green 真实数据目录未被改动。
