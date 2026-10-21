# Stitch 设计来源对照（2026-10-21，只读）

项目10243059433218383839，整合页206611daf7a948edb97ea60c7a7d8654。截图实际查看，HTML1683行分段完整读取，实时下载hash与外部快照一致，见MANIFEST。本报告不建立进度；实际状态只写唯一执行记录。

| 项目 | 设计事实与当前实现 | 接续要求 |
| --- | --- | --- |
| 构图 | 星际背景、内缩研究主窗、右侧助手/资料、底部应用导航 | 可借鉴层级与留白；截图壁纸不等于可交互大地图，保留Owner大地图要求 |
| 研究链 | 问题→证据卡→来源页码/段落→笔记→结论草稿；设置有连接/任务模型/诊断 | 映射同一Core对象/版本/权限，保留支持反对冲突，不复制硬编码专题/学术结论 |
| 主壳 | App.tsx:759/804已有ConsoleWindow和DockWorkspace；前者有八边调整、键盘等价、Esc/pointercancel及compact | 保留现有壳与原生/内部窗口分别调整；原型仅鼠标SE手柄，不整体移植 |
| 拆分恢复 | DockWorkspace.tsx:85/97/129/154有容器标签降级、ResizeObserver、workspace/epoch校验、显式保存恢复 | 继续既有拆分/标签/会话与耐久；原型AppState仅内存，无真实Dock拆分 |
| 尺寸 | HTML:123主窗580–900×480–640；:153右栏380×600；无@media，body overflow:hidden，底Dock不换行 | 不覆盖640×480、窄矮组合/中文长文/DPI/缩放；后续按实际容器适配，不能截图等比缩小 |
| 材质主题 | 单cyan/slate、9–12px字和发光；现有glass-cabin.css:1/24/29有语义材质/边框/内缩token | 落到五主题/默认cosmic；正文可读，减少透明/forced-colors保留，不直接硬编码色或重装字体 |
| 小栖 | 原型只是文字助手，无虚拟人物资产/renderer | 保留ConversationPanel.tsx:27、XiaoqiAvatar及CompanionSession现有状态/授权材料/确认取消/未知查询/历史，人物窗口独立保留 |
| 图谱 | 原型没有关系图谱 | 保留CanonicalRelationSpace.tsx:107的ConstellationGraph，以及既有语义SVG、固定版本回调、减少动画、规模降级、键盘/pointer交互；不换画布 |
| 假成功 | HTML:1381诊断直接connected=true/alert，无真实API；同步/解析100%/资料128/关联94%固定；来源定位多为alert | 连接/加载/推理/保存/同步严格分开；真实API消费者才给可执行入口。HTML:1151的Ollama不覆盖LM Studio路线 |
| 覆盖 | 5路由workbench/knowledge/reader/research/settings＋3设置tab | UI-P01—24和22语义角色仍完整欠账；学习/能力/模型/图谱/安装等不能因原型没画而删 |
| 可访问性 | span/div点击缺键盘语义；缺dialog焦点/标签/状态播报；全局user-select:none；无减少动画策略 | 迁入React语义组件与现有焦点/键盘实现，允许选中文字；逐页状态验收 |
| 资源与安全 | Tailwind/CDN字体/图像外链；innerHTML插值包括连接名称/endpoint/key草稿 | 不执行或把这些实现搬进产品；后续先核许可/离线来源并走现有受控组件/安全存储合同 |

本轮范围：REAL远端只读获取；静态截图/源码对照。原型点击、浏览器a11y、性能、系统DPI、五主题渲染、真实产品接口、原生安装及Owner视觉验收均NOT_EXECUTED。原生Stitch MCP挂载UNVERIFIED，Read-Stitch.ps1入口在本会话REAL PASS。

后续顺序：当前后端CL/J优先；前端恢复时先小切片将“证据→原文→笔记→结论”及助手上下文布局接回现有研究/阅读消费者，保留大地图、内缩主控台、人物窗口和现有renderer，再按全部UI分片覆盖。只读设计接收不扩大产品实现或Stitch写权限。
