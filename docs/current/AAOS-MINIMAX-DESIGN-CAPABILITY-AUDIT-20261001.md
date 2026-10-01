# MiniMax Design 可用能力与 AAOS 取舍（2026-10-01）

官方资料：[MiniMax Design 中文站](https://design.minimax.cn/)、[英文站](https://design.minimax.io/)、[工具目录](https://design.minimax.io/tools)、[AI Design](https://design.minimax.io/tools/ai-design)。公开说明覆盖 Agent Mode 自动任务拆解和模型匹配、Canvas Flow、图片/视频/音频创作、本地资产中心、自定义及广场 Skills、审核节点；Windows 10+ x64 版本。官方站列出的 `image-remix` v0.7.14 可从参考图重制视觉语言，适合缺失星球/宇宙背景；图生视频与剪辑可用于低频动效样片。先确认安装版本、功能、费用、许可证和导出格式，再调用。

上述站点没有证明 MiniMax Design 是 Git 客户端、Avalonia IDE、可修改 C# 源码，或拥有某项 Skill 的下载量/热度排名。“最新/最火”只能在软件内广场及官方发布页实时核验，当前标 `UNVERIFIED`；以任务适配、可维护性、成本为筛选优先级。9/30 包列出的 Magic UI、React Bits、Aceternity 等是 Web/React 视觉参考，不能直接嵌入正式 Avalonia Desktop。可用矢量图标与原生动效须在正式 UI 运行时落地，并记录版本、许可证和路径。

推荐顺序：读取母版及资产清单 → 用本地 Canvas/参考图重制确实缺失的星环、行星、微光资产 → 导出静态源图与可审阅短动效 → Avalonia 实现者按统一主题令牌和 reduced-motion 规则接入 → 原生界面逐页、双主题、缩放验收。避免为每页重复生成相同背景；复用一个经审核的资产系列。不要上传私人数据、凭据、数据库或用户工作区至云模型。
