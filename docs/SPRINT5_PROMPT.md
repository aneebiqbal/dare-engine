# Sprint 5 prompt: finish, speed up, and add the live show layer

Paste everything below the line into your coding agent at the start of every session.

---

Read `PROGRESS.md` and every prompt in `docs/` first. All earlier rules apply:
test first, run the real thing, never report unproven work as working, secrets
only from the environment, Gate 0 reported every session, no pushes to `main`.

## Part 0: finish Sprint 4 before anything new

Do these in order. They are already specified in `docs/SPRINT4_PROMPT.md`.

1. **R3 / M4.** Real stream keys, MediaMTX recording to storage, Live page
   connection status, a Short produced mid-stream from an FFmpeg-pushed stream.
   Record the seconds from Done to finished file.
2. **R6 proof.** A test that a deleted user leaves no rows and no stored files.
3. **Design pass D1 to D3.** `docs/design.md`, pages rebuilt to it on real
   data, three rounds of fixing the five weakest screens, keyboard tests,
   performance budgets.
4. **M12 hardening and M13 scale measurement.**

Do not start Part 1 until all four are done or blocked by a named Gate 0 item.

## Part 1: a faster, sturdier worker

Three clips took two to three minutes rendered one after another.

**S1. Parallel rendering.** A worker pool sized from CPU count, configurable.
Jobs for one stream render concurrently. Each job is idempotent and safe to
retry; a crashed worker's job returns to the queue after a timeout.
*Done when:* three clips from one upload finish in clearly less wall time than
serial, the measured times are in `docs/performance.md`, and killing a worker
mid-render still ends with three finished clips and no duplicates.

**S2. Render stages and progress.** Split a job into fetch, transcribe, select,
render, upload. Store the stage and percentage; show it live on the Clips page.
Cache the transcript so a re-render after a trim does not transcribe again.
*Done when:* a trim re-render skips transcription, proven by a test, and the
Clips page shows stage changes in a Playwright test.

**S3. Hardware encoding where present.** Detect an available hardware H.264
encoder and use it, with software encoding as the fallback. Never assume one.
*Done when:* both paths produce a valid file in tests and the choice is logged.

## Part 2: the live show layer

These features make the stream itself the product. Build each behind a feature
flag.

**L1. Stream overlay.** A transparent page for OBS's browser source: current
mission, running timer, last result, leaderboard rank. Three visual themes.
Updates within a second of a tap on the remote.
*Done when:* a test drives Start and Done and sees the overlay change, and the
setup steps are documented with screenshots.

**L2. OBS dock.** The remote's controls as a compact page that can be added to
OBS as a custom dock, so the creator needs no second device.
*Done when:* the dock page works at 300 px wide and passes the same flow test
as the phone remote.

**L3. Chat votes.** The creator opens a timed vote between two missions. Votes
come from live chat messages. The winner becomes the next mission and its hook
text says chat chose it. Put chat behind a `ChatSource` interface with two
implementations: a simulator for tests, and YouTube live chat.
*Done when:* the simulator drives a full vote in a test. Report the YouTube
implementation as built and unproven until an OAuth client exists.

**L4. Paid bounties.** A paid chat message containing a mission keyword puts
that mission in a bounty queue with the viewer's display name on the overlay.
The creator accepts or declines each one. The app only reads payment events
that the platform reports; it never handles money itself.
*Done when:* the simulator's paid message appears in the queue and on the
overlay after acceptance. Store the display name only for the stream's
duration unless the creator pins it, and record that choice in
`docs/decisions.md`.

**L5. Seasons.** Leaderboards grouped into weekly seasons with a standings
page and a weekly showdown: one mission, all attempts, ranked.
*Done when:* attempts across two simulated weeks land in the right seasons.

**L6. Notifications inside the app.** Clip ready, bounty received, rank
changed. Delivered over the existing live-update channel, with a history panel.
*Done when:* each event appears in a test and survives a page reload.

## Report format

Unchanged, plus: measured render times before and after Part 1, and for every
Part 2 feature, whether it has run against a real stream or only the simulator.
