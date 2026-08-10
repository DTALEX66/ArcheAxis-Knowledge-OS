# 前端技术实施方案

## 当前约束

当前 Workspace 使用：

- `index.html`
- `styles.css`
- `app.js`
- FastAPI 静态资源；
- Tauri 打开本地 `/workspace`；
- CSP 为 self-only；
- Wheel 明确检查 UI 资源。

## 推荐路线

### A0–A1：保留当前静态栈

原因：

- 风险低；
- 不影响 Wheel；
- 不增加 Node Runtime；
- 可先验证信息架构；
- 保留真实 closed-loop。

工作：

- 格式化并模块化组织单文件；
- 设计 tokens；
- App Shell；
- 苹果式主题；
- 页面路由映射；
- Inspector；
- 状态栏；
- 浏览器回归。

### A2：拆分静态模块

如资源路由允许，拆分：

```text
ui/
  index.html
  assets/
    app.js
    styles.css
    modules/
      shell.js
      api.js
      validators.js
      pages/
```

需要同步修改：

- package-data；
- asset route；
- Wheel member test；
- CSP；
- browser smoke。

### A3 以后：评估 React + TypeScript

只有以下条件满足时迁移：

- A1/A2 行为 parity；
- Wheel/Tauri build strategy 明确；
- 静态产物完全 self-contained；
- 无 CDN；
- Browser smoke 覆盖；
- 迁移有独立 TaskPack。

禁止在 UI 换皮 TaskPack 中同时做框架迁移。

## CSS 架构

```text
tokens
reset
shell
layout
components
pages
states
responsive
reduced-motion
print/export
```

## JS 架构

```text
state
routing
api
validators
renderers
actions
accessibility
polling
bootstrap
```

## 性能预算

- 首屏 HTML/CSS/JS gzip 尽量 < 350KB（不含图片）；
- 无外部网络请求；
- DOM 列表使用分页/虚拟化阈值；
- Canvas 大于 500 节点需要性能方案；
- Polling 页面不可全局 3 秒刷新所有 API；
- 页面不可见时停止高频刷新。
