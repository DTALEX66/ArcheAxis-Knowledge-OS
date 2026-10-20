# HUB Node consumer 修正冻结入口

状态 **ISOLATED_FINAL_CANDIDATE_BOUND_PASS / NOT_APPLIED / HUB003 PARTIAL**。产品root单writer；本目录仅ignored提案，零产品修改。旧node-next提案存在重复import，旧“可应用”结论撤回；旧字节保留，不能叠加应用。

- 补丁 `capability-manifest-consumer-node-corrected.patch`，SHA256 `b5704554f3c934b362304b6262906aba2bfc0315c2cdc48ccff5cd72d089c981`，10候选、2现行文件preimage、8新增。完整前后hash `code-manifest.json`；git apply --check exit0。
- 本次仅修旧10候选中的vite.config.ts，单guard import；新配置SHA `65efc5497288d6b9f0e6294ec4cafc8f275047c3bded8082c5fc6ba3d1b47579`。旧冻结10候选/patch/manifest/prepare/validation及旧mirror原字节已核实未变。事故解释 `ROOT-CAUSE.md`、精确复现 `ROOT-CAUSE.json`、输入证据 `FROZEN-INPUTS.json`。
- canonical `hub-node-corrected-1019`：outer/child0、source_consistent=true，实际receipt `.project-local/runs/be268a2d33/hub-node-corrected-1019/artifacts/execution.json`。11个实际步骤，每项开始/结束逐核对10候选和mirror，见 `validation.json`，不累计旧PASS。
- Node9、Python11、page17两文件8项、显式Python生成--check、镜像src全TS、**vite.config.ts独立全TS**、两份Python Ruff均PASS。真实Vite config在不存在Python+空PATH以及owned无jsonschema Python中各正/manifest字节漂移拒绝/恢复3例PASS，均核实root正确且没开服务。旧7重复import真实Vite接受但TypeScript7条TS2300负例复现成功，说明为何单独Vite加载不够。
- Node guard仍固定有限公开源读取，不使用generated.sources授予路径；拒绝私有/越界/links/junction/缺失/超大/重复，绑定manifest原字节、host/schema/validator/generator/guard及整个生成物。Python显式Schema/semantic不变，Node-only路径不调用Python。canonical build既有Python路由保持，不宣称完整build不需要Python。

应用：只应用本patch，root先核对2既有before与8新增不存在，10after精确一致；正式环境重跑Node/Python/page17/srcTS/配置TS/Vite正负恢复。没有新registry、安装/执行、依赖/锁/CI更动。**完整构建、exact-SHA CI、native/installed/Owner及真实引擎/许可认证均NOT_EXECUTED或UNVERIFIED**；本镜像不升级资格。

镜像只复制固定公开输入与前端源码供TS/page17；BASELINE.json记录范围/hash。仅本镜像node_modules junction只读复用现有依赖，未复制依赖/缓存；stdlib-only Python无pip/安装包。没有业务DB、模型、服务、浏览器、全局配置或E/F操作。最终核对 `FINAL-READBACK.json`。候选已冻结，不再改。
