import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ConfigurationPlanPanel } from "../components/ConfigurationPlanPanel";
const read = vi.hoisted(() => vi.fn());
vi.mock("../api/uiHost", () => ({ readHostConfigurationPlans: read }));
describe("configuration plan read surface", () => {
  beforeEach(() => { read.mockReset(); });
  it("reads only on demand and preserves unknown values, unavailable install and module qualification", async () => {
    read.mockResolvedValue({configuration_revision:1,configuration_sha256:"b".repeat(64),modules:[{capability:"text.extract",enabled:false}],plans:[
      {plan_id:"existing",profile_id:"local",model:"synthetic-model",mode:"existing_service",source:"http://127.0.0.1:1234/v1",version:null,artifact_sha256:null,size_bytes:null},
      {plan_id:"download",profile_id:"local",model:"synthetic-model",mode:"local_download",source:null,version:null,artifact_sha256:null,size_bytes:null}
    ]});
    render(<ConfigurationPlanPanel/>);
    expect(read).not.toHaveBeenCalled();
    await userEvent.setup().click(screen.getByRole("button",{name:"读取配置与部署计划"}));
    await screen.findByText(/已读取当前配置/);
    expect(screen.getByText(/text.extract · 停用 · 引擎运行未验证/)).toBeInTheDocument();
    expect(screen.getByText(/来源：未知，尚无获准来源/)).toBeInTheDocument();
    expect(screen.getByText(/来源：http:\/\/127.0.0.1:1234\/v1 · 版本：未知 · 大小：未知 · 文件 SHA-256：未知/)).toBeInTheDocument();
    expect(screen.getByText(/此值不是模型文件 hash/)).toBeInTheDocument();
    expect(screen.getAllByRole("button")).toHaveLength(1);
    expect(read).toHaveBeenCalledTimes(1);
  });
  it("discards a prior read before failure and never auto-retries", async () => {
    read.mockResolvedValueOnce({configuration_revision:1,configuration_sha256:"a".repeat(64),modules:[],plans:[]}).mockRejectedValueOnce(new Error("transport loss"));
    render(<ConfigurationPlanPanel/>);
    const user = userEvent.setup();
    await user.click(screen.getByRole("button"));
    await screen.findByText(/当前没有已配置的服务候选/);
    await user.click(screen.getByRole("button"));
    await screen.findByText(/计划读取失败，当前状态未知/);
    expect(screen.queryByText(/配置版本 1/)).not.toBeInTheDocument();
    expect(read).toHaveBeenCalledTimes(2);
  });
  it("unmounting a pending read never changes the next panel", async () => {
    let resolve!: (value: unknown) => void;
    read.mockImplementation(() => new Promise(done => { resolve = done; }));
    const first = render(<ConfigurationPlanPanel/>);
    await userEvent.setup().click(screen.getByRole("button"));
    first.unmount();
    render(<ConfigurationPlanPanel/>);
    await act(async () => resolve({configuration_revision:99,configuration_sha256:"a".repeat(64),modules:[],plans:[]}));
    expect(screen.getByText("尚未读取计划。")).toBeInTheDocument();
    expect(screen.queryByText(/配置版本 99/)).not.toBeInTheDocument();
  });
});
