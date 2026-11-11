# MACHINE-READABLE HANDOFF SCHEMAS — HOMELESS V3

**These companion JSON files are added on top of the original human-readable skill outputs.** Do not replace rich narrative outlines with these compact objects. JSON strings can be descriptive placeholders only in templates; do not use template placeholders as actual evidence.

## TITLE_CARD.json
```json
{"title":"Exact approved title (<=100 chars)","source_title":"Example source","viewer_contract":"...","viral_dna":"...","new_mechanism":"...","score":98,"readiness":"READY","instant_comprehension":true,"opening_serviceability":true}
```
`score` is an editorial assessment, not determined by Python.

## STORY_BLUEPRINT.json
```json
{"title":"Exact approved title","score":98,"premise":"...","primary_mystery":"...","deeper_mystery":"...","mechanism":"Specific physical discovery mechanism","payoff":"Distinct emotional/legal consequence","ending_action":"Action, not speech","dna_primary":"DNA A/B/C/D/E",
"parts":[{"part":1,"entry":"...","discovery":"...","exit":"...","target_chars":10000,"beats":["action","proof","decision"]}],
"clues":[{"id":"E01","setup_part":1,"payoff_part":4,"evidence":"physical clue","reinterpreted":true}],
"reveals":[{"part":2,"answer":"R1 grounded reveal"}],
"early_retention":{"title_promise_at":100,"physical_proof_at":250,"micro_payoff_1_at":800,"forward_question_at":1650,"micro_payoff_2_at":3800},
"canon":{"protagonist":"...","property":"...","timeline":"...","money":"...","object_states":"...","knowledge":"...","authority":"...","resolution_mode":"A"}}
```
**Actual valid Blueprint requires exactly 7 sequential part records with >=3 beats each and budgets summing 70–80k, >=8 unique clues with setup <= payoff, >=2 reinterpreted, >=4 reveals, plus all required fields.** The JSON cannot prove that the events are believable.

## CONTINUITY_HANDOFF_A/B/C.json
```json
{"title":"Exact approved title","segment":"A","facts":[{"key":"protagonist_name","value":"Name","immutable":true},{"key":"age","value":"42","immutable":true}],"open_loops":["L1"],"closed_loops":[],"evidence":[{"part":1,"quote":"Exact excerpt from actual segment"}]}
```
**B/C:** `closed_loops` can close IDs opened by prior stages; C must leave no major recorded open loop. `facts[].immutable` must not change across handoffs. For a deliberately changing fact (money state/repair progress), use a state-change event rather than overwriting an immutable field.

## REPAIR_PLAN.json
```json
{"baseline_sha256":"Exact SHA-256 of current full TXT","edits":[{"ticket_id":"P01","part":3,"old":"Exactly occurring old text snippet","new":"Replacement text"}]}
```
Each `old` must uniquely occur once inside the specified part; proposed candidate must be **exactly identical** to the baseline after these replacements. Protected span anchors must remain. Every `ticket_id` must be present in frozen QA findings. `commit-patch` does not write text, it only locks a user-created versioned candidate.

## SEO_PACK.json
```json
{"title":"Exact approved title","description":"170–280 natural English words...","tags":"comma, separated, tags, <=500 characters","hashtags":["#Story","#Mystery","#Restoration"],"evidence_quotes":["Exact manuscript quote 1 >=10 chars","Exact quote 2 >=10 chars","Exact quote 3 >=10 chars"],"thumbnail":{"aspect_ratio":"16:9","prompt":"Detailed grounded high CTR prompt >80 characters","evidence_quote":"Exact manuscript quote >=10 chars"},"trailer":{"seconds":20,"no_dialogue":true,"no_lip_sync":true,"clips":[{"seconds":10,"prompt":"Detailed silent no-lip-sync multishot prompt >=80 characters","shots":[{"action":"A grounded action","environment":"Real script setting","evidence_quote":"Exact script quote"},{"action":"Next grounded action","environment":"Real script setting","evidence_quote":"Exact script quote"}]}]},"factual_review":true,"trailer_review":true}
```
**Actual 10/20/30s trailers require exactly 1/2/3 separate 10-second OMNI clips**, each including its own long prompt and at least two shots. Every shot has a matching quote in the approved script. `factual_review` and `trailer_review` are editorial assertions, not machine proof of narrative truth. No actual image/video is rendered by creating a prompt.

## Cross-project originality memory
Use `init --memory /path/to/LOCAL_STORY_MEMORY.json` for each new project to compare against a **single user-owned local history**. Without this flag, only project-local history exists; uniqueness beyond it is UNKNOWN. Red similarity warning is a human review trigger, not a semantic plagiarism verdict.
