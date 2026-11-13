# Continuum Engine

Zero-paid-spend video planning, rendering and technical review for Continuum Arc.
Source specs live in `specs/<date>/*.json`; review outputs are private-to-the-workflow
GitHub Actions artifacts, not automatic public YouTube uploads. No API keys or
channel credentials live in this public repository.

## Actual production stages

1. `Autopilot` runs every six hours when repository variable
   `AUTOPILOT_NETWORK_REVIEW=1`. It queries Studio feedback, attempts to fill
   per-channel slots and writes **ephemeral review inventory**. Missing or
   rejected scripts are reported, not counted as delivered videos. GitHub
   free-model provider quotas can prevent the 50 daily target being filled.
2. `Render (technical review only)` and `Render preview` produce MP4, thumbnail,
   pack, media probe, source spec and checksums. They validate script structure,
   editorial score receipts, media decoding and audible audio.
3. A person **watches and checks the exact video**, and separately commits an
   approval tied to the spec hash and technical review artifact. Instructions:
   [`approvals/README.md`](approvals/README.md).
4. Only the manually dispatched `Promote approved review` workflow may attach
   those exact, checked, owner-approved media bytes to a GitHub release.
   `scripts/publish.py` refuses unapproved packs even if called directly.
5. Continuum Studio accepts **only approved** release packs. YouTube uploads
   remain manually gated until both `YOUTUBE_MANUAL_UPLOADS=0` and
   `YOUTUBE_AUTO_PUBLISH_ENABLED=1`, after a full backlog audit and private test.

A successful scheduled workflow is not evidence of video creation, YouTube
publication, viewers, or income. `Continuum Network Health` runs daily and
tracks missing specs, technical artifacts and provider errors in one GitHub issue.

**Channel cadence configured:** Counterfactual Atlas 1 long + 2 Shorts per day;
47 other non-creator-led channels 1 episode per day each, with their own playbooks
and staggered long-form days. Felix and GOTZ stay creator-led. This is a planning
target, **not a verified publishing or monetization claim**. Quality, factual
support, artistic uniqueness, rights and YouTube's inauthentic-content policy
still determine which finished work is fit for release.

## Development checks

```bash
python -m pytest -q tests
python scripts/validate.py --strict specs/2026-11-14/atlas-s1.json
```
