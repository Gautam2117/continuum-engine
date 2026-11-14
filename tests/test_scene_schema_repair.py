"""Grounded local script repairs must preserve editorial gates and real spoken fields."""
from autopilot.daily import Planner


def make_planner(outputs):
    p=Planner(object(),max_calls=10)
    calls=[]
    def fake(system,user,**kw):
        calls.append(user)
        return outputs[len(calls)-1]
    p._call=fake
    return p,calls


def test_flat_visual_scenes_trigger_one_explicit_grounded_repair():
    before={"title":"QR code survives damage","thumb":"QR safety","description":"Codes can resist damage.","tags":["science"],
            "scenes":[{"type":"title","text":"Why QR codes survive"},{"type":"number","value":5,"label":"Data"}]}
    after={**before,"scenes":[{"say":"QR codes can sometimes survive local damage.","show":{"type":"title","text":"QR codes"}},
                               {"say":"Error correction helps recover encoded information.","show":{"type":"number","value":5,"label":"Data"}}]}
    planner,calls=make_planner([before,after]);g={"text":"QR codes use error correction.","sources":[]}
    result=planner.draft_short("Samjho System",{"topic":"QR code error correction"},g)
    assert result==after and len(calls)==2
    assert 'DO NOT put type' in calls[0]
    assert 'REWRITE THIS MALFORMED JSON' in calls[1]
    assert 'QR codes use error correction.' in calls[1]


def test_compliant_scene_schema_never_spends_an_extra_model_call():
    original={"title":"Test","scenes":[{"say":"A complete line in the scene.","show":{"type":"say","text":"A"}}]}
    planner,calls=make_planner([original]);g={"text":"Grounding","sources":[]}
    assert planner.draft_short("Samjho System",{"topic":"Reason"},g)==original
    assert len(calls)==1
