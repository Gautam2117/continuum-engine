# Final style map: all 50 channels, ₹0 stack (13 Nov 2026)

Decision: no Higgsfield or other paid generators. Every channel gets the best-fit look. Most are now true 3D or 3D-depth, and whiteboard, pixel, ink, footage and persona looks are kept where they are the best fit, each with added depth. Everything below is free and open source or free-tier, and is usable commercially (licences checked 13 Nov; recheck before each new model goes live).

## 0. Status (13 Nov, 21:00 IST)
- **Kaggle is live.** Account **continuumarc**; the key is in GitHub secrets. Cycles renders on 2x T4 with OptiX.
- **Built in the engine** (continuum-engine main) — 15 3D scenes; reference in lab/3d-kit.md:
  - **S1 world sims:** bars3d, orbit3d, fall3d, earth_tunnel, moon_drive, everest_flood
  - **S3 clay:** clay — people, robots, mannequins, gummies; 7 actions, 4 faces; 6 sets: tabletop, Indian street, office, shop, space, studio; 12 props incl. rickshaw, chai cart, coins; speech bubbles
  - **S2 POV:** room_pov (classroom, bedroom, office; hands, clock, stamp) and corridor (hotel with a 404 door)
  - **S4 technical:** gears (exploding gear train) and extrude (blueprint block with route, or 3D bar map)
  - **S5 glass UI:** panels — cards that build in depth
  - **S6 ambient:** corridor (liminal corridor, pool, flicker)
  - **S8 voxel:** voxel island with a walking hero
  - **F overlay / all channels:** title3d — 3D type in the channel font
- **Labels:** all scenes draw labels, counters, bubbles and cards in the channel's own fonts, pinned to the 3D objects.
- **Rendering:**
  - GitHub (clay/Workbench, about 1.4 s per frame) for daily videos.
  - Kaggle (Cycles GPU) for hero videos.
  - Kaggle Wan 2.2 TI2V-5B (ai-kaggle.yml) for persona and cinematic motion from a still: built; first test run in progress.
- **Autopilot:** Atlas may use the world-sim scenes whenever a topic fits; other channels are made on request using the presets in lab/3d-kit.md.
- **Still to do:**
  - real animal and creature models for Wild Creature Files (Quaternius CC0 / TRELLIS);
  - lip-sync (LatentSync) for talking personas;
  - Hindi voice + Devanagari captions test for Samjho System;
  - Grease Pencil drawn-in-3D (S7) for Drawn Out Minds and Truth Over Propaganda;
  - your character sheets for the three personas.

## 1. Proven today (spike, 13 Nov)
- Blender 5.3 runs headless as a Python module (`pip install bpy`, no GPU, no display).
- Test shot: a low-poly Earth cutaway with layered core, a tunnel, a falling capsule, and camera dolly at 1080x1920.
  - Workbench engine (flat-shaded clay look with shadows and cavity): about 2.3 s per frame on 2 vCPU.
  - Cycles (cinematic, 8 samples plus denoise): about 35 s per frame on 2 vCPU.
  - EEVEE also renders through software EGL (slow without a GPU).
- continuum-engine is a public repo, so GitHub Actions minutes are free and render jobs can be split across parallel matrix jobs. A 45 s Short is 1,350 frames: about 5–10 min in Workbench split 10 ways, and roughly 20–30 min in Cycles split 20 ways (estimate, to be measured on the real runners).
- Spike script: lab/spike3d/earth_cutaway.py (branch 3d-spike).

## 2. The free stack (what does what)

