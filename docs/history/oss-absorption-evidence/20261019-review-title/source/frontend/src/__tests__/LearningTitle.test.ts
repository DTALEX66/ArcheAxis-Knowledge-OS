import {expect,it} from "vitest";
import {learningTitle} from "../presentation/learningTitle";

it.each([
  [undefined,"学习项目"],
  [null,"学习项目"],
  ["\n \t\n\u0000","学习项目"],
  ["\n 固定\t 摘要\u0000 内容\n不要取第二行","固定 摘要 内容"],
  ["\u0085标题\u0085摘要","标题 摘要"],
  ["星🛰".repeat(50),"星🛰".repeat(40)],
] as const)("keeps the Core-equivalent display-only title for %s",(value,expected)=>{
  expect(learningTitle(value)).toBe(expected);
});
it("uses a verified course title before its fixed assessment, with an empty-title fallback",()=>{
  expect(learningTitle("课程原标题","固定题面")).toBe("课程原标题");
  expect(learningTitle(" \n\t ","固定题面")).toBe("固定题面");
});
