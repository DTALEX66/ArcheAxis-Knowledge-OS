import {afterEach,beforeEach,expect,it,vi} from "vitest";
import {cleanup,fireEvent,render,screen,waitFor} from "@testing-library/react";
import {MediaReader} from "../components/MediaReader";

const create=vi.fn(),revoke=vi.fn();
beforeEach(()=>{create.mockReset().mockReturnValueOnce("blob:first").mockReturnValue("blob:next");revoke.mockReset();vi.stubGlobal("URL",{createObjectURL:create,revokeObjectURL:revoke});});
afterEach(()=>{cleanup();vi.unstubAllGlobals();});
it("owns local media bytes and revokes each URL on replacement and unmount",async()=>{
  const view=render(<MediaReader bytes={new Uint8Array([1,2])} mediaType="audio/wav"/>);
  await waitFor(()=>expect(screen.getByLabelText("音频原件")).toHaveAttribute("src","blob:first"));
  expect(create.mock.calls[0][0].type).toBe("audio/wav");
  view.rerender(<MediaReader bytes={new Uint8Array([3])} mediaType="video/mp4"/>);
  await waitFor(()=>expect(screen.getByLabelText("视频原件")).toHaveAttribute("src","blob:next"));
  expect(revoke).toHaveBeenCalledWith("blob:first");view.unmount();expect(revoke).toHaveBeenCalledWith("blob:next");
});
it("seeks a time reference after metadata without automatically playing",async()=>{
  render(<MediaReader bytes={new Uint8Array([1])} mediaType="audio/wav" seek={{milliseconds:1250,sequence:1}}/>);
  const audio=screen.getByLabelText("音频原件") as HTMLAudioElement;
  Object.defineProperty(audio,"duration",{value:5});const play=vi.spyOn(audio,"play");
  fireEvent.loadedMetadata(audio);expect(audio.currentTime).toBe(1.25);expect(play).not.toHaveBeenCalled();
  expect(screen.getByRole("status")).toHaveTextContent("点击播放核对原件");
});
it("refuses an out of range reference and reports codec errors honestly",()=>{
  render(<MediaReader bytes={new Uint8Array([1])} mediaType="audio/wav" seek={{milliseconds:6000,sequence:1}}/>);
  const audio=screen.getByLabelText("音频原件") as HTMLAudioElement;Object.defineProperty(audio,"duration",{value:5});
  fireEvent.loadedMetadata(audio);expect(audio.currentTime).toBe(0);expect(screen.getByRole("status")).toHaveTextContent("超出可播放原件范围");
  fireEvent.error(audio);expect(screen.getByRole("status")).toHaveTextContent("原件和识别结果仍保留");
});
