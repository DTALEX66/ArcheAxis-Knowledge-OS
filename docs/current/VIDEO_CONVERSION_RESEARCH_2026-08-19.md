# 视频转化开源方案调研（2026-08-19）

> 背景：ceshi 测试库有 64 个 mp4 课程视频。已有：抽帧+RapidOCR 画面文字（已实证，课程画面含"进步本"学习法/黑石案例/复合增长计算等知识）；音轨 ASR 引擎就绪（SenseVoice 快 / faster-whisper 兜底，F1 暂停中）。自有开源清单（04/13/D5）**无视频专项**——本调研补齐该缺口。

## 1. 候选开源项目（web_search 核实）

| 项目 | URL | 许可/维护 | 能力 | 适配判定 |
| --- | --- | --- | --- | --- |
| **PySceneDetect** | github.com/breakthrough/pyscenedetect | BSD-3/活跃 | OpenCV 场景切分（cut/fade）+ 每场景关键帧 | **直接集成**（轻量、纯本地）→ 视频结构化核心 |
| **WhisperX** | github.com/m-bain/whisperX | BSD-3 | 词级时间戳 + 强制对齐 + 说话人分离 → 高质量字幕 | **借鉴架构**（对齐思想；引擎用已就绪的 SenseVoice/faster-whisper） |
| **VideoContext-Engine** | github.com/dolphin-creator/VideoContext-Engine | 本地视频 RAG：场景检测+Whisper ASR+Qwen3-VL，FastAPI，Win/Linux | **参考架构**（我们管线形状同源，自研不引） |
| **video-to-txt** | github.com/lzA6/video-to-txt | 中文、Ollama+OpenAI 双引擎、关键帧+Whisper+摘要 WebUI | **参考架构**（中文体验/WebUI 参考） |
| **VideoRAC** | pypi.org/project/VideoRAC | 视频 RAG 分块 + QA 生成 | **借鉴算法**（时间戳分块与 QA 思路） |
| **Qwen2.5-VL**（已有 qwen2.5vl:7b） | ollama 本地 | 帧/短视频理解、视觉问答 | **直接使用**（画面语义层：帧描述/板书总结） |
| **stable-ts** | github.com/jianfch/stable-ts | 稳定时间戳字幕 | 可选（字幕细化） |

## 2. 推荐视频转化管线（本地全链）

```text
mp4 → ffmpeg 预处理（音轨 16k wav + 抽帧）
  ├─ PySceneDetect 场景切分 → 每场景关键帧（结构化单元）
  │     ├─ RapidOCR 画面文字（实证：进步本/黑石案例/复合增长计算）
  │     └─ Qwen2.5-VL 帧描述（可选语义层：板书/图表总结）
  ├─ SenseVoice/faster-whisper 音轨字幕 → 词级时间戳对齐（WhisperX 思路）
  └─ 合成：{场景, 时间戳[起-止], 画面文字, 字幕, 帧描述} → 知识块 → 入库（证据锚定）
```

- 价值：课程视频的知识在**画面（PPT/板书/案例数字）** + **语音（讲解）** 两轨；画面已实证，语音轨 = F1 待恢复
- 时间戳对齐使知识块可定位（证据驱动）

## 3. 落地优先级

| # | 动作 | 复杂度 | 依赖 |
| --- | --- | --- | --- |
| V1 | PySceneDetect 接入（场景→关键帧） | 小 | pip install scenedetect（本地） |
| V2 | 全量视频抽帧 OCR（已有脚本 _video_full.py，暂停中） | 中 | RapidOCR（已装） |
| V3 | F1 音轨转写恢复（SenseVoice）→ 字幕 SRT 导出 | 中 | 引擎已就绪 |
| V4 | Qwen2.5-VL 帧描述（关键画面语义） | 中 | ollama qwen2.5vl（已装） |
| V5 | 时间戳对齐知识块 + 证据锚定入库 | 中 | temporal_graph/evidence |

## 4. 与本仓已有能力的衔接
- 画面文字 → content_cleaner 去噪 → ocr_gate 质量门 → knowledge（证据锚定）
- 字幕/描述 → 知识块 → temporal_graph.ingest_episode（会话批量摄入）
- 学习侧 → 转 quiz/teach-back/学习路径（现有学习引擎直接消费）

## 5. 结论
视频**可以且应该**转化：主链路 = 场景切分（PySceneDetect）→ 画面 OCR（RapidOCR，已实证）+ 音轨字幕（SenseVoice，已就绪）+ 可选 VLM 帧描述（Qwen2.5-VL）→ 时间戳对齐知识块入库。执行待用户指示（当前暂停）。
