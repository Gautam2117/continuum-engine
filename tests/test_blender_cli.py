"""Mac Blender app must execute B3D without an external bpy Python wheel."""
from types import SimpleNamespace
from pathlib import Path
import pytest

from engine import b3d


def test_native_blender_binary_selected_when_bpy_wheel_missing(monkeypatch):
    b3d.blender_runner.cache_clear()
    monkeypatch.delenv('B3D_OFF',raising=False)
    monkeypatch.delenv('B3D_PYTHON',raising=False)
    monkeypatch.setenv('B3D_BIN','/mock/bin/blender')
    monkeypatch.setattr(b3d.shutil,'which',lambda name: '/mock/bin/blender' if name=='/mock/bin/blender' else None)
    calls=[]
    def run(argv,**kwargs):
        calls.append(argv)
        return SimpleNamespace(returncode=0,stdout='Blender 5.2.1 LTS\nbuild date 2026-08-25\n',stderr='')
    monkeypatch.setattr(b3d.subprocess,'run',run)
    result=b3d.blender_runner()
    assert result is not None
    cmd,backend=result
    assert cmd[:5]==('/mock/bin/blender','-b','--python-exit-code','1','--python')
    assert cmd[-1]=='--'
    assert backend=='native:Blender 5.2.1 LTS'
    assert calls==[['/mock/bin/blender','--version']]
    b3d.blender_runner.cache_clear()


def test_blender_off_disables_native_backend(monkeypatch):
    b3d.blender_runner.cache_clear()
    monkeypatch.setenv('B3D_OFF','1')
    assert b3d.blender_runner() is None
    assert not b3d.available()
    b3d.blender_runner.cache_clear()


def test_native_version_reflects_in_cache_identity(monkeypatch,tmp_path):
    b3d.blender_runner.cache_clear()
    monkeypatch.delenv('B3D_OFF',raising=False)
    monkeypatch.delenv('B3D_PYTHON',raising=False)
    monkeypatch.setattr(b3d,'blender_runner',lambda: (('/mock/blender','-b','--python',str(b3d.MAIN),'--'),'native:Blender test-v5'))
    monkeypatch.setenv('B3D_CACHE',str(tmp_path))
    from PIL import Image
    observed=[]
    def run(argv,**kwargs):
        job=Path(argv[-1]); observed.append(argv)
        data=__import__('json').loads(job.read_text())
        out=Path(data['out'])
        Image.new('RGB',(32,32)).save(out/'f_0001.png')
        (out/'done.json').write_text('{}')
        return SimpleNamespace(returncode=0,stdout='b3d: dummy test\n',stderr='')
    monkeypatch.setattr(b3d.subprocess,'run',run)
    seq=b3d.render_clip('voxel',{},1,(32,32),{'bg':'#111111','ink':'#ffffff','panel':'#222222','accent':'#ff0000'})
    assert seq and len(seq)==1
    assert observed[0][-2]=='--' and observed[0][-1].endswith('job.json')
    assert __import__('json').loads((seq[0].parent/'job.json').read_text())['runtime']=='native:Blender test-v5'


@pytest.mark.skipif(__import__('os').environ.get('B3D_TEST') != '1',
                    reason='explicit real Blender binary smoke test on a machine with bpy')
def test_real_voxel_actor_visible_through_entire_scene(tmp_path, monkeypatch):
    """A moving frame is insufficient when the protagonist is behind trees."""
    import numpy as np
    from PIL import ImageChops
    monkeypatch.setenv('B3D_CACHE', str(tmp_path))
    b3d.blender_runner.cache_clear()
    assert b3d.available(), 'B3D_TEST=1 requires an actual Blender runtime'
    pal={'bg':'#081321','panel':'#142845','ink':'#f2f8ff','accent':'#ffca4b'}
    seq=b3d.render_clip('voxel', {'seed':19,'hero':'#ec743c','level':'Original voxel story'},
                        9,(450,800),pal)
    assert seq and len(seq)==9
    anchors=b3d.anchors(seq)['points']['hero']
    assert len(anchors)==9
    assert all(.02<x<.98 and .10<y<.90 and depth==1 for x,y,depth in anchors)
    frames=[b3d.load(frame,(450,800)) for frame in seq]
    assert ImageChops.difference(frames[0],frames[-1]).getbbox() is not None
    for frame in frames:
        pixels=np.asarray(frame).astype(int)
        # Orange shirt is the protagonist's identifying garment. Its absence
        # is an occlusion even when the root is inside the camera frustum.
        visible=(pixels[:,:,0]>pixels[:,:,1]*1.4)&(pixels[:,:,0]>pixels[:,:,2]*1.3)&(pixels[:,:,0]>90)
        assert int(np.count_nonzero(visible))>90