| Job | Tool | Licence or cost | Runs on |
|---|---|---|---|
| 3D scenes, animation, crowds, cameras | Blender 5.3 (bpy) + Geometry Nodes | GPL (outputs ours) | GitHub Actions (CPU) |
| Fast clay or flat-shaded 3D look | Blender Workbench | free | Actions |
| Cinematic 3D look | Blender Cycles + OpenImageDenoise | free | Actions matrix; Kaggle GPU for long videos |
| Whiteboard and ink lines in 3D space | Blender Grease Pencil + Line Art / Freestyle | free | Actions (to test headless) |
| HUD, captions, counters, stickers, end cards | Continuum Engine (PIL + ffmpeg) composites over Blender passes | ours | Actions |
| Data-driven 3D titles, glass UI, 3D text | Remotion + @remotion/three (React Three Fiber) | free for teams of 3 or fewer | Actions |
| Maths and physics diagrams | Manim (Community) | MIT | Actions |
| Ready-made CC0 models | Kenney, Quaternius, KayKit, Poly Haven (models, HDRIs, textures), ambientCG | CC0 | bundled in repo |
| Extra low-poly models | Poly Pizza / Icosa (mostly CC-BY: credit in description) | CC-BY / CC0 | bundled |
| Real objects and space | NASA 3D Resources, Smithsonian Open Access | public domain or CC0 | bundled |
| Maps | Natural Earth (public domain) + OpenStreetMap (ODbL, credit) extruded in Blender | free | Actions |
| Image to 3D (props, mascots, goat) | TRELLIS (MIT, Microsoft) on Kaggle; Hunyuan3D 2.1 as backup (Tencent community licence, India allowed, but check terms) | free | Kaggle T4 (about 30 GPU h a week) |
| Still images, plates, textures | Qwen-Image-2512 or Z-Image Turbo or FLUX.2 klein 4B (all Apache 2.0); Antigravity (you) | free | Kaggle; Antigravity |
| AI video motion (persona, cinematic) | Wan 2.2 (Apache 2.0) image-to-video; LTX-Video for fast drafts | free | Kaggle via ComfyUI notebook |
| Lip-sync (personas, anchors) | LatentSync (Apache code) or MuseTalk (MIT) | free | Kaggle |
| Mouth flaps for 3D or cartoon characters | Rhubarb Lip Sync | MIT | Actions |
| Character animation clips | Mixamo (free, Adobe account) + Quaternius universal animations (CC0) | free | baked into assets |
| Voice | Kokoro (Apache 2.0; English + Hindi voices) | free | Actions |
| Music beds | ACE-Step 1.5 (Apache 2.0) + our pad synth; Freesound CC0 for SFX | free | Kaggle / Actions |
| Thumbnails | Blender hero frame (Cycles, high samples) + engine text | free | Actions |
| Your desktop control | blender-mcp (MIT) lets Claude drive Blender on your PC for hand-built hero assets | free | your machine |

Kaggle automation: kernels are pushed and run with the Kaggle API from a GitHub Action, and results come back as kernel output. This needs a free Kaggle account and an API token stored as a GitHub secret.

## 3. Style systems (9 looks, shared assets)

1. **S1 Low-poly World Sim.** Blender low-poly worlds, crowds (Geometry Nodes), HUD counter, serif question title with one coloured word, slow dolly and orbit, Cycles.
2. **S2 POV Clay.** First-person, flat-shaded and outlined (Workbench + cavity + Line Art), fisheye lens, time-and-place stamp, A/B dilemma end (the trz_ftb grammar, our own scenes).
3. **S3 Clay Diorama.** Round-head clay figures, tabletop, tilt-shift depth of field, soft daylight, Cycles.
4. **S4 Technical 3D.** Exploded models, turning gears, extruded isometric blueprints and maps, labels tracked to 3D points.
5. **S5 Glass UI in 3D.** Floating panels and 3D type in depth, particle servers, Remotion three or Blender.
6. **S6 Ambient 3D.** Procedural rooms, corridors, pools and lamps, very slow drift, volumetric light, Cycles at low samples (long renders on Kaggle).
7. **S7 Drawn-in-3D.** Whiteboard or ink strokes drawn live with Grease Pencil on a real 3D desk, paper or wall with camera moves (keeps the hand-drawn charm, adds depth).
8. **S8 Voxel / Pixel 3D.** Voxel and isometric pixel worlds, retro HUD, orthographic camera.
9. **S9 AI Cinematic + Persona.** Antigravity or Qwen-Image stills, then Wan 2.2 motion on Kaggle, LatentSync for speech, film grade, plus a 3D-lit title layer. Footage channels use the **F overlay**: your footage plus 3D titles, cards, counters and mascots.

## 4. Final style per channel (all 50)

Readiness: **Now** = can render today with the current engine; **Kit** = needs the shared kit for that style (build order in section 5); **You** = needs your footage, face or approval.

