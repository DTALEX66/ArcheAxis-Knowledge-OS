/* ArcheAxis production UI adapter and OSUI v3 shell behaviors.
   Every request targets a real local endpoint; unsupported methods fail closed. */
(function () {
  const jsonHeaders = { "Content-Type": "application/json" };

  async function request(path, options) {
    try {
      const response = await fetch(path, options);
      const data = await response.json();
      if (!response.ok) {
        throw new Error(typeof data?.detail === "string" ? data.detail : `HTTP ${response.status}`);
      }
      return { ok: true, data, meta: { source: "本地接口", fixture: false, stale: false } };
    } catch (error) {
      return {
        ok: false,
        error: {
          kind: "UNAVAILABLE",
          summary: "本地数据暂时不可用",
          originalSafe: true,
          recovery: ["稍后重试", "打开系统诊断"],
        },
        meta: { source: "本地接口", fixture: false, stale: true },
      };
    }
  }

  function unsupported(summary) {
    return Promise.resolve({
      ok: false,
      error: {
        kind: "UNSUPPORTED",
        summary,
        originalSafe: true,
        recovery: ["查看能力规划", "返回工作台"],
      },
      meta: { source: "能力合同", fixture: false, stale: false },
    });
  }

  window.ArcheAxisUIAdapter = Object.freeze({
    getWorkspaceOverview: () => request("/workspace/api/status"),
    createIntakeDraft: () => unsupported("资料草稿只保存在当前导入表单，尚无独立持久化端点"),
    inspectIntake: () => unsupported("请选择真实网页地址或本地文件后再检查"),
    submitIntake: (payload) => payload?.url
      ? request("/workspace/api/intake/url", { method: "POST", headers: jsonHeaders, body: JSON.stringify({ url: payload.url }) })
      : unsupported("请选择真实来源后再导入"),
    listSources: () => request("/workspace/api/knowledge"),
    getOriginalAsset: () => unsupported("请先在资料库选择原件"),
    getDocument: () => unsupported("请先在阅读器选择原件"),
    resolveAnchor: () => unsupported("请先选择证据锚点"),
    listClaims: () => request("/workspace/api/research"),
    getClaimEvidence: () => request("/workspace/api/lifecycle"),
    recordReviewDecision: () => unsupported("请从证据复核队列记录决定"),
    getEvidenceBundle: () => request("/workspace/api/lifecycle"),
    listLearningRoutes: () => request("/workspace/api/learning"),
    getLearningSession: () => request("/workspace/api/learning"),
    recordLearningResponse: () => unsupported("请先选择真实学习项目"),
    submitTeachBack: () => unsupported("Teach Back 写入仍需选定真实学习项目"),
    listAIAssets: () => request("/workspace/api/runtime/candidates"),
    getAIAsset: () => request("/workspace/api/runtime/candidates"),
    decideAIAsset: () => unsupported("AI 资产决定必须来自受治理审核流程"),
    listJobs: () => request("/workspace/api/jobs"),
    retryJob: () => unsupported("请在任务与回执页面选择可恢复任务"),
    getCapabilityMatrix: () => request("/workspace/api/status"),
    getSettings: () => request("/workspace/api/status"),
    subscribe: () => () => {},
  });

  function bindGlobalSearch() {
    const input = document.querySelector("#global-search");
    if (!input) return;
    const routes = {
      "资料": "vault",
      "原件": "vault",
      "证据": "evidence",
      "主张": "research",
      "学习": "learning",
      "任务": "runtime",
      "回执": "runtime",
      "设置": "diagnostics",
      "能力": "diagnostics",
    };
    input.addEventListener("keydown", (event) => {
      if (event.key !== "Enter") return;
      const match = Object.entries(routes).find(([keyword]) => input.value.includes(keyword));
      if (match) location.hash = match[1];
    });
    window.addEventListener("keydown", (event) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        input.focus();
      }
    });
  }

  function bindLessonBlueprint() {
    const scenes = [
      ["场景 01 · 对象边界", "原件和派生产物不能由同一个结论替代。", "先保留原件，再分别审查转译质量与事实证据。"],
      ["场景 02 · 证据关系", "主张需要关系，而不是伪精确评分。", "支持、反驳、背景和适用范围必须同时可见。"],
      ["场景 03 · 复核停止点", "结论出现前，应先允许学习者停下核查。", "回到来源、检查范围、记录冲突或提出问题。"],
    ];
    document.querySelectorAll("[data-lesson-scene]").forEach((button) => {
      button.addEventListener("click", () => {
        const scene = scenes[Number(button.dataset.lessonScene)] || scenes[0];
        document.querySelectorAll("[data-lesson-scene]").forEach((item) => item.toggleAttribute("aria-current", item === button));
        const title = document.querySelector("#lesson-stage-title");
        const copy = document.querySelector("#lesson-stage-copy");
        const step = document.querySelector("#lesson-stage-step");
        if (step) step.textContent = scene[0];
        if (title) title.textContent = scene[1];
        if (copy) copy.textContent = scene[2];
      });
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    document.documentElement.dataset.uiContract = "osui-v3-production";
    bindGlobalSearch();
    bindLessonBlueprint();
  });
})();
