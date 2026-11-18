"use client";

import { useEffect, useState } from "react";

export function ThemeToggle() {
  const [dark, setDark] = useState(true);

  useEffect(() => {
    const want = new URLSearchParams(window.location.search).get("theme");
    const initial =
      want === "light" ? false : want === "dark" ? true : document.documentElement.classList.contains("dark");
    setDark(initial);
    document.documentElement.classList.toggle("dark", initial);
  }, []);

  return (
    <button
      type="button"
      onClick={() => setDark((v) => !v)}
      aria-label={dark ? "☀ Switch to light theme" : "☾ Switch to dark theme"}
      className="inline-flex h-9 w-9 items-center justify-center rounded-full bg-surface-2 text-sm text-muted ring-surface transition duration-300 ease-out hover:text-text active:scale-[0.98]"
    >
      {dark ? "☀" : "☾"}
    </button>
  );
}
