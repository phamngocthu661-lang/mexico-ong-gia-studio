# PADRE MX V3.0 — SHARED CROSS-SKILL CONTRACT (NORMATIVE)

## Identity and ownership
5 independent installable SKILLs control 6 production steps: Title STEP1, Outline STEP2, Writer STEP3 and STEP5, QA STEP4, SEO STEP6. Do not invoke unrequested operations or blend with other genre pipelines. Source of truth: this V3 contract, current controller and owning SKILL. V1.2 single-repair docs and old QA frozen artifacts are incompatible; never re-label them as V3 evidence.

| Command | Owner | Obligations |
|---|---|---|
| STEP1 | Title | Generate five original es-MX candidate titles, select immutable locked title <=100 Unicode codepoints. |
| STEP2 | Outline | 7 Parts, causality/evidence/character-knowledge canon, exact saved outline SHA. |
| STEP3 A/B/C | Writer | Three full source files, seven parts, verified 70k–80k Unicode-body-character manuscript. No self-scored QA. |
| STEP4 ROUND1 | QA | **100% forensic logic audit**, unbounded confirmed/suspected issue inventory, scene and cross-Part continuity, frozen source/evidence. Do not edit prose. |
| STEP5 REPAIR1 | Writer | Fix **all confirmed logic issues** in one deterministic authorized batch; preserve everything else. |
| STEP4 ROUND2 | QA | **100% holistic audit** of first revised script: verify logic regressions, hook, plot, retention, voice, tension, character agency, emotional payoff, spelling, grammar, TTS, reality, length. Label zones PASS / NEEDS_IMPROVEMENT / FAIL / BLOCKED, freeze passed quotations. |
| STEP5 REPAIR2 | Writer | Fix **all verified FAIL and NEEDS_IMPROVEMENT** items, including any remaining/new logic flaws, while leaving PASS spans byte-exact wherever possible. |
| FINAL VERIFY | QA | After repair2, verify lineage, coverage outcomes, exact final file integrity, protected PASS spans, no P0/P1, and publish verdict. Not a third audit/repair. |
| STEP6 | SEO | Only exact V3 FINAL PASS; create metadata and exactly two rendered 16:9 PNGs. |

## Fixed hard gates
- `CURRENT_FINAL_TITLE` exact es-MX text <=100 Unicode codepoints; `title_sha12 = sha256(title UTF-8)[:12]`.
- `CURRENT_FINAL_OUTLINE` exact LF UTF-8 7-Part canon file; `outline_sha256 = sha256(bytes)`.
- `video_id = sha256(title + "\n" + outline_sha256)[:16]`.
- Seven **standalone** `[PART 1]`…`[PART 7]` headings; UTF-8 LF, no BOM.
- Body count: Unicode codepoints, after removing only standalone heading lines and their newline: **70,000–80,000 inclusive**, every Part **>=8,500**. Draft stage A (Parts1–2) 20,000–24,000; B (Parts3–5) 30,000–35,000; C (Parts6–7) 20,000–25,000. Use actual persisted files, not approximate response tokens. Never call a half-length output PASS.
- LOCKED_TITLE, scene facts, real rights/knowledge, major proof chain, and story identity must be preserved across stages.

## Two audits, two repairs — absolutely maximum
**ROUND1:** logic only. Examine all dialogue turns, abandoned questions, self-answers, scene entrances/exits, location shifts, temporal sequence, knowledge transfer, motive, causal transitions, evidence provenance, financial/ownership/legal mechanics and setup/payoff. Do not stop after a quota of errors; do not invent suspicion as confirmed fault.
**REPAIR1:** every CONFIRMED issue recorded in locked Round1 inventory should receive a source-anchored fix. Multiple edit windows in one batch are one repair. Nonfixable errors must be reported BLOCKED, not hidden.
**ROUND2:** read **100% again** and independently assess the story's complete listener experience and regression from Repair1. All P0/P1 flaws and actionable quality deficits go in the new issue ledger, not merely general advice. Register concrete PASS zones for preservation; repair only deficient sections. A strong scene is not edited for stylistic preference.
**REPAIR2:** source-anchored, selective, minimally sufficient content changes for confirmed Round2 issues; may fix outstanding logic plus quality. No unauthorized Part rewrite, silent retcon, filler, deletion, or PASS-zone rewriting. A justified dependent PASS override requires a causal explanation >=35 characters and is recorded.
**FINAL VERIFY:** checks exact hashes, two audit/repair chain, regression, score, all confirmed Round2 items resolved, PASS-zone preservation, and structural length. No third repair. Failure => `NOT_PUBLISH_READY`, with unbounded remaining/new issues. Never falsify PASS.
If an audit finds no confirmed issues, corresponding repair may be SKIPPED; skipping never creates a spare repair credit. Each video may have **0–2** actual repairs only, in order.

