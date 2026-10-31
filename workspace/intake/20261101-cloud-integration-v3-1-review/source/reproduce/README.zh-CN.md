# v3.1 定向补件：full-suite 包装脚本证据保全

## 结论

最小候选已实际完成故障注入与隔离控制流验证，**未重跑 AAOS 全量业务测试**。原始 v3 输入 ZIP 和恢复的证据树合计 1914 个文件，测试前后逐文件 SHA-256 完全一致。候选仅位于 `supplement/reproduce`，未覆盖历史 harness、deliverable、日志或 v3 ZIP。

修复 `harness/full_suite_reproduce.sh`：

- `RUN` 解析和 `cd repo` 失败即停止，不在调用者当前目录误运行。
- 每次用 `mktemp` 创建新 `.project-local/runs/<worktree-identity>/full-suite-<UTC>-<随机值>`；不复用旧 venv，不写原 `deliverable/config/full-ci-locked.txt`。
- 新锁导出到本 run 的 `.partial`，只有导出成功且非空才移动为正式输入。失败的 partial 留作证据，不供后续安装使用。
- 导出、校验、venv 创建、解释器/非 system-site 校验、依赖安装任一失败，立即停止其依赖门；每条命令有 stdout/stderr/退出码及开始结束 UTC。
- 安装完成后 9 个独立 gate 仍收集失败；有任何 gate 失败，wrapper 最后返回非零。
- 日志、锁配置、venv、初始数据根、临时文件、pycache、Cargo target、npm cache 属于本次 run。既有 Rust 工具链/Cargo registry 与 uv 下载 cache 可共用，但不据共享 cache 声称新运行证据。不会复制全部历史工件。

**业务路径边界：** `ARCHEAXIS_DATA_DIR` 初始传为本 run/data，`ARCHEAXIS_RUN_ROOT` 指向本 run。pytest 的真实 conftest 还会将数据目录覆盖到其自身 run/tmp 下的 TemporaryDirectory。因此只能描述“目标是本次隔离目录树”，不能说“所有业务数据始终位于 wrapper 的 data 子目录”。本轮 stub 测试仅证明环境变量与控制流传递，不是业务数据持久化实验。

## 实际定向测试

`evidence/results.json`：8 次运行、8 个不同 run 目录，断言全部通过。

| 注入情形 | 实际退出码 | 后续行为 |
|---|---:|---|
| uv export 先写 partial 再失败 | 23 | 无 venv/安装/业务 gate，旧锁未读取 |
| uv export 成功但文件为空 | 1 | validate-export 阻断后续 |
| venv 创建失败 | 31 | 不安装、不运行 gate，不复用旧环境 |
| venv 返回成功但缺少解释器 | 127 | validate-venv 阻断后续 |
| 安装依赖失败 | 42 | 不执行业务 gate |
| 一个独立 gate 失败 | 1（gate 本身 17） | 9 个门仍全部调用、最终不报 PASS |
| 第一次模拟成功 | 0 | 9 门调用、独立 run |
| 第二次模拟成功 | 0 | 新 run，不覆盖前次 |

另测 repo 不存在：非零停止，不创建 run，不执行任何工具。真实 Python venv 创建与配置检查参与测试；uv/npm/cargo 和业务脚本是明确标注的控制流 stub，没有下载依赖或伪造业务 suite 成绩。

首轮测试脚本把门数误写为 10，实际为 9，测试断言失败；原失败日志原样收录于 `evidence-attempt1`；本地诊断 fixture 保留但不收录 `fixture-attempt1`，校正测试计数后完成上述复测，不改产品 gate 以凑绿。

## 与旧 reproduce.sh 的边界

历史 `reproduce.sh` 先建立 repo，使用 `--system-site-packages` 建 worker/upgraded-worker venv，并写固定的 reproduced 输出位置。本补件不执行或改写它，也不将其所有步骤提升为干净/可重复发行资格。

本轮另建一次性 `--system-site-packages --without-pip` venv，实际 `sys.path` 包含宿主 Python 的 site-packages，`pyvenv.cfg` 为 true（证据 `system-site-probe.*`）。因此这种环境会继承未列入实验依赖清单的宿主包，不能声称完全封闭、全锁定的干净复现。候选 full-suite 则新建不继承 system site 的 venv，并实际检查 false；仍不等于锁定 OS、系统二进制、网络或整个机器状态。

运行本候选前，需要在**独立可写实验副本**准备 repo/工具链/前端依赖；不要直接在只读历史证据目录运行原 reproduce.sh。旧 reproduce.sh 的固定输出与系统包继承风险未被此一文件补丁自动修复。

## 复现与交付

- `full_suite_reproduce.sh`：候选完整脚本。
- `full_suite_reproduce.patch`：针对 v3 原 harness 的最小 patch。
- `full_suite_reproduce.original.sh`：用于差异比对的原字节副本；原件仍不变。
- `test_control_flow.py`：故障注入脚本；只测试包装器，不是业务套件。
- `evidence/`：真实 stdout/stderr、退出码、UTC、逐文件保全 SHA、patch 语法/应用检查。

`bash -n`、`git apply --check` 和将 patch 应用到一次性原文件副本后的字节比对均通过。每次重现故障注入请在新的独立测试目录放入候选、original 和测试脚本再执行，避免覆盖本次测试证据；不要删除旧 fixture 后冒充首次运行。实际 full-suite 脚本本身可重复执行，每次自动分配新 run。


## 真实配置解析的轻量补验

`verify_real_path.py` 使用当前获授权恢复源码的 `shared/config.py` 真函数，显式传入独立测试数据根；实际解析数据库、backups、api_keys 路径均落在该根内，exit 0。记录源码哈希、参数和实际返回路径于 `evidence/real-path.stdout`。同时只读核对真实 conftest 中 TemporaryDirectory 与环境变量覆盖语句，不执行其数据库初始化。该补验不是完整业务数据落盘/pytest运行证明。

打包仅收本目录顶层脚本、patch、说明及 evidence、evidence-attempt1、evidence-final；每次 run 的真实 command/stdout/stderr/exit/UTC 已单独复制到 evidence/run-receipts。不得打包 fixture、fixture-attempt1、missing-repo-fixture、system-site-probe 或任何 venv/原始历史工件全集。


最终字节回归：所有最终脚本修改完成后，再在全新的 `reproduce-final-validation` 目录执行同一套定向故障注入，8/8 场景及缺 repo 启动检查全部通过；新日期/原始日志见 `evidence-final`，未覆盖第一次成功或早期失败证据。`final-byte-binding.json` 将交付脚本/patch SHA-256 绑定到实际被测脚本字节，同时再次核对原 1914 文件不变。临时验证目录整体不打包。
