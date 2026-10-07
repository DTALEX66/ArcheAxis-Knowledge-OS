# 说话人分离（F10）外部供给探测记录 — 2026-10-07

本文件登记**外部发布方**给出的固定标识，不是本仓库的 Git 对象。这些值形状上是 40 位十六进制，
会被 `tests/test_axr060_completion_audit.py` 的"当前权威面只引用真实对象"检查误判，因此按既有先例
（`docs/integrations/DEEPTUTOR_PRODUCT_BASE.md`、`*_PRODUCT_BASE.md` 一族）放在 `docs/integrations/`，
`docs/current/` 的台账只引用本文件，不内联这些标识。

## 已核实的发布方事实（ModelScope 逐文件 API，未下载任何文件）

发布方按文件给出 `Size`、`Revision`、`Sha256`、`IsLFS`，满足本机"固定文件且发布方自带校验和"的前置条件。

- 仓库：`iic/speech_campplus_sv_zh-cn_16k-common`（模型卡许可证 Apache-2.0）
  - `campplus_cn_common.bin` — 28,036,335 字节，SHA-256 `3388cf5fd3493c9ac9c69851d8e7a8badcfb4f3dc631020c4961371646d5ada8`，
    发布方 Revision `013c18884dffb82846cf472dd06dd4a08d97e2cd`（ModelScope 的提交标识，不是 Git 对象）
  - `config.yaml` — 537 字节，SHA-256 `17342041bd5b22f6fd7e32f6e7a267b0bf65f018c0a721bada6547e3d28fbfc9`
  - `requirements.txt` — 19 字节，SHA-256 `c6d1bd9fd0c46b2cd29a6dab9859d99355e8c621dd726d4cde5c1d650c8faca0`
  - 该仓库只有 PyTorch 权重，**没有 ONNX 导出**（逐文件枚举结果就这三项与目录项）。

## 同日实测的供给阻塞（全部为测量，不是推测）

1. ModelScope 的搜索接口 `GET https://www.modelscope.cn/api/v1/dolphin/models?Query=…` 对
   `campplus onnx`、`3dspeaker campplus`、`speaker diarization onnx`、`sherpa-onnx speaker`
   四个查询**一律返回 HTTP 404**；同一主机的逐文件接口 `…/repo/files?Revision=master&Recursive=true`
   正常返回，所以能用的是"已知仓库名取清单"，不能是"按关键词找仓库"。
2. `huggingface.co` 在本机**连接不返回**：整段探测在 120 秒超时被杀（`REAL_EXIT=124`），四个检索请求
   没有任何一个完成。
3. GitHub Release 资源主机本机不可达（2026-10-07 早先实测：`curl -L` 得 `http=000`，
   `urllib` 得 `RemoteDisconnected`）；sherpa-onnx 的 CAM++ ONNX 导出正是发布在该处。
4. 磁盘上不存在任何说话人嵌入模型：`D:\All projects\Model library` 全树检索
   `campplus|3dspeaker|eres2net|sv_zh|speaker|diar` 零命中；`sherpa-onnx\` 下只有两个 **ASR** 模型
   （SenseVoice、streaming-zipformer），`40-models`、`60-cache` 同样零命中。
5. 运行侧：CI venv 已装 `onnxruntime 1.20.1`、`faster_whisper 1.2.1`、`ctranslate2 4.8.1`、`numpy`；
   **未装** `torch`、`torchaudio`、`sherpa-onnx`、`pyannote.audio`、`speechbrain`、`scikit-learn`、`scipy`、
   `soundfile`、`librosa`。而 `sherpa-onnx` 已在 `config/environment/capability-requirements.yaml`
   作为引擎声明并配了模型条目——即"声明了但未安装"这一条本身也是待办的对账项。

## 结论与下一步的前置条件

F10（说话人分离）当前的真实卡点是**供给路径**，不是意愿：可用的发布方式只剩"已知仓库名 + 逐文件校验和"
这一条，而它给出的是需要 torch 的权重；能免 torch 的 ONNX 导出恰好落在本机不可达的两个主机上。

因此要继续 F10，需要下列之一（都需要 Owner 或网络侧决策，不能由我单方越过）：

- 允许把 `sherpa-onnx`（PyPI 可达，`uv` 已验证可解析）装进**项目自有**的 venv，并由我按其文档指定的
  镜像取 ONNX 嵌入模型；或
- 提供一条可达的、逐文件发布校验和的 ONNX 下载源；或
- 接受 torch 权重路线（体量与维护成本明显更高）。

在这之前，F10 在格式矩阵里保持 `PARTIAL`，`gap` 文本"仍无说话人分离"是对的，不改。
