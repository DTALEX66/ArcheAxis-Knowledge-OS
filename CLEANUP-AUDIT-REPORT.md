# 仓库清理审计报告 - 2026-10-16

## 当前状态
- 总大小：155 GB
- 文件数：2,121,197个文件
- 文件夹数：475,128个

## 大目录分析

### 1. assets/ - 999MB ⚠️
- ASTRYN完整资产包
- 包含：小栖角色图片、概念图、状态图
- **状态**：生产资产，不应删除
- **建议**：保留，或移动到外部存储

### 2. docs/ - 505MB ⚠️
- 文档和历史归档
- 包含：任务包、执行记录、审计报告
- **状态**：重要文档
- **建议**：保留，或归档压缩旧版本

### 3. frontend/node_modules/ - 233MB ✅
- npm依赖包
- **状态**：可重新安装
- **安全性**：✅ 完全安全删除
- **恢复**：`npm install`

### 4. .project-local/ - 未知大小 🔍
- 构建产物和缓存
- **状态**：临时文件
- **安全性**：✅ 安全删除
- **恢复**：重新构建生成

### 5. .hermes/ - 未知大小 🔍
- Hermes任务运行时缓存
- **状态**：临时缓存
- **安全性**：✅ 安全删除
- **恢复**：自动重建

### 6. data/ - 98MB ⚠️
- 数据库文件
- **状态**：生产数据
- **建议**：不要删除

### 7. tests/ - 27MB
- 测试代码和fixtures
- **状态**：源代码
- **建议**：保留

## 安全清理列表

### 完全安全（可立即删除）
1. ✅ `.project-local/runs/` - 构建缓存
2. ✅ `.project-local/worktrees/` - 临时工作树
3. ✅ `.hermes/` - 任务缓存
4. ✅ `frontend/node_modules/` - npm依赖
5. ✅ `.venv/` - Python虚拟环境
6. ✅ `__pycache__/` - Python字节码
7. ✅ `.ruff_cache/` - Ruff缓存
8. ✅ `.pytest_cache/` - Pytest缓存

### 需要确认（建议压缩或移动）
1. ⚠️ `assets/astryn-full/` - 553MB资产包
2. ⚠️ `docs/history/` - 历史文档
3. ⚠️ `docs/authority/` - 旧任务包

### 绝对不能删除
1. ❌ `data/archeaxis.sqlite` - 生产数据库
2. ❌ `assets/brand/` - 品牌资源
3. ❌ `src/`, `app/`, `crates/` - 源代码
4. ❌ `config/` - 配置文件
5. ❌ `.git/` - Git历史

## 预计清理效果

### 方案1：保守清理（推荐）
删除：
- `.project-local/` 
- `.hermes/`
- `frontend/node_modules/`
- Python缓存

**预计释放**：~10-20GB

### 方案2：激进清理
删除方案1 + 
- 移动 `assets/astryn-full/` 到外部
- 压缩 `docs/history/`

**预计释放**：~15-30GB

### 方案3：Git历史清理
使用 `git filter-branch` 或 `BFG Repo-Cleaner` 清理Git历史中的大文件

**预计释放**：可能50GB+

## Git仓库分析

需要检查：
```bash
git rev-list --objects --all | 
  git cat-file --batch-check='%(objecttype) %(objectname) %(objectsize) %(rest)' |
  awk '/^blob/ {print $3, $4}' | 
  sort -n | 
  tail -20
```

## 清理执行计划

### 阶段1：缓存清理（安全）
```bash
rm -rf .project-local/
rm -rf .hermes/
rm -rf frontend/node_modules/
rm -rf .venv/
find . -type d -name __pycache__ -exec rm -rf {} +
find . -type d -name .pytest_cache -exec rm -rf {} +
```

### 阶段2：Git垃圾回收
```bash
git gc --aggressive --prune=now
git repack -a -d --depth=250 --window=250
```

### 阶段3：资产归档（可选）
```bash
# 移动大资产到外部存储
mv assets/astryn-full/ ../ArcheAxis-Assets/
# 创建符号链接
ln -s ../ArcheAxis-Assets/astryn-full/ assets/astryn-full
```

## 风险评估

### 低风险（推荐执行）
- 删除构建缓存
- 删除node_modules
- 删除Python缓存

### 中风险（需要确认）
- 移动大型资产
- 压缩历史文档

### 高风险（不建议）
- 修改Git历史
- 删除数据库备份

## 建议执行顺序

1. ✅ 先执行Git提交确保当前状态安全
2. ✅ 清理缓存和临时文件
3. ✅ 运行Git垃圾回收
4. ⚠️ 根据需要移动大资产
5. ⚠️ 清理Git历史（最后考虑）

## 验证清单

清理后验证：
- [ ] 前端可以启动（npm install + npm run dev）
- [ ] 后端可以启动
- [ ] 测试可以通过
- [ ] 数据库完整
- [ ] Git历史完整

## 结论

**推荐方案**：执行阶段1的安全清理
- 预计释放：10-20GB
- 风险：低
- 可恢复性：高

**需要你确认**：是否执行？

---
生成时间：2026-10-16 22:20
状态：等待确认
