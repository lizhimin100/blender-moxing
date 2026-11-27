# Blacksmith / Forge — Art Direction Brief
**Target:** stylized low-poly RTS building, 8.0 m frontage, isometric camera (35–45° pitch), texture-free, mobile/indie budget, must read as *forge* not *house* at 96–140 px on screen.

---

## 0. The read test (do this before modelling)
Render the finished asset at **96 px tall, flat black, no interior detail**, next to the barracks / farm / town hall. A viewer must name "blacksmith" in <1 s. Pass requires **at least 3 of these 4 silhouette cues**:

| # | Cue | Where it lives |
|---|-----|----------------|
| A | Stack breaking the ridge by 12–25% | roof |
| B | Open glowing mouth with a hood above it | annex facade |
| C | Lean-to / canopy cantilevered over a yard | front third |
| D | Tool-cluster silhouette outside the wall line | yard edge |

A house has **none** of these. Any two of them plus a normal gable is still "house with a chimney" — this is exactly the failure mode of the current `blacksmith_v6` (it has A weakly, C weakly, and no B, no D).

---

## 1. Silhouette language — what makes it read "forge"

Analysed from the five Age of Empires II DE blacksmith variants ([variant sheet](https://static1.thegamerimages.com/wordpress/wp-content/uploads/2023/03/all-the-various-blacksmith-style-in-age-of-empires-2-definitive-edition.jpg), footprint 3×3 tiles per the [AoE2 wiki](https://wiki.biligame.com/aoe2de/%E9%93%81%E5%8C%A0%E9%93%BA)), the [Warcraft III human building set](https://classic.battle.net/war3/human/buildingstats.shtml), the [Northgard Forge](https://cdn.mobygames.com/screenshots/18468911-northgard-windows-the-forge-can-upgrade-your-tools-and-weapons.jpg), the [Clash of Clans Blacksmith](https://static.wikia.nocookie.net/clashofclans/images/e/e8/Blacksmith9.png) and the [Stronghold blacksmith](https://stronghold.heavengames.com/gameinfo/buildings/arms/):

- **Every single one is two masses**, never one box: a tall main hall + a **lower annex at one end**, with the annex aligned to the *front* corner (camera side). AoE2's European, Middle-Eastern and Japanese variants all push the annex to the same screen-left position regardless of civ.
- **Every one has a stack that clears the ridge.** No exceptions across AoE2, WC3, Northgard, CoC.
- **Every one has one dark-to-bright value jump at the annex** — a black hood/canopy over an orange interior. This is the highest-contrast area of the whole sprite and it is what the eye lands on first.
- **Yard props sit outside the wall footprint**, not inside it, so they add to the silhouette rather than the texture.
- Roofs are **steep (≈45–55°) and plain**, walls are **low-contrast**, props/glow are **high-contrast**. Silhouette is carried by 3 shapes only: stack, canopy edge, yard spikes.

---

## 2. Roof & top-silhouette specifics

Numbers are **relative to building height H** (H ≈ 7.4 m for an 8 m frontage: 3.2 m eave + 4.2 m gable rise) or to **width W = 8 m**.

| Element | Spec | Rationale |
|---|---|---|
| Main gable pitch | **45–52°**, ridge at **0.62–0.66 H** | steeper than a cottage, shallower than a tower; matches AoE2/WC3 |
| Eave height | **0.42–0.45 H** (3.2 m) | keeps the building wider-than-tall at the base, reads "workshop" not "keep" |
| Lean-to span | **50–70% of W** (4.0–5.6 m) along the frontage | long enough to shade a real work yard |
| Lean-to projection | **1.6–2.2 m** (20–28% W), pitch **20–26°** | deep shadow plane under it |
| Lean-to low edge | **2.2–2.4 m** above pad | worker-height + 0.6; below the main eave so the skyline steps |
| Lean-to lateral offset | **≥ 8% W (0.65 m)** against the main ridge | misalignment = two masses; alignment = one house |
| Stack section | **0.9–1.1 m square** (11–14% W), batter **8–12%** | chunky masonry, not a stovepipe |
| Stack cap height | **1.15–1.25 × ridge** (i.e. 12–25% above ridge) | the single cheapest forge signal |
| Stack crown | **+15–20% wider than shaft**, slab **0.18–0.25 m**, 3–5 louver slats at **25–35°** | "mushroom head" = industrial, reads at 60 px |
| Ridge strap | **0.06–0.10 m** iron band, full length | ties the roof planes, adds a hard horizontal |
| Ridge crest | **one only**, **6–8% H** tall (0.45–0.6 m), at the gable end | >2 crests = clutter, and crosses read as chapel |
| Gable vent | **0.9–1.2 m** at base, inset **0.10–0.15 m**, 4–6 slats | loft/vent read, not window read |
| Forge hood | base **1.8 × 1.4 m** at 1.1 m, throat **0.7 m** at **2.6 m** | battered truncated pyramid = the iconic forge form |
| Forge mouth | **1.3 m W × 1.1 m H**, 0.15 m inset reveal, emissive | must be ≥ 1/3 of the annex facade width |

---

## 3. Yard / work-area props — sizes against an 8 m building

Readability floor: at default RTS zoom an 8 m building is **≈110 px wide**, so **1 px ≈ 7 cm**. Anything under **0.12 m** is invisible; a prop needs **≥ 0.4 m** in its smallest dimension and **≥ 0.9 m** to read *shape*.

| Prop | Size (relative to W = 8 m) | Absolute | Placement |
|---|---|---|---|
| Anvil + stump | 13% W tall | anvil 0.95 L × 0.34 W × 0.5 H, stump ⌀0.45 × 0.5 | camera-right of forge mouth, 1.2–1.6 m out |
| Tool rack | 24% W tall / 20% W wide | 1.9 H × 1.6 W, 6–8 tools at 0.35–0.45 pitch | yard corner, wall-parallel |
| Quench barrel | 10% W ⌀ | 0.8 ⌀ × 0.95 H, water disc 0.06 below rim | beside anvil |
| Water trough (AoE2 cue) | 20% W long | 1.6 × 0.5 × 0.4 | yard edge, bright teal surface |
| Coal scuttle / heap | 11% W | 0.9 W × 0.55 H, near-black + 2 ember dots 0.08 ⌀ | under the lean-to, deep shadow |
| Ingot basket | 7% W | 0.55 ⌀ × 0.45 H, 5 bars 0.4 L | on the pad, mid-ground |
| Weapon rack | 28% W long | 2.2 L × 1.25 H, 5–6 blades at 12–20° tilt | far yard edge — serrated top edge survives at 96 px |
| Grindstone | 11% W ⌀ | wheel 0.85 ⌀ × 0.22, axle 0.65 | mid yard, circular contrast to all the boxes |
| Outdoor hearth + hood | 20% W | 1.6 × 1.1 base, hood to 2.6 H | under the lean-to |
| Bellows | 18% W long | 1.4 L × 0.7 H, nozzle at 1.0 H | wall-mounted left of the hood |

Yard pad: **3.2 × 2.4 m**, +0.05–0.08 m, different flat color (packed ash/earth). 7–9 props, **0.3 m of clean background between any two silhouettes**, tall props on the two outer corners, low props inside.

---

## 4. Team color

Measured on the current `blacksmith_v6` render: blue covers **≈4.3%** of the non-background pixels (≈7% of the building body, since the mask includes the plinth and cast shadow). Target is **8–12% of the building's visible pixels**.

| Shape standard | Dimensions | Notes |
|---|---|---|
| Swallowtail banner | 0.55 W × 1.5 H (**1:2.7**) | top at **4.2–4.6 m** (60–75% H) |
| Heater shield / emblem | 0.55 × 0.65 (**≈1:1.18**) | gable face or door lintel |
| Trim band | **0.15 m** tall, tileable at 1.0 m modules | eave fascia, full frontage |
| Pennant on stack | 0.22 × 0.85 | at the stack crown, single |
| Lintel crest | 0.40 × 0.50 | over the door, TC2 mask slot |

Conventions that hold across the references: AoE2 spends a **0.15 m fascia band + one small banner** and reads faction instantly; WC3 spends **15–25%** on roof planes and banners and is loud by design; CoC tints the roof plus 2 accents. **Pick one convention and keep it consistent across all six buildings** — the failure is per-building improvisation.

---

## 5. Mobile budget

| Item | LOD0 | LOD1 | LOD2 |
|---|---|---|---|
| Structure (walls, floor, beams) | 900–1,300 tris | 500 | 180 |
| Roof + eaves + fascias | 800–1,100 | 400 | 120 |
| Stack + crown + hood | 350–550 | 220 | 90 |
| Lean-to / canopy | 300–450 | 150 | 60 |
| Yard props (all) | 1,400–1,900 | 900 (drop <0.5 m) | merged 200 |
| Team-color plates | 120–200 | 120 | banner sprite |
| **Total** | **≤ 6,000** | **≤ 2,600** | **≤ 700** |

- **2 materials, 0 textures** — one flat-color material (vertex color or material-slot IDs), one emissive for forge/embers/window. Geometry instead of texture is the documented studio practice for this style ([80.lv](https://80.lv/articles/tips-on-low-poly-game-environments)).
- **3 draw calls** — structure / props / team plates, merged at build time.
- Subdivision & bevel **only** on 6 hero curved forms (anvil horn, bellows, barrel, grindstone, hood flare, stack crown); everything architectural stays **hard-edged**, bevel 1 segment at 2–3 cm.
- Cylinder segments: **8** (barrel, stump), **12** (grindstone), **6** (posts), **8** (round hood).
- Vertex-color AO at **0.75×** in crevices; flat normals on architecture, smooth only on barrels/wheels.
- Motion is **emissive only** (1 flicker) + one **24-tri smoke card** — never animate geometry.

---

## 6. The 30 recommendations

1. Compose every forge as two masses — tall hall + lower off-centre annex — because all five AoE2 blacksmith variants, WC3 and Northgard use this L-shaped read ([AoE2](https://static1.thegamerimages.com/wordpress/wp-content/uploads/2023/03/all-the-various-blacksmith-style-in-age-of-empires-2-definitive-edition.jpg), [AoE2 stats](https://wiki.biligame.com/aoe2de/%E9%93%81%E5%8C%A0%E9%93%BA)).
2. Hold the annex at **55–62% of the hall's ridge height** and overlap it only **1.5–2.0 m** laterally, so the skyline steps down in one direction.
3. Push the stack **12–25% above the ridge** (cap at **1.15–1.25 × ridge**) — a chimney that stops below the ridge is the strongest "generic house" tell, and it is what v6 does.
4. Crown the stack with a **flared corbelled cap +15–20% wider, 0.18–0.25 m thick, 3–5 louvers at 25–35°** — the mushroom head is the second-fastest forge read after the glow ([Northgard](https://cdn.mobygames.com/screenshots/18468911-northgard-windows-the-forge-can-upgrade-your-tools-and-weapons.jpg)).
5. Cut one **unglazed 1.3 × 1.1 m opening** with a 0.15 m inset reveal and emissive interior, at **≥1/3 of the annex facade width** — CoC pushes the same idea to a mouth ≈25% of the facade ([CoC](https://static.wikia.nocookie.net/clashofclans/images/e/e8/Blacksmith9.png)).
6. Make a **battered forge hood** (truncated pyramid, base 1.8 × 1.4 m, throat 0.7 m at 2.6 m) the hero form of the annex — the hood, not the chimney, is what says "forge" ([Northgard](https://cdn.mobygames.com/screenshots/18468911-northgard-windows-the-forge-can-upgrade-your-tools-and-weapons.jpg)).
7. Delete chapel markers — **no crosses, no finials thinner than 0.06 m, no pointed arches**; replace the ridge finial with an anvil silhouette or a hammer-and-tongs crest (v6 reads as a chapel because of the gold crosses + spike row).
8. Force **one prop outside the wall footprint** (weapon rack or anvil+stump, 0.5–0.9 m proud) — RTS buildings are read at the yard edge, not the wall.
9. Pitch the main gable **45–52°** with the eave at **0.42–0.45 H** (3.2 m eave / 6.4 m ridge on an 8 m frontage) — steeper than a cottage, shorter than a keep ([WC3](https://classic.battle.net/war3/human/buildingstats.shtml)).
10. Cantilever a **lean-to over the yard, 50–70% of the frontage, 1.6–2.2 m deep, 20–26° pitch, low edge 2.2–2.4 m** so a worker fits under it and the eave line still steps.
11. Offset the lean-to against the main ridge by **≥8% of W (0.65 m)** — aligned ridges fuse the two masses into one house.
12. Give the lean-to an **asymmetric rafter rhythm (0.9 / 0.6 m alternating)** and a **0.25–0.35 m fascia board**, because the dark under-plane is the value anchor that makes the fire pop.
13. Run a **0.06–0.10 m iron ridge strap** the full length and allow **one crest only, 6–8% of H (0.45–0.6 m)** — more than two silhouette-breakers on a ridge reads as fairytale.
14. Cut a **triangular louvered gable vent, 0.9–1.2 m at the base, 0.10–0.15 m inset, 4–6 slats** so it reads as a vent, not a window, at RTS zoom.
15. Model the **stack–roof junction with a masonry collar 0.25 m proud** of the roof plane so the chimney grows out of the roof instead of floating on it.
16. Lay a **3.2 × 2.4 m work pad +0.05–0.08 m** in front of the annex in a different flat color — the pad is the production icon the player learns.
17. Size **anvil+stump at 1.05 m (13% of W)**: anvil 0.95 × 0.34 × 0.5, stump ⌀0.45 × 0.5, placed 1.2–1.6 m camera-right of the forge mouth — CoC's oversized anvil is the same trick at 1.3× ([CoC](https://static.wikia.nocookie.net/clashofclans/images/e/e8/Blacksmith9.png)).
18. Build the **tool rack 1.9 m × 1.6 m with 6–8 tools at 0.35–0.45 m spacing**, dark heads on light hafts — never a solid black comb.
19. Set a **0.8 m ⌀ × 0.95 m quench barrel** next to the anvil with a flat desaturated-teal water disc 0.06 m below the rim — AoE2 uses exactly this bright trough as the forge color accent ([AoE2](https://static1.thegamerimages.com/wordpress/wp-content/uploads/2023/03/all-the-various-blacksmith-style-in-age-of-empires-2-definitive-edition.jpg)).
20. Put a **weapon rack 2.2 m × 1.25 m with 5–6 blades at 12–20°** at the yard's far edge — its serrated top is the only part visible from 45° and it survives at 96 px.
21. Cluster **7–9 props** on the pad: tall corners (weapon rack, tool rack), medium middle (anvil, grindstone), low centre (barrel, coal, ingots), with **0.3 m of clean background between silhouettes**.
22. Enforce a **0.4 m minimum dimension** on every prop (≈5 px at default zoom) and delete anything under **0.12 m** — a 6 cm nail is negative detail.
23. Budget **8–12% of visible building pixels for team color** as 4–6 discrete shapes — AoE2 reads faction from a 0.15 m fascia + one banner, WC3 spends 15–25% on roof and banners ([WC3](https://www.ludo.guide/guide/warcraft-iii-reforged/i-structures)).
24. Standardize **three swap plates**: swallowtail banner **0.55 × 1.5 m (1:2.7)**, heater shield **0.55 × 0.65 m**, and a **0.15 m tileable trim band** — all UV-free tinted quads.
25. Hang the banner with its **top at 4.2–4.6 m (60–75% of H)** and **0.25 m proud of the wall** so it sits above prop clutter and catches the key light.
26. Keep team color **off the roof and off anything under 0.4 m** — Nationfall measured that a thin sash disappears at play distance and moved to a large tinted plane at 0.7 saturation ([Nationfall](https://www.indiedb.com/games/nationfall/news/making-a-melee-readable-team-colour-shorter-spears-no-more-rings)).
27. Split every team color into **base + 0.7× shadow variant** and put the shadow on undersides and back faces so the tint survives flat shading without a darken map.
28. Hold **LOD0 ≤6,000 tris and LOD1 ≤2,600** (≈1,200 structure / 1,000 roof / 500 stack+hood / 400 canopy / 1,700 props / 200 plates), dropping sub-0.5 m props at LOD1.
29. Ship **2 materials and 0 textures** (flat color + emissive) and build detail as geometry, not atlas — the documented stylized-low-poly shortcut ([80.lv](https://80.lv/articles/tips-on-low-poly-game-environments), [80.lv](https://80.lv/articles/optimization-of-stylized-game-assets)).
30. Spend subdivision **only** on six curved hero forms, keep everything else **hard-edged at 1-segment 2–3 cm bevels, 8–12 segment cylinders, 3 draw calls, vertex AO 0.75×, emissive-only motion + one 24-tri smoke card** ([80.lv](https://80.lv/articles/stylized-production-tips-and-tricks)).

---

## 7. Reference ladder — what to steal from each

| Reference | Steal this | Don't steal |
|---|---|---|
| **AoE2 DE blacksmith** | annex-at-one-end + bright quench trough + team fascia band; the smoke plume as a readability cheat ([variants](https://static1.thegamerimages.com/wordpress/wp-content/uploads/2023/03/all-the-various-blacksmith-style-in-age-of-empires-2-definitive-edition.jpg)) | 2D-painted texture density |
| **Warcraft III / Reforged** | stone plinth → plaster wall → steep saturated roof three-step section; player color on roof + banner ([stats](https://classic.battle.net/war3/human/buildingstats.shtml)) | 15–25% team color (fights the glow) |
| **AoE4 blacksmith** | per-civ variation on one shared silhouette skeleton; strong emissive interiors ([building page](https://www.aoe4world.com/explorer/civs/hre/buildings/blacksmith)) | its texture/material budget |
| **Stronghold / Crusader** | tiny footprint, one chimney, one worker door — economy of means ([buildings](https://stronghold.heavengames.com/gameinfo/buildings/arms/)) | flat 2D elevation |
| **Northgard Forge** | the flared hood/stack as the entire identity; open front, single room ([Forge](https://cdn.mobygames.com/screenshots/18468911-northgard-windows-the-forge-can-upgrade-your-tools-and-weapons.jpg)) | monochrome palette |
| **Clash of Clans Blacksmith** | 1.3× hero prop (anvil) + 25% glowing mouth + squat crown ([Blacksmith](https://static.wikia.nocookie.net/clashofclans/images/e/e8/Blacksmith9.png)) | chunky 2-tone roof for a serious RTS |
| **They Are Billions** | production buildings read by roof color + a single yard prop ([building list](https://www.gamepressure.com/they-are-billions/list-of-buildings-statistics/zcaaee)) | top-down orthographic flattening |
| **0 A.D.** | historically grounded smithy: open colonnade + tiled lean-to + trough ([0 A.D. blacksmiths](https://www.indiedb.com/games/0-ad/images/alpha-14-preview-blacksmiths-and-islands-map)) | high-poly trim |
| **Anno 1800 / 1404** | stacked chimney groups and smoke columns as *industry* grammar; use 2–3 stacks only when the building is tier-3 | the density (too much for RTS zoom) |
| **Tropico** | deep arcaded shade under a heavy eave — reuse as the work arcade | pastel palette |
| **SpellForce 3 / Settlers** | one exaggerated roof gesture + oversized props for silhouette | ornate roof cresting |
| **Dune: Spice Wars** | silhouette carried by value, not hue, so tint can be reserved for faction | its rock-toned palette |

---

## 8. Applied fixes to `blacksmith_v6` (highest value first)

1. **Remove the two gold crosses + the 8-spike ridge row** → replace with one iron ridge strap and a single anvil-or-tongs crest at 0.5 m. This alone stops the chapel read.
2. **Raise the stack**: currently it terminates *below* the ridge. Take the crown to **1.18 × ridge**, widen the shaft to 1.0 m, add a flared cap + 4 louvers.
3. **Add the forge hood** over the existing fire pit — battered pyramid 1.8 × 1.4 m → 0.7 m throat at 2.6 m, with a masonry collar at the roof.
4. **Add the missing 4 props** in the empty right-front quarter: anvil+stump (1.05 m), tool rack (1.9 m), quench barrel (0.8 ⌀), weapon rack (2.2 m). The yard is currently 60% empty and half the props are log piles, which read "lumber mill".
5. **Deepen the lean-to**: it currently projects ~1.2 m; take it to **1.8–2.0 m** with a 0.30 m fascia and asymmetric rafters, and shift it **0.7 m** off the main ridge axis.
6. **Rebalance team color** from the two large shields (≈4–7%) toward the 8–12% kit: keep one shield, add the 0.15 m eave band + one 0.55 × 1.5 m swallowtail banner at 4.4 m.

---

## 9. Definition of done

- Silhouette test at **96 px, flat black**: 3 of 4 cues present, named correctly by 3/3 viewers.
- **Team color 8–12%** of building-body pixels (measured, not eyeballed); no team-color element < 0.4 m.
- **≤6,000 tris, 2 materials, 0 textures, 3 draw calls**, no feature < 0.12 m.
- Camera-correct check at **35° and 45°** pitch: the forge mouth and the stack cap both remain visible; no prop is fully occluded by the lean-to.

---

### Sources & limits
Fetched and inspected directly: AoE2 DE blacksmith variant sheet, AoE2 3×3 footprint ([biligame](https://wiki.biligame.com/aoe2de/%E9%93%81%E5%8C%A0%E9%93%BA)), WC3 Reforged base screenshot + [building stats](https://classic.battle.net/war3/human/buildingstats.shtml) / [structure guide](https://www.ludo.guide/guide/warcraft-iii-reforged/i-structures), Northgard Forge screenshot, CoC Blacksmith render, the project's own `blacksmith_v6` render (blue coverage measured at 4.3% of non-background pixels), plus the three 80.lv production articles. AoE4, Stronghold, TAB and 0 A.D. were cited from their pages, not from pixel inspection. Anno, Tropico, SpellForce, Settlers and Dune are from general knowledge — treat those four table rows as direction, not measurement.
