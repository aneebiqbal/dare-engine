import Link from "next/link";
import { Badge, Button, Card, Eyebrow } from "@/components/ui";
import { api, type Today as TodayResponse } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function Welcome() {
  let today: TodayResponse | null = null;
  try {
    today = await api.today();
  } catch {
    today = null;
  }

  return (
    <main className="relative flex min-h-[100dvh] flex-col overflow-hidden px-6 py-10 sm:px-10">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-x-0 top-0 h-px bg-accent"
      />
      <header className="relative flex items-center justify-between">
        <span className="text-sm font-medium tracking-tight text-text">clipdesk</span>
        <nav className="flex items-center gap-2">
          <Link href="/landing" className="rounded-md px-4 py-2 text-sm text-muted ring-surface transition hover:bg-surface-2 hover:text-text">
            Download
          </Link>
          <Link href="/signin" className="text-sm text-muted transition hover:text-text">
            Sign in
          </Link>
        </nav>
      </header>

      <section className="relative flex flex-1 flex-col justify-center gap-6 py-24">
        <Eyebrow>Mission-first clipping</Eyebrow>
        <h1 className="max-w-4xl text-balance text-5xl font-semibold leading-[1.02] tracking-tight sm:text-7xl">
          The Short is written before the game is played.
        </h1>
        <p className="max-w-xl text-pretty text-lg leading-relaxed text-muted">
          A mission card with a hook, a win condition and a title. You tap Start and
          Done. The platform cuts the exact window into a finished 9:16 Short.
        </p>
        <div className="flex flex-wrap gap-3">
          <Link href="/signin">
            <Button size="lg">Start playing</Button>
          </Link>
          <Link href="/leaderboard">
            <Button size="lg" variant="outline">
              Daily leaderboard
            </Button>
          </Link>
        </div>
      </section>

      <section className="relative grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {[
          ["Question", "Missions", "Questions people ask become playable cards."],
          ["Window", "Marks", "Start and Done give the clip its exact window."],
          ["Render", "Short", "Hook, captions and end card, rendered in minutes."],
        ].map(([label, title, body]) => (
          <Card key={title}>
            <div className="flex flex-col gap-2">
              <span className="folio">{label}</span>
              <h3 className="text-base font-medium">{title}</h3>
              <p className="text-sm text-muted">{body}</p>
            </div>
          </Card>
        ))}
      </section>

      {today?.daily && (
        <section className="relative mt-4">
          <Card>
            <div className="flex flex-col gap-3">
              <Badge tone="accent">Today's Daily Mission</Badge>
              <h2 className="text-2xl font-semibold">{today.daily.hook_text}</h2>
              <p className="text-muted">{today.daily.question}</p>
              <div>
                <Link href={`/m/${today.daily.id}`}>
                  <Button variant="outline" size="sm">
                    View mission
                  </Button>
                </Link>
              </div>
            </div>
          </Card>
        </section>
      )}
    </main>
  );
}
