"use client";

import { useState } from "react";
import { api, type Clip } from "@/lib/api";
import { Badge, Button, Field, Input, PageState, Textarea, useToast } from "@/components/ui";

export function ClipReview({ clip }: { clip: Clip }) {
  const [title, setTitle] = useState(clip.title ?? "");
  const [description, setDescription] = useState("");
  const [state, setState] = useState(clip.state);
  const [loading, setLoading] = useState(false);
  const toast = useToast();

  async function save() {
    setLoading(true);
    try {
      await api.retitleClip(clip.id ?? "", title);
      toast("Title saved", "success");
    } catch {
      toast("Could not save", "danger");
    } finally {
      setLoading(false);
    }
  }

  async function approve() {
    setLoading(true);
    try {
      await api.approveClip(clip.id ?? "");
      setState("approved");
      toast("Clip approved", "success");
    } catch {
      toast("Could not approve", "danger");
    } finally {
      setLoading(false);
    }
  }

  async function post() {
    setLoading(true);
    try {
      await api.postClip(clip.id ?? "");
      setState("posted");
      toast("Queued as unlisted", "success");
    } catch {
      toast("Could not post", "danger");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,26rem)_1fr]">
      <div className="mx-auto w-full max-w-[26rem]">
        <div className="overflow-hidden rounded-lg bg-black ring-surface">
          <div className="flex aspect-[9/16] items-center justify-center bg-gradient-to-b from-surface-2 to-black p-6 text-center">
            <span className="text-sm text-muted">Preview · {clip.template}</span>
          </div>
        </div>
        {clip.download_url && (
          <a
            href={clip.download_url}
            className="mt-4 block rounded-full py-3 text-center text-sm font-medium text-accent ring-surface transition hover:bg-surface-2"
          >
            Download
          </a>
        )}
      </div>

      <PageState loading={loading} error={null} empty={false}>
        <div className="flex flex-col gap-5">
          <div className="flex items-center gap-3">
            <Badge tone={state === "ready" ? "success" : "muted"}>{state}</Badge>
            <span className="text-xs text-muted">{clip.duration_seconds ?? "—"}</span>
          </div>
          <Field label="Title">
            <Input value={title} onChange={(e) => setTitle(e.target.value)} />
          </Field>
          <Field label="Description">
            <Textarea rows={5} value={description} onChange={(e) => setDescription(e.target.value)} />
          </Field>
          <div className="flex flex-wrap gap-3">
            <Button variant="outline" onClick={save}>
              Save
            </Button>
            <Button onClick={approve} disabled={state === "approved" || state === "posted"}>
              Approve
            </Button>
            <Button variant="outline" onClick={post} disabled={state !== "approved" && state !== "posted"}>
              Post unlisted
            </Button>
          </div>
        </div>
      </PageState>
    </div>
  );
}
