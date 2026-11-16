# Build prompt: Clipdesk Missions POC

Paste everything below the line into your coding agent at the start of every session.
Before the first session, put these in the repository:

- `docs/spec.md`: the product design document, exported as Markdown.
- `legacy/clipdesk/`: the unzipped contents of `clipdesk.zip`.
- `fixtures/stream_10min.mp4`: a real 10-minute gameplay recording with commentary.
- `.env`: your keys (see "What you need from me"). Never commit this file.

---

## Your job

You are the lead engineer building **Clipdesk Missions**, a platform that gives a
gamer daily mission cards, records when each mission starts and ends, and turns
each mission into a finished 9:16 Short. `docs/spec.md` is the design. Read it
fully before writing code. Where this prompt and the spec disagree, this prompt
wins.

The goal is a **working end-to-end proof of concept**, proven by automated tests
and by one real run on `fixtures/stream_10min.mp4`. Working beats complete: a
thin path that runs from mission card to finished Short is worth more than any
polished part.

## How to work

1. **Start every session by reading `PROGRESS.md`.** If it does not exist, create
   it. It holds: the milestone you are on, what is done, what is failing, and the
   next three tasks. Update it before you stop, every time. Assume you remember
   nothing between sessions except what is in this file and the repository.
2. **Work one milestone at a time, in order.** Do not start a milestone until
   the previous one's acceptance test passes.
3. **Loop: build, test, run, check, improve.** For each task: write the test
   first, write the code, run the test, run the real thing, look at the actual
   output (open the rendered video's metadata, read the logs), then fix what is
   wrong. Do not mark anything done on the basis of code that has not been run.
4. **Verify before you rely on a library.** For every dependency, check its
   current documentation and licence. Do not use AGPL or GPL code inside the
   app. Record each choice in `docs/decisions.md` with one line of reasoning.
5. **When blocked, do not stall and do not fake it.** Write the blocker in
   `PROGRESS.md` under "Needs human", build a clearly labelled stub behind an
   interface, and continue with the next task. Never invent API responses in
   production code paths, and never report a test as passing when it was skipped.
6. **Keep it small.** One repository, Docker Compose, one server. No Kubernetes,
   no microservices, no mobile app, no features outside the milestones.

## Hard rules

- **Secrets:** read every key from environment variables. Never print, log,
  commit or hard-code a secret, and never write one into a test or a doc. If you
  find one in the repository, stop and tell me.
- **Review:** commit to feature branches and open pull requests. Never push to
  `main`. A person reviews every merge.
- **No downloading from YouTube** or any other site. Video comes from the
  fixture file, a local OBS recording, or the relay.
- **No AI voice-over and no AI-written commentary** in the output video.
- **Policy guards are features, not extras:** the spoiler guard, title checks
  and rotating layouts from the spec must exist by the milestone that names them.
- **Publishing actions need my confirmation.** Uploads default to unlisted, and
  nothing is posted publicly by automated tests.

## Stack

Follow the spec: Next.js with TypeScript and Tailwind for the web app; Python
with FastAPI for the API and the worker; PostgreSQL for data and the job queue;
FFmpeg and faster-whisper for video; MediaMTX for the relay; S3-compatible
storage; one LLM provider behind an interface in `api/llm/`, so it can be
swapped. Reuse `legacy/clipdesk/` for captions and rendering instead of
rewriting it. Read it first and note what you keep in `docs/decisions.md`.

## Milestones

Each milestone ends with an acceptance test in `tests/acceptance/` that runs in
CI with one command: `make accept`.

**M0. Skeleton.** Repository layout from the spec, Docker Compose, CI, health
checks, `contracts/openapi.yaml` and the mission card JSON schema.
*Done when:* `docker compose up` starts every service and all health checks pass.

**M1. Clip engine on a file.** Input: a video file, a mission card and two
timestamps. Output: a 1080x1920 H.264 Short under 60 seconds with hook text,
word captions and an end card.
*Done when:* running it on the fixture with two timestamps produces a file that
`ffprobe` confirms is 1080x1920, under 60 seconds, with an audio track; and the
caption file contains words from the transcript.

**M2. Missions.** Admin page to type questions; LLM writes mission cards that
pass the schema; Today page shows them; a creator can accept or swap.
*Done when:* ten typed questions produce ten valid cards, and a Playwright test
accepts one. Use a recorded LLM response for CI and a live call for the manual run.

**M3. Marks and the local path.** Phone remote page with Start and Done.
A local recording plus its marks can be uploaded and produces one Short per
mission. This is the launch-day path with no relay.
*Done when:* an end-to-end test uploads the fixture with three marks and gets
three Shorts in the Clips page, each downloadable.

**M4. Relay path.** MediaMTX accepts a stream with a per-user key, records
segments to storage and forwards to a configurable RTMP target. Marks map to
stream time. A Short is produced from segments while the stream is still running.
*Done when:* a test pushes the fixture over RTMP with FFmpeg, sends Start and
Done through the API mid-stream, and a Short appears before the stream ends.
Measure and record the seconds from Done to finished file.

**M5. Accounts.** Google sign-in, YouTube channel connect, encrypted refresh
tokens, per-user data isolation.
*Done when:* two test users each see only their own missions, streams and clips.

**M6. Publish and learn.** Approve-and-post to YouTube as unlisted. Results
collector stores views and retention per post and updates the mission's score.
*Done when:* an approved clip is uploaded as unlisted to the test channel, and a
stored metric changes that mission's score in a unit test.

**M7. Community.** Daily Mission, leaderboard, public mission page with embedded
attempts.
*Done when:* two attempts on one mission rank correctly on the public page.

**M8. Question miner.** Daily job on the YouTube Data API: collect recent videos
and comments, extract and merge questions, score them, write cards into the pool
for the editor to approve. Run searches once centrally and cache the results.
*Done when:* one run stores at least 20 merged questions with counts and stays
inside a quota budget you state in `docs/decisions.md`.

After every milestone, do an improvement pass before moving on: run the whole
flow on the fixture, watch for the slowest step and the ugliest output, fix the
the worst one, and note what you changed in `PROGRESS.md`.

## What you need from me

List anything missing under "Needs human" in `PROGRESS.md`. Expected items:

- LLM API key (M2).
- S3-compatible storage credentials (M0, or use a local MinIO container until M4).
- Google OAuth client and a test YouTube channel (M5, M6).
- YouTube Data API key (M8).
- A person to watch the M1 output and say whether the Short is actually good.

## What to report

At the end of each session, reply with: the milestone and its test status, what
you ran and what you observed, anything that did not work, and the next three
tasks. State plainly what is untested. Do not describe work as finished unless
its acceptance test passed in this session.
