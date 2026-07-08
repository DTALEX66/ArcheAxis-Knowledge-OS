# CC MCP 集成 → B 线 | 外部工具扩展

## 参考来源

src/services/mcp/（4 种传输方式）

## 传输方式

1. StdioClientTransport — 子进程通信（最常用）
2. SSEClientTransport — Server-Sent Events
3. StreamableHTTPClientTransport — 流式 HTTP
4. WebSocketTransport — WebSocket

## B 线迁移

Agent 可通过 MCP 接入外部工具：
- 搜索工具 → web_search MCP
- 翻译工具 → translate MCP
- 代码分析 → lsp MCP
- 文档抓取 → fetch MCP


---

## A-Line 对齐

本组件为 B-Line 的一部分，与 A-Line (Human Learning OS) 的对接关系：
通过MCP协议扩展A线系统的工具能力

> 详细双线集成方案见 `/dual-system-integration/`
