# 重复import与漏检根因：已复现

本轮纠正先前“可应用”判断。旧冻结10文件及其patch/manifest/日志均原字节保留，不能再作为推荐应用候选；新目录只有vite.config.ts删除6条重复import，另外9候选字节不变。

1. 旧prepare.py每次执行都对已转换candidate中的react import追加guard import，非幂等；run_checks.py每轮先调用prepare，因此7轮累计7条。冻结前只做hash相等性，没有检查import唯一性。
2. 不是用另一个单import镜像冒充交付：旧冻结candidate与旧mirror目前均be224eab3c4a8f4078d0c539477fa92165b69f76ca8a48bb223fdfba97f1a812。本轮在自有镜像装入精确该字节，真实Vite loadConfigFromFile仍成功。这是转译器接受重复相同import的行为，配置加载成功不能替代TypeScript绑定诊断。旧日志没有每步hash，不能事后声称证明了旧执行瞬间字节；旧最终readback只证明了冻结终态相等。
3. 本轮对相同字节用TypeScript实际编译得到7条TS2300 Duplicate identifier。原frontend/tsconfig.json只include src，根本没检查vite.config.ts。旧page17用了自有Vitest config，page17通过也不构成产品Vite配置TS验收。
4. 新prepare一次性创建，已有proposal时拒绝再次运行；run_checks不再调用prepare。修正仅删除6条重复行，单import配置SHA见ROOT-CAUSE.json。所有11个实际检查在前后对全部10个final candidate及mirror逐hash相等，绑定到初始化CANDIDATE-HASHES.json，不修改或重新生成候选。Vite正/负/恢复工具自身也记录全10文件前后hash。
5. 新增真实配置单独tsc --noEmit（allowJs推导现有mjs；不跳过TS2300），结果PASS；保留src全套TS和所有消费/语义测试。ROOT-CAUSE.json记录精确旧candidate/旧mirror/复现actual_tested/new/restored hashes及7条原始诊断；root-cause-frozen-config.log保存命令输出。复现仅在本目录镜像替换并finally恢复，不改冻结目录。

该缺陷来自本提案准备/验证设计，应由本agent承担；先前未发现重复import的交付结论撤回，新回执独立计数。未跑全构建或远端CI，不以新局部PASS替代原生运行、许可或Owner验收。
