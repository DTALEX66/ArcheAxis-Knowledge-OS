# Backend runtime 直备与重复输入治理

正式 CI 的 `desktop-fast` / `desktop-build` 使用 `python -m desktop.scripts.prepare_bundle --backend-candidate`。旧入口先准备 `destination-python-input/runtime/python`，再由正式 stager 完整复制至 `destination/runtime`；消费者是正式 Tauri 资源与 frontend runtime qualification。本次已由 root 部署 3 个实现文件和 3 个测试文件，通过内部 callback 直接准备 fresh 最终 runtime，避免第二份 host runtime 树。初次 base Python 复制、依赖安装、默认独立 stager copy 和正式分发复制仍保留；没有实测生产包节省字节的声明。

未增加公共 CLI 特权、第二 manifest、通用 ownership 框架或成员前缀豁免。默认入口继续拒绝覆盖现存 destination；default copy 保留 donor。内部 callback 校验当前 canonical run/owner/source/允许输出位置，只接受 fresh root，保留依赖、Core/worker、SHA、link/nlink 检查。VC 仅精确 3 个已验证 DLL 与 ASR 精确成员/identity 的合法写入更新期望 SHA，其余漂移拒绝。UV_LINK_MODE=copy 仅作用于准备子进程；失败保留新根与 timing 失败记录。显式路径在 resolve 前排除 junction，fresh mkdir 与重复检查不等于长期 OS handle 锁定或原子 TOCTOU 保证。

资格按原快照分别保留：

- `spr-pyinput5`：候选加载模式，127 passed / 1 warning，22.40s；child/receipt0、source_consistent=true。这是候选合成资格。
- `spr-pa1`：已部署正式 7 测试路径，无 source overlay，127 passed / 1 warning，19.59s，pytest0；6 文件严格 Ruff1（11 项），所以 child/receipt1、总 FAIL、source_consistent=true。报告保留原 6 文件 SHA，不能改成总 PASS。
- Ruff 11 项中 3 项为本次新增：新 test import 排序/未用 sys，以及重写 desktop test 函数的 import 分组；8 项已由 HEAD 原字节对照证明既有。本次仅修新增 3 项，未处理旧 ProgramFiles 大小写、nested with、旧 import/unused 或异常命名。
- `pa2`：style 部署后正式新 test 文件严格 Ruff0，child/receipt0、source_consistent=true。只调整 imports/空行与删除未用 sys，未重跑 127 行为测试；127 测试仍绑定 `spr-pa1` 原 6 SHA，最终 2 个 style 文件 SHA 单列。全仓既有 E9/F63/F7/F82 gate 等 root 后继 finalrun，未在此冒称已执行。

测试使用真实 producer/stager 校验和布局，依赖安装/构建与合成解释器版本响应由 fixture 替代。覆盖 default copy 保留 donor、没有第二 runtime 树、失败保留、跨 run/owner/source/额外成员/中途漂移拒绝，以及实际 junction 的 output/Core/ASR/internal preparer 拒绝。Windows tmp_path 仅缩短到 canonical run/tmp/t/<counter> 避免 MAX_PATH，输入与断言不变。1 warning 是禁用 cacheprovider 后的 cache_dir 配置警告。

早期失败不改：`spr-pyinput3` 为 112 passed / 11 failed；只纠正 env 全量比较和 VC donor 的 fixture 前提。`spr-pyinput4` 对原 timing 测试单独执行 exit1（host 3.13 在模拟 dependency failure 前触发现存 3.12 guard）；候选只在该合成案例明确模拟 3.12.9，版本拒绝测试仍保留；后续候选 123 passed / exit0。

真实 wheel/uv/install、下载、应用 build、VM、模型与完整产品旅程本轮执行次数均为 0。该实现修复 host preparation 生成方式；完整生产打包、安装运行、旧 native producers 不在本轮资格范围。回退仅回退列明 6 个公共文件，不删 payload/失败证据。

MANIFEST 绑定部署前冻结证据、原候选/正式测试/后继 style 收据、命令、原资格 SHA 与当前最终 SHA。本导航为 canonical 终态后按 root 指示直接编写的 ignored 小型交付候选，不是新 canonical 收据；原收据/FAIL/patch 均未改。拟发布 `docs/history/storage-cleanup/2026-10-31-backend-runtime-in-place/`，由 root 唯一写入 tracked 与当前进度。
