"""Restore review specs without replacing specs already tracked for release."""
import datetime as dt
import hashlib
import json
import re
from pathlib import Path


def restore(source: Path, destination: Path, today: dt.date) -> int:
    restored = 0
    for path in sorted(source.glob("*/*.json")):
        try:
            day = dt.date.fromisoformat(path.parent.name)
            spec = json.loads(path.read_text())
        except (ValueError, OSError):
            continue
        if not today <= day <= today + dt.timedelta(days=30):
            continue
        if not isinstance(spec, dict) or spec.get("id") != f"{day}-{path.stem}":
            continue
        target = destination / day.isoformat() / path.name
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(path.read_bytes())
            restored += 1
    return restored


def review_artifact(path: Path) -> str:
    spec = json.loads(path.read_bytes())
    identifier = spec["id"]
    if identifier != f"{path.parent.name}-{path.stem}" or not re.fullmatch(r"[a-z0-9-]+", identifier):
        raise ValueError(f"Invalid review spec identity: {path}")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return f"review-{identifier}-{digest}"


def pending_specs(paths: list[Path], available: set[str]) -> list[str]:
    return [path.as_posix() for path in sorted(paths) if review_artifact(path) not in available]


if __name__ == "__main__":
    today = dt.datetime.now(dt.timezone.utc).date()
    print(f"Restored {restore(Path('previous-review/inventory'), Path('specs'), today)} review specs.")
