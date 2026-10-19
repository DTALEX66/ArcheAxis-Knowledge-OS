# HUB Node corrected 冻结交叉复核

**NO_BLOCKING_FINDING_FOR_SERIAL_APPLICATION**。绑定 patch `b5704554f3c934b362304b6262906aba2bfc0315c2cdc48ccff5cd72d089c981`。

- 10候选逐字节核对：仅vite.config删除6条重复import，余9文件与旧冻结字节完全相同；新配置单import SHA `65efc5497288d6b9f0e6294ec4cafc8f275047c3bded8082c5fc6ba3d1b47579`。10份proposal/mirror/manifest/tested/初始CANDIDATE-HASHES一致，2份preimage一致。旧10候选及旧patch/manifest/prepare/validation/mirror按FROZEN-INPUTS核对未变。
- validation的11个步骤全部exit0，日志hash逐一匹配；每步before/after均覆盖全部10候选与镜像共440个hash值，精确等于最终清单。新 `typescript-vite-config` 实际命令显式对vite.config.ts独立 `tsc --noEmit`，保留src全TS，没有沿用旧src-only漏检。无Python/无jsonschema两组Vite正/负/恢复仍是精确配置加载而非server。
- ROOT-CAUSE精确旧字节复现 Vite 接受、TypeScript7条TS2300，与旧config hash一致；finally恢复新hash。旧Vite PASS可以与TS重复绑定共存，因此未虚构镜像差异或日志造假。一次性prepare在proposal已存在时拒绝，run_checks不再调用prepare；复验阶段的故意旧配置/manifest负例仅在新自有镜像，前后恢复哈希均绑定。
- Node guard/generator/manifest/UI消费者不再变化；上一审查的新增Python依赖消除、固定public路径/links/有限来源绑定/UNKNOWN资格边界仍成立。没有新增产品权限/执行入口/registry或依赖升级。冻结说明正确保持NOT_APPLIED、HUB003 PARTIAL；全构建/CI/native/installed/Owner及真实许可不因局部PASS提升。

本轮仅只读差异、哈希与回执核对；未重复执行测试、服务或推理，未改产品/候选。推荐root仍按声明核对当前2 before/8新增不存在再串行应用；不得先叠加旧patch。EVIDENCE.json保存全部矩阵/引用。
