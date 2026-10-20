# 有限请求测量：交付与接续

本候选只补失败路径的证据分辨率；不是推理速度修复。原request_stage枚举、elapsed_s、reason code、Core120秒及worker剩余预算语义均保留。模型/provider/endpoint/load/profile/输出预算/请求内容/序列化不变，没有自动重试。

新增可选有限字段：

| 字段 | 实测含义 | 不能推出 |
|---|---|---|
| request_phase=http_open | urllib.open等待响应头或抛错所在阶段 | 不是TTFT；connect/服务排队/prefill/非流式生成各自仍未知 |
| request_phase=body_read | 原有MAX+1有界read，含失败等待 | 不等于模型正在生成；失败read不填造response_bytes |
| request_phase=json_parse | UTF-8解码、JSON对象解析与根对象形状检查 | 不是provider inference或tokenizer计时 |
| request_phase=response_validation | JSON已返回，完成原协议字段/最终answer判定 | 没有新增该段时长或改验收 |
| http_open_elapsed_s/body_read_elapsed_s/json_parse_elapsed_s | monotonic测量相应已到达阶段；异常finally也记录该段实际耗时 | 没到达的字段缺失，不写0；round4可能将极短实测显示0 |
| prompt_utf8_bytes | 实际构造prompt的UTF-8字节数 | 不是token/context使用量 |
| serialized_request_bytes | 原json.dumps(body).encode实际出站正文长度 | 不含HTTP headers；没有URL/headers/body字节或hash外泄 |
| response_bytes | 已返回有界read的实际字节数，超限时最多MAX+1 | 不报未知的partial bytes；不是完整网络包大小 |

有限白名单同步：Python failure_diagnostics、Rust MachineFailure sanitize、OpenAPI与material/conversation两schema、两生成TS、UI readMachineFailureDiagnostics。新增字段均optional，旧receipt仍可读，不生成新权限。原NO_FINAL_ANSWER/EMPTY/late-response也携带已观测元数据；reasoning正文永不输出。错误类型/timeout判定仍按原异常，不根据字符串猜；不从读超时宣称server停止、worker已启动或cancel成功。

成功请求说明：ModelReply内部暂存测量，仅供后续失败/迟到/无final路径；成功answer/extract未暴露公共measurements，不改成功合同和历史序列化。provider TTFT/token/reasoning/MTP counters及成功测量仍NEXT/UNVERIFIED。

隔离验证：仅复制10份变更preimage、4份必要Python测试/生成依赖，以及11候选到必要验证镜像。没有整源码树、环境、权重或业务DB复制。UI只对有限sanitizer及两个自包含生成DTO做TS slice；Rust编译真实machine_failure.rs精确模块与root Cargo.lock所选serde_json，不等于整个application/API编译。复用已有前端node_modules只读junction，无安装/依赖升级。Cargo canonical runner会使用项目声明的ignored构建缓存，未修改共享工具配置。

原始13项RED与142项GREEN验证actual_call→read_model_json→answer→failure_receipt，覆盖open直接/URLError timeout、read timeout、JSON失败、响应字段失败、no-final、超大响应、精确序列化/UTF8长度、零值/类型/安全整数边界、有限时长、隐私字段拒绝、成功形状不变。Rust6含旧deadline/新sanitizer；UI3含非法值与旧阶段兼容；合同拒绝额外字段/TTFT/provider stop。

失败保全：FAILURES.md保存构造脚本嵌套引号SyntaxError（写入前失败）、验证制备误猜不存在依赖（没有候选变更）、Ruff3项原有失败。canonical RED FAIL/首GREEN FAIL/continuation LOCAL_PASS均source_consistent=true，见manifest；没有累计成一次全仓PASS。验证每步前后绑定全部11候选/mirror hash。

应用后最小门禁：root核对10before+新test目标不存在，串行应用唯一patch；重跑当前worker/测量/contract tests、生成check与UI sanitizer；正式application MachineFailure与API material/conversation失败持久化定向门禁，运行项目前端TS并保留现存Ruff基线。真实模型测量若另行授权，应保持同profile/预算，只取本新增有限元数据；不能因合成PASS宣称27B性能已恢复。未运行整体Rust/API/全仓/CI/native/installed/Owner验收，全部NOT_EXECUTED。

回退：仅恢复manifest列出的10份before并移除新test，保护其余dirty内容；没有数据迁移、provider修改或历史receipt写入需要回退。
