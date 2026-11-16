# Sprint 3 prompt: the complete web app

Paste everything below the line into your coding agent at the start of every session.

---

## Scope of this sprint

Build every page of the Clipdesk Missions web app, end to end, to a standard a
paying creator would accept. Read `PROGRESS.md`, `docs/spec.md`,
`docs/BUILD_PROMPT.md` and `docs/SPRINT2_PROMPT.md` first. All their rules still
apply, including Gate 0 reporting. This sprint runs alongside the milestone
order: keep building M3 onward on stand-in data, and never mark a milestone
accepted that Gate 0 says cannot be.

## Rules for this sprint

1. **Contract first.** Every page talks to the API through a typed client
   generated from `contracts/openapi.yaml`. If a page needs an endpoint that is
   not in the contract, add it to the contract in its own pull request first.
2. **Real where possible, mocked where blocked.** If the backend for a page
   exists, use it. If it is blocked by Gate 0, serve the contract from a mock
   layer behind `NEXT_PUBLIC_API_MOCK=1`, and list that page under
   "Mocked pages" in `PROGRESS.md`. A mocked page is never reported as working.
3. **Every page has four states:** loading, empty, error and filled. Build and
   test all four.
4. **Phone first.** The remote and the Clips review are used on a phone, with
   one hand, mid-game. Design those at 390 px wide before desktop.
5. **Look at your own work.** Take headless Playwright screenshots of every page
   at 390 px and 1280 px, in light and dark, into `docs/screens/`. Open them,
   find the worst-looking page, fix it, and repeat. Headless screenshots need no
   desktop window.
6. **Stream keys are secrets.** Show them masked, reveal on tap, copy with one
   button, never log them, never put them in a URL.

## Design system (W0)

One set of tokens for colour, type, spacing, radius and motion, in one file.
Light and dark themes. A small component set built once and reused: button,
input, card, badge, tabs, dialog, toast, table, empty state, skeleton.
*Done when:* a `/styleguide` page shows every component in both themes and
passes automated accessibility checks.

## Pages

**W1. Public**
- Landing page: what it is, how a day works, a live Daily Mission preview.
- Sign-in.
- Mission page `/m/{slug}`: the question, the rules, every attempt as an embed.
- Leaderboard per mission, and a Daily Mission board.
- Creator profile: their attempts and ranks.
- Terms and privacy, marked as drafts.

**W2. Creator, before the stream**
- Onboarding wizard: connect channel, stream address and key, test stream check,
  practice mission.
- Today: Daily Mission, three personal picks, accept, swap, edit, reorder.
- Go Live: stream address, masked key, connection status, checklist.

**W3. Creator, during the stream**
- Phone remote `/remote`: current mission, big Start and Done, result entry,
  next mission, connection indicator, works after a dropped connection by
  queueing taps and sending them with their original timestamps.
- Clip review on the phone: preview, retitle, approve, discard.

**W4. Creator, after the stream**
- Clips: queue and library, viewer, title and description edit, approve,
  download, post status.
- Stream detail: timeline with every mark, each mission's window, its clip.
- Results: views and retention per clip and per mission type.
- Mission history.

**W5. Account**
- Settings: channel, plan and usage, caption and layout preferences, data
  export, delete account with confirmation.

**W6. Admin**
- Questions in, pool editor with approve, edit and reject.
- Templates, users, job queue and system health.

*Each of W1 to W6 is done when:* a Playwright test walks its main flow on phone
and desktop sizes, all four states of each page are covered, accessibility
checks pass, and screenshots are saved.

## Final check (W7)

One Playwright journey from sign-in through onboarding, accepting a mission,
Start and Done on the remote, reviewing a clip and seeing it on a leaderboard.
State in the report which steps ran against the real backend and which against
mocks.

## Report format

Unchanged, plus: the list of mocked pages, and the three worst screens you
found and what you did about them.
