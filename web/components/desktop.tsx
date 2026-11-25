"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { Badge, Button, Card, Notice } from "./ui";

type Invoke = (cmd: string, args?: Record<string, unknown>) => Promise<unknown>;

/** Only renders inside the Tauri desktop app. In a browser it is absent. */
function tauriInvoke(): Invoke | null {
  if (typeof window === "undefined") return null;
  const w = window as unknown as { __TAURI_INTERNALS__?: { invoke?: Invoke } };
  return w.__TAURI_INTERNALS__?.invoke ?? null;
}

/**
 * The desktop-only engine controls: start the local stack, record the screen,
 * and drop the recording straight into the studio. Nothing leaves the machine.
 */
export function DesktopEngine({ onRecording }: { onRecording: (id: string) => void }) {
  const invoke = tauriInvoke();
  const [busy, setBusy] = useState(false);
  const [recording, setRecording] = useState(false);
  const [path, setPath] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  if (!invoke) return null;

  const run = async (cmd: string, args?: Record<string, unknown>) => {
    try {
      return await invoke(cmd, args);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : String(exc));
      return null;
    }
  };

  async function startStack() {
    setBusy(true);
    setError(null);
    setMessage(null);
    const out = await run("start_stack");
    setMessage(out ? "Local engine started. The app is on http://localhost:3100." : null);
    setBusy(false);
  }

  async function toggleRecord() {
    setError(null);
    setMessage(null);
    if (recording) {
      await run("capture_stop");
      setRecording(false);
      if (path) {
        setBusy(true);
        const imported = await importRecording(path);
        setBusy(false);
        if (imported) onRecording(imported);
      }
      return;
    }
    const dir = (await run("recordings_dir")) as string | null;
    if (!dir) return;
    const out = `${dir.replace(/\/$/, "")}/clipdesk-${Date.now()}.mp4`;
    const started = await run("capture_start", { out_path: out, device: "1:0" });
    if (started) {
      setRecording(true);
      setPath(out);
      setMessage("Recording. Press stop when the moment is over.");
    }
  }

  async function importRecording(file: string): Promise<string | null> {
    const b64 = (await run("read_file_b64", { path: file })) as string | null;
    if (!b64) return null;
    const bin = atob(b64);
    const bytes = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i += 1) bytes[i] = bin.charCodeAt(i);
    const name = file.split("/").pop() ?? "recording.mp4";
    const res = await api.studioUpload(
      new File([bytes], name, { type: "video/mp4" }),
    );
    return res.recording_id;
  }

  return (
    <Card>
      <div className="flex flex-col gap-3">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-medium">Desktop engine</h2>
          <Badge tone="accent">this Mac</Badge>
        </div>
        <p className="text-sm text-muted">
          Start the local stack and record the screen. The recording is imported
          into the studio on this machine — it is never uploaded.
        </p>
        {error && <Notice tone="warn">{error}</Notice>}
        {message && <Notice tone="info">{message}</Notice>}
        <div className="flex flex-wrap gap-2">
          <Button variant="outline" onClick={startStack} disabled={busy}>
            Start local engine
          </Button>
          <Button onClick={toggleRecord} disabled={busy}>
            {recording ? "Stop recording" : "Record screen"}
          </Button>
        </div>
      </div>
    </Card>
  );
}
