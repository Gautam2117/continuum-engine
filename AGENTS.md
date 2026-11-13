# Continuum Engine: instructions for coding agents (Antigravity, Claude Code, others)

This is a public repo. Never commit API keys, tokens, passwords or channel credentials. Secrets live only in GitHub Actions secrets.

## What this repo does
It turns JSON video specs into finished YouTube videos with no paid services. `specs/` holds one spec per video, `engine/` renders, `autopilot/` writes and schedules specs unattended (GitHub Actions workflow `Autopilot`, four times a day), and Continuum Studio (separate repo) uploads. A channel playbook lives in `autopilot/playbooks.py`; the craft and honesty rules live in `autopilot/prompts.py`. Read both before editing any script.

## Rules for any script you write or edit
- Hook: first spoken line is 14 words or fewer, a claim or a question, and the second line adds a real number or name.
- Every scene is one or two sentences and changes what is on screen. At least three visual types per video, never the same type more than three times in a row.
- Facts come only from the grounding text in the spec's description or from settled textbook knowledge. If unsure of a number, say "roughly" or drop it. Never invent quotes, studies, statistics, test results or people.
- No medical, legal, financial or political advice. The voice is synthetic: never claim to be a human expert or to have tested something by hand.
- Do not copy another channel's wording. Each channel keeps its own voice from its playbook.
- Run `python scripts/validate.py --strict <spec>` after every change. A spec that fails must be fixed or deleted, never published.

## Never do
- Do not change upload or publishing behaviour, and do not try to make videos public. Uploads wait for Google's API audit.
- Do not change a channel's videos per day on your own. SG set the rule on 14 Nov 2026: Counterfactual Atlas makes 3 a day; every other channel the engine runs makes 1 a day (a Short most days, a long video on two days a week; see `cadence_for` in `autopilot/playbooks.py`). Felix and GOTZ are SG's own and are not automated. Later volume changes come from SG or the learning loop in `autopilot/state/`.
- Do not add `.agents/credentials/` or any file holding a key.

## Checks
`python -m pytest -q tests` must pass before a commit. Commit specs and code separately.
