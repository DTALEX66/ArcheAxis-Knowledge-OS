# Root 应用入口（已冻结）

本候选仅四文件，详见 `manifest.json` 的 before/after SHA-256。`proposed.patch` 是最终补丁；`preimages/` 保留精确原字节，`proposal/` 保留精确候选。proposal 中其他文件仅为隔离验证来源，不属于 write set。

先读 `REVIEW.md`，核对 `FINAL-VERIFICATION.json` 及 `FROZEN-MANIFEST-READBACK.json`。原始 RED 和早期 GREEN 在 `verification.json`。最终 Node 10 PASS、Python 11 PASS、真实 Git clean 后两项 guard PASS，16 MANIFEST / 470 冻结成员 checkout 零字节变化；注入 Git 定位环境仍隔离 PASS。

可重复 runner：`.venv/Scripts/python.exe -B .project-local/audits/hub-lifecycle-gap-20261019/verify_candidate.py`。仅写本审计目录，不改产品。应用后 main preimage 校验预期不再成立；使用封存验证回执或在新隔离目录以应用后的文件作为 baseline。

resource-catalog 既存 core-contract/notices 漂移单独记录，不在本四文件补丁中，不影响本修复自身的 guard GREEN，不代表 catalog 全门禁通过。HUB004 通用生命周期调研暂缓。没有执行真实模型、宿主、浏览器或服务操作。
