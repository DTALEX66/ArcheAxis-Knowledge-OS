# 当前 Core 构建与 V2 离线准备

特性提交后，`cfcore-339a6bb6` 用既有 Cargo 包装器执行 locked/offline 的 `archeaxis-api` 单二进制 build，actual/wrapper 为 0、源码一致，绑定 clean `89b21d4e9b9be319ab58e6c10b9a4fd9bf5b0edc`。缓存命中，输出 27,897,344 B，SHA `043834e07c50f84c6eed51fafa24879b8a8570d537323445a121096596b05a1a`。更早的 run 名分配碰撞发生于 Cargo 前，未覆盖旧 run，也不是本次构建收据。此处仅取得 Core 构建身份，未修改 bpr1 原包。

`v2prev-50860dba` 只生成纯本地 V2 预览，actual/wrapper 为 0、源码一致；Core、HTTP、模型调用均为 0。沿用原问题、材料、prompt、2048 token 和超时/最多五正向候选预算，仅请求中显式给出有限字段类型，不给正确值。V2 前后同题格式必须相同，不能拿新格式结果改判旧 real1/ar2 失败。

非作者独立静态复核未确认固定调用的 P1/P2 阻断；这仍不是执行资格。预备混合入口保留原 17 routes 和默认 text 路由，仅 machine.answer 指向当前生产 worker；拟复用原 Python，只复制一个 Core、launcher 和两个 scheduler 小文件。它是有限组件组合，不是原包或新完整安装包。实际执行前须另冻结当期 metadata、所有选择成员、profile 和 override 身份，并先做 preflight。

`v2unit-d6efc35b` 实际执行 16 项全内存测试，16 passed，actual/wrapper 为 0、源码一致，绑定同一 clean HEAD。覆盖首答/拒答/迁移早停、NO_FINAL、request/worker 格式及哈希不符、持久读回不符、同题格式变化和复测绑定。没有 socket、Core、模型或真实入口执行。

当前真实模型对结构化请求的支持仍 UNKNOWN，学习效果 NOT_ESTABLISHED，F05 整体 PARTIAL。旧真实模型失败、UI/安装/Owner 验收边界不变。证据身份见同目录 MANIFEST；后继实际执行不能由本文件的候选说明自动宣称完成。
