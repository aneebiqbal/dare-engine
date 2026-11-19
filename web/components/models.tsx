"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { ModelStatus, PullTask } from "@/lib/types";
import {
  Badge,
  Button,
  Card,
  Input,
  Notice,
  PageState,
  Progress,
  Stat,
  StatusDot,
  Table,
  Td,
  Tr,
  useToast,
} from "./ui";

function gb(bytes: number) {
  return bytes > 0 ? `${(bytes / 1e9).toFixed(2)} GB` : "—";
}

export function AdminModels() {
  const toast = useToast();
  const [status, setStatus] = useState<ModelStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [name, setName] = useState("");
  const [task, setTask] = useState<PullTask | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      setStatus(await api.adminModels());
      setError(null);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Could not load models.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
    const id = setInterval(load, 5000);
    return () => clearInterval(id);
  }, [load]);

  useEffect(() => {
    if (!task || task.done) return;
    const id = setInterval(async () => {
      try {
        const next = await api.adminModelPullStatus(task.id);
        setTask(next);
        if (next.done) {
          toast(
            next.error ? `Pull failed: ${next.error}` : `${next.name} ready`,
            next.error ? "danger" : "success",
          );
          load();
        }
      } catch {
        /* keep polling; the bridge may be busy */
      }
    }, 1000);
    return () => clearInterval(id);
  }, [task, load, toast]);

  async function pull() {
    const model = name.trim();
    if (!model) return;
    setBusy(true);
    try {
      setTask(await api.adminModelPull(model));
      setName("");
    } catch (exc) {
      toast(exc instanceof Error ? exc.message : "Pull failed", "danger");
    } finally {
      setBusy(false);
    }
  }

  async function unload(model: string) {
    try {
      await api.adminModelUnload(model);
      toast(`${model} unloaded`, "success");
      load();
    } catch (exc) {
      toast(exc instanceof Error ? exc.message : "Unload failed", "danger");
    }
  }

  async function freeAll() {
    try {
      await api.adminModelFree();
      toast("All models unloaded", "success");
      load();
    } catch (exc) {
      toast(exc instanceof Error ? exc.message : "Free all failed", "danger");
    }
  }

  if (loading) return <PageState loading />;
  if (error && !status) return <PageState error={error} />;

  const engine = status?.engine ?? null;
  const ollama = engine?.ollama ?? null;
  const mlx = engine?.mlx ?? null;
  const host = engine?.host ?? null;
  const running = new Set(ollama?.running.map((r) => r.name) ?? []);
  const vram = (ollama?.running ?? []).reduce((sum, r) => sum + r.size_vram_bytes, 0);
  const models = ollama?.models ?? [];

  return (
    <div className="grid gap-6">
      {status?.bridge === "down" && (
        <Notice tone="warn">
          Local engine bridge is offline, so this page cannot show real models.
          Start it with <code>make mlx-bridge</code>. {status.error ?? ""}
        </Notice>
      )}

      <div className="grid gap-4 sm:grid-cols-2">
        <Card>
          <div className="flex items-center justify-between">
            <span className="text-xs uppercase tracking-[0.2em] text-muted">AI provider</span>
            <Badge tone={status?.provider.configured ? "success" : "muted"}>
              {status?.provider.configured ? "configured" : "not configured"}
            </Badge>
          </div>
          <div className="mt-4 grid gap-3">
            <Stat label="Provider" value={status?.provider.llm_provider ?? "—"} />
            <Stat label="Model" value={status?.provider.llm_model || "—"} />
            <Stat label="Base URL" value={status?.provider.llm_base_url || "—"} />
            <Stat
              label="Transcription"
              value={status?.provider.asr === "mlx" ? "MLX Whisper (Metal)" : "faster-whisper (CPU)"}
              hint={status?.provider.mlx_model}
            />
          </div>
        </Card>

        <Card>
          <div className="flex items-center justify-between">
            <span className="text-xs uppercase tracking-[0.2em] text-muted">Memory</span>
            <StatusDot tone={engine ? "success" : "muted"} label={engine ? "live" : "offline"} />
          </div>
          <div className="mt-4 grid gap-3">
            <Stat
              label="Host RAM"
              value={`${gb(host?.used_bytes ?? 0)} / ${gb(host?.total_bytes ?? 0)}`}
              hint={host ? `${host.percent}% used` : undefined}
            />
            <Stat
              label="Ollama VRAM"
              value={gb(vram)}
              hint={`${running.size} model${running.size === 1 ? "" : "s"} resident`}
            />
            <Stat
              label="MLX peak"
              value={gb(mlx?.peak_memory_bytes ?? 0)}
              hint={mlx?.transcribing ? "transcribing now" : "idle"}
            />
          </div>
        </Card>
      </div>

      <Card>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <span className="text-xs uppercase tracking-[0.2em] text-muted">Local models</span>
            <p className="mt-1 text-sm text-muted">
              Ollama models on this Mac. Pulled and unloaded here; nothing leaves the machine.
            </p>
          </div>
          <Button variant="outline" onClick={freeAll} disabled={!running.size}>
            Free all
          </Button>
        </div>

        <div className="mt-4 flex flex-col gap-2 sm:flex-row">
          <Input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="model name, e.g. qwen3:8b"
            aria-label="Model name"
          />
          <Button onClick={pull} disabled={busy || !name.trim()}>
            Pull model
          </Button>
        </div>

        {task && !task.done && (
          <div className="mt-4">
            <Progress value={task.progress} label={`Pulling ${task.name}`} />
            <p className="mt-2 text-xs text-muted">
              {task.status} · {task.progress}%
            </p>
          </div>
        )}
        {task?.done && task.error && (
          <div className="mt-4">
            <Notice tone="warn">{task.error}</Notice>
          </div>
        )}

        <div className="mt-4">
          <Table head={["Model", "Size", "Status", "Action"]} caption="Local Ollama models">
            {models.length === 0 && (
              <Tr>
                <Td colSpan={4}>No models yet. Pull one above.</Td>
              </Tr>
            )}
            {models.map((m) => (
              <Tr key={m.name}>
                <Td>{m.name}</Td>
                <Td>{gb(m.size_bytes)}</Td>
                <Td>
                  <span className="inline-flex items-center gap-2">
                    <StatusDot
                      tone={running.has(m.name) ? "success" : "muted"}
                      label={running.has(m.name) ? "loaded" : "on disk"}
                    />
                    {running.has(m.name) ? "Loaded" : "On disk"}
                  </span>
                </Td>
                <Td>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => unload(m.name)}
                    disabled={!running.has(m.name)}
                  >
                    Unload
                  </Button>
                </Td>
              </Tr>
            ))}
          </Table>
        </div>
      </Card>
    </div>
  );
}
