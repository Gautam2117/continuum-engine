import json
from pathlib import Path
from scripts.verify_skill_routes import verify

def test_all_48_have_distinct_valid_routes():
    path=Path(__file__).resolve().parents[1]/"docs/CHANNEL_SKILL_ROUTING.json"
    data=json.loads(path.read_text())
    assert verify(data)==[]
    assert len(data["routes"])==48
    assert "Felix" not in data["routes"] and "GOTZ" not in data["routes"]

def test_missing_skill_is_rejected():
    path=Path(__file__).resolve().parents[1]/"docs/CHANNEL_SKILL_ROUTING.json"
    data=json.loads(path.read_text())
    assert any("missing installed primary" in p for p in verify(data,{"motion-art-direction","shot-composition"}))

def test_cross_channel_duplicate_is_rejected():
    path=Path(__file__).resolve().parents[1]/"docs/CHANNEL_SKILL_ROUTING.json"
    data=json.loads(path.read_text())
    data["routes"]["Pixel Fables"]=dict(data["routes"]["OHGUMMY"])
    assert any("duplicate or indistinguishable" in p for p in verify(data))
