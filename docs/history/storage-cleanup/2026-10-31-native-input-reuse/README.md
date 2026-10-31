# Native 输入复用：宿主准备与离线映射的有限资格

正式入口 `scripts/runtime/native_inputs.py` 复用现有共享沙盒机制，只接受已审 `cnprep3` 历史公开工具胶囊及完整清单 SHA `f5e1b73674dd9110d51d7b81912c50b7ad46b18af2e8df068bac3dbd25754d0f`。三组输入为 package 14、input 5,806、PowerShell 657，合计 6,477 成员、1,984,670,438 逻辑字节；先审全部声明及目录库存，再核所有载荷 SHA、独立文件和祖先无 reparse。没有新增私有路径豁免或修改历史输入。

## 已执行

候选 `spr-nativecand4` 的四组 host 回归为 94 passed、14 subtests passed，PowerShell AST 通过。早期长路径/命名空间失败保持原始记录；缩短测试临时目录名，没有修改旧测试断言。候选和 VM 均绑定 `f5d8b570` + dirty patch `2ce0aa81962609e0f867975c18db68f68b134b47d17d8b9005dbd351fe97e55c`，不是干净 HEAD 的产品构建资格。

唯一 VM `spr-nativevm1` / owned ID `1683c059-decc-4082-9f19-126bbfedc839` 完成离线 mapping-only：保持原四个虚拟映射，三输入只读、独立输出可写，移除 `LogonCommand`，没有 connect、安装器、旧 parent 或 native/UI 业务。guest 对全部 6,477 成员计算的树 SHA 与 host 绑定一致；三代表文件的 write-open 都被拒绝，fresh marker/nonce/owned ID 一致。宿主完整输入事后重核；官方只停止该 ID，最后库存为空，实际 probe/wrapper 0、source_consistent=true。

本轮协作控制有一处缺口：root 要求先审具体脚本时，代理的 canonical 启动调用已经返回 running；消息后检查见 start-intent 和前三份官方收据，之后仅封存该在途 ID 并清场，没有新 VM 或重试。缺少独立消息壁钟，不能据文件 mtime 推断消息与 intent 的毫秒顺序；不能描述为具体脚本预审已完成。root 随后审阅实际 runner/配置/源码，独立只读复核未发现可确认 P1/P2 阻断。后续执行须等待明确放行窗口。

部署后 `r6n1` 在任何测试/prepare 前因模板 raw SHA 不同拒绝：仓库既有 `*.ps1 eol=crlf` 将候选 LF 6,512B / SHA `ff7e4213eccf309d126a8c6bfa01e7fa1888ecdd2afb1d9534e2c3cd60161d52` 转为 CRLF 6,606B / SHA `8826f6f2a51a82f5899ad05e81607c124cec942a87ee4369f77eb7356dbe3a7d`。原失败保留；没有修改 `.gitattributes`。`r6n2` 精确验证只有该换行转换，三 Python 文件 raw SHA 与候选相同，同 binding 经实际模板生成的完整 encoded command 与原候选相同。

`r6n2` 在实际正式源码上 94 passed、14 subtests passed（1 条既有 cache_dir 配置警告），真实 CLI `--prepare-native-probe` 退出 0，全量复核上述输入并生成 fresh config/output，未启动 VM；actual/wrapper 0、source_consistent=true，dirty patch `9b61d5f632933c5540940299c5079074e5551898d9aefb0010973b80021e6c1c`。候选 VM 的 raw LF 模板身份与部署后 raw CRLF 身份分别记录，不冒称字节相同。全部收据 SHA 见 MANIFEST。

## 如何接续及限制

沿 `dev.py` 的新唯一 run 使用 `native_inputs.py --stage <已审 cnprep3> --manifest-sha256 <上述SHA> --prepare-proposal`，仅写 `native-retry.wsb.proposed` 与 fresh `native-output`。共享入口 `shared_sandbox.py --prepare-native-probe` 仅准备移除 native 命令的探针配置；`--execute-native-probe` 只执行映射探针，使用 fresh owned ID、先落意图、精确停止及输入事后核验。本记录不自行授权再运行。

**零拷贝只指宿主输入准备和映射。** 每次不再向新 run 复制这三组载荷；这不是已经释放的磁盘字节，也不保证后续业务全程零复制。原 `guest-launch.py:57` 仍复制 source 到 guest capsule，`guest-parent.ps1:118` 仍复制合成快照到 output。旧生产者整体替代仍 PARTIAL。

原 native 命令在 `.wsb.proposed` 中仅作 prepared-only 保全，本次未实现其新的受控业务执行入口、未运行该命令。未来使用前必须重新核全部输入 SHA、空输出、候选身份及 owned 生命周期，并单独验证 native 业务。宿主输入未长期加锁，仍可能变化；保留原输入及恢复链，不能据本次映射结果清理来源。没有产品/安装/Owner 验收、模型调用、真实资料操作或目录删除。当前进度只沿[唯一执行记录](../../../current/AAOS-UI-FIRST-EXECUTION-20261009.md)。
