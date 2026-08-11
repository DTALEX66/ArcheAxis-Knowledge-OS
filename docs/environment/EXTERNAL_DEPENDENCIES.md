# ArcheAxis Learning Workspace — External Dependency & Environment Configuration

> 文档位置：`D:\All projects\OS configuration\EXTERNAL_DEPENDENCIES.md`
> 仓库同步：`docs/environment/EXTERNAL_DEPENDENCIES.md`
> 更新：2026-08-12
> 生产主机：Windows 10/11 x64
>
> **本文是项目外置依赖的唯一权威文档。任何新增系统工具、模型文件、外部服务
> 或环境变量必须在此登记。CI 与本地开发环境均以此文档为准。**

---

## 0. 环境变量（会话级，不写注册表）

| 变量 | 值 | 用途 |
|---|---|---|
| `UV_CACHE_DIR` | `D:\All projects\OS configuration\uv-cache` | uv 包缓存 |
| `UV_PROJECT_ENVIRONMENT` | `D:\All projects\OS configuration\cognitive-loop-os-ci-venv` | 项目虚拟环境 |
| `HERMES_HOME` | `C:\Users\ALEX\AppData\Local\hermes` | Hermes Agent 配置（全局） |
| `PYTHONPATH` | 清空（显式 `env -u PYTHONPATH`） | 避免污染 uv 环境 |

---

## 1. 系统级工具（必须安装）

### 1.1 Python 3.11+

- **用途**：运行时
- **版本**：3.11.15（主）/ 3.14.6（辅）
- **下载**：https://www.python.org/downloads/windows/
- **管理**：scoop（`scoop install python311`）
- **验证**：`python --version` → `Python 3.11.x`

### 1.2 uv（Python 包管理器）

- **用途**：依赖锁定、虚拟环境、包安装
- **版本**：>=0.7
- **下载**：https://github.com/astral-sh/uv/releases
- **安装**：`scoop install uv` 或 `pip install uv`
- **验证**：`uv --version`

### 1.3 Tesseract-OCR

- **用途**：图像 OCR 引擎
- **版本**：5.5.0（tesseract）+ 1.85.0（leptonica）
- **下载**：https://github.com/UB-Mannheim/tesseract/wiki
- **语言包**：额外安装 `chi_sim`（中文简体）和 `eng`（英文）
- **路径**：`D:\All projects\OS configuration\toolchains\scoop\shims\tesseract`
- **验证**：`tesseract --version`
- **Python 绑定**：`pytesseract>=0.3.13`（pyproject.toml 中已声明）

### 1.4 FFmpeg

- **用途**：音视频解码、格式转换、关键帧提取
- **版本**：>=6.0
- **下载**：https://ffmpeg.org/download.html
- **路径**：`D:\All projects\OS configuration\toolchains\scoop\shims\ffmpeg`
- **验证**：`ffmpeg -version`
- **许可注意**：构建选项决定 LGPL/GPL；项目只用 LGPL 子集

### 1.5 Git

- **用途**：版本控制
- **版本**：>=2.40
- **下载**：https://git-scm.com/download/win
- **验证**：`git --version`

### 1.6 Node.js（可选，仅桌面构建）

- **用途**：Tauri 桌面壳构建
- **版本**：LTS（当前 22.x）
- **下载**：https://nodejs.org/
- **验证**：`node --version`

---

## 2. Python 包（pyproject.toml 管理）

全部由 `uv lock` 锁定。以下按用途分组：

### 2.1 核心运行时

| 包 | 版本约束 | 许可 | 用途 |
|---|---|---|---|
| fastapi | >=0.133,<0.134 | MIT | Web 框架 |
| uvicorn[standard] | >=0.22 | BSD-3 | ASGI 服务器 |
| pydantic | >=2.0 | MIT | 数据验证 |
| pydantic-settings | >=2.0 | MIT | 配置管理 |
| python-multipart | >=0.0.20 | Apache-2.0 | 文件上传 |

### 2.2 数据处理

