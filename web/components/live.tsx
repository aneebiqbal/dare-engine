"use client";

import { useEffect, useState } from "react";
import { api, type ObsStatus, type Stream } from "@/lib/api";
import { NextStep } from "./next-step";
import { Badge, Button, Card, Field, Input, PageState, Progress, StatusDot, useToast } from "@/components/ui";

function masked(key: string | null) {
  if (!key || key.length <= 6) return "••••••";
  return key.replace(/(.{3}).+(.{3})/, "$1••••••$2");
}

const CHECK_KEY = "clipdesk.live-checklist";

export function Live({ initial }: { initial: Stream | null }) {
  const [stream, setStream] = useState<Stream | null>(initial);
  const [title, setTitle] = useState("Launch day stream");
  const [revealed, setRevealed] = useState(false);
  const [copied, setCopied] = useState<"url" | "key" | null>(null);
  const [busy, setBusy] = useState(false);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [checked, setChecked] = useState<string[]>([]);
  const [obs, setObs] = useState<ObsStatus | null>(null);
  const [obsError, setObsError] = useState<string | null>(null);
  const [snapTick, setSnapTick] = useState(0);
  const [snapOk, setSnapOk] = useState(true);
  const toast = useToast();

  useEffect(() => {
    try {
      const saved = JSON.parse(localStorage.getItem(CHECK_KEY) ?? "[]");
      if (Array.isArray(saved)) setChecked(saved);
    } catch {
      /* ignore */
    }
  }, []);

  useEffect(() => {
    let alive = true;
    let timer: ReturnType<typeof setTimeout>;
    const loop = async () => {
      try {
        const status = await api.obsStatus();
        if (alive) {
          setObs(status);
          setObsError(null);
        }
      } catch (e) {
        if (alive) setObsError(e instanceof Error ? e.message : "Failed to read OBS");
      }
      if (alive) timer = setTimeout(loop, 3000);
    };
    void loop();
    const snap = setInterval(() => setSnapTick((t) => t + 1), 5000);
    return () => {
      alive = false;
      clearTimeout(timer);
      clearInterval(snap);
    };
  }, []);

  useEffect(() => {
    if (!stream) {
      setError(null);
      void create();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [stream]);

  useEffect(() => {
    if (!stream?.id) return;
    let alive = true;
    const tick = async () => {
      try {
        const status = (await api.streamStatus(stream.id)) as { connected?: boolean };
        if (alive) setConnected(Boolean(status.connected));
      } catch {
        if (alive) setConnected(false);
      }
    };
    let timer: ReturnType<typeof setTimeout>;
    const loop = async () => {
      await tick();
      if (alive) timer = setTimeout(loop, 2500);
    };
    void loop();
    return () => {
      alive = false;
      clearTimeout(timer);
    };
  }, [stream?.id]);

  async function create() {
    setBusy(true);
    setError(null);
    try {
      setStream(await api.createStream(title));
      toast("Stream address issued", "success");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not issue a stream address");
    } finally {
      setBusy(false);
    }
  }

  async function copy(value: string, which: "url" | "key") {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(which);
      setTimeout(() => setCopied(null), 2000);
      toast(which === "url" ? "Address copied" : "Key copied", "success");
    } catch {
      toast("Copy failed", "danger");
    }
  }

  function toggleCheck(id: string) {
    setChecked((prev) => {
      const next = prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id];
      localStorage.setItem(CHECK_KEY, JSON.stringify(next));
      return next;
    });
  }

  const checks = [
    { id: "address", label: "Stream address issued", done: Boolean(stream) },
    { id: "relay", label: "Relay reachable", done: connected },
    { id: "obs", label: "OBS connected", done: Boolean(obs?.connected) },
    { id: "recording", label: "Recording on", done: Boolean(obs?.recording) },
    { id: "hdcp", label: "HDCP off", done: checked.includes("hdcp"), manual: true },
    { id: "mic", label: "Mic level checked", done: checked.includes("mic"), manual: true },
    { id: "radio", label: "Radio off", done: checked.includes("radio"), manual: true },
  ];
  const done = checks.filter((c) => c.done).length;

  return (
    <div className="flex flex-col gap-6">
      <PageState loading={busy && !stream} error={error} empty={false}>
        {stream && (
          <div className="grid gap-4 lg:grid-cols-2">
            <Card>
              <div className="flex flex-col gap-4">
                <Badge tone="accent">Stream address</Badge>
                <code className="break-all rounded-xl bg-bg p-4 text-xs text-muted">
                  {stream.rtmp_url}
                </code>
                <Button variant="outline" size="sm" onClick={() => copy(stream.rtmp_url, "url")}>
                  {copied === "url" ? "Copied" : "Copy address"}
                </Button>
              </div>
            </Card>
            <Card>
              <div className="flex flex-col gap-4">
                <Badge tone="accent">Stream key</Badge>
                <code className="break-all rounded-xl bg-bg p-4 text-xs text-muted">
                  {revealed ? stream.stream_key : masked(stream.stream_key)}
                </code>
                <div className="flex gap-2">
                  <Button variant="outline" size="sm" onClick={() => setRevealed((v) => !v)}>
                    {revealed ? "Hide" : "Reveal"}
                  </Button>
                  <Button variant="outline" size="sm" onClick={() => copy(stream.stream_key, "key")}>
                    {copied === "key" ? "Copied" : "Copy key"}
                  </Button>
                </div>
              </div>
            </Card>
          </div>
        )}
      </PageState>

      <Card>
        <div className="flex flex-col gap-4">
          <div className="flex items-center justify-between gap-3">
            <h2 className="text-base font-medium">OBS</h2>
            <span
              className="inline-flex items-center gap-2 text-xs"
              role="status"
              aria-live="polite"
              data-testid="obs-status"
            >
              <StatusDot
                tone={obs?.connected ? "success" : "danger"}
                label={obs?.connected ? "OBS connected" : "OBS not connected"}
              />
              {obs?.connected ? "Connected" : "Not connected"}
            </span>
          </div>
          {obsError ? (
            <p className="text-sm text-danger" role="alert">{obsError}</p>
          ) : !obs ? (
            <p className="text-sm text-muted">Reading OBS…</p>
          ) : !obs.connected ? (
            <div className="flex flex-col gap-2">
              <p className="text-sm text-danger" role="alert">
                OBS is not reachable over its WebSocket.
              </p>
              {obs.detail && <p className="text-xs text-muted">{obs.detail}</p>}
              {obs.how_to_enable && <p className="text-xs text-muted">{obs.how_to_enable}</p>}
            </div>
          ) : (
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="flex flex-col gap-2 text-sm">
                <span className="text-muted">
                  OBS {obs.obs_version} · WebSocket {obs.websocket_version}
                </span>
                <span>Scene · <strong>{obs.scene ?? "—"}</strong></span>
                <span>Streaming · {obs.streaming ? "live" : "idle"}</span>
                <span>
                  Recording · {obs.recording ? (obs.record_paused ? "paused" : "on") : "off"}
                </span>
                {(obs.audio_inputs ?? []).map((i) => (
                  <span key={i.name}>
                    Mic · {i.name} {i.muted ? "muted" : "live"}
                  </span>
                ))}
              </div>
              <div className="flex flex-col gap-2">
                <span className="text-xs text-muted">
                  Preview — periodic snapshot, not a live video feed.
                </span>
                {snapOk ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={`${api.obsSnapshotUrl()}?t=${snapTick}`}
                    alt="OBS program scene snapshot"
                    className="w-full rounded-xl bg-bg object-cover ring-surface"
                    onError={() => setSnapOk(false)}
                  />
                ) : (
                  <div className="flex h-40 items-center justify-center rounded-xl bg-bg text-xs text-muted ring-surface">
                    Snapshot unavailable — OBS is connected but the scene screenshot failed.
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </Card>

      <Card>
        <div className="flex flex-col gap-4">
          <h2 className="text-base font-medium">Before you go live</h2>
          <div className="flex flex-col gap-2">
            {checks.map((item) => (
              <div key={item.id} className="flex items-center gap-3 text-sm">
                <StatusDot
                  tone={item.done ? "success" : "muted"}
                  label={item.done ? `${item.label} done` : `${item.label} not done`}
                />
                <span className={item.done ? "text-text" : "text-muted"}>{item.label}</span>
                {item.manual && (
                  <label className="ml-auto flex items-center gap-2 text-xs text-muted">
                    <input
                      type="checkbox"
                      checked={item.done}
                      onChange={() => toggleCheck(item.id)}
                      className="h-4 w-4 accent-[var(--accent)]"
                    />
                    Mark done
                  </label>
                )}
              </div>
            ))}
          </div>
          <Progress value={(done / checks.length) * 100} label="Pre-stream checklist" />
          <span className="text-xs text-muted">
            {done} of {checks.length} complete
          </span>
        </div>
      </Card>

      <Card>
        <div className="flex flex-col gap-4">
          <Field label="Stream title">
            <Input value={title} onChange={(e) => setTitle(e.target.value)} />
          </Field>
          <div className="flex flex-wrap items-center gap-4">
            <Button onClick={create} disabled={busy}>
              {stream ? "Issue a new address" : "Issue stream address"}
            </Button>
            <span
              className="inline-flex items-center gap-2 text-xs text-success"
              data-testid="relay-status"
              role="status"
              aria-live="polite"
            >
              <StatusDot tone={connected ? "success" : "danger"} label={connected ? "connected" : "waiting"} />
              {connected ? "Relay connected" : "Relay waiting"}
            </span>
          </div>
        </div>
      </Card>

      <NextStep
        href="/remote"
        title="Open the phone remote"
        body="Tap Start when the moment begins and Done when it ends."
      />
    </div>
  );
}
