# R13 使用说明（简短）与同源证据

> 适用对象：在 Windows 上从**同一被测提交**运行 ArcheAxis Core 的人。
> 入口脚本：`scripts/launch/core_launch.py`（所有路径相对**仓库根**解析，不从安装目录推断）。

## 1. 一键启动与诊断

```powershell
# 依赖检查 + 端口诊断（不启动任何进程）
.venv\Scripts\python.exe -X utf8 scripts\launch\core_launch.py --check

# 真实拉起 Core：报告就绪端口，随后自动停止（用于自检/冒烟）
.venv\Scripts\python.exe -X utf8 scripts\launch\core_launch.py --probe

# 前台常驻启动（Ctrl+C 停止）
.venv\Scripts\python.exe -X utf8 scripts\launch\core_launch.py
```

- `--check` 逐项具名报告 9 项依赖（Core 二进制、Python、text/pdf/ocr 三个 worker、PyMuPDF、tesseract
  可执行、仓库自带 `tools/tesseract/tessdata/eng.traineddata`、cargo 包装器），并报告
  8001（DeepTutor 后端）/3782（前端）/11434（ollama）是否在用。**任一缺失即具名失败并给出退出码，绝不空成功。**
- `--probe` 用随机生成的启动声明拉起真实 Core（写 stdin 后关闭，触发 EOF），读到就绪行即报端口；
  退出码 0 表示真实进程报过就绪。
- 仓库路径含**中文与空格**（例如本机 `D:\All projects\...`）已按上述方式实测可运行。

## 2. 停止

```powershell
.venv\Scripts\python.exe -X utf8 scripts\launch\core_launch.py --stop
```

- 只停止**本工具自己记录过的**启动会话（状态文件 `.project-local/runs/launch/core-launch.json`）。
- 没有会话记录 / 进程已消失 → 幂等成功（`stopped=false` + 具名原因）。
- 记录的 pid 已被**无关进程复用**（镜像名不是 `archeaxis-api`）→ **拒绝终止**（exit 4）并保留状态文件供人查看。
- pid 仍在但超时未退出 → exit 4 具名失败。

## 3. 保存与恢复

```powershell
# 一致性备份（VACUUM INTO）＋ sha256 与 sidecar 记录
.venv\Scripts\python.exe -X utf8 scripts\launch\core_launch.py --backup
.venv\Scripts\python.exe -X utf8 scripts\launch\core_launch.py --backup --out <目录>

# 恢复：先把当前库移开再放回备份
.venv\Scripts\python.exe -X utf8 scripts\launch\core_launch.py --restore --from <备份文件>
```

- 备份用 SQLite `VACUUM INTO`，并记录**源库前后 sha256**；`source_unchanged=true` 才说明没动源库。
- **Core 会话仍在运行**时，备份/恢复均**拒绝执行**（exit 5 / 7），不会对活库操作。
- 恢复**绝不删除**被替换的库：先移动到 `<库名>.replaced-<UTC时间戳>`（同名冲突自动追加序号），
  再放回备份，并断言放回后的哈希等于备份哈希。
- 备份带 `.sha256` sidecar；sidecar 与实际哈希不符 → 拒绝恢复（exit 7）。非 SQLite 文件 → 拒绝恢复（exit 7）。

## 4. 交付物哈希 ↔ 被测提交

```powershell
.venv\Scripts\python.exe -X utf8 scripts\launch\core_launch.py --manifest `
  --artifact <交付物1> --artifact <交付物2> --out .project-local\runs\r13-package-manifest.json
```

- 清单包含 `tested_source_sha`（`git rev-parse HEAD`）与每个交付物的 `bytes` / `sha256`。
- **被跟踪工作树脏（tracked 文件有改动）时拒绝生成**（exit 8）——清单只能描述一个被测提交。
- 未跟踪路径只作为 `untracked_present` 记录，**不改变 tested sha**。
- 清单自身声明限制：哈希把交付物**绑定**到被测提交，它不是签名，也不是安装包。

## 5. 候选包（bundle）与自验证

```powershell
# 1) 先构建 release 版 Core（target 目录与测试运行器一致，落在 .project-local/build/cargo）
cargo build --release -p archeaxis-api --offline

# 2) 打成候选包，并输出 zip 及其 sha256
.venv\Scripts\python.exe -X utf8 scripts\release\build_candidate.py --zip

# 3) 验证候选包；--run 还会真的启动它、读到端口后停掉
.venv\Scripts\python.exe -X utf8 scripts\release\verify_candidate.py `
  --candidate .project-local\dist\archeaxis-core-<sha>-release-build --run --json
```

- 候选包 = **二进制 + 生成的 README + `CANDIDATE.json`**；清单记录**源提交**、构建种类、
  以及**每个文件的 bytes/sha256**。README 由清单生成，**清单又记录 README**，所以两者都不能被悄悄改动。
- `verify_candidate.py` **拒绝**四类情形：清单未记录的**夹带文件**、清单记录了却**缺失**的文件、
  **本仓库不存在**的源提交、以及**哈希/字节数不符**。退出码：0 通过、2 无候选、3 不一致、4 运行失败。
- **跟踪工作树脏时拒绝打包**（exit 5）：清单只能描述一个**被测提交**；确需打包未提交状态时用
  `--allow-dirty`，此时清单会把 `tree_clean_when_built: false` **如实记录**。
- **只有 debug 二进制时拒绝**（exit 2），除非显式 `--allow-debug`——那样清单标为 `debug-build`，
  **绝不**把 debug 当作 release 提供。

## 6. 明确的未完成（不声称）

- **没有**提供 MSI/EXE 安装包、代码签名、卸载器；本节是"候选包 + 同源哈希绑定 + 自验证"。
  **哈希绑定不是签名**：它只能证明"这些字节与这份清单一致"，不能证明"谁产出的"。
- 候选包**只含 Core 二进制**：没有 Python 运行时与 workers，因此**依赖 worker 的路由会具名失败**，
  不会静默返回空结果。
- 普通用户"导入—理解—练习—复习 + 机器调用—纠错—再调用"的界面旅程属 R10（宿主界面接线），本切片不含。
- 干净环境（另一台无工具链机器）的启动与重启恢复**尚未在此环境外验证**。

