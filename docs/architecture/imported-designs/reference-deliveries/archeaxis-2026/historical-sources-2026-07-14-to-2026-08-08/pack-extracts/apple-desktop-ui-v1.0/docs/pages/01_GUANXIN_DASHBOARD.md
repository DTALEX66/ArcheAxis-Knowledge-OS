# 页面 01：观心总览

## 参考图

`references/screens/01_guanxin_dashboard.png`

## 目标

作为桌面默认首页，将 Human 入口、真实任务、知识、审批、系统状态和认知检查器放在同一视图。

## 页面结构

- 左侧：一级导航 + 项目空间；
- 顶部：全局搜索、环境、模型路由、通知；
- Hero：问候、全局任务输入；
- 快捷入口：导入资料、创建研究、运行任务、打开画布、连接数据源；
- 真实指标卡：
  - 待审核 Research；
  - Job 数量；
  - Outbox pending/failed；
  - Learning/Mastery；
  - approved Machine Knowledge；
- 最近真实活动；
- 能力边界；
- 右侧 Inspector；
- 底部状态栏。

## 数据要求

A1 只能使用现有 status/jobs/delivery/research/knowledge/learning/evolution API。

## 禁止

- “3 个 Agent 正在运行”除非后端已存在真实 Agent projection；
- 静态 GPT-5.6；
- 静态 Token/费用；
- 虚构系统资源；
- 任务百分比。
