# GF01 人物与关系档案（小栖学习伴侣 v1）

分支 `feat/astryn-learning-companion-v1` · 任务包 ASTRYN-COMPANION-20261013 · 日期 2026-10-13

## 交付内容

| 交付物 | 位置 | 说明 |
| --- | --- | --- |
| 档案 schema v2 | `contracts/character.ts` | `schemaVersion:2` + `profileRevision`；人格（persona）/ 主动程度 / 学习偏好 / 声音连接从表达风格中拆出；`ASTRYN_COMPANION_PERSONAS` 三种人格（学习伴侣默认；女友语气 `optIn:true`，必须本人显式选择）；`migrateCharacterProfile()` 迁移与回退（`MIGRATED_V1_TO_V2` / `EMPTY_DEFAULT` / `INVALID_FALLBACK`） |
| 人格提示组装 | `src/companion/prompt-composer.ts` | 模板 v2（`xiaoqi-system-2`）：identity / persona / boundaries / continuity / style / initiative / learning / authority / style-scope 九节；**不变量**：boundaries、continuity、authority、style-scope 四节不随人格与设置变化 |
| 档案存储端口 | `src/companion/profile-store.ts` | `createEphemeralProfileStore()`（进程内，刷新即失）+ `createHostProfileStore()`（宿主未接通：读取回退默认并标注 `HOST_UNAVAILABLE_DEFAULT`，保存显式失败 `BLOCKED_BY_HOST_CONTRACT`，指认 BE06 + BE01）；乐观并发：陈旧 `expectedRevision` 保存被拒 `REVISION_CONFLICT` 且不写坏已存档案 |
| 配置视图 | `src/presentation/companion-settings.tsx` + `astryn.css` | 身份 / 关系风格 / 表达 / 主动程度 / 学习偏好 / 外观 / 声音七个分组；女友语气选中后出现"本人选择"提示；声音启用在接通前保持禁用 |
| 会话连续性 | `src/interaction/companion-controller.ts` | 新增 `setProfile()`：改档案不重建控制器（守卫状态、历史、在途请求保留），新档案只作用于下一轮提示 |
| 宿主接线 | `src/presentation/companion-shell.tsx`、`dev-host/app.tsx`、`src/index.ts` | 控制器 identity 只跟会话与端口；`profileStore` 可选注入；开发宿主用进程内回退存储并在边界声明中标注"保存会显式失败" |

## 证据（本机实测）

### 门禁

- 命令：`bash .project-local/runs/gate-chain.sh`，日志 `.project-local/runs/gate-20261013-220559.log`
- 阶段：`STAGE=lint EXIT=0`、`typecheck EXIT=0`、`test EXIT=0`、`build EXIT=0`、`record EXIT=0`、`anchors EXIT=0`
- 回执：`docs/verification/gates.json`，69 个源文件，树哈希 `6b299213d57459bd…`，全绿=true（在 `PROJECT_CONTRACT.yaml` 更新后重封存；早一次 220414 记录为 `bca833f9…`）
- 测试：17 个文件 136 通过（GF00 基线为 14 文件 118 通过）；新增 `tests/companion/character-profile.test.ts`、`tests/companion/profile-store.test.ts`、`tests/presentation/companion-settings.test.tsx`，并在 `tests/interaction/controller.test.ts` 增加 `setProfile` 连续性用例

### 浏览器实测（开发宿主，非合成替代）

- `npm run dev` → `http://127.0.0.1:5183/`；面板工具栏出现"设置"按钮，打开后渲染七个分组
- 实测字符串：保存去向显示 `进程内（开发回退）· EPHEMERAL_DEV_MEMORY（进程内，刷新即失，仅开发宿主）`；选择女友语气后出现"女友语气正在启用：这是你本人的选择…"；点击保存后提示 `已保存（修订 1）→ 进程内（开发回退）…`，档案版本显示 `档案版本 v2 · 修订 1`
- 控制台消息仅 vite 连接与 React DevTools 提示，0 条错误

### 边界核对

- `tests/boundary/no-sensitive-apis.test.ts` 全绿：档案存储不落浏览器本地持久化、不落文件（进程内内存），档案序列化不含采集/存储接口痕迹
- 开发宿主边界声明新增："小栖档案在开发宿主里只存进程内（刷新即失）；正式保存归宿主（character.profile.write，BE06 未接通，保存会显式失败）"

## 阻塞与残余

- **宿主档案持久化 BLOCKED_BY_HOST_CONTRACT**：`character.profile.read/write` 属 BE06，且合同本体 `PROPOSED_REQUIRES_BE01_FORMAL_ADMISSION`（合同所有者 AX-HOST-20261013/BE01）。ASTRYN 侧不冒充成功，保存一律显式失败。
- 外观 `theme` 字段保留在 schema 中但设置视图暂不提供切换：当前渲染器只有一个配色，暴露无效控件属装饰性欺骗（GF03 提供第二配色后再开放）。
- 声音组仅展示未接通状态，不播放任何语音或占位音效（GF09 预留）。

## 门禁工具修正（如实记录）

GF00 的核对回执 `docs/companion/source-ports-readback.json`（含 8 个 git blob sha1）在 GF00 提交后才进入被扫描集合，本次锚点校验首次扫到它们并按"必须为提交"误报 16 条。修正：`verify-doc-anchors.mjs` 对 40 位十六进制串按对象类型判定——commit 必须在本仓库 log（过期指针照旧拦截），blob 必须是本仓库真实对象（伪造仍拦截）。修正后 `anchors EXIT=0`。

## 回滚

本任务线性提交于 `feat/astryn-learning-companion-v1`（GF00 之后）；回滚 = `git revert` 本提交。未改写已推送历史。
