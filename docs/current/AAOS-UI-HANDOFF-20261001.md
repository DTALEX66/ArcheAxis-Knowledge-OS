# AAOS 正式 UI 与真实后端接手交接（2026-10-01）

状态：`PARTIAL / TESTED_LOCAL`。当前 Authority 是项目配置索引、R6 不变任务包与 M0 优先级覆盖；本记录不替代它们。清理任务已由用户停止，缓存、历史文档、数据库和待核恢复包保持原样。

## 本轮完成与证据

- 母版逐页覆盖、资产、接口及验收差距见 `AAOS-UI-COVERAGE-MATRIX-20261001.md`、`AAOS-UI-MASTER-ASSET-AUDIT-20261001.md`、`AAOS-UI-ASSET-MANIFEST-20261001.json`、`AAOS-UI-BACKEND-MAP-20261001.md`。B10 母版无独立配图包，原版 HTML 内嵌 SVG/CSS；Formal 已有资产与 Green 未提交资产分别标明。
- 9 月 30 日 ZIP 只有任务文档、无可部署代码/图片；将其中规划与当前 Authority 分开记录在覆盖矩阵。
- 用户指定的四份 10 月 1 日外部文件已只读审计。`../history/external-inputs/2026-10-01/AAOS-ECOSYSTEM-AUDIT.md` 与 `AAOS-ECOSYSTEM-EXTRACT.json` 是本项目 AAOS 切片的归档副本和来源哈希索引。`R6-EXECUTION.md` 仅登记 `PROPOSED_NOT_EXECUTED` 后续输入；没有把外部文件指令升格为 Authority，也没有执行其清理/迁移提案。
- Formal Desktop 修复原生 capture 遗留 owned Core 导致下次启动 SQLite 写锁的缺陷；Review POST 后追加 GET 状态回读，只有真实匹配 event/item/assessment/answer 才显示成功。启动根因、真实 EventLog、隔离合成工作区证据见 `AAOS-DESKTOP-STARTUP-20261001.md`。
- Green `.ui-task-tree/ArcheAxis-Knowledge-OS-mainline` 保留原有未提交前端成果，定向镜像小补丁；嵌套工作树标准 launcher 资源 preflight 修复。该树 self-contained Release EXE 在合成工作区可直接启动，普通 GUI 标题为“已连接”、退出码 0，1280/720 DIP 原生截图分别见启动报告。原绿色版根目录尚未部署。
- Formal 16 模块定向测试 `262 passed`；Green 历史/新增合同范围尚有 32 项失败，分类见 `AAOS-GREEN-UI-TEST-DELTA-20261001.md`。这些测试和合成 SQLite 不代表真实用户数据全链路验收。

## 待闭合与下一步

1. 在 Green 隔离树处理 32 项合同差距，并逐页比对 B10 和其余母版的原生截图、主题、动画、DPI 与所有窗口尺寸。当前母版浏览器基准截图未产生，像素复刻状态为 `UNVERIFIED`。
2. 验证所有可用真实后端接口的页面级加载、空、错误、离线、变更及回读。Review 已有局部回读；完整真实用户工作区旅程未执行。
3. 确认有来源、版本和依赖证据的独立 Python runtime（含 FSRS），随后按 `scripts/release/assemble_green_candidate.py` 组包，运行严格 `verify_green_candidate.py --require-runtime --require-workers`，再在原 Green 根目录更新并原位启动验收。当前该环节 `BLOCKED`，不能把开发候选 EXE 称作已安装绿色版。
4. 将本轮属于公共仓的改动独立提交并上传任务分支，回读远端精确 SHA 与该 SHA 的 CI。Green 大量先存未提交修改须由对应 writer 核对，不能整树批量认领。

回退：Formal 本轮新增改动按单独提交回退；Green 隔离树仅对本轮精确文件补丁单独回退，保留既有用户修改。历史资料和数据库不参与回退或清理。

## 2026-10-01 阶段二增量（同日追加）

