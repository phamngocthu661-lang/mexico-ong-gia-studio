# MAFIA × MAID STORY SYSTEM — V2.0 MASTER PRODUCTION CONTRACT

## Scope / routing
This is one **five-skill** production system for original US-English Mafia Boss × Maid/Waitress/Underestimated Woman narrative videos. Roles are **TITLE → OUTLINE → SCRIPT → FORENSIC QA/CONTROLLED REPAIR → SEO/THUMBNAIL/8S HOOK**. No channel audit, market research, vidIQ or external accounts are prerequisites. Use the previously bundled A/B/C channel DNA as **creative references**, not as instructions to copy existing stories.

## Authority (conflict resolution)
1. Current user's explicit, feasible hard constraints for the current project.
2. Immutable `CURRENT FINAL TITLE` / project `LOCKED_TITLE` and exact title anchors.
3. Locked `STORY CORE`, numbered outline Beat map, causality, loop/payoff, and approved factual canon.
4. **This V2.0 contract** and the role-specific V2.0 overlay.
5. Original synchronized `SHARED_PRODUCTION_CONTRACT.md` (September 2026), if not overridden here.
6. Operational instructions from legacy SKILL.md and historical master references.
7. Historical/raw DNA and competitor title collections = samples only.

A user's newly supplied title can start a **new project**. It must NOT silently change a title already locked in the same project, including via the SEO skill. An explicit rebase requires a deliberate new project/approved reset, not automatic reassignment.

## Contract — preserve the actual niche rules
- Title skill: standard mode generates **exactly 5** title candidates, each **≤100 Unicode characters including spaces and punctuation**, scored separately, with **one selected winner**. The original 60/40 viral-DNA vs creative-mutation concept is editorial guidance, not a literal arithmetic word ratio.
- Outline skill: choose primary DNA **A Archives / B Romance / C Hidden Heart** from title and explicit narrative evidence. Beat/Part count is **dynamic** (often 5 or 6), never forcibly 7 or 8. **Exactly 1 script PART per numbered outline BEAT**, same order. Outline is not the final script.
- Script language: **American English**, third-person past tense unless user overrides; cinematic but natural TTS-clean narrative, grounded mechanics and consequences, heroine drives the payoff.
- Standard script release targets: **44,000–48,000 visible Unicode characters** AND **7,400–7,650 spoken words**. Strict **<8,000 words** (exactly 8,000 fails), absolute ceiling **55,000 characters**, lower emergency hard envelope **40,000 characters**. 40–43,999 or 48,001–55,000 characters is a target miss, **not** normal release. Count with trusted code rather than an LLM estimate.
- No bracketed TTS/performance cues or filming notes in spoken text. Permitted output: PART headings, narration, spoken dialogue.
- QA has **MODE A: REVIEW ONLY** (do not edit) and **MODE B: CONTROLLED REWRITE** (only after an authorized patch ledger). Original production baseline **OPB** never auto-resets. Current revision baseline **CRB** changes every authorized edit. Default one complete review → one controlled rewrite → fresh verification; optional second recovery patch cycle for unresolved problems. Tool cap: **2 cycles** per project; no third automatic edit.
- Use the pre-existing Forensic Score 8 components, weights **A20 / B20 / C15 / D10 / E10 / F10 / G10 / H5**; P0 caps score at 59. `READY` requires **zero known actionable defects** and mechanical gates passing; do not replace this with an arbitrary 95/98 threshold.
- SEO: locked PRIMARY TITLE **verbatim** plus **exactly two** new supporting titles ≤100 characters; do not rebase. Default 12 sections, 3 thumbnail hypotheses, one final 16:9 image prompt and one **8-second** video prompt with 0–2, 2–5, 5–7, 7–8s phases. Three input levels (premise/outline/full script) retain caps 55/75/95 for packaging confidence. Earlier SEO can be labeled DRAFT; **PUBLISHABLE** only on current verified full script + READY QA.

## Source-derived creative non-negotiables
- Title promise is central, never merely cosmetic. Avoid new unseeded protagonists, secret competence, evidence, identity, inheritance, rescue, pregnancy or dramatic reversal.
- Main woman takes an indispensable causal action; boss protection does not replace agency. Romantic boundaries and consent are respected; coercion/abuse are not glamourized.
- Each beat has an entry cause, active decision, consequence, evidence/knowledge update, and bridge forward. The climax resolves the locked central promise using previously established elements.
- Spatial/time/knowledge/resource/injury/security logic is coherent. No abrupt plot-solving outsider or magic evidence.
- Content is fictional, non-graphic, non-instructional and suitable for YouTube. No glorification of criminal violence or actionable crime instructions.

## V2.0 workflow / state machine
`WAIT_TITLE → WAIT_OUTLINE → WAIT_SCRIPT → WAIT_CONTINUITY → WAIT_QA → (WAIT_REPAIR → WAIT_CONTINUITY → WAIT_QA)* → READY_FOR_SEO → PACKAGED`.

Use the standard JSON handoff templates to produce durable artifacts. The local Python controller checks file hashes, exact title, Part count, characters, word count, bracket cues, continuity ledgers, QA rubrics, patch scopes and the SEO package. SHA establishes **integrity**, not literary truth. Editorial review must still read the entire actual script.

## Memory & anti-duplication
A small local JSON `content_memory.json` stores project titles plus a seven-dimension premise fingerprint: heroine role, trigger event, power dynamic, hidden competence, evidence mechanism, core reversal, payoff. Similarity is a **signal**, not proof of copying. Exact match or very high similarity must be resolved before title lock; do not silently change user title. No live competitors or platform data are required.

## Authoritative handoff artifacts
- `title.json`: 5 scored candidates, selected winner, premise fingerprint.
- `outline.json`: locked title, selected DNA, story core, sequential beats, open-loop closure map, evidence setup/payoff map.
- `script.txt`: N PART headings and TTS-clean English prose.
- `continuity.json`: per-PART handoffs, character knowledge, relationship state, open loops, script SHA.
- `qa.json`: current script/title/outline/continuity SHA, two claimed read passes, PART-based exact evidence anchors, P0–P3 issues and deterministic score.
- `patch.json`: approved issue IDs, exact old→new replacements and baseline SHA.
- `seo.json`: primary title, 2 supporting, meta, 3 thumbnail ideas, final image+8s prompts, fact checks, current QA/script SHA.

Do not describe a saved file, completed research, generated image/video or 100% reading coverage if it did not happen. Without access to local Python runtime, produce checkable artifacts but mark machine checks **NOT RUN**, not PASS.
