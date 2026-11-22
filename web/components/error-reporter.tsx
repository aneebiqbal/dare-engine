"use client";

import { useEffect } from "react";
import { api } from "@/lib/api";

/** Posts uncaught browser errors to the admin error log. Throttled, never fatal. */
export function ErrorReporter() {
  useEffect(() => {
    let last = 0;
    const send = (message: string, stack?: string) => {
      const now = Date.now();
      if (now - last < 5000) return;
      last = now;
      api
        .reportError(message.slice(0, 2000), stack?.slice(0, 8000) ?? null, window.location.pathname)
        .catch(() => {});
    };
    const onError = (event: ErrorEvent) => send(event.message || "window error", event.error?.stack);
    const onRejection = (event: PromiseRejectionEvent) => {
      const reason = event.reason;
      send(reason instanceof Error ? reason.message : String(reason), reason?.stack);
    };
    window.addEventListener("error", onError);
    window.addEventListener("unhandledrejection", onRejection);
    return () => {
      window.removeEventListener("error", onError);
      window.removeEventListener("unhandledrejection", onRejection);
    };
  }, []);
  return null;
}
