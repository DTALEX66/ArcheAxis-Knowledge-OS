# 验收矩阵

## 视觉与结构

- [ ] 默认主题是 Violet Core。
- [ ] 旧 localStorage 主题不会导致白屏。
- [ ] 一级 Rail 存在。
- [ ] 二级导航随模块变化。
- [ ] 当前页面和模块高亮一致。
- [ ] 右侧 Inspector 可折叠。
- [ ] 底部活动坞可折叠。
- [ ] 960×640 可操作。
- [ ] 390×844 无横向溢出。
- [ ] Reduced Motion 生效。
- [ ] 长文区域没有持续发光干扰。

## 产品真相

- [ ] 所有数字来自真实 API。
- [ ] 无假 Agent。
- [ ] 无假模型。
- [ ] 无假 Token/成本。
- [ ] 无假进度。
- [ ] Planned 页面无可执行假按钮。
- [ ] 未实现能力显示明确边界。

## 功能回归

- [ ] Status。
- [ ] Diagnostics。
- [ ] URL intake。
- [ ] GitHub intake。
- [ ] File upload。
- [ ] Oversize/invalid fail closed。
- [ ] Research refresh。
- [ ] Research approve。
- [ ] Knowledge refresh。
- [ ] Start learning。
- [ ] Practice。
- [ ] Evolution。
- [ ] Runtime candidate approve。
- [ ] Jobs。
- [ ] Delivery dispatch。
- [ ] Delivery retry。
- [ ] Lifecycle。

## 隐私与安全

- [ ] 页面不出现 package_id。
- [ ] 页面不出现 job_id。
- [ ] 页面不出现 command_id。
- [ ] 页面不出现 event_id。
- [ ] 页面不出现数据库路径。
- [ ] 页面不出现本地绝对路径。
- [ ] Workspace 仍只允许 Loopback。
- [ ] Same-origin 保留。
- [ ] CSP 保留。
- [ ] 外部导航仍被 Tauri 拒绝。
- [ ] 新窗口和下载仍被拒绝。

## 浏览器闭环

- [ ] 真实文件上传。
- [ ] SQLite Job/Outbox。
- [ ] UI 显示 pending。
- [ ] Dispatch。
- [ ] Receipt recorded。
- [ ] Reload 后回读一致。
- [ ] Console error 为零。
- [ ] Page error 为零。

## 打包

- [ ] Wheel 包含 index/styles/app。
- [ ] 仓库外安装可加载 Workspace。
- [ ] Windows Runtime smoke。
- [ ] Tauri build。
- [ ] NSIS install/start/uninstall。
