# Production compute: zero-spend and policy gates

Status checked **14 November 2026**. No dedicated 24/7 render worker is connected.
`AUTOPILOT_NETWORK_REVIEW=0` is intentionally set on GitHub.

## Do not use GitHub Actions as a bulk video factory

GitHub's Additional Product Terms restrict GitHub-hosted Actions to workloads
connected to development, testing, deployment or publication of the software
project, and prohibit a disproportionate load or turning Actions into a
serverless application. A perpetual high-CPU 48-channel commercial video
rendering service has substantial compliance risk. Public repository compute
being billed at $0 **does not** authorize using it for arbitrary workloads.

Official source:
https://docs.github.com/en/site-policy/github-terms/github-terms-for-additional-products-and-features

The remaining Actions are bounded to one episode per manually triggered QA
workflow and a small daily health audit. Their successful tests do not prove
production publishing. All bulk scheduled runs were removed.

## Compliant worker selection, ranked

**1. Owned always-on computer:** dedicated existing machine (such as an older
computer with a reliable power supply, network, stable Linux and UPS if
needed). It can run our renderer with no cloud compute invoice, though
physical electricity and device wear are real costs. It is not 'independent
of a computer' and must be hardened before exposure to the network.

**2. Oracle Cloud Always Free instance, if capacity and an account are already
available:** as of Nov 2026 the Always Free A1 allowance is **2 Arm OCPUs and
12 GB total memory** (not the older 4 OCPU / 24 GB figures). Region capacity,
identity verification, account restrictions, VM retention and Blender/Kokoro
ARM compatibility must be established first. Do not provision a paid shape or
enable a paid account. This capacity may be insufficient for 50 daily videos;
measure actual scene render time and RAM on the intended host.

Source: https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm

**3. Kaggle notebooks:** official daily/weekly notebook scheduling may be
appropriate for discrete experiments, but GPU access is quota-limited and not
a verified nonstop 48-channel commercial factory. Do not misuse notebook
accelerators or evade quotas.

Source: https://www.kaggle.com/docs/notebooks

**Avoid Render Free for the primary video worker:** it is explicitly not meant
for production, sleeps after 15 minutes idle, lacks persistent disk, has
outbound bandwidth limits and cannot run free one-off jobs. A cheap paid cron
service is not permitted by the zero-paid-service budget.

Source: https://render.com/docs/free

## Prepared portable worker

The repository includes [`scripts/worker.py`](../scripts/worker.py), a standalone
SQLite-backed private render-review queue suitable for deployment on a future
owned machine or compliant dedicated VM. See [`SELF_HOSTED_WORKER.md`](SELF_HOSTED_WORKER.md)
and the systemd service/timer templates. This is a verified **software
capability**, not a provisioned 24/7 worker. No unattended production or
cloud billing resources have been enabled.

## Deployment gates before enabling unattended publishing

1. A selected execution host must be owned or provisioned under its free-use
   terms with no unexpected billing access and a durable local work queue.
2. Benchmark a real 3D Atlas Short, one text-heavy Long and one Hindi video,
   including peak RAM, CPU-hours, TTS speed, completion rate and all relevant
   per-host limits. Compute projected daily capacity using measurements.
3. Create separate channel-specific visual systems and reject generic filler,
   missing assets, unlicensed sources and repetitive/inaccurate scripts.
4. Provide authenticated owner review of the exact file, with source,
   `videoSha256`, `thumbnailSha256`, and GitHub run/artifact lineage.
5. Check and cancel all legacy Studio queued destinations before enabling
   YouTube automation. Verify one private upload and metadata outcome per
   connected YouTube account; an upload success response is not public reach.
6. Learn from real retention, view count, returning viewers and subscribers,
   respecting YouTube's inauthentic-content rules. 50 videos per day and
   monetization by 31 January 2027 are targets, not verified outcomes.

**Current production classification:** engineering QA operational; unattended
cloud video render/publishing **not configured**. Never mark this as complete.

## Native Blender on the existing Mac (verified 14 Nov 2026)

The original B3D engine only searched for a Python wheel containing `bpy`, so
`/opt/homebrew/bin/blender` was ignored even though Blender 5.2.1 was installed.
Engine now invokes the installed Blender CLI directly in background mode,
checks for actual rendered frames and binds cache identity to the Blender
version. An original voxel actor, moving camera and foreground walking path
rendered nine frames locally, with per-frame color/anchor checks that the
character remained visible. This is valid **local 3D execution**, not an
always-on independent host. The Mac being shut down still interrupts work.
