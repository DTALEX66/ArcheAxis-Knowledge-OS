// One small configuration per discipline; the three templates share Core engines.
import type { CoreOperation } from "../api/generated/core-contract";

export type DisciplinePack = { id:string; name:string; fields:string[]; relations:string[]; activity:string; evaluation:string; sample:string };
export const DISCIPLINES: DisciplinePack[] = [
  {id:"math",name:"数学",fields:["定义域","条件"],relations:["推导自","反例"],activity:"证明或构造反例",evaluation:"核对每步条件和推导",sample:"比较两种勾股定理证明的前提"},
  {id:"statistics",name:"统计与数据科学",fields:["样本","假设"],relations:["估计","检验"],activity:"复现统计分析",evaluation:"检查抽样、误差与可重复性",sample:"比较均值估计的置信区间"},
  {id:"physics",name:"物理",fields:["单位","边界条件"],relations:["解释","近似"],activity:"建模与实验对照",evaluation:"量纲、误差与适用范围",sample:"记录单摆周期实验"},
  {id:"chemistry",name:"化学",fields:["物质","实验条件"],relations:["反应","表征"],activity:"分析反应与测量",evaluation:"条件、守恒与实验来源",sample:"比较两种滴定方法"},
  {id:"biology",name:"生物",fields:["对象","层级"],relations:["调控","证据支持"],activity:"解释机制与观察",evaluation:"区分观察和因果解释",sample:"梳理细胞信号通路资料"},
  {id:"astronomy",name:"天文",fields:["天体","观测波段"],relations:["观测于","模型预测"],activity:"比较观测与模型",evaluation:"观测来源与不确定性",sample:"比较恒星光谱分类资料"},
  {id:"earth",name:"地球科学",fields:["区域","年代"],relations:["形成于","关联层位"],activity:"分析地质证据",evaluation:"时空尺度与样本来源",sample:"记录岩层剖面解释"},
  {id:"environment",name:"环境",fields:["区域","指标"],relations:["影响","监测"],activity:"比较环境指标",evaluation:"测量口径与因果限制",sample:"分析河流水质监测资料"},
  {id:"computer",name:"计算机",fields:["版本","复杂度"],relations:["依赖","实现"],activity:"运行与复现程序",evaluation:"测试结果与环境版本",sample:"比较两种排序算法的实际输入"},
  {id:"engineering",name:"工程",fields:["约束","容差"],relations:["满足","失效于"],activity:"设计与验证",evaluation:"需求、试验与失效模式",sample:"比较桥梁结构方案"},
  {id:"medicine",name:"医学",fields:["人群","研究设计"],relations:["支持","反证"],activity:"评价原始研究",evaluation:"研究质量、效应与适用人群",sample:"比较同一主题的两项研究；不生成诊疗结论"},
  {id:"agriculture",name:"农业",fields:["作物","生长条件"],relations:["影响产量","适用"],activity:"比较田间观察",evaluation:"试验条件与地域差异",sample:"记录灌溉方案试验资料"},
  {id:"economics",name:"经济",fields:["假设","数据口径"],relations:["解释","预测"],activity:"检验经济模型",evaluation:"假设、识别与数据来源",sample:"比较供需模型的适用条件"},
  {id:"management",name:"管理",fields:["目标","组织条件"],relations:["支持决策","依赖"],activity:"分析决策案例",evaluation:"目标、限制与结果证据",sample:"比较两个项目风险处理案例"},
  {id:"law",name:"法律",fields:["法域","生效时间"],relations:["引用","区别于"],activity:"核对规则与案例",evaluation:"法域、时效与原始条文",sample:"比较两条规范的适用范围；不生成法律意见"},
  {id:"politics",name:"政治",fields:["制度","时期"],relations:["影响","比较"],activity:"比较制度与论证",evaluation:"来源立场与证据范围",sample:"比较政策过程的解释框架"},
  {id:"sociology",name:"社会学",fields:["群体","研究方法"],relations:["解释","观察"],activity:"分析社会研究",evaluation:"样本、方法与外推限制",sample:"比较社区研究的观察方法"},
  {id:"psychology",name:"心理学",fields:["构念","测量工具"],relations:["测量","复现"],activity:"评价实验设计",evaluation:"效度、重复与不确定性",sample:"比较记忆实验的测量方式"},
  {id:"education",name:"教育",fields:["学习目标","评价方式"],relations:["前置","达成"],activity:"设计学习活动",evaluation:"作答证据与实操表现分开",sample:"设计一个来源定位练习"},
  {id:"history",name:"历史",fields:["时期","史料类型"],relations:["佐证","相矛盾"],activity:"比较史料",evaluation:"出处、时间与转引关系",sample:"比较两份同一事件史料"},
  {id:"philosophy",name:"哲学",fields:["命题","前提"],relations:["蕴含","反驳"],activity:"重建论证",evaluation:"前提、有效性与异议",sample:"重建一个认识论论证"},
  {id:"literature",name:"文学",fields:["作品版本","文本位置"],relations:["互文","比较"],activity:"细读与文本比较",evaluation:"引文定位与解释依据",sample:"比较两首诗的意象"},
  {id:"language",name:"语言",fields:["语种","语料"],relations:["例证","对比"],activity:"分析语言实例",evaluation:"语境、语料与规则例外",sample:"比较两组句法实例"},
  {id:"design",name:"设计",fields:["用户目标","约束"],relations:["响应","迭代自"],activity:"原型与反馈",evaluation:"任务结果与反馈依据",sample:"比较两个表单交互方案"},
  {id:"music",name:"音乐",fields:["作品版本","段落"],relations:["变奏","呼应"],activity:"分析与演奏练习",evaluation:"文本分析与实操评价分开",sample:"记录一个乐句的演奏练习"},
  {id:"media",name:"媒体",fields:["媒介","发布时间"],relations:["转引","原始来源"],activity:"核对传播与来源",evaluation:"独立来源与转引去重",sample:"追溯一则报道的原始依据"},
  {id:"architecture",name:"建筑",fields:["场地","使用需求"],relations:["约束","参照"],activity:"比较空间方案",evaluation:"尺度、规范与使用证据",sample:"比较公共空间的动线方案"},
  {id:"sport",name:"体育",fields:["活动","训练条件"],relations:["练习","反馈"],activity:"记录练习与表现",evaluation:"训练记录、表现与复习状态分开",sample:"记录一次动作练习及反馈"},
];
// A template requirement is what the template asks the platform to do, stated so a reader can
// audit the join instead of trusting it:
//  - `declared` keeps the name the template has always declared.
//  - `capability_id` carries the stable Atlas ID only where the declaration genuinely joins an
//    existing entry: either the dotted name appears verbatim in config/capability-map.v1.json's
//    runtime_capabilities, or the Atlas entry's own objects/views/dependencies name the same
//    concern (the resolver reports which of the two it is). Anything else stays null — inventing an
//    ID would be a rename/demote decision reserved to the Owner by the Atlas tombstone rule.
//  - `served_by` names the first-party Core commands the template really calls today. The type
//    annotation below checks every entry against the generated contract, so a stale or invented
//    command is a compile error rather than a claim on screen.
export type TemplateRequirement = { declared: string; capability_id: string | null; served_by?: readonly CoreOperation[] };
export type TemplateDefinition = { id: string; name: string; capabilities: readonly TemplateRequirement[] };
export const TEMPLATES: readonly TemplateDefinition[] = [
  {id:"T1",name:"知识网络",capabilities:[
    {declared:"document.save",capability_id:null,served_by:["document_create","document_draft"]},
    {declared:"document.reference",capability_id:null,served_by:["document_get","document_version"]},
    {declared:"document.backlinks",capability_id:null,served_by:["documents_list","document_get"]},
    {declared:"document.local-graph",capability_id:null,served_by:["documents_list","document_get"]},
    {declared:"canvas.references",capability_id:null,served_by:["document_draft","document_version"]},
  ]},
  {id:"T2",name:"研究与项目",capabilities:[
    {declared:"document.save",capability_id:null,served_by:["document_create","document_draft"]},
    {declared:"document.collection",capability_id:null,served_by:["documents_list","document_get"]},
    {declared:"document.reference",capability_id:null,served_by:["document_get","document_version"]},
    {declared:"search.local",capability_id:null},
    {declared:"html.structure",capability_id:"CAP-0020"},
    {declared:"pdf.extract",capability_id:"CAP-0020"},
    {declared:"office.structure",capability_id:"CAP-0020"},
  ]},
  {id:"T3",name:"学习与实践",capabilities:[
    {declared:"document.save",capability_id:null,served_by:["document_create","document_draft"]},
    {declared:"learning.review",capability_id:"CAP-0040"},
    {declared:"learning.state",capability_id:"CAP-0040",served_by:["learning_state"]},
    {declared:"learning.fsrs",capability_id:"CAP-0040"},
    {declared:"course.general",capability_id:"CAP-0060"},
  ]},
] as const;
