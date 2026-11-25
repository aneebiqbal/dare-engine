"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import {
  api,
  type Clip,
  type ClipExport,
  type ReviewResult,
  type VoiceOver,
} from "@/lib/api";
import { NextStep } from "./next-step";
import { CaptionEditor } from "./caption-editor";
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
  Textarea,
  useToast,
} from "@/components/ui";
import { Pipeline, Section, StatusBadge, WorkHeader } from "./work";
import { PlatformSelect, usePlatforms } from "./platforms";
import { Thumb } from "./media";

const VOICES = [
  "en_US-amy-medium",
  "en_US-ryan-medium",
  "en_US-lessac-medium",
  "en_GB-alan-medium",
];

const LAYOUTS = ["blur_fit", "center_crop", "fit_height"];

const RENDER_STAGES = ["fetch", "transcribe", "select", "render", "store"];

function stageIndex(stage: string | null): number {
  if (!stage) return 0;
  const i = RENDER_STAGES.indexOf(stage);
  return i < 0 ? 0 : i;
}

export function ClipReview({ clip }: { clip: Clip }) {
  const [current, setCurrent] = useState(clip);
  const [title, setTitle] = useState(clip.title ?? "");
  const [description, setDescription] = useState(clip.export_description ?? "");
  const [commentary, setCommentary] = useState(clip.commentary ?? "");
  const [tags, setTags] = useState((clip.export_tags ?? []).join(", "));
  const [trimStart, setTrimStart] = useState("");
  const [trimEnd, setTrimEnd] = useState("");
  const [voice, setVoice] = useState(clip.voice ?? "en_US-amy-medium");
  const [review, setReview] = useState<ReviewResult | null>(null);
  const [exportCopy, setExportCopy] = useState<ClipExport | null>(null);
  const [preview, setPreview] = useState<VoiceOver | null>(null);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const toast = useToast();
  const platforms = usePlatforms();
  const [videoFailed, setVideoFailed] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (["ready", "approved", "posted", "discarded"].includes(current.state)) return;
    pollRef.current = setInterval(async () => {
      try {
        const fresh = await api.clip(clip.id);
        setCurrent(fresh);
      } catch {
        /* keep polling */
      }
    }, 3000);
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [current.state, clip.id]);

  async function run(fn: () => Promise<void>) {
    setBusy(true);
    setError(null);
    try {
      await fn();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Request failed");
    } finally {
      setBusy(false);
    }
  }

  const saveTitle = () =>
    run(async () => {
      const res = await api.updateClip(clip.id, { title });
      setCurrent((p) => ({ ...p, title: res.title }));
      toast("Title saved", "success");
    });

  const saveCommentary = () =>
    run(async () => {
      await api.updateClip(clip.id, { commentary });
      setCurrent((p) => ({ ...p, commentary }));
      toast("Commentary saved", "success");
    });

  const applyTrim = () =>
    run(async () => {
      await api.trim(clip.id, Number(trimStart), Number(trimEnd));
      toast("Trim queued; re-rendering", "success");
    });

  const applyStyle = (layout: string, caption_style: string) =>
    run(async () => {
      await api.updateClip(clip.id, { layout, caption_style });
      setCurrent((p) => ({ ...p, layout, caption_style }));
      toast("Re-rendering with the new style", "success");
    });

  const applyPlatform = (platform: string) =>
    run(async () => {
      await api.updateClip(clip.id, { platform });
      setCurrent(await api.clip(clip.id));
      toast("Target changed — re-rendering for that platform", "success");
    });

  const toggleVoice = (enabled: boolean) =>
    run(async () => {
      await api.voiceOver(clip.id, enabled, voice);
      setCurrent((p) => ({ ...p, voice_over: enabled, voice: enabled ? voice : null }));
      toast(enabled ? "Voice-over on; re-rendering" : "Voice-over off", "success");
    });

  const previewVoice = () =>
    run(async () => {
      const created = await api.voicePreview(clip.id, voice);
      const tick = async () => {
        const status = await api.voiceOverStatus(created.id);
        setPreview(status);
        if (status.state === "ready") return;
        setTimeout(tick, 2000);
      };
      await tick();
    });

  const runReview = () =>
    run(async () => {
      setReview(await api.reviewClip(clip.id));
    });

  const runExportCopy = () =>
    run(async () => {
      const res = await api.exportCopy(clip.id);
      setExportCopy(res);
      if (res.fallback) setNotice(res.notice ?? "AI is unavailable; using a plain fallback.");
      if (res.titles?.length) setTitle((prev) => prev || res.titles[0]);
      setDescription(res.description ?? "");
      setTags((res.tags ?? []).join(", "));
    });

  const saveExport = () =>
    run(async () => {
      await api.createExport(clip.id, {
        title,
        description,
        tags: tags.split(",").map((t) => t.trim()).filter(Boolean),
      });
      setCurrent(await api.clip(clip.id));
      toast("Export package saved", "success");
    });

  const ready = ["ready", "approved", "posted", "discarded"].includes(current.state);

  return (
    <div className="grid gap-6">
      <WorkHeader
        eyebrow="Review"
        title={current.title ?? "Clip review"}
        status={
          current.state === "ready" || current.state === "approved" || current.state === "posted"
            ? "done"
            : current.state === "failed"
              ? "failed"
              : current.state === "discarded"
                ? "idle"
                : "running"
        }
        actions={
          current.download_url ? (
            <a
              href={api.downloadClipUrl(clip.id)}
              className="inline-flex items-center rounded-md px-5 py-2.5 text-sm font-medium text-text ring-surface transition hover:bg-surface-2"
            >
              Download video
            </a>
          ) : undefined
        }
      />

      <div className="grid gap-6 lg:grid-cols-[minmax(0,24rem)_1fr]">
      <div className="flex flex-col gap-4">
        <div className="mx-auto w-full max-w-[24rem]">
          <div className="overflow-hidden rounded-lg bg-black ring-surface">
            {current.download_url && !videoFailed ? (
              <video
                controls
                src={api.downloadClipUrl(clip.id)}
                poster={api.thumbnailUrl(clip.id)}
                preload="metadata"
                onError={() => setVideoFailed(true)}
                className="aspect-[9/16] w-full object-contain"
                aria-label={`Preview of ${current.title ?? "this clip"}`}
                data-testid="clip-preview"
              />
            ) : current.thumb_url ? (
              <Thumb
                src={api.thumbnailUrl(clip.id)}
                alt={`Preview of ${current.title ?? "this clip"}`}
                className="aspect-[9/16] w-full object-contain"
              />
            ) : (
              <div className="flex aspect-[9/16] items-center justify-center bg-surface-2 p-6 text-center">
                <span className="text-sm text-muted">
                  {current.layout ?? "Preview"} · {current.state}
                </span>
              </div>
            )}
          </div>
          {!ready && (
            <div className="mt-3 flex flex-col gap-2">
              <Pipeline
                steps={RENDER_STAGES}
                current={stageIndex(current.stage)}
                label={`Render stages for ${current.title ?? "this clip"}`}
              />
              <Progress
                value={current.progress}
                label={`Render progress for ${current.title ?? "this clip"}`}
              />
              <span className="font-mono text-xs text-muted">
                {current.stage ?? "queued"} · {current.progress}%
              </span>
            </div>
          )}
          {current.error && <Notice tone="warn">{current.error}</Notice>}
          {current.download_url && (
            <a
              href={api.downloadClipUrl(clip.id)}
              className="mt-4 block rounded-md py-3 text-center text-sm font-medium text-text ring-surface transition hover:bg-surface-2"
            >
              Download video
            </a>
          )}
        </div>
        <Card>
          <div className="flex flex-col gap-3">
            <Badge tone={current.voice_over ? "accent" : "muted"}>
              {current.voice_over ? "Voice-over on" : "Voice-over off"}
            </Badge>
            <p className="text-xs leading-relaxed text-muted">
              The hook line and an outro line are spoken over the gameplay, which ducks
              underneath. For monetisation, your own voice is the safer choice.
            </p>
            <Field label="Voice">
              <Select value={voice} onChange={(e) => setVoice(e.target.value)}>
                {VOICES.map((v) => (
                  <option key={v} value={v}>
                    {v}
                  </option>
                ))}
              </Select>
            </Field>
            <div className="flex flex-wrap gap-2">
              <Button size="sm" variant="outline" onClick={previewVoice} disabled={busy}>
                Preview
              </Button>
              <Button
                size="sm"
                variant={current.voice_over ? "danger" : "outline"}
                onClick={() => toggleVoice(!current.voice_over)}
                disabled={busy}
              >
                {current.voice_over ? "Turn off" : "Turn on"}
              </Button>
            </div>
            {preview?.audio_url && (
              <audio
                controls
                src={api.voiceOverAudioUrl(preview.id)}
                className="w-full"
                data-testid="voice-preview"
              />
            )}
          </div>
        </Card>
      </div>

      <div className="flex flex-col gap-5">
        <PageState loading={false} error={error} empty={false}>
          {notice && <Notice tone="warn">{notice}</Notice>}

          <Card>
            <div className="flex flex-col gap-4">
              <Field label="Title">
                <Input value={title} onChange={(e) => setTitle(e.target.value)} />
              </Field>
              <Field label="Description">
                <Textarea rows={4} value={description} onChange={(e) => setDescription(e.target.value)} />
              </Field>
              <Field label="Tags" hint="Comma separated.">
                <Input value={tags} onChange={(e) => setTags(e.target.value)} />
              </Field>
              <Field
                label="Commentary / added value"
                hint="Your own context, reaction or explanation. Required for monetisation; a silent re-upload is not enough."
              >
                <Textarea
                  rows={4}
                  value={commentary}
                  onChange={(e) => setCommentary(e.target.value)}
                  placeholder="What were you doing, and why is this moment worth watching?"
                />
              </Field>
              <div className="flex flex-wrap gap-2">
                <Button variant="outline" onClick={saveTitle} disabled={busy}>
                  Save title
                </Button>
                <Button variant="outline" onClick={saveCommentary} disabled={busy}>
                  Save commentary
                </Button>
                <Button variant="outline" onClick={runExportCopy} disabled={busy}>
                  Write with AI
                </Button>
                <Button
                  onClick={() =>
                    run(async () => {
                      await api.approveClip(clip.id);
                      setCurrent((p) => ({ ...p, state: "approved" }));
                      toast("Clip approved", "success");
                    })
                  }
                  disabled={busy || current.state === "approved" || current.state === "posted"}
                >
                  Approve
                </Button>
              </div>
              {exportCopy && !exportCopy.fallback && (
                <div className="flex flex-col gap-2">
                  {exportCopy.titles.map((t, i) => (
                    <label key={i} className="flex items-center gap-2 text-sm">
                      <input
                        type="radio"
                        name="title-option"
                        checked={title === t}
                        onChange={() => setTitle(t)}
                      />
                      <span>{t}</span>
                    </label>
                  ))}
                </div>
              )}
            </div>
          </Card>

          <Card>
            <div className="flex flex-col gap-4">
              <h2 className="text-base font-medium">Trim and style</h2>
              <div className="grid gap-3 sm:grid-cols-2">
                <Field label="Start (seconds)">
                  <Input value={trimStart} onChange={(e) => setTrimStart(e.target.value)} placeholder="5" />
                </Field>
                <Field label="End (seconds)">
                  <Input value={trimEnd} onChange={(e) => setTrimEnd(e.target.value)} placeholder="35" />
                </Field>
              </div>
              <div className="flex flex-wrap gap-2">
                <Button variant="outline" size="sm" onClick={applyTrim} disabled={busy}>
                  Apply trim
                </Button>
              </div>
              <Field label="Target platform">
                <PlatformSelect
                  value={current.platform ?? "youtube_shorts"}
                  onChange={applyPlatform}
                  items={platforms.items}
                  label={`Target platform for ${current.title ?? "this clip"}`}
                />
              </Field>
              <div className="grid gap-3 sm:grid-cols-2">
                <Field label="Layout">
                  <Select
                    value={current.layout ?? ""}
                    onChange={(e) => applyStyle(e.target.value, current.caption_style ?? "word")}
                  >
                    <option value="">Rotate</option>
                    {LAYOUTS.map((l) => (
                      <option key={l} value={l}>
                        {l}
                      </option>
                    ))}
                  </Select>
                </Field>
                <Field label="Captions">
                  <Select
                    value={current.caption_style ?? "word"}
                    onChange={(e) => applyStyle(current.layout ?? "", e.target.value)}
                  >
                    <option value="word">Word highlight</option>
                    <option value="none">None</option>
                  </Select>
                </Field>
              </div>
            </div>
          </Card>

          <CaptionEditor clipId={clip.id} />

          <Card>
            <div className="flex flex-col gap-4">
              <div className="flex items-center justify-between">
                <h2 className="text-base font-medium">AI review</h2>
                <Button variant="outline" size="sm" onClick={runReview} disabled={busy}>
                  Review this Short
                </Button>
              </div>
              {review && (
                <div className="flex flex-col gap-3" data-testid="ai-review">
                  <div className="flex items-center gap-3">
                    <span className="text-3xl font-semibold">{review.score}</span>
                    <span className="text-sm text-muted">/ 100</span>
                    {review.fallback && <Badge tone="muted">fallback</Badge>}
                  </div>
                  <p className="text-sm font-medium">{review.hook_line}</p>
                  {review.weaknesses?.length ? (
                    <ul className="list-disc pl-5 text-sm text-muted">
                      {review.weaknesses.map((w, i) => (
                        <li key={i}>{w}</li>
                      ))}
                  </ul>
                  ) : null}
                  {review.fallback && review.notice && <Notice tone="warn">{review.notice}</Notice>}
                </div>
              )}
            </div>
          </Card>

          <Card>
            <div className="flex flex-col gap-4">
              <h2 className="text-base font-medium">Export package</h2>
              <p className="text-sm text-muted">
                Video, thumbnail, title, description and tags in one download.
              </p>
              <div className="flex flex-wrap gap-2">
                <Button onClick={saveExport} disabled={busy}>Save package</Button>
                <Link
                  href={`/export/${clip.id}`}
                  className="inline-flex items-center rounded-md px-5 py-2.5 text-sm font-medium text-muted ring-surface transition hover:bg-surface-2 hover:text-text"
                >
                  Open export page
                </Link>
                <a
                  href={api.downloadExportUrl(clip.id)}
                  className="inline-flex items-center rounded-md px-5 py-2.5 text-sm font-medium text-text ring-surface transition hover:bg-surface-2"
                  data-tour="export-button"
                >
                  Download package
                </a>
              </div>
            </div>
          </Card>
        </PageState>
      </div>
      </div>

      {current.state === "approved" && (
        <NextStep
          href="/admin/calendar"
          title="Schedule this Short"
          body="Add it to the posting calendar and keep the cadence."
        />
      )}
    </div>
  );
}
