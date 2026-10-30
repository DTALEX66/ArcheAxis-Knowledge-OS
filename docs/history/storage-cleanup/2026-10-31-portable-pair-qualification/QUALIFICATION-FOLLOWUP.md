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
