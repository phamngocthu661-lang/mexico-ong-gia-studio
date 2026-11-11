# Viết Kịch Bản Homeless — v1.6.9 THREE-STAGE PERSIST-FIRST

**HOMELESS V11 — step3 ba lượt:** Gõ `step3` lần 1 để viết A (Part 1–2), lần 2 B (Part 3–5), lần 3 C (Part 6–7), rồi ghép nguyên bytes A+B+C thành một FULL_SCRIPT đã kiểm chuẩn.

- Mỗi lượt **thực sự viết và lưu** một file TXT có prose American English, kiểm segment + SHA-256 và cập nhật manifest; mặc định trả link file thật (không bắt buộc in toàn văn trong chat).
- Đọc `SKILL.md`, `references/THREE_STAGE_PERSIST_PROTOCOL.md` và các mandatory references của skill.
- A/B là partial drafts, chỉ sau C mới kiểm full exact body 70.000–80.000 ký tự bằng `scripts/verify_full_script.py` và bàn giao cho QA step4.
- Các scripts là công cụ kiểm file/proof/assembly, **không tự sinh văn học**, không xác nhận chất lượng narrative/QA.
- Giữ canon/forensic/retention/7 Part, không filler, không bịa source/hashes. Không dùng `next`/`continue`, không `WORKFLOW_STATUS`.

## Các lệnh tiện ích

```bash
python scripts/segment_workflow.py stage --title 'EXACT TITLE' --segment A --file /mnt/data/HML_<sha12>_SCRIPT_A.txt
python scripts/segment_workflow.py inspect --title 'EXACT TITLE'
python scripts/segment_workflow.py assemble --title 'EXACT TITLE'
python scripts/verify_full_script.py /mnt/data/HML_<sha12>_FULL_SCRIPT.txt
```

Nếu fail, giữ dữ liệu thật đã được xác minh và chạy lại cùng `step3` để hoàn thành phase còn thiếu. Không reset bản thảo và không tự gợi `step4` khi mới có A/B.


## HOMELESS V3.0 — REQUIRED COMMON CONTRACT
See `references/HOMELESS_V3_CROSS_SKILL_CONTRACT.md` + `references/HANDOFF_SCHEMAS_V3.md`. Includes self-contained `scripts/homeless_controller.py` and dependency scripts for offline file-state gates. To orchestrate all 5 skills, use PROJECT_INSTRUCTIONS in the **total** ZIP. The original core/source materials are retained.