| 包 | 版本约束 | 许可 | 用途 |
|---|---|---|---|
| numpy | >=1.24 | BSD-3 | 数值计算 |
| pillow | >=10.0 | Historical | 图像处理 |
| pyyaml | >=6.0 | MIT | YAML 解析 |
| requests | >=2.28 | Apache-2.0 | HTTP 客户端 |
| beautifulsoup4 | >=4.11 | MIT | HTML 解析 |
| defusedxml | >=0.7.1 | Python-2.0 | 安全 XML 解析 |

### 2.3 数据库与搜索引擎

| 包 | 版本约束 | 许可 | 用途 |
|---|---|---|---|
| sqlite-vec | >=0.1.6 | Apache-2.0 | 向量索引 |
| apscheduler | >=3.10 | MIT | 任务调度 |

### 2.4 日志与观测

| 包 | 版本约束 | 许可 | 用途 |
|---|---|---|---|
| loguru | >=0.7 | MIT | 日志 |
| structlog | >=24.0 | MIT OR Apache-2.0 | 结构化日志 |

### 2.5 多格式转换引擎

| 包 | 版本约束 | 许可 | 用途 |
|---|---|---|---|
| markitdown[pdf,docx,pptx,xlsx,xls] | >=0.1 | MIT | PDF/Office 文本提取 |
| trafilatura | >=1.6 | Apache-2.0 | 网页正文提取 |
| pytesseract | >=0.3.13 | Apache-2.0 | Tesseract OCR 绑定 |
| networkx | >=3.0 | BSD-3 | 图计算 |

### 2.6 LLM Provider

| 包 | 版本约束 | 许可 | 用途 |
|---|---|---|---|
| litellm | ==1.91.0 | MIT（核心） | LLM Provider 路由 |

### 2.7 吸收实现新增（PR #81，待 merge）

| 包 | 版本约束 | 许可 | 用途 |
|---|---|---|---|
| jiwer | >=3.1 | Apache-2.0 | CER/WER 计算 |
| rapidfuzz | >=3.9 | MIT | 文本对齐 |
| fsrs | >=5.0 | MIT | 间隔重复调度 |
| onnxruntime | >=1.18 | MIT | ONNX 模型推理 |

### 2.8 CI/测试（dependency-groups ci）

| 包 | 版本约束 | 许可 | 用途 |
|---|---|---|---|
| pytest | >=7.0 | MIT | 测试框架 |
| ruff | >=0.5 | MIT | Linter/格式化 |
| playwright | >=1.61,<1.62 | Apache-2.0 | 浏览器自动化 |

---

## 3. 内置（Vendored）第三方资产

这些不是 pip 依赖，而是直接复制进仓库的源码/模型/二进制文件。

### 3.1 PDF.js

- **来源**：https://github.com/mozilla/pdf.js
- **版本**：3.11.174（上游当前 5.x）
- **许可**：Apache-2.0
- **位置**：`app/workspace/ui/assets/pdf.min.js` + `pdf.worker.min.js`
- **许可文件**：`app/workspace/ui/assets/licenses/pdfjs-3.11.174-LICENSE.txt`
- **记录**：`THIRD_PARTY_NOTICES.md`
- **升级**：独立 spike，验证兼容/CVE/WebView/包大小后再升

### 3.2 Magika ONNX 模型（PR #81，待 merge）

- **来源**：https://github.com/google/magika
- **模型**：standard_v3_0（3.1 MB ONNX）
- **许可**：Apache-2.0
- **位置**：`shared/models/magika/model.onnx` + `config.min.json`
- **许可文件**：`shared/models/magika/LICENSE`
- **推理代码**：`shared/file_detection.py`（纯 Python，无 magika pip 依赖）

---

## 4. 外部 API 服务（无需安装，但需网络）

### 4.1 证据查询 API

