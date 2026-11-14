# Independent private media review archive

The source Mac can fill rapidly when video targets reach 50/day. `scripts/archive_verified_reviews.py` implements **verified copy only**, never media deletion, public GitHub uploads, YouTube publishing, or a paid service.

## Security and integrity

This tool reads only `state='verified'` rows from the existing review worker SQLite database and checks the source manifests: exact spec ID and SHA-256, exact video, thumbnail, spec, pack and probe hashes, and the expected `NOT_APPROVED_FOR_PUBLICATION` status. It rejects symlinked media, malformed receipts, path traversal, mismatched worker-database video hashes, and corrupt bytes. Relative review paths are resolved from the original Engine repository, not the operator's shell directory. Copies land in a temporary directory on the backup filesystem, are flushed, independently rehashed, and then renamed atomically. It does not overwrite existing archives; a previously archived review must still pass its full checksum audit before it can count as an existing backup. Every operation leaves the Mac's source intact.

By default it refuses a destination on the same **mounted filesystem** as the source. This is a minimum check, not proof of a physically independent machine or protected offsite backup. Verify the backup drive is genuinely physically distinct and encrypted (FileVault, LUKS or comparable) before enabling. No external trusted mount was available on the Mac on 14 November 2026.

## When an owner-controlled encrypted external drive is available

Create a private writable directory on that real drive yourself (example `/Volumes/EncryptedArchive/ContinuumReviews`); verify its owner, encryption and physical identity first. Then run:

```bash
.venv/bin/python scripts/archive_verified_reviews.py \
  --db var/worker.sqlite3 --reviews var/reviews \
  --destination /Volumes/EncryptedArchive/ContinuumReviews \
  --confirm-trusted-mount
```

The supervisor will also invoke this copy after its render cycle when **both** `CONTINUUM_ARCHIVE_ROOT` and `CONTINUUM_ARCHIVE_MOUNT_ENCRYPTED=1` are provided in its approved service environment. If either is missing, archiving is skipped with an explicit status rather than treating the local review folder as a backup. Inspect `var/supervisor/archive.log` for successful copies and failure receipts. A missing mount, disk full or invalid checksum must never be swallowed.

No auto-deletion or pruning of private original video is enabled: one verified second copy is not a sufficient durable retention policy for a long-running media business. A separately controlled third copy or explicitly accepted retention policy is needed before source deletion. The Mac's render safety reserve remains 20 GiB regardless of archive status.

**Deployment state:** archive code verified locally; independent external encrypted mount still not provisioned. It cannot keep running when the Mac is powered off and is not a substitute for the independent production host.
