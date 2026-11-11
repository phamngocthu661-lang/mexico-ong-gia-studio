
> **V1.8.0 EXACT-LENGTH ENFORCEMENT:** Before any QA score or frozen ledger, read `EXACT_BODY_COUNT_ARTIFACT_PROOF_LOCK.md`, hash + machine-count the exact current full body. No exact count = QA ABORTED. Old counts cannot be reused.

# CROSS-SKILL QUALITY CONTRACT — HOMELESS STORY PIPELINE V1.4

## PURPOSE

Đây là contract dùng chung bắt buộc giữa:
- `viet-gian-y-homeless` (Outline)
- `viet-kich-ban-homeless` (Script)
- `kiem-tra-kich-ban` (QA / Revision)

Mục tiêu: ba skill phải dùng **cùng một delivery contract, cùng hard gates và cùng định nghĩa regression**, để không xảy ra tình trạng một skill tạo output đúng chuẩn của nó nhưng skill sau lại chấm lỗi vì dùng chuẩn khác.

Nếu một file nội bộ cũ mâu thuẫn contract này, **contract này thắng**, trừ khi user trực tiếp yêu cầu khác trong tác vụ hiện tại.

---

# 1. SHARED DELIVERY CONTRACT — HARD BOUNDED RANGE LOCK

Default cho full Homeless script 7 Part:
- **HARD MINIMUM:** `70,000` characters.
- **HARD MAXIMUM:** `80,000` characters.
- **VALID RANGE:** `70,000–80,000` characters **inclusive**, tính cả spaces/punctuation/newlines trong script body.
- **Preferred operating zone:** `74,000–78,000` characters để tạo buffer an toàn khỏi hai mép hard range.
- **Character count is authoritative.** Word count chỉ là telemetry/diagnostic; **không còn hard `<8,000 words` cap** trừ khi user trực tiếp đặt thêm word target trong tác vụ hiện tại.
- `[PART X]` headings được loại khỏi count nếu và chỉ nếu cùng một phương pháp được dùng nhất quán ở Outline handoff, Script pre-output và QA baseline/revision.
- **69,999 characters = FAIL. 80,001 characters = FAIL.** Không score nào được bù cho length failure.
- Không được output full script ngoài range rồi hứa sửa sau. Draft phải được normalize nội bộ trước khi user nhìn thấy.
- User instruction mới nhất vẫn có quyền đặt một range khác trong tác vụ hiện tại; nếu user không override, `70k–80k` là source of truth của pipeline.

### Default Part Planning Budgets — SOFT HANDOFF, TOTAL RANGE IS HARD
| Part | Preferred planning zone | Typical role |
|---|---:|---|
| Part 1 | 10,200–11,000 | Early-retention survival + title-promise proof + setup while moving |
| Part 2 | 10,200–11,000 | Investigation + first deeper payoff + pressure shadow |
| Part 3 | 10,200–11,000 | First opening + active pressure window |
| Part 4 | 10,200–11,000 | Human truth + reinterpretation + tightening pressure |
| Part 5 | 10,200–11,000 | Hard choice + convergence |
| Part 6 | 11,800–12,800 | Grand reveal + immediate consequence |
| Part 7 | 9,800–10,800 | Procedural resolution if needed + healing + legacy |

Các Part zone là planning guardrail, **không phải independent hard caps**. Story có thể redistribute giữa Parts nếu causal pacing cần, nhưng full script bắt buộc `70,000–80,000` characters inclusive. Outline phải tạo đủ functional material để đạt range mà không filler.

### Quality-Preserving Length Expansion Rule
Vì pipeline mới có **hard minimum 70k**, việc tăng length phải đến từ functional story content, không phải padding. Được mở rộng bằng:
1. cause→effect bridge;
2. practical restoration/process có state change;
3. evidence verification / triangulation;
4. reaction/subtext làm đổi decision;
5. pressure / consequence / temptation;
6. community/human beat có later payoff;
7. sensory grounding gắn với action;
8. legal/historical/professional process khi stakes cần;
9. clue reinterpretation hoặc payoff đã được setup;
10. transitions/time progression cần cho chronology.

Cấm dùng để chạm 70k:
- duplicate reaction;
- repeated theme explanation;
- redundant sensory paragraphs;
- paraphrase lại clue đã hiểu;
- stacked document dump không đổi hypothesis;
- filler dialogue;
- invented twist/lore chỉ để tăng ký tự.

---

# 2. SHARED HARD GATES — ZERO COMPENSATION

