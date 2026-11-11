
> **V1.8.0 EXACT-LENGTH ENFORCEMENT:** Before any QA score or frozen ledger, read `EXACT_BODY_COUNT_ARTIFACT_PROOF_LOCK.md`, hash + machine-count the exact current full body. No exact count = QA ABORTED. Old counts cannot be reused.

# BASELINE PRESERVATION & STRICT-PATCH REVISION PROTOCOL V1.7.0

## PURPOSE
Ngăn hai lỗi revision phổ biến:
1. càng sửa càng ngắn;
2. sửa một lỗi nhưng vô tình tái sinh/đổi những đoạn đã tốt và tạo lỗi mới.

Đây là protocol bắt buộc cho cả REVIEW planning và REWRITE execution. V1.6 adds an absolute Immutable Pass Zone: unapproved baseline text must remain textually identical.

# A. MASTER BASELINE SNAPSHOT
Trước khi review/rewrite, ghi nội bộ:
- source version/file;
- exact characters per Part;
- exact total characters;
- exact total words;
- title/Part structure;
- target min/max/hard cap nếu có;
- strong spans/beat đã PASS.

Character count phải dùng cùng một phương pháp trước/sau. Ưu tiên count visible script body bao gồm spaces/punctuation/newlines; Part heading có thể tách riêng nhưng phải nhất quán.

# B. BASELINE PRECEDENCE
1. User-specified MASTER đủ dài > revised version mới hơn nhưng bị co ngắn.
2. User-specified current range > shared contract > baseline preservation. Default shared range is **70,000–80,000 characters inclusive**.
3. Nếu baseline nằm trong target, preservation là mặc định.
4. Nếu baseline nằm ngoài 70k–80k, shared bounded range thắng preservation: under-range phải functional-expand; over-range phải controlled-compress.

# C0. SHARED BOUNDED-RANGE NORMALIZATION
If baseline violates the current shared range and user did not override:

### Baseline <70,000 chars
- preserving the undersized baseline at 99–101% is NOT allowed;
- first review MUST authorize enough functional ADD spans across appropriate Parts to reach >=70,000;
- add causality/process/verification/reaction/pressure/consequence/human-payoff/needed chronology;
- no filler, repeated theme, decorative scenes or invented twist solely for length.

### Baseline >80,000 chars
- first review MUST identify/authorize enough redundant spans for controlled compression;
- preserving an oversized baseline at 99–101% is NOT allowed;
- strong functions remain frozen; compress redundancy/explanation, not story spine.

### Baseline 70,000–80,000 chars
- normal preservation bands apply.
- preferred zone is 74,000–78,000 when authorized edits naturally permit safer buffering.

# C. LENGTH STABILITY LOCK
Nếu ledger KHÔNG yêu cầu net cut:
- mỗi Part: target 98–102% baseline Part;
- toàn script: target 99–101% baseline total;
- tuyệt đối không rời shared 70k–80k range.

Nếu ledger yêu cầu CUT:
- Patch phải nêu cut location và reason;
- net decrease không được lớn hơn tổng planned cuts + 0.5% baseline Part, trừ khi Part được đánh dấu structural rewrite với target mới rõ ràng;
- không được dùng một yêu cầu “tighten exposition” để rút gọn toàn Part.

Nếu ledger yêu cầu ADD:
- thêm đúng function cần thiết;
- vẫn phải nằm trong 70k–80k;
- nếu chạm cap, trim redundancy ở đúng spans đã ledger authorizes, không cắt strong spans.

# D. FUNCTIONAL REPLACEMENT RULE
Nếu một patch phải bỏ 300–800 ký tự nhưng Part cần giữ body/nhịp:
được bù bằng content có chức năng:
- cause→effect bridge;
- physical process;
- reaction/subtext;
- consequence;
- tension/pressure;
- character decision;
- sensory/location grounding;
- transition cần thiết.

Cấm:
- filler;
- lặp theme;
- thêm mô tả vô nghĩa chỉ để đủ ký tự;
- tạo clue/twist mới không cần thiết.

# E. IMMUTABLE PASS-ZONE FREEZE
After Patch Ledger approval, every baseline span outside approved Pxx/Oxx + dependencies explicitly enumerated before approval is an **IMMUTABLE PASS ZONE**.

It must remain textually identical. Do not paraphrase, punctuation-normalize, spell-fix, move, shorten, expand, reline, or polish it.

Strong spans inside a larger authorized rewrite zone are additionally marked MUST PRESERVE and copied **exactly** unless the original Patch Ledger explicitly authorizes that exact span.

If a later re-audit discovers an old defect in an Immutable Pass Zone, classify it `AUDIT INTEGRITY MISS`; do not edit it, do not automatically open another cycle, and do not use it to cancel the score gain from correctly closed approved patches.

