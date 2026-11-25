"use client";

import { useState } from "react";
import { api, type Clip, type ClipExport } from "@/lib/api";
import { Badge, Button, Card, Field, Input, Notice, PageState, Textarea, useToast } from "@/components/ui";
import { WorkHeader } from "./work";
import { Thumb } from "./media";

export function ExportPackage({ clip }: { clip: Clip }) {
  const [title, setTitle] = useState(clip.export_title ?? clip.title ?? "");
  const [description, setDescription] = useState(clip.export_description ?? "");
  const [tags, setTags] = useState((clip.export_tags ?? []).join(", "));
  const [copy, setCopy] = useState<ClipExport | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const toast = useToast();

  async function writeWithAi() {
    setBusy(true);
    setError(null);
    try {
      const res = await api.exportCopy(clip.id);
      setCopy(res);
      if (res.fallback) setNotice(res.notice ?? "AI is unavailable; using a plain fallback.");
      if (res.titles?.length) setTitle((prev) => prev || res.titles[0]);
      setDescription(res.description ?? "");
      setTags((res.tags ?? []).join(", "));
    } catch (e) {
      setError(e instanceof Error ? e.message : "AI request failed");
    } finally {
      setBusy(false);
    }
  }

  async function save() {
    setBusy(true);
    setError(null);
    try {
      await api.createExport(clip.id, {
        title,
        description,
        tags: tags.split(",").map((t) => t.trim()).filter(Boolean),
      });
      toast("Export package saved", "success");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not save");
    } finally {
      setBusy(false);
    }
  }

  return (
    <PageState loading={false} error={error} empty={false}>
      <div className="grid gap-6">
        <WorkHeader eyebrow="Export" title={clip.title ?? "Export package"} status="idle" />
        <div className="grid gap-6 lg:grid-cols-[minmax(0,24rem)_1fr]">
        <div className="mx-auto w-full max-w-[24rem]">
          <div className="overflow-hidden rounded-lg bg-black ring-surface">
            {clip.thumb_url ? (
              <Thumb
                src={api.thumbnailUrl(clip.id)}
                alt={`Preview of ${clip.title ?? "this clip"}`}
                className="aspect-[9/16] w-full object-contain"
              />
            ) : (
              <div className="flex aspect-[9/16] items-center justify-center bg-surface-2 p-6 text-center">
                <span className="text-sm text-muted">{clip.layout ?? "Short"}</span>
              </div>
            )}
          </div>
          {clip.download_url && (
            <a
              href={api.downloadClipUrl(clip.id)}
              className="mt-4 block rounded-md py-3 text-center text-sm font-medium text-text ring-surface transition hover:bg-surface-2"
            >
              Download video only
            </a>
          )}
        </div>

        <div className="flex flex-col gap-5">
          <Card>
            <div className="flex flex-col gap-4">
              <div className="flex items-center justify-between">
                <h2 className="text-base font-medium">Package metadata</h2>
                <Button variant="outline" size="sm" onClick={writeWithAi} disabled={busy}>
                  Write with AI
                </Button>
              </div>
              {notice && <Notice tone="warn">{notice}</Notice>}
              {copy && !copy.fallback && (
                <div className="flex flex-col gap-2">
                  {copy.titles.map((t, i) => (
                    <label key={i} className="flex items-center gap-2 text-sm">
                      <input type="radio" name="export-title" checked={title === t} onChange={() => setTitle(t)} />
                      <span>{t}</span>
                    </label>
                  ))}
                </div>
              )}
              <Field label="Title">
                <Input value={title} onChange={(e) => setTitle(e.target.value)} />
              </Field>
              <Field label="Description">
                <Textarea rows={5} value={description} onChange={(e) => setDescription(e.target.value)} />
              </Field>
              <Field label="Tags" hint="Comma separated.">
                <Input value={tags} onChange={(e) => setTags(e.target.value)} />
              </Field>
            </div>
          </Card>

          <Card>
            <div className="flex flex-col gap-4">
              <Badge tone="muted">Includes video, thumbnail, title, description and tags</Badge>
              <div className="flex flex-wrap gap-2">
                <Button onClick={save} disabled={busy}>Save package</Button>
                <a
                  href={api.downloadExportUrl(clip.id)}
                  className="inline-flex items-center rounded-md px-5 py-2.5 text-sm font-medium text-text ring-surface transition hover:bg-surface-2"
                >
                  Download package
                </a>
              </div>
            </div>
          </Card>
        </div>
        </div>
      </div>
    </PageState>
  );
}
