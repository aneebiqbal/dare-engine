import Link from "next/link";
import fs from "node:fs";
import path from "node:path";
import { Button, Card, Eyebrow } from "@/components/ui";

export const dynamic = "force-dynamic";

type Download = {
  id: string;
  title: string;
  body: string;
  requirements: string;
  file: string;
  url: string;
  size: number;
  sha256: string;
};

type Manifest = {
  version: string;
  web_portal_url: string;
  demo_clip: { file: string; url: string };
  downloads: Download[];
};

const EMPTY: Manifest = {
  version: "",
  web_portal_url: "",
  demo_clip: { file: "", url: "" },
  downloads: [],
};

function readManifest(): Manifest {
  try {
    const raw = fs.readFileSync(
      path.join(process.cwd(), "releases", "manifest.json"),
      "utf8",
    );
    return { ...EMPTY, ...(JSON.parse(raw) as Partial<Manifest>) };
  } catch {
    return EMPTY;
  }
}

/** A local public file if it exists, else an explicit CDN URL, else null. */
function asset(href: { file: string; url: string }): string | null {
  if (href.url) return href.url;
  if (!href.file) return null;
  const name = path.basename(href.file);
  const onDisk = path.join(process.cwd(), "public", "downloads", name);
  return fs.existsSync(onDisk) ? `/downloads/${name}` : null;
}

function size(bytes: number): string {
  if (!bytes) return "";
  const mb = bytes / (1024 * 1024);
  return mb >= 1 ? `${mb.toFixed(1)} MB` : `${Math.round(bytes / 1024)} KB`;
}

export default function Landing() {
  const manifest = readManifest();
  const portal =
    manifest.web_portal_url || process.env.NEXT_PUBLIC_WEB_PORTAL || "";
  const demo = asset(manifest.demo_clip);

  return (
    <main className="relative flex min-h-[100dvh] flex-col overflow-hidden px-6 py-10 sm:px-10">
      <div aria-hidden className="pointer-events-none absolute inset-x-0 top-0 h-px bg-accent" />

      <header className="relative flex flex-wrap items-center justify-between gap-3">
        <Link href="/welcome" className="text-sm font-medium tracking-tight text-text">
          clipdesk
        </Link>
        <nav className="flex flex-wrap items-center gap-2">
          <a
            href="#download"
            className="rounded-md px-4 py-2 text-sm text-muted ring-surface transition hover:bg-surface-2 hover:text-text"
          >
            Download
          </a>
          {portal ? (
            <a
              href={portal}
              className="rounded-md px-4 py-2 text-sm text-muted ring-surface transition hover:bg-surface-2 hover:text-text"
            >
              Open the web portal
            </a>
          ) : (
            <Link
              href="/signin"
              className="rounded-md px-4 py-2 text-sm text-muted ring-surface transition hover:bg-surface-2 hover:text-text"
            >
              Open the web app
            </Link>
          )}
          <Link
            href="/signin"
            className="rounded-md px-4 py-2 text-sm text-text ring-surface transition hover:bg-surface-2"
          >
            Sign in
          </Link>
        </nav>
      </header>

      <section className="relative flex flex-1 flex-col justify-center gap-6 py-24">
        <Eyebrow>{manifest.version ? `Release ${manifest.version}` : "One product, three ways to run it"}</Eyebrow>
        <h1 className="max-w-4xl text-balance text-5xl font-semibold leading-[1.02] tracking-[-0.02em] sm:text-7xl">
          One stream in. A series of Shorts out.
        </h1>
        <p className="max-w-xl text-pretty text-lg leading-relaxed text-muted">
          Upload or record a video. Clipdesk analyses the whole thing, proposes the best moments,
          and renders platform-ready clips — YouTube Shorts, Reels or TikTok — with captions,
          trimmed and reviewed in the app.
        </p>
        <div className="flex flex-wrap gap-3">
          <a
            href="#download"
            className="inline-flex items-center justify-center rounded-md bg-accent px-6 py-3 text-sm font-medium text-accent-ink transition hover:bg-accent/92"
          >
            Get the desktop app
          </a>
          {portal && (
            <a
              href={portal}
              className="inline-flex items-center justify-center rounded-md px-6 py-3 text-sm font-medium text-text ring-surface transition hover:bg-surface-2"
            >
              Use the web portal
            </a>
          )}
        </div>
      </section>

      <section id="download" className="relative flex flex-col gap-4 py-10">
        <div className="flex items-end justify-between gap-4">
          <h2 className="text-2xl font-semibold tracking-[-0.02em]">Download the app</h2>
          {manifest.version && (
            <span className="font-mono text-xs text-muted">v{manifest.version}</span>
          )}
        </div>
        <div className="grid gap-4 lg:grid-cols-2">
          {manifest.downloads.map((d) => {
            const href = asset(d);
            return (
              <Card key={d.id}>
                <div className="flex h-full flex-col gap-4">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <h3 className="text-base font-medium">{d.title}</h3>
                      <p className="mt-1 text-sm leading-relaxed text-muted">{d.body}</p>
                    </div>
                    <span className="folio shrink-0">{d.requirements}</span>
                  </div>
                  <div className="mt-auto flex flex-col gap-2">
                    {href ? (
                      <>
                        <a
                          href={href}
                          download
                          className="inline-flex items-center justify-center rounded-md bg-accent px-5 py-3 text-sm font-medium text-accent-ink transition hover:bg-accent/92"
                        >
                          Download {d.title}
                          {size(d.size) ? ` · ${size(d.size)}` : ""}
                        </a>
                        {d.sha256 && (
                          <span className="break-all font-mono text-[10px] text-muted">
                            sha256 {d.sha256}
                          </span>
                        )}
                      </>
                    ) : (
                      <span className="inline-flex items-center justify-center rounded-md bg-surface-3 px-5 py-3 text-sm font-medium text-muted ring-surface">
                        Not uploaded yet
                      </span>
                    )}
                  </div>
                </div>
              </Card>
            );
          })}
          {manifest.downloads.length === 0 && (
            <Card>
              <p className="text-sm text-muted">
                No release manifest yet. Run <span className="font-mono text-xs">scripts/prepare-release.sh</span> to
                publish the installers.
              </p>
            </Card>
          )}
        </div>
        <p className="text-xs text-muted">
          The desktop app carries the local engine and your footage never leaves the machine. The
          web portal holds the plan: games, research, calendar and results.
        </p>
      </section>

      <section className="relative mt-4">
        <Card>
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div className="min-w-0 flex-1">
              <span className="folio">See it work</span>
              <h2 className="mt-1 text-base font-medium">Demo clip</h2>
              <p className="mt-1 text-sm text-muted">
                A real run on real gameplay: full-video analysis, ranked moments, captions, edit
                panel, finished Short.
              </p>
            </div>
            {demo ? (
              <video
                src={demo}
                controls
                className="h-44 w-auto shrink-0 rounded-md bg-black ring-surface"
              />
            ) : (
              <div className="flex h-44 w-24 shrink-0 items-center justify-center rounded-md bg-surface-3 px-2 text-center font-mono text-[10px] text-muted ring-surface">
                demo clip not uploaded
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
