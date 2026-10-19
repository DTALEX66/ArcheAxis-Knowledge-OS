# BE10 CLI真实handoff准备消费提案

状态：**ISOLATED_PROPOSAL_PASS / NOT_APPLIED / BE10 PARTIAL**。root唯一产品writer，本目录已冻结，未应用正式产品。

- 可应用补丁：`be10-cli-consumer.patch`，SHA-256 `aeb7e489f63a04e839512d48f7141662d90a4ebf8ae3cb642b6b14f35a88bf16`，4文件，`git apply --check` exit0。
- 精确preimage与after：`code-manifest.json`、`preimages/`、`proposal/`；3份既有文件before原字节保留，1份新测试before=null。仅CLI、新process测试、2份现有合同说明；无依赖/锁文件/配置变化。
- 最终隔离验证：`validation.json`，20项PASS（6项新真实临时Core/CLI、6项原Observer进程、8项pure projection），child/outer均0，正式源基线与测试镜像一致。初轮19项只保留历史，不累计。
- 真实负对照：`be10-cli-red-reference-1019`在owned镜像移除引用allowlist守卫，新进程回归正确失败1项，child/outer101；`red-mutation.json`记录精确改动及hash。已恢复正式纯投影源码并重新编译，最终20项绿色。
- 固定验证镜像：`.project-local/runs/be268a2d33/be10-proposal-prepare-1019/tmp/workspace`；复制范围和逐文件hash在`validation-baseline.json`。独立target为本目录`validation-target/`。不复制环境、依赖缓存或整仓。

新增prepare_handoff/prepare_receipt沿用stdin64KiB/5秒、专用admission与真实握手，读取固定objects端口，然后调用已正式存在的pure projection。stdout严格Handoff；5类metadata有真实消费者，错误有限不回显认证正文/token。旧3操作回归通过。manifest仍UNKNOWN。

本轮只证明自建合成资料下的工程集成，不证明外部产品已接入、实际投递、执行、业务持久化、exactly-once、UI/native、安装或Owner接纳；整体保持PARTIAL。不能以本ignored消费者证据升级正式产品消费者资格。

应用接续：root核对3份preimage与新目标不存在、patch/hash后串行应用4文件，使用canonical runner运行新`project_handoff_process`及旧`project_observer_process`/`project_handoff_projection`。严格metadata输入、有限错误、UNKNOWN/CONFLICT、业务全表不变、无泄漏必须保留。回退仅恢复该3份before并撤下该新测试，不能覆盖其他修改。
