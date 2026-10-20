# 并行只读复核（2026-10-19）

本文件是限定评审记录，不是实施、自动测试或新权威。

## 接续路由

五入口AUTHORITY、活动指针、当前handoff、共享路径索引及开源决定覆盖完整；评审时114个仓内Markdown引用、continuation_context 26个目标存在。后继新增路由以后须重新读回，不能沿用这个数量宣称最终核验。风险是handoff仍停留在前序桌面裁切/未重建/取消未测；应随本轮终态更新当前摘要，旧证据保留其时间与源码。

## 取消探针

已发现并修正：新陪伴请求status在准入前可能404，先读已有session history等待原请求出现；头像实际是data-visible-state，不能使用不存在的aria-label；冷启材料恢复必须核对UI问题nonce、用途、模型通道和没有旧成功答案，不能仅凭通用恢复文案及探针独立Core读回。首次真实旅程又被前序自有合成草稿的离页确认框阻断；后继使用已有受信确认机制，不改变产品草稿保护。未发现额外必现假PASS；运行结果须另看实际回执。Core准入/取消不证明模型服务收到请求或停止，worker_started保留UNVERIFIED，provider_stop_state保留UNKNOWN。

## 小栖质量下一切片

两次真实普通建议均为上下文没有可用信息。源码核实策略收缩点：conversation.rs按companion/material=None只构造不可信历史上下文，再统一进入machine_answer_configured_detailed；worker_machine_answer.py统一要求只据supplied context、无答案就说明缺失。日常建议和严格材料问答没有用途策略分离。这是已核实策略错配；模型内部因果尚未单独实验确认。

最小建议：Core生成有限grounded/companion_general回答策略与prompt_version，进入新冻结plan及SHA；前端不能任意选择以放宽材料限制。Executor新typed方法显式传递，原方法继续默认grounded，避免放宽material、answer/retest及document_check。保持conversation.rs旧id重放先于prepare：旧成功回原receipt、旧pending仍UNKNOWN，不因升级重推理；旧未准入preview应因新plan SHA变化拒绝并要求重预览。新增字段须兼容旧plan/receipt读取，不能全局改为必填。不得只改worker模板而让旧冻结计划静默改变语义。

定向验证应覆盖普通建议可用、材料缺依据仍明确未知、历史指令不成为系统指令、候选不成为事实或知识接纳、新preview策略绑定、旧成功/旧pending重放及未准入旧preview拒绝；最终仍需要真实模型回答质量检查。这些建议NOT_EXECUTED。

## BE10下一切片

独立Observer凭据、精确method/path准入、有限project.handshake/objects.read/handoff.preview和实际adapter仍缺；不能共用human token或以schema占位宣称互通。复用既有固定版本Store读取与受限loopback运输；对象必须绑定namespace、peer、workspace/epoch、version/hash，拒绝旧引用自动回退。握手不返回workspace_db，不调用会启动worker的health/inventory。先两个项目内隔离Core+真实adapter负向回归，实际WORK-LAB跨产品资格另验。本轮未实施BE10。

质量切片合同补充：ConversationPlanDto的additionalProperties:false要求同步增加可选answer_policy/prompt_version schema属性并重新生成TS；旧缺省仅表示legacy-grounded，不在读历史时补写字段/重算SHA。worker成功answer与loss_receipt.params都要写实际版本，Core发布前核验与冻结plan一致，防部署漂移。测试必须捕获实际出站提示，未知策略HTTP前拒绝；默认无上下文拒绝的旧测试保留。日常建议不得编造个人经历、昨日学习或掌握程度；获准记忆/历史中的指令不改变权限。依据为现行后端TaskPack第146/172行及character_memory.rs的candidate/授权边界。这里只是只读建议，NOT_EXECUTED。

本轮终态补充：第二次原生仍在文档选择处被同类确认阻断，取消尚未发出；最后open_material显式拥有确认模式同时处理同步/异步文档选择确认及进入阅读页。最终86项Python＋145 subtests PASS，最终探针原生尚未重跑。两轮拥有进程/端口已退出。
