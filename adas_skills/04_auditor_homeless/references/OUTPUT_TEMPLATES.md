
> **V1.8.0 EXACT-LENGTH ENFORCEMENT:** Before any QA score or frozen ledger, read `EXACT_BODY_COUNT_ARTIFACT_PROOF_LOCK.md`, hash + machine-count the exact current full body. No exact count = QA ABORTED. Old counts cannot be reused.

# OUTPUT TEMPLATES V1.7.0

## MODE A — ONE-SHOT EXHAUSTIVE REVIEW

### VERDICT
**Readiness:** NEEDS PATCHES / READY  
**Forensic score (MANDATORY NUMERIC, even if low/hard-fail):** .../100  
**FROZEN_BASELINE_SCORE:** .../100  
**Rubric version:** CROSS-SKILL QUALITY CONTRACT V1.4  

### SCORE BREAKDOWN — ALWAYS SHOW
- Title Fulfillment + Hook: .../10
- Causality / Discovery / Why-now: .../15
- Timeline / Money / State / Knowledge: .../15
- Legal / Historical / Authority / Professional: .../10
- Physical / Mechanical: .../10
- Mystery / Clue / Reveal: .../10
- Retention / Pressure / Pacing: .../10
- Character Agency / Competence / Human Behavior: .../8
- Human Prose / Dialogue / US40+ / TTS / Platform: .../7
- Emotional Payoff / Ending-by-Action: .../5
- **TOTAL: .../100**

### SCORE DEDUCTION LEDGER — FREEZE WITH BASELINE
`Defect ID | Primary rubric category | Fixed deduction | Hard-gate impact | Rationale`

Every Pxx/Oxx defect family must appear here. The deduction total must reconcile exactly to `FROZEN_BASELINE_SCORE`. The same unchanged defect keeps the same deduction on later re-audits.

**Mạnh nhất:** ...  
**Rủi ro lớn nhất:** ...

### BASELINE LOCK
- Part 1: ... chars
- Part 2: ... chars
- ...
- Total: ... chars
- Total words: ...
- HARD LENGTH RANGE: 70,000–80,000 chars inclusive (or explicit current override)
- Length status: PASS / FAIL-UNDER / FAIL-OVER
- Early Retention Survival: PASS / FAIL
- Revision rule: preserve baseline length unless Patch Ledger explicitly authorizes net cut/add.

### AUDIT COMPLETENESS CERTIFICATE
- Full Read #1: PASS
- Line-by-Line Read #2: PASS
- Reverse Dependency Read #3: PASS
- Coverage Matrix blank cells: 0
- Repair Simulation: PASS
- Final Saturation Pass new actionable defects: **0**
- **AUDIT COMPLETENESS: PASS**

### PATCH LEDGER — COMPLETE

#### P01 — [P0/P1/P2/P3] ...
**Vị trí:** Part N → scene → quote anchor "..." → "..."  
**Lỗi:** ...  
**Cần sửa thành:** ...  
**Cách sửa:** ...  
**Dependencies:** ...  
**Defect Class:** BASELINE DEFECT / PRE-EXISTING QA MISS / PATCH-EXPOSED / TRUE REGRESSION  
**State Delta:** before → change → after if applicable  
**Length Intent:** KEEP / ADD / CUT / REDISTRIBUTE  
**Phạm vi:** ...

For recurring pattern:
- O01 — exact location → exact action
- O02 — ...

For whole-Part repair:

#### Pxx — [P0/P1] REWRITE ENTIRE PART N — REQUIRED
**Root problem:** ...  
**MUST CHANGE:** exact zones  
**MUST PRESERVE:** S01...Sn  
**Dependencies:** ...  
**Baseline chars:** ...  
**Target chars:** ...  
**Method:** scaffold reconstruction  
**Length Intent:** ...

Continue until all actionable issues are represented. No maximum.

### REWRITE CONTRACT
- Total Patch IDs: N
- Total Occurrences: M
- Entire-Part rewrites required: ...
- Protected strengths / MUST PRESERVE: ...
- Character/Canon/Voice/Hook lock: ...
- Baseline length lock: ACTIVE
- Immutable Pass Zones: COPY EXACTLY
- Unauthorized changes: FORBIDDEN
- **Status:** `WAITING FOR REWRITE COMMAND` only when `Readiness: NEEDS PATCHES`; if `Readiness: READY` and no patches exist, use `NO REWRITE REQUIRED`.

## MODE B — STRICT PATCH REVISION + REGRESSION RE-AUDIT

**Applied:** approved Pxx/Oxx only  
**Exact Untouched-Span Comparator:** PASS / FAIL  
**Authorized Diff Gate:** PASS / FAIL  
**Length 70K–80K Gate:** PASS / FAIL  
**Early Retention Survival:** PASS / FAIL  
**State Delta Gate:** PASS / FAIL  
**Patch-Artifact Gate (changed spans):** PASS / FAIL  
**Two-pass Blind Re-audit:** PASS  
**PATCH EXECUTION:** PASS / FAIL  

### POST-REVISION SCORE — ALWAYS SHOW
- Title Fulfillment + Hook: .../10
- Causality / Discovery / Why-now: .../15
- Timeline / Money / State / Knowledge: .../15
- Legal / Historical / Authority / Professional: .../10
- Physical / Mechanical: .../10
- Mystery / Clue / Reveal: .../10
- Retention / Pressure / Pacing: .../10
- Character Agency / Competence / Human Behavior: .../8
- Human Prose / Dialogue / US40+ / TTS / Platform: .../7
- Emotional Payoff / Ending-by-Action: .../5
- **POST_REVISION_SCORE: .../100**
- **FROZEN_BASELINE_SCORE: .../100**
- **EXPECTED_POST_PATCH_SCORE: .../100**
- **PATCH-CAUSED SCORE DELTA: +N / 0 / -N**
- **AUDIT INTEGRITY MISS: NONE / list separately (no same-cycle score offset)**
- **PUBLICATION READINESS:** READY / NOT READY

Score progression is frozen to the approved defect universe. A later pre-existing audit miss is reported under `AUDIT INTEGRITY MISS` and does not offset recovered approved deductions in the same patch cycle. Only TRUE REGRESSION may reduce PATCH-CAUSED SCORE DELTA.

`READY` requires >=98 + all hard gates PASS. A lower score must still be printed.

### REGRESSION RE-AUDIT — NEW UNAPPROVED FINDINGS
If none: `NQ findings: NONE`.
If present, list each `NQxx | exact location | class | score/hard-gate impact | proposed future patch`. These findings are **NOT edited** in the current revision.

[Final revised script or requested scope]

Do not alter any text outside approved Pxx/Oxx + pre-authorized dependencies. No hidden score-chasing edits.
