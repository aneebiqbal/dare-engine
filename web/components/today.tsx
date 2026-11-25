"use client";

import Link from "next/link";
import { useState } from "react";
import { api, type MissionCard, type Today as TodayResponse } from "@/lib/api";
import { NextStep } from "./next-step";
import { DareCard } from "./dare-card";
import {
  Badge,
  Button,
  Card,
  Dialog,
  Notice,
  PageState,
  useToast,
} from "@/components/ui";
import { StatusBadge, WorkHeader } from "./work";

export function Today({ initial }: { initial: TodayResponse | null }) {
  const [data, setData] = useState<TodayResponse | null>(initial);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [suggestions, setSuggestions] = useState<MissionCard[]>([]);
  const [suggestNotice, setSuggestNotice] = useState<string | null>(null);
  const [swapFor, setSwapFor] = useState<MissionCard | null>(null);
  const toast = useToast();

  async function refresh() {
    setLoading(true);
    setError(null);
    try {
      setData(await api.today());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  }

  async function suggest(liked: string) {
    try {
      const res = await api.suggest(liked);
      setSuggestions(res.suggestions ?? []);
      setSuggestNotice(res.fallback ? res.notice ?? null : null);
    } catch {
      setSuggestNotice("Suggestions are unavailable right now.");
    }
  }

  async function accept(missionId: string) {
    try {
      const res = await api.accept(missionId);
      const id = (res as { id?: string }).id ?? "pending";
      setData((prev) =>
        prev
          ? {
              ...prev,
              accepted: { ...prev.accepted, [missionId]: "accepted" },
              assignments: [
                ...(prev.assignments ?? []).filter((a) => a.mission_id !== missionId),
                { id, mission_id: missionId, state: "accepted" },
              ],
            }
          : prev,
      );
      toast("Dare accepted", "success");
    } catch {
      toast("Could not accept", "danger");
    }
  }

  async function swap(target: MissionCard) {
    if (!swapFor) return;
    const assignment = data?.assignments?.find((a) => a.mission_id === swapFor.id);
    if (!assignment) {
      toast("Accept the dare before swapping it", "danger");
      return;
    }
    try {
      await api.swap(assignment.id, target.id);
      setSwapFor(null);
      await refresh();
      toast("Dare swapped", "success");
    } catch {
      toast("Could not swap", "danger");
    }
  }

  const cards = data?.daily
    ? [data.daily, ...(data.picks ?? []).filter((p) => p.id !== data.daily?.id)]
    : data?.picks ?? [];
  const swapOptions = cards.filter((c) => c.id !== swapFor?.id);
  const accepted = cards.some((c) =>
    ["accepted", "swapped", "assigned"].includes(data?.accepted?.[c.id] ?? ""),
  );

  return (
    <div className="flex flex-col gap-6">
      <WorkHeader
        eyebrow="Today"
        title="Play today's mission"
        status={accepted ? "done" : cards.length ? "needs" : "idle"}
        actions={
          <span className="font-mono text-xs text-muted">
            {cards.length} dare{cards.length === 1 ? "" : "s"} available
          </span>
        }
      />
      <PageState
        loading={loading}
        error={error}
        empty={cards.length === 0}
        emptyTitle="No dares today"
        emptyBody="Dares appear here once the admin approves them."
      >
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3" data-tour="today-missions">
          {cards.map((card) => {
            const state = data?.accepted?.[card.id];
            return (
              <DareCard
                key={card.id}
                card={card}
                highlight={card.id === data?.daily?.id}
              >
                <div className="mt-auto flex flex-wrap items-center gap-2 pt-2">
                  {state === "accepted" || state === "swapped" ? (
                    <Badge tone="success" data-testid="accepted">
                      {state}
                    </Badge>
                  ) : state === "assigned" ? (
                    <Badge tone="accent">assigned</Badge>
                  ) : (
                    <Button size="sm" data-testid="accept-button" onClick={() => accept(card.id)}>
                      Accept
                    </Button>
                  )}
                  {state && (
                    <Button size="sm" variant="outline" onClick={() => setSwapFor(card)}>
                      Swap
                    </Button>
                  )}
                  <Link href={`/missions/${card.id}`} className="text-sm text-muted hover:text-text">
                    Edit
                  </Link>
                  <button
                    type="button"
                    onClick={() => suggest(card.id)}
                    className="text-sm text-text underline decoration-border underline-offset-4 hover:text-accent"
                  >
                    More like this
                  </button>
                </div>
              </DareCard>
            );
          })}
        </div>
      </PageState>

      {suggestNotice && <Notice tone="warn">{suggestNotice}</Notice>}

      {accepted ? (
        <NextStep
          href="/live"
          title="Go live and mark the moment"
          body="Connect OBS, then tap Start and Done on the phone remote."
        />
      ) : (
        <NextStep
          href={data?.daily ? `/missions/${data.daily.id}` : "/today"}
          title="Read the dare"
          body="Check the win condition, accept it, then go live."
        />
      )}

      <section className="flex flex-col gap-3" aria-live="polite">
        <h2 className="text-xl font-semibold tracking-tight">More like this</h2>
        {suggestions.length === 0 ? (
          <p className="text-sm text-muted">Suggestions will appear here.</p>
        ) : (
          <div className="grid gap-4 md:grid-cols-3">
            {suggestions.map((card) => (
              <Card key={card.id}>
                <div className="flex h-full flex-col gap-2">
                  <Badge tone="muted">{card.id}</Badge>
                  <h3 className="text-base font-medium leading-snug">{card.question}</h3>
                  <p className="text-sm text-muted">{card.hook_text}</p>
                </div>
              </Card>
            ))}
          </div>
        )}
      </section>

      <Dialog open={Boolean(swapFor)} onClose={() => setSwapFor(null)} title="Swap this dare">
        <p className="mb-4 text-sm text-muted">Pick a different dare for today.</p>
        <div className="flex flex-col gap-2">
          {swapOptions.map((card) => (
            <button
              key={card.id}
              type="button"
              onClick={() => void swap(card)}
              className="rounded-md bg-surface p-3 text-left text-sm ring-surface transition hover:bg-surface-2"
            >
              <span className="text-xs text-muted">{card.id}</span>
              <span className="block">{card.question}</span>
            </button>
          ))}
        </div>
      </Dialog>
    </div>
  );
}
