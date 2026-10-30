# 洁净冲突输入与共享来源

本页冻结本轮维护证据。当前顺序与全项目进度仍沿[活动指针](../../../current/AAOS-ACTIVE-EXECUTION.json)和[唯一执行记录](../../../current/AAOS-UI-FIRST-EXECUTION-20261009.md)，全目标仍 PARTIAL；不恢复前端实施、监控、外发或部署。

## 已完成

正式准备入口 [`conflict_inputs.py`](../../../../scripts/runtime/conflict_inputs.py) 从固定 Git commit 提取冲突探针需要的8个公开文件，生成独立、无remote的有限 harness Git快照。旧 `zc1c8/input/repo` 不枚举、不读正文、不复制；旧清单只用于选择已声明的公开便携Git、驱动、guest入口及保留安装包/PowerShell。所选公开组核完整清单、大小和SHA，失败保留，不修改原件或私有豁免。

新 `source_roots` 是清单中被SHA绑定的三路精确来源。input仍在新stage；package/tools可指向本仓保留run内同名目录，不能重定向input、越界、重叠调用者可写run、跟随链接或夹带未声明/私有文件。启动和停止后均完整重核；旧单stage格式继续支持。共享执行沿 [`shared_sandbox.py`](../../../../scripts/runtime/shared_sandbox.py)，新增显式 `--execute-conflict`，不执行其他冻结guest类别。

本次新输入 `sci-build1/artifacts/clean-conflict-source`，清单SHA `590663a74d81321467af9a6ffe342a3fd3491030e7a1fe5e67e3a684a5086ce2`。完整映射10,228成员、1,125,405,225逻辑字节；其中新input载荷9,560成员、436,700,573字节，另清单2,037,599字节。公开便携Git/驱动/guest入口一次复制436,098,577字节；安装包与PowerShell复制0。旧repo清单为6,023成员/1,739,282,907字节，新harness repo为27成员/601,996字节（含新Git元数据）；8个源码文件共451,721字节。后续重试输入载荷复制0，输出独立。这里是避免重复增长，本轮实际删除和外部迁移均0。

快照来源commit `e43a91b92af37a65b2c9a03a7e578ba6604b82af`；有限harness commit `5935a2f4864cc1843d357e2c59d14165e3625f30`，明确不是产品构建源码身份，不把裁剪快照视为当前产品重建。C1安装器/Host/Core/runtime manifest仍分别为 `3337fce6…` / `ac4c399b…` / `b6f5b591…` / `440e9084…`，从保留packaging/identity/成员哈希重新绑定。

`sci-vm1` 真实离线映射探针PASS；`sci-conf2` 真实离线安装态冲突旅程PASS：guest SYSTEM核全部10,228成员，三个映射代表文件的写句柄被AccessDenied拒绝，新输出标记读回；原有冲突断言、可信WebDriver控件、独立重启读回、来源不变、Core/Host/安装器身份和自有进程/端口清场均通过。guest外层 `wdconf` 与内层 `webdriver-<id>` 两个canonical run分别核元数据与真实收据，不能凭复制的第一份JSON放行。实际新收据176,686字节，SHA `e47c29b43021e3a14bdf1e9c0990fab28d21971098d142136b8e74bfe32a3dcb`。沙盒ID `f850c96c-6450-4b62-b9f2-dfd93f2d179e` 已经官方精确停止，最终清单为空。

## 验证与原始失败

最终 `sci-t6` 53测试及14个subtest通过；`sci-a3` 架构、`sci-l4` Ruff通过。`sci-proof1` 独立重核新输入、原始所选公开成员、真实guest收据/身份/清场，LOCAL_PASS/source_consistent=true。文件身份沿[MANIFEST](MANIFEST.json)，详细计量、全部检查与原失败沿其ignored证据引用。

- `sci-t1` 的一次Git长路径fixture失败，用单次Git进程的 `core.longpaths=true` 修正，未改全局设置。
- `sci-t4` 的7项深路径fixture失败，改用Windows extended-path文件操作；没有缩短测试来避开问题。
- `sci-a1` 6项绝对guest字符串违规，改为复用既有guest命名空间配置，未扩大架构豁免。
- `sci-conf1` guest实际通过，宿主错误地把旅程收据定位到外层run，保留FAIL。按探针真实独立run的ID/归属/源码元数据修正，并用全新 `sci-conf2` 验证，未重签旧收据。

还补了异常验证器不得保存PASS的防护；未知异常仍保留FAIL并精确停止自有沙盒。合成测试和真实VM证据分开，不把测试数量当产品能力完成数。

## 接续与回退

每次用新的短run ID，沿 `dev.py` 调共享入口、固定stage与完整清单SHA，显式选择探针或冲突；无开关只准备。正式Core仍是唯一SQLite/CAS writer，UI实施暂停，测试数据为本轮自有合成工作区。没有实际模型、云推理、跨版本升级/回滚、Owner验收、CI、Green替换或真实资料覆盖。

保留旧输入、唯一失败及所有消费者/恢复映射；本轮共享资格不授权删除 `zc1c8` 的package/tools或私有状态，也不证明其他staging生产者已经归一。可回退本轮维护代码与导航提交，保留原件和新旧运行证据；回退不自动重启旧复制入口。剩余目录规范、旧候选/恢复映射与外溢追踪继续按原优先级逐批处理。

Owner已贴剩余533根ACL脚本的初始review输出；本轮最终核查仍未见apply终态收据，不把启动两行当权限恢复。另一批并行目录/外溢/后端工作各自沿唯一执行记录接续，不在本页维护第二份状态。
