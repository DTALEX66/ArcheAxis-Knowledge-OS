# AAOS v3.1 定向补件

本包绑定原交付 `AAOS-Cloud-Integration-20261031-v3.zip`：
`de984bf8917d24f4bc837221f76983dde20973f8285808e1fa6c351a5c68ac43`。
原 v3 不变。本包不是完整新版本、不是本地 70dfc397 的可直接安装升级包，也没有将云端历史 PASS 改称本地当前版本 PASS。

## 逐项答复

1. **补齐：原始模板。** `originals/05-format-results-template.csv`（22数据行）、`originals/06-interop-results-template.csv`（37数据行）直接取自原输入ZIP原成员字节，非最终映射反向生成。SHA、原成员路径、历史使用路径及与 v3 输入清单的比较见 `provenance/original-provenance.json`。
2. **仍缺失：两份历史stdout；索引已勘误。** `logs/full/final-freeze.stdout`、`logs/wheel-smoke/export.stdout` 均为 **MISSING**；历史是否生成、是否为空为 **UNVERIFIED**。保留实际存在的exit/stderr旁证，独立 `provenance/command-index-errata.json` 修正引用，不创建空stdout、不以新运行替代历史日志。exit 0不能证明缺失stdout内容。
3. **修复候选：实际模型身份绑定。** 真实ONNX反例复现v3 caller-root hash与实际installed/env模型及config不一致。候选只修改两产品文件，hash来自传入ORT和JSON解析的同一份字节，记录model/config双hash；缓存保留已加载身份，并发切换锁住整个推理和回执生成。详见detector说明、增量patch与新运行原始日志。16项定向测试通过；受影响shared/transport另26项与47子测试通过。测试是小范围反例与回归，不是全产品资格化。
4. **修复候选：复现证据保全。** 新配置、venv、日志、临时数据使用独立run；export/空文件/venv/install必要前置失败停止依赖步骤；不消费旧锁或复用旧venv。故障注入验证的是脚本控制流，不冒充业务全套执行。宿主site-packages可泄漏到旧脚本的worker环境，原 `reproduce.sh` 不能称干净或完全封闭复现。详见reproduce说明和实测证据。
5. **补齐：补丁承接规则。** 原v3最终主patch已含detector、安全锁、资源重绑等中间候选，不能再次叠加。6份中间候选在精确基线实际应用后的文件均与主patch相应文件一致。主patch适用基线为 `8d367bac4a85bebfbb523503678ade0838faa73e`；用户本地70dfc397及13路径不适用仅记录用户审计反馈，未获取本地源码。新候选须按语义移植，不能整文件覆盖。详见 `handoff/HANDOFF.zh.md`。

## 环境与证据边界

2026-10-31 本次云端环境重启，原运行工作目录不可读取。已向用户报告并取得明确同意后，从已保存原v3及原输入附件恢复隔离基线；原v3 1873项内部清单逐项hash无差异。候选源码另从精确历史Git对象和原v3最终patch恢复，不以最新main替代。没有访问本地源码，没有推送、发布或修改正式仓库、其他项目、真实资料、全局配置。

所有本次运行均为2026-10-31 UTC新证据，与缺失历史日志区分。没有重跑未变化的Python/Rust/前端全量实验，也未重复打包历史数据库、构建产物或完整源码。

## 使用方式

- 先读此文件和各专项说明；核对原包SHA，再验证本包 `MANIFEST.sha256`。
- 模板和历史旁证是原字节补交，可用其SHA复核；不要用新索引覆盖原证据。
- detector新增patch以**原v3最终已应用源码**为起点，非原baseline直接增量；reproduce patch针对**原v3包的harness脚本**。两者目标树不同。
- 本补件不要求再次叠加原主patch及历史候选，也不要求本地源码回退到云端基线。
- 新反例复现步骤见各专项说明。脚本原始绝对路径用于证明这次实际执行位置，不代表用户机器存在同路径。

## 未解决／未验证

- 两历史stdout原内容无法恢复。
- 本地70dfc397适用性及13冲突逐项内容未验证。
- 原v3 Windows、原生UI及外部真实服务等未验证范围不因本补件升级为PASS。
- 模型双hash证明实际推理字节身份，不证明外部模型的作者、上游版本或准确率。固定Magika profile字段不能当作外部模型来源认证。
