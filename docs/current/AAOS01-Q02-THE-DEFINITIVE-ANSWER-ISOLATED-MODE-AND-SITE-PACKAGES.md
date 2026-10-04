# 🎯 AAOS-01 Q02：**完全确定性的答案 —— 三条硬证据**

## 1. 三条实测证据

```
=== 随包 runtime 的 site-packages 里有没有这些包？ ===
  missing   app
  missing   archeaxis
  missing   shared

=== sys.path（cwd 是一个【含有 app 的】目录） ===
  加 -I:    ['...\python312.zip', '...\DLLs', '...\Lib', '...\python']   // 没有 cwd
  不加 -I:  同上

=== 能否导入 app？ ===
  加 -I:    ModuleNotFoundError: No module named 'app'      // 失败
  不加 -I:  IMPORT_OK                                        // 【成功】
```

**第二、三条是关键对照**：**同一个 cwd、同一个解释器，只差一个 `-I`** ——
**去掉 `-I` 就能导入成功**。这就把原因钉死在隔离模式上，而不是我的目录摆法。

## 2. 机制（现在没有任何推断成分）

```
启动用 -I（隔离模式）
  → cwd 不进 sys.path（-I 隐含 -P）
  → PYTHONPATH 被显式移除（backend.rs:22, 295-297）
  → 无 user site（PYTHONNOUSERSITE=1，backend.rs:310）
     → 唯一可导入处：runtime 自己的 Lib / Lib\site-packages
        → 而 app / archeaxis / shared 并未安装在那里
           → ModuleNotFoundError: No module named 'app'
```

**与第 94 轮应用自己给出的错误原文逐字一致。**

## 3. 所以修法**没有歧义**（我第 95 轮以为需要你裁定，现在不需要了）

第 95 轮我写：「有两条路（把 `app/` 送到 `cwd`，或让 `cwd` 指向有 `app/` 的地方）」。

**本轮实测证明第一条路是错的** —— 因为 `-I` 下 **cwd 根本不算数**。

| 做法 | 是否可行 | 依据 |
| --- | --- | --- |
| 把 `app/` 放到 cwd | ❌ **无效** | 我建了 junction 到 cwd，`-I` 下**仍然失败** |
| **把包装进 runtime 的 `Lib\site-packages`** | ✅ **这才是 `-I` 下唯一可行处** | `sys.path` 只含 runtime 自身目录 |

**即：`-I` 的语义决定了「可导入的东西必须是被**安装**进 runtime 的」** ——
**这不是设计口味问题，是 CPython 的行为。**

## 4. 这解释了此前几件事

| 现象 | 解释 |
| --- | --- |
| 老 Green 候选能跑 | 它是 `core/`（**编译好的** `archeaxis-api.exe`）+ `workers/` + `runtime/` 的**已安装布局**，不依赖 `-m app.*` |
| Q14 验证器断言「installed desktop backend did not become ready」 | **真实安装态里包是装进 runtime 的**，所以后端能就绪 |
| 我的临时构建目录失败 | 我只 stage 了**裸 Python 发行版**，**没有把 `app` 等包装进去** |

## 5. 我**不**声称的

| 不声称 | 原因 |
| --- | --- |
| 「把包装进 site-packages 后 Core 一定能就绪」 | **未验证** —— 还有 worker-profile、迁移、readiness 等条件 |
| 「产品有缺陷」 | **没有** —— 代码假设的是标准安装布局，**是我的构建布局不完整** |

## 6. 本轮改了什么（说清楚）

| 改动 | 位置 | 性质 |
| --- | --- | --- |
| 在 `.project-local/runs/cwd-with-app/` 下建了 6 个 **junction** 指向仓库包 | **项目自有开发输出目录** | **只读指向，未复制、未改仓库文件** |

**没有改任何仓库文件。**

## 7. 本轮未做

1. **未**把包装进 runtime（那会改我的构建产物 —— 下一轮，且会先说明范围）；
2. **未**触碰官方 Green 的 `data/` 与资料库；
3. **未**删除仓库内的任何东西。
