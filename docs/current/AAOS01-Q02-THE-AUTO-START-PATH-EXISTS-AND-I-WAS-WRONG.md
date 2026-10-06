historical: true
superseded-by: AAOS01-Q00-Q15-LEDGER-FINAL-20261005.md
说明：仅当前状态声明由上述主表替代；本文历史正文与原始证据保留，不能作为当前验收结论。

# AAOS-01 Q02：**找到了开机自启路径 —— 并更正我第 74 轮的结论**

## 1. 决定性的几行

```rust
// src-tauri/src/main.rs
727: fn main() {
748:   .setup(move |app| {
785:     // Backend launch can take up to the migration + readiness timeout;
813:     let launch_state = startup_backend.clone();
814:     std::thread::spawn(move || {                  // 启动线程
815:       let Ok(_operation) = launch_state.operations.lock() else {
816:         record_failure(&launch_state, RECOVERY_STATE_UNAVAILABLE);
819:       match BackendProcess::launch(&runtime) {    // 【在 setup 里就启动后端】
821:         if let Ok(mut slot) = launch_state.process.lock() {
827:         if let Ok(mut recovery) = launch_state.recovery.lock() {
```

**所以宿主在 `.setup()` 里、由一个派生线程就启动了后端。**

## 2. ⚠️ 更正我第 74 轮「只有点按钮才启动 Core」的结论

| 路径 | 位置 | 触发方式 |
| --- | --- | --- |
| **A** | `.setup()` → `std::thread::spawn` → `BackendProcess::launch`（`main.rs:814/819`） | **开机自动** |
| **B** | `#[tauri::command] retry_backend` → `retry_backend_blocking` → 同一个 `launch`（`main.rs:470/526`） | 界面按钮 |

**我第 74 轮只读了 B，却把它当成了「唯一的路」。**
**我当时写：「无人值守时它永远不会自己起 Core —— 因为没有任何代码路径在启动时调用。」**
**那句话是错的 —— 有，就在 `.setup()` 里。**

**这已经是我这个会话里第三次「从一个样本过度概括」**（第 59 轮的 503、第 73 轮的窗口标题、这次）。
**共同模式：我只看到一条路径，就断言「只有这一条」。**

## 3. 那为什么我几次跑它都没起 Core？

`.setup()` 里那个线程**先解析 runtime，再启动**：

```rust
819: match BackendProcess::launch(&runtime) {
```

对照我实测到的现象：

| 观察 | 与「启动路径失败」是否相符 |
| --- | --- |
| `data_file_count: 0` | ✅ 相符 —— 运行时解析失败就不会建库 |
| 界面显示 RecoveryShell | ✅ 相符 —— 失败会 `record_failure`，前端据此进恢复态 |
| WebDriver 读到的是 **Chromium 错误页** | ✅ 相符 —— debug 构建走 `devUrl`，5173 无服务 |

**所以有两个独立问题叠在一起**：

```
问题一：debug 构建 → 加载 devUrl → 没有前端 → 界面是错误页
问题二：runtime 解析 → 若失败 → 后端自启也不发生
```

**我此前只认了问题一，把它当成全部原因。** 实际上**问题二可能是更根本的那个** ——
因为即使前端正常，`BackendProcess::launch` 也需要能解析出 runtime。

## 4. 我**不**声称的

| 不声称 | 原因 |
| --- | --- |
| 「runtime 解析失败就是根因」 | **未验证** —— 我只是看到 `data_file_count: 0` 与失败路径相符 |
| 「前端不是问题」 | 前端仍是独立问题（debug 走 devUrl） |

## 5. 下一轮该查什么（具体）

1. **读 `.setup()` 那段线程里的 runtime 解析逻辑**（`main.rs:785-819`）—— 它究竟要求 `runtime/` 与 `worker-profile.json` 以什么形态存在；
2. **对照老 Green 的目录形态**（它有 `runtime/`、`frontend/`、`ArcheAxis.exe` 平铺在一起）—— **那很可能就是解析器期望的布局**；
3. 若如此，**我此前的临时构建目录缺的正是这个布局**。

## 6. 本轮未做

1. **未**做 release 构建（下一轮）；
2. **未**改任何实现文件；**未**触碰官方 Green 的 `data/` 与资料库；
3. 全程**只读**。
