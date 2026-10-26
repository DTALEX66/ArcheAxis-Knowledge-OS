// @vitest-environment jsdom
// Owner bar for this slice: a template calls a qualified implementation through a stable CAP ID,
// and where it cannot, the surface says which of the honest cases it is — never a fabricated 可用,
// never an inert control. Each test below names the product change that would turn it red.
import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { App } from "../app/App";
import { resetRuntimeClient } from "../api/workspace";
import { CanonicalCapabilitiesSpace } from "../spaces/CanonicalCapabilitiesSpace";
import { CanonicalLibrarySpace } from "../spaces/CanonicalLibrarySpace";
import { CAPABILITY_CATALOG } from "../api/generated/capability-catalog";
import type { DocumentDto } from "../api/generated/core-contract";
import { TEMPLATES } from "../templates/disciplines";
import {
  absorptionClassification,
  resolveRequirement,
  resolveTemplateRequirements,
  templatesRequiring,
  type CapabilityRead,
} from "../templates/capabilityRequirements";
import { TemplateWorkspace } from "../templates/TemplateWorkspace";
import { documentRequestIdentity } from "../presentation/documentRequestIdentity";
import { DiagnosticConsole } from "../components/DiagnosticConsole";
import { resetDiagnostics } from "../presentation/diagnostics";

const api = vi.hoisted(() => ({ call: vi.fn() }));
// Partial, not total: a factory that returns only `coreCommand` also erases `verifyCanonicalCore`
// from the module, so the App shell's canonical startup gets `undefined`, throws, and silently
// drops to the Recovery Shell - the test would then be measuring a surface it never intended.
vi.mock("../api/core", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../api/core")>()),
  coreCommand: api.call,
}));

function scopedReadiness(body:{scope:string;operations:readonly string[]}) {
 const expires=Date.now()+30_000;
 return {schema:"archeaxis.operation-readiness/v1",scope:body.scope,observed_at_ms:Date.now(),expires_at_ms:expires,aggregate:"UNVERIFIED",network_performed:false,models_loaded:false,execution_authorized:false,operations:body.operations.map(operation=>({operation,implementation:"IMPLEMENTED",dependencies:"AVAILABLE",connection:"UNKNOWN",qualification:"UNVERIFIED",permission:"ENABLED",status:"UNVERIFIED",reasons:["CONNECTION_NOT_PROBED","RUNTIME_QUALIFICATION_UNVERIFIED"],expires_at_ms:expires}))};
}

const NOT_READ: CapabilityRead = { state: "not_read" };
const LAUNCHER_SUMMARY = "学科模板 · 知识网络 / 研究与项目 / 学习与实践";
/** The disclosure's own toggle contract, opened the way the committed template tests open it. */
async function openLauncher() {
  const details = (await screen.findByText(LAUNCHER_SUMMARY)).closest("details")!;
  details.open = true;
  fireEvent(details, new Event("toggle"));
  return details;
}
function live(rows: Array<{ capability: string; enabled?: boolean; health?: string }>): CapabilityRead {
  return { state: "read", rows: new Map(rows.map((row) => [row.capability, row])) };
}
function rowOf(templateId: string, declared: string, read: CapabilityRead = NOT_READ) {
  const row = resolveTemplateRequirements(templateId, read).find((item) => item.declared === declared);
  if (!row) throw new Error(`no such requirement: ${templateId}/${declared}`);
  return row;
}
const runtimeNames = new Set<string>(CAPABILITY_CATALOG.entries.flatMap((entry) => [...entry.implementation.runtime_capabilities]));
const allRows = TEMPLATES.flatMap((template) => resolveTemplateRequirements(template.id, NOT_READ));

