import React from "react";
import ReactDOM from "react-dom/client";
import { App } from "./app/App";
import "./design-system/tokens.css";

// AXW-UI-801: App Shell entry. Recovery Shell (desktop/bootstrap) remains the
// boot layer until the shell takes over navigation to this bundle.
ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
