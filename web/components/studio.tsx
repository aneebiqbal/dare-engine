"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { api, type Clip, type MissionCard, type SsdResponse, type StudioCandidate, type StudioRecording, type SystemLoad } from "@/lib/api";
import { NextStep } from "./next-step";
import {
  Badge,
  Button,
  Card,
  EmptyState,
  Field,
  Input,
  Notice,
  Progress,
  Select,
  useToast,
} from "@/components/ui";

const TEMPLATES = ["cold_open", "center", "punch", "clean", "wide"];

type Window = { candidate_id: string; start: number; end: number; template_id: string | null };

export function Studio() {
  const [recording, setRecording] = useState<StudioRecording | null>(null);
  const [templates, setTemplates] = useState<string[]>(TEMPLATES);
  const [captionStyles, setCaptionStyles] = useState<string[]>(["word", "line", "pop"]);
  const [clipEdits, setClipEdits] = useState<Record<string, { template: string; captions: string }>>({});
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [detecting, setDetecting] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [missions, setMissions] = useState<MissionCard[]>([]);
  const [missionId, setMissionId] = useState("");
  const [load, setLoad] = useState<SystemLoad | null>(null);
  const [clips, setClips] = useState<Clip[]>([]);
  const [edits, setEdits] = useState<Record<string, { start: string; end: string; template: string }>>({});
  const [playing, setPlaying] = useState<string | null>(null);
  const [ssd, setSsd] = useState<SsdResponse | null>(null);
  const [ssdBusy, setSsdBusy] = useState(false);
  const [importing, setImporting] = useState<string | null>(null);
  const [release, setRelease] = useState(true);
  const videoRef = useRef<HTMLVideoElement>(null);
  const toast = useToast();

  useEffect(() => {
    api.studioTemplates()
      .then((d) => {
        setTemplates(d.templates.map((t) => t.id));
        setCaptionStyles(Object.keys(d.caption_styles));
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    Promise.all([
      api.pool("?status=unverified"),
      api.pool("?status=candidate"),
    ])
      .then(([unverified, candidate]) => {
        const all = [...unverified.items, ...candidate.items].map((e) => e.card);
        setMissions(all);
        setMissionId((prev) => prev || all[0]?.id || "");
      })
      .catch(() => {});
  }, []);

  // Real system load, never a fake gauge.
  useEffect(() => {
    const tick = () => api.studioSystem().then(setLoad).catch(() => {});
    tick();
    const timer = setInterval(tick, 2000);
    return () => clearInterval(timer);
  }, []);

  const refreshClips = useCallback(async (ids: string[]) => {
    const res = await api.clips("?page_size=50");
    setClips(res.items.filter((c) => ids.includes(c.id)));
    return res.items;
  }, []);

  async function upload() {
    if (!file) {
      setError("Choose a recording first.");
      return;
    }
    setError(null);
    setNotice(null);
    setUploading(true);
    try {
      const res = await api.studioUpload(file);
      const detail = await api.studioRecording(res.recording_id);
      setRecording(detail);
      setClips([]);
      setEdits({});
      setFile(null);
      toast("Recording ready", "success");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  }

  async function refreshSsd() {
    setSsdBusy(true);
    setError(null);
    try {
      setSsd(await api.studioSsd());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not read the drives");
    } finally {
      setSsdBusy(false);
    }
  }

  async function importSsd(path: string) {
    setImporting(path);
    setError(null);
    setNotice(null);
    try {
      const res = await api.studioSsdImport(path, release);
      const detail = await api.studioRecording(res.recording_id);
      setRecording(detail);
      setClips([]);
      setEdits({});
      toast(
        res.released ? "Imported from SSD and released the copy" : "Imported from SSD",
        "success",
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : "Import failed");
    } finally {
      setImporting(null);
    }
  }

  async function findMoments() {
    if (!recording) return;
    setError(null);
    setDetecting(true);
    try {
      await api.studioDetect(recording.recording.id, 5);
      for (let i = 0; i < 120; i++) {
        await new Promise((r) => setTimeout(r, 2000));
        const detail = await api.studioRecording(recording.recording.id);
        setRecording(detail);
        if (detail.candidates.length && detail.compute.whisper_device) break;
      }
      setNotice("Moments found. Accept the ones you want, then generate.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Detection failed");
    } finally {
      setDetecting(false);
    }
  }

  function edit(id: string, patch: Partial<{ start: string; end: string; template: string }>) {
    setEdits((prev) => {
      const cur = prev[id] ?? { start: "", end: "", template: "" };
      return { ...prev, [id]: { ...cur, ...patch } };
    });
  }

  function candidateState(c: StudioCandidate) {
    const e = edits[c.id];
    return {
      start: e?.start !== "" && e?.start != null ? Number(e.start) : c.start,
      end: e?.end !== "" && e?.end != null ? Number(e.end) : c.end,
      template: e?.template || c.template_id || "cold_open",
    };
  }

  function acceptTop(n: number) {
    if (!recording) return;
    setRecording({
      ...recording,
      candidates: recording.candidates.map((c, i) => ({
        ...c,
        state: i < n ? "accepted" : c.state === "accepted" ? "accepted" : "rejected",
      })),
    });
  }

  function play(c: StudioCandidate) {
    if (!recording) return;
    const v = videoRef.current;
    if (!v) return;
    v.src = api.studioRecordingUrl(recording.recording.id);
    v.currentTime = candidateState(c).start;
    void v.play();
    setPlaying(c.id);
    v.onended = () => setPlaying(null);
  }

  async function generate() {
    if (!recording) return;
    const windows: Window[] = recording.candidates
      .filter((c) => c.state === "accepted")
      .map((c) => {
        const s = candidateState(c);
        return { candidate_id: c.id, start: s.start, end: s.end, template_id: s.template };
      });
    if (!windows.length) {
      setError("Accept at least one moment.");
      return;
    }
    setError(null);
    setGenerating(true);
    try {
      const res = await api.studioGenerate(recording.recording.id, missionId, windows);
      for (let i = 0; i < 120; i++) {
        await new Promise((r) => setTimeout(r, 3000));
        const items = await refreshClips(res.clips);
        if (res.clips.every((id) => items.find((c) => c.id === id)?.state === "ready")) break;
      }
      const detail = await api.studioRecording(recording.recording.id);
      setRecording(detail);
      toast("Clips ready", "success");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Generate failed");
    } finally {
      setGenerating(false);
    }
  }

  async function rerender(clip: Clip) {
    const edit = clipEdits[clip.id] ?? { template: "cold_open", captions: "word" };
    try {
      await api.updateClip(clip.id, {
        template_id: edit.template,
        caption_style: edit.captions,
      });
      for (let i = 0; i < 60; i++) {
        await new Promise((r) => setTimeout(r, 3000));
        const items = await refreshClips([clip.id]);
        const fresh = items.find((c) => c.id === clip.id);
        if (fresh && fresh.state === "ready") {
          setClips((prev) => prev.map((c) => (c.id === clip.id ? fresh : c)));
          break;
        }
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Re-render failed");
    }
  }

  const idle = !uploading && !detecting && !generating;
  const rendering = clips.some((c) => !["ready", "approved", "posted", "discarded", "failed"].includes(c.state));

  return (
    <div className="flex flex-col gap-6">
      <Card>
        <div className="flex flex-col gap-4" data-tour="studio-upload">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-medium">Recording</h2>
            <Badge tone="muted">Local only · nothing uploads</Badge>
          </div>
          <div className="grid gap-4 md:grid-cols-[1fr_1fr]">
            <Field label="File">
              <Input
                type="file"
                accept="video/*,audio/*"
                data-testid="studio-file"
                onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              />
            </Field>
            {recording && (
              <div className="flex flex-col justify-center gap-1 text-sm text-muted">
                <span className="text-text">{recording.recording.filename}</span>
                <span>
                  {recording.recording.duration_seconds.toFixed(1)}s ·{" "}
                  {recording.recording.width}×{recording.recording.height}
                </span>
              </div>
            )}
          </div>
          {uploading && <Progress value={50} />}
          {error && <Notice tone="warn">{error}</Notice>}
          {notice && <Notice tone="info">{notice}</Notice>}
          <div className="flex flex-wrap gap-2">
            <Button onClick={upload} disabled={uploading || !file} data-testid="studio-upload">
              {uploading ? "Uploading…" : "Upload recording"}
            </Button>
            <Button
              variant="ghost"
              onClick={findMoments}
              disabled={!recording || detecting}
              data-testid="studio-find"
            >
              {detecting ? "Finding moments…" : "Find moments"}
            </Button>
          </div>
        </div>
      </Card>

      <Card>
        <div className="flex flex-col gap-4">
          <div className="flex items-center justify-between gap-3">
            <h2 className="text-base font-medium">Import from SSD</h2>
            <Button size="sm" variant="outline" onClick={refreshSsd} disabled={ssdBusy}>
              {ssdBusy ? "Reading…" : "Refresh drives"}
            </Button>
          </div>
          <label className="flex items-start gap-2 text-xs text-muted">
            <input
              type="checkbox"
              checked={release}
              onChange={(e) => setRelease(e.target.checked)}
              className="mt-0.5 h-4 w-4 accent-[var(--accent)]"
            />
            <span>
              Process and release — delete the inbox copy after import so the disk never
              fills. The clip is already safe in local storage.
            </span>
          </label>
          {!ssd ? (
            <p className="text-sm text-muted">Plug in a drive and press Refresh drives.</p>
          ) : ssd.error ? (
            <Notice tone="warn">
              {ssd.error} {ssd.how_to}
            </Notice>
          ) : !ssd.enabled ? (
            <Notice tone="warn">{ssd.reason}</Notice>
          ) : ssd.drives.length === 0 ? (
            <EmptyState
              title="No external drive mounted"
              body="Plug in an SSD or USB drive, then refresh."
            />
          ) : (
            ssd.drives.map((drive) => (
              <div key={drive.path} className="flex flex-col gap-2">
                <div className="flex items-center gap-2">
                  <Badge tone="accent">{drive.name}</Badge>
                  <span className="text-xs text-muted">{drive.videos.length} video(s)</span>
                </div>
                {drive.error && <Notice tone="warn">{drive.error}</Notice>}
                {drive.videos.length === 0 && (
                  <p className="text-xs text-muted">No videos found at the top level of this drive.</p>
                )}
                {drive.videos.map((video) => (
                  <div key={video.path} className="flex items-center justify-between gap-3 text-sm">
                    <span className="min-w-0 truncate">{video.name}</span>
                    <span className="shrink-0 text-xs text-muted">
                      {video.error
                        ? video.error
                        : `${(video.size_bytes / 1e6).toFixed(1)} MB · ${video.duration_seconds?.toFixed(1)}s · ${video.width}×${video.height}`}
                    </span>
                    <Button
                      size="sm"
                      variant="outline"
                      disabled={importing === video.path || Boolean(video.error)}
                      onClick={() => importSsd(video.path)}
                    >
                      {importing === video.path ? "Importing…" : "Import"}
                    </Button>
                  </div>
                ))}
              </div>
            ))
          )}
        </div>
      </Card>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <div className="flex flex-col gap-2">
            <h3 className="text-sm font-medium">Compute path</h3>
            <div data-testid="studio-compute" className="flex flex-wrap gap-2">
              <Badge tone={recording?.compute.gpu ? "success" : "muted"}>
                {recording?.compute.gpu ? "GPU" : "CPU"}
              </Badge>
              <Badge tone="muted">whisper {recording?.compute.whisper_device ?? "—"}</Badge>
              <Badge tone="muted">encode {recording?.compute.encoder ?? "—"}</Badge>
            </div>
          </div>
        </Card>
        <Card>
          <div className="flex flex-col gap-2">
            <h3 className="text-sm font-medium">System load</h3>
            <div className="flex flex-wrap items-center gap-3 text-sm text-muted">
              <span>CPU {load?.cpu_percent ?? "—"}%</span>
              <span>Memory {load?.memory_percent ?? "—"}%</span>
              <span>GPU {load?.gpu ? `${load.gpu.utilization_percent}%` : "none"}</span>
            </div>
            <div data-testid="studio-idle" className="text-xs text-muted">
              {idle && !rendering ? "Idle — no jobs running" : "Working…"}
            </div>
          </div>
        </Card>
      </div>

      {recording && recording.candidates.length > 0 && (
        <Card>
          <div className="flex flex-col gap-4">
            <div className="flex items-center justify-between">
              <h2 className="text-base font-medium">Moments</h2>
              <div className="flex gap-2">
                <Button variant="ghost" onClick={() => acceptTop(1)} data-testid="studio-accept-top">
                  Accept top 1
                </Button>
                <Button variant="ghost" onClick={() => acceptTop(3)}>
                  Accept top 3
                </Button>
              </div>
            </div>
            <div className="flex flex-col gap-3">
              {recording?.candidates.map((c, i) => {
                const s = candidateState(c);
                return (
                  <div
                    key={c.id}
                    data-testid={`studio-candidate-${i}`}
                    className="flex flex-col gap-3 rounded-lg p-3 ring-surface"
                  >
                    <div className="flex flex-wrap items-center gap-3">
                      <Badge tone={c.state === "accepted" ? "success" : c.state === "rejected" ? "danger" : "muted"}>
                        {c.state}
                      </Badge>
                      <span className="text-sm font-medium">#{i + 1} · score {c.score.toFixed(2)}</span>
                      <span className="text-xs text-muted">{c.reasons.join(", ")}</span>
                    </div>
                    <div className="grid gap-3 sm:grid-cols-[80px_80px_1fr_auto_auto_auto]">
                      <Input
                        aria-label="Start seconds"
                        value={edits[c.id]?.start ?? String(c.start)}
                        onChange={(e) => edit(c.id, { start: e.target.value })}
                      />
                      <Input
                        aria-label="End seconds"
                        value={edits[c.id]?.end ?? String(c.end)}
                        onChange={(e) => edit(c.id, { end: e.target.value })}
                      />
                      <Select
                        aria-label="Template"
                        value={s.template}
                        onChange={(e) => edit(c.id, { template: e.target.value })}
                      >
                        {templates.map((t) => (
                          <option key={t} value={t}>
                            {t}
                          </option>
                        ))}
                      </Select>
                      <Button variant="ghost" onClick={() => play(c)} data-testid={`studio-play-${i}`}>
                        {playing === c.id ? "Playing" : "Play"}
                      </Button>
                      <Button
                        variant="ghost"
                        onClick={() =>
                          setRecording((prev) => prev && {
                            ...prev,
                            candidates: prev.candidates.map((x) =>
                              x.id === c.id ? { ...x, state: "accepted" } : x,
                            ),
                          })
                        }
                      >
                        Accept
                      </Button>
                      <Button
                        variant="danger"
                        onClick={() =>
                          setRecording((prev) => prev && {
                            ...prev,
                            candidates: prev.candidates.map((x) =>
                              x.id === c.id ? { ...x, state: "rejected" } : x,
                            ),
                          })
                        }
                      >
                        Reject
                      </Button>
                    </div>
                  </div>
                );
              })}
            </div>
            <video ref={videoRef} controls className="hidden" />
            <div className="flex flex-wrap gap-2">
              <Select aria-label="Mission" value={missionId} onChange={(e) => setMissionId(e.target.value)}>
                <option value="">Mission…</option>
                {missions.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.id} · {m.question.slice(0, 30)}
                  </option>
                ))}
              </Select>
              <Button onClick={generate} disabled={generating || !missionId} data-testid="studio-generate">
                {generating ? "Generating…" : "Generate"}
              </Button>
            </div>
          </div>
        </Card>
      )}

      {clips.length > 0 && (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {clips.map((clip, i) => (
            <Card key={clip.id}>
              <div className="flex h-full flex-col gap-3">
                <div className="flex items-center justify-between">
                  <Badge tone={clip.state === "ready" ? "success" : "muted"}>{clip.state}</Badge>
                  <span className="text-xs text-muted">
                    {clip.duration_seconds ? `${clip.duration_seconds.toFixed(1)}s` : "—"}
                  </span>
                </div>
                {clip.state === "ready" ? (
                  <video
                    controls
                    src={api.downloadClipUrl(clip.id)}
                    className="w-full rounded-md"
                    data-testid={`studio-clip-${i}`}
                  />
                ) : (
                  <Progress value={clip.progress} />
                )}
                <h3 className="text-sm font-medium">{clip.title ?? "Untitled"}</h3>
                <div className="flex flex-wrap items-center gap-2">
                  <Select
                    aria-label="Clip template"
                    value={clipEdits[clip.id]?.template ?? "cold_open"}
                    onChange={(e) =>
                      setClipEdits((prev) => ({
                        ...prev,
                        [clip.id]: {
                          template: e.target.value,
                          captions: prev[clip.id]?.captions ?? "word",
                        },
                      }))
                    }
                  >
                    {templates.map((t) => (
                      <option key={t} value={t}>
                        {t}
                      </option>
                    ))}
                  </Select>
                  <Select
                    aria-label="Clip caption style"
                    value={clipEdits[clip.id]?.captions ?? "word"}
                    onChange={(e) =>
                      setClipEdits((prev) => ({
                        ...prev,
                        [clip.id]: {
                          template: prev[clip.id]?.template ?? "cold_open",
                          captions: e.target.value,
                        },
                      }))
                    }
                  >
                    {captionStyles.map((s) => (
                      <option key={s} value={s}>
                        {s}
                      </option>
                    ))}
                  </Select>
                  <Button variant="ghost" onClick={() => rerender(clip)}>
                    Re-render
                  </Button>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}
      {recording && recording.candidates.length === 0 && !detecting && (
        <EmptyState title="No moments yet" body="Upload a recording, then press Find moments." />
      )}

      {clips.length > 0 ? (
        <NextStep
          href="/clips"
          title="Review the clips"
          body="Watch, add commentary and approve the finished Shorts."
        />
      ) : recording && recording.candidates.length > 0 ? (
        <NextStep
          href="/admin/studio"
          title="Generate a clip"
          body="Accept a candidate and build the Short."
        />
      ) : (
        <NextStep
          href="/admin/studio"
          title="Import a recording"
          body="Bring in a session from SSD or an upload, then find moments."
        />
      )}
    </div>
  );
}
