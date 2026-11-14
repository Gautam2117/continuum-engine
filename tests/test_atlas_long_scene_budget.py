"""Atlas long-form planning must be physically capable of eight-minute narration."""
from autopilot import schemas


def test_long_form_schema_exceeds_old_three_scenes_per_chapter_ceiling():
    short=schemas.short_script("Counterfactual Atlas")["properties"]["scenes"]["items"]
    long=schemas.chapter("Counterfactual Atlas")["properties"]["scenes"]
    assert long["minItems"] == long["maxItems"] == 12
    assert long["items"]["properties"]["say"]["maxLength"] > short["properties"]["say"]["maxLength"]
    assert long["items"]["properties"]["say"]["minLength"] >= 90
    assert long["items"]["properties"]["show"]["properties"]["scene"]["enum"]
    assert 6*long["minItems"] == 72


def test_other_channels_keep_original_long_form_scene_granularity():
    for channel in ("Foundbeam","Samjho System","10SecScientist"):
        schema=schemas.chapter(channel)["properties"]["scenes"]
        assert schema["minItems"] == 3
        assert schema["maxItems"] == 12
