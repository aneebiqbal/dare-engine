"use client";

import { useState } from "react";

export type Card = {
  id: string;
  question: string;
  hook_text: string;
  setup: string;
  win_condition: string;
  result_type: string;
  est_minutes: number;
  title_options: string[];
  mode: string;
};

export type TodayData = {
  date: string;
  daily: Card | null;
  picks: Card[];
  accepted: Record<string, string>;
};

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export function Today({ data }: { data: TodayData }) {
  const [accepted, setAccepted] = useState(data.accepted);
  const [busy, setBusy] = useState<string | null>(null);

  async function accept(missionId: string) {
    setBusy(missionId);
    try {
      const res = await fetch(`${API}/assignments`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mission_id: missionId }),
      });
      if (res.ok) setAccepted((prev) => ({ ...prev, [missionId]: "accepted" }));
    } finally {
      setBusy(null);
    }
  }

  const daily = data.daily;
  const cards = daily ? [daily, ...data.picks.filter((p) => p.id !== daily.id)] : data.picks;

  return (
    <main className="relative flex min-h-[100dvh] flex-col gap-10 px-6 py-10 sm:px-10">
      <header className="flex items-center justify-between">
        <span className="text-sm font-medium tracking-tight text-white/80">clipdesk</span>
        <span className="rounded-full border-white/10 bg-white/5 px-3 py-1.5 text-[11px] text-white/60 ring-1 ring-black/5">
          {data.date}
        </span>
      </header>

      <section className="flex flex-col gap-3">
        <span className="w-fit rounded-full border-white/10 bg-white/5 px-3 py-1 text-[10px] uppercase tracking-[0.2em] text-white/60 ring-1 ring-black/5">
          Daily mission
        </span>
        <h1 className="max-w-3xl text-balance text-4xl font-semibold leading-[1.05] tracking-tight sm:text-6xl">
          {daily?.hook_text ?? "No mission yet"}
        </h1>
        {daily && <p className="max-w-xl text-pretty text-white/55">{daily.question}</p>}
      </section>

      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {cards.map((card) => {
          const state = accepted[card.id];
          return (
            <article
              key={card.id}
              className="rounded-[2rem] border-white/10 bg-white/[0.03] p-1.5 ring-1 ring-black/5"
            >
              <div className="flex h-full flex-col gap-4 rounded-[calc(2rem-0.375rem)] bg-white/[0.02] p-6">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] uppercase tracking-[0.2em] text-white/35">
                    {card.id}
                  </span>
                  <span className="text-[10px] uppercase tracking-[0.2em] text-white/35">
                    {card.est_minutes} min
                  </span>
                </div>
                <h2 className="text-xl font-medium leading-snug">{card.question}</h2>
                <p className="text-sm leading-relaxed text-white/45">{card.win_condition}</p>
                <div className="mt-auto pt-2">
                  {state ? (
                    <span
                      data-testid="accepted"
                      className="inline-flex items-center gap-2 text-sm text-emerald-300"
                    >
                      <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
                      {state}
                    </span>
                  ) : (
                    <button
                      data-testid="accept-button"
                      onClick={() => accept(card.id)}
                      disabled={busy === card.id}
                      className="inline-flex items-center gap-3 rounded-full bg-white/5 py-2 pl-5 pr-2 text-sm font-medium text-white/80 ring-1 ring-black/5 transition active:scale-[0.98] hover:bg-white/10 disabled:opacity-50"
                    >
                      {busy === card.id ? "Accepting" : "Accept"}
                      <span className="flex h-8 w-8 items-center justify-center rounded-full bg-black/5">
                        →
                      </span>
                    </button>
                  )}
                </div>
              </div>
            </article>
          );
        })}
      </section>
    </main>
  );
}
