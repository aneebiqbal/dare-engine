# Start here

Two ways to run the same product. Every step below is a command or a screen.

| You are | Run |
| --- | --- |
| A gamer, or an admin planning on any browser | the **cloud website** (`docs/deploy-web.md`) |
| The admin who records and cuts clips | the **desktop app** on your Mac (`docs/desktop-app.md`) |

The two share one database and one API. The cloud holds the plan; the desktop
does the heavy work. Nothing heavy is uploaded.

## The fastest path: all-in-one on one Mac

```sh
cp .env.example .env      # local defaults; .env is gitignored
make up                   # database, API, worker, web, relay
make doctor               # every check PASS (14/14)
make create-admin         # creates the first administrator (prompts)
```

Open <http://localhost:3100> and sign in. First run builds the images; later
starts are seconds. This runs the whole stack on one machine — the way to try it
today. To give other people access, deploy the cloud half and install the
desktop app (below).

## 1. Add a game

Admin → **Games** → **Add game** → search RAWG (or add by slug) → **Add**.

Research runs daily per enabled game, or press **Research now**.

## 2. Generate ideas

Admin → **Games** → the game → **Candidates**.

Each candidate is a sourced idea: the hook, the question, the win condition and
the source it came from. **Approve**, then **Assign** to a gamer. Only an
approved idea reaches a gamer.

With no source keys the brain runs on the saved sample feed and is flagged
`fallback`; with `YOUTUBE_API_KEY` / Reddit / `RAWG_API_KEY` it reads live.

## 3. Play a dare (gamer)

Sign in as the gamer (an admin invites one from **Admin → Invites**). Then:

1. **Today** → accept the dare.
2. **Go Live** → copy the stream address and key into OBS; the page shows the
   real OBS connection, scene and mic state.
3. **Remote** → tap **Start** when the moment begins and **Done** when it ends.

## 4. Make clips

Admin → **Studio**.

- **Import from SSD**: plug in the drive, **Refresh drives**, choose a video,
  **Import**. “Process and release” deletes the inbox copy after a safe import.
  (You can also upload a file directly, or record in the desktop app.)
- **Find moments**: the detector ranks the recording and shows each candidate
  with its score and reasons.
- **AI also suggest clips** (optional): tick the box, or press **Ask the vision
  model**. A small vision model samples the recording — about one frame every
  five seconds, never every frame — and proposes extra moments with a reason and
  the frame it judged. It loads a model only for that pass and unloads it after.
- **Accept** a candidate (or **Accept top 3**) → **Generate**. The render shows
  the real compute path (MLX Whisper on Metal, or CPU), live stages and the
  finished clip.

The clip is cut, re-transcribed, given word-synced animated captions and the
grammar (cold open, hook, payoff, clean end). Nothing leaves the machine.

## 5. Review, comment, schedule

Open the clip from **Clips**.

- Add **commentary / added value** — your own context, required for monetisation.
- **Approve**, then **Schedule** it on the **Calendar** (drag it onto a day).
- **Export package** produces the video, thumbnail, title, description and tags.

## 6. Results

**Results** shows views, swipe-through, saves and shares, and a summary of what
is working. Those numbers feed the idea ranking.

## 7. Models & Setup

Admin → **Models** is the single source of truth for the local engine. It shows
the three models the engine needs — transcription (MLX Whisper), writing (the
LLM) and the optional vision model — with installed state, size, “fits this Mac”,
download progress, working status, unload and a live memory readout.

```sh
make setup-engine       # Ollama + MLX Whisper
make mlx-bridge         # host bridge for Metal transcription and the vision model
make ssd-bridge         # host bridge for the SSD reader
```

One-click **Install** pulls a missing model with visible progress. The memory
readout proves one model loads at a time: each pass unloads the previous model
and the screen shows it.

## 8. The desktop app

`docs/desktop-app.md` builds and installs the admin’s app: one application with
the capture (OBS, or a built-in recorder), the SSD import, the clip engine and
the Models screen. It talks to the same cloud account and database.

## 9. Deploy the cloud website

`docs/deploy-web.md` is the exact process: managed Postgres, TLS with Caddy,
`docker compose up api web`, health check, rate limiting, error reporting and
`make backup`.

## What is real right now

- The full flow runs on real data: real accounts, real jobs, real FFmpeg
  renders, real OBS state, real local models.
- The research brain runs on the sample feed unless you add source keys; it says
  so.
- The AI writing runs on the recorded provider unless you add a live key; it says
  so.
- The vision pass is built and unit-tested; a real suggestion run needs the
  vision model installed and a real recording.

## What still needs you

- **Your own gameplay recording** (`fixtures/stream_10min.mp4`) — the only thing
  that makes a real demo clip. Drop it in and run the Studio.
- **Key credit** for live AI and live research sources.
- **A host and a domain** for the cloud website, and **a git remote decision**
  before the repo is published.
