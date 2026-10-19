# 当前 Agent 完整交接提示词：全量前端优先，再后端闭环

用户再提“闭环”时，首先按[唯一最快最短完整闭环定义](../truth/CLOSED_LOOP_DEFINITION.md)（AAOS-SHORTEST-COMPLETE-LOOP-V2）理解范围，再核活动指针和实际进度。新定义包含免费百科／社区／科研检索比较、全面非企业知识库特色、既有开源池和本地／云端双通道，不能缩成小演示；定义落地不代表产品已完成。

> **最新接续决定（2026-10-19）**：Owner要求完整交接，并明确**全量UI界面优先，先前端再后端**。执行顺序及细分验收见[24个前端／15个后端分片](AAOS-FRONTEND-FIRST-EXECUTION-OVERLAY-20261019.md)。本文可整体复制给其他Agent；本次整理不启动后台开发。新会话收到接手／继续指令后按此执行。旧收尾只代表其时点，不能据它否定后继决定；不承诺自动继续。

状态 **RUNNING_BY_OWNER / PARTIAL**：Owner 明确要求今天停止额度监控并继续完成当前任务。今天不查询额度、不因额度阈值停工；已知监控id archeaxis的删除接口返回not_found；截图未命名卡片的身份仍未核实，详见收尾归档。本次准备完整交接，不新增产品修改；后续全量前端按分片接续，实际进度唯一来源为 [UI 执行记录](AAOS-UI-FIRST-EXECUTION-20261009.md)。

1. 先读 [根权威](../../AUTHORITY.md)、[AGENTS](../../AGENTS.md)、[活动指针](AAOS-ACTIVE-EXECUTION.json) 与 [文档职责索引](../DOCUMENTATION_AUTHORITY_INDEX.md)。
2. 读 [Owner 决定](AAOS-OSS-INTEGRATION-DECISION-20261019.md)、指针选择的任务来源与 [待办来源索引](AAOS-EXECUTION-BACKLOG-20261018.json)。既有实现先读源码及对应回执，避免重复实施。
3. 查 [共享路径](../SHARED_RESOURCE_PATH_INDEX.md)、[运行依赖声明](../../config/environment/capability-requirements.yaml)、[本地模型入口](AAOS-LOCAL-LLM-20261018.md)。登记不替代现场版本、加载、推理与权限检查。
4. 会话出处读 [项目会话索引](AAOS-CODEX-SESSION-INDEX-20261018.md)、[已授权资料整合](AAOS-SESSION-RECONCILIATION-20261018.md) 与 [Owner 原话映射](../history/owner-dialogue-20261019/README.md)，不猜私人路径或扫描原生会话。

当前采用强核心底座与按需能力接入；模型调度、权限、持久化、多格式基本链属于底座，扩展在既有能力中心按插件、技能、MCP 或模板表达。专业 PSD／AI／CDR／CAD／3D 源格式已移出直接支持目标。小栖在 AAOS 内适配；ASTRYN 源仓仍未取得删除资格。

旧报告、旧 current、旧收据和旧目录统一见 [历史入口](../history/README.md) 及 [迁移清单](../history/repository-consolidation-20261019/MANIFEST.json)。[路径身份登记](AAOS-AUTHORITY-ROUTES.json) 可解析旧路径；不在旧位置重建副本。仍绑定的 M0/R6 约束继续有效，旧整包执行顺序不重新激活。

接续先完成全量前端审查、必要修复及前端阶段验收，再处理模型完整旅程、BE10外部投递、常用格式和业务全链路。前端阶段可读后端合同和核已有接口；缺失接口登记精确阻断，继续独立UI，不扩写后端、不假装成功。阶段进度只写唯一执行记录，UI-P／BE-P是原UF／CB／FE／BE任务的实施分片，不建立第二任务真值。

只运行变更相关检查，按 [验证策略](../VERIFICATION_POLICY.md) 决定必要门禁。Owner 后继已允许覆盖 `D:\All projects\ArcheAxis.Knowledge.Green-x64` 的程序文件；按活动指针 `green_update_authorization` 先保全程序回退、核实候选与停止状态，再更新并读回身份。现有候选安装失败尚未闭环，此授权不是安装资格。V01 暂停、FT01–04 冻结；公开发布、真实数据覆盖及终止未知共享进程仍未授权。

