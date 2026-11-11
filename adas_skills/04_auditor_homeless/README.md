# Kiểm Tra Kịch Bản — v1.8.1 CHECKPOINT + RESUME

Upgrade tương thích MODE A / MODE B v1.8.0, bổ sung **checkpoint thật cho QA chưa hoàn thành**, công cụ xác minh provenance/coverage/score + đóng băng Frozen Patch Ledger sau khi toàn bộ kiểm tra đã thực sự xong.

**Không phải một mô hình tự động phát hiện lỗi văn học:** công cụ chỉ kiểm tính nhất quán của bằng chứng do reviewer nhập. Không tự chấm, tự PASS, tự lấp ô coverage hay tự tạo lỗi.

**Bước nhập & xuất:**

```sh
python scripts/qa_checkpoint.py init /mnt/data/HML_<title_sha12>_FULL_SCRIPT.txt --title 'EXACT LOCKED TITLE' --out /mnt/data/HML_<title_sha12>_QA_CHECKPOINT.json
# Biên tập viên THỰC SỰ kiểm script, ghi từng phase/Part×dimension, Pxx, saturation, điểm vào JSON; lưu liên tục.
python scripts/qa_checkpoint.py inspect /mnt/data/HML_<title_sha12>_QA_CHECKPOINT.json
python scripts/qa_checkpoint.py freeze /mnt/data/HML_<title_sha12>_QA_CHECKPOINT.json --out /mnt/data/HML_<title_sha12>_QA_FROZEN.json
```

- `init` tạo checkpoint **toàn PENDING** với count/hash thực tế.
- `inspect` kiểm progress và hash lại source; exit 2 nếu chưa hoàn thành/đổi source.
- `freeze` chỉ cho phép lập manifest sau khi thực sự hoàn tất và saturation đầy đủ 0 lỗi mới; exit 2 nếu còn blocker.
- Nếu bị ngắt, cung cấp checkpoint thật và hướng dẫn user gọi lại `step4` để **tiếp tục chính bước QA này**, không gợi `step5`/`step6` sớm.
- Frozen JSON là đầu vào hỗ trợ; MODE A vẫn phải xuất full QA report + score/readiness + frozen patch ledger người dùng có thể duyệt.
- MODE B strict surgical rewrite giữ đúng rule v1.8.0.

**V1.8.0 CRITICAL:** QA now FAILS CLOSED before scoring unless the exact current full-script body has been machine-counted and hashed. `LENGTH UNVERIFIED` is no longer a valid completed-audit state. Old counts may never be reused for new bodies.

**Current version: 1.8.0 — One-sweep exhaustive QA + saturation freeze + exact-copy revision.**

# Kiểm Tra Kịch Bản — V1.6.0

Skill forensic editor cho workflow:

**1 review exhaustive + score thật → 1 strict authorized revision → regression re-score**

## Review
- khóa MASTER BASELINE và đếm ký tự từng Part + tổng;
- đọc toàn bộ tối thiểu 2 lần;
- liệt kê mọi actionable defect, không giới hạn;
- vị trí patch phải exact bằng Part/scene/quote anchors hoặc lines;
- nếu phải rewrite cả Part, ghi ngay `REWRITE ENTIRE PART` + MUST PRESERVE + target length;
- trước khi publish ledger, simulate dependencies/length effect để tránh sửa xong mới phát hiện chuỗi lỗi mới;
- dừng và chờ lệnh.

## Rewrite
- không generate lại full Part từ trí nhớ;
- patch trên MASTER BASELINE;
- mọi đoạn ngoài approved Patch Ledger = **IMMUTABLE PASS ZONE, giữ nguyên văn**;
- global compression bị cấm nếu không có enumerated scope;
- mọi changed span phải map tới Patch ID/dependency đã được pre-authorize; không có internal late-fix authority mở rộng scope;
- Part/total character count phải PASS regression;
- blind re-audit toàn script 2 lần;
- TRUE REGRESSION chỉ sửa trong patch scope; lỗi baseline mới ngoài scope chỉ NQxx report;
- **luôn xuất POST_REVISION_SCORE dù thấp hoặc hard-fail**.

## Length protection
**HARD full-script PASS range: 70,000–80,000 characters inclusive.**
- baseline <70k: review must authorize functional expansion to range;
- baseline >80k: authorize controlled compression to range;
- baseline in range: preservation bands apply;
- any revised full script outside range = HARD FAIL; do not label the body publication-ready, but **still output numeric score + exact length + hard-gate/Patch Execution/Readiness status**.

## Early retention hard audit
~200 promise → ~400 proof → ~650 stakes → ~1,100 micro-payoff #1 → ~2,000 next action → ~5,000 micro-payoff #2; no Hook Reset; no ~6,500-char retention desert.

## Core rules
**COPY WHAT PASSES. PATCH WHAT FAILS.**  
**NO UNAUTHORIZED DIFF.**  
**NO COMPRESSION SPILLOVER.**  
**REVIEW ONCE, PATCH ONLY THE APPROVED FAILURES, RE-AUDIT WHOLE SCRIPT, REPORT NEW OUT-OF-SCOPE FINDINGS WITHOUT EDITING THEM.**


V1.6.0 shares `CROSS_SKILL_QUALITY_CONTRACT.md` V1.3 with Outline V2.3.1 and Script V1.6.1: fixed rubric, HARD 70k–80k character range, Early Retention Survival, State Delta, Defect Universe Freeze and regression classification. Threshold remains >=98.

## Strict score/preservation rule
**PATCH WHAT THE AUDIT FOUND. COPY EVERYTHING ELSE EXACTLY. SCORE THE RESULT HONESTLY.**
A low score is never hidden. READY remains >=98 + all hard gates PASS.


## HOMELESS V3.0 — REQUIRED COMMON CONTRACT
See `references/HOMELESS_V3_CROSS_SKILL_CONTRACT.md` + `references/HANDOFF_SCHEMAS_V3.md`. Includes self-contained `scripts/homeless_controller.py` and dependency scripts for offline file-state gates. To orchestrate all 5 skills, use PROJECT_INSTRUCTIONS in the **total** ZIP. The original core/source materials are retained.
