"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { ModelStatus, ProviderStatus, PullTask } from "@/lib/types";
import {
  Badge,
  Button,
  Card,
  Field,
  Input,
  Notice,
  PageState,
  Progress,
  Select,
  StatusDot,
  Table,
  Td,
  Tr,
  useToast,
} from "./ui";
import { Metric, Section, StatusBadge, WorkHeader } from "./work";

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
  const [provider, setProvider] = useState<ProviderStatus | null>(null);
  const [providerBusy, setProviderBusy] = useState(false);
  const [form, setForm] = useState({
    llm_provider: "openai",
    llm_model: "",
    llm_base_url: "",
    asr: "mlx",
  });

  const load = useCallback(async (initial = false) => {
    if (initial) setLoading(true);
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
    void load(true);
    const id = setInterval(() => void load(), 30_000);
    return () => clearInterval(id);
  }, [load]);

  useEffect(() => {
    api
      .adminProvider()
      .then((p) => {
        setProvider(p);
        setForm({
          llm_provider: p.effective.llm_provider,
          llm_model: p.effective.llm_model,
          llm_base_url: p.effective.llm_base_url,
          asr: p.effective.asr,
        });
      })
      .catch(() => {});
  }, []);

  async function saveProvider() {
    setProviderBusy(true);
    try {
      await api.adminSaveProvider(form);
      setProvider(await api.adminProvider());
      toast("Provider saved", "success");
    } catch (exc) {
      toast(exc instanceof Error ? exc.message : "Could not save the provider", "danger");
    } finally {
      setProviderBusy(false);
    }
  }

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
    }, 2000);
    return () => clearInterval(id);
  }, [task, load, toast]);

  async function pull(target = name.trim()) {
    const model = target.trim();
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
  const available = host ? Math.max(0, host.total_bytes - host.used_bytes) : 0;
  const installed = new Map((ollama?.models ?? []).map((m) => [m.name, m]));
  const llmName = status?.provider.llm_model || "";
  const visionName = status?.provider.vision_model || "";
  // Approximate sizes; the exact number comes from Ollama once it is installed.
  const suggested = [
    {
      role: "Transcription",
      name: status?.provider.mlx_model ?? "—",
      size: 3.0e9,
      state: mlx?.downloaded ? "downloaded" : "not downloaded",
      hint: "MLX · downloads on first use",
      action: null as null | (() => void),
    },
    {
      role: "Writing",
      name: llmName || "not set",
      size: (llmName && installed.get(llmName)?.size_bytes) || 6.0e9,
      state: llmName && installed.has(llmName) ? "on disk" : "not installed",
      hint: "Ollama · the research and caption writer",
      action: llmName && !installed.has(llmName) ? () => pull(llmName) : null,
    },
    {
      role: "Vision",
      name: visionName || "not set",
      size: (visionName && installed.get(visionName)?.size_bytes) || 6.0e9,
      state: visionName && installed.has(visionName) ? "on disk" : "not installed",
      hint: "Ollama · optional clip suggestions",
      action: visionName && !installed.has(visionName) ? () => pull(visionName) : null,
    },
  ];
  const missingGb =
    suggested.filter((s) => s.state === "not installed").reduce((n, s) => n + s.size, 0) / 1e9;

  return (
    <div className="grid gap-6">
      <WorkHeader
        eyebrow="Manage"
        title="Models"
        status={running.size > 0 || (task && !task.done) ? "running" : "idle"}
        actions={
          <span className="font-mono text-xs text-muted">
            {status?.provider.configured ? "provider configured" : "provider not configured"}
          </span>
        }
      />
      {status?.bridge === "down" && (
        <Notice tone="warn">
          Local engine bridge is offline, so this page cannot show real models.
          Start it with <code>make mlx-bridge</code>. {status.error ?? ""}
        </Notice>
      )}

      <div className="grid gap-4 sm:grid-cols-2">
        <Card>
          <div className="flex items-center justify-between">
            <span className="text-xs uppercase tracking-[0.2em] text-muted">Provider picker</span>
            <Badge tone={provider?.effective.configured ? "success" : "muted"}>
              {provider?.env.configured ? "configured" : "not configured"}
            </Badge>
          </div>
          <div className="mt-4 grid gap-3">
            <Field label="Provider">
              <Select
                value={form.llm_provider}
                onChange={(e) => setForm({ ...form, llm_provider: e.target.value })}
              >
                <option value="openai">OpenAI-compatible (cloud or Ollama)</option>
                <option value="recorded">Recorded (CI)</option>
                <option value="stub">Stub</option>
              </Select>
            </Field>
            <Field label="Model" hint="Pick a local Ollama model or type any id.">
              <Input
                list="local-models"
                value={form.llm_model}
                onChange={(e) => setForm({ ...form, llm_model: e.target.value })}
                placeholder="qwen3:8b"
              />
              <datalist id="local-models">
                {(engine?.ollama?.models ?? []).map((m) => (
                  <option key={m.name} value={m.name} />
                ))}
              </datalist>
            </Field>
            <Field label="Base URL">
              <Input
                value={form.llm_base_url}
                onChange={(e) => setForm({ ...form, llm_base_url: e.target.value })}
                placeholder="http://localhost:11434/v1"
              />
            </Field>
            <Field label="Transcription engine">
              <Select
                value={form.asr}
                onChange={(e) => setForm({ ...form, asr: e.target.value })}
              >
                <option value="mlx">MLX Whisper (Metal)</option>
                <option value="cpu">faster-whisper (CPU)</option>
              </Select>
            </Field>
            <div>
              <Button onClick={saveProvider} disabled={providerBusy}>
                Save provider
              </Button>
            </div>
          </div>
        </Card>

        <Card className="sm:col-span-2">
          <div className="flex items-center justify-between">
            <span className="text-xs uppercase tracking-[0.2em] text-muted">Engine</span>
            <StatusDot tone={engine ? "success" : "muted"} label={engine ? "live" : "offline"} />
          </div>
          <div className="mt-4 grid grid-cols-2 gap-4 sm:grid-cols-4">
            <Metric
              label="Host RAM"
              value={`${gb(host?.used_bytes ?? 0)} / ${gb(host?.total_bytes ?? 0)}`}
              hint={host ? `${host.percent}% used` : undefined}
            />
            <Metric label="Ollama VRAM" value={gb(vram)} hint={`${running.size} resident`} />
            <Metric
              label="MLX peak"
              value={gb(mlx?.peak_memory_bytes ?? 0)}
              hint={mlx?.transcribing ? "transcribing now" : "idle"}
            />
            <Metric
              label="MLX model"
              value={mlx?.downloaded ? "downloaded" : "not downloaded"}
              hint={mlx?.downloaded ? mlx.model : "downloaded on first use"}
            />
          </div>
          {task && !task.done && (
            <div className="mt-4">
              <Progress value={task.progress} label={`Pulling ${task.name}`} />
              <p className="mt-2 font-mono text-xs text-muted">
                {task.status} · {task.progress}%
              </p>
            </div>
          )}
          {task?.done && task.error && <div className="mt-4"><Notice tone="warn">{task.error}</Notice></div>}
        </Card>
      </div>

      <Card>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <span className="text-xs uppercase tracking-[0.2em] text-muted">Suggested engine</span>
            <p className="mt-1 text-sm text-muted">
              The three models the engine needs.{" "}
              {missingGb > 0
                ? `≈ ${missingGb.toFixed(1)} GB left to install (approximate).`
                : "All present."}
            </p>
          </div>
        </div>
        <div className="mt-4 flex flex-col gap-2">
          {suggested.map((s) => (
            <div key={s.role} className="flex flex-wrap items-center justify-between gap-3 text-sm">
              <div>
                <span className="font-medium">{s.role}</span>
                <span className="ml-2 text-xs text-muted">{s.name}</span>
                <div className="text-xs text-muted">{s.hint}</div>
              </div>
              <div className="flex items-center gap-2">
                <Badge tone={s.state === "on disk" || s.state === "downloaded" ? "success" : "muted"}>
                  {s.state}
                </Badge>
                <span className="text-xs text-muted">{(s.size / 1e9).toFixed(1)} GB</span>
                {s.action && (
                  <Button size="sm" variant="outline" onClick={() => s.action?.()} disabled={busy}>
                    Install
                  </Button>
                )}
              </div>
            </div>
          ))}
        </div>
      </Card>

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
          <Button onClick={() => pull()} disabled={busy || !name.trim()}>
            Pull model
          </Button>
        </div>

        <div className="mt-4">
          <Table head={["Model", "Size", "Fit", "Status", "Action"]} caption="Local Ollama models">
            {models.length === 0 && (
              <Tr>
                <Td colSpan={5}>No models yet. Pull one above.</Td>
              </Tr>
            )}
            {models.map((m) => {
              const fits = !host || m.size_bytes <= available;
              return (
                <Tr key={m.name}>
                  <Td>{m.name}</Td>
                  <Td>{gb(m.size_bytes)}</Td>
                  <Td>
                    <Badge tone={fits ? "success" : "danger"}>
                      {fits ? "Fits this Mac" : `Needs ${gb(m.size_bytes - available)} free`}
                    </Badge>
                  </Td>
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
              );
            })}
          </Table>
        </div>
      </Card>
    </div>
  );
}
