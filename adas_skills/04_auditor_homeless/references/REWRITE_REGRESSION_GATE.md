
> **V1.8.0 EXACT-LENGTH ENFORCEMENT:** Before any QA score or frozen ledger, read `EXACT_BODY_COUNT_ARTIFACT_PROOF_LOCK.md`, hash + machine-count the exact current full body. No exact count = QA ABORTED. Old counts cannot be reused.

# REWRITE REGRESSION GATE V1.7.0

## GOAL
Một revision đạt `PATCH EXECUTION PASS` khi:
- mọi approved patch fixed;
- mọi Immutable Pass Zone giữ nguyên;
- không có unauthorized rewrite;
- không làm mất strong material;
- approved length intent được giữ;
- không có TRUE REGRESSION do patch.

Regression re-audit phải đọc toàn script để bắt **patch-caused regression**, không để mở lại baseline defect hunt. Lỗi baseline cũ ngoài approved scope nếu hiếm hoi bị phát hiện là `AUDIT INTEGRITY MISS`: report-only, không tự sửa, không tự mở cycle mới, và không được triệt tiêu score gain của approved patches.

Mandatory companion: `BASELINE_PRESERVATION_ONE_SHOT_PROTOCOL.md`.

# PASS 0 — LOAD MASTER BASELINE
Khóa:
- exact original script/version;
- chars per Part + total + total words;
- target/hard caps;
- Patch Ledger/Oxx;
- Character/Canon/Voice/Platform/Hook locks;
- Strong-Span Sxx;
- rewrite scope.

# PASS 1 — PATCH APPLICATION
Với mỗi Pxx/Oxx:
- APPLIED? yes/no
- ROOT ISSUE REMOVED? yes/no
- DEPENDENCIES UPDATED? yes/no
- LENGTH INTENT RESPECTED? yes/no
- STRONG SPAN DAMAGED? yes/no

Bất kỳ no → chưa được tiếp tục.

# PASS 2 — EXACT UNTOUCHED-SPAN + AUTHORIZED DIFF GATE
Diff baseline vs revised by Part/scene.

First: every Immutable Pass Zone must match baseline exactly. Any difference = FAIL → revert.

Changed spans may map only to:
- approved Pxx/Oxx;
- dependency explicitly enumerated in that Pxx before approval;
- `REG(Pxx)` for a TRUE REGRESSION, within the original patch/dependency zone.

Unmapped change = FAIL → revert.

Specifically catch:
- paraphrase of PASS text;
- punctuation/spelling normalization outside approved occurrences;
- cutting reaction/process/transition outside scope;
- rewriting dialogue just to make it “better”;
- changing scene rhythm outside scope.

# PASS 3 — CHARACTER + WORD COUNT REGRESSION
Tính exact chars từng Part + total. Shared full-script default MUST remain **70,000–80,000 characters inclusive** unless user explicitly overrides. Word count is telemetry unless separately constrained.
Áp dụng bounded-range normalization trước, sau đó mới preservation bands từ baseline protocol.

Nếu Part bị ngắn đáng kể mà ledger không authorize CUT:
- không được PASS;
- restore lost strong content;
- hoặc thêm functional content đúng nơi patch tạo khoảng trống.

Không bù padding.

# PASS 3B — STATE DELTA GATE
For every changed state: BEFORE → PATCH EVENT → AFTER → downstream dependency.
No new animal/object/payment/vehicle/legal status may appear without a transition.

# PASS 4 — DEPENDENCY / CANON REGRESSION
Check:
- earlier setup;
- later payoff/callback;
- timeline;
- knowledge;
- object state/location;
- character motive/voice;
- legal/professional status;
- open loops;
- title promise;
- ending.

# PASS 5 — LOGIC / REAL-WORLD REGRESSION
Chạy lại:
- physics/mechanics;
- why-not-found-earlier;
- evidence triangulation;
- law/property/money;
- profession/institution;
- human incentives.

