# 风险与回滚

## 基线漂移

- fetch 后比较；
- 不硬重置；
- 新 HEAD 重审；
- 实际 SHA 写入报告。

## 参考图诱导假数据

- 图片只做布局；
- 每张页面建立 API Mapping；
- 没有 API 的部分 Planned；
- Browser test 扫描敏感字段。

## 大规模 UI 重构

- A1 只做 Shell；
- 逐阶段合并；
- 每阶段独立 PR；
- 不和后端高风险改动混合。

## 苹果风格可访问性

- 玻璃透明需保证对比；
- 灰字通过 WCAG；
- Focus 可见；
- 颜色不是唯一表达；
- Reduced Motion。

## 静态栈维护性

- A1 先整理文件；
- 后续框架迁移独立 TaskPack；
- 不因“现代化”破坏 Wheel/Tauri。

## 回滚

A1 无数据库变化：

- `git revert` 即可；
- 保留旧主题；
- 保留旧 API；
- 不删除持久化；
- 不需要 Migration rollback。

A3–A5 如涉及 Schema/Contracts，必须使用项目既有迁移与备份体系。
