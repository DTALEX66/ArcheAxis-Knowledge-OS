# CC File Tools → A 线 | 捕获系统

## 参考来源

| 文件 | 路径 |
|------|------|
| FileReadTool | src/tools/FileReadTool/ |
| FileEditTool | src/tools/FileEditTool/ |
| FileWriteTool | src/tools/FileWriteTool/ |

## 关键模式

1. **分块读取** — 大文件自动分块，避免 OOM
2. **编码检测** — 自动识别文件编码（UTF-8/GBK/等）
3. **增量处理** — 只读变更部分，不重复全部

## A 线迁移

文档导入模块可以借鉴 FileReadTool 的分块+编码检测策略
