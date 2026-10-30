# 随包 ASR 的有限真实验证与初始资产保护

`asrwav-b2ab23a7`实际完成同一合成英文WAV两次独立转录、时间定位、错误checksum负控及同库冷重启。actual/wrapper0、clean58803b80且源码一致，41业务HTTP、两次自有Core启动、两独立job均attempt1 succeeded。结果均4个cue/4个raw cue、14028ms，固定文字/结构/原始及定位时间段/时长投影完全相同；原件、两结果和唯一anchor重启精确读回。三个预设短语完整出现，仅是该合成样本内容检查，不是WER或普遍准确率。

复用原448968B speech.wav（SHA5dacc3cf…），未重新TTS或复制输入文件；Core按业务保存原件blob是本次必要写入。实际Core SHA043834e0…来自clean89b21d4e显式offline build，混合launcher/profile原17路由保留；Python3.12与ASR/decoder/transport/tool_paths仍为原bpr1不可变包。不是当前HEAD完整重打包或安装资格，也不把后继worker修补移绑到该真实运行。

52选择成员、5混合成员、123模型/VAD/关键依赖成员及4当前源前后完整SHA一致，四模型资产147882941B前后保全，对应base随包模型已以CPU int8实际完成转录；不声称依赖逐个读取了全部资产。原两Core PID13472/18656均回收exit1，精确端口两相IPv4/6无LISTEN；connect_ex10035仍UNKNOWN，不称优雅停止或明确拒连。两job已终态，异常取消分支NOT_REQUIRED，未实际演练；无独立OS worker PID回收证明。本样本无尾垫越界，合法尾垫正例未在真实旅程出现。

本次0运行环境复制、0LLM请求，harness只向loopback Core发HTTP；原件/model/runtime不改。精确执行run在新增计量收据前11文件1165874逻辑B，排除此前准备与共享缓存，不是全仓或物理磁盘变化。独立复核仅读四份精确终态文件，没有重跑模型。MP3/MP4音轨、中文/复杂音频、备份恢复、UI/安装、Owner验收及完整J1/CL/F05仍未获本次资格。

## 当前生产源的初始缺失保护

指定faster-whisper1.2.1构造在本地tokenizer.json缺失时会另走Tokenizer.from_pretrained；local_files_only参数没有覆盖该fallback。当前worker在选定目录缺model.bin/config.json/tokenizer.json、空文件或非文件时先报错，并在whole/windowed两处构造传local_files_only=True。显式选择不回退其他模型；既有随包/声明/默认顺序、base/CPU int8和全局配置不变，preprocessor_config.json仍可选。

正式`asrred-af44b31c`对旧生产源纯mock构造哨兵得到17失败/3通过，actual/wrapper1、clean05cc2601且源码一致；没有真实构造或下载。修补后的实际tracked源`asrgreen-3a1be35a`十条受影响测试路径75通过，actual/wrapper0、58803b80+dirty9f61c1bd…且源码一致。包含20个新保护反例/正例；部分既有解码/分窗测试实际使用本机ffmpeg/PyAV，模型构造为替身，不能把75项全部叫纯mock或真实ASR。禁cacheprovider的cache_dir警告保留。

首次changed-file Ruff `asrlint-7cd12ca5`因现有test_windowed_extract未使用json导入失败，原HEAD同导入已核。仅删除该行，75项仍保留原资格SHA，未重跑相同行为检查；最终`asrlint2-1a9889b5`对八个changed Python路径Ruff0，actual/wrapper0且源码一致。ignored候选先前20通过/17失败3通过和fixture副本8通过1失败1deselected均是informal，原日志保留，不替代正式结果。原patch缺LF及CRLF apply-check失败也保留；无失败重签。

该保护覆盖初始资产缺失，不是OS网络隔离；检查后外部删除tokenizer的竞态未消除。非空检查不证明资产语义正确或识别质量。真实ASR运行早于当前源补丁，原bpr1没有被偷偷改写；当前修补仅有上述定向资格。全部证据与源码身份见[清单](MANIFEST.json)，当前进度只在[唯一执行记录](../../current/AAOS-UI-FIRST-EXECUTION-20261009.md)维护。撤销实现可精确回退该worker和受影响测试，不回写原包、DB或既有收据。
