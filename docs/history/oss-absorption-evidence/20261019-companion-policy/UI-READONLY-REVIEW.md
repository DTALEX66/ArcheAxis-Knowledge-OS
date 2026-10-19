# 现有原生页面语义与信息密度只读复核

状态 PARTIAL；两张现有原生截图已用 view_image 实际查看。未执行新测试；未修改产品、文档或测试源码。此建议不能覆盖当前 Authority，不能替代后续实际视觉验证。

## 发现

1. P1：page14 的全局/侧栏名称为“纠正、评测与复测”，活动 Dock tab 却是“项目记忆与上下文”；page20 全局/侧栏为“版本、来源与历史”，Dock tab 却是“阅读与编辑”。业务面板内容确实接收了正确 pageId，不宜误诊为整个路由错误。直接根因：PanelRegistry.businessPanelId 将13/14/22归为13、02/03/20归为03；DockWorkspace.open用findUiPage(panelId).label命名，existing分支不更新标题。保留同一个业务宿主和草稿，语义标题应由retained.current中的实际uiPageId投影，首次创建、同族切换、重开、布局恢复、对象文档视图均同步；对象视图维持独立文档身份。不可拆成重复业务宿主，也不可改写页面权威名称掩盖冲突。
2. P2：page14最前面固定排列CharacterMemoryPanel、ConversationPanel，再是CanonicalAiJourneySpace。结果该页首屏主要呈现普通陪伴回答/会话表单，与当前页面目的不符。最小修复是在既有ControlledAi页面内建立清楚的业务章节标题，纠正与复测主流程优先，角色记忆及普通陪伴使用现有details折叠或清晰分区；保持其挂载以保留草稿/会话，继续复用同一CompanionSession。不能以隐藏真实失败/取消反馈换取简洁，也不能另建UI壳或诊断中心。是否默认展开某组需结合当前主任务与回到同一会话状态，不能每次重新mount。
3. P2：FrozenRequestSummary直接输出document_id/source_id/transform_id。CanonicalLibrarySpace.onInspect.detail将文档ID、正文SHA和sourceRevision拼成字符串，Inspector不分层直接输出，造成截图右栏多行长哈希挤占。应使用材料标题/版本/范围作为业务摘要，完整身份作为结构化诊断经既有RawReceiptButton保留；不要正则截断原字符串。材料标题必须来自确切已读回身份，不以当前输入冒充冻结计划。
4. 知情确认字段不能一概当工程噪音删除：用途、冻结问题、固定版本/选区、模型与通道、本地/云端目的地及生成预算仍应清楚可见。地址和模型不能用虚假“本地”标签概括；可把字段排成紧凑分组，完整内部ID移入诊断。截图中的模型拒答另属已识别回答策略问题，此次不重复归因于UI。

## 最小回归

- 扩展现有真实Dockview组件测试：13→14→22与02→03→20，各次断言活动tab可访问名称、关闭按钮名称与收到pageId一致，mount次数保持1，输入草稿不丢；布局冷恢复后及关闭/重开后仍一致。现有测试只断言draft-pageId，不检查tab标题，因此漏掉此问题。
- App层行为测试断言当前标题、侧栏aria-current、location.hash及实际业务section一致；拒绝草稿导航时四者都保持原值。不要仅测字符串映射。
- FrozenRequestSummary测试同名材料不同版本、选区、云端目的地、未核实模型：可见摘要准确，完整ID可通过既有诊断动作读取，确认提交使用原冻结请求。不能为外观更改待确认计划或SHA。
- Inspector测试业务摘要默认不含长ID/hash，诊断打开后完整原值保留；长中文标题、120字符内部ID不产生横向溢出。
- 最后在固定原生候选重新截取page14/page20、普通陪伴与材料取消屏，必须实际查看。记录视口/DPR/主题/字体/版本；结构测试不等于原生视觉PASS。保留大地图、内缩结构、虚拟人物窗口与现有渲染器。

## 后续可应用提案

`navigation-labels.patch` 只涉及 DockWorkspace.tsx、DockWorkspace.test.tsx 和 AppDockNavigation.test.tsx 中原先依赖错误标签的一处选择期望。产品文件未写入。

新发现并覆盖：Dockview.setTitle本身不会使独立组关闭按钮重读activePanel.title；提案通过useSyncExternalStore订阅onDidTitleChange并释放订阅，确保关闭动作的可访问名称同步。所有标题修改在quiet控制区执行，不反向发业务导航。布局恢复后重投影全部已登记保留宿主的语义标题；对象视图保留文档ID标题。

隔离提案验证：run ui-label-proposal-1019-r8，exit 0，26/26通过、0跳过。真实现有Dockview在jsdom中运行，Core/业务空间为既有测试替身，证据级别SYNTHETIC。原始产品负对照 run ui-label-proposal-1019-original，exit 1，17通过/9失败，证明新断言能够捕获原始语义错位。早期隔离路径/依赖解析及伴随aria-label失败日志保留，不算产品失败或最终通过。

`git apply --check`通过，三源文件SHA读回未变。TypeScript与应用补丁后的原生视觉验证仍NOT_EXECUTED。主Agent须在解除原生源码冻结后核对source-manifest.json，再应用并在产品真实入口统一验证。
