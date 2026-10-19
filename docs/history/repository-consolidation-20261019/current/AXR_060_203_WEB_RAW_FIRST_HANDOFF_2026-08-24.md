# AXR-060-203 Web Raw-first 修复交接（2026-08-24）

## 状态

`IMPLEMENTED_LOCAL` / `TESTED_LOCAL`，但 AXR-060-203 总体仍为 `PARTIAL`。
本记录对应候选分支 `codex/raw-first-web`；未取得该分支 exact-SHA CI、网络隔离
端到端或安装版证据。

## 本次修复

- `capture_web()` 不再把已抓取的 URL 交给 `convert_url()` 二次请求；正文只从同一
  原始响应的 bytes 本地提取。
- 原始 bytes 在提取前写入 `RawAssetStore`，由完整 SHA-256 内容寻址；持久化失败
  会终止捕获，不会继续产生没有原件的转换结果。
- 回执保留完整 SHA-256、请求 URL、最终 URL、HTTP 状态、捕获时间、内容类型、ETag
  与 Last-Modified；响应 header 以大小写无关方式读取，匹配 SafeHTTP 的实际输出。
- 可选 HTML 提取器缺失或崩溃时保留原始 HTML，并返回明确 `loss_report=degraded`，
  不伪称成功转换。
- 即使 HTML 正文抽取成功，结构损失仍标记为 `loss_report=not_assessed`，直至有
  冻结结构金标准；不把提取器成功等同于无损或准确率。

## 已验证证据

- `tests/test_web_asr_d4.py` + `tests/test_raw_asset.py`：25 passed。
- `tests/test_ingestion.py`：3 passed、1 skipped。
- 回归覆盖单次抓取、完整哈希、RawAsset 读回、最终 URL/响应元数据，以及可选提取器
  崩溃时的原件保全与诚实降级。

## 未关闭范围

- WebSnapshot 回执尚未作为独立领域对象持久化；现有 RawAsset sidecar 只保存原件的
  基础来源/MIME 信息。调用方必须保存返回的 receipt 才能长期保留 ETag/时间等细节。
- 未执行真实公网/网络隔离 E2E；测试使用注入响应，不能作为网络运行证据。
- 未实现动态页面、站点遍历、登录平台、可恢复 CrawlJob 或安装态 Web 摄取；这些属于
  独立的 AXW-WEB 后续任务，不能借本次静态单页修复宣称完成。
