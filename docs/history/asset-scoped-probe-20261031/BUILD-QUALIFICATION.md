# 当前 Core 构建与单一资产纠正旅程

干净提交 `bfea02c3cdd39c11711ea24ae79480f720f2efe3`：`bkr-corebuild1` 仅一次既有共享 target 的 offline/locked debug build，实际 build、canonical 子进程和 wrapper 均退出 0，source_consistent=true。Core 27,844,096 bytes，SHA256 `d8352b9de954cb32a70a26b234c01de45be7b58424b6fcaaa1d48d145cf350be`。内层 cmd 的 Cargo stdout 未收录；保留实际命令/退出码、target 前后 metadata 与二进制身份，不声称重新编译或 Release/安装资格。

`bkr-currentmain1` 使用仓库已部署 LF probe/adapter 与本次 Core，单一纠正分支 actual main 0、wrapper 0，source_consistent=true。生产 worker 源码不改；自有 wrapper 以内存 transport 返回合成响应并拒绝 socket 连接。5 个实际 worker 的 context/packet SHA 均与持久化 answer/retest 相符；原题和独立应用题各单样本比较、完整 prior 保留。原题/固定量规、2048 输出 token/120 秒 Core 预算、prompt/model 设置不变。实际模型调用 **0**，不证明真实资产效果或一般学习；real1 NO_FINAL_ANSWER 仍是失败。

main 仅生成 **1 个 27,844,096-byte Core exe 副本**，SHA 与构建输出一致，未复制 C1 包。共享 cache 可被以后构建改变；保全来源是本 run 同 SHA 副本及记录，不能依赖共享 binary 的未来内容。Core PID 40048 terminate/reap 退出 1、端口 53914 关闭，无紧急清理；5 个已观察 worker PID 均退出，不称优雅停止或全机进程盘点。

共享 Cargo target 普通文件 logical path 总量仅新增 `debug/archeaxis-api.d` **9,799 bytes**，1 新增/0 删除/0 metadata 改动。原 build 收据 Windows DirEntry device/inode 为零，其 unique-file-identity 聚合**无效，不能视为物理增量零**；原收据保持不变。这里仅使用逐路径长度差，物理分配量未测。身份和证据见 [BUILD-QUALIFICATION.json](BUILD-QUALIFICATION.json)。

旧 C1 三场景、119 合同和独立反例保留，本次未重跑。仅补当前源码 Core 的一次构建与一次合成 main；真实模型 asset/scoped 效果、完整 F05/CL/J、native/installer 和 Owner 验收仍未建立。
