# 小栖 GF03 睡衣短裤版交付清单

日期：2026-10-14。生成平台：MiniMax Design。图像生成模型：General Image Pro（能力 ID：nano_banana_2）。服装方向：成年女性、柔软纯色短袖家居上衣与宽松家居短裤，保留灰蓝渐变发和星球发夹，写实数字角色风格。

## 依据与参数
- 用户原始参考：ver_83077dbccf75、ver_2ae37454796e、ver_9b80ef711ee7。
- 已确认人脸锚点：ver_cd9a3b0a57b8。
- 睡衣版三视图：A2 ver_73eef29ea54f；A3 ver_9a1146d785cf。
- 本轮 A1/B/C：2:3、2k，每次生成一个目标。通道未暴露 seed 与 prompt_optimizer 参数，未伪造参数记录。
- 去背：Remove background；采用同一 Resource 新版本，原始有底版本仍保留。
- D：FFmpeg 从透明 idle 母版派生，没有重新绘制人物。

## 文件命名与资产状态
下表名称是项目 Resource 名称，PNG 导出建议追加 .png。版本标记 v1 指本轮睡衣半身与构图交付，不代表早期夹克版。

|名称|用途|当前背景|
|---|---|---|
|xiaoqi_key_visual_sleepwear_v1|A1 基准卡|透明|
|xiaoqi_state_idle_sleepwear_v1|B 待机|透明|
|xiaoqi_state_listening_sleepwear_v1|B 倾听|透明|
|xiaoqi_state_thinking_sleepwear_v1|B 思考|有底；去背失败|
|xiaoqi_state_speaking_sleepwear_v1|B 反馈|透明|
|xiaoqi_state_interrupted_sleepwear_v1|B 打断|透明|
|xiaoqi_state_awaiting_approval_sleepwear_v1|B 等待决定|透明|
|xiaoqi_state_executing_sleepwear_v1|B 执行回执|透明|
|xiaoqi_state_completed_sleepwear_v1|B 完成|有底；去背失败|
|xiaoqi_state_failed_sleepwear_v1|B 失败|有底；去背失败|
|xiaoqi_pose_idle_sleepwear_v1|C 静止|透明|
|xiaoqi_pose_listening_sleepwear_v1|C 倾听|有底；去背失败|
|xiaoqi_pose_thinking_sleepwear_v1|C 思考|透明|
|xiaoqi_pose_nod_sleepwear_v1|C 点头|透明|
|xiaoqi_pose_point_sleepwear_v1|C 指点|透明|
|xiaoqi_pose_speaking_sweep_sleepwear_v1|C 舒展讲解|透明|
|xiaoqi_home_sleepwear_v1|D 首页，4096×2304|透明|
|xiaoqi_avatar_sleepwear_v1|D 头像，2048×2048|透明|
|xiaoqi_sidebar_sleepwear_v1|D 侧边，1024×2048|透明|

## 尚未完成 / 限制
- 4 个去背任务因服务 429 限流失败，失败费用已退回。任务 ID：thinking tsk_8e8eb75ed3e7；completed tsk_97a4374d4ed6；failed tsk_f85cfb34ae92；C listening tsk_3aeb57ddebfc。需要用户明确重试授权后用原任务 retry，不重新绘制。
- E 组要求仅口部或眼睑变化、其余像素级一致。当前生成通道没有局部像素锁定能力，按简报跳过，留给矢量层/可控局部编辑；不是音素口型。
- D 头像为裁切派生，圆形安全区和眼线位置尚未通过实际界面试装核对；不声明已满足精确验收。
- 本轮 A1/B/C 使用 2k 生成档，未全部升级到建议的 4096 长边。首页为 4096 画布，属于布局缩放，不声称原生 4K 人物细节。
- 尚未逐张完成用户要求的正式视觉验收，不声明身份、正交或边缘完全合格。
- 成果已保存至项目画布；尚未落盘到 gf03-out/，尚未验证统一 sRGB 配置。
- 可选 360° 转台视频未制作；本轮不交付可编辑 3D/VRM 本体。

## 权利说明
输出的权利和许可按平台与用户适用协议执行；不额外承诺专有权或无第三方权利风险。不使用真人照片硬裁作为角色资产；未绘制状态环、状态符号的生成要求已写入提示词，实际画面以用户审阅为准。
