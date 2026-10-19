# HUB10 Node-only 修正版只读复核

**BLOCKED_SOURCE_DEFECT**，冻结 patch `c0d004392d1b5ff4cf7690fe356bc71afcf0ab967bd30c7382d2d85c11ea73c3` 不应直接应用。

**P1：配置重复绑定。** `proposal/frontend/vite.config.ts:6–12` 有7条同名 `checkCapabilityPackageDetails` import。现有 TypeScript API 对这份精确文件产生7条 TS2300 Duplicate identifier。`prepare.py:17` 对现文无条件追加导入，重复准备会继续污染提案，是可证形成机制。最小修复：另建修正版，单份 import；制备入口从固定preimage构造或幂等断言；冻结后不再准备重写；重新绑定patch/after hash并复验精确Vite配置。

**证据绑定结论：** 当前 proposal/validation-mirror 全10成员 hash 相同，均匹配 code-manifest，Vite两份都是7条重复导入；不存在当前两者hash差异。不能声称PASS来自另一份已证不同的镜像。旧 `typescript-mirror` 使用 `tsconfig.include=["src"]`，不含 vite.config，因此不覆盖该错误。page17 使用独立vitest config，同样不是产品vite配置验收。真实Vite日志记录了正/漂移拒绝/恢复PASS，loader确实指向镜像vite.config，但validation.json没有记录逐次加载时配置hash；FINAL-READBACK只绑定最终字节。本审查未执行Vite：转译器可能接受/去重重复import，**不能把TS2300扩大成已实测Vite运行失败、或据现有日志断言伪造**。首条即时消息中过强的“真实Vite无法加载”已向root收窄为此证据范围。

其它审查：Node guard仅标准库，无Python subprocess/import；原P1“新增无条件Python/jsonschema依赖”已从入口实现消除。`verifyBuildEnvironment`既有完整构建前提保留，不代表build全脱离Python。guard从固定public清单和有限manifest公共ref取路径，不相信生成sources授予读权限；逐级links/junction、越界、私有段、大小、UTF-8、重复key/depth有界拒绝。完整固定header/payload/suffix比较，不eval；生成data中的manifest与原JSON、manifest raw sha及所有source hash已逐一核对一致。真实性/资格/runtime仍UNVERIFIED/UNKNOWN，Node drift guard没有冒充完整Python语义验收。未发现除此重复绑定以外的可证阻断问题。

下一门禁：单import修正版的精确文件静态无重复绑定；真实Vite配置在无Python及无jsonschema环境正/负/恢复并记录每次before/after config/guard/projection hash；生成--check、Node9项与Python11项/page17/TS按原门禁复验，不能沿用旧PASS覆盖修订。canonical完整构建/CI/原生仍未被本审查验证。

本轮只读源码、受控TypeScript noEmit诊断及hash/JSON核对；未启动服务/模型，未重复全套测试，未写产品或原提案。仅本ignored审阅目录产物。EVIDENCE.json含真实引用和同版本hash矩阵。
