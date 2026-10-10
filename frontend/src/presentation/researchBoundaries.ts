// Execution boundaries supplement the immutable design intent and Atlas;
// local UI availability is not source-platform or installed qualification.
export const RESEARCH_BOUNDARIES: Record<string, { available: readonly string[]; pending: readonly string[] }> = {
  "CAP-0090": {
    available: ["问题、材料、假设、方法、实验、反证、结论与待解决项；结论来源和推导依据分别保存", "文档、来源原件与知识的固定身份引用；版本历史和只读详情"],
    pending: ["学术数据库检索与连接器", "OpenScholar / AstaBench 研究线索资格", "自动文献综述、专业依据核验与真人研究验收"],
  },
  "CAP-0100": {
    available: ["文档内的集合、类型属性、固定对象成员与关系；过滤、排序和分页", "表格、列表、看板、日期分组日历与记录卡片；视图定义随文档版本保存", "Core 有界公式表达式、依赖和显式错误；未知来源字段保留"],
    pending: ["Rollup 跨记录聚合", "外部平台公式方言等价资格", "单位换算、时区解释与跨平台日期语义", "带媒体预览的完整图库与媒体交换包", "外部平台导入映射与往返语义等价验收"],
  },
  "CAP-0110": {
    available: ["文档关系和集合关系共用固定版本的图、列表与反向链接；原定义仍由文档保存", "扫描范围、游标、显示截断和不可用目标明确可见；对象身份不按标题猜测"],
    pending: ["GraphRAG 与多跳自动研究", "别名消歧、自动实体关系抽取与推断资格", "全库连续增量图索引与大型图布局引擎"],
  },
};
