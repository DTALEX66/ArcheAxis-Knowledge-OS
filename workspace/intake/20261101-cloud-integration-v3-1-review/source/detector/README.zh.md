# v3.1 定向补件：实际 detector 模型/config 身份

## 结论
发现且真实复现 v3 不一致，提供 **候选最小修复**，未合并正式项目。仅改 `shared/file_detection.py` 与 `services/python-workers/document/worker_detect.py`，相对 v3 最终源码的补丁为 `detector-v3-to-v3.1.patch`。

原云端副本在本次环境不存在。经用户明确允许恢复，从原 v3 ZIP（SHA256 `de984bf8917d24f4bc837221f76983dde20973f8285808e1fa6c351a5c68ac43`）及固定历史 commit 恢复；没有拉取用户本地代码，也没有使用远端 main 代替基线。`source-binding.json` 将涉及源码、模型、config、fixture、权限/版本/receipt相关文件逐一核对原包的 v3 SHA。原ZIP、解压证据均未修改。

## 实测
- **基线反例**：`logs/baseline-confirmed.*`，真实 ONNX 推理；caller不同有效模型与config被回执hash，但检测仍使用installed版本返回xlsx；env版本真实返回png，回执却仍为installed模型hash。退出0表示反例断言成功，不是原实现正确。
- **候选最终定向套件**：`logs/final-scope.*`：**42 passed，47 subtests passed，0 skipped，exit0，4.48s**。9项新模型身份测试 + 7项既有worker测试 + 10项shared检测测试 + 16项既有transport安全/协议测试。没有跑不相关全套。此前15、16、26项日志与最终42重叠，不能累加。
- 新测试覆盖installed/caller/env/显式caller优先、env切换导致新会话、同路径替换仍缓存旧会话且保留旧身份、真实ORT构建后文件替换、坏模型不得复用成功结果、双线程不同模型不得混用标签/身份。
- 三套ONNX字节确实不同：保留真实模型计算图，使用ONNX库修改doc metadata得到有效不同字节；config对xlsx覆写为pdf/png用于观察选择。不是另一种模型质量实验，也没有伪造推理输出。`baseline_probe.py`生成样本并执行原反例；`generate_fixtures.py`可单独生成。

## 修复语义和边界
1. shared读取一次model bytes与config bytes；**同一份bytes**传给真实ORT和JSON解析，hash保存在已加载会话身份中。worker不再事后另读文件生成“模型hash”；structure与loss receipt都绑定实际会话双hash。
2. 显式CLI `--repo-root`只选数据文件；可执行detector仍固定为worker自身安装目录的代码。未显式提供时保留原env优先/缺文件时installed回退规则。未增加远程模型参数或新执行权限。
3. 同路径文件替换**不自动热更新**：旧会话继续用旧数据，回执诚实保留旧双hash。选择不同路径或新进程才加载新会话。RLock覆盖load→feature→推理→身份返回，避免并发全局缓存错配。
4. `model_sha256`仍是实际ONNX字节SHA256，没有改成路径或组合hash。新增`config_sha256`及receipt双hash。`revision=standard_v3_0`保留既有profile声明，新增`revision_status=declared_profile_not_publisher_verified`；不凭hash认证外部模型的上游身份、版本或许可。
5. 既有engine版本0.1.0、transport权限/路径/输入hash/输出hash/协议拒绝检查未修改。定向transport测试真实进程通过。Core源码逐字节与v3一致：此补件未重编译或重跑Core端到端，不能把Python定向测试冒充新的Core资格。
6. 没有改原识别算法/训练模型、没有改全局模型配置或权限。未知/损坏有效路径模型仍失败，不回退为伪成功。大模型外部tensor文件加载不在本次单文件Magika范围；候选不提供新能力保证。

## 复现
使用 Python 3.12（本次3.12.14）、Git、uv。将本目录复制到独立空目录，设置 `V3_PACKAGE` 为已解压且校验过SHA的原v3包根（含patches/aaos-isolated.patch），运行 `bash reproduce.sh`。脚本创建全新`reproduced-run`（可用WORK_DIR指定不存在的新目录），若已存在则拒绝，绝不覆盖附带历史日志/venv。脚本只恢复固定commit、应用v3补丁、运行基线反例、应用本候选与四个定向测试文件。它不上传、不推送、不执行无关全套，不读本地项目。

测试依赖见requirements.txt；onnxruntime=1.20.1、numpy=2.4.6、onnx=1.19.1、pytest=9.1.1。新增onnx仅用于制造可复现异字节fixture，不加入产品依赖/锁文件。

打包仅包含本目录（patch、脚本、绑定记录和真实日志），不包含repo、venv、模型、缓存或大构建产物。历史stdout不回填/改写；新日期与命令/退出码见`*.command.json`。

```bash
# 在非正式项目的全新位置保存该补件目录后：
export V3_PACKAGE=/绝对路径/原v3解压根/AAOS-Cloud-Integration-20261031
bash reproduce.sh
```
`reproduce.sh`中的基线probe同时生成fixtures；模型与XLSX来自固定历史commit，hash已列source-binding.json，无旧工作区依赖。首次依赖freeze因uv默认缓存只读失败，`logs/freeze.*`保留；显式局部cache后`freeze-qualified`成功，requirements为其实际stdout。

`verify_patch.py`是保留的**历史执行脚本证据**，对应`logs/patch-readback.*`，依赖当时恢复区的v3-source/repo/deliverable目录，不能直接在精简补包中运行；未伪装为自足入口。唯一自足复现入口是`reproduce.sh`，它按固定commit+v3 patch恢复源码并应用补件，随后实际执行相同定向测试。原模型字节不打包，基准身份可按source-binding核对。
