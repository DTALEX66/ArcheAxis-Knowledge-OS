# AAOS-01：打包流水线仍只产出 Python runtime —— 这是资源表失败的根因（2026-10-05）

## 1. 事实

CI 用 `python -m desktop.scripts.prepare_bundle --repository . --destination .project-local/rt`
准备资源（`ci.yml:918-922` 的 desktop-fast、`:994-998` 的 desktop-build）。
该脚本（`desktop/scripts/prepare_bundle.py`，111 行）**只产出 Python runtime**：

```python
18: def prepare_bundle_runtime(*, repository, destination):
25:     staged_python = stage_runtime(repository=repository, destination=destination)
26:     requirements = destination / "requirements.locked.txt"
27:     wheels = destination / "wheels"
93:     "import app.runtime_entrypoint, fastapi, uvicorn; print('installed runtime imports passed')"
```

**没有 `core/`，没有 `workers/`，没有 `shared/`。**

## 2. 因此

| 结论 | 依据 |
| --- | --- |
| **我上次把 `core`/`workers`/`shared` 加进资源表会失败，是必然的** | CI 的 `.project-local/rt` 里根本没有这些目录，`tauri-build` 因缺失资源路径报错 |
| **`prepare_bundle` 不产出 Core ⇒ 正式壳拿不到 Core** | 于是先前加的 Core 发现会返回空，**壳静默回落到 legacy entrypoint** |
| **CI 构建的产物至今仍是 Python 后端产品** | 第 93 行断言 `import app.runtime_entrypoint` |

**即：Tauri→Rust canonical 接管**没有**接进打包流水线** —— 第 132 轮的 Q02 更正（「legacy 接线可运行；Tauri→Rust canonical 接管未完成」）在此得到机制层面的证据。

## 3. 所以正确的下一步不是资源表

**先让流水线产出 Core，再让资源表指向它。** 顺序反了就会重现我那次失败：

```
正确顺序：
  1. prepare_bundle（或其后一步）把 core/archeaxis-api.exe 与 workers/ 落到 .project-local/rt
     —— 复用已有的 scripts/release/stage_backend_runtime.py，或按 CI 的方式构建 Core
  2. 资源表加入 core/、workers/、shared/
  3. 构建出包并确认资源真的落位
  4. 再做窗口级第一验收
```

## 4. 我这一轮的错误（记录，避免重犯）

**我在上一步直接把资源表改了，而没有先读 CI 是怎么准备资源的。**
**结果：把「本地能过」当成「CI 能过」，红了一个必需门禁。**
**教训**：**改打包/资源相关的东西之前，先读那条 CI 步骤到底产出什么。**

## 5. 未完成

`prepare_bundle` 仍未产出 Core；资源表仍只有 `runtime`；窗口级第一验收未做；
引擎身份/定位损失/重启读回未采集；依赖闭包仍由调用方给；长根 MAX_PATH；`runtime_jobs.rs:285` flaky。
