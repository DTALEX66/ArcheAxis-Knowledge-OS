# 依赖与许可证登记

生成方式：从 `package-lock.json`（lockfileVersion 3）程序化读取，非手工誊写。核验日期：2026-10-13。
绑定运行时：Node `v26.7.0` + npm `11.19.0`（`%LOCALAPPDATA%\hermes\tools\node-26.7.0-win32-x64`），npm 缓存限定在 `.project-local/runs/cache/npm`，未触碰全局配置。

## 1. 版本收敛依据

版本不是自选，而是**对齐 AAOS 现行前端**（P1 要求星栖作为 AAOS 的 React 原生组件挂载；React 19 组件树无法挂进 React 18 宿主）。AAOS `frontend/package.json` 实测：`react ^18.3.1`、`typescript ^5.5.4`、`vite ^5.4.11`、`vitest ^2.1.9`、`@vitejs/plugin-react ^4.3.4`、`@testing-library/react ^16.1.0`、`jsdom ^25.0.1`、Tauri CLI `^2.11.4`。

唯一超出 AAOS 的新增：`eslint ^9` + `typescript-eslint ^8`（AAOS 前端 devDependencies 中无 ESLint）。理由：T03 要求 lint 门禁。这是**有意的偏离**，记录为决策 D005。

## 2. 直接依赖（14 个，含 lockfile 解析出的精确版本）

| 包 | 声明范围 | 锁定版本 | 许可 | 作用域 |
| --- | --- | --- | --- | --- |
| `react` | ^18.3.1 | 18.3.1 | MIT | runtime |
| `react-dom` | ^18.3.1 | 18.3.1 | MIT | runtime |
| `@testing-library/dom` | ^10.4.0 | 10.4.2 | MIT | dev |
| `@testing-library/react` | ^16.1.0 | 16.3.3 | MIT | dev |
| `@types/node` | ^22.10.0 | 22.20.5 | MIT | dev |
| `@types/react` | ^18.3.12 | 18.3.31 | MIT | dev |
| `@types/react-dom` | ^18.3.1 | 18.3.7 | MIT | dev |
| `@vitejs/plugin-react` | ^4.3.4 | 4.7.0 | MIT | dev |
| `eslint` | ^9.17.0 | 9.39.4 | MIT | dev |
| `jsdom` | ^25.0.1 | 25.0.1 | MIT | dev |
| `typescript` | ^5.5.4 | 5.9.3 | Apache-2.0 | dev |
| `typescript-eslint` | ^8.18.0 | 8.71.1 | MIT | dev |
| `vite` | ^5.4.11 | 5.4.21 | MIT | dev |
| `vitest` | ^2.1.9 | 2.1.9 | MIT | dev |

运行时依赖只有 `react` 与 `react-dom` 两个：M0 未引入 Tauri、Rust、Python、状态管理库、UI 组件库、路由、请求库或任何数字人框架。

## 3. 传递依赖许可总账

lockfile 共 **320** 个包条目，许可分布：

```
MIT=273  Apache-2.0=18  ISC=14  BSD-2-Clause=8  BSD-3-Clause=3
MIT-0=1  BlueOak-1.0.0=1  Python-2.0=1  CC-BY-4.0=1
```

非 MIT/ISC/BSD 的四项逐个点名（不放过任何一个）：

| 包 | 版本 | 许可 | 判定 |
| --- | --- | --- | --- |
| `typescript` | 5.9.3 | Apache-2.0 | 可商用，需保留声明 |
| `@csstools/color-helpers` | 5.1.0 | MIT-0 | MIT 的免署名变体，无义务 |
| `minimatch`（typescript-eslint 嵌套） | 10.2.6 | BlueOak-1.0.0 | ISC 风格，宽松 |
| `argparse` | 2.0.1 | Python-2.0 | PSF 系许可，宽松 |
| `caniuse-lite` | 1.0.30001815 | **CC-BY-4.0** | 唯一带署名义务的包。它是 Browserslist 的浏览器兼容性**数据集**（非代码复用），构建期使用、不进产物。若日后要消除该义务，方案是换用 `browserslist --ignore-config` 或在发行版剥离该数据；本轮记录为已知项 |

结论：无 GPL/AGPL/LGPL 传染成分，无 NC 素材，无模型权重，无二进制素材。`assets/third-party/` 仅有 `.gitkeep`，由 `tests/boundary/no-sensitive-apis.test.ts` 强制。

## 4. 安装与回退

```bash
npm ci            # 严格按 lockfile 安装（320 包）
npm install       # 仅用于有意升级依赖范围时
```

回退方案：删除 `node_modules/` 后重新 `npm ci`；本项目不写全局、不装全局包、不改 PATH。`package-lock.json` 是唯一 lockfile，禁止混用 pnpm/yarn 锁文件。

## 5. 未引入但已评估的候选

`@met4citizen/talkinghead`（MIT，但要求 GLB+Mixamo 骨骼且无中文口型）、`three`、`@pixi/*`、Live2D Web SDK、`@ricky0123/vad-web`、sherpa-onnx/Piper 系。取舍依据见 `docs/research/OPEN-SOURCE-MATRIX.md`。渲染路线为"位图默认 + 原创 SVG 回退下限"（N1，2026-10-14 起默认 `xiaoqi-raster-v2`，位图由外部 AI 生产并按 `STATE-ASSET-INDEX.json` 登记），因此这些骨骼/口型/3D 库仍不在关键路径上；引入时机与授权归属由 P2 单独决策。
