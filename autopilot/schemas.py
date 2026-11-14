"""Ollama's native JSON Schemas: constrain the *shape*, not the truth of the script.

The strict creative, source, identity, timestamp and editorial gates are
independent of these model-output shapes. These schemas do not approve media.
"""
from __future__ import annotations

from engine.scenes import SCENES
from .playbooks import PLAYBOOKS


TEXT = {"type": "string"}
LIST_OF_TEXT = {"type": "array", "items": TEXT}


def allowed_scene_types(channel: str) -> list[str]:
    """Follow the channel's specific visual grammar, not a global template."""
    pb = PLAYBOOKS[channel]
    scene_bias = {str(item).split(" (")[0].strip() for item in pb.get("scene_bias", [])}
    allowed = scene_bias.intersection(SCENES)
    if pb.get("b3d"):
        allowed.add("b3d")
    return sorted(allowed | {"title", "end", "say"})


def visual_scene(channel: str, *, ten_seconds: bool = False,
                 atlas_long: bool = False) -> dict:
    words = {"type": "string",
             "minLength": 5 if ten_seconds else 90 if atlas_long else 25,
             "maxLength": 95 if ten_seconds else 160 if atlas_long else 115}
    if PLAYBOOKS[channel].get("lang") == "hi":
        # The normal independent script reviewer still enforces the >=60%
        # Devanagari ratio. The schema only prevents fully romanized Hindi.
        words["pattern"] = "[\u0900-\u097f]"
        words["description"] = "Natural spoken Hindi in Devanagari script, not Romanized Hinglish"
    show_properties = {"type": {"type": "string", "enum": allowed_scene_types(channel)}}
    if PLAYBOOKS[channel].get("b3d"):
        show_properties["scene"] = {"type": "string", "enum": PLAYBOOKS[channel]["b3d"]}
    return {
        "type": "object",
        "properties": {
            "say": words,
            "show": {
                "type": "object", "properties": show_properties,
                "required": ["type"], "additionalProperties": True,
            },
            "emoji": TEXT,
        },
        "required": ["say", "show"],
        "additionalProperties": False,
    }


def short_script(channel: str) -> dict:
    ten_seconds = channel == "10SecScientist"
    return {
        "type": "object",
        "properties": {
            "title": TEXT, "thumb": TEXT, "description": TEXT,
            "tags": LIST_OF_TEXT,
            "scenes": {"type": "array", "items": visual_scene(channel, ten_seconds=ten_seconds),
                       "minItems": 4 if ten_seconds else 7,
                       "maxItems": 4 if ten_seconds else 11},
        },
        "required": ["title", "thumb", "description", "tags", "scenes"],
        "additionalProperties": False,
    }


TOPICS = {
    "type": "object", "properties": {
        "topics": {"type": "array", "items": {
            "type": "object", "properties": {
                "topic": TEXT, "axis": TEXT, "wiki_query": TEXT, "why": TEXT,
            }, "required": ["topic", "axis", "wiki_query", "why"],
            "additionalProperties": False,
        }, "minItems": 1, "maxItems": 8},
    }, "required": ["topics"], "additionalProperties": False,
}


def long_outline(chapters: int) -> dict:
    return {
        "type": "object", "properties": {
            "title": TEXT, "thumb": TEXT, "description": TEXT,
            "tags": LIST_OF_TEXT,
            "promise": TEXT,
            "chapters": {"type": "array", "items": {
                "type": "object", "properties": {
                    "name": TEXT, "beats": TEXT, "open_loop": TEXT,
                }, "required": ["name", "beats", "open_loop"],
                "additionalProperties": False,
            }, "minItems": chapters, "maxItems": chapters},
        },
        "required": ["title", "thumb", "description", "tags", "promise", "chapters"],
        "additionalProperties": False,
    }


def chapter(channel: str) -> dict:
    # A 1,250-word Atlas episode needs roughly 72 cuts of 17-22 spoken
    # words. Old 3-scene chapters could produce a 1-minute "long" video.
    atlas_long = channel == "Counterfactual Atlas"
    return {"type": "object", "properties": {
        "scenes": {"type": "array", "items": visual_scene(channel, atlas_long=atlas_long),
                   "minItems": 12 if atlas_long else 3, "maxItems": 12},
    }, "required": ["scenes"], "additionalProperties": False}

EDITOR = {"type": "object", "properties": {
    "hook": {"type": "integer", "minimum": 1, "maximum": 10},
    "originality": {"type": "integer", "minimum": 1, "maximum": 10},
    "accuracy": {"type": "integer", "minimum": 1, "maximum": 10},
    "unsupported_claims": LIST_OF_TEXT,
    "fixes": LIST_OF_TEXT,
    "pass": {"type": "boolean"},
}, "required": ["hook", "originality", "accuracy", "unsupported_claims", "fixes", "pass"],
    "additionalProperties": False}
