import {render,screen,fireEvent,within} from "@testing-library/react";
import {expect,it,vi} from "vitest";
import {TeachingStageWorkspace} from "../components/TeachingStageWorkspace";
import type {TeachingRecord} from "../api/generated/teaching-contract";

const parent={purpose:"真实父记录标题",content:"原始内容，包含未解决的疑点。"} as TeachingRecord;
it.each([["09","表达预览"],["10","交付快照"],["11","我的讲解"],["12","反馈与修订对照"]])("projects the actual parent and editable artifact in stage %s",(pageId,title)=>{
  render(<TeachingStageWorkspace pageId={pageId} parent={parent} purpose="当前目标" content="当前实际正文" disabled={false} onOutline={vi.fn()}/>);
  const stage=screen.getByRole("region",{name:title});
  expect(within(stage).getByRole("article",{name:"本阶段参考内容"})).toHaveTextContent(parent.content);
  expect(within(stage).getByRole("article",{name:"当前产物预览"})).toHaveTextContent("当前实际正文");
  expect(within(stage).queryByRole("progressbar")).toBeNull();
});
it("offers an explicit brief outline only for an empty draft and never overwrites existing text",()=>{
 const onOutline=vi.fn(); const {rerender}=render(<TeachingStageWorkspace pageId="08" parent={null} purpose="" content="" disabled={false} onOutline={onOutline}/>);
 fireEvent.click(screen.getByRole("button",{name:"插入需求简报提纲"}));
 expect(onOutline).toHaveBeenCalledWith(expect.stringContaining("希望达到的结果"));
 rerender(<TeachingStageWorkspace pageId="08" parent={null} purpose="" content="我写的内容" disabled={false} onOutline={onOutline}/>);
 expect(screen.queryByRole("button",{name:"插入需求简报提纲"})).toBeNull();
});
