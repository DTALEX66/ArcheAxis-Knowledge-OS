# 扩大验证：最终结果与可继承边界

本页对应用户追加的“能执行的全部执行好”；是仓库已有验证的扩大执行，不是把186项变成186套开发/安装任务。原始失败、修复候选和重跑日志全部保留。**全部适用回归通过不等于全部产品能力已集成。**

## 已完成的核心结果

| 验证 | 最终实际结果 | 资格 |
|---|---:|---|
| Python tests + knowledge_base/tests + integration-tests | **5780 passed，105 skipped，4 deselected；379 subtests passed；0失败/错误，465.28秒** | 最后固定候选；4项浏览器真实阻塞不再重复执行；H01材料测试另列 |
| H01可独立运行的归档/路径保护 | **11 passed** | 原材料无关；另12项依赖缺失的owner原材料，不声明通过 |
| Rust workspace | **208组，1025 passed，0 failed，0 ignored** | Linux Rust/Core；不是Tauri/Windows。末次仅测试输出目录修正，同一target 2/2复验；未变范围继承 |
| 全前端Vitest | **189文件通过、2文件跳过；1983 passed、4 skipped** | jsdom，非真实浏览器；opt-in集成占位不算通过 |
| 实际生产组件→真Core | **8 passed** | 真实HTTP、SQLite/CAS、进程重启、冲突拒绝、恢复；独立于fixture测试 |
| 双提供方/格式/恢复矩阵 | **25/25** | 双页PDF、实际pypdf升级/回退、原件与产物保存，不外推表格/OCR准确率 |
| 独立worker unittest | **207运行、203通过、4跳过** | 与Python主套件有交集，不能累计为新增207能力 |
| 独立contract --noconftest | **258 passed，29 subtests passed** | 与Python主套件有交集 |
| 静态及生成合同 | **22/22命令；preflight 19/19** | 最终独立审计；含34个route-inventory测试，不重复计数 |
| Python 3.11.17 / 3.13.5兼容 | 各compileall成功、各7/7 imports | 最新锁下独立copies venv，不是这两个版本都跑全Python套件 |
| 生产前端build | 退出0 | TypeScript+Vite，保留大bundle警告；非原生安装 |
| 当前run vNext receipt | 退出0 | 原12步in-process、模拟worker回执；绑定真实dirty patch，不包装为正式commit/installed资格 |

逐项机器可读结果：`full-validation-results.{json,csv}`。最后Python JUnit为`evidence/python-delivery.xml`；105项是全套当次skip，不是最终全部未验：随后42项定向补过、63项仍有明确条件限制，见`skip-closure-results.{json,csv}`。不把补测和主套件重复相加。105项原始理由逐条保存在`../logs/full/python-delivery.stdout`。没有把skip、环境拒绝或模型自报置信度计为验证成功。

## 为什么不是直接转交本地再测

完整执行找出了并在云端解决了真实问题：
- 原检测worker在Core的staging cwd下无法导入`shared`，却误报缺onnxruntime。现在只从worker自己的安装位置加载现有成熟检测实现；实际外cwd、无PYTHONPATH、恶意model-root输入测试均通过，不放宽沙箱。
- 基线sleep-loop用本地naive时间写租约、SQLite用UTC判过期，非UTC机器会立即lease_lost。仅设TZ=UTC曾能过37项，但未把这当修复；现在持久化/比较统一UTC，夜窗仍本地，UTC/Phoenix/Shanghai各38项通过，过期token拒绝保留。
- 原锁适配器组有真实安全公告。最小兼容锁变更6包：brotli1.2.1、cryptography50.0.0、filelock4.2.1及父依赖pyopenssl26.4.0、python-discovery1.9.0、virtualenv21.14.5；pyproject未改。保留solver UNSAT和原漏洞证据，没有忽略漏洞强过门。
- 安全锁变更使资源旧锁来源失效。严格证明4个被引用包完整条目未变，仅重绑8处来源；68行资格state/value不提高，使用原生成器更新资源目录。unreleased manifest仅同步真实锁摘要，没有冒充发布。
- 全前端发现旧导航测试期待残留；改成最新五入口并保留明确按钮数量/角色断言。Rust Windows路径fixture改为平台对应绝对路径，并追加Unix拒绝Windows盘符，产品安全规则没改。
- 本轮初始临时路径不符合项目规范、浅历史/未取分支对象、固定handshake run ID导致重复运行冲突，都已真实修正并补测。未通过修改权威材料或删除历史来凑绿。

最初旧锁Python：5756通过、36失败、12错误、105跳过。中间新锁批次：5771通过、2失败、7错误。它们是**保留的失败轮次**，不是最终通过数，也不能与最终数相加。

