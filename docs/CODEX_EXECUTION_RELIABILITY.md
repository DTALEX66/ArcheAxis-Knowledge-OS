# Codex Execution Reliability

> 适用范围：`Cognitive-Loop-OS` 的本地执行、Windows 命令、Git 交付、测试环境、运行时清理和完成证据。
>
> 本文件只保存长期规则。一次性任务的 SHA、PR、测试数量和临时路径应记录在 TaskPack、追加式状态日志或 CI 中，不复制到本文件。

## 1. 基线、分支与 writer

开始修改前，分别解析并记录：Git 根目录、当前分支、`HEAD`、当前分支的显式 upstream、预期基线、divergence、worktree 列表和 dirty paths。

- “当前分支等于其 upstream”不等于“当前分支等于 `origin/main`”。
- `git fetch` 后必须重新解析所依赖的 refs，不能复用 fetch 前展开的 SHA。
- 当前 checkout 含未知修改、不是批准的执行基线，或已有其他 writer 时，在项目内 `.hermes/task-runtime/` 创建隔离 worktree；不得覆盖或复用未知 writer 的树。
- 一个 checkout 只能有一个 writer。只读审查可以并行，但不得修改同一树。
- 未经单独授权，不 commit、push、创建或合并 PR、发布、重写历史。

推荐使用显式 refs：

```powershell
git rev-parse HEAD
git rev-parse origin/main
git branch --show-current
git for-each-ref --format='%(upstream:short)' 'refs/heads/<branch>'
```

## 2. Windows shell 与 Git 参数

执行命令前先确认当前方言是 PowerShell、cmd.exe、Git Bash/MSYS 还是 WSL。同一命令字符串中不得混用不同方言的路径、变量和转义规则。

### PowerShell

- 双引号会展开 `$var` 和 `$()`；含 `$`、`@`、反引号或 Git revision shorthand 的参数优先使用单引号。
- 不把 `$()` 或变量插值拼进 Git revision 参数；使用显式 refs、参数数组或必要时使用 `--%`。
- PowerShell 会把未引用的 `@{...}` 解析为 hashtable。优先避免该 shorthand；必须使用时写成 `'@{upstream}'`、`'@{1}'` 或 `'HEAD@{5 minutes ago}'`。
- 路径包含空格、括号或通配符字符时使用完整 Windows 路径和 `-LiteralPath`。
- PowerShell 非终止错误可能仍返回退出码 0。关键操作使用 `-ErrorAction Stop` 或 `$ErrorActionPreference = 'Stop'`，并验证最终状态。

### Git Bash/MSYS 与路径

- `/c/...` 只属于 Git Bash 语义；传给 Windows 原生程序时使用 `C:\...` 或 `C:/...`。
- MSYS 自动路径转换造成参数变形时，使用 `MSYS_NO_PATHCONV=1`、`MSYS2_ARG_CONV_EXCL=*` 或显式原生路径。
- 命令出现 shell parse error 时，先归类为 quoting/parsing failure，再以显式 refs 或正确引用重发；不得把它记录成仓库故障。

### 字符、编码与换行

- 仓库文本服从 `.gitattributes`；shell 脚本保持 LF，Windows `.bat`、`.cmd`、`.ps1` 按仓库声明处理。
- PowerShell 5.1 重定向可能写出 UTF-16；写文本时显式使用 UTF-8。中文 Windows 可使用 UTF-8 code page 和 `core.quotepath=false` 改善显示。
- 终端 ANSI 颜色控制码不是文件乱码。工具把文本报告为 binary 时，先检查 `utf-8-sig` 或 `utf-16`，不得直接判定文件损坏。

## 3. Python 与测试环境

测试前必须确认解释器、包管理器和依赖属于同一环境：

```powershell
Get-Command python
python --version
python -c 'import sys; print(sys.executable)'
```

- 项目指定 `.venv` 时，使用其精确解释器运行测试。
- 可选依赖缺失、解释器错误或环境配对错误标记为 `ENVIRONMENT_FAIL`，不得冒充产品回归。
- 在正确环境重跑通过后，分别报告首次环境失败和有效测试结果，不能抹去或混合两类证据。
- 只运行能回答当前风险的最小验证；完整门禁频率遵循 `docs/VERIFICATION_POLICY.md`。

## 4. 项目数据与精确清理

运行时缓存、日志、临时环境和测试状态写入已忽略的 `.hermes/task-runtime/`；用户需要保留的任务证据写入 `.hermes/task-artifacts/`。

清理必须满足：

