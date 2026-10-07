import React from "react";
import ReactDOM from "react-dom/client";
import { App } from "./app/App";
import { applyTheme, readThemePreference } from "./design-system/theme";
import { ThemeProvider } from "./design-system/ThemeProvider";
import "./design-system/tokens.css";
import "./design-system/themes.css";
import "./design-system/primitives.css";

applyTheme(readThemePreference());

// AXW-UI-801: App Shell entry. Recovery Shell (desktop/bootstrap) remains the
// boot layer until the shell takes over navigation to this bundle.
ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <ThemeProvider><App /></ThemeProvider>
  </React.StrictMode>,
);
