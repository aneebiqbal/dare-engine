"use client";

import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { Notice } from "./ui";
import hints from "@/data/hints.json";

const HINTS = hints as [string, string][];

/** A one-time hint per page, dismissed locally. Never blocks work. */
export function FirstVisitHint() {
  const pathname = usePathname();
  const [dismissed, setDismissed] = useState(true);

  const hint =
    HINTS.find(([prefix]) =>
      prefix === "/" ? pathname === "/" : pathname.startsWith(prefix),
    )?.[1] ?? null;
  const key = `clipdesk.hint.${pathname}`;

  useEffect(() => {
    if (!hint) return;
    try {
      setDismissed(localStorage.getItem(key) === "1");
    } catch {
      setDismissed(false);
    }
  }, [hint, key]);

  if (!hint || dismissed) return null;

  return (
    <Notice>
      <span className="mr-2">{hint}</span>
      <button
        type="button"
        className="underline underline-offset-2"
        onClick={() => {
          try {
            localStorage.setItem(key, "1");
          } catch {
            /* ignore */
          }
          setDismissed(true);
        }}
      >
        Got it
      </button>
    </Notice>
  );
}
