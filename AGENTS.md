# Continuum Engine: instructions for coding agents (Antigravity, Claude Code, others)

This is a public repo. Never commit API keys, tokens, passwords or channel credentials. Secrets live only in GitHub Actions secrets.

## What this repo does
It turns JSON video specs into finished YouTube videos with no paid services. `specs/` holds one spec per video, `engine/` renders, `autopilot/` drafts and plans specifications; the old bulk GitHub Actions schedule is paused for platform compliance. GitHub Actions is reserved for isolated software QA. A separate, compliant dedicated execution host is required for unattended production. Continuum Studio (separate repo) ingests only exact owner-approved releases. A channel playbook lives in `autopilot/playbooks.py`; the craft and honesty rules live in `autopilot/prompts.py`. Read both before editing any script.

## Rules for any script you write or edit
- Hook: first spoken line is 14 words or fewer, a claim or a question, and the second line adds a real number or name.
- Every scene is one or two sentences and changes what is on screen. At least three visual types per video, never the same type more than three times in a row.
- Facts come only from the grounding text in the spec's description or from settled textbook knowledge. If unsure of a number, say "roughly" or drop it. Never invent quotes, studies, statistics, test results or people.
- No medical, legal, financial or political advice. The voice is synthetic: never claim to be a human expert or to have tested something by hand.
- Do not copy another channel's wording. Each channel keeps its own voice from its playbook.
- Run `python scripts/validate.py --strict <spec>` after every change. A spec that fails must be fixed or deleted, never published.

## Never do
- Do not enable public YouTube uploads or remove editorial gate flags. An API policy change alone does not establish YouTube account readiness. Do not run bulk video production on GitHub Actions or change it back to a recurring video factory.
- Do not change a channel's videos per day on your own. SG set the rule on 14 Nov 2026: Counterfactual Atlas makes 3 a day; every other channel the engine runs makes 1 a day (a Short most days, a long video on two days a week; see `cadence_for` in `autopilot/playbooks.py`). Felix and GOTZ are SG's own and are not automated. Later volume changes come from SG or the learning loop in `autopilot/state/`.
- Do not add `.agents/credentials/` or any file holding a key.

## Checks
`python -m pytest -q tests` must pass before a commit. Commit specs and code separately.

## Original motion skill routing for creative development

Before authoring or replacing an animation scene, consult `docs/CHANNEL_SKILL_ROUTING.json` and the full identity in `autopilot/directors.py`. Read and apply only that channel's primary, supporting and QA skills from the local, pinned `~/.agents/skills/` collection. Validate with `python scripts/verify_skill_routes.py --installed` on an authorized workstation. In CI, run without `--installed` to verify mapping without local user files. Skills are agent guidance; they do not make the daily JSON planner a Remotion, Manim or Three.js renderer. Author new scene code, then review real video frames and rights before granting approval. Never fetch a paid service or copy a competitor's visual identity.
