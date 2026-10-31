# 2026-10-30 权限定点恢复、长路径计量与外溢续查

本页冻结本次维护证据，不维护第二份当前进度；当前任务沿[活动指针](../../../current/AAOS-ACTIVE-EXECUTION.json)与[唯一执行记录](../../../current/AAOS-UI-FIRST-EXECUTION-20261009.md)。Owner 追加外溢数据追踪、迁移和清理，R5 交接审计与归档见[独立 intake](../../../../workspace/intake/20261030-r5-future-capability-review/README.md)。

## 三处读取权限已独立复核

Owner 在管理员 Windows PowerShell 执行只读检查及定点修复：3 个精确目录下 23 个对象，添加读取权限，0 错误，1 项测试 `.git` 原样保留。原始所有者为旧 CodexSandboxOnline；继承被保护且只有 OWNER RIGHTS/SYSTEM/Administrators。原始 review、逐对象原 SDDL、计划哈希、持久意图日志及回退驱动都在 `.project-local/runs/be268a2d33/acl-{review,repair}-20261030/` 保留。

Codex 当前普通 ALEX、管理员令牌 false：23/23 可列举或只读打开，23/23 ACL 与计划一致，23/23 原所有者未变，复核未写内容或权限。原管理员收据 `apply-20261030T1300461710855Z-b84cf22a-result.json` 仍保留其 `PENDING_UNELEVATED_VERIFICATION` 历史字段，本次后继核验另记 `unelevated-access-verification.json`，不重写旧证据。

模块模拟 v5 先验证添加3/恢复3、错误计划哈希、重复回退、并发权限变化、private/deny/junction/硬链接/其他所有者保留。只持久化 DACL Access 部分，不写 owner/group/audit，不重置继承。早期模块自动加载、Set-Acl 安全权限问题与首次普通权限复核的相对 Import-Module 失败原件保留；后者导致的无效核验已改用绝对模块路径并重做，不能计为第一次就通过。

## 长路径计量修正

`storage_report.py` 对长路径使用进程内扩展 Win32 拼写，覆盖目录枚举、DirEntry.stat、reparse 和 readlink；报告仍使用普通路径。私有名称仍先于 stat/下降检查，junction 不跟随。没有改系统长路径开关、ACL 或全局环境。

`acr-t2` 25 项定向检查通过，包括真实 >330 字符目录/文件、UNC 拼写、private 先拒绝、真实 Windows junction 和权限失败仍报告。`acr-size4` 同范围复测：137,784,982,873 可读逻辑字节，1,248,330 文件，534 个权限错误，长路径 FileNotFoundError 0，私有排除106。相对权限修复后的 `acr-size2`，854 个长路径错误消失，读到的字节和文件增加；新增 R5 归档/本次证据也计入。未删除文件，差值不能称释放空间。runs/candidates 仍超复核线，582 个布局项、31 个错误层级 run 和19个退役身份未因此归位。

`acr-size1` 把互斥的 rank/growth 参数组合而被 CLI 拒绝，原始退出2保留。中间 `acr-size3` 曾扩大 nested .git 排除范围，造成计量覆盖减少，不能用于大小/增长结论；该改法已撤回，正式 Git 字节仍计入，`acr-size4` 恢复原覆盖后复测。原始读数和失败不覆盖。

封存架构检查 `r5-arch1` 将不含 host/share 的裸 Win32 UNC 命名空间前缀误判为外部目标；守卫仅排除此完整裸前缀，完整 UNC/扩展 UNC/扩展盘符目标仍拒绝。`r5-gate1` 26项守卫测试通过，`r5-arch2` 架构及 `r5-lint2` 四个改动代码/测试的 Ruff 检查通过，原失败保留；未添加机器路径豁免。文档权威 `r5-doc2` 通过，后继封存结果另见本目录 verification，不将其绑定为产品测试。

## 剩余精确权限批次

534 个唯一权限入口均在本项目 `.project-local`；排除原样保留的测试 `.git` 后，533 条路径已固化为 `acl-remainder-20261030/artifacts/exact-roots.json`，SHA-256 `16daa3fb5aadabf19001fc32ce58b708587d9fd59a16bf8d06009a92b3237801`。没有据首次3处修复推断全仓已可读。

后继驱动复用模拟验证后的相同模块，仅旧所有者且相同受限 ACL 的对象符合补读取权条件；先对所有可处理对象保存逐项 SDDL 与计划哈希，再逐项复核/写 DACL。private、reparse、硬链接、deny、不同所有者/ACL、漂移或长路径异常均保留，不接管所有权、不扩大权限或执行清理。

当前 Codex 进程无管理员令牌；实际剩余批次尚未运行。Owner 在管理员 PowerShell 执行：

```powershell
powershell.exe -NoProfile -File "D:\All projects\ArcheAxis-Knowledge-OS\.project-local\runs\be268a2d33\acl-remainder-20261030\tmp\Repair-RemainingProjectReadAccess.ps1" -Action Apply
```

回退使用同一文件 `-Action Rollback`，逐对象比对修复后状态后恢复，不覆盖并发变化。普通权限前置门禁必须退出5且没有真实计划；这不是管理员实际修复通过。后继仍须用普通权限复核并再次分类遗漏项。

## 外溢追踪的已核范围

沿既有 20260928/29 迁移及体积记录，只复查8个精确历史路径：D 根 All/All-wal/All-shm/All.writer.lock，三个已登记 AAOS 临时源码/候选根，以及 C Temp 的 a0-frozen-4578-28499。8 个入口均在当前精确路径未解析到；本轮没有删除或迁移它们，没有读取数据库、扫描父目录或记入回收字节。历史指向的恢复材料仍需沿索引确认，不把旧别名失效写成原件丢失或本轮清理完成。

当前 Core/Host 进程按两个精确进程名查询，未发现匹配进程；没有输出无关命令行或凭据。这只是进程快照，不是所有历史输出来源已证明。系统/共享工具与 Agent 状态均不认领。

正式 `dev.py` 已按源码登记 TMP/TEMP/TMPDIR、Python、pip/uv/npm、Cargo、NuGet 和 dotnet 的项目/run/cache 落点；环境声明与静态检查不等于所有外部组件已实测。后继按“生产者→配置/命令/运行证据→所有者→精确源/目标→消费者/哈希/恢复→迁移及源清理”逐批推进，先止住生成外写，再处理可确认冗余。归属未知、活动数据和私有状态仍保留。

本轮新增实际删除/外部迁移均为0；此前两批99,089文件、51,068,863,617逻辑字节保持原身份，不能把本次计量变化相加。具体收据身份见同目录 MANIFEST，远端/云CI/Green/真实数据/模型设置未操作。
