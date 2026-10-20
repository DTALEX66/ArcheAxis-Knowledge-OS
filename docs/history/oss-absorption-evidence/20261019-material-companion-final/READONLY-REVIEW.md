# 后续切片只读评审路由（2026-10-19）

本文件保存本轮并行只读评审的代码落点与风险，不是产品实现、验收或新的任务授权。当前写者仍为主 Agent，实际进度回到原 UI 执行记录。

## BE10 有限只读接入

- `crates/archeaxis-api/src/launch.rs` 当前 human/machine 认证及 actor 覆盖不能等同 Observer。v2 bootstrap 的 actor 集合封闭；新角色需要按兼容政策选择新主版本，保留旧 v2。
- 观察者必须使用独立凭证和有限路由白名单，不能复用 human token。其他 GET 也不得自动开放，例如 `/system/version` 包含工作区数据库定位，UI state 可含草稿。
- `packages/contracts/v2/ui-host.schema.json` 的三项 project operation 尚无完整输入合同；应冻结 namespace/type/workspace/restore epoch/document/version/hash/freshness 等引用身份，不隐式追随最新版本。
- 沿现有 schema、`scripts/contracts/generate_ui_host.py`、Rust/TS 桥接和真实 consumer 接入，不再建注册器。现有 page19 是配置 consumer，不能冒称项目对象接入已实现。
- 需真实二进制认证边界、全部写入／执行／恢复拒绝、角色伪造、协议不兼容、未知 namespace、过期引用、两个隔离工作区与真实 consumer 验证。WORK-LAB／DESIGN-LAB 外部宿主仍 UNVERIFIED。

## 复习标题

- API 入口在 `crates/archeaxis-api/src/lib.rs`，领域来源在 `crates/archeaxis-domain/src/learning.rs`，不是不存在的 runtime/learning.rs。
- 保留 item key 身份。可加只读标题投影：合法 course/artifact 需验证所属课程；使用课程／学习内容的简短中文展示标题，缺失时中立回退，不把内部长键当主标题。数据库错误不得伪装为空。
- 同步 `packages/contracts/v1/core-document.schema.json`、生成器及生成 TS，检查学习页、工作台、教学页与 breadcrumb 调用方；不新增迁移或事件。
- 验证同名对象身份不混、陈旧或畸形引用、CRLF／Unicode／长度边界、数据库失败与原状态不变；真实 Core 及前端定向回归分开。

## 本轮探针修复限制

有界等待＋只读重新命中能解决临时布局变化；不证明页面没有溢出，永久不可达仍应失败。可在后续按实证需要观察连续稳定帧。当前相同回答的单请求夹具不代表多请求同文案均已身份绑定；启动前调用计数继续 UNVERIFIED。
