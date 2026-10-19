# 失败与恢复轨迹

1. 首次准备新增Node源后，旧Python生成器用SOURCES[4]定位crosswalk，索引位移触发KeyError/有限MANIFEST_PROJECTION_CHECK_FAILED。修正版改用明确公共crosswalk路径；没有修改旧冻结提案或产品。
2. 首轮canonical run hub-node-consumer-1019：审计loader的Vite模块相对路径多一级，ERR_MODULE_NOT_FOUND，outer/child1。原日志/validation保存在failures/config-loader-path及原run，不算产品失败或PASS。修正仅审计loader路径。
3. 第二轮hub-node-consumer-v2-1019：原Python测试要求Vite源码含Python脚本名，1 failed/10 passed。原回执/日志在failures/legacy-python-hook-assertion。该实现镜像断言被替换成实际Node guard源identity变化会改变生成投影的行为回归；真正Vite消费通过单独加载配置并注入来源漂移验证，未降低漂移标准。
4. hub-node-consumer-final-1019曾全部通过；随后补明确duplicate source/guard-source绑定检查，最终以hub-node-consumer-frozen-1019为唯一冻结结果，不累计两轮。

最终：9 Node、11 Python、8 page17均PASS，配置无Python与无jsonschema两组各正/负/恢复PASS、TS/Ruff/显式生成--check PASS。负例的Vite stderr会出现failed to load config，这是预期拒绝，不是隐藏的正例错误。Vite CJS deprecation warning保留，无相关产品修改。