| 服务 | 地址 | 认证 | 限制 |
|---|---|---|---|
| Crossref | https://api.crossref.org/ | 无（polite pool） | ~50 次/秒 |
| DataCite | https://api.datacite.org/ | 无 | ~50 次/秒 |
| OpenAlex | https://api.openalex.org/ | 可选免费 key | 10次/秒（key）/ ~10次/分（无key） |
| Wikidata | https://www.wikidata.org/ | 无 | 1 次/秒（礼貌） |
| Europe PMC | https://www.ebi.ac.uk/europepmc/ | 无 | 5 次/秒 |
| NCBI E-utilities | https://eutils.ncbi.nlm.nih.gov/ | 可选 key | 3 次/秒（key）/ 10次/秒（key） |
| Open Library | https://openlibrary.org/ | 无 | 低频（批量用 dump） |

### 4.2 LLM API（通过 LiteLLM）

| Provider | URL | 用途 |
|---|---|---|
| DeepSeek | https://api.deepseek.com/v1 | 主要推理（deepseek-v4-pro） |
| 其他 | 由 LiteLLM 配置决定 | 备选/回退 |

---

## 5. 本地运行时服务（开发/测试用）

| 服务 | 端口 | 启动 | 用途 |
|---|---|---|---|
| FastAPI Gateway | 8000 | `uv run python -m app.runtime_entrypoint` | 主网关 |
| FlClashCore 代理 | 7890 | 由 FlyintPro 管理（禁止强杀） | 系统代理 |

---

## 6. 工具链路径（scoop 管理）

```
D:\All projects\OS configuration\toolchains\
├── downloads/          # scoop 下载缓存
├── playwright/         # Playwright 浏览器
├── rust/               # Rust 工具链（Tauri 构建用）
├── scoop/              # scoop 安装根目录
│   └── shims/
│       ├── python3      → Python 3.11
│       ├── tesseract    → Tesseract 5.5.0
│       ├── ffmpeg       → FFmpeg
│       └── ...
└── wsl2/               # WSL2 配置（备用）
```

---

## 7. 安装清单（从零开始）

```powershell
# 1. 安装 scoop（Windows 包管理器）
#    https://scoop.sh

# 2. 系统工具
scoop install python311 git tesseract ffmpeg nodejs-lts

# 3. Tesseract 语言包
tesseract --list-langs  # 应有 eng + chi_sim

# 4. uv
pip install uv

# 5. 环境变量（用户级）
setx UV_CACHE_DIR "D:\All projects\OS configuration\uv-cache"
setx UV_PROJECT_ENVIRONMENT "D:\All projects\OS configuration\cognitive-loop-os-ci-venv"

# 6. 克隆仓库
git clone git@github.com:DTALEX66/Cognitive-Loop-OS.git "D:\All projects\Cognitive-Loop-OS"
cd "D:\All projects\Cognitive-Loop-OS"

# 7. 安装依赖
uv sync --frozen

# 8. 验证
uv run python -c "import fastapi, pydantic, numpy; print('core OK')"
uv run python -c "import pytesseract; print('tesseract OK')"  # 需系统安装 Tesseract
uv run python -m pytest tests/test_workspace_api.py -q  # 基础测试

# 9. 启动
uv run python -m app.runtime_entrypoint
# 访问 http://127.0.0.1:8000/workspace
```

---

## 8. GitHub 仓库描述（固定字段）

当前描述：
```
ArcheAxis OS — a local-first, evidence-driven, bidirectional Human–AI Learning Workspace for individuals and AI.
```

**注意**：GitHub 仓库描述（About section）是固定字段，更新受限。产品名 "ArcheAxis Learning Workspace" 已在此文档和仓库的 `AGENTS.md`、`app/main.py`、`docs/PROJECT_STATUS.md` 等文件中使用，但 GH 描述字段中的旧名 "ArcheAxis OS" 暂不在维护范围内手工修改。后期更新绕开此字段，以仓库内 `app/main.py` 的 `title` 为准。

---

## 9. 更新规则

1. 任何新增系统工具、模型文件或外部 API 必须在本文档登记
2. `pyproject.toml` 依赖变更自动反映到 `uv.lock`；本文档手动同步
3. 文档同步位置：`D:\All projects\OS configuration\EXTERNAL_DEPENDENCIES.md`（本地） ↔ `docs/environment/EXTERNAL_DEPENDENCIES.md`（仓库）
4. 每季度或用重大版本升级时复审一次
