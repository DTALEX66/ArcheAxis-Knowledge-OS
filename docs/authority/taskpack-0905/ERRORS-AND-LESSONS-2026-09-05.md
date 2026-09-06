# 错误总结与经验教训 — DeepSeek 线（2026-09-05）

> 全部为本次会话实际发生、已修复的错误；每条含根因/修复/预防，避免旧坑复发。

## 环境/运行时类
1. **嵌入运行时 os.getenv 不读 env（Green python）**：sitecustomize 证明 env 在启动时存在，
   但模块函数内 getenv 返回空；追因多轮后以 sitecustomize 快照 + 文件兜底绕过（测试脚手架，已删）。
   - 修复/预防：验证阶段用 ps1 文件 + PYTHONUTF8=1；产品侧不依赖该运行时 quirk。
2. **PowerShell 控制台编码 GBK 乱码**：`ls-tree`/python 中文输出被按 GBK 误读。
   - 修复：`core.quotePath=false`、子进程二进制+UTF-8/surrogateescape 解码、PYTHONUTF8=1。
3. **DSH 的 pwsh 实为 Windows PowerShell 5.1**：默认命令按用户要求改走 PS7
   （`C:\Users\ALEX\AppData\Local\Microsoft\PowerShell\7\pwsh.exe`），复杂脚本 `.ps1` + `-File`。
4. **cargo 环境未就绪**：cargo 不在 PATH、CARGO_HOME 误指向 doc 目录。
   - 修复：显式 `RUSTUP_HOME/CARGO_HOME/PATH` + vcvars64 + `-c core.quotePath=false`。

## 规范/门禁类
5. **python 文本写入在 Windows 自动转 CRLF**：生成 manifest/证据触发 crlf/missing-final-newline。
   - 修复：`open(..., newline='\n')`、字节级 LF 归一；审计脚本改为 LF 写。
6. **gate 脚本绝对路径字面量**：`--out-dir /tmp` 触发 forbidden-absolute-path 架构守卫 → lint 红。
   - 修复：改相对占位 `ignored`（缺输入先报错，out-dir 未被使用）。
7. **gateplan 引号路径**：git diff 中文/空格路径被引号转义 → 误入 unclassified/漏门禁。
   - 修复：`-c core.quotePath=false --name-only -z` + surrogateescape 解析。
8. **风险类遮蔽**：兜底类（frontend/**/desktop/**）插入位置过早，遮蔽 ui/installer 专类。
   - 修复：兜底类后置到 docs-mechanical 之前；加回归测试守护 first-match 序。

## 漂移类（自审发现）
9. **cargo fmt 漂移**：20 个 vNext Rust 文件未格式化 → `cargo fmt --all` 修复。
10. **收据 PENDING_COMMIT 占位**：3 张早期收据 head_sha 未钉真实 SHA → 钉 9b4a4ec/55021e9/891118c。
11. **LEGACY_MANIFEST head_sha 滞后**：记录 a1c7ccd 落后最终 HEAD → 重跑审计刷新到当前。
12. **契约常量漂移**：crate STATUS_* 用旧短词（candidate/accepted/...）与词表 schema 不一致
    → 对齐 DRAFT/MACHINE_CANDIDATE/NEEDS_REVIEW/USER_ACCEPTED/USER_REJECTED/SUPERSEDED + include_str! 漂移测试。

## 数据/清理类
13. **migrate 误落仓库 data**：cwd 解析到仓库导致 operator 写仓库 db + 生成备份 → 删除新备份文件复原。
14. **在线备份 PermissionError**：运行锁文件被 msvcrt 排他锁，备份遍历读取失败
    → 修复 app/exchange/backup.py 排除运行时工件 + Green 捆绑同步 + 字节锁回归测试。
15. **外溢数据**：AppData 测试工作区 + .hermes 测试残留（tmp/web-tmp/quality-tmp）→ 清理。

## 结论
错误共 15 项，全部修复并留下对应回归/门禁/收据；教训核心：
- 任何 python 生成物显式 `newline='\n'`；git 列表类用 `-z`/quotePath=false；
- 兜底/专类规则按 first-match 语义排序并加测试；cargo fmt/test 每次改 Rust 后必跑；
- 收据/台账的 head_sha 与真实 HEAD 同步，自审纳入“漂移清单”。
