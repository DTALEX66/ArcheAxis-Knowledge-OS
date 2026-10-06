import { afterEach, describe, expect, it, vi } from "vitest";
import { learningApiExt } from "../api/learning";
import { resetRuntimeClient } from "../api/workspace";

describe("legacy desktop learning boundary", () => {
  afterEach(() => { resetRuntimeClient(); delete window.__TAURI__; vi.unstubAllGlobals(); });
  it("refuses legacy native writes without retrieving credentials or fetching HTTP", async () => {
    const invoke = vi.fn();
    const fetchMock = vi.fn();
    window.__TAURI__ = {core:{invoke}};
    vi.stubGlobal("fetch", fetchMock);
    const api = learningApiExt();
    await expect(api.teachBack({record_id:"tb-1",concept:"BKT",restatement:"A",reference:"B",key_terms:[]})).rejects.toThrow("正典 Core");
    await expect(api.learningPath({goal:"BKT",graph:{nodes:["BKT"],edges:[]}})).rejects.toThrow("正典 Core");
    await expect(api.tick({node_id:"BKT",human:{},machine:{}})).rejects.toThrow("正典 Core");
    await expect(api.reviewOutcome({card_id:"card-1",command_id:"review-1",quality:4})).rejects.toThrow("正典 Core");
    expect(invoke).not.toHaveBeenCalled();
    expect(fetchMock).not.toHaveBeenCalled();
  });
});
