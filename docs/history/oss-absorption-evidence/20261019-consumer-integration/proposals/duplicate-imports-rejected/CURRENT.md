# HUB page17 Node-only guard修正版

状态：**ISOLATED_NODE_CONSUMER_PASS / NOT_APPLIED / HUB003 PARTIAL**。root唯一产品writer；原8文件提案保持冻结，本修正版没有应用。

- 固定补丁：`capability-manifest-consumer-node.patch`，SHA256 **`c0d004392d1b5ff4cf7690fe356bc71afcf0ab967bd30c7382d2d85c11ea73c3`**，10文件（原8修正 + Node guard + 内置Node测试）。before/after见`code-manifest.json`，2份既有preimage原字节保留，8份新增。git apply --check exit0。
- 修正P1：Vite配置不再无条件exec Python；通过Node标准库guard检查。Python仍显式生成、完整Schema及CAP/供体/route语义验证，前端Node-only入口不新增Python/jsonschema前提。既有canonical build的Python路由/verifyBuildEnvironment未改，不能声称完整构建已摆脱Python。
- 真实漂移guard：从固定public source清单和manifest有限公共ref导出读取路径，绝不使用生成TS.sources作为读取许可。逐级拒绝links/junction、私有段、越界/缺失/超大文件；有界UTF-8/JSON、重复key/来源/深度校验；原manifest字节hash、host、schema、validator、generator及guard本体hash均绑定，重新构造固定UNKNOWN状态payload并比较整个固定TS声明。没有eval、Python调用、生成或安装。
- 真实验证：`validation.json`。9项Node +11项Python +8项page17 PASS；镜像完整TS、2份Python Ruff、显式生成--check PASS。Vite serve/test真实配置加载在不存在Python+空PATH和独立无jsonschema Python两种环境中，各正/原字节漂移拒绝/恢复3例PASS，cwd分别frontend和审计目录且config.root正确；没有创建server。
- canonical总回执：`.project-local/runs/be268a2d33/hub-node-consumer-frozen-1019/artifacts/execution.json`，child/outer0、source_consistent=true；实际命令、时间、日志hash见回执和`validation.json`。失败/中间通过不累计，见`FAILURES.md`。
- 镜像：本目录`validation-mirror/`，只复制公开生成输入及前端源码供TS/page17检查，清单`BASELINE.json`。node_modules仅本目录指向现有frontend/node_modules的依赖复用junction；没有复制依赖、缓存、环境或历史。独立stdlib-only Python未安装任何包，仅验证缺jsonschema场景。

真实许可、发布者真实性、资格和runtime保持UNVERIFIED/UNKNOWN；page17仅按所选精确CAP显示，不新增registry、执行、安装/启用按钮或服务。Node hash/byteguard只是漂移检查，不取代Python semantic或真实上游许可/执行admission，也不是签名或恶意源码修改防护。

应用门禁：root核对2份before、8份新增目标仍不存在及10份after/patch hash，串行应用；项目Python显式生成--check与11项合同测试，Node内置9项、真实Vite配置缺Python正负恢复、page17 8项、TS/Ruff。正式全量前端与完整构建、exact-SHA CI、原生/安装/Owner验收仍NOT_EXECUTED。本ignored镜像PASS不能提升它们的资格。

原8文件旧补丁仍 `16df8256ed8511d137c4d74e7668d551e1aabbd66cc344ed4a4c2b1c5dab188f`，不可与本10文件补丁先后叠加。回退只恢复这2份before并撤下这8份新增，保护其余dirty修改。最后readback见`FINAL-READBACK.json`。此处已冻结，不再追加实现。
