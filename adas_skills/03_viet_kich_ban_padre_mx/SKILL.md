---
name: padre-mx-script-writer
version: 3.0.0
description: "PADRE MX STEP3 full seven-Part es-MX draft in A/B/C with 70k–80k verified characters; STEP5 executes maximum two QA-authorized source-anchored targeted repairs (R1 logic, R2 holistic), protecting all passed prose."
---
# PADRE MX — 3-STAGE SCRIPT WRITER + TWO CONTROLLED REPAIRS

Read `references/CROSS_SKILL_QUALITY_CONTRACT.md`, `references/MEXICO_CHANNEL_DNA.md`, `references/DRAFT_AND_DUAL_REPAIR.md`. The current user command determines DRAFT or REPAIR. Do not run them both unless explicitly requested in a full authorized pipeline. First person older Mexican father, fluent es-MX, literary but natural narration and TTS-ready dialogue; realism and causal actions before generic moral exposition.

## STEP3 DRAFT A/B/C — unchanged hard length contract
- Stage A: `[PART 1]` and `[PART 2]`, 20,000–24,000 Unicode body characters; opening concrete family injustice + irrevocable stake. Save real `PMX_<title_sha12>_SCRIPT_A.txt`.
- Stage B: `[PART 3]`–`[PART 5]`, 30,000–35,000; consequences and documentary evidence with real access, motivation, new dilemmas. Reopen persisted A and outline, check scene boundaries. Save B.
- Stage C: `[PART 6]`–`[PART 7]`, 20,000–25,000; consequence, earned reveal and closing action. Reopen A/B; save C; assemble exact A+B+C.
- **Total 70,000–80,000 Unicode codepoints after removing only heading lines**, and every one of seven Parts >=8,500. Count persisted UTF-8, not tokens or model guesses. No padding by repetitive thoughts; no half-length completion. If incomplete report `DRAFT_INCOMPLETE` and continue the *same* stage using last persisted paragraph, not regenerate from chat memory.
- Original `segment_workflow.py` and `verify_full_script.py` remain included and enforce counts and hashes.
```
python scripts/segment_workflow.py stage --title "CURRENT_FINAL_TITLE" --directory OUTPUT_DIR --outline-file CURRENT_FINAL_OUTLINE.txt --segment A --file OUTPUT_DIR/PMX_<sha12>_SCRIPT_A.txt
python scripts/segment_workflow.py stage --title "CURRENT_FINAL_TITLE" --directory OUTPUT_DIR --outline-file CURRENT_FINAL_OUTLINE.txt --segment B --file OUTPUT_DIR/PMX_<sha12>_SCRIPT_B.txt
python scripts/segment_workflow.py stage --title "CURRENT_FINAL_TITLE" --directory OUTPUT_DIR --outline-file CURRENT_FINAL_OUTLINE.txt --segment C --file OUTPUT_DIR/PMX_<sha12>_SCRIPT_C.txt
python scripts/segment_workflow.py assemble --title "CURRENT_FINAL_TITLE" --directory OUTPUT_DIR --outline-file CURRENT_FINAL_OUTLINE.txt
python scripts/verify_full_script.py OUTPUT_DIR/PMX_<sha12>_FULL_SCRIPT.txt
```

### Drafting preventive continuity check
Before every Part update character age and knowledge matrix, date of each flashback, actual location, object hands/owners, who signed a document, and how other characters first heard a secret. Check Part boundaries with overlapping context. Every Part needs meaningful action; avoid fabricated Mexico court/notary/bank powers. Preserve LOCKED_TITLE, approved 7-Part outline, es-MX not es-ES.

## STEP5 REPAIR 1 — ALL CONFIRMED LOGIC ISSUES, ONE BATCH
Only start if user authorized STEP5 REPAIR1 and auditor produced `AUDIT_R1_FROZEN.json` + `REPAIR1_CONTRACT.json` bound to exact baseline script. Read **all** reported issues, root causes, affected scenes and source-anchored windows. There is no arbitrary limit to number of fixes: 3, 30 or 300 confirmed issues are all to be addressed in one planned batch.

Fix conversation turns, missing intermediary action, object provenance, time/space continuity, evidence rights, contradicting ages/money, motivative and causality breakdowns. Fix ROOT CAUSE and dependent paragraphs; do not change good material, do not invent new story canon. If an issue is blocked without source, explicitly report BLOCKED, do not pretend solved. Write `REPAIR1_REPLACEMENTS.json`, one zone entry per contract, plus a full `REPAIR1_CHANGELOG.md` mapping ID → exact replacement and downstream tests.
```
python scripts/pmx_v3_pipeline.py repair --round 1 --script FULL_SCRIPT.txt --audit AUDIT_R1_FROZEN.json --contract REPAIR1_CONTRACT.json --replacements REPAIR1_REPLACEMENTS.json --title "LOCKED_TITLE" --outline-file FINAL_OUTLINE.txt --user-approved --out SCRIPT_REVISED_R1.txt --proof REPAIR1_PROOF.json
```
The tool verifies heading/length, SHA, exact untouched bytes, exact zones, and an on-disk one-use repair lock. It does **not** validate literary repairs; independent STEP4 ROUND2 must review the entire revised source.

## STEP5 REPAIR 2 — SELECTIVE QUALITY + REMAINING LOGIC
Only after independently frozen `AUDIT_R2_FROZEN.json` and `REPAIR2_CONTRACT.json`, on the **exact** Round2 script. Read 100% Round2 confirmed FAIL/NEEDS_IMPROVEMENT findings. Prioritize new/residual logical errors, then hook, structural weakness, pacing/retention, credible emotion, twist/payoff, natural dialogue, es-MX language/TTS, reasonable length fixes. Every change needs a verified deficiency and acceptance test.

**PASS ZONE FREEZE:** Keep passages marked PASS absolutely unchanged unless strictly necessary to repair a causally dependent confirmed issue. In exceptional cases auditor must provide `pass_dependency_override_ids` and >=35-character reason in zone spec, then writer must document why no smaller edit resolves the issue. The automated contract prevents all other intersections with protected PASS quotes. No subjective rewrite of strong prose; no replacing entire Parts when a narrow fix suffices; no delete-to-hide-error or padding.
```
python scripts/pmx_v3_pipeline.py repair --round 2 --script SCRIPT_REVISED_R1.txt --audit AUDIT_R2_FROZEN.json --contract REPAIR2_CONTRACT.json --replacements REPAIR2_REPLACEMENTS.json --title "LOCKED_TITLE" --outline-file FINAL_OUTLINE.txt --user-approved --out SCRIPT_FINAL_R2.txt --proof REPAIR2_PROOF.json
```
After real REPAIR2, stop edits. Recommend QA FINAL VERIFY, not another rewrite. If no confirmed issue in either audit, skip that repair permanently: unused allowance cannot be spent later as REPAIR3. Do not overwrite any baseline, frozen review, proof, or output.

## Non-negotiable editorial principles
Preserve unbroken story voice and locked facts, exact key title promise, strong scene lines, foreshadowing and payoffs. For each changed zone check previous two and next two scenes, character knowledge, timestamps, grammar agreement, and real social/legal permissions. Compute counts on actual files. Writer cannot self-issue quality scores or PASS_PUBLISH_READY. If tooling unavailable, do not claim a verified file exists. No legacy ONE_REPAIR scripts or V1 SHA proofs accepted.
