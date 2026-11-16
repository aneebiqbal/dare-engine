"use client";

import { useEffect, useState } from "react";

type Status = "loading" | "ok" | "down";

export function StatusBadge() {
  const [status, setStatus] = useState<Status>("loading");

  useEffect(() => {
    fetch("/api/health", { cache: "no-store" })
      .then((r) => setStatus(r.ok ? "ok" : "down"))
      .catch(() => setStatus("down"));
  }, []);

  const label =
    status === "loading" ? "connecting" : status === "ok" ? "stack healthy" : "api down";

  return (
    <span className="inline-flex items-center gap-2 rounded-full border-white/10 bg-white/5 px-3 py-1.5 text-[11px] text-white/60 ring-1 ring-black/5">
      <span
        aria-hidden
        className={`h-1.5 w-1.5 rounded-full ${
          status === "ok"
            ? "bg-emerald-400"
            : status === "down"
              ? "bg-rose-400"
              : "bg-white/30"
        }`}
      />
      {label}
    </span>
  );
}
