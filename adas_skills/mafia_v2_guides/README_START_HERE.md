# Mafia Maid × Người Hầu — 5 SKILLS V2.0

Bản nâng cấp trực tiếp từ 5 ZIP do người dùng gửi: Title v1.2, Outline v1.1, Script v1.4, Forensic QA v1.1, SEO v1.3.

**Không thêm Channel Audit hoặc nghiên cứu thị trường. Không thay đổi hệ DNA A/B/C gốc, giới hạn bài viết hay template SEO 12 mục.**

## Cấu trúc ZIP tổng
- `01_INSTALL_5_SKILLS`: năm ZIP có thể cài độc lập, mỗi file có SKILL.md, tài liệu legacy, bộ điều khoản V2 và bản sao công cụ CLI.
- `02_CONTROLLER_AND_GUIDES`: controller Python + hướng dẫn Project + thư viện contract, templates và test.
- `03_FULL_SOURCE`: toàn bộ source trước khi đóng gói.
- `04_ORIGINAL_BACKUPS`: bản sao chính xác năm ZIP được gửi.
- `05_REPORTS`: test log, danh sách files, manifest SHA256.

## Cài đặt
1. Giải nén ZIP tổng.
2. Cài 5 ZIP từ `01_INSTALL_5_SKILLS` vào Skills của ChatGPT (mỗi ZIP là một skill riêng).
3. Sao chép `PROJECT_INSTRUCTIONS_COPY_PASTE.md` vào Project Instructions của dự án.
4. Giữ `02_CONTROLLER_AND_GUIDES` trên máy để chạy kiểm chứng địa phương nếu cần; Python 3.9+, không cần thư viện ngoài.
5. Tạo dự án mới cho V2: không tự nâng cấp trạng thái SHA đã khóa từ bản gốc.

## Chạy cơ bản (terminal)
```bash
python maid_pipeline.py init --project ./runs/maid_001 --id maid_001
python maid_pipeline.py title --project ./runs/maid_001 --input ./title.json --memory ./content_memory.json
python maid_pipeline.py outline --project ./runs/maid_001 --input ./outline.json
python maid_pipeline.py script --project ./runs/maid_001 --input ./script.txt
python maid_pipeline.py continuity --project ./runs/maid_001 --input ./continuity.json
python maid_pipeline.py qa --project ./runs/maid_001 --input ./qa.json
# Nếu WAIT_REPAIR và đã được người dùng cho phép:
python maid_pipeline.py repair --project ./runs/maid_001 --input ./patch.json
# Bắt buộc chạy lại continuity, qa trước khi SEO.
python maid_pipeline.py seo --project ./runs/maid_001 --input ./seo.json
python maid_pipeline.py verify --project ./runs/maid_001
```
Các file JSON mẫu ở `templates/` là cấu trúc tham khảo, chưa phải kịch bản/QA thực tế. Lấy SHA từ `state.json`, không tự gõ bừa. `seo` chạy sau QA READY; nếu chỉ có tiêu đề/dàn ý, SEO có thể soạn DRAFT theo skill gốc nhưng không thể xác nhận publish readiness.

## Giới hạn
Kiểm thử tự động chỉ kiểm tra cấu trúc, ký tự/từ, SHA, cue, mốc continuity tự khai báo, mức điểm toán học, vị trí quote, phạm vi patch và tính đầy đủ của SEO. Không thể tự chứng minh chất lượng cảm xúc, đủ bằng chứng đời thực hoặc độ an toàn của mọi tình huống; phải có biên tập độc lập.
