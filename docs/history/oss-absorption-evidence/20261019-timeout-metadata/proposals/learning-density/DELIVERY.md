# 学习与反馈信息密度隔离提案

状态：PARTIAL；隔离行为测试 PASS / SYNTHETIC；产品未应用。

## 固定入口

- `learning-density.patch`：SHA-256 `70b66e7f13729ea7c15b82ff4820cfb6f4d685405e9789a1db2d0829711e1a89`。
- `source-manifest.json`：4 个现有文件前置哈希、5 个提案文件哈希与验证边界。
- `verification-summary.json`：最终命令、时间、退出码、负对照失败用例与历史失败说明。
- `readback.json`：最终提案/源文件哈希、git apply --check、Git 忽略边界回检。
- `proposed/frontend/src/`：可审阅的产品与测试副本；`validation/` 仅用于复用现有依赖的隔离执行。

## 发现与修复范围

已通过 view_image 实际查看 `.project-local/runs/be268a2d33/webdriver-415f723fdf9f/tmp/journey/grouped-learning-review.png`（1600×1000）。图中顶部知识/问题/课程/课时身份拼接及默认学习项目键表单挤压真实题目；重复说明与当前对象重复队列继续占用首屏。输入答案后，旧草稿 summary 还会再次显示完整 item_key 和知识修订。

补丁仅改 2 个产品组件、扩展 2 个既有测试并新增 1 个密度回归文件：

1. Teaching 同对象区域标题使用已核对的真实业务标题；未取得对象时明确“学习项目（标题尚未核对）”，身份失败仍显示 alert。完整 journey 身份从原段落移交既有 RawReceiptButton / 对象与来源诊断；不新建诊断入口或宿主。
2. 当前对象练习中的学习队列按需展开；独立学习页队列仍默认显示。手动精确键定位放入原生 details；输入框、读取命令和精确键保持原样。去掉首屏重复说明，作答/对错/自评区域的 Core 规则和知识、机器能力边界仍保留。
3. 独立学习页当前对象使用队列真实标题；缺标题明确未核对，不从隐藏答案造标题。题目版本标识进入既有诊断通道，完整保留 item_key、assessment_id、question_version、knowledge_id/version、source/anchor，避免诊断身份按钮提前显示答案内容。
4. 草稿 summary 改为对应真实标题或未核对标题；完整 item_key/knowledge_version 与原始保留答案仍可展开核对。恢复、丢弃确认、1 MiB 拒绝、未知提交、冻结重试及真实对象请求保持既有行为。

不修改请求/课程键、课程绑定、冻结复习语义、大地图、内缩结构、虚拟人物窗口、渲染器或当前任务台账。

## 验证

- 原源码负对照：5 文件，49 测试；41 PASS / 8 FAIL，退出码 1。第一次原源码负对照先于任何产品提案副本生成；追加草稿复发回归也先重新验证原源码，再更新提案。
- 最终隔离提案：5 文件，49/49 PASS，退出码 0。覆盖同对象 11/12 路径、明确未核对/失败、诊断身份精确值、显式展开按键定位、独立答案/当前标题、禁止提前显示答案、精确提交、草稿复发、跨题草稿、恢复、冻结重试与 1 MiB 保全拒绝。
- `git apply --check`：PASS，退出码 0；4 个现有文件 preimage 与当前磁盘一致，新测试在产品目录不存在。只读回检通过。
- 第一次正例曾失败：jsdom 不模拟原生 summary+Enter 的默认行为。保留失败记录；最终回归验证显式点击展开，原生键盘标 NOT_EXECUTED。另保留一次因测试错误假定 assessment_item1_v1 导致的失败；核对 fixture 后改为实际 assessment_1，产品语义未改。
- 最终命令与起止时间以 `verification-summary.json` 和两次 runtime execution.json 为准；原生候选/共享浏览器及服务均未操作，未创建常驻服务或浏览器。

## 应用后最小验证与限制

主 Agent 应在原生运行冻结解除后先核对 manifest 中 4 个现有文件 preimage 和补丁哈希，再应用并运行定向测试、TypeScript、构建。原生截图与键盘测试需核对：按键定位和队列 Tab/Enter/Space 展开、焦点返回、长标题/窄窗口、题目首屏可见、输入答案后的草稿摘要、诊断全文精确身份及未知提交仍保留答案。

本轮未执行提案的 TypeScript、Vite/Tauri 构建、原生视觉/键盘、全产品测试、exact-SHA CI、安装及 Owner 验收；不将 49 个 SYNTHETIC 行为测试宣称为全产品或原生 PASS。次要全队列 ISO 时间仍在展开队列保留真实原值；多条未确认复习请求的恢复按钮仍沿用原行为，未扩成全页重设计。

原有 dirty 修改未覆盖；本任务仅在当前 ignored 目录写提案、验证脚本、报告及测试缓存。最终 Git 状态保存在 `git-status-final.txt`，应用前还需与主 Agent 并行工作状态核对。
