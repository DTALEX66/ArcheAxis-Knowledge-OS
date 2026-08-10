# 前端与桌面融合最终方案

## 1. 重新排序后的产品中心

项目定位改变后，一级产品重点从“Agent Desktop”调整为：

1. 总览；
2. 资料库；
3. 研究验证；
4. 知识库；
5. 学习中心；
6. AI 知识；
7. 双向转化；
8. 任务应用；
9. 画布与回放；
10. 连接；
11. 系统。

Agent Center 仍存在，但属于 AI 使用层。

## 2. OpenHuman 的吸收

保留：

- 用户友好的外层桌面；
- 一级导航 + 动态二级导航；
- 对话/学习/连接统一；
- 简洁 Empty State。

不保留：

- Tiny Place；
- 钱包；
- 社区；
- 静态功能介绍卡；
- 品牌资产。

## 3. 旧紫晶方案

保留为深色主题：

- 元枢·紫曜 / Violet Core；
- 高密度；
- 适合画布、研究、系统控制、夜间使用；
- 顶部标签；
- 左树；
- 右 Inspector；
- 底状态栏。

## 4. 苹果风格方案

作为默认明亮主题：

- Apple-light；
- 柔和白灰；
- 蓝紫环境光；
- 磨砂顶栏；
- 轻阴影；
- 14–18px 圆角；
- 适合长时间学习与阅读。

不使用 Apple Logo、字体文件或系统图标资产。

## 5. 最终桌面壳

```text
顶部：
  品牌 / 项目 / 全局命令 / 搜索 / 环境 / 模型 / 通知

左侧：
  一级导航 / 项目空间 / 动态二级导航

中央：
  Dashboard / Library / Editor / Learning / Task / Canvas / Replay

右侧：
  Context / Source / Evidence / Permission / Trace / Evaluation / Audit

底部：
  Local / Core / SQLite / Job / Delivery / Review / Version
```

## 6. 页面优先级

### A1

- App Shell；
- 观心总览；
- 当前真实状态；
- Inspector 框架；
- 底部真实活动；
- 两套主题兼容；
- Planned 空状态。

### A2

- 资料导入；
- Research；
- Knowledge；
- Learning；
- Mastery；
- Machine Knowledge。

### A3

- AI 使用；
- Task Mission Control；
- Agent Center；
- Public Task/Agent Reference；
- Action Capabilities。

### A4

- Research Canvas；
- Knowledge Canvas；
- Execution Canvas；
- Replay。

## 7. 产品真相

参考图中所有数字、模型、Agent、成本和进度都是视觉占位。

实现时：

- 有 API：真实接入；
- 无 API：显示 Planned；
- 不伪造；
- 不暴露内部 ID；
- 不用前端计时器生成任务历史。
