# Self-hosted private rendering worker

**Status:** Software implemented and offline tested, **not provisioned or running on any dedicated machine**. Does not publish videos, spend money, generate script topics, or bypass editorial approval. It provides durable local video rendering to make the handoff to a compliant host possible.

## Architecture

`python scripts/worker.py` uses only Python standard-library persistence and the existing repository renderer. It scans *today through the next six UTC days* by default, never historic specs. A rolling cycle also skips older queued work outside its date window. Explicit one-shot runs can still process those jobs. Jobs are unique by `(spec id, exact SHA256)`. New revisions supersede queued older ones, while existing successful review receipts are preserved for provenance. One host's exclusive file lock stops two render processes running simultaneously. SQLite WAL persists job state, detects stale leases after a crash, retries transient errors with exponential backoff, and permanently blocks strict-quality failures. A render is never called `verified` until strict spec validation, MP4 decoding, ffprobe checks, visual evidence/rights checks, audible audio, and file hashing pass. A `manifest.json` records `mp4Sha256`, `thumbnailSha256`, duration and `publicationStatus=NOT_APPROVED_FOR_PUBLICATION`.

Failed staging directories and logs remain for diagnosis rather than being mislabeled as complete. Preflight requires at least 2 GiB free on the review filesystem. The worker has no YouTube credentials or public upload function. SQLite is designed for **one attached machine**, not a distributed multi-host queue.

## Manual evaluation on an authorized host

Run from a Linux or macOS checkout with `python >=3.11`, packages from `requirements.txt`, `ffmpeg`, `ffprobe`, fontconfig fonts and a compatible Blender runner if specs use 3D.

```bash
python scripts/worker.py preflight --require-blender
python scripts/worker.py scan --spec specs/2026-11-16/atlas-s1.json
python scripts/worker.py status
python scripts/worker.py once --limit 1 --timeout 7200
```

A real host with the complete future backlog can invoke:

```bash
python scripts/worker.py cycle --days 7 --limit 1
```

The worker does **not** produce the owner approval record required by `scripts/release_gate.py`. A future authenticated artifact transfer must preserve run identity and MP4/thumbnail hashes before any Studio publication integration. Do **not** publish private worker files to public GitHub assets as a shortcut.

## Suggested Ubuntu systemd installation on a machine you administer

These templates assume an intentionally provisioned `/opt/continuum-engine` checkout, a `continuum` system account, `/opt/continuum-engine/.venv` with tested dependencies, and `ffmpeg`/font dependencies installed. The required paths do not exist until the machine is provisioned. **Do not execute these steps on a random computer or an account without authorization.**

The two unit files in [`docs/systemd`](systemd) set a 10-minute timer. Running services cannot overlap and the SQLite lock is the final guard. They use a fixed non-root user, private state directory and a read-only project install. `KOKORO_DIR` and `B3D_CACHE` are writable caches under `/var/cache/continuum`. 3D Blender Python must be installed and benchmarked separately on the chosen hardware, especially on ARM machines.

Once the host prerequisites actually exist, its administrator installs and enables the timer:

```bash
sudo install -m 0644 docs/systemd/continuum-review-worker.service /etc/systemd/system/
sudo install -m 0644 docs/systemd/continuum-review-worker.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now continuum-review-worker.timer
systemctl list-timers continuum-review-worker.timer
sudo journalctl -u continuum-review-worker.service -n 100 --no-pager
```

The service is **NOT enabled by this repository change**. This systemd configuration is also **NOT** a remotely hosted or always-free provider account. A valid execution host, owner-controlled credentials and real-world throughput benchmark still remain outstanding.

## Operations and safeguards

Monitor `python scripts/worker.py status` and `/var/lib/continuum/reviews`. Blocked jobs need a source/code fix and deliberate re-enqueue of an updated spec. Do not edit DB rows to make failed media appear verified. Artifacts and 3D caches consume storage, so retain only the evidence you need and archive verified videos securely with owner consent. Workers must not run over internet-exposed shared storage without additional locking and authentication.

Avoid committing secrets, downloaded Kokoro weights, generated videos, SQLite state, OAuth tokens, face stills, or media requiring third-party rights clearance. The existing GitHub owner-approval workflow is *not* automatically compatible with local worker manifests because it requires a GitHub review run ID. This deliberate mismatch prevents an unreviewed local artifact from bypassing owner approval.

## Import a private worker package for editorial review

Transfer the worker's package directory through your authenticated SSH connection to
a private landing directory. Verify the host key and keep the files off public release
storage. From the editor's engine checkout, run:

```bash
python -m scripts.import_private_review /private/landing/episode \
  specs/2026-11-16/atlas-s1.json /private/editor-inbox
```

The importer checks a copied snapshot against the tracked spec, the manifest and
checksums, decodes the media, and moves the package into the private inbox atomically.
Reimports of the identical cut reuse the same path. The editor can review the exact video
and thumbnail there. Import preserves the worker's unapproved state. The existing
GitHub release workflow still requires its own approval and artifact provenance.
