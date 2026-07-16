# Phase 3 TaskPack：Approved Source/Output Roots

> 状态：completed
> 当前刀：统一本地路径 containment 与 symlink/junction 逃逸防护
> Ownership：`shared/approved_paths.py`、`tests/test_approved_paths.py`、首批文件写入/摄入 Adapter

## 目标

建立单一 fail-closed `ApprovedRoots` Facade。所有纳入本 TaskPack 的本地 source/output 路径必须在显式批准根内；路径解析后统一验证，拒绝 traversal、symlink 和 Windows junction 逃逸。

## 允许范围

- 新增 `shared.approved_paths` 标准库实现；
- 首批接入 `app/ingestion/file.py`、`shared/safe_writer.py`、`shared/obsidian_projection.py`；
- 新增负向 containment 测试和 Windows junction skip/negative evidence；
- 保持现有业务结果结构与 SafeWriter dry-run 默认行为。

## 禁止范围

- 不修改 Safe HTTP、approved source 内容语义、稳定哈希、FTS/Vector rebuild、Migration Runner 或数据库 Schema；
- 不访问 `E:`、外部项目或个人 Vault；
- 不依赖环境变量隐式放宽 approved roots；
- 不把 `Path.resolve()` 单独当作完整合同，必须由统一 Facade 返回验证后的路径。

## 安全合同

1. source/output 根必须显式提供，空根 fail closed；
2. absolute/relative path 均须 resolve 后 containment 校验；
3. `..`、existing symlink、Windows junction 逃逸必须拒绝；
4. source 与 output roots 分权，source 路径不能冒充 output 目标；
5. output 目标允许不存在，但其已存在父目录仍必须在 approved root 内；
6. 错误返回明确拒绝，不返回假成功或 fallback 路径。

## 首批验收

- traversal、absolute outside root、symlink escape、junction escape（平台支持时）均有失败优先测试；
- SafeWriter 不再只依赖 project root containment；
- projection 写入不再接受 vault 外部路径；
- file ingestion 通过 source-root policy；
- changed Ruff、index convention、完整 pytest、独立 reviewer GO 和 exact-SHA CI 通过。

## 回滚

本 TaskPack 独立提交；可逆回滚 `ApprovedRoots` 与首批 Adapter，不触碰 Safe HTTP 或 Phase 2 Contracts。