## 一、接手职责与现场起点

你接手星环知识系统ArcheAxis Knowledge（AAOS）。Owner懂一点编程，描述可能不准确：理解意图、拆解依赖、独立判断，不机械顺从，不以工程术语掩盖缺口。沟通中文，普通实现细节自行推进；互斥范围、付费、私人资料外发和不可逆副作用才提出具体问题。

工作区`D:\All projects\ArcheAxis-Knowledge-OS`，先核cwd、git status --short、分支、HEAD、remote、当前PR／CI；保护未知修改，不切分支、不清理产品worktree，不reset／clean／force-push。同checkout只有一个writer；并行按当时平台／项目规则执行，独立writer用已授权隔离worktree。不要擅改Agent模型／provider／推理等级。

除上方入口外，读取[项目合同](../../PROJECT_CONTRACT.yaml)、[配置权威](../CONFIGURATION_AUTHORITY_INDEX.md)、[目录权威](../DIRECTORY_AUTHORITY_INDEX.md)、[运行交付导航](../RUNTIME_DELIVERY_AUTHORITY_INDEX.md)。当前任务来源`docs/taskpacks/aaos-ui-first-20261009/`内TASKPACK.md、TASKS.json、PAGE-PLAN.csv、FREEZE-REGISTER.md；补充合同`docs/authority/taskpack-20261013-frontend-ui/01-Frontend-UI/`和`docs/authority/taskpack-20261013-backend-host/`。规划时NOT_EXECUTED不是当前实现状态，原任务ID继续沿用。

引用缺失报告AUTHORITY_REFERENCE_MISSING，不从旧报告拼造权威。正式宿主是Tauri 2／React／TypeScript／Vite；Rust Core唯一SQLite/CAS业务写入者，Python workers隔离。frontend/、src-tauri/为正式宿主，旧Avalonia等仅供体。保留已有图谱renderer、DockWorkspace、普通保存原则和人工接纳正式知识流程。

## 二、闭环含义和架构决定

闭环完整范围只维护在docs/truth/CLOSED_LOOP_DEFINITION.md，七项缺一不能报完整通过：完整核心、常用多格式、免费百科／社区／科研真实检索比较、全面非企业知识库特色、既有开源池轻量吸收、本地＋云端真实模型、同候选全链路可靠运行。最快约束复用和顺序，不是缩成“导入一文件后回答一次”。

模型调度、身份、权限、保存、索引、多格式基础沉入强核心；软件协议走适配器、专用视图算法走插件、流程走技能、结构走模板、外部工具走MCP。在**同一个能力中心**发现／配置／管理，未来能力可展示但标规划／未接入，没有真实接线不提供假执行入口。底层库不伪装可安装插件，不新增另一市场、注册器或业务真值。

格式盘点包含TXT/Markdown/RTF、CSV/TSV/JSON/JSONL/YAML/XML、文本与扫描PDF、HTML/EPUB、常用Office新旧格式／开放文档、图片OCR、音视频转写／时间定位、知识库附件／双链／块／属性／Canvas。按实际矩阵列导入、阅读、编辑、检索、引用、导出、往返、依赖及损失；识别扩展名不等于内容可用。PSD／Illustrator AI／CDR／CAD／3D专业源文件直接支持已排除，用户外部导出图片或PDF后接入；不承诺源结构往返，AI这里指Illustrator文件。

全面兼容以软件／版本／非企业特色／接入方向矩阵验收，不把导入Markdown称全部特色；企业排除或延期，高难个人特色可具名延期但保留差距、降级损失、原因、恢复条件和蓝图位置。不得默默只剩几款或几个好测特色，也不承诺未枚举的全世界软件和未来版本。

最终同一候选完成J1多格式与批次恢复、J2外部研究、J3知识库特色、J4本地与云端模型、J5扩展生命周期、J6安装与可靠性。同一批对象／原件／版本连贯使用；不同分支／旧版本／样例的局部PASS不能拼成闭环。

## 三、交接编写前的实际快照

以下仅为2026-10-19编写前观察，接手必须动态核对：分支codex/sync-20261019，头5836b90687aaae3b9d6e8750f0793f0426c639ae，当时本地＝远端，PR194 Draft/Open，目标main；本文后继提交身份从Git读回。[PR194](https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/pull/194)；该头的[CI39271537141](https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/actions/runs/39271537141)当时queued，未取得完整资格。

