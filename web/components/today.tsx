"use client";

import { useState } from "react";
import { api, type Today as TodayResponse } from "@/lib/api";
import { Badge, Button, Card, PageState, useToast } from "@/components/ui";

export function Today({ initial }: { initial: TodayResponse }) {
  const [data, setData] = useState(initial);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
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
      setData((prev) => ({
        ...prev,
        accepted: { ...prev.accepted, [missionId]: "accepted" },
      }));
      toast("Mission accepted", "success");
    } catch {
      toast("Could not accept", "danger");
    }
  }

  const cards = data.daily
    ? [data.daily, ...(data.picks ?? []).filter((p) => p.id !== data.daily?.id)]
    : data.picks ?? [];

  return (
    <PageState loading={loading} error={error} empty={cards.length === 0}>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {cards.map((card) => {
          const state = data.accepted?.[card.id];
          return (
            <Card key={card.id}>
              <div className="flex h-full flex-col gap-3">
                <div className="flex items-center justify-between">
                  <Badge tone="accent">{card.id}</Badge>
                  <span className="text-xs text-muted">{card.est_minutes} min</span>
                </div>
                <h3 className="text-base font-medium leading-snug">{card.question}</h3>
                <p className="text-sm text-muted">{card.win_condition}</p>
                <div className="mt-auto pt-2">
                  {state ? (
                    <Badge tone="success" data-testid="accepted">
                      {state}
                    </Badge>
                  ) : (
                    <Button size="sm" data-testid="accept-button" onClick={() => accept(card.id)}>
                      Accept
                    </Button>
                  )}
                </div>
              </div>
            </Card>
          );
        })}
      </div>
    </PageState>
  );
}
