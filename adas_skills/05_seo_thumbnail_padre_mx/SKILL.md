---
name: padre-mx-seo-packaging
version: 3.0.0
description: "Step6 only. Verified es-MX SEO and exactly two matched 16:9 PNG deliverables: THUMBNAIL.png + THUMBNAIL-NENXANH.png with strict 80/20 layout: text-heavy left zone and main man on the right."
---
# PADRE MX — STEP6 SEO + TWO MATCHED THUMBNAIL IMAGES (80/20 FIXED LAYOUT)

Before Step6 read `references/CROSS_SKILL_QUALITY_CONTRACT.md`, `references/MEXICO_CHANNEL_DNA.md`, `references/SEO_THUMBNAIL_RULES.md`, the actual final script, QA_FINAL_V3.json (after TWO audit rounds) and locked outline. The canonical title is immutable. Do not create anything for a failed QA-ready preflight.

Run source/QA hash preflight:
```
python scripts/verify_seo_ready.py --script CURRENT_SCRIPT.txt --qa-frozen QA_FINAL_V3.json --outline-file CURRENT_FINAL_OUTLINE.txt --title "CURRENT_FINAL_TITLE" [--round2-proof REPAIR2_PROOF.json]
```
If no PASS, block rather than invent readiness. Step3 final script must contain 70k–80k true Unicode body characters. Do not modify manuscript at Step6.

## Metadata deliverable
1. Primary `CURRENT_FINAL_TITLE` exact es-MX <=100 codepoints, never relabel.
2. Exactly TWO supporting title options A/B, each <=100 codepoints; these are NOT thumbnail alternatives.
3. Concise vivid es-MX description and truthful hook based on real scenes.
4. Useful keywords, comma-separated tags with 450–500 chars including spaces/punctuation, optional separate hashtags.
5. Exactly ONE selected thumbnail concept (no 3 A/B/C images). Hook matches the title and a witnessed moment, does not reveal false outcome. Text in natural, correctly accented es-MX.
6. One 8–15 second trailer script based on existing beats.
7. `PROMISE_TO_SCENE_MAP`: >=3 verbatim quotes + matching Part numbers from actual approved script, and one `FACT_LOCK` table.
8. Persist `STEP6_SEO_PACKAGE.md` using **these exact two headings** and labels:
```
## Imagen THUMBNAIL
**Archivo:** THUMBNAIL.png
**Prompt THUMBNAIL 16:9:** ...

## Imagen THUMBNAIL-NENXANH
**Archivo:** THUMBNAIL-NENXANH.png
**Prompt THUMBNAIL-NENXANH 16:9:** ...
```
Then verify package:
```
python scripts/validate_seo_package.py --package STEP6_SEO_PACKAGE.md --script EXACT_QA_READY_SCRIPT.txt --title "CURRENT_FINAL_TITLE"
```
A prompt document is only metadata; it never counts as a completed rendered image.

## MANDATORY two-image production (same Step6)
**Produce exactly TWO FINAL image files, not three**. Render actual 16:9 RGB PNGs at equal resolution, preferably 1920x1080 (>=1280x720):
- `THUMBNAIL.png`: finished clickable Spanish thumbnail. Reference layout from `references/example_thumbnail.jpg`: **text-heavy left block occupying about 78–82% of the canvas width** and the **main man on the right occupying about 18–22%**. The left area must carry the dense multi-line Spanish headline, using bold uppercase typography with mixed black / cyan / orange emphasis on a clean white or very light background. Keep a warm red bottom banner and a strong yellow/orange kicker if needed, but never let the text block become narrow. The right side shows the believable photographic main man only, cropped vertically and aligned to the right edge. Original story-driven copy, NO source text copied.
- `THUMBNAIL-NENXANH.png`: generated directly from `THUMBNAIL.png` by isolating and drawing the COMPLETE upper-body portrait of the exact same older Mexican father (full head, hair, both ears, neck, and BOTH FULL SHOULDERS & CHEST without cutting off his shoulders, zero background trapped under the ears/neck, and 100% ZERO text/banners/documents) on EXACT flat chroma green RGB(0,255,0) / #00FF00. Same 16:9 pixel dimensions and **identical person, hairstyle, face, clothing, expression, crop, x/y placement, size, direction and lighting** as `THUMBNAIL.png`. Absolutely NO text, title, badge, icon, gradients, floor, texture, shadows, edge haze, green spill, green clothes or secondary people. Keep the **same 80/20 composition logic**: the man remains on the right occupying about 18–22% of the width, and the left about 78–82% stays uniformly pure green (see `references/example_green_screen.png`).

