import { expect, it } from "vitest";
import { compactIdentity, displayTitle, localDateTime } from "../presentation/display";

it("displays equivalent ISO instants consistently without exposing raw ISO", () => {
  const value = "2026-10-27T06:35:12.000Z";
  const text = localDateTime(value);
  expect(text).toBe(localDateTime("2026-10-27T14:35:12+08:00"));
  expect(text).toContain("2026");
  expect(text).not.toContain("T06:35");
  expect(value).toBe("2026-10-27T06:35:12.000Z");
});

it("keeps a date-only value on its calendar day and handles missing/invalid/ambiguous times", () => {
  expect(localDateTime("2026-10-27")).toMatch(/2026.*10.*27/);
  expect(localDateTime(null)).toBe("时间未记录");
  expect(localDateTime("")).toBe("时间未记录");
  for (const value of ["bad", "2026-02-30", "2026-02-30T06:35:12Z", "2026-10-27T06:35:12", "2026-99-99T06:35:12Z"]) expect(localDateTime(value)).toBe("时间待核对");
});

it("shortens long identity labels only and uses human-readable empty-title fallbacks", () => {
  const id = "knowledge_" + "x".repeat(70) + "_tail12";
  expect(compactIdentity(id)).toBe("knowledg…tail12");
  expect(id).toHaveLength(87);
  expect(compactIdentity("doc_123")).toBe("doc_123");
  expect(compactIdentity(undefined)).toBe("编号未记录");
  expect(displayTitle("  ")).toBe("未命名文档");
  expect(displayTitle(null,"未命名知识")).toBe("未命名知识");
  expect(displayTitle(" 原标题 ")).toBe("原标题");
});
