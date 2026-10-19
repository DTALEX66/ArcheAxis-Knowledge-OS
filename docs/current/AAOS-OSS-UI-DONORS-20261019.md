# 图谱视觉吸收与 UI 跟进收敛（2026-10-19）

本轮把 Neural Creator 的星团/曲线/弹簧交互改造并入 AAOS **原有语义 SVG 图谱**，没有引入第二主壳或画布。实现及限定本地验证 PASS；整体产品、已安装宿主、真实 Core 图谱与视觉逐像素还原仍 PARTIAL / UNVERIFIED。机器收据见 `receipts/AAOS-NEURAL-GRAPH-ABSORPTION-20261019.json`，后续 OpenMAIC 研究见 `AAOS-OPENMAIC-ABSORPTION-20261019.md`。

## 上游分型与证据

| 上游固定版本 | 决定 | 归档 |
|---|---|---|
| [Linye-ai/neural-creator-dashboard](https://github.com/Linye-ai/neural-creator-dashboard/tree/e12317fbc570fd290654db7692e2a1b4bdd7fcb5)，e12317fbc570fd290654db7692e2a1b4bdd7fcb5，v0.6.3 | ADAPT：Home/NetworkCanvas/StarCore/neural.css 的交互几何与视觉层。根 LICENSE 为 MIT；About 的旧非商业文字与当前 LICENSE 不一致，采用固定版本实际许可并保留完整版权 | `.project-local/archives/oss-intake-20261018/neural-creator-dashboard/<SHA>/`，完整源码 ZIP 43 个成员逐字节 SHA256/Git blob 核对；ZIP SHA256 `cbe46e146536318043fa3bd48e030454622d99f5ffa90d2fe9f03b2f28278e69` |
| [SENLIN-SAMA/win-.-](https://github.com/SENLIN-SAMA/win-.-/tree/aa64bc73c03110f9529bae288e70d2a3fc32760f)，aa64bc73c03110f9529bae288e70d2a3fc32760f，GlassBoard v0.9.12 | REFERENCE：布局、拖动与锁定、隐藏恢复、背景透明度和状态反馈。源代码与主许可缺失，代码/二进制/素材复用 BLOCKED；第三方 MIT 通知不授予整个软件权利 | `.project-local/archives/oss-intake-20261018/win-.-/<SHA>/`，3 个公开 Markdown 及 tree/manifest 校验；6 个用户 ZIP 不作为可复用源码 |

Neural Creator 是 React19/Vite7 的前端与 localStorage 应用，不是完整 LLM 后端；没有把它的测试/CI状态等同本项目。原实现有大量两两距离计算、基于位置/标题的身份、不充分的输入/截断处理，以及保存异常可能被吞的路径；这些外围导入器、存储和 shell 均未吸收。天文星表来源未独立核实，本轮星点用确定性伪随机过程生成，不复制数据集。完整 MIT 正文位于 `frontend/src/components/neural-creator-NOTICE.txt`，通过 Vite URL 资源随 bundle 分发，主 THIRD_PARTY_NOTICES.md 已登记来源与排除项。

GlassBoard 的 WPF/.NET 实现与当前宿主不匹配，文档还明确保留 DPI、多屏、拖动等待验项。诊断打包脚本会包括日志与布局，未照搬。一次追加静态媒体脚本读取和 ZIP 哈希命令被自动审批审核拒绝，未给出具体原因；该深读项 BLOCKED，停止该路径，没有绕过。已有公开 Markdown 研究与独立图谱开发不受此项影响。

## 实际改造

- `presentation/neuralGraph.ts`：稳定 ID 种子、确定性星点、按实际对象类型分区、焦点列队、临界阻尼弹簧、三次 Bézier 连线与粒子位置；邻接索引 O(N+E)，不推导或持久化知识关系。
- `ConstellationGraph.tsx/css`：星云、核心光晕/环线、真实互向连接区分、邻域高亮；独立星团控制、视口缩放/平移/适应、节点键盘打开与 Escape 返回。低质量、减少动画、不可见及卸载停止连续动画；大图降低装饰，保留全部已加载节点与关系列表。
- `CanonicalRelationSpace.tsx`：只替换原 SVG 呈现段，保留固定版本与来源投影、分页/过滤、扫描范围和失败提示，节点仍调用原固定对象引用。没有新数据库写口、模型请求或自动推断边。
- 修复上游思路迁入后的缺陷：稳定槽位不受输入顺序和标题变化影响；平行/互向/自环 lane 有界，曲线控制点纳入适应视角；1000节点焦点扇区有界列队；中文标题按宽度保守省略并硬裁剪，完整名称留在 title；焦点模式上下文改为有间隔的纵列，避免卡片遮挡。

## UI-FOLLOWUP-006

原标签切换/关闭回退只改变 Dock，App 顶部与 hash 仍可能指向旧页面。已通过完整面板身份和原导航保护同步 App，不把文档对象视图/普通03或AI家族页混为同一面板；同页显式导航可以重开已关闭宿主，拒绝导航则回退原活动视图。保留草稿、输入法保护、未知回执与恢复边界。

只读复核又发现恢复场景需清除旧活动覆盖、布局读取迟到不能反向解锁；已修复并以9项 App/Dock 回归覆盖。锁定竞态有实际 RED→修复；恢复保护包含静态竞态预防，早期测试 readFlight 时机错误单独保留，不冒充产品 RED。真实浏览器依次使用 Delete、兄弟关闭按钮和中键关闭，按实际剩余活动标签断言标题/hash：01→05→03。没有假定关闭三个标签后首页必须仍存在。

## 验证范围与失败历史

最终命令、开始结束 UTC、退出码、HEAD/dirty patch、脚本及源码哈希、构建资源与截图见机器收据和对应 ignored run。

- 全套仅指当前前端 Vitest 收集集；不代表全仓或需求覆盖率。图谱专项覆盖0/1/1000节点、密集平行关系/自环、稳定身份、过滤槽位、缺失端点、动画退出、键盘和固定跳转。
- 浏览器使用生产 bundle、Chrome、1 worker、独立 profile 与127.0.0.1静态服务；Core/数据库/文档内容为 SYNTHETIC。图谱固定10节点10边，验证五类分区、焦点展开到目标、邻域、缩放平移、固定v1读取、三主题、640窄窗和 reduced-motion。
- axe 只是自动扫描；incomplete 保留，不能当作完整 WCAG 合规。截图都实际打开查看；桌面完整卡片与窄窗滚动中的局部画面分别标记，窄窗缩放前文字偏小、上下文标签/关系仍可能拥挤，未宣称商业视觉验收。
- 保留1658/1659初次全套失败（3个无用静态class没有规则），修复为移除无用class，不放宽检查。保留测试脚本的路径基准、闭合后首页假设、未展开导航入口及截图未等弹簧收敛的失败/不足，最终针对实际活动面板与目标坐标验证。
- 公共演示 IAB 读取超时，没有查看上游实际效果截图；本轮为源码几何/效果结构适配，逐像素还原 UNVERIFIED。没有将工具样例通过率或上游宣传当成产品证据。

性能仅有该环境的构建耗时与单次浏览器 navigation timing；没有GPU/FPS/内存/功耗的可比较基准。1000节点几何测试不代表千节点交互性能 PASS。

## 剩余最小范围与回退

1. `OSS-GRAPH-003`：真实 Core 图谱固定引用与过滤、原生 WebView2 动画/缩放/焦点及安装环境，NOT_EXECUTED。
2. `OSS-GRAPH-004`：同条件上游视觉参考与帧时/内存/减少动画基准，UNVERIFIED；进一步处理小窗可读性、密集标签和所有主题。
3. `OSS-GB-001`：设计参考审计 PASS；`OSS-GB-002` 拖动取消/锁定/恢复专项 NOT_EXECUTED，代码/资产复用继续 HOLD，先取得实际源码与许可。

回退需按本轮写集与 before 备份逐段审阅。图谱前置源备份 `.project-local/audits/neural-absorption-20261018/before/`；Dock 前置源及二次复核备份 `.project-local/audits/ui-dock-navigation-20261018/`。不使用全仓 checkout/reset；未知原有修改保留。最终只新增本轮源码/证据/研究与执行记录，没有提交、推送、发布、安装或替换 Green。

## 最终验证数值

HEAD `fe18fdc3cbcab9a0f84a02c5a4db1b6bcef13f46` + qualified dirty patch `0c32b22ef72b3a11f94164019166154e5a0484f85d0c30ad3165901670edc87d`；源码在全套/构建/最终浏览器三组均保持一致。前端 **171文件1661项PASS、0失败0skip**；TypeScript/Vite PASS；14浏览器检查PASS；14组axe扫描0违规、23条incomplete；20张最终截图实际查看。收据写入后的变动仅为本轮文档/收据，源码逐文件SHA另存。

实际命令、UTC时间、退出码：`.project-local/runs/be268a2d33/ui-neural-final-full-1019/artifacts/test-command.json`、`.project-local/runs/be268a2d33/ui-neural-final-full-1019/artifacts/host-build.json`、`.project-local/runs/be268a2d33/ui-neural-final-browser-1019/artifacts/execution.json`；静态服务与浏览器退出读回见`.project-local/runs/be268a2d33/ui-neural-final-browser-1019/artifacts/ui-pilot/postflight.json`。