### Identity/position lock (within the same episode) & Mandatory Anti-Clone Diversity (across episodes)
1. **Cross-Episode Diversity & Randomization (NEVER draw the same old man or outfit twice)**:
   - Every video on the channel represents a **different family's story with a completely different elderly Mexican protagonist**.
   - **Strictly forbid** defaulting to the generic "silver-haired man with thick mustache in a brown plaid shirt".
   - Each episode MUST randomize and specify a distinct combination of:
     + **Face & Morphology**: vary between gaunt/angular, round/broad-cheeked, square-jawed, frail/slender, oval intellectual, rugged sun-weathered, indigenous-mestizo bronze, or fair-olive complexion (ages 62–82).
     + **Hair & Facial Hair**: rotate between **clean-shaven face (no mustache/beard)**, **full white beard**, **short goatee (candado)**, **bald crown with white sides**, **3-day gray stubble**, **curly silver hair**, **traditional straw sombrero / northern Texana hat**, or **flat wool beret/cap (boina)**.
     + **Eyewear**: rotate between thin gold-rimmed reading glasses, dark rectangular frames, half-rim bifocals, wire-frame round spectacles, or no glasses.
     + **Wardrobe / Clothing (strictly NO green `#00FF00` clothes)**: rotate across diverse outfits such as a navy quilted vest over a sky-blue shirt, charcoal wool cardigan with buttons, burgundy V-neck sweater over cream shirt, formal dark suit jacket with tie, camel suede jacket, deep indigo denim jacket, dark brown leather jacket, chocolate corduroy blazer, oatmeal turtleneck sweater, artisan navy work shirt, traditional earth-tone woven jorongo, or crisp white embroidered guayabera.
2. **Same-Episode Pair Lock (`THUMBNAIL.png` ↔ `THUMBNAIL-NENXANH.png`)**:
   - Build or isolate ONE realistic subject portrait cutout (transparent alpha layer internally) and use it for BOTH deliverables of the current episode. Place it on identical pixel coordinates. **Lock the composition to a text-left / man-right 80/20 split**. Final thumbnail: the left 78–82% is reserved for the text system and the right 18–22% contains the man. Greenscreen: keep the man on the exact same coordinates and replace the rest of the canvas with solid #00FF00. DO NOT independently regenerate a different man for the second image of the same episode; DO NOT crop/zoom/reposition for the second image. Avoid cutting hair, shoulders, hands. Do not include readable prop text.

### Required final QA
1. Run `python scripts/validate_thumbnail_pair.py --thumbnail THUMBNAIL.png --green THUMBNAIL-NENXANH.png`.
2. Visually inspect and affirm both actual files are 16:9, same resolution, matching subject pixels/position, right placement, clean keyable green, and final Spanish typography. The script only checks mechanical image properties, not subjective identity or copied visuals.
3. Report EXACT delivered paths, size, name and QA status. Explicitly confirm the **left text zone is ~80% and the man-right zone is ~20% in both images**. Output `STEP6_DONE` only after metadata/content QA + BOTH ACTUAL IMAGES passed. If image generation/compositing tools unavailable or paths not physically created, say `STEP6_METADATA_ONLY / IMAGES_NOT_RENDERED` without inventing files or claiming complete delivery.

## Hard locks
No false 'historia real', fake judicial seizure, fictional stock legal document, or text copied from example thumbnails. References demonstrate ONLY layout, palette and **80/20 right-side alignment**; cast and story visuals must be original. Exact FINAL V3 QA script SHA binding required. SEO never reopens either Step5 repair phase.

## V3 final publication gate (MANDATORY)
Accept ONLY `PADRE_MX_QA_FINAL_V3` with `PASS_PUBLISH_READY`, score >=95 and exact final script SHA. Both frozen audits are required; STEP5 repairs may be skipped only where findings had zero CONFIRMED items. If REPAIR2 was used, require its proof. Never accept legacy V1 `QA_FROZEN` or fake file hashes. Two real matched PNGs remain mandatory, with **strict 80/20 text-left / portrait-right** geometry.
