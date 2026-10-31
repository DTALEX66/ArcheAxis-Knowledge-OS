# 剩余精确对象：普通权限独立复核

管理员Apply终态为102,591个计划对象全部修改、错误0。独立验证器核TokenElevation=0且SID为原指定reader，单批读取原plan，不重新枚举533根；102,591对象（47,644目录/54,947文件）的预期owner/group/DACL/protection/ACE、同句柄只读可开、type/size/mtime通过，未读取文件正文，未写ACL/owner。533根均有计划对象，不等于所有后代已覆盖。

发现原计划的preserved库存769条中有9个目录也被列入members并实际VERIFIED：生成器先记录目录本身的ACL计划，后枚举子目录失败，又catch记为preserved。其余760条没有记录操作；私有/链接等排除对象未被验证器读取正文。保留原plan/journal不改，不能再称769条全未改，也不能推断9个子树已恢复完整访问。

首轮验证在输入交集断言失败（exit1）留证；后继全对象通过但因上述库存语义缺陷诚实返回exit2/FAIL，source_consistent=true。详见[MANIFEST](MANIFEST.json)。大小/mtime及零正文读取不是独立内容SHA证明。新验证器不替换旧Apply/Rollback模块，原权限备份和原回退方式保留。

下一步沿本仓storage_report重计可读范围与剩余拒绝，再精确判断长路径后代；不重启Apply、不全盘授权或改权限、不读私有状态。权限局部恢复不等于产品、构建、安装态或Owner验收。
