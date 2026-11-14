"""LaunchAgent safety contract: one low-priority owner machine, no uploads."""
import pathlib
import plistlib

import pytest

from scripts.install_mac_supervisor import configuration, install


def fixture_root(tmp_path):
    (tmp_path/'.venv'/'bin').mkdir(parents=True)
    (tmp_path/'.venv'/'bin'/'python').write_bytes(b'fake executable')
    (tmp_path/'scripts').mkdir()
    (tmp_path/'scripts'/'network_supervisor.py').write_text('')
    return tmp_path


def test_launchd_supervisor_is_bounded_and_private(tmp_path):
    conf=configuration(root=fixture_root(tmp_path))
    assert conf['StartInterval']>=600
    assert conf['RunAtLoad'] is True
    assert conf['KeepAlive'] is False
    assert conf['Nice']>=10
    assert conf['LowPriorityIO'] is True
    command=' '.join(conf['ProgramArguments'])
    assert 'network_supervisor.py cycle' in command
    assert '--require-blender' in command and '--render-limit 1' in command
    assert '--plan' in command and '--render' in command
    assert 'publish' not in command and 'upload' not in command
    assert 'API_KEY' not in str(conf) and 'TOKEN' not in str(conf)
    assert conf['EnvironmentVariables']['CONTINUUM_SPEC_DIR'].endswith('/specs')


def test_install_does_not_overwrite_existing_different_configuration(tmp_path):
    root=fixture_root(tmp_path)
    plist=tmp_path/'user'/'service.plist'
    assert install(root=root,plist=plist)==plist
    assert plistlib.loads(plist.read_bytes())['Nice']==10
    assert install(root=root,plist=plist)==plist
    plist.write_text('Do not overwrite')
    with pytest.raises(FileExistsError):
        install(root=root,plist=plist)


def test_interval_abuse_fails_closed(tmp_path):
    with pytest.raises(ValueError):
        configuration(root=fixture_root(tmp_path),interval=15)
