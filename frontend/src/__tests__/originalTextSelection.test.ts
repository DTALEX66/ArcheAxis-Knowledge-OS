import {describe,expect,it} from "vitest";
import {originalTextSelection} from "../presentation/originalTextSelection";
describe("immutable UTF-8 original selection",()=>{
 it("maps Chinese and non-BMP characters to exact bytes without normalizing CRLF or BOM",()=>{
  const text="\uFEFF甲\r\n😀乙",bytes=new TextEncoder().encode(text),start=text.indexOf("😀");
  const selected=originalTextSelection(bytes,start,start+2);
  expect(selected.start).toBe(8);expect(selected.end).toBe(12);expect(selected.quote).toBe("😀");expect(Array.from(selected.bytes)).toEqual(Array.from(new TextEncoder().encode("😀")));
 });
 it("rejects partial surrogate, empty range and invalid UTF-8",()=>{
  const bytes=new TextEncoder().encode("甲😀乙");
  for(const [start,end] of [[1,2],[2,3],[0,0],[-1,2],[0,99]])expect(()=>originalTextSelection(bytes,start,end)).toThrow();
  expect(()=>originalTextSelection(new Uint8Array([255]),0,1)).toThrow();
 });
});
