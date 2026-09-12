# X00-01 R3.1 → R5 差分

基线 `c06b234ca335b9cbb2c1fde270851e2390c36b89`；树 `281255538ee3d4a4235facfddaf01d2b97d406ba`。只读代码/收据核查，不是产品验收。

原收据全文继续位于0910 STATE/EXECUTION；JSON保存原状态与证据路径hash/最后修改提交，后者不作为测试SHA。

## 原23任务

|任务|状态|复用来源|具体缺口|
|---|---|---|---|
|X00 基线、冲突裁决与唯一任务入口|PARTIAL_NEEDS_WORK|R00|R5尚未安装；语言索引/验证策略仍指0906。必须更新唯一入口并保留0910证据；HL01来源版本/资格导入未测。|
|X01 运行路径止增、浏览器失败与关键 CI|PARTIAL_NEEDS_WORK|R01|dev.py隔离根已实现；异常/取消/并发/真实浏览器全路径差分及容量预算仍需定向验证；远端CI未查询。|
|X02 旧资产保全与当前能力的语义复用|PARTIAL_NEEDS_WORK|R07|1246旧资产仍为INVENTORIED_NOT_SEMANTICALLY_REVIEWED；M0供体需逐调用链语义复核和来源hash；未知私有状态保留。|
|X03 现成学习工作台资格与默认入口|PARTIAL_NEEDS_WORK|R10|项目侧journey_panel存在；DeepTutor默认入口挂载/产物回收未闭合，先定稿项目侧宿主方案，不修改外置上游。|
|X04 跨语言真实契约及身份语义|PARTIAL_NEEDS_WORK|R04|启动角色枚举拒绝与会话覆盖已实现；宿主持有的人/机身份签发待定稿。learning-feedback/v1 additionalProperties=false不能承载新增曝光/原回答版本语义。结构寻址契约亦待定稿。|
|X05 Rust原件、事务、作业与恢复底座|PARTIAL_NEEDS_WORK|R02,R03|审校事务、CAS/作业与v3 10/11/12/13表恢复存在；R5学习字段、来源命名空间、修正追加与归档仍需实现/验证。|
|X06 复用workers贯通首批真实格式|PARTIAL_NEEDS_WORK|R08|已有Core-worker路由和PDF/OCR/HTML接线；动态网页实时抓取、结构定位、复杂样本质量与真实模型资格未闭合。|
|X07 质量、公开核查、知识修订和搜索|PARTIAL_NEEDS_WORK|R02,R06,R08,R09|修订/撤销及公开检查probe已有；云端逐主张核查需配置及预算；HL02关系/阅读深度和HL10研究更正影响未测。|
|X08 人类学习侧复用与事件回收|PARTIAL_NEEDS_WORK|R05,R09,R10|学习幂等、FSRS适配和卡片引用已有；无card_state仍可走旧阶梯。真实曝光/题目修正/样例/交错/讲回/负担/互动及离线恢复未完成。|
|X09 机器知识、真实调用、评测与反馈|PARTIAL_NEEDS_WORK|R09,R11|真实MCP SDK客户端和未见例评测已实现，不能回退成完全没有；原任务全部方法类型/纠错后真实客户端资格及R5研究更正链未测。|
|X10 旧库非空迁移与无损差分|PARTIAL_NEEDS_WORK|R03,R07|非空合成迁移已有；附件/关系为损失记录、时间未保留。新学习字段需补兼容，真实用户库资格需精确授权。|
|X11 Windows人机闭环候选与可用包|PARTIAL_NEEDS_WORK|R10,R11,R13|Core候选hash绑定/验证已有；完整worker/宿主依赖、Windows非开发机GUI闭环、重启恢复、安装签名卸载未闭合。|
|Q00 独立GPT审计M0|BLOCKED|R14|独立M0审计尚未执行；需要同候选完整G01-G14原始证据，执行者不得自签。|
|X12 多格式完整覆盖与学科活动|PARTIAL_NEEDS_WORK|R15|当前格式记录0 complete/14 partial/2 custody-only；目录续跑驱动已有但非UI入口。全格式链、真实Vault客户端往返、三个主题未验收。|
|X13 全仓规范化与必要交付体验收口|PARTIAL_NEEDS_WORK|R00,R15|仍有69条历史未归属记录；全仓语义归属/默认入口/依赖与安装体验尚未收口。|
|X14 本地50多GB保全清理与容量止增|PARTIAL_NEEDS_WORK|R01,R12|已有清单而未删除；不能沿用6.877GiB预计值为释放量。需更新互斥容量/生产者/保全/逐路径授权/删除后复测。|
|Q01 独立GPT审计M1及清理结果|BLOCKED|R16|受Q00、X12、X13、X14前置约束；当前不具备独立M1资格。|
|F01 视觉教学、动画与交互仿真|DEFERRED_RETAINED||原文与依赖保留，未激活。|
|F02 大型知识宫殿与2D/2.5D/3D/VR/AR|DEFERRED_RETAINED||原文与依赖保留，未激活。|
|F03 完整人机学习、经验迁移和可选微调|DEFERRED_RETAINED||原文与依赖保留，未激活。|
|F04 多端同步、SDK、扩展和可选协作|DEFERRED_RETAINED||原文与依赖保留，未激活。|
|F05 研究课程项目工作空间与图谱纵深|DEFERRED_RETAINED||原文与依赖保留，未激活。|
|F06 吸收失败后的必要独立实现|DEFERRED_RETAINED||原文与依赖保留，未激活。|

