# Python C++ 依赖修补与候选组件身份

本记录约束当前已授权后端修复的实现，不新增任务队列或发布授权；实际进度只写活动指针所选唯一执行记录。前端实现与构建继续暂停。既有 `local-pinned-packaging/v1` 对产品源码增量的拒绝保持，不能把本次 runtime 修补登记为七项工具增量或套用旧整包身份。

## 触发与目标

旧候选的安装态 PDF 任务明确失败于 `PDF_DEPENDENCY_IMPORT_FAILED`。独立进程对照已证明：仅增加精确 WebView 目录的进程级 DLL 搜索后，`pymupdf` 和 `fitz` 可导入，并观察到 MSVCP140 从该目录加载；这不是正式分发修复，旧任务不重放。原件见本轮 v6 冻结证据。正式修补使用注册 Microsoft VS x64 Redist，不复制 WebView DLL，不安装全局 Redistributable，不修改 PATH、注册表或模型设置。

已核注册 donor 为 `ext.toolchains.msvc` 所指工具链的 `VC/Redist/MSVC/14.44.35112/x64/Microsoft.VC143.CRT`，三文件实际版本均为 `14.44.35211.0`、AMD64、Microsoft 签名 Valid：

| 成员 | 字节 | SHA-256 |
| --- | ---: | --- |
| vcruntime140.dll | 124544 | d5e4d9a3e835fa679450145d6a7d94e36573a509317111904d9b3712c30d9066 |
| vcruntime140_1.dll | 49792 | 1f2d41c4aa5db0bc33ebf7b66d72943a817d7ce6cbe880502a9403823633093f |
| msvcp140.dll | 557728 | 0f885b509a685d2bbfa652fed26b5fb31d88fbdab0a978c641d1c7b8aa460aa9 |

签名是文件来源证据，不替代许可条款。按现有 VS 工具链的适用许可和 [VS2022 可再分发代码清单](https://learn.microsoft.com/en-us/visualstudio/releases/2022/redistribution#visual-c-runtime-files)处理，保留所需版权／许可记录；[Microsoft 分发说明](https://learn.microsoft.com/en-us/cpp/windows/redistributing-visual-cpp-files?view=msvc-170)与 [PyMuPDF 的同类 Windows 导入故障说明](https://pymupdf.readthedocs.io/en/latest/installation.html#problems-after-installation)仅支持实施依据，不代替本项目实际运行验收。

## 默认打包行为

权威 stager 只接收明确 donor 或已包含完整批准套件的 Python runtime，不搜索系统目录或下载。默认 desktop builder 必须显式解析并交入完整 donor，或因缺件／未知身份拒绝生成包；不能让修复仅在 opt-in 参数下成立、默认仍产出已知缺依赖的包。官方 VS 安装清单与精确版本文件可以作为构建器定位输入，不能从 PATH、System32、私人目录或相似文件名选 DLL。

三个最终文件须为已批准的同套身份。若原 Python donor 的两个 VCRUNTIME 不同，只允许在本轮全新 staging 副本中、核准原始和最终摘要后受控替换；原 donor 和旧候选不变。MSVCP140 先仅位于 `runtime/`，不改变 Tauri 根资源映射；根目录与 `core/` 的两份 VCRUNTIME 应与 Python runtime 最终套件一致。manifest 分别记录原始 donor、最终成员、每个真实安装位置和维护责任，不把 MSVCP140 误称为已放在根目录／core。

## 旧编译组件与新 runtime

复用 Host SHA `ac4c399b34ce3bbeab2a8f82e9f1d039b03c04b82f537ebdb99e6cd4863de145`、Core SHA `40b563626a07c5bd9658da9b1b8a8c2289bf930e4d9fbbf4b39b20fe7909db30` 时，原构建收据、c453 源码与 `6b30cae2…` dirty 补丁身份继续保留。新 runtime 由当前权威 stager、完整当前源码快照、实际 worker／launcher／Python／DLL 输入和 canonical 执行收据独立证明。

新候选须使用明确的组件来源模型和全新 identity／manifest，不能填写一个虚构的“整包由当前源码编译”身份，不能手造 Host build PASS 或修改旧收据。完整逐成员差分应拒绝未经声明的变化：本轮本地 donor 两个 VCRUNTIME 与旧字节相同，预计产品字节只增加 `runtime/msvcp140.dll` 并更新 runtime／candidate manifest；其他产品文件必须逐字节保持。实际差分若超出该范围应停下来核查，不能扩大目录白名单放过。

通过新的本地组件资格后才可沿现有纯 NSIS bundle、`--no-binary-patching` 路径生成新安装器。安装消费者必须明确接收该新身份，复核完整 payload 与组件来源，不把它伪装成旧 `local-pinned-packaging/v1`、正式 CI candidate 或 Release；原默认资格分支不得放宽。

## 必要验证

先验证缺件／未知 SHA／混版／链接／受控替换／安装位置与 manifest 的回归，再在新 runtime 使用真实解释器、正常启动环境及原生 DLL 搜索导入两个模块，核实际加载路径；不得靠额外 `add_dll_directory` 或 PATH 变通作为新包成功。用新合成 PDF 和新请求完成 Core 转换、全文／定位、重启和导出恢复，再验证新安装包。旧失败或 UNKNOWN 请求不重放；测试与隔离运行的退出、payload 及输入前后摘要分别记录。

本记录不宣称上述实现／构建／安装已完成，也不授予 Owner 账户安装、Green 替换、真实资料覆盖、提交／推送／合并或发布权限。
