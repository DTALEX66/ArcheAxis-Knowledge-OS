// 只决定提示文案；实际键盘监听继续同时支持 Control 和 Meta。
export function commandKeyLabel(platform = typeof navigator === "undefined" ? "" : navigator.platform): string {
  return /Mac|iPhone|iPad|iPod/i.test(platform) ? "⌘" : "Ctrl";
}
