# 文字实践记录可直接接收人工反馈

此前Observation可保存纯文字实践记录，但Feedback只能挂Delivery。尚未接纳的知识会被Delivery准入拒绝，因而“先保存文字，再人工反馈”必须伪造交付或被阻断。现在沿既有append-only教学记录允许Feedback的parent为Observation或Delivery；反馈后可显式追加Revision，不新建类型、表、API或Runtime。

这项反馈只是人工内容，仍为`not_scored`。Mastery是反馈分类，不能凭分类、自报或AI输出自动推断掌握；knowledge保持candidate，assessment/rubric不会自动出现。原同课程、知识版本、assessment引用、人类权限、隐私、撤回和导出规则继续检查，Delivery仍须当前accepted或personal知识，不从本修补绕过。

只部署新测试的两个正式RED都复现原断点：domain返回非法parent，API返回422而非201，child/receipt均101、源码一致。仅改parent匹配后，完整domain teaching_records **21通过**、API teaching_state_api **10通过**，三改动文件rustfmt检查0；三个GREEN run均actual/wrapper0、源码一致。绑定HEAD `aab6c27d69d564bf5e1d0691ba4c228207670f56`＋dirty patch `7ebaaee818e89aa5253123e81303adef9a511272d9848e518d27dd668f6c43da`。[24份证据、原RED与源码身份](FEEDBACK.json)保存在本仓索引；载荷和日志仍为ignored。

新旅程验证candidate知识下文字记录→人工反馈→显式计划修订；原字节与内容hash冷回读、重复提交/异内容冲突、撤回后历史保全及拒绝新子记录/导出。domain把原export链导入另一个真实文件workspace并冷启回读；API用实际Router/Store验证原workspace重开和重复import。课程注入、知识混绑、缺assessment、将文字记录当TeachBack、机器/缺失principal等负控均拒绝。最终knowledge仍candidate，learning_events、learning_assessments与jobs均0，没有专业工具执行、模型调用或自动掌握/晋升。

独立静态审阅未发现P1/P2，没有删除旧Feedback(parent=Revision)等反例。准备时格式器先按2021 edition运行，随后依两个crate实际2024 edition重格式化，正式RED/GREEN均在最终格式下执行；原补丁及最终文件身份分列，未将准备命令当产品资格。

本次复用既有共享Cargo target及离线依赖，未复制runtime。大写入前后各一次全仓测量均PARTIAL/child1：可读下界142,277,318,793→142,280,381,205B，窗口差3,062,412B、build类差2,142,316B；674错误/243私有排除/581布局项保持，NO_NEW_GROWTH_TRIGGER不改变旧预算债。该非原子读数不等于物理占用或本命令精确生成大小；后续文档/门禁未计入这对读数。

这只取得当前源码domain及进程内API有限行为资格：使用隔离真实SQLite文件，未运行新standalone Core二进制、真实socket、安装态、UI或Owner验收；旧bpr1/混合候选不移绑新源。专门开始/自报状态、独立mastery、第二产品消费者、完整R6/F05/J1/CL仍未资格化。原R6 E01—E10、R5验收与静态186/22快照保留原时点。[唯一执行记录](../../current/AAOS-UI-FIRST-EXECUTION-20261009.md)维护接续。

回退只撤回本次父类型放行及新测试，不删除已保存记录；若已有新形态记录，须先评估旧源码对其新增/交换消费的限制，不能通过清库回退。没有schema迁移或对真实库的写入。
