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
   **未装** `torch`、`torchaudio`、`pyannote.audio`、`speechbrain`、`scikit-learn`、`scipy`、
   `soundfile`、`librosa`。
6. 一处**我自己的误判已更正**：先前把 `sherpa-onnx` 记成"已声明但未安装"的治理缺陷。读声明本体后不成立：
   `config/environment/capability-requirements.yaml:291-300` 写的是 `install_method: uv`，健康检查是
   `uv run --extra asr-sensevoice python -c "import sherpa_onnx"`，即它本来就该在项目隔离环境里按需解析，
   而不是躺在 CI venv 中。判一个引擎是否"绑定"要按声明自身的安装方式来核，不能拿另一个 venv 的清单当尺子。
7. 镜像主机也不能供货（实测）：`hf-mirror.com` 的**搜索**接口一次返回了 7 个 CAM++ ONNX 候选仓库名，
   但紧接着逐文件树接口一次超时、三次 `WinError 10060` 连接失败，文件 `resolve` 路径因此无从验证。
   搜索答过一次而文件服务不通，与"完全没有这个源"是两件事；本机的代理环境确实存在（宿主收据
   `conditions.proxy_environment_present: true`），所以这类主机的表现是间歇性的。
   规则不变：**拿不到发布方自己的逐文件校验和，就不下载**。
   候选仓库名（未采信，仅供后续若网络策略改变时复核）：`welcomyou/campplus-3dspeaker-200k-onnx`、
   `bitsydarel/campplus-onnx`、`Alkd/campplus-zh-cn-common-200k-onnx`、
   `Serkan007/Speaker-Diarization-ONNX-sherpa`、`Serkan007/Speaker-ID-ONNX-sherpa`。

## 结论与下一步的前置条件

F10（说话人分离）当前唯一的真实卡点是**一个能给出逐文件校验和且本机可达的 ONNX 源**：

- 运行时不是卡点。`sherpa-onnx` 已按 `uv` extra 声明（见上第 6 条），`onnxruntime` 也已在 CI venv 内；
  目标里"缺工具下载到工具库"这一条在这台机器上有可用通道。
- 模型是卡点。可达且带校验和的发布源只给出需要 torch 的权重；免 torch 的 ONNX 导出分别在
  GitHub Release（不可达）、`huggingface.co`（超时）与 `hf-mirror.com`（搜索答过一次，文件与树接口
  连接失败）三处，均无法在下载前核验。

因此要继续 F10，需要下列之一：允许我在网络策略上把镜像主机的 `resolve` 路径当作可用源重试（并只在
拿到发布方 SHA-256 时才落盘）；或由 Owner 提供一条可达、逐文件发布校验和的 ONNX 源。二者都不具备时，
F10 在格式矩阵里保持 `PARTIAL`，`gap` 文本"仍无说话人分离"是对的，不改。