Các gate dưới đây là PASS/FAIL. Điểm số không được bù cho hard failure:
1. TITLE CONTRACT / literal promise fulfillment;
2. MASTER TIMELINE / chronology / season / age;
3. MONEY arithmetic `before → change → after`;
4. OBJECT + ANIMAL + INVENTORY state;
5. KNOWLEDGE state / who-knows-what;
6. ACCESS / AUTHORITY / LEGAL ROLE;
7. PERIOD-SENSITIVE legal/professional terminology;
8. NAMING introduction lock;
9. COLD-OPEN event identity + exact return point;
10. EXACT-NUMBER state/payoff;
11. Part 6→7 RESOLUTION MODE chronology;
12. WHY-NOT-FOUND-EARLIER / WHY-NOW causality;
13. LENGTH `70,000–80,000 chars inclusive` unless user explicitly overrides with a new current range;
14. EARLY RETENTION SURVIVAL GATE from Section 2A;
15. TTS cleanliness / no stage directions when script is narration-ready.

Nếu bất kỳ hard gate FAIL:
- Outline không được output là final 98+;
- Script không được output là final 98+;
- QA không được gắn READY / >=98.

---

# 2A. EARLY RETENTION SURVIVAL CONTRACT — HARD GATE

The pipeline must optimize the first minutes for **click-to-story continuity**, not merely a dramatic first sentence. Default architecture:

**PROMISE CONTACT → PHYSICAL PROOF → PERSONAL/STORY STAKES → MICRO-PAYOFF #1 → BIGGER QUESTION → CONTEXT-WHILE-MOVING → NEXT ACTION → MICRO-PAYOFF #2**

For full scripts using ordinary narration/TTS, audit the script-body opening by approximate character position:
- **By char ~200:** the title-promise object/action/anomaly is concretely present or directly referenced. No generic atmospheric preamble.
- **By char ~400:** viewer receives physical/verifiable proof that the anomaly/conflict is real.
- **By char ~650:** stakes are clear: why this matters to the protagonist now.
- **By char ~1,100:** **MICRO-PAYOFF #1** answers one small question or confirms one meaningful fact. Opening may not be question-only.
- **By char ~2,000:** the answer has opened a bigger question and protagonist is taking a next action.
- **By char ~5,000:** **MICRO-PAYOFF #2 / first functional clue or reinterpretation** must materially advance the mystery/story.

These character points are practical proxies for roughly the first seconds/minutes and may flex slightly for natural sentence completion, but they are **QA-enforced story-position gates**, not decorative suggestions. A script that plainly delays these functions is an EARLY RETENTION FAIL.

### NO HOOK RESET
- Do not open on the promised mystery and then abandon it for a long biography/backstory reset.
- Before Micro-Payoff #1, standalone biography/exposition is forbidden except short context embedded in current action.
- Within the first ~2,000 characters, no uninterrupted backstory/exposition block should exceed ~500 characters without returning to current action/evidence/stakes.
- If a flashback/cut-back is truly needed, earn Micro-Payoff #1 first and return quickly; `CONTEXT-WHILE-MOVING` is the default.

### RETENTION DESERT GATE
After the first ~5,000 characters, no stretch of roughly **6,500 characters or more** may pass without at least one meaningful change:
- new evidence/clue payoff;
- new consequence;
- decision/hard choice;
- pressure/leverage change;
- reinterpretation;
- relationship change that affects action;
- mechanism/restoration progress that changes story state.

Quiet scenes are allowed. **Static scenes are not.**

### LONG-FORM REWARD LADDER
Do not front-load the final answer. Front-load **progress**. The grand title-level reveal can remain late, but the viewer must receive escalating partial rewards throughout the 70k–80k script.

---

# 3. STATE DELTA GATE — MANDATORY

Mọi phase phải coi story như state machine.

Trước và sau mỗi beat/patch làm thay đổi state, track tối thiểu:
`STATE | BEFORE | CHANGE EVENT | AFTER | NEXT DEPENDENCY`

Bắt buộc cho:
- cash/debt;
- cattle/animals;
- vehicles/horses;
- critical objects/documents;
- injury/physical condition;
- property/legal status;
- knowledge;
- access/permission;
- weather/season when consequential.

**NO NEW STATE WITHOUT TRANSITION:** noun/object/animal/money/legal status quan trọng không được xuất hiện trong prose downstream nếu không có acquisition/change event hoặc pre-existing state đã được establish.

---

# 4. SCORE STABILITY + RUBRIC FREEZE