- 产品总体PARTIAL。旧源码867d7c8a07d6e0e36895b84e3ad1490e0a58badb的[CI39264199340](https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/actions/runs/39264199340)整体CANCELLED，installer-lifecycle实际FAIL：`actual installed grouped UI engineering journey failed`，exit1。失败step为Verify the installed NSIS lifecycle；[失败job](https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/actions/runs/39264199340/job/118109895029)、[20文件证据包](https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/actions/runs/39264199340/artifacts/12192499506)。根因UNVERIFIED，先看日志／截图定位，不能猜测、减断言求绿。
- 已有ConsoleWindow移动／调整／键盘取消、密度／玻璃／菜单定位修复、DockWorkspace及小栖窗口。存在组件不等于全UI合格；Owner玻璃视觉验收、完整拆分／DPI／辅助技术仍须核。
- 正式A0浏览器曾PASS，13档视口／5主题，是真实Chromium＋合成host/Core，不能外推原生安装、真实业务或系统DPI。Rust workspace一次915通过、0失败、0忽略、194结果组；TS/Vite及相关合同曾通过，仅证明对应源码。历史156文件1492用例不是当前整仓资格，各轮重叠数字不能累加。
- 冲突探针已按业务页可读预览／诊断中心严格比较JSON迁移，保留三份快照、明确保存、B独立草稿、版本与重启；49项Python合同和19项组件检查只是局部资格，不能覆盖后继安装FAIL。
- DOCX/XLSX/PPTX/文本PDF有真实Core解析／保存／定位／重启证据，不等于全部格式、整批恢复、UI和往返。BE10本地human固定snapshot已有有限真实原生资格，外部对端／OS URI欠缺。
- LM Studio 27B曾真实回答，MTP曾启用；没有基线不称加速收益或质量达标。真实云端全旅程、三类免费研究、HUB004生命周期及全面知识库特色仍须补齐。

后继读回：5836b906的CI39271537141已实际出现test (3.12)两项FAIL，来自tests/test_project_contract_references.py：闭环登记新增closed_loop_definition但严格Schema未同步，additionalProperties拒绝该字段。云端5573 passed／2 failed／88 skipped仅为该作业，不是整轮通过。此处同步Schema及原失败回归，不放宽其他字段或保存／写入边界；本地修复不等于新exact-SHA CI已合格。原867d7c8a安装FAIL仍是独立未闭环证据。

审计实际边界沿[审计覆盖说明](AAOS-AUDIT-TEST-COVERAGE-20261018.md)、[会话收尾](../history/product-loop-20261019/conversation-closeout.md)、[验证索引](../history/product-loop-20261019/verification-index.json)和唯一执行记录追踪。历史结论不能直接当当前PASS。

## 四、先执行24个前端分片

**必须读取详细分片的逐项验收标准**，以下是执行目录。先核既有实现，按缺陷／缺失／待验收分类，只补必要差距：

