# AAOS-01 Q02/Q03 改接前基线：**Tauri 前端 16/16 套件、119/119 用例通过**（2026-10-04）

## 1. 基线结果（真实执行）

```
npm ci          -> added 181 packages, exit 0
npm test (vitest run) -> VITEST_EXIT=0
Test Files  16 passed (16)
Tests       119 passed (119)
Duration    7.56s
```

**日志**：`.project-local/runs/frontend-vitest-baseline.log`

**意义**：既有 Tauri 前端**是一个能跑、有测试的应用**（不是空壳）。任何"改接"都必须让这 16 个套件继续通过 —— 这是**可比的改前基准**。

## 2. 环境：一处必须记录的工具踩坑

直接用共用工具库的 scoop node（`10-toolchains\scoop\apps\nodejs-lts\24.18.0`）跑 `npm ci` **失败**：

```
npm error ENOTDIR: not a directory, mkdir 'C:\Users\ALEX\scoop'
npm error Log files were not written ... C:\Users\ALEX\scoop\persist\nodejs-lts\cache\_logs
```

**原因**：该 node 的 npm 把缓存/日志指向 `C:\Users\ALEX\scoop\persist\...`，而那个路径在这台机器上不可用。**这是环境问题，不是项目问题。**

**可用做法（已验证）**：把缓存指到项目自己的开发输出目录 ——

```powershell
$env:npm_config_cache = "<repo>\.project-local\runs\npm-cache"
npm ci      # -> exit 0，181 packages
```

另有一条无害警告：`esbuild@0.21.5` 的 postinstall 未被 scoop 的 allow-scripts 放行；实测**不影响** vitest（`@esbuild/win32-x64` 作为可选依赖已就位，测试全绿）。**记录现象，不夸大。**

## 3. 本轮**未**做的

1. **未改任何实现文件** —— 本提交只新增本文件。**改接尚未动手。**
2. **未跑 `cargo check src-tauri`** —— Tauri 宿主的编译状态**仍未验证**。
3. **未读** `job.rs` / `protocol.rs`；`readiness_payload_valid` 校验什么**未确定**。
4. `node_modules` 与 npm 缓存都在忽略目录内（提交后 `git status` 应为 CLEAN —— 若不为 CLEAN，说明忽略规则有洞，需单独处理）。

## 4. 下一项（Q03 先于 Q02 改接）

按包内"**共享合同先定归属**"，**Q03（类型合同与权限）应先于 Q02 的改接**：

1. 确定 **Core HTTP v2** 的 DTO 归属与生成方式（Q03 的产出）；
2. 再据此把前端 `client.ts` 的 `1.x` / `archeaxis-workspace` 迁到 v2；
3. 然后才动 `RuntimeSpec` + `runtime_command` 的启动目标。

**每一步后重跑本基线（16/119），确保不回退。**
