# 资产路径真实模型检查点：首答未评分与提前停止

本记录保存失败，不声明 F05 改善。实际 bpr1 包内 Python、start-backend.py、profile、Core 与生产 worker，在新独立库和合成材料上进入正式 asset adapter；第一个正向回答因代码围栏不满足预先冻结的纯 JSON 量规，记 REVIEW_REQUIRED 并停止。未去围栏、修改回答、伪造 INCORRECT，未改问题、模板、预算或模型配置。

执行源码为 `33ccac5aed304d3ead5996733ec582a65291c9ea`，dirty=true，patch SHA-256 `25345d98f564644061583d96c957bccf2b2fa9295c91af9b34dee2d8da7c6c62`。最终正式 adapter SHA-256 `0a6b5a93b50089856d31983bd9e920f33014f6bc848336b277854e089a5f0b3c`。七个主要 run 引用、原始轻量收据和最终源码身份见 [MANIFEST](MANIFEST.json)。这是历史执行身份，不是后续提交状态的复述。

| 证据 | 实际结果 | 边界 |
| --- | --- | --- |
| bkr-stop2 / bkr-sl2 | 123 tests passed / Ruff exit 0；各 actual/wrapper 0 | 无模型调用；新增四个持久边界覆盖原答未评分只 1 次、错误/未评分拒答只 2 次、正常 5 次控制，不依赖 ignored 历史 fixture |
| mdlpre2 | 两个只读 inventory HTTP 200；loaded_instances 全空 | 0 推理/配置请求；目录存在不等于 ready；旧 mdlpre1 保留，mdlpre2 为临近执行补充元数据 |
| bkr-ar1 | entry/wrapper 1；0 HTTP、0 Core、0 模型、0 text job | v3 入口误断言空串为 REVIEW_REQUIRED，实际 scorer 为 INCORRECT；finally 又以空 runtime identity 覆盖主状态。原失败字节保留，不称模型失败 |
| bkr-apreflight1 | entry/wrapper 0；NOT_EXECUTED_MAIN | v4 改用非空 prose 负控，生产 scorer 不变；启动前校验成功，0 Core/HTTP/模型/text job；异常阶段和 identity NOT_CHECKED 分开 |
| bkr-ar2 | adapter/entry/wrapper 1；source_consistent=true；11.733 秒 | 1 正向机器 HTTP 200（7.891 秒）；先有 1 个候选包授权负控 HTTP 403；1 text job、无自动重试 |
| 原 bkr-real1 | 保留 legacy FAIL，main 1 | 第一次 CORRECT；第二次 503/NO_FINAL_ANSWER、finish_reason=length、2048 输出耗尽。与本轮格式未评分及入口错误分别记录，不重签旧失败 |

bkr-ar2 使用 qwen3.5-4b/既有 loopback openai 路由、grounded 模板、max_tokens=2048、Core 120 秒及 HTTP 135 秒上限。原冻结量规/材料/生产模板 SHA 均在推理前落盘。返回内容包含匹配事实的 writer/frozen，但外有 fenced JSON，严格评分为 REVIEW_REQUIRED；finish_reason=stop、truncated=false，input/output/total 为 161/497/658。原 request、answer、授权、context 和 SHA 完整保留在原收据。

授权负控带候选 package/grant 引用且被 403 拒绝，不称“没有 grant 字段”；其后正向仅携知识 context grant，packet_sha256=null、asset_members=[]。前置 rule 成员采用及候选 package 准备已发生，但 package 干预采用/使用、拒答题、独立迁移题前后、纠正与复测均未执行。因此这次不是资产包进入模型的效果证明，learning_improvement=NOT_ESTABLISHED，F05 仍 PARTIAL。预造错误仅用于 pure scorer 负控，不冒充模型原答；正确原答不会人工纠正。

正向候选计数为 1，HTTP 返回及生产诊断证实一个真实模型回答；入口未做底层 transport 拦截，不能把此数当全服务硬计量。仅使用合成 CONTEXT，自有库；包内 Python/Core/launcher/profile/worker 五个观察成员前后 SHA 相同，未复制 runtime。Core PID 36152 已 terminate/wait 回收 exit 1；精确端口 53428 的 IPv4/IPv6 两相均 complete 且无 LISTEN。connect_ex=10035 仍 UNKNOWN，不称 refused/closed 或 graceful，不扩称全机 worker 清场。

本次归档只读收据并生成本目录候选，未重跑推理、Core、编译或测试。先前 synthetic/current-Core 证据仍沿 [既有资产探针历史](../asset-scoped-probe-20261031/README.md)，旧真实失败沿 [legacy 历史](../colearning-real-model-20261031/README.md)。未验证一般学习、完整资产 scoped 改善、安装、UI、Owner 验收或全闭环；实际进度仍只导航唯一执行记录。
