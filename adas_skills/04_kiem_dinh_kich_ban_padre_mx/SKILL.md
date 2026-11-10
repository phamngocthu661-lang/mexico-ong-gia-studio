---
name: padre-mx-independent-qa
version: 4.0.0
description: "PADRE MX two-stage exhaustive QA owner: Round 1 forensic logic, Round 2 complete storytelling quality, plus mechanical final verification; separate writer performs at most two authorized targeted repairs. No issue count limit."
---
# PADRE MX — FORENSIC QA ROUND 1 + FULL QUALITY QA ROUND 2

Read `references/CROSS_SKILL_QUALITY_CONTRACT.md`, `references/MEXICO_CHANNEL_DNA.md`, `references/QA_SCOPE_AND_FORMS_V4.md`, actual exact 7-Part source, locked title, outline and canon. **QA never edits manuscript prose.** Operate only the requested stage. No old V1 frozen QA reused.

## STEP4 / AUDIT ROUND 1: find all detectable LOGIC faults
Read the **complete manuscript**, not a partial summary. Track every Part, scene and cross-Part boundary with overlapping 6k–10k character windows; run reader pass + adversarial causal pass + dialogue/action pass. Create unlimited, individually identified **confirmed** and **suspected** findings; don't stop at 10 or 100. Determine severity P0/P1/P2/P3, exact location/quote, root cause, story consequence, acceptance tests, all affected downstream scenes. Do not treat intentional character misunderstanding as author error.

Required forensic matrix:
1. **Speech turn graph** — who speaks/responds, missing question/answer, self-response, pronoun referents, what listener knows, interrupted dialogue, text stitching omissions.
2. **Physical action graph** — object appears before introduction, unopened note is read, a character sets down a fork during unrelated moving-box sequence, props teleport, entrances/exits, who physically holds a document, impossible movement.
3. **Scene location matrix** — whose house, where each participant stands, room-to-room/time shifts, missing transitions and scene cuts.
4. **Chronology + ages + money** — exact dated sequences, birth/pregnancy flashbacks, repayment/contract signing, contradiction across distant Parts.
5. **Knowledge matrix** — facts each person knows, when learned, source/authorization, contradictory memory, narrative POV leakage.
6. **Causality and motivation** — goal, cause, decision, consequence, emotional change; convenience-only outcomes and missing causal bridge.
7. **Evidence lifecycle** — creation, ownership, authorized access, discovery, reading, authenticity, meaning, legal evidentiary limit, resulting action, payoff or deliberate ambiguity.
8. **Mexican reality** — no impossible unilateral bank freeze, ownership seizure, notarization, hospital release, undocumented rights, unsupported Mexican-law certainty.
9. **Setup/payoff** — note, anonymous debt sheet, mysteriously introduced object, clue and callback must have believable impact.
10. **Adversarial backward read** — compare ending to opening, any retcon of character/evidence/timing; identify potentially missing lines introduced by text stitching.

First mark each suspected inconsistency; investigate its source and classify CONFIRMED vs SUSPECTED. Report every one, do not guess repair from inadequate evidence. P0/P1 must not be hidden behind a high score.

### Round 1 mandatory outputs
`ROUND1_LOGIC_AUDIT.md`, `ROUND1_LOGIC_ISSUES.json`, `SCENE_CONTINUITY_MAP.md`, `TIMELINE_AND_KNOWLEDGE_MAP.md`, `AUDIT_R1_FROZEN.json`. Source `ROUND1_LOGIC_ISSUES.json` can be the freeze tool's reviewer JSON; it must include all discovered findings, evidence_per_part and coverage. Full issue ledger *cannot* be replaced by a synopsis.

Run:
```
python scripts/pmx_v4_pipeline.py audit --round 1 --script FULL_SCRIPT.txt --title "LOCKED_TITLE" --outline-file FINAL_OUTLINE.txt --review ROUND1_LOGIC_ISSUES.json --out AUDIT_R1_FROZEN.json
```
If confirmed issues exist, set precise UTF-8 half-open windows in `REPAIR1_ZONES.json` then:
```
python scripts/pmx_v4_pipeline.py contract --round 1 --script FULL_SCRIPT.txt --audit AUDIT_R1_FROZEN.json --zones REPAIR1_ZONES.json --out REPAIR1_CONTRACT.json
```
Every confirmed issue must have authorized zone(s). Each zone contains its exact source anchor and cannot touch `[PART N]` headings. Protected PASS quotes cannot be changed. The editing actor is STEP5 Writer.