1. UI-P01：生产页面×状态×尺寸覆盖与已有FAIL证据，PAGE-PLAN的22角色不是必须新建22路由。
2. UI-P02：信息架构和所有业务文案，清理“正典任务”等工程词；ID／schema／协议／JSON／日志进运行诊断，保留必要业务来源和版本。
3. UI-P03：最新大地图／主背景＋内缩主控台，像桌面工作空间，但不接管系统桌面／任务栏／全局快捷键。
4. UI-P04：内部主控台与原生窗口分别测移动、边角调整、铺满还原复位、键盘等价、Esc／pointercancel取消、防拖出可视区与草稿保护。
5. UI-P05：复用DockWorkspace做左右／上下拆分、分隔条、标签、关闭／重开、独立滚动、布局复位；窄屏退为标签或单栏；已有保存合同须验重启和失效几何恢复。
6. UI-P06：外层窗口／主控台／Dock／portal按实际容器响应，窄矮组合、长中文、Windows DPI和应用／浏览器缩放分别测，不整体缩小字体。
7. UI-P07：菜单／正文／辅助字／按钮／portal字号行距密度和点击区一致，长标题／路径／URL／表格可读，无失控溢出。
8. UI-P08：玻璃磨砂／透明度／阴影与同圆角边框高光，修错位／重复描边；五主题、对比与减少透明／高对比回退。默认cosmic以活动指针核，不按旧blueprint改回。
9. UI-P09：全部导航／抽屉／设置／命令菜单／tooltip／弹层实际命中、边缘定位、遮挡、关闭和焦点返回，不JS点隐藏按钮掩盖失败。
10. UI-P10：Tab/Shift+Tab/Enter/Escape、快捷键范围、中文IME、文本选择、键盘拖动等价、焦点陷阱与还原。
11. UI-P11：加载／空／失败／超时／取消／未知／离线／权限依赖缺失／重试／部分成功，防重复提交；202请求取消和未确认保存不报成功。
12. UI-P12：工作台／知识库／列表筛选排序／导入批次／格式损失／逐件失败／导出恢复入口，临时数组不冒充耐久批次。
13. UI-P13：阅读编辑、PDF／图片／媒体、分屏、引用定位、保存、草稿、三方比较／版本／重启；原始JSON从诊断读。
14. UI-P14：免费百科／社区／科研检索、结果详情／原文／引用、证据比较／冲突／保存与失败；模型生成链接不是检索证据。
15. UI-P15：现有图谱布局／视觉算法、缩放平移／选中聚焦、密集遮挡／中文标签、详情联动；保留renderer，尽可能合法还原供体效果。
16. UI-P16：学习路径／课程／教学需求／方案审阅／交付／Teach-back／反馈修订连续页面，复用OpenMAIC quiz M1，核对象版本、返回和状态。
17. UI-P17：本地／云端模型选择、连接加载推理区别、材料授权、依据回答、纠正复测、停止重试；BUFFERED不称token流，迟到片段缺口显式记。
18. UI-P18：同一能力中心整合插件／技能／模板／MCP／未来蓝图，可用／未配置／缺依赖／未接入／延期真实区分，底层库不假装可安装插件。
19. UI-P19：小栖直接适配AAOS，移动／收起／缩放／聊天／焦点／遮挡，复用资产和模型；不另起ASTRYN开发。
20. UI-P20：诊断／系统可靠性／来源历史版本／受限任务回执／备份恢复收敛，正常业务清爽、错误仍可发现并回跳。
21. UI-P21：所有生产页axe＋必要键盘／屏幕阅读检查，标签播报对比焦点和点击区，保留incomplete；自动扫描不是全面合规。
22. UI-P22：展开收起／连续中断／减少动画，大列表图谱性能；记录设备、规模、方法、结果，装工具不等于接性能监控。
23. UI-P23：全页面主题／尺寸／状态视觉回归，保存并真正看截图，记录浏览器字体DPR主题数据；首次基准不等于正确、不更新掩盖差异。FE25可本地采素材，不为此强行公网部署。
24. UI-P24：同候选隔离实际安装，窗口菜单键盘草稿冲突诊断重启，关闭grouped UI失败；交付前端覆盖、未测及后端接口阻断，不能报全产品闭环。

全量包含22业务语义角色及共用壳、状态栏、对象侧栏、命令菜单、Inspector、splitter、设置、人物浮层；详细分片列齐。角色合并在同页时按语义验，不制造新页凑数。前端阶段不得绕过Core写库；fixture只证明隔离UI，缺API明确登记并继续其他独立项。

## 五、前端阶段交付后执行15个后端分片

