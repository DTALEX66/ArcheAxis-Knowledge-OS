# Backend 接手范围与实施次序

BE00 接手审计已完成。现场 main 基准、有限宿主链、复用能力和真实缺口见 AAOS-HOST-BASELINE-20261013.json。此结果是 SOURCE_REVIEW，不代表新 BE01–12 实现或联合运行验收。

顺序：BE01 合同登记 → BE02 独立布局；BE04 配置/用途/凭据 → BE03 材料问答与 BE05 会话；BE06 角色与受控记忆、BE07 范围化就绪、BE08 只读计划；BE09 类型化草稿与 BE11 格式资格；BE10 有限本地适配互通；BE12 按实际 source identity 完整验收。前端依赖按 frontend_selected_tasks 接续，不用通用假成功接口代替缺失实现。

所有状态只更新当前执行记录及 receipts/AAOS-REMAINING-EXECUTION-20261013.json，不改不可变 TaskPack。ASTRYN 提供片段缺依赖，先使用固定版本本项目适配器，外部联合运行仍独立验证。正式 workers 位置 services/python-workers/，不是 TaskPack 中历史建议 workers/。布局不复用业务 ui_state 的正文存储；launch-token 不进 React。

回退：任务来源与原始材料保全；源码增量可单提交 revert；数据库兼容、授权恢复 fence、知识特殊人工批准流程保持有效。
