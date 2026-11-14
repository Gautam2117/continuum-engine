# Pixel Fables: Independent original voxel-story pilot

Pilot specification: `specs/2026-11-17/pixel-s1.json`.

**Review state: PRIVATE, NOT PUBLISHED, NO APPROVAL FOR AUTONOMOUS RELEASE.** This is a functional original creative pilot, not evidence of subscriber growth, a complete 48-channel production worker, or a viral guarantee.

## Narrative proof

The opening scene shows a physically modelled 'NO ROAD AHEAD' sign. The map next shows only part of the supposed route. In the third scene a walkable path of 3D tiles rises out of a cut-out crossing as the protagonist chooses to walk. The second map animation reveals the full route, and the destination reveals the mapmaker theme. The final screen invites the viewer to imagine a new path. All illustrated environments, props, sprites and sounds are locally original. No footage or character model from reference channels is used.

## Real rendering and isolation

- Pixel-only `pixel_map` scene with `lost` and `choice` variants. Other channels fail validation if they attempt to use it.
- Three distinct `voxel` Blender scene acts: `warning`, `bridge`, `arrival`. Animated bridge blocks are tied to the actor's path. Unsupported acts fail validation.
- A `world_focus` portrait layout uses a near-full-frame original stage and separate, checked zones for in-world labels, map subtitles, narration captions and native Shorts controls.
- No generic mascot or emoji stickers. Pixel Fables keeps its own director camera, subtitle treatment and visible story actions.
- Native local Blender works without a separate pip `bpy` package on the Mac.
- A dedicated optional Blender test (`B3D_PIXEL_TEST=1`) physically renders each act at test resolution, checks image differences, and verifies in-world sign and goal labels.

## Production verification

On 14 November 2026 the complete 26.8-second 1080x1920 H.264/AAC master was locally rendered, technically verified, decoded from start to end and contact-sheet inspected. The review pack reported three requested and three actual 3D scenes, zero 3D and asset fallbacks. Audio analysis measured approximately -18.7 dBFS mean, -0.5 dBFS maximum. Strict spec validation passed. The caption/header and map-footer clashes detected in earlier previews were fixed and rechecked in the final frame contact.

Durable local review package: `~/Documents/ContentCreationLab/production/pixel-fables/2026-11-17-pixel-s1/`. It contains `video.mp4`, `thumb.jpg`, `spec.json`, `pack.json`, `probe.json`, `contact.jpg`, `map-check.jpg`, `SHA256SUMS` and explicit private review status. None of these generated binary artifacts belongs in the Git repository.

## Still unverified

Creative audience reception, upload account authorization, distribution and monetization are unknown. Other 47 automated channels have independent creative specifications, but have not all passed bespoke frame-level acceptance. The continuously operated off-Mac worker and policy-compliant daily mass publishing are still separate production gates. The video is deliberately not posted.

## Original click-surface upgrade

The original Pixel Fables thumbnail is composed by `engine/pixel_thumbnail.py` directly from the **actual 3D bridge scene frame** at approximately 60% through that shot. It is not a stock image or the shared generic Engine background. The typography, hero, bridge and palette are original to this story. The full render pack records `pixelPosterFromReal3d=true`; `scripts/verify_review.py` rejects Pixel Fables media when that evidence is missing. Standalone 1280x720 JPEG and mobile-sized contact inspection were performed. The exact thumbnail and updated checksums are preserved alongside the video in the private review package. Predictive click-through and mobile feed exposure remain unmeasured; the owner must still approve the finished upload package.
