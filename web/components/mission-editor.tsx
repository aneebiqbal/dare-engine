"use client";

import { useState } from "react";
import { api, type EditorResult, type MissionCard, type PoolEntry } from "@/lib/api";
import { Badge, Button, Card, Field, Input, Notice, PageState, Textarea, useToast } from "@/components/ui";

export function MissionEditor({ initial }: { initial: PoolEntry | null }) {
  const [card, setCard] = useState<MissionCard | null>(initial?.card ?? null);
  const [busy, setBusy] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const toast = useToast();

  async function improve(field: "hook" | "win_condition" | "title") {
    if (!card) return;
    setBusy(field);
    setNotice(null);
    try {
      const res: EditorResult = await api.missionEditor(card, field);
      setCard((prev) =>
        prev
          ? {
              ...prev,
              hook_text: res.hook_text || prev.hook_text,
              win_condition: res.win_condition || prev.win_condition,
              title_options: res.title_spoiler
                ? prev.title_options
                : [res.hook_text, ...prev.title_options].slice(0, 3),
            }
          : prev,
      );
      setNotice(res.fallback ? res.notice ?? "AI is unavailable; nothing was changed." : null);
      toast(res.fallback ? "AI unavailable" : "Improved", res.fallback ? "danger" : "success");
    } catch (e) {
      setError(e instanceof Error ? e.message : "AI request failed");
    } finally {
      setBusy(null);
    }
  }

  async function save() {
    if (!card) return;
    try {
      await api.updateMission(card.id, card);
      toast("Mission saved", "success");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not save");
    }
  }

  if (!card) {
    return <PageState loading={false} error="Mission not found" empty={false} />;
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[2fr_1fr]">
      <div className="flex flex-col gap-5">
        <Card>
          <div className="flex flex-col gap-4">
            <Field label="Question">
              <Textarea
                rows={2}
                value={card.question}
                onChange={(e) => setCard({ ...card, question: e.target.value })}
              />
            </Field>
            <Field label="Hook text" hint="Shown over the first two seconds.">
              <Input
                data-tour="editor-hook"
                value={card.hook_text}
                onChange={(e) => setCard({ ...card, hook_text: e.target.value })}
              />
            </Field>
            <Field label="Setup">
              <Textarea
                rows={3}
                value={card.setup}
                onChange={(e) => setCard({ ...card, setup: e.target.value })}
              />
            </Field>
            <Field label="Win condition">
              <Textarea
                rows={2}
                value={card.win_condition}
                onChange={(e) => setCard({ ...card, win_condition: e.target.value })}
              />
            </Field>
            <Field label="Title options">
              {card.title_options.map((title, i) => (
                <Input
                  key={i}
                  value={title}
                  onChange={(e) =>
                    setCard({
                      ...card,
                      title_options: card.title_options.map((t, j) => (j === i ? e.target.value : t)),
                    })
                  }
                />
              ))}
            </Field>
            <div className="flex flex-wrap gap-3">
              <Button onClick={save}>Save mission</Button>
            </div>
          </div>
        </Card>
      </div>

      <aside className="flex flex-col gap-4">
        <Card>
          <div className="flex flex-col gap-3">
            <span className="text-[10px] uppercase tracking-[0.2em] text-muted">Card identity</span>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={api.cardImageUrl(card.id)}
              alt={`Card for ${card.hook_text}`}
              className="w-full rounded-xl bg-bg object-cover ring-surface"
            />
          </div>
        </Card>
        <Card>
          <div className="flex flex-col gap-4">
            <Badge tone="accent">AI assist</Badge>
            <p className="text-sm text-muted">
              Rewrite the hook, tighten the win condition, or check the title for spoilers.
            </p>
            <div className="flex flex-col gap-2">
              <Button variant="outline" size="sm" disabled={busy !== null} onClick={() => improve("hook")}>
                {busy === "hook" ? "Working…" : "Rewrite hook"}
              </Button>
              <Button
                variant="outline"
                size="sm"
                disabled={busy !== null}
                onClick={() => improve("win_condition")}
              >
                {busy === "win_condition" ? "Working…" : "Tighten win condition"}
              </Button>
              <Button variant="outline" size="sm" disabled={busy !== null} onClick={() => improve("title")}>
                {busy === "title" ? "Working…" : "Check title for spoilers"}
              </Button>
            </div>
            {notice && <Notice tone="warn">{notice}</Notice>}
            {error && <Notice tone="warn">{error}</Notice>}
          </div>
        </Card>
        <Card>
          <div className="flex flex-col gap-2 text-sm text-muted">
            <span>Mode · {card.mode}</span>
            <span>Estimated · {card.est_minutes} min</span>
            <span>Result · {card.result_type}</span>
            <span>Status · {card.status}</span>
          </div>
        </Card>
        {initial?.sources && initial.sources.length > 0 && (
          <Card>
            <div className="flex flex-col gap-2">
              <Badge tone="accent">Sources</Badge>
              <ul className="flex flex-col gap-1">
                {initial.sources.map((s) => (
                  <li key={s.url} className="text-xs">
                    <Badge tone="muted">{s.kind}</Badge>{" "}
                    <a
                      href={s.url}
                      target="_blank"
                      rel="noreferrer"
                      className="text-accent hover:underline"
                    >
                      {s.title}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          </Card>
        )}
      </aside>
    </div>
  );
}
