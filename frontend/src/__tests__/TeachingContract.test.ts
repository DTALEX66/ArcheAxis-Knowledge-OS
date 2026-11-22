import { expect, it } from "vitest";
import { assertTeachingDto } from "../api/generated/teaching-contract";
import { assertUiWorkingState } from "../api/generated/ui-working-state-contract";
const record = () => ({schema:"archeaxis.teaching-record/v2",record_id:"_id",kind:"feedback",knowledge_id:"knowledge_v1",knowledge_version:"knowledge_v1",course_id:null,parent_id:"delivery",purpose:"专业依据审阅",scope:"manual_exchange",privacy:"authorized_export",content:"原文",feedback_class:"professional_basis",assessment_id:null,rubric_version:null,assisted:false,producer_kind:"external_material"});
it("accepts explicit professional basis independently of retained fidelity and actor claims",()=>{
  expect(assertTeachingDto("TeachingRecord",record())).toEqual(record());
  expect(assertTeachingDto("TeachingRecord",{...record(),feedback_class:"evidence_fidelity"})).toBeTruthy();
  expect(()=>assertTeachingDto("TeachingRecord",{...record(),actor:"human"})).toThrow();
});
it("enforces UTF8 bytes rather than Javascript string length",()=>{
  expect(()=>assertTeachingDto("TeachingRecord",{...record(),purpose:"中".repeat(171)})).toThrow();
  expect(assertTeachingDto("TeachingRecord",{...record(),purpose:"中".repeat(170)})).toBeTruthy();
});
it("accepts the optional version observation in both teaching record readers", () => {
  const view = { record: record(), content_sha256: "a".repeat(64), withdrawn: false, scoring_status: "not_scored" };
  const state = {
    knowledge_id: "knowledge_v1", status: "accepted", active: false, currentness: "superseded",
    superseded_by: "knowledge_v2", successor_count: 1, valid_to: null,
  };
  for (const read of [assertTeachingDto, assertUiWorkingState]) {
    expect(read("RecordView", view)).toEqual(view);
    expect(read("RecordView", { ...view, knowledge_state: state })).toBeTruthy();
    expect(() => read("RecordView", { ...view, knowledge_state: { ...state, active: "false" } })).toThrow();
  }
});
it("preserves optional input and explicit nullable response without accepting paths or mixed versions",()=>{
  const input = record() as Record<string,unknown>;delete input.course_id;delete input.assessment_id;delete input.rubric_version;
  expect(assertTeachingDto("TeachingRecordInput",input)).toBeTruthy();
  expect(()=>assertTeachingDto("TeachingRecord",input)).toThrow();
  for (const patch of [{record_id:"../id"},{record_id:".."},{knowledge_version:"other_version"},{kind:"delivery",feedback_class:"professional_basis"}]) {
    expect(()=>assertTeachingDto("TeachingRecord",{...record(),...patch})).toThrow();
  }
});
