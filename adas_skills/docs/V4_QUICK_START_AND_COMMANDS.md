# PADRE MX V4.0 — QUICK START / CLI CHEAT SHEET

## Installation
1. Extract the OUTER ZIP `PADRE_MX_5_SKILLS_V4_0_UPGRADED.zip`.
2. Install five individual files under `01_INSTALL_5_SKILLS/` as five separate skills. Each inner archive contains exactly one `SKILL.md` skill folder and related scripts/references.
3. Put `02_CONTROLLER_AND_GUIDES/PADRE_MX_PROJECT_INSTRUCTIONS_COPY_PASTE.md` in your project instructions, and read `PADRE_MX_STEP_CONTROLLER_V4.md`.
4. Work in a per-video project directory. Copy `PROJECT_MEMORY_V4_EMPTY.json` as `PADRE_MX_PROJECT_MEMORY_V4.json` **once** for a new channel/key; keep it outside disposable chat workspaces and back it up. This file is a list of approved *local* productions, NOT a channel audit or market-research data source.
5. Scripts use Python 3.10+; `Pillow` and `numpy` required for pixel-level thumbnail QA. No paid API, YouTube search or vidIQ connector required by V4.

## STEP 1 local title originality (optional memory in first session)

Example candidate JSON:
```json
{"title":"Mi hijo quiso vender mi casa, pero yo tenía las llaves",
 "originality_signature":{
  "central_injustice":"Mi hijo intenta vender un patrimonio sin permiso",
  "leverage":"El padre es el único propietario legal vigente",
  "evidence_mechanism":"Escritura legítima de dominio y testimonio presencial",
  "antagonist_cost":"El hijo pierde confianza y una ayuda voluntaria",
  "earned_payoff":"El padre ejerce un límite y protege su hogar"}}
```

```bash
python scripts/padre_v4_planning.py dedup --candidate CANDIDATE.json --memory PADRE_MX_PROJECT_MEMORY_V4.json --corpus references/CHANNEL_CORPUS_71.json
```
`BLOCK`: exact title or declared local signature conflict. `REVIEW`: strong lexical or partial mechanism similarity. `NO_HIGH_SIMILARITY_FOUND`: not a guarantee of novelty.

## STEP 2 Story Blueprint
Use `references/STORY_BLUEPRINT_V4_TEMPLATE.json`, replace *every* placeholder with story-specific content. Treat 8–12 scenes/Part as a planning preflight, not a license to pad narrative.

```bash
python scripts/padre_v4_planning.py blueprint --blueprint STORY_BLUEPRINT_V4.json --title "LOCKED_TITLE" --outline CURRENT_FINAL_OUTLINE.txt --memory PADRE_MX_PROJECT_MEMORY_V4.json
```

## STEP 3 Continuity Ledger (on writer skill)
```bash
python scripts/padre_v4_ledger.py create --blueprint STORY_BLUEPRINT_V4.json --outline CURRENT_FINAL_OUTLINE.txt --out LEDGER_INIT.json
python scripts/padre_v4_ledger.py checkpoint --ledger LEDGER_INIT.json --segment STAGE_A.txt --stage A --report LEDGER_A_REPORT.json --out LEDGER_A.json
python scripts/padre_v4_ledger.py checkpoint --ledger LEDGER_A.json --segment STAGE_B.txt --stage B --report LEDGER_B_REPORT.json --out LEDGER_B.json
python scripts/padre_v4_ledger.py checkpoint --ledger LEDGER_B.json --segment STAGE_C.txt --stage C --report LEDGER_C_REPORT.json --out LEDGER_C.json
```
Each report has one part_update for every Part in its stage. Fields: `part`, `source_quote` (verbatim), `continuity_bridge`, `new_value`, `character_change`, `knowledge_delta` (array), `evidence_delta` (array), `open_loops` (array), `closed_loops` (array). Loops may be explicitly justified as intentionally open at C; otherwise must be closed. This ledger cannot independently tell whether a claimed fact is true.

## STEP 4 audit source windows (QA skill, every round)
```bash
python scripts/pmx_v4_pipeline.py range-plan --script SOURCE_EXACT.txt --out RANGE_PLAN_R1.json
```
Reviewer must genuinely inspect every window. `ROUND1_REVIEW.json` must include `range_evidence` for every expected window: `id`, `window_sha256` from plan, `quote` inside that window (>=18 chars), `checks` >=3 distinct dimensions, and `reviewer_note` >=18 chars. `coverage.total_ranges` and `reviewed_ranges` must match real plan. Same process for Round2 on the freshly repaired source. The tool checks exact quotes, not semantic reasoning.

