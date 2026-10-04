# AAOS-01 Q02：**错误前移了 —— 修法生效，并暴露下一个缺失**

## 1. 我做的改动

按第 96 轮的结论，把仓库包**装进构建产物的 site-packages**（用 junction，不复制）：

```
C:\Windows\Temp\aaos-target\release\runtime\python\Lib\site-packages\
  app  archeaxis  config  inspiration_research  knowledge_base  shared   (全部 junction)
```

**验证（用启动器自己的 `-B -I`，且在中立 cwd 下）**：

```
APP_IMPORT_OK
SIBLINGS_IMPORT_OK
```

## 2. 🎯 结果：应用诊断里的错误**变了**

**改之前**（第 94 轮）：

```
Error while finding module specification for 'app.runtime_entrypoint'
(ModuleNotFoundError: No module named 'app')
```

**改之后**（本轮）：

```
desktop migration failed with exit code: 1
[migration:stderr] Traceback (most recent call last):
[migration:stderr]   File [redacted] line [redacted] in _load_yaml
[migration:stderr]     import yaml
[migration:stderr] ModuleNotFoundError: No module named 'yaml'
```

> **`No module named 'app'` 消失了。修法生效。**
> **迁移前进到下一个缺失：第三方依赖 `yaml`。**

## 3. 所以真正的模式清楚了

**随包 runtime 是一个「裸 Python 发行版」** —— 它既没有仓库包，**也没有任何第三方依赖**。

| 层 | 状态 |
| --- | --- |
| 仓库包（app/archeaxis/shared…） | ✅ **本轮已装** |
| **第三方依赖（yaml，以及其后可能还有更多）** | ❌ **缺** |

**「已安装布局」的含义因此更完整**：不只是把仓库包放进去，
**而是把项目声明的依赖一并装进随包 runtime。**

## 4. 一个方法论上的确认

| 观察手段 | 可靠性 |
| --- | --- |
| 我轮询子进程命令行 | ⚠️ **不可靠** —— 本轮一个都没抓到，但迁移**确实跑了**（诊断里有新鲜 stderr） |
| **应用自己的诊断日志** | ✅ **可靠，而且是它主动给我的** |

**所以此后我以应用的自述为准，不以我的进程轮询为准。**
（第 90 轮我曾因读取不稳定而下保守结论 —— 现在有了更好的手段。）

## 5. 我**不**声称的

| 不声称 | 原因 |
| --- | --- |
| 「装完依赖 Core 就一定能就绪」 | **未验证** —— 未知还有几个缺失，且迁移后还有 readiness |
| 「缺失只有 yaml 一个」 | **很可能不止** —— 依赖是一整组 |

**但这已经是一条**可迭代**的路：装 → 跑 → 读应用诊断 → 看错误是否前移。**

## 6. 本轮改了什么（说清楚）

| 改动 | 位置 | 性质 |
| --- | --- | --- |
| 在构建产物的 `site-packages` 下建 6 个 **junction** 指向仓库包 | `C:\Windows\Temp\aaos-target\release\...`（**临时构建目录**） | **只读指向，未复制** |

**没有改任何仓库文件**；**未触碰官方 Green 的 `data/` 与资料库**；**未删除仓库内任何东西**。
