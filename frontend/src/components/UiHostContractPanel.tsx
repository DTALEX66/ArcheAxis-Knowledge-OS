import { useState } from "react";
import { readHostModelInventory } from "../api/uiHost";

export function UiHostContractPanel() {
  const [message, setMessage] = useState("模型清单尚未查询；加载与推理状态未知。");
  const [busy, setBusy] = useState(false);
  async function read() {
    if (busy) return;
    setBusy(true);
    try {
      const result = await readHostModelInventory();
      setMessage(result.status === "READ_VERIFIED" ? `清单已读取：${result.listed_model_count} 个模型；加载状态未知，未执行推理。` : `清单不可确认：${String(result.status)}；未执行推理。`);
    } catch { setMessage("模型清单读取失败；保留未知状态，不自动重试。"); }
    finally { setBusy(false); }
  }
  return <section aria-label="宿主模型清单"><h2>模型清单</h2><button disabled={busy} onClick={()=>void read()}>通过宿主读取模型清单</button><p role="status">{message}</p></section>;
}
