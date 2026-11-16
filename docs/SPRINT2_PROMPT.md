# Sprint 2 prompt: Clipdesk Missions, from proof of concept to product

Save the first prompt in the repository as `docs/BUILD_PROMPT.md`.
Paste everything below the line into your coding agent at the start of every session.

---

## Where we are

M0 and M1 pass on a stand-in fixture. Read `PROGRESS.md`, `docs/spec.md` and
`docs/BUILD_PROMPT.md` first. Every working rule and hard rule in
`docs/BUILD_PROMPT.md` still applies. This prompt adds scope; it removes nothing.

Known gaps from the last session, to close before anything else is called done:

- M1 has never run on real gameplay. The stand-in proves the pipeline, not the output.
- The spoiler guard checks speech only.
- Beat selection uses word density, not the LLM.
- There is no git remote, so no pull requests yet.
- The clip engine was written from scratch. That is now the decision: do not
  wait for `legacy/clipdesk/`. Record it in `docs/decisions.md`.

## Gate 0: check what the human has supplied

At the start of each session, check for each item below and list what is missing
under "Needs human" in `PROGRESS.md`. Do not fake any of them.

| Item | Unblocks |
| --- | --- |
| `fixtures/stream_10min.mp4`, real gameplay with commentary | Real M1 acceptance, every quality judgement |
| LLM API key in `.env` | M2 live run, LLM beat selection |
| Git remote on the organisation's own Git host | Pull requests and review |
| Google OAuth client and a test YouTube channel | M5, M6 |
| YouTube Data API key | M8 |
| Payment provider test-mode keys | M10 |

If the real fixture is missing, you may continue building, but you may not mark
M1, M3 or M4 as accepted, and you must say so in every report.

## Phase A: finish the proof of concept

1. **Close M1.** Run the real fixture when it exists. Add interface detection to
   the spoiler guard: start with letterbox and black-bar detection as a cutscene
   signal, and make it flag for review instead of dropping until it has been
   checked on real footage. Switch beat selection to the LLM once a key exists,
   keeping word density as the fallback.
2. **M2 to M8** exactly as written in `docs/BUILD_PROMPT.md`, in order.

## Phase B: product

Start Phase B only when M2 to M8 pass. Same rule as before: one milestone at a
time, each with a test under `tests/acceptance/`, run by `make accept`.

**M9. Onboarding.** A setup wizard: connect channel, show the personal stream
address, verify a test stream arrives, run one practice mission.
*Done when:* a Playwright test takes a new account from sign-in to a first
practice Short using an FFmpeg-pushed test stream.

**M10. Plans and billing.** Free and paid plans with limits enforced in the API,
not the UI. Payment provider behind an interface in `api/billing/`, test mode only.
*Done when:* a free account is refused its next clip at the limit, a test-mode
upgrade lifts it, and a webhook replay does not double-apply.
You never run a real transaction and never enter real payment details.

**M11. Design pass.** One design system (colour, type, spacing tokens), every
page responsive, the phone remote usable one-handed, keyboard and screen-reader
checks on the main flows.
*Done when:* automated accessibility checks pass on the five main pages and
screenshots at phone and desktop widths are saved for human review.

**M12. Hardening.** Database migrations, automated backups with a tested
restore, rate limits, structured logs, error reporting, dependency and secret
scanning in CI, and authorisation tests for every endpoint.
*Done when:* a restore test rebuilds the database from backup, and a test suite
proves user A cannot read or change any of user B's resources.

**M13. Scale readiness.** Make each tier scale sideways: stateless API behind a
load balancer, a worker pool sized by queue depth, relay instances assigned per
stream key, storage and database as the only shared state.
Then measure. Load-test the API at 10, 100 and 1,000 simulated creators, and
the relay at as many concurrent streams as the test machine allows.
*Done when:* `docs/capacity.md` states measured limits for one server, the first
bottleneck found, and the cost drivers per stream hour. Report measurements,
not estimates. Do not add infrastructure that no measurement justified.

**M14. More platforms.** A publisher interface with YouTube as the first
implementation. Add TikTok and Instagram as implementations that stop at
"needs human" wherever platform approval is required.
*Done when:* the interface has contract tests and each stub states exactly which
approval it is waiting for.

**M15. Community and safety.** Creator-submitted missions with an editor queue,
reporting, and blocking. Account deletion and data export that actually remove
or return a user's data.
*Done when:* a deleted test account leaves no rows and no stored files behind.

**M16. Launch documents.** Draft terms, privacy policy and a creator guide
covering game publisher video rules. Mark each one as a draft for human and
legal review. Do not present them as final.

## Data rules

- Store the minimum about a person: provider subject id, display name, channel id.
  Do not store email addresses, payment details or anything else unless a
  milestone requires it and you record why in `docs/decisions.md`.
- Tests use synthetic accounts only. Never copy real user data into fixtures,
  logs or reports.

## Report format

Unchanged from `docs/BUILD_PROMPT.md`. Add one line per session: which Gate 0
items are still missing, and which accepted milestones are accepted on stand-in
data only.
