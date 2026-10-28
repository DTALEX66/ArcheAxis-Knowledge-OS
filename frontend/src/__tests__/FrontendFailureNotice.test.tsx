import {StrictMode} from "react";
import {afterEach, expect, it} from "vitest";
import {act, cleanup, fireEvent, render, screen} from "@testing-library/react";
import {FrontendFailureNotice} from "../components/FrontendFailureNotice";
import {DiagnosticConsole} from "../components/DiagnosticConsole";
import {resetDiagnostics} from "../presentation/diagnostics";

afterEach(() => {cleanup(); resetDiagnostics();});
it("keeps drafts and focus without exposing errors, opening dialogs or replaying writes", () => {
  render(<StrictMode><textarea aria-label="草稿" defaultValue="尚未保存"/><FrontendFailureNotice/><DiagnosticConsole/></StrictMode>);
  const draft = screen.getByRole("textbox"); draft.focus();
  act(() => {window.dispatchEvent(new ErrorEvent("error", {message:"SECRET_PATH", error:new Error("SECRET_BODY")}));});
  expect(draft).toHaveFocus();
  expect(draft).toHaveValue("尚未保存");
  expect(screen.getByRole("status")).toHaveTextContent("尚未确认");
  expect(screen.queryByRole("dialog")).toBeNull();
  expect(document.body).not.toHaveTextContent("SECRET_");
  fireEvent.click(screen.getByRole("button", {name:"查看问题记录"}));
  expect(screen.getByText(/"kind": "event"/)).toBeInTheDocument();
  expect(document.body).not.toHaveTextContent("SECRET_");
  fireEvent.click(screen.getByRole("button", {name:"关闭提示"}));
  expect(screen.queryByRole("status")).toBeNull();
  expect(draft).toHaveValue("尚未保存");
});
it("handles rejection without reading its reason and removes listeners on unmount", () => {
  const {unmount} = render(<FrontendFailureNotice/>);
  const rejection = new Event("unhandledrejection");
  Object.defineProperty(rejection, "reason", {get() {throw new Error("must not read");}});
  act(() => {window.dispatchEvent(rejection);});
  expect(screen.getByRole("status")).toBeInTheDocument();
  unmount();
  act(() => {window.dispatchEvent(rejection);});
  render(<FrontendFailureNotice/>);
  expect(screen.queryByRole("status")).toBeNull();
});