```bash
python scripts/pmx_v4_pipeline.py audit --round 1 --script FULL_SCRIPT.txt --title "LOCKED_TITLE" --outline-file CURRENT_FINAL_OUTLINE.txt --blueprint STORY_BLUEPRINT_V4.json --review ROUND1_REVIEW.json --out AUDIT_R1_FROZEN.json
python scripts/pmx_v4_pipeline.py contract --round 1 --script FULL_SCRIPT.txt --audit AUDIT_R1_FROZEN.json --zones REPAIR1_ZONES.json --out REPAIR1_CONTRACT.json
```
Only create a contract if R1 actually has CONFIRMED issues. SUSPICIOUS issues are NOT automatically confirmed.

## STEP 5 Repair 1 (writer skill)
```bash
python scripts/pmx_v4_pipeline.py repair --round 1 --script FULL_SCRIPT.txt --title "LOCKED_TITLE" --outline-file CURRENT_FINAL_OUTLINE.txt --blueprint STORY_BLUEPRINT_V4.json --audit AUDIT_R1_FROZEN.json --contract REPAIR1_CONTRACT.json --replacements REPAIR1_REPLACEMENTS.json --user-approved --out SCRIPT_REVISED_R1.txt --proof REPAIR1_PROOF.json
```
`--user-approved` is a tool assertion, not proof of user identity. Run only with user authorization for the requested workflow.

## STEP 4 Audit 2 / STEP 5 Repair 2
```bash
python scripts/pmx_v4_pipeline.py range-plan --script SCRIPT_REVISED_R1.txt --out RANGE_PLAN_R2.json
python scripts/pmx_v4_pipeline.py audit --round 2 --script SCRIPT_REVISED_R1.txt --title "LOCKED_TITLE" --outline-file CURRENT_FINAL_OUTLINE.txt --blueprint STORY_BLUEPRINT_V4.json --review ROUND2_REVIEW.json --previous-audit AUDIT_R1_FROZEN.json --previous-proof REPAIR1_PROOF.json --out AUDIT_R2_FROZEN.json
python scripts/pmx_v4_pipeline.py contract --round 2 --script SCRIPT_REVISED_R1.txt --audit AUDIT_R2_FROZEN.json --zones REPAIR2_ZONES.json --out REPAIR2_CONTRACT.json
python scripts/pmx_v4_pipeline.py repair --round 2 --script SCRIPT_REVISED_R1.txt --title "LOCKED_TITLE" --outline-file CURRENT_FINAL_OUTLINE.txt --blueprint STORY_BLUEPRINT_V4.json --audit AUDIT_R2_FROZEN.json --contract REPAIR2_CONTRACT.json --replacements REPAIR2_REPLACEMENTS.json --user-approved --out SCRIPT_FINAL_R2.txt --proof REPAIR2_PROOF.json
```
If Repair 1 was genuinely skipped, omit `--previous-proof` and review unchanged original source; if Repair 2 skipped, use the last audited script as final. Never create fake empty repair contracts or third patch.

## FINAL VERIFY / SEO
```bash
python scripts/pmx_v4_pipeline.py final --script SCRIPT_FINAL_R2.txt --title "LOCKED_TITLE" --outline-file CURRENT_FINAL_OUTLINE.txt --blueprint STORY_BLUEPRINT_V4.json --round1-audit AUDIT_R1_FROZEN.json --round1-proof REPAIR1_PROOF.json --round2-audit AUDIT_R2_FROZEN.json --round2-proof REPAIR2_PROOF.json --review FINAL_VERIFY_REVIEW.json --out QA_FINAL_V4.json
python scripts/verify_seo_ready.py --script SCRIPT_FINAL_R2.txt --qa-frozen QA_FINAL_V4.json --outline-file CURRENT_FINAL_OUTLINE.txt --title "LOCKED_TITLE" --blueprint STORY_BLUEPRINT_V4.json --round2-proof REPAIR2_PROOF.json
python scripts/validate_thumbnail_pair.py --thumbnail THUMBNAIL.png --green THUMBNAIL-NENXANH.png
```
Omit missing proof CLI flags for genuinely skipped repair rounds. Verify both actual PNG files and independently inspect content. If QA fails, stop — no repair #3 or SEO READY.

## Archive & Memory update (only after actual V4 QA PASS)
```bash
python scripts/padre_v4_planning.py register --blueprint STORY_BLUEPRINT_V4.json --qa QA_FINAL_V4.json --script SCRIPT_FINAL_R2.txt --outline CURRENT_FINAL_OUTLINE.txt --memory PADRE_MX_PROJECT_MEMORY_V4.json
```
This updates only the local approved-project registry; do not change a V3 memory or invent completed video records. Back up the registry file; no remote sync occurs in this version.
