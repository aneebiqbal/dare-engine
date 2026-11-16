"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

export type PoolEntry = {
  id: string;
  card: {
    question: string;
    hook_text: string;
    win_condition: string;
    est_minutes: number;
    mode: string;
  };
  state: string;
};

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export function Admin({ pool }: { pool: PoolEntry[] }) {
  const router = useRouter();
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  async function submit() {
    const questions = text
      .split("\n")
      .map((q) => q.trim())
      .filter(Boolean);
    if (!questions.length) return;
    setBusy(true);
    setMessage("");
    try {
      const res = await fetch(`${API}/admin/questions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ questions }),
      });
      const body = await res.json();
      setMessage(res.ok ? `Wrote ${body.count} cards.` : `Failed: ${JSON.stringify(body)}`);
      if (res.ok) setText("");
      router.refresh();
    } finally {
      setBusy(false);
    }
  }

  async function approve(id: string) {
    await fetch(`${API}/admin/pool/${id}/approve`, { method: "POST" });
    router.refresh();
  }

  return (
    <main className="relative flex min-h-[100dvh] flex-col gap-10 px-6 py-10 sm:px-10">
      <header className="flex items-center justify-between">
        <span className="text-sm font-medium tracking-tight text-white/80">clipdesk · admin</span>
        <a href="/" className="text-sm text-white/50 hover:text-white/80">
          Today →
        </a>
      </header>

      <section className="flex flex-col gap-4">
        <span className="w-fit rounded-full border-white/10 bg-white/5 px-3 py-1 text-[10px] uppercase tracking-[0.2em] text-white/60 ring-1 ring-black/5">
          Type questions
        </span>
        <textarea
          data-testid="questions"
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={6}
          placeholder={"One question per line.\nCan you outrun five stars on a bicycle?"}
          className="w-full rounded-[calc(2rem-0.375rem)] border-white/10 bg-white/[0.03] p-6 text-base text-white/80 ring-1 ring-black/5 outline-none placeholder:text-white/25 focus:bg-white/[0.05]"
        />
        <div className="flex items-center gap-4">
          <button
            data-testid="write-cards"
            onClick={submit}
            disabled={busy}
            className="inline-flex items-center gap-3 rounded-full bg-white/5 py-2 pl-5 pr-2 text-sm font-medium text-white/80 ring-1 ring-black/5 transition active:scale-[0.98] hover:bg-white/10 disabled:opacity-50"
          >
            {busy ? "Writing" : "Write cards"}
            <span className="flex h-8 w-8 items-center justify-center rounded-full bg-black/5">→</span>
          </button>
          {message && <span className="text-sm text-white/50">{message}</span>}
        </div>
      </section>

      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {pool.map((entry) => (
          <article
            key={entry.id}
            className="rounded-[2rem] border-white/10 bg-white/[0.03] p-1.5 ring-1 ring-black/5"
          >
            <div className="flex h-full flex-col gap-3 rounded-[calc(2rem-0.375rem)] bg-white/[0.02] p-6">
              <span className="text-[10px] uppercase tracking-[0.2em] text-white/35">
                {entry.id}
              </span>
              <h2 className="text-lg font-medium leading-snug">{entry.card.question}</h2>
              <p className="text-sm text-white/45">{entry.card.hook_text}</p>
              <div className="mt-auto pt-2">
                <button
                  data-testid="approve-button"
                  onClick={() => approve(entry.id)}
                  className="inline-flex items-center gap-3 rounded-full bg-white/5 py-2 pl-5 pr-2 text-sm font-medium text-white/80 ring-1 ring-black/5 transition active:scale-[0.98] hover:bg-white/10"
                >
                  Approve
                  <span className="flex h-8 w-8 items-center justify-center rounded-full bg-black/5">→</span>
                </button>
              </div>
            </div>
          </article>
        ))}
      </section>
    </main>
  );
}
