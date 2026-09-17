# 当前桌面开发入口

这是项目开发入口，使用现有Debug构建和项目解释器，不是安装器。默认只准备配置，不弹出窗口、
不启动Core、也不创建数据库。不会选择既有Green或真实资料库。

在仓库根的PowerShell执行：

```powershell
.\.project-local\build\venv\Scripts\python.exe scripts/runtime/dev.py -- .\.project-local\build\venv\Scripts\python.exe scripts/launch/desktop_launch.py
```

输出 `desktop-launch.json` 和 `worker-profile.json` 位于本次run的artifacts/desktop-launch唯一子目录。
前者记录所用桌面/Core路径、工作目录及三个启动环境变量，不含身份秘密。
需要交互式打开时，在同一命令末尾加 `--launch`；关闭窗口后启动命令结束。
默认复用当前 worktree 的 `.project-local/state/<worktree-id>/desktop-test/workspace.sqlite`，
退出后再次启动沿用同一 TEST 库；显式加 `--fresh-workspace` 才使用新的隔离测试库。
运行收据及 worker staging 仍每次隔离。准备操作不创建数据库；该入口不绑定 GREEN/STABLE 或真实四库，
也不代表已完成用户库的迁移、升级和恢复验收。

需要的既有文件：dev.py解析的worktree build下
`dotnet/ArcheAxis.Desktop/bin/Debug/net10.0/ArcheAxis.Desktop.exe`、
同一worktree build下的 `cargo/debug/archeaxis-api.exe`、
`services/python-workers/transport/text_ndjson.py` 以及当前实际Python解释器。
缺失时具名拒绝，不自动build/install/download。`--desktop`/`--core`只接受项目开发root的build/runs/dist文件，
不能通过该入口覆盖已有软件。
本轮验证使用了既有 `.project-local/build/cargo/debug/archeaxis-api.exe` 构建目录，因此复用这份
已测二进制时在命令末尾加 `--core .project-local/build/cargo/debug/archeaxis-api.exe`；
标准dev.py构建写入worktree build，默认入口与之匹配，不用复制或重复构建二进制。

## 桌面侧加载规则

`WorkerProfile.Load`默认读取应用旁 `worker-profile.json`；环境变量`ARCHAXIS_WORKER_PROFILE`显式指定时优先。
格式只有四个字符串字段：`schema=archeaxis.worker-profile/v1`、`python`、`script`、`staging`。
相对路径从配置文件目录解析；未知/重复/缺失字段、未知schema、超过16KiB、父目录跳转、
E/UNC/代理私有目录及链接路径拒绝。解释器和脚本必须存在；解析配置不会创建staging。
Core仍独立检查传入路径，不能以桌面验证代替Core边界。

应用旁默认配置缺失时，只连接Core并显示“文本处理组件未配置”；显式配置缺失或内容无效则停止启动。
完整配置经MainWindow传给CoreSupervisor，启用Core既有的worker执行路径；不直接写数据库。
三个启动变量沿用宿主的`ARCHAXIS_`拼写：CORE_BIN、VNEXT_DB、WORKER_PROFILE。
开发生成器集中设置它们，不修改全局环境或legacy YAML配置。

## 已验证和未验证

`r5-worker-profile-final`：同一加载器的相对路径/协议/字段/缺失/真实Windows junction拒绝，
随后真实C#→双身份Core→Python→持久输出通过。
`r5-desktop-profile-build`：正式Avalonia工程无网络构建成功，0 warning/0 error。
`r5-desktop-launch-prepare`：真实既有二进制准备成功，状态PREPARED_NOT_LAUNCHED；未打开可见窗口。

当前窗口主体已替换为星环工作台壳层：包含工作区导航、资料选择、Core导入提交和学习入口状态反馈；
资料导入通过已认证的`POST /api/v1/imports`提交，仍不代表转换质量或学习队列已完成。DeepTutor Web宿主、
完整学习交互、跨进程机器adapter、安装签名与独立完整审计仍未完成。当前环境尚未重新编译或打开可见
Windows窗口，上述构建/配置/链路结果不能升级为完整Windows前端验收通过。
