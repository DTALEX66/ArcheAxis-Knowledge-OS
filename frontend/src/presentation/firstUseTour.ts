import { driver, type Driver } from "driver.js";
import "driver.js/dist/driver.css";

const stages: readonly { page: string; selector: string; prepare?: string; title: string; description: string; next: string }[] = [
  { page: "16", prepare: '[data-guide="import-originals-tab"]', selector: '[data-guide="first-original"]', title: "1 / 3 · 导入一份资料", description: "在这里选择本地文件。原件保存后，查看实际处理状态；阅读、保存和后续学习不需要先连接模型。", next: "去阅读页" },
  { page: "03", selector: '[data-stitch-library="reader"] [data-guide="saved-documents"], .stitch-reader-document, .stitch-reader-empty', title: "2 / 3 · 打开内容", description: "从已保存文档中打开阅读。空工作区可先新建原创笔记；导入原件与完成文字识别是两个步骤。", next: "看保存位置" },
  { page: "03", selector: '[data-guide="document-save"], [data-guide="new-note"]', title: "3 / 3 · 写下并保存", description: "打开文档后，在正文中编辑并保存草稿；空工作区可先点新建原创笔记。保存后核对页面状态。关闭提示不会替你执行或确认保存。", next: "结束操作提示" },
] as const;

/** Presentation only: navigation uses the existing draft guard; no business commands. */
export function beginFirstUseTour(onPage: (page: string) => boolean | void, onUnavailable: (message: string) => void) {
  let active: Driver | null = null;
  let stopped = false;
  let cancelWait: (() => void) | undefined;
  let watch: MutationObserver | undefined;
  const previousFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null;
  function stop() {
    stopped = true; cancelWait?.(); watch?.disconnect();
    const old = active; active = null; old?.destroy();
    if (previousFocus?.isConnected && !document.querySelector('.aaos-dialog-content,[role="alertdialog"],dialog[open]')) previousFocus.focus();
  }
  function unavailable(message: string) { stop(); onUnavailable(message); }
  function target(selector: string): Promise<HTMLElement | null> {
    return new Promise(resolve => {
      let settled = false;
      const finish = (value: HTMLElement | null) => {
        if (settled) return;
        settled = true; observer.disconnect(); window.clearTimeout(timer); cancelWait = undefined; resolve(value);
      };
      const find = () => {
        if (stopped) { finish(null); return; }
        if (document.querySelector('.aaos-dialog-content,[role="alertdialog"],dialog[open]')) return;
        const element = Array.from(document.querySelectorAll<HTMLElement>(selector)).find(value =>
          !value.closest('[hidden],[aria-hidden="true"],[inert]') && value.getClientRects().length > 0);
        if (element) finish(element);
      };
      const observer = new MutationObserver(find);
      const timer = window.setTimeout(() => finish(null), 3000);
      cancelWait = () => finish(null);
      observer.observe(document.body, { childList: true, subtree: true, attributes: true }); find();
    });
  }
  async function show(index: number) {
    const stage = stages[index];
    if (stopped) return;
    try {
      if (index < 2 && onPage(stage.page) === false) {
        unavailable("页面尚未切换。请先处理当前草稿或操作，再继续引导。"); return;
      }
      if (stage.prepare) {
        const tab = await target(stage.prepare);
        if (stopped) return;
        if (!tab) { unavailable("导入区域暂未出现。请从导入导出页选择原件与转换，再继续引导；原进度已保留。"); return; }
        // Use the existing presentation action after guarded navigation. Retained
        // export/teaching sessions stay mounted; no import/save is performed.
        if (tab.getAttribute("aria-pressed") !== "true") tab.click();
      }
      const element = await target(stage.selector);
      if (stopped) return;
      if (!element) { unavailable("操作控件暂未出现。请先打开一份文档或新建笔记，再从使用引导继续；原进度已保留。"); return; }
      const instance = driver({
        animate: false, smoothScroll: false, allowClose: true, allowKeyboardControl: true,
        disableActiveInteraction: false, overlayClickBehavior: "close", overlayOpacity: .4,
        popoverClass: "aaos-first-use-tour", closeBtnLabel: "暂停操作提示", showButtons: ["next", "close"],
        onDestroyed: () => { if (active === instance) { active = null; stop(); } },
      });
      active = instance;
      instance.highlight({ element, popover: {
        // highlight() suppresses config-level buttons; this popover must opt in.
        showButtons: ["next", "close"],
        title: stage.title, description: stage.description, nextBtnText: stage.next, doneBtnText: stage.next,
        onNextClick: () => {
          watch?.disconnect(); active = null; instance.destroy();
          if (index === stages.length - 1) stop(); else void show(index + 1);
        },
        onDoneClick: () => {
          watch?.disconnect(); active = null; instance.destroy();
          if (index === stages.length - 1) stop(); else void show(index + 1);
        },
      } });
      watch = new MutationObserver(() => {
        if (!element.isConnected || element.closest('[hidden],[aria-hidden="true"],[inert]') ||
          document.querySelector('.aaos-dialog-content,[role="alertdialog"],dialog[open]')) stop();
      });
      watch.observe(document.body, { childList: true, subtree: true, attributes: true });
    } catch { if (!stopped) unavailable("操作提示暂未打开，完整引导和已有进度仍可继续使用。"); }
  }
  void show(0);
  return stop;
}
