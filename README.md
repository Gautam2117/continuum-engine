# Continuum Engine

Zero-cost video renderer for Continuum Arc channels. Specs in `specs/<date>/*.json` are rendered on GitHub Actions (Kokoro TTS + Pillow + ffmpeg). Each render is published as a release containing the video, thumbnail and upload pack, which Continuum Studio pulls into its Upload packs page.

No secrets live in this repository.


## Autopilot (runs with no laptop, no Claude, no human)

`.github/workflows/autopilot.yml` runs four times a day on GitHub's servers:

1. **learn** pulls real per-video analytics from Continuum Studio (`/api/autopilot/feedback`).
2. **plan** fills each channel's quota for today and the next two days, so a two-day buffer always exists.
   Topic, then Wikipedia grounding, then draft, then hard quality gates, then an editor pass. A spec already in
   `specs/<date>/` (for example written by Claude) always wins; the Autopilot only fills gaps.
3. **commit and render**: new specs are committed and rendered; specs that never rendered are found and retried.
4. Continuum Studio pulls finished videos from the releases and schedules each at its `publishAt`.

Publish times start from audience-geography priors and are learned per channel (see `autopilot/slots.py`).

### One-time setup (repo Settings, Secrets and variables, Actions)

| Secret | What for |
|---|---|
| `GEMINI_API_KEY` | Free key from Google AI Studio. Writes the scripts. |
| `AUTOPILOT_SECRET` | Same value as the `AUTOPILOT_SECRET` setting in the Studio's Vercel project. Lets the Autopilot read analytics. |
| `GROQ_API_KEY` (optional) | Second free provider, used when Gemini's daily limit is reached. |
| `OPENROUTER_API_KEY` (optional) | Third. |

Without `GEMINI_API_KEY` (or another key) the Autopilot generates nothing; videos already specified still render and publish.
Check `autopilot/state/heartbeat.json` to see when it last ran and what it did.
