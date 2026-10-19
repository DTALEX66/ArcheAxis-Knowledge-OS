# HUB page17 consumer交叉审查

结论：**BLOCKED（原8文件提案应用）/ P1 前端入口新增未声明的Python依赖**。不阻断已应用的manifest准备合同；未修改原提案或产品，未跑完整构建。

## P1：Vite无条件同步Python语义检查不适配当前CI及standalone入口

原提案`proposal/frontend/vite.config.ts:27`在defineConfig回调入口无条件`execFileSync(projectPython(root), [...generate_capability_package_details.py, --check])`。该生成器导入现有validator，后者顶层导入jsonschema。原有frontend/package.json的dev/test/preview直接加载Vite，之前不要求Python/jsonschema；现增加此依赖。

当前`.github/workflows/ci.yml:1022` desktop-fast先npm ci并调用canonical frontend.py build；setup-uv在1030，`uv sync --frozen`在1061。该build之前只有setup-python，没有声明安装jsonschema。干净声明环境因此无法保证Vite配置可加载；本地完整venv的正/负/恢复证据不能覆盖这条路线。真实GitHub运行NOT_EXECUTED，不能声称已在CI观察失败，也不能依赖host image恰好预装包。

projectPython本身优先显式ARCHEAXIS_PYTHON或公共managed .venv，然后回退PATH python；这是既有构建路由，不是本提案改全局配置。但把它搬到所有Vite加载路径，使Node-only测试/预览也可能使用全局Python且缺模块。最小修复建议：Vite使用Node stdlib有限只读漂移guard；Python完整Schema/semantic验证保留在显式生成和合同测试，CI不需为了配置解析临时安装全局Python依赖。

## 已审查且未发现阻断

- root通过import.meta.url与frontendRoot解析，和现行canonical路径策略一致，没有引入process.cwd根错误。
- page17只用精确selected.atlas.capability_id筛选manifest.capability_ids，切换CAP不按相似名称联接。
- publisher authenticity UNVERIFIED、license UNVERIFIED/null、qualification UNKNOWN、runtime UNKNOWN分别显示。没有installed/enabled/执行按钮或把manifest hash提升为真实性/商用许可。
- 仍复用现有CAP、供体stable_key及route；生成器要求catalog精确CAP/route联接，不新增注册器、安装器、HTTP或执行入口。
- Python来源hash与生成物--check能阻止普通陈旧输出，但“有依赖的本地guard加载PASS”不能证明Node-only可用。

原冻结补丁：`16df8256ed8511d137c4d74e7668d551e1aabbd66cc344ed4a4c2b1c5dab188f`。本审查仅静态核对提案/正式入口/CI/依赖声明及作者配置加载回执；未改配置/依赖/锁文件。root已接受P1并授权另目录Node-only修正版，原提案保持冻结。
