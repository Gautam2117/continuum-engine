# 3D kit: scene reference

Every 3D shot is a `b3d` show inside a normal spec scene. Blender renders it (GitHub: fast clay look; Kaggle: Cycles GPU),
the engine draws labels, bubbles, counters and titles on top in the channel's fonts. Always add a 2D `fallback`.

```json
{"say": "...", "show": {"type": "b3d", "scene": "<name>", "params": {...},
  "title": {"text": "What if ...?", "hl": "word"}, "hud": {"label": "...", "from": 0, "to": 100, "unit": "km"},
  "clock": {"from": 0, "to": 60, "unit": "days"}, "fallback": {"type": "say", "text": "..."}}}
```

| Scene | For | Key params |
|---|---|---|
| bars3d | any comparison | items [{label, value, highlight}], unit |
| orbit3d | orbits (Kepler timing) | ratio, a, b |
| fall3d | gravity, drop times (true time) | height, items [{label, g}] |
| earth_tunnel | falling through the Earth | t0, t1 (0..1 trip), hud law "harmonic" |
| moon_drive | Earth → Moon travel | p0, p1, shot chase/wide |
| everest_flood | rising seas | h0, h1 (fraction of peak) |
| clay | clay people, robots, mannequins, gummies on a set | set, cast, props, camera, focus |
| title3d | 3D title / chapter card, any channel | text, hl, sub, look plinth/float |
| corridor | ambient / liminal / horror / hotel | kind corridor/pool/hotel, lights warm/cold/flicker, door "404", drift |
| room_pov | first-person room (fisheye, hands, clock) | kind classroom/bedroom/office, clock "10:42", stamp, look_to |
| gears | working gear train that explodes apart | n 2-5, labels [], glow index, explode 0..1 |
| extrude | blueprint city block rising, red route; or 3D bar map | blocks, route true, items [{label, value, highlight}] |
| panels | glass UI cards building in depth | cards [{title, body, highlight}] |
| voxel | voxel island, hero walking a path | hero colour, level label |

## clay
- `set`: tabletop · street (Indian street, bunting, houses) · office · shop (counter + shelves) · space · studio
- `cast` (up to 5): `{"name", "kind": person|robot|mannequin|gummy, "color", "skin", "x", "to", "action": idle|talk|wave|point|walk|think|cheer, "face": happy|neutral|worried|shock, "says": "speech bubble"}`
- `props` (up to 12): `{"kind": rickshaw|chai_cart|coins|house|tree|desk|laptop|phone|sign|jar|lamp|box, "x", "y", "rot", "n" (coins), "label" (tag, or sign text), "color"}`
- `camera`: push (default) · wide · orbit · close (+ `focus`: cast index)

Channel presets:

| Channel | Set | Cast |
|---|---|---|
| Samjho System | street, office | person host (Hindi bubbles) |
| Money Has Mechanics | street, tabletop | people + rickshaw, chai cart, coins |
| The Odd Units | shop | two robots |
| Think Beyond This | space | mannequin |
| Majority Rules | studio, office | people |
| Tiny Histories | tabletop | people + houses, signs |
| Wild Creature Files | tabletop | (animal models from Quaternius/TRELLIS next) |
| OHGUMMY | studio | gummy |

Preview any shot: `B3D_PYTHON=<python with bpy> python -m lab.action_preview b3d '<show json>' --short --dur 2 --out x.png`

## Channel → scene map (all 3D channels)
- Counterfactual Atlas, What If Anomaly, Crazy Clipz, What Happens in 10, 10SecScientist: bars3d, orbit3d, fall3d, earth_tunnel, moon_drive, everest_flood, title3d
- Survive This, Room 404, Next Frame, LifeSpawn: room_pov, corridor (hotel), clay
- Clay channels (see presets above): clay, title3d
- Gears Unseen, What Drives It: gears, title3d · Heist & Con, Unsealed Show, The India Machine: extrude, title3d
- Workflow Verdict, Brieflylatest, Foundbeam, Oddly Proven, OH THIS EXISTS, News From 2099, Brain Fool Lab (stage): panels, title3d
- BLANK HOURS, The Night Archive, The Low Battery Show, History to Drift To: corridor (pool/corridor/flicker), title3d
- Pixel Fables: voxel · Footage channels (GOTZ, Felix, Founder, Strata, Sent In, Builders, One-Dollar, Benchwise): title3d cards + panels for spec cards
