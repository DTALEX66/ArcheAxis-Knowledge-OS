historical: true
superseded-by: AAOS01-Q00-Q15-LEDGER-FINAL-20261005.md
说明：仅当前状态声明由上述主表替代；本文历史正文与原始证据保留，不能作为当前验收结论。

# AAOS-01 Q02：壳自己的 Core 启动**到不了就绪态** —— 本地端到端探针抓到（2026-10-05）

## 1. 怎么抓到的

写了一个**临时**集成测试（**不入库**），直接调用壳自己的 `BackendProcess::launch_core`，
对**权威流水线产出的真候选** `C:\Windows\Temp\aaos-cand1` 启动 Core。

## 2. 结果

```
thread 'launches_the_real_staged_core' panicked at tests\zz_local_core_probe.rs:21:10:
the shell's own Core launch should reach readiness:
  "desktop Core readiness timed out
   [core:stdout] archeaxis-api ready on http://127.0.0.1:61770"
```

**Core 确实起来了**（宿主选的端口 61770）✓ —— **而壳的就绪探针一直没成功** ✗。

## 3. 根因（已读源码确认）

```rust
596: fn probe_readiness(port: u16, token: &str, path: &str) -> Result<(), &'static str> {
627:     let payload = response_body(headers, body).or_else(|| json_body(body));
631:         .is_some_and(|line| line == "HTTP/1.1 200 OK" || line == "HTTP/1.0 200 OK")
638:     if !readiness_payload_valid(&payload) {
```

**我把 `path` 参数化成了 Core 的 `/api/v1/system/version`，但保留了对 Python 后端就绪载荷的校验**
（`readiness_payload_valid` 期望 `{"schema_version":"v1","product":…,"workspace":…}`）。
**Core 返回的是 `{"runtime":"archeaxis-api","contract":…,"schema_version":6,…}`** ⇒ **永远校验不过**。

## 4. 为什么这个比 CI 能发现的更严重

**CI 的新断言只检查 `.project-local/rt/core` 与 `rt/workers` **存在**** ——
**它不检查壳能否**到达**那个 Core。**
**只有这个调用壳自己代码的本地端到端探针抓到了它。**

**若就这样发出去**：候选里有 Core ⇒ `beside_runtime` 返回 Some ⇒ **走 `launch_core` ⇒ 就绪超时 ⇒ 启动失败**；
**且因为 `Some` 时不回落，壳会停在恢复态**，而不是悄悄用 Python。

## 5. 修法（下一步，需一次改动 + 重跑探针）

**给 Core 自己的就绪接受条件**：200 状态 + JSON 中 `runtime == "archeaxis-api"`（并可校验 `schema_version` 为整数）。
**`/api/v1/system/version` 是 Core 已特判的既有路由**（`runtime/mod.rs`），所以这是稳定判据。
**保留 Python 路径的 `readiness_payload_valid` 不变**（有既有测试断言其 chunked 解码 ✓）。

## 6. 本轮不声称

**未修**（下一轮改）；**未入库那个探针**（环境相关，已删除）；**未因此断定 `launch_core` 整体设计有问题** ——
**只是就绪接受条件复用了错误的载荷契约**。
