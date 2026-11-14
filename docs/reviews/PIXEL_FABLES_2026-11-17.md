# Pixel Fables original episode: quality acceptance record

Status: **TECHNICALLY VERIFIED, EDITORIAL HOLD. NOT APPROVED FOR UPLOAD.**

Source specification: `specs/2026-11-17/pixel-s1.json`.

Actual private local render on 14 Nov 2026:

`/tmp/ca-pixel-fables-full-review/2026-11-17-pixel-s1/video.mp4`

Measured output: 31.000 seconds; 1080 × 1920; H.264 video; AAC audio; 7,346,023 bytes. All decoded successfully with FFmpeg. The technical package's `renderEvidence` reports three Blender 3D shots requested and three rendered; zero 2D fallbacks and no third-party image assets. Independent `verify(...)` and `verify_audio(...)` checks passed. A contact sheet was inspected locally at `/tmp/ca-pixel-fables-full-contact.jpg`.

Original fictional narrative: `The Map Forgot One Thing`, 88 words, six scenes. The 3D voxel character has a face, clothing and animated gait. Original `pixel_map` illustration stages show an animated route in two independent phases. Generic orange mascot overlays and unrelated stickers are disabled. No copyrighted game characters, outside art, alleged historical facts or unsafe acts.

## Editorial defects found during real visual review

1. **Repeated 3D world:** The voxel environment, character blocking and camera feel nearly identical in all three 3D scenes. Different seeds and text labels do not constitute three purposeful story beats. Add an obstacle and visually changed outcome with materially new staging.
2. **Caption transitions:** In the full-film contact sheet, a title-adjacent caption can crowd the in-world map title near the top of the illustration. Test individual transition frames on a phone-sized crop, not just the contact sheet.
3. **Foley and narrative action:** The map moves and the character walks, but story-specific physical consequences (e.g. crossroads/decision/arrival) are still underanimated. The soundtrack needs intentional footsteps, choice and arrival cues rather than only general pop/whoosh transitions.
4. **Thumbnail:** Generated key art exists and needs a separate mobile click-surface review. Do not copy the visual concept of the example Instagram/YouTube channels.
5. **End-to-end publishing:** No owner approval receipt, Studio posting validation or connected YouTube upload test exists for this episode.

**Result:** Keep the media private. Fix the visual and editorial defects and render again. The approved video will need a new exact MP4+thumbnail digest and a separately recorded owner decision. No public upload was made.

## Revision 2: 14 November 2026, continued independent quality pass

The previous review remains in the historical record. A follow-up original 26.8-second plot-turn cut replaces the 31-second generic motivational story. A physical warning sign, a cut-out crossing with new blocks rising under the actor's feet, and an individually modelled destination arch now supply distinct 3D story beats. Both pixel-map phases distinguish an incomplete route from the completed path. The original title, grid, footer and narration-caption collisions were identified on actual encoded frames and corrected through the final revision. The generic host and stickers remain disabled. A per-channel portrait-focused layout and strict story-state validators protect those decisions.

Local, decoded and audio-verified master: `~/Documents/ContentCreationLab/production/pixel-fables/2026-11-17-pixel-s1/video.mp4`. The same private folder holds its spec, metadata pack, contact sheet, frame detail, SHA-256 list and explicit NO-UPLOAD status. The final render package requested three 3D scenes and confirms all three rendered with no fallback. Audio volume check passed at -18.7 dBFS mean and -0.5 dBFS maximum. Full 1080 x 1920 H.264/AAC decode passed. The scripted duration is 26.8 seconds. Native Blender act tests passed on the Mac; final Engine suite 169 passed, 17 optional skipped prior to merging other concurrent work.

**Remaining editorial holds:** bespoke scene-linked foley and music acceptance, independent mobile thumbnail click-surface review, comparison against a self-defined creative-quality rubric, publisher authorization and owner approval of the actual SHA-256 media. No automatic upload was performed and no growth claim is supported. The source of truth for this revised cut is `docs/PIXEL_FABLES_PILOT.md` plus the current version of `specs/2026-11-17/pixel-s1.json`.
