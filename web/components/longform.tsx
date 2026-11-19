"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { AdminClip, LongForm } from "@/lib/types";
import {
  Badge,
  Button,
  Card,
  Field,
  Input,
  PageState,
  Table,
  Td,
  Tr,
  useToast,
} from "./ui";

export function AdminLongForm() {
  const toast = useToast();
  const [clips, setClips] = useState<AdminClip[]>([]);
  const [items, setItems] = useState<LongForm[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [title, setTitle] = useState("");
  const [intro, setIntro] = useState("");
  const [outro, setOutro] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      const [c, l] = await Promise.all([api.adminClips(), api.adminLongForms()]);
      setClips(c.items);
      setItems(l.items);
      setError(null);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Could not load.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  function toggle(id: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  async function build() {
    if (!title.trim() || selected.size === 0) return;
    setBusy(true);
    try {
      await api.adminCreateLongForm(title.trim(), Array.from(selected), intro.trim(), outro.trim());
      toast("Long-form build queued", "success");
      setTitle("");
      setIntro("");
      setOutro("");
      setSelected(new Set());
      load();
    } catch (exc) {
      toast(exc instanceof Error ? exc.message : "Could not build", "danger");
    } finally {
      setBusy(false);
    }
  }

  if (loading) return <PageState loading />;
  if (error && !items.length) return <PageState error={error} />;

  return (
    <div className="grid gap-6">
      <Card>
        <div className="flex flex-col gap-4">
          <div>
            <span className="text-xs uppercase tracking-[0.2em] text-muted">Build a long-form video</span>
            <p className="mt-1 text-sm text-muted">
              Pick a session&apos;s finished Shorts and assemble them into one video. The build
              runs in the background like any other job.
            </p>
          </div>
          <Field label="Title">
            <Input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Sunday session — all the clutches"
            />
          </Field>
          <div className="grid gap-3 sm:grid-cols-2">
            <Field label="Intro card" hint="Optional text on a 2 s title card before the first clip.">
              <Input
                value={intro}
                onChange={(e) => setIntro(e.target.value)}
                placeholder="Sunday session"
              />
            </Field>
            <Field label="Outro card" hint="Optional text on a 2 s title card after the last clip.">
              <Input
                value={outro}
                onChange={(e) => setOutro(e.target.value)}
                placeholder="Clipdesk Missions"
              />
            </Field>
          </div>
          <div className="flex flex-col gap-2">
            {clips.length === 0 && (
              <p className="text-xs text-muted">No finished clips yet. Render and approve some first.</p>
            )}
            {clips.map((c) => (
              <label key={c.id} className="flex items-center gap-3 text-sm">
                <input
                  type="checkbox"
                  checked={selected.has(c.id)}
                  onChange={() => toggle(c.id)}
                />
                <span className="truncate">{c.title ?? c.id}</span>
                <span className="text-xs text-muted">
                  {c.duration_seconds ? `${Math.round(c.duration_seconds)}s` : ""}
                </span>
              </label>
            ))}
          </div>
          <div>
            <Button onClick={build} disabled={busy || !title.trim() || selected.size === 0}>
              Build long-form ({selected.size})
            </Button>
          </div>
        </div>
      </Card>

      <Card>
        <span className="text-xs uppercase tracking-[0.2em] text-muted">Builds</span>
        <div className="mt-4">
          <Table head={["Title", "Clips", "State", "Download"]} caption="Long-form builds">
            {items.length === 0 && (
              <Tr>
                <Td colSpan={4}>No long-form videos yet.</Td>
              </Tr>
            )}
            {items.map((l) => (
              <Tr key={l.id}>
                <Td>{l.title}</Td>
                <Td>{l.clip_ids.length}</Td>
                <Td>
                  <Badge tone={l.state === "ready" ? "success" : l.state === "failed" ? "danger" : "muted"}>
                    {l.state}
                  </Badge>
                  {l.error && <span className="ml-2 text-xs text-danger">{l.error}</span>}
                </Td>
                <Td>
                  {l.download_url ? (
                    <a href={api.adminLongFormUrl(l.id)} className="text-accent hover:underline">
                      Download
                    </a>
                  ) : (
                    "—"
                  )}
                </Td>
              </Tr>
            ))}
          </Table>
        </div>
      </Card>
    </div>
  );
}
