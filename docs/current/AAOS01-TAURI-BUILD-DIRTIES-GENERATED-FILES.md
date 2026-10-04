# AAOS-01 Q02 附带发现：**构建 Tauri 宿主会改脏 4 个生成文件，并让它们违反约定门禁**

## 1. 现象

我跑了一次 `cargo check --manifest-path src-tauri/Cargo.toml`，之后工作树多出 4 个改动：

```
 M src-tauri/gen/schemas/acl-manifests.json
 M src-tauri/gen/schemas/capabilities.json
 M src-tauri/gen/schemas/desktop-schema.json
 M src-tauri/gen/schemas/windows-schema.json
```

## 2. 改动其实只是**丢了文件末尾换行**

```diff
--- a/src-tauri/gen/schemas/capabilities.json
+++ b/src-tauri/gen/schemas/capabilities.json
@@ -1 +1 @@
-{}
+{}
\ No newline at end of file
```

四个文件**都只是** `-{}
` 变成 `+{}`（无末尾换行）。

## 3. 为什么这件事重要

`scripts/check_repository_conventions.py` 的 `missing-final-newline` 规则**正是查这个**。
所以：

**只要有人构建一次 Tauri 宿主，工作树就会出现 4 个会门禁失败的文件改动。**

这意味着 **「构建宿主」与「约定门禁」之间有一个未处理的冲突** —— 不是谁的错，而是**工具产出的规范化与仓库约定不一致**。

## 4. 本轮的处理：**还原，不提交**

```
git checkout -- src-tauri/gen/schemas/
```

理由：
1. 它们是**生成产物**，提交生成物的抖动是噪声；
2. 提交无末尾换行的版本会**让门禁失败**；
3. 我的改动（加 `[workspace]`）**语义上不该改变这些 schema**。

## 5. 留给下一轮的处置选项（**未裁决**）

| 选项 | 说明 |
| --- | --- |
| A | 构建后**自动还原**这些生成文件（放进开发脚本） |
| B | 让 `tauri-build` 产出带末尾换行（可能需要版本/配置调整） |
| C | 把 `src-tauri/gen/` 纳入生成物豁免 |

**我没有选任何一个** —— 这需要与仓库既有约定所有者确认，**不是我在这一轮能单方面决定的**。

## 6. 本轮**未**做

1. **改接仍未做**（宿主构建还缺 staged runtime）；
2. **未**选 §5 的方案；
3. 官方 Green 与官方资料库**零触碰**。
