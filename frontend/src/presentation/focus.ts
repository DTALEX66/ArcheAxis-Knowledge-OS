/** Restore focus only to a current, visible surface; parked workspace views are ineligible. */
export function focusVisibleTarget(preferred: HTMLElement | null, fallback: HTMLElement | null): void {
  const usable = (element: HTMLElement | null): element is HTMLElement => {
    if (!element?.isConnected || element.closest('[hidden],[inert],[aria-hidden="true"]') || element.matches(':disabled')) return false;
    for (let node: HTMLElement | null = element; node; node = node.parentElement) {
      const style = getComputedStyle(node);
      if (style.display === "none" || style.visibility === "hidden" || style.visibility === "collapse") return false;
    }
    return true;
  };
  if (usable(preferred)) preferred.focus();
  else if (usable(fallback)) fallback.focus();
}
