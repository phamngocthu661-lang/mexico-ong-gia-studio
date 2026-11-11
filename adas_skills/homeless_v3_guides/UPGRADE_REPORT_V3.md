# HOMELESS STORY 5 SKILLS V3.0 — TECHNICAL UPGRADE REPORT

## Source inventory
- `Viet-Tieu-De(1).zip`: viral-title-rewriter-v1.1 — source-title forensic, 60/40 conceptual DNA, 98+ title rubric, <=100 chars.
- `viet-gian-y-homeless(2).zip`: outline V2.3.1 — 5 DNA references, 7 PART, 8 clues, 2 reinterpreted, 4 reveals, early retention, canon/forensic handoff.
- `Viet-kich-ban-homeless-v1.6.9-THREE-STAGE-PERSIST(1).zip`: Writer V1.6.9 — hard 70k–80k, persisted stages A/B/C, SHA/count verifier.
- `kiem-tra-kich-ban-homeless-v1.8.1-CHECKPOINT(1).zip`: Auditor V1.8.1 — evidence-first checkpoint, rubric 100, 98 READY, frozen patch ledger.
- `seo-homeless(1).zip`: SEO V2.0 — title-locked metadata, thumbnail concept and multi-shot Omni prompts.

## V3 changes actually implemented
1. Cross-skill override in each SKILL.md plus shared invariant contract and setup documents. All original deep references retained.
2. `TITLE_CARD.json` / `STORY_BLUEPRINT.json` / `CONTINUITY_HANDOFF_A/B/C.json` / `REPAIR_PLAN.json` / `SEO_PACK.json` versioned JSON interfaces.
3. Controller `init`, `lock-title`, `lock-outline`, `stage`, `assemble`, `attach-qa`, `verify-patch`, `commit-patch`, `verify-seo`, `remember`, `status` with strict phase checks.
4. Same title SHA across stages; 100-char title gate, scores >=98 and <=100 (editorial assertion), original 7 PART and 70–80k proof preserved.
5. Actual SHA and UTF-8/LF checks; persistent writer source files and full-script readback; no falsely claimed finished file.
6. Cross-stage immutable facts and open/closed loop gate. C cannot finish with unresolved registered loops. Quotes must occur in stated parts.
7. Optional **shared local** memory with lexical similarity screening of title/premise/mechanism/payoff. GREEN is heuristic; UNKNOWN without a corpus. No internet channel research.
8. Frozen QA integrity bound to exact full manuscript; stale audit rejected after any byte change. Reviewer still responsible for real editorial inspection.
9. Authorized surgical repair using exact ticket+Part+anchor and versioned immutable baseline; unapproved diff rejected; on commit old QA invalidated.
10. SEO 170–280-word description, <=500-char tags, 16:9 thumbnail **prompt** grounded by script excerpt, 1–3 standalone 10-second Omni clips with >=2 script-grounded shots per clip, and fact-review declarations.

## Validation scope
Two self-contained automated integration suites: `tests/test_pipeline.py` (20 checks) and `tests/test_repair.py` (14 checks). All use synthetic 7-part manuscripts solely to test structural software behavior. Final ZIP archive and each standalone skill archive undergo ZIP CRC (`testzip`) and SHA256 manifest checks in the build process.

## Limitations
- Editorial scores are not computed by tools; program only checks declared ranges/lineage. Real screenplay logic, originality, character age motives, historical/legal process and true audience retention require independent review.
- Strict `REPAIR_PLAN` supports exact targeted text replacements; scene-wide re-planning needs a new approved outline/manuscript lineage, not unauthorized bulk patch.
- This package does not generate thumbnails or video. It validates prompts/metadata only; user must explicitly trigger rendering and QA the output visually.
- Original source versions are included as pristine fallback archives under `04_ORIGINAL_BACKUPS/`.

## Deliberately excluded
Channel Audit, current market research, mandatory vidIQ, external scraping or demand estimates.