## 安全与安装资格

`security/FINAL-IMPLEMENTATION.zh.md`记录主锁与候选完全相同、主venv实际修复版本及pip check；相同冻结导出继承严格pip-audit无已知漏洞的结果。最终gitleaks工作树与全部已取refs扫描无命中。Rust两锁没有改变，保留root 1项/Tauri 8项警告；退出0不等于零风险。

Installed wheel使用真正构建、独立安装、离源码运行、迁移、API上传/任务读回和新进程SQLite检查。最新wheel内置锁摘要与实际锁一致。原CI在pip check后剥离setuptools，却留下声明依赖它的ctranslate2；补测发现post-strip依赖图不闭合。该原始失败仍保留；已在隔离CI中最小修正为保留setuptools，post-strip `uv pip check` 114包兼容且原离repo smoke通过；主4文件CI回归87/87，详见`review/wheel-smoke-retain-setuptools.md`，不引用“卸载前pip check”冒充卸载后健康。实际ASR推理、模型权重与质量没有测试。

## 明确不能继承为通过的部分

1. Chromium Unix socket被拒绝；CUA浏览器不能到达独立执行namespace的服务。没有伪造截图、多视口、IME、键盘/读屏真实视觉验收。
2. 当前Linux容器不是Windows Sandbox宿主；无可用KVM/已装QEMU/Windows介质或已连接Windows桌面。理论TCG不能当实际Windows资格。详见`windows-feasibility/`。
3. H01原owner材料不可用/来源边界拒绝；12项无法执行。已经能独立跑的11项安全保护测试仍执行了。
4. X8真实同次修订综合观察仍发现研究/AI统一currentness投影缺口。测试13项通过是证实该观察，不是业务缺口已修。不能把resolved说成当前或已核验。
5. 旧非UTC数据库的naive租约无法靠新库测试证明迁移安全；正式升级须停止、备份、处理未决租约与写操作，不猜历史时区或静默续约。
6. 检测器默认模型路径真实验证；非默认外部模型选择与receipt模型hash对应的风险仍需定向解决。不是默认成功即可推广任意模型路径。
7. H5P播放/xAPI、真实外部练习结果、本地LLM消费、Windows安装/设备和全部22格式/37平台均未被小样本替代。研究发现成熟方案，不等于已装已集成。

## 本地免重复与失效规则

详见`HANDOFF-NO-REDUNDANT-AUDIT.zh.md`。本轮不要求本地Codex重新做同一源码/锁/配置的通用全量审计。可以直接继承有hash和原始日志的范围；必须保留真正的环境差异、未完成能力，以及后续代码改动触发的定向验证。

## 可解skip补验，不把条件缺失全推给本地

- Core路径/平台后缀修正后原7项通过；Win32 CIM的6项仍必须Windows。
- 公共Crossref DOI/Wikidata QID真实请求成功，原2个网络skip关闭；只是已知标识的元数据，不是自主全文查证。
- 现有Tesseract5.5.0+eng原7文件44通过/4仍skip，关闭23个原skip；中文PNG/JPEG/扫描PDF两页另做4个实际OCR输入，英文public profile实际通过，不冒充原Windows注册测试。
- antiword0.37、官方Tika4.1.0/Java、现有ffmpeg：33项中32通过/1注册配对skip，关闭5个原skip。ffmpeg为真工具，ASR stub明确不是转写模型运行。
- 官方Linux PowerShell7.6.9便携包校SHA后，5个原C#行为skip实际通过；相应4文件22/22，未装完整SDK、未假称Windows桌面。

余63个原skip逐条保留原因：Windows/Win32/junction/本机安装/原模型与资源声明/特定用户PDF等。大型ASR权重未为清零skip临时替换；H5P浏览器和真实图形宿主阻塞仍在。

## 最后6文件变更的继承边界
完整Python固定候选后，仅`.github/workflows/ci.yml`的runtime依赖保留步骤，以及5个Core探针/测试的可移植路径发生变化。其余5123个已记录文件未变化；当前完整源码哈希见`config/delivery-source-hashes.json`。这6文件另有CI87项、Core7项及最后22静态门补测，不宣称5780项是在修改后的每一文件上再完整跑过。生产Core/前端组件未因此改动。最终31个tracked文件和2个新增真实Core测试，补丁在新基线worktree实际应用后5129文件逐字节匹配。

完整存储盘点工具保守地跳过敏感命名合成安全fixture/其他登记worktree，给出PARTIAL而不是全盘字节扫描通过；布局本身无out-of-layout，未为清零状态读取被排除内容或删历史。
