# 星环知识系统前端 UI 分支任务包

目标：完整前端与可复用视觉资产，支撑多格式真实学习闭环和个人本地测试。

执行仓库：DTALEX66/ArcheAxis-Knowledge-OS。建议分支：feat/archeaxis-ui-v1，本轮未创建该产品分支。

1. 先读本文件、TASKPACK.md、TASKS.json 和 EXECUTOR_PROMPT.md。
2. 读取本仓实际 AUTHORITY／AGENTS／current／现行合同／Git 状态，核对分支与允许范围。
3. 查 shared/GLOBAL-DEPENDENCIES.json。按依赖拓扑执行，不按任务编号硬跑。外部包只提交所需合同或导出产物，不互相改仓。
4. 一项完成即更新现有执行账本与证据；复用已验证实现，不重做已完成步骤。
5. 依据 ACCEPTANCE.md 收尾；运行状态、安装、人工观察与宣传资格分开。

本包包含 26 个有依赖和验收的任务。延期范围保留在 TASKS.json，未接后端仍能完成明确交互外壳，但不能用夹具或占位结果宣称真实通过。

## 共同交付边界

正式产品使用 ArcheAxis／星环知识系统；AAOS 是内部代号。产品为本地优先的知识与 Human–AI 双向学习工作区。首期关注多格式、最快真实闭环、完整前端框架与基础文本小栖，多位测试者各自在本机使用。

主项目继续使用 Tauri 2、React 18、TypeScript、Vite、Rust Core 单写者及隔离 Python workers。ASTRYN 只持有人格、交互与人物表现；模型、长期记忆、上下文、任务和权限由主项目持有。WORKLAB／DESIGNLAB 独立运行、独立数据与凭据，Observer 只读，专业设计编辑回原生宿主。

本包是新分支的执行输入，产品任务为 PLANNED；已下载资产、合同提案和代码配方不表示产品已接通。旧任务在继承表中保留，未选择的 V01、FT01–04 和六核心历史增量不自动解冻。用户当前明确指令优先；实施者核对本包与当前权威、合同和实际代码，登记必要的新范围，不因为历史字段阻止已明确授权的新 UI 工作。

每个 checkout 只有一个 writer；用独立分支或隔离 worktree，保护现有 dirty/untracked 文件。运行资料、密钥、个人对话、模型权重和数据库不进入公开任务包或提交。例行可逆操作按当前任务授权继续；提交、推送、合并、安装发布及正式资料覆盖按当前会话与仓库现行授权处理，不能从此压缩包额外推导权限。

shared 中逻辑合同由 BE01 统一正式登记。前端和 ASTRYN 不能各自新建另一套模型中心、长期记忆库或泛用执行桥。Contract Proposal 明确是提案；执行前必须变成实际请求／响应 Schema、Rust／TypeScript DTO、有限命令映射和负面测试。


## 包完整性检查

解压后可运行 `python3 VERIFY_PACKAGE.py` 核对全部随包文件的 SHA-256 与尺寸。ASSET-MANIFEST.json 区分已打包源资产、参考图和待生产资产；PACKAGE-VALIDATION.json 记录本轮检查范围与未执行项。这些检查不代替产品安装或真实模型验收。
