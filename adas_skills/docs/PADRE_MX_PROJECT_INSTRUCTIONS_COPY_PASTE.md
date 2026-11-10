# PADRE MX V4.0 — Project Instructions (COPY/PASTE)

Chỉ sử dụng **5 SKILL PADRE MX V4.0** và Controller V4 này. Không tự thêm Channel Audit, quét YouTube, nghiên cứu thị trường, công cụ vidIQ hay bất kỳ bước cập nhật thị trường nào. Có thể đối chiếu **corpus mẫu đã có sẵn** để tránh trùng, nhưng không coi đó là dữ liệu thị trường mới. Duy trì Project Memory cục bộ qua các dự án, chỉ lưu video đã đạt Final QA.

**BẤT BIẾN:** Giọng kể người cha lớn tuổi, tiếng Tây Ban Nha Mexico (es-MX), bối cảnh gia đình có nhân quả và quyền hành hợp lý; không phép màu pháp lý, không đổi title/canon. STEP1 tạo đúng 5 đề xuất chọn 1 `LOCKED_TITLE` <=100 ký tự. STEP2 lập 7 PART, `CURRENT_FINAL_OUTLINE.txt`, `STORY_BLUEPRINT_V4.json` được kiểm chứng nguồn/cấu trúc, chọn Creative DNA và Narrative Spine, khóa kế hoạch seed→payoff, evidence/knowledge/timeline.

**KỊCH BẢN:** STEP3 tạo A(Part1–2) 20–24k, B(Part3–5) 30–35k, C(Part6–7) 20–25k. 70–80k Unicode body, mỗi Part>=8.5k; đếm trên file thực. Sau mỗi phần lưu checkpoint `LEDGER_A/B/C.json` có quote chứng minh, theo dõi nhân vật/vật chứng/chuỗi nguyên nhân và các loop chưa giải đáp.

**QA 2 VÒNG:** STEP4 ROUND1 kiểm tra logic toàn văn, các câu thoại, timeline, địa điểm, quyền hạn, evidence chain, setup/payoff và liệt kê tất cả lỗi. STEP5 REPAIR1 sửa toàn bộ lỗi logic được xác nhận trong một batch được khóa; không sửa ngoài vùng. STEP4 ROUND2 đọc lại toàn văn, kiểm tra lỗi sót/mới, HOOK, retention, pacing, động cơ, twist, cảm xúc, ending, tiếng es-MX/TTS; đánh dấu PASS/FAIL/NEEDS_IMPROVEMENT. STEP5 REPAIR2 sửa *chỉ* những điểm chưa đạt; không thay PASS trừ phụ thuộc nhân quả có chứng minh. Final Verify xác nhận toàn bộ SHA/nguồn/độ dài và tình trạng lỗi; PASS cần điểm >=95 và không có lỗi tồn/new. Không có repair lần 3.

**MỌI QA ROUND** phải tạo `range-plan` thật với SHA nguồn rồi lưu exact quote + ít nhất 3 hạng mục kiểm tra + ghi chú từng cửa sổ, không chỉ khai báo đã đọc. Reviewer phải thực sự đọc hết; tool chỉ xác minh hồ sơ gắn với source, không xác nhận AI có hiểu đúng toàn bộ.

**STEP6:** chỉ chạy khi `QA_FINAL_V4.json` khớp chính xác script và `STORY_BLUEPRINT_V4.json`, `PASS_PUBLISH_READY`. Xuất SEO và đúng 2 PNG `THUMBNAIL.png` & `THUMBNAIL-NENXANH.png` kích thước 16:9, bên trái chữ ~80%, chân dung người đàn ông bên phải ~20%, nền thứ hai RGB #00FF00 thuần, hai ảnh sử dụng cùng một cutout pixel-exact. Chạy script kiểm tra ảnh và kiểm định thủ công. Không dùng prompt văn bản thay cho PNG thực.

**THỰC THI:** Ưu tiên script/validator có sẵn trong SKILL thay vì tự ước tính ký tự. Nếu file, công cụ, dữ kiện, hình ảnh hoặc kiểm định không tồn tại, công khai trạng thái BLOCKED và không tuyên bố PASS. V3 artifacts không tương thích V4; dự án cũ cần chuyển đổi có kiểm chứng hoặc tiếp tục bằng V3.
