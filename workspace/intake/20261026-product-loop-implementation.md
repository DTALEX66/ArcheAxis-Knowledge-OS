# 2026-10-26 UI与产品链修复说明

这是本轮实现与证据说明；唯一进度仍在 `docs/current/AAOS-UI-FIRST-EXECUTION-20261009.md`，执行与交付授权仍读活动指针。以下本地候选已经过组件与原生验证；提交前尚未获得本轮托管CI、安装或Green更新资格。人工视觉与内容质量评审延期，不伪造为通过。

## 具体成因与修复

| 问题 | 本次核实的原因 | 已实现的变化 |
|---|---|---|
| 卡片偏蓝、玻璃廉价 | 新页面仍有不透明嵌套底色，材质规则部分只命中旧组件；所有层级使用接近的蓝色与亮边 | 统一中性灰透光层、外壳/标题/工具/嵌套卡的层级，组合模糊、饱和、边缘与阴影；正文基准14px |
| 主窗太低、人物太小 | 浮动主窗的固定高度与人物旧容器限制；窄高研究区还会压缩保存区域 | 保留顶部菜单和Dock，1920 CSS基线主窗 y48/h968；人物默认半身约205×208；研究保存条不再被挤压 |
| 人物不统一 | 原九张独立静态图的构图和人物一致性不足 | 使用内置imagegen生成同一人物、服装、镜头和光线的透明3×3九状态素材；原素材原字节保留作失败回退；“全幅”是腰部以上构图 |
| 小白不知道下一步 | 空态、首用说明、导入和模型配置入口割裂 | 可跳过、恢复的10步引导；真实16页单原件入口；空阅读态导入可达；高级模型字段折叠；未知结果按同一请求读回 |
| 能力看起来缺很多 | 父类摘要和折叠分类隐藏了细项，已有部分实现大类仍包含未来子项 | 16族/186设计细项全量入口、细项搜索与未来分类；目录完整不等于186项已实现 |
| 右键像网页、退出挂住 | 缺少按区域动作；Windows原生菜单的活动消息循环可能阻住宿主退出 | 原生功能菜单及键盘回退；复用导入/导航/编辑/窗体动作；退出前仅取消本宿主菜单，再沿原有Core退出链 |
| 多行保存失败 | TipTap换行/粘贴复制了段落ID，Core真实返回400 duplicate block ID | 事务中保留原段落身份，为缺失/重复ID分配新ID；保留未知内容，回归测试覆盖换行与粘贴 |
| 文件夹映射不可达 | 正式FolderIngest与关系Panel已存在，但16回调没接上，实际03分支提前返回 | 接通16→03，读取真实批次及成员身份；刷新/历史/重开可回到同一映射 |
| Canvas与大文本转换拒收 | worker升为0.1.1而Core白名单仍只有0.1.0；transport定位上限与Core不一致 | 显式接纳0.1.1并保留旧版本；5000行定位上限与实际覆盖率一致，全文及尾部不截断 |
| 百科检索失败 | 本机直连TLS超时，系统已有本地代理但worker未沿该路线 | 仅读取已启用的无鉴权literal loopback系统代理；显式专用配置优先、direct可强制直连；无PAC执行/端口猜测/全局配置变化 |
| 引导样式被拦截 | Radix滚动锁动态style不在style-src许可中；本地IPC来源也缺少精确声明 | 只允许已核验0gap CSS的SHA256，补ipc:及http://ipc.localhost；不加入unsafe-inline，不改模态焦点结构 |
| 模型有思考但无正文 | 新快捷预设仅1024/2048输出预算；真实材料补充请求在2048内未产生最终正文 | 新建快捷/缺失预设预算4096，保留已有有效profile/binding；失败明确提示调整上限、新请求预览，原请求保留且不自动重试 |
| 媒体回退源码有而包里没有 | 本地增量stage只遍历旧manifest，漏掉新增media_decode.py；正式全量stager正确 | 隔离stage合并Git已跟踪worker清单，补唯一漏件并核对共同19742个清单身份；不改业务或正式stager |

## 本地最终候选与验证

