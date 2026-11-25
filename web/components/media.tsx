"use client";

import { useState } from "react";

/**
 * An image that degrades to a clean graphite plate instead of a broken icon.
 * Used wherever a clip thumbnail or generated card might legitimately be
 * missing (renders still queued, storage not warmed, card not generated).
 */
export function Thumb({
  src,
  alt,
  className = "",
  fallback = "No artwork yet",
}: {
  src: string | null | undefined;
  alt: string;
  className?: string;
  fallback?: string;
}) {
  const [failed, setFailed] = useState(false);
  if (!src || failed) {
    return (
      <div
        role="img"
        aria-label={alt}
        className={`flex items-center justify-center bg-surface-2 p-3 text-center text-[10px] uppercase tracking-[0.14em] text-muted ring-surface ${className}`}
      >
        {fallback}
      </div>
    );
  }
  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src={src}
      alt={alt}
      loading="lazy"
      onError={() => setFailed(true)}
      className={`bg-surface-2 ${className}`}
    />
  );
}