1. BE-P01：核心对象／版本／保存／未知ACK／冲突／幂等／备份恢复，复用Rust单写者。
2. BE-P02：常用格式矩阵、解析OCR转写位置损失、真实样例与对外承诺操作。
3. BE-P03：正式FolderIngest→Core耐久批次、逐文件身份作业结果／重试取消／重启，不以legacy流程替代正式真值。
4. BE-P04：百科／社区／科研三类真实免费检索，核官方API／许可／账号／免费范围／限流／元数据摘要全文，复用原候选。
5. BE-P05：去重与来源独立性、定位引用、支持反对冲突、人工知识接纳／学习及重启关联。
6. BE-P06：软件／版本／非企业特色／方向兼容矩阵，不适用／损失／具名延期，不能只留好测项目。
7. BE-P07：兑现特色，通用机制核心、协议适配器、视图算法插件、流程技能、结构模板、外部工具MCP。
8. BE-P08：LM Studio本地＋云端真实模型、真实增量／材料权限／取消超时迟到事件／恢复；无云端授权凭据如实BLOCKED。
9. BE-P09：HUB004真实扩展生命周期、依赖权限版本、安装更新回退禁用卸载与原对象保全；复用HUB001—003。
10. BE-P10：图谱与OpenMAIC已有成果接同一Core和真实业务数据，不另建画布或课堂平台。
11. BE-P11：BE10外部对端／OS URI、用途身份、选区固定版本、过期撤销重启，不以本地human资格替代。
12. BE-P12：同一候选完整J1—J6和失败恢复。
13. BE-P13：稳定CI，源码／生成物／合同／探针同步，原问题回归再阶段门禁，不减断言／required skip求绿，不连续无意义push取消重型CI。
14. BE-P14：合格候选Green更新、哈希读回、数据保全和程序回退。
15. BE-P15：企业／复杂项蓝图、资料会话缺口／账号设置／未命名定时尾项单独标识，治理不反复阻塞产品。

## 六、各类库、模型和工具路径

路径唯一依据是docs/SHARED_RESOURCE_PATH_INDEX.md及config/environment/capability-requirements.yaml；config/environment/external-resources-index.json只代表时点观察。登记≠安装≠会话发现≠连接≠真实调用。

| 资源 | 精确登记位置／边界 |
| --- | --- |
| 主项目／产物 | D:\All projects\ArcheAxis-Knowledge-OS；通过scripts/runtime/dev.py放.project-local/，不写旧.hermes/。 |
| 日常Green | D:\All projects\ArcheAxis.Knowledge.Green-x64，和CI隔离NSIS不同。 |
| 模型库 | D:\All projects\Model library，共享只读，按索引取，不迁移删除或再下载一套。 |
| 共享工具库 | D:\All projects\OS External Configuration，共享只读；工具链子目录10-toolchains，具体位置核manifest。 |
| 真实材料／样本 | D:\All projects\资料库、D:\All projects\ceshi；仅本任务明确批准的隔离样本可用，登记不是内容读取／上传／修改许可。 |
| 资料／兼容来源 | D:\All projects\Record、D:\All projects\Obsidian-Assistance，只按manifest读具体对象，不扫描根目录。 |
| ASTRYN | 旧D:\All projects\ASTRYN及云端NOT_READY_TO_DELETE，AAOS人物适配不证明原资料全迁完。 |
| 其他软件与库 | GPT导出、Claude Code/Cowork、Codex会话只沿本项目索引最小读取，不扫Home或凭据。WORK-LAB／DESIGN-LAB独立，不随本项目授权写入。 |

模型入口docs/current/AAOS-LOCAL-LLM-20261018.md、config/model-profiles/lm-studio.json、scripts/runtime/lm_studio_profile.mjs；既有LM Studio http://127.0.0.1:1234/v1，**不自动回Ollama**。27B MTP／GPU比例／context等按实际profile与加载readback核，不凭历史配置宣称成功或加速，不改Agent provider／endpoint。

当前视觉工具根C:\Users\ALEX\.codex\tools\visual-tool-lab。已装技能C:\Users\ALEX\.codex\plugins\cache\alex-local-tools\visual-audit-tools\1.0.0\skills\visual-project-audit\SKILL.md，先核references/runtime.json实际绑定，读工具README.md、INSTALL-MANIFEST.md、CAPABILITY-MATRIX.md、BROWSER-USAGE.md、PROJECT-GUIDANCE.md及脚本。旧C:\Users\ALEX\Documents\Codex\2026-10-18\codex-codex-ui-ux-work-lab只是迁移来源，不作运行入口。

按当前可用性调用visual-project-audit、ui-ux-pro-max、web-design-guidelines、Playwright、gh-fix-ci、workflow-assistance-github-delivery等。文件存在不代表会话加载，更不代表产品通过；不重复安装浏览器／升级依赖／改全局Skills、MCP、Hooks、PATH。样例browser.mjs只服务样例（41730—41739及profile／输出受限），不改限制接管产品。产品专用脚本、独立profile、空闲127.0.0.1端口、一浏览器一worker，记自建PID／命令／时间，只结束自己的实例。启动前核脚本不会安装／迁移／写真实业务或连正式服务；有副作用就用其他安全路径。