本地冻结身份：HEAD `41e1848dca00f724db437c649c6445532221705a` 加 dirty patch `77b583e07bc31d1f42f2e323a23a6530254d88287cae0936dbe06b204876ab8e`。其后说明文档更新不冒充该构建点。托管CI必须另绑定实际提交及制品SHA。

| 成员 | SHA256 |
|---|---|
| Host | `fc579f832799a3437bb7a0e090201fe57aa0c84b2539f6178d33f6e9f31ee376` |
| Core | `c44e9bbf04688c85cf64f2fa89ab5bfa55f1e58727c03b11881fd60ce2b77369` |
| backend manifest | `16ac41031ffcd2ebf17e5fa63033c3e04364a2da29b63c402c7a543e8809f58f` |
| 新人物素材 | `1b5582f64da0a0dd3b3c70c314dfa972dfe27a327f4a6efdced7fc4d9963df11` |

候选位于 `.project-local/runs/be268a2d33/closure-20261026-portable-qualified-b2/artifacts/星环便携候选`；组装19746成员，未安装/发布。构建回执 `f6854aba9850/artifacts/frontend-build.json`，Core资格 `closure-20261026-core-qualified-b8/artifacts/execution.json`，均在同一runs根；原有Python/依赖基线声明与增量成员验证分别保留，不把声明来源说成独立重建证明。

| 检查 | 实测与边界 | 回执（均相对 `.project-local/runs/be268a2d33/`） |
|---|---|---|
| 前端全套 | 2166/2166 PASS；生产typecheck/Vite/Rust offline locked PASS | `closure-20261026-frontend-all-final/artifacts/vitest.json` |
| CSP契约 | 7/7 PASS；只允许固定样式hash与精确本地连接 | `native-csp-20261026-security-contract/artifacts/execution.json` |
| 原生总览 | 真实Tauri/Core，无bridge stub；22/22原生与8/8独立1920 CSS；页面/console/CSP错误0，前后原件和文档均0 | `native-overview-20261026-qualified-b3/artifacts/native-overview/receipt.json` |
| 引导滚动锁 | 首次与恢复两次sheet实际存在，overflow hidden/overscroll contain，0 CSP拦截 | `native-csp-20261026-qualified-b4/artifacts/native-overview/receipt.json` |
| 原生业务与引导 | 多段v1→v2/重开DTO一致；真实目录FileList及16→03映射/历史/重开一致；10步入口、暂停恢复、完成与进度持久化；6次退出0/Core GRACEFUL/端口闭合 | `ui-native-csp-refresh-suite-20261026-final-b2/artifacts/native-csp-suite.json` |
| 三路公开检索 | 百科/社区/论文均真实complete；固定原始与选中快照、引用、导出、重启读回；公共知识仍候选 | `closure-20261026-public-qualified/artifacts/public-research-receipt.json` |
| Office四类 | DOCX/XLSX/PPTX/文本PDF真实Core/worker、定位、重新解析与重启 | `1f71b2b505ec/artifacts/common-formats.json` |
| 研究/知识/学习/恢复 | 110请求，三公开渠道完整、重启和独立恢复相等；工程夹具的审核不等于真人批准 | `closure-20261026-learning-qualified/artifacts/research-learning-runtime.json` |
| 真实本地模型 | 同候选qwen3.5-4b两次真实材料回答，19.6064/31.6648秒，1350/2392输出token，均最终stop；补充是作者约束，非伪造发现模型错误；44请求/重启一致 | `closure-20261026-material-model-qualified/artifacts/local-material-model-runtime.json` |
| Canvas与轻量/OCR | 原包Canvas6例、11格式first/reparse/定位/重启通过；新包共同成员与46个实际关键文件逐字节映射，未声称整组重跑 | `closure-qualified-b2-backend-rebind-20261026-b2/artifacts/backend-component-evidence-rebind.json` |
| 媒体 | 原包WAV/MP3/MP4真实ASR、4时间片段/11735ms、重解析/重启；MP4产物338–341字符长路径有效；视觉语义未执行，视频整体partial | 同上组件映射及 `closure-final-common-speech-20261026/artifacts/common-speech-qualified-receipt.json` |
| 新包实际解码回退 | 隔离外置FFmpeg，正式worker自动PyAV，完整音轨+3帧且无解码/帧错误；无ASR env本机自动发现已登记模型；缺模型时拒绝转换、原件保留、无发布产物 | `closure-qualified-b2-asr-default-discovery-20261026-b3/artifacts/asr-default-discovery-receipt.json` |

