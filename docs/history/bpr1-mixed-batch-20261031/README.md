# bpr1混合目录中断与显式续做

`j1b1`复用原bpr1后端包、生产worker路由和一个全新合成工作区，实际完成六成员批次的部分注册拒绝、重复注册/改写冲突、原件校验、同字节双路径去重、TXT成功、坏DOCX失败、运行中HTML取消、停止Core及两次冷重启读回。第一次重启只重放原请求，不重新执行；随后Core实际准入坏DOCX和已取消HTML的新请求，分别再次失败和成功，再处理原先未处理的CSV及未知扩展原件。未知扩展猜作text被拒绝。四个唯一job共六个attempt，七次同key回放摘要及重启前后两对完整快照一致。

actual/wrapper均0、源码一致，源为clean `35de7ce6`；包构建身份仍为`71569d17`加原dirty patch，未重建或修改包。160次Core HTTP、34条POST意图均落当前run。取消实际观察running、202且cancel_requested=true、持久化cancelled；不能据此独立证明OS worker子进程已在取消前启动。坏DOCX两次均AAK-WORKER-003、retryable=false，第二次是Core准入的新失败，不是修复成功。中断点在已终态attempt和未处理成员之间，不是worker内部检查点续传。

三个自有Core各自reap退出1，保存的两相精确PID/IPv4及IPv6无LISTEN守卫成立；socket六次10035仍为PENDING，未说拒连、优雅退出或全机worker清场。6个合成输入共35,750B，阶段观测最大1,880,695B，零runtime/DB复制；50MiB只作阶段观测线，不是OS硬配额。原件、失败、取消、成功、DB/CAS和全部证据保留。

root独立核17个当前包/输入文件SHA、6份保存输出内容SHA、请求数、取消及快照关系。runner作者后审另核同17文件原生身份、5个原件CAS和20份API原件读回；身份与角色分列。其首版误把输出当作原件CAS，失败保留，纠正后按实际job_outputs存储核保存的API输出；不读数据库正文、不把复核脚本错误归于目标run。原回放ACK正文未逐个保存，只保留runner断言、摘要和HTTP状态，证据边界如实登记。

这是有限批次/attempt缝隙的实际验证，不构成完整J1/CL、UI/Host选择器、安装或本批次备份恢复验收。四格式恢复证据沿[独立三阶段记录](../bpr1-format-recovery-20261031/README.md)，不能拼成一次完整旅程通过。当前进度沿[唯一执行记录](../../current/AAOS-UI-FIRST-EXECUTION-20261009.md)。
