# 仅留现用最新产物：实际清理记录

Owner 本次明确要求加速、复用已审结果，并删除最新构建和产物以外的旧生成物。本记录覆盖旧大包无限保留策略；主仓源码、原始输入、真实或未确认数据、私有状态与凭据不属于旧构建垃圾。

实际删除或解除 **558,412 个旧文件名 / 72,363,689,996 逻辑B（72.36GB）**，另移除 **62,128 个空目录**。28份最终actual收据只计一次；已缺失项、NO-OP、首轮HOLD、子收据和代理累计不重复入账。此前执行的六源清理不混入本批。硬链接仅解除选中名字，不等于物理释放。

| 同口径可读计量 | 清理前B | 清理后B |
| --- | ---: | ---: |
| 全仓 | 134,357,299,417 | 62,038,724,678 |
| `.project-local/runs` | 100,262,216,903 | 37,997,541,462 |
| `.project-local/build` | 14,078,469,637 | 7,231,859,415 |

全仓可读下界 **134.36→62.04GB**，净差 **-72,318,574,739B**。`finalsize-28d9b4a7` actual/wrapper均1、源码clean a33a6204且前后一致；原674访问错误、243私有排除及581布局条目逐项不变。PARTIAL、非原子、runs预算仍超限，不能宣称项目只剩最新版、全目录规范化完成或物理磁盘释放量。清理logical与全仓net因新小收据及非原子计量不同。

主要退役：旧便携包与Host/Core、安装器/打包release复制、旧Python/工具/仓库和guest输入副本、相同对象索引的旧clone复制pack、编译中间物、旧隔离浏览器缓存/生成截图及250个已终止现代pytest scope。Windows目录枚举的零ID/link占位导致首轮HOLD，旧结果保留，后继改用fresh `os.lstat`；真实DELETE拒绝未绕过。

最新 `ui-small-final-portable`（现用启动器）与 `cppcand1` 公共声明共38,589去重成员存在/size匹配，7个关键Core/Python/setup/pwsh叶匹配；四profile的58个顶层主输出metadata前后保持。`bpr1`、`ocrstage1`、`cnprep3`、`zc1c8`、cppns2最新setup及当前 `.project-local/rt` 资格依赖保留。只是清理保留验证，不是新运行/安装或Owner产品验收。

V12/C453/runtime-before 旧恢复端已按最新要求退役，旧clone需先恢复pack名字才能独立重放。原restore-map、FAIL/PARTIAL和POST保持历史原字节，不再承诺旧路径即时恢复。

仍保留：五个9月pytest scope的16,219叶/1,132,875,600B删除未成功，精确样例DELETE打开WinError5；一个旧conflict target整目录动作被执行策略拒绝（blocked by policy），未换工具/代理重试。两件尺寸异常、未确认工作区、原件、真实数据、私有目录及必要依赖不盲删。权限恢复的旧读取PASS不等于拥有DELETE权限。

持续规则已写入[目录权威索引](../../../DIRECTORY_AUTHORITY_INDEX.md)：保留现用最新与真实依赖；历史版本只留紧凑结论/manifest/必要原失败，旧大副本不因FAIL标签永久保留；测试temp与fixture复制同属生成物。现有便携producer增长门禁以本次原始POST作为固定治理基线，不逐包上调。其他producer尚未全面自动执行保留/增长约束，不宣称已有后台清理或全仓预算PASS。

完整28份收据身份、增量、保留核验、原拒绝与原始POST见[机器记录](LATEST-ONLY-RETIREMENT.json)。唯一实际进度仍沿[执行记录](../../../current/AAOS-UI-FIRST-EXECUTION-20261009.md)。无新产品代码、构建、云端操作、ACL修改、Green替换或真实库覆盖。
