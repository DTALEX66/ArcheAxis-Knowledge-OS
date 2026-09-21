# AAOS UI 套件审计 Intake

日期：2026-09-22
来源：Owner 明确授权审计 `D:\\All projects\\UI套件` 并将分析放入 AAOS。
审计结果：`READ_ONLY_AUDIT / IMPLEMENTATION_NOT_STARTED`

## 结论

UI 套件不是无关参考，而是 AAOS 的完整设计来源链。权威顺序为 B10→B01，B03 AAOS 配色纠正母版是颜色特权来源。当前 Avalonia P3 吸收了部分四列壳层、Core 投影和深色面板概念，但没有达到 B05/B10 的 AAOS 页面和交互层级。

## 决策

1. 继续使用 Avalonia 作为正式桌面壳，不另起 React 第二真相。
2. 吸收 UI 套件的 Tokens、页面 IA、组件状态和交互模式，不复制 demo 数据或 localStorage。
3. 先建立 Avalonia Theme/ResourceDictionary 和共享组件，再逐页接真实 Core projection。
4. 首个 UI 主链为 Capture Inbox → Evidence Library → Evidence Detail → Review/FSRS。
5. GUI 视觉验收必须包含真实窗口截图、点击和状态回读；headless smoke 不能替代 GUI 验收。

详细报告：

- `docs/current/UI_IMPLEMENTATION_AUDIT.md`
- `docs/current/AAOS_VISUAL_QA.md`
- `docs/current/DATA_PROVENANCE_UI_AUDIT.md`

本 Intake 没有修改产品代码、外置 UI 套件、Green 或共享资源库。
