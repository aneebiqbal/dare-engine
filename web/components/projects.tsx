"use client";

import { useCallback, useEffect, useState } from "react";
import { api, type Project } from "@/lib/api";
import {
  Badge,
  Button,
  Card,
  EmptyState,
  Field,
  Input,
  Notice,
  PageState,
  Progress,
  Select,
  useToast,
} from "@/components/ui";

const STAGES = [
  "planned",
  "recording",
  "imported",
  "analyzing",
  "clips_ready",
  "reviewed",
  "exported",
] as const;

const LABELS: Record<string, string> = {
  planned: "Planned",
  recording: "Recording",
  imported: "Imported",
  analyzing: "Analyzing",
  clips_ready: "Clips ready",
  reviewed: "Reviewed",
  exported: "Exported",
};

type RecordingOption = { id: string; filename: string };

export function Projects() {
  const [items, setItems] = useState<Project[]>([]);
  const [recordings, setRecordings] = useState<RecordingOption[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const [attachFor, setAttachFor] = useState<Record<string, string>>({});
  const toast = useToast();

  const load = useCallback(async () => {
    try {
      const [p, r] = await Promise.all([api.projects(), api.studioRecordings()]);
      setItems(p.items);
      setRecordings(r.items);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
    const timer = setInterval(() => void load(), 5000);
    return () => clearInterval(timer);
  }, [load]);

  async function create() {
    if (!name.trim()) return;
    setBusy(true);
    try {
      await api.createProject(name.trim());
      setName("");
      await load();
      toast("Project created", "success");
    } catch (e) {
      toast(e instanceof Error ? e.message : "Failed", "danger");
    } finally {
      setBusy(false);
    }
  }

  async function attach(id: string) {
    const recording_id = attachFor[id];
    if (!recording_id) return;
    try {
      await api.attachProject(id, recording_id);
      await load();
      toast("Recording attached", "success");
    } catch (e) {
      toast(e instanceof Error ? e.message : "Failed", "danger");
    }
  }

  async function queue(id: string, vision: boolean) {
    try {
      await api.queueProject(id, vision);
      await load();
      toast("Queued for analysis", "success");
    } catch (e) {
      toast(e instanceof Error ? e.message : "Failed", "danger");
    }
  }

  async function toggleVision(id: string, vision: boolean) {
    try {
      await api.setProjectVision(id, vision);
      await load();
    } catch (e) {
      toast(e instanceof Error ? e.message : "Failed", "danger");
    }
  }

  async function remove(id: string) {
    try {
      await api.deleteProject(id);
      await load();
      toast("Project deleted", "success");
    } catch (e) {
      toast(e instanceof Error ? e.message : "Failed", "danger");
    }
  }

  return (
    <div className="flex flex-col gap-6" data-tour="admin-projects">
      <Card>
        <div className="flex flex-col gap-3">
          <Field label="New project" hint="One stream or recording is one project. It moves through the stages below.">
            <div className="flex gap-2">
              <Input
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Friday stream — GTA"
              />
              <Button onClick={create} disabled={busy || !name.trim()}>
                Create project
              </Button>
            </div>
          </Field>
        </div>
      </Card>

      <PageState
        loading={loading}
        error={error}
        empty={items.length === 0}
        emptyTitle="No projects yet"
        emptyBody="Create a project, or import a recording — it starts one automatically."
      >
        <div className="grid gap-4 lg:grid-cols-2">
          {items.map((p) => (
            <Card key={p.id}>
              <div className="flex h-full flex-col gap-4">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex flex-col gap-1">
                    <h3 className="text-base font-medium">{p.name}</h3>
                    <span className="text-xs text-muted">
                      {p.created_at ? new Date(p.created_at).toLocaleString() : "—"}
                    </span>
                  </div>
                  <Badge tone={p.stage === "exported" ? "success" : p.queued ? "accent" : "muted"}>
                    {p.queued ? `Queued #${p.queue_position ?? "…"}` : LABELS[p.stage]}
                  </Badge>
                </div>

                <div className="flex flex-col gap-2">
                  <Progress value={p.progress} label={`${p.name} progress`} />
                  <div className="flex flex-wrap gap-1">
                    {STAGES.map((s, i) => (
                      <Badge key={s} tone={i <= p.stage_index ? "accent" : "muted"}>
                        {LABELS[s]}
                      </Badge>
                    ))}
                  </div>
                </div>

                <p className="text-sm text-muted" data-testid={`project-stage-${p.id}`}>
                  {p.stage_note ?? "Waiting for the next step."}
                </p>

                <div className="grid grid-cols-3 gap-2 text-center text-xs">
                  <div className="rounded-xl bg-surface-2 p-2">
                    <div className="text-base font-medium">{p.candidates}</div>
                    <div className="text-muted">candidates</div>
                  </div>
                  <div className="rounded-xl bg-surface-2 p-2">
                    <div className="text-base font-medium">{p.clips.ready}/{p.clips.total}</div>
                    <div className="text-muted">clips ready</div>
                  </div>
                  <div className="rounded-xl bg-surface-2 p-2">
                    <div className="text-base font-medium">{p.clips.reviewed}/{p.clips.total}</div>
                    <div className="text-muted">reviewed</div>
                  </div>
                </div>

                <div className="mt-auto flex flex-col gap-3">
                  {!p.recording_id && (
                    <Field label="Attach a recording">
                      <div className="flex gap-2">
                        <Select
                          aria-label={`Recording for ${p.name}`}
                          value={attachFor[p.id] ?? ""}
                          onChange={(e) =>
                            setAttachFor((prev) => ({ ...prev, [p.id]: e.target.value }))
                          }
                        >
                          <option value="">Choose a recording…</option>
                          {recordings.map((r) => (
                            <option key={r.id} value={r.id}>
                              {r.filename}
                            </option>
                          ))}
                        </Select>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => attach(p.id)}
                          disabled={!attachFor[p.id]}
                        >
                          Attach
                        </Button>
                      </div>
                    </Field>
                  )}

                  <div className="flex flex-wrap items-center gap-2">
                    <Button size="sm" onClick={() => queue(p.id, p.vision)} disabled={!p.recording_id}>
                      {p.queued ? "Queued…" : "Run analysis"}
                    </Button>
                    <label className="flex items-center gap-2 text-xs text-muted">
                      <input
                        type="checkbox"
                        checked={p.vision}
                        onChange={(e) => toggleVision(p.id, e.target.checked)}
                      />
                      Vision pass
                    </label>
                    <Button
                      size="sm"
                      variant="danger"
                      onClick={() => remove(p.id)}
                      className="ml-auto"
                    >
                      Delete
                    </Button>
                  </div>
                  {p.vision && (
                    <Notice tone="warn">
                      The vision pass is sampled, off unless you enable it, and unloads the model
                      when it finishes.
                    </Notice>
                  )}
                </div>
              </div>
            </Card>
          ))}
        </div>
      </PageState>
    </div>
  );
}
