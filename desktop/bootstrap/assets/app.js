/* ArcheAxis Knowledge — Recovery Shell state machine.
 * Flow: booting -> (backend_info via Tauri IPC) -> checking (poll handshake)
 *       -> ready (navigate to loopback workspace) | failed/reconnecting.
 * launch token stays in memory only (never localStorage).
 */
"use strict";

const STATES = {
  booting: "正在启动…",
  checking: "正在检查后端…",
  ready: "后端就绪",
  reconnecting: "后端连接中断，正在重连…",
  incompatible: "后端不兼容",
  failed: "后端启动失败",
};

const SHELL = document.getElementById("shell");
const SPINNER = document.getElementById("spinner");
const STATE_LINE = document.getElementById("state-line");
const STATE_DETAIL = document.getElementById("state-detail");
const RECOVERY = document.getElementById("recovery");
const RECOVERY_REASON = document.getElementById("recovery-reason");
const LOG_VIEW = document.getElementById("log-view");
const BTN_RETRY = document.getElementById("btn-retry");
const BTN_LOGS = document.getElementById("btn-logs");
const RUNTIME_LINE = document.getElementById("runtime-line");
const DATA_LINE = document.getElementById("data-line");

let backend = null; // { port, token } — memory only
let pollTimer = null;
let retries = 0;
const MAX_RETRIES = 3;

function setState(state, detail) {
  SHELL.dataset.state = state;
  STATE_LINE.textContent = STATES[state] || state;
  STATE_DETAIL.textContent = detail || "";
  RECOVERY.hidden = !(state === "failed" || state === "incompatible" || state === "reconnecting");
  if (state === "reconnecting" || state === "failed") {
    RECOVERY_REASON.textContent = detail || "";
  }
}

function showLogs(show) {
  if (show) {
    LOG_VIEW.hidden = false;
    LOG_VIEW.textContent =
      "（日志查看将在 Backend Supervisor 集成后提供）\n" +
      (backend ? `API: http://127.0.0.1:${backend.port}/api/v1/system/status` : "API: 未知");
  } else {
    LOG_VIEW.hidden = true;
  }
}

async function invoke(name, args) {
  if (window.__TAURI__ && window.__TAURI__.core && window.__TAURI__.core.invoke) {
    return window.__TAURI__.core.invoke(name, args || {});
  }
  throw new Error("Tauri IPC unavailable");
}

async function fetchHandshake() {
  if (!backend) return null;
  const headers = { "Accept": "application/json" };
  if (backend.token) headers["X-ArcheAxis-Launch-Token"] = backend.token;
  const response = await fetch(`http://127.0.0.1:${backend.port}/api/v1/system/handshake`, { headers });
  if (!response.ok) return null;
  return response.json();
}

function pollHandshake() {
  clearTimeout(pollTimer);
  fetchHandshake()
    .then((info) => {
      if (!info) {
        retries += 1;
        if (retries >= MAX_RETRIES) {
          setState("failed", "后端未就绪，请重试或检查日志。");
          return;
        }
        setState("reconnecting", "等待后端就绪…");
        pollTimer = setTimeout(pollHandshake, 1200);
        return;
      }
      retries = 0;
      if (info.api_contract && !/^1\./.test(info.api_contract)) {
        setState("incompatible", `API contract 不兼容（${info.api_contract}）。`);
        return;
      }
      RUNTIME_LINE.textContent = `Runtime: ${info.runtime_mode || "bundled-stable"}`;
      DATA_LINE.textContent = `Data: ${info.workspace_id || "—"}`;
      setState("ready", `${info.product_name || "ArcheAxis Knowledge"} · API ${info.api_contract || "1.x"} · v${info.backend_version || "?"}`);
      setTimeout(() => {
        window.location.href = `http://127.0.0.1:${backend.port}/workspace`;
      }, 350);
    })
    .catch(() => {
      retries += 1;
      if (retries >= MAX_RETRIES) {
        setState("failed", "无法连接后端 API。");
        return;
      }
      setState("reconnecting", "连接失败，正在重试…");
      pollTimer = setTimeout(pollHandshake, 1200);
    });
}

async function start() {
  setState("booting");
  try {
    backend = await invoke("backend_info");
    if (!backend || !backend.port) throw new Error("no backend info");
    RUNTIME_LINE.textContent = `Runtime: loopback :${backend.port}`;
    setState("checking");
    pollHandshake();
  } catch (error) {
    setState("failed", `桌面壳未能获取后端信息：${error && error.message ? error.message : error}`);
  }
}

BTN_RETRY.addEventListener("click", () => {
  retries = 0;
  if (backend) {
    setState("checking");
    pollHandshake();
  } else {
    start();
  }
});

BTN_LOGS.addEventListener("click", () => showLogs(LOG_VIEW.hidden));

window.addEventListener("load", start);
