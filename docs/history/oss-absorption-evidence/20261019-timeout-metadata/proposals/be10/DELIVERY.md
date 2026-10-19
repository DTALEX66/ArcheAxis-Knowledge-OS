# BE10 首切片可应用提案

状态：**ISOLATED_PROPOSAL_PASS / NOT_APPLIED**。产品 root writer 应用后统一验收，不把本提案当已实现 BE10。

- 补丁：`be10-observer.patch`，SHA-256 `4c0a09cf75101e641987e93fe2b4e6a1929786ddeb011da7993ddc2ad579c817`；15个文件，`git apply --check` exit0。
- 实际改动文件及前后 SHA：`code-manifest.json`。仅3个既有文件增改（两个lib导出、launch），其余新增。无依赖/lock/config/原产品修改。
- 验证：`validation.json`，保留全部原失败及 INVALIDATED 回执，不覆盖。`proposal-preimages.json` 是最小编译镜像复制范围清单。
- `proposal/` 只含改动文件。最小 Rust 源码/合同镜像位于 `.project-local/runs/be268a2d33/be10-proposal-prepare-1019/tmp/workspace`；没有环境、依赖、target、历史文档或hardlink副本。独立 Cargo target 在本审计目录 `validation-target/deadline-v2`；早先 target 保留为历史失败轨迹。15项最终提案字节均与编译镜像读回一致。

## 已实际验证

- `be10-proposal-api-final-1019`：6个真实 Core/CLI/HTTP 进程回归与2个实际 HTTP adapter 负例测试，child/outer exit0，source_consistent=true。
- `be10-proposal-admission-api-1019`：1个实际 protect middleware API 回归，positive human 到达可变下游、Observer合法读/受拒请求都不进入下游；exit0。
- `be10-proposal-contract-final-1019`：1个 Rust strict DTO/语义回归遍历27共享case，exit0。
- `be10-proposal-python-final-1019`：1个 JSON Schema 回归遍历同27case，exit0。
- `be10-proposal-legacy-launch-1019`：4项现有launch/角色/未授权回归，exit0；不是整个launch suite。
- `be10-proposal-v2-final-1019`：3项既有v2测试的child exit0；外层因产品源同时修改INVALIDATED，不能计当前产品PASS。重跑时先保证正式源码稳定。
- 已枚举本任务独立 target 下的 `archeaxis-api.exe` 与 `archeaxis-project-observer.exe`，未发现遗留进程。测试owned child采用kill+wait Drop，不停止其他服务。

失败轨迹保留：一次cmd路径空格解析失败；一次Windows owned stub继承非阻塞导致WouldBlock（改fixture为blocking后通过）；一次最小镜像缺FSRS worker导致旧v2检查 unavailable（以进程env只读引用现有脚本后child恢复PASS）。未降低断言标准或把失败计绿。

## 实现与限制

独立v3 Observer grant经stdin进入，独立token与consumer/producer/restore/expiry/object allowlist绑定；认证层提前隔离普通API。版本化三个只读端口、有限DTO/schema、真实Rust loopback客户端与CLI已连通；无任意URL、正文、title、记忆、业务路径或凭据投影。空库只读不建身份，revision变STALE，恢复和断连拒绝继续报CURRENT。

证据是自建合成资料的工程集成。两个workspaces用于独立数据/生命周期验证；真正consumer是独立Rust CLI，不是已接入WORK-LAB/DESIGN-LAB原生UI。服务未注册worker，因此不能宣称覆盖已注册所有真实worker的端到端取消；独立API负例已证明Observer不会落入任何下游handler。

本切片未交付：可见关联UI、真实deep link handler、外部产品native集成、future handoff/delivery合同、幂等投递、安装打包/共享配置、用户资料或Owner验收。旧v2 Tauri不会自动启用Observer；不得因补丁测试通过即改全局或另一产品。

## Root 应用后最小门禁

1. 对照 `code-manifest.json` 复核3项preimage并`git apply --check`，由唯一writer应用。
2. canonical dev runner 运行 API三项新test targets + 现有完整`launch_auth`；正式仓已有worker源码，不应延续最小镜像环境缺口。
3. 运行 contracts新Rust target及Python新JSON Schema测试；再检查当前diff/status与非预期变更。
4. 中文合同说明在提案 `docs/contracts/project-observer-v1.md`，当前进度只由root回写原有唯一执行记录；保持BE10 PARTIAL并列明剩余产品集成。

## P2 总截止修订（2026-10-19）

已将生产每次请求固定3秒的同一个单调时钟截止贯穿 connect、有限 write 循环、read、EOF、DTO解析及最终成功门。每次系统调用仅使用剩余预算；连接/写入后、每次读取后（包括EOF）及最终Ok前重新拒绝过期为Unavailable。短预算仅private测试入口可用，公开生产接口无配置扩张。

- 4项内部回归实际通过：及时真实HTTP正控2ms、持续35ms间隔慢流250ms截止、完整合法响应延迟EOF 260ms拒绝、已过期最终门拒绝合法DTO。
- 实际公开生产入口连到独占loopback静默对端，对端保持4.2秒，客户端3003ms返回Unavailable；同一轮3 client + 1 middleware API + 6进程测试全通过。数据仅合成fixture，传输和进程是实际工程集成。
- 新独立target重跑既有v2 3项及launch 4项全通过，canonical child/outer均0且source_consistent=true。此为7项选定回归，不宣称完整launch suite通过。
- 初轮包装器参数位置失误、同target混入产品编译导致的0测试假绿/导入失败全部保留，明确不计PASS；修正参数位置后使用全新deadline-v2 target，确认编译路径为本任务mirror及准确非零测试数。
- 旧patch、manifest、validation和交付原字节保全在`revisions/pre-deadline-fix/`。新旧散列、3文件增量diff与回执见`deadline-revision.json`、`deadline-fix.diff`。最终15项提案文件与编译镜像逐项hash一致，git apply --check=0，产品仍未应用。
- 未人为填满OS backlog或注入内核connect/write阻塞；该段剩余预算路径为代码核验，真实HTTP覆盖静默、慢流、延迟EOF和正常完成。未补造这部分运行证据。
