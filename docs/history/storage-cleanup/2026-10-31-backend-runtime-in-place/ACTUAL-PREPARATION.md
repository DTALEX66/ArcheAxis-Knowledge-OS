# 实际离线 backend 直备后继资格

`bpr1` 在 HEAD71569d17 + dirty patch5bbc8d12939e37a3aa12e2723705bc77d0b079b7517258f25d6401fc9768444e 完成真实 Python3.12.13 backend准备：107项锁定依赖离线安装、单项目wheel构建/安装、隔离import、正式stager均成功；producer/wrapper/canonical均0、source_consistent=true。正式manifest记录1份host runtime、0份中间树；16,947声明成员836,484,884B + manifest3,073,891B，共839,558,775逻辑B。ASR显式供体四文件147,882,941B核SHA并BUNDLED；未运行ASR/模型推理。Core由obuild1正式收据独立绑定，manifest原ASSERTED_NOT_VERIFIED字段不改。

本次BACKEND_ONLY_NO_TAURI_INVALIDATION只对子进程移除两个Cargo target变量，走既有缓存清理早返回，原CI行为未改。8个Tauri对象顶层metadata/inode前后相同，不冒充全部后代独立字节核验；无长期handle锁定保证。`obsgreen1` 使用该包内python -I -B及实际launcher/profile/Core，在新合成data根完成22 HTTP、5 teaching、0 learning/assessment，0model/worker/external-tool请求，canonical0/source一致；包内data/profile未写。green是harness模式，不是外部Green替换；清场terminate exit1且端口关闭，未宣称graceful。

前后全仓计量均PARTIAL/receipt1：141,985,368,043→142,856,788,334可读逻辑B，区间净增871,420,291B，不能混同候选839,558,775B。build/cache/runs分别增24,710,963/2,397,154/844,312,174B。NO_NEW_GROWTH_TRIGGER，无新越线/散落；674 errors、231 private exclusions、581 layout项延续，既有超预算和保全不变，不产生清理授权。

root obsrev1 exit0/source一致，复核关键4成员及收据/源身份、候选data为空，未重hash全部runtime。本附录仅增加实际离线准备与有限合成HTTP资格；UI/Tauri应用build、安装器/桌面安装、推理、完整产品旅程与Owner接受未执行。旧合成记录、spr-pa1 FAIL、preflight HOLD和原计量均保留原字节。JSON仅绑定现有证据；本轮附录直接写入ignored候选，无新canonical/载荷复制，由root发布。