## 4.1 Same-Lineage Rubric Freeze
Ngay ở QA đầu tiên của một script lineage, khóa:
- scoring categories;
- weights;
- hard gates;
- target threshold;
- delivery caps.

Mọi re-audit của cùng lineage phải dùng **y nguyên rubric và weights đó**. Cấm thêm category mới hoặc đổi trọng số sau revision chỉ vì vừa phát hiện một nhóm lỗi khác.

## 4.2 Fixed Script/QA Quality Rubric — 100 points
Dùng **nguyên cấu trúc chất lượng cao của Script V1.4**, không hạ trọng số các yếu tố cốt lõi để nhường điểm cho compliance:
- Title Fulfillment + Hook: **10**
- Causality / Discovery / Why-now logic: **15**
- Timeline / Money / State / Knowledge Continuity: **15**
- Legal / Historical / Authority / Professional Plausibility: **10**
- Physical / Mechanical Plausibility: **10**
- Mystery / Clue / Reveal Architecture: **10**
- Retention / Pressure / Pacing: **10**
- Character Agency / Competence / Human Behavior: **8**
- Human Prose / Dialogue / US 40+ / TTS / Platform Readiness: **7**
- Emotional Payoff / Ending-by-Action: **5**
TOTAL: **100**

**Length / Delivery Compliance remains a HARD PASS/FAIL GATE, not a point bucket.** Vì vậy việc đồng bộ length không thể làm điểm story cao hơn hoặc thấp hơn bằng cách đổi weight.

Threshold: **>=98/100 AND all hard gates PASS.**
Không hạ threshold để “ổn định điểm”.

## 4.3 Absolute Score vs Regression Classification
Nếu một vòng QA sau phát hiện lỗi đã tồn tại từ baseline nhưng vòng trước bỏ sót, phải label:
- `PRE-EXISTING QA MISS` — lỗi có từ trước, audit trước bỏ sót;
- `PATCH-EXPOSED` — patch làm lỗi cũ lộ rõ hơn nhưng không tạo ra;
- `TRUE REGRESSION` — patch thực sự tạo lỗi mới.

Không được gọi một `PRE-EXISTING QA MISS` là “revision làm script tệ hơn”.

## 4.4 Score Transparency + Patch Non-Degradation Rule
- `FROZEN_BASELINE_SCORE` is publishable only after the initial Defect Universe/Omission Sweep is complete, so the first score is not a provisional guess.
- **The numeric score MUST ALWAYS be shown to the user**, even when it is low, even when one or more hard gates FAIL, and even when `Readiness = NEEDS PATCHES / NOT READY`.
- Never hide a score, replace it with only PASS/FAIL, round it upward to the threshold, or suppress it because the script failed length/logic/retention.
- Every post-revision re-audit must also show `POST_REVISION_SCORE` using the exact same frozen rubric, regardless of whether the score is 98, 72, 41, or lower.
- `READY` still requires `>=98/100 AND all hard gates PASS`; score transparency does **not** lower the standard.
- A revision may not knowingly lose points because an approved patch created a `TRUE REGRESSION`. Repair or revert that patch **inside its original authorized patch/dependency scope** before delivery.
- If a later re-audit discovers a defect that already existed outside the approved patch universe, label it `AUDIT CORRECTION / PRE-EXISTING QA MISS` or `PATCH-EXPOSED`, score it honestly, and **do not edit that untouched baseline span in the current revision**.
- When a newly discovered baseline miss changes the absolute score, show the score and classification clearly; do not falsely describe the drop as damage caused by the revision.

## 4.5 Score Deduction Ledger — Anti-Scoring-Drift Lock
At the first exhaustive QA, create and freeze a `SCORE DEDUCTION LEDGER` together with the defect universe.

Format:
`DEFECT ID | PRIMARY RUBRIC CATEGORY | FIXED DEDUCTION | HARD-GATE IMPACT | RATIONALE`

Rules:
- Every numeric deduction must be traceable to a concrete defect/occurrence or a clearly defined category-level weakness found in the exhaustive audit.
- The same unchanged defect keeps the same deduction in later re-audits. Do not change deductions because the evaluator's mood/strictness changed.
- A fixed category score may not exceed its weight or fall below zero.
- Hard-gate status remains separate; a hard-gate failure may coexist with any numeric score and never causes the score to be hidden.
- When an approved Pxx is correctly fixed, remove only the deduction causally attached to that defect; do not rescore unrelated categories downward.
- A newly discovered `NQxx` receives a new fixed deduction. If it is PRE-EXISTING/PATCH-EXPOSED in unchanged baseline text, back-apply that same deduction to an `AUDIT_CORRECTED_BASELINE_SCORE` for apples-to-apples comparison.
- Report all three when applicable:
  - `FROZEN_BASELINE_SCORE` — historical first audit score;
  - `AUDIT_CORRECTED_BASELINE_SCORE` — baseline rescored only to include newly discovered pre-existing NQxx using the same deduction;
  - `POST_REVISION_SCORE` — current revised script absolute score.