describe("template capability resolver", () => {
  it("binds only what the authorities join, and every bound ID really exists", () => {
    // Red if a declaration is re-pointed at an ID the projection does not carry, or if a name that
    // is verbatim in the map stops being bound (the join then silently degrades to a bare claim).
    expect(allRows.filter((row) => row.status === "provider_unknown")).toEqual([]);
    for (const template of TEMPLATES) {
      for (const requirement of template.capabilities) {
        if (!requirement.capability_id) continue;
        expect(CAPABILITY_CATALOG.entries.some((entry) => entry.atlas.capability_id === requirement.capability_id)).toBe(true);
      }
    }
    expect(allRows.filter((row) => row.join_basis === "map_runtime").map((row) => row.declared).sort())
      .toEqual(["course.general", "html.structure", "office.structure", "pdf.extract"]);
    expect(allRows.filter((row) => row.join_basis === "atlas_entry").map((row) => row.declared).sort())
      .toEqual(["learning.fsrs", "learning.review", "learning.state"]);
    expect(allRows.filter((row) => row.join_basis === "unbound").map((row) => row.declared).sort())
      .toEqual(["canvas.references", "document.backlinks", "document.collection", "document.local-graph", "document.reference", "document.reference", "document.save", "document.save", "document.save", "search.local"]);
    // A map_runtime row must name the entry that actually lists it — the ID is not decorative.
    for (const row of allRows.filter((item) => item.join_basis === "map_runtime")) {
      const entry = CAPABILITY_CATALOG.entries.find((item) => item.atlas.capability_id === row.capability_id)!;
      expect([...entry.implementation.runtime_capabilities]).toContain(row.declared);
      expect(runtimeNames.has(row.declared)).toBe(true);
    }
    expect(rowOf("T2", "html.structure").capability_id).toBe("CAP-0020");
    expect(rowOf("T2", "html.structure").capability_name).toBe("多格式转换");
    expect(rowOf("T3", "course.general").capability_id).toBe("CAP-0060");
  });
  it("leaves the twelve dangling names unbound instead of inventing an ID or a similar-name join", () => {
    // Red if someone "fixes" search.local into CAP-0110 or canvas.references into canvas.structure:
    // both are name inference, and the owner decision they would need is a tombstone-rule decision.
    expect(rowOf("T2", "search.local").capability_id).toBeNull();
    expect(rowOf("T2", "search.local").status).toBe("declared_no_implementation");
    expect(rowOf("T2", "search.local").missing_reason).toContain("纯声明");
    expect(rowOf("T1", "canvas.references").capability_id).toBeNull();
    // The document.* path really is served — by first-party Core commands, not by a catalog ID.
    expect(rowOf("T1", "document.save").served_by).toEqual(["document_create", "document_draft"]);
    expect(rowOf("T1", "document.save").missing_reason).toContain("document_create");
    expect(rowOf("T1", "document.save").status).toBe("declared_no_implementation");
    expect(rowOf("T1", "document.save").navigable).toBe(false);
  });
  it("reports an unresolvable ID as provider unknown rather than borrowing a neighbour", () => {
    const row = resolveRequirement({ declared: "made.up", capability_id: "CAP-9999" }, live([]));
    expect(row.status).toBe("provider_unknown");
    expect(row.availability).toBe("unlinked");
    expect(row.navigable).toBe(false);
    expect(row.missing_reason).toContain("CAP-9999");
    expect(row.provider).toContain("无提供方可述");
  });
  it("keeps an unread handshake NOT_RUN, never 可用", () => {
    // Red if the resolver defaults a missing read to an optimistic value.
    for (const row of allRows) {
      expect(["可用", "允许", "enabled"]).not.toContain(row.availability_label);
    }
    expect(rowOf("T2", "pdf.extract", NOT_READ).availability).toBe("not_read");
    expect(rowOf("T2", "pdf.extract", NOT_READ).availability_label).toBe("未读取（NOT_RUN）");
    expect(rowOf("T2", "pdf.extract", NOT_READ).status).toBe("qualified");
    expect(rowOf("T2", "pdf.extract", { state: "read_failed" }).availability_label).toBe("读取失败，显示未知");
    expect(rowOf("T2", "pdf.extract", { state: "read_failed" }).missing_reason).toContain("未知");
  });
  it("separates allowed, disabled, unhealthy, absent-from-host and no-live-surface", () => {
    // Red if one live verdict is collapsed into another: "disabled" is not "unregistered", and a
    // sibling capability's handshake row is never this row's evidence.
    expect(rowOf("T2", "html.structure", live([{ capability: "html.structure", enabled: true, health: "handshake_ready" }])).availability).toBe("allowed");
    expect(rowOf("T2", "html.structure", live([{ capability: "html.structure", enabled: false, health: "handshake_ready" }])).availability).toBe("disabled");
    expect(rowOf("T2", "html.structure", live([{ capability: "html.structure", enabled: false, health: "handshake_ready" }])).status).toBe("qualified");
    expect(rowOf("T2", "html.structure", live([{ capability: "html.structure", enabled: false }])).missing_reason).toContain("禁用");
    expect(rowOf("T2", "html.structure", live([{ capability: "html.structure", enabled: true, health: "worker_missing" }])).availability).toBe("handshake_incomplete");
    expect(rowOf("T2", "html.structure", live([{ capability: "html.structure", health: "handshake_ready" }])).availability).toBe("enabled_unknown");
    expect(rowOf("T2", "html.structure", live([{ capability: "pdf.extract", enabled: true, health: "handshake_ready" }])).availability).toBe("runtime_absent");
    expect(rowOf("T2", "html.structure", live([{ capability: "pdf.extract", enabled: true, health: "handshake_ready" }])).availability_label).toBe("本轮握手列表无此运行能力");
    // CAP-0040 is declared core_native: no worker handshake can speak for it, and reading the list
    // does not change that.
    expect(rowOf("T3", "learning.state", live([{ capability: "course.general", enabled: true, health: "handshake_ready" }])).availability).toBe("no_live_surface");
    expect(rowOf("T3", "learning.state").status).toBe("qualified");
    expect(rowOf("T3", "learning.state").provider).toContain("Core 原生实现声明");
  });
  it("lists the templates that require a capability by reading the same declarations back", () => {
    // Red if the reverse list is hand-copied or the forward binds move without it.
    expect(templatesRequiring("CAP-0020").map((item) => item.declared).sort()).toEqual(["html.structure", "office.structure", "pdf.extract"]);
    expect(templatesRequiring("CAP-0020").every((item) => item.template_id === "T2" && item.template_name === "研究与项目")).toBe(true);
    expect(templatesRequiring("CAP-0040").map((item) => item.declared).sort()).toEqual(["learning.fsrs", "learning.review", "learning.state"]);
    expect(templatesRequiring("CAP-0060").map((item) => item.declared)).toEqual(["course.general"]);
    // Nothing requires these, and the surface must say that instead of implying adoption.
    expect(templatesRequiring("CAP-0110")).toEqual([]);
    expect(templatesRequiring("CAP-0010")).toEqual([]);
  });
  it("names the joined classes, and stays unconfirmed where the crosswalk has no row", () => {
    const unjoined = absorptionClassification("CAP-0060");
    expect(unjoined.confirmed).toBe(false);
    expect(unjoined.label).toBe("分类未确认");
    expect(unjoined.sources).toEqual([]);
    // CAP-0020 is joined by the crosswalk, so the surface must stop saying 未确认 and name the
    // classes it actually has - and must not present every one of them as enable-able.
    const joined = absorptionClassification("CAP-0020");
    expect(joined.confirmed).toBe(true);
    expect(joined.label).toContain("可启停能力供体");
    expect(joined.label).toContain("吸收算法");
    expect(joined.sources.length).toBeGreaterThan(1);
    expect(joined.sources.some((row) => row.surface_class !== "enableable_plugin")).toBe(true);
    expect(joined.reason).toContain("可启停仅指");
    expect(unjoined.donor_mapping).toBe(CAPABILITY_CATALOG.donor_mapping);
    // Seven, matching the generator's closed set; the old list had six with its own ids and no
    // `not_adopted`, so the surface could name a bucket the crosswalk never emits.
    expect(unjoined.classes.map((item) => item.label)).toEqual([
      "可启停能力供体", "吸收算法", "体验供体", "格式规范", "基础依赖", "未来候选", "未采用",
    ]);
  });
});

