"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { api, type Clip, type HistoryEntry, type Results, type Today } from "@/lib/api";
import { DareCard } from "./dare-card";
import { Badge, Button, Card, Notice, PageState, Progress } from "@/components/ui";
import { Metric, Section, StatusBadge, WorkHeader, WorkQueue, type WorkItem } from "./work";

export function Dashboard({ role }: { role: string }) {
  const [today, setToday] = useState<Today | null>(null);
  const [clips, setClips] = useState<Clip[]>([]);
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [results, setResults] = useState<Results | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      api.today(),
      api.clips("?page_size=6"),
      api.history("?page_size=1"),
      api.results(),
    ])
      .then(([t, c, h, r]) => {
        setToday(t);
        setClips(c.items);
        setHistory(h.items);
        setResults(r);
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load"))
      .finally(() => setLoading(false));
  }, []);

  const ready = clips.filter((c) => c.state === "ready" || c.state === "approved");
  const rendering = clips.filter((c) => c.stage && !["ready", "approved", "posted", "discarded"].includes(c.state));
  const recentResults = useMemo(
    () => [...(results?.clips ?? [])].sort((a, b) => b.views - a.views).slice(0, 4),
    [results],
  );

  const next = useMemo(() => {
    if (!today || Object.keys(today.accepted ?? {}).length === 0)
      return { label: "Accept today's mission", href: "/today" };
    if (clips.length === 0) return { label: "Upload a recording", href: "/clips" };
    const firstReady = clips.find((c) => c.state === "ready");
    if (firstReady) return { label: "Review your Short", href: `/clips/${firstReady.id}` };
    return { label: "Watch the render", href: "/clips" };
  }, [today, clips]);

  // First steps are read from real state, not a local checkbox.
  const steps = [
    { id: "mission", label: "Accept a mission", href: "/today", done: Object.keys(today?.accepted ?? {}).length > 0 },
    { id: "upload", label: "Upload a recording", href: "/clips", done: clips.length > 0 },
    { id: "render", label: "Render your first Short", href: "/clips", done: ready.length > 0 },
    { id: "voice", label: "Try a voice-over", href: "/clips", done: clips.some((c) => c.voice_over) },
  ];
  const doneCount = steps.filter((s) => s.done).length;

  const renderItems: WorkItem[] = rendering.map((c) => ({
    id: c.id,
    title: c.title ?? "Untitled",
    subtitle: c.error ?? undefined,
    status: c.state === "failed" ? "failed" : "running",
    meta: `${c.stage ?? "queued"} · ${c.progress}%`,
    href: `/clips/${c.id}`,
  }));

  return (
    <div className="grid gap-6">
      <WorkHeader
        eyebrow="Dashboard"
        title="Your day"
        status={rendering.length ? "running" : ready.length ? "done" : "idle"}
        actions={
          <div className="flex items-center gap-4">
            <Metric label="Shorts ready" value={ready.length} />
            <Metric label="Views" value={(results?.clips ?? []).reduce((n, c) => n + c.views, 0).toLocaleString()} />
          </div>
        }
      />

      <div className="grid gap-6 lg:grid-cols-[2fr_1fr]">
        <section className="flex flex-col gap-4">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-semibold tracking-tight">Today&apos;s dares</h2>
            <Link href="/today" className="text-sm text-text underline decoration-border underline-offset-4 hover:text-accent">
              Open Today
            </Link>
          </div>
          <PageState
            loading={loading}
            error={error}
            empty={!today || (today.daily === null && today.picks.length === 0)}
            emptyTitle="No dares today"
            emptyBody="The admin pool is empty. Dares appear here once one is approved."
          >
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3" data-tour="dashboard-today">
              {today?.daily && <MissionCard card={today.daily} />}
              {today?.picks?.map((card) => (
                <MissionCard key={card.id} card={card} />
              ))}
            </div>
          </PageState>
        </section>

        <aside className="flex flex-col gap-4">
          <Card>
            <div className="flex flex-col gap-3">
              <Badge tone="accent">Next step</Badge>
              <Link href={next.href}>
                <Button className="w-full">{next.label}</Button>
              </Link>
            </div>
          </Card>
          <Card>
            <div className="flex flex-col gap-4">
              <h2 className="text-base font-medium">First steps</h2>
              <div className="flex flex-col gap-2">
                {steps.map((item) => (
                  <div key={item.id} className="flex items-center gap-3 text-sm">
                    <input
                      type="checkbox"
                      checked={item.done}
                      readOnly
                      aria-label={item.label}
                      className="h-4 w-4 accent-[var(--accent)]"
                    />
                    <Link href={item.href} className="text-muted hover:text-text">
                      {item.label}
                    </Link>
                  </div>
                ))}
              </div>
              <Progress value={(doneCount / steps.length) * 100} label="First steps" />
              <span className="text-xs text-muted">
                {doneCount} of {steps.length} complete
              </span>
            </div>
          </Card>
        </aside>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <div className="flex flex-col gap-3">
            <h2 className="text-base font-medium">Ready to review</h2>
            {ready.length === 0 ? (
              <p className="text-sm text-muted">Nothing is ready yet.</p>
            ) : (
              ready.slice(0, 4).map((clip) => (
                <Link
                  key={clip.id}
                  href={`/clips/${clip.id}`}
                  className="flex items-center justify-between gap-3 text-sm"
                >
                  <span className="truncate">{clip.title ?? "Untitled"}</span>
                  <Badge tone="success">{clip.state}</Badge>
                </Link>
              ))
            )}
          </div>
        </Card>
        <Card>
          <div className="flex flex-col gap-3">
            <h2 className="text-base font-medium">Recent results</h2>
            {recentResults.length === 0 ? (
              <p className="text-sm text-muted">No views recorded yet.</p>
            ) : (
              recentResults.map((r) => (
                <div key={r.clip_id} className="flex items-center justify-between gap-3 text-sm">
                  <span className="truncate">{r.title ?? "Untitled"}</span>
                  <span className="text-muted">
                    {r.views.toLocaleString()} views
                    {r.avg_view_percentage != null ? ` · ${r.avg_view_percentage}%` : ""}
                  </span>
                </div>
              ))
            )}
          </div>
        </Card>
      </div>

      {renderItems.length > 0 && (
        <Section title="Rendering now" count={renderItems.length} live>
          <Card>
            <WorkQueue items={renderItems} />
          </Card>
        </Section>
      )}
    </div>
  );
}

function MissionCard({ card }: { card: NonNullable<Today["daily"]> }) {
  return <DareCard card={card} highlight href={`/missions/${card.id}`} />;
}
