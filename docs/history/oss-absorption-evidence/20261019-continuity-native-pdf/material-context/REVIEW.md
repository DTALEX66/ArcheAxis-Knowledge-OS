# 原生材料回答低效用：只读诊断

结论 **PARTIAL**。可证的具体问题是探针生成了两个不同的“材料编号”，把观察标记写进模型问句，造成指代歧义。**没有证据证明产品正文丢失**；原生全文/选区/proof与源码传递链反而一致。此歧义是否实际导致该次回答，仍 **UNVERIFIED**，不能用模型“上下文未提供”的自述作根因证据。79.95秒实际模型内部耗时成因亦UNVERIFIED。

## 保留原例与证据

- 指定原生receipt SHA256 `e1df045abc5f5881c2e42c09395aac0f42946d414fdc6a34ab7ecfbab9737e3e`，与NATIVE-READBACK绑定一致；原样本、问题、回答未修改。
- 自有合成正文：`Independent synthetic material 59a40506553e4814bb3de90b0e65e99f. ArcheAxis keeps a versioned local note for reading and review.`
- 问题：`合成材料 91375d0555ef：请用一句中文概括所选材料的主题。`
- 回答：`上下文未提供合成材料 91375d0555ef 的主题，无法概括。`
- 该正文127 UTF8 bytes，选区UTF16 `[0,127)`，quote SHA与context SHA均 `9d995968e30c89e85fb9e4a538c74f408bc428155af4802b5a676e19fbac7ba4`，全文重算一致。document content SHA是结构快照身份，不能与纯文本SHA混为一谈。
- 79.95s，finish_reason=stop，truncated=false，answer_source=content，grounded，usage input210/output252/total462；candidate/succeeded不表示语义质量达标。provider output252不能拆成已知reasoning token数或最终正文token数，也不能用aggregate时间冒称生成TPS。

## 可追踪责任边界（当前源码行号）

1. **探针歧义已证实**：`scripts/probes/aaos01_material_independent_loop.py:22` 创建正文时独立uuid；`scripts/probes/aaos01_material_companion_loop.py:169-170` 又生成另一个nonce并把它放入“合成材料 <nonce>”问句。receipt直接证明问句编号不在所选正文。observer在同文件20-28行用问句相等判断own，因此隔离标记泄漏进业务语义；问题在测试设计，不是文档版本绑定。
2. **选区/正文准备**：`crates/archeaxis-domain/src/material_question.rs:58-76` 按document id/version读快照并校验content SHA，97-115按UTF16边界摘quote并验证quote SHA、限制非空及长度，返回同一text和proof。`scripts/probes/aaos01_material_companion_loop.py:189-192` 实际断言所选文档完整身份及全文全选；原生receipt均成立。
3. **Core→worker**：`crates/archeaxis-api/src/runtime/material_questions.rs:100-109` 返回text+proof；135-136在准入时复核proof；165-173把text直接传Executor。`crates/archeaxis-application/src/executor.rs:247-267` 明确Grounded策略；365-367将原context UTF8写入自有临时context.txt，407-428传文件、原question、预算及冻结策略版本。没有从“purpose”或材料编号取代正文的路径。
4. **worker请求**：`services/python-workers/machine/worker_machine_answer.py:591-604` 读取context文件；475-481做strip/非空检查；195-204的grounded模板包含Context全文和Question。413-417的OpenAI body只有一条user message，规则也在同条user文本中，**没有显式system角色**。没有证据应归因于缺system角色；服务端默认system/chat template未在指定证据中保存，本轮未读配置或日志。对原生运行前worker精确preimage `510c4973…` 与当前worker做AST常量对照，grounded template/version完全一致；当前新增测量代码不能追认原生已测量。
5. **仅源码重建，非wire抓取**：使用原receipt的合成正文、问题及冻结版本重建prompt，528 UTF8 bytes，JSON request700 bytes，全文出现在Question之前。prompt SHA在EVIDENCE.json。实际该次HTTP request body/context.txt现存字节未保存，本轮没有读取业务库或私人日志补齐，因此不能绝对证明provider实际收到的字节；应明确此证据缺口，而不是断言丢失。
6. **回答提取不是reasoning误充**：worker447-457优先取非空content，只有content空且reasoning非空才标reasoning_content；529-537拒绝reasoning-only。该次answer_source=content且非空，因此不是已知reasoning-only假成功路径。provider的实际reasoning正文未记录，也未读取，不可由output252反推出思考内容或原因。extract605-626直接保留最终answer，没有删改“主题”的逻辑。
7. **成功guard边界**：`crates/archeaxis-application/src/executor/machine_failure.rs:10-39`校验时限/非空/请求模型；material_questions.rs187-210校验目的地/模型后标succeeded，authority仍candidate，grants_knowledge_acceptance=false。probe的assert_bound_receipt54-77要求模型/stop/nontruncated/content/非空/哈希，但没有摘要真值。它的227行状态明确NOT_QUALITY_QUALIFICATION；当前报告也已标低效用，未发现被升级成知识资格的事实。禁止用“无法概括”字符串一刀切失败，真实材料确实缺依据时谨慎拒答是合法结果。

## 最小修正及回归建议（本轮未实施）

- 保留本次旧receipt/question/answer与低效用结论；新版本探针将隔离nonce放stage证据身份或现有purpose字段，明确问句只指当前所选正文，例如“请根据当前选中的正文，用一句中文概括材料主题。”。不要改旧问句、覆盖原报告或声称替换后的PASS修复了旧问题。observer仍可在隔离workspace内比对精确问题/请求身份，不需要把随机编号当材料名称。
- 离线回归1：固定当前原正文和旧问句作为负例，断言旧问句引入的实体编号确实不在正文；新问句不引入任何独立材料编号。两个nonce故意不同，避免测试随机碰巧一致。
- 离线回归2：fake HTTP opener截获worker实际序列化请求（不启动服务、不接模型），从同一context文件经extract→answer→_call核对全文、顺序、UTF8、question、grounded版本/1024budget；content+reasoning并存时只发布content，reasoning-only仍NO_FINAL_ANSWER。此测试可证明应用构建请求，不等价真实provider接收。
- 质量单列：同一已知合成正文保留真值概念“版本化本地笔记／阅读复习”，摘要评估单独记录SUPPORTED / ABSTAINED / UNSUPPORTED / UNVERIFIED，允许中文同义表达，不钉死一句话、不以第二模型自评分代替真值；本次为观察到的拒概括低效用，不能倒填质量PASS。先离线验证探针修正，再由root决定是否执行授权的同模型/同预算新版本原生测量。
- 不改provider/model/1024/120s、无自动重试；不能为快或好看而转general策略、移除grounded约束或把失败显示成功。后续性能测量需新测量字段实际原生应用证据，HTTP open非TTFT。

本轮实际执行只有只读源码、JSON、AST及SHA断言；**没有测试套件执行、模型调用、服务操作或产品写入**。EVIDENCE.json保存有限合成样本和来源哈希。真实wire、服务端system/chat template、reasoning正文及provider阶段耗时保持UNVERIFIED。
