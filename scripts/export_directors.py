"""Export each independent channel's active creative contract for operations."""
from __future__ import annotations
import argparse
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from autopilot.directors import DIRECTORS, VERSION, verify_directors
from autopilot.playbooks import PLAYBOOKS


def render() -> str:
    verify_directors(set(PLAYBOOKS))
    rows = [
        '# All 48 independent channel directors',
        '',
        f'Contract version: **{VERSION}**. Every row is an independent creative identity, not a shared channel category.',
        '',
        'Camera and caption modes are implemented in the current Pillow/Blender renderer. The visual world, shot grammar and sound notes are explicit editorial instructions and still need bespoke models, sound assets or new scene code where the requested scene is not available. A prompt alone does not implement an animation.',
        '',
        '| Channel | Primary visual system | Storyboard and signature action | Camera | Captions |',
        '| :--- | :--- | :--- | :--- | :--- |',
    ]
    for name, d in DIRECTORS.items():
        assert name in PLAYBOOKS
        safe = lambda value: value.replace('|', '/').replace('\n', ' ')  # noqa: E731
        rows.append(f'| {safe(name)} | {safe(d.visual_world)} | {safe(d.shot_sequence)} | {d.camera} | {d.captions} |')
    rows += [
        '', '## Operating guarantees and limits', '',
        '- `Planner._system()` incorporates only the named channel director; `exemplar()` cannot import another channel\'s episode.',
        '- The renderer uses actual channel camera and caption modes, not only a palette switch.',
        '- New Autopilot specs carry an exact director fingerprint. A mismatched director fails validation, preserving the evidence trail.',
        '- Rights clearance, model asset completion and on-screen accuracy still require actual rendered media verification.',
        '- These design contracts do not mean a complete original 3D model or Motion Canvas project exists for all 48 channels.',
        '- Felix and GOTZ are creator-led and intentionally outside the automated registry.',
        '',
    ]
    return '\n'.join(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    path = ROOT / 'docs' / 'CHANNEL_DIRECTORS.md'
    expected = render()
    if args.check:
        if not path.is_file() or path.read_text() != expected:
            raise SystemExit('CHANNEL_DIRECTORS.md is stale. Regenerate with python scripts/export_directors.py')
        print('48 director contracts are synchronized')
    else:
        path.write_text(expected)
        print(f'Exported {len(DIRECTORS)} distinct channel contracts to {path}')

if __name__ == '__main__':
    main()
