# 🎯 AAOS-01：**`data/` 那条线结案 —— 从来没有缺口**

## 1. 决定性的一段（`shared/config.py:253-282`）

```python
253: def resolve_runtime_path(value: str | Path) -> Path:
254:     """Resolve paths without falling back to an uncontrolled user-home directory.
256:     Canonical root: ``ARCHEAXIS_DATA_DIR`` (wins when set).
259:     Default: project root (source checkouts)."""
261:     candidate = Path(value).expanduser()
262:     if candidate.is_absolute():
263:         return candidate
264:     configured_root = os.getenv("ARCHEAXIS_DATA_DIR", "").strip()
269:     if configured_root:
270:         base = Path(configured_root).expanduser()
271:         parts = (
272:             candidate.parts[1:]                        // ★ 丢掉第一段
273:             if candidate.parts and candidate.parts[0] in {"data", "config"}
274:             else candidate.parts
275:         )
276:         return base.joinpath(*parts)
```

## 2. 🎯 所以 `data/archeaxis.sqlite` 的真实去处

```
ARCHEAXIS_DB_PATH = "data/archeaxis.sqlite"
  -> 相对路径
  -> 第一段是 "data"  -> 【被丢掉】
  -> 其余 "archeaxis.sqlite" 拼到 ARCHEAXIS_DATA_DIR
  -> 结果 = <ARCHEAXIS_DATA_DIR>/archeaxis.sqlite
```

**这与第 125 轮实测完全一致** —— 数据库就在**数据根**，不在 `data/` 里 ✓

## 3. 为什么这么设计（这才是关键）

函数的第一句话就是答案：

> **"Resolve paths without falling back to an uncontrolled user-home directory."**

**丢掉 `data` / `config` 这一段，是为了让配置值**无法逃出**所配置的数据根。**

| 若不做这一步 | 若做了这一步 |
| --- | --- |
| 相对路径会相对**进程 cwd** 解析 | **相对配置好的数据根**解析 |
| cwd 是可控/可变的 → 可能写到意外位置 | **路径被钉在数据根内** |

**这是一条安全属性，不是巧合。** **`data/` 是**虚拟根标记**，不是目录。**

## 4. 🎯 所以整条线**结案**：从来没有缺口

| 轮次 | 我写的 | 现评价 |
| --- | --- | --- |
| 100 | 「相对路径需要 `<数据根>/data/`」 | ❌ **前提就是错的** |
| **102** | 「把数据根指到含 `data/` 的目录」让它工作 | ❌ **也错了** —— 真正让它工作的是第 97/98 轮装的包与依赖，**`data/` 只是恰好也在** |
| 123 | 「这是真实缺口」 | ❌ **错** |
| 124 | 「不是缺口，setup 会建它」 | ❌ **结论对、理由错** —— **没有缺口，但不是因为 setup 建 `data/`，而是因为 `data/` 从来不需要存在** |
| 125 | 「假设未验证，我撤回两轮结论」 | ✅ **对** —— **而本轮把它验证了** |
| **126（本轮）** | **`data` 前缀被设计性地丢弃；无需 `data/`；无缺口** | ✅ **源码 + 实测一致** |

**四轮里我错了三次、方向各不相同。** 共同根因：

> **我一直在用「操作系统会按相对路径解析」这个心智模型去套它，
> 而它其实是**应用自己的配置路径解析器**，且带有一条安全规则。**
**我没有先读解析器，就先按常识推断 —— 这是我该改的地方。**

## 5. 一个实际影响

**没有任何地方需要创建 `data/`** ✓ —— 安装器不建它是对的 ✓，
**而我第 102 轮为了让宿主跑通去建它，是**不必要的**（虽然无害）。**

**让宿主真正跑通的是第 97 轮（包进 `site-packages`）与第 98 轮（装依赖）。**

## 6. 我**不**声称的

| 不声称 | 原因 |
| --- | --- |
| 「配置里其它路径也都不需要存在的目录」 | **只验证了 `data/` 这一条** |
| 「`config` 前缀行为也一样」 | **源码如此，但我没实测** |

## 7. 本轮改了什么（说清楚）

**无。** 本轮**全程只读**（grep + 读一个文件）。
**未改任何仓库文件**；**未执行任何安装**；**未触碰官方 Green 的 `data/` 与资料库**；**未删除任何文件**。
