# Quality pass on upcoming specs

Use when the laptop is on and you want a second, stronger review of what Autopilot wrote.

1. Read `AGENTS.md`, `autopilot/prompts.py` and the channel's entry in `autopilot/playbooks.py`.
2. List specs for the next three days: `ls specs/*/` and pick files whose date is today or later. Check `autopilot/state/ledger.json` and `autopilot/state/feedback.json` to see which topics and slots are winning.
3. For each spec, read the hook, the numbers, and the closing loop. Look for: a hook over 14 words, vague adjectives instead of numbers, claims not backed by the grounding, repeated scene types, a title close to a recent one.
4. Rewrite weak scenes in place, keeping the JSON schema. Do not change `publishAt`.
5. Run `python scripts/validate.py --strict` on every file you touched, then `python -m pytest -q tests`.
6. Commit with a message listing the specs improved, and push. Autopilot renders them on its next run.
