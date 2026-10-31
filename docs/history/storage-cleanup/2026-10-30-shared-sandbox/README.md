# 共享沙盒输入：真实隔离与同候选生命周期

本页冻结本轮维护结果；当前授权、顺序和实际进度沿[活动指针](../../../current/AAOS-ACTIVE-EXECUTION.json)及[唯一执行记录](../../../current/AAOS-UI-FIRST-EXECUTION-20261009.md)。本轮接续 Owner 的体积/目录/外溢治理优先项，不恢复前端实施或监控。

## 已完成

正式启动入口为 [`scripts/runtime/shared_sandbox.py`](../../../../scripts/runtime/shared_sandbox.py)，复用既有 `sandbox_inputs.py` 的全量声明、私有边界、文件集和哈希检查。每轮使用独立 canonical run，三路输入映射到保留来源且只读，输出独立；启动前重核源码、清单、模板、命令、配置、run归属和空输出。VM 通过已安装的官方 `wsb` CLI 管理，启动前持久记录唯一请求 ID；超时/未知返回不重试启动，只对该 ID 发出一次停止意图，不按进程名或列表第一项停止其他实例。

只读探针在 guest SYSTEM 上运行：核全部成员大小/SHA，分别尝试以写权限打开一个现存代表文件而不改字节，要求 Win32 AccessDenied（不把共享冲突等错误算通过）；另在本轮输出创建 nonce 绑定标记并由宿主读回。这证明本次三个写句柄检查与输出写入，不宣称遍历了每个文件的所有权限或覆盖所有 OS 组合。

`ssp-vm1` 为真实离线映射探针；`ssp-life1` 进一步复用原 `zc1i2` 的冻结 guest 生命周期脚本，在新 VM 内安装同一 C1 候选并连接 guest 用户会话。两个 run 均 LOCAL_PASS/source_consistent=true，输入为672成员、688,965,713字节，清单 SHA `82f2c42901049665b8b85a4d9620bbcdfd67419025ebe2746956e02d4e0e7fef`。host事前、guest、host事后完整核对通过，输入载荷复制0；各自只停自己的ID，官方最终清单为空。没有改历史输入、旧清单、旧 launcher 或原始收据。

`ssp-life1` 同候选安装收据 SHA `92c3aa1eb8467a7cfb7a1af62283fa7fbf14c7705629b71ae5110566d7582095`，`complete_lifecycle_verified=true`：正常关闭、同版本重装保全、强制树清场、干净卸载、卸载保留数据、重装读回均true，pyc增长0。安装器 `3337fce6…`、Host `ac4c399b…`、Core `b6f5b591…`、runtime manifest `440e9084…` 均从当前只读输入身份独立核对，不按历史 PASS 放行；fresh persisted job 为 `installer-lifecycle-6522617e96657c0c`。途中前端启动独立检查PASS，额外只读guest进程快照保留；没有人工补操作或改变验收断言。

新run实测：`ssp-vm1` 21文件/33,462逻辑字节；`ssp-life1` 492文件/157,112逻辑字节，均无计量错误、链接或私有排除，未产生 package/input/tools 副本。该类别原每次 staging 的约689MB输入现在复用一份，后续重试只增加输出与收据。这里是避免新增副本，不是本轮删除或物理空间回收；本轮实际删除和外部迁移均0，没有为这两个小run重复全仓盘点。

## 使用与保留

只有既有有限测试授权仍有效、输入原件/收据保留、当前版本和完整哈希检查通过时才执行。历史清单 `approval` 只是来源，不能自行授予运行权限。每次换唯一短run ID：

```powershell
.\.venv\Scripts\python.exe -B scripts/runtime/dev.py --run-id ss-YYYYMMDD-N -- .\.venv\Scripts\python.exe -B scripts/runtime/shared_sandbox.py --stage "D:/All projects/ArcheAxis-Knowledge-OS/.project-local/runs/be268a2d33/zc1i2" --manifest-sha256 82f2c42901049665b8b85a4d9620bbcdfd67419025ebe2746956e02d4e0e7fef --execute-lifecycle
```

`--execute-probe` 只做映射检查；不传执行开关只准备方案。`--execute-lifecycle` 仅支持具名混合Core同版本生命周期输入，执行前核 packaging/identity/installer 三方身份。成功收据仍不涵盖冲突UI、AI、跨版本升级/回滚、云CI、Green替换或Owner验收；不自动启用其他guest脚本。失败、观察期限、停止失败或输入变化均保留且不签发PASS，不复用已发出启动意图的run。

保留来源 `zc1i2` 的 package/input/tools 直到全部消费者/恢复映射另行审阅；不能因本轮共享资格删除旧输入。历史冲突包含 `.mimosa`，仍须准备洁净来源后才能接入，不修改私有豁免或旧证据。新入口已覆盖本次生命周期类别；其他 staging 生产者、旧候选、散落路径仍逐批处理，不宣称全部膨胀来源已经替换。

回退：保留新旧 run 证据和原输入，可撤回本次工具/导航提交；回退代码不重启旧 staging。已停止 VM 无常驻工作；失败后若官方状态仍有本轮 ID，先沿启动/停止意图核查，不能按观察超时重建另一个实例。

## 验证与外溢追踪

`ssp-t2` 30项定向测试及11个subtest通过，覆盖输入/私有声明重核、配置/命令/run归属漂移、旧proof、写权限意外成功、并发其他环境、启动超时、停止失败及错误候选/不完整/多份生命周期收据。`ssp-l2` Ruff和`ssp-a2`架构通过。真实VM结果与合成测试分别保存，详细身份沿[summary](summary.json)、[MANIFEST](MANIFEST.json)。

本机检查的CLI版本为0.8.107.0；通用API语义参考 [Microsoft Windows Sandbox CLI](https://learn.microsoft.com/en-us/windows/security/application-security/application-isolation/windows-sandbox/windows-sandbox-cli)，实际参数先核本机help，没有安装/升级软件或更改宿主设置。

外溢续查：当前Git只注册正式根一个worktree；旧三处迁移档案所指 `.project-local/mig` 在当前正式根未解析到。已查活动路由、资料索引、Record归档121条登记与已登记 runtime-migration 归档入口，尚无三组原件的直接恢复映射；没有遍历所有ZIP/CAS成员，不判SOURCE_MISSING或丢失，不追读其他项目/私有状态。此处是待追溯缺口，不是迁移或清理完成。533条精确ACL批次仍未出现执行结果，未再修改权限。
