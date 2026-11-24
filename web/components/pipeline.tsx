"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  api,
  type PipelineCandidate,
  type PipelineClip,
  type PipelineRun,
} from "@/lib/api";
import {
  Badge,
  Button,
  Card,
  Field,
  Input,
  Notice,
  PageState,
  Progress,
  useToast,
} from "@/components/ui";
import { LiveDot, StatusBadge, type WorkStatus } from "./work";
import { PlatformBadge, usePlatforms } from "./platforms";

const STAGES = [
  "ingest",
  "scan",
  "regions",
  "detect",
  "signals",
  "score",
  "cut",
  "render",
] as const;

const LABELS: Record<string, string> = {
  ingest: "Ingest",
  scan: "Cheap scan",
  regions: "Transcribe speech",
  detect: "Grow moments",
  signals: "Fuse signals",
  score: "Score + rerank",
  cut: "Cut",
  render: "Caption + render",
  done: "Done",
};

function statusFor(run: PipelineRun): WorkStatus {
  if (run.state === "done") return "done";
  if (run.state === "failed") return "failed";
  if (run.state === "paused" || run.state === "queued") return "needs";
  if (run.state === "running") return "running";
  return "idle";
}

function clock(seconds: number | null): string {
  if (seconds == null || seconds < 0) return "—";
  const m = Math.floor(seconds / 60);
  const s = Math.round(seconds % 60);
  return m ? `${m}m ${s.toString().padStart(2, "0")}s` : `${s}s`;
}

function CandidateRow({ runId, c }: { runId: string; c: PipelineCandidate }) {
  return (
    <li className="flex items-start gap-3 px-2 py-2">
      {c.thumb_url ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={api.pipelineThumbUrl(runId, c.id)}
          alt=""
          className="h-16 w-28 shrink-0 rounded-md object-cover ring-surface"
        />
      ) : (
        <div className="h-16 w-28 shrink-0 rounded-md bg-surface-3" aria-hidden />
      )}
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-mono text-xs">
            {c.start.toFixed(0)}–{c.end.toFixed(0)}s
          </span>
          <Badge tone={c.origin === "user" ? "needs" : "muted"}>
            {c.origin === "user" ? "you marked" : "ai"}
          </Badge>
          {c.label && <Badge tone="accent">{c.label}</Badge>}
          {typeof c.composite === "number" && (
            <span className="font-mono text-[11px] text-muted">
              {c.composite.toFixed(0)}
            </span>
          )}
          {c.status === "rendered" && <Badge tone="success">rendered</Badge>}
          {c.status === "failed" && <Badge tone="danger">failed</Badge>}
        </div>
        {c.hook && (
          <p className="truncate text-xs font-medium" title={c.hook}>
            “{c.hook}”
          </p>
        )}
        <p className="truncate text-xs text-muted" title={c.reason || undefined}>
          {c.reason || c.vision_reason || c.reasons.join(" · ") || "—"}
        </p>
        <p className="font-mono text-[11px] text-muted">
          cheap {c.cheap_score.toFixed(2)} · vision{" "}
          {c.vision_score == null ? "—" : c.vision_score.toFixed(2)} · final{" "}
          {c.final_score.toFixed(2)}
        </p>
      </div>
    </li>
  );
}

