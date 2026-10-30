# 两份历史便携包的逐叶保全候选

既有PARTIAL尺寸索引显示runs是主要占用来源，沿索引只核V11/V12两份历史便携包，未重扫百万文件。两版Host同为49,960,960B但SHA不同；V11引导原FAIL、V12后继PASS，两个Host、manifest及原失败证据均保留，不能以新版本代替旧失败。

`nrm-port1`先固定两manifest声明的同SHA公共集合。root审阅后，`nrm-port2`实际只读19,711对公共叶：双份完整SHA均匹配、常规文件且nlink1、Windows卷/文件ID互异、读前后及重开路径身份稳定，errors=0，actual/wrapper0且源码一致。源侧1,350,261,264逻辑字节；不是已回收或物理去重大小。33个保护名称不读正文、不进入集合；不同Host和manifest不进入映射。逐项restore-map为8,110,099B，留本仓ignored路径，Git仅记录SHA和结论。

这仅取得当前字节及替代映射证明。闲置、所有权/清理范围、删除句柄和恢复重放仍未资格化，cleanup_qualified=false；删除、搬迁、载荷复制及ACL修改均0。未来执行须重核当前身份和授权，不能沿历史时间、同尺寸或本报告直接删除。现有49散落目录资格未因此改变。[唯一执行记录](../../../current/AAOS-UI-FIRST-EXECUTION-20261009.md)维护后继状态。

后继实际操作及恢复导航见[精确删除与全量保留链核验](DEPLOYMENT.md)。本页和原MANIFEST保留清理前及观察时点；最新接续沿唯一执行记录读取。
