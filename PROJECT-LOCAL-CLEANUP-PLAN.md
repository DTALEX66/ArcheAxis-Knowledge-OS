# .project-local/ 目录清理计划

## 发现问题
.project-local/ 占用 **111GB** - 这是主要问题！

## 详细分析
- `build/` - 76GB ⚠️ 构建缓存
- `recovery/` - 9.6GB ⚠️ 恢复备份
- `worktrees/` - 8.3GB ⚠️ Git工作树
- `mig/` - 4.4GB ⚠️ 迁移文件
- `cache/` - 3.5GB ⚠️ 通用缓存
- `archives/` - 2.4GB ⚠️ 归档文件
- `artifacts/` - 2.3GB ⚠️ 构建产物
- `legacy-scratch-20261008/` - 1.8GB ⚠️ 旧临时文件

## 建议清理
所有这些都是可以删除的临时/缓存文件

**预计释放**: ~111GB

## 执行?
