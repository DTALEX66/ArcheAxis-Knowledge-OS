# 小栖 / ASTRYN 迁移现状

状态 **PARTIAL / NOT_READY_TO_DELETE**。此页是现状与证据入口，进度仍回写现有 UI 执行记录。
Owner 已决定小栖直接适配 AAOS，后续不再在 ASTRYN 独立开发；源仓库目前保留。

现场核对：`D:/All projects/ASTRYN` 的版本化工作区干净，HEAD 与云端
`DTALEX66/ASTRYN` main 均为 `3115378bb3fe13849ed422c739002428fef82892`。
云端 feature 分支为 `38d1fb24a5d88ee40c467af8f5135ed6ae5cf973`，两条云端分支均有本地对应引用。
本轮没有删除、推送、归档云端仓库或修改源仓库。

现已完成以下保全与接入：

- 206 个版本化文件的源码 ZIP，逐项以 Git blob 身份核对，附每项 SHA-256。
- 全部现有本地分支及远端跟踪引用的 Git bundle，通过 `git bundle verify`，覆盖已核两条云端分支。
- 保全目录：`.project-local/archives/astryn-versioned-20261018T111424Z/`；完整本地清单为该目录 `MANIFEST.json`。
- 9 张状态位图已接入正式会话呈现；2 份来源文件与原始哈希保留在 `frontend/src/companion/PROVENANCE.json`。
- 新原生候选已包含这些呈现、正式搜索和模型通道改动，成员校验通过；候选配置保存/冷重开有独立原生证据。

源码 ZIP 为 111,493,070 字节，SHA-256 `9cb97365e15474137e1db2fe5b53cc7cb43150c3201e9d66538f3cb3281d36dd`。
Git bundle 为 134,091,418 字节，SHA-256 `7f1edd3afef1497fd8a458f1b3e4879d8a2da3561b6eb6148a31d3067aa92bce`。
均为忽略的本地保全资料，不将私有源码、运行时或原始会话上传到公共仓库。

目前仍不能删除本地或云端源仓库：

- 原始素材已经另行保全：指定 `虚拟人物/小栖/assets` 与 `store` 中的 75 个独立对象、126 条逻辑路径全部通过 ZIP 成员、CRC、逐项 SHA-256 和恢复映射校验；51 组是两个源目录之间的 NTFS hardlink，没有外部别名。未进入 `.hilo` 工具内部状态；源 `.project-local/` 与 `node_modules/` 不属于源码及素材迁移完成证明。
- 云端只读元数据已另存本地：2 分支、1 PR，当前可见 issues/tags/releases/comments/reviews/rulesets 均读回 0；16 个 JSON 解析及清单15文件哈希核对通过。wiki 内容、事件时间线、discussions、附件及未覆盖设置仍未保全，不能宣称云端已完整迁移。
- home/reading/sidebar 与 page14 已在源码接入同一个 App 生命周期会话服务。草稿、通道、冻结材料和原请求 ID 共享；视图卸载不取消 Core 请求，UNKNOWN 只查原 ID。14 项新增合成回归覆盖重复确认、换槽、材料迟到、恢复屏障、工作区替换和目录恢复。人格结构化配置、真实语音、原生共享旅程与完整恢复验收尚未完成；九态静图不等于动画或口型。
- 完整当前原生学习闭环与 Owner 产品验收仍未完成；源码归档和测试不能替代功能迁移。

直接适配继续使用 AAOS Core 的配置、会话和记忆真值；不启用 ASTRYN 的演示存储、合成宿主或第二模型代理。
原始整合决定见 [Owner 决定](../../workspace/intake/20261018-xiaoqi-in-project.md)，
本轮证据见 [共享会话与候选更新回执](receipts/AAOS-SHARED-COMPANION-20261018.json)。原生 home/sidebar/reader 共享及折叠重开已核；展开侧栏陪伴造成导航零高度，后续完整页/冷启未执行，整个旅程 FAIL。见[审计覆盖与缺陷](AAOS-AUDIT-TEST-COVERAGE-20261018.md)。

## 2026-10-18 原始素材保全与共享会话增量

素材归档：`.project-local/archives/astryn-originals-20261018-20261018T112515305Z-8fc7933f/`。
`manifest.json` SHA-256 `78ef181cc75c71686ea94e793acc0ec26a6546a31edfbe1e38ecade65c204357`；
`original-objects.zip` 274,097,787 bytes，SHA-256 `e7188654e752532f2a13aeba8fca0ce3df416bee5963c59f0028f14c4caffb1b`。
保全 274,087,867 个唯一对象字节，可恢复 459,018,818 个逻辑路径字节。源前后身份、链接、大小、时间、内容一致，指定目录剩余未保全素材为 0。
素材 ZIP 不覆盖云端元数据，也不授予源目录删除资格。独立云端快照目录为
`.project-local/archives/astryn-cloud-metadata-20261018-20261018T114724Z-7fc1502a/`；
`sha256-manifest.json` SHA-256 `536a38e62d85f2b5b6c66af0cfa0d6b82a1f80d854d1705e6e421a80afac6c96`。
未覆盖项见该目录 `coverage.json`；没有云端写入或源仓库删除。

源码入口：`frontend/src/companion/CompanionSession.ts`、`CompanionSessionProvider.tsx`。
三槽与 page14 只包装 AAOS Core 的 history/preview/execute/status/cancel，不引入 ASTRYN 演示存储、第二模型代理或本地伪终态。
恢复开始后立即暂停发送；普通 CAS 回包不能解锁，恢复结束后须独立读回相同 workspace/restore 身份。
目录失败有显式只读重试；旧 scope 的迟到模型配置不能触发后续 preview，旧 execute 回包不能继续旧 history。
源码与本地构建、候选部署及原生旅程分别按收据判断，不能从新增单元测试推导安装版完成。
