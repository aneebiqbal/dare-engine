"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { api, type Clip, type HistoryEntry, type Results, type Today } from "@/lib/api";
import { Badge, Button, Card, EmptyState, Notice, PageState, Progress, Stat } from "@/components/ui";

const CHECKLIST = [
  { id: "tour", label: "Take the tour", href: "/help" },
  { id: "mission", label: "Accept a mission", href: "/today" },
  { id: "clip", label: "Render your first Short", href: "/clips" },
  { id: "voice", label: "Try a voice-over", href: "/clips" },
  { id: "export", label: "Export a package", href: "/clips" },
];

export function Dashboard({ role }: { role: string }) {
  const [today, setToday] = useState<Today | null>(null);
  const [clips, setClips] = useState<Clip[]>([]);
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [results, setResults] = useState<Results | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState<string[]>([]);

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
    try {
      const saved = JSON.parse(localStorage.getItem("clipdesk.checklist") ?? "[]");
      if (Array.isArray(saved)) setDone(saved);
    } catch {
      /* ignore */
    }
  }, []);

  const toggle = (id: string) => {
    setDone((prev) => {
      const next = prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id];
      localStorage.setItem("clipdesk.checklist", JSON.stringify(next));
      return next;
    });
  };

  const next = useMemo(() => {
    if (!today || Object.keys(today.accepted ?? {}).length === 0)
      return { label: "Accept today's mission", href: "/today" };
    if (clips.length === 0) return { label: "Upload a recording", href: "/clips" };
    if (clips.some((c) => c.state === "ready")) return { label: "Review your Short", href: `/clips/${clips.find((c) => c.state === "ready")!.id}` };
    return { label: "Watch the render", href: "/clips" };
  }, [today, clips]);

  const ready = clips.filter((c) => c.state === "ready" || c.state === "approved");

  return (
    <div className="grid gap-6">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card>
          <Stat label="Accepted today" value={Object.keys(today?.accepted ?? {}).length} />
        </Card>
        <Card>
          <Stat label="Shorts ready" value={ready.length} hint={`${clips.length} total`} />
        </Card>
        <Card>
          <Stat
            label="Views"
            value={results?.clips.reduce((n, c) => n + c.views, 0)?.toLocaleString() ?? "0"}
          />
        </Card>
        <Card>
          <Stat
            label="Last session"
            value={history[0]?.date ?? "—"}
            hint={history[0]?.state}
          />
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-[2fr_1fr]">
        <section className="flex flex-col gap-4">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-semibold tracking-tight">Today&apos;s missions</h2>
            <Link href="/today" className="text-sm text-accent hover:underline">
              Open Today
            </Link>
          </div>
          <PageState loading={loading} error={error} empty={!today || (today.daily === null && today.picks.length === 0)}>
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
                {CHECKLIST.map((item) => (
                  <label key={item.id} className="flex items-center gap-3 text-sm">
                    <input
                      type="checkbox"
                      checked={done.includes(item.id)}
                      onChange={() => toggle(item.id)}
                      className="h-4 w-4 accent-[var(--accent)]"
                    />
                    <Link href={item.href} className="text-muted hover:text-text">
                      {item.label}
                    </Link>
                  </label>
                ))}
              </div>
              <Progress value={(done.length / CHECKLIST.length) * 100} />
              <span className="text-xs text-muted">
                {done.length} of {CHECKLIST.length} complete
              </span>
            </div>
          </Card>
        </aside>
      </div>

      {clips.some((c) => c.stage && c.state !== "ready") && (
        <Notice tone="warn">
          {clips.filter((c) => c.stage && c.state !== "ready").length} Short
          {clips.filter((c) => c.stage && c.state !== "ready").length === 1 ? "" : "s"} still
          rendering.
        </Notice>
      )}
    </div>
  );
}

function MissionCard({ card }: { card: Today["daily"] }) {
  if (!card) return null;
  return (
    <Card>
      <div className="flex h-full flex-col gap-3">
        <div className="flex items-center justify-between">
          <Badge tone="accent">{card.id}</Badge>
          <span className="text-xs text-muted">{card.est_minutes} min</span>
        </div>
        <h3 className="text-base font-medium leading-snug">{card.question}</h3>
        <p className="text-sm text-muted">{card.win_condition}</p>
        <Link href={`/missions/${card.id}`} className="mt-auto pt-2 text-sm text-accent hover:underline">
          Edit mission
        </Link>
      </div>
    </Card>
  );
}
