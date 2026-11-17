"use client";

import Link from "next/link";
import { useState } from "react";
import { api, type MissionCard, type Today as TodayResponse } from "@/lib/api";
import { Badge, Button, Card, Notice, PageState, useToast } from "@/components/ui";

export function Today({ initial }: { initial: TodayResponse | null }) {
  const [data, setData] = useState<TodayResponse | null>(initial);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [suggestions, setSuggestions] = useState<MissionCard[]>([]);
  const [suggestNotice, setSuggestNotice] = useState<string | null>(null);
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

  async function accept(missionId: string) {
    try {
      await api.accept(missionId);
      setData((prev) =>
        prev ? { ...prev, accepted: { ...prev.accepted, [missionId]: "accepted" } } : prev,
      );
      toast("Mission accepted", "success");
    } catch {
      toast("Could not accept", "danger");
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

  const cards = data?.daily
    ? [data.daily, ...(data.picks ?? []).filter((p) => p.id !== data.daily?.id)]
    : data?.picks ?? [];

  return (
    <div className="flex flex-col gap-6">
      <PageState loading={loading} error={error} empty={cards.length === 0}>
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3" data-tour="today-missions">
          {cards.map((card) => {
            const state = data?.accepted?.[card.id];
            return (
              <Card key={card.id}>
                <div className="flex h-full flex-col gap-3">
                  <div className="flex items-center justify-between">
                    <Badge tone="accent">{card.id}</Badge>
                    <span className="text-xs text-muted">{card.est_minutes} min</span>
                  </div>
                  <h3 className="text-base font-medium leading-snug">{card.question}</h3>
                  <p className="text-sm text-muted">{card.win_condition}</p>
                  <div className="mt-auto flex flex-wrap items-center gap-2 pt-2">
                    {state ? (
                      <Badge tone="success" data-testid="accepted">
                        {state}
                      </Badge>
                    ) : (
                      <Button size="sm" data-testid="accept-button" onClick={() => accept(card.id)}>
                        Accept
                      </Button>
                    )}
                    <Link href={`/missions/${card.id}`} className="text-sm text-muted hover:text-text">
                      Edit
                    </Link>
                    <button
                      type="button"
                      onClick={() => suggest(card.id)}
                      className="text-sm text-accent hover:underline"
                    >
                      More like this
                    </button>
                  </div>
                </div>
              </Card>
            );
          })}
        </div>
      </PageState>

      {suggestNotice && <Notice tone="warn">{suggestNotice}</Notice>}

      {suggestions.length > 0 && (
        <section className="flex flex-col gap-3">
          <h2 className="text-xl font-semibold tracking-tight">More like this</h2>
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
        </section>
      )}
    </div>
  );
}
