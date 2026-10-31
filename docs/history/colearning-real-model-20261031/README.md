# 真实本地模型：固定合成材料的失败检查点

基线6d556c48、空dirty patch，实际C1 Core与生产worker沿既有qwen3.5-4b/loopback路由执行完整probe入口。只使用新run的合成材料与独立Core库；正常JIT允许，未使用load/unload、下载、切换或配置修改。

实际模型请求2次。第1次HTTP200/finish_reason=stop，20.44秒，冻结量规评分CORRECT，没有纠正正确答案。第2次HTTP503/NO_FINAL_ANSWER：25.09秒、finish_reason=length、answer_source=reasoning_content，固定2048输出token耗尽但没有最终答案；不是135秒客户端超时。原result.model_response_observed_count=1只统计顶层成功答案，不代表总推理仅1次；两次都有用量诊断，合计input326/output3266/total3592。

实际main exit1、收据FAIL/source_consistent=true，REVIEW_REQUIRED。第3转移题及纠正/复测均未执行，无自动重试或降低量规。自有Core端口关闭、10个已观察进程退出；Core以terminate/reap退出，不称优雅停止。详见[MANIFEST](MANIFEST.json)。

这是已执行的真实legacy路径失败证据；不提升为全链通过、一般学习改善、asset/scoped效果、当前产品重建/安装态或Owner验收。后继不能为通过而暗改问题、预算或模型设置，实际进度仍只读唯一执行记录。
