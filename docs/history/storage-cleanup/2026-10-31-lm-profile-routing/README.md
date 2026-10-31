# LM Studio profile收据：规范生成落点

从既有49项固定清单精确查当前tracked源码，唯一完整路径字面量命中 `lm_studio_profile.mjs` 的旧 `.project-local/runs/lm-studio-profile` 输出。此搜索不证明其他48项没有动态消费者，也不认领旧载荷。正式修复仅让receipt通过既有Node `projectPython` / `safePath` 调用正式 `dev.artifact_directory`，有env与无env均落 `runs/<worktree>/<run>/artifacts/lm-studio-profile/<uuid>/`；SDK/provider/profile及模型加载卸载策略不变。候选两patch保留；root部署另加Python UTF-8及测试正确恢复原env缺省值，最终源码两文件SHA独立列于MANIFEST。

候选3项纯path检查与正式 `nrm-lmp2` 资格分列：后者真实Node测试原4项合成加载策略加3项路径回归，7通过、actual/wrapper0、source_consistent=true；foreign run负控的预期ValueError traceback保留。未执行main或真实SDK/client/模型操作，不证明近期实际调用或新产品runtime资格。旧root未删除/搬迁，回收0B，49项仍0获清理资格；不把未来落点修复当作旧目录清理完成。当前进度仅沿[唯一执行记录](../../../current/AAOS-UI-FIRST-EXECUTION-20261009.md)。