| # | Channel | Final look | System | Tools | Readiness |
|---|---|---|---|---|---|
| 1 | Counterfactual Atlas | Low-poly 3D worlds and cutaways, HUD timer, serif question, vote end | S1 | Blender (Workbench on Actions, Cycles on Kaggle) + engine HUD | **Built**: 6 scenes, Autopilot uses them |
| 2 | What If Anomaly | Low-poly cities and crowds, terminal-green anomaly counter, scanlines | S1 | Blender + engine | Kit S1 |
| 3 | Crazy Clipz | Records rebuilt as low-poly 3D sims, red HUD counter | S1 | Blender + engine | Kit S1 |
| 4 | What Happens in 10 | 3D room or object with an amber clock HUD, before and after states | S1 | Blender + engine | Kit S1 |
| 5 | Survive This | 3D POV emergency scenes, 60 s clock HUD, official source card | S2 | Blender Workbench + engine | Kit S2 |
| 6 | Room 404 | POV through stylised 3D hotel corridors, glowing clues, timer | S2 | Blender | Kit S2 |
| 7 | Next Frame | Clay 3D setups frozen one beat before impact, A/B/C cards, no voice | S2+S3 | Blender rigid-body physics | Kit S2 |
| 8 | Samjho System | Clay 3D Indian street and office, blob host, Hindi captions, clock | S3 | Blender + Kokoro hf_alpha + Devanagari font | Kit S3 + Hindi |
| 9 | 10SecScientist | 3D lab bench, objects reacting in 11 s loops | S1 | Blender Workbench (fast) | Kit S1 |
| 10 | Wild Creature Files | Low-poly 3D animal in its habitat diorama + public-domain photo cards | S3 | Quaternius animals + TRELLIS + Blender | Kit S3 |
| 11 | Tiny Histories | Real 3D tabletop dioramas, tilt-shift, little flags | S3 | Blender + Kenney/KayKit + TRELLIS props | Kit S3 |
| 12 | Money Has Mechanics | Clay figures, 3D rickshaw and chai cart, ticking rupee counters | S3 | Blender + engine | Kit S3 |
| 13 | Think Beyond This | Lone clay mannequin in a 3D starfield, one elegant object per idea | S3 | Blender | Kit S3 |
| 14 | The Odd Units | Two clay 3D robots at a 3D corner shop, glitch frames | S3 | Blender + Rhubarb mouths | Kit S3 + You approve cast |
| 15 | OHGUMMY | Glossy 3D gummy mascots | S3 | TRELLIS/Blender, Cycles subsurface | Kit S3 |
| 16 | Majority Rules | Stylised 3D clay cast, A/B vote cards | S3 | Blender + Rhubarb | Kit S3 + You approve premise |
| 17 | What Drives It | Real 3D exploded engines and machines, labels track parts | S4 | Blender + NASA/Smithsonian/CC0 models | Kit S4 |
| 18 | Gears Unseen | Procedural brass gears and mechanisms opening on a book | S4 | Blender procedural gears | Kit S4 |
| 19 | Heist & Con | Extruded isometric building, red route, protect-yourself checklist | S4 | Blender | Kit S4 |
| 20 | The India Machine | Extruded 3D India map with animated flows | S4 | Natural Earth + Blender | Kit S4 |
| 21 | Unreal Goods Co. | 3D product on pedestal, studio lighting, slow orbit, CONCEPT label | S4 | TRELLIS/Blender + Poly Haven HDRI | Kit S4 |
| 22 | Unsealed Show | 3D evidence wall in a dim room, camera to each pinned document | S4+S6 | Blender | Kit S4 |
| 23 | Foundbeam | 3D poster wall, camera pushes panel by panel, amber | S5 | Remotion three or Blender | Kit S5 |
| 24 | Workflow Verdict | Neon boxes building in 3D space, floating verdict card | S5 | Remotion three | Kit S5 |
| 25 | OH, THIS EXISTS | One slow-rotating 3D object, single-line reveals | S5 | Blender | Kit S5 |
| 26 | Brieflylatest | Glass headline and source cards floating in depth | S5 | Remotion three | Kit S5 |
| 27 | Oddly Proven | 3D study card flip, icon grid in depth, PROVEN stamp | S5 | Remotion three | Kit S5 |
| 28 | Brain Fool Lab | Exact code-drawn illusions on a flat panel inside a 3D stage (illusions must stay flat to work) | S5 | engine + Blender stage | Now (flat) → Kit S5 |
| 29 | News From 2099 | 3D holographic studio, fictional 3D anchor, permanent FICTION badge | S5+S9 | Blender + LatentSync anchor | Kit S5 |
| 30 | History to Drift To | Painted plates split into true 2.5D depth layers, slow camera, candle light | S6 | Antigravity plates + depth layers in Blender | Now (2D) → Kit S6 |
| 31 | The Low Battery Show | Cosy low-poly 3D rooms, rain on window, lamp glow | S6 | Blender | Kit S6 |
| 32 | BLANK HOURS | Procedural liminal corridors and pools, slow drift | S6 | Blender (renders on Kaggle) | Kit S6 |
| 33 | The Night Archive | 3D found-footage corridor or room with VHS grade, redacted docs | S6 | Blender + engine VHS overlay | Kit S6 |
| 34 | Drawn Out Minds | Whiteboard marker drawing itself on a real 3D board or desk, camera moves | S7 | Grease Pencil + Blender | Kit S7 |
| 35 | Truth Over Propaganda | Ink-and-wash paper layers in 3D depth, redrawn posters | S7 | Grease Pencil + Antigravity plates | Kit S7 |
| 36 | Pixel Fables | Voxel and isometric pixel worlds, retro HUD | S8 | Blender voxel + orthographic camera | Kit S8 |
| 37 | Inkbound | Cinematic AI stills with motion and depth, page-turn cards | S9 | Antigravity/Qwen-Image → Wan 2.2 | You (book pick) |
| 38 | LifeSpawn | Cinematic life arcs with age cards | S9 | Antigravity → Wan 2.2 | You (first being) |
| 39 | Epic Elsewhere | Painterly myth frames with depth, split-panel comparisons | S9 | Antigravity → Wan 2.2 | You |
| 40 | Sienna Carter | Photoreal persona from her locked face, soft depth, 3D title cards, AI label | S9 | Antigravity sheet → Wan 2.2 → LatentSync | You (sheets) |
| 41 | Aditi Raichand | Same as Sienna, pink grade, Indian settings | S9 | as above | You (sheets) |
| 42 | Kiara | Same, sage grade, calm motion | S9 | as above | You (sheets) |
| 43 | GOTZ | Your gameplay + 3D goat avatar reacting + 3D title cards | F + S3 | OBS + TRELLIS/Blender goat + Rhubarb | You (record) |
| 44 | Felix | Your gameplay + 3D depth-blur title cards, no avatar | F | OBS + Blender titles | You (record) |
| 45 | Founder, Actually | Your face + 3D number cards | F | camera + Blender cards | You (film) |
| 46 | Strata | App's own 3D scenes as hero + 3D titles | F | screen capture | You (capture) |
| 47 | Sent In | Submissions + 3D mascot reaction + score card | F + S3 | Blender mascot | You (consent form) |
| 48 | The Builders Long Game | Podcast + 3D lower-thirds and chapter cards | F | Blender cards | You (record) |
| 49 | One-Dollar Builds | Hands footage + 3D cost counter | F | Blender counter | You (film) |
| 50 | Benchwisedeals | Product footage + 3D spec cards and verdict badge | F | Blender cards | You (products) |

