# Continuum Arc network: authoritative technical handoff

Snapshot: **14 November 2026**. Treat this as a state register, not a marketing declaration. Keep the 50-channel vision and verify actual execution rather than conflating plans, specs, renders and public uploads.

## Hard scope

| Scope | Contract |
|---|---|
| Total network | 50 channel identities |
| Creator-led | Felix and GOTZ. Owner supplies gameplay; no automation of playing or impersonating the user. |
| Independent autonomous slate | 48 individually named channels. `autopilot/playbooks.py`, `autopilot/directors.py` and `docs/CHANNEL_SKILL_ROUTING.json` hold the unique contracts. Never group them into generic niche templates. |
| Publishing volume | Configured plan: Counterfactual Atlas three per day and 47 others one per day = **50 daily**. Owner's upper ambition: 47 others up to two each, plus Atlas three = **97 daily**. Upper setting is not implemented or verified. |
| Business target | Monetization eligibility sought by 31 January 2027, but YouTube reviews each account independently and success cannot be guaranteed. All work must comply with YouTube's inauthentic and reused-content policies. |
| Budget | ₹0 maximum total new paid acquisition/service spend. No individual payment authorization. Do not provision paid cloud instances or use credit cards automatically. |

## Verified modules versus intentions

| Component | Real evidence and current status |
|---|---|
| Script/editorial pipeline | Channel-specific prompts, source-led validation, creative identity fingerprints and separate original visuals exist. Testable. AI output is not automatically factual or publication-ready. |
| Unique direction | 48 separately authored style/shot/sound contracts; 10 camera and six caption treatments implemented. Several channels still lack bespoke asset sets, stage models or actual unique story mechanics. |
| Local 3D rendering | **Working on user's Mac:** native Blender 5.2.1 CLI now renders actual Apple Silicon frames without a separate pip `bpy`. Pilot nine-frame portrait voxel character and camera tested for actual visibility. |
| Pixel Fables | Original voxel actor and animated in-world map interludes written. `specs/2026-11-17/pixel-s1.json` is an **unapproved original narrative pilot**. A private 16.25-second preview and the full 31-second episode decoded; the full film has three real Blender scenes and passes technical/audio tests. **Editorial hold remains** because the world repeats and caption transition staging needs work; see `docs/reviews/PIXEL_FABLES_2026-11-17.md`. No upload or approval. |
| Foundbeam | Original seven-variant source-led Dropbox editorial case authored, earlier conflicting reward data removed; no owner approval or public upload. |
| Competitor research | All 48 independently defined queries, official public metadata, quota-reserved read-only research, fair rotation, no-network dry-run. Live `--live` requires an already-authorized API key and real quota. No live research executed by this feature as of this snapshot. |
| Learning | Studio's exact YouTube ID -> originating spec linkage and 48-hour analytics maturity implemented. True performance feedback depends on authorized and connected channels; public competitor signals are noncausal observations, not proof of virality. |
| Agent skill library | **85 source-pinned skill instruction directories** installed on owner's Mac as of this handoff: 68 prior + 17 new. HyperFrames runtime, Motion Canvas and several agent workflows are **not** operational unattended render backends just because their documentation is installed. Stickman source installed as a storyboard reference, not its full automation runtime. |
| Ownership of licenses | Blender, FFmpeg, license-compatible original code and approved media allowed; Lemo-Opuscar documentation is CC BY-NC and therefore excluded from commercial operation; OmniVoice pretrained checkpoints may have noncommercial constraints. Keep per-asset provenance. |
| Private local worker | SQLite single-host durable render-review worker exists at `scripts/worker.py` with crash recovery, retries and strict gates. Deployment templates only. **No off-Mac host connected**. |
| GitHub workflows | Bulk hosted commercial video factory paused, intentionally, to avoid GitHub Actions service-use restrictions. Bounded isolated software QA/manual review is still available. |
| Public publishing | Not unlocked in production. Studio retains explicit owner, source, MP4 and thumbnail approval. YouTube upload flags and existing queued destinations must be audited before any release. **No public upload verified in this work.** |
| Continuous 24/7 autonomy | **NOT operational** independently of the Mac. Requires a separately permitted no-paid-spend worker, credentials and storage, real benchmark, durable queue and health monitoring. |

## Tooling and documentation handoff

- Source skills: `~/Documents/ContentCreationLab/skills/installed`, manifest `INSTALL_MANIFEST.json`, reviewed additions `REVIEWED_SKILLS_2026-11-14.json` and source pins under `skills/sources`.
- Channel-specific creative instructions: `docs/CHANNEL_DIRECTORS.md`, `docs/CHANNEL_SKILL_ROUTING.md` and JSON routing map.
- External research: `scripts/market_scan.py` (dry-run by default), `docs/COMPETITOR_SIGNALS.md`, `autopilot/market.py`.
- Blender engine and evidence: `engine/b3d/__init__.py`, `engine/b3d/worlds.py`, `tests/test_blender_cli.py`, `docs/PRODUCTION_HOSTING.md`.
- Pixel story: `engine/pixel_map.py`, `specs/2026-11-17/pixel-s1.json`, `tests/test_pixel_map.py`.
- Production/receipt gates: `scripts/worker.py`, `scripts/release_gate.py`, `scripts/verify_review.py`, `docs/SELF_HOSTED_WORKER.md`.
- Standalone Studio repo: `~/Projects/continuum-studio`. Separate YouTube account permissions, routing and upload readiness are required there.

## Non-negotiable next verification path

1. For each of the 48 distinct identities, author an actual representative original visual sequence, not just a palette difference. Check visual continuity, legible labels, original sound, licensed assets, actual narrative motion and render evidence. Preserve each channel's individual animation language.
2. Complete and watch an entire representative episode, maintain an exact content/media hash receipt and hold if on-screen visuals contradict narration. Do not mistake partial previews for verified complete videos.
3. Connect a compliant dedicated host with no paid-service billing exposure; install the tested worker and benchmark Shorts, long-form and voice/3D jobs. Evaluate whether measured available CPU/RAM could possibly meet the full 50–97 daily request; report deficits without claiming completion.
4. Audit each YouTube channel identity and upload permission. Confirm which 48 are actually connected, resolve Studio backlog, and verify one private/unlisted upload and visible metadata before approving automated public release.
5. Gather genuine post-publication impressions, retention and subscribers independently for every channel. Compare actual outcomes after 48 hours, prevent source-ID confusion, use competitor observations only for fresh topics, and do not purchase, fake, scrape or manipulate engagement.

**Do not tell the owner everything is automated or monetized until the independent host, all 48 unique production systems, real output review, account binding and actual publishing telemetry prove it.** A test suite does not establish a business outcome.