- `PATCH-CAUSED SCORE DELTA = POST_REVISION_SCORE - AUDIT_CORRECTED_BASELINE_SCORE` when an audit correction exists; otherwise compare to FROZEN_BASELINE_SCORE.
- A negative patch-caused delta indicates true regression/scoring inconsistency and must be resolved inside approved patch scope before delivery.

This ledger exists specifically to prevent a script from appearing to lose points merely because later QA used a different standard.

---

# 5. DEFECT UNIVERSE FREEZE — STRICT USER-AUTHORIZED REVISION

QA đầu tiên phải tạo `KNOWN DEFECT UNIVERSE V1`:
`Pxx | occurrences | PRE-AUTHORIZED dependencies | affected states | severity | length intent | expected post-patch state`

Trước khi publish ledger:
- full read #1;
- full read #2;
- exact-number sweep;
- state-delta sweep;
- hook/retention sweep;
- period/legal sweep;
- human-prose/patch-artifact sweep;
- repair simulation;
- omission sweep.

Sau freeze:
- Patch IDs/Occurrence IDs stable;
- dependencies needed to execute a patch safely must already be written into that patch before user approval;
- revision không được tự mở một creative rewrite agenda mới;
- **no internal late-fix authorization may expand the approved edit universe.**

## 5.1 IMMUTABLE PASS ZONE — HARD LOCK

After the user approves the Patch Ledger, divide the MASTER BASELINE into two classes:

### AUTHORIZED EDIT ZONE
Only text explicitly covered by:
- approved `Pxx/Oxx` locations;
- dependencies explicitly enumerated inside that approved `Pxx` before approval;
- `REG(Pxx)` micro-repair needed solely because the approved patch itself created a true regression.

### IMMUTABLE PASS ZONE
Every baseline character/span outside the Authorized Edit Zone is **locked**.
It must remain textually identical to the MASTER BASELINE.

In an Immutable Pass Zone, revision MUST NOT:
- paraphrase;
- polish wording;
- change dialogue rhythm;
- tighten pacing;
- normalize punctuation/spelling;
- move paragraphs;
- shorten/expand description;
- alter sentence breaks;
- add a bridge;
- repair a newly noticed old defect.

If a later blind re-audit finds a real issue in an Immutable Pass Zone:
1. classify it `PRE-EXISTING QA MISS` or `PATCH-EXPOSED`;
2. assign a report-only `NQxx` finding with exact location and score impact;
3. **do not edit it in the current revision**;
4. it may become a new user-approved Patch ID only in a later QA/patch cycle.

## 5.2 TRUE REGRESSION EXCEPTION — REG(Pxx), NOT NEW SCOPE

A `TRUE REGRESSION` created by an approved patch may be repaired only when all are true:
1. it is causally attributable to a specific approved `Pxx`;
2. repair stays inside that patch's original location or its pre-authorized dependency span;
3. the repair is the smallest change that makes the approved patch non-degrading;
4. no Immutable Pass Zone is touched.

If a true regression cannot be repaired without modifying an Immutable Pass Zone, revert/redesign the originating Pxx within its authorized scope. Do not expand scope silently.

**Authorized Diff Set:** approved `Pxx/Oxx`, their pre-authorized dependencies, and qualifying `REG(Pxx)` only.

---

# 6. REVISION RE-AUDIT + SCORE TRANSPARENCY

Trong Revision Mode:
1. apply only the user-approved Patch Ledger on the MASTER BASELINE;
2. run an **Exact Untouched-Span Comparator**: every Immutable Pass Zone must match baseline exactly;
3. Authorized Diff Gate;
4. State Delta Gate;
5. exact character-count bounded-range gate (`70k–80k inclusive`) + word telemetry;
6. dependency/canon/legal/physics regression inside the affected patch neighborhoods plus whole-script read-only verification;
7. Patch-Artifact Gate on changed spans;
8. Blind Read #1 whole revised script;
9. Blind Read #2 whole revised script;
10. calculate and **always display** the exact fixed-rubric `POST_REVISION_SCORE` plus hard-gate status.