describe("template detail renders the requirement table", () => {
  const metadata = { schema: "archeaxis.template/v1" as const, template_id: "T2", discipline_id: "computer", fields: { status: "unevaluated", 版本: "", 复杂度: "" }, references: [], learning_item_key: null };
  function doc(id: string): DocumentDto {
    return {
      document_id: id, title: id, version: 1, source_id: null, source_revision: null, content_sha256: "hash",
      editor_json: { type: "doc", attrs: { archeaxis_template: metadata }, content: [{ type: "paragraph", attrs: { block_id: "p1" }, content: [{ type: "text", text: "研究笔记" }] }] },
      text_projection: "研究笔记", blocks: [{ block_id: "p1", kind: "paragraph", ordinal: 0, node_json: {}, text_projection: "研究笔记", codec_status: "known" }],
    };
  }
  beforeEach(() => {
    api.call.mockReset();
    api.call.mockImplementation(async (operation: string) => {
      if (operation === "documents_list") return { documents: [doc("tpl")], next_cursor: null, snapshot_count: 1 };
      if (operation === "document_get" || operation === "document_version") return structuredClone(doc("tpl"));
      if (operation === "capabilities_list") return { capabilities: [{ capability: "html.structure", enabled: false, health: "handshake_ready" }] };
      throw new Error(`unexpected ${operation}`);
    });
  });

  it("keeps protocol details out of template reading while retaining the complete diagnostic record", async () => {
    resetDiagnostics();
    const view = render(<><TemplateWorkspace onOpen={vi.fn()} onOpenCapability={vi.fn()} /><DiagnosticConsole /></>);
    fireEvent.click(await screen.findByRole("button", { name: "tpl · v1" }));
    const panel = await screen.findByRole("region", { name: "模板能力需求" });
    expect(within(panel).getByRole("heading", { level: 3, name: "研究与项目 · 所需能力" })).toBeInTheDocument();
    expect(panel.textContent).not.toMatch(/Core|worker|CAP-|稳定 ID|html\.structure|pdf\.extract|NOT_RUN|handshake_ready/);
    expect(within(panel).getByRole("row", { name: /网页结构读取/ })).toHaveTextContent("已禁用");
    expect(within(panel).getByRole("row", { name: /PDF内容提取/ })).toHaveTextContent("当前应用未接入此处理服务");
    expect(within(panel).getByRole("row", { name: /本地内容检索/ })).toHaveTextContent("只有需求说明，尚未接入实际处理");
    fireEvent.click(within(panel).getByRole("button", { name: "状态与诊断：模板能力登记与运行状态" }));
    const observed = { capability: "html.structure", enabled: false, health: "handshake_ready" };
    expect(JSON.parse(view.container.querySelector(".diagnostic-console pre")!.textContent!)).toEqual({
      template: TEMPLATES.find(template => template.id === "T2"),
      requirements: resolveTemplateRequirements("T2", { state: "read", rows: new Map([["html.structure", observed]]) }),
      read: { state: "read", rows: [observed] },
    });
    resetDiagnostics();
  });

  it("shows provider, availability and missing reason per requirement, and links only what resolves", async () => {
    render(<TemplateWorkspace onOpen={vi.fn()} onOpenCapability={vi.fn()} />);
    // The saved list arrives from a read, so it has to be awaited; the sibling test below already
    // does. A synchronous getByRole here races the fetch and loses.
    fireEvent.click(await screen.findByRole("button", { name: "tpl · v1" }));
    const table = await screen.findByRole("table", { name: /研究与项目的能力需求/ });
    // The live read is what the table reports: html.structure is disabled in this host, and its
    // sibling pdf.extract is absent from the handshake list — two different sentences.
    expect(within(table).getByRole("row", { name: /网页结构读取/ }).textContent).toContain("已禁用");
    expect(within(table).getByRole("row", { name: /PDF内容提取/ }).textContent).toContain("当前应用未接入此处理服务");
    expect(within(table).getByRole("row", { name: /本地内容检索/ }).textContent).toContain("尚未关联到能力目录");
    expect(within(table).getByRole("row", { name: /Office文档结构读取/ }).textContent).toContain("多格式转换");
    // Navigable rows are exactly the resolvable ones.
    expect(within(table).getAllByRole("button", { name: /^查看.+的能力详情$/ })).toHaveLength(3);
    expect(within(table).getAllByText("尚未关联到能力目录", { selector: "span" })).toHaveLength(4);
    expect(within(table).queryByRole("button", { name: /本地内容检索/ })).toBeNull();
  });
  it.each([
    [{ enabled: true, health: "handshake_ready" }, "连接检查允许使用", "实际处理结果与质量仍需单独核对"],
    [{ enabled: true, health: "starting" }, "处理服务尚未就绪", "当前不能使用此处理步骤"],
    [{ health: "handshake_ready" }, "使用权限未知", "尚不能判断是否允许执行"],
  ])("does not promote a connection observation into a successful template task: %j", async (observation, label, reason) => {
    const previous = api.call.getMockImplementation()!;
    api.call.mockImplementation(async (operation: string, ...args: unknown[]) => operation === "capabilities_list"
      ? { capabilities: [{ capability: "html.structure", ...observation }] } : previous(operation, ...args));
    render(<TemplateWorkspace onOpen={vi.fn()} />);
    fireEvent.click(await screen.findByRole("button", { name: "tpl · v1" }));
    const row = within(await screen.findByRole("table", { name: /研究与项目的能力需求/ })).getByRole("row", { name: /网页结构读取/ });
    expect(row).toHaveTextContent("已有实现声明");
    expect(row).toHaveTextContent(label);
    expect(row).toHaveTextContent(reason);
    expect(row.textContent).not.toMatch(/已执行成功|任务已完成|handshake_ready|starting/);
  });
  it("routes a resolvable requirement into the capability detail and adds no live region", async () => {
    const onOpenCapability = vi.fn();
    const view = render(<TemplateWorkspace onOpen={vi.fn()} onOpenCapability={onOpenCapability} />);
    fireEvent.click(await screen.findByRole("button", { name: "tpl · v1" }));
    const table = await screen.findByRole("table", { name: /研究与项目的能力需求/ });
    fireEvent.click(within(table).getByRole("button", { name: "查看网页结构读取的能力详情" }));
    expect(onOpenCapability).toHaveBeenCalledWith("CAP-0020");
    // The table describes persisted declarations; the workspace owns exactly one outcome region.
    expect(view.container.querySelectorAll('[role="status"],[role="alert"],[aria-live]:not([aria-live="off"])')).toHaveLength(1);
    expect(view.container.querySelector('[role="status"]')).toHaveTextContent("");
    // Without a host route the affordance is absent rather than inert.
    view.unmount();
    const orphan = render(<TemplateWorkspace onOpen={vi.fn()} />);
    fireEvent.click(await screen.findByRole("button", { name: "tpl · v1" }));
    const second = await screen.findByRole("table", { name: /研究与项目的能力需求/ });
    expect(within(second).getAllByText("当前视图未提供能力入口")).toHaveLength(3);
    orphan.unmount();
  });

  it("keeps create, field edit and save working while every enhancement capability is unconfirmed", async () => {
    // The degradation the owner demands: a missing or disabled enhancement must not break the basic
    // document path. Red if a guard is ever put in front of create/save on capability availability.
    let saved:DocumentDto|null=null;
    function normalized(id:string,title:string,editor:unknown,version:number):DocumentDto {
      const value=structuredClone(editor) as {content:Array<{type:string;attrs?:Record<string,unknown>}>};
      value.content.forEach((node,index)=>{node.attrs={...node.attrs,block_id:node.attrs?.block_id??`generated_${index}`};});
      return {...doc(id),title,version,editor_json:value,content_sha256:"a".repeat(64),blocks:value.content.map((node,index)=>({block_id:String(node.attrs!.block_id),kind:node.type,ordinal:index,node_json:node,text_projection:"fixture",codec_status:"known"}))};
    }
    api.call.mockImplementation(async (operation: string, payload: Record<string, unknown> = {}) => {
      if (operation === "documents_list") return { documents: saved?[saved]:[], next_cursor: null, snapshot_count: saved?1:0 };
      if (operation === "document_get" || operation === "document_version") {if(!saved||saved.document_id!==payload.document_id||saved.version!==payload.version)throw new Error("not found");return structuredClone(saved);}
      if (operation === "capabilities_list") throw new Error("unavailable");
      if (operation === "document_create") {
        const body = payload.body as Record<string, unknown>;
        saved=normalized(await documentRequestIdentity(String(body.create_request_id)),body.title as string,body.editor_json,1);return structuredClone(saved);
      }
      if (operation === "document_draft") {
        saved=normalized(saved!.document_id,saved!.title,(payload.body as Record<string,unknown>).editor_json,2);return structuredClone(saved);
      }
      throw new Error(`unexpected ${operation}`);
    });
    render(<TemplateWorkspace onOpen={vi.fn()} />);
    await screen.findByText("尚无已保存的模板对象；选择学科与模板后创建第一个。");
    fireEvent.change(screen.getByLabelText("模板"), { target: { value: "T2" } });
    fireEvent.change(screen.getByLabelText("学科"), { target: { value: "statistics" } });
    fireEvent.click(screen.getByRole("button", { name: "创建学科对象" }));
    const table = await screen.findByRole("table", { name: /研究与项目的能力需求/ });
    // This fixture makes the handshake read throw, so the honest cell is "read failed", not
    // "not read" - the two are different sentences and the resolver keeps them apart.
    expect(within(table).getByRole("row", { name: /PDF内容提取/ }).textContent).toContain("读取失败，运行状态未知");
    expect(within(table).getByRole("row", { name: /本地内容检索/ }).textContent).toContain("只有需求说明，尚未接入实际处理");
    fireEvent.change(await screen.findByLabelText("样本"), { target: { value: "n=12" } });
    fireEvent.click(screen.getByRole("button", { name: "保存模板属性与关系" }));
    await screen.findByText(/模板对象与属性已保存并完整读回/);
    expect(api.call.mock.calls.map(([operation]) => operation)).toEqual(expect.arrayContaining(["document_create", "document_draft"]));
    const draft = api.call.mock.calls.find(([operation]) => operation === "document_draft")?.[1] as { body: { editor_json: { attrs: { archeaxis_template: { fields: Record<string, string> } } } } };
    expect(draft.body.editor_json.attrs.archeaxis_template.fields.样本).toBe("n=12");
    // The failed handshake read never becomes a claim about the save, and no worker/job was tried.
    expect(new Set(api.call.mock.calls.map(([operation]) => operation))).toEqual(new Set(["documents_list", "capabilities_list", "document_create", "document_draft", "document_version"]));
  });
});

