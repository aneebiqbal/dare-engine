# 15 — Open questions

Only the owner can answer these. They are grouped by topic; none are answered
here.

## Acceptance and the real fixture

1. Will `fixtures/stream_10min.mp4` (real gameplay with commentary) be supplied?
2. Is M1/M3/M4 acceptance on the real fixture required before launch, or is the
   stand-in enough for the next design?
3. Who watches a rendered Short and decides it is good enough?

## Managed database

4. Neon or Aiven? Who creates the project and holds the credentials?
5. Are both the pooled and direct connection strings available?
6. What is the expected creator count and stream volume, to size the instance?

## AI provider and cost

7. OpenCode Zen or xAI Grok (or another OpenAI-compatible provider)?
8. Which exact model id, and what is the monthly token/latency budget?
9. Is the AI usage table expected to feed billing or only diagnostics?
10. Should the worker beat-selection call move to the same client, or stay on
    word density?

## Licence and legal

11. The installed `piper-tts` is GPL-3.0-or-later. Is that acceptable for this
    product, or should the TTS engine be replaced?
12. The voice repository declares MIT, but individual voice cards vary. Which
    voice is approved for commercial use?
13. Has FFmpeg's GPL/LGPL build been reviewed? Is the OpenH264 fallback needed?
14. The title policy flags "GTA 6", "Grand Theft Auto" and "Rockstar". Is that
    the right trade-off for discoverability?

## Product scope

15. Is export-only acceptable for launch, or must YouTube posting ship?
16. Are Google sign-in, billing, the question miner and creator-submitted
    missions in the next version or out?
17. Is invite-only sign-up with admin-issued reset links (no email) acceptable,
    or is an email service required?
18. Should creators be able to edit any mission (`PATCH /missions/{id}` is
    currently open to all signed-in users)?

## Data, retention, operations

19. How long should recordings, clips and relay segments be kept? Who deletes
    them?
20. Are backups and a tested restore required, and what is the RPO/RTO?
21. Is TLS termination (Caddy or a load balancer) in scope for the next version?
22. What monitoring, alerting and error reporting are expected?
23. Should the session token be hashed at rest, and should `SESSION_SECRET` be
    used to sign it?

## Measurement

24. What are the real web performance budgets, and who measures them?
25. What is the target render time from Done to a finished Short on real
    gameplay?
26. What is the maximum acceptable upload size, and what happens above it?
