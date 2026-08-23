# 管线后续任务记录（全链路 · 多格式管线测试）· 2026-08-19

> 状态：全部**已记录、可开跑、当前不跑**（用户指示）；脚本固化在 scripts/pipeline/。
> 目标：一条全链路多格式管线（文件 → 转化 → 去噪 → 质量门 → 知识 → 学习），各格式随时可测。

## 1. 多格式覆盖状态（ceshi 实测基线）

| 格式 | 引擎 | 状态 | 开跑命令 |
| --- | --- | --- | --- |
| 文本 md/txt/csv/json/canvas/ajson | passthrough | ✅ 已跑（20804） | scripts/pipeline/pipeline_sweep.py（归档副本） |
| PDF | pymupdf → OCR 兜底 | ✅ 66/66 | 同上 |
| Office docx/pptx/xlsx | adapter/markitdown | ✅ 24+4 | 同上 |
| 图片 png/jpg/webp/gif | RapidOCR | ✅ 1273（8 超大失败） | 同上 |
| 旧版 .doc | 需 LibreOffice/antiword | ⏸ F2 | 装转换器后 |
| 音频 mp3/m4a | SenseVoice → faster-whisper（<5min 兜底） | 🔄 F1 执行中 | **scripts/pipeline/pipeline_audio.py** |
| 视频 mp4 画面 | 抽帧 + RapidOCR | ✅ F8 完成 64/64 | **scripts/pipeline/pipeline_video.py** |
| 视频增强 | PySceneDetect + Qwen2.5-VL + 字幕 | 🟡 F9：V1 场景切分 ✅ V2=帧OCR ✅ V3 SRT ✅ / V4 VLM BLOCKED(ollama 500) | V1-V5（见视频调研文档） |
| Web URL | raw-first 捕获 + 提取链 | ✅ web.py 实现 | C2 后续 |

## 2. 全链路多格式测试计划（恢复顺序）

1. **F1 音频全量转写**：pipeline_audio.py（SenseVoice 已验证 26x 快）→ 回执入 .hermes/task-runtime/
2. **F8 视频画面转化**：pipeline_video.py（抽帧 OCR 已实证）→ 视频画面知识
3. **F9 视频增强**：V1 PySceneDetect → V2 全量抽帧 → V3 音轨字幕 SRT → V4 Qwen2.5-VL 帧描述 → V5 时间戳知识块入库
4. **F2 旧 .doc**：装 LibreOffice/antiword 到共用库工具链 → 转 2 个遗留文件
5. **F3 超大图**：PIL 上限调高或跳过（8 张）→ 补扫
6. **格式质量 bake-off 收尾**：固定改写查询 + CER/WER/资源矩阵（包 C 遗留）
7. **Web 捕获全量**：C2 TaskPack 余下 DAG（PolicyGate 统一/真实 E2E）

## 3. 开跑前置（已就绪清单）
- ✅ SenseVoice int8（Model library）+ sherpa-onnx 1.13.6 → F1
- ✅ RapidOCR（venv 已装）+ tesseract（TESSDATA 已修）→ F8/图片
- ✅ ffmpeg（共用库工具链）→ 提音轨/抽帧
- ✅ ollama qwen2.5vl:7b / qwen3-embedding → F9/QA
- ✅ 脚本固化 scripts/pipeline/（README 含命令）
- ⏳ PySceneDetect 未装（V1 时 pip install scenedetect）

## 4. 统一出口
- 每轮跑完 → 回执 JSON（.hermes/task-runtime/）→ 归档副本入 verified-knowledge/ceshi-2026-08-18/receipts/ → 报告更新
- 内容一律过：content_cleaner（去噪）→ ocr_gate（质量门）→ 知识入库（证据锚定）
