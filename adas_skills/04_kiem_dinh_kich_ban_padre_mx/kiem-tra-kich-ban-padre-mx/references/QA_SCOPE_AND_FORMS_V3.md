# PADRE MX V3 — Audit forms, scene analysis and two repair scopes

## Mandatory reviewer JSON for both rounds
Use `references/AUDIT_REVIEW_V3_SCHEMA.json` as a **structural** example, not pre-filled actual evidence. Never submit example anchors as observed facts. JSON keys: `audit_round` 1 or 2; `focus` `LOGIC` or `COMPREHENSIVE`; `score` 0–100; `coverage:{total_ranges,reviewed_ranges,unread_ranges:[],reviewed_parts:[1..7]}`; `evidence_per_part:{"1":"<actual >=18 chars>",..."7":"..."}`; `issues:[...]`; `pass_spans:[{id,text}]`; `chronology` optional metadata.

Every issue: `{id,severity:'P0|P1|P2|P3',category,part:1..7,anchor:'<exact Part quote >=18 chars>',problem:'<specific contradiction or quality weakness>',acceptance_tests:['<observable desired state>'],status:'CONFIRMED|SUSPECTED',root_cause:'...',affected_scenes:[...]}`. Record **all** independent positions, regardless of quantity. Avoid noisy false positives: misunderstandings/lie/flashback are not automatic continuity defects. Suspected issues need investigation; a suspected issue blocks final readiness until resolved/reclassified.

`ROUND1_LOGIC_ISSUES.json`: use only `LOGIC, CAUSALITY, DIALOGUE, TIMELINE, SPACE, MONEY, MOTIVATION, KNOWLEDGE, ACCESS, LEGAL, PHYSICAL, NAME, CONTINUITY, EVIDENCE, SETUP_PAYOFF` categories. Do not mix aesthetic improvements into logic repair. Four separate outputs recommended for traceability: issue ledger, scene map, event timeline, knowledge matrix.

`ROUND2_QUALITY_ISSUES.json`: categories above plus `HOOK, RETENTION, PACING, EMOTION, CHARACTER, STRUCTURE, TWIST, ENDING, ORTHOGRAPHY, GRAMMAR, PUNCTUATION, ES_MX, TTS, STYLE, LENGTH, REALISM, REPETITION`. Every actionable quality issue needs precise viewer impact, exact quote, acceptance tests and classification (FAIL or NEEDS_IMPROVEMENT). `pass_spans` protects good content. Retest any Round1 issue on revised text and search for newly caused contradictions.

## Zone specification and offsets
`REPAIR1_ZONES.json` / `REPAIR2_ZONES.json` schema:
```
{"zones":[{"zone_id":"Z001","start_byte":1234,"end_byte":1350,"issue_ids":["LG-001"]}]}
```
Offsets must be from `script.read_bytes()` (UTF-8 zero-based, end exclusive), not character indices. Every CONFIRMED issue must be assigned a zone including the **whole** exact quote anchor; zones non-overlap, no `[PART N]` header edits, no pass-span intersection. For Round2 exceptional causal dependence only:
```
{"zone_id":"Z002","start_byte":...,"end_byte":...,"issue_ids":["QL-007"],
 "pass_dependency_override_ids":["PASS-03"],"pass_dependency_reason":"...at least 35 chars, explaining why immutable strong line cannot remain..."}
```
This is not broad permission to rewrite other PASS passages. Audit file and zone spec are frozen before STEP5 edits.

## Full coverage anti-laziness protocol
Scan every range of 6k–10k Unicode characters with 10–15% overlap; independently enumerate all seven Parts. After each range record evidence; inspect intersections of dialogue, object, tense and location. Global passes: scene table, timeline, evidence ownership table, character knowledge graph, setup/payoff ledger and end-to-opening read. No arbitrary "top 10 issues" output. If cannot read full script: `AUDIT_INCOMPLETE`; no frozen certification.

## Final editorial verification
After REPAIR2 do not perform a new audit/repair cycle. Verify resolution against Round2 Issue IDs and inspect changed areas, adjacent transitions and whole-script integrity. `FINAL_VERIFY_REVIEW.json`:
```
{"final_verification":true,"score":96,"integrity_checked":true,
 "remaining_issues":[],"new_issues":[],"resolved_issue_ids":["QL-007"],
 "pass_span_dependency_overrides":{}}
```
If some confirmed issue remains or new severe bug exists, list it, issue `NOT_PUBLISH_READY`, and **STOP**. Do not disguise an extra editorial rewrite as final check.

## Regression examples from sample manuscript
Verify detection of: a father appearing to respond to himself; broken cup referenced without introduction; note's content read without opening transition; abrupt description of father's home while in daughter's house; Q/A without matching turn; fork placed down during a box-moving sequence; duplicate `Sonrió. Sonrió.`; anonymous debt evidence not plausibly verified/paid off. These are regression prompts for *source-grounded* auditing, not blanket errors for all stories.
