"""Attach a rendered video, thumbnail and pack.json to the release for its date (created if needed)."""
import json
import pathlib
import shutil
import subprocess
import sys
import time

from release_gate import approval_for

spec = pathlib.Path(sys.argv[1])
out_root = pathlib.Path(sys.argv[2])
sid = json.loads(spec.read_text())["id"]
tag = spec.parent.name  # specs/<date>/<file>.json
src = out_root / sid
# Only an exact owner-approved technical review can ever become a release.
approval = approval_for(spec)
pack = json.loads((src / "pack.json").read_text())
receipt = pack.get("editorialApproval") or {}
if (receipt.get("status") != "approved"
        or receipt.get("specSha256") != approval["specSha256"]
        or receipt.get("reviewArtifact") != approval["reviewArtifact"]):
    raise SystemExit("RELEASE REJECTED: pack lacks matching owner approval")

staged = []
for name, dst in (("video.mp4", f"{sid}-video.mp4"), ("thumb.jpg", f"{sid}-thumb.jpg"), ("pack.json", f"{sid}-pack.json")):
    shutil.copy(src / name, src / dst)
    staged.append(str(src / dst))


def gh(*args, check=True):
    return subprocess.run(["gh", *args], capture_output=True, text=True, check=check)


# Several matrix jobs may race to create the same release; whoever loses just uses it.
for attempt in range(5):
    if gh("release", "view", tag, check=False).returncode == 0:
        break
    r = gh("release", "create", tag, "--title", f"Renders {tag}", "--notes", "Rendered by Continuum Engine. Studio pulls these into Upload packs.", check=False)
    if r.returncode == 0:
        break
    time.sleep(2 + attempt * 2)

# pack.json goes last: the Studio only picks up a video once its pack exists.
gh("release", "upload", tag, *staged[:2], "--clobber")
gh("release", "upload", tag, staged[2], "--clobber")
print(f"attached {sid} to release {tag}")
