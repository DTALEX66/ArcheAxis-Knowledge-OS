import {render,screen,cleanup} from "@testing-library/react";
import {afterEach,describe,it,expect} from "vitest";
import {ModelTaskRoles} from "../components/ModelTaskRoles";
afterEach(cleanup);
describe("task roles use evidence boundaries",()=>{
 it("does not turn failed registry observation into availability",()=>{
  render(<ModelTaskRoles capabilities={null}/>);
  expect(screen.getByText("当前工具状态未知")).toBeInTheDocument();
  expect(screen.getByText("本地回答路由未确认")).toBeInTheDocument();
  expect(screen.getByText(/供应商真实接通状态未知/)).toBeInTheDocument();
 });
 it("retains disabled local execution and separates registration from inference",()=>{
  render(<ModelTaskRoles capabilities={new Map([["machine.answer",{enabled:false}],["text.extract",{}]])}/>);
  expect(screen.getByText("本地回答路由已禁用")).toBeInTheDocument();
  expect(screen.getByText(/登记 1 项转换路由；登记不代表产物已验证/)).toBeInTheDocument();
  expect(screen.getByText(/最终采用由用户决定/)).toBeInTheDocument();
 });
});
