# 27B MTP 超时只读诊断

状态：**PARTIAL；实际推理迟缓根因 UNVERIFIED；没有证据足以提出性能产品修复。** 本轮仅查源码、已脱敏项目证据、硬件元数据和两个 loopback GET。未推理、加载/卸载、改配置或读取模型权重、认证、私人日志/数据库。

## 可证结论

- 加速方案已部署到当前加载实例：冻结 load 回执与本轮库存都回读 `aaos-deep-27b-mtp`、context 2048、parallel 1、flash attention=true、MTP=true、KV 不在 GPU；load 回执还确认 gpu.ratio=0.4、draft 2/1。历史同机短合成试验曾记录 MTP accepted/rejected counters，支持曾实际使用；不证明本次失败请求的 MTP 命中率或加速效果。
- 两个 GET 返回 HTTP 200，服务及模型库存可读。最新 retest 在 `model_request` 118.03 秒触发超时；Core 120 秒包含前置开销，worker 剩余预算 118 秒合理。**服务可读≠推理成功，超时≠停服或未装载。** 本次仍 FAIL，answer 未发布、usage=null、provider stop UNKNOWN。
- RTX 5060 总显存 8151 MiB，注册模型文件 14,252,845,984 字节，profile 明确部分 offload。无法将整个模型文件及运行开销都放入这块显存；这支持资源约束存在，不证明 timeout 由 CPU/PCIe/显存导致。CPU i5-14600KF、物理内存约 63.8 GiB。瞬时 GPU 剩余 560 MiB/利用率 2% 是超时之后的总设备快照，不能解释失败时的资源状态；0.4 是加载参数，不是实测利用率。
- 本轮合成 retest 可重建为 context 252 UTF-8 bytes、question 65 bytes、worker prompt 642 bytes。不是大段文本；实际 tokenizer/chat-template token 数和失败请求线传字节未采集，不能据字符数宣称 ctx 一定足够，亦没有证据证明 context overflow。库存的模型最大 ctx 262144 不等于实际加载 ctx 2048。
- worker `_call()` 显式发送 model/max_tokens/messages；没有显式 temperature、seed、stop、reasoning 或 context-overflow 策略。库存报告 reasoning 默认 on；是否本次实际生成、消耗多少思考 token 未知。150-word prompt 约束不限制隐藏思考。max_tokens 1024 与 ctx 2048 是不同预算，不能相加后凭字节猜是否适配。历史 SDK 短烟测固定 temperature=0/seed=42/stopAtLimit，不能当同参数应用负载结论。
- 同一已归档应用路径曾完成 74.95 秒/237 output token 的 original answer；上一轮材料 79.97 秒/240、companion 107.7 秒/291 也曾结束。只证明部分调用可完成，不能据此认证稳定性、质量或本轮 retest。历史 MTP 短试验 TPS 约提升 12%–16%，样本小且 grounding 输出 token 数不同，不能外推任意任务必定在 120 秒内结束。

## 精确诊断缺口与下一最小任务

`worker.answer()` 在 `_call()` 整体返回前都记 `model_request`；该阶段覆盖 HTTP 建连/排队/prefill/decode/收头/正文 read/JSON parse。现有 TimeoutError 元数据无法区分这些阶段；非流式请求失败也没有 TTFT、已生成 token、reasoning、finish reason 或 MTP 命中数据。**没有可证的具体性能根因，也不据 client_request_id 的 null 字段推断关联丢失。**

下一任务仅需一个明确授权、固定相同模型/profile/预算与自建合成输入的测量切片：先补有限的请求长度与阶段计时，不保存正文；如精确服务版本提供正式统计接口，再采集同次调用的 prompt/output/reasoning tokens、TTFT、stop 与 MTP counters。有限字段须同步 Python/Rust sanitizer、合同及显示映射，负例拒绝任意 prompt/JSON/路径泄露，历史回执不重写。只在证据分出 queue/prefill/decode/read 后考虑对应优化。该诊断改进本身不承诺解决超时。

本轮不建议抬高 timeout/token/context、换模型、关闭思考、改 stop、变更 GPU/KV/MTP 参数来获得 PASS。此类高资源/profile 改动须作为单独受权对照实验，先明确共享服务影响、同条件指标和回退；现任务不授予更改权限。

## 证据与范围

EVIDENCE.json 保存有限元数据与重建长度；LIVE-INVENTORY.json 保存本轮 GET 白名单读回与响应哈希；SOURCE-MANIFEST.json 绑定实际读取来源。未新增或运行测试、未启动进程服务，产品零写。本轮只是诊断，不提升 native/REAL/Owner 资格。

官方协议核对：[模型库存与 loaded config](https://lmstudio.ai/docs/developer/rest/list)区分模型上限与已加载配置；[Chat Completions](https://lmstudio.ai/docs/developer/openai-compat/chat-completions)说明模板/推理参数；[推测解码](https://lmstudio.ai/docs/app/advanced/speculative-decoding)说明通用 draft 速度依赖接受率。后者不是当前内置 MTP 实现的独立认证。
