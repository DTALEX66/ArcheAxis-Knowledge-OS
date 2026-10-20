# HUB003 manifest 能力详情消费接续入口

状态：**ISOLATED_CONSUMER_PASS / NOT_APPLIED / HUB003 PARTIAL**。

补丁：`capability-manifest-consumer.patch`，SHA256 **`16df8256ed8511d137c4d74e7668d551e1aabbd66cc344ed4a4c2b1c5dab188f`**，共8文件；详细before/after及镜像一致性见 `code-manifest.json`。本提案从已正式应用的 capability-package schema/validator/TS 合同继续，尚未写入产品。

## 实际消费链

明确提供的 `config/capability-packages/pdf-extract.manifest.json` 原字节 → 现有 `parse_manifest_bytes`（完整schema、CAP/stable_key/runtime声明、公共来源hash及当前宿主范围）→ 精确catalog CAP/route联接 → 只读生成TS → page17能力详情仅按选中的稳定CAP显示。

内置的是包说明，**不是内置/已安装pymupdf引擎**。不修改现有默认实现、worker route、catalog、许可结论或运行资格；无新registry/DB、安装/启用/执行按钮、HTTP入口或调用模型。发布者真实性UNVERIFIED、许可UNVERIFIED/null、独立资格UNKNOWN、当前runtime UNKNOWN分别保留。

## 已执行的隔离验证

- Python **11 passed**：真实字节身份、来源/兼容校验、CAP/route/stable_key错配、缺失/漂移与旧生成物拒绝。
- Vitest **2文件8 passed**：4项新增page17消费回归 + 原page17 4项；切换CAP不借用或残留包说明，显示未知/无执行权限。
- **完整镜像前端 TypeScript PASS**；两份新增Python Ruff PASS；生成投影 `--check` PASS。
- 真正加载提案Vite配置（没有启动服务）：原字节exit0；只追加一个空白、旧投影未更新时触发特定 `MANIFEST_PROJECTION_CHECK_FAILED` exit23；恢复字节exit0。详见 `vite-guard-validation.json`，不是随机异常负例。
- `git apply --check` exit0；没有提交、push、服务、浏览器、模型调用或产品写入。

实际命令、时间、日志hash与退出码：`validation.json`；公开输入初始hash：`BASELINE.json`。

## 串行应用的最小门禁

Root是唯一writer。先检查2个现有文件（`frontend/vite.config.ts`、`frontend/src/spaces/CanonicalCapabilitiesSpace.tsx`）before hash，遇现有变化逐项合并，禁止覆盖最新代码；其余6文件为新增。重新用项目Python生成并`--check`，然后运行新Python 11项、新+原page17 8项、前端TypeScript以及来源漂移负例。任何manifest/公共来源/当前宿主或生成输出变化都必须显式重生成并重验；启动/构建前检查失败不能继续使用旧生成物。

Vite hook只校验、不生成、不安装。当前版本的检查依赖现有项目Python与jsonschema；不适用于尚未接入的外部热加载安装。生成声明只证明构建时一致性，不是当前运行服务探测，也不是签名/商业许可或产物质量验收。

本轮归档只登记 **NOT_APPLIED**；不得与已应用22文件或原生旅程67312的资格合并。原生、真实引擎、外部产品、安装和Owner验收均 **NOT_EXECUTED/UNVERIFIED**。
