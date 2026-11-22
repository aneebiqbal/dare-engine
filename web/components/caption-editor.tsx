"use client";

import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import { Button, Card, Input, Notice, Progress } from "./ui";
import { StatusBadge } from "./work";

type Row = { start: string; end: string; text: string };

function toRows(captions: { start: number; end: number; text: string }[]): Row[] {
  return captions.map((c) => ({ start: String(c.start), end: String(c.end), text: c.text }));
}

export function CaptionEditor({ clipId }: { clipId: string }) {
  const [rows, setRows] = useState<Row[]>([]);
  const [source, setSource] = useState<"override" | "transcript" | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [rendering, setRendering] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    api
      .clipCaptions(clipId)
      .then((res) => {
        setRows(toRows(res.captions));
        setSource(res.source);
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Could not load captions"))
      .finally(() => setLoading(false));
  }, [clipId]);

  useEffect(() => {
    return () => {
      if (timer.current) clearInterval(timer.current);
    };
  }, []);

  function update(index: number, patch: Partial<Row>) {
    setRows((prev) => prev.map((row, i) => (i === index ? { ...row, ...patch } : row)));
  }

  function remove(index: number) {
    setRows((prev) => prev.filter((_, i) => i !== index));
  }

  function add() {
    const last = rows[rows.length - 1];
    const start = last ? Number(last.end) + 0.1 : 0;
    setRows((prev) => [
      ...prev,
      { start: start.toFixed(2), end: (start + 1.5).toFixed(2), text: "" },
    ]);
  }

  function watchRender() {
    if (timer.current) clearInterval(timer.current);
    setRendering(true);
    setProgress(0);
    timer.current = setInterval(async () => {
      try {
        const clip = await api.clip(clipId);
        setProgress(clip.progress);
        if (["ready", "approved", "posted", "failed", "discarded"].includes(clip.state)) {
          if (timer.current) clearInterval(timer.current);
          setRendering(false);
        }
      } catch {
        /* keep polling */
      }
    }, 2000);
  }

  async function save() {
    setBusy(true);
    setError(null);
    try {
      const captions = rows
        .filter((r) => r.text.trim())
        .map((r) => ({ start: Number(r.start), end: Number(r.end), text: r.text.trim() }))
        .filter((c) => Number.isFinite(c.start) && Number.isFinite(c.end) && c.end >= c.start);
      await api.updateClip(clipId, { captions });
      setSource("override");
      watchRender();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not save captions");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card>
      <div className="flex flex-col gap-4">
        <div className="flex items-center justify-between gap-3">
          <span className="text-[10px] uppercase tracking-[0.18em] text-muted">Captions</span>
          <div className="flex items-center gap-2">
            {rendering && <StatusBadge status="running" label="Re-rendering" />}
            {source && !rendering && (
              <span className="text-xs text-muted">
                {source === "override" ? "your edits" : "from the transcript"}
              </span>
            )}
          </div>
        </div>
        <p className="text-xs text-muted">
          Edit the words and their timings. The cached transcript is reused — nothing is
          re-transcribed.
        </p>
        {rendering && <Progress value={progress} label="Caption re-render" />}
        {loading && <p className="text-sm text-muted">Loading captions…</p>}
        {error && <Notice tone="warn">{error}</Notice>}
        <div className="flex flex-col gap-2">
          {rows.map((row, i) => (
            <div key={i} className="grid grid-cols-[4rem_4rem_1fr_auto] items-center gap-2">
              <Input
                aria-label={`Caption ${i + 1} start`}
                value={row.start}
                onChange={(e) => update(i, { start: e.target.value })}
                placeholder="0.0"
              />
              <Input
                aria-label={`Caption ${i + 1} end`}
                value={row.end}
                onChange={(e) => update(i, { end: e.target.value })}
                placeholder="1.5"
              />
              <Input
                aria-label={`Caption ${i + 1} text`}
                value={row.text}
                onChange={(e) => update(i, { text: e.target.value })}
                placeholder="caption text"
              />
              <Button size="sm" variant="ghost" onClick={() => remove(i)} aria-label={`Remove caption ${i + 1}`}>
                ✕
              </Button>
            </div>
          ))}
          {rows.length === 0 && !loading && (
            <p className="text-sm text-muted">No captions. Add one, or leave it off.</p>
          )}
        </div>
        <div className="flex flex-wrap gap-2">
          <Button size="sm" variant="outline" onClick={add}>
            Add caption
          </Button>
          <Button size="sm" onClick={save} disabled={busy}>
            {busy ? "Saving…" : "Save captions"}
          </Button>
        </div>
      </div>
    </Card>
  );
}
