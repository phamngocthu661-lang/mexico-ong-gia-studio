# PADRE MX V4.0 — MASTER CONTROLLER / 5 SKILL / 6 STEP

**Scope:** Historical corpus + local project memory only. **KHÔNG Channel Audit, KHÔNG nghiên cứu thị trường, KHÔNG vidIQ bắt buộc.** No live external intelligence is added in V4.

## Owners and routing

| STEP | Owner | Source of truth | Deliverable and gate |
|---|---|---|---|
| 1 | Skill 01 — Title | User seed, retained channel DNA, supplied offline benchmark, local project memory | Five titles, winner, exact LOCKED_TITLE and distinctive five-field originality signature. Run offline duplicate check. |
| 2 | Skill 02 — Outline | LOCKED_TITLE and creative selector | Exact seven-Part `CURRENT_FINAL_OUTLINE.txt` + `STORY_BLUEPRINT_V4.json`; validate creative structure before drafting. |
| 3 A/B/C | Skill 03 — Writer | Exact LOCKED_TITLE, outline, V4 blueprint | Persisted A(20–24k), B(30–35k), C(20–25k), seven Parts each >=8.5k, 70–80k total; `LEDGER_INIT` → `LEDGER_A` → `LEDGER_B` → `LEDGER_C`. |
| 4 ROUND1 | Skill 04 — QA | Exact full script + V4 blueprint | Independently review 100% logic; compute source windows; `AUDIT_R1_FROZEN.json`, optional `REPAIR1_CONTRACT.json`. |
| 5 REPAIR1 | Skill 03 — Writer | Authorized R1 contract | Precisely fix all CONFIRMED logic issues, preserve other bytes, produce `SCRIPT_REVISED_R1.txt` and `REPAIR1_PROOF.json`. |
| 4 ROUND2 | Skill 04 — QA | Exact R1 result + V4 blueprint | New full-range review of logic regressions + quality; protected PASS spans; `AUDIT_R2_FROZEN.json`, optional `REPAIR2_CONTRACT.json`. |
| 5 REPAIR2 | Skill 03 — Writer | Authorized R2 contract | Only confirmed FAIL and NEEDS_IMPROVEMENT zones, preserve PASS; `SCRIPT_FINAL_R2.txt`, `REPAIR2_PROOF.json`. |
| FINAL VERIFY | Skill 04 — QA | Source lineage, proofs and fresh report | `QA_FINAL_V4.json`, score >=95, no remaining/new issues, full structure, signed immutable hashes. No 3rd repair. |
| 6 | Skill 05 — SEO | Exact V4 PASS script + blueprint | SEO metadata + `THUMBNAIL.png` and `THUMBNAIL-NENXANH.png`, pixel-aligned same person, valid 80/20 split. |

## V4 new gates

1. **Offline originality**: compare title and five-part causal signature against locally saved completed projects; use historical supplied corpus only as an optional reference. `REVIEW` requires editor judgment; `BLOCK` requires alternative title/story mechanism.
2. **Creative Blueprint**: one Primary DNA, one/two Secondary DNA, one Story Mode, one Hook Pattern, one Narrative Spine; 7 Parts with 8–12 scenes and >=2 retention beats each; >=3 seeded payoffs; knowledge, evidence and time maps. Requires structurally valid JSON saved on disk.
3. **Continuity Ledger**: every A/B/C stage checkpoint is grounded in actual segment bytes and exact quotes. This binds recorded scene facts, knowledge gains, objects and open/closed loops. The tool checks structural claims, not literary truth.
4. **QA range attestation**: create a fresh `range-plan` per audited source, verify one exact quote *per* derived window with SHA and >=3 checked dimensions. Coverage counters must match the real plan, not just a declared number. This does **not** prove actual reading; independent editors still must read all text.
5. **PASS protection**: frozen round2 passage quotations include source Part. Final verifies actual presence/count and rejects modified passage without an authorized R2 dependency override. `pass_spans_preserved` reports the number of intact tracked spans.
6. **Strong thumbnail QA**: green left 78% tested as exact RGB(0,255,0), portrait bbox approx right 20%, and interior portrait pixel equality >=98.5% across the real pair. Final visual inspection is still needed.
7. **Memory registration after PASS only**: append project signature to persistent `PADRE_MX_PROJECT_MEMORY_V4.json` only after V4 final PASS and exact QA/blueprint/script SHA verified.

## Identities and length locks (unchanged)
- `title_sha12 = sha256(title UTF-8)[:12]`.
- `outline_sha256 = sha256(raw outline bytes)`.
- `video_id = sha256(title + '\n' + outline_sha256)[:16]`.
- `blueprint_sha256` is an additional V4 hard identity field.
- 7 ordered `[PART 1]`…`[PART 7]` lines, UTF-8 LF no BOM; total Unicode prose body 70,000–80,000; each PART >=8,500.
- Stage A 20,000–24,000 (Parts1–2), B 30,000–35,000 (Parts3–5), C 20,000–25,000 (Parts6–7).
- Exactly 2 independent audits, 0–2 permitted actual repairs, never a third. A skipped repair remains skipped.
- QA source protection uses byte-exact UTF-8 offsets and immutable signed frozen artifacts; AI reviewers themselves remain responsible for semantic quality.

## User calls
- `CHẠY PADRE MX V4.0 — STEP 1: tạo 5 tiêu đề, kiểm tra trùng trong PROJECT MEMORY, khóa 1 tiêu đề.`
- `CHẠY PADRE MX V4.0 — STEP 2: lập 7 PART, khóa STORY_BLUEPRINT_V4 và canon.`
- `CHẠY PADRE MX V4.0 — STEP 3 A/B/C: viết đủ ký tự, lưu file thực và checkpoint Continuity Ledger.`
- `CHẠY PADRE MX V4.0 — STEP 4 ROUND1 → STEP 5 REPAIR1 → STEP 4 ROUND2 → STEP 5 REPAIR2 → FINAL VERIFY. Không sửa lần ba.`
- `CHẠY PADRE MX V4.0 — STEP 6: chỉ đóng gói SEO + 2 thumbnail thực khi FINAL QA V4 PASS.`

## CLI examples
See `V4_QUICK_START_AND_COMMANDS.md`. Every `audit`, `repair`, and `final` command now requires `--blueprint STORY_BLUEPRINT_V4.json`. Existing V3 frozen files are **not valid V4 artifacts** and cannot be relabeled or assumed converted.
