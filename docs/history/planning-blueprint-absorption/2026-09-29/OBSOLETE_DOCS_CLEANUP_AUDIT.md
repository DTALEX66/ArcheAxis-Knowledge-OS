# Superseded 文档精确盘点与清理结论

盘点日期：2026-09-29。来源为 `docs/DOCUMENTATION_AUTHORITY_INDEX.md` 的明确 superseded 列表、仓库精确路径/hash/status 扫描及 basename 引用扫描。

**结论：本轮没有安全可删除项。** 索引已禁止把“日期较旧”当作删除证据，并要求先完成逐路径/hash/reference manifest、兼容链接更新和回归检查。以下文档仍有仓内引用；删除会破坏历史证据或引用。迁移到统一历史目录也须先完成引用目标改写与验证。本清单用于下一次逐项迁移审核，不代表物理迁移/删除已授权。

| 源路径（仓库相对） | SHA-256 | 工作树状态 | 已发现引用 / 处置 |
| --- | --- | --- | --- |
| `docs/current/AXR_060_COMPLETION_AUDIT_2026-08-23.md` | `B98438008CE429652EB2B6508728A61A22D8A020180AD493D4E11B2711824FBE` | clean | Authority index、R6/branch receipts、plans、tests、legacy manifest；KEEP |
| `docs/current/AXR_060_401_UNIFIED_CLIENT_HANDOFF_2026-08-24.md` | `250B885309D98F2B9463B48D090AD0B484C1492131FEA513897A6A3312DD6C68` | clean | Authority index、R6/branch receipts、plans、legacy manifest；KEEP |
| `docs/current/CURRENT_PRODUCT_PLAN_V2.md` | `40E1816A6586BCBD028FD7F5C9FBEB7354540F1610BD05C26709168BD188D70A` | clean | Authority index、R6/R5/branch receipts、tests、legacy manifest；KEEP |
| `docs/current/CONTINUATION_HANDOFF_2026-09-03.md` | `F16127D6BCFF7A78536929EF753F20C66AF0FC26A907FBCB0CC3B0E8E338978E` | clean | Authority index、R6/branch receipts、legacy manifest；KEEP |
| `docs/current/CURRENT_REALITY_2026-09-01.md` | `BED04848423F54FAF6DB11632CD943AAA107CB552E1164DB566221CE4B045E2C` | clean | Authority index、truth logs, current diagnostics, tests, legacy manifest; KEEP |
| `docs/current/FRONTEND_CONSOLIDATION_V1_2026-08-28.md` | `74E032CAE5FBEED70B148F3DD8546915CA04DE55D32E18B619F94FE0217A6B29` | clean | Authority index、UI roadmap/adoption、legacy manifest；KEEP |
| `docs/current/UI_PRODUCTION_ADOPTION_V3_2026-08-27.md` | `5F020527438899150C0D534418FCD9AA4A6159C74D08DB6CB4C382FD9B37B88A` | clean | Authority index、PROJECT_STATUS、legacy manifest；KEEP |
| `docs/current/AAOS-CLOUD-AUDIT-RECONCILIATION-20260923.md` | `2AB167A79EE0881300310A3FEBA339431478EC7D7346606BFB0C43B4CB39F9CA` | clean | Authority index、dated plan/R6 receipts/tests/DSH handoff；KEEP |
| `docs/current/UI_V3_PRODUCT_ROADMAP.md` | `33F7F03338FE4E89BE70B38F83FEA340E39DCD0EB9482DAB15FC23FBA51FD4B9` | **dirty (M)** | Authority index、UI checkpoint/coverage/journey/tests/legacy manifest；KEEP, do not move/overwrite |
| `docs/truth/ARCHITECTURE_FINAL.md` | `93238FD2E0AA8F5A10B00C534E6BEC45F7738B50BD0219C96A11ADBD440CE750` | clean | Authority index、truth README、legacy manifest；KEEP |
| `docs/truth/AUTHORITY_CONTRACT.md` | `39F2F4E3E0F4E55BA3B798907B61CC4038B5B158BEC780CEA19DC636BAFC2F38` | clean | README、Authority index、truth logs/tests、legacy manifest；KEEP |
| `docs/current/DSH-COMPLETION-REPORT-20260918.md` | `3B4B292DDD1B30A7BACD3554CD7795E2399F65001D205B241D87C1265CFEEC93` | clean | Authority index、R5 receipts、paired Hermes audit; KEEP |
| `docs/current/HERMES-FULL-AUDIT-PROMPT-20260918.md` | `1CBF675B1F67B4B099ED28D9CE5079A5508B9A7CDF1B9402EA274EDD5AA0525F` | clean | Authority index、R5 audit; KEEP |
| `docs/current/AXM_LANGUAGE_AUDIT_TASK_ADOPTION_2026-09-02.md` | `F553878A2E0D4A0962EB45AD8804A990B9F03DC1D8EFE3D81CEBFEC76D488C0B` | clean | Authority index、truth/dated plans/current reality/T17 audit/legacy manifest; KEEP |
| `docs/current/AX_DIRECTORY_MIGRATION_TASK_ADOPTION_2026-09-02.md` | `32081B635A824089C2B0B46D46622949D0421DDB2E55191E3A0A0EC4124D4720` | clean | Authority and Directory indexes、truth/dated plans/T17 audit/legacy manifest; KEEP |
| `docs/ABSORPTION_EXECUTION_MATRIX.md` | `A2C51AE1B9D27A90667B80348589370054C466CAE1385E4BDDC5CFBA6ECD26BD` | clean | Authority index、handoff/blueprint/README/absorbed-design evidence/T17; KEEP |
| `docs/PROJECT_STATUS.md` | `9D73653D41658379B47B9EF49DB76B93A4A006A0E981FA1D7D7A56535222AA3E` | clean | README、Authority index、truth/legacy/docs/test/current reports; KEEP |
| `docs/superpowers/specs/2026-08-23-six-space-closed-loop-design.md` | `75BF69F7CC8B26E495F250F29A42E8ACE98508DF601AABA9292EF4F476B51904` | clean | Authority index、dated plan/T17/legacy manifest; KEEP |
| `HERMES_HANDOFF.md` | `1065D8A485531C97268F40747E206F73851C3C1AC9D450EF217C8D762D555474` | clean | Authority and Directory indexes、legacy manifest、dated lineage/branch/path receipts; KEEP |

另外，当前 `docs/history/` 下还有多组未跟踪材料，所有权/来源未在本轮逐项确证，因此未列入删除对象，也未清理。项目的 `docs/current/AUTHORITY_AND_STATUS_RULES_V1.md` 明确禁止在 cleanup 中删除历史任务、能力、需求及命名映射；`docs/DIRECTORY_AUTHORITY_INDEX.md` 说明目录分类本身不授予迁移或删除权限。`docs/current/UI_V3_PRODUCT_ROADMAP.md` 当前有用户未提交修改，需由后续工作单独审阅。表中 SHA-256 是本轮扫描时实际文件字节的哈希；路线图当前为 dirty (M)，任何迁移前都要重新计算并复核。

逐路径的当前字节哈希、Git 状态和 basename 引用命中见 [OBSOLETE_DOCS_REFERENCES.json](OBSOLETE_DOCS_REFERENCES.json)；扫描范围为仓库可读文本路径，排除本归档自身。

下一步如需实物迁移：逐份记录当前工作树 SHA-256（包含未提交内容）、源/目标路径、所有引用的改写、回滚路径和 exact deletion-authorization state；先以兼容链接/重定向维持旧引用，再做文档链接回归。完成这些条件前维持原路径及字节不变。
