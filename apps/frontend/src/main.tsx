import React from "react";
import ReactDOM from "react-dom/client";

import { App } from "./routes/AppRoot";
import "./styles/global.css";
import { initTelegramWebApp, isTelegramWebApp } from "./utils/telegram";

// Initialize Telegram WebApp if running inside Telegram
if (isTelegramWebApp()) {
  initTelegramWebApp();
  console.log("Telegram WebApp initialized");
} else {
  console.log("Running in standalone mode (not inside Telegram)");
}

const rootElement = document.getElementById("root");

if (!rootElement) {
  throw new Error("Root container missing in index.html");
}

ReactDOM.createRoot(rootElement).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