Count by main system: S1 5, S2 3, S3 8, S4 6, S5 7, S6 4, S7 2, S8 1, S9 6, F 8 = 50.

## 5. Build order (one kit unlocks many channels)
1. **S1 world-sim kit + Atlas** (render worker in Actions, asset pack, HUD compositing, Earth/Moon/Everest/crowd scenes). Atlas switches to 3D when a full Short passes QA.
2. **S3 clay kit** (shared figure rig, Quaternius/Kenney import, tilt-shift): 9 channels.
3. **F overlay** (3D title, card and counter templates): 7 footage channels as soon as you record.
4. **S2 POV**, **S4 technical**, **S5 glass UI**.
5. **S9 Kaggle worker** (Wan 2.2 + LatentSync + Qwen-Image notebooks) for personas and cinematic.
6. **S6 ambient**, **S7 drawn-in-3D** (headless Grease Pencil test first), **S8 voxel**.

## 6. Rules that do not change
- Disclosed AI on every persona and AI-motion video; FICTION badge on News From 2099.
- No copying of reference reels' scenarios, characters or frames; we copy structure only.
- Credit CC-BY assets and ODbL map data in the description; CC0 needs nothing.
- Licence check before any new model: Qwen-Image 2.1 (Sep 2026) is non-commercial, so use Qwen-Image-2512 / Z-Image / FLUX.2 klein 4B; the Wan open line ends at 2.2; FLUX.1/2 dev weights are non-commercial for deployment.
