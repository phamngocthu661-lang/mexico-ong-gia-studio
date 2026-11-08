# HƯỚNG DẪN CHUYỂN ỨNG DỤNG MEXICO ÔNG GIÀ STUDIO SANG MÁY TÍNH KHÁC

Ứng dụng **Mexico Ông Già Studio** được thiết kế độc lập (Self-contained). Bạn có thể copy toàn bộ thư mục sang máy tính khác hoặc dùng bộ cài `.zip` chuẩn dành cho khách hàng.

---

## 🖥️ 1. YÊU CẦU CẤU HÌNH TRÊN MÁY TÍNH MỚI

| Thành phần | Máy có Card NVIDIA (Khuyên dùng) | Máy chỉ có CPU (Máy văn phòng / Laptop) |
| :--- | :--- | :--- |
| **Hệ điều hành** | Windows 10 hoặc Windows 11 (64-bit) | Windows 10 hoặc Windows 11 (64-bit) |
| **Phần cứng GPU** | Card đồ họa NVIDIA (GTX 1660, RTX 2060, 3060, 4060, 4070...) | CPU Core i5 / i7 / i9 hoặc AMD Ryzen |
| **Phần mềm bắt buộc** | 1. Python 3.10 hoặc 3.11<br>2. FFmpeg (đã tích hợp sẵn trong `bin/`) | 1. Python 3.10 hoặc 3.11<br>2. FFmpeg (đã tích hợp sẵn trong `bin/`) |

---

## ⚙️ 2. ĐÓNG GÓI & CÀI ĐẶT KHI SANG MÁY MỚI (CHỈ LÀM 1 LẦN)

0. **Đóng gói Bộ Cài Khách Hàng chuẩn (Dành cho Admin):**
   - Nhấp đúp vào **`ADMIN_KEYGEN\Dong_Goi_Bo_Cai_Khach_Hang.bat`** để tự động xuất ra file **`D:\Mexico_Ong_Gia_Studio_Bo_Cai_Khach_Hang.zip`** và **`D:\Mexico_Ong_Gia_Studio_Ban_Update_Nhanh.zip`** (tương thích 100% với `Extract All...` của Windows Explorer, đã lọc sạch Key Admin, Cookie Chrome và video nháp).
1. **Giải nén `Mexico_Ong_Gia_Studio_Bo_Cai_Khach_Hang.zip`** sang máy mới (tốt nhất đặt ở ổ `D:\Mexico_Ong_Gia_Studio`).
2. **Chạy file cài đặt tự động 1-Click**:
   - Nhấp đúp vào file 👉 **`Cai_Dat_May_Moi.bat`**
   - Hệ thống tự động cài đặt Python 3.11 (nếu chưa có), PyTorch GPU CUDA, FastAPI, PyWebView, yt-dlp, faster-whisper và tải Model AI OmniVoice.
3. **Bắt đầu sử dụng**:
   - Nhấp đúp vào 👉 **`Mexico_Ong_Gia.exe`** (hoặc `Chay_App.bat`) để nhập Key `MEXICO-...` và mở ứng dụng Desktop!
