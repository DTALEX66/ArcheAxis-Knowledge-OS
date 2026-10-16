# 给接手 AGENT 的提示词

下面文本供用户复制发送。只有用户实际向接手 AGENT 发出后，才构成该次任务的请求；仓库内保存本身不触发执行。

```text
你接手 Project ASTRYN｜星栖，默认角色小栖。请执行真实 M0 开发，不只写计划或原型说明。

唯一默认写入项目：D:\All projects\ASTRYN。
目标 GitHub：https://github.com/DTALEX66/ASTRYN。

先完整阅读：
1. AGENTS.md、AUTHORITY.md、PROJECT_CONTRACT.yaml。
2. docs/current/STATUS.md。
3. docs/authority/PATH-REGISTRY.md、docs/development/REPOSITORY-LAYOUT.md。
4. docs/tasks/archive/ASTRYN-DEVELOPMENT-START-V1.0.txt。
5. docs/tasks/M0-EXECUTION-HANDOFF.md、docs/tasks/M0-ACCEPTANCE-TRACKER.md。

当前已完成的只有任务归档与仓库规范。没有已实现 M0。最近核验本地 .git 不存在，远端关联 UNVERIFIED；原文 SHA-256 已匹配。请动态复核，不覆盖已有文件，不自动 git init、clone 到非空目录或重建远端。若需要建立 Git 关联，提出保护已有文件的具体方案并请求该操作授权；Git 阻塞不应阻止本地获准的开发。

本次授权你在 ASTRYN 内实施 M0、项目内必要依赖与测试、Dev Host 和交付文档；先确认具体依赖版本、官方来源、scope 和 lockfile，不全局安装或下载大型模型/运行时。可按原任务对 D:\All projects\ArcheAxis-Knowledge-OS 作最小必要只读核验；本地不可用可查官方 GitHub 只读源码。AAOS 源码写入、其他项目操作、全局配置、凭据修改、付费调用、commit/push/PR/merge/release、正式安装均不在本次授权内。权限拒绝不绕过，E:/F: 不访问，不读取私人会话或其他项目秘密。

依照交接 T00-T10 连续推进。先简要报告现场与路线，然后立即实施不受阻塞的源码工作。无需每个常规步骤再次确认。保留单 writer；未经我要求不创建多 AGENT。

保持能力归属：ASTRYN 负责人格、陪伴、表达、角色渲染与可复用 UI；AAOS 负责统一模型、会话、记忆、上下文、任务和权限。经有类型、版本、权限的 Host Adapter 接入；禁止直接写 AAOS 数据库，禁止第二长期记忆库、模型中心或正式前端。

M0 优先原创 SVG/Canvas 角色与轻量 React Dev Host，具体技术以现行 AAOS 约束和实际依赖核验收敛。不同时引入多个数字人底座。必须实现可见角色、文本交互、状态驱动表情/动作、流式与取消、会话隔离、真实错误、宿主契约与定向测试。任务审批/完成/失败仅由可信系统回执触发；模型宣称完成不能改变系统状态。

先尝试已存在 AAOS 模型接口；不可接通可实现仅开发环境服务端兼容适配器，密钥不进入浏览器。无获准模型时明确 MODEL_UNAVAILABLE，不脚本冒充 AI、不擅自付费。合成传输/记忆/文档只用于明确标注的测试；真实模型和真实 AAOS 接入缺失保留 NOT_TESTED 或 BLOCKED_BY_HOST_CONTRACT。

研究原文九个优先开源仓库与补充候选，记录官方版本、实际源码功能、维护、代码/权重/素材许可证、适配成本、最小吸收能力和采用决定。研究要支持 M0，不无限等待研究全部生态。

按真实 manifest 运行 lint、typecheck、unit、build，并做浏览器交互验证。重点覆盖缺模型/错误、取消、重复/乱序/迟到、快速切换、卸载、记忆越权和模型伪造任务完成。不要默认录音、摄像头、采屏或系统命令。

每个实施切片记录实际路径、测试命令/退出码、证据和阻塞；回填验收台账。更新 README、STATUS、架构能力归属、研究矩阵和验证报告。原始本地日志/产物存 .project-local，脱敏报告存 docs/verification。

结束前审阅范围、意外文件及可用 Git diff/status。最终给出可运行源码与启动方法、实际功能、验收结果、真实模型/宿主集成状态、未完成项、Git/远端状态和下一阶段最短队列。不可把接口、fixture、build、CI 配置或漂亮页面宣称为真实智能集成。遇阻塞继续完成独立任务，不编造成功。
```
