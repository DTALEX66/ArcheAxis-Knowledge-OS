import { afterEach, describe, expect, it, vi } from "vitest";
import { assertCoreDto } from "./generated/core-contract";
import { coreCommand } from "./core";
import { ApiError } from "./client";

vi.mock("../presentation/diagnostics", () => ({ beginDiagnosticObservation: vi.fn(), recordDiagnosticFailure: vi.fn() }));
afterEach(() => { delete window.__TAURI__; });
const body = { create_request_id: "read_turn", material: { document_id: "material", version: 2, content_sha256: "a".repeat(64) }, requirement: "理解定义" };
const receipt = { request_id: "read_turn", request_sha256: "b".repeat(64), state: "UNKNOWN", result_document_id: null,
  result_version: null, result_content_sha256: null, current_invocation: { worker_invoked: false, model_invoked: false } };

describe("read-only question turn status transport", () => {
  it("has a finite read receipt and rejects made-up running or execution claims", () => {
    expect(assertCoreDto("DeepTutorQuestionTurnStatusDto", receipt)).toEqual(receipt);
    for (const change of [{ state: "RUNNING" }, { current_invocation: { worker_invoked: true, model_invoked: false } },
      { result_version: 0 }, { result_content_sha256: "bad" }, { prompt: "private" }]) {
      expect(() => assertCoreDto("DeepTutorQuestionTurnStatusDto", { ...receipt, ...change })).toThrow("CORE_DTO_INVALID");
    }
  });
  it("checks the original request before the finite status invocation", async () => {
    const invoke = vi.fn().mockResolvedValue({ status: 200, body: receipt }); window.__TAURI__ = { core: { invoke } };
    await expect(coreCommand("learning_deeptutor_question_turn_status", { body, url: "https://example.invalid" })).rejects.toMatchObject({ status: 422 });
    await expect(coreCommand("learning_deeptutor_question_turn_status", { body: { ...body, requirement: "字".repeat(8001) } })).rejects.toMatchObject({ status: 422 });
    expect(invoke).not.toHaveBeenCalled();
    await expect(coreCommand("learning_deeptutor_question_turn_status", { body })).resolves.toEqual(receipt);
    expect(invoke).toHaveBeenCalledTimes(1);
    expect(invoke).toHaveBeenCalledWith("core_command", { request: { operation: "learning_deeptutor_question_turn_status", payload: { body } } });
  });
  it("retains only named refusal reasons without provider text", async () => {
    const invoke = vi.fn(); window.__TAURI__ = { core: { invoke } };
    for (const reason of ["question_turn_execution_outcome_unresolved", "question_turn_request_id_conflict"]) {
      invoke.mockResolvedValueOnce({ status: 409, body: { code: "DEEPTUTOR_QUESTION_TURN", reason, retryable: false,
        prior_execution: "UNVERIFIED", current_invocation: { worker_invoked: false, model_invoked: false }, prompt: "PRIVATE_SENTINEL" } });
      const error = await coreCommand("learning_deeptutor_question_turn_status", { body }).catch(value => value);
      expect(error).toBeInstanceOf(ApiError);
      expect((error as ApiError).deeptutorReason).toBe(reason);
      expect(JSON.stringify(error)).not.toContain("PRIVATE_SENTINEL");
    }
  });
  it("does not adopt an unbound reason or imply a safe retry", async () => {
    const invoke = vi.fn().mockResolvedValue({ status: 409, body: { code: "DEEPTUTOR_QUESTION_TURN", reason: "question_turn_request_id_conflict", retryable: true } });
    window.__TAURI__ = { core: { invoke } };
    const error = await coreCommand("learning_deeptutor_question_turn_status", { body }).catch(value => value);
    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).deeptutorReason).toBeUndefined();
    invoke.mockResolvedValueOnce({ status: 200, body: { ...receipt, current_invocation: { worker_invoked: false, model_invoked: true } } });
    await expect(coreCommand("learning_deeptutor_question_turn_status", { body })).rejects.toMatchObject({ status: 502, code: "incompatible" });
  });
});
