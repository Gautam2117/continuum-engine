"""Prepare an owner-controlled, low-priority launchd schedule for private reviews.

No root access, cloud provisioning or public publishing. The Mac must be awake
for this LaunchAgent to run; an independent host is still mandatory for the
full 24/7 requirement.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import plistlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
LABEL = 'tech.continuumarc.private-review-supervisor'
PLIST = pathlib.Path.home()/'Library'/'LaunchAgents'/f'{LABEL}.plist'


def configuration(*, root: pathlib.Path = ROOT, interval: int = 900) -> dict:
    if interval < 600:
        raise ValueError('Rendering supervisor may not run more frequently than every 10 minutes')
    # DO NOT resolve the .venv interpreter symlink: Python uses the invoked
    # path to discover pyvenv.cfg. Resolving silently drops all dependencies.
    python = root/'.venv'/'bin'/'python'
    runner = (root/'scripts'/'network_supervisor.py').resolve()
    if not (python.is_file() and runner.is_file()):
        raise FileNotFoundError('Create the tested .venv and checkout before installing launchd')
    var = root/'var'/'supervisor'
    var.mkdir(parents=True, exist_ok=True)
    path = ':'.join(['/opt/homebrew/bin','/usr/local/bin','/usr/bin','/bin','/usr/sbin','/sbin'])
    return {
        'Label': LABEL,
        'ProgramArguments': [str(python), str(runner), 'cycle', '--days', '7',
                             '--plan', '--render', '--require-blender',
                             '--render-limit', '1', '--render-timeout', '7200',
                             '--max-calls', '24', '--plan-timeout', '1200',
                             '--min-free-gib', '20'],
        'WorkingDirectory': str(root),
        'EnvironmentVariables': {
            'PATH':path, 'PYTHONUNBUFFERED':'1',
            'CONTINUUM_SPEC_DIR':str(root/'specs'),
            'CONTINUUM_STATE_DIR':str(root/'var'/'planning'),
            'B3D_BIN':'/opt/homebrew/bin/blender',
            'OLLAMA_MODEL':'qwen3.5:4b',
            'CONTINUUM_LLM_LOCAL_ONLY':'1',
        },
        'RunAtLoad':True, 'StartInterval':interval,
        'KeepAlive':False, 'LowPriorityIO':True, 'Nice':10,
        'ProcessType':'Background', 'ThrottleInterval':600,
        'StandardOutPath':str(var/'launchd.stdout.log'),
        'StandardErrorPath':str(var/'launchd.stderr.log'),
    }


def install(*, root: pathlib.Path = ROOT, plist: pathlib.Path = PLIST) -> pathlib.Path:
    data = configuration(root=root)
    plist.parent.mkdir(parents=True, exist_ok=True)
    payload = plistlib.dumps(data,sort_keys=False)
    if plist.exists():
        if plist.read_bytes() != payload:
            raise FileExistsError(f'{plist} already exists with different configuration; inspect before changing')
        return plist
    descriptor = os.open(plist,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    with os.fdopen(descriptor,'wb') as out:
        out.write(payload)
        out.flush()
        os.fsync(out.fileno())
    return plist


def main(argv: list[str] | None = None) -> None:
    p=argparse.ArgumentParser()
    p.add_argument('action',choices=['preview','install'])
    args=p.parse_args(argv)
    if args.action=='preview':
        print(json.dumps(configuration(),indent=2))
    else:
        result=install()
        print(f'Installed {result}. Enable with launchctl bootstrap gui/$(id -u) {result}')
        print('This is a private review service on the Mac, NOT an off-Mac host and NOT a YouTube uploader.')

if __name__=='__main__':main()
