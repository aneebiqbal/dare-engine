# Clip scoring skill

Editable tuning surface for the moment picker. **No code change is needed** to
retune how moments are chosen: edit these files and re-run.

Files:

| File | What it controls |
| --- | --- |
| `rubric.md` | The dimensions, weights, scoring bands, worked examples and kill criteria. |
| `prompt_score.md` | The per-candidate scoring prompt (reads transcript + event timeline). |
| `prompt_rerank.md` | The head-to-head rerank prompt that orders the finalists. |

Rules the code enforces regardless of these files:

- Candidate windows are grown from whole sentences and are at least
  `pipeline.min_seconds` (default 14 s) long; scoring cannot shorten one.
- A candidate rejected by a kill criterion is never selected.
- Every selected clip records its label, hook line, reason and per-dimension
  scores in its metadata and in the run manifest.
- Scoring runs at the temperature in `prompt_score.md`; the strict schema is
  validated before anything is accepted.

See `docs/decisions.md` for where this design came from.
