# 本地 LLM 当前入口 · 2026-10-18

默认服务为 **LM Studio**，产品 OpenAI 兼容地址 `http://127.0.0.1:1234/v1`。
当前实测引擎是 `llama.cpp-win-x86_64-nvidia-cuda12-avx2@2.60.0`，
识别 RTX 5060 8GB、i5-14600KF、约 64GB RAM。这里的 LLM 是语言模型；
在已核的项目配置、脚本、当前记录及模型库登记内没有 vLLM 部署证据。
不将 vLLM、Ollama、LM Studio 和 LM Studio 内部 llama.cpp 混写成同一运行时。

27B 权重确实存在，LM Studio 当前实例读回绑定其模型库路径。
原 MTP 方案曾经完成临时实测，但没有形成受版本管理的加载入口，测试后实例被卸载；
因此后续只查询下载库存，不能知道历史参数有没有在新加载中生效。
10/13 历史结果保留于 [MTP 配对收据](../history/repository-consolidation-20261019/current/receipts/AAOS-27B-MATCHED-MTP-20261013.json)。

本轮已将参数写入 [`config/model-profiles/lm-studio.json`](../../config/model-profiles/lm-studio.json)，
由 [`scripts/runtime/lm_studio_profile.mjs`](../../scripts/runtime/lm_studio_profile.mjs) 显式加载和读回。
`deep-mtp` 为 27B、40% GPU 卸载、严格显存上限、2048 context、单并发、Flash Attention、
CPU KV cache、MTP 草稿 1–2 token。它是现有机器的有界配置，不能无限吞入完整长文档。

```powershell
node scripts/runtime/lm_studio_profile.mjs inspect
node scripts/runtime/lm_studio_profile.mjs load deep-mtp
node scripts/runtime/lm_studio_profile.mjs smoke deep-mtp
```

本轮工具依赖固定为官方 `@lmstudio/sdk@2.0.0`，已安装在忽略目录
`.project-local/tools/lm-studio-sdk/`，保留本地 lockfile；不增加前端依赖。
官方 npm integrity 登记于 profile。恢复工具环境时使用官方 registry、项目缓存与 `--ignore-scripts`，
不全局安装、不修改 PATH、provider/auth/endpoint 或 LM Studio per-model defaults。
默认模型和已有模型用途配置保持其原值；深度任务显式选择加载实例 `aaos-deep-27b-mtp`。

加载入口发现另一 LLM 已驻留会拒绝替换；相同标识绑定不同模型、不同有效参数也拒绝。
不会静默卸载别的软件所用模型。成功实例空闲 1800 秒自动释放；不是开机服务或后台常驻承诺。
重新运行加载入口可恢复。回退为等待实例 TTL 释放并撤下项目配置；不删除权重、既有模型配置或用户数据。

本轮实际结果见 [当前运行回执](../history/repository-consolidation-20261019/current/receipts/AAOS-LOCAL-LLM-20261018.json)：
SDK 合成短测完成、MTP 26 accepted / 6 rejected，约 4.77 token/s；
当前正式 Python worker 使用同一实例完成回答，30.07 秒、73 output tokens、stop、未截断、最终来源 content。
这些是 **REAL 本地合成材料**，不是完整 Core/宿主/安装版学习旅程、稳定速度或独立准确性结论。

随后再次现场读取 `/api/v1/models`：27B 实例 `aaos-deep-27b-mtp` 仍驻留，
MTP、Flash Attention 和 2048 context 有效；4B 在库存中但未驻留。只读快照位于
`.project-local/runs/be268a2d33/continuation-runtime-investigation/live-model-readback-1756.json`，
驻留及剩余 TTL 只对该快照时间成立。`/v1/models` 包含未加载库存，不能单凭它判断驻留。
当前 worker 无显式选择时默认 `qwen3.5-4b`；27B 加载成功不等于产品保存的所有用途绑定已改成27B。
产品用途绑定仍需通过正式 Core 配置接口独立读回；`config/models.yaml` 的占位值也不构成该读回证据。
源码核对：正式配置保存在当前 workspace 的 SQLite `workspace_meta`，键
`product_model_configuration_v1`。无保存记录时返回 revision 0、空 profiles/bindings，
不会从 LM Studio 下载库存自动生成绑定。首次保存后，缺失用途绑定会阻断请求。
回答、复测、材料问答和小栖会话均已接入 FAST/DEEP 选择；预览时解析一次并冻结用途、通道、配置版本和目的地。
revision 0 仅保留 FAST 兼容执行；未配置的 DEEP 阻止执行，不静默使用默认 4B。
设置中的“补齐 LM Studio FAST/DEEP 配置”读取本地目录后只补缺失草稿，覆盖上述四用途的八项绑定；
已有配置、绑定与 embedding 不变，仍须显式保存并通过 Core CAS 校验。
27B 服务实例 ID 必须在 OpenAI 兼容目录中存在，原始权重库存名称不能替代 MTP 实例 ID。
保存配置不加载模型；正式用户 workspace 的实际已保存绑定仍 UNVERIFIED。
本轮候选原生配置保存与冷重开已通过合成配置验证，并非正式 workspace 绑定或真实模型闭环验收。
具体源码绑定、测试与失败保留见[用途通道与候选更新回执](../history/repository-consolidation-20261019/current/receipts/AAOS-MODEL-LANES-20261018.json)。
表单中的 document_check/embedding 枚举不代表相应执行链已全部接通；不能把库存或加载状态写成六用途验收。

官方加载与推测解码说明：[lms load](https://lmstudio.ai/docs/cli/local-models/load)、
[Speculative Decoding](https://lmstudio.ai/docs/app/advanced/speculative-decoding)。
通用说明不替代本机有效参数和非零接受 token 的实际观测。
