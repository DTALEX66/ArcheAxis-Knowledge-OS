# AAOS-01：**`reject_reparse` 确认了 —— 并守着项目自己的边界**

## 1. 实现全文（`scripts/release/stage_backend_runtime.py:108-123`）

```python
108: def reject_reparse(path: Path) -> None:
109:     """A staged runtime must not follow a link out of its own tree."""
110:     raw = str(path).replace("\\", "/").lower()
111:     if raw.startswith(("e:", "//")) or ".." in raw.split("/"):
112:         raise ValueError("unsafe staging path")
113:     path = Path(os.path.abspath(path))
114:     full = str(path).replace("\\", "/").lower()
115:     if full.startswith(("e:", "//")) or any(part in PRIVATE_NAMES or part.startswith(".env")
116:             for part in full.split("/")) or "/.project-local/agents/" in full:
117:         raise ValueError("protected staging path")
118:     for part in (*reversed(path.parents), path):
119:         try:
120:             info = part.lstat()
121:         except (FileNotFoundError, NotADirectoryError):
122:             continue
123:         if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
124:             raise ValueError("linked staging path rejected")
```

## 2. 它检查**每一级祖先**，判定两种链接

| 判定 | 依据 |
| --- | --- |
| 符号链接 | `stat.S_ISLNK(info.st_mode)` |
| **junction / reparse point** | **`st_file_attributes & 0x400`** —— **`0x400` 就是 `FILE_ATTRIBUTE_REPARSE_POINT`** |

**而且 `for part in (*reversed(path.parents), path)` —— 它沿**每一级祖先**检查** ✓，
**不是只看终点。** 所以哪怕链接在很上层也会被发现 ✓

**我的 junction staging 因此不只是「不会被打包」——**
**它连作为分发输入都会被这个函数拒绝。**

## 3. 它还守着项目文档里那条边界

同一函数顺带禁止：

| 禁止 | 与项目规则的关系 |
| --- | --- |
| `e:` 开头 | **与 `AGENTS.md`「不得访问 `E:\`」完全一致** ✓ |
| `//`（UNC 路径） | 阻止把暂存指向网络位置 |
| `..` 路径穿越 | 阻止暂存逃出自身树 |
| `PRIVATE_NAMES` / `.env*` | **阻止把私密配置带进分发包** |
| `/.project-local/agents/` | **阻止把 agent 私有状态带进分发包** |

**函数注释一句话概括了设计意图**：

> **"A staged runtime must not follow a link out of its own tree."**

**即：分发产物必须自包含，不能依赖树外的链接。** —— **这与我用 junction 的做法正好相反。**

## 4. 这条线索的**完整结论**

```
第 79 轮：我找「能力↔路由」的映射，没找到 -> 结论：缺一张表
第 123 轮：我的安装工件里没有仓库包 -> 我克制，不下结论
第 128 轮：找到 stage_backend_runtime.py
   -> 正式分发用【复制】而非链接（reject_reparse 强制）
   -> 依赖按【已批准列表】逐个复制，不是我那样 pip install
   -> 并在分发时生成 worker-profile.json（含 declared_routes）
   -> 所以第 79 轮那张「表」是【分发产物】，不是仓库里该有的文件
```

**第 123 轮那次克制是对的；本轮给出了它的确切答案。**

## 5. 我**不**声称的

| 不声称 | 原因 |
| --- | --- |
| 「用这个脚本 stage 后安装必成功」 | **还没做，更没安装** |
| 「`declared_routes` 就是 atlas 的正式对应」 | **我未把两者对照** |

## 6. 本轮改了什么（说清楚）

**无。** 本轮**全程只读**（grep + 读文件）。
**未改任何仓库文件**；**未执行任何安装**；**未触碰官方 Green 的 `data/` 与资料库**；**未删除任何文件**。
