# ArcheAxis Knowledge OS - 部署指南

## 系统要求

### 硬件
- CPU: 4核心+
- 内存: 8GB+
- 硬盘: 20GB+

### 软件
- Python 3.12+
- Node.js 18+
- Git 2.0+

## 快速开始

### 1. 克隆仓库

```bash
git clone https://github.com/DTALEX66/ArcheAxis-Knowledge-OS.git
cd ArcheAxis-Knowledge-OS
```

### 2. 安装依赖

#### 后端
```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac

pip install -e .
```

#### 前端
```bash
cd frontend
npm install
```

### 3. 配置环境

创建 `.env` 文件：
```env
DATABASE_PATH=data/archeaxis.sqlite
UPLOAD_DIR=data/uploads
```

### 4. 启动服务

#### 开发模式

终端1 - 后端:
```bash
python -m app.runtime_entrypoint core
```

终端2 - 前端:
```bash
cd frontend
npm run dev
```

访问: http://localhost:5173

#### 生产模式

```bash
# 构建前端
cd frontend
npm run build

# 启动后端（生产配置）
python -m app.runtime_entrypoint core --production
```

## 目录结构

```
ArcheAxis-Knowledge-OS/
├── app/                    # 后端应用
│   ├── api/               # API路由
│   │   ├── ai_chat.py    # AI对话
│   │   ├── learning.py   # 学习系统
│   │   └── upload.py     # 文件上传
│   └── main.py           # 主入口
├── archeaxis/             # 核心库
│   └── learning/         # 学习模块
│       └── fsrs_scheduler.py  # FSRS算法
├── frontend/              # 前端应用
│   ├── src/
│   │   ├── components/   # React组件
│   │   │   ├── XiaoqiPanel.tsx
│   │   │   ├── FileUpload.tsx
│   │   │   ├── PdfReader.tsx
│   │   │   └── MediaReader.tsx
│   │   └── assets/       # 资源文件
│   └── package.json
├── data/                  # 数据目录
│   ├── archeaxis.sqlite  # 主数据库
│   └── uploads/          # 上传文件
└── tests/                 # 测试套件
```

## 配置说明

### 后端配置
文件: `config/default.yaml`

```yaml
database:
  path: data/archeaxis.sqlite

upload:
  directory: data/uploads
  max_size: 100MB

learning:
  fsrs:
    request_retention: 0.9
    maximum_interval: 36500
```

### 前端配置
文件: `frontend/vite.config.ts`

```typescript
export default defineConfig({
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://localhost:8000'
    }
  }
})
```

## 常见问题

### Q: 端口被占用
A: 修改配置文件中的端口号

### Q: 数据库连接失败
A: 确保 `data/` 目录存在且有写权限

### Q: 前端构建失败
A: 清理依赖并重新安装
```bash
rm -rf node_modules package-lock.json
npm install
```

## 测试

### 运行所有测试
```bash
pytest tests/ -v
```

### 运行前端测试
```bash
cd frontend
npm test
```

### 端到端测试
```bash
# 确保服务运行
pytest tests/test_e2e_workflows.py -v
```

## 生产部署

### Docker部署（推荐）

```dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY . .

RUN pip install -e .
RUN cd frontend && npm install && npm run build

EXPOSE 8000
CMD ["python", "-m", "app.runtime_entrypoint", "core"]
```

构建和运行:
```bash
docker build -t archeaxis-knowledge .
docker run -p 8000:8000 -v ./data:/app/data archeaxis-knowledge
```

### 系统服务部署

创建systemd服务: `/etc/systemd/system/archeaxis.service`

```ini
[Unit]
Description=ArcheAxis Knowledge OS
After=network.target

[Service]
Type=simple
User=archeaxis
WorkingDirectory=/opt/archeaxis
ExecStart=/opt/archeaxis/.venv/bin/python -m app.runtime_entrypoint core
Restart=always

[Install]
WantedBy=multi-user.target
```

启动服务:
```bash
sudo systemctl enable archeaxis
sudo systemctl start archeaxis
```

## 性能优化

### 数据库
- 定期运行 `VACUUM`
- 添加索引
- 定期备份

### 缓存
- 启用Redis缓存
- 配置CDN

### 监控
- 使用Prometheus监控
- 配置日志轮转

## 安全建议

1. **认证授权**: 添加用户认证系统
2. **HTTPS**: 使用SSL/TLS证书
3. **文件验证**: 严格验证上传文件
4. **API限流**: 防止滥用
5. **定期更新**: 保持依赖最新

## 备份策略

### 自动备份脚本
```bash
#!/bin/bash
DATE=$(date +%Y%m%d)
sqlite3 data/archeaxis.sqlite ".backup data/backup-$DATE.sqlite"
tar czf backup-$DATE.tar.gz data/
```

### 恢复
```bash
cp data/backup-20261017.sqlite data/archeaxis.sqlite
```

## 更新升级

```bash
git pull origin main
pip install -e . --upgrade
cd frontend && npm install && npm run build
```

## 支持

- 文档: [docs/](docs/)
- Issues: https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/issues
- API文档: [docs/API-DOCUMENTATION.md](docs/API-DOCUMENTATION.md)

---

更新时间: 2026-10-17
版本: 0.6.14
