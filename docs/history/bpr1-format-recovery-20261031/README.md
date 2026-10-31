# bpr1 四格式实际 worker 与分段恢复资格（2026-10-31）

这是一条复用同一 bpr1 后端包的三阶段实际证据链，**不是单次全旅程 PASS**。包内 Python 3.12.13、实际 `start-backend.py` / worker profile / Core / Office 与 PDF workers 原地使用，没有重新构建、安装或复制包。包来源资格仍绑定 `71569d17` + dirty patch `5bbc8d12…`，Core SHA `07a9fe00…`、包 manifest SHA `e2e22f8e…`；三次探针的源码快照分别记录，不能将包的原资格移绑到当前 checkout。包的实际准备资格另见[原记录](../storage-cleanup/2026-10-31-backend-runtime-in-place/ACTUAL-PREPARATION.md)。

| 阶段 | 已实际完成 | 真实终态与源码 patch |
| --- | --- | --- |
| `fmt1` | 合成 DOCX/XLSX/PPTX/文字 PDF 的4个成功 worker job、1个坏 DOCX 失败；原件 SHA、内容/结构/损失/质量、8个定位及8次坏 checksum 拒绝；4份笔记 v1/v2、4次 stale-write 409、Markdown 与原定位记录导出 | child1 / wrapper1，FAIL；首个 Core 已 terminate/reap exit1，但10035连接未完成，原严格拒连守卫未满足。HEAD `33ccac5a` + `48ea8379…`，source_consistent=true。未做冷启/备份/恢复。 |
| `fmtc1` | 原 DB 冷启读回全部既定对象；live Core API 生成 verified 380,928 B 备份，SHA `684df39e81f1ede7f46f66ef64c8df8060c960b76f6470469e6dca74aeb1994c` | child1 / wrapper1，FAIL；PID39680 已 reap exit1，第一相仍能打开 signaled/exit1 的终止进程对象，第二相消失，原“必须 NOT_FOUND”守卫过严。HEAD `33ccac5a` + `25345d98…`，source_consistent=true。未做恢复、未重做 worker/备份前序。 |
| `fmtr1` | 直接复用上述备份，Core maintenance restore exit0/verified；新 run 独立 DB 读回原件、成功/失败 job、结构/损失/质量、定位、笔记与历史版本、导出均相等；实际包启动器和后继 owned 生命周期守卫通过 | child0 / wrapper0，LOCAL_PASS，10.446 s；HEAD `33ccac5a` + `25345d98…`，source_consistent=true。只恢复及读回，不再冷启原 DB、生成备份或请求5个 worker。原两次 FAIL 不变。 |

Windows 进程终止后对象进入 signaled 状态，仍可能因未关闭的句柄而暂存；[Microsoft：Terminating a Process](https://learn.microsoft.com/en-us/windows/win32/procthread/terminating-a-process) 与 [Process Handles and Identifiers](https://learn.microsoft.com/en-us/windows/desktop/procthread/process-handles-and-identifiers) 说明了该差异。后继守卫须先有 owned Popen reap，再在两相精确 PID 观测中满足 NOT_FOUND，或 wait0/signaled + 成功查询且退出码非259并匹配 owned exit；每相精确端口 IPv4/IPv6 均无 LISTEN。`fmtr1` PID28252 第一相 signaled/exit1、第二相 NOT_FOUND，符合该条件。socket10035仍记 PENDING，未声称 REFUSED/连接关闭，也不声称 graceful shutdown 或全机 worker 清场。12项纯 PID 谓词反例与实际 OS 观测是不同证据层。

独立只读后核复算了4格式内容/结构/损失/质量及定位 checksum，重核23个选定文件 SHA，并重核新恢复目录5个原件 CAS SHA；原 receipt、fixture/CAS、备份和选定包成员的前后保护均成立。`fmtr1` 原 DB/侧文件仅有大小、mtime 与身份前后相等证据，不是数据库内容哈希；没有重新 hash 全部16,947个包成员。本次后核直接写 ignored 小报告，没有运行新 Core/worker/SQLite/网络任务。机器身份、原命令、收据和有限复核范围见 [MANIFEST.json](MANIFEST.json)，原始载荷留在既有 ignored run，不复制到公开历史。

本记录只补充当前 bpr1 的选定格式实际 worker、保存/定位/导出及分段恢复资格。它不代表完整 CL-02/J1、混合目录批量/断点续跑、源应用渲染或往返重建、OCR、媒体/ASR或模型推理、UI、安装运行、专业事实核验、外部 Green 替换或 Owner 验收。ASR BUNDLED 是原包库存状态，本旅程没有执行 ASR。现有原件、失败、备份与恢复数据保留，本记录不增加清理授权。
