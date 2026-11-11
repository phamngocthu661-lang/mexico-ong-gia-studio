# HOMELESS 5 SKILLS V3.0 — HƯỚNG DẪN SỬ DỤNG

## 1. Cài đặt

Trong **ZIP tổng**, mở `01_INSTALL_5_SKILLS/`, cài lần lượt 5 ZIP trong ChatGPT Skills:

1. `01_VIRAL_TITLE_REWRITER_V3.zip` — viết lại/khóa tiêu đề (tùy nhu cầu)
2. `02_HOMELESS_OUTLINE_V3.zip` — giàn ý 7 Part
3. `03_HOMELESS_SCRIPT_WRITER_V3.zip` — kịch bản A/B/C
4. `04_HOMELESS_FORENSIC_AUDITOR_V3.zip` — QA 98 và sửa lỗi có ticket
5. `05_HOMELESS_SEO_TRAILER_V3.zip` — SEO, thumbnail prompt, OMNI trailer prompt

Tạo một ChatGPT Project và sao chép nội dung `PROJECT_INSTRUCTIONS_COPY_PASTE.md` vào **Project Instructions**. Nếu dùng Python Controller, giữ thêm thư mục `02_CONTROLLER_AND_GUIDES/`. Mỗi ZIP skill V3 có `scripts/homeless_controller.py` tự chứa mã giống nhau; các file SHA chỉ được bảo đảm sau khi chạy các công cụ trên file thật.

**Không yêu cầu Channel Audit, nghiên cứu thị trường, vidIQ, đối thủ hay web scraping.** Lịch sử chống trùng do bạn tự lưu trong JSON cục bộ.

## 2. Dùng bằng lệnh trong chat

| Lệnh mẫu | Hành động | Kết quả cần có |
|---|---|---|
| `step1 — viết lại tiêu đề` | Title Rewriter | 1 title đã kiểm 100 ký tự và card khóa |
| `step2 — lập giàn ý cho title này` | Outline | Detailed 7 PART + `STORY_BLUEPRINT.json` |
| `step3` lần 1 | Writer A | `HML_<sha12>_SCRIPT_A.txt` + handoff A |
| `step3` lần 2 | Writer B | File B + handoff B |
| `step3` lần 3 | Writer C | File C, manifest, full manuscript đã verify |
| `step4` | QA review only | Checkpoint + frozen report hoặc pending item |
| `step5` | Controlled repair | File revision mới, patch proof, chờ QA mới |
| `step6` | SEO/thumbnail/trailer | Metadata, prompt, fact-lock, không nhận là đã render |

Nếu đầu vào đã có **LOCKED_TITLE**, có thể bỏ step1 và thực hiện step2. Nếu chỉ cần một skill, nó có thể chạy độc lập; các cổng chưa kiểm sẽ được ghi chú riêng.

## 3. Dùng Controller ngoại tuyến (Python >=3.9, không cài thư viện ngoài)

Đặt biến `CTL=.../homeless_controller.py` hoặc thay bằng đường dẫn thật:

```bash
python homeless_controller.py init --project ./HML_PROJECT --title "EXACT USER-APPROVED TITLE" --memory ./SHARED_MEMORY.json
python homeless_controller.py lock-title --project ./HML_PROJECT --card ./HML_PROJECT/TITLE_CARD.json
python homeless_controller.py lock-outline --project ./HML_PROJECT --blueprint ./HML_PROJECT/STORY_BLUEPRINT.json
```

Phải lưu ba file script theo đúng tên `HML_<sha12>_SCRIPT_[A|B|C].txt` (tính `sha12` bằng SHA256 UTF-8 của title):

```bash
python homeless_controller.py stage --project ./HML_PROJECT --directory ./HML_PROJECT --segment A --file ./HML_PROJECT/HML_<sha12>_SCRIPT_A.txt --handoff ./HML_PROJECT/CONTINUITY_HANDOFF_A.json
python homeless_controller.py stage --project ./HML_PROJECT --directory ./HML_PROJECT --segment B --file ./HML_PROJECT/HML_<sha12>_SCRIPT_B.txt --handoff ./HML_PROJECT/CONTINUITY_HANDOFF_B.json
python homeless_controller.py stage --project ./HML_PROJECT --directory ./HML_PROJECT --segment C --file ./HML_PROJECT/HML_<sha12>_SCRIPT_C.txt --handoff ./HML_PROJECT/CONTINUITY_HANDOFF_C.json
python homeless_controller.py assemble --project ./HML_PROJECT --directory ./HML_PROJECT
```

Tại đây có file full thật 7 PART, 70k–80k ký tự đúng cách đếm. Sau đó:

```bash
python qa_checkpoint.py init ./HML_PROJECT/HML_<sha12>_FULL_SCRIPT.txt --title "EXACT USER-APPROVED TITLE" --out ./HML_PROJECT/QA_CHECKPOINT.json
# Reviewer điền bằng chứng thực tế, rubric và defect vào QA_CHECKPOINT.json
python qa_checkpoint.py inspect ./HML_PROJECT/QA_CHECKPOINT.json
python qa_checkpoint.py freeze ./HML_PROJECT/QA_CHECKPOINT.json --out ./HML_PROJECT/QA_FROZEN.json
python homeless_controller.py attach-qa --project ./HML_PROJECT --frozen ./HML_PROJECT/QA_FROZEN.json
```

Nếu QA NOT READY, Writer tạo bản sửa **file mới** và lập `REPAIR_PLAN.json`, kiểm tra rồi cam kết:

```bash
python homeless_controller.py verify-patch --project ./HML_PROJECT --candidate ./HML_PROJECT/FULL_SCRIPT_REV1.txt --plan ./HML_PROJECT/REPAIR_PLAN.json
python homeless_controller.py commit-patch --project ./HML_PROJECT --candidate ./HML_PROJECT/FULL_SCRIPT_REV1.txt --plan ./HML_PROJECT/REPAIR_PLAN.json
# Bắt buộc tạo lại checkpoint và audit trên chính bản sửa REV1, rồi attach-qa lần nữa.
```

Chỉ sau `QA_READY`:

```bash
python homeless_controller.py verify-seo --project ./HML_PROJECT --pack ./HML_PROJECT/SEO_PACK.json
python homeless_controller.py remember --project ./HML_PROJECT
python homeless_controller.py status --project ./HML_PROJECT
```

## 4. Những điều chưa thể tự kiểm bằng Python

Độ hay của câu chuyện, nguyên bản thực chất, các sự kiện hợp lý trong bối cảnh Mỹ, chất lượng hook, retention thực tế, nội dung lời thoại tự nhiên, tính chính xác hình thumbnail và trailer dựng thực tế. Các cổng này phải đánh giá bằng biên tập viên/AI với bằng chứng từ toàn bộ kịch bản. Giá trị `score=98` trong JSON không tự chứng minh đã đạt chất lượng 98.

## 5. Trạng thái có ý nghĩa

`TITLE_PENDING → TITLE_LOCKED → OUTLINE_LOCKED → STAGING_A → STAGING_B → STAGING_C → SCRIPT_READY_FOR_QA → QA_NOT_READY / QA_READY → SEO_PACK_READY`.

Sau `commit-patch`, trạng thái quay về `SCRIPT_READY_FOR_QA`, mọi QA/SEO cũ không còn hợp lệ với SHA mới.

## 6. Kiểm thử

Chạy:

```bash
python tests/test_pipeline.py
python tests/test_repair.py
```

Đó là kiểm thử **cơ học với nội dung tổng hợp**, không phải thành phẩm chuyện Homeless được duyệt chất lượng.
