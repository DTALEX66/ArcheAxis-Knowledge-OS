# ⚠️ AAOS-01：**我两轮的结论都被推翻 —— 并暴露出一个贯穿四轮的未验证假设**

## 1. 本轮实测

### (a) 我先补上第 124 轮留的那个问题

```python
58:  def workspaces_base() -> Path:
59:      """Data-root-relative parent directory holding all workspaces."""
60:      policy = resolve_paths(resolve_runtime_mode())
61:      return policy.data_root / "workspaces"
```

**是 `<数据根>/workspaces`，不是 `<数据根>/data/`。**

### (b) `POST /api/v1/setup/preflight` 实测

```json
"preflight": [200, "{\"ready\":true,\"mode\":\"quick\",\"domains\":{
  \"source_archive\":      \"...\\workspaces\\workspace\\source_archive\",
  \"evidence_ledger\":     \"...\\workspaces\\workspace\\evidence_ledger\",
  \"human_learning_vault\":\"...\\workspaces\\workspace\\human_learning_vault\",
  \"ai_asset_vault\":      \"...\\workspaces\\workspace\\ai_asset_vault\"}}"]
```

### (c) `GET /api/v1/setup/status` 实测

```json
{"schema_version":"v1","ready":false,"workspace_id":null,
 "workspace_root":"...\\workspaces\\workspace","legacy_db_present":false,
 "steps":[{"id":"workspace_exists","state":"pending",
           "message":"workspace has not been created yet",
           "action_hint":"POST /api/v1/setup/initialize creates the workspace"}, …]}
```

**产品明确说「工作区尚未创建」并给出补救路由** ✓ —— **与第 124 轮读到的源码一致** ✓

### (d) preflight **确实创建了目录**

```
"dirs_created": ["backups", "capabilities", "capabilities\disabled",
                 "capabilities\installed", "capabilities\packages",
                 "capabilities\plugins", "capabilities\quarantine",
                 "capabilities\registry", "capabilities\staging",
                 "output", "reports", "workspaces"]
```

**`_paths_writable_step` 的 `base.mkdir(parents=True, exist_ok=True)` 真的执行了** ✓

### (e) ⚠️ 但 `data/` 依然不存在

```json
"data_subdir_present_at_start": false
"data_subdir_now": false
```

**`workspaces` ≠ `data`。** **setup 流程创建的是 `workspaces`，不是 `data/`。**

## 2. 🎯 更要命的一点：`ARCHEAXIS_DB_PATH` **不是**按相对路径解析的

启动器设的是 `ARCHEAXIS_DB_PATH=data/archeaxis.sqlite`；
**而我实测到的数据库文件落在**数据根**：

```
"files_created": ["archeaxis.sqlite",          // ← 在数据根，不在 data/ 里
                  ".archeaxis.sqlite.runtime.lock",
                  "backups\pre_migration_..._.sqlite", …]
```

**如果那个值真的被当作相对路径，文件应该在 `<数据根>/data/archeaxis.sqlite`。**
**它不在。** **所以那个值由应用自己的路径逻辑解析，不是操作系统相对路径。**

## 3. ⚠️ 因此我要同时更正**两轮**的结论

| 轮次 | 我写的 | 现评价 |
| --- | --- | --- |
| **123** | 「这是一条从安装态到启动态的**真实缺口**」 | ❌ **未证实** —— 我基于「相对路径需要 `data/`」这个假设 |
| **124** | 「**不是缺口** —— setup 会创建它」 | ❌ **也不对** —— setup 创建的是 `workspaces`，**不是 `data/`** |
| **125（本轮）** | **`data/` 从未被创建；而数据库落在数据根** | ✅ **实测** |

**两轮都错了，方向相反。** 根因是同一个：

> **我从第 100 轮起就假设「`data/archeaxis.sqlite` 会被当作相对路径解析」，
> 而我**从未验证**这一点。**
> 第 123 轮拿它推出「缺口」，第 124 轮又拿它推出「setup 补上了缺口」。
> **同一个未验证的假设，支撑了两个相反的结论。**

## 4. 现在**真正**确证的只有这些

| 事实 | 依据 |
| --- | --- |
| `data/` 在 preflight 与 migrate 之后仍不存在 | 本轮实测（前后都为 false） |
| **数据库落在数据根**，不在 `data/` 里 | 本轮实测的文件列表 |
| setup 创建 `workspaces` 及其它目录（`backups`/`capabilities`/`output`/`reports`） | 本轮实测 |
| `workspaces_base()` = `<数据根>/workspaces` | 源码 + 实测路径一致 |
| 产品会报告 `workspace_exists: pending` 并给出补救路由 | 本轮实测 |

**而「`data/` 该不该存在」「谁该建它」这两个问题，我给不出可靠答案** ——
**因为我还不知道那个 DB 路径值到底怎么被解释。**

## 5. 下一轮该做什么（具体）

**只读地找 `ARCHEAXIS_DB_PATH` 的读取处**，看它究竟如何解析成路径 ——
**先弄清楚这一点，才谈得上判断「缺口」是否存在。**

## 6. 我**不**声称的

| 不声称 | 原因 |
| --- | --- |
| 「这是缺口」 | **第 123 轮那么说过，现在收回** |
| 「这不是缺口」 | **第 124 轮那么说过，现在也收回** |
| 「`data/` 应该存在」 | **我不知道那个环境变量的语义** |

## 7. 本轮改了什么（说清楚）

| 改动 | 位置 | 性质 |
| --- | --- | --- |
| 建 scratch 数据根、跑 migrate + core、调 `/setup/preflight` 与 `/setup/status` | `.project-local/runs/setup-preflight/` | **项目自有开发输出** |

**未改任何仓库文件**；**未执行任何安装**；**未触碰官方 Green 的 `data/` 与资料库**；
**未删除任何东西**；只 kill 自己起的句柄。
