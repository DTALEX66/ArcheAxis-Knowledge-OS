# 022 Windows Desktop Shell

## 目标

为元枢系统提供专用 Windows 桌面入口。普通用户不需要运行 Python 命令、选择端口或打开浏览器；FastAPI 仍是 Workspace 页面与产品 API 的唯一来源。

## 生命周期

```text
Tauri
→ 解析开发或安装版 Python Runtime
→ 在可写数据目录执行 migration
→ 启动 owned Core（随机 127.0.0.1 端口）
→ 使用每次启动随机令牌验证产品身份
→ readiness 成功后创建元枢·观心窗口
→ 窗口关闭时通过 stdin 请求优雅退出
→ 超时或壳异常退出时由 Windows Job Object 清理进程树
```

开发模式只使用仓库 `.venv/Scripts/python.exe`。安装模式只使用应用资源目录内的 `runtime/python/python.exe` 并启用 `-B -I`，既隔离用户环境也禁止向安装资源写入字节码；缺失捆绑 Runtime 时 fail closed，不回退到 PATH 或系统 Python。

## 安全边界

- Core 只绑定本次启动的 `127.0.0.1` 随机端口。
- readiness 令牌不进入 URL、不回显，并使用常量时间比较。
- WebView 只允许本次端口的 `/workspace` 路径；拒绝公网、`localhost`、其他 loopback 表达、`file:`、`data:`、`blob:`、新窗口和下载。
- 桌面壳不启用 shell、opener 或 HTTP 插件，也不向 Workspace 页面暴露 Tauri IPC 能力。
- 壳只停止自己拥有的 Core，不接管外部服务。

## 打包边界

`desktop/scripts/prepare_bundle.py` 从锁文件准备项目忽略区内的 Windows Python Runtime，安装当前 wheel，并在隔离模式下验证导入。Tauri 将该 Runtime 作为只读资源打入 current-user NSIS 安装包；运行时数据库、日志和 WebView 数据留在应用本地数据目录，不进入 Git。

Windows CI 在生成 NSIS 后必须真实执行安装、启动、Workspace HTTP、正常关闭、强制终止进程树、字节码零增长和卸载零残留验证；仅检查 EXE 文件存在不能作为安装闭环证据。

当前源码 Release Manifest 仍保持 `unreleased`、`public=false`；这不否定已独立验证的公开 `v0.5.0` artifact identity、资产 checksum 与 installer lifecycle。当前没有签名发布声明；后续未签名构建仍不能自动作为新的公开发行证据。