describe("capability detail is the plugin side of the same join", () => {
  beforeEach(() => {
    api.call.mockReset();
    api.call.mockImplementation(async(operation:string,payload:{body:{scope:string;operations:readonly string[]}})=>{expect(operation).toBe("operation_readiness");return scopedReadiness(payload.body);});
  });
  it("lists the templates that require the selected capability and offers one real route", async () => {
    const onNavigate = vi.fn();
    render(<CanonicalCapabilitiesSpace onNavigate={onNavigate} />);
    expect(api.call).not.toHaveBeenCalled();
    await userEvent.setup().click(screen.getByRole("button", { name: /多格式转换/ }));
    await screen.findByText(/已读取当前视图的范围化状态/);
    const detail = screen.getByRole("article", { name: "能力详情" });
    expect(within(detail).getByRole("heading", { name: "使用此能力的模板" })).toBeInTheDocument();
    expect(detail.textContent).toContain("研究与项目");
    expect(detail.textContent).toContain("Office文档结构读取");
    expect(detail.textContent).not.toContain("office.structure");
    expect(detail.textContent).not.toContain("知识网络");
    await userEvent.setup().click(screen.getByRole("button", { name: "到资料库打开学科模板" }));
    expect(onNavigate).toHaveBeenCalledWith("library");
  });
  it("says plainly when no template requires the capability, and offers no dead route", async () => {
    render(<CanonicalCapabilitiesSpace onNavigate={vi.fn()} />);
    expect(api.call).not.toHaveBeenCalled();
    await userEvent.setup().click(screen.getByRole("button", { name: /搜索、图谱与索引/ }));
    const detail = screen.getByRole("article", { name: "能力详情" });
    expect(detail.textContent).toContain("模板套件当前没有声明此能力");
    expect(screen.queryByRole("button", { name: "到资料库打开学科模板" })).toBeNull();
  });
  it("shows each joined absorption source with its own class, and does not call them all plugins", async () => {
    render(<CanonicalCapabilitiesSpace onNavigate={vi.fn()} />);
    expect(api.call).not.toHaveBeenCalled();
    await userEvent.setup().click(screen.getByRole("button", { name: /多格式转换/ }));
    await screen.findByText(/已读取当前视图的范围化状态/);
    const detail = screen.getByRole("article", { name: "能力详情" });
    // The class now comes from the generated crosswalk projection, so a joined capability names its
    // sources instead of hiding behind 分类未确认.
    expect(detail.textContent).toContain("吸收来源分类：");
    expect(detail.textContent).toContain("faster-whisper");
    expect(detail.textContent).toContain("类别：吸收算法");
    expect(detail.textContent).toContain("跨词汇表分歧");
    expect(detail.textContent).not.toContain("分类未确认");
    // Displaying a donor is not the same as offering to switch it on.
    expect(detail.textContent).not.toMatch(/已吸收自|来源插件已启用/);
  });
  it("still says 分类未确认 for a capability the crosswalk does not join", async () => {
    render(<CanonicalCapabilitiesSpace onNavigate={vi.fn()} />);
    expect(api.call).not.toHaveBeenCalled();
    await userEvent.setup().click(screen.getByRole("button", { name: /LER 视觉教学与课件/ }));
    const detail = screen.getByRole("article", { name: "能力详情" });
    expect(detail.textContent).toContain("吸收来源分类：分类未确认");
    expect(detail.textContent).toContain("候选类别为");
  });
});

