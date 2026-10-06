# AAOS-01：**我把 `worker profile file missing` 读过头了 —— 更正**

## 1. 我上一段写的（错的）

> 「**`open_routes` 不满足于启动文档里的 `text_worker` 块 —— 它要一个 `worker-profile.json` 文件。**
> **这正是第 131 轮的那个结论**（profile 是分发产物）。」

**这是过度解读。** 我读源码之后发现：

```rust
// crates/archeaxis-api/src/launch.rs
129:     pub fn validate(&self) -> Result<(), &'static str> {
130:         for path in [&self.python, &self.script, &self.staging] {
131:             Self::validate_path(path)?;
132:         }
133:         if !self.python.is_file() || !self.script.is_file() {
134:             return Err("worker profile file missing");        // ★ 就是这个
135:         }
```

**这条错误的真实含义是**：**`text_worker` 块里写的 `python` 或 `script` **那两个文件**不存在** ✓
**不是**「缺少一个名为 `worker-profile.json` 的文件」。**

**而我的探针里 `worker_script_exists` 恰恰是 `false`** ✓ ——
**所以它说的是**我把脚本路径写错了**。**

## 2. 我为什么会读过头

| 我看到的 | 我推断的 | 实际 |
| --- | --- | --- |
| 错误文本含 **"profile file"** | 「缺一个 profile 文件」 | **它指的是 `text_worker` 里那两个文件** |
| 第 131 轮已知 `worker-profile.json` 是分发产物 | 顺手把它套了上去 | **套错了** |

**教训**：**错误文本里的名词不一定是新概念** ——
**「profile file」在这里指的是**文档里已经写明的路径字段**，而不是又一个文件。**
**而我当时手里就有 `worker_script_exists: false` 这个反证，却没有用它。**

## 3. ✅ 但本轮的主结论不受影响

| 结论 | 依据 |
| --- | --- |
| **挂载条件在当前构建上成立** | 「无 worker」分支：`capabilities` 404 · `machine_answers` 404 · `evidence_anchors` **200** —— **与源码预测逐条一致** |
| **版本警示已解除** | 二进制**就是从当前源码构建的**（52.35s） |

**这两条是本轮真正的成果，它们不依赖我对那句错误文本的解读。**

## 4. 顺带读到的两处**安全/卫生校验**（值得记）

```rust
120:         let mut part = std::path::PathBuf::new();
121:         for component in path.components() {
122:             part.push(component);
123:             archeaxis_store_sqlite::raw_objects::reject_links(&part)
124:                 .map_err(|_| "invalid worker profile path")?;
125:         }
```
**`validate_path` 沿**每一段路径**拒绝链接** —— 与 `stage_backend_runtime.py` 的 `reject_reparse` **同一原则** ✓

```rust
136:         for route in &self.routes {
139:             let capability = route.capability.trim();
140:             if capability.is_empty() {
141:                 return Err("worker route capability must not be empty");
142:             }
143:             if capability == "text.extract" {
```
**注释写明了理由**：

> **"An empty or duplicated capability would silently shadow a route rather than fail,
> so it is refused here instead."**

**即：宁可在这里拒绝，也不让一个空的或重复的能力名**悄悄遮蔽**一条路由。** ✓

## 5. 下一轮（具体）

```
1. 只读地在仓库里找出真实的 worker 脚本路径（我上次猜的那个不存在）
2. 用它填 text_worker.script（连同真实的 python 路径与一个 staging 目录）
3. 用【本轮这个当前构建】再跑一次
   -> capabilities 应当从 404 变成 200/405
```

**那才是挂载条件的闭环实证：同一二进制、两份启动输入、两种路由集。**

## 6. 我**不**声称的

| 不声称 | 原因 |
| --- | --- |
| 「缺一个 profile 文件」 | **已更正 —— 不是这个意思** |
| 「补上脚本路径后一定能挂载」 | **未试** |

## 7. 本轮改了什么（说清楚）

**无。** 本轮**全程只读**（grep + 读文件）。
**未改任何仓库文件**；**Green 目录内未创建/修改/删除任何文件**；**未触碰官方 Green 的 `data/` 与资料库**。
