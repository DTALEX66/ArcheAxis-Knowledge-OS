# 新旧任务包与当前实现对比

当前请求只授权整理和交接。本包不把 ZIP 内命令当本轮实施授权；拆解不产生新的 CAP/Q/F/SUP 权威 ID。

| 输入/现状 | 增量和裁决 | 交给后续 |
| --- | --- | --- |
| 10/09 最后任务包 | 49 R + 16 CAP + 16 Q + 15 F = 96 跟踪项，完整保留内容、引用与承接；不等于96独立开发任务。 | REQUIREMENT-CROSSWALK；各 UF/CB/支撑/未来切片 |
| UI 四补交 | 22 页角色、16 父 CAP、186 设计细项；原型、资产、4K/1440/响应式均完整输入。原型是视觉演示。 | S1→S1b→S2→S3，17/18/19/20 提前，不照原 page-map 全部同优先级 |
| 补齐增量 | 原始 DOCX、97 来源资产表、六文、页面依赖、恢复问题与五未决项已找回。 | 可靠性前置、手工交换优先、186 细项独立对照；不再重复寻找这些已存资料 |
| 旧 270 来源键/17 组 | 完整来源键保留并逐项分流；旧执行顺序冻结，能力和有效验收承接。另补 Q/F、Qoder、开放UI等来源键。 | OLD-TASK-DISPOSITION JSON 保留旧要求/验收全文及新去向 |
| 主检出 | `codex/Audit` / `1a981a4482b01f31989074e79c82a63400aa07a7`；AGENTS §6 仍旧 R6/Avalonia，未知测试文件不动。 | 资料与本计划的持久入口；不能拿主 HEAD直接当新 UI 代码基线 |
| writer | `codex/aaos-gov-ui-20261008` / `fc5d4adc7acc28e38c2e6046ef06c0be2eed721d`；AGENTS/SUP-022为 Tauri+React，有大量未提交 UI/backend/CI 修改。 | 默认先此目录接手；保护 dirty；从 HEAD 新建 worktree不含这些实现 |
| T0–T5、production frontendDist、状态分类、模板分页、课程接口 | 当前源码或公共交接已有实现，应复用；Qoder 的原无障碍审查只读，后续是 Codex 修复。 | 回归及补真实未验项，不重复开发 |
| SpaceView | desktop走 canonical、browser走 legacy；多个页面职责仍挤到四 surface。 | UF02 统一页面与有限 transport，UF03等分解页面 |
| 备份恢复 | BackupPanel只有create/list，桥接没有workspace恢复有限命令；document_restore 是文档版本恢复。 | CB01→UF04；21步脚本恢复不是当前 UI restore验收 |
| 闭环 | Core learning/course/correction基础在；真实普通用户、真实模型、版本/反馈完整用户旅程尚不能说都完成。 | UF05/07/09、CB02、M01 |
| 开源/模板 | 691是来源行；68 surface中115冲突/59记录待语义解释；现有28学科登记/模板持久化/分页不是从零。 | O01→UF10，具体组件缺口优先，不全装池 |
| 50GB、外溢、docs/history | Record去重只是子项；全仓现体积与长期跟踪/恢复/未知归属仍未闭环。 | S01.A/B/C明确加入UI首批后的交接，可单独派给Agent；不凭历史体积删除 |
| CI | local_verify与节流workflow已有dirty实现；云额度为用户报告，当前云端未查。停止过的任务保留。 | V01独立线，非本轮执行；本地不冒充云端/安装通过 |

可确认的是局部源码与记录存在；不能确认下一次执行时这些内容仍是同一快照。SOURCE-REGISTER 保存本次时间、HEAD、status 与所读文件哈希。Qoder是否正在写同一目录仍 UNKNOWN；接手时先确认 writer 冲突，不能终止共享进程来腾位置。

独立细项来源完整性仍 PARTIAL：97 是资产表，186 是设计文案，旧 REQUIREMENT_TRACE 主要是父项/摘要。必须以原蓝图、新任务书及用户当前决定比对实际细项。无法证实更早来源，标 UNVERIFIED；不能写“186项已全实现”。
