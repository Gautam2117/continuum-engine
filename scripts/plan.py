"""Which specs to render: a glob from the manual trigger, or the spec files changed by the push."""
import glob
import json
import subprocess
import sys

pattern = sys.argv[1] if len(sys.argv) > 1 else ""
before = sys.argv[2] if len(sys.argv) > 2 else ""

if pattern.strip():
    specs = sorted({f for part in pattern.split() for f in glob.glob(part)})
else:
    if before and set(before) != {"0"}:
        out = subprocess.run(["git", "diff", "--name-only", "--diff-filter=AM", before, "HEAD", "--", "specs"], capture_output=True, text=True)
    else:
        out = subprocess.run(["git", "show", "--name-only", "--diff-filter=AM", "--pretty=format:", "HEAD", "--", "specs"], capture_output=True, text=True)
    specs = sorted({line for line in out.stdout.splitlines() if line.endswith(".json")})
print(f"specs={json.dumps(specs)}")
