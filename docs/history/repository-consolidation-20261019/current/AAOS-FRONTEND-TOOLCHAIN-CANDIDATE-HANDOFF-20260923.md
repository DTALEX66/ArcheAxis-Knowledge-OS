# AAOS 前端工具链与 Candidate 交接记录（2026-09-23）

## 结论

AAOS 前端已使用共享外置工具链完成当前 HEAD 的 Release self-contained `win-x64` Candidate 构建。Candidate 只落在项目 `.project-local` 隔离目录，**没有覆盖** `D:\All projects\ArcheAxis.Knowledge.Green-x64`，没有修改 Green 用户数据，没有发布 GitHub Release。

状态：`CANDIDATE_BUILT / GREEN_NOT_REPLACED / GUI_UNVERIFIED`

## 权威路径

- 项目源码：`D:\All projects\ArcheAxis-Knowledge-OS`
- 共享工具链根：`D:\All projects\OS External Configuration`
- .NET SDK：`D:\All projects\OS External Configuration\10-toolchains\dotnet\dotnet.exe`
- NuGet/Avalonia 缓存：`D:\All projects\OS External Configuration\60-cache\nuget`
- Green 真实运行目录（本次未写入）：`D:\All projects\ArcheAxis.Knowledge.Green-x64`
- Candidate：`D:\All projects\ArcheAxis-Knowledge-OS\.project-local\build\green-candidates\ArcheAxis.Knowledge.Green-v1ae2955974fb-x64`

路径职责以 `docs/SHARED_RESOURCE_PATH_INDEX.md` 为唯一索引；本交接不创建第二套资源根定义。

## 构建与验证读回

| 项目 | 结果 |
| --- | --- |
| Source commit | `1ae2955974fb30e4d38fd933e07ccc8cef7d609d` |
| SDK | `.NET SDK 10.0.400` / Host `10.0.11` |
| Target | `net10.0`, `Release`, `win-x64`, `SelfContained=true` |
| Avalonia | `12.1.2` |
| Candidate files | `225` |
| Candidate bytes | `216,489,411` |
| `ArcheAxis.Desktop.exe` SHA-256 | `D4A5C280E3E8113A9CE5633D8B5EC421666E8100F97FA5CE33245EE2082864C1` |
| Static desktop contracts | `201 passed` |
| XAML XML parse | `MainWindow.axaml` / `AaosTheme.axaml` passed |
| Diff check | `git diff --check` passed |

## 本次源码修复

Avalonia 12 编译器拒绝 Hero 区域三处 `Panel.ZIndex` 字符串附加写法。已改为同一控件上可编译的 `ZIndex` 属性，并加入静态回归断言。修改文件：

- `apps/ArcheAxis.Desktop/MainWindow.axaml`
- `tests/test_desktop_navigation_contract.py`

## 未完成门禁

- 当前 CUA 没有可接管的原生 Avalonia 窗口；真实截图、点击、焦点、无障碍树、DPI、冷启动仍未验证。
- Candidate 尚未完成 Local Green staging 的真实 first-use、restart/readback、migration/rollback。
- 不能据此执行 Green 原位替换；仍需按 R6/P6 完成 hash-addressed backup、Owner Gate 和回滚验证。
- 不创建 tag、Release、公开资产或新产品版本号。

## 后续执行顺序

```text
Candidate
→ 原生 GUI staging 验证
→ first-use / restart / readback
→ 现有 Green Runtime hash-addressed backup
→ Owner Gate
→ 只替换 Runtime，不动 data/资料库
→ 启动脚本 readback
→ failure/recovery/rollback
→ LOCAL_GREEN_READY_FOR_OWNER_REVIEW 或 NOT_READY
```

证据等级：`TESTED_LOCAL_BUILD / TESTED_LOCAL_STATIC / GUI_UNVERIFIED / GREEN_NOT_REPLACED`。
