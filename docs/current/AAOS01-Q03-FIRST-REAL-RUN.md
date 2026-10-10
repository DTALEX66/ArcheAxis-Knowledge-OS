# AAOS-01 Q03 首次**实际运行**：两个真实观察，其中一个**限定我第 18 轮的结论**

## 1. 实际运行（对着数据库的**临时副本**，绝不碰正式数据）

启动 `uvicorn app.main:app`（端口随机、`ARCHEAXIS_DB_PATH` 指向临时副本），结果**启动即被拒绝**：

```
RuntimeError: SQLite schema has not been migrated:
  D:\All projects\...\.project-local\runs\handshake-probe\archeaxis.sqlite
  shared/storage.py:430  validate_schema
  shared/runtime_guard.py:18  core_runtime_guard
  app/main.py:39  core_runtime_lifespan
```

**这是好设计**：应用在 schema 未迁移时**失败即关闭**（fail-closed），不会在半成品库上跑起来。

## 2. **真正重要的发现**：工作树里根本没有 `archeaxis.sqlite`

```
data/ 目录内容：
  cognitive_os.sqlite   3223552 bytes      <- 唯一的数据文件
```

而配置说的是：

```yaml
# config/defaults.yaml:11
  path: "data/archeaxis.sqlite"
```

## 3. 这**限定**了我第 18 轮的结论（必须说清楚）

第 18 轮我写"三处指向同一个 `data/archeaxis.sqlite`"，并列了 config、宿主 env、Python 解析三处。

**那个结论对的是"配置"层面**——三处**配置值**确实一致。**但我没有核实那个文件是不是真正装着数据的那一个。**

| 我第 18 轮说的 | 实际情况 |
| --- | --- |
| 三处**配置**指向 `data/archeaxis.sqlite` | ✅ 成立 |
| （我隐含暗示的）**数据就在那个文件里** | ❌ **工作树里没有这个文件；有的是 `cognitive_os.sqlite`** |

**所以"同一个库文件"这个结论要降级为**：
> **配置层同值；但工作树中实际存在的数据文件是 `cognitive_os.sqlite`，其与 `archeaxis.sqlite` 的关系（是否同一套数据的旧名/迁移前身）我尚未查。**

**又一次是"读了源码就下结论"的代价** —— 而这次我是在**实际运行**时发现的，正说明第 21 轮这个动作选对了。

## 4. 顺带定位到的迁移入口

```
app/workspace/migrate.py:497                    def migrate(
shared/migration.py:449                        def migrate(
shared/workspace_migration.py:267              def migrate(
shared/knowledge_governance_migration.py:612   def migrate(
shared/research_migration.py:314               def migrate(
shared/sleep_loop_migration.py:394             def migrate(
```

**多个迁移入口** —— 哪一个（或哪几个、以什么顺序）构成"把一个库迁到可用"的完整路径，**本轮未查**。

## 5. 下一轮

1. **查明 `cognitive_os.sqlite` 与 `archeaxis.sqlite` 的关系**（谁读谁、谁是 canonical、是否同一套数据）；
2. 用**临时副本**跑一次迁移，把库迁到可用，然后**真正调用一次** `/api/v1/system/handshake`。

## 6. 本轮**未**做

1. **未成功调用**握手 —— 被 schema 守门挡住，**如实记录，不谎报"已跑通"**；
2. **未跑迁移**（未查明入口顺序）；
3. **未碰正式数据**：全程只操作 `.project-local/runs/` 下的临时副本；
4. 官方 Green 与官方资料库**零触碰**。