真实窗口物理DWM 2560×1380、DPI120，CSS 2048×1082/DPR1.25；1920×1080是单独标记的CDP设计基线。程序初始尺寸与最大化不改变显示器分辨率。原生菜单实际popup与退出复验正常；旧5秒CDP清理观察曾失败，后续15秒有界复验约0.4秒闭合，不能断言旧失败只是阈值过短。物理菜单项逐项点击仍未执行，Owner按Esc停止后的CUA未恢复。

## 兼容范围与仍待评审的项目

正式兼容链是Rust Core/UI的文件夹清单→原件CAS→成员任务→同批Markdown/wiki/附件映射→Document/Graph。历史Obsidian测试中的md-only、默认0选中、10000字符截断及created_at问题来自legacy共享数据库路线，不能写成当前正式链的根因或修复成果。

| 对标能力 | 当前能够证明的范围 | 不作出的完成声明 |
|---|---|---|
| Obsidian/JSON Canvas | 合成MD全文、同批wiki/附件映射、原件身份；Canvas1.0空文件、节点/边及未知字段事实保全、subpath保全 | file.subpath目标解析/迁移未实现；不运行其插件/MetadataCache/workspace运行时 |
| Notion/Anytype类结构化知识 | 当前文件格式与canonical文档/关系链按对应回执验收 | 未实测对方数据库公式、权限、全部原生块与插件语义等价 |
| Zotero类文献工作流 | 公开论文元数据/摘要快照、来源版本与引用可追溯 | 未声明原生库同步、全部引用样式与第三方插件兼容 |
| Open WebUI/AnythingLLM类本地材料问答 | 本地真实模型、材料预览/权限绑定、最终回答候选/重启；云端专业接口测试独立记账 | 未声明通用Agent Runtime、Marketplace或第三方工具任意执行；真实云推理延期 |

对标采用官方资料及既有实现，不将产品名字相似当成兼容证明：[JSON Canvas 1.0](https://jsoncanvas.org/spec/1.0/)、[Open WebUI API](https://docs.openwebui.com/reference/api-endpoints/)、[AnythingLLM embedding](https://docs.anythingllm.com/setup/embedder-configuration/overview)。CSP沿[Tauri官方本地IPC说明](https://v2.tauri.app/security/csp/)收窄配置。

人物九静态图、现有状态切换与动效不等于Live2D、真实口型、全身动画或3D。材质审美、人物偏好、长页面信息密度、代表性OCR/ASR/答案质量与Owner实际使用评审仍未执行；工程检查不能替代。中文扫描识别未测，音视频仅合成英文。ASR权重为外置资源，本机可自动发现；换机需合规准备模型或使用正式stager的--asr-model及许可/哈希登记，当前未提供产品内ASR目录选择，缺组件的中文修复指引仍需改进。

本轮保留原菜单退出、Canvas拒收、2048模型无正文与漏模块等失败回执。新文件Ruff通过；修改过的旧文件仍有HEAD已存在的Ruff发现，不宣称全库lint已通过。提交/托管CI/安装/Green程序更新及回滚证据将另在唯一执行记录与活动指针回读，不以本地PASS代替。

## 本轮交付读回

本地功能提交 `d4f72bf193b0b653bfc167a21818ae93af4afa5f` 已形成；正常push被当前自动审批拒绝（需要审批但AskForApproval=Never），未绕过。远端分支仍41e1848d…，本轮CI/安装/Green未执行；旧CI成功不用于新提交。Green Host仍da8dc768…。详细过程及后继路径只记唯一执行记录。

可以通过 `.project-local/AAOS-UI-Preview-20261026.cmd` 打开已验证的本地候选，使用独立工作区与WebView配置；`--check`参数检查通过，未将其算成实际启动验收。最终1920 CSS首页截图 `native-overview-20261026-qualified-b3/artifacts/native-overview/baseline-1920-01.png`，全22页及引导截图同目录。当前可审阅本地实现，不能称现用Green已换新。
