"""The engine must not monetize noncommercial imagery or lose attribution."""
import io
import json
import urllib.request

from PIL import Image

from engine.asset_rights import commercial_license, provenance, safe_commons_url
from engine import render as renderer


def test_only_commercially_usable_license_families_are_accepted():
    for name in ("Public domain", "PD", "CC0", "CC0 1.0", "CC BY 4.0", "CC BY-SA 3.0"):
        assert commercial_license(name), name
    for name in ("", "CC BY-NC-SA 4.0", "CC BY-ND 4.0", "Fair use", "All rights reserved", "CC BY-NC 3.0", "Unknown", "CC BY-SA-NC 4.0"):
        assert commercial_license(name) is None, name


def test_provenance_requires_commons_host_and_license():
    pg = {"title": "File:River.jpg"}
    info = {"thumburl": "https://upload.wikimedia.org/wikipedia/commons/1/1a/River.jpg",
            "extmetadata": {"LicenseShortName": {"value": "CC BY-SA 4.0"}, "Artist": {"value": "<b>Alex Example</b>"}}}
    proof = provenance(pg, info)
    assert proof and proof["author"] == "Alex Example"
    assert proof["sourceUrl"] == "https://commons.wikimedia.org/wiki/File:River.jpg"
    assert "CC BY-SA 4.0" in proof["credit"]
    assert not safe_commons_url("http://upload.wikimedia.org/test.jpg")
    assert not safe_commons_url("https://upload.wikimedia.org.evil.example/test.jpg")
    assert not safe_commons_url("https://localhost/test.jpg")
    info["extmetadata"]["LicenseShortName"]["value"] = "CC BY-NC 4.0"
    assert provenance(pg, info) is None
    info["extmetadata"]["LicenseShortName"]["value"] = "CC BY 4.0"
    info["thumburl"] = "https://example.org/river.jpg"
    assert provenance(pg, info) is None


def test_renderer_keeps_license_proof_and_avoids_direct_urls(monkeypatch):
    pic = io.BytesIO()
    Image.new("RGB", (24, 24), (12, 41, 80)).save(pic, format="PNG")
    pg = {"title": "File:Example.jpg", "index": 0, "imageinfo": [{
        "thumburl": "https://upload.wikimedia.org/wikipedia/commons/0/01/Example.jpg",
        "extmetadata": {"LicenseShortName": {"value": "CC BY-SA 4.0"},
                        "Artist": {"value": "<span>Example Photographer</span>"}}}]}
    calls = []

    def fake_open(req: urllib.request.Request, timeout: int):
        calls.append(req.full_url)
        if "api.php" in req.full_url:
            return io.BytesIO(json.dumps({"query": {"pages": {"1": pg}}}).encode())
        return io.BytesIO(pic.getvalue())

    monkeypatch.setattr(renderer, "_open", fake_open)
    scene = {"query": "example photo"}
    found = renderer.fetch_image(scene)
    assert found is not None and found.size == (24, 24)
    assert "Example Photographer" in scene["credit"]
    assert scene["assetProvenance"]["sourceUrl"].startswith("https://commons.wikimedia.org/")
    assert len(calls) == 2
    assert renderer.fetch_image({"image_url": "https://example.org/unverified.jpg"}) is None
    assert len(calls) == 2
