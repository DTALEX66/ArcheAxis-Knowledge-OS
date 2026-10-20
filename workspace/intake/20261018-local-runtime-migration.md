# 本地运行配置迁移

Owner 本轮明确要求 LM Studio，更新旧代码/索引，迁移归档旧文件并清理确属项目的旧运行组件。

执行收敛到现有 Tauri/React + Rust canonical writer + isolated Python workers；不引入第二框架。
默认服务统一为 `http://127.0.0.1:1234/v1`，不自动探测或回退 Ollama。显式旧协议适配器
保留兼容能力，不自动改变已保存的用户 profile、冻结请求或真实数据。

旧 profile 移入 `docs/history/runtime-migration-20261018/`，按原字节和 SHA-256 校验。
能力索引增加当前 manifest 字节绑定，回归覆盖源码、无 manifest 的暂存 worker、旧 manifest 顺序、
服务不可用时不回退，以及新建 UI profile 和 Core 默认目标计划。

运行目录更新与清理必须核实当前路径、来源、进程占用和恢复清单；保留项目 runtime Python
依赖、真实 data、共享模型库、Green 与未知来源对象。旧回执中的路径先现场核实，缺失不算已删除或回收。
