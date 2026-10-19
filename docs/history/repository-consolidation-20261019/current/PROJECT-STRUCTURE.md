# AAOS 项目结构说明

## 目录结构

```
ArcheAxis-Knowledge-OS/
├── frontend/              # React + TypeScript 前端
│   ├── src/
│   │   ├── components/    # UI组件库
│   │   ├── spaces/        # 空间视图
│   │   ├── styles/        # 样式文件
│   │   ├── api/           # API客户端
│   │   ├── assets/        # 静态资源
│   │   └── app/           # 应用入口
│   └── package.json
│
├── crates/                # Rust核心服务
│   └── archeaxis-core/    # 核心逻辑
│
├── src-tauri/             # Tauri桌面应用
│
├── archeaxis/             # Python后端
│   ├── core/              # 核心模块
│   ├── services/          # 服务层
│   └── api/               # API层
│
├── tests/                 # 测试套件
│   ├── integration-tests/ # 集成测试
│   └── unit/              # 单元测试
│
├── docs/                  # 文档
│   ├── current/           # 当前文档
│   ├── history/           # 历史归档
│   └── taskpacks/         # 任务包
│
├── assets/                # 资产文件
│   ├── brand/             # 品牌资源
│   ├── xiaoqi/            # 小栖形象
│   └── astryn-full/       # ASTRYN完整资产
│
├── config/                # 配置文件
├── scripts/               # 构建脚本
├── .project-local/        # 本地构建产物
└── .hermes/               # Hermes任务运行时

```

## 核心模块

### 前端 (frontend/)

#### 组件系统
- **基础组件**: `components/` - 可复用UI组件
- **空间视图**: `spaces/` - 工作台、图书馆、学习等空间
- **设计系统**: `styles/` - 全局样式和令牌

#### 关键组件
- `TopNavBar.tsx` - 顶部导航栏
- `BrandHeader.tsx` - 品牌头部
- `XiaoqiPanel.tsx` - 小栖AI助手
- `GlobalSearch.tsx` - 全局搜索
- `DocumentEditor.tsx` - 文档编辑器
- `MediaReader.tsx` - 媒体播放器

### 后端 (archeaxis/)

#### Python服务
- `core/` - 核心业务逻辑
- `services/` - 服务接口
- `api/` - HTTP API层

#### Rust Core (crates/)
- 高性能文件处理
- 内容哈希验证
- 格式转换引擎

### 桌面应用 (src-tauri/)
- Tauri框架
- 系统集成
- 原生功能

## 数据流

```
用户界面 (React)
    ↓
API客户端 (TypeScript)
    ↓
HTTP API (Python/Rust)
    ↓
核心服务 (Rust)
    ↓
本地存储/CAS
```

## 构建系统

### 前端构建
- Vite 5.4.21
- TypeScript 5.5.4
- React 18.3.1

### 后端构建
- Cargo (Rust)
- uv/pip (Python)
- Tauri CLI

### 脚本
- `scripts/runtime/frontend.mjs` - 前端构建脚本
- `run_all.sh` / `run_all.bat` - 全栈启动脚本

## 配置文件

### 项目级
- `PROJECT_CONTRACT.yaml` - 项目合约
- `DIRECTORY_AUTHORITY.yaml` - 目录权限
- `DECISION_SUPERSESSION_LEDGER.yaml` - 决策记录

### 构建级
- `vite.config.ts` - Vite配置
- `tsconfig.json` - TypeScript配置
- `Cargo.toml` - Rust配置
- `pyproject.toml` - Python配置

## 测试策略

### 前端测试
- Vitest (单元测试)
- Testing Library (组件测试)

### 后端测试
- pytest (Python)
- Rust内置测试

### 集成测试
- `integration-tests/` - 端到端测试
- Playwright (浏览器自动化)

## 开发工作流

1. **本地开发**
   ```bash
   cd frontend && npm run dev
   ```

2. **构建验证**
   ```bash
   npm run build
   ```

3. **测试**
   ```bash
   npm test
   pytest
   ```

4. **Tauri开发**
   ```bash
   npm run tauri dev
   ```

## 部署结构

### 桌面应用
- Windows: `.exe`
- macOS: `.dmg`
- Linux: `.AppImage`

### Web版本
- 静态文件部署
- Nginx反向代理
- Python后端服务

## 依赖管理

### npm (前端)
- 270个依赖包
- 关键依赖: React, Vite, Tiptap, PDF.js

### Cargo (Rust)
- 见 `Cargo.lock`

### Python
- 见 `requirements.txt` / `uv.lock`

## 资产管理

### 品牌资源
- Logo: `assets/brand/archeaxis-logo-white.svg`
- 图标: `frontend/src/components/AaosIcon.tsx`

### 小栖形象
- `assets/xiaoqi/xiaoqi-idle.png`
- `assets/xiaoqi/xiaoqi-thinking.png`
- `assets/xiaoqi/xiaoqi-speaking.png`

### ASTRYN资产
- `assets/astryn-full/` (553MB)

## 性能优化

### 代码分割
- 懒加载: PDF.js, DocumentEditor
- 动态导入: 大型组件

### 构建优化
- Tree shaking
- Minification
- Gzip压缩

## 安全策略

- Content Security Policy
- XSS防护
- CSRF保护
- 本地存储加密

## 许可证

MIT License - 见 `LICENSE`

## 相关文档

- [启动指南](../../启动指南.md)
- [支持的格式](SUPPORTED-FORMATS.md)
- [资料索引](../../AAOS-资料索引.md)
