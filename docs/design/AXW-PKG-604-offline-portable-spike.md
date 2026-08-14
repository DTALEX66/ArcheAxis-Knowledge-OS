# AXW-PKG-604 — 完整离线便携版 Spike（Fixed WebView2）

> 状态：Spike 完成（2026-08-15）。任务包 §7.1：可选产物，**不是默认**。
> 关联：`scripts/webview2_detect.py`（本机检测工具，真实运行输出见下）。

## 1. 本机实测（scripts/webview2_detect.py，2026-08-15）

```json
{
  "evergreen": null,
  "fixed_version": "151.0.4129.78",
  "fixed_version_size_mb": 849,
  "offline_installer_present": false,
  "recommendation": "fixed-version-only (151.0.4129.78, ~849 MB): offline portable must bundle Fixed Version (~250 MB)"
}
```

- 本机无 Evergreen 注册项（HKLM/HKCU EdgeUpdate Clients 均无 pv）；
- 本机以 Fixed Version 形式存在（Program Files (x86)\\Microsoft\\EdgeWebView\\Application\\151.0.4129.78，**~849 MB**）；
- 无离线 bootstrap 安装器（MicrosoftEdgeWebview2Setup.exe）。

## 2. 结论与决策（Spike）

| 维度 | 数据/决策 |
|---|---|
| 官方体积声明 | 固定版 WebView2 增加 ~250 MB 以上（Microsoft 文档）；**本机实测现代版本 151.x 为 ~849 MB** |
| 默认策略 | Evergreen 优先（安全更新自动、体积小）——任务包 §7.1 与 Microsoft Best Practices 一致 |
| 缺失处理 | Green/Portable 默认提供 `MicrosoftEdgeWebview2Setup.exe` 离线安装入口（bootstrap，Evergreen 模式）；不捆绑 Fixed Version |
| 离线便携版 | 可选产物 `ArcheAxis.Knowledge.Portable-Offline-x64.zip`：额外含 Fixed Version WebView2 + 基础 OCR/媒体能力包；仅断网/受控环境 |
| CVE/更新责任 | Fixed Version 由应用负责更新（微软不自动推送安全更新）——离线包需在 Release 说明标注版本与更新责任 |
| 组装影响 | assemble_distributions.py 增加 `--offline` 开关（把 webview2 fixed runtime 目录复制进 portable/app/webview2-fixed + 写 portable-profile.toml 的 webview2_mode: fixed）——**不在默认组装链** |

## 3. 未做（等待 RC/用户决策）

- 实际捆绑 Fixed Version 下载与打包（~850 MB 资产，需用户明确授权下载——本机已有 151.0.4129.78 可作源）；
- 离线包的 Release 资产接入（release.yml 保持默认 6 资产 + Developer Kit；offline 作为可选 tag 触发）。

## 4. 回滚方法

- 不产生任何默认链改动；offline 组装开关未接入 release.yml，无需回滚。
