# 交付边界

本修正版解决原page17 consumer提案P1：当前desktop-fast在Python依赖安装前加载Vite，原无条件Python/jsonschema同步检查没有声明可用环境。Node-only guard现在直接被Vite消费，真实配置漂移负例证明该检查不是只存在于样例或独立脚本。

来源读取许可来自固定代码清单与manifest已经声明且严格限界的公共引用，不来自generated.sources。generated.sources只是比较对象，删改、重排、重复、私有路径或伪造hash都不能扩展读取。整个生成TS由固定header+严格JSON段+固定结尾解析和比较，不执行其代码；原字节、metadata、identity、权限/许可声明和UNKNOWN runtime与实际固定输入比较。guard不会把合法hash视为许可/可用/安装或授权；完整Schema/semantic仍由显式Python生成和11项测试验证。

8项page17新旧测试保留精确CAP筛选、切换不残留、未知许可/真实性/runtime分别呈现和不新增执行按钮。Node guard新增9项覆盖无Python、原字节漂移/恢复、validator/generator/guard/host/schema漂移、sources篡改/重复、TS完整性、重复JSON/depth、protected/私有/穿越、缺失/超大和Windows junction拒绝。实际Vite配置加载各3例在两种环境通过；没有服务/浏览器/模型或跨项目业务写入。

未运行完整build或GitHub CI；serve/test配置加载与镜像TS不是安装资格。保留既有canonical build Python路由、root解析和verifyBuildEnvironment，不重排CI、不新增依赖/锁。镜像测试仅使用公开工程资料，不代表真实引擎/商业许可/用户验收。