1. 解析目标绝对路径，并证明它位于当前项目批准的运行时根目录内；
2. 只处理一个明确、可再生成的 exact target，不使用宽泛 glob、`git clean` 或跨项目枚举；
3. 删除前只记录必要的数量、字节、属性和 reparse 元数据，不读取无关正文；
4. 用原生工具核验 symlink、junction 或 reparse point，不跟随不受信任的链接边界；
5. 遇到 ACL 或 file lock 时，不提权改 ACL、不夺取所有权、不强杀共享浏览器、桌面、代理或认证进程；
6. 删除命令成功后再次验证 exact target 不存在。

最终状态只能是：

- `REMOVED`：目标曾存在，已验证不存在；
- `ABSENT`：执行前即不存在；
- `BLOCKED_RUNTIME_CLEANUP`：权限、占用或边界风险阻止安全删除，并保留证据。

Git 工作树干净与 ignored runtime residue 已删除是两个独立结论。

## 5. 失败分类与重试

命令失败后先分类，禁止原样重复相同命令：

| 状态 | 识别方式 | 下一步 |
| --- | --- | --- |
| `SHELL_PARSE_FAIL` | hashtable、引号、拼接 revision、语法解析错误 | 使用显式 refs、单引号或参数数组重发 |
| `PATH_TRANSLATION_FAIL` | MSYS 转换、相对路径层级错误、目标解析到意外位置 | 改用经过验证的绝对路径或正确相对基准 |
| `ENCODING_FAIL` | mojibake、UTF-16 痕迹、错误 binary 判断 | 显式解码和 UTF-8 写入 |
| `LINE_ENDING_FAIL` | bad interpreter、输出含 `\r` | 按 `.gitattributes` 恢复 LF/CRLF |
| `ENVIRONMENT_FAIL` | 错误解释器或依赖缺失 | 切换到项目批准环境再验证 |
| `BLOCKED_PROCESS_LOCK` | file in use、device busy | 等待持有进程正常退出，禁止强杀共享进程 |
| `PERMISSION_BLOCKED` | ACL 或沙箱拒绝 | 保持边界并请求必要的最小授权，或报告阻塞 |
| `PRODUCT_TEST_FAIL` | 正确环境中的真实断言失败 | 定位根因，修复后只重跑受影响门禁 |

## 6. PR、squash merge 与精确 SHA

- PR head SHA、merge SHA 和 `main` 当前 SHA 是不同事实。squash merge 后，PR head 通常不是 `main` 的祖先，不能只用祖先关系判断 PR 未合并。
- 合并状态应由 PR 状态、merge commit、目标分支 readback 和内容检查共同确认。
- CI 只能证明其实际运行的 `headSha`。分支 push、远端 SHA readback、文档或版本号不能替代 exact-SHA CI。
- 每次报告都要把本地实现、测试、分支发布、CI、合并和安装态运行分开。

## 7. 完成证据词汇

按实际达到的最高层报告，不跨层推断：

| 状态 | 含义 |
| --- | --- |
| `PLANNED` | 蓝图或 TaskPack 已存在 |
| `IMPLEMENTED_LOCAL` | 本地工作树已实现 |
| `TESTED_LOCAL` | 指定本地验证在明确环境通过 |
| `BRANCH_PUBLISHED` | 分支已推送且远端 SHA 回读一致 |
| `CI_PASS_EXACT_SHA` | 对应精确 SHA 的要求检查通过 |
| `MERGED` | 目标分支已确认包含交付内容 |
| `INSTALLED_RUNTIME_VERIFIED` | 安装态或真实运行态已按要求验证 |

规划发布不得表述为运行实现完成；本地测试不得表述为云端 CI；远端分支存在不得表述为已经合并；合并不得表述为安装态已验证。

## 8. 最终汇报最小字段

```text
PRECHECK: PASS/BLOCKED
IMPLEMENTATION: IMPLEMENTED_LOCAL/NOT EXECUTED/BLOCKED
TARGETED_TESTS: PASS/FAIL/ENVIRONMENT_FAIL/NOT EXECUTED
RUNTIME_RESIDUE: REMOVED/ABSENT/BLOCKED_RUNTIME_CLEANUP/NOT APPLICABLE
FULL_GATE: PASS/FAIL/NOT EXECUTED
COMMIT: NOT EXECUTED 或 SHA
PUSH: NOT EXECUTED 或 remote SHA
CI: NOT EXECUTED 或 exact SHA + URL
MERGE: NOT EXECUTED 或 merge SHA
INSTALLED_RUNTIME: NOT EXECUTED 或验证证据
CANONICAL_CHECKOUT_UNCHANGED: PASS/FAIL/NOT APPLICABLE
```

最终还必须检查 `git diff --check`、任务写集、`git diff` 和 `git status --short`，并说明回滚方式。
