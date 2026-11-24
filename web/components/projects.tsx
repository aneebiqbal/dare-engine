"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { api, type PipelineRun, type Project } from "@/lib/api";
import {
  Badge,
  Button,
  Card,
  Field,
  Input,
  Notice,
  PageState,
  Select,
  useToast,
} from "@/components/ui";
import { Pipeline, StatusBadge, WorkHeader, type WorkStatus } from "./work";
import { PipelinePanel } from "./pipeline";
import { PlatformBadge, PlatformSelect, usePlatforms } from "./platforms";

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

function statusFor(p: Project): WorkStatus {
  if (p.stage === "exported") return "done";
  if (p.stage === "analyzing" || p.queued) return "running";
  if (p.stage === "clips_ready" || p.stage === "reviewed") return "needs";
  if (p.stage === "imported") return "needs";
  return "idle";
}

type RecordingOption = { id: string; filename: string };

export function Projects() {
  const [items, setItems] = useState<Project[]>([]);
  const [recordings, setRecordings] = useState<RecordingOption[]>([]);
  const [runs, setRuns] = useState<PipelineRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [platform, setPlatform] = useState("youtube_shorts");
  const [uploadPlatform, setUploadPlatform] = useState("youtube_shorts");
  const [projectPlatforms, setProjectPlatforms] = useState<Record<string, string>>({});
  const platforms = usePlatforms();
  const [busy, setBusy] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [attachFor, setAttachFor] = useState<Record<string, string>>({});
  const fileRef = useRef<HTMLInputElement>(null);
  const toast = useToast();

  const load = useCallback(async (initial = false) => {
    if (initial) setLoading(true);
    try {
      const [p, r, pipe] = await Promise.all([
        api.projects(),
        api.studioRecordings(),
        api.pipelines(),
      ]);
      setItems(p.items);
      setRecordings(r.items);
      setRuns(pipe.items);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load(true);
    const timer = setInterval(() => void load(), 4000);
    return () => clearInterval(timer);
  }, [load]);

  async function create() {
    if (!name.trim()) return;
    setBusy(true);
    try {
      await api.createProject(name.trim(), undefined, platform);
      setName("");
      await load();
      toast("Project created", "success");
    } catch (e) {
      toast(e instanceof Error ? e.message : "Failed", "danger");
    } finally {
      setBusy(false);
    }
  }

  async function uploadVideo(file: File) {
    setUploading(true);
    try {
      const res = await api.pipelineUpload(file, uploadPlatform);
      toast("Uploaded — the pipeline started", "success");
      await load();
      if (fileRef.current) fileRef.current.value = "";
      const el = document.querySelector('[data-testid="pipeline-panel"]');
      el?.scrollIntoView({ behavior: "smooth", block: "start" });
    } catch (e) {
      toast(e instanceof Error ? e.message : "Upload failed", "danger");
    } finally {
      setUploading(false);
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

  async function queue(id: string, vision: boolean, platform?: string) {
    try {
      await api.queueProject(id, vision, platform);
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

  const live = items.some((p) => p.queued || p.stage === "analyzing");
  const counts = STAGES.map((s) => ({
    stage: s,
    label: LABELS[s],
    count: items.filter((p) => p.stage === s).length,
  }));

  return (
    <div className="flex flex-col gap-6" data-tour="admin-projects">
      <WorkHeader
        eyebrow="Create"
        title="Projects"
        status={live ? "running" : "idle"}
        actions={
          <span className="font-mono text-xs text-muted">
            {items.filter((p) => p.queued || p.stage === "analyzing").length} in the analysis lane
          </span>
        }
      />

      <Card>
        <div className="flex flex-col gap-3">
          <span className="text-[10px] uppercase tracking-[0.18em] text-muted">New project</span>
          <div className="flex flex-wrap gap-2">
            <Input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Friday stream — GTA"
              className="sm:max-w-sm"
            />
            <PlatformSelect
              value={platform}
              onChange={setPlatform}
              items={platforms.items}
              label="Project target platform"
            />
            <Button onClick={create} disabled={busy || !name.trim()}>
              Create project
            </Button>
          </div>
          <p className="text-xs text-muted">
            One stream or recording is one project. The target decides clip length and caption
            style. Import a recording and it starts a project automatically.
          </p>
        </div>
      </Card>

      <Card>
        <div className="flex flex-col gap-3">
          <span className="text-[10px] uppercase tracking-[0.18em] text-muted">
            Automatic upload to Shorts
          </span>
          <div className="flex flex-wrap items-center gap-3">
            <input
              ref={fileRef}
              type="file"
              accept="video/*"
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) void uploadVideo(file);
              }}
              className="text-sm text-muted file:mr-3 file:rounded-full file:border-0 file:bg-accent file:px-4 file:py-2 file:text-xs file:font-medium file:text-white"
              aria-label="Upload a video to clip automatically"
              data-testid="pipeline-upload"
            />
            <PlatformSelect
              value={uploadPlatform}
              onChange={setUploadPlatform}
              items={platforms.items}
              label="Upload target platform"
            />
            {uploading && <span className="font-mono text-xs text-muted">uploading…</span>}
          </div>
          <p className="text-xs text-muted">
            Upload one video and walk away: it scans, ranks, vision-scores, cuts, transcribes,
            captions and renders finished 9:16 clips for the target you picked, with no further
            steps. Nothing leaves this Mac.
          </p>
        </div>
      </Card>

      <div className="flex flex-wrap gap-2">
        {counts.map((c) => (
          <span
            key={c.stage}
            className={`rounded-full px-3 py-1 text-[10px] uppercase tracking-[0.14em] ring-surface ${
              c.count ? "bg-accent-soft text-accent" : "bg-surface-2 text-muted"
            }`}
          >
            {c.label} · <span className="font-mono">{c.count}</span>
          </span>
        ))}
      </div>

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
                  <div className="flex min-w-0 flex-col gap-1">
                    <h3 className="truncate text-base font-medium">{p.name}</h3>
                    <span className="font-mono text-xs text-muted">
                      {p.created_at ? new Date(p.created_at).toLocaleString() : "—"}
                    </span>
                  </div>
                  <StatusBadge status={statusFor(p)} label={
                    p.queued ? `Queued #${p.queue_position ?? "…"}` : LABELS[p.stage]
                  } />
                </div>

                <div className="flex flex-wrap items-center gap-2">
                  <PlatformBadge platform={projectPlatforms[p.id] ?? p.platform} items={platforms.items} />
                  <PlatformSelect
                    value={projectPlatforms[p.id] ?? p.platform ?? "youtube_shorts"}
                    onChange={(v) =>
                      setProjectPlatforms((prev) => ({ ...prev, [p.id]: v }))
                    }
                    items={platforms.items}
                    label={`Target platform for ${p.name}`}
                  />
                </div>

                <Pipeline steps={STAGES.map((s) => LABELS[s])} current={p.stage_index} label={`${p.name} stage`} />

                <p className="text-sm text-muted" data-testid={`project-stage-${p.id}`}>
                  {p.stage_note ?? "Waiting for the next step."}
                </p>

                <div className="grid grid-cols-3 gap-2 rounded-xl bg-surface-2 p-2 text-center ring-surface">
                  <div>
                    <div className="font-mono text-base font-semibold">{p.candidates}</div>
                    <div className="text-[10px] uppercase tracking-[0.14em] text-muted">candidates</div>
                  </div>
                  <div>
                    <div className="font-mono text-base font-semibold">
                      {p.clips.ready}/{p.clips.total}
                    </div>
                    <div className="text-[10px] uppercase tracking-[0.14em] text-muted">clips ready</div>
                  </div>
                  <div>
                    <div className="font-mono text-base font-semibold">
                      {p.clips.reviewed}/{p.clips.total}
                    </div>
                    <div className="text-[10px] uppercase tracking-[0.14em] text-muted">reviewed</div>
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

                  <div className="flex flex-wrap items-center gap-3">
                    <Button size="sm" onClick={() => queue(p.id, p.vision, projectPlatforms[p.id] ?? p.platform)} disabled={!p.recording_id}>
                      {p.queued ? "Queued…" : "Run analysis"}
                    </Button>
                    <label className="flex items-center gap-2 text-xs text-muted">
                      <input
                        type="checkbox"
                        checked={p.vision}
                        onChange={(e) => toggleVision(p.id, e.target.checked)}
                        className="h-4 w-4 accent-[var(--accent)]"
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
                  {p.queued && (
                    <p className="font-mono text-xs text-muted">
                      Position {p.queue_position ?? "…"} in the lane — projects analyse one at a time.
                    </p>
                  )}
                </div>
              </div>
            </Card>
          ))}
        </div>
      </PageState>

      {runs.length > 0 && (
        <div className="flex flex-col gap-4">
          <span className="text-[10px] uppercase tracking-[0.18em] text-muted">
            Automatic pipelines · {runs.length}
          </span>
          {runs.map((run) => (
            <Card key={run.id}>
              <PipelinePanel runId={run.id} name={run.name} />
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
