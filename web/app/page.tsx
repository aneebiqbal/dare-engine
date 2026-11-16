import { StatusBadge } from "@/components/status-badge";

export default function Home() {
  return (
    <main className="relative flex min-h-[100dvh] flex-col overflow-hidden px-6 py-10 sm:px-10">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(60%_50%_at_50%_0%,rgba(120,119,198,0.18),transparent_70%)]"
      />

      <header className="relative flex items-center justify-between">
        <span className="text-sm font-medium tracking-tight text-white/80">
          clipdesk
        </span>
        <StatusBadge />
      </header>

      <section className="relative flex flex-1 flex-col justify-center py-24">
        <span className="mb-6 w-fit rounded-full border-white/10 bg-white/5 px-3 py-1 text-[10px] uppercase tracking-[0.2em] text-white/60 ring-1 ring-black/5">
          Mission-first clipping
        </span>
        <h1 className="max-w-4xl text-balance text-5xl font-semibold leading-[1.02] tracking-tight sm:text-7xl">
          The Short is written before the game is played.
        </h1>
        <p className="mt-8 max-w-xl text-pretty text-lg leading-relaxed text-white/55">
          A mission card with a hook, a win condition and a title. You tap Start
          and Done. The platform cuts the exact window into a finished
          9:16&nbsp;Short.
        </p>
      </section>

      <footer className="relative grid gap-3 sm:grid-cols-3">
        {[
          ["01", "Missions", "Questions people ask become playable cards."],
          ["02", "Marks", "Start and Done give the clip its exact window."],
          ["03", "Short", "Hook, captions and end card, rendered in minutes."],
        ].map(([n, title, body]) => (
          <div
            key={n}
            className="rounded-[calc(2rem-0.375rem)] border-white/10 bg-white/[0.03] p-6 ring-1 ring-black/5"
          >
            <div className="text-[10px] uppercase tracking-[0.2em] text-white/35">
              {n}
            </div>
            <div className="mt-3 text-base font-medium">{title}</div>
            <p className="mt-2 text-sm leading-relaxed text-white/45">{body}</p>
          </div>
        ))}
      </footer>
    </main>
  );
}
