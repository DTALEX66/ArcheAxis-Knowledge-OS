# AAOS-01 步骤2：候选实际解释器的导入能力实测（2026-10-05）

**审计要求**：用候选**实际选中的解释器**检查导入路径/版本，而非用目录名推断。
**执行方式**：对候选与产物中**每一个** `python.exe`，以 `-I`（隔离模式）检查 `openpyxl`/`pptx`/`tesseract`。

## 结果

```
aaos-cand1\runtime\python.exe                  openpyxl=false  pptx=false  tesseract=null
aaos-msvc-target\release\runtime\python.exe    openpyxl=false  pptx=false  tesseract=null
runtime\Lib\venv\scripts\nt\python.exe         ERR: No pyvenv.cfg file
```

## 结论

1. **候选与产物均只有平铺解释器，无嵌套解释器。**
   ⇒ **我此前「陈旧嵌套解释器残留」的判断，只适用于更早那一次的构建目录状态，
   **不适用于当前候选**；该判断不应作为「陈旧候选」的依据。**
2. **两个解释器都确实无法导入 `openpyxl` 与 `pptx`。**
   ⇒ **断言若真的执行，会在**实际会运行的那个解释器**上失败**；
   ⇒ **在本候选上它不是「假通过」风险** —— **但审计对断言设计的批评仍成立**：
   **断言只能证明存在同名目录，不能证明被启动的解释器可导入。**
3. **`tesseract` 在两个解释器下均为 `null`**，与 §2.8 的「缺指向」一致。
4. **新增观察**：`runtime\Lib\venv\scripts\nt\python.exe` **缺 `pyvenv.cfg`**，
   是一个**损坏的 venv 启动器** —— 是否会被任何代码路径选中，**未查**。

## 这对「陈旧候选 vs 流水线漏装」意味着什么

**两者仍未排除**，但**判据被削去一条**：
- **不能再以「嵌套解释器陈旧」论证陈旧候选**（当前候选中不存在嵌套解释器）；
- **可确定的是**：**锁定声明中的两个引擎，没有进入**实际会运行的解释器****；
- **仍缺**：候选**构建 SHA**、**锁文件哈希**、**该解释器的身份** —— 审计已指出这三者是必需判据。

## 下一步（未做）

- **用该解释器跑 XLSX/PPTX 样本**（已知会失败于导入，可确认错误文本与 worker 报错一致）；
- **诊断 `desktop-fast` 的 `Test the canonical Windows desktop shell` 失败**（§2 已登记，未诊断）；
- **强化断言**：改为**用实际选中的解释器执行 `find_spec`**，而不是查找目录名。
