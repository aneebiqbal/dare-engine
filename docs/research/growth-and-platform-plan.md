# Growth and platform plan

A plan, not a promise. The product is demo-ready; the launch depends on the
owner's footage, key credit and host (see `docs/BUILD_STATE.md`).

## The product in one line

Clipdesk Missions turns a gameplay stream into a series of captioned vertical
Shorts: the platform writes the dare, the creator plays it, and the local engine
cuts, captions and packages the clip.

## Who it is for

| Person | What they do | Where |
| --- | --- | --- |
| Gamer / creator | Sign in, get a dare, go live, tap Start/Done, see history and results | Any browser |
| Admin / editor | Add games, approve sourced ideas, assign, cut clips, schedule, read results | Browser for planning; desktop app for the heavy work |

## Why someone would use it

1. **The dare is written before the game is played.** Sourced ideas, not a blank
   page.
2. **The clip is made from the exact window.** Start/Done marks, then a detector
   and an optional vision pass widen the net.
3. **Captions are word-synced and the grammar is deliberate.** Cold open, hook,
   payoff, clean end.
4. **It runs locally.** The footage and the models never have to leave the
   machine; the cloud is only the plan.

## The differentiator

The **vision pass**: a small VLM samples the recording and proposes clips the
creator never marked, each with a reason and the frame it judged. The admin
accepts or rejects. It is opt-in, sampled (never every frame) and memory-safe.

## Packaging

| Tier | What you get | Cost |
| --- | --- | --- |
| Cloud web | Accounts, dares, approval, calendar, results, community | A small VPS + managed DB |
| Desktop app | The clip engine, capture, models, SSD import | Free (the user's Mac) |
| Local models | MLX Whisper, the LLM, the vision model | Free, downloaded once |

The free tier is the whole product for a single admin. There is no billing in the
code (`docs/BUILD_STATE.md`: billing is out of scope).

## Launch checklist

1. **The owner's footage.** Drop `fixtures/stream_10min.mp4` in and run the
   Studio. A human watches the clip. Until then clip quality is unproven.
2. **Key credit** for live AI and live research sources. The fallbacks are
   flagged, never presented as live.
3. **A host and a domain.** `docs/deploy-web.md` reproduces the deployment.
4. **A git remote decision.** The repo's history and the leaked token (revoke
   it) are the owner's call. See `docs/launch.md`.
5. **A real desktop test.** Install the `.dmg`, start the stack, record a clip.
6. **The vision model.** Install `qwen2.5vl:7b` and run the sampled pass on a
   real recording.

## What we would measure

- Dares accepted → clips rendered (the funnel).
- Vision suggestions accepted vs rejected (does the net help?).
- Seconds from recording to a ready clip, and the compute path used.
- Clip quality: a human verdict, not a metric.

## Honest limits

- No YouTube/TikTok posting; export is a zip.
- No billing, no Google sign-in, no S3 proof.
- Clip quality is unproven until the owner watches real clips.
