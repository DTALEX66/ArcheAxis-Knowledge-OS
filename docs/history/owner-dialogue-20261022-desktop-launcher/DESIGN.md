# Design System: AAOS Stitch能力启动台与玻璃材质候选

本文件由StitchDesign入口及stitch-design-taste工作流组织，为本轮设计研究的冻结说明。用户已有Stitch／五主题／本地字体／减少动画要求优先于技能通用禁蓝、换字体、无限微动或禁止窗口叠放建议。本文不是第二权威；生效要求读决定第十九／二十节。当前没有修改产品CSS、安装图标包或获得Owner视觉验收。

## 1. Visual Theme & Atmosphere

延续已接收Stitch的深色青蓝桌面、主背景、内缩业务窗、右侧小栖与资料窗。使用真实半透明材质与柔和透光层次，正文安静清晰；密度6/10、动效2/10。启动台是现有界面的菜单窗，不是第二桌面系统、独立仪表盘或市场。

生成图只保留窗口关系和入口组织；其大号彩色发光图标已被Owner否定。不能用该图证明已实现、像素还原或材质合格。

## 2. Color Palette & Roles

- 深空背景：沿现有本地背景资产，避免多层暗色遮罩把细节抹成单色；不新增远程壁纸依赖。
- 窗口基色：深海墨色 `#0e141d`；卡片基色 `#161c25`；主文字 `#e2e8f0`，辅助文字 `#b9c4d4`。
- 青蓝强调：`#38bdf8`，用于选中、焦点及有限边缘高光；支持／冲突／未知语义色沿五主题token，不以单色禁令取消。
- 现有原Stitch HTML为panel 88%不透明度、blur 16px，card为75%；当前外窗已经采用这些值，不能声称只是漏写blur。
- 后续试片可比较panel约64–80%、card约28–50%、blur 16–24px，正文阅读区局部提高不透明度；这些是待比较的候选区间，不是批准值或全部主题通用值。

## 3. Typography Rules

保留项目本地字体栈和中文兼容，不为技能换字体、不新增CDN。启动台标题20–24px，图标标签14px，说明12–13px；正文14–16px并按容器重排。不得为了放满图标缩小字。选中状态同时使用形状／文本，不能仅靠颜色。

## 4. Component Stylings

**材质根因与待核查**：`frontend/src/components/StitchWorkspaceChrome.css`的 `.ui-card/.capability-card/.ui-asset-card/.ui-learning-card`仍统一使用不透明 `var(--ax-panel)`；标题栏多用不透明raised底色。外层有blur时，这些层仍可能盖住背景。壁纸存在叠加遮罩；同样blur值在不同背景和覆盖层上视觉不同。这是源码静态证据，实际各主题合成效果、祖先backdrop采样及原生WebView结果仍待验证，不能标为已修复。

修正方向：窗口承载层、内部卡片、标题栏和阅读面分别定义语义材质；减少不必要的实色覆盖，保留正文可读底面；同圆角盒承担边框和内侧高光，不叠两个错位外框；模糊与内容文字分层，禁止对整窗使用 `filter: blur()`。

**标准图标候选，尚未安装或锁版本**：

| 候选 | 官方已核信息 | AAOS适用判断 |
| --- | --- | --- |
| [Lucide React](https://lucide.dev/guide/react) | 独立SVG React组件，可调尺寸／颜色／线宽，按导入打包，ISC | 主候选：统一24单位图标，细节克制，适合菜单／Dock／能力入口；最终版本及样例视觉待核 |
| [Phosphor React](https://github.com/phosphor-icons/react) | 官方React图标家族，MIT，多种weight及duotone用法 | 备选：若主候选在大图标入口过于单薄，比较整套regular／duotone，不只拼贴几枚 |
| [Material Symbols](https://developers.google.com/fonts/docs/material_symbols) | Outlined／Rounded／Sharp，fill／weight／grade／optical size，Apache-2.0，可取SVG或自托管 | 第三候选：统一Rounded风格；不运行时加载Google Fonts |

控件继续优先复用项目已有Radix Dialog／Tabs和Aaos组件，不为图标更换整套组件库。产品现有 `AaosIcon.tsx`为历史手写路径，不是上述标准库，也不是生成图中的3D图标。

建议对应语义：导入→上传／文件，阅读→书本，研究→文档比较，图谱→关系节点，集合→表格，画布→画框，学习→学习卡，模板技能→拼图。精确组件名须安装前对所选版本导出核对，不把建议名写成可用API。

启动台图标可用28–36px SVG置于48–56px轻量底托，条目整体负责点击，不再是大号高饱和渐变卡片；同一家族、同尺寸与视觉重量。普通／悬停／选中／不可用四态齐全；未来项用文字标签和低强调，不单纯降低到不可读。

## 5. Layout Principles

保留现有Stitch业务窗与DockWorkspace；中央增加启动台，点击进入既有消费者。窗口可以有受控遮挡，但关闭、焦点和任务状态仍可达；右侧辅助窗避免挤压正文。窄屏转单活动窗，图标网格自动降列，不横向裁切。Dock建议六入口但精确排列待实施评审。

## 6. Motion & Interaction

仅短暂悬停／切换动效，约120–180ms；不默认无限脉冲、声浪、浮动或新动画引擎。减少动画、减少透明、高对比及不支持backdrop-filter时使用可读的实色回退。窗口移动／缩放、连续切换、键盘、焦点和草稿保护复用既有规则。

## 7. Anti-Patterns & Verification

禁止纯色卡片＋发光描边冒充毛玻璃、模糊文字、全屏高透明导致正文难读、彩色3D图标拼贴、emoji、在线icon字体、为美化伪造成功／已连接状态。

后续必须对照原Stitch和实际截图查看：固定主题／尺寸／DPR／数据，比较窗口跨背景明暗区域时的透光和边缘，检查卡片与标题栏覆盖、正文对比和无backdrop回退。组件检查、浏览器、原生宿主及Owner视觉确认分别记账；CSS数值匹配不是视觉PASS。

本轮原生Stitch `get_screen` 只读调用成功：project `10243059433218383839`，screen `206611daf7a948edb97ea60c7a7d8654`，标题“AAOS 交互整合版”。本地已保全HTML快照参与静态核对；未重新下载渲染、未生成／编辑／应用新Stitch设计系统，不把元数据读取升级为这些结果。必要新稿仅针对启动台及材质试片，不覆盖原稿，不上传私人材料，不发布。

技术依据：[MDN backdrop-filter](https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/Properties/backdrop-filter)明确需半透明背景才能看到背后过滤效果。上述官方资料均于2026-10-22本轮读取；未据此安装依赖或宣称AAOS集成通过。
