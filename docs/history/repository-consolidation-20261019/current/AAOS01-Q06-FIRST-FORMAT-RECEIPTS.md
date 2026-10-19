# AAOS-01 Q06 首个真实切片：**三种格式的真实回执**（不是通过声明）

绕过 Tauri 宿主（本机卡在路径空格），改用**已跑通的产品现场**：临时库 → `runtime_entrypoint migrate` → 起 app → **把真实文件投进去**。

## 1. 方法与样本

`POST /workspace/api/intake/upload`（multipart，本地调用），样本取自仓库内的**真实素材**：

```
crates/archeaxis-archive/tests/fixtures/obsidian-vault/notes/index.md
crates/archeaxis-archive/tests/fixtures/obsidian-vault/vault.canvas
crates/archeaxis-archive/tests/fixtures/obsidian-vault/attachments/diagram.png
```

## 2. 逐项真实结果

| 样本 | format | engine | 状态 | 原件哈希 |
| --- | --- | --- | --- | --- |
| `note.md`（734 B） | `md` | **`passthrough`** | 200 | `76fc557e…` **与源文件一致** |
| `board.canvas`（1040 B） | `canvas` | `json-canvas` | 200 | `7c28a78d…` **与源文件一致** |
| `picture.png`（69 B） | `png` | — | **失败** | — |

## 3. 这三条结果**各自说明了什么**（这才是重点）

### (a) `.md` 只是 **passthrough** —— 不算结构提取

```json
{ "format": "md", "engine": "passthrough", "char_count": 734,
  "requires_human_review": true,
  "content_preview": "---\ntags: [vault, sample, roundtrip]\ncanvas: \"[[vault.canvas]]\"\n---\n\n# Index\n…" }
```

**引擎名就是 `passthrough`** —— 内容被原样带过，**没有结构化提取**。
按包内标准「**probe、元数据、保留原件、旁路未知字段都不能算全部能力通过**」，**这一条不能算通过**。

### (b) `.canvas` **产品自己承认只是保管**

```
"Custody only: no ingest route claims .canvas yet."
```

engine 是 `json-canvas`，`char_count` 只有 131（原文 1040 B），内容里**明确写着没有摄入路由认领 `.canvas`**。

**这是产品在诚实自述缺口**，而且比我去推断更可信。**同样不能算通过。**

### (c) `.png` 失败，但**给足了原因**

```
No engine could convert image file …: pytesseract+tesseract:
  Image OCR requires Tesseract-OCR (system) and pytesseract (Python). Install both to OCR
```

**缺的是可选引擎**（Tesseract + pytesseract），错误里**点名要装什么**。
这与包内"重型或旧格式引擎作为可选"一致 —— **不是缺陷，是未安装的可选依赖**。

## 4. 这一轮的真正价值

- **三条真实回执**，每条的**原件 sha256 都可核对**（成功两条与源文件哈希一致 ✓）；
- **区分了"通过 / 保管 / 缺引擎"三种状态**，而不是笼统说"支持若干格式"；
- **产品自述缺口**（canvas 的 custody only）比自己推断更可信；
- **没有把 passthrough 说成支持** —— 这正是包内最强调的那条纪律。

## 5. 本轮**未**做

1. **未**做"准确定位/损失回执/冷启动/导出"这些 Q06 要求的其余维度（本轮只做了**摄入**这一环）；
2. **未**安装 Tesseract/pytesseract（包内不鼓励为凑数装引擎；且是否安装应作为裁决项）；
3. **未**改任何实现文件；
4. 官方 Green 与官方资料库**零触碰**；临时库用完即留在 `.project-local/runs/format-intake`（忽略区）。

## 6. 下一轮

把本次手工结果**固化成探针 + 测试**（与握手那条同样的做法），断言三种状态各自的**判据**：
- md → 断言 engine 是 passthrough（**并明确断言它不是结构提取**，防止以后被误报为支持）；
- canvas → 断言内容里出现 custody-only 自述；
- png → 断言失败原因点名缺失引擎。

**这样"未通过"也会被门禁记住，而不是随时间被说成通过。**
