# 音视频默认能力：包内解码器 + 包内转写模型（2026-10-25）

## 变更方向

安装后的产品不再依赖“开发机上有 ffmpeg / 共享 Model library”才能处理 mp4、mp3。
本次把两条能力放进 app-local runtime，并让 worker 优先发现它们：

| 能力 | 落地位置 | 许可 |
| --- | --- | --- |
| 解码（demux + 音频/视频解码） | runtime 自带 PyAV 18.0.0 与其 FFmpeg 8.1.2 共享库 | PyAV BSD-3-Clause；FFmpeg 库 LGPL-2.1-or-later |
| 转写（分段 + 时间戳） | runtime/models/asr/faster-whisper-base（Systran base 权重，~139MB） | 代码 MIT；权重按上游 model card（MIT），不由本仓库再许可 |

## 为什么不是“打包 ffmpeg.exe”

本机唯一可用的 ffmpeg 构建是 gyan full_build（GPLv3，695MB），不能随应用分发；
离线环境也没有 BtbN LGPL 构建可供复制。PyAV 已在 runtime（faster-whisper 的依赖），
自带 LGPL FFmpeg 库，因此先以它作为默认解码器。未来引入 LGPL ffmpeg/ffprobe 只需
声明为 app-local 资源，worker 契约已经“声明二进制优先于内置解码器”，无需二次改动。

## 可验证事实（本机实测）

- 真实合成 mp3（由项目内 golden WAV 转码）与 golden MP4：解码→16kHz 单声道 WAV→
  faster-whisper base 转写得到 `Learning evidence anchor.`，段落 0–2000 ms，
  `model_source: bundled`。
- MP4 在 PATH 无 ffmpeg 时由 PyAV 解码：3 帧带容器 PTS（0/1000/2000 ms），
  `decoder: pyav`，`decode_errors` 为空。
- `stage_backend_runtime.py --asr-model` 生成的后端候选清单含 `asr-model` 组件与
  逐文件 SHA-256，候选内 worker `--probe` 报告 `model_source: bundled`。

## 仍未补齐

- sherpa-onnx + SenseVoice int8 + silero VAD（说话人分离与 SenseVoice 时间锚点）不在本轮：
  本机无 silero VAD 资产，且 SenseVoice 无词/段级时间戳，缺 VAD 时只能给整段文本。
  `worker_diarize.py` 继续按名报告缺失资产。
- CI 构建机没有声明模型供体，因此 CI 生成的候选仍会记录 `asr_model: MISSING`；
  正式发布通道需要先给打包机一个固定模型供体（或另行批准的内置资产来源）。
