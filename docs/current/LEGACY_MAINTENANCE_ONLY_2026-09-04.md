# Legacy 路径 maintenance-only 声明（2026-09-04 生效）

> 依据：MASTER-TASKPACK（vNext）执行裁决。旧产品树**不再是未来权威主线**；同仓 vNext（`vnext/`）为未来权威。

## 冻结与限制

| 对象 | 状态 |
| --- | --- |
| `v0.6.14`（tag `691aaf2d`） | **不可变 legacy 基线**：recoverable / migration-source / behavior-oracle；不改 tag/资产/收据 |
| `app/` `shared/` `knowledge_base/` `frontend/` `src-tauri/` `desktop/` 等旧路径 | **maintenance-only**：只允许安全/数据损坏/导出/备份/迁移/资格化修复；**不再新增终局产品功能** |
| 主分支 | 继续接收隔离的永久 vNext 目录（`vnext/`）小 PR |

## 边界（不得违反）
- Rust = vNext Core 唯一权威 writer；C#/Avalonia = 桌面层；Python = worker（无主库权限）
- 旧库新库不共享写权限、不实时同步、不双写；旧数据只经一致快照→只读导出→Rust dry-run→staging→差分→人工确认进入新库
- Rust 不写 legacy 数据库；构建成功不是迁移证据

## 现有代码角色
Python/React/Tauri 代码 = 行为与 fixture 来源（behavior-oracle），不是新权威；其测试/回执可继续作为旧基线维护与迁移 oracle。