- 先前公共增量 PR #155 已合并：head `6621aab7b7e2067f0ffe0fcaad1f479f7fd691d6`，远端 main/merge `59498723a8d4e94c6314e490473ba6d60847c247`；该精确 main SHA 的 `CI` 和 `vnext-ci` 工作流均 success。它仍不是正式 UI 完成或 Green 根安装证明。
- 新集成树 `D:/All projects/ArcheAxis.Knowledge.Green-x64/.ui-task-tree/aaos-ui-phase2-integrate` 从此 main SHA 建立，保护原 Green mainline 的大量既有 dirty。并入 B10/B05 视觉改动：移动品牌块、Evidence 空态矢量图标和窄窗布局、Capture 双栏与草稿高度、Home 无真实趋势时的中性空态、Learning/Review 1160 整窗断点及 Learning 双栏比例。Review 的真实回读和 capture owned Core 释放逻辑在并入后保留。
- 该新树 Desktop Debug 构建 `0 warnings / 0 errors`；定向合同初次运行 `219 passed / 4 failed`，失败均为旧品牌/间距/占位文案/图标尺寸断言，已据当前 B10 控件结构调整。补充单测 `1 passed`，新增 Home 草稿/标题与知识人审合同 `4 passed`。最终 6 模块完整复验及原生多页验收仍待执行。
- 新树通过标准 `desktop_launch.py --fresh-workspace` 生成隔离合成库收据，原生 `--ui-capture home 1280 900 aurora` exit 0，截图在项目 `.project-local/runs/22cad761f8/ccb851cbb19e/artifacts/desktop-launch/c487a861f57b4e7aa359118bf357305e/phase2-home-1280.png`。该画面和既有 Green mainline 多页截图是阶段视觉证据，尚缺母版同尺寸像素对照、DPI、动效及全页面运行。
- 当前 Green mainline `.project-local/rt/runtime/python/python.exe` 已按 `uv.lock` 构造并在 `-I -B` 下导入 fsrs 6.3.2、FastAPI、Uvicorn 与应用入口。其后隔离候选组包与验证见下节；原 Green 根安装与真实用户库闭环仍未执行。Canonical 构造还生成 Green mainline 根目录被忽略的 `build/lib` 和 `build/bdist.win-amd64`，按用户清理禁令保留。

### 阶段二候选与真实 Core 空态回读

- phase2 capture 曾在 Core 启动前切页且不加载 worker profile，使页面停在“Core 未就绪”。现在只在显式 `AAOS_UI_CAPTURE_WAIT_CORE=1` 时加载同一 worker profile、启动 owned Core 后切页，并等待 Evidence/Home 数据回读；退出仍在 `finally` 中释放 owned Core。隔离合成库的 720 Monochrome Evidence 截图呈现“Core 已响应，但当前没有 Evidence anchor”，不再把未读状态冒充空列表。
- `phase2-ui-publish-workerfix-20261001` self-contained Release 发布 exit 0；新树 9 模块 UI/Review/capture 定向合同 `227 passed`（1 条既有 pytest config 警告）。
- 以当前 main commit/tree 加 dirty source snapshot 构造的隔离候选 `ArcheAxis.Knowledge.Green-vphase2-20261001-r2-x64` 首次严格 `verify_green_candidate.py --require-runtime --require-workers --require-provenance --expected-commit --expected-tree --require-current-source`：`ok=true`、20,081 文件、无问题。包内 Python 直接导入 fsrs 6.3.2。
- 此候选目录内使用自身 Desktop/Core/runtime/worker 和自身合成 `data/workspace.sqlite` 原位运行：720 Monochrome Evidence 截图 exit 0，SQLite 4096 字节，画面显示 Core 已响应且返回空 anchor。最初仅传新拼写 Core 环境变量导致离线；按候选 VBS 同时传兼容旧拼写后成功。所有这些均为合成库证据。
- 原位运行产生 `data/` 截图与 SQLite/WAL/锁文件。用户当前禁止清理，现保留这些文件；因此对这个**已运行目录**再次执行严格 verifier 会因未登记的 `data/` 文件失败。组装时生成的原始 ZIP 仍保留；未来安装须从经验证的洁净包另建 staging，不能把已运行目录直接当作严格验收通过的包，也不能覆盖原 Green 根未知数据。
