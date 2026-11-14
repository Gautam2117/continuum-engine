# Counterfactual Atlas: indefinite daily cadence, starting November 2026

Owner's target: **2 original Shorts + 1 original researched long form video, every UTC calendar day, for the remainder of 2026 and throughout 2027 and beyond**. There is no job expiry and no finite end-date list. Production uses a continuously rolling **seven-day ahead** pipeline, not a one-time batch of three days. The other 47 channels retain their unique configurations and are not enabled to publish by the Atlas switch.

## Tested upload windows

The daily schedule allocates one production slot to each geographically distinct UTC window: Asia-Pacific (00:30/03:30), Europe-Africa (12:00/14:00) and Americas (18:00/20:30). The long video rotates across all three windows by date; Shorts occupy the others. Each slot has stable, small day-to-day minute variation. A restart preserves already drafted schedules and avoids creating a second upload within three hours. If a slot is too late to schedule safely, it is marked missing, not published immediately.

The cold start explores within every window, not an unsupported "best time" guess. Once actual Atlas public videos have matured, the existing per-format slot statistics use normalized views, average viewing percentage and subscribers per view to prefer stronger observed windows while retaining exploration. These comparisons are observational, and need adequate samples before assuming causation. YouTube Studio's *When your viewers are on YouTube* report offers independent audience-time context; no platform promises reach from a particular posting hour.

## Production and quality controls

The Mac launchd supervisor runs every 15 minutes when awake, creates researched scripts for a rolling seven-day future buffer, renders privately and records checksum receipts. It prioritizes only Atlas while keeping the 50/day network reporting target intact. Production rejects unsupported science, factual errors, unattributed visuals, very thin scripts, incorrect audio, unverifiable renders and duplicate titles. A self-review from the same local LLM is not independent editorial approval; it cannot authorize automatic release. Owner's standing instruction to schedule three Atlas uploads does **not** mean an unreviewed MP4 passed the exact-media editorial requirements.

The separate Studio Atlas-only publisher is enabled. Only a verified Google OAuth channel identity, actual owner-approved source/MP4/thumbnail hashes, canonical approved GitHub release URL and future private-scheduled `publishAt` may become a YouTube upload. The other 47 channels remain manual. Every public upload must be checked against the YouTube videos API after its scheduled publish time. An uploaded private scheduled video does not count as public production. If a deadline is missed, record it explicitly rather than make a rushed low-quality video.

## Continuity and risks

Run `python -m scripts.atlas_continuity --days 8` to inspect live future coverage and the verified worker counts. The private Mac is **not independent 24/7 compute**. If the Mac is switched off, planning and rendering cannot continue there. A separate authorized always-on machine with 0 paid spending must be provisioned for genuine Mac-off production; do not abuse GitHub-hosted Actions as a video-rendering farm. The second hard blocker is acceptance by an independently credible editor. The currently installed `qwen3.5:4b` generates drafts but often fails science/novelty review, and its own evaluation is deliberately ineligible. Provisioning a machine or selecting a model does not guarantee accuracy, retention, distribution or monetization.