describe("template surface reaches the capability route through the shell", () => {
  it("opens the capability detail from a template requirement row in the library", async () => {
    // Red if CanonicalLibrarySpace stops forwarding the capability route to the launcher.
    const onOpenCapability = vi.fn();
    api.call.mockImplementation(async (operation: string) => {
      if (operation === "sources_list") return { sources: [] };
      if (operation === "documents_list") return { documents: [], next_cursor: null, snapshot_count: 0 };
      if (operation === "capabilities_list") return { capabilities: [{ capability: "course.general", enabled: true, health: "handshake_ready" }] };
      throw new Error(`unexpected ${operation}`);
    });
    render(<CanonicalLibrarySpace onOpenCapability={onOpenCapability} />);
    await openLauncher();
    const table = await screen.findByRole("table", { name: /知识网络的能力需求/ });
    fireEvent.change(screen.getByLabelText("模板"), { target: { value: "T3" } });
    expect(within(table).getByRole("row", { name: /通用课程/ }).textContent).toContain("连接检查允许使用");
    fireEvent.click(within(table).getByRole("button", { name: "查看通用课程的能力详情" }));
    expect(onOpenCapability).toHaveBeenCalledWith("CAP-0060");
  });
});

describe("app shell wiring of the template→capability route", () => {
  it("moves from a template requirement row to the capability detail and writes the hash route", async () => {
    const previous=api.call.getMockImplementation()!;
    api.call.mockImplementation(async(operation:string,payload:Record<string,unknown>={})=>operation==="ui_state_read"?{schema:"archeaxis.ui-working-state/v1",workspace_id:"a".repeat(32),restore_epoch:"initial",state_revision:0,state:{drafts:{},opened_documents:[],active_document:null,page_id:null,pending_original:null},draft_digests:{},pending_document_id:null,recovery_candidates:null,recovery_requires_confirmation:false}:previous(operation,payload));
    window.__TAURI__ = { core: { invoke: vi.fn(async (command: string, args?: Record<string, unknown>) => {
      if (command === "recovery_status") return { state: "ready", safe_mode: false, backend_available: true, message: "已就绪", backups: [], external_dev: false };
      if (command !== "core_command") throw new Error(`unexpected command ${command}`);
      const operation = (args?.request as Record<string, unknown>).operation;
      if (operation === "system_version") return { status: 200, body: { runtime: "archeaxis-api", contract: "0.1.0-outline", schema_version: 7, sqlite_version: "3.51.3" } };
      if (operation === "learning_items") return {status:200,body:{items:[],count:0}};
      if (operation === "sources_list") return { status: 200, body: { sources: [] } };
      if (operation === "documents_list") return { status: 200, body: { documents: [],next_cursor:null,snapshot_count:0 } };
      if (operation === "capabilities_list") return { status: 200, body: { capabilities: [] } };
      throw new Error(`unexpected operation ${operation}`);
    }) } };
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/api/v1/system/handshake")) return { ok: true, status: 200, json: async () => ({ product_id: "archeaxis-workspace", product_name: "ArcheAxis Knowledge", api_contract: "1.x", backend_version: "0.6.11", source_commit: "abc1234", schema_version: 15, runtime_mode: "desktop", workspace_id: "workspace-1", capabilities: [], migration_state: "ready" }) } as Response;
      if (url.endsWith("/workspace/api/status")) return { ok: true, status: 200, json: async () => ({ schema_version: "v1", observed_at: "2026-08-29T00:00:00Z", release: { version: "0.6.11", status: "candidate", public: false }, components: {}, migrations: {}, counts: {}, capabilities: {} }) } as Response;
      if (url.endsWith("/workspace/api/v1/home")) return { ok: true, status: 200, json: async () => ({ release: { version: "0.6.11", status: "candidate", public: false }, counts: {}, capabilities: {}, components: {}, recent_activity: [] }) } as Response;
      if (url.includes("/workspace/api/v1/activity")) return { ok: true, status: 200, json: async () => ({ items: [], next_cursor: null }) } as Response;
      if (url.endsWith("/workspace/api/delivery")) return { ok: true, status: 200, json: async () => ({ summary: { jobs: 0, outbox: {}, receipts: {} } }) } as Response;
      throw new Error(`unexpected URL ${url}`);
    }));
    try {
      window.location.hash = "#space=library";
      render(<App />);
      await openLauncher();
      const table = await screen.findByRole("table", { name: /知识网络的能力需求/ });
      expect(within(table).getAllByText("尚未关联到能力目录", { selector: "span" })).toHaveLength(5);
      fireEvent.change(screen.getByLabelText("模板"), { target: { value: "T2" } });
      fireEvent.click(await screen.findByRole("button", { name: "查看网页结构读取的能力详情" }));
      expect(await screen.findByRole("heading", { name: "能力中心" })).toBeInTheDocument();
      expect(screen.getByRole("article", { name: "能力详情" })).toHaveTextContent("多格式转换");
      expect(screen.getByRole("article", { name: "能力详情" })).not.toHaveTextContent("稳定入口 ID CAP-0020");
      expect(window.location.hash).toBe("#capability/CAP-0020");
    } finally {
      delete window.__TAURI__;
      vi.unstubAllGlobals();
      resetRuntimeClient();
      window.location.hash = "";
    }
  });
});

// These shell/guard tests isolate onboarding; FirstUseGuideApp and FirstUseGuide test it directly.
vi.mock("../components/FirstUseGuide", async importOriginal => ({ ...await importOriginal<object>(), FirstUseGuide: () => null, requestFirstUseGuide: vi.fn() }));