Re-audit handling:
- approved Pxx still wrong → repair only inside its Authorized Edit Zone;
- `TRUE REGRESSION` from Pxx → repair/revert only under `REG(Pxx)` inside original authorized scope;
- `PRE-EXISTING QA MISS` / `PATCH-EXPOSED` outside approved scope → create report-only `NQxx`, deduct/reflect it in the score, **DO NOT EDIT**;
- pure preference → do not score as defect and do not edit.

Two statuses are separate:
- **PATCH EXECUTION:** PASS only when all approved patches are correctly applied, no true regression remains, and no unauthorized diff exists.
- **PUBLICATION READINESS:** READY only when absolute score `>=98` and every hard gate PASS.

A revision with correct approved patches may therefore be returned as `PATCH EXECUTION: PASS / PUBLICATION READINESS: NOT READY` if the re-audit reveals previously unapproved baseline defects. The score must still be shown. The skill must not chase 98 by modifying unapproved text.

---

# 7. PATCH-ARTIFACT GATE

Sau revision, tìm và loại câu tồn tại chủ yếu để “chứng minh đã sửa QA” thay vì phục vụ viewer/story.

Red flags:
- “modern permit / modern law” comparison trong historical narration;
- “earlier in the story”;
- “this time there was no cut/flashback”;
- “the narrator now calls...”;
- legal disclaimer không có character/story function;
- meta wording nhắc tới outline, script, patch, viewer logic trong diegesis.

Nếu artifact nằm trong changed/authorized span → rewrite/delete ở radius nhỏ nhất dưới originating Pxx/REG(Pxx).
Nếu artifact đã tồn tại trong Immutable Pass Zone → report `NQxx`; **không sửa trong revision hiện tại**.

---

# 8. PHASE RESPONSIBILITIES

## Outline
- thiết kế đủ functional depth để script **bắt buộc đạt 70k–80k characters** mà không filler;
- handoff Part Budget + First-5-Minute Retention Map + Canon/State ledgers;
- xây reward ladder đủ dày để không có retention desert >~6.5k chars;
- quality gate >=98 + hard gates PASS.

## Script
- dùng Outline Budget Handoff + Early Retention Map;
- pre-draft Canon State Matrix;
- pre-output State Delta + fixed QA mirror;
- **không output full script <70,000 hoặc >80,000 characters**;
- character count phải được kiểm lại ngay trước output;
- không thêm state mới mà không có transition.

## QA / Revision
- dùng cùng `70k–80k inclusive` delivery contract và fixed rubric;
- **full script ngoài 70k–80k = HARD FAIL / NOT READY**, dù score nội dung >=98;
- baseline dưới 70k phải được authorize functional expansion; baseline trên 80k phải controlled-compress về range;
- audit exhaustive một lần;
- freeze defect universe;
- phân biệt QA miss vs true regression;
- revision chỉ được sửa approved Patch Universe; Immutable Pass Zones giữ nguyên tuyệt đối;
- regression re-audit phải chấm điểm số công khai dù thấp/hard-fail;
- `PATCH EXECUTION PASS` không đồng nghĩa `PUBLICATION READY`; READY vẫn cần >=98 + all hard gates PASS;
- không được chase score bằng cách sửa text chưa được user authorize;
- không hạ score threshold và không dùng filler/cắt strong material để “chạy length”.


# 9. ONE-SWEEP QA FINALITY + SCORE PROGRESSION LOCK — V1.4

For QA/Revision lineage:
1. Initial QA may freeze only after full multi-pass audit + Coverage Matrix + a complete Saturation Pass that finds **0 new actionable defects**.
2. The first frozen Patch Ledger is intended to contain the entire actionable defect universe, not a sample.
3. Revision applies only that approved universe. Every untouched span is copied **exactly** from the Master Baseline.
4. Regression re-audit is primarily a **patch-caused regression test**, not permission to reopen baseline defect hunting.
5. Same-cycle `POST_REVISION_SCORE` must progress from the frozen deduction ledger: correctly fixed approved defects recover their fixed deductions; only TRUE REGRESSION may remove points.
6. A later-discovered pre-existing miss is an `AUDIT INTEGRITY MISS`. It may block READY if critical, but may not be used as a moving-goalpost deduction that cancels recovered patch points in the same cycle.
7. No automatic endless patch cycles. A new cycle requires explicit user request.
