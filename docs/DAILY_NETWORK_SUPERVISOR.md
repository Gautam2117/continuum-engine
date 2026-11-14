# Continuum Network Supervisor: zero-paid-service review execution

Implemented for **48 individual channels**. The existing playbook cadence requires **50 original videos per UTC day**: Atlas 3, and each other automated channel 1. Content styles remain independent; Felix and GOTZ are not in the registry. Long videos for most channels are staggered on two weekdays each week.

## Real status and limits

`python scripts/network_supervisor.py status --days 3` checks exact per-channel short/long targets, validates actual specs, identifies invalid scripts separately, and reads genuine SQLite queue receipts. An empty spec directory is reported as **150 missing over three days**, never as successful production. `cycle` writes a private atomic report under `var/supervisor/latest.json`, contains a single-owner lock, and never executes a YouTube upload.

The Supervisor separates three states: specification coverage, technically verified private renders, and public publishing. A valid script is NOT a verified render; a verified render is NOT approved/published; a published upload is NOT audience growth. The existing Studio approval policy continues to require source and media hashes. Current macros set `fullyAutonomous=false`, `offMacHostProvisioned=false`, and `publishing=PRIVATE_REVIEW_NOT_APPROVED` until independent real-world evidence exists.

## Mac installation (an interim host only)

Install the actual pinned renderer dependencies into the project's private `.venv` and verify native Blender/FFmpeg:

```bash
uv venv --python 3.11 .venv
uv pip install --python .venv/bin/python -r requirements.txt
.venv/bin/python scripts/worker.py preflight --require-blender
.venv/bin/python scripts/network_supervisor.py status --days 3
.venv/bin/python scripts/install_mac_supervisor.py install
launchctl bootstrap "gui/$(id -u)" ~/Library/LaunchAgents/tech.continuumarc.private-review-supervisor.plist
launchctl print "gui/$(id -u)/tech.continuumarc.private-review-supervisor"
```

This launch agent schedules a low-priority, nonoverlapping tick every 15 minutes when the Mac is available. It uses one bounded render-review job per tick, runs strict preflight, leaves any failures in private logs and a persistent SQLite queue, and writes atomic status. The `CONTINUUM_SPEC_DIR` and `CONTINUUM_STATE_DIR` environment variables are not global and don't change other projects.

Planning uses a verified local-only Ollama endpoint on `127.0.0.1:11434` with `qwen3.5:4b`. `CONTINUUM_LLM_LOCAL_ONLY=1` prevents contacting remote LLMs regardless of other ambient API keys. Ollama is physically installed, and a JSON-mode native API response with `think=false` was confirmed on the Mac. Its draft models are **not** independent editors: their own scores are stored as an editorial hold with `pass=false`, not as a finished-video authorization. The early review gate excludes unreviewed drafts from the render queue. The service invokes a bounded 10-call/10-minute planning cycle at most every 15 minutes, then runs a separately bounded private renderer. Generated drafts may fail factual or distinct-brand checks and must be reviewed before production. This is not evidence of 50 high-quality episodes/day.

Planning with nonlocal third-party models remains **disabled** unless the owner separately configures an approved no-charge provider and sets `CONTINUUM_ZERO_COST_LLM_CONFIRMED=1` in the host service environment after verifying its billing settings. No model key, quota, or promotional free-tier claim authorizes unlimited use.

Host-specific logs: `var/supervisor/{planner,render,launchd.stdout,launchd.stderr}.log`. Database: `var/worker.sqlite3`. Verified media: `var/reviews/`. The supervisor requires at least 20 GiB free before launching each new heavy render; the lower 2 GiB worker minimum is an additional hard stop; files cannot be discarded silently for disk recovery. Back up approved originals in authorized private storage and implement a retention policy **before** allowing continuous 50-video daily volume.

## Operator diagnostic

```bash
.venv/bin/python scripts/network_supervisor.py status --days 3
.venv/bin/python scripts/worker.py status
cat var/supervisor/latest.json
launchctl print "gui/$(id -u)/tech.continuumarc.private-review-supervisor"
```

## Hard blockers to genuinely unattended daily public publishing

1. No independently provisioned owned/Always-Free-compliant host exists in the current environment. A LaunchAgent does not work when the Mac is powered off. The legal and capacity-tested Linux systemd templates are under `docs/systemd`.
2. Only real quality-reviewed episode specs can render. A schedule must not invent filler or auto-approve unseen media. Daily 50 output depends on genuinely available model capacity, original artwork, sound, source verification and per-channel render benchmarks.
3. There is not yet an authorized publishing pass across all 48 account targets, and old Studio queues have not been fully audited. No script here disables the `YOUTUBE_MANUAL_UPLOADS` or `YOUTUBE_AUTO_PUBLISH_ENABLED` safety flags.
4. Every publication needs actual video-level evidence, timestamp and analytics lineage. No fabricated subscribers, views, or monetization metrics.

No paid service, public posting, mass Actions render or account-privilege changes are authorized by this deployment.
