import { expect, it } from "vitest";
import { render } from "@testing-library/react";
import { auditAriaLabels, auditColorContrast } from "../test/accessibility";

it("does not mistake a text input value for its accessible name",()=>{
 const {container}=render(<input defaultValue="private draft"/>);expect(auditAriaLabels(container)).toHaveLength(1);
});
it("recognizes a real wrapping label but rejects a broken labelledby reference",()=>{
 const {container,rerender}=render(<label>模型名称<input/></label>);expect(auditAriaLabels(container)).toHaveLength(0);
 rerender(<input aria-labelledby="missing"/>);expect(auditAriaLabels(container)).toHaveLength(1);
});
it("requires normal text contrast for 18px text and uses 24px for large text",()=>{
 const {container,rerender}=render(<p style={{color:"rgb(119, 119, 119)",backgroundColor:"rgb(255, 255, 255)",fontSize:18}}>readable text</p>);
 expect(auditColorContrast(container).filter(i=>i.severity==="error")).toHaveLength(1);
 rerender(<p style={{color:"rgb(119, 119, 119)",backgroundColor:"rgb(255, 255, 255)",fontSize:24}}>large text</p>);expect(auditColorContrast(container).filter(i=>i.severity==="error")).toHaveLength(0);
});
it("reports translucent contrast as unevaluated instead of assuming a passing 21:1",()=>{
 const {container}=render(<p style={{color:"rgba(0, 0, 0, 0.1)",backgroundColor:"rgb(255, 255, 255)"}}>translucent</p>);
 expect(auditColorContrast(container).some(i=>i.severity==="info"&&i.issue.includes("not evaluated"))).toBe(true);
});
