# 可选的请求级结构化输出合同

机器回答及复测新增可选`response_format`，沿Core请求、执行器暂存文件和现有生产worker传递到OpenAI兼容chat/completions。采用[LM Studio官方请求字段](https://lmstudio.ai/docs/developer/openai-compat/structured-output)；官方也说明部分小模型不支持，当前qwen实际支持状态仍UNKNOWN。本轮只实现和验证合同，未发起新的真实模型请求；原real1和ar2失败、F05 PARTIAL及学习效果未建立保持原结论。

合同仅接受最多8KiB、32个ASCII字段的平面object：固定name为archeaxis_response，strict=true，全部字段required，additionalProperties=false；字段只含string/boolean/integer/number类型。const、enum、default、description、examples、引用及其他额外键均拒绝，不把正确答案填进schema。integer另外限制为整数词法及±(2^53−1)，拒绝-0、1.0和指数词法；number须有限。这是明确的有限子集，不声称完整JSON Schema实现。字段顺序规范化后Core/Python共享向量核同一SHA。

省略或null保留旧请求投影、哈希、argv及回答行为；显式格式要求冻结client_request_id。格式及SHA写入持久请求和回答，参与缓存、冲突、拒绝指纹、journal与复测比较；复测须显式保留原格式，包括原先缺省的身份。worker和Core各自核原始最终content，禁止去围栏、补JSON、提取reasoning或重试；结构有效不表示事实正确。缺格式/格式不符/截断作为INVALID_OUTPUT拒绝成功发布，原NO_FINAL_ANSWER语义保留。不支持的传输协议拒绝结构化推理，不自动换端点。

正式`bkr-fpy2`269项通过（worker146及既有探针合同123），`bkr-flint2` Ruff通过；Rust四次offline/locked调用共41项通过：域格式3、重启journal1、拒绝指纹1、三API集成suite共36。API测试使用真实Store和合成worker子进程/内存router，不是生产模型或新包端到端资格；Python包含合成回环HTTP重定向测试，不能字面称零网络。全部正式收据actual/wrapper0、source_consistent=true，绑定b7358272加测试时dirty patch。候选146、格式检查与正式运行分别保留。stdin rustfmt原exit0但8份有diff，不把原exit0当格式通过；11份后继无diff。

根首轮`bkr-fpy1`测试路径错误，collection退出4且0项执行；`bkr-flint1`22条诊断保留。最小风格修正后重验；两个既有公开Failure异常名用具名N818行注释保留API，HTTP处理器使用标准override，无全局忽略或量规降低。

构建复用既有共享Core target和已配置离线工具链/registry，未复制runtime。逐命令target净增605,000,086逻辑B；完整前后可读下界142,872,594,863→143,490,535,065B，净增617,940,202B。两次均PARTIAL/exit1：674计量错误、243私有排除、581布局项仍在；新增长触发为NO_NEW_GROWTH_TRIGGER，不能据此称项目体积治理通过。预算估算约1.42GB、2GiB复核线及原失败均封存，未删除缓存。当前[唯一执行记录](../../current/AAOS-UI-FIRST-EXECUTION-20261009.md)继续区分实现、合成合同、实际模型、包及产品验收。
