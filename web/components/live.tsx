"use client";

import { useEffect, useState } from "react";
import { api, type Stream } from "@/lib/api";
import { Badge, Button, Card, Field, Input, PageState, useToast } from "@/components/ui";

function masked(key: string) {
  return key.replace(/(.{3}).+(.{3})/, "$1••••••$2");
}

export function Live({ initial }: { initial: Stream | null }) {
  const [stream, setStream] = useState<Stream | null>(initial);
  const [title, setTitle] = useState("Launch day stream");
  const [revealed, setRevealed] = useState(false);
  const [copied, setCopied] = useState<"url" | "key" | null>(null);
  const [busy, setBusy] = useState(false);
  const [connected, setConnected] = useState(false);
  const toast = useToast();

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
    tick();
    const timer = setInterval(tick, 1000);
    return () => {
      alive = false;
      clearInterval(timer);
    };
  }, [stream?.id]);

  async function create() {
    setBusy(true);
    try {
      setStream(await api.createStream(title));
      toast("Stream address issued", "success");
    } catch {
      toast("Could not issue a stream address", "danger");
    } finally {
      setBusy(false);
    }
  }

  async function copy(value: string, which: "url" | "key") {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(which);
      setTimeout(() => setCopied(null), 2000);
    } catch {
      toast("Copy failed", "danger");
    }
  }

  return (
    <PageState loading={busy} error={null} empty={!stream}>
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
      <Card>
        <div className="flex flex-col gap-4">
          <Field label="Stream title">
            <Input value={title} onChange={(e) => setTitle(e.target.value)} />
          </Field>
          <div className="flex flex-wrap items-center gap-4">
            <Button onClick={create} disabled={busy}>
              Issue stream address
            </Button>
            <span className="inline-flex items-center gap-2 text-xs text-success" data-testid="relay-status">
              <span className={`h-1.5 w-1.5 rounded-full ${connected ? "bg-success" : "bg-danger"}`} />
              {connected ? "Relay connected" : "Relay waiting"}
            </span>
          </div>
        </div>
      </Card>
    </PageState>
  );
}
