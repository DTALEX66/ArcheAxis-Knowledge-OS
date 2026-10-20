/**
 * Accessibility audit utilities
 * Provides tools for checking ARIA labels, keyboard navigation, and color contrast
 */

export type AccessibilityIssue = {
  severity: "error" | "warning" | "info";
  element: string;
  issue: string;
  recommendation: string;
};

/**
 * Check for missing ARIA labels on interactive elements
 */
export function auditAriaLabels(container: HTMLElement): AccessibilityIssue[] {
  const issues: AccessibilityIssue[] = [];
  const interactiveSelectors = ["button", "a", "input", "select", "textarea", "[role='button']"];

  interactiveSelectors.forEach((selector) => {
    const elements = container.querySelectorAll(selector);
    elements.forEach((el) => {
      const labelledBy = (el.getAttribute("aria-labelledby") ?? "").split(/\s+/).filter(Boolean).map(id=>el.ownerDocument.getElementById(id)?.textContent?.trim() ?? "").join("");
      const labels = Array.from((el as HTMLInputElement).labels ?? []).map(label=>label.textContent?.trim()).join("");
      const buttonValue = el.tagName==="INPUT" && ["button","submit","reset"].includes((el as HTMLInputElement).type) ? (el as HTMLInputElement).value : "";
      const hasLabel =
        el.getAttribute("aria-label")?.trim() ||
        labelledBy || labels || buttonValue ||
        el.textContent?.trim() ||
        el.getAttribute("title");

      if (!hasLabel) {
        issues.push({
          severity: "error",
          element: selector,
          issue: "Interactive element missing accessible label",
          recommendation: "Add aria-label or visible text content",
        });
      }
    });
  });

  return issues;
}

/**
 * Check keyboard navigation support
 */
export function auditKeyboardNavigation(container: HTMLElement): AccessibilityIssue[] {
  const issues: AccessibilityIssue[] = [];
  const focusableElements = container.querySelectorAll(
    'button, a, input, select, textarea, [tabindex]:not([tabindex="-1"])'
  );

  focusableElements.forEach((el) => {
    const tabIndex = el.getAttribute("tabindex");
    if (tabIndex && parseInt(tabIndex) > 0) {
      issues.push({
        severity: "warning",
        element: el.tagName.toLowerCase(),
        issue: "Positive tabindex disrupts natural tab order",
        recommendation: "Use tabindex='0' or remove tabindex",
      });
    }

    // Check if element is visible but not focusable
    const style = window.getComputedStyle(el);
    if (style.display !== "none" && style.visibility !== "hidden") {
      const isFocusable = el.getAttribute("tabindex") !== "-1";
      if (!isFocusable && el.tagName !== "INPUT") {
        issues.push({
          severity: "info",
          element: el.tagName.toLowerCase(),
          issue: "Interactive element not in tab order",
          recommendation: "Ensure element is keyboard accessible",
        });
      }
    }
  });

  return issues;
}

/**
 * Check color contrast (simplified check)
 */
export function auditColorContrast(container: HTMLElement): AccessibilityIssue[] {
  const issues: AccessibilityIssue[] = [];
  const textElements = container.querySelectorAll("p, span, div, label, button, a");

  textElements.forEach((el) => {
    const style = window.getComputedStyle(el);
    const color = style.color;
    const bgColor = style.backgroundColor;

    // Only check if we have both colors
    if (color && bgColor && bgColor !== "rgba(0, 0, 0, 0)") {
      const ratio = getContrastRatio(color, bgColor);
      if(ratio===null){issues.push({severity:"info",element:el.tagName.toLowerCase(),issue:"Contrast not evaluated: unresolved or translucent color",recommendation:"Measure composited colors in the actual browser/theme"});return;}

      // WCAG AA requires 4.5:1 for normal text, 3:1 for large text
      const fontSize = parseFloat(style.fontSize);
      const bold = style.fontWeight === "bold" || Number(style.fontWeight)>=700;
      const isLargeText = fontSize >= 24 || (fontSize >= 18.6667 && bold);
      const requiredRatio = isLargeText ? 3 : 4.5;

      if (ratio < requiredRatio) {
        issues.push({
          severity: "error",
          element: el.tagName.toLowerCase(),
          issue: `Insufficient contrast ratio ${ratio.toFixed(2)}:1 (required ${requiredRatio}:1)`,
          recommendation: "Increase color contrast between text and background",
        });
      }
    }
  });

  return issues;
}

/**
 * Calculate relative luminance
 */
function getLuminance(r: number, g: number, b: number): number {
  const [rs, gs, bs] = [r, g, b].map((c) => {
    c = c / 255;
    return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
  });
  return 0.2126 * rs + 0.7152 * gs + 0.0722 * bs;
}

/**
 * Calculate contrast ratio between two colors
 */
function getContrastRatio(color1: string, color2: string): number | null {
  const rgb1 = parseColor(color1);
  const rgb2 = parseColor(color2);

  if (!rgb1 || !rgb2) return null;

  const l1 = getLuminance(rgb1.r, rgb1.g, rgb1.b);
  const l2 = getLuminance(rgb2.r, rgb2.g, rgb2.b);

  const lighter = Math.max(l1, l2);
  const darker = Math.min(l1, l2);

  return (lighter + 0.05) / (darker + 0.05);
}

/**
 * Parse CSS color to RGB
 */
function parseColor(color: string): { r: number; g: number; b: number } | null {
  const rgb = color.match(/^rgba?\((\d+),\s*(\d+),\s*(\d+)(?:,\s*([\d.]+))?\)$/);
  if (rgb) {
    if(rgb[4]!==undefined&&Number(rgb[4])!==1)return null;
    return {
      r: parseInt(rgb[1]),
      g: parseInt(rgb[2]),
      b: parseInt(rgb[3]),
    };
  }
  return null;
}

/**
 * Run scoped DOM checks. These do not establish full WCAG or installed-runtime qualification.
 */
export function runAccessibilityAudit(container: HTMLElement): {
  errors: AccessibilityIssue[];
  warnings: AccessibilityIssue[];
  info: AccessibilityIssue[];
} {
  const allIssues = [
    ...auditAriaLabels(container),
    ...auditKeyboardNavigation(container),
    ...auditColorContrast(container),
  ];

  return {
    errors: allIssues.filter((i) => i.severity === "error"),
    warnings: allIssues.filter((i) => i.severity === "warning"),
    info: allIssues.filter((i) => i.severity === "info"),
  };
}
