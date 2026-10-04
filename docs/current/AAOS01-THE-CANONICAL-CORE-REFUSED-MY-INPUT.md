# AAOS-01：**Rust Core 的启动输入未满足**（如实记录）

## 1. 我做了什么

第 129 轮确认 `core/archeaxis-api.exe` 是「规范写入者」，而老 Green 的候选里**有编译好的二进制**。
于是本轮：

```
1. 只读确认三个候选都有 core/archeaxis-api.exe（6.06 / 85.7 / 6.06 MiB）
2. 把最小那个【复制】到我的 scratch 区（Green 目录本身未改动）
3. 无参运行 -> 得到用法：usage: archeaxis-api <workspace-db-path> [port]
4. 用 scratch 的 DB 路径与端口 8815 运行
```

## 2. 结果：它拒绝启动

```json
"exit_code": 2
"output_tail": ["invalid launch input"]
"db_files": []
"up_after_tenths": null
```

**`invalid launch input`** —— 用法行说 `<workspace-db-path> [port]`，
**但它对输入另有校验**，我的组合没通过。

## 3. 可能的原因（未验证）

| 可能 | 依据 |
| --- | --- |
| 要求 DB 文件**已存在** | 我给的是不存在的路径，`db_files` 为空 |
| 要求路径在**期望的根**之下 | 未知 |
| 需要**启动令牌 / 作用域环境变量** | Tauri 启动器会给 Python 后端设 `ARCHEAXIS_DESKTOP_LAUNCH_TOKEN` 等（第 112 · 113 轮） |

**我只列可能，不挑一个当结论。**

## 4. ✅ 但有两件事是确证的

| 事实 | 依据 |
| --- | --- |
| **三个候选都带编译好的 `core/archeaxis-api.exe`** | 只读存在性检查 |
| **该二进制是可运行的、且会自我校验** | 无参运行给出用法并以码 2 退出；带参运行给出明确错误 |

**所以它不是缺失或损坏 —— 它只是要我给出它期望的输入。**

## 5. 我要守住的两条边界

| 做法 | 理由 |
| --- | --- |
| **只复制二进制到我的 scratch 区运行，不在 Green 目录内运行** | Green 的 `data/` 属于**不得检查/复制/清空/改名/删除**的类别 |
| **用 scratch 的 DB 路径** | 不让它碰到任何既有数据 |

**本轮没有改动 Green 目录里的任何文件** ✓ —— 只**读**了目录项与文件大小 ✓

## 6. 下一轮（具体、低成本）

**只读地在 `crates/` 里找到 `invalid launch input` 的抛出点**，看它究竟校验什么 ——
**那才是「它期望什么输入」的权威答案**，比我从错误信息猜要可靠。

## 7. 我**不**声称的

| 不声称 | 原因 |
| --- | --- |
| 「Rust Core 跑不起来」 | **它跑起来了并拒绝了输入** —— 两回事 |
| 「Q03 的 actor 契约已测」 | **完全没测到** —— 进程没起来 |

## 8. 本轮改了什么（说清楚）

| 改动 | 位置 | 性质 |
| --- | --- | --- |
| 从 Green 候选**复制**了 `archeaxis-api.exe`，并用 scratch DB 试运行 | `.project-local/runs/rust-core-probe/` | **只读 Green + 本地副本** |

**未改任何仓库文件**；**未触碰官方 Green 的 `data/` 与资料库**；
**Green 目录内未创建/修改/删除任何文件**；**未执行任何安装**。
