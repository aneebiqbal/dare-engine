# Head-to-head rerank prompt

Small local models score absolute quality in a narrow band. Relative judgement
is far easier: show the finalists and ask for an order.

```
You are ranking the finalist clips from one video against EACH OTHER.
Absolute scores were noisy; your job is the order only.

For each clip you get its transcript window and its label/hook line.

Rank them by which a viewer would watch to the end and share, considering:
hook strength first, then payoff delivery, then how well it stands alone.
Prefer variety: two near-identical moments should not both rank at the top.

Return JSON only:
{"order": [<start_seconds>, ...], "drop": [<start_seconds>, ...]}

Put every start you would still post in `order`, best first. Put any finalist
that proves weaker than the others (duplicate idea, missing payoff) in `drop`.
Use the same language as the clips for nothing — this is numbers only.
```

Temperature: **0.3**. Only the finalists (default up to 24) are compared.
