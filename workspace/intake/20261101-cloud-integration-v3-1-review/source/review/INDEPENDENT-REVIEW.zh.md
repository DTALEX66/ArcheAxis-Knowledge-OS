# v3.1专项独立审阅结论

**可作为与原v3 SHA绑定的定向补件交付。未发现需阻止交付的剩余问题；不构成本地版本适用性或全产品PASS。**

1. 原包与最终主patch身份实际核对；6份中间patch制品分别在精确基线隔离副本应用，与主patch对应文件逐字节相同。不得重复叠加；两个新增测试须单独配套。详情与12次实际应用退出码见handoff目录。hunk呈现不同不等于最终文件不同。
2. detector候选只改2个产品文件，实际模型/config同次读取bytes交给ORT/JSON并生成双hash；缓存返回已加载bytes身份；RLock覆盖完整加载、推理、结果与回执，防并发模型交叉。可执行Python仍由worker自身安装位置选择，不取用户模型目录代码。
3. 已读16项定向、26项shared/transport及47子测试原始结果，未把重复运行累计为总体准确率。另独立运行并发切模型/同路径替换后缓存身份2项，2通过（属于定向测试子集，不新增计数）；独立将v3→v3.1 patch应用到原v3两个文件副本，产物与被测候选字节一致，退出0。证据detector-independent.*和independent-candidate-checks.json。
4. reproduce候选RUN/cd失败停止；每次新run、partial锁导出验证、不继承system site的venv、前置失败阻断依赖门、独立gate失败汇总返回非零。已读8场景/8独立run、missing-repo证据，确认被测fixture脚本与交付候选hash一致；另独立bash -n退出0。明确这是控制流stub实验，不是全业务重跑。
5. 实际shared/config函数探针确认ARCHEAXIS_DATA_DIR配置被读取；pytest conftest后续改为自身新run/tmp临时目录仅做源码核对。不存在“已证明所有数据始终在wrapper/data”的夸大；旧reproduce.sh系统包继承及固定输出风险未被单文件候选自动修复。
6. 根README正确区分MISSING历史stdout与新运行证据、原模板字节、原包不可改、detector增量基于v3最终源码、reproduce增量基于旧harness脚本。外部模型profile不是认证来源/版本，双hash也不证明准确率。

本地70dfc397的13个不适用路径仅按用户反馈记录；未读取本地源码、未给出伪造冲突列表、不要求回退/整文件覆盖或再次全量审计。相同范围继承云端证据，确实改变/环境特有处做针对性验证。
