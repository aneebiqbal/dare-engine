import Link from "next/link";
import { Badge, Button, Card, Eyebrow } from "@/components/ui";

export const metadata = {
  title: "Download Clipdesk",
  description: "The desktop clip engine and the web portal, from one product.",
};

// Owner slots. Fill these in the deployment environment; the page shows an
// honest "link slot" until they are set, never a dead button.
const MAC_URL = process.env.NEXT_PUBLIC_DOWNLOAD_MAC ?? "";
const WINDOWS_URL = process.env.NEXT_PUBLIC_DOWNLOAD_WINDOWS ?? "";
const WEB_PORTAL_URL = process.env.NEXT_PUBLIC_WEB_PORTAL ?? "";
const DEMO_URL = process.env.NEXT_PUBLIC_DEMO_CLIP ?? "";

function DownloadCard({
  title,
  body,
  url,
  slot,
  meta,
}: {
  title: string;
  body: string;
  url: string;
  slot: string;
  meta: string;
}) {
  return (
    <Card>
      <div className="flex h-full flex-col gap-4">
        <div className="flex items-center justify-between gap-3">
          <h2 className="text-base font-medium">{title}</h2>
          <Badge tone="muted">{meta}</Badge>
        </div>
        <p className="text-sm leading-relaxed text-muted">{body}</p>
        {url ? (
          <a
            href={url}
            className="mt-auto inline-flex items-center justify-center rounded-full bg-accent px-5 py-3 text-sm font-medium text-white transition hover:opacity-90"
          >
            Download
          </a>
        ) : (
          <div className="mt-auto flex flex-col gap-1">
            <span className="inline-flex items-center justify-center rounded-full bg-surface-3 px-5 py-3 font-mono text-xs text-muted ring-surface">
              {slot}
            </span>
            <span className="text-center text-[11px] text-muted">
              Owner slot — set the URL in the deploy environment.
            </span>
          </div>
        )}
      </div>
    </Card>
  );
}

export default function Landing() {
  return (
    <main className="relative flex min-h-[100dvh] flex-col overflow-hidden px-6 py-10 sm:px-10">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(60%_50%_at_50%_0%,rgba(120,119,198,0.16),transparent_70%)]"
      />
      <header className="relative flex items-center justify-between">
        <Link href="/welcome" className="text-sm font-medium tracking-tight text-text">
          clipdesk
        </Link>
        <nav className="flex items-center gap-2">
          {WEB_PORTAL_URL ? (
            <a
              href={WEB_PORTAL_URL}
              className="rounded-full px-4 py-2 text-sm text-muted ring-surface transition hover:bg-surface-2 hover:text-text"
            >
              Open the web portal
            </a>
          ) : (
            <span className="rounded-full px-4 py-2 font-mono text-[11px] text-muted ring-surface">
              NEXT_PUBLIC_WEB_PORTAL
            </span>
          )}
          <Link
            href="/signin"
            className="rounded-full px-4 py-2 text-sm text-muted ring-surface transition hover:bg-surface-2 hover:text-text"
          >
            Sign in
          </Link>
        </nav>
      </header>

      <section className="relative flex flex-1 flex-col justify-center gap-6 py-24">
        <Eyebrow>One product, three ways to run it</Eyebrow>
        <h1 className="max-w-4xl text-balance text-5xl font-semibold leading-[1.02] tracking-tight sm:text-7xl">
          One stream in. A series of Shorts out.
        </h1>
        <p className="max-w-xl text-pretty text-lg leading-relaxed text-muted">
          Upload or record a video. Clipdesk analyses the whole thing, proposes the best moments,
          and renders platform-ready clips — YouTube Shorts, Reels or TikTok — with captions,
          trimmed and reviewed in the app.
        </p>
      </section>

      <section className="relative grid gap-4 lg:grid-cols-3">
        <DownloadCard
          title="Desktop app — macOS"
          body="The admin's local engine: capture, SSD import, MLX Whisper, models and rendering. Nothing heavy leaves the Mac."
          url={MAC_URL}
          slot="NEXT_PUBLIC_DOWNLOAD_MAC"
          meta=".dmg"
        />
        <DownloadCard
          title="Desktop app — Windows"
          body="The same shell on Windows, with the bundled FFmpeg recorder. See docs/desktop-app.md for the build and signing steps."
          url={WINDOWS_URL}
          slot="NEXT_PUBLIC_DOWNLOAD_WINDOWS"
          meta=".exe"
        />
        <Card>
          <div className="flex h-full flex-col gap-4">
            <div className="flex items-center justify-between gap-3">
              <h2 className="text-base font-medium">Web portal</h2>
              <Badge tone="accent">cloud</Badge>
            </div>
            <p className="text-sm leading-relaxed text-muted">
              Games, research, ideas, calendar, results and reviewers in any browser. The heavy
              clip engine stays on the desktop.
            </p>
            {WEB_PORTAL_URL ? (
              <a
                href={WEB_PORTAL_URL}
                className="mt-auto inline-flex items-center justify-center rounded-full bg-accent px-5 py-3 text-sm font-medium text-white transition hover:opacity-90"
              >
                Open the web portal
              </a>
            ) : (
              <div className="mt-auto flex flex-col gap-1">
                <span className="inline-flex items-center justify-center rounded-full bg-surface-3 px-5 py-3 font-mono text-xs text-muted ring-surface">
                  NEXT_PUBLIC_WEB_PORTAL
                </span>
                <span className="text-center text-[11px] text-muted">
                  Owner slot — the deployed origin.
                </span>
              </div>
            )}
          </div>
        </Card>
      </section>

      <section className="relative mt-4">
        <Card>
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div className="min-w-0 flex-1">
              <span className="text-[10px] uppercase tracking-[0.18em] text-muted">
                See it work
              </span>
              <h2 className="mt-1 text-base font-medium">Demo clip</h2>
              <p className="mt-1 text-sm text-muted">
                A real run on real gameplay: full-video analysis, ranked moments, captions, edit
                panel, finished Short.
              </p>
            </div>
            {DEMO_URL ? (
              <video src={DEMO_URL} controls className="h-40 w-24 shrink-0 rounded-lg bg-black object-contain" />
            ) : (
              <div className="flex h-40 w-24 shrink-0 items-center justify-center rounded-lg bg-surface-3 px-2 text-center font-mono text-[10px] text-muted ring-surface">
                NEXT_PUBLIC_DEMO_CLIP
              </div>
            )}
          </div>
        </Card>
      </section>

      <footer className="relative flex flex-wrap items-center justify-between gap-3 pt-10 text-xs text-muted">
        <span>Clipdesk · local engine + cloud plan</span>
        <Link href="/welcome" className="transition hover:text-text">
          About the product
        </Link>
      </footer>
    </main>
  );
}
