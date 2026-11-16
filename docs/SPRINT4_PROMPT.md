# Sprint 4 prompt: make every page real

Paste everything below the line into your coding agent at the start of every session.

---

## The goal

Fourteen pages currently run on the mock layer. This sprint ends when **no page
depends on a mock**: every screen reads and writes through the real API, the
real database and the real worker. After that come a design pass, hardening and
measured scale.

Read `PROGRESS.md`, `docs/spec.md`, `docs/BUILD_PROMPT.md`,
`docs/SPRINT2_PROMPT.md` and `docs/SPRINT3_WEB_PROMPT.md` first. All their rules
still apply. Where they conflict with this prompt on order, this prompt wins.

## Rules for this sprint

1. **A page is done only against the real backend.** `make web-accept` must run
   with `NEXT_PUBLIC_API_MOCK=0` for every page you mark done.
2. **CI enforces it.** Add a check that fails if `web/lib/mock.ts` is imported
   outside test files. Until it passes, keep a "Mocked pages" list in
   `PROGRESS.md`; every entry must name the exact Gate 0 item blocking it, or
   be fixed.
3. **Blocked by a human is not blocked for you.** For anything waiting on a
   key or an approval, build the full feature behind an interface with contract
   tests and a local stand-in, and report it as "built, unproven against the
   real service". Never as working.
4. **Gate 0 still applies.** Without `fixtures/stream_10min.mp4`, nothing that
   judges clip quality is accepted. Say so in every report.

## Part 1: real backend behind every page

**R1. Local sign-in and real sessions.** Add a development sign-in that creates
real users and real sessions in the database, so per-user pages stop needing
mocks. It is enabled only by an environment flag, refuses to start in a
production build, and a test proves that. All endpoints enforce ownership now.
Google sign-in later replaces only the identity provider.
*Done when:* two dev users each see only their own data, and a production
build with the flag set fails to start.

**R2. Marks, upload and clips (M3).** Real `POST /marks` with stream time, the
offline queue flushing to the real endpoint, the local upload path, one clip
job per mission, and real Clips, clip review, History and stream detail pages.
*Done when:* the fixture with three marks yields three Shorts through the real
UI, with no mock.

**R3. Relay and the Live page (M4).** Real stream keys, masked in the UI, real
connection status, recording to storage, a Short produced mid-stream.
*Done when:* an FFmpeg-pushed stream shows as connected on the Live page, and
Start and Done on the remote produce a Short before the stream ends. Record the
seconds from Done to finished file.

**R4. Community (M7).** Real Daily Mission sets, mission pages, leaderboards
and creator profiles, driven by real attempts.
*Done when:* two dev users' attempts rank correctly on the public page.

**R5. Results.** Real Results page from the metrics table. Until a YouTube key
exists, metrics come from manual entry and from a collector interface with a
stand-in; the page states which source each number came from.
*Done when:* entering metrics changes a mission's score and the page shows it.

**R6. Settings.** Real preferences, data export and account deletion that
removes every row and file for that user.
*Done when:* a deleted dev user leaves nothing behind, proven by a test.

**R7. Admin.** Real templates, users, job queue and health pages.
*Done when:* a failed job appears on the jobs page with its error and can be
retried from there.

**R8. The full journey, real.** Rerun the W7 journey with the mock off.
*Done when:* sign-in, accept, Start and Done, review and leaderboard all pass
against the real stack, and the "Mocked pages" list is empty or every entry
names its Gate 0 blocker.

## Part 2: design to a professional standard

**D1. Direction.** Write `docs/design.md`: the concept in three sentences, the
type scale, colour roles, spacing, motion rules, and the three signature
moments of the product: the live mission timer, the moment a finished Short
appears, and the leaderboard. Choose deliberately. Do not ship default
component-library looks.

**D2. Apply and iterate.** Rebuild every page to that direction with real data
on screen, not mock data. Each page gets real empty, loading and error states
with useful wording. Respect reduced-motion settings.
Then run three rounds: take all screenshots, list the five weakest screens with
the specific reason each is weak, fix them, repeat.

**D3. Prove it.** Keyboard-only Playwright tests for the main flows, checking
focus order and visible focus. Automated accessibility checks on every page.
Performance budgets on the five main pages, measured and recorded in
`docs/performance.md`.
*Done when:* all three pass and the final screenshots are saved for human
review. A person decides whether it looks good. You do not.

## Part 3: hardening and scale

Do M12 (hardening) and M13 (scale readiness) exactly as written in
`docs/SPRINT2_PROMPT.md`. Report measured limits in `docs/capacity.md`. Do not
claim a user capacity you did not measure.

## Still waiting on the human

Build to the interface, test against stand-ins, and list as unproven:
Google sign-in (M5), posting to YouTube (M6), the question miner (M8),
billing (M10), TikTok and Instagram (M14).

## Report format

Unchanged, plus: the "Mocked pages" list with blockers, and a table of every
feature marked "built, unproven against the real service".
