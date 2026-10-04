# AAOS-01 Q02：**错误连续前移两格 —— 现已进入模块内部**

## 1. 三格的轨迹（每一格都由应用自述）

| 阶段 | 应用诊断里的错误 | 性质 |
| --- | --- | --- |
| 第 94 轮 | `ModuleNotFoundError: No module named 'app'` | 包不可导入 |
| 第 97 轮 | `ModuleNotFoundError: No module named 'yaml'` | 第三方依赖缺失 |
| **本轮** | **`File "<frozen runpy>", line … in _run_module_as_main`** | **模块**已找到并开始执行**，在内部失败** |

**这条轨迹说明修法每一步都生效**：`app` ✓ → `yaml` ✓ → **入口点真的跑起来了** ✓。

## 2. 本轮做了什么

把项目声明的依赖装进随包 runtime：

```
"%PY%" -m pip install --target "<runtime>\Lib\site-packages" --upgrade \
    pyyaml pydantic numpy requests fastapi "uvicorn[standard]" python-multipart \
    loguru structlog sqlite-vec beautifulsoup4 defusedxml apscheduler
```

**一次障碍**：`pip` 报 `externally-managed-environment`（该发行版由 uv 管理）。
**我没有用 `--break-system-packages`**，而是用了 **`--target`** —— 它把包装进 runtime 自己的
site-packages，**语义上正是我要的**，且不触发 PEP 668 检查。

**结果**：`PIP_EXIT=0`，装了 36 个包（`pyyaml-6.0.3`、`pydantic-2.13.5`、`sqlite-vec-0.1.9` …）；
**用启动器自己的 `-B -I`、中立 cwd 验证：`CORE_DEPS_OK`** ✓

## 3. ⚠️ 但应用把有用的那行截断了

诊断里只留下：

```
File "<frozen runpy>", line [redacted] in _run_module_as_main
File "<frozen runpy>", line [redacted] in _…        // ← 到此为止
```

**原因在源码**：宿主有 `MAX_LOG_LINES`/行长上限，界面只显示缩短后的行。
**所以我拿不到完整的 traceback** —— 而完整 traceback 才是下一步所需的。

## 4. 下一轮：绕过截断，自己跑那条命令

我可以**自己执行启动器会执行的那条命令**，看完整输出：

```
<runtime>\python.exe -B -I -m app.runtime_entrypoint migrate
   cwd / env 按 backend.rs:294-312 复现（含 ARCHEAXIS_DATA_DIR 等）
```

**要点**：指向一个**临时数据目录**，不碰真实产品数据；**只读诊断**，不改仓库。

**这样就能拿到应用界面给不出的完整 traceback。**

## 5. 我**不**声称的

| 不声称 | 原因 |
| --- | --- |
| 「迁移已通过」 | **没有** —— 它仍然是 `exit code: 1` |
| 「剩下的依赖只有这一批」 | **可能还有** —— 只是错误一直前移 |

## 6. 本轮改了什么（说清楚）

| 改动 | 位置 | 性质 |
| --- | --- | --- |
| 用 `--target` 把 36 个依赖装进随包 runtime 的 `site-packages` | `C:\Windows\Temp\aaos-target\release\...`（**临时构建目录**） | **只写构建产物，未碰仓库** |

**未改任何仓库文件**；**未触碰官方 Green 的 `data/` 与资料库**；**未删除仓库内任何东西**。
