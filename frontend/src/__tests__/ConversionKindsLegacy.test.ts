import { describe, expect, it } from "vitest";
import { conversionKindFor, legacyOfficeRequirementFor } from "../api/conversionKinds";
describe("Legacy Office request kinds do not imply runtime qualification", () => {
  it.each(["saved.doc", "saved.DOC", "sheet.xls", "slide.ppt"])("maps Core-supported %s to Office with unmet engine requirement", name => {
    expect(conversionKindFor(name)).toBe("office");
    expect(legacyOfficeRequirementFor(name)).toMatchObject({ capability: "office.structure", qualification: "DECLARATION_ONLY", requires_actual_result: true });
    expect(legacyOfficeRequirementFor(name)?.engine_requirement).toBeTruthy();
  });
  it("does not widen unsupported formats or conflate OOXML prerequisite", () => {
    expect(conversionKindFor("saved.qzx")).toBeNull();
    expect(legacyOfficeRequirementFor("saved.docx")).toBeNull();
    expect(legacyOfficeRequirementFor("saved.doc.exe")).toBeNull();
  });
});
