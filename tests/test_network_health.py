from scripts.network_health import report


def rows(specs=0):
    return {"days": ["2026-11-15"], "spec_inventory": [
        {"date": "2026-11-15", "channel": f"Channel {i}", "format": "short",
         "target": 1, "specs": specs, "missing": 1 - specs} for i in range(50)
    ], "failed": [], "attempts_by_model": {"a:b": 4}}


def artifacts():
    return [f"review-2026-11-15-id-{i}-{'a' * 64}" for i in range(50)]


def test_missing_heartbeat_is_an_actionable_alert():
    body, alert = report(None, [], "")
    assert alert and "No usable scheduled inventory" in body


def test_unfilled_channel_slots_are_accurately_reported():
    body, alert = report(rows(), [], "123")
    assert alert and "**0**" in body and "**50**" in body
    assert "actions/runs/123" in body and "Channel 0" in body


def test_all_slots_with_unique_render_artifacts_are_only_technically_complete():
    body, alert = report(rows(1), artifacts(), "99")
    assert not alert
    assert "All required specs and technical artifacts" in body
    assert "public publishing remain separate" in body


def test_provider_failures_are_reported_even_when_specs_are_filled():
    beat = rows(1)
    beat["failed"] = ["this provider failed"]
    body, alert = report(beat, artifacts(), "99")
    assert alert and "Planning failures recorded: **1**" in body


def test_paused_hosting_is_reported_without_false_production_claims():
    body, alert = report(rows(1), artifacts(), "99", hosted_enabled=False)
    assert alert and "intentionally paused" in body
    assert "50 daily published videos are NOT verified" in body
