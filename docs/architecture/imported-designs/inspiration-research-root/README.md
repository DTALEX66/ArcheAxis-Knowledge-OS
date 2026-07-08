# Inspiration Research — 灵感研究

> **未来核心系统研发专线** | [DTALEX66](https://github.com/DTALEX66)
> **Human Learning OS (A-Line) + Machine Knowledge OS (B-Line)**
> 建立时间：2026-06-25 | 最后更新：2026-06-25

---

## 项目定位

本项目是 [Knowledge-Base](https://github.com/DTALEX66/Knowledge-Base) 的**未来核心系统**，两者为两条并行开发专线：

| 专线 | 仓库 | 定位 | 性质 | 代码 |
|------|------|------|------|:----:|
| **未来核心** | **Inspiration-Research** | 未来核心系统研究 — 双系统架构设计、学习科学、多 Agent 协同原型 | 研究分析 | ❌ 不编程 |
| **当前实用** | [Knowledge-Base](https://github.com/DTALEX66/Knowledge-Base) | 可运行的个人知识库 — 功能完整性与用户体验 | 工程实现 | ✅ Python + Next.js |

**两条专线独立迭代，本仓库的研究成果成熟后逐步集成进 Knowledge-Base。**

详细关系定义见 `00_项目声明.md`，桥接方案见 `IR-to-KB-Bridge.md`。

---

## 专线总览

### A 线：Human Learning OS
CC Source 逆向 → 人类学习能力增强系统

| 模块 | 内容 | 状态 |
|------|------|:----:|
| 01-08 子系统设计 | 捕获→诊断→知识结构→路径规划→编码→宫殿→反馈→画像 | ✅ |
| 09-Learning-Science-Knowledge-Base | 学习科学全学科资料库 — **446篇有效论文** + 88知识文件 | ✅ 已验证111篇，已删除172篇伪造 |
| 10-16 子系统设计 | 训练→执行→治理→巩固→迁移→元认知→输出 | ✅ |

### B 线：Machine Knowledge OS
CW Source 逆向 → 机器知识与 Agent 执行系统

| 组件 | 内容 | 状态 |
|------|------|:----:|
| 01-06 | 协调器→任务编排→并行调度→事件路由→Agent权限→MCP扩展 | ✅ |

---

## 📊 论文验证状态

通过 CrossRef API（DOI验证） + 格式分析，对全部论文执行真实性验证：

| 状态 | 数量 | 说明 |
|:----|:----:|------|
| ✅ **验证通过** | **111篇** | DOI经CrossRef确认有效 |
| 📄 **保留（结构完整）** | **17篇** | 结构化格式，无DOI待后续确认 |
| 📄 **综述文档** | **18篇** | 非论文，主题概览文档 |
| 🗑️ **已删除伪造** | **151篇** | 批次生成紧凑格式，CrossRef查无此论文 |
| 🔲 **需CNKI验证** | **169篇** | 中文论文，CrossRef不可查 |
| ⚠️ **DOI需修正** | **27篇** | 结构完整但DOI无效 |
| **当前有效** | **446篇** | 18主题，平均每主题26篇 |

> 详细验证报告见 `15_论文摘要库/_reports/`

---

## 证据等级体系

| 等级 | 含义 |
|:----:|------|
| **S** | 元分析 / 系统综述 |
| **A** | 高质量实证研究 / 随机对照实验 |
| **B** | 准实验 / 相关研究 |
| **C** | 案例研究 / 实践经验 |
| **D** | 流行方法 / 未经实证（放入避坑区） |

---

## 统计数据

| 维度 | 数值 |
|------|:----:|
| 论文摘要（有效） | **446 篇**（18 主题，累计删除172篇伪造） |
| 学习科学知识文件 | 88 份 |
| 案例库 | 9 案例（含研究证据+国际对比） |
| 学科国际对比 | 13 学科（全部添加） |
| A 线子系统 | 16 个（全部完成） |
| B 线组件 | 6 个（全部完成，A-Line已对齐） |
| 双系统集成文档 | 8 篇 |
| KB 参考分析文档 | 23 份 |
| 代码行数 | **0**（纯研究项目，不编程） |

---

## 快速入口

1. 先读 `00_项目声明.md` 了解定位与双线关系
2. 读 `00_铁律.md` + `01~03_*.md` 了解操作规范（**必须全部遵守**）
3. 查看论文验证报告：`15_论文摘要库/_reports/_SUMMARY_verification.md`
4. 按专线深入：A-Line-Human-Learning-OS/ 或 B-Line-Multi-Agent/
5. 查看 IR-to-KB-Bridge.md 了解与 KB 的桥接方案

---

## 关联仓库

| 仓库 | 说明 |
|------|------|
| [Knowledge-Base](https://github.com/DTALEX66/Knowledge-Base) | 当前实用专线 — 可运行的个人知识库 |
| [Skill-Integration](https://github.com/DTALEX66/Skill-Integration) | Codex 技能集成 |
| [AI-Enhancement-Package](https://github.com/DTALEX66/AI-Enhancement-Package) | Codex 增强包 |
