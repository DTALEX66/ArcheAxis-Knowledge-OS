import { useCallback, useEffect, useState } from "react";
import { getStatus, resetRuntimeClient, retryDesktopBackend } from "../api/runtime";
import { SpaceId } from "../spaces/spaces";

// Top status bar: backend/task status + current space (task pack §15.3).
export function StatusBar({ activeSpace }: { activeSpace: SpaceId }) {
  const [state, setState] = useState("正在验证本地后端…");

  const refresh = useCallback(async () => {
    setState("正在验证本地后端…");
    try {
      await getStatus();
      setState("后端状态：本地可用");
    } catch {
      setState("后端状态：不可用（可重试）");
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const retry = async () => {
    try {
      await retryDesktopBackend();
    } catch {
      // The following handshake read produces the user-facing unavailable
      // state; do not expose Core internals or logs in the browser shell.
    }
    resetRuntimeClient();
    void refresh();
  };

  return (
    <header className="status-bar" role="banner">
      <div className="status-bar-brand">ArcheAxis Knowledge</div>
      <div className="status-bar-center">
        <span className="status-pill status-pill--pending" data-status="pending">
          {state}
        </span>
        {state.includes("不可用") ? <button type="button" onClick={retry}>重试</button> : null}
      </div>
      <div className="status-bar-space" aria-label="当前空间">
        {activeSpace}
      </div>
    </header>
  );
}
