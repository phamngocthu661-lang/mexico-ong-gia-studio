---
name: padre-mx-outline-writer
version: 4.0.0
description: "Step2 only. Generate a 7-Part forensic Mexican Spanish father-betrayal outline, continuity canon, and earned legal/emotional payoff from the locked title."
---
# PADRE MX — 7 PART OUTLINE / CANON ENGINE (STEP2 ONLY)

First read shared contract and `references/MEXICO_CHANNEL_DNA.md` and `references/OUTLINE_CANON_HANDOFF.md`. Read locked title; produce a genuine seven-Part source TXT, NOT script prose. Preserve user's winner promise, father identity and thematic cost. Do not secretly re-title. All dialogue sample lines must be original es-MX.

## Story engine
Opening action: a specific betrayal while father cannot simply walk away; he responds with restraint because emotional ties matter. Over seven Parts, father gradually learns he is not powerless and protects someone, a home, hard-earned work, or dignity; withholds only support he lawfully controls; consequences grow from antagonist's decisions, not improbable courtroom magic. End from an action rather than lecture.

| Part | Function | Nonnegotiable change |
|---|---|---|
| 1 | Visible humiliation/injury + immediate concrete stake | The father has a costly choice in the first scene |
| 2 | Years of sacrifice shown through 2 vivid memories / evidence | A relationship contradicts the antagonists' stated motive |
| 3 | Pressure escalates; father tries a humane resolution | A new obstacle disproves his first strategy |
| 4 | Reversal seed revealed and tested; protect rights, gather proof | A document/witness changes what can actually be proved |
| 5 | Antagonist crosses a justified irreversible line | Father's refusal is legally and morally actionable |
| 6 | Earned consequence, confrontation, witness/payoff | Prior seeds pay off; no instant ownership miracles |
| 7 | Human aftermath and irreversible boundary | Closure by choices; restitution or realistic separation |

Each Part: 8–12 scene beats with location, time, POV, objective, opposing intention, evidence, friction, new information, specific hook exit. Vary dramatic mode (quiet personal vs public vs factual) so not all Parts recycle a phone call. Provide 5 key first-person dialogue lines in es-MX but DO NOT draft screenplay.

## Mandatory canon ledger
Names (given+family), ages and relations, chronic conditions and recovery limitations, assets and true current owner, pension/monthly expense, paperwork timeline, authorized access, evidence provenance (who had paper/video, when, how), witnesses, protagonist's knowledge vs audience's knowledge, antagonist incentives, educational/household dependencies, calendar, outstanding promises, legal process timeline, seed/payoff map and loopholes. Avoid legal detail unsupported by fact-check; annotate verification issue rather than inventing.

## Handoff artifacts
`CURRENT_FINAL_TITLE`, `CURRENT_FINAL_OUTLINE` actual file UTF-8 LF with `[PART 1]...` headings or clear labeled seven-Part outline sections (do not use the exact full-script path); compute actual outline SHA256 and video_id; `CANON_LOCK.md`; `STATE_MATRIX.json` or plaintext equivalent; `EVIDENCE_CHAIN`, `MOTIVE_COST`, `RETENTION_EXIT_CUE`, `TRUTHFULNESS_CHECK`. Writer must read the exact file bytes, not guess outline SHA.

## Narrative QA before handing off
Check the villain is plausible, the father's strategic options are actually lawful, the twist is surprising but foreshadowed, the child retains accountability, nobody is humiliated simply for catharsis, the ending honors title without false promises. If a story requires supernatural money/legal mechanism, replace at Outline stage. Recommend step3.

## V1.1 Mandatory story & date preflight
Add a structured CAST_AGE_TIMELINE and FLASHBACK_BIRTH_LEDGER: for every character with stated age, derive possible birth year(s) at every dated scene. Pregnancy, child birth, marriage, founding, death, inheritance and contract timing must not contradict those ages. Verify THEN lock; flashback phrases must clearly identify whether earlier than or after the workshop founding. A 41-year-old in 2026 was born 1984/1985: do not state or imply a new pregnancy with him in 1986.
Ensure each Part has (a) a new family cost, (b) an independent, visible action or revelation, (c) a new power constraint, (d) no repetitive moral essay. Put the promised conflict and source of leverage in demonstrable scenes; the father cannot only read paperwork without consequences. Provide measurable Part-level scene and emotional turning points in outline, but no ungrounded legal miracles.

## V1.2 outline-to-writer length plan
Build 7 distinct, nonredundant Parts that can honestly sustain 70,000–80,000 characters, not the 35k–40k half-length observed in some drafts. Lock separate per-stage targets: A (Parts 1–2) 20,000–24,000; B (Parts 3–5) 30,000–35,000; C (Parts 6–7) 20,000–25,000 characters. Each individual Part >=8,500 characters. Preferred total 74k–78k. Add scene objectives and turning points; never pad with repetitive retrospection.

## V4.0 downstream consistency
Later STEP4/STEP5 use TWO frozen audits and TWO targeted repairs: Round1 logic then Round2 holistic quality. The locked title/7-Part outline must remain stable across both. No editor may silently revise this skill output to hide audit defects. Read V4 shared contract rather than legacy single-repair rules.


## V4 STEP2 — Mandatory Story Blueprint & Creative Selector
Read `references/PADRE_MX_CREATIVE_DNA_V4.md` and build `STORY_BLUEPRINT_V4.json` following `references/STORY_BLUEPRINT_V4_TEMPLATE.json`. Choose one Primary DNA, 1–2 Secondary DNA, one Story Mode, one Hook Pattern and a seven-Part escalation path. Compare candidate twist/evidence against known local project signatures; do not rely on the title alone.
Each Part must carry eight–twelve distinct scenes, two or more genuine retention beats (new action/proof/consequence), explicit entry/exit causality and a change in character cost. Plan at least three setup→payoff pairs with payoff after seed. Record character knowledge, evidence provenance and time constraints as separate structured lists. A generic slogan is NOT a retention beat.
After saving true `CURRENT_FINAL_OUTLINE.txt` and the Blueprint, run:
```
python scripts/padre_v4_planning.py blueprint --blueprint STORY_BLUEPRINT_V4.json --title "LOCKED_TITLE" --outline CURRENT_FINAL_OUTLINE.txt --memory PADRE_MX_PROJECT_MEMORY_V4.json
```
Skip --memory on first project. If FAIL, correct the blueprint BEFORE Step3. A structurally passing blueprint is NOT automatically a good story: evaluate plausibility. Freeze file hash as a new mandatory identity gate. No channel audit or market intelligence.
