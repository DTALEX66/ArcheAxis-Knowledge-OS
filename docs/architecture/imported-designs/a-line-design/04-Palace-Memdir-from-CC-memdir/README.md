# CC memdir 系统 → A 线 | 知识宫殿系统

## 文件全景（8 文件，1,635 行）

| 文件 | 行数 | 职责 |
|------|------|------|
| memdir.ts | 471 | 核心：记忆目录管理、条目截断、prompt 构建 |
| paths.ts | 265 | 路径管理：自动记忆路径、每日日志路径 |
| memoryTypes.ts | 260 | 记忆类型定义、分类体系 |
| teamMemPaths.ts | 280 | 团队记忆路径、路径遍历防护 |
| findRelevantMemories.ts | 128 | 语义相关性检索 |
| memoryScan.ts | 87 | 扫描记忆文件、生成清单 |
| teamMemPrompts.ts | 96 | 团队记忆 prompt |
| memoryAge.ts | 48 | 记忆时效计算 |

## 核心架构

### 记忆目录层次

```text
memoryBaseDir/
├── MEMORY.md              ← 入口点（前 200 行/25KB 截断）
├── daily/                 ← 每日自动记录
│   └── 2026-06-25.md
├── projects/             ← 项目记忆
├── concepts/             ← 概念记忆
├── people/               ← 人物记忆（团队）
└── ...                   ← 其他类型目录
```

### 记忆类型体系（memoryTypes.ts）

```typescript
MEMORY_TYPES = [
  "project",       // 项目上下文
  "concept",       // 关键概念
  "preference",    // 用户偏好
  "decision",      // 决策记录
  "pattern",       // 代码/设计模式
  "person",        // 人物信息
  "resource",      // 外部资源引用
  "lesson",        // 经验教训
  "goal",          // 目标与进展
]
```

### 记忆生命周期

```text
写入（自动/手动）
  ↓
存储 → 文件系统（Markdown 文件）
  ↓
老化 → memoryAge.ts 计算时效（天/周/月）
  ↓
检索 → findRelevantMemories.ts 语义搜索
  ↓
加载 → loadMemoryPrompt() → 构建 prompt 上下文
```

### 关键机制

#### 1. 入口点截断（memdir.ts）
```typescript
MAX_ENTRYPOINT_LINES = 200
MAX_ENTRYPOINT_BYTES = 25_000
truncateEntrypointContent(raw) → 前 N 行/字节
```

#### 2. 记忆时效（memoryAge.ts）
```typescript
memoryAgeDays(mtimeMs) → 天数
memoryFreshnessText(mtimeMs) → "刚刚" / "1小时前" / "3天前"
memoryFreshnessNote(mtimeMs) → 新鲜度提示
```

#### 3. 自动记忆路径（paths.ts）
```typescript
getAutoMemPath() → 自动记忆目录
getAutoMemDailyLogPath(date) → 每日日志路径
isAutoMemoryEnabled() → 是否启用自动记忆
```

#### 4. 记忆扫描（memoryScan.ts）
```typescript
scanMemoryFiles(memoryDir) → MemoryHeader[]  // 扫描所有记忆文件
formatMemoryManifest(memories) → string       // 生成清单
```

## → A 线迁移映射

| A 线子系统 | CC 映射 | 迁移方式 |
|-----------|---------|---------|
| 7. 知识宫殿 | memdir.ts 目录层次 | 学科→章节→知识点三层目录结构 |
| 7. 知识宫殿 | memoryTypes.ts 分类 | 9 种记忆类型 → 知识分类标签 |
| 7. 知识宫殿 | paths.ts 路径管理 | 知识路径生成 + 每日学习日志 |
| 7. 知识宫殿 | memoryAge.ts 时效 | 知识点掌握度时效评估（结合 FSRS） |
| 7. 知识宫殿 | memoryScan.ts | 构建知识点索引清单 |

### 宫殿目录设计（参考 memdir）

```text
knowledgeBaseDir/
├── INDEX.md              ← 知识索引入口（类比 MEMORY.md）
├── daily/               ← 每日学习记录
│   └── 2026-06-25.md
├── subjects/            ← 学科目录
│   ├── programming/
│   │   ├── python/
│   │   └── rust/
│   ├── math/
│   └── ai/
├── concepts/            ← 跨学科概念
├── projects/            ← 项目知识
└── archive/             ← 归档
```
