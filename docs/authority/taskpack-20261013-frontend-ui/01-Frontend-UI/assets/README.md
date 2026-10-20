# 已纳入资产及使用方法

assets/vendor/npm 包含五个已核对包身份与 registry SRI 的归档：dockview-react、dockview、dockview-core 8.5.1，Radix dialog 1.2.0、tabs 1.1.22。下载不等于已安装；Radix 传递依赖与 React 由实际项目 lockfile/安装流程补齐，本包不是完整离线 npm 缓存。公开包的签名未在本轮做独立密码学校验。

assets/vendor/lucide/icons 是 24 个原始 SVG，保留 ISC 与 Feather 派生图标 MIT 的完整声明。Noto 字体与官方当前 blob 一致，按 OFL 1.1 保留原文件；完整 OTF 约 16.4 MB，不作为首次打开的强制下载。默认系统字体，生产可选做合法子集或按需字体包。

components 内 CSS 和 React wrappers 是本项目材料配方，Dialog/Tabs 复用 Radix，不另写焦点和模态体系。DockviewIntegrationRecipe 是接入参考，业务实例、正式状态和布局保存由 FE06/BE02 完成。配方的语法与材料展示可以验证，不等同于原生主项目集成已完成。

references 是用户提供的设计参考，只用于研究与生成方向。character/states 由 ASTRYN 当前原创 SVG 代码输出，作为首期状态资产；文本事件驱动表情不等于真实音频口型。代码与源素材另存，以便 GF03 改进后统一升级。
