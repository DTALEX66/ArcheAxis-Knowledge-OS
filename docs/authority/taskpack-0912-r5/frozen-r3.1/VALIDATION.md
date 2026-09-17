# R3 包结构与破坏样本校验结果

日期：2026-09-08。环境：Python 3.12.13，Linux，标准库。

R3.1原包校验通过；20项破坏/语义漂移样本均按预期拒绝。JSON语义破坏样本重新计算测试清单，确保不仅靠hash检查拦截。它们在独立临时副本操作，未修改产品代码或用户真实数据。

验证：23任务及原依赖/条款保留、29功能、26验收场景、16CAP、16格式、11增强、C01—C10和G01—G14映射；未来仍冻结，未伪造授权或实现。8份源快照已对照GitHub返回的git blob SHA验证字节一致。

|测试|预期|实际|
|---|---|---|
|original_package|PASS|PASS|
|lost_migration_slice|REJECT|REJECT|
|lost_task_migration_binding|REJECT|REJECT|
|missing_companion|REJECT|REJECT|
|changed_bytes|REJECT|REJECT|
|lost_task|REJECT|REJECT|
|lost_original_acceptance|REJECT|REJECT|
|changed_dependency|REJECT|REJECT|
|false_done|REJECT|REJECT|
|future_unfrozen|REJECT|REJECT|
|false_authorization|REJECT|REJECT|
|lost_feature|REJECT|REJECT|
|unknown_feature_parent|REJECT|REJECT|
|unknown_case_reference|REJECT|REJECT|
|lost_capability|REJECT|REJECT|
|lost_format|REJECT|REJECT|
|lost_enhancement|REJECT|REJECT|
|fabricated_test_pass|REJECT|REJECT|
|unlisted_extra_file|REJECT|REJECT|
|manifest_path_traversal|REJECT|REJECT|
|invalid_utf8|REJECT|REJECT|

MANIFEST不包含自身hash，不是数字签名。若同时恶意修改文件与校验器/清单，不能提供真实性保证。校验器只读；部署、Windows运行、产品回归、实际磁盘释放均未在本轮执行。
