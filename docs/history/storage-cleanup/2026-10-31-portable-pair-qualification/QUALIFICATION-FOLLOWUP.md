# 占用核验仍为 HOLD

当前活动指针已明确授权项目内精确清理，条件包括所有权、可再生或同 SHA 保留替代、闲置、保护输入及后置检查；无需重复取得清理授权。此前 README 中的“清理范围未资格化”是检查进度，不代表 Owner 未授权。

`nrm-port3` 在普通令牌下逐项核 19,711 对文件：两侧 owner/DACL 均符合条件，无读取错误；源侧 19,711 次独占 DELETE 权限句柄探测成功，全部关闭，未调用删除 disposition。两个小恢复样本共 25,201 B，复制至独占新建的项目内 scratch 并核 SHA 成功。这是有限恢复样本，不是全部映射的恢复重放；瞬时权限句柄也不证明后续删除时闲置。

Restart Manager 首批注册 19,712 个资源返回系统错误 29，未执行 GetList，EndSession 为 0。整个集合保持 HOLD，eligible=0，cleanup_qualified=false。检查程序 actual/wrapper 为 0、源码一致，仅表示审计完成。

为区分接口整体不可用与资源规模问题，root 另做两次固定诊断：

- `rm6-1d709273`：只注册两侧 Host/Core/Python 六个资源，注册、GetList、EndSession 均成功，未报告这些资源的占用者。不能扩大到全部叶文件。
- `rm256-f0ac10dd`：同一会话固定每批 256 个资源，前 25 批成功，第 26 批返回 29；立即停止，未执行 GetList，EndSession 为 0。完整覆盖未取得，仍为 HOLD。不能据此确认具体系统根因。

两次诊断 actual/wrapper 均 0、源码一致，绑定 clean `89b21d4e9b9be319ab58e6c10b9a4fd9bf5b0edc`。Restart Manager 会维护系统内部会话注册状态，本记录只承诺项目原文件未改，并非“零系统写入”。接口语义见 [RmRegisterResources](https://learn.microsoft.com/en-us/windows/win32/api/restartmanager/nf-restartmanager-rmregisterresources) 和 [RmGetList](https://learn.microsoft.com/en-us/windows/win32/api/restartmanager/nf-restartmanager-rmgetlist)。

本批删除、迁移和 ACL 修改均为 0；1,350,261,264 B 仍是待审重复源的逻辑字节，不能报告为已回收空间。原两个 Host、manifest、V11 原失败、保护名及旧 49 项保持原边界。任何后继执行都需要重新核当前身份、保留替代、完整占用证据和同句柄后置条件。逐项证据的路径、字节与 SHA 见同目录 MANIFEST，当前进度只在唯一执行记录维护。

后继一次固定 component 诊断 `rm125-aff6b59c`：从原失败第 26 批冻结最前 125 对可映射叶，双端加六个 Host/Core/Python guard，共 256 个资源；新会话 Start0、Register29、未调用 GetList、End0，身份前后稳定。actual/wrapper0、源码一致仅代表审计完成；仍 UNKNOWN、cleanupfalse。本支到此停止，不换样本、缩批重试或运行全覆盖多会话。六资源成功、单会话累计失败和固定 256 失败都不足以确定系统根因；Owner 授权不替代技术前提，整批旧副本保留。


## 现有短名与有占用控制的有限核验

旧 component 诊断支路保持停止。后继只读比较发现，原失败批含超长路径，既有成功批没有；这是相关性，错误29的系统根因仍未证实。`shrt-3eebd817`只对固定两叶读取已存在短名：261个UTF-16单元缩为151，两侧long/alias并开句柄的volume/fileID、大小、写入时间及规范化最终长路径一致。另六个Host/Core/Python使用原完整路径；11次CloseHandle均成功。没有创建短名、链接或盘符映射，也未改ACL/注册表配置。

第一次正控`aliaspc-562bc26d`报HOLD：父持有Popen身份5560，而RM报30552，创建时间也不同，故未执行释放后第二会话。自有child释放、wait/reap退出0及句柄关闭已确认。Windows Python redirector是可能解释，未取得该历史进程链的独立证明；不把返回PID认作无关进程或据此操作它。

另立显式身份门的v2：父/子固定复用已核bpr1解释器，child-ready实际PID/FILETIME先与保留的Popen句柄精确一致，才允许RM。`alias2-807cb889`的三处身份同为PID30224/创建FILETIME134378695662523993；file-only登记固定8资源，nApplications=0，正控只报该child。End0后明确释放两原长路径句柄、child终态RELEASED、退出0并回收；第二新会话同8资源无占用报告、End0。共9次RM/2会话，父31次、child3次文件/token CloseHandle均成功，Popen句柄关闭已确认。原HOLD收据不改。

两次控制及短名run actual/wrapper均0、clean05cc2601且源码一致，只表示各自审计执行完成。v2通过的是两条短名和该普通读句柄场景的有限正/释放控制，不证明整批19,711对闲置、原子安全或错误29根因。全部重复源仍保留，cleanup_qualified=false，删除/迁移/ACL修改均0；1,350,261,264逻辑B仍不能报告为已回收。完整集合如需后继资格，必须另冻结清单并完整核验；没有自动重试或删除授权从本控制产生。


## 完整固定集合的后继观察

`fullalias-6f7260b4`冻结原39,424资源（19,711对公共叶加两不同Host）；仅70条原超长路径读取已存在短名，原/别名并开句柄身份及最终长路径一致。前后各39,424文件完整SHA/身份/祖先核验一致，精确读取最多5,600,888,896B、不复制载荷。单会话两次固定19,712资源登记均0，GetList0/count0/needed0，End0；共5RM调用。78,989次CloseHandle观察均成功。actual/wrapper0、58803b80+dirty9f61c1bd…且源码一致（dirty为无关当前ASR guard实现），162.36s。v1累计close扫描成本已在执行前改为线性检查，源v1和精确diff保留。

该run取得完整固定集合一次RM无locker观察及前后内容一致，仍不是全局原子闲置或永久清理资格。没有在本片重测owner/DACL/DELETE，后继精确删除须在同句柄下重新保护源和保留端并留下恢复意图/逐项持久账。cleanup_qualified仍false，删除/迁移/ACL0；原Host/manifests/失败及33保护名不动。两个主要观察文件合计59,054,428B，其余元数据另计，未生成第二runtime。原29与第一次控制HOLD不改，也不单凭别名成功确认29根因。
