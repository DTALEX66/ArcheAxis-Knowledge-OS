export type FrontendFailureKind = "event" | "async";

/** Report only the event class. Never read message, stack, URL or rejection reason. */
export function installFrontendFailureListener(report: (kind: FrontendFailureKind) => void) {
  const error = (event: Event) => {
    // Resource loading errors have their own page-level feedback.
    if (event instanceof ErrorEvent) report("event");
  };
  const rejection = () => report("async");
  window.addEventListener("error", error);
  window.addEventListener("unhandledrejection", rejection);
  return () => {
    window.removeEventListener("error", error);
    window.removeEventListener("unhandledrejection", rejection);
  };
}
