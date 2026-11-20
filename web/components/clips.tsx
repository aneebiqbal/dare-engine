"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { api, type Clip, type MissionCard } from "@/lib/api";
import { NextStep } from "./next-step";
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

type MarkRow = { mission_id: string; start: string; end: string; result: string };

export function Clips({ initial }: { initial: Clip[] }) {
  const [clips, setClips] = useState(initial);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [missions, setMissions] = useState<MissionCard[]>([]);
  const [rows, setRows] = useState<MarkRow[]>([{ mission_id: "", start: "", end: "", result: "" }]);
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState<number | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const toast = useToast();

  const refresh = useCallback(async () => {
    try {
      const res = await api.clips("?page_size=50");
      setClips(res.items);
      return res.items;
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load clips");
      return [];
    }
  }, []);

  useEffect(() => {
    api.today()
      .then((t) => setMissions([t.daily, ...t.picks].filter((m): m is MissionCard => Boolean(m))))
      .catch(() => {});
  }, []);

  // Poll while anything is rendering.
  useEffect(() => {
    if (!clips.some((c) => !["ready", "approved", "posted", "discarded"].includes(c.state))) return;
    const timer = setInterval(() => void refresh(), 3000);
    return () => clearInterval(timer);
  }, [clips, refresh]);

  async function upload() {
    if (!file) {
      setUploadError("Choose a recording first.");
      return;
    }
    const marks = rows
      .filter((r) => r.mission_id && r.start && r.end)
      .map((r) => ({
        mission_id: r.mission_id,
        start: Number(r.start),
        end: Number(r.end),
        result: r.result,
      }));
    if (!marks.length) {
      setUploadError("Add at least one mission with a start and end time.");
      return;
    }
    setUploadError(null);
    setUploading(0);
    try {
      const start = await api.uploadStart();
      const chunkSize = start.chunk_size;
      const total = Math.ceil(file.size / chunkSize);
      for (let i = 0; i < total; i++) {
        const blob = file.slice(i * chunkSize, (i + 1) * chunkSize);
        await api.uploadChunk(start.upload_id, i, blob);
        setUploading(Math.round(((i + 1) / total) * 100));
      }
      await api.uploadComplete(start.upload_id, marks, file.name);
      setUploading(null);
      setFile(null);
      setRows([{ mission_id: "", start: "", end: "", result: "" }]);
      if (fileRef.current) fileRef.current.value = "";
      toast("Upload complete; rendering", "success");
      await refresh();
    } catch (e) {
      setUploading(null);
      setUploadError(e instanceof Error ? e.message : "Upload failed");
    }
  }

  const needsCommentary = clips.find((c) => c.state === "ready" && !c.commentary);
  const firstReady = clips.find((c) => c.state === "ready" || c.state === "approved");

  return (
    <div className="flex flex-col gap-6">
      <Card>
        <div className="flex flex-col gap-4" data-tour="clips-upload">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-medium">Upload a recording</h2>
            <Badge tone="muted">Chunked upload</Badge>
          </div>
          <div className="grid gap-4 md:grid-cols-[1fr_2fr]">
            <Field label="Recording">
              <Input
                ref={fileRef}
                type="file"
                accept="video/*,audio/*"
                onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              />
            </Field>
            <div className="flex flex-col gap-3">
              <div className="grid gap-3 sm:grid-cols-[1fr_1fr_1fr_1fr_auto]">
                <Select
                  aria-label="Mission"
                  value={rows[0]?.mission_id ?? ""}
                  onChange={(e) =>
                    setRows((prev) => prev.map((r, i) => (i === 0 ? { ...r, mission_id: e.target.value } : r)))
                  }
                >
                  <option value="">Mission…</option>
                  {missions.map((m) => (
                    <option key={m.id} value={m.id}>
                      {m.id} · {m.question.slice(0, 30)}
                    </option>
                  ))}
                </Select>
                <Input
                  aria-label="Start seconds"
                  placeholder="Start s"
                  value={rows[0]?.start ?? ""}
                  onChange={(e) =>
                    setRows((prev) => prev.map((r, i) => (i === 0 ? { ...r, start: e.target.value } : r)))
                  }
                />
                <Input
                  aria-label="End seconds"
                  placeholder="End s"
                  value={rows[0]?.end ?? ""}
                  onChange={(e) =>
                    setRows((prev) => prev.map((r, i) => (i === 0 ? { ...r, end: e.target.value } : r)))
                  }
                />
                <Input
                  aria-label="Result"
                  placeholder="0:41"
                  value={rows[0]?.result ?? ""}
                  onChange={(e) =>
                    setRows((prev) => prev.map((r, i) => (i === 0 ? { ...r, result: e.target.value } : r)))
                  }
                />
                <Button
                  type="button"
                  variant="ghost"
                  onClick={() => setRows((prev) => [...prev, { mission_id: "", start: "", end: "", result: "" }])}
                >
                  + Mission
                </Button>
              </div>
              {rows.slice(1).map((row, i) => (
                <div key={i} className="grid gap-3 sm:grid-cols-[1fr_1fr_1fr_1fr_auto]">
                  <Select
                    aria-label={`Mission ${i + 2}`}
                    value={row.mission_id}
                    onChange={(e) =>
                      setRows((prev) => prev.map((r, j) => (j === i + 1 ? { ...r, mission_id: e.target.value } : r)))
                    }
                  >
                    <option value="">Mission…</option>
                    {missions.map((m) => (
                      <option key={m.id} value={m.id}>
                        {m.id} · {m.question.slice(0, 30)}
                      </option>
                    ))}
                  </Select>
                  <Input
                    aria-label="Start seconds"
                    value={row.start}
                    onChange={(e) =>
                      setRows((prev) => prev.map((r, j) => (j === i + 1 ? { ...r, start: e.target.value } : r)))
                    }
                  />
                  <Input
                    aria-label="End seconds"
                    value={row.end}
                    onChange={(e) =>
                      setRows((prev) => prev.map((r, j) => (j === i + 1 ? { ...r, end: e.target.value } : r)))
                    }
                  />
                  <Input
                    aria-label="Result"
                    value={row.result}
                    onChange={(e) =>
                      setRows((prev) => prev.map((r, j) => (j === i + 1 ? { ...r, result: e.target.value } : r)))
                    }
                  />
                  <Button
                    type="button"
                    variant="danger"
                    onClick={() => setRows((prev) => prev.filter((_, j) => j !== i + 1))}
                  >
                    Remove
                  </Button>
                </div>
              ))}
            </div>
          </div>
          {uploading !== null && <Progress value={uploading} label="Upload progress" />}
          {uploadError && <Notice tone="warn">{uploadError}</Notice>}
          <div>
            <Button onClick={upload} disabled={uploading !== null} data-testid="upload-button">
              {uploading !== null ? `Uploading ${uploading}%` : "Upload and render"}
            </Button>
          </div>
        </div>
      </Card>

      <PageState loading={loading} error={error} empty={clips.length === 0}>
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {clips.map((clip) => (
            <Card key={clip.id}>
              <div className="flex h-full flex-col gap-3">
                <div className="flex items-center justify-between">
                  <Badge tone={clip.state === "ready" ? "success" : clip.state === "failed" ? "danger" : "muted"}>
                    {clip.state}
                  </Badge>
                  <span className="text-xs text-muted">{clip.stage ?? ""}</span>
                </div>
                {clip.thumb_url && (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={api.thumbnailUrl(clip.id)}
                    alt=""
                    loading="lazy"
                    className="h-32 w-full rounded-xl object-cover"
                  />
                )}
                <h3 className="text-base font-medium leading-snug">{clip.title ?? "Untitled"}</h3>
                {clip.state !== "ready" && clip.progress > 0 && (
                  <Progress value={clip.progress} label={`Render progress for ${clip.title ?? "this clip"}`} />
                )}
                {clip.error && <Notice tone="warn">{clip.error}</Notice>}
                <p className="text-xs text-muted">
                  {clip.duration_seconds ? `${clip.duration_seconds.toFixed(1)}s` : "—"}
                  {clip.layout ? ` · ${clip.layout}` : ""}
                  {clip.voice_over ? " · voice-over" : ""}
                </p>
                <div className="mt-auto flex flex-wrap gap-2 pt-2">
                  <a
                    href={`/clips/${clip.id}`}
                    className="inline-flex items-center rounded-full px-4 py-2 text-sm font-medium text-muted ring-surface transition hover:bg-surface-2 hover:text-text"
                  >
                    Review
                  </a>
                  {clip.download_url && (
                    <a
                      href={api.downloadClipUrl(clip.id)}
                      className="inline-flex items-center rounded-full px-4 py-2 text-sm font-medium text-muted ring-surface transition hover:bg-surface-2 hover:text-text"
                    >
                      Download
                    </a>
                  )}
                </div>
              </div>
            </Card>
          ))}
        </div>
      </PageState>

      {needsCommentary ? (
        <NextStep
          href={`/clips/${needsCommentary.id}`}
          title="Add commentary for monetisation"
          body="Tell viewers what you were doing — a silent re-upload is not enough."
        />
      ) : firstReady ? (
        <NextStep
          href={`/clips/${firstReady.id}`}
          title="Review and export"
          body="Watch the Short, approve it, then schedule it."
        />
      ) : (
        <NextStep
          href="/admin/studio"
          title="Import a session"
          body="Bring in a recording and find the moments worth clipping."
        />
      )}
    </div>
  );
}
