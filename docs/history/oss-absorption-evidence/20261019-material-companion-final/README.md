# 材料／陪伴最新原生尝试与失败接续（2026-10-19）

**PARTIAL；最新原生整旅程 FAIL。** 当前源码候选绑定 patch `95428057cc7cefe520f9e4c0a87d0c1ca9508b090e05003b6bf307281a287be4`，host `b80b9cdd7804db876d22829049a81d1381a7b350abd717a13f18f5903536df47`。本目录保全本次证据，不建立新权威或进度库；继续沿[活动指针](../../../current/AAOS-ACTIVE-EXECUTION.json)和[当前执行记录](../../../current/AAOS-UI-FIRST-EXECUTION-20261009.md)执行。

## 实际改动与验证

- 恢复现有材料请求后再读回答；保留原回执与调用次数核对。
- 布局瞬时不可达时仅有界等待、重新命中测试；永久遮挡仍失败，不强制点击、不修改 DOM。
- 受控输入框改为真实键盘全选替换，避免 WebDriver clear 与 React 状态竞争造成 endpoint 重复拼接；只读核对最终值。
- 最终61项＋145 subtests PASS，TypeScript/Vite/Tauri/Core 同源码构建 PASS。精确命令、开始结束时间、退出码及身份在 `probe-tests.json`、`host-build.json`、`core-build.json`、`native-execution.json`；构建、原组件回退 ZIP 与19524候选成员资格见 `candidate-build.json`。

## 三次实际尝试分别保留

| 尝试 | 结果与接续 |
| --- | --- |
| `webdriver-402c847cf11e` | 材料与陪伴实际27B调用成功，同进程恢复／冷重开读回 PASS；备份恢复后的文档导航遭遇布局瞬态，整旅程 FAIL。[独立历史快照](../20261019-material-companion-recovery/README.md)保留原源码资格 |
| `webdriver-0d698191e974` | 目录连接检查失败，截图显示输入 endpoint 重复拼接；本轮尚未开始材料／陪伴推理。不能归因于模型 TTL 或服务卸载 |
| `webdriver-3edafe42aed3` | 新键盘输入路径正常，首答／复测实际模型路径到达；材料请求返回 HTTP200，但持久终态为 failed、`material_model_timeout`。界面显示执行失败或取消，探针只等成功而最终超时。陪伴、冷重开与备份材料读回未到达 |

最后一项原因是从**本次自建合成工作区**以 SQLite `mode=ro` 读取 `machine_tasks.conditions` 的限定字段，见 `terminal-failure-metadata.json`；没有改数据库或读取真实用户资料。它确认超时终态，不证明模型内部耗时原因，也不能用延长预算后重跑替代调查。探针未记录执行响应正文是可观测性缺口，后续应及时识别失败／取消终态并保存原因；仍须保持失败不是成功。

`failed-attempts.json` 保存前两次命令、失败与原始回执引用；四份 red/green execution 保留修复前失败及中间断言失败，不抹除失败。新脚本与回归源码复制进本目录，按本次 hash 冻结。

## 范围、截图与退出

实际环境为 Windows、Tauri候选、真实本地Core／LM Studio及合成材料；没有安装或覆盖 Green、用户 workspace、模型绑定、共享配置或 provider。模型加载与答案质量、独立学习效果、完整格式、BE10、取消、安装和 Owner 验收分别未闭环。

最新 `failure.png`、`grouped-learning-review.png` 已实际查看；目录检查失败轮的 `failure.png` 也已实际查看。最新截图路径、长度和 SHA 在 `native-result.json`。PNG、原始回执及本次合成库保留于项目 `.project-local/`；仅派生元数据和脚本进公开归档。最新与前两轮拥有的服务、宿主和监听均已退出，记录在各原始回执及派生摘要中。

下一步最小范围：查明材料超时并改进探针终态记录；完成材料／陪伴原生恢复及备份读回，随后取消、BE10、复习标题与既有后续队列。并行只读核对见 `READONLY-REVIEW.md`，不把评审当实现。`MANIFEST.json` 绑定本目录字节；本地未提交、未推送、未云端备份。
