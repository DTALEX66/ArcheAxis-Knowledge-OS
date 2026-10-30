# 六源公共重复叶清理与独立后验

本批按既有 Owner 精确条件授权，仅删除六份历史便携候选的公共重复集合：每源19,709项、1,350,213,438源路径逻辑字节，合计118,254项、8,101,280,628字节。V12保留端19,709项完整SHA和原Windows文件身份经独立POST全部匹配；35个公开Host、管理文件及原manifest也保持原SHA/身份。错误为空；目录删除、载荷复制、ACL修改及停止其他进程均0。该结果不等于物理空间释放或产品验收。

| 角色 | 本仓ignored位置 |
| --- | --- |
| 六个精确源run | `ui-audit-remediation-v4-portable`、`v6-portable`、`v7-portable`、`v8-portable`、`v9-portable`（后四者均有同一`ui-audit-remediation-`前缀），以及`ui-polish-20261027-portable` |
| 源/保留包共同位置 | `.project-local/runs/be268a2d33/<run>/artifacts/星环便携候选/` |
| 唯一同SHA保留run | `ui-audit-remediation-v12-portable` |
| 原逐项恢复映射 | `.project-local/runs/be268a2d33/batchhash-6c4aae2b/artifacts/restore-map.jsonl` |
| 当前权限/别名/全资源只读资格 | `.project-local/runs/be268a2d33/batchelig-96752792/artifacts/` |
| 全量意图、六份COMMIT与实际摘要 | `.project-local/runs/be268a2d33/batchdel-40e21d2a/artifacts/` |
| 独立后验 | `.project-local/runs/be268a2d33/batchpost-b71be9b1/artifacts/` |
| 后续整仓有限计量 | `.project-local/runs/be268a2d33/batchsize-12792afb/artifacts/storage-after.json` |

精确六路径、完整收据身份及各层限制见[BATCH-DEPLOYMENT.json](BATCH-DEPLOYMENT.json)。原映射22,499,572B，SHA `17ca4402536768ab23ec844926408a05ca321b5d6a672142a6866e6de9617f8b`；它不是V11旧19,711项映射。原[当前字节报告](BATCH-CURRENT.md)、原HOLD/FAIL与`cleanup_qualified=false`观察收据均保留各自时点，不追改为新PASS。

执行前已核当前公开消费者和已登记回滚选择其他根；这不是证明所有未登记快捷方式或进程均不存在。583.35秒的只读资格核验包含137,970项前后metadata/owner/DACL观察、236,508次DELETE-right打开、452次长路径别名查询、六次全资源RM；>=260 UTF-16边界及原manifest前后身份均纳入。所有权、字节保全、恢复前置和精确操作合同在root及独立审阅中闭合；没有从附件提示词或“旧版没用了”扩大删除范围。

实际`batchdel-40e21d2a`六对顺序执行，每对先固定源/保留目录、双组各19,710个资源fresh RM无locker且End0，再以同句柄独占读、完整SHA/身份/ownerACL及Host/Core/Python守卫逐项操作。118,254次原生disposition成功并持久COMMIT，500,963次已记录CloseHandle全返回1；六对全部关闭后才进入下一对，实际与清理错误为空。操作前ALL-INTENT先落盘，COMMIT每256项fsync；崩溃时最后未落盘段及在途项须先核对，不能自动重试。15个新driver纯mock实际通过，旧v3组件有限Windows负控/微小排他恢复证据另保留，不冒称本批完整恢复已演练。

后继94.47秒只读`batchpost-b71be9b1`独立核对六journal/意图/摘要与原映射，逐项确认118,254源路径在父目录存在时WinError2缺失，全部保留件完整SHA/旧WinID一致，35个公开保护项原SHA/ID一致，errors0。实际与POST均actual/wrapper0、clean `96e4300870938506aea55b8a7bb1162ffc371fae`源码一致。33个denied名称每端均不探存在性、不读正文；所有目录、映射外独有项和原失败按构造保护，不把它们说成已全量重哈。

历史源重放须先按该映射验证保留件完整SHA，排他创建缺失的原相对路径；现存不同内容绝不覆盖。恢复后的新文件身份须重新资格化，再核原manifest/config/权限/占用。六源完整恢复未执行，旧FAIL/PARTIAL不被替换，恢复和再次清理均不自动发生。

一次后续整仓计量显示可读下界142,280,381,205→134,357,299,417B，差−7,923,081,788B；不是物理释放或原子快照。674个访问错误、243个私有排除、581个布局项与前次原列表逐项一致，measurement仍PARTIAL、actual/wrapper1、源码一致；NO_NEW_GROWTH_TRIGGER不消除旧超预算债务。hash/eligibility/actual/POST四个具名run合计184,414,241逻辑B，不含准备、此前/后续run和其他产物，不能从删除数直接推算全仓净收益。

后续按[目录权威](../../../DIRECTORY_AUTHORITY_INDEX.md)继续解决存量49项归属、规范化与producer增长约束。F05固定请求第二题未完成仍阻断真实模型资格；没有证据支持把它改称JSON语法错误或通过调参重试强行通过。完整J1/CL、R6开始/自报/掌握等后继仍PARTIAL。未启动UI/Host构建、云端上传、Green替换或真实资料覆盖；最新实际进度只由[唯一执行记录](../../../current/AAOS-UI-FIRST-EXECUTION-20261009.md)维护。
