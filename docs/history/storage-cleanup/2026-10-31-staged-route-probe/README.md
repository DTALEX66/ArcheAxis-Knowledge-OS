# Staged routes探针：规范落点与缓存筛选

正式 `staged_runtime_routes_smoke.py` 将固定 `.project-local/runs/staged-routes` 及启动删除旧树改为现有 dev 分配当前 run 的 `artifacts/staged-routes/<uuid>`；复制 workers 时排除 `__pycache__`、`*.pyc`、`*.pyo`，与正式 stager 规则一致。`nrm-route1` 旧函数有限反例退出1，候选退出0；原失败保留。root部署后 `nrm-route2` 真实import整个正式模块，2/2检查、actual/wrapper 0：真实分配两次独立UUID，main在build入口明确拦截且删除trap未触发；tiny自有workers fixture验证源码保留和缓存排除，copy2 mock避免复制Core/解释器，正式 `stager.present_routes` 未替换。`nrm-rlint1` 既有最小Ruff门槛退出0；准确源码/两类补丁身份、收据与限制见MANIFEST。

这是生成落点和筛选行为的有限源码资格，不证明近期实际调用、完整probe业务或新增runtime资格。Core/API/模型/job/构建均0，未删除、搬迁或清理旧产物，回收0B；原49项仍0项获得清理资格，目录规范化整体未通过。本页是历史记录，不维护第二当前进度；当前状态见[唯一执行记录](../../../current/AAOS-UI-FIRST-EXECUTION-20261009.md)。

后继 `nrm-lint2` 保留三处既有风格问题的失败；仅删除本探针未用base64 import，`nrm-lint3`通过。`nrm-route3`在该后继源码重做上述两项有限检查仍2/2通过，actual/wrapper0且源码一致。未重做完整业务探针，历史SOURCE/SHA及首次资格不回改。
