# .NET SDK 10.0.401 归属迁移交接

状态：`IMPLEMENTED_LOCAL / SDK_VERSION_READBACK`。完整迁移已执行；产品构建、测试与运行验收 `NOT_EXECUTED`。

- 原位置：`D:\All projects\ArcheAxis.Knowledge.Green-x64\.ui-task-tree\ArcheAxis-Knowledge-OS-mainline\.project-local\tooling\dotnet-sdk-10.0.401`，现已不存在。
- 当前归属：`D:\All projects\OS External Configuration\10-toolchains\dotnet-sdk-10.0.401`。
- 5577 文件、814 个子目录、807,336,133 B，复制前后及删除前后全部文件 SHA-256、目录集合一致。
- SDK 仍为 `10.0.401`、Runtime `10.0.12`；目标 `--info` 和源删除后的 `--version` 均 exit 0。
- 既有共享 `10-toolchains\dotnet` 中 SDK `10.0.400` 保留；未改全局 PATH、注册表、ACL，未创建 junction。
- 未来 Green mainline 手工构建显式调用当前归属下的 `dotnet.exe`；本项目 `docs/SHARED_RESOURCE_PATH_INDEX.md` 的 `shared_dotnet_sdk_10_0_401` 与工具库 `00-registry/project-tool-index.yaml` 已登记。历史成功构建收据保留原文，不改写其原路径。
- 工具库 `.gitignore` 精确忽略 `/10-toolchains/dotnet-sdk-10.0.401/`；SDK 二进制不提交、不上传。

## 证据与恢复

证据根：`D:\All projects\ArcheAxis-Knowledge-OS\.project-local\mig\storage-cleanup-current-20260930`。

- `sdk-owner-copy-mapping.json`：原位置、当前位置、完整相对路径、目录集合、长度和 SHA-256。
- `sdk-owner-copy-verified.json`：完整复制与 SDK 信息验证。
- `sdk-owner-source-prune-readback.json`：原副本删除、完整目标读回、旧共享版本不变。

恢复时仅将映射中的当前 SDK 文件与目录复制回原精确位置；不覆盖已有文件，逐文件核对映射 SHA，完整集合验证后再调整当前资源索引。不要删除或覆盖既有共享 10.0.400。目标完整 SDK 是当前恢复副本，应保留。

此操作是同盘归属迁移：绿色版减少约807 MB，工具库增加相同 SDK 载荷，磁盘净释放计 **0**。清理累计净值不计此迁移。SDK CLI 信息通过不代表产品构建或整机软件健康验收通过。
