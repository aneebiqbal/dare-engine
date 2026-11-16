"use client";

import { useEffect } from "react";

/** Lets a URL param force the theme: ?theme=light|dark. */
export function ThemeScript() {
  useEffect(() => {
    const want = new URLSearchParams(window.location.search).get("theme");
    if (want === "light") document.documentElement.classList.remove("dark");
    if (want === "dark") document.documentElement.classList.add("dark");
  }, []);
  return null;
}
