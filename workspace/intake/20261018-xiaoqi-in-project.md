# 小栖并入 AAOS 的 Owner 决定

Owner 当前明确要求：“还有小栖虚拟人物 本地仓库和云端也并入到本项目里来，不在独立开发，直接适配到项目里”。
这更新此前 FE18/QODER 独立开发边界；历史回执仍保持原日期与资格。

已核源仓库 `D:/All projects/ASTRYN` clean，`main` 与云端 `DTALEX66/ASTRYN`
均为 `3115378bb3fe13849ed422c739002428fef82892`。学习陪伴 feature 分支提交
`38d1fb24a5d88ee40c467af8f5135ed6ae5cf973` 已在当前 main 历史中。
本轮不删除源仓库、不改远端，不启动第二开发宿主。

直接适配目标为本项目 `frontend/` 内的人物呈现、正式 ConversationPanel 和 CharacterMemoryPanel。
SQLite/CAS、模型配置、会话 preview/confirm/status/cancel/history 继续由现有 AAOS Core 负责。
不引入 ASTRYN 的 SyntheticHost/Conversation/Memory/Context、开发代理、直接 OpenAI adapter、
旧 machine/answers 伪流式 bridge 或 ephemeral profile 持久化回退。

ASTRYN 源码登记为 private/UNLICENSED，Owner 本轮授权第一方整合，不改写成 MIT。
人物位图是 MINIMAX DESIGN AI 生成、用户转交，沿用平台条款登记与原始 SHA；
缺独立公开再许可证明，不能标为 CC0/MIT。九态位图是静帧，无音素口型。
先将可用呈现适配到当前正式请求与记忆接口，再逐项验证首页、阅读、侧栏和恢复。

状态：IN_PROGRESS；源身份核对不是产品集成或 Owner 验收。
