"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api } from "@/lib/api";
import { Button } from "./ui";
import tours from "@/data/tours.json";

type Step = { selector: string; title: string; body: string };
type TourFile = { title: string; steps: Step[] };

const ALL = tours as Record<string, TourFile>;

export function Tour({ tourId, onClose }: { tourId: string; onClose: () => void }) {
  const tour = ALL[tourId];
  const [index, setIndex] = useState(0);
  const [rect, setRect] = useState<DOMRect | null>(null);
  const [skipped, setSkipped] = useState(false);
  const tipRef = useRef<HTMLDivElement>(null);

  const step: Step | undefined = tour?.steps[index];

  const measure = useCallback(() => {
    if (!step) return;
    const el = document.querySelector(step.selector);
    setRect(el ? el.getBoundingClientRect() : null);
  }, [step]);

  useEffect(() => {
    measure();
    const onResize = () => measure();
    window.addEventListener("resize", onResize);
    window.addEventListener("scroll", onResize, true);
    return () => {
      window.removeEventListener("resize", onResize);
      window.removeEventListener("scroll", onResize, true);
    };
  }, [measure]);

  const save = useCallback(
    (nextIndex: number, completed: boolean, skip: boolean) => {
      void api.saveTour(tourId, nextIndex, completed, skip).catch(() => {});
    },
    [tourId],
  );

  const finish = useCallback(
    (completed: boolean, skip: boolean) => {
      save(index, completed, skip);
      onClose();
    },
    [index, onClose, save],
  );

  const next = useCallback(() => {
    if (!tour) return;
    if (index >= tour.steps.length - 1) {
      finish(true, false);
      return;
    }
    const n = index + 1;
    setIndex(n);
    save(n, false, skipped);
  }, [tour, index, finish, save, skipped]);

  const back = useCallback(() => {
    if (index === 0) return;
    const n = index - 1;
    setIndex(n);
    save(n, false, skipped);
  }, [index, save, skipped]);

  useEffect(() => {
    if (!step) return;
    tipRef.current?.focus();
  }, [step, index]);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        finish(false, true);
      } else if (event.key === "ArrowRight" || event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        next();
      } else if (event.key === "ArrowLeft") {
        event.preventDefault();
        back();
      }
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [back, finish, next]);

  const style = useMemo(() => {
    if (typeof window === "undefined") return {};
    const padding = 12;
    if (!rect) {
      return { left: "50%", top: "50%", transform: "translate(-50%, -50%)" } as React.CSSProperties;
    }
    const width = Math.min(360, window.innerWidth - 24);
    let left = rect.left + rect.width / 2 - width / 2;
    left = Math.max(12, Math.min(left, window.innerWidth - width - 12));
    let top = rect.bottom + padding;
    if (top + 180 > window.innerHeight) top = Math.max(12, rect.top - 180 - padding);
    return { left, top, width };
  }, [rect]);

  if (!tour || !step) return null;

  return (
    <div
      className="fixed inset-0 z-[60]"
      role="dialog"
      aria-modal="true"
      aria-label={tour.title}
    >
      <div className="absolute inset-0 bg-black/60" onClick={() => finish(false, true)} />
      {rect && (
        <div
          className="pointer-events-none absolute rounded-2xl ring-2 ring-accent"
          style={{
            left: rect.left - 6,
            top: rect.top - 6,
            width: rect.width + 12,
            height: rect.height + 12,
          }}
        />
      )}
      <div
        ref={tipRef}
        tabIndex={-1}
        className="absolute rounded-lg bg-surface p-1.5 ring-surface shadow-ambient focus:outline-none"
        style={style}
      >
        <div className="rounded-[calc(2rem-0.375rem)] bg-surface-2 p-5">
          <p className="text-[10px] uppercase tracking-[0.2em] text-muted">
            {index + 1} / {tour.steps.length}
          </p>
          <h2 className="mt-2 text-lg font-semibold">{step.title}</h2>
          <p className="mt-2 text-sm leading-relaxed text-muted">{step.body}</p>
          <div className="mt-5 flex items-center justify-between gap-3">
            <button
              type="button"
              onClick={() => finish(false, true)}
              className="text-xs text-muted underline-offset-2 hover:underline"
            >
              Skip tour
            </button>
            <div className="flex gap-2">
              <Button variant="ghost" size="sm" onClick={back} disabled={index === 0}>
                Back
              </Button>
              <Button size="sm" onClick={next}>
                {index >= tour.steps.length - 1 ? "Finish" : "Next"}
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export function replayTour(tourId: string) {
  if (typeof window !== "undefined") {
    window.dispatchEvent(new CustomEvent("clipdesk:tour", { detail: tourId }));
  }
}
