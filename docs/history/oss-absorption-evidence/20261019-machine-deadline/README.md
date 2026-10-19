# 材料/陪伴超时与失败采集修复快照 · 2026-10-19

本快照保存八个相关源码文件、红绿回归、实际命令/时间/退出码、只读评审和导航观察。历史快照不改写；实际进度仍归[唯一UI执行记录](../../../current/AAOS-UI-FIRST-EXECUTION-20261009.md)，最新决定归[决定第九节](../../../current/AAOS-OSS-INTEGRATION-DECISION-20261019.md)。

## 当前限定结论

源码 patch `feb84661b15d3457ff243aa32c57ed7f0ee168fe6e93db5fd6c4276206af85ef`：153项Python＋145 subtests、46项应用层Rust、30项Core API集成检查PASS，三个最终run均source_consistent。假时钟验证到期前、恰好到期及超期；真实自建worker验证预算传递、超时后仅拥有PID回收；自建SQLite/API验证失败重开读回及查询不重复推理。它们不是完整真实模型原生验收。

CLI预算现在传到worker；服务发现与推理共享预算，worker拒绝迟到回答。Core暂存后过期不启动worker、循环与最终接收处检查总截止，硬超时保存安全诊断。探针只采本任务request/session/plan的allowlist终态，HTTP200失败立即记录并失败，不保留模型正文或其他请求正文。

中间patch `8cfc37ec2051b7bb90349be46fca4e502e4a15e0268eab7f8859f103eb860917`已有Core/TypeScript/Vite/Tauri构建PASS，但随后补了截止边界，不能作为本快照最终源码构建资格。候选**尚未更新**，本patch原生**NOT_EXECUTED**。最新实际模型原生仍是[旧候选失败](../20261019-material-companion-final/README.md)，模型内部原因UNKNOWN；终止本任务worker不证明LM Studio服务端推理停止。

## 接续实施

1. 先沿[活动指针](../../../current/AAOS-ACTIVE-EXECUTION.json)读取当前权威、决定、handoff、进度和共享manifest；不要从本文复制默认路径。
2. 最终源码构建Core与host，核对相同source patch/HEAD。中间构建和旧candidate不升级资格。
3. `promotion-helper.py.txt`保全已准备但未执行的本任务八组件promotion脚本。使用前读脚本、核对精确目标/进程/manifest/哈希；默认源脚本在项目内`.project-local/runs/be268a2d33/closure-native-stage/promote_timeout_components.py`。它不是新授权、不面向Green、不复制或删除用户资料。
4. 重走原生材料/陪伴终态、恢复、取消、冷重开与备份后读回，实际查看截图，保留失败和拥有进程/端口清理结果。再推进BE10、复习标题及既有能力任务。

## 保全与限制

`SOURCE-MAP.json`固定八个源码身份，`COMMANDS.json`保存各run的命令、开始/结束、退出码与patch。同名日志逐run保存；红色用例原失败保留。`ROUTES-OBSERVED.json`只作当时导航观察，不替代当前索引。`MANIFEST.json`逐成员SHA-256，不包含自身。

完整Cowork正文仍UNVERIFIED。归档为本地仓库文件，未提交、未推送、未云备份；未改共享模型、provider、endpoint或全局配置；产品PARTIAL。