# PASS 5B — PATCH-ARTIFACT GATE
Inspect changed spans for editor-facing/meta/historical-anachronistic patch residue such as `modern permit`, `earlier in the story`, `the narrator`, `no cut backward`, or legal disclaimers that exist only to prove a patch. Repair those under the originating Pxx. If such residue pre-existed in an Immutable Pass Zone, report NQxx and do not edit it.

# PASS 6 — HOOK / RETENTION / HUMAN PROSE / YOUTUBE
Chạy lại:
- Early Retention Survival Gate: ~200 promise / 400 proof / 650 stakes / 1,100 payoff #1 / 2,000 next action / 5,000 payoff #2;
- No Hook Reset / early biography dump;
- no ~6,500-char retention desert after opening;
- Part-level retention;
- AI-pattern occurrences;
- spelling/grammar/American English;
- US 40+ legendary/heritage voice;
- YouTube/community/advertiser-sensitive wording.

# PASS 7 — BLIND FULL READ #1
Set aside old ledger. Đọc entire revised script như script mới.
Không chỉ kiểm vùng sửa.

# PASS 8 — BLIND FULL READ #2
Read the entire revised script line-by-line. Findings do not automatically create edit authority.

For each actionable finding:
1. first ask whether it was CAUSED by an approved patch;
2. TRUE REGRESSION → repair/revert only as `REG(Pxx)` inside originating approved scope;
3. if it already existed in an unchanged baseline span → classify `AUDIT INTEGRITY MISS`; report-only, **do not edit and do not subtract it from patch-progress score in this cycle**;
4. rerun Exact Untouched-Span + Diff + State + Length + Dependency gates after any REG(Pxx) repair.

# PASS 9 — PATCH STABILITY TEST
Ask:
“Did any approved patch remain incomplete or create a regression?”
If yes → repair/revert inside approved scope.

Then ask:
“Did the blind read reveal any unapproved baseline defect that the saturated initial audit should have caught?”
If yes → record `AUDIT INTEGRITY MISS`; do not edit, do not auto-create a new patch cycle, and mark initial audit completeness failure separately.

# PASS 9B — SCORE PROGRESSION + ANTI-MOVING-GOALPOST LOCK
Calculate `POST_REVISION_SCORE` with the exact frozen rubric.

For the current approved patch cycle:
- start from `FROZEN_BASELINE_SCORE`;
- add back exactly the fixed deductions of approved defects that were successfully fixed;
- subtract only deductions for `TRUE REGRESSION` caused by those patches;
- **do not add new deductions for pre-existing baseline misses discovered after freeze in the same cycle**. Those belong to `AUDIT INTEGRITY MISS`, not patch performance.

Therefore:
`EXPECTED_POST_PATCH_SCORE = FROZEN_BASELINE_SCORE + RECOVERED_APPROVED_DEDUCTIONS - TRUE_REGRESSION_DEDUCTIONS`.

If actual scoring would produce a lower value only because an old unchanged defect was newly noticed, report that defect under `AUDIT INTEGRITY MISS` and keep patch-progress scoring frozen. This prevents moving goalposts.

A critical Audit Integrity Miss may still make `PUBLICATION READINESS = NOT READY`, but must be labeled `INITIAL QA COMPLETENESS FAILURE`; it must not be described as a regression or used to claim the approved repair did not improve the script.

A negative `PATCH-CAUSED SCORE DELTA` is allowed only when a true patch-caused regression remains. Resolve/revert it before output.

# PASS 10 — OUTPUT
Always output:
- `PATCH EXECUTION: PASS/FAIL`;
- `FROZEN_BASELINE_SCORE: XX/100`;
- `AUDIT_CORRECTED_BASELINE_SCORE: XX/100` or `N/A`;
- `POST_REVISION_SCORE: XX/100`;
- `PATCH-CAUSED SCORE DELTA: +N/-N/0`;
- hard-gate status + `PUBLICATION READINESS: READY/NOT READY`.

A completed approved revision may be delivered as `PATCH EXECUTION: PASS / PUBLICATION READINESS: NOT READY` when report-only NQxx findings remain. List those NQxx findings compactly; do not silently repair them.

Do not output a patch-caused regression or unauthorized diff.
