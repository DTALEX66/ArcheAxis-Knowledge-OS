# 在 Windows 独立后端启用本地结构化回答

本补充包适用于星环知识系统 0.1.00 的 Windows x64 独立后端，以及同版安装器所带的后端目录。它让本次后端进程通过 LM Studio 的 SDK 调用本机 Qwen 模型，并为最终回答预留生成空间。

## 第一次启动

1. 将本 ZIP 完整解压到一个新目录。准备好同一下载页的独立后端 ZIP 并解压，或使用已安装的 0.1.00 后端。
2. 启动本机 LM Studio，在开发者页面启动端口 1234 的本地服务器。准备好模型 `qwen3.5-4b` 及其推理运行时。断网使用前，先在这台电脑上备齐两者。[LM Studio 离线说明](https://lmstudio.ai/docs/app/offline)
3. 在 LM Studio 终端运行 `lms ps` 查看已加载模型。如果已有 `aaos-fast-4b` 实例，沿用它。如果本机已备好权重且有可用资源，运行下方命令加载。模型键可用 `lms ls` 核对。[LM Studio 加载说明](https://lmstudio.ai/docs/cli/local-models/load)

   ```powershell
   lms load qwen3.5-4b --identifier aaos-fast-4b --context-length 4096 --parallel 1 --ttl 1800
   ```

4. 双击 `start-fast-local.cmd`。如果补充目录与名为 `backend` 的目录并列，会自动找到后端。放在其他位置时，选择原后端目录中的 `start-backend.cmd`。也可以把该文件拖到补充包启动器上。

窗口会显示本次的本机地址、工作区路径和所选 profile。默认工作区保存在 `%LOCALAPPDATA%\ArcheAxis Knowledge\Fast Local\data`。按 Ctrl+C 关闭本次后端。桌面应用从原快捷方式启动时使用它自己的后端配置。

## 指定工作区或检查启动

第二个参数可指定有写权限的工作区目录。下面的目录是示例，请换成本机路径。已有工作区一次只交给一个后端进程。

```powershell
.\start-fast-local.cmd "D:\AAOS\backend" "D:\AAOS\我的工作区"
.\start-fast-local.cmd "D:\AAOS\backend" "D:\AAOS\启动检查" --smoke
```

启动检查会读回 Core 版本、工作区信息及 `machine.answer` 握手状态，然后关闭进程。实际回答还需要模型实例已加载、业务请求获得授权，并在工作区已配置模型用途时选中相应的本地模型。

补充包自带锁定的 SDK 2.0.0、worker 和上游许可，复用原后端中的 Python、Node 和 Core。启动器会核对配套后端清单及相关文件。出现版本不匹配时，请选择同页的 `0b014775` 后端。要使用原启动方式，关闭本窗口后打开原后端的 `start-backend.cmd`。
