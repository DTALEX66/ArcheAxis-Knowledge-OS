# 真实失败与修正轨迹

1. 生成case时首次错误fixture名valid_task_proposal导致StopIteration，改为已存在valid_task；没有把未生成结果报PASS。
2. be10-native-preview-1019 schema相对$id引用未解析：pytest失败1；修正为本地相对schema ref + 明确Registry键，无网络解析。旧回执/log/hash在failures/schema-relative-reference。
3. v2直接Cargo linker找不到link.exe：101。v3绝对bat路径含空格错误：1。保留在failures/cargo-linker-environment、cmd-batch-quoting；改用root已验证dev.py + cwd根目录相对scripts\ci\cargo_test.bat，不改全局/MSVC路径。
4. v4最小镜像漏现有domain编译嵌入template-binding.schema.json：101；仅补这份公开输入，旧回执保留missing-embedded-template-schema。
5. v5 Core25已经PASS，但native最小harness漏公开core-command schema、url/getrandom现有依赖：101。仅补固定公共输入和与正式Cargo相同已有版本，无产品依赖修改；旧失败保留native-harness-closure-and-command-schema。
6. 补合法非context负例准备脚本发生GBK decode错误，因PowerShell多行顺序继续v6。此轮仍通过的旧负例不冒充补充后结果；改显式UTF8，保留v6与修正轨迹valid-non-context-negative-utf8，并最终重跑真正合法task拒绝。另补既有公开core-command枚举，使native实现与schema一致，候选从11增至12。
7. owned mirror删除身份守卫红例：预期子101，实际200与409不符，断言捕获；finally恢复原字节。red-validation.json与red-identity-guard.log保留。红例没有修改产品或候选。
8. root另切片更新公共machine_failure.rs后，旧镜像绿不再绑定当前基线。仅刷新该一文件，before/after hash及此前结果保留failures/baseline-public-machine-failure-update；最终current run以新基线独立重编译验证。

最终结果只以validation-summary.json所指最终current run为准；旧失败及旧绿不删除、不升级产品资格。