## 42专项

|专项|归属|状态|具体差分|
|---|---|---|---|
|CLEAN01 确认范围与磁盘基线|X00,X02|PARTIAL_NEEDS_WORK|本轮核根/分支/卷；未全范围计量，外置根只按资源索引定向使用。|
|CLEAN02 完整体积与大文件盘点|X02,X14|PARTIAL_NEEDS_WORK|旧逻辑容量不可当当前物理占用；互斥分类、硬链接去重、分配大小未测。|
|CLEAN03 外溢数据追踪到生产者|X01,X02,X14|PARTIAL_NEEDS_WORK|dev.py可定位工具环境生产者；跨入口真实输出与未知外溢归属需补证；私有代理状态不扫描。|
|CLEAN04 先修写入路径与持续增长|X01|PARTIAL_NEEDS_WORK|已有dev.py隔离实现；需启动/解析/测试/打包失败取消的同范围前后差分。|
|CLEAN05 唯一资产保全与恢复抽查|X02,X10,X14|PARTIAL_NEEDS_WORK|归档/合成迁移已存在；真实资产保全与恢复抽查未授权未测。|
|CLEAN06 重复文件与多份缓存辨别|X14|PARTIAL_NEEDS_WORK|重复候选的引用/版本/重建及硬链接核验未测，不能按同hash删除。|
|CLEAN07 清理预演、隔离与精确执行|X14|PARTIAL_NEEDS_WORK|旧R12清单为预演；逐路径执行未授权，.zcode用途未确证不得删。|
|CLEAN08 释放空间与功能回归|X14,X11|PARTIAL_NEEDS_WORK|未删除，因此净释放/受影响运行回归NOT_RUN。|
|CLEAN09 容量预算与保留策略|X01,X13,X14|PARTIAL_NEEDS_WORK|按生产者预算、超限诊断和重复运行峰值尚未验收；不硬凑GB阈值。|
|CLEAN10 Git与交付包瘦身|X13,X14|PARTIAL_NEEDS_WORK|候选白名单/防夹带已有；Git对象、LFS、开发依赖误打包及包瘦身未核。|
|REPO01 唯一规范与任务状态|X00,X13|PARTIAL_NEEDS_WORK|当前0910入口与语言索引/验证策略0906指针冲突；R5安装登记待做。|
|REPO02 全仓归属和旧资产复用|X02,X13|PARTIAL_NEEDS_WORK|历史69路径归属缺口和1246资产未语义复核，不能批量标吸收。|
|REPO03 依赖构建发布一致|X01,X11,X13|PARTIAL_NEEDS_WORK|候选Core同源hash已有；完整Windows依赖/许可/SBOM/干净环境/CI未测。|
|REPO04 默认启动和安装可用|X03,X11,X13|PARTIAL_NEEDS_WORK|默认宿主接线与完整GUI启动/退出/恢复待补，Core启动不是桌面闭环。|
|MIG01 逐模块迁移台账|X02,X04,X13|PARTIAL_NEEDS_WORK|语言职责已有；逐模块源hash/调用者/目标/退役条件需补齐。|
|MIG02 Rust领域权威真正接管|X04,X05,X07|PARTIAL_NEEDS_WORK|知识修订事务和角色校验已有；新主张关系及身份签发契约待定稿。|
|MIG03 跨语言实际接线|X03,X04,X06,X08,X09|PARTIAL_NEEDS_WORK|Core-worker/MCP接线已有；受信UI曝光、兼容事件与默认宿主仍缺。|
|MIG04 数据迁移、旧权威退出与回滚|X05,X10,X11,X13|PARTIAL_NEEDS_WORK|v3恢复/非空迁移已有；默认旧入口退出、新字段、真实库资格/Windows恢复仍未闭合。|
|GOV01 唯一规范与活动入口|X00|PARTIAL_NEEDS_WORK|同REPO01；当前检查仅发现指针差异，不证明所有守卫已生效。|
|GOV02 开发运行目录执行治理|X01|PARTIAL_NEEDS_WORK|dev.py设置工具级路径且拒绝链接；中文路径/并发/取消/浏览器实际差分待测。|
|GOV03 源码与资产归属盘点|X02,X13|PARTIAL_NEEDS_WORK|同REPO02；未知项保留。|
|GOV04 清理、容量和防止再增长|X14|PARTIAL_NEEDS_WORK|同CLEAN07/08；未实际释放。|
|GOV05 依赖、构建与发布一致性|X11,X13|PARTIAL_NEEDS_WORK|同REPO03；Core目录包不是完整非开发机可用包。|
|LANG01 语言边界和迁移范围冻结|X00,X02,X04|PARTIAL_NEEDS_WORK|既定Rust/Python/C#/Web职责可复用；逐资产迁移台账未全部闭合。|
|LANG02 把领域权威从旧实现迁入Rust|X04,X05,X07|PARTIAL_NEEDS_WORK|Rust审校事务/权限已有；真实主入口全链与R5新增领域规则需验证。|
|LANG03 Python保留为受控能力层|X02,X05,X06,X12|PARTIAL_NEEDS_WORK|12 worker/10路由历史记录可复用；取消重试和全格式资格不可据probe直接通过。|
|LANG04 C#宿主和Web学习界面承接|X03,X08,X11|PARTIAL_NEEDS_WORK|项目侧面板已实现；默认DeepTutor挂载和真实学习回流待补。|
|LANG05 跨语言契约与语义迁移|X04,X08,X09|PARTIAL_NEEDS_WORK|旧事件幂等已实现；跨语言新版本/曝光/可信身份语义待冻结。|
|LANG06 数据与旧备份迁移|X05,X10|PARTIAL_NEEDS_WORK|v3多表历史布局恢复存在；新字段/真实库附件和关系完整迁移未证明。|
|LANG07 旧入口退役和迁移终验|X02,X11,X13|PARTIAL_NEEDS_WORK|旧入口退出/真实新入口/兼容回滚尚未汇合，不能按Rust占比验收。|
|HL01 对话连续性、来源导入与历史资格|X00,X02,X05|PARTIAL_NEEDS_WORK|原包研究素材仅为来源；来源命名空间/版本/重导不重复/历史资格行为未测。|
|HL02 逐主张证据关联与研究使用边界|X04,X07|PARTIAL_NEEDS_WORK|现有knowledge/anchor基础可复用；claim-研究-定位关系和阅读深度独立字段未验收。|
|HL03 提示、作答与学习事件契约|X04,X05,X08|PARTIAL_NEEDS_WORK|旧键+payload_hash重放冲突已有；提示曝光/允许工具/答案曝光/评价来源/版本字段在生产v1缺失。|
|HL04 提取反馈与实际学习活动|X08|NOT_TESTED|需要真实主题提取-反馈-纠错和坏题暂停评分；现有面板不证明此链。|
|HL05 样例、缺步与提示撤除|X08|NOT_TESTED|完整例/缺步/独立变式及提示转换记录未测。|
|HL06 交错辨别与变式选法|X08|NOT_TESTED|易混类别选择方法与执行分评未测，不能用一般测验代替。|
|HL07 讲回、信心校准与独立测验|X08|NOT_TESTED|讲回条件/信心/隔离答案的未曝光测验未测。|
|HL08 复习负担、卡片质量与方法停用|X08|PARTIAL_NEEDS_WORK|FSRS worker已接；旧阶梯仍可达，四档原评分/参数版本/负担坏卡暂停待补。|
|HL09 学科活动、表征与空间助记|X08,X12|NOT_TESTED|至少一个现成互动和三主题实际事件回收未测；大型3D仍冻结。|
|HL10 研究更正与人机双侧影响|X07,X08,X09|PARTIAL_NEEDS_WORK|知识撤销/卡片引用可复用；研究更正→题目/方法影响及真实人机再测未闭合。|
|HL11 学习资产离线、导出和恢复|X05,X08,X10,X11|PARTIAL_NEEDS_WORK|旧归档底座已实现；卡片引用未纳入归档，新曝光/修正/版本字段与离线重发待补。|
|HL12 产品验收与学习效果分别证明|X11,Q00,Q01|PARTIAL_NEEDS_WORK|必须把产品机制与学习效果分开；当前Windows同候选及独立审计未完成。|

## 下一步

X00-02：按原字节安装R5，仅定向更新当前入口，另建进度侧车，原TASKS与历史证据不改。随后X01-01和X02-01；X04-01契约不需等待X08完整闭环。

已实现且可复用的具体子项：Rust不可变正文/审校事务、v3历史布局恢复、键与payload冲突检查、真实MCP SDK接线。只对这些窄范围复用历史证据，不把整个父任务标完成。

仍需定稿：可信人/机身份签发、学习事件版本与曝光、结构寻址、默认宿主。需资源/额外范围：完整测试解释器、真实模型/OCR资源、云端预算与产品内配置、真实库迁移、逐路径清理、Windows视觉操作和独立审计。

本轮未运行产品测试/构建/网络/清理；基础Python 3.12.13可用，但其pytest/jsonschema缺失，不代表产品失败。

回滚：仅ignored证据产物，无产品改动需要回滚。
