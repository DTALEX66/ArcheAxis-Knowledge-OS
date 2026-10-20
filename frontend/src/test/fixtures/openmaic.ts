/** Synthetic fixture of the pinned formatVersion=1 export; no upstream runtime qualification. */
export function openMaicFixture() {
  return {
    formatVersion: 1, exportedAt: "2026-10-19T00:00:00.000Z", appVersion: "1.2.1",
    stage: { name: "证据与来源", description: "外部测验", createdAt: 1, updatedAt: 2 },
    agents: [], mediaIndex: {}, scenes: [{ type: "quiz", title: "辨认来源", order: 2,
      content: { type: "quiz", questions: [{ id: "q1", type: "single", question: "选择来源 <script>never()</script>",
        options: [{ label: "原件", value: "source" }, { label: "猜测", value: "guess" }],
        answer: ["source"], analysis: "核对原件", points: 2 }] } }],
  };
}
export const fixtureBytes = () => new TextEncoder().encode(JSON.stringify(openMaicFixture()));
