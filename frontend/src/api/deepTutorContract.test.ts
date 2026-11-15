import { afterEach, describe, expect, it, vi } from "vitest";
import { assertCoreDto } from "./generated/core-contract";
import { coreCommand } from "./core";
vi.mock("../presentation/diagnostics", () => ({beginDiagnosticObservation:vi.fn(),recordDiagnosticFailure:vi.fn()}));
afterEach(() => { delete window.__TAURI__; });

const material = { document_id: "doc_material", version: 1, content_sha256: "a".repeat(64) };
const document = { ...material, source_id: null, source_revision: null, title: "材料", editor_json: { type: "doc", content: [] }, text_projection: "", blocks: [] };
const safety = { human_review_required: true, active_content_executed: false, rendering_authorized: false };

describe("new DeepTutor host DTO boundary", () => {
  it("binds generation to a finite version and rejects stale or unbounded requests", () => {
    const request = { create_request_id: "turn_1", material, requirement: "理解材料" };
    expect(assertCoreDto("DeepTutorQuestionTurnRequestDto", request)).toEqual(request);
    for (const invalid of [{...request, url:"https://example.invalid"}, {...request, material:{...material,version:0}}, {...request, requirement:"x".repeat(8001)}]) {
      expect(() => assertCoreDto("DeepTutorQuestionTurnRequestDto", invalid)).toThrow("CORE_DTO_INVALID");
    }
  });
  it("does not accept a generated candidate with execution or review claims changed", () => {
    const receipt = { schema:"archeaxis.deeptutor-question-turn-persistence/v1", document, material,
      question:{question_id:"q1",question:"问题",question_type:"choice",options:{A:"一",B:"二",C:"三",D:"四"}},
      candidate_document_status:"current", generation_route:"deeptutor_question_turn_local_model",
      answer_secrecy:"not_established",response_origin:"LOCAL_MODEL_UNVERIFIED",...safety };
    expect(assertCoreDto("DeepTutorQuestionTurnReceiptDto",receipt)).toEqual(receipt);
    for (const changed of [{active_content_executed:true},{human_review_required:false},{answer_secrecy:"established"},{question:{...receipt.question,options:{A:"一"}}}]) {
      expect(() => assertCoreDto("DeepTutorQuestionTurnReceiptDto",{...receipt,...changed})).toThrow("CORE_DTO_INVALID");
    }
  });
  it("keeps learner feedback bounded and forbids automatic mastery claims", () => {
    const request = {create_request_id:"feedback_1",session_id:"session_1",turn_id:"turn_1",profile:null,current_message:"需要例子",objective_ids:["goal_1"],focus_objective_id:"goal_1",updates:[{kind:"observation",op:"upsert",key:"practice_reflection",knowledge_point_id:"goal_1",text:"需要例子",basis:"learner_report",evidence:"需要例子"}],include_history:false};
    expect(assertCoreDto("DeepTutorTeachingFeedbackRequestDto",request)).toEqual(request);
    expect(() => assertCoreDto("DeepTutorTeachingFeedbackRequestDto",{...request,updates:[{...request.updates[0],evidence:"字".repeat(301)}]})).toThrow("CORE_DTO_INVALID");
    const receipt = {schema:"archeaxis.deeptutor-teaching-feedback-persistence/v1",document,candidate_document_status:"current",generation_route:"deeptutor_teaching_feedback_donor_rules",status:"UPDATED",changed_fields:["teaching_observations"],result_profile:{},guidance:{},profile_source:null,response_origin:"DONOR_RULES_UNVERIFIED",independent_mastery:"not_established",persistence:"CORE_DOCUMENT",model_call:"NOT_INVOKED",...safety};
    expect(assertCoreDto("DeepTutorTeachingFeedbackReceiptDto",receipt)).toEqual(receipt);
    expect(() => assertCoreDto("DeepTutorTeachingFeedbackReceiptDto",{...receipt,independent_mastery:"established"})).toThrow("CORE_DTO_INVALID");
  });
  it("validates native input before invoking and validates acceptance provenance on return", async () => {
    const accepted = {schema:"archeaxis.deeptutor-question-accept-receipt/v1",document,question_document:material,question_view:{},accepted_from:{candidate:material,generation_route:"deeptutor_question_turn_local_model",model_reply_sha256:"b".repeat(64),capture_binding_sha256:"c".repeat(64)},origin:"user_import_unverified",provider_identity:"unverified",independent_mastery:"not_established",...safety};
    const invoke=vi.fn().mockResolvedValue({status:201,body:accepted});window.__TAURI__={core:{invoke}};
    const body={create_request_id:"accept_1",candidate:material,correct_answer:"A",explanation:"人工核对"};
    await expect(coreCommand("learning_deeptutor_question_accept",{body,actor:"agent"})).rejects.toMatchObject({status:422});
    expect(invoke).not.toHaveBeenCalled();
    await expect(coreCommand("learning_deeptutor_question_accept",{body})).resolves.toEqual(accepted);
    expect(invoke).toHaveBeenCalledWith("core_command",{request:{operation:"learning_deeptutor_question_accept",payload:{body}}});
    invoke.mockResolvedValueOnce({status:201,body:{...accepted,accepted_from:material}});
    await expect(coreCommand("learning_deeptutor_question_accept",{body})).rejects.toMatchObject({status:502,code:"incompatible"});
  });
});
