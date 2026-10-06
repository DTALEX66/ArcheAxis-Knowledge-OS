# 🎯 AAOS-01 Q02/Q03：**实测到真正的写权限强制**

## 1. 三次写入，全部 403

```json
"compliant_write":       {"status": 403, "body": "{\"detail\":\"desktop write authorization rejected\"}"}
"forbidden_assertion":   {"status": 403, "body": "{\"detail\":\"desktop write authorization rejected\"}"}
"empty_idempotency_key": {"status": 403, "body": "{\"detail\":\"desktop write authorization rejected\"}"}
"names_offending_field": false
```

| 测试 | 意图 | 结果 |
| --- | --- | --- |
| ① 合规写入（只有意图字段） | 期望 200 | **403** |
| ② 越权断言 `human` + `evidence_verified` | 期望 400 且指名 | **403** |
| ③ 空 `idempotency_key` | 期望 400 | **403** |

## 2. 两个结论

### (a) ✅ 写权限门禁**真的在生效**

```
{"detail": "desktop write authorization rejected"}
```

**这是我这个会话里第一次实测到真正的授权行为** —— 不是源码上的 `Depends(...)`，
**而是活的拒绝响应。**

### (b) ✅ 它**作为依赖先于处理器体执行**

三次全部返回同一个 403 —— **包括那个带越权字段的**。

**而处理器体里的真值检查（`forbidden` → 400）从未触发**（`names_offending_field: false`）✓

**这说明**：`dependencies=[Depends(_require_desktop_write_request)]` **在函数体之前运行** ——
**权限不足时，连业务校验都不会发生** ✓

## 3. `workspace:write` **不够** —— 这指向真正的授权来源

我的启动器环境设了：

```
ARCHEAXIS_DESKTOP_WRITE_SCOPES=workspace:write
ARCHEAXIS_DESKTOP_CONTROL=stdio-v1
ARCHEAXIS_DESKTOP_LAUNCH_TOKEN=<64 位十六进制>
```

**但仍然 403。** 结合第 101 轮的观察：

```
PermissionError: [Errno 1] PeekNamedPipe failed for desktop parent pipe
```

**推断**：写入授权需要**真正的桌面父进程管道握手** ——
而我是**独立启动**的，那条管道不存在 ✓

**即：写操作被绑定在「宿主确实在管着这个进程」这个事实上。**

## 4. 因此读写闭环的**正确测法**变了

| 测法 | 可行性 |
| --- | --- |
| ❌ 独立启动 Core 后直接写 | **行不通** —— 403，授权需要宿主管道 |
| ✅ **通过宿主写** | **这才是真实路径** —— 宿主会建立那条管道 |

**所以我应当回到宿主那条路**（第 102 轮已跑通宿主启动 Core），
**在宿主运行期间发起写入** —— 那才是「读写闭环」的真实形态。

## 5. 我**不**声称的

| 不声称 | 原因 |
| --- | --- |
| 「通过宿主写就一定能成功」 | **未验证** —— 授权可能还有别的条件 |
| 「403 的原因**一定**是缺管道」 | **那是推断** —— 我只知道 `workspace:write` 不足 |
| 「真值检查不存在」 | **存在**（源码里读过），**只是本轮没走到** |

## 6. 本轮改了什么（说清楚）

| 改动 | 位置 | 性质 |
| --- | --- | --- |
| 建 scratch 数据根、跑 migrate + core、尝试三次写入（均被拒） | `.project-local/runs/write-tests/` | **项目自有开发输出** |

**未改任何仓库文件**；**未触碰官方 Green 的 `data/` 与资料库**；
**未修改真实产品数据目录**；**未删除任何东西**；只 kill 自己起的句柄。
