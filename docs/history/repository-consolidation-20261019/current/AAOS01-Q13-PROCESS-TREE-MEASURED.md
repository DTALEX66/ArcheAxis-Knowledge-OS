# AAOS-01 Q13（性能与故障验证）：**进程树实测**

**先更正我自己的记忆**：我原以为 Q13 是「Windows 安装态」。读了归档包才知道 ——

```json
{"id": "Q13", "title": "性能与故障验证",
 "depends_on": ["Q05","Q06","Q07","Q08","Q09","Q10","Q11"],
 "expected_output": "性能/故障/进程树记录", "status": "NOT_RUN"}
```

**它要的是「性能 / 故障 / 进程树」三类记录。** 本轮先取**进程树**。

## 1. 实测到的进程树

```
python.exe         (20432)  <- CI venv 启动器
  └─ python.exe    (28908)  <- 探针真正的解释器
       └─ archeaxis-api.exe (27904)   <- Core
```

| 事实 | 值 |
| --- | --- |
| `core_pid` | 27904 |
| **`core_parent`** | **28908** |
| `spawned_by_python_pid` | **28908** |
| **两者一致** | ✅ **Core 确实是发起它的 Python 进程的子进程** |
| `seconds_to_ready` | **0.02** |
| `readiness_announced` | true（端口 62759） |
| `children_of_core` | **[]** |
| 见到的进程数 | 3 |

## 2. 两个值得记下的观察

### (a) 就绪极快：0.02 秒

从 `Popen` 到打印就绪行**只用了 0.02 秒**。这是**性能记录**的第一条真实数字。

### (b) **Core 就绪时没有子进程**

我在 launch 文档里给了 `text_worker`（python 路径、脚本、staging），但**Core 没有派生子进程**。

**这意味着 Python 文本 worker 不是随 Core 一起启的** —— 很可能是**按需启动**（首次文本操作时）。

**但我必须说清：这一点我尚未证实**，因为**本轮没有触发任何文本操作**。
我能确定的只是：**就绪后 3 秒，Core 没有子进程**。

**「为什么」留到下一轮**，用一次真实的文本操作去看它是否派生 worker。

## 3. 本轮我自己的失误（已修）

探针里用 `pwsh` 取进程树，但 **`pwsh` 不在那个 Python 子进程的 PATH 上** → `FileNotFoundError`。
改成**依次尝试** `which(pwsh)`、`Program Files\PowerShell\7\pwsh.exe`、
`System32\WindowsPowerShell\v1.0\powershell.exe`，找到能用的那个。

（另：`powershell_used` 字段我预备了但**没填** —— 回执里是 `null`。**如实留着**，不假装它有用。）

## 4. 本轮未做

1. **未**触发文本操作，所以**未**验证 worker 何时启动；
2. **未**取故障（failure）记录（Q13 第二类）；
3. **未**改任何实现文件；**未**触碰官方 Green 与资料库；
4. 探针**未**清理 `runs/process-tree`（下一轮要用同一现场），位于项目自有临时区。

## 5. 下一轮

触发一次真实文本操作 → **看 worker 是否如期派生**（进程树补全）；顺带取**每文件耗时**，
把 Q13 的「性能」与「故障」两类记录也立起来。
