# PROJECT INSTRUCTIONS — MAFIA MAID / NGƯỜI HẦU V2.0

## ROLE ROUTER (exactly 5 skills)
1. `viet-lai-tieu-de-mafia-nguoi-hau` → Viết lại/đề xuất tiêu đề (5 ứng viên, chọn 1; title ≤100 ký tự).
2. `viet-gian-y-nguoi-hau` → Giàn ý & Story Blueprint; chọn DNA A/B/C; số BEAT động.
3. `viet-kich-ban-nguoi-hau-tu-gian-y` → Viết SCRIPT từ outline, PART 1:1 với BEAT.
4. `kiem-tra-kich-ban-nguoi-hau` → Forensic review ONLY hoặc CONTROLLED REWRITE theo lệnh người dùng.
5. `viet-seo-nguoi-hau` → SEO, 3 thumbnail hypotheses, 16:9 image prompt và 8s hook video prompt.

## LOAD ORDER
Read each installed skill's SKILL.md plus `references/V2_0_INTEGRATION_CONTRACT.md`, which overrides conflicting legacy text. Keep title/outline/script/continuity/QA files for traceability. Do not assume vidIQ, internet access, file-write permissions, image or video generation tools exist.

## HARD CONTRACT
Title once locked is immutable across skills and full project. New title for a different video = new project. DETAILED OUTLINE Beat count N maps to exactly N PARTS. Script American English; NFC visible characters 44,000–48,000 and 7,400–7,650 words; STRICT <8,000 words, emergency 40,000–55,000 chars; no bracket TTS cues. Use real counters, no invented counts.

## CREATIVE & QC
Heroine materially solves major problem; earned competence; credible leverage/evidence, timeline, knowledge, injury, consent and causality; no unseeded deus ex machina. QA skill REVIEW ONLY by default; after explicitly authorized repair ticket, apply minimal exact replacement and re-audit entire revised script. Preserve OPB; invalidate prior QA after any change. No more than two automatic repair cycles. Correct forensic rubric determines score; READY requires zero known actionable defects, not a numerical shortcut.

## SEO
Require a verified current full script+QA READY for PUBLISHABLE package. PRIMARY TITLE verbatim and exactly 2 distinct supporting titles ≤100 characters. Default output 12 sections from original production template, 3 thumbnail hypotheses, 1 16:9 thumbnail image prompt and 1 8-second video hook prompt. Earlier stages may create DRAFT only, never claim script-verified packaging. If user explicitly provides a new title in a *new run*, create a new project, do not overwrite a locked project title.

## LOCAL VALIDATION
If runtime/tool exists, use bundled `maid_pipeline.py` with title → outline → script → continuity → qa → repair (if permitted) → seo. If unavailable, mark mechanical checks NOT RUN and provide the missing verification work explicitly. No Channel Audit or market research.
