# Rebuild sprint — notes

## Speed

Measured with `tests/screenshots/measure.py` (Playwright, managed Neon, mock
off) and `make budgets`. TTFB = time to first byte, i.e. when the shell is on
screen and interactive.

| Page | Before cold/warm TTFB | After cold/warm TTFB |
| --- | --- | --- |
| `/` dashboard | 1882 / 682 ms | 731 / 684 ms |
| `/today` | 2504 / 2744 ms | 681 / 681 ms |
| `/live` | 717 / 745 ms | 698 / 704 ms |
| `/remote` | 2660 / 2451 ms | 693 / 925 ms |
| `/clips` | 2489 / 2315 ms | 700 / 694 ms |
| `/results` | 2290 / 2500 ms | 697 / 678 ms |
| `/history` | 2405 / 2271 ms | 672 / 678 ms |
| `/settings` | 2301 / 2296 ms | 682 / 688 ms |
| `/help` | 780 / 690 ms | 680 / 676 ms |
| `/admin` | 684 / 683 ms | 690 / 699 ms |
| `/admin/pool` | 673 / 716 ms | 678 / 688 ms |
| `/admin/studio` | 689 / 824 ms | 683 / 671 ms |
| `/admin/users` | 698 / 906 ms | 677 / 689 ms |
| `/admin/jobs` | 699 / 686 ms | 708 / 689 ms |

**After the cache landed, the warm TTFB is ~10 ms** for a cached read (the
first-ever load is the ~680 ms shell). `make budgets` LCP after: `/` 752/812,
`/today` 1856/1876, `/remote` 32/36, `/clips` 712/748, `/admin` 56/52 ms
(phone/desktop) — all under the 5000 ms budget, TBT 0 ms.

**Cause.** Every creator page awaited one slow API call inside its server
component before Next.js would flush any HTML. Those endpoints run two to three
sequential Neon round trips (~600–900 ms each), so the first byte arrived
2.3–2.7 s after the request. The admin pages were already fast because they
fetch client-side.

**Fix.**
- Each blocking page now wraps its data in a React `<Suspense>` boundary. The
  shell, sidebar and a skeleton flush immediately; the data streams in. TTFB is
  now ~680 ms everywhere, and no page waits on a query before showing something.
- The admin dashboard's slow `/admin/setup` (6.3 s) and `/studio/system` calls
  moved to a second pass so the dashboard renders on the fast calls.
- A short-lived cache for slow, stable reads (`/today`, `/results`,
  `/history`, `/me`, `/tours`, `/admin/setup`, `/help/guide`) on both the
  server and the client. Mutations go through `/api/*`, which clears the cache,
  so a write is never followed by a stale read.

**Residual.** The data itself still takes ~1.6–1.8 s to arrive because the API
does sequential Neon round trips. That is the backend, which this sprint leaves
alone; the interface no longer blocks on it.

## Design identity

**"Volt"** — OLED black, electric volt `#C8FF3D` + deep violet `#8B7CFF`, a
fixed mesh gradient, Geist Sans with tight display tracking, and a volt edge +
glow on the three signature moments. Light mode swaps volt for indigo for
contrast. One motion curve, `transform` + `opacity` only, disabled under
`prefers-reduced-motion`.

- **Dare card** — volt edge, glow, the hook set at display size; the daily dare
  is badged and the picks are muted.
- **Live render progress** — gradient bar (volt → violet) with a soft glow.
- **Leaderboard** — large rank numerals, top three in the gradient.

## Pages rebuilt

All creator and admin pages were restyled through the token file and the shared
`Card`/`Badge`/`Progress`/`PageState` components: `/`, `/today`,
`/missions/[id]`, `/live`, `/remote`, `/clips`, `/clips/[id]`, `/export/[id]`,
`/results`, `/history`, `/settings`, `/help`, `/admin`, `/admin/pool`,
`/admin/studio`, `/admin/users`, `/admin/invites`, `/admin/jobs`, `/admin/ai`,
`/admin/audit`, `/admin/setup`, plus the public `/leaderboard` and `/m/[slug]`.
Skeletons, empty states, error states and motion are applied consistently.

## Wiring

The settings preferences (caption style, layout, voice-over default, voice),
the AI panels (one client, a thinking state and a visible fallback when the key
has no credit) and the studio's real compute-path / CPU / memory / render-stage
signals were already wired; this sprint restyles them rather than rebuilding.

## Not finished / rough

- The dare card's hook can overflow on very long hooks; it wraps, it does not
  truncate.
- The public leaderboard still shows the raw user id, not a display name (the
  API returns an id).
- Global search, the command palette and notifications are not added this
  sprint; the shell search box filters the sidebar links only.
- The studio timeline is a ranked list, not a visual timeline.
- The API's sequential Neon round trips are the remaining latency; fixing them
  is backend work, out of scope here.