## Reviewer evidence and categories
Every audit: inspect each of seven parts and all byte ranges; record coverage `total_ranges`, `reviewed_ranges`, `unread_ranges=[]`, `reviewed_parts=[1..7]`, >=18-char verbatim evidence quote in each Part, unlimited issue ledger including category, P0..P3, specific anchor, why and acceptance tests. Also maintain scene map, timeline, knowledge matrix, object ledger, protected PASS spans, spans influenced by patches. Three reader passes at minimum: natural story reading; adversarial continuity/causality pass; language/precision pass. The automated tool verifies declared coverage and quotations, **not** actual cognitive completeness or legal truth.

## Round 2 100-point rubric and hard requirements
Logic causality 25; dialogue/continuity 15; character/knowledge/motivation 15; story hook/architecture/retention 15; twist/payoff 10; emotional authenticity 10; es-MX/TTS 5; ending 5. Target score >=95 with ZERO confirmed P0/P1, zero unresolved actionable issues and exact file/provenance PASS. An average score cannot excuse a logic contradiction.

## Files and provenance (V3 only)
Auditor + writer each ship `scripts/pmx_v3_pipeline.py` for self-contained command-line validation. Strict original-to-repaired SHA and UTF-8 half-open byte ranges, heading protection, on-disk no-overwrite, immutable untouched bytes and `REPAIR_1_LOCK`/`REPAIR_2_LOCK`. Reviewer must use actual script anchors, not memorized paraphrases; `--user-approved` is only an assertion, not cryptographic identity verification.

Main artifacts: `AUDIT_R1_FROZEN.json`, `REPAIR1_CONTRACT.json`, `SCRIPT_REVISED_R1.txt`, `REPAIR1_PROOF.json`, `AUDIT_R2_FROZEN.json`, `REPAIR2_CONTRACT.json`, `SCRIPT_FINAL_R2.txt`, `REPAIR2_PROOF.json`, `QA_FINAL_V3.json`. Audit/repair commands are in the owning SKILL and examples.

## Mexico voice, narrative ethics and truth
Fictional first-person older Mexican father, es-MX for adult Mexican audience. Events follow earned causal evidence, humane consequences, no legal or medical shortcuts, no crime-as-instruction. Verify niche legal specifics with reliable sources before making firm claims. Source samples provide structural cues only; do not copy names, lines or specific plots. Do not represent fiction as independently verified true history.

## SEO truth and 80/20 assets
STEP6 requires `PADRE_MX_QA_FINAL_V3` status `PASS_PUBLISH_READY` with exact hash of the published source, score >=95 and lineage to both frozen audits, plus proof of the final repair if used. No SEO claims from an unapproved draft. EXACTLY two final RGB 16:9 PNGs `THUMBNAIL.png` and `THUMBNAIL-NENXANH.png`, same identical subject cutout, same pixel position. Final text occupies about 78–82% LEFT; male protagonist is 18–22% RIGHT. Green-screen file has uniform RGB(0,255,0) under the same right-side cutout. Deliver real files, not only prompts.

## Authority
Actual user command and explicit permissions > this shared contract > `PADRE_MX_STEP_CONTROLLER_V3.md` > owning SKILL > references. In conflicts, preserve hard gates and do not fabricate artifact state. Report unavailable tools/errors transparently. No blanket statement that software can prove literary quality.
