# AAOS 支持的文件格式

## 文档格式

### ✅ 已支持
- **PDF** - 完整支持（PDF.js渲染器）
- **文本文件** (.txt, .md) - 完整支持
- **Markdown** - 完整支持
- **EPUB** - 完整支持（EpubParagraphs组件）

### 实现位置
- PDF渲染: `frontend/src/components/PdfReader.tsx`
- EPUB解析: `frontend/src/components/EpubParagraphs.tsx`
- 文本处理: `frontend/src/components/OriginalTextCitation.tsx`

## 媒体格式

### ✅ 已支持
- **音频** - audio/* (MP3, WAV, OGG等)
- **视频** - video/* (MP4, WebM等)
- **图片** - image/* (PNG, JPG, GIF, WebP等)

### 实现位置
- 媒体播放器: `frontend/src/components/MediaReader.tsx`
- 转写支持: `frontend/src/components/TranscriptionCues.tsx`

## 数据格式

### ✅ 已支持
- **JSON** - 完整支持
- **YAML** - 配置文件
- **CSV** - 待实现

## 代码格式

### ✅ 已支持
- **TypeScript/JavaScript** - 完整支持
- **Python** - 完整支持
- **Rust** - 完整支持
- **Markdown代码块** - 完整支持

## 导出格式

### ✅ 已支持
- **Markdown** - `document_export` API
- **Obsidian包** - `document_export` API

### 实现位置
- 导出功能: `frontend/src/spaces/CanonicalLibrarySpace.tsx` (第566-577行)

## 特殊格式处理

### 内容检测
- 二进制文件检测: `frontend/src/components/ContentDetectionPanel.tsx`
- 容器成员链: `frontend/src/components/ContainerMemberChain.tsx`

### PDF特殊处理
- 页面识别: `frontend/src/components/PdfPageRecognition.tsx`
- PDF Worker: `pdfjs-dist` 版本 6.4.299

## 格式能力矩阵

| 格式类型 | 导入 | 渲染 | 引用 | 导出 | 转换 |
|---------|------|------|------|------|------|
| PDF     | ✅   | ✅   | ✅   | ❌   | ✅   |
| 文本    | ✅   | ✅   | ✅   | ✅   | ✅   |
| Markdown| ✅   | ✅   | ✅   | ✅   | ✅   |
| EPUB    | ✅   | ✅   | ✅   | ❌   | ✅   |
| 音频    | ✅   | ✅   | ✅   | ❌   | ✅   |
| 视频    | ✅   | ✅   | ✅   | ❌   | ✅   |
| 图片    | ✅   | ✅   | ❌   | ❌   | ❌   |

## 技术栈

### 前端
- PDF.js 6.4.299
- Tiptap 3.31.4 (文档编辑器)
- 原生 HTML5 Audio/Video API

### 后端
- Rust Core (文件处理)
- Python (转换任务)

## 扩展计划

### 短期 (P1)
- [ ] CSV导入/导出
- [ ] Excel支持
- [ ] Word文档支持

### 中期 (P2)
- [ ] PowerPoint支持
- [ ] 压缩包处理
- [ ] 更多视频编解码器

### 长期 (P3)
- [ ] CAD文件查看
- [ ] 3D模型查看
- [ ] 实时协作编辑

## 参考文档

- API合约: `shared-contracts/`
- 核心处理: `crates/archeaxis-core/`
- 前端组件: `frontend/src/components/`
