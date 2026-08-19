# 管线可开跑脚本（scripts/pipeline/）

> 保证后续"随时能开跑"；全部本地模型（共用库：模型 Model library / 工具 OS External Configuration）。

| 脚本 | 任务 | 命令 |
| --- | --- | --- |
| pipeline_audio.py | F1 音频全量转写（SenseVoice 快引擎 → faster-whisper 兜底） | env -u PYTHONPATH .venv\Scripts\python.exe scripts/pipeline/pipeline_audio.py |
| pipeline_video.py | F8 视频画面转化（64 mp4 抽帧 + RapidOCR） | 同上（pipeline_video.py） |
| （归档副本）ceshi_sweep.py | 全库文本/PDF/docx 扫描（含噪声过滤） | verified-knowledge/ceshi-2026-08-18/scripts/ceshi_sweep.py |
| （归档副本）qa_local_verify.py | qwen3 检索对比 + 本地 LLM 接地问答 | verified-knowledge/ceshi-2026-08-18/scripts/qa_local_verify.py |

- 输出回执一律写 .hermes/task-runtime/*.json（证据，不入 Git）
- 引擎依赖：ollama（qwen3-embedding / qwen2.5vl）/ sherpa-onnx+SenseVoice（Model library）/ rapidocr / ffmpeg
