# Root 串行应用入口

最终 write set 只有 `manifest.json` 列出的三项，候选字节在 **proposal-v2/**，原字节在 preimages/，补丁为 proposed.patch。proposal/ 与 baseline/ 是保留的首轮 fixture 失败，不应用。

先核对 REVIEW.md、SOURCE-REVIEW.json、verification.json。旧源码 RED：1失败15通过；候选及实际 Git clean 检出分别16通过，生成检查/Core生成相等/apply check通过。历史 qualification、许可、权限、运行与激活状态均未改写，当前未知边界明确记录。

可重复：`.venv/Scripts/python.exe -B .project-local/audits/resource-catalog-source-rebind-20261019/verify.py`。

此处候选冻结供 root 应用；没有产品写入、真实模型、宿主、浏览器或服务操作。