## 七、开源池、会话和历史资料入口

- docs/truth/CAPABILITY_ATLAS_V2.yaml、CAPABILITY_ABSORPTION_REGISTRY.yaml、SUPPLY_CHAIN_LEDGER.json；docs/current/OSS-ABSORPTION-SURFACE-CROSSWALK-20261008.json的68项是混合供体库存，不是已装插件数。
- 历史369池、供体取舍、研究映射的精确链接见闭环定义第八节，不重复搜索／引入。先核许可，不能把源码可见当可商用或改名规避许可；付费能力取合法替代／独立实现或具名延期。
- [UI供体分析](AAOS-OSS-UI-DONORS-20261019.md)：[Neural Creator](https://github.com/Linye-ai/neural-creator-dashboard)、[GlassBoard/win-.-](https://github.com/SENLIN-SAMA/win-.-)、[OpenMAIC](https://github.com/THU-MAIC/OpenMAIC)。重点图谱交互和视觉算法、合法效果还原，复用原renderer与quiz M1，不重做整课堂／多Agent／第二画布。
- docs/current/AAOS-CODEX-SESSION-INDEX-20261018.md、AAOS-SESSION-RECONCILIATION-20261018.md、[39主题原话映射](../history/owner-dialogue-20261019/README.md)是授权脱敏派生物，不是全部私人逐字正文；Cowork完整正文UNVERIFIED，恢复任务包不等于恢复会话。
- 根AAOS-资料索引.md、docs/history/record-archive-20261009/INDEX.md及MANIFEST.json；原始字节.project-local/archives/record-20261009/忽略，不上传。
- docs/history/README.md、repository-consolidation-20261019/MANIFEST.json：旧交接／提示词／摘要／目录按原路径和hash查档，不在原位重建副本；清理先查现有引用及唯一证据，更新活动引用后只处理确证冗余，不删未知文件。
- docs/history/product-loop-20261019/下conversation-closeout.md/.json、conversation-review.md、follow-up.md、verification-index.json、tool-usage.json保留前轮实测与失败；后继决定走活动指针，不让旧“停止新增”覆盖当前指令。

## 八、授权、冻结和未核实尾项

commit／push／PR／merge按活动指针delivery_authorization与当前任务核对；merge须当前审阅及required CI合格，push不代表main已合并。仅上传授权公开源码／文档，不上传密钥、.env、私人会话／记忆、浏览器认证、运行数据库或真实材料。

Owner明确允许D:\All projects\ArcheAxis.Knowledge.Green-x64的**程序文件更新**，无需再问同一路径；授权不是候选资格。先修安装FAIL、核合格候选／成员、目标停止、保全hash标识程序回退；按清单替换并核哈希／启动身份。保留data、根archeaxis.sqlite、backups、用户资产／偏好／未知目录；不偷做真实数据覆盖／不兼容迁移／公开发布／终止未知共享进程。v0.6.14标签不证明当前安装成员一致。

V01暂停，FT01—04及活动指针六项增量冻结，展示蓝图不激活运行。2026-10-19不查额度、不据额度停工；其他日期按当时Owner决定核，不自行恢复监控。已知archeaxis删除返回not_found，不证明截图未命名卡片已删，该身份仍UNVERIFIED，不阻塞产品、不重建定时、不承诺后台工作。ChatGPT账号记忆／个性化没有确认成功，不写已同步；仓库可验证决定与客户端真正加载分别验。

E:/F:默认禁访，读到旧脚本不构成进入许可。不扫Home／磁盘，不改全局账号、模型、provider、认证、网络或服务配置；路径登记不授予跨项目或私人数据权限。

## 九、验证、交付和首次动作

先读canonical gate及变更风险，不默认全仓pytest或npm test。已知入口：项目.venv/Scripts/python.exe、scripts/runtime/dev.py、Windows scripts/ci/run_tests.ps1、Rust scripts/ci/cargo_test.bat（裸cargo可能缺MSVC）；前端manifest的build／tauri走scripts/runtime/frontend.mjs。每次核实际版本／入口，不新装替代环境。

回执示例：`.venv/Scripts/python.exe -B scripts/runtime/dev.py --run-id <唯一ID> -- <确切可执行文件> <相关参数>`，具体门禁以当前manifest为准。权限／锁／编码失败先分类，不改ACL／换身份绕过拒绝。产物.project-local/，公开脱敏摘要按现行目录记录并回链唯一进度，不能覆盖旧FAIL。

每分片写清原问题／预期／实测→必要修改→最小回归，阶段终验再跑规定门禁。全量必须定义边界、用例目标、核心业务／风险、未测；随机点击只探索，有价值问题转为可复现缺陷。截图保存并实际查看，不能仅凭无障碍树、首次基准或工具样例报产品通过。

状态PASS/PARTIAL/BLOCKED/NOT_EXECUTED/UNVERIFIED；证据NO_EVIDENCE/SIMULATED/SYNTHETIC/INTEGRATED/REAL。源码结构、本地单测、浏览器合成桥、真实Core、原生、安装、exact-SHA CI、Owner验收分别报告，失败／取消／required skip不算PASS。记录源SHA／patch、命令、时间、退出码、截图回执、未测与回退。

**首次接手行动**：简短报告现场与本轮UI切片，执行UI-P01，核现有CI失败证据、页面和组件；优先共用壳／窗口与拆分／响应适配／文案诊断／玻璃，逐步覆盖24分片，不拿新一轮长审计或重复全测代替修复。前端交付全部页面覆盖／截图／原生安装结果／接口阻断，再执行15后端分片与J1—J6。结束核diff／status、自建PID与端口，更新唯一执行记录，给下一步和阻断；不能用交接、归档、测试数量或模型加载宣布产品完成。

## 十、补充必须交付：分支合并、体积清理与双端规范

Owner后继明确要求把“分支合并”“体积清理、本地和云端仓库规范化、目录规范化”一并纳入。详细分片第五节RC-P01—08规定逐项验收，继承G01／UF13／交付范围；先只读盘点，UI相关供体按前端顺序吸收，不能让整理变成新的后端优先或无止境审计。

1. RC-P01 动态列本地与**实际远端**分支、PR、worktree、独有提交／修改与归属，保留所有未知脏内容。
2. RC-P02 比较未合入内容、patch等价／squash／cherry-pick、供体效果与冲突；非祖先不等于没吸收，不能盲合旧整包把旧权威带回来。
3. RC-P03 核PR192／193／194重叠，逐项定保留／后继已包含／拆分，合格审阅＋required exact-SHA CI后合入main并复验。不能只push不完成合并，也不能绕过失败强合。
4. RC-P04 合入并证实无独有内容、无占用后，按授权清理确切已合并本地／远端分支和已妥善处理的PR，读回；不删未吸收／未知分支、不改写历史。
5. RC-P05 分开量化源码工作区／tracked大文件／Git历史对象／构建缓存证据／云端CI产物和release，写时间、字节、归属、再生性，不把共享模型资料算可删缓存。
6. RC-P06 清理先列原路径／hash／大小／归档或替代／重建方法；保全独有原件、失败证据和有效回退，只处理核实项目所有且可再生／重复对象。压缩验成员和hash，普通删文件不等于Git历史减小，历史改写未授权。
7. RC-P07 按DIRECTORY_AUTHORITY.yaml和职责索引规范源码／合同／current导航／历史／供体许可／忽略运行产物，更新活动引用、查孤儿旧入口、原位不留第二可变副本，不乱搬不可变TaskPack。
8. RC-P08 分别读回本地／远端／main／PR／release身份和清理前后字节，公开源码文档才同步。云端artifact按证据价值、期限和精确授权处理，保留失败／待审候选；不改可见性、保护规则、付费存储或擅自发布。

2026-10-19后继盘点：实际远端7个heads（含main及sync、character-memory-ui、layout-preferences、closure-integration、remaining-loop-stage1、ui-polish），开放PR192／193／194均Draft；当前checkout唯一登记worktree。大量本地供体不是当前头的祖先，**是否有独有有效改动仍UNVERIFIED**，需查patch，不能立即删除。远端remaining-loop-stage1没有出现在旧tracking列表，证明只看本地引用会漏项。具体头与观察见verification-index的branch_and_repository_normalization；下次接手仍动态核对。