## STEP4 / AUDIT ROUND 2: independent full quality re-read
Open EXACT `SCRIPT_REVISED_R1.txt` and `REPAIR1_PROOF.json` when first repair happened. If Round1 had zero confirmed findings, review the untouched script as round2 and omit proof. Cover **all seven Parts in full again**. Audit BOTH remaining/regression logic and all quality dimensions:
- Hook first 30 seconds, specific injury, credible curiosity, promised title outcome.
- Scene necessity, character agency, plot progression, escalating stakes, midpoint and irreversible choice.
- Pacing, retention valleys, repetitive reflection, long irrelevant meals/errands, unnecessary false endings.
- Dialogue rhythm, speaker-specific voice, es-MX idiom, TTS pronoun/transition clarity, grammar and accents.
- Character motivations, earned forgiveness, proportional reaction, grounded evidence, real rights/agency.
- Twist/setup/payoff, no magic documents, revelation after causal setup, final emotional landing.
- Cross-Part continuity and all Round1 findings independently rechecked, INCLUDING sections unchanged during repair.

Mark **PASS** passages with exact `pass_spans` quotes; **NEEDS_IMPROVEMENT** and **FAIL** appear in `issues` with exact anchor and acceptance tests; **BLOCKED** is not falsely declared fixed. Do not author style-only replacement unless specific viewer-impact quality flaw exists. Do not edit a PASS zone merely because alternative prose might sound prettier. No issue cap.

Run:
```
python scripts/pmx_v4_pipeline.py audit --round 2 --script SCRIPT_REVISED_R1.txt --title "LOCKED_TITLE" --outline-file FINAL_OUTLINE.txt --review ROUND2_QUALITY_ISSUES.json --previous-audit AUDIT_R1_FROZEN.json --previous-proof REPAIR1_PROOF.json --out AUDIT_R2_FROZEN.json
python scripts/pmx_v4_pipeline.py contract --round 2 --script SCRIPT_REVISED_R1.txt --audit AUDIT_R2_FROZEN.json --zones REPAIR2_ZONES.json --out REPAIR2_CONTRACT.json
```
Omit `--previous-proof` and skip a repair contract only when the corresponding confirmed-issue list was empty. `REPAIR2_ZONES.json` must only target confirmed Round2 deficits; PASS spans are frozen, except tightly justified causal dependency overrides with documented reason.

## FINAL VERIFY after STEP5 REPAIR2 (NOT ROUND 3)
Check the exact final file and editorially attest that Round2 issues were resolved. No third repair permission. `FINAL_VERIFY_REVIEW.json` must include `final_verification:true`, `score`, `integrity_checked:true`, complete `remaining_issues:[]`, `new_issues:[]`, `resolved_issue_ids:[...]` and any documented PASS dependency overrides. If there are remaining/new issues, list ALL; result becomes `NOT_PUBLISH_READY` and must not proceed to SEO.
```
python scripts/pmx_v4_pipeline.py final --script SCRIPT_FINAL_R2.txt --title "LOCKED_TITLE" --outline-file FINAL_OUTLINE.txt --round1-audit AUDIT_R1_FROZEN.json --round1-proof REPAIR1_PROOF.json --round2-audit AUDIT_R2_FROZEN.json --round2-proof REPAIR2_PROOF.json --review FINAL_VERIFY_REVIEW.json --out QA_FINAL_V4.json
```
If REPAIR1/REPAIR2 was skipped, omit its proof argument and use the appropriate last audited source; still perform final verification. `PASS_PUBLISH_READY` needs 95+/100, exact identity, no remaining/new issues, passed length/structure, preserved passed passages and independent human/editorial evidence. Script verifies source integrity, not semantic truth. Writer never asserts publish READY.

## Absolute prohibits
No cap on issue discovery; no unverifiable source quotes; no elided middle Parts; no weak proofreading-only QA; no large indiscriminate creative rewrites; no repair within QA; no hypothetical third edit; no `READY` from score alone. When context limits block a complete seven-Part read, mark AUDIT_INCOMPLETE and continue same round without inventing coverage.


## V4 STEP4 — Deterministic audit-range attestation (required for BOTH rounds)
First generate true range plan from exact current 70–80k source:
```
python scripts/pmx_v4_pipeline.py range-plan --script CURRENT_SOURCE.txt --out RANGE_PLAN_R1.json
```
For Round2, regenerate from repaired source into `RANGE_PLAN_R2.json`. Plans are SHA-locked per source. Each audit review must include `range_evidence` of the same length as windows, one record per expected ID and `window_sha256` copied from this plan plus a **>=18-character exact quote located inside its specific byte window**, >=3 distinct `checks` categories and a >=18-character `reviewer_note`. Set coverage counts to actual number of windows, never guess. Auditor must independently read the full source; generated windows alone do NOT constitute reading. Do not create fictitious or formulaic notes.
Supply `--blueprint STORY_BLUEPRINT_V4.json` to BOTH audit invocations and FINAL VERIFY. Round2 PASS spans require `part` (1–7), a unique ID and exact source quote. V4 final gate checks authorized dependency overrides and correct PASS preservation count. `AUDIT_REVIEW_V4_SCHEMA.json` is an example, never copy its fake evidence into an audit. Legacy V3 frozen review files are invalid for V4.
