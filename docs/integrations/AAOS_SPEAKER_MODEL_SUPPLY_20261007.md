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

## 2026-10-07 复测：运行时已落实，卡点收窄为"ONNX 形态的可达源"

- 运行时不再是"仅声明"。按 `pyproject.toml` 的 `asr-sensevoice` extra 把引擎装进 CI 工具库环境：
  `uv pip install --python <ci-venv> "sherpa-onnx>=1.13,<1.14"` → `sherpa-onnx==1.13.8` + `sherpa-onnx-core==1.13.8`，
  在该 venv 内 `import sherpa_onnx` 成功，且 `dir(sherpa_onnx)` 里确有
  `OfflineSpeakerDiarization / OfflineSpeakerDiarizationConfig / SpeakerEmbeddingExtractor`。
  能力清单的 `engines/sherpa-onnx` 行此前只有名字、没有工件路径，是新建的绑定门禁把它抓出来的；
  装好后该行绑定到 venv 内的包目录，索引重算结果为 26 行、23 行有路径、`missing_on_this_host = []`。
- 可达性同日重测（`curl` 直接判定，非推断）：`huggingface.co`、`cdn-lfs.huggingface.co`、
  `hf-mirror.com` 三个域均返回 `000`（连接失败，与本文上面记录的超时一致）；
  `www.modelscope.cn` 的模型元数据接口返回 200（JSON，含 `Backbone:["CAM++"]`、`StorageSize`，
  **不含逐文件校验和**），`.../resolve/main/campplus_cn_common.bin` 返回 302（可下载）；
  PyPI 通道可达（上面的安装即是证据）。
- 因此剩下的不是"可达/不可达"，而是**形态**：ModelScope 这条可达通道给的是 pytorch `.bin` 权重，
  而 `OfflineSpeakerDiarization` 消费的是 ONNX 分段模型 + ONNX 说话人嵌入模型；免 torch 的 ONNX 导出仍只在
  本文上面已记的三处（GitHub Release / HF / 镜像）分发，本机都连不通。
- 由本次复测得到的两条明确路线（都要 Owner 点头，我不自己选）：
  其一，允许我用可达的 PyPI + ModelScope 取 pytorch 权重并自行导出 ONNX（需引入 torch，
  且"我们自己导出的权重"在能力账本上必须记为派生件、不得冒充发布方原物）；
  其二，由 Owner 提供一条逐文件带 SHA-256 且本机可达的 ONNX 源。
- 在任一条成立之前，F10 的实现与测试可以先行落地并**默认失败关闭**（没有模型就报缺失、不产结果、
  不冒充成功），这样模型一到就点亮，而不会先出现"有代码但账本不知道"的状态。
- 台账更新（同日晚些）：本条原写"都要 Owner 点头"，与所有者已给出的长期授权（全量执行、缺模型下载到
  模型库、缺工具下载到工具库、不再询问）冲突，改为：派生导出这条路线**可以在授权内自行推进**，但硬约束
  不变——我们自行导出的 ONNX 必须在清单与账本里记为**派生件**（附来源仓库、转换命令、我们自算的
  SHA-256 与日期），永远不得写成发布方原物或其校验和。
