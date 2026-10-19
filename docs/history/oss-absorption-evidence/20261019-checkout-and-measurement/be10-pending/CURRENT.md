# BE10 原生只读context预览消费：冻结接续入口

状态：**ISOLATED_PROPOSAL_PASS_NOT_APPLIED / NOT_APPLIED / BE10整体PARTIAL**。本目录12候选文件（4改8新）已冻结；root唯一产品writer。

- 补丁 `be10-native-preview.patch` SHA-256 `46d1312c965151a6ef72cb837be9d6c198a7069c482cc8164a52d3481ec1e9b4`，`git apply --check` exit0。
- 精确before/after、文件数及字节：`code-manifest.json`；4份原字节在`preimages/`，12候选在`proposal/`。不含依赖、锁、用户/模型/全局配置修改。
- 最终证据 `validation-summary.json` 和逐步`validation.json`；每步前后12候选与实际测试镜像hash一致。最终canonical `be10-native-preview-final-current-1019` child/outer均0且source_consistent=true；当前公共依赖基线114文件无漂移。
- 最终结果：JSON Schema 1 pytest循环16共同正负case；Rust DTO 1 test循环相同16case；实际Core 25（新增5 + 既有handoff6/Observer6/pure8）；native桥29（新增owned Core消费1 + 既有桥28）；Ruff通过。不是全产品全量测试，不累计历史重复次数。
- 真实红例：`red-validation.json`只在owned镜像移除workspace/epoch拒绝，实际HTTP200被409断言捕获，子101；`red-identity-guard.log`保留。镜像已恢复原字节并重编译最终绿色，产品与候选从未注入缺陷。
- 隔离镜像 `validation-mirror/`仅8crate公共源依赖闭包/固定公开嵌入合同/选定测试；独立`validation-target/`。`native-harness/`仅真实桥/test两文件、既有公开依赖的最小Cargo声明/独立lock，源码与正式候选逐hash等同，不含Tauri/环境/缓存复制。共享Cargo cache通过原canonical入口复用。

实现固定POST与human-only有限native operation；严格context/64KiB/无query、同一只读transaction核对已有workspace/restore epoch及冻结version/hash，返回CURRENT/STALE/NOT_FOUND和未认证来源；不读正文，不投递/执行/接纳/创建业务DB。原Observer三端口及human/machine原接口保留。

确切下一接线见`proposal/docs/contracts/project-handoff-preview-v1.md`：先做同事务workspace/restore_epoch+冻结引用绑定的本地human snapshot读取，再接现有PinnedReferencePanel与显式预览/关闭返回原草稿、焦点、布局。现panel/document_version无恢复epoch约束，不能将metadata预览当正文阅读授权；禁止直接Library.openDocument进入编辑/working-state写路径。OS URI、外部WORK-LAB/DESIGN-LAB真实UI/native与安装均NOT_EXECUTED。

应用：root核对4份preimage和8新目标不存在，串行应用12文件；按`validation.json`命令在正式源运行相同合同与进程回归。native真实Core测试需BE10_PREVIEW_CORE指向本轮owned构建产物，无该值测试失败不skip。该测试复用现有Tauri桥模块，未执行完整Tauri构建/已安装宿主验收。回退仅该4份before和8新文件，不覆盖其他writer改动。
