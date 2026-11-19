# Launch

Launch readiness, the git-history cleanup plan, and the inputs only a human can
supply. Status detail is in `PROGRESS.md` and `docs/BUILD_STATE.md`.

## Launch checklist

| Item | Status |
| --- | --- |
| App builds and runs locally | yes (`make up`) |
| Acceptance suite | 67 passed, 2 skipped, 0 failed |
| Unit + licence check | 60 passed, 1 skipped; `make check` 2 passed |
| Accessibility | axe-core 0 serious/critical, 30 pages x phone/desktop |
| Performance budgets | TBT 0 ms; LCP under the 5000 ms budget (`docs/screens/budgets.json`) |
| Dependency licences | no GPL/AGPL in the core (`docs/licences.md`) |
| Copyrighted media in git | **not clean** — see the cleanup plan below |
| Real gameplay footage | **missing** — `fixtures/stream_10min.mp4` |
| Human clip verdict | **missing** |
| Live AI | not proven (key returns 402/429) |
| Live research sources | not proven (sample feed) |
| Production database | Neon configured; the default local run uses container Postgres |
| Object storage | local disk by default; S3 unproven |
| TLS, backups, logging, error reporting | not built |
| Publishing to YouTube/TikTok/Instagram | calendar queue + manual marker; YouTube API and TikTok/IG approval blocked |
| Git remote | exists, URL is clean, but points at `dare-engine` |

## Git-history cleanup plan

Read-only audit, 2026-11-19. Tracked bytes: 45.2 MB; `.git`: 66 MB.

### What is tracked that should not be

| File | Size | Added | Status |
| --- | --- | --- | --- |
| `fixtures/gameplay_4min.mp4` | 33,201,383 B (31.7 MB) | `1fa80dd` (2026-11-19) | **Publisher trailer** (GTA V, IGN watermark), not the owner's gameplay. Do not ship, do not use as demo footage. |
| `tests/fixtures/standin_speech_45s.mp4` | 1,421,695 B | `59ac367` (2026-11-17) | Synthetic stand-in (test pattern + macOS `say` speech). Safe to keep; used by 9 test files. |
| `docs/screens/*.png` | 116 files, 10.4 MB | `1a88a75`, `3f0c53b`, `1fa80dd` | First-party UI screenshots, regenerable with `make screens`. Not copyrighted, but binary weight. |
| `tests/screenshots/lib/axe.min.js` | 653,780 B | `1a88a75` | axe-core 4.14.1, MPL-2.0, dev/test only. Never copied into an image. |

The trailer is present on `main`, `research-brain`, `sprint-6`, `ui-rebuild`
and `origin/main` (blob `fb52e783`). It was pushed, so removing it from the
working tree alone does not remove it from the remote.

Root cause: `.gitignore` ignores `*.mp4` but then un-ignores `!fixtures/*.mp4`,
so anything dropped in `fixtures/` is tracked.

### Plan (needs the owner's approval; no history rewrite without sign-off)

1. **Decide the remote first.** `origin` is
   `https://github.com/aneebiqbal/dare-engine.git`. Confirm whether this is the
   intended product remote or a scratch repo.
2. **Preferred: a fresh private repo.** Create a new remote, add it as `origin`
   (or a second remote), and push only the intended tree. No history rewrite,
   no force push, no coordination with other clones.
3. **If the current remote must be reused, purge the blob from history.**
   `git filter-repo --path fixtures/gameplay_4min.mp4 --invert-paths` (or
   `git filter-branch`), then force-push every branch. This rewrites shared
   history and breaks other clones; do not run it without the owner's explicit
   approval and without telling everyone who has a clone.
4. **Minimum safe change, no history rewrite** (the blob stays in history and
   on `origin/main`):

   ```sh
   git rm --cached fixtures/gameplay_4min.mp4
   ```

   Then edit `.gitignore`: replace `!fixtures/*.mp4` with `!fixtures/.gitkeep`
   and keep `!tests/**/*.mp4` for the synthetic stand-in. Commit.
5. **Fix the tests that read the trailer.**
   - `tests/unit/test_ssd.py` reads the 33 MB trailer into memory and asserts
     `duration_seconds > 200`; it breaks when the file is gone. Point it at a
     generated fixture or the stand-in with a relaxed assertion.
   - `tests/unit/test_transcribe.py` returns early when the trailer is missing,
     so the test silently passes. Change the early return to `pytest.skip`.
6. **Screenshots (optional).** Either keep them as evidence or:

   ```sh
   git rm --cached docs/screens/*.png
   ```

   and ignore `docs/screens/*.png`, regenerating them with `make screens`.
   Saves 10.4 MB.
7. **Verify after cleanup:**

   ```sh
   git ls-files | grep -E '\.(mp4|mov|mkv|zip)$'
   ```

   should list only `tests/fixtures/standin_speech_45s.mp4`. Check
   `du -sh .git` and confirm no `.env`, `*.key` or `*.pem` is tracked.

## Human inputs still required

1. **The owner's own gameplay recording with commentary**, saved as
   `fixtures/stream_10min.mp4`. This is the only thing that makes the
   clip-quality verdict meetable; the detector and grammar are validated on a
   publisher trailer and a synthetic stand-in. Do not substitute the trailer.
2. **AI and source keys with credit.** `LLM_API_KEY` (the account returns
   402/429), `YOUTUBE_API_KEY`, the Reddit app, `RAWG_API_KEY`. Until then the
   AI paths run on the recorded provider and the brain on the sample feed.
3. **A safe git remote.** `origin` exists and its URL is clean (no embedded
   token), but it points at `dare-engine`, not a Clipdesk repo. Choose the real
   remote and use a credential helper; never put a token in the URL. Note:
   `PROGRESS.md` and `docs/BUILD_STATE.md` still say the URL embeds a live
   GitHub token — that is stale.
4. **A decision on the GPL voice add-on.** Keep `piper-tts` as the optional
   `make voice` add-on, or replace the TTS engine. The core stays GPL-free
   either way (`docs/licences.md`).
5. **Object storage credentials** for anything beyond local disk (S3 or R2).
6. **Legal review of the FFmpeg build** before commercial use.
7. **A person to watch the rendered clips** and record one verdict line each.

## Doc drift found while auditing

- `PROGRESS.md` Part 0 and `docs/BUILD_STATE.md` say `origin` embeds a live
  GitHub token. It does not: `git config --get remote.origin.url` returns a
  clean URL. The remote does exist, so the older "no git remote" claims in
  `docs/context/14-gaps-and-risks.md` are stale too.
- Fixed 2026-11-19: `piper-tts` now points at `worker/requirements-voice.txt`
  in `docs/context/13-dependencies-and-licences.md`, `01-repository-map.md`
  and `10-ai.md` (`docs/licences.md` is the current manifest);
  `docs/decisions.md`'s Sprint 6 row says GPL-3.0-or-later;
  `docs/performance.md`'s LCP table matches `docs/screens/budgets.json`;
  `docs/context/*.md` points at `worker/worker_app/...`; and
  `docs/context/05-api.md` says 105 contract paths.
- `tests/unit/test_transcribe.py` line 19 says the trailer is "not committed".
  It is committed, and it is a publisher trailer.