# F. SURGICAL PATCH DEFAULT
Mặc định thao tác:
ORIGINAL SPAN → PATCHED SPAN.

For every untouched region the operation is literally:
`COPY BASELINE EXACTLY` — character-for-character, including punctuation, paragraph order and line breaks.

Không thao tác:
ORIGINAL PART → GENERATE NEW PART FROM MEMORY.

Ngay cả khi nhiều patch trong một Part, vẫn patch trên baseline trước. Chỉ chuyển sang scaffold reconstruction nếu ledger đã ghi `REWRITE ENTIRE PART — REQUIRED`.

# G. ENTIRE-PART SCAFFOLD RECONSTRUCTION
Khi rewrite cả Part:
1. Copy các MUST PRESERVE/PASS spans **exactly** vào scaffold trước.
2. Giữ nguyên thứ tự các beat mạnh trừ khi ledger yêu cầu move.
3. Viết lại chỉ các zones MUST CHANGE.
4. Viết bridge tối thiểu quanh preserved spans.
5. Match baseline length band/target.
6. Không làm mất restoration/process/reaction/tension detail đang đạt chỉ để prose gọn hơn.

# H. NO COMPRESSION SPILLOVER
Các từ khóa sau là LOCAL trừ khi ledger nói GLOBAL kèm occurrences:
- compress;
- tighten;
- reduce AI prose;
- remove repetition;
- shorten exposition;
- improve pacing.

Không được diễn giải chúng thành “viết lại cô đọng toàn Part”.

# I. AUTHORIZED DIFF + EXACT UNTOUCHED-SPAN GATE
After rewrite, compare MASTER BASELINE vs revised text. First verify that every Immutable Pass Zone is identical.

Every changed span must map to:
- approved Pxx/Oxx;
- a dependency explicitly enumerated inside that approved Pxx before user approval;
- `REG(Pxx)` only for a TRUE REGRESSION created by the approved patch, and only inside the original patch/pre-authorized dependency zone.

Changed span without this authorization → **REVERT to baseline**.

No internal late-fix authorization, automatic typo cleanup, style polish, formatting normalization, or newly discovered baseline fix may expand the edit universe. A spelling/format change is allowed only when that exact occurrence/family was part of the approved ledger.

If a new baseline issue is noticed outside scope, record `NQxx` for the re-audit report and score it honestly; do not edit it.

# J. CHARACTER-COUNT REGRESSION
Sau mỗi Part:
- Original chars = A
- Revised chars = B
- Delta = B-A
- Delta % = (B-A)/A
- Hard range = 70,000–80,000 unless current user override

FAIL nếu:
- B <70,000 hoặc >80,000 ở full-script total;
- B thấp hơn preservation band mà ledger không authorize cut;
- total script nằm ngoài 70k–80k contract.

Không được output trước khi mọi Part PASS.

# K. REPAIR SIMULATION BEFORE LEDGER FREEZE
Trước khi publish review, với mỗi Pxx hỏi:
- sửa Pxx sẽ buộc đổi câu/scene nào khác?
- có làm character biết sớm hơn không?
- có đổi object state không?
- có làm later callback sai không?
- có đổi timeline/legal consequence không?
- có làm Part hụt length không?

Dependency phải được ghi vào cùng patch trước khi user approve.

# L. STRICT-PATCH FINALIZER
After revision:
1. Approved-patch completeness.
2. Exact Untouched-Span Comparator.
3. Authorized Diff.
4. Character-count regression.
5. Canon/character/knowledge/object/timeline regression.
6. Physics/legal/professional regression.
7. Hook/retention regression.
8. Human-prose/spelling/YouTube regression.
9. Blind full read #1.
10. Blind full read #2.
11. Numeric fixed-rubric re-score — always publish the score.

Handling findings:
- approved patch incomplete → repair inside its authorized zone;
- TRUE REGRESSION → repair/revert under REG(Pxx) inside original scope;
- PRE-EXISTING QA MISS/PATCH-EXPOSED outside scope → report `NQxx`, do not edit;
- pure preference → ignore.

Do not return an interim patch implementation with a true regression. But do return the completed approved revision with its honest score/status even if unapproved NQxx findings mean Publication Readiness is below target.

# M. FINAL PASS CRITERIA

## PATCH EXECUTION PASS
Requires simultaneously:
- every approved Pxx/Oxx fixed;
- no unauthorized diff;
- every Immutable Pass Zone identical to baseline;
- no approved-patch-caused regression;
- approved length intent respected.

## PUBLICATION READY
Separately requires:
- numeric score >=98/100;
- all shared hard gates PASS, including 70k–80k length;
- no remaining actionable defect.

If new unapproved `NQxx` findings prevent READY, show them and the numeric score. Do not modify their spans until user authorizes a new patch cycle.
