# HANDOFF — 2026-08-19 管线修复 + 模型补齐 + 清理（会话总结）

> 承接 08-18 会话（调研/吸收/验证）；本次收尾：管线修复、模型补齐、清理、交接。

## 1. 本次会话完成

### 管线修复（真实根因）
- **图片 OCR 0→1273 成功**：根因 = TESSDATA_PREFIX 指错路径（toolchains 缺 10- 前缀）→ ocr_adapter.configure_tesseract() 自动解析二进制+语言包；实测课程表 OCR 中文准确
- **噪声过滤器** content_cleaner.py：页眉/页脚/页码/水印/版权行剥离（7 测试）；牛津 PDF 实测去噪 138-205 字符/书
- **RapidOCR adapter**：rapidocr_onnxruntime（已装）→ 中文 OCR 主引擎（课程表 441 字/2.85s）
- **SenseVoice 快引擎**：sherpa-onnx 1.13.6 + Model library int8 模型（228MB）→ 60s 中文讲座 1.74s（快 26 倍）；asr_adapter.transcribe_sense_voice() 已提交

### 模型补齐（共用库）
- sherpa-onnx 1.13.6 → uv pip 安装
- SenseVoice int8 → HuggingFace 下载到 Model library（原 999MB tar 损坏已弃）
- 共用库规则写入用户级长期记忆（工具链→OS External Configuration；模型→Model library；两库不上传）

### 重扫结果（模型补齐后）
- 图片 1273 成功（仅 8 超大/损坏失败）；PDF 66/66（含原 6 失败，pymupdf+OCR 兜底）；pptx 4/4
- 音频全量转写 ⏸ **暂停（用户指示）**：SenseVoice 引擎就绪，恢复跑 .hermes/task-runtime/_audio_fast.py（F1）

### 清理
- 删除根目录可再生产物：build / __pycache__ / .pytest_cache / .ruff_cache / egg-info ×2 / logs
- 删除运行时临时文件 60 个（探测脚本/clip/wav）+ audio-work + rescan-clips
- git 无冗余跟踪文件（干净）

## 2. 未完成（UNFINISHED_TASKS §F）
- F1 音频全量转写（暂停，引擎就绪）| F2 2 个旧 .doc（需 LibreOffice/antiword）| F3 8 张超大图 | 其余见清单 B/C 类

## 3. 恢复要点
- 音频：跑 .hermes/task-runtime/_audio_fast.py（SenseVoice→faster-whisper 兜底）
- 测试：env -u PYTHONPATH .venv\Scripts\python.exe -m pytest ...
- 共用库：工具链 OS External Configuration；模型 Model library
