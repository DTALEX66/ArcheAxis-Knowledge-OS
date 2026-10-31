# 2026-10-30 体积治理续批：生命周期副本与共享输入

本页是冻结维护结果。当前任务、授权和后继进度仍读取[活动指针](../../../current/AAOS-ACTIVE-EXECUTION.json)与[唯一执行记录](../../../current/AAOS-UI-FIRST-EXECUTION-20261009.md)。本轮接续 Owner 已授权的项目体积清理、文件规范化和后端优先任务；前端实施暂停，未进行远端写入或云端 CI。

本批仅删除 `zc1i` 首次失败沙盒中与保留的 `zc1i2` 完全相同的 672 个输入载荷文件：688,965,713 逻辑字节（约 0.642 GiB）、42 个空目录，错误 0。原始 inputs.json、WSB、staging/launch/stop 收据、失败输出和日志保留。逐文件映射保存旧路径、保留路径、大小和 SHA-256，可在核验后复制恢复旧路径；目录大小或失败状态均未作为删除依据。前批与本批累计删除 99,089 个文件、51,068,863,617 逻辑字节（约 47.562 GiB），不是物理释放空间的承诺。

后验核对：672 个原路径不存在，672 个保留替代文件哈希匹配，69 项保护文件不变。安装器、PowerShell、guest 脚本、混合身份文件四项实际复制恢复及哈希检查通过，验证副本已移除。当前 C1 候选树与 rollback、原始失败终态没有被重写，历史清场字段也没有因本机当前空闲而改成 PASS。

全仓可读逻辑计量为 137,761,270,223 字节（128.300181 GiB），相对前批基线减少 679,193,807 字节；本轮新增证据、测试输出和扫描时点会使它与精确删除字节不同。计量仍 PARTIAL，子进程原退出 1 保留；`NO_NEW_GROWTH_TRIGGER` 只表示没有新布局/净增触发，runs 与 candidates 的既有超预算、访问/长路径错误及未归位条目仍需治理。

## 生成方式的改动与边界

新增[共享输入检查工具](../../../../scripts/runtime/sandbox_inputs.py)。它复用 dev.py 的项目/run 路由和既有独立文件/哈希校验，核验整份清单后生成共享映射提案，不复制 payload、不改 ACL、不启动 VM、不执行输入中的脚本或安装器。[guest 虚拟路径配置](../../../../config/sandbox/shared-inputs.v1.json)声明固定四映射，代码验证其命名空间；这些路径不作为宿主文件落点，架构门禁保持启用。

在保留的 `zc1i2` 实际输入上，两次独立 run 均验证 672 成员、688,965,713 字节，三个输入映射指向同一来源且 ReadOnly=true，输出各自为空且路径不同；两次 payload 复制字节均为 0。该结论仅是主机端配置/字节验证，guest 写入隔离、安装、运行和 Owner 验收均 NOT_EXECUTED。

原 `zc1c8` 冲突旅程输入清单声明两项 `.mimosa` 私有状态。工具在读取任何声明载荷前拒绝，退出 1、无配置提案；只核清单元数据，没有读取私有正文。原件及原始成功证据保持不变。后继须从洁净源码身份准备新的共享输入；不得删除私有状态、改写旧清单或加豁免来换取通过。

现有冻结 launcher 要求 package/input 位于本次 run，尚不能消费共享映射；工具明确输出 `SHARED_MAPPING_LAUNCHER_NOT_QUALIFIED`，文件后缀保持 `.wsb.proposed`。共享 launcher 的哈希/映射/来源身份绑定、运行归属和真实 guest 隔离，是替换旧重试路径前仍需完成的工作，本轮不宣称已经全面阻止后续膨胀。未来启动前还须重新核验宿主可变输入，不能沿用一次历史哈希结果。

可重复的主机检查示例（历史输入若后续归档，先沿 manifest 查保留位置）：

```powershell
.\.venv\Scripts\python.exe scripts/runtime/dev.py --run-id sfi-YYYYMMDD-N -- .\.venv\Scripts\python.exe scripts/runtime/sandbox_inputs.py --stage "D:/All projects/ArcheAxis-Knowledge-OS/.project-local/runs/be268a2d33/zc1i2" --manifest-sha256 82f2c42901049665b8b85a4d9620bbcdfd67419025ebe2746956e02d4e0e7fef --prepare-proposal
```

## 验证与接续

最终代码的定向回归为 142 passed、1 skipped、20 subtests passed；Ruff E9/F63/F7/F82、架构和暂存索引格式检查通过。跳过项为本机文件 symlink 不可用的既有用例，Windows junction 反例实际通过。早期使用长 run 名导致既有测试 WinError 206，原失败保留；改用短 canonical run ID 后同一断言通过，未修改全局长路径设置或放宽测试。最终源码哈希与各原始退出码见[summary.json](summary.json)、[证据定位和哈希](MANIFEST.json)。文档/路径检查在唯一执行记录封存后另记，不把新增文字移绑为产品验收。

格式门禁原先拒绝冻结输入的 BOM/CRLF；现沿既有精确身份机制登记 12 份已由归档 MANIFEST 校验的材料和两份现存冻结 CSV，不豁免目录、修改内容或未登记副本。两份 CSV 的旧 Git blob 为 LF、现存工作树为 BOM/CRLF；添加精确 `.gitattributes` 后重新登记索引，保留现存字节，CSV 内容值未改。14 份材料的工作树、索引及 process-local `core.autocrlf=true` 实际 checkout 字节全部匹配，临时验证副本清除；14 个新增篡改/未登记路径反例通过。普通测试文件仅补末行 LF。最初 7 项架构拒绝、11 项格式拒绝及首次属性变更后未强制刷新索引的两项哈希拒绝均保留，不覆盖失败。

下一步顺序仍为体积/规范化：共享 launcher 与洁净冲突输入资格、旧候选相同载荷的消费者和恢复映射、既有散落/错误层级路径的归属与迁移；随后接既有 F01—F05 和 R2 后端要求。模型监听/网络和跨版本号仍按既有 Owner 待决边界，不用清理授权代替这些决定。新原始输出集中于 `.project-local/runs/be268a2d33/storage-followup-20261030/`；大型逐文件映射和日志留 ignored，Git 仅保留轻量索引。
