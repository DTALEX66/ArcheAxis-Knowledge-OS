# Contributing to ArcheAxis Knowledge OS

感谢你考虑为ArcheAxis Knowledge OS做出贡献！

## 行为准则

### 我们的承诺
- 尊重所有贡献者
- 欢迎不同的观点和经验
- 接受建设性的批评
- 关注对社区最有利的事情

## 如何贡献

### 报告Bug

**提交Bug前请检查**:
1. 搜索已存在的issues
2. 使用最新版本
3. 准备复现步骤

**Bug报告应包含**:
- 清晰的标题
- 详细的描述
- 复现步骤
- 期望行为
- 实际行为
- 截图（如适用）
- 环境信息（OS、Python版本、Node版本）

### 提出新功能

1. 先开issue讨论
2. 说明功能价值
3. 描述使用场景
4. 考虑替代方案

### Pull Request流程

#### 1. Fork项目
```bash
git clone https://github.com/YOUR-USERNAME/ArcheAxis-Knowledge-OS.git
cd ArcheAxis-Knowledge-OS
git remote add upstream https://github.com/DTALEX66/ArcheAxis-Knowledge-OS.git
```

#### 2. 创建分支
```bash
git checkout -b feature/your-feature-name
# 或
git checkout -b fix/your-bug-fix
```

分支命名规范:
- `feature/` - 新功能
- `fix/` - Bug修复
- `docs/` - 文档更新
- `refactor/` - 代码重构
- `test/` - 测试相关

#### 3. 进行更改

**代码规范**:

Python:
```bash
# 使用black格式化
black archeaxis/ app/

# 使用ruff检查
ruff check archeaxis/ app/
```

TypeScript/React:
```bash
# 使用prettier格式化
npm run format

# 运行linter
npm run lint
```

**提交规范**:
```
type(scope): subject

body

footer
```

类型:
- `feat`: 新功能
- `fix`: Bug修复
- `docs`: 文档
- `style`: 格式
- `refactor`: 重构
- `test`: 测试
- `chore`: 构建/工具

示例:
```
feat(learning): 实现FSRS算法

- 添加记忆稳定性计算
- 实现间隔调度
- 添加测试覆盖

Closes #123
```

#### 4. 测试

```bash
# 运行所有测试
pytest tests/ -v

# 运行特定测试
pytest tests/test_fsrs.py -v

# 检查覆盖率
pytest --cov=archeaxis tests/
```

前端测试:
```bash
cd frontend
npm test
```

#### 5. 提交PR

**PR标题**: 清晰描述更改
**PR描述**应包含:
- 更改概述
- 相关issue
- 测试说明
- 截图（UI更改）
- 破坏性更改说明

**PR检查清单**:
- [ ] 代码遵循项目规范
- [ ] 添加了测试
- [ ] 测试通过
- [ ] 更新了文档
- [ ] 更新了CHANGELOG.md
- [ ] 提交信息清晰

## 开发设置

### 后端开发
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
```

### 前端开发
```bash
cd frontend
npm install
npm run dev
```

### 运行开发环境
```bash
# 终端1 - 后端
python -m app.runtime_entrypoint core

# 终端2 - 前端
cd frontend && npm run dev
```

## 代码审查

### 审查者关注点
- 代码质量
- 测试覆盖
- 文档完整性
- 性能影响
- 安全问题

### 响应反馈
- 及时回复审查意见
- 解释设计决策
- 进行必要的更改

## 文档

### 更新文档的情况
- 添加新功能
- 更改API
- 修改配置
- 更新依赖

### 文档位置
- API: `docs/API-DOCUMENTATION.md`
- 部署: `docs/DEPLOYMENT-GUIDE.md`
- README: `README.md`
- Changelog: `CHANGELOG.md`

## 测试指南

### 测试类型
1. **单元测试**: 测试单个函数/组件
2. **集成测试**: 测试模块间交互
3. **端到端测试**: 测试完整流程

### 编写测试
```python
# Python测试示例
def test_fsrs_scheduler():
    scheduler = FSRSScheduler()
    card = scheduler.init_card()
    assert card.stability > 0
```

```typescript
// TypeScript测试示例
it('should render upload button', () => {
  render(<FileUpload />);
  expect(screen.getByText(/上传/)).toBeInTheDocument();
});
```

## 发布流程

1. 更新版本号
2. 更新CHANGELOG.md
3. 创建Git tag
4. 推送到GitHub
5. 创建Release

## 获取帮助

- 📧 Email: support@archeaxis.com
- 💬 Issues: [GitHub Issues](https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/issues)
- 📚 文档: [docs/](docs/)

## 许可证

贡献即表示同意你的贡献将在MIT许可下授权。

---

再次感谢你的贡献！🎉
