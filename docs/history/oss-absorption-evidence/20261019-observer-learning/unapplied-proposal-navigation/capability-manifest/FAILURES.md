# 保留的失败

1. `validation-first.json` / `pytest-first.log`：首轮exit1，105 passed / 2 errors。pytest默认将`b'x' * 262145`负例值作为参数ID，Windows写PYTEST_CURRENT_TEST超过32767字符，引发ValueError并影响后一个setup。只把4个byte负例改为明确短ID；未缩小超限负例或降低断言。原日志是合成x字符，不含真实私有资料。
2. 提案Python首次Ruff check exit1：2项I001（validate与test imports）及1项F401（unused re）。仅对提案的3个新Python文件format/修正import；最终Ruff exit0，未修改产品或处理全仓旧诊断。
3. 早期验证118通过后，审查补了包ID/版本末尾换行的严格正则负例，最终57共享case、122项通过。不将105/118/122相加；最终receipt与冻结patch绑定。

首轮pytest原始回执/日志保留。最终PASS只指隔离声明契约，没有安装、启动或能力启用证据。
