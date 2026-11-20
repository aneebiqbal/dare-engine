# Start here

The fastest path from a clean checkout to a real clip. Every step below is a
command or a screen in the app.

## 1. Run it

```sh
cp .env.example .env      # local defaults; .env is gitignored
make up                  # database, API, worker, web, relay
make doctor              # every check PASS (14/14)
make create-admin        # creates the first administrator (prompts)
```

Open <http://localhost:3100> and sign in as the admin you just created.

First run builds the images; later starts are seconds.

## 2. Add a game

Admin → **Games** → **Add game** → search RAWG (or add by slug) → **Add**.

The game appears in the grid. Research runs daily per enabled game, or press
**Research now**.

## 3. Generate ideas

Admin → **Games** → the game → **Candidates**.

Each candidate is a sourced idea: the hook, the question, the win condition and
the source it came from. Press **Approve**, then **Assign** to a gamer. Only an
approved idea reaches a gamer.

With no source keys the brain runs on the saved sample feed and is flagged
`fallback`; with `YOUTUBE_API_KEY` / Reddit / `RAWG_API_KEY` in `.env` it reads the
live sources.

## 4. Play a dare (gamer)

Sign in as the gamer (an admin can invite one from **Admin → Invites**, or use a
test sign-in). Then:

1. **Today** → accept the dare.
2. **Go Live** → copy the stream address and key into OBS; the page shows the
   real OBS connection, scene and mic state.
3. **Remote** → tap **Start** when the moment begins and **Done** when it ends.

## 5. Make clips

Admin → **Studio**.

- **Import from SSD**: plug in the drive, **Refresh drives**, choose a video,
  **Import**. “Process and release” deletes the inbox copy after a safe import.
  (You can also upload a file directly.)
- **Find moments**: the detector ranks the recording and shows each candidate
  with its score and reasons.
- **Accept** a candidate (or **Accept top 3**) → **Generate**. The render shows
  the real compute path (MLX Whisper on Metal, or CPU), live stages and the
  finished clip.

The clip is cut, re-transcribed, given word-synced animated captions and the
grammar (cold open, hook, payoff, clean end). Nothing leaves the machine.

## 6. Review, comment, schedule

Open the clip from **Clips**.

- Add **commentary / added value** — your own context, required for monetisation.
- **Approve**, then **Schedule** it on the **Calendar** (drag it onto a day).
- **Export package** produces the video, thumbnail, title, description and tags.

## 7. Results

**Results** shows views, swipe-through, saves and shares, and a summary of what
is working. Those numbers feed the idea ranking.

## 8. Local models (optional)

```sh
make setup-engine       # Ollama + MLX Whisper
make mlx-bridge         # host bridge for Metal transcription
make ssd-bridge         # host bridge for the SSD reader
```

Admin → **Models** shows every local model, its size, whether it fits this Mac,
the MLX download state, and a live memory readout. Pull, unload and free-all are
real.

## What is real right now

- The full flow above runs on real data: real accounts, real jobs, real FFmpeg
  renders, real OBS state, real local models.
- The research brain runs on the sample feed unless you add source keys; it says
  so.
- The AI writing runs on the recorded provider unless you add a live key; it says
  so.

## What still needs you

- **Your own gameplay recording** (`fixtures/stream_10min.mp4`) — the only thing
  that makes a real demo clip. Drop it in and run the Studio.
- **Key credit** for live AI and live research sources.
- **A git remote decision** before the repo is published.
