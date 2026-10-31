# 保存版标签与属性接入

范围沿现行 CL-04/J3 和 Stitch 02/03：Core 从同一 editor JSON 保存版本派生标签、JSON 兼容 YAML 属性和明确限制；无新业务存储、迁移或第二写入者。原件、正文、未知属性及历史版本继续由既有 Document/CAS/portable package 保全。标签不是知识采纳或事实核验。

项目级 Cargo 依赖固定为 pulldown-cmark 0.13.4、serde_yaml_ng 0.10.0、unicode-general-category 1.1.0；精确 crate/许可 SHA 见 Cargo.lock 与供应链账本 A051—A053。YAML 库声明 YAML 1.1，使用有界 JSON 兼容映射，不宣称完整 YAML 或 Obsidian 软件往返。继承运行器最初使用已登记的镜像缓存；后继已按 lock 校验可用包/index 并复制到项目 ignored Cargo cache，后续构建用进程级 ARCHEAXIS_CARGO_HOME 显式选它。未更改全局工具、registry/provider/auth 配置。crates.io 网络超时的自有尝试已取消，保留失败，不能计为 PASS。

标签支持行内及 tags 列表、大小写键、下级标签、Unicode 类别；不从代码、链接、转义或非 tags 属性文本造标签。保存不因属性解析失败而阻断。正文解析上限与不支持项返回 PARTIAL；每文档最多256个标签、单标签512 UTF-8字节、前置属性64 KiB/64项，原文仍完整保留。列表单文档标签投影最多16 KiB，超出为 PARTIAL；完整保存版可读取全部有界标签。列表计数只涵盖已加载文档，未知不能当空库。大小写使用 Unicode lowercase，不宣称任意正规化等价。

Markdown/Obsidian 导出保留原有前置属性位置，身份仍在现有详情和 manifest 中。富文本代码/链接的 Markdown 文本投影可能改变标签语境，损失单具名报告，精确 editor 仍在 manifest/package。属性目前从保存正文编辑并派生，视图只读；非完整外部属性编辑器、标签重命名/批改/完整视图或所有软件兼容资格。实际进度及候选验证只写唯一执行记录，不以此说明替代。

回退仅撤销本片明确 hunk 和新模块/探针、恢复本片依赖登记；不批量 restore 其他修改、不修改历史种子、不替换 Green 或真实资料库。旧候选及失败回执保留。
