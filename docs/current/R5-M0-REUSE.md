# R5 M0 供体与来源登记

[机器记录](R5-M0-REUSE.json)包含12组、19个源文件版本，以及215条V15来源定位。
每项绑定实际SHA256、HEAD blob、调用方、目标、行为差异、证据及退役条件。
基线为`c06b234ca335b9cbb2c1fde270851e2390c36b89`加本轮明确记录的diff。

这是有剩余项的复用登记，不是全体旧资产语义审查通过。记录中的部分审查状态保持PARTIAL；
只有调度供体已在本批阅读全文并核对所列行为。LEGACY_MANIFEST的1246项保持原状态，
不根据此表删除源代码或把旧实现批量标成ABSORBED。

## 实际调用边界

- Rust Core在启动claim提供worker profile时启用executor；没有profile时运行projection路由。
- 正式Avalonia的MainWindow已通过WorkerProfile向Supervisor传入CoreTextWorker；同加载器真实Core/Python链路通过。
  窗口主体仍是`Welcome to Avalonia!`，尚无默认学习交互，不能用构建/配置通过代替完整Windows导入闭环。
- text/PDF/OCR保留为受控Python计算层；FSRS继续复用，Rust负责持久化。
- MCP、core_client、journey_panel是当前项目侧适配器；panel HTTP通过不等于DeepTutor内部挂载。
- 旧DeepTutor bridge的当前已定位消费者是integration导出和legacy测试，不是旧表所说的learning API。
  bridge除只读投影外还通过legacy event_store追加候选事件，不能接到vNext数据库形成第二写者。
- 旧due_queue/Anki-Zotero及其余M1资产保留；未确认活跃调用不等于可以删除。

## V15来源资格

冻结RESEARCH-ADOPTION中的40方法、35研究、36学科、104资源全部保持候选；
登记键含`learning-v15@source_package_sha256/类别/source_id`，并带原文件JSON pointer。
原V15包哈希来自冻结R5声明，本批未重新读取原V15包；冻结R5文件本身的SHA256已实算。
这只解决来源定位，不替代X04/X05的运行时导入幂等、不同版本隔离、修正追加和历史资格实现。

## 本批验证

`r5-m0-pdf-ocr-reuse`：28 passed，包含真实原生PDF/阅读顺序/结构及PDF、OCR sidecar。
`r5-fsrs-validation-green`：20 passed，修正显式无效rating被correct覆盖、非对象state被当新卡、
非有限浮点进入算法的问题；对应RED为12失败，未改FSRS算法或数据库接口。
`r5-m0-registration-verify`：12组文件哈希匹配、215定位键唯一、全部候选，exit 0。
完整命令与各自限制见[R5执行台账](R5-EXECUTION.md)。外部许可/完整桌面发行资格仍按独立交付层验收。
