/* ArcheAxisUIAdapter — 演示实现。所有方法只返回 fixture，不访问网络、文件系统或真实端点。 */
const fixtureMeta = Object.freeze({observedAt:'2026-08-12T00:00:00Z',source:'mock',fixture:true,stale:false,capabilityState:'PARTIAL',traceRef:'fixture:archeaxis-ui-v1'});
const ok = data => Promise.resolve({ok:true,data,meta:fixtureMeta});
const unavailable = capability => Promise.resolve({ok:false,error:{kind:'UNSUPPORTED',summary:'此能力尚未绑定真实 Adapter。',originalSafe:true,recovery:['查看能力说明','回到可用空间']},meta:{...fixtureMeta,capabilityState:capability}});
window.ArcheAxisUIAdapter = Object.freeze({
  getWorkspaceOverview:()=>ok({title:'示例工作台',fixture:true}), search:()=>ok({items:[],fixture:true}),
  createIntakeDraft:()=>ok({id:'fixture:intake-draft'}), inspectIntake:()=>ok({originalSafe:true,plannedDerivative:true}), submitIntake:()=>unavailable('PARTIAL'),
  listSources:()=>ok({items:[],total:0}), getOriginalAsset:()=>ok({id:'fixture:original-a',integrityState:'UNKNOWN'}), getDocument:()=>ok({id:'fixture:document-a',conversionState:'PARTIAL'}), resolveAnchor:()=>ok({type:'PAGE',page:7}),
  listClaims:()=>ok({items:[]}), getClaimEvidence:()=>ok({claimRef:'fixture:claim-c01',stance:'UNCLEAR'}), recordReviewDecision:()=>unavailable('PARTIAL'), getEvidenceBundle:()=>ok({id:'fixture:bundle-b01',lifecycle:'IN_REVIEW'}),
  listLearningRoutes:()=>ok({items:[]}), getLearningSession:()=>ok({id:'fixture:learning-s01'}), recordLearningResponse:()=>unavailable('PARTIAL'), submitTeachBack:()=>unavailable('PLANNED'),
  listAIAssets:()=>ok({items:[]}), getAIAsset:()=>ok({id:'fixture:asset-r01',lifecycle:'CANDIDATE'}), decideAIAsset:()=>unavailable('PARTIAL'),
  listJobs:()=>ok({items:[]}), retryJob:()=>unavailable('PARTIAL'), getCapabilityMatrix:()=>ok({fixture:true}), getSettings:()=>ok({fixture:true}),
  subscribe:()=>()=>{}
});
