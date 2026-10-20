# 交付说明

此目录仅为ignored、可审阅的消费实现提案。CURRENT.md是唯一固定接续入口，产品源码未写入。

8个文件中新增6个：内置manifest说明原字节、只读生成器、生成TS、详情组件、Python回归、page17回归；修改2个：page17接入一处组件、Vite配置增加只读 --check。没有修改依赖、锁文件、现有Atlas/map/catalog/worker注册或模型配置。

原始说明由既有合同形状建立，以真实当前core-document schema hash、CAP-0020、pdf.extract与pymupdf stable_key声明联接。package version是说明合同版本，不是引擎版本。许可没有从Python库名称、已有依赖或repo LICENSE推导。

validation-mirror是限定公开源码副本；frontend/node_modules为指向本项目既有依赖的本地junction，仅用于隔离测试，未安装或更改依赖。Vitest cache、pytest tmp与全部生成物均在本目录。没有启动浏览器、HTTP/模型或共享进程，无服务待清理。mirror不能当作另一个产品工作区或运行数据源。

所有最终验证在validation.json记录；首次未强化错误分类的Vite探针保存在vite-guard-initial.json，最终探针要求特定manifest门禁错误。无Windows失败被隐藏或记为通过；本切片实际校验命令均通过，预期拒绝用exit23单独记录。

回滚：由Root恢复本补丁对2个现有文件的确切差分，移除本补丁6个新增文件；不得覆盖其他write set或清理本项目其他现有修改。当前未应用，无需产品回滚。
