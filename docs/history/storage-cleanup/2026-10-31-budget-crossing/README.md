# 类别预算新增越线：有限反例与实际源码验证

修复 `storage_report.growth_review` 的类别预算漏报：存在baseline时，原逻辑仅用总净增超过2GiB或新布局触发复核，会漏掉由其他类别减少抵消的“某类别首次越线”。现在比较baseline已超预算类别与当前类别，只对新增超预算类别触发审查，旧债与消债不新增触发；不改变阈值、目录豁免、测量或删除权限。

规则依据为 `docs/DIRECTORY_AUTHORITY_INDEX.md` 生命周期第3条：既有预算是复核线，新增规范外路径和净增超过2GiB“同样”触发。baseline承接已知旧债，不意味着屏蔽新类别预算。

## 反例的证据边界

原 `spr-size5` v2快照原字节与SHA保持不变，measurement仍PARTIAL。只在内存副本中，把build提高至22GiB+1字节，runs相应减少，构造总增量0；没有在磁盘制造大文件、真实减少runs或重新计量全仓。该delta0是反例输入，不是当前磁盘观察。

baseline超预算类是 `candidates/、runs/`，反例增加 `build/`。原growth返回NO_NEW_GROWTH_TRIGGER，旧main在注入同一测量副本时退出1（保留原布局/计量未覆盖）；修复后实际growth返回REVIEW_REQUIRED、新预算类仅build/，实际main退出2。外层断言wrapper/dev退出0，不能把main的2记作失败或完整测量PASS。

旧债不变与消债对照均无新增触发；foreign/v1 baseline仍拒绝。既有旧债测试补全baseline中已审runs超预算记录，保留原NO_NEW断言；新增baseline缺类别证明时不隐藏当前债的对照。

## 实际源码验证

实际源码HEAD `e792dadc062033a93914b433278cd1a41b6d368b`，dirty patch SHA `4e1a53deae95f1df0370d3a6e42a47f889f4ebae5131685cfb4987fe21992c7e`，前后一致；source/test文件SHA见MANIFEST。实际正式测试路径运行28项，通过、退出0，没有替换为ignored候选；有1条既有cache_dir配置警告。Ruff现有最小门槛退出0。

此前 `nrm-grow2` 是ignored候选验证；本次 `nrm-gactual1` 是部署后正式源码验证。两者都仅使用内存反例和测试自有小fixture树；不构成当前全仓体积、VM/API/模型、安装或Owner验收证据。`nrm-grow1` 因候选相邻dev.py加载位置失败的原收据保留，未作成功证据。

当前r6n1/r6n2等metadata在合法worktree/run内，不能当布局债；本次修复正是覆盖这类规范输出的类别预算信号。没有清理或迁移旧目录，也没有修改原snapshot的PARTIAL。
