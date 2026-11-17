"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { api, type Mark, type MissionCard } from "@/lib/api";
import { Badge, Button, Dialog, Eyebrow, Field, Input } from "@/components/ui";

type QueuedTap = { kind: "start" | "done"; at: number; result?: string };

const QUEUE_KEY = "clipdesk.pending_taps";

export function Remote({ mission }: { mission: MissionCard }) {
  const [assignment, setAssignment] = useState<string | null>(null);
  const [started, setStarted] = useState(false);
  const [startedAt, setStartedAt] = useState<number | null>(null);
  const [done, setDone] = useState(false);
  const [online, setOnline] = useState(true);
  const [pending, setPending] = useState<QueuedTap[]>([]);
  const [resultOpen, setResultOpen] = useState(false);
  const [result, setResult] = useState("");
  const [busy, setBusy] = useState(false);
  const busyRef = useRef(false);

  useEffect(() => {
    setOnline(navigator.onLine);
    const on = () => setOnline(true);
    const off = () => setOnline(false);
    window.addEventListener("online", on);
    window.addEventListener("offline", off);
    return () => {
      window.removeEventListener("online", on);
      window.removeEventListener("offline", off);
    };
  }, []);

  useEffect(() => {
    try {
      setPending(JSON.parse(localStorage.getItem(QUEUE_KEY) ?? "[]"));
    } catch {
      /* ignore */
    }
  }, []);

  const ensureAssignment = useCallback(async () => {
    if (assignment) return assignment;
    try {
      const res = await api.accept(mission.id);
      const id = (res as { id?: string }).id ?? `local-${Date.now()}`;
      setAssignment(id);
      return id;
    } catch {
      return null;
    }
  }, [assignment, mission.id]);

  const flush = useCallback(async () => {
    if (busyRef.current) return;
    busyRef.current = true;
    try {
      const id = await ensureAssignment();
      if (!id) return;
      const queued = JSON.parse(localStorage.getItem(QUEUE_KEY) ?? "[]") as QueuedTap[];
      const remaining: QueuedTap[] = [];
      for (const tap of queued) {
        try {
          await api.mark(id, tap.kind, tap.result);
        } catch {
          remaining.push(tap);
        }
      }
      localStorage.setItem(QUEUE_KEY, JSON.stringify(remaining));
      setPending(remaining);
    } finally {
      busyRef.current = false;
    }
  }, [ensureAssignment]);

  useEffect(() => {
    if (online) void flush();
  }, [online, flush]);

  function queue(tap: QueuedTap) {
    setPending((prev) => {
      const next = [...prev, tap];
      localStorage.setItem(QUEUE_KEY, JSON.stringify(next));
      return next;
    });
  }

  async function start() {
    const at = Date.now();
    setStarted(true);
    setStartedAt(at);
    if (!navigator.onLine) {
      queue({ kind: "start", at });
      return;
    }
    try {
      const id = await ensureAssignment();
      if (!id) throw new Error("no assignment");
      await api.mark(id, "start");
    } catch {
      queue({ kind: "start", at });
    }
  }

  async function finish() {
    setResultOpen(true);
  }

  async function submitResult() {
    setBusy(true);
    try {
      const at = Date.now();
      setDone(true);
      setResultOpen(false);
      if (!navigator.onLine) {
        queue({ kind: "done", at, result });
        return;
      }
      const id = await ensureAssignment();
      if (!id) throw new Error("no assignment");
      await api.mark(id, "done", result);
    } catch {
      queue({ kind: "done", at: Date.now(), result });
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="mx-auto flex min-h-[100dvh] max-w-md flex-col gap-6 px-5 pb-10 pt-8">
      <header className="flex items-center justify-between">
        <Eyebrow>Remote</Eyebrow>
        <span
          data-testid="connection"
          className={`inline-flex items-center gap-2 rounded-full px-3 py-1 text-[10px] uppercase tracking-[0.2em] ${
            online ? "bg-success/10 text-success" : "bg-danger/10 text-danger"
          }`}
        >
          <span className={`h-1.5 w-1.5 rounded-full ${online ? "bg-success" : "bg-danger"}`} />
          {online ? "Live" : "Offline"}
        </span>
      </header>

      <section className="flex flex-col gap-3">
        <Badge tone="accent" className="self-start">{mission.id}</Badge>
        <h1 className="text-balance text-3xl font-semibold leading-tight tracking-tight">
          {mission.hook_text}
        </h1>
        <p className="text-pretty text-sm text-muted">{mission.question}</p>
      </section>

      <section className="flex flex-col gap-3 rounded-lg bg-surface p-1.5 ring-surface">
        <div className="flex flex-col gap-4 rounded-[calc(2rem-0.375rem)] bg-surface-2 p-5">
          <div className="flex items-center justify-between text-xs text-muted">
            <span>Setup</span>
            <span>{mission.est_minutes} min</span>
          </div>
          <p className="text-sm leading-relaxed">{mission.setup}</p>
          <p className="text-sm text-muted">{mission.win_condition}</p>
        </div>
      </section>

      <section className="mt-auto flex flex-col gap-3 pt-6">
        {pending.length > 0 && (
          <p className="text-center text-xs text-danger" data-testid="pending">
            {pending.length} tap{pending.length === 1 ? "" : "s"} queued — will send when back online
          </p>
        )}
        {!started ? (
          <Button
            size="lg"
            data-testid="start"
            data-tour="remote-start"
            onClick={start}
            className="w-full rounded-2xl py-7 text-lg"
          >
            Start
          </Button>
        ) : !done ? (
          <Button
            size="lg"
            variant="outline"
            data-testid="done"
            data-tour="remote-done"
            onClick={finish}
            className="w-full rounded-2xl py-7 text-lg"
          >
            Done
          </Button>
        ) : (
          <div
            data-testid="done-state"
            className="rounded-2xl bg-success/10 py-7 text-center text-lg font-medium text-success"
          >
            Mission logged{result ? ` · ${result}` : ""}
          </div>
        )}
      </section>

      <Dialog open={resultOpen} onClose={() => setResultOpen(false)} title="Result">
        <Field label="Result" hint="A time, a star count, or pass/fail.">
          <Input
            data-testid="result-input"
            value={result}
            onChange={(e) => setResult(e.target.value)}
            placeholder="e.g. 0:41"
          />
        </Field>
        <div className="mt-5 flex justify-end gap-3">
          <Button variant="ghost" onClick={() => setResultOpen(false)}>
            Cancel
          </Button>
          <Button onClick={submitResult} disabled={busy} data-testid="submit-result">
            Save
          </Button>
        </div>
      </Dialog>
    </main>
  );
}
