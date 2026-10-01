# MiniMax Design 可用能力与 AAOS 取舍（2026-10-01）

官方资料：[MiniMax Design 中文站](https://design.minimax.cn/)、[英文站](https://design.minimax.io/)、[工具目录](https://design.minimax.io/tools)、[AI Design](https://design.minimax.io/tools/ai-design)。公开说明覆盖 Agent Mode 自动任务拆解和模型匹配、Canvas Flow、图片/视频/音频创作、本地资产中心、自定义及广场 Skills、审核节点；Windows 10+ x64 版本。官方站列出的 `image-remix` v0.7.14 可从参考图重制视觉语言，适合缺失星球/宇宙背景；图生视频与剪辑可用于低频动效样片。先确认安装版本、功能、费用、许可证和导出格式，再调用。

上述站点没有证明 MiniMax Design 是 Git 客户端、Avalonia IDE、可修改 C# 源码，或拥有某项 Skill 的下载量/热度排名。“最新/最火”只能在软件内广场及官方发布页实时核验，当前标 `UNVERIFIED`；以任务适配、可维护性、成本为筛选优先级。9/30 包列出的 Magic UI、React Bits、Aceternity 等是 Web/React 视觉参考，不能直接嵌入正式 Avalonia Desktop。可用矢量图标与原生动效须在正式 UI 运行时落地，并记录版本、许可证和路径。

推荐顺序：读取母版及资产清单 → 用本地 Canvas/参考图重制确实缺失的星环、行星、微光资产 → 导出静态源图与可审阅短动效 → Avalonia 实现者按统一主题令牌和 reduced-motion 规则接入 → 原生界面逐页、双主题、缩放验收。避免为每页重复生成相同背景；复用一个经审核的资产系列。不要上传私人数据、凭据、数据库或用户工作区至云模型。

## 可核实候选与适用边界

| 入口 | 官方可核实能力 | AAOS 用法 | 不得推断 |
| --- | --- | --- | --- |
| Design 内 Skill Plaza：`image-remix` v0.7.14 | 按参考图视觉语言生成新画面。 | 重制缺失的星环、星球、山脊背景，留源图和导出索引。 | 自动获得版权、自动输出矢量或可直接嵌入 Avalonia。 |
| Design 内 Skill Plaza：`character-scene-storyboard` v1.4.11 | 依据参考与脚本生成设计板。 | 为 Home Hero/品牌转场做运动分镜，仅在需要时使用。 | 这是 UI 组件库或代码生成器。 |
| Design 工具目录：AI Image Generator / Photo Editor / Image to Video / AI Video Editor | 参考图生图、修图、静图转短视频、视频剪辑。 | 先做静态视觉，再做少量低频动效样片；导出后由原生 UI 审核性能与 reduced motion。 | 所有页面都要视频、生成结果无需复核。 |
| Design Agent Mode / Canvas Flow / 本地资产中心 | 自动任务拆解、画布节点、资产管理及导出。 | 以页面批次复用同一令牌与资产，减少重复上下文。 | Design 必然支持 Git、C# 编辑或运行 Avalonia。 |
| [MiniMax-AI/skills](https://github.com/MiniMax-AI/skills/blob/main/README_zh.md) 编程工具技能库 | 官方 `frontend-dev`、`shader-dev`、`minimax-multimodal-toolkit`；社区 `vision-analysis` 等。README 称 Beta，提供 Codex/Claude/Cursor/OpenCode 接法。 | `vision-analysis` 可辅助母版截图审查，`shader-dev` 可作光效算法参考；媒体工具可作资产候选。先核版本、许可证、费用与软件实际可调用性。 | 该 GitHub 仓库的 Skill 已安装在 MiniMax Design；`frontend-dev` 的 React/Next.js、Framer Motion/GSAP 可直接用于 Avalonia。 |

官方页面只展示部分广场 Skills 和 15 个工具条目，没有可审计的全量插件清单或热度排名。所谓“最新、最火”须在执行当天以广场/官方发布页核实，当前为 `UNVERIFIED`；不得为了排名安装与 AAOS 无关的有声书、MV、电商或付费插件。来源：[Design 官网](https://design.minimax.io/)、[工具目录](https://design.minimax.io/tools)、[官方编程 Skills](https://github.com/MiniMax-AI/skills/blob/main/README_zh.md)。