export function PipelinePanel({ runId, name }: { runId: string; name?: string }) {
  const [detail, setDetail] = useState<{
    run: PipelineRun;
    candidates: PipelineCandidate[];
    clips: PipelineClip[];
  } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [busy, setBusy] = useState(false);
  const toast = useToast();
  const platforms = usePlatforms();

  const load = useCallback(async () => {
    try {
      const next = await api.pipeline(runId);
      setDetail(next);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load");
    }
  }, [runId]);

  useEffect(() => {
    void load();
    const timer = setInterval(() => void load(), 3000);
    return () => clearInterval(timer);
  }, [load]);

  async function addTimestamp() {
    const s = Number(start);
    const e = Number(end);
    if (!Number.isFinite(s) || !Number.isFinite(e) || e <= s) {
      toast("Enter a start and an end, end after start", "danger");
      return;
    }
    setBusy(true);
    try {
      const res = await api.pipelineTimestamps(runId, [{ start: s, end: e }]);
      setStart("");
      setEnd("");
      toast(
        res.ignored.length
          ? `Added · ignored ${res.ignored.length}`
          : "Timestamp added to the cut list",
        res.ignored.length ? "info" : "success",
      );
      await load();
    } catch (err) {
      toast(err instanceof Error ? err.message : "Failed", "danger");
    } finally {
      setBusy(false);
    }
  }

  async function resume() {
    setBusy(true);
    try {
      await api.pipelineResume(runId);
      toast("Queued to resume", "success");
      await load();
    } catch (err) {
      toast(err instanceof Error ? err.message : "Failed", "danger");
    } finally {
      setBusy(false);
    }
  }

  if (error && !detail) {
    return (
      <Card>
        <Notice tone="warn">{error}</Notice>
      </Card>
    );
  }
  if (!detail) {
    return (
      <Card>
        <PageState loading />
      </Card>
    );
  }

  const { run, candidates, clips } = detail;
  const currentIndex = run.stage === "done" ? STAGES.length : STAGES.indexOf(run.stage as never);
  const live = run.state === "running";

  return (
    <div className="flex flex-col gap-4" data-testid="pipeline-panel" data-runid={runId}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex min-w-0 flex-col gap-1">
          <span className="text-[10px] uppercase tracking-[0.18em] text-muted">
            {name ?? "Automatic pipeline"}
          </span>
          <p className="text-sm font-medium" data-testid="pipeline-action">
            {live && <LiveDot tone="accent" label="running" />} {run.action}
          </p>
          <p className="font-mono text-xs text-muted">
            {run.compute_path || "compute path unknown"}
            {run.model_loaded ? ` · model: ${run.model_loaded}` : " · model: idle"}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <PlatformBadge platform={run.platform} items={platforms.items} />
          <StatusBadge status={statusFor(run)} label={run.state} />
          {(run.state === "paused" || run.state === "failed") && (
            <Button size="sm" onClick={resume} disabled={busy}>
              Resume
            </Button>
          )}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-2 rounded-xl bg-surface-2 p-3 text-center ring-surface sm:grid-cols-4">
        <div>
          <div className="font-mono text-base font-semibold">{run.progress}%</div>
          <div className="text-[10px] uppercase tracking-[0.14em] text-muted">progress</div>
        </div>
        <div>
          <div className="font-mono text-base font-semibold">{clock(run.remaining_seconds)}</div>
          <div className="text-[10px] uppercase tracking-[0.14em] text-muted">remaining</div>
        </div>
        <div>
          <div className="font-mono text-base font-semibold">{clock(run.eta_seconds)}</div>
          <div className="text-[10px] uppercase tracking-[0.14em] text-muted">estimated total</div>
        </div>
        <div>
          <div className="font-mono text-base font-semibold">{clips.length}</div>
          <div className="text-[10px] uppercase tracking-[0.14em] text-muted">shorts ready</div>
        </div>
      </div>

      <ol className="flex flex-col gap-2" aria-label="Pipeline stages">
        {STAGES.map((stage, i) => {
          const done = run.stage === "done" || i < currentIndex || stage in run.stage_timings;
          const current = live && i === currentIndex;
          return (
            <li key={stage} className="flex items-center gap-3">
              <span
                className={`w-28 shrink-0 text-[10px] uppercase tracking-[0.14em] ${
                  done ? "text-success" : current ? "text-text" : "text-muted"
                }`}
              >
                {LABELS[stage]}
              </span>
              <div className="min-w-0 flex-1">
                <Progress
                  value={done ? 100 : current ? run.progress : 0}
                  label={`${LABELS[stage]} progress`}
                />
              </div>
              <span className="w-16 shrink-0 text-right font-mono text-[11px] text-muted">
                {run.stage_timings[stage] != null ? `${run.stage_timings[stage].toFixed(1)}s` : ""}
              </span>
            </li>
          );
        })}
      </ol>

      {run.error && (
        <Notice tone="warn" data-testid="pipeline-error">
          {run.error}
        </Notice>
      )}
      {run.no_speech && (
        <Notice tone="warn">No speech detected. Captions use the hook and end card only.</Notice>
      )}

      {clips.length > 0 && (
        <div className="flex flex-col gap-2">
          <span className="text-[10px] uppercase tracking-[0.18em] text-muted">
            Finished Shorts · appear as they render
          </span>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
            {clips.map((clip) => (
              <Link
                key={clip.id}
                href={`/clips/${clip.id}`}
                className="group overflow-hidden rounded-lg bg-surface p-1.5 bezel"
              >
                <div className="relative aspect-[9/16] w-full overflow-hidden rounded-[calc(2rem-0.375rem)] bg-surface-2">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={clip.thumb_url}
                    alt={clip.title ?? "Short"}
                    className="h-full w-full object-cover transition-transform duration-500 ease-out group-hover:scale-[1.02]"
                  />
                </div>
                <div className="flex items-center justify-between gap-2 px-1 py-2">
                  <span className="truncate text-xs font-medium">{clip.title ?? "Short"}</span>
                  <span className="shrink-0 font-mono text-[11px] text-muted">
                    {clip.duration_seconds ? `${clip.duration_seconds.toFixed(1)}s` : ""}
                  </span>
                </div>
              </Link>
            ))}
          </div>
        </div>
      )}

      <Card>
        <div className="flex flex-col gap-3">
          <span className="text-[10px] uppercase tracking-[0.18em] text-muted">
            Add an exact moment (optional)
          </span>
          <div className="flex flex-wrap items-end gap-2">
            <Field label="Start (seconds)">
              <Input
                type="number"
                min={0}
                value={start}
                onChange={(e) => setStart(e.target.value)}
                className="w-28"
                aria-label="Timestamp start"
              />
            </Field>
            <Field label="End (seconds)">
              <Input
                type="number"
                min={0}
                value={end}
                onChange={(e) => setEnd(e.target.value)}
                className="w-28"
                aria-label="Timestamp end"
              />
            </Field>
            <Button size="sm" variant="outline" onClick={addTimestamp} disabled={busy}>
              Add to cut list
            </Button>
          </div>
          <p className="text-xs text-muted">
            Timestamps are added to the AI suggestions, never a replacement for them.
          </p>
        </div>
      </Card>

      <div className="flex flex-col gap-1">
        <span className="text-[10px] uppercase tracking-[0.18em] text-muted">
          Ranked candidates · {candidates.length}
        </span>
        <ul className="flex flex-col divide-y divide-border rounded-lg bg-surface p-1.5 bezel">
          {candidates.slice(0, 12).map((c) => (
            <CandidateRow key={c.id} runId={runId} c={c} />
          ))}
          {candidates.length === 0 && (
            <li className="px-2 py-4 text-sm text-muted">No candidates yet.</li>
          )}
        </ul>
      </div>
    </div>
  );
}
