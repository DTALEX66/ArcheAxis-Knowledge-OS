# 开发启动与命令

平台：Windows（也在 Linux CI 上跑门禁）。所有命令需在仓库根执行。

## 1. 前置：找到可用的 Node

PATH 里**没有** `node`/`npm`（Git Bash 下 `which node` 失败是正常现象，不代表未安装）。本轮实测绑定：

```bash
# Git Bash 下 $HOME 即用户目录；不要在本仓库文档里写死含用户名的绝对路径。
export N26="$HOME/AppData/Local/hermes/tools/node-26.7.0-win32-x64"
export PATH="$N26:$PATH"
export npm_config_cache="D:/All projects/ASTRYN/.project-local/runs/cache/npm"   # 缓存留在项目内
NM="$N26/node_modules/npm/bin/npm-cli.js"
node -v                                            # v26.7.0
"$N26/node.exe" "$NM" -v                           # 11.19.0
```

若该路径不存在，改用 `%LOCALAPPDATA%\OpenHuman\node-runtime\node-v22.11.0-win-x64`（Node 22.11.0 + npm 10.9.0）；Vite 5 支持 `>=18`，但 `package.json` 的 `engines` 写的是 `>=20.19.0`，Node 22.11.0 满足。**注意**：只有 v26.7.0 经过本轮全部门禁实测，v22.11.0 对本项目的兼容性为 UNVERIFIED。

npm 必须以 `node <npm-cli.js>` 形式调用并把 node 目录前置到 PATH，否则包内 `install.js` 会因找不到 `node` 而失败。

## 2. 安装

```bash
"$N26/node.exe" "$NM" ci        # 按 lockfile 精确安装 320 个包
```

## 3. 命令表（全部来自 `package.json`，均已实际执行）

| 命令 | 作用 | 本轮实测 |
| --- | --- | --- |
| `npm run dev` | 启动开发宿主，`http://127.0.0.1:5183/`（仅 loopback，`strictPort`） | PASS |
| `npm run dev:proxy` | 启动仅开发环境的模型代理（`127.0.0.1:8791`） | 见 §5 |
| `npm run lint` | ESLint 9 扁平配置 | PASS，exit 0 |
| `npm run typecheck` | `tsc --noEmit`（strict + exactOptionalPropertyTypes + noUncheckedIndexedAccess） | PASS，exit 0 |
| `npm run test` | Vitest 单次运行 | PASS，118 tests / 14 files，exit 0 |
| `npm run build` | typecheck + `vite build`，产物落 `.project-local/artifacts/dev-host-dist` | PASS，exit 0 |
| `npm run verify` | lint → typecheck → test → build 串行 | 见 `docs/verification/M0-VALIDATION.md` |
| `npm run record-gates` | 生成门禁回执 `docs/verification/gates.json`（源码树内容哈希 + 各阶段退出码 + 工具链绑定） | PASS，exit 0 |

## 4. 配置

复制 `.env.example` 为 `.env`（已被 `.gitignore` 排除）。前端可见变量只有 `VITE_` 前缀的四个，且**都不含密钥**：

| 变量 | 含义 |
| --- | --- |
| `VITE_ASTRYN_AAOS_BASE_URL` | AAOS Core loopback 地址；留空即"宿主不可连接"，星栖不猜测现场 |
| `VITE_ASTRYN_DEV_PROXY_ENABLED` | 置 1 表示开发代理已配置上游 |
| `VITE_ASTRYN_DEV_MODEL` | 模型标识（非密钥） |
| `VITE_ASTRYN_ALLOW_SYNTHETIC` | 置 1 才允许明确标注 SYNTHETIC 的合成回复；默认关闭 |
| `VITE_ASTRYN_SYNTHETIC_HOST` | 置 1 启用合成宿主模拟器（演示审批/执行/完成链路） |

## 5. 真实模型接入（本轮未执行）

密钥只进入代理进程环境，不进浏览器包、不进日志、不进 Git：

```bash
export ASTRYN_DEV_MODEL_BASE_URL=https://api.<provider>/v1
export ASTRYN_DEV_MODEL_API_KEY=...        # 由你提供，本仓库不代为获取
export ASTRYN_DEV_MODEL=<model-id>
export VITE_ASTRYN_DEV_PROXY_ENABLED=1
export VITE_ASTRYN_DEV_MODEL=<model-id>
npm run dev:proxy &        # 另一个进程
npm run dev
```

代理约束：只绑 `127.0.0.1`；只转发到配置的单一上游（非开放代理）；请求体上限 64 KB；上游超时默认 30 s；不回传上游正文；未配置时返回 503 `MODEL_UNAVAILABLE`。

本轮**没有**任何获准的模型凭据，因此真实模型验收（A05）保持 `NOT_TESTED`。

## 6. 目录职责

见 `docs/development/REPOSITORY-LAYOUT.md`。补充实现落位：`contracts/` 是纯类型与运行时校验（不依赖 React）；`src/` 按 companion / interaction / adapters / memory / context / avatar / presentation 分层；`dev-host/` 是开发宿主（含 `server/dev-model-proxy.mjs`）；`tests/` 全部夹具显式标注 SYNTHETIC；本地日志与产物在 `.project-local/`，不提交。
