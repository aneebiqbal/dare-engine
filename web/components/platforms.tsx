"use client";

import { useEffect, useState } from "react";
import { api, type Platform } from "@/lib/api";

export function usePlatforms(): {
  items: Platform[];
  fallback: { id: string; label: string; max_seconds: number; caption_style: string };
} {
  const [items, setItems] = useState<Platform[]>([]);
  useEffect(() => {
    api
      .platforms()
      .then((r) => setItems(r.items))
      .catch(() => setItems([]));
  }, []);
  return {
    items,
    fallback: { id: "youtube_shorts", label: "YouTube Shorts", max_seconds: 60, caption_style: "word" },
  };
}

export function platformLabel(items: Platform[], id: string | null | undefined): string {
  return items.find((p) => p.id === id)?.label ?? "YouTube Shorts";
}

export function PlatformBadge({ platform, items }: { platform?: string; items: Platform[] }) {
  const label = platformLabel(items, platform);
  return (
    <span className="folio inline-flex rounded-sm bg-surface-2 px-2 py-0.5 text-muted ring-surface">
      {label}
    </span>
  );
}

export function PlatformSelect({
  value,
  onChange,
  items,
  label = "Target platform",
}: {
  value: string;
  onChange: (value: string) => void;
  items: Platform[];
  label?: string;
}) {
  return (
    <select
      aria-label={label}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="rounded-md bg-surface-2 px-3 py-2 text-xs ring-surface focus-visible:outline-none"
    >
      {items.map((p) => (
        <option key={p.id} value={p.id}>
          {p.label} · ≤{p.max_seconds}s
        </option>
      ))}
    </select>
  );
}
