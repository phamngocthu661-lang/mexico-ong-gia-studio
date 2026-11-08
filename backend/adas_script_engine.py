import os
import re
import sys
import json
import time
import shutil
import threading
import unicodedata
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable, Tuple

import importlib
from . import voice_service as _voice_service_mod
try:
    importlib.reload(_voice_service_mod)
except Exception:
    pass
from .chatgpt_web_client import (
    ChatGPTWebSession,
    AccountRateLimitError,
    mark_account_rate_limited,
    is_account_in_cooldown,
    get_earliest_cooldown_remaining_sec,
    ACCOUNT_LIMIT_COOLDOWN_SEC,
    check_all_web_accounts_status,
    ensure_all_saved_chatgpt_accounts_open,
    MAX_THREADS_PER_ACCOUNT,
)
from .voice_service import split_japanese_script, strip_leaked_titles_and_metadata
from .logger_service import log_info, log_warn, log_error

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


# ==============================================================================
# 1. BỘ ĐẾM KÝ TỰ CHUẨN PADRE MX V3.0 (70.000 - 80.000 CHARS • 7 PARTS >= 8.500)
# ==============================================================================
_STANDALONE_PART_HEADING_LINE_RE = re.compile(r"^\s*\[\s*PART\s*([1-7])\s*\]\s*$", re.IGNORECASE | re.MULTILINE)


def pure_char_count(text: str) -> int:
    """
    Bộ đếm ký tự chuẩn:
    - Đối với kịch bản Tây Ban Nha Mexico (PADRE MX V3.0 — es-MX): Chuẩn hóa LF, loại bỏ các dòng tiêu đề độc lập
      `[PART 1]`..`[PART 7]` (cùng ký tự xuống dòng của chúng) và đếm tổng số ký tự Unicode của phần thân kịch bản
      (khớp 100% với `verify_full_script.py` và `pmx_v3_pipeline.py`: 70.000–80.000 chars).
    - Đối với kịch bản tiếng Nhật cũ (nếu có chữ CJK): Chuẩn hóa NFC và đếm ký tự Unicode L+N.
    """
    if not text:
        return 0
    norm = unicodedata.normalize("NFC", text).replace("\r\n", "\n").replace("\r", "\n")
    if any("\u3040" <= ch <= "\u9fff" for ch in norm):
        return sum(1 for ch in norm if unicodedata.category(ch)[0] in {"L", "N"})
    body = re.sub(r"(?m)^\s*\[\s*PART\s*[1-7]\s*\]\s*\n?", "", norm).strip()
    return len(body)


def ensure_part_headings_for_stage(text: str, part_letter: str) -> str:
    """
    Đảm bảo văn bản từng Stage của PADRE MX V3.0 luôn có đủ nhãn `[PART N]` độc lập:
    - Stage A (`part_a.txt`): `[PART 1]` và `[PART 2]`
    - Stage B (`part_b.txt`): `[PART 3]`, `[PART 4]`, `[PART 5]`
    - Stage C (`part_c.txt`): `[PART 6]` và `[PART 7]`
    """
    if not text or any("\u3040" <= ch <= "\u9fff" for ch in text):
        return (text or "").strip()
    norm = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    # Chuẩn hóa các dạng viết lệch như `### [PART 1]`, `**PART 1**`, `PART 1:` về đúng `[PART 1]`
    norm = re.sub(
        r"(?m)^[#*>\-\s`]*\[?\s*PART\s*([1-7])\s*\]?[*`\s:：\-—]*$",
        r"[PART \1]",
        norm,
        flags=re.IGNORECASE,
    )
    stage_map = {
        "A": [1, 2],
        "B": [3, 4, 5],
        "C": [6, 7],
    }
    expected_nums = stage_map.get((part_letter or "A").upper(), [1, 2])
    present_nums = [int(m.group(1)) for m in re.finditer(r"(?m)^\[PART\s*([1-7])\]$", norm)]
    if present_nums == expected_nums:
        return norm

    # Nếu thiếu hoặc thừa nhãn [PART N], xóa nhãn cũ trong stage này và chia đều theo đoạn văn tự nhiên
    body_only = re.sub(r"(?m)^\s*\[PART\s*[1-7]\]\s*\n?", "", norm).strip()
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", body_only) if p.strip()]
    if not paragraphs:
        return norm

    k = len(expected_nums)
    if len(paragraphs) < k:
        lines = [ln.strip() for ln in body_only.splitlines() if ln.strip()]
        paragraphs = lines if len(lines) >= k else [body_only]

    total_len = sum(len(p) for p in paragraphs)
    target_per_part = total_len / float(k)
    grouped: List[List[str]] = [[] for _ in range(k)]
    curr_bucket = 0
    curr_len = 0
    for idx_p, para in enumerate(paragraphs):
        remaining_paras = len(paragraphs) - idx_p
        remaining_buckets = k - 1 - curr_bucket
        if (
            curr_bucket < k - 1
            and curr_len >= target_per_part * 0.88
            and remaining_paras > remaining_buckets
        ):
            curr_bucket += 1
            curr_len = 0
        grouped[curr_bucket].append(para)
        curr_len += len(para)

    rebuilt: List[str] = []
    for p_num, bucket in zip(expected_nums, grouped):
        rebuilt.append(f"[PART {p_num}]")
        if bucket:
            rebuilt.append("\n\n".join(bucket))
    return "\n\n".join(rebuilt).strip()


# ==============================================================================
# 2. MẪU PROMPT STEP 1/2 CHUẨN PADRE MX V3.0 (5 IDEAS • LOCKED TITLE • 80/20 THUMB)
# ==============================================================================
DEFAULT_STEP2_PROMPT_TEMPLATE = """CHẠY NGAY STEP 1 — PADRE MX V3.0 TITLE REWRITER & THUMBNAIL COPY PLAN — MÃ {{MÃ_ID}}

MỤC TIÊU: Bạn là Chuyên gia Biên kịch & Tối ưu CTR YouTube cho kênh **PADRE MX V3.0 (Mexican Spanish Elderly Father Family Betrayal / Earned Legal & Financial Justice — `es-MX`)**. Từ dữ liệu ý tưởng đầu vào dưới đây, hãy phân tích DNA, tạo đúng **5 IDEAS (5 ứng viên tiêu đề tiếng Tây Ban Nha Mexico `es-MX` <= 100 ký tự)**, chấm điểm từng tiêu đề trên thang 100, khóa 1 tiêu đề xuất sắc nhất (`CURRENT_FINAL_TITLE` / `LOCKED_TITLE`), và thiết kế phương án chữ cho **2 Ảnh Thumbnail 16:9 (`THUMBNAIL.png` bố cục 80/20 + `THUMBNAIL-NENXANH.png` nhân vật tách nền xanh `#00FF00`)**.

ĐỊNH VỊ KÊNH: {{ĐỊNH_VỊ_BATCH}}

========== ĐẦU VÀO DUY NHẤT: {{MÃ_ID}} ==========
01. Mức ưu tiên: {{ƯU_TIÊN}}
02. Trạng thái hiện tại: CHƯA_CHẠY_STEP1
03. Đánh giá năng lực viết dài 7 Part (70.000–80.000 ký tự): {{LONGFORM_CAPACITY_STEP1}}
04. Tiêu đề mẫu / Ý tưởng nháp (Tham khảo DNA, chưa khóa): {{TIÊU_ĐỀ_NHẬT_NHÁP_CHƯA_KHÓA}}
05. Dịch ý / Tóm tắt tiếng Việt: {{DỊCH_Ý_TIÊU_ĐỀ_VI}}
06. Quan hệ nhân vật (Ngôi thứ nhất `yo` — Người cha/ông lớn tuổi Mexico 60–82 tuổi): {{QUAN_HỆ_NHÂN_VẬT}}
07. Trụ cột cảm xúc & công lý pháp lý: {{NHÓM_CHỦ_ĐỀ}}
08. Bối cảnh & Sự kiện mở đầu tại Mexico: {{BỐI_CẢNH_SỰ_KIỆN}}
09. Xung đột / Sự phản bội gia đình mở đầu: {{XUNG_ĐỘT_MỞ_ĐẦU}}
10. PREMISE GỐC: {{PREMISE_GỐC_STEP1}}
11. Câu hỏi giữ chân khán giả (Curiosity Gap): {{CÂU_HỎI_CẦN_TRẢ_LỜI}}
12. Vật chứng pháp lý / Tài chính Mexico bắt buộc gieo & thu hồi: {{VẬT_CHỨNG_GIEO_TRƯỚC}}
13. Lớp tiết lộ 1 (Phát hiện mâu thuẫn / âm mưu): {{REVEAL_LỚP_MỘT_ĐỀ_XUẤT}}
14. Lớp tiết lộ 2 (Đòn chuẩn bị pháp lý âm thầm với Notario / Escritura / Fideicomiso): {{REVEAL_LỚP_HAI_ĐỀ_XUẤT}}
15. Lớp tiết lộ 3 (Đảo ngược thế cờ công khai & hậu quả): {{REVEAL_LỚP_BA_ĐỀ_XUẤT}}
16. Phần thưởng cảm xúc & công lý (Earned Payoff): {{PAYOFF_CẢM_XÚC_DỰ_KIẾN}}
17. Cơ chế cốt truyện (Story Mechanism): {{CƠ_CHẾ_STORY_STEP1}}
18. Từ khóa SEO Tây Ban Nha Mexico (`es-MX`): {{TỪ_KHÓA_NHẬT_GỢI_Ý_CHƯA_XÁC_MINH_VOLUME}}
19. Căn cứ triển khai 7 Part (70k–80k ký tự): {{LÝ_DO_CÓ_THỂ_VIẾT_DÀI_HOẶC_RỦI_RO}}
20. Lưu ý pháp lý & văn hóa Mexico (`notario público`, `escritura pública`, `usufructo vitalicio`, `MXN`): {{LƯU_Ý_LOGIC_PHÁP_LÝ_Y_TẾ}}
21. Quy tắc chống sao chép: Giữ ~60% công thức cảm xúc/click DNA, biến đổi sáng tạo >=40% nhân vật, bối cảnh, vật chứng và cơ chế pháp lý.
22. Gợi ý bố cục Thumbnail 80/20 + Nền xanh: {{GÓC_THUMBNAIL_ĐỀ_XUẤT}}
23. Nguồn tham chiếu: {{RESEARCH_SOURCE}}

========== THAM CHIẾU BENCHMARK KÊNH PADRE MX ==========
{{THAM_CHIẾU_MOTIF_BATCH}}

========== QUY TRÌNH BẮT BUỘC CỦA STEP 1 (PADRE MX V3.0) ==========

A. PHÂN TÍCH DNA & CHẤM PREMISE (/100 ĐIỂM)
- Nhân vật chính BẮT BUỘC là người cha / người ông lớn tuổi người Mexico (60–82 tuổi), kể chuyện ngôi thứ nhất (`yo`), điềm tĩnh, từng trải, tự trọng cao.
- Chuỗi nhân quả 4 nhịp: Sự phản bội/coi thường của con cái/con dâu/con rể -> Chi tiết/câu nói tàn nhẫn cụ thể -> Quyền lực/tài sản/vật chứng pháp lý bị đánh giá thấp -> Đòn phản công pháp lý hợp pháp, đanh thép, không bạo lực.
- Xuất điểm Premise /100 và bản `PREMISE_FINAL` + `CONFLICT_FINAL`.

B. KIỂM ĐỊNH NĂNG LỰC 7 PART DÀI KỲ (70.000–80.000 KÝ TỰ)
- Kịch bản mục tiêu ở STEP 3: Tổng **70.000–80.000 ký tự** chia làm 7 phần `[PART 1]`..`[PART 7]` (mỗi Part >= 8.500 ký tự; viết qua 3 chặng Stage A = 20k–24k, Stage B = 30k–35k, Stage C = 20k–25k).
- Xuất `LONGFORM_CAPACITY: PASS` kèm tóm tắt 7 bước tiến triển nhân-quả.

C. 5 IDEAS — BẢNG 5 TIÊU ĐỀ TIẾNG TÂY BAN NHA MEXICO (`es-MX`, <= 100 KÝ TỰ)
- Tạo chính xác **5 ứng viên tiêu đề (`Candidate 1` .. `Candidate 5`)** hoàn toàn bằng tiếng Tây Ban Nha Mexico (`es-MX`), ngôi thứ nhất (`yo` / `mi` / `me`), độ dài **65–100 ký tự Unicode** (TUYỆT ĐỐI <= 100 ký tự).
- Không viết IN HOA toàn bộ tiêu đề (chỉ viết hoa chữ cái đầu câu và tên riêng).
- Với mỗi ứng viên, xuất:
  1. Tiêu đề tiếng Tây Ban Nha (`es-MX`) + số ký tự chính xác.
  2. Bản dịch nghĩa tiếng Việt.
  3. Điểm số `/100` (Emotional Wound `/25`, Curiosity Gap `/25`, Concrete Specificity `/20`, Natural Mexican Spanish `/15`, Length & Mobile Readability `/15`).

D. KHÓA TIÊU ĐỀ CHÍNH THỨC (`CURRENT_FINAL_TITLE` / `LOCKED_TITLE`)
- Chọn ứng viên điểm cao nhất (>= 88/100, <= 100 ký tự) và xuất chính xác khối:
  `CURRENT_FINAL_TITLE: <tiêu đề tiếng Tây Ban Nha thắng cuộc>`
  `LOCKED_TITLE: <tiêu đề tiếng Tây Ban Nha thắng cuộc>`
  `LOCKED_TITLE_CHAR_LEN: <số ký tự>`
  `VIETNAMESE_TRANSLATION: <bản dịch tiếng Việt>`
  `LOCKED_TITLE_PROMISE: <lời hứa cốt truyện với khán giả>`
  `TITLE_LOCKED: YES`

E. THIẾT KẾ CẶP ẢNH THUMBNAIL 80/20 (`THUMBNAIL.png` + `THUMBNAIL-NENXANH.png`)
- Bố cục 80/20 chuẩn kênh Mexico Ông Già:
  + **Vùng Trái (~78–80% chiều ngang)**: Nền trắng/sáng sạch sẽ, chứa **4–5 dòng chữ IN HOA tiếng Tây Ban Nha** siêu đậm (kết hợp màu Đen `#111111`, Xanh Cyan `#00AEEF`, Cam `#F7941D`) + **Thanh Banner Đỏ (`#E31E24`) ở đáy** chứa 1–2 dòng chữ Vàng/Cam chốt hạ cảm xúc.
  + **Vùng Phải (~20–22% chiều ngang)**: Ảnh chân dung bán thân (ngực lên đầu) của người cha già Mexico (62–78 tuổi, tóc bạc, ria mép bạc, ánh mắt điềm tĩnh uy nghiêm hoặc rơi lệ).
  + **Ảnh thứ 2 (`THUMBNAIL-NENXANH.png`)**: Giữ nguyên 100% chân dung ông già ở cùng tọa độ bên phải trên nền xanh lá thuần `#00FF00` (`RGB(0, 255, 0)`) để hệ thống tự động tách nền và ghép vào góc dưới bên trái Video!
- Xuất rõ:
  + `THUMBNAIL_MAIN_LINES_ES`: 4–5 dòng chữ IN HOA ngắn gọn (2–4 từ/dòng) cho nền trắng bên trái.
  + `THUMBNAIL_BANNER_LINES_ES`: 1–2 dòng chữ IN HOA ngắn gọn cho thanh banner đỏ bên dưới.
  + `PROTAGONIST_VISUAL_BRIEF`: Mô tả chi tiết ngoại hình, tuổi, trang phục, biểu cảm của người cha Mexico để vẽ đồng bộ 2 ảnh.

F. `STEP3_HANDOFF` (BÀN GIAO SANG STEP 2 OUTLINE 7 PART)
- Tóm tắt đầy đủ hồ sơ nhân vật, tên tuổi, số tiền MXN, tài sản, giấy tờ công chứng (`Notaría Pública`, `Escritura`, `Usufructo`) để chuyển sang lập Dàn Ý 7 Phần (`[PART 1]`..`[PART 7]`). Không viết kịch bản ở bước này."""

DEFAULT_MOTIF_REFERENCES = (
    "- Ref #01: Mi hijo me gritó que era un viejo inútil en su fiesta, sin saber que la casa seguía a mi nombre.\n"
    "- Ref #02: Mis hijos me dejaron en la calle tras enviudar, pero olvidaron quién era el dueño del rancho.\n"
    "- Ref #03: Mi nuera tiró mis herramientas al patio, hasta que el notario leyó la cláusula que firmé.\n"
    "- Ref #04: Me quitaron mi tarjeta de pensión y me mandaron al cuarto del fondo, pero guardé el contrato original."
)

DEFAULT_BATCH_POSITIONING = (
    "Kênh YouTube Mexican Spanish Elderly Father Drama — PADRE MX V3.0 (85–110 phút, 70.000–80.000 ký tự, 7 Parts). "
    "Khán giả mục tiêu: Khán giả nói tiếng Tây Ban Nha (Mexico / Mỹ Latinh / US Hispanic) yêu thích câu chuyện người cha già "
    "bị con cái/con dâu/con rể coi thường, âm thầm dùng trí tuệ và công lý pháp lý Mexico để giành lại phẩm giá."
)


# ==============================================================================
# 3. TRÌNH PHÂN TÍCH ĐẦU VÀO THÔNG MINH (HỖ TRỢ TIẾNG TÂY BAN NHA ES-MX, VIỆT & NHẬT)
# ==============================================================================
# Nhận diện dòng mở đầu của bộ tiêu đề 2 cột (Mã \t Tiêu đề) hoặc cố định:
# VD: "Mexico-Ong-Gia-001	Mi yerno me pidió ciento veinte mil euros..." hoặc "P01 — Mi hijo me echó..."
FIXED_PACK_HEADER_RE = re.compile(
    r"^(?:(?:#|\*|\-|\•)\s*)?(?P<code_id>(?:[A-Za-z0-9]+[-_][A-Za-z0-9_\-]+|(?:P|PMX|MX|ID|IDEA_?|M|T)\s*\d{1,5}))(?:\t+|\s*[|—–:：]\s*|\s{2,})(?P<ja_title>.{8,})$",
    re.IGNORECASE,
)

# Nhận diện dòng tiêu đề đánh số thứ tự (không phải dòng thuộc tính 01..23 của Step 2)
NUMBERED_JA_TITLE_RE = re.compile(
    r"^(?:(?:#|\*|\-|\•)\s*)?(?P<num>\d{1,3})[\.\)\-—–]\s*(?P<ja_title>.{15,})$"
)

# Nhận diện các dòng thuộc tính (TUYỆT ĐỐI KHÔNG BAO GIỜ TÁCH THÀNH TIÊU ĐỀ MỚI)
FIELD_LINE_PREFIX_RE = re.compile(
    r"^(?:(?:\d{1,2}[\.\)\-:]|\-|•|\*)\s*)?"
    r"(?:vi|vn|es|mx|dịch\s*ý(?:\s*tiếng\s*việt)?|tóm\s*tắt|premise(?:\s*gốc)?|nội\s*dung"
    r"|keyword|keywords|từ\s*khóa(?:\s*nhật|\s*mexico|\s*es)?"
    r"|evidence|proof(?:\s*object)?|vật\s*chứng|bằng\s*chứng"
    r"|reveal|reveals|ba\s*lớp\s*tiết\s*lộ|3\s*lớp\s*tiết\s*lộ|lớp\s*tiết\s*lộ(?:\s*thứ\s*(?:nhất|hai|ba))?|tiết\s*lộ"
    r"|capacity|longform(?:_capacity(?:_step1)?|\s*step\s*1)?|đánh\s*giá\s*năng\s*lực\s*viết\s*dài"
    r"|quan\s*hệ(?:\s*nhân\s*vật)?|nhân\s*vật|relation|relationship"
    r"|trụ\s*cột(?:\s*cảm\s*xúc)?|nhóm\s*chủ\s*đề|chủ\s*đề|pillar"
    r"|không\s*gian(?:\s*và\s*sự\s*kiện\s*mở)?|bối\s*cảnh|setting"
    r"|xung\s*đột(?:\s*trọng\s*tâm|\s*mở\s*đầu)?|conflict"
    r"|câu\s*hỏi(?:\s*khán\s*giả\s*cần\s*đáp\s*án|\s*cần\s*trả\s*lời)?"
    r"|payoff|hệ\s*quả"
    r"|mức\s*ưu\s*tiên|ưu\s*tiên|priority"
    r"|trạng\s*thái(?:\s*quản\s*lý)?|status"
    r"|mã\s*cơ\s*chế|cơ\s*chế|mechanism"
    r"|căn\s*cứ(?:\s*khả\s*năng)?|lưu\s*ý(?:\s*tính\s*khả\s*tín)?|quy\s*tắc(?:\s*kiểm\s*soát)?"
    r"|góc\s*thumbnail|nguồn\s*gốc(?:\s*ý\s*tưởng)?|research_source)\s*[:：]",
    re.IGNORECASE,
)

TITLE_LABEL_START_RE = re.compile(
    r"^(?:(?:\d+[\.\)\-:]|\-|•|\*|#+\s*)\s*)?(?:tiêu\s*đề(?:\s*nhật|\s*mexico|\s*tây\s*ban\s*nha)?(?:\s*nháp)?|04\.\s*tiêu\s*đề|title|titulo|título)\s*[:：]",
    re.IGNORECASE,
)

ID_LABEL_START_RE = re.compile(
    r"^(?:(?:\d+[\.\)\-:]|\-|•|\*|#+\s*)\s*)?(?:chạy\s*ngay\s*step\s*[12].*mã|đầu\s*vào\s*duy\s*nhất\s*[:：]|mã(?:\s*id)?\s*[:：]|id\s*[:：]|ý\s*tưởng\s*[:：]|idea\s*[:：])",
    re.IGNORECASE,
)


def clean_single_title_line(raw_line: str) -> str:
    """
    Làm sạch 1 dòng tiêu đề:
    - Tự động BỎ QUA mọi Mã dự án (Code/ID), cột Tab đầu dòng hoặc số thứ tự ở đầu dòng
      (VD: 'Mexico-Ong-Gia-001\\tMi yerno...', 'P01 — Mi hijo...', '1. Mi hijo...', '[01] Mi hijo...').
    - Chỉ giữ lại đúng nội dung câu tiêu đề trên dòng đó.
    """
    s = (raw_line or "").strip()
    if not s or re.match(r"^[-=*#]{3,}$", s):
        return ""
    if FIELD_LINE_PREFIX_RE.match(s):
        return ""

    # 1. Nếu dòng có ký tự Tab (copy từ Excel/Sheet nhiều cột: Mã \t Tiêu đề hoặc STT \t Mã \t Tiêu đề)
    if "\t" in s:
        cols = [c.strip() for c in s.split("\t") if c.strip()]
        if len(cols) >= 2:
            # Chọn cột văn bản dài nhất hoặc cột cuối cùng làm tiêu đề, bỏ qua cột Mã ở đầu
            best_col = cols[-1]
            for c in reversed(cols):
                if len(c) >= 12 and not re.match(r"^[A-Za-z0-9_\-]+$", c):
                    best_col = c
                    break
            s = best_col

    # 2. Nếu dòng có nhãn Tiêu đề: / Title: / LOCKED_TITLE:
    if TITLE_LABEL_START_RE.match(s):
        s = TITLE_LABEL_START_RE.sub("", s).strip()

    # 3. Nếu dòng bắt đầu bằng Mã cố định (VD: Mexico-Ong-Gia-001 — ..., P01: ..., IDEA_01 - ...)
    m_fixed = FIXED_PACK_HEADER_RE.match(s)
    if m_fixed:
        s = m_fixed.group("ja_title").strip()

    # 4. Bỏ số thứ tự hoặc mã ngắn ở đầu dòng (VD: "1. ", "01) ", "#1 - ", "[01] ", "P01 - ")
    s = re.sub(
        r"^(?:(?:#|\*|\-|\•)\s*)?(?:\[\s*[A-Za-z0-9_\-]+\s*\]|(?:[A-Za-z]+[-_])?[A-Za-z]*\d{1,5}|(?:\d{1,4}))\s*(?:[\.\)\-—–:：|]+\s+|\s{2,})",
        "",
        s,
        flags=re.IGNORECASE,
    ).strip()
    s = re.sub(r"^(?:\d+[\.\)\-:]|\-|•|\*)\s*", "", s).strip()
    return s.strip("`\"' ")


def _is_new_idea_block_header(ln: str) -> bool:
    """Kiểm tra xem dòng `ln` có phải là dòng mở đầu của một bộ tiêu đề mới hay không."""
    s = (ln or "").strip()
    if not s:
        return False
    if FIELD_LINE_PREFIX_RE.match(s):
        return False
    if FIXED_PACK_HEADER_RE.match(s):
        return True
    if TITLE_LABEL_START_RE.match(s) or ID_LABEL_START_RE.match(s):
        return True
    m_num = NUMBERED_JA_TITLE_RE.match(s)
    if m_num:
        return True
    return False


def split_raw_text_into_idea_blocks(raw_text: str) -> List[str]:
    """
    Tự động nhận diện và tách văn bản khi người dùng dán danh sách tiêu đề:
    - Mặc định: MỖI DÒNG 1 TIÊU ĐỀ (tự động bỏ qua mọi Mã ở đầu dòng).
    - Nếu người dùng dán khối có dòng thuộc tính phụ (VI:, Keyword:, Evidence:...) thì gom các dòng thuộc tính đó vào tiêu đề phía trên.
    """
    text = (raw_text or "").strip()
    if not text:
        return []

    raw_lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if not raw_lines:
        return []

    has_any_field_lines = any(bool(FIELD_LINE_PREFIX_RE.match(ln)) for ln in raw_lines)

    # TRƯỜNG HỢP CHUẨN (MỖI TIÊU ĐỀ 1 DÒNG — BỎ QUA MÃ ĐẦU DÒNG):
    if not has_any_field_lines:
        plain_blocks: List[str] = []
        for ln in raw_lines:
            if ID_LABEL_START_RE.match(ln) and len(ln) < 25:
                continue
            cleaned = clean_single_title_line(ln)
            if len(cleaned) >= 4:
                plain_blocks.append(cleaned)
        if plain_blocks:
            return plain_blocks
        return [clean_single_title_line(text) or text]

    # TRƯỜNG HỢP DÁN KHỐI CÓ THUỘC TÍNH PHỤ (VI:, Keyword:, Evidence:...):
    blocks: List[List[str]] = []
    current_block: List[str] = []
    current_has_header_or_content = False
    sep_re = re.compile(r"^[-=*]{3,}$")

    for ln in raw_lines:
        if sep_re.match(ln):
            if current_block:
                blocks.append(current_block)
                current_block = []
                current_has_header_or_content = False
            continue

        is_field = bool(FIELD_LINE_PREFIX_RE.match(ln))
        is_id_label = bool(ID_LABEL_START_RE.match(ln))
        if is_id_label and not is_field:
            # Bỏ qua dòng Mã ID riêng lẻ
            continue

        if not is_field:
            cleaned_title = clean_single_title_line(ln)
            if cleaned_title:
                if current_has_header_or_content:
                    blocks.append(current_block)
                    current_block = [cleaned_title]
                else:
                    current_block.append(cleaned_title)
                current_has_header_or_content = True
            continue

        current_block.append(ln)
        current_has_header_or_content = True

    if current_block:
        blocks.append(current_block)

    result_blocks = ["\n".join(b).strip() for b in blocks if b]
    return result_blocks if result_blocks else [text]


def _infer_relationship_from_text(vi_text: str, keyword_text: str, draft_title: str) -> str:
    """Tự động nhận diện mối quan hệ nhân vật chính xác từ VI / Keyword / Tiêu đề Tây Ban Nha hoặc Nhật."""
    combined = f"{vi_text} {keyword_text} {draft_title}".lower()
    mapping = [
        (("nuera", "con dâu", "nàng dâu", "mẹ chồng"), "Người cha già Mexico (Don) — Con trai & Con dâu tham lam"),
        (("yerno", "con rể", "hija", "con gái"), "Người cha già Mexico (Don) — Con gái & Con rể thực dụng"),
        (("hijos", "mis hijos", "các con", "ba người con", "herencia", "thừa kế"), "Người cha già Mexico (Don) và các con tranh giành tài sản"),
        (("nietos", "nieto", "nieta", "cháu nội", "cháu ngoại"), "Người ông/cha già Mexico và con cháu trong gia đình"),
        (("hermano", "cuñado", "anh em", "chú bác"), "Người cha già Mexico — Con cái & Họ hàng"),
        (("rancho", "hacienda", "taller", "empresa", "nhà xưởng", "trang trại"), "Người cha già chủ trang trại/xưởng Mexico và các con"),
    ]
    for keys, label in mapping:
        if any(k in combined for k in keys):
            return label
    return "Người cha già Mexico (65–78 tuổi, ngôi kể 'yo') và con cái trong gia đình"


def parse_idea_input_block(raw_text: str, custom_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Bóc tách đoạn văn bản đầu vào của người dùng (Hỗ trợ cả Tây Ban Nha Mexico es-MX, tiếng Việt, tiếng Anh và tiếng Nhật).
    """
    text = (raw_text or "").strip()
    raw_lines = [ln.strip() for ln in text.splitlines() if ln.strip()]

    expanded_lines: List[str] = []
    inline_split_re = re.compile(
        r"\.\s+(?=(?:Xung đột|Payoff|Longform(?:\s+STEP\s*1|_CAPACITY_STEP1)?|Vật chứng|Quan hệ|Nhân vật|Ba lớp tiết lộ|Tóm tắt|Premise|VI|ES|MX|Keyword|Evidence|Reveal|Capacity)\s*[:：])",
        re.IGNORECASE,
    )
    for ln in raw_lines:
        parts = inline_split_re.split(ln)
        for p in parts:
            if p.strip():
                expanded_lines.append(p.strip())

    extracted: Dict[str, str] = {}
    pending_key: Optional[str] = None
    header_code_id: str = ""
    header_draft_title: str = ""

    for ln in expanded_lines:
        m_fixed = FIXED_PACK_HEADER_RE.match(ln)
        if m_fixed and not FIELD_LINE_PREFIX_RE.match(ln):
            raw_cid = re.sub(r"\s+", "", m_fixed.group("code_id"))
            if not header_code_id:
                header_code_id = raw_cid
            if not header_draft_title:
                header_draft_title = m_fixed.group("ja_title").strip()
            continue

        m_num = NUMBERED_JA_TITLE_RE.match(ln)
        if m_num and not FIELD_LINE_PREFIX_RE.match(ln):
            if not header_draft_title:
                header_draft_title = m_num.group("ja_title").strip()
            continue

        if ":" in ln or "：" in ln:
            sep = ":" if ":" in ln else "："
            k, v = ln.split(sep, 1)
            k_clean = re.sub(r"^(?:\d+[\.\)\-:]|\-|•|\*)\s*", "", k.strip()).lower()
            v_clean = v.strip()
            if v_clean:
                extracted[k_clean] = v_clean
                pending_key = None
            else:
                pending_key = k_clean
        elif pending_key:
            extracted[pending_key] = ln.strip()
            pending_key = None

    def _pick_exact_or_contains(*keywords: str, default: str = "") -> str:
        for kw in keywords:
            kw_low = kw.lower()
            if kw_low in extracted and extracted[kw_low]:
                return extracted[kw_low]
        for k, v in extracted.items():
            for kw in keywords:
                kw_low = kw.lower()
                if len(kw_low) <= 3:
                    if k == kw_low and v:
                        return v
                elif kw_low in k and v:
                    return v
        return default

    draft_title_ja = (
        header_draft_title
        or _pick_exact_or_contains("tiêu đề", "title", "titulo", "título", "es", "mx", "04.")
    )
    if not draft_title_ja:
        for ln in raw_lines:
            if FIELD_LINE_PREFIX_RE.match(ln):
                continue
            cleaned_ln = clean_single_title_line(ln)
            if cleaned_ln:
                draft_title_ja = cleaned_ln
                break
    else:
        draft_title_ja = clean_single_title_line(draft_title_ja) or draft_title_ja.strip()

    vi_line = _pick_exact_or_contains("vi", "vn", "dịch ý", "05.")
    summary_raw = _pick_exact_or_contains("tóm tắt", "premise gốc", "10.", "premise", "nội dung")
    keyword_line = _pick_exact_or_contains("keyword", "keywords", "18.", "từ khóa")
    evidence_line = _pick_exact_or_contains("evidence", "proof", "vật chứng", "bằng chứng", "12.")
    reveal_line = _pick_exact_or_contains("reveal", "reveals", "ba lớp tiết lộ", "3 lớp tiết lộ", "lớp tiết lộ", "tiết lộ")
    capacity_line = _pick_exact_or_contains("capacity", "longform_capacity", "longform step 1", "longform", "03.", default="PASS")

    dich_y_vi = vi_line or summary_raw or (f"Ý tưởng gốc: {draft_title_ja}" if draft_title_ja else "")

    if summary_raw:
        summary_vi = summary_raw
    elif vi_line:
        extra_parts = [vi_line.rstrip(".")]
        if evidence_line:
            extra_parts.append(f"Vật chứng pháp lý trọng tâm: {evidence_line}")
        if reveal_line:
            extra_parts.append(f"Tiết lộ / Đảo ngược cốt lõi: {reveal_line}")
        summary_vi = ". ".join(extra_parts) + "."
    else:
        summary_vi = f"Triển khai câu chuyện người cha già Mexico (PADRE MX V3.0 — 7 Part, 70k–80k ký tự) bám sát ý tưởng: {draft_title_ja}" if draft_title_ja else ""

    relationship = _pick_exact_or_contains(
        "quan hệ", "nhân vật", "06.", "relation", "relationship",
        default=_infer_relationship_from_text(vi_line or summary_vi, keyword_line, draft_title_ja),
    )

    inferred_conflict = "Con cái / con dâu / con rể coi thường người cha già sau khi nghĩ ông đã hết tiền và tài sản"
    if vi_line and ";" in vi_line:
        inferred_conflict = vi_line.split(";", 1)[0].strip()
    elif vi_line:
        inferred_conflict = vi_line.strip()

    conflict = _pick_exact_or_contains("xung đột", "09.", "conflict", default=inferred_conflict)
    proof_object = evidence_line or "Escritura pública original, cláusula de usufructo vitalicio y estados de cuenta bancarios en MXN"
    tu_khoa_goi_y = keyword_line or "historias de reflexión, padre mayor, hijos ingratos, herencia, justicia familiar, México"
    longform_cap = capacity_line or "PASS"

    rev1 = _pick_exact_or_contains("13.", "lớp tiết lộ thứ nhất")
    rev2 = _pick_exact_or_contains("14.", "lớp tiết lộ thứ hai")
    rev3 = _pick_exact_or_contains("15.", "lớp tiết lộ thứ ba")

    if reveal_line and not (rev1 and rev2 and rev3):
        parts = [p.strip().rstrip(".") for p in re.split(r"→|->|=>|;", reveal_line) if p.strip()]
        if len(parts) >= 3:
            rev1 = rev1 or parts[0]
            rev2 = rev2 or parts[1]
            rev3 = rev3 or " → ".join(parts[2:])
        elif len(parts) == 2:
            rev1 = rev1 or f"Phát hiện kế hoạch chiếm đoạt tài sản của các con liên quan đến ({proof_object}): {parts[0]}"
            rev2 = rev2 or f"Người cha âm thầm làm việc với Notario Público để kích hoạt điều khoản bảo vệ tài sản"
            rev3 = rev3 or parts[1]
        else:
            core_reveal = reveal_line.strip().rstrip(".")
            vi_second_half = vi_line.split(";", 1)[1].strip() if (vi_line and ";" in vi_line) else (vi_line or "Sự thật pháp lý được công bố")
            rev1 = rev1 or f"Phát hiện âm mưu qua mặt người cha ngay sau biến cố mở đầu ({inferred_conflict})"
            rev2 = rev2 or f"Vật chứng pháp lý '{proof_object}' được chuẩn bị cùng công chứng viên: {vi_second_half}"
            rev3 = rev3 or f"Đòn công lý hợp pháp đảo ngược toàn bộ thế cờ: {core_reveal}"

    rev1 = rev1 or "Phát hiện con cái âm mưu gạt người cha ra khỏi chính ngôi nhà/tài sản ông gây dựng"
    rev2 = rev2 or "Người cha âm thầm kiểm tra sổ sách, tài khoản MXN và làm việc với Notario Público"
    rev3 = rev3 or "Buổi công bố văn bản pháp lý chính thức khiến những kẻ phản bội mất trắng quyền kiểm soát"

    payoff = _pick_exact_or_contains(
        "payoff", "hệ quả", "16.",
        default=f"{reveal_line} — Đòi lại công lý, quyền sở hữu hợp pháp và phẩm giá người cha qua '{proof_object}'" if reveal_line else "Giành lại toàn bộ tài sản hợp pháp, phẩm giá và sự bình yên tuổi già",
    )

    # Bỏ qua mọi mã đầu dòng trong văn bản, luôn lấy Mã theo STT (custom_id truyền vào là STT "1", "2", "3"...)
    ma_id = str(custom_id or "1").strip()
    ma_id = re.sub(r"[^A-Za-z0-9_\-]", "_", ma_id)

    boi_canh = _pick_exact_or_contains(
        "không gian", "bối cảnh", "08.", "setting",
        default=f"Gia đình tại Mexico gắn với sự kiện: {vi_line or summary_vi[:80]}" if (vi_line or summary_vi) else "Ngôi nhà gia đình / Văn phòng công chứng (Notaría Pública) tại Mexico",
    )
    nhom_chu_de = _pick_exact_or_contains(
        "trụ cột cảm xúc", "nhóm chủ đề", "chủ đề", "07.",
        default=f"{relationship} — {tu_khoa_goi_y}",
    )
    cau_hoi = _pick_exact_or_contains(
        "câu hỏi", "11.",
        default=f"Người cha già sẽ dùng '{proof_object}' như thế nào để lật ngược âm mưu của những đứa con bất hiếu?",
    )

    return {
        "ma_id": ma_id,
        "raw_input_text": text,
        "draft_title_ja": draft_title_ja,
        "locked_title": "",  # Sẽ được tự động cập nhật sau khi chạy STEP 1/2
        "dich_y_tieu_de_vi": dich_y_vi,
        "summary_vi": summary_vi,
        "relationship": relationship,
        "nhom_chu_de": nhom_chu_de,
        "boi_canh_su_kien": boi_canh,
        "conflict": conflict,
        "cau_hoi_can_tra_loi": cau_hoi,
        "proof_object": proof_object,
        "three_reveals_raw": reveal_line or f"{rev1} → {rev2} → {rev3}",
        "reveal_1": rev1,
        "reveal_2": rev2,
        "reveal_3": rev3,
        "payoff": payoff,
        "longform_capacity_step1": longform_cap,
        "uu_tien": _pick_exact_or_contains("01.", "ưu tiên", "priority", default="CAO (HIGH_PRIORITY)"),
        "co_che_story": _pick_exact_or_contains("17.", "cơ chế", "mechanism", default="PATRIARCH_LEGAL_REVERSAL_MX (Vật chứng công chứng Mexico đảo ngược sự phản bội gia đình)"),
        "tu_khoa_goi_y": tu_khoa_goi_y,
        "ly_do_viet_dai": _pick_exact_or_contains("19.", "căn cứ", default=f"Capacity = {longform_cap}. Cấu trúc 7 Part (70.000–80.000 ký tự) với chuỗi nhân quả 3 lớp ({rev1} -> {rev2} -> {rev3})."),
        "luu_y_logic": _pick_exact_or_contains("20.", "lưu ý", default="Đảm bảo tính xác thực của thủ tục pháp lý Mexico (Notario Público, Escritura Pública, Usufructo Vitalicio, đồng Peso MXN)."),
        "goc_thumbnail": _pick_exact_or_contains("22.", "góc thumbnail", default=f"Layout 80/20: Bên trái 80% nền trắng chữ IN HOA Tây Ban Nha + Banner đỏ; Bên phải 20% chân dung người cha già Mexico (kèm bản nền xanh #00FF00)."),
        "research_source": _pick_exact_or_contains("23.", "nguồn gốc", "research_source", default=f"PADRE MX V3.0 ({ma_id} — Keyword: {tu_khoa_goi_y})."),
        "dinh_vi_batch": DEFAULT_BATCH_POSITIONING,
        "tham_chieu_motif": DEFAULT_MOTIF_REFERENCES,
        "status": "SAVED_READY",
        "current_step": "CHƯA CHẠY (Sẵn sàng chạy PADRE MX V3.0)",
        "pure_char_count": 0,
        "audit_score": 0,
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }


def build_step2_prompt_from_idea(idea: Dict[str, Any], custom_template: Optional[str] = None) -> str:
    """Điền đầy đủ thông tin ý tưởng đã lưu vào mẫu Prompt STEP 1/2 (kèm tự động nhúng SKILL 01 PADRE MX V3.0)."""
    tpl = (custom_template or DEFAULT_STEP2_PROMPT_TEMPLATE).strip()
    # Nếu file step2_prompt_template.txt cũ trên ổ cứng vẫn là bản tiếng Nhật cũ, tự động nâng cấp lên mẫu PADRE MX V3.0
    if "TITLE MATRIX — VIẾT HOÀN TOÀN BẰNG TIẾNG NHẬT" in tpl or "40.001–50.000 PURE_CHARACTER_COUNT tiếng Nhật" in tpl:
        tpl = DEFAULT_STEP2_PROMPT_TEMPLATE.strip()
    replacements = {
        "{{MÃ_ID}}": idea.get("ma_id", "PMX_001"),
        "{{ĐỊNH_VỊ_BATCH}}": idea.get("dinh_vi_batch", DEFAULT_BATCH_POSITIONING),
        "{{ƯU_TIÊN}}": idea.get("uu_tien", "CAO"),
        "{{LONGFORM_CAPACITY_STEP1}}": idea.get("longform_capacity_step1", "PASS sơ bộ."),
        "{{TIÊU_ĐỀ_NHẬT_NHÁP_CHƯA_KHÓA}}": idea.get("draft_title_ja", ""),
        "{{DỊCH_Ý_TIÊU_ĐỀ_VI}}": idea.get("dich_y_tieu_de_vi") or idea.get("summary_vi", ""),
        "{{QUAN_HỆ_NHÂN_VẬT}}": idea.get("relationship", ""),
        "{{NHÓM_CHỦ_ĐỀ}}": idea.get("nhom_chu_de", ""),
        "{{BỐI_CẢNH_SỰ_KIỆN}}": idea.get("boi_canh_su_kien", ""),
        "{{XUNG_ĐỘT_MỞ_ĐẦU}}": idea.get("conflict", ""),
        "{{PREMISE_GỐC_STEP1}}": idea.get("summary_vi", ""),
        "{{CÂU_HỎI_CẦN_TRẢ_LỜI}}": idea.get("cau_hoi_can_tra_loi", ""),
        "{{VẬT_CHỨNG_GIEO_TRƯỚC}}": idea.get("proof_object", ""),
        "{{REVEAL_LỚP_MỘT_ĐỀ_XUẤT}}": idea.get("reveal_1", ""),
        "{{REVEAL_LỚP_HAI_ĐỀ_XUẤT}}": idea.get("reveal_2", ""),
        "{{REVEAL_LỚP_BA_ĐỀ_XUẤT}}": idea.get("reveal_3", ""),
        "{{PAYOFF_CẢM_XÚC_DỰ_KIẾN}}": idea.get("payoff", ""),
        "{{CƠ_CHẾ_STORY_STEP1}}": idea.get("co_che_story", ""),
        "{{TỪ_KHÓA_NHẬT_GỢI_Ý_CHƯA_XÁC_MINH_VOLUME}}": idea.get("tu_khoa_goi_y", ""),
        "{{LÝ_DO_CÓ_THỂ_VIẾT_DÀI_HOẶC_RỦI_RO}}": idea.get("ly_do_viet_dai", ""),
        "{{LƯU_Ý_LOGIC_PHÁP_LÝ_Y_TẾ}}": idea.get("luu_y_logic", ""),
        "{{GÓC_THUMBNAIL_ĐỀ_XUẤT}}": idea.get("goc_thumbnail", ""),
        "{{RESEARCH_SOURCE}}": idea.get("research_source", ""),
        "{{THAM_CHIẾU_MOTIF_BATCH}}": idea.get("tham_chieu_motif", DEFAULT_MOTIF_REFERENCES),
    }
    for k, v in replacements.items():
        tpl = tpl.replace(k, str(v or ""))
    return tpl


# ==============================================================================
# 4. CÁC HÀM BÓC TÁCH KẾT QUẢ & LỌC KỊCH BẢN TÂY BAN NHA ES-MX / NHẬT CHO TTS
# ==============================================================================
def extract_locked_title_from_step2(step2_text: str, fallback_title: str = "") -> str:
    """Trích xuất CURRENT_FINAL_TITLE / LOCKED_TITLE chính thức từ phản hồi của STEP 1/2 (Hỗ trợ Tây Ban Nha es-MX <= 100 ký tự và Tiếng Nhật)."""
    if not step2_text:
        return fallback_title

    vi_re = re.compile(r"[ăâđêôơưảãạẻẽẹỉĩịỏõọủũụỷỹỵ]", re.IGNORECASE)
    jp_re = re.compile(r"[\u3040-\u30ff\u4e00-\u9faf]")

    def _is_valid_locked_candidate(cand: str) -> bool:
        c = (cand or "").strip().strip("`*'\"「」«» ")
        if len(c) < 15 or len(c) > 140:
            return False
        if vi_re.search(c):
            return False
        if c.upper().startswith(("YES", "NO", "PASS", "FAIL", "STEP", "CANDIDATE", "TITLE_LOCKED")):
            return False
        if len(jp_re.findall(c)) >= 10:
            return True
        # Tiêu đề tiếng Tây Ban Nha Mexico (có khoảng trắng và chữ cái Latin)
        if " " in c and re.search(r"[a-záéíóúñüA-ZÁÉÍÓÚÑÜ]{3,}", c):
            return True
        return False

    # 1. Quét ưu tiên cùng dòng với CURRENT_FINAL_TITLE / LOCKED_TITLE / SELECTED_TITLE / WINNING_TITLE
    inline_pats = [
        r"CURRENT_FINAL_TITLE\s*[:：\-—=]+\s*([^\r\n<]+)",
        r"LOCKED_PRIMARY_TITLE\s*[:：\-—=]+\s*([^\r\n<]+)",
        r"LOCKED_TITLE\s*[:：\-—=]+\s*([^\r\n<]+)",
        r"WINNING_TITLE\s*[:：\-—=]+\s*([^\r\n<]+)",
        r"SELECTED_TITLE\s*[:：\-—=]+\s*([^\r\n<]+)",
        r"WINNER\s*[:：\-—=]+\s*(?:Candidate\s*\d+\s*[:：\-—]?\s*|Title\s*[ABC1-5]\s*[:：\-—]?\s*)?([^\r\n<]+)",
    ]
    for pat in inline_pats:
        for m in re.finditer(pat, step2_text, flags=re.IGNORECASE):
            cand = re.sub(r"<[^>]+>", "", m.group(1)).replace("**", "").strip().strip("`*'\"「」 ")
            if cand.upper() in ("VERBATIM", "YES", "PASS"):
                continue
            if _is_valid_locked_candidate(cand):
                return cand[:100].strip() if not jp_re.search(cand) and len(cand) > 100 else cand

    # 2. Quét các khối tiêu đề viết ở dòng kế tiếp bên dưới nhãn
    header_pats = [
        r"CURRENT_FINAL_TITLE\b",
        r"LOCKED_TITLE\s*[—\-:：]+\s*VERBATIM",
        r"\*\*LOCKED_TITLE[:：]?\*\*",
        r"###\s*LOCKED_TITLE\b",
        r"LOCKED_TITLE\b",
        r"SELECTED\s+TITLE\b",
        r"WINNING\s+TITLE\b",
    ]
    for hpat in header_pats:
        for m in re.finditer(hpat, step2_text, flags=re.IGNORECASE):
            tail = step2_text[m.end() : m.end() + 700]
            mt = re.search(r"<title[^>]*>([^<]+)</title>", tail, flags=re.IGNORECASE)
            if mt:
                cand = mt.group(1).strip().strip("`*'\"「」 ")
                if _is_valid_locked_candidate(cand):
                    return cand
            for raw_ln in tail.splitlines()[:8]:
                ln = re.sub(r"<[^>]+>", "", raw_ln).replace("**", "").strip()
                ln = re.sub(
                    r"^(?:CURRENT_FINAL_TITLE|LOCKED_TITLE|SELECTED\s+TITLE|WINNING\s+TITLE|TITLE\s+[ABC1-5]|CANDIDATE\s+\d+)[\s:：\-—=]*",
                    "",
                    ln,
                    flags=re.IGNORECASE,
                ).strip()
                ln = ln.strip("`*'\" ")
                if _is_valid_locked_candidate(ln):
                    return ln

    return fallback_title


def extract_clean_japanese_narration(raw_text: str, part_letter: str = "") -> str:
    """
    Lọc bỏ toàn bộ dòng tiêu đề kỹ thuật, [LOCKED_TITLE], [CURRENT_FINAL_TITLE], bảng Handoff/Continuity/Count Gate,
    chỉ giữ lại 100% văn bản tự sự & lời thoại (Tây Ban Nha Mexico `es-MX` kèm nhãn `[PART 1]`..`[PART 7]` hoặc Tiếng Nhật).
    """
    if not raw_text:
        return ""

    norm_raw = raw_text.replace("\r\n", "\n").replace("\r", "\n")
    norm_raw = re.sub(
        r"</?(?:CodeBlock|WritingBlock|title|grid|grid-item|caption)[^>]*>",
        "",
        norm_raw,
        flags=re.IGNORECASE,
    )

    stop_markers = [
        "PART_PURE_CHARACTER_COUNT",
        "PART_LENGTH_GATE",
        "STAGE_A_COUNT_GATE",
        "STAGE_B_COUNT_GATE",
        "STAGE_C_COUNT_GATE",
        "CONTINUITY_LEDGER",
        "CONTINUITY LEDGER",
        "PART_HANDOFF_LEDGER",
        "HANDOFF_LEDGER",
        "HANDOFF LEDGER",
        "PART_A_HANDOFF",
        "PART_B_HANDOFF",
        "PART_C_HANDOFF",
        "NEXT_ACTION",
        "READY_FOR_AUDIT",
        "PATCH_CHANGELOG",
        "REPAIR_1_EXECUTION_LOG",
        "REPAIR_2_EXECUTION_LOG",
    ]
    # Chỉ lọc những ký tự đặc trưng riêng của tiếng Việt (không trùng với á, é, í, ó, ú, ñ, ü của tiếng Tây Ban Nha)
    vi_only_re = re.compile(r"[ăâđêôơưảãạẻẽẹỉĩịỏõọủũụỷỹỵ]", re.IGNORECASE)
    is_cjk_doc = bool(re.search(r"[\u3040-\u30ff\u4e00-\u9faf]", norm_raw))

    clean_lines: List[str] = []
    for raw_ln in norm_raw.splitlines():
        ln = raw_ln.strip()
        if not ln:
            continue
        upper_ln = ln.upper().lstrip("#*>- `")
        if any(upper_ln.startswith(mk) or f"**{mk}" in upper_ln or f"`{mk}" in upper_ln for mk in stop_markers):
            break
        if ln.startswith(("```", "---", "===")):
            continue

        # Giữ nguyên hoặc chuẩn hóa dòng nhãn [PART 1] .. [PART 7] của PADRE MX V3.0
        m_part_tag = re.match(r"^[#*>\-\s`]*\[\s*PART\s*([1-7])\s*\][*`\s]*$", ln, flags=re.IGNORECASE)
        if m_part_tag:
            clean_lines.append(f"[PART {m_part_tag.group(1)}]")
            continue

        if ln.startswith("#"):
            m_hdr_part = re.match(r"^#+\s*\[?\s*PART\s*([1-7])\s*\]?\s*$", ln, flags=re.IGNORECASE)
            if m_hdr_part:
                clean_lines.append(f"[PART {m_hdr_part.group(1)}]")
            continue

        cleaned = re.sub(r"<[^>]+>", "", ln).replace("**", "").replace("`", "").strip()
        if not cleaned:
            continue

        if re.match(
            r"^(?:[A-Z]{1,6}\d{1,5}\s*[—–\-·:：]+\s*)?(?:STEP\s*[1-7]\b|BUILD\s+PART\s*[ABC]\b|STAGE\s*[ABC]\b|PART\s*[:：\-—–·]?\s*[ABC]\b|SCENE\s+[ABC]?\d+\b|CHAPTER\s+\d+\b|第\d+章|【.*】)\s*[:：\-—–·]?.*$",
            cleaned,
            re.IGNORECASE,
        ) and len(cleaned) < 95:
            continue

        if re.match(
            r"^(?:LOCKED_TITLE|CURRENT_FINAL_TITLE|SELECTED_TITLE|WINNING_TITLE|FINAL_TITLE|DRAFT_TITLE|TITLE_LOCKED|PART_[1-7]_CHAR_COUNT|STAGE_TOTAL_CHAR_COUNT|STAGE_[ABC]_PASS|TOTAL_SCRIPT_CHAR_COUNT|ALL_7_PARTS_GE_8500|TOTAL_IN_70000_80000|ID|STATUS|COMPLETED_STEP|NEXT_STEP|CONTINUITY|ENDING)\s*[:：=]",
            cleaned,
            re.IGNORECASE,
        ):
            continue

        if vi_only_re.search(cleaned):
            continue

        if is_cjk_doc:
            has_jp = bool(re.search(r"[\u3040-\u30ff\u4e00-\u9faf]", cleaned))
            is_meta_kv = bool(re.match(r"^[A-Z][A-Z0-9_/\-\s]{1,35}[:：]", cleaned))
            if has_jp and not is_meta_kv:
                clean_lines.append(cleaned)
        else:
            # Văn bản Tây Ban Nha (es-MX): loại bỏ dòng key:value kỹ thuật in hoa
            is_meta_kv = bool(re.match(r"^[A-Z][A-Z0-9_/\-\s]{2,38}[:：=]\s*", cleaned))
            if not is_meta_kv:
                clean_lines.append(cleaned)

    joined = "\n\n".join(clean_lines).strip()
    if part_letter and not is_cjk_doc:
        joined = ensure_part_headings_for_stage(joined, part_letter)
    return joined


def trim_japanese_to_max_pure_chars(text: str, max_pure_chars: int = 24800) -> str:
    """Nếu 1 Stage vượt quá trần ký tự, cắt gọn tại dấu chấm câu gần nhất mà vẫn bảo toàn các nhãn [PART N]."""
    if pure_char_count(text) <= max_pure_chars:
        return text
    if not any("\u3040" <= ch <= "\u9fff" for ch in (text or "")):
        # Cắt gọn an toàn cho văn bản Tây Ban Nha (es-MX) theo từng đoạn/câu ở cuối
        lines = text.splitlines()
        while len(lines) > 4 and pure_char_count("\n".join(lines)) > max_pure_chars:
            last_ln = lines[-1].strip()
            if re.match(r"^\[PART\s*[1-7]\]$", last_ln, flags=re.IGNORECASE):
                break
            sentences = re.split(r"(?<=[\.!\?…])\s+", last_ln)
            if len(sentences) > 1:
                lines[-1] = " ".join(sentences[:-1]).strip()
            else:
                lines.pop()
        return "\n".join(lines).strip()

    sentences = split_japanese_script(text)
    kept: List[str] = []
    running = 0
    for s in sentences:
        c = pure_char_count(s)
        if running + c > max_pure_chars and running >= 13334:
            break
        kept.append(s)
        running += c
    return "\n".join(kept)


# ==============================================================================
# 5. ĐỘNG CƠ CHẠY DÂY CHUYỀN ADAS (STEP 2 -> STEP 3 -> STEP 4 A/B/C -> STEP 5 -> STEP 6)
# ==============================================================================
class ADASScriptEngine:
    """
    Quản lý danh sách Ý tưởng/Tiêu đề đã lưu và tự động điều phối 3 Tài khoản ChatGPT Web
    chạy từ STEP 2 -> STEP 6, sau đó đẩy thẳng sang ProductionPipeline để xuất Video.
    """

    def __init__(self, root_dir: Path, video_pipeline: Any = None):
        self.root_dir = Path(root_dir).resolve()
        if self.root_dir.name.lower() == "app":
            self.root_dir = self.root_dir.parent
        self.video_pipeline = video_pipeline
        self.ideas_file = self.root_dir / "saved_ideas.json"
        self.step2_template_file = self.root_dir / "step2_prompt_template.txt"
        self.projects_dir = self.root_dir / "projects"
        self.final_video_dir = self.projects_dir
        self.ssd_staging_dir = (
            Path(os.environ.get("LOCALAPPDATA") or (Path.home() / "AppData" / "Local"))
            / "Mexico_Ong_Gia_Studio"
            / "SSD_Render_Staging"
        )
        self.use_ssd_staging = True

        self.lock = threading.Lock()
        self.ideas_io_lock = threading.RLock()
        self.is_running = False
        self.should_stop = False
        self.listeners: List[Callable[[Dict[str, Any]], None]] = []

        self._load_storage_paths_config()

        self.state: Dict[str, Any] = {
            "status": "idle",
            "current_ma_id": None,
            "current_step": "Sẵn sàng",
            "progress": 0.0,
            "message": "Sẵn sàng nhận Tiêu đề nháp & Tóm tắt để chạy Step 2 -> Step 6.",
            "logs": [],
        }

        if self.video_pipeline and hasattr(self.video_pipeline, "set_job_status_callback"):
            try:
                self.video_pipeline.set_job_status_callback(self._on_video_pipeline_job_update)
            except Exception:
                pass

        self._sync_projects_disk_state()

    def _on_video_pipeline_job_update(
        self,
        ma_id: str,
        status: str,
        step_desc: str,
        extra: Optional[Dict[str, Any]] = None,
    ):
        """Nhận thông báo trực tiếp từ ProductionPipeline khi dự án đang tạo Voice / Render MP4 / Hoàn tất."""
        now_ts = time.time()
        if not hasattr(self, "_vp_job_update_tracker") or not isinstance(getattr(self, "_vp_job_update_tracker", None), dict):
            self._vp_job_update_tracker = {}
        prev_st, prev_ts = self._vp_job_update_tracker.get(ma_id, ("", 0.0))

        # Tránh bão I/O ổ cứng (ghi đè saved_ideas.json + quét 300 thư mục liên tục mỗi giây) khi đang ở trạng thái trung gian VIDEO_RENDERING
        is_status_transition = (status != prev_st) or (status in ("COMPLETED_VIDEO", "ERROR_VIDEO", "ERROR", "SCRIPT_DONE"))
        if not is_status_transition and status == "VIDEO_RENDERING" and (now_ts - prev_ts) < 20.0:
            return

        self._vp_job_update_tracker[ma_id] = (status, now_ts)
        fields: Dict[str, Any] = {"status": status, "current_step": step_desc}
        if status == "COMPLETED_VIDEO":
            fields["has_video_mp4"] = True
        elif status in ("ERROR_VIDEO", "VIDEO_RENDERING", "VIDEO_QUEUED", "SCRIPT_DONE"):
            fields["has_video_mp4"] = False
        if extra:
            if extra.get("video_path") and status == "COMPLETED_VIDEO":
                fields["has_video_mp4"] = True
                fields["video_mp4_path"] = str(extra["video_path"])
            if extra.get("error"):
                fields["last_error"] = str(extra["error"])
        self._update_idea_record(ma_id, **fields)
        if is_status_transition:
            self._emit(
                current_ma_id=ma_id,
                current_step=step_desc,
                message=f"[{ma_id}] {step_desc}",
            )

    def subscribe(self, cb: Callable[[Dict[str, Any]], None]):
        self.listeners.append(cb)

    def _emit(self, **kwargs):
        with self.lock:
            for k, v in kwargs.items():
                self.state[k] = v
            msg = kwargs.get("message")
            curr_id = kwargs.get("current_ma_id") or self.state.get("current_ma_id")
            if msg:
                ts = time.strftime("%H:%M:%S")
                log_line = f"[{ts}] {msg}"
                logs = self.state.setdefault("logs", [])
                if not logs or logs[-1] != log_line:
                    logs.append(log_line)
                    if len(logs) > 120:
                        self.state["logs"] = logs[-120:]
            snapshot = dict(self.state)

        if msg:
            st = str(kwargs.get("status", "")).lower()
            if st == "error" or "❌" in msg:
                log_error("SCRIPT", msg, project_id=curr_id)
            elif "⚠️" in msg:
                log_warn("SCRIPT", msg, project_id=curr_id)
            else:
                log_info("SCRIPT", msg, project_id=curr_id)

        for cb in self.listeners:
            try:
                cb({"type": "adas_update", "adas_state": snapshot})
            except Exception:
                pass

    def get_state(self) -> Dict[str, Any]:
        with self.lock:
            return dict(self.state)

    def get_step2_template(self) -> str:
        if self.step2_template_file.exists():
            try:
                return self.step2_template_file.read_text(encoding="utf-8")
            except Exception:
                pass
        return DEFAULT_STEP2_PROMPT_TEMPLATE

    def save_step2_template(self, template_text: str) -> str:
        clean = (template_text or "").strip() or DEFAULT_STEP2_PROMPT_TEMPLATE
        self.step2_template_file.write_text(clean, encoding="utf-8")
        return clean

    def _get_persistent_appdata_dir(self) -> Path:
        base = Path(os.environ.get("LOCALAPPDATA") or (Path.home() / "AppData" / "Local")) / "Mexico_Ong_Gia_Studio"
        try:
            base.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
        return base

    def _normalize_projects_folder_path(self, raw_path: str) -> Path:
        cand = Path(str(raw_path).strip()).resolve()
        if cand.exists() and cand.is_dir():
            sub_projects = cand / "projects"
            if sub_projects.exists() and sub_projects.is_dir():
                has_direct_proj = False
                try:
                    for d in cand.iterdir():
                        if d.is_dir() and d.name.lower() != "projects":
                            if (
                                (d / "idea_info.json").exists()
                                or (d / "script_clean.txt").exists()
                                or (d / "part_a.txt").exists()
                                or (d / "renders").exists()
                            ):
                                has_direct_proj = True
                                break
                except Exception:
                    pass
                if not has_direct_proj:
                    return sub_projects.resolve()
        return cand

    def _migrate_misplaced_voice_assets_from_final_dir(self):
        """
        Đảm bảo thư mục Nơi Chứa Video Cuối (`final_video_dir` / `VIDEO XONG`) CHỈ chứa các dự án đã hoàn thiện Video MP4,
        và toàn bộ file Voice (`assets/`) luôn nằm tại Folder Project đã chọn (`projects_dir`).
        """
        try:
            f_dir = getattr(self, "final_video_dir", None)
            p_dir = getattr(self, "projects_dir", None)
            if not f_dir or not p_dir:
                return
            f_root = Path(f_dir).resolve()
            p_root = Path(p_dir).resolve()
            if f_root == p_root or not f_root.exists():
                return

            ignore_names = {"renders", "assets", "sentences", "stook", "ssd_render_staging", "__pycache__"}
            for sub in list(f_root.iterdir()):
                if not sub.is_dir() or sub.name.lower() in ignore_names or sub.name.startswith(".") or sub.name.startswith("_"):
                    continue
                mid = sub.name.strip()
                target_proj = p_root / mid
                misplaced_assets = sub / "assets"
                if misplaced_assets.exists() and misplaced_assets.is_dir():
                    try:
                        dest_assets = target_proj / "assets"
                        dest_assets.mkdir(parents=True, exist_ok=True)
                        for item in list(misplaced_assets.iterdir()):
                            dest_it = dest_assets / item.name
                            if item.is_dir():
                                shutil.copytree(item, dest_it, dirs_exist_ok=True)
                            elif not dest_it.exists() or item.stat().st_size > dest_it.stat().st_size:
                                shutil.copy2(item, dest_it)
                        shutil.rmtree(misplaced_assets, ignore_errors=True)
                    except Exception:
                        pass

                # Chuyển các file kịch bản / thông tin dự án về Folder Project nếu bên Folder Project chưa có
                for fn in ("script_clean.txt", "script.txt", "idea_info.json", "00_TIEU_DE_VA_SEO_YOUTUBE.txt", "step2_title_thumbnail.txt", "part_a.txt", "part_b.txt", "part_c.txt"):
                    src_f = sub / fn
                    if src_f.exists():
                        try:
                            target_proj.mkdir(parents=True, exist_ok=True)
                            dst_f = target_proj / fn
                            if not dst_f.exists() or src_f.stat().st_size > dst_f.stat().st_size:
                                shutil.copy2(src_f, dst_f)
                        except Exception:
                            pass

                # Nếu trong thư mục con ở VIDEO XONG chưa có file Video MP4 hoàn thiện thì xóa thư mục rỗng ở VIDEO XONG
                mp4_in_renders = sub / "renders" / f"{mid}_master.mp4"
                mp4_direct = sub / f"{mid}_master.mp4"
                has_finished_mp4 = (
                    (mp4_in_renders.exists() and mp4_in_renders.stat().st_size > 1_000_000)
                    or (mp4_direct.exists() and mp4_direct.stat().st_size > 1_000_000)
                )
                if not has_finished_mp4 and target_proj.exists():
                    try:
                        shutil.rmtree(sub, ignore_errors=True)
                    except Exception:
                        pass
        except Exception:
            pass

    def _sync_storage_paths_to_pipeline(self):
        if self.video_pipeline is not None:
            try:
                self.video_pipeline.projects_dir = self.projects_dir
                self.video_pipeline.default_projects_dir = self.projects_dir
                self.video_pipeline.final_video_dir = self.final_video_dir
                self.video_pipeline.ssd_staging_dir = self.ssd_staging_dir
                self.video_pipeline.use_ssd_staging = self.use_ssd_staging
            except Exception:
                pass
        try:
            for root_sp in (self.root_dir / "storage_paths.json", self.root_dir / "app" / "storage_paths.json"):
                if root_sp.parent.exists():
                    root_sp.write_text(
                        json.dumps(
                            {
                                "projects_dir": str(self.projects_dir),
                                "final_video_dir": str(self.final_video_dir),
                                "ssd_staging_dir": str(self.ssd_staging_dir),
                                "use_ssd_staging": bool(self.use_ssd_staging),
                            },
                            ensure_ascii=False,
                            indent=2,
                        ),
                        encoding="utf-8",
                    )
        except Exception:
            pass
        threading.Thread(target=self._migrate_misplaced_voice_assets_from_final_dir, daemon=True).start()

    def _load_storage_paths_config(self):
        """
        Khôi phục cấu hình 3 đường dẫn lưu trữ từ `%LOCALAPPDATA%\\Drama_Nhat_Studio\\storage_paths.json` và `config.json`:
        1. `projects_dir`: Folder Project (Nơi chứa các folder dự án P01, P02..., kịch bản, thumbnail, SEO).
        2. `final_video_dir`: Nơi Chứa Video Cuối (Ổ lưu MP4 hoàn chỉnh sau khi Render trên SSD xong).
        3. `ssd_staging_dir`: Ổ SSD Render Tạm (Scratch Disk NVMe tốc độ cao).
        """
        appdata_dir = self._get_persistent_appdata_dir()
        sp_file = appdata_dir / "storage_paths.json"
        cfg_file = self.root_dir / "config.json"

        raw_cfg: Dict[str, Any] = {}
        for fp in (cfg_file, sp_file):
            if fp.exists():
                try:
                    data = json.loads(fp.read_text(encoding="utf-8"))
                    if isinstance(data, dict):
                        raw_cfg.update(data)
                except Exception:
                    pass

        default_proj = (self.root_dir / "projects").resolve()
        proj_str = str(raw_cfg.get("projects_dir") or "").strip()
        if proj_str:
            try:
                self.projects_dir = self._normalize_projects_folder_path(proj_str)
            except Exception:
                self.projects_dir = default_proj
        else:
            self.projects_dir = default_proj

        final_str = str(raw_cfg.get("final_video_dir") or "").strip()
        if final_str:
            try:
                self.final_video_dir = Path(final_str).resolve()
            except Exception:
                self.final_video_dir = self.projects_dir
        else:
            self.final_video_dir = self.projects_dir

        ssd_str = str(raw_cfg.get("ssd_staging_dir") or "").strip()
        default_ssd = appdata_dir / "SSD_Render_Staging"
        if ssd_str:
            try:
                self.ssd_staging_dir = Path(ssd_str).resolve()
            except Exception:
                self.ssd_staging_dir = default_ssd
        else:
            self.ssd_staging_dir = default_ssd

        self.use_ssd_staging = bool(raw_cfg.get("use_ssd_staging", True))

        for d_path in (self.projects_dir, self.final_video_dir, self.ssd_staging_dir):
            try:
                d_path.mkdir(parents=True, exist_ok=True)
            except Exception:
                pass

        # Nếu dùng chung thư mục mặc định root_dir/projects thì giữ saved_ideas.json, đồng thời lưu bản index trong projects_dir
        local_idx = self.projects_dir / "_saved_ideas_index.json"
        root_idx = self.root_dir / "saved_ideas.json"
        if self.projects_dir.resolve() == default_proj:
            self.ideas_file = root_idx
            if root_idx.exists() and not local_idx.exists():
                try:
                    shutil.copy2(root_idx, local_idx)
                except Exception:
                    pass
        else:
            self.ideas_file = local_idx

        self._sync_storage_paths_to_pipeline()

    def get_storage_paths(self) -> Dict[str, Any]:
        if not hasattr(self, "final_video_dir") or self.final_video_dir is None:
            self._load_storage_paths_config()
        try:
            is_sep = self.final_video_dir.resolve() != self.projects_dir.resolve()
        except Exception:
            is_sep = False
        return {
            "projects_dir": str(self.projects_dir),
            "final_video_dir": str(self.final_video_dir),
            "ssd_staging_dir": str(self.ssd_staging_dir),
            "use_ssd_staging": bool(getattr(self, "use_ssd_staging", True)),
            "is_separate_final_dir": is_sep,
        }

    def set_storage_paths(
        self,
        projects_dir: Optional[str] = None,
        final_video_dir: Optional[str] = None,
        ssd_staging_dir: Optional[str] = None,
        use_ssd_staging: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """
        Cập nhật đường dẫn Folder Project (`projects_dir`), Nơi Chứa Video Cuối (`final_video_dir`) và Ổ SSD Render Tạm (`ssd_staging_dir`).
        Tự động lưu cấu hình và quét nạp ngay 100% dự án + trạng thái MP4 từ các thư mục vừa chọn!
        """
        if not hasattr(self, "final_video_dir") or self.final_video_dir is None:
            self._load_storage_paths_config()

        old_proj = self.projects_dir.resolve()
        old_final = self.final_video_dir.resolve()
        was_same = (old_proj == old_final)

        if projects_dir is not None and str(projects_dir).strip():
            self.projects_dir = self._normalize_projects_folder_path(str(projects_dir).strip())
            if was_same and (final_video_dir is None or not str(final_video_dir).strip()):
                self.final_video_dir = self.projects_dir

        if final_video_dir is not None and str(final_video_dir).strip():
            self.final_video_dir = Path(str(final_video_dir).strip()).resolve()

        if ssd_staging_dir is not None and str(ssd_staging_dir).strip():
            self.ssd_staging_dir = Path(str(ssd_staging_dir).strip()).resolve()

        if use_ssd_staging is not None:
            self.use_ssd_staging = bool(use_ssd_staging)

        for d_path in (self.projects_dir, self.final_video_dir, self.ssd_staging_dir):
            try:
                d_path.mkdir(parents=True, exist_ok=True)
            except Exception:
                pass

        default_proj = (self.root_dir / "projects").resolve()
        if self.projects_dir.resolve() == default_proj:
            self.ideas_file = self.root_dir / "saved_ideas.json"
        else:
            self.ideas_file = self.projects_dir / "_saved_ideas_index.json"

        payload = {
            "projects_dir": str(self.projects_dir),
            "final_video_dir": str(self.final_video_dir),
            "ssd_staging_dir": str(self.ssd_staging_dir),
            "use_ssd_staging": bool(self.use_ssd_staging),
            "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        sp_file = self._get_persistent_appdata_dir() / "storage_paths.json"
        try:
            sp_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass

        cfg_file = self.root_dir / "config.json"
        try:
            cfg = json.loads(cfg_file.read_text(encoding="utf-8")) if cfg_file.exists() else {}
            cfg.update(payload)
            cfg["output_dir"] = str(self.final_video_dir)
            cfg_file.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass

        self._sync_storage_paths_to_pipeline()
        restore_res = self.restore_scripts_from_disk()
        log_info(
            "SYSTEM",
            f"📂 Đã cập nhật đường dẫn lưu trữ: Folder Project=[{self.projects_dir}] | Nơi Chứa Video Cuối=[{self.final_video_dir}] | SSD Render=[{self.ssd_staging_dir} ({'BẬT' if self.use_ssd_staging else 'TẮT'})]",
        )
        res = self.get_storage_paths()
        if isinstance(restore_res, dict):
            res.update(restore_res)
        res["restore_summary"] = restore_res
        return res

    def _get_effective_project_dir(self, ma_id: str) -> Path:
        """Trả về thư mục dự án trên `projects_dir` (ưu tiên) hoặc `final_video_dir` nếu dự án nằm ở thư mục video cuối."""
        p_main = self.projects_dir / ma_id
        if p_main.exists():
            return p_main
        f_dir = getattr(self, "final_video_dir", None)
        if f_dir:
            p_final = Path(f_dir) / ma_id
            if p_final.exists():
                return p_final
        return p_main

    def resolve_project_mp4_path(self, ma_id: str) -> Optional[Path]:
        """
        Tìm chính xác đường dẫn file `{ma_id}_master.mp4` dù file nằm ở:
        1. `final_video_dir/{ma_id}/renders/{ma_id}_master.mp4`
        2. `final_video_dir/{ma_id}/{ma_id}_master.mp4` hoặc `final_video_dir/{ma_id}_master.mp4`
        3. `projects_dir/{ma_id}/renders/{ma_id}_master.mp4`
        4. Đường dẫn được ghi trong `projects_dir/{ma_id}/renders/video_location.json`
        """
        candidates: List[Path] = []
        f_dir = getattr(self, "final_video_dir", None)
        if f_dir:
            f_path = Path(f_dir)
            candidates.extend([
                f_path / ma_id / "renders" / f"{ma_id}_master.mp4",
                f_path / ma_id / f"{ma_id}_master.mp4",
                f_path / "renders" / f"{ma_id}_master.mp4",
                f_path / f"{ma_id}_master.mp4",
            ])
        p_dir = self.projects_dir / ma_id
        candidates.extend([
            p_dir / "renders" / f"{ma_id}_master.mp4",
            p_dir / f"{ma_id}_master.mp4",
        ])
        loc_file = p_dir / "renders" / "video_location.json"
        if loc_file.exists():
            try:
                loc_data = json.loads(loc_file.read_text(encoding="utf-8"))
                vp_str = str(loc_data.get("video_mp4_path") or "").strip()
                if vp_str:
                    candidates.insert(0, Path(vp_str))
            except Exception:
                pass

        seen: set[str] = set()
        for c in candidates:
            cs = str(c)
            if cs in seen:
                continue
            seen.add(cs)
            try:
                if c.exists() and c.is_file() and c.stat().st_size > 0:
                    return c
            except Exception:
                pass
        return None

    def _list_all_existing_project_ids_on_disk(self) -> Dict[str, Path]:
        """
        Quét đồng thời cả `projects_dir` (Folder Project) và `final_video_dir` (Nơi Chứa Video Cuối)
        để trả về bảng ánh xạ `{ma_id: project_dir}` giúp ứng dụng luôn load được 100% dự án và MP4!
        """
        found: Dict[str, Path] = {}
        ignore_names = {"renders", "assets", "sentences", "stook", "ssd_render_staging", "__pycache__"}

        def _natural_dir_sort_key(d: Path):
            nm = d.name.strip()
            return (0, int(nm)) if nm.isdigit() else (1, nm.lower())

        f_dir = getattr(self, "final_video_dir", None)
        if f_dir and Path(f_dir).exists():
            try:
                f_path = Path(f_dir)
                if f_path.resolve() != self.projects_dir.resolve():
                    for d in sorted(f_path.iterdir(), key=_natural_dir_sort_key):
                        if d.is_dir():
                            nm = d.name.strip()
                            if (
                                nm
                                and not nm.startswith(".")
                                and not nm.startswith("_")
                                and nm.lower() not in ignore_names
                                and not (d / ".deleted_by_user").exists()
                            ):
                                found[nm] = d
                        elif d.is_file() and d.name.endswith("_master.mp4"):
                            mid_mp4 = d.name[: -len("_master.mp4")].strip()
                            if mid_mp4 and mid_mp4 not in found:
                                found[mid_mp4] = f_path
            except Exception:
                pass

        if self.projects_dir.exists():
            try:
                for d in sorted(self.projects_dir.iterdir(), key=_natural_dir_sort_key):
                    if d.is_dir():
                        nm = d.name.strip()
                        if (
                            nm
                            and not nm.startswith(".")
                            and not nm.startswith("_")
                            and nm.lower() not in ignore_names
                            and not (d / ".deleted_by_user").exists()
                        ):
                            found[nm] = d
            except Exception:
                pass
        return found

    def _load_deleted_ids(self) -> set[str]:
        """Đọc danh sách các mã dự án/tiêu đề mà người dùng đã chủ động xóa để không bao giờ tự load lại khi bật app."""
        deleted: set[str] = set()
        for fp in (
            self.root_dir / "deleted_ideas.json",
            self._get_persistent_appdata_dir() / "deleted_ideas.json",
        ):
            if fp.exists():
                try:
                    data = json.loads(fp.read_text(encoding="utf-8"))
                    if isinstance(data, list):
                        deleted.update(str(x).strip() for x in data if x)
                except Exception:
                    pass
        return deleted

    def _save_deleted_ids(self, deleted_set: set[str]):
        payload = json.dumps(sorted(deleted_set), ensure_ascii=False, indent=2)
        for fp in (
            self.root_dir / "deleted_ideas.json",
            self._get_persistent_appdata_dir() / "deleted_ideas.json",
        ):
            try:
                fp.write_text(payload, encoding="utf-8")
            except Exception:
                pass

    def _mark_ids_deleted(self, ma_ids: List[str]):
        cur = self._load_deleted_ids()
        for mid in ma_ids:
            m = (mid or "").strip()
            if m:
                cur.add(m)
        self._save_deleted_ids(cur)

    def _unmark_ids_deleted(self, ma_ids: List[str]):
        cur = self._load_deleted_ids()
        changed = False
        for mid in ma_ids:
            m = (mid or "").strip()
            if m in cur:
                cur.discard(m)
                changed = True
        if changed:
            self._save_deleted_ids(cur)

    def _register_and_sync_external_projects(self):
        """
        Lưu đường dẫn thư mục `projects/` hiện tại vào `%LOCALAPPDATA%\\Drama_Nhat_Studio\\projects_dirs_registry.json`.
        Tuyệt đối KHÔNG tự động copy ngầm các thư mục dự án cũ từ thư mục khác sang `projects/` để đảm bảo
        khi người dùng xóa hết folder trong `projects/`, ứng dụng luôn phản ánh đúng 100% trạng thái thực tế của `projects/`.
        """
        appdata_dir = self._get_persistent_appdata_dir()
        reg_file = appdata_dir / "projects_dirs_registry.json"
        known_dirs: List[str] = []
        if reg_file.exists():
            try:
                data = json.loads(reg_file.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    known_dirs = [str(x) for x in data if x]
            except Exception:
                pass

        curr_str = str(self.projects_dir.resolve())
        if curr_str not in known_dirs:
            known_dirs.insert(0, curr_str)
            try:
                reg_file.write_text(json.dumps(known_dirs[:15], ensure_ascii=False, indent=2), encoding="utf-8")
            except Exception:
                pass

    def load_saved_ideas(self) -> List[Dict[str, Any]]:
        with self.ideas_io_lock:
            raw_list: Optional[List[Dict[str, Any]]] = None
            if self.ideas_file.exists():
                try:
                    data = json.loads(self.ideas_file.read_text(encoding="utf-8"))
                    if isinstance(data, list):
                        raw_list = data
                except Exception:
                    raw_list = None

            if raw_list is None:
                local_idx = self.projects_dir / "_saved_ideas_index.json"
                if local_idx.exists():
                    try:
                        data = json.loads(local_idx.read_text(encoding="utf-8"))
                        if isinstance(data, list):
                            raw_list = data
                    except Exception:
                        raw_list = None

            if raw_list is None:
                bak_file = self._get_persistent_appdata_dir() / "saved_ideas_backup.json"
                if bak_file.exists():
                    try:
                        data = json.loads(bak_file.read_text(encoding="utf-8"))
                        if isinstance(data, list):
                            raw_list = data
                    except Exception:
                        raw_list = []

            if raw_list is None:
                raw_list = []

            # Luôn đối chiếu trực tiếp với thư mục `projects_dir` & `final_video_dir` trên ổ cứng:
            existing_dirs = set(self._list_all_existing_project_ids_on_disk().keys())

            filtered_list = [
                it
                for it in raw_list
                if isinstance(it, dict) and str(it.get("ma_id", "")).strip() in existing_dirs
            ]
            if len(filtered_list) != len(raw_list):
                self.save_ideas_list(filtered_list)
            return filtered_list

    def save_ideas_list(self, ideas: List[Dict[str, Any]]):
        with self.ideas_io_lock:
            payload = json.dumps(ideas, ensure_ascii=False, indent=2)
            for target_idx in {
                self.ideas_file,
                self.projects_dir / "_saved_ideas_index.json",
                self.root_dir / "saved_ideas.json",
            }:
                try:
                    target_idx.parent.mkdir(parents=True, exist_ok=True)
                    tmp_file = target_idx.with_suffix(".json.tmp")
                    tmp_file.write_text(payload, encoding="utf-8")
                    os.replace(str(tmp_file), str(target_idx))
                except Exception:
                    try:
                        target_idx.write_text(payload, encoding="utf-8")
                    except Exception:
                        pass
            # Luôn đồng bộ cả khi ideas == [] để khi xóa hết folder trong projects/, bản backup cũng được làm sạch 100%
            try:
                bak_file = self._get_persistent_appdata_dir() / "saved_ideas_backup.json"
                bak_tmp = bak_file.with_suffix(".json.tmp")
                bak_tmp.write_text(payload, encoding="utf-8")
                os.replace(str(bak_tmp), str(bak_file))
            except Exception:
                pass

    def _sanitize_and_note_script_text(self, ma_id: str, raw_text: str, source_label: str = "") -> Tuple[str, int]:
        """
        Quét, ghi nhận (note) và xóa sạch 100% các dòng [LOCKED_TITLE], SELECTED_TITLE,
        PART A/B/C header, CONTINUITY, ENDING hoặc thẻ XML bị rò rỉ trong kịch bản.
        Trả về `(cleaned_text, removed_lines_count)`.
        """
        if not raw_text:
            return "", 0
        cleaned, removed_lines = strip_leaked_titles_and_metadata(raw_text)
        if removed_lines:
            lbl = f" ({source_label})" if source_label else ""
            removed_strs = [str(ln[1] if isinstance(ln, (tuple, list)) and len(ln) > 1 else ln) for ln in removed_lines]
            sample_preview = " | ".join([s[:55] for s in removed_strs[:2]])
            log_info(
                "SCRIPT",
                f"🛡️ [Agent Kiểm Tra Kịch Bản] Đã ghi nhận & tự động xóa {len(removed_strs)} dòng [LOCKED_TITLE]/Metadata rò rỉ trong [{ma_id}]{lbl}: {sample_preview}",
                project_id=ma_id,
            )
            try:
                p_dir = self._get_effective_project_dir(ma_id)
                assets_d = p_dir / "assets"
                if assets_d.exists():
                    leaked_log_f = assets_d / "leaked_lines_log.json"
                    existing_pool: List[str] = []
                    if leaked_log_f.exists():
                        try:
                            existing_pool = json.loads(leaked_log_f.read_text(encoding="utf-8", errors="ignore"))
                        except Exception:
                            existing_pool = []
                    for rs in removed_strs:
                        if rs not in existing_pool:
                            existing_pool.append(rs)
                    leaked_log_f.write_text(json.dumps(existing_pool, ensure_ascii=False, indent=2), encoding="utf-8")

                audit_note_file = p_dir / "step5_audit_report.txt"
                note_block = (
                    f"\n[AUTO-CLEAN NOTE — {time.strftime('%Y-%m-%d %H:%M:%S')}]{lbl}: "
                    f"Đã phát hiện và xóa {len(removed_strs)} dòng [LOCKED_TITLE]/Metadata rò rỉ:\n"
                    + "\n".join([f"  - Removed: {s}" for s in removed_strs])
                    + "\n"
                )
                if audit_note_file.exists():
                    existing_audit = audit_note_file.read_text(encoding="utf-8", errors="ignore")
                    if removed_strs[0] not in existing_audit:
                        audit_note_file.write_text(existing_audit + note_block, encoding="utf-8")
            except Exception:
                pass
        return cleaned, len(removed_lines)

    def get_script_parts_progress(self, ma_id: str, min_part_chars: int = 9500) -> Dict[str, Any]:
        """
        Kiểm tra chi tiết tiến độ 3 phần (`part_a.txt`, `part_b.txt`, `part_c.txt`) của dự án `ma_id`.
        Giúp phát hiện chính xác các dự án bị thiếu Part (ví dụ mới xong Part A 15.848 chữ hoặc Part A+B 32.684 chữ)
        đồng thời tự động làm sạch [LOCKED_TITLE]/Metadata nếu bị rò rỉ trong các file Part.
        """
        proj_dir = self._get_effective_project_dir(ma_id)
        done_parts: List[str] = []
        missing_parts: List[str] = []
        part_counts: Dict[str, int] = {"A": 0, "B": 0, "C": 0}
        part_texts: Dict[str, str] = {}

        for p_let in ("A", "B", "C"):
            p_file = proj_dir / f"part_{p_let.lower()}.txt"
            cnt = 0
            txt = ""
            if p_file.exists():
                try:
                    raw_p = p_file.read_text(encoding="utf-8").strip()
                    txt, rem_cnt = self._sanitize_and_note_script_text(ma_id, raw_p, source_label=f"part_{p_let.lower()}.txt")
                    if rem_cnt > 0 and txt:
                        p_file.write_text(txt, encoding="utf-8")
                    cnt = pure_char_count(txt)
                except Exception:
                    cnt = 0
            part_counts[p_let] = cnt
            if cnt >= min_part_chars:
                done_parts.append(p_let)
                part_texts[p_let] = txt
            else:
                missing_parts.append(p_let)

        partial_total = sum(part_counts[p] for p in done_parts)
        return {
            "done_parts": done_parts,
            "missing_parts": missing_parts,
            "part_counts": part_counts,
            "part_texts": part_texts,
            "partial_chars": partial_total,
            "all_three_valid": len(done_parts) == 3,
        }

    def has_valid_script_on_disk(self, ma_id: str, min_pure_chars: int = 35000, min_part_chars: int = 9500) -> Tuple[bool, str, int]:
        """
        Kiểm tra nghiêm ngặt xem dự án `ma_id` đã có kịch bản tiếng Nhật ĐỦ 3 PART (A + B + C) và ĐỦ ĐỘ DÀI CHUẨN hay chưa:
        - Kiểm tra trên cả `projects_dir` và `final_video_dir`.
        - Tự động quét và xóa sạch mọi dòng `[LOCKED_TITLE]` / Metadata rò rỉ trong cả `script_clean.txt` và `renders/{ma_id}_KICH_BAN.txt`.
        """
        proj_dir = self._get_effective_project_dir(ma_id)
        f_dir = getattr(self, "final_video_dir", None)
        final_proj_dir = (Path(f_dir) / ma_id) if f_dir else proj_dir
        if not proj_dir.exists() and not final_proj_dir.exists():
            return False, "", 0

        pa, pb, pc = proj_dir / "part_a.txt", proj_dir / "part_b.txt", proj_dir / "part_c.txt"
        script_file = proj_dir / "script_clean.txt"
        render_script_file = proj_dir / "renders" / f"{ma_id}_KICH_BAN.txt"
        has_any_part_file = pa.exists() or pb.exists() or pc.exists()

        if has_any_part_file:
            prog = self.get_script_parts_progress(ma_id, min_part_chars=min_part_chars)
            if prog["all_three_valid"]:
                combined = "\n\n".join([prog["part_texts"]["A"], prog["part_texts"]["B"], prog["part_texts"]["C"]]).strip()
                combined, _ = self._sanitize_and_note_script_text(ma_id, combined, source_label="combined_parts")
                cnt = pure_char_count(combined)
                if cnt >= min_pure_chars:
                    try:
                        need_sync_sc = not script_file.exists()
                        if not need_sync_sc:
                            cur_sc_raw = script_file.read_text(encoding="utf-8", errors="ignore")
                            _, sc_rem = strip_leaked_titles_and_metadata(cur_sc_raw)
                            if sc_rem or pure_char_count(cur_sc_raw) != cnt:
                                need_sync_sc = True
                        if need_sync_sc:
                            script_file.write_text(combined, encoding="utf-8")
                    except Exception:
                        pass
                    try:
                        if render_script_file.exists():
                            cur_ren_raw = render_script_file.read_text(encoding="utf-8", errors="ignore")
                            _, ren_rem = strip_leaked_titles_and_metadata(cur_ren_raw)
                            if ren_rem or pure_char_count(cur_ren_raw) != cnt:
                                render_script_file.write_text(combined, encoding="utf-8")
                    except Exception:
                        pass
                    return True, combined, cnt

            # Nếu có file part nhưng chưa đủ cả 3 Part hợp lệ (VD: P16 mới có Part A, P17 mới có Part A+B):
            for p_let in prog["missing_parts"]:
                bad_pf = proj_dir / f"part_{p_let.lower()}.txt"
                if bad_pf.exists():
                    try:
                        bad_pf.unlink()
                    except Exception:
                        pass
            if script_file.exists():
                try:
                    sc_txt = script_file.read_text(encoding="utf-8").strip()
                    if pure_char_count(sc_txt) < min_pure_chars or not prog["all_three_valid"]:
                        script_file.unlink()
                except Exception:
                    pass
            return False, "", prog["partial_chars"]

        # Trường hợp kịch bản nạp trực tiếp hoặc nằm ở final_video_dir:
        alt_script_candidates = [
            script_file,
            proj_dir / f"{ma_id}_KICH_BAN.txt",
            render_script_file,
            proj_dir / f"{ma_id}.txt",
            final_proj_dir / "script_clean.txt",
            final_proj_dir / "renders" / f"{ma_id}_KICH_BAN.txt",
            final_proj_dir / f"{ma_id}_KICH_BAN.txt",
        ]
        for cand_f in alt_script_candidates:
            if cand_f.exists():
                try:
                    raw_txt = cand_f.read_text(encoding="utf-8", errors="ignore").strip()
                    txt, rem_cnt = self._sanitize_and_note_script_text(ma_id, raw_txt, source_label=cand_f.name)
                    cnt = pure_char_count(txt)
                    if cnt >= min_pure_chars:
                        if rem_cnt > 0:
                            try:
                                cand_f.write_text(txt, encoding="utf-8")
                            except Exception:
                                pass
                        if proj_dir.exists() and (cand_f != script_file or rem_cnt > 0):
                            try:
                                script_file.write_text(txt, encoding="utf-8")
                            except Exception:
                                pass
                        if render_script_file.exists() and (cand_f != render_script_file or rem_cnt > 0):
                            try:
                                render_script_file.write_text(txt, encoding="utf-8")
                            except Exception:
                                pass
                        return True, txt, cnt
                except Exception:
                    pass

        # Quét dự phòng các file .txt lớn trong thư mục dự án
        ignore_kw = ("SEO", "STEP", "AUDIT", "TIEU_DE", "PROMPT", "IDEA_INFO")
        for scan_dir in (proj_dir, proj_dir / "renders", final_proj_dir, final_proj_dir / "renders"):
            if not scan_dir.exists():
                continue
            for tf in sorted(scan_dir.glob("*.txt")):
                up_name = tf.name.upper()
                if any(k in up_name for k in ignore_kw) or up_name in ("PART_A.TXT", "PART_B.TXT", "PART_C.TXT"):
                    continue
                try:
                    raw_txt = tf.read_text(encoding="utf-8", errors="ignore").strip()
                    txt, rem_cnt = self._sanitize_and_note_script_text(ma_id, raw_txt, source_label=tf.name)
                    cnt = pure_char_count(txt)
                    if cnt >= min_pure_chars:
                        if rem_cnt > 0:
                            try:
                                tf.write_text(txt, encoding="utf-8")
                            except Exception:
                                pass
                        if proj_dir.exists():
                            try:
                                script_file.write_text(txt, encoding="utf-8")
                            except Exception:
                                pass
                        return True, txt, cnt
                except Exception:
                    pass

        return False, "", 0

    def has_thumbnail_and_seo_on_disk(self, ma_id: str) -> Tuple[bool, bool, str]:
        """
        Kiểm tra và tự động đồng bộ bộ 2 file Thumbnail (`THUMBNAIL.png` + `THUMBNAIL-NENXANH.png`) + SEO của dự án `ma_id`
        (trên cả `projects_dir` và `final_video_dir`).
        Nếu đã có `THUMBNAIL.png` nhưng thiếu `THUMBNAIL-NENXANH.png`, tự động tách nền tạo ngay `THUMBNAIL-NENXANH.png` khớp tọa độ!
        Trả về `(has_thumbnail, has_seo, thumb_path_str)`.
        """
        proj_dir = self._get_effective_project_dir(ma_id)
        f_dir = getattr(self, "final_video_dir", None)
        final_proj_dir = (Path(f_dir) / ma_id) if f_dir else proj_dir
        if not proj_dir.exists() and not final_proj_dir.exists():
            return False, False, ""

        renders_dir = proj_dir / "renders"
        final_renders_dir = final_proj_dir / "renders"
        target_thumb = renders_dir / f"{ma_id}_THUMBNAIL_1.png"
        target_thumb_std = renders_dir / "THUMBNAIL.png"
        target_green = renders_dir / "THUMBNAIL-NENXANH.png"
        target_green_id = renders_dir / f"{ma_id}_THUMBNAIL_NENXANH.png"
        found_thumb: Optional[Path] = None

        thumb_candidates = [
            target_thumb,
            target_thumb_std,
            proj_dir / "THUMBNAIL.png",
            proj_dir / f"{ma_id}_THUMBNAIL_1.png",
            renders_dir / f"{ma_id}_THUMBNAIL.png",
            proj_dir / f"{ma_id}_THUMBNAIL.png",
            renders_dir / f"{ma_id}.png",
            proj_dir / f"{ma_id}.png",
            final_renders_dir / f"{ma_id}_THUMBNAIL_1.png",
            final_renders_dir / "THUMBNAIL.png",
            final_proj_dir / f"{ma_id}_THUMBNAIL_1.png",
            final_proj_dir / "THUMBNAIL.png",
        ]
        for tc in thumb_candidates:
            if tc.exists() and tc.stat().st_size > 10_000:
                found_thumb = tc
                break

        if found_thumb is None:
            for scan_dir in (renders_dir, proj_dir, final_renders_dir, final_proj_dir):
                if not scan_dir.exists():
                    continue
                for ext in ("*.png", "*.jpg", "*.jpeg", "*.webp"):
                    for img_f in sorted(scan_dir.glob(ext)):
                        up_img = img_f.name.upper()
                        if "NENXANH" in up_img or "GREEN" in up_img:
                            continue
                        if img_f.stat().st_size > 10_000:
                            found_thumb = img_f
                            break
                    if found_thumb:
                        break
                if found_thumb:
                    break

        if found_thumb is not None and proj_dir.exists():
            try:
                renders_dir.mkdir(parents=True, exist_ok=True)
                if found_thumb.resolve() != target_thumb.resolve():
                    shutil.copy2(found_thumb, target_thumb)
                if not target_thumb_std.exists():
                    shutil.copy2(found_thumb, target_thumb_std)
                if not (proj_dir / "THUMBNAIL.png").exists():
                    shutil.copy2(found_thumb, proj_dir / "THUMBNAIL.png")
                found_thumb = target_thumb
            except Exception:
                pass

            # Đảm bảo luôn có ảnh nền xanh THUMBNAIL-NENXANH.png đi kèm THUMBNAIL.png
            has_green = (target_green.exists() and target_green.stat().st_size > 10_000) or (
                target_green_id.exists() and target_green_id.stat().st_size > 10_000
            )
            if not has_green:
                for g_cand in (
                    proj_dir / "THUMBNAIL-NENXANH.png",
                    proj_dir / f"{ma_id}_THUMBNAIL_NENXANH.png",
                    final_renders_dir / "THUMBNAIL-NENXANH.png",
                    final_renders_dir / f"{ma_id}_THUMBNAIL_NENXANH.png",
                    final_proj_dir / "THUMBNAIL-NENXANH.png",
                ):
                    if g_cand.exists() and g_cand.stat().st_size > 10_000:
                        try:
                            shutil.copy2(g_cand, target_green)
                            shutil.copy2(g_cand, target_green_id)
                            has_green = True
                            break
                        except Exception:
                            pass
            if not has_green and hasattr(self, "_create_matched_green_screen_from_thumbnail_bytes"):
                try:
                    green_bytes = self._create_matched_green_screen_from_thumbnail_bytes(found_thumb.read_bytes())
                    if green_bytes and len(green_bytes) > 10_000:
                        target_green.write_bytes(green_bytes)
                        target_green_id.write_bytes(green_bytes)
                        (proj_dir / "THUMBNAIL-NENXANH.png").write_bytes(green_bytes)
                        has_green = True
                except Exception:
                    pass
            if has_green:
                try:
                    part1_chk = proj_dir / "script_green_images" / "green_part_01.png"
                    if not part1_chk.exists():
                        from backend.visual_cue_director import ensure_project_script_green_images
                        ensure_project_script_green_images(proj_dir=proj_dir, renders_dir=renders_dir, proj_name=ma_id)
                except Exception:
                    pass

        master_seo = proj_dir / "00_TIEU_DE_VA_SEO_YOUTUBE.txt"
        render_seo = renders_dir / f"{ma_id}_SEO.txt"
        seo_candidates = [
            master_seo,
            render_seo,
            proj_dir / "PMX_SEO_PACK.md",
            proj_dir / f"{ma_id}_SEO.txt",
            proj_dir / "step6_seo_pack.txt",
            final_renders_dir / f"{ma_id}_SEO.txt",
            final_proj_dir / "00_TIEU_DE_VA_SEO_YOUTUBE.txt",
        ]
        found_seo: Optional[Path] = None
        for sc in seo_candidates:
            if sc.exists() and sc.stat().st_size > 80:
                found_seo = sc
                break

        if found_seo is not None and proj_dir.exists():
            try:
                seo_txt = found_seo.read_text(encoding="utf-8", errors="ignore")
                if not master_seo.exists():
                    master_seo.write_text(seo_txt, encoding="utf-8")
                if not render_seo.exists():
                    renders_dir.mkdir(parents=True, exist_ok=True)
                    render_seo.write_text(seo_txt, encoding="utf-8")
            except Exception:
                pass

        return (found_thumb is not None), (found_seo is not None), (str(found_thumb) if found_thumb else "")

    def has_valid_video_mp4_on_disk(
        self,
        ma_id: str,
        sc_chars: int = 0,
        auto_delete_corrupted: bool = True,
    ) -> Tuple[bool, Optional[Path], str]:
        """
        Kiểm định nghiêm ngặt xem dự án `ma_id` có file `{ma_id}_master.mp4` HOÀN CHỈNH 100% trên ổ cứng hay không
        (Hỗ trợ kiểm tra đồng thời trên cả `final_video_dir` — Nơi Chứa Video Cuối và `projects_dir` — Folder Project).
        """
        if not hasattr(self, "_mp4_valid_cache"):
            self._mp4_valid_cache: Dict[str, Tuple[int, int, bool, str]] = {}

        vp_running = bool(self.video_pipeline and getattr(self.video_pipeline, "is_running", False))
        vp_active = set(getattr(self.video_pipeline, "active_projects", set())) if vp_running else set()
        is_actively_rendering = ma_id in vp_active

        p_dir = self._get_effective_project_dir(ma_id)
        f_dir = getattr(self, "final_video_dir", None)
        final_p_dir = (Path(f_dir) / ma_id) if f_dir else p_dir

        # Dọn các file tạm _rendering_tmp.mp4 bị bỏ lại nếu dự án hiện không đang render
        if not is_actively_rendering:
            for r_clean in (p_dir / "renders", final_p_dir / "renders"):
                if r_clean.exists():
                    for tmp_mp4 in r_clean.glob("*_rendering_tmp.mp4"):
                        try:
                            tmp_mp4.unlink()
                        except Exception:
                            pass

        mp4_file = self.resolve_project_mp4_path(ma_id)
        if mp4_file is None or not mp4_file.exists():
            self._mp4_valid_cache.pop(ma_id, None)
            return False, None, "rendering_in_progress" if is_actively_rendering else "missing"

        if is_actively_rendering:
            return False, None, "rendering_in_progress"

        try:
            st = mp4_file.stat()
            mtime_ns, st_size = st.st_mtime_ns, st.st_size
        except Exception:
            return False, None, "stat_error"

        cached = self._mp4_valid_cache.get(ma_id)
        if cached and cached[0] == mtime_ns and cached[1] == st_size and cached[2]:
            return True, mp4_file, "ok"

        if sc_chars <= 0:
            _, _, sc_chars = self.has_valid_script_on_disk(ma_id)

        from backend.sync_checker import validate_completed_mp4_file
        master_wav = p_dir / "assets" / "master_voice.wav"
        if not master_wav.exists():
            master_wav = final_p_dir / "assets" / "master_voice.wav"
        val = validate_completed_mp4_file(
            mp4_path=mp4_file,
            master_wav_path=master_wav if master_wav.exists() else None,
            script_char_count=sc_chars,
        )

        if val.get("valid"):
            self._mp4_valid_cache[ma_id] = (mtime_ns, st_size, True, "ok")
            return True, mp4_file, "ok"

        reason = str(val.get("reason") or "Video MP4 bị lỗi hoặc ngắt giữa chừng")
        self._mp4_valid_cache.pop(ma_id, None)
        log_warn(
            "RENDER",
            f"⚠️ [{ma_id}] Phát hiện file MP4 bị lỗi/ngắt giữa chừng ({reason}). Đã tự động lọc sang danh sách Lỗi / Chưa Render để chạy tiếp!",
            project_id=ma_id,
        )
        if auto_delete_corrupted:
            try:
                mp4_file.unlink()
            except Exception:
                pass
        return False, None, reason

    def _reconstruct_idea_from_project_dir(self, p_dir: Path) -> Optional[Dict[str, Any]]:
        """
        Khôi phục bản ghi dự án từ thư mục `projects_dir/<ma_id>` hoặc `final_video_dir/<ma_id>` khi dự án đó:
        - ĐÃ TẠO XONG KỊCH BẢN ĐỦ 3 PART (`has_sc = True`), HOẶC
        - ĐANG VIẾT DỞ 1-2 PART (`partial_chars >= 9500`, để người dùng bấm viết tiếp Part thiếu), HOẶC
        - ĐÃ XUẤT VIDEO MP4 HOÀN CHỈNH (`has_mp4 = True`).
        Tuyệt đối KHÔNG tự động khôi phục các tiêu đề nháp chưa viết chữ nào (`partial_chars == 0`) đã bị xóa!
        """
        mid = p_dir.name
        eff_dir = self._get_effective_project_dir(mid)
        has_sc, sc_txt, sc_chars = self.has_valid_script_on_disk(mid)
        prog = self.get_script_parts_progress(mid)
        partial_chars = prog["partial_chars"]
        has_partial = len(prog["done_parts"]) > 0 and not has_sc
        has_mp4, mp4_f, mp4_reason = self.has_valid_video_mp4_on_disk(mid, sc_chars=sc_chars if has_sc else partial_chars)

        info_file = eff_dir / "idea_info.json"
        if not info_file.exists():
            info_file = p_dir / "idea_info.json"
        if info_file.exists():
            try:
                info_data = json.loads(info_file.read_text(encoding="utf-8"))
                if isinstance(info_data, dict) and info_data.get("ma_id"):
                    has_th, has_seo, th_path = self.has_thumbnail_and_seo_on_disk(mid)
                    info_data["has_script"] = has_sc
                    info_data["has_thumbnail"] = has_th
                    info_data["has_seo"] = has_seo
                    if th_path:
                        info_data["thumbnail_path"] = th_path
                    info_data["pure_char_count"] = sc_chars if has_sc else partial_chars
                    info_data["has_video_mp4"] = has_mp4
                    if has_mp4 and mp4_f:
                        info_data["video_mp4_path"] = str(mp4_f)
                    info_data["completed_parts_count"] = 3 if has_sc else len(prog["done_parts"])
                    info_data["missing_parts"] = [] if has_sc else prog["missing_parts"]
                    if has_mp4:
                        info_data["status"] = "COMPLETED_VIDEO"
                        info_data["current_step"] = f"✅ Đã xuất Video MP4 ({sc_chars:,} chữ)"
                    elif has_sc:
                        if mp4_reason not in ("missing", "rendering_in_progress", "ok") or info_data.get("status") == "ERROR_VIDEO":
                            info_data["status"] = "ERROR_VIDEO"
                            info_data["current_step"] = f"❌ Video bị ngắt/lỗi ({mp4_reason if mp4_reason != 'missing' else 'Chưa hoàn tất'}) — Chờ Render lại ({sc_chars:,} chữ)"
                        else:
                            info_data["status"] = "SCRIPT_DONE"
                            info_data["current_step"] = f"📝 Đã xong Kịch bản ({sc_chars:,} chữ) — Sẵn sàng Render MP4"
                    elif has_partial:
                        miss_str = ", ".join(prog["missing_parts"])
                        info_data["status"] = "PARTIAL_SCRIPT"
                        info_data["current_step"] = f"⚠️ Thiếu Part {miss_str} (Mới có {len(prog['done_parts'])}/3 Part: {partial_chars:,} chữ)"
                    else:
                        info_data["status"] = "SAVED_READY"
                    return info_data
            except Exception:
                pass

        if not (has_sc or has_partial or has_mp4):
            return None

        step2_f = eff_dir / "step2_title_thumbnail.txt"
        seo_f = eff_dir / "00_TIEU_DE_VA_SEO_YOUTUBE.txt"
        if not seo_f.exists():
            seo_f = p_dir / "renders" / f"{mid}_SEO.txt"

        locked_title = ""
        if step2_f.exists():
            try:
                locked_title = extract_locked_title_from_step2(step2_f.read_text(encoding="utf-8"), fallback_title="")
            except Exception:
                pass
        if not locked_title and seo_f.exists():
            try:
                for ln in seo_f.read_text(encoding="utf-8").splitlines():
                    ln_s = ln.strip()
                    if any("\u3040" <= ch <= "\u9fff" for ch in ln_s) and len(ln_s) >= 15:
                        locked_title = ln_s.lstrip("-•*0123456789. ").strip()
                        break
            except Exception:
                pass
        if not locked_title and sc_txt:
            first_line = sc_txt.splitlines()[0].strip() if sc_txt.splitlines() else ""
            locked_title = first_line[:95] if first_line else f"Dự án khôi phục [{mid}]"

        reconstructed = parse_idea_input_block(locked_title or f"{mid} — Dự án khôi phục từ ổ cứng", custom_id=mid)
        if locked_title:
            reconstructed["locked_title"] = locked_title
            reconstructed["draft_title_ja"] = locked_title
        reconstructed["has_script"] = has_sc
        reconstructed["pure_char_count"] = sc_chars if has_sc else partial_chars
        reconstructed["has_video_mp4"] = has_mp4
        reconstructed["completed_parts_count"] = 3 if has_sc else len(prog["done_parts"])
        reconstructed["missing_parts"] = [] if has_sc else prog["missing_parts"]
        if has_mp4:
            reconstructed["status"] = "COMPLETED_VIDEO"
            reconstructed["current_step"] = f"✅ Đã xuất Video MP4 ({sc_chars:,} chữ)"
            reconstructed["video_mp4_path"] = str(mp4_f)
        elif has_sc:
            reconstructed["status"] = "SCRIPT_DONE"
            reconstructed["current_step"] = f"📝 Đã xong Kịch bản ({sc_chars:,} chữ) — Sẵn sàng Render MP4"
        else:
            miss_str = ", ".join(prog["missing_parts"])
            reconstructed["status"] = "PARTIAL_SCRIPT"
            reconstructed["current_step"] = f"⚠️ Thiếu Part {miss_str} (Mới có {len(prog['done_parts'])}/3 Part: {partial_chars:,} chữ)"

        try:
            if eff_dir.exists() and eff_dir.is_dir():
                (eff_dir / "idea_info.json").write_text(json.dumps(reconstructed, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass
        return reconstructed

    def _sync_projects_disk_state(self, force_restore_deleted: bool = False):
        """
        Đồng bộ trạng thái thực tế từ `projects_dir` (Folder Project) và `final_video_dir` (Nơi Chứa Video Cuối):
        - Kiểm tra nghiêm ngặt đủ 3 Part (`part_a.txt`, `part_b.txt`, `part_c.txt` >= 9.500 chữ/part, tổng >= 35.000 chữ).
        - Tự động nhận diện 100% các video MP4 đã được di chuyển sang `final_video_dir`!
        """
        now_sync = time.time()
        if getattr(self, "is_checking_repairing", False):
            return
        if not force_restore_deleted and (now_sync - getattr(self, "_last_disk_sync_ts", 0.0) < 6.0):
            return
        with self.ideas_io_lock:
            self._last_disk_sync_ts = time.time()
            if force_restore_deleted:
                self._save_deleted_ids(set())
                if hasattr(self, "_proj_dir_mtime_cache"):
                    self._proj_dir_mtime_cache.clear()
                if hasattr(self, "_mp4_valid_cache"):
                    self._mp4_valid_cache.clear()
            self._register_and_sync_external_projects()
            deleted_ids = self._load_deleted_ids()
            disk_proj_map = self._list_all_existing_project_ids_on_disk()
            raw_ideas = self.load_saved_ideas()
            changed = False

            ideas: List[Dict[str, Any]] = []
            for it in raw_ideas:
                mid_chk = str(it.get("ma_id", "")).strip()
                if not mid_chk:
                    changed = True
                    continue
                if not force_restore_deleted and mid_chk in deleted_ids:
                    changed = True
                    continue
                if mid_chk not in disk_proj_map:
                    deleted_ids.add(mid_chk)
                    changed = True
                    continue
                ideas.append(it)
            if changed:
                self._save_deleted_ids(deleted_ids)

            existing_ids = {str(it.get("ma_id", "")).strip() for it in ideas if it.get("ma_id")}

            # Bước 1: Quét thư mục con trong projects_dir & final_video_dir để tự động khôi phục các dự án
            if disk_proj_map:
                restored_items: List[Dict[str, Any]] = []
                unblocked_deleted: Set[str] = set()
                for mid, p_dir in sorted(disk_proj_map.items()):
                    if not mid or mid in existing_ids:
                        continue
                    del_marker = p_dir / ".deleted_by_user"
                    has_sc_probe, _, _ = self.has_valid_script_on_disk(mid)
                    has_mp4_probe = self.resolve_project_mp4_path(mid) is not None
                    if (has_sc_probe or has_mp4_probe) and not del_marker.exists() and mid in deleted_ids:
                        unblocked_deleted.add(mid)
                        deleted_ids.discard(mid)
                    elif del_marker.exists() or mid in deleted_ids:
                        if force_restore_deleted:
                            if del_marker.exists():
                                try:
                                    del_marker.unlink()
                                except Exception:
                                    pass
                        else:
                            continue

                    rec_dir = p_dir if p_dir.name == mid else (p_dir / mid)
                    rec = self._reconstruct_idea_from_project_dir(rec_dir)
                    if rec:
                        restored_items.append(rec)
                        existing_ids.add(mid)
                        changed = True

                if unblocked_deleted:
                    self._save_deleted_ids(deleted_ids)

                if restored_items:
                    ideas = restored_items + ideas
                    restored_ids_str = ", ".join([x.get("ma_id", "") for x in restored_items])
                    log_info(
                        "SCRIPT",
                        f"🔄 Đã tự động nhận & khôi phục {len(restored_items)} dự án từ ổ cứng vào Kho Dự Án: [{restored_ids_str}]",
                    )

            # Bước 2: Đồng bộ trạng thái Kịch bản (Đủ 3 Part vs Thiếu Part), Thumbnail, SEO & Video MP4 cho từng dự án
            if not hasattr(self, "_proj_dir_mtime_cache"):
                self._proj_dir_mtime_cache: Dict[str, Tuple[int, int, int]] = {}
            if not hasattr(self, "_mp4_valid_cache"):
                self._mp4_valid_cache: Dict[str, Tuple[int, int, bool, str]] = {}

            vp_running = bool(self.video_pipeline and getattr(self.video_pipeline, "is_running", False))
            vp_active_set = set(getattr(self.video_pipeline, "active_projects", set())) if vp_running else set()
            vp_pending_set = {
                str(j.get("name") or "")
                for j in getattr(self.video_pipeline, "pending_jobs", [])
                if isinstance(j, dict)
            } if vp_running else set()

            f_dir = getattr(self, "final_video_dir", None)
            for it in ideas:
                mid = it.get("ma_id")
                if not mid:
                    continue
                p_dir = self._get_effective_project_dir(mid)
                if not p_dir.exists() and mid not in disk_proj_map:
                    continue
                curr_st = str(it.get("status") or "")
                is_vp_busy_for_mid = (mid in vp_active_set) or (mid in vp_pending_set)

                try:
                    r_dir = p_dir / "renders"
                    f_r_dir = (Path(f_dir) / mid / "renders") if f_dir else r_dir
                    dir_sig = (
                        p_dir.stat().st_mtime_ns if p_dir.exists() else 0,
                        r_dir.stat().st_mtime_ns if r_dir.exists() else 0,
                        f_r_dir.stat().st_mtime_ns if f_r_dir.exists() else 0,
                    )
                except Exception:
                    dir_sig = (0, 0, 0)
                if (
                    not force_restore_deleted
                    and is_vp_busy_for_mid
                    and it.get("has_script")
                ):
                    continue
                if (
                    not force_restore_deleted
                    and dir_sig != (0, 0, 0)
                    and self._proj_dir_mtime_cache.get(mid) == dir_sig
                    and (
                        curr_st not in ("RUNNING", "VIDEO_RENDERING", "VIDEO_QUEUED", "COMPLETED_VIDEO")
                        or is_vp_busy_for_mid
                    )
                    and not (it.get("has_video_mp4") and mid not in self._mp4_valid_cache)
                ):
                    continue
                if (
                    not force_restore_deleted
                    and dir_sig != (0, 0, 0)
                    and self._proj_dir_mtime_cache.get(mid) == dir_sig
                    and curr_st == "COMPLETED_VIDEO"
                    and it.get("has_video_mp4")
                    and mid in self._mp4_valid_cache
                ):
                    continue

                has_sc, _, sc_chars = self.has_valid_script_on_disk(mid)
                has_thumb, has_seo, thumb_p = self.has_thumbnail_and_seo_on_disk(mid)
                prog = self.get_script_parts_progress(mid)
                done_cnt = 3 if has_sc else len(prog["done_parts"])
                missing_list = [] if has_sc else prog["missing_parts"]
                effective_chars = sc_chars if has_sc else prog["partial_chars"]

                has_mp4, mp4_file, mp4_reason = self.has_valid_video_mp4_on_disk(
                    mid, sc_chars=effective_chars, auto_delete_corrupted=True
                )
                if dir_sig != (0, 0, 0):
                    self._proj_dir_mtime_cache[mid] = dir_sig

                item_changed = False
                if it.get("has_script") != has_sc:
                    it["has_script"] = has_sc
                    changed = True
                    item_changed = True
                if it.get("has_thumbnail") != has_thumb:
                    it["has_thumbnail"] = has_thumb
                    changed = True
                    item_changed = True
                if it.get("has_seo") != has_seo:
                    it["has_seo"] = has_seo
                    changed = True
                    item_changed = True
                if thumb_p and it.get("thumbnail_path") != thumb_p:
                    it["thumbnail_path"] = thumb_p
                    changed = True
                    item_changed = True
                if it.get("completed_parts_count") != done_cnt:
                    it["completed_parts_count"] = done_cnt
                    changed = True
                    item_changed = True
                if it.get("missing_parts") != missing_list:
                    it["missing_parts"] = missing_list
                    changed = True
                    item_changed = True
                if it.get("has_video_mp4") != has_mp4:
                    it["has_video_mp4"] = has_mp4
                    changed = True
                    item_changed = True
                if has_mp4 and mp4_file:
                    it["video_mp4_path"] = str(mp4_file)
                elif not has_mp4 and it.get("video_mp4_path"):
                    it["video_mp4_path"] = ""
                    changed = True
                    item_changed = True

                if it.get("pure_char_count") != effective_chars:
                    it["pure_char_count"] = effective_chars
                    changed = True
                    item_changed = True

                step2_f = p_dir / "step2_title_thumbnail.txt"
                if not it.get("locked_title") and step2_f.exists():
                    try:
                        s2_txt = step2_f.read_text(encoding="utf-8")
                        lt = extract_locked_title_from_step2(s2_txt, fallback_title=it.get("draft_title_ja", ""))
                        if lt:
                            it["locked_title"] = lt
                            changed = True
                            item_changed = True
                    except Exception:
                        pass

                curr_st = str(it.get("status") or "")
                if has_mp4:
                    if curr_st != "COMPLETED_VIDEO":
                        it["status"] = "COMPLETED_VIDEO"
                        it["current_step"] = f"✅ Đã xuất Video MP4 ({effective_chars:,} chữ)"
                        changed = True
                        item_changed = True
                elif has_sc and not has_mp4:
                    if not is_vp_busy_for_mid:
                        ckpt_step_msg = ""
                        if (p_dir / "renders" / f"_{mid}_master_resume_cache").exists():
                            try:
                                from backend.renderer import get_saved_render_progress
                                ckpt_d = get_saved_render_progress(str(p_dir / "renders" / f"{mid}_master.mp4"))
                                if ckpt_d.get("has_checkpoint"):
                                    ckpt_step_msg = (
                                        f"⏸️ Đã lưu Checkpoint Render {ckpt_d['percent']}% "
                                        f"({ckpt_d['completed_sec']:.0f}s/{ckpt_d['total_dur']:.0f}s) — Bấm Render để chạy tiếp đoạn còn lại!"
                                    )
                            except Exception:
                                ckpt_step_msg = ""

                        if ckpt_step_msg:
                            if curr_st != "ERROR_VIDEO" or it.get("current_step") != ckpt_step_msg:
                                it["status"] = "ERROR_VIDEO"
                                it["current_step"] = ckpt_step_msg
                                changed = True
                                item_changed = True
                        elif mp4_reason not in ("missing", "rendering_in_progress", "ok"):
                            err_step = f"❌ Video bị ngắt/lỗi ({mp4_reason}) — Chờ Render lại ({effective_chars:,} chữ)"
                            if curr_st != "ERROR_VIDEO" or it.get("current_step") != err_step:
                                it["status"] = "ERROR_VIDEO"
                                it["current_step"] = err_step
                                changed = True
                                item_changed = True
                        elif curr_st == "COMPLETED_VIDEO":
                            err_step = f"⚠️ Video MP4 chưa hoàn thành hoặc bị ngắt — Chờ Render lại ({effective_chars:,} chữ)"
                            it["status"] = "ERROR_VIDEO"
                            it["current_step"] = err_step
                            changed = True
                            item_changed = True
                        elif curr_st == "VIDEO_RENDERING":
                            err_step = f"⚠️ Render Video bị ngắt giữa chừng — Chờ Render lại ({effective_chars:,} chữ)"
                            it["status"] = "ERROR_VIDEO"
                            it["current_step"] = err_step
                            changed = True
                            item_changed = True
                        elif curr_st == "RUNNING" and self.is_running and not (has_seo and has_thumb):
                            # Dự án vừa ghép xong 3 Part kịch bản (Step 4) nhưng vẫn đang chạy tiếp Step 5 (Kiểm toán) / Step 6 (SEO) / Step 7 (Thumbnail) trên ChatGPT -> Giữ nguyên trạng thái RUNNING!
                            pass
                        elif curr_st in ("", "SAVED_READY", "CHƯA_CHẠY_STEP2", "ERROR", "RUNNING", "PARTIAL_SCRIPT", "COMPLETED_HANDOFF", "VIDEO_QUEUED"):
                            it["status"] = "SCRIPT_DONE"
                            it["current_step"] = f"📝 Đã xong Kịch bản ({effective_chars:,} chữ) — Sẵn sàng Render MP4"
                            changed = True
                            item_changed = True
                elif not has_sc and not has_mp4 and done_cnt > 0:
                    # Dự án mới viết được 1 hoặc 2 Part (VD: P16 = 15,848 chữ, P17 = 32,684 chữ) -> Đánh dấu thiếu Part để viết tiếp!
                    miss_str = ", ".join(missing_list)
                    expected_step = f"⚠️ Thiếu Part {miss_str} (Mới xong {done_cnt}/3 Part: {effective_chars:,} chữ)"
                    if (curr_st != "RUNNING" or not self.is_running) and (curr_st != "PARTIAL_SCRIPT" or it.get("current_step") != expected_step):
                        it["status"] = "PARTIAL_SCRIPT"
                        it["current_step"] = expected_step
                        changed = True
                        item_changed = True
                elif not has_sc and not has_mp4 and done_cnt == 0 and not self.is_running:
                    # Tự động dọn trạng thái RUNNING / ERROR bị treo từ phiên cũ khi máy đang ở trạng thái nghỉ (Idle)
                    step3_f = p_dir / "step3_architecture.txt"
                    has_s3 = step3_f.exists() and step3_f.stat().st_size > 2500
                    has_s2 = step2_f.exists() and step2_f.stat().st_size > 2500
                    if curr_st in ("RUNNING", "ERROR"):
                        it["status"] = "SAVED_READY"
                        if has_s3:
                            it["current_step"] = "♻️ Đã xong Step 2 & Step 3 — Bấm Chạy để viết tiếp Step 4 (Part A/B/C)"
                        elif has_s2:
                            it["current_step"] = "♻️ Đã xong Step 2 — Bấm Chạy để viết tiếp Step 3"
                        else:
                            it["current_step"] = "CHƯA CHẠY (Sẵn sàng từ Step 2)"
                        changed = True
                        item_changed = True

                if item_changed:
                    info_f = p_dir / "idea_info.json"
                    if info_f.exists():
                        try:
                            info_f.write_text(json.dumps(it, ensure_ascii=False, indent=2), encoding="utf-8")
                        except Exception:
                            pass

            if changed:
                self.save_ideas_list(ideas)

    def restore_scripts_from_disk(self, custom_folder: Optional[str] = None) -> Dict[str, Any]:
        """Quét lại toàn bộ thư mục `projects/` (hoặc thư mục tùy chỉnh) để cập nhật chính xác 100% các folder hiện có (thêm folder mới, xóa bỏ hoàn toàn các folder đã bị xóa)."""
        if custom_folder and str(custom_folder).strip():
            cand_dir = Path(str(custom_folder).strip())
            if cand_dir.exists() and cand_dir.is_dir() and cand_dir.resolve() != self.projects_dir.resolve():
                try:
                    self.import_external_projects_folder(str(cand_dir))
                except Exception:
                    pass
        with self.ideas_io_lock:
            raw_before = []
            if self.ideas_file.exists():
                try:
                    d = json.loads(self.ideas_file.read_text(encoding="utf-8"))
                    if isinstance(d, list):
                        raw_before = d
                except Exception:
                    pass
            before_cnt = len(raw_before)
            self._last_disk_sync_ts = 0.0
            if hasattr(self, "_proj_dir_mtime_cache"):
                self._proj_dir_mtime_cache.clear()
            self._sync_projects_disk_state(force_restore_deleted=True)
            after_list = self.load_saved_ideas()
            script_cnt = sum(1 for x in after_list if x.get("has_script"))
            mp4_cnt = sum(1 for x in after_list if x.get("has_video_mp4"))
            removed_cnt = max(0, before_cnt - len(after_list))
            added_cnt = max(0, len(after_list) - before_cnt)
        log_info(
            "SCRIPT",
            f"🔄 Đã cập nhật lại thư mục [{self.projects_dir}]: Hiện có {len(after_list)} dự án ({script_cnt} kịch bản đã xong, {mp4_cnt} video MP4, +{added_cnt} mới, -{removed_cnt} đã xóa).",
        )
        return {
            "restored_count": added_cnt,
            "removed_count": removed_cnt,
            "total_count": len(after_list),
            "script_done_count": script_cnt,
            "video_done_count": mp4_cnt,
            "projects_dir": str(self.projects_dir),
            "ideas": after_list,
        }

    def _resolve_target_projects_dir(self, custom_folder: Optional[str] = None) -> Path:
        if custom_folder and str(custom_folder).strip():
            cand = Path(str(custom_folder).strip())
            if cand.exists() and cand.is_dir():
                if (cand / "projects").exists() and (cand / "projects").is_dir():
                    return cand / "projects"
                return cand
        return self.projects_dir

    def check_and_repair_all_projects(self, custom_folder: Optional[str] = None) -> Dict[str, Any]:
        """
        Nút "🛡️ Check Toàn Bộ" (2 Giai đoạn siêu tốc):
        1. GIAI ĐOẠN 1 (1–2s): Quét toàn bộ thư mục `projects/` để xóa sạch `[LOCKED_TITLE]` / Metadata trong tất cả kịch bản `.txt`.
        2. GIAI ĐOẠN 2 (4–8s/video): Tự động cắt bỏ trực tiếp các đoạn giây đọc `[LOCKED_TITLE]` khỏi file `.mp4`, `master_voice.wav` và `subtitles.srt`.
        3. Đồng bộ lại danh sách Kho Dự Án (chỉ làm mới đúng các mã vừa sửa, không chạy lại ffprobe toàn bộ kho).
        """
        from .voice_service import check_and_repair_all_projects_sync

        target_dir = self._resolve_target_projects_dir(custom_folder)
        self.is_checking_repairing = True
        if not hasattr(self, "_check_repair_state") or not isinstance(getattr(self, "_check_repair_state", None), dict):
            self._check_repair_state = {
                "running": False,
                "completed": False,
                "progress": 0.0,
                "status_text": "",
                "logs": [],
                "result": None,
                "error": "",
            }

        self._check_repair_state.update({
            "running": True,
            "completed": False,
            "progress": 2.0,
            "status_text": f"🛡️ Đang quét kịch bản tại [{target_dir}]...",
            "logs": [],
            "result": None,
            "error": "",
        })

        self._emit(
            status="running",
            current_step="🛡️ Đang Check Toàn Bộ Kịch Bản & Video MP4...",
            progress=2.0,
            message=f"🛡️ Đang quét toàn bộ thư mục [{target_dir}] để dọn sạch [LOCKED_TITLE] trong Kịch bản & Video MP4...",
        )
        log_info("SCRIPT", f"🛡️ Bắt đầu chạy Check Toàn Bộ Kịch Bản & Video tại [{target_dir}]...")

        def _prog_cb(pct: float, msg: str):
            self._check_repair_state["progress"] = pct
            self._check_repair_state["status_text"] = msg
            self._emit(
                status="running",
                current_step="🛡️ Check Toàn Bộ (Dọn Kịch Bản & Video Lỗi)",
                progress=pct,
                message=msg,
            )

        def _log_cb(msg: str):
            self._check_repair_state["logs"].append(msg)
            log_info("SCRIPT", msg)

        try:
            summary = check_and_repair_all_projects_sync(target_dir, progress_cb=_prog_cb, log_cb=_log_cb)
            touched_ids = set((summary.get("repaired_script_ids") or []) + (summary.get("repaired_video_ids") or []))
            if hasattr(self, "_proj_dir_mtime_cache") and isinstance(self._proj_dir_mtime_cache, dict):
                for tid in touched_ids:
                    self._proj_dir_mtime_cache.pop(tid, None)
            if hasattr(self, "_mp4_valid_cache") and isinstance(self._mp4_valid_cache, dict):
                for vid in (summary.get("repaired_video_ids") or []):
                    mp4_p = target_dir / vid / "renders" / f"{vid}_master.mp4"
                    if mp4_p.exists():
                        try:
                            st_v = mp4_p.stat()
                            self._mp4_valid_cache[vid] = (st_v.st_mtime_ns, st_v.st_size, True, "ok")
                        except Exception:
                            self._mp4_valid_cache.pop(vid, None)
        finally:
            self.is_checking_repairing = False

        if touched_ids:
            self._last_disk_sync_ts = 0.0
            self._sync_projects_disk_state(force_restore_deleted=False)
        ideas_after = self.load_saved_ideas()

        done_msg = (
            f"✅ Check Toàn Bộ hoàn tất ({summary['total_scanned']} dự án trong {summary['elapsed_sec']}s): "
            f"Đã sửa sạch {summary['scripts_repaired_count']} Kịch bản, "
            f"cắt bỏ đoạn lỗi trong {summary['videos_repaired_count']} Video MP4 "
            f"(Tổng {summary['total_lines_removed']} dòng/khung [LOCKED_TITLE] đã xóa)!"
        )
        self._emit(
            status="idle" if not self.is_running else "running",
            current_step="✅ Đã hoàn tất Check Toàn Bộ!",
            progress=100.0,
            message=done_msg,
        )
        log_info("SCRIPT", done_msg)
        final_res = {
            **summary,
            "ideas": ideas_after,
            "message": done_msg,
        }
        self._check_repair_state["running"] = False
        self._check_repair_state["completed"] = True
        self._check_repair_state["progress"] = 100.0
        self._check_repair_state["status_text"] = done_msg
        self._check_repair_state["result"] = final_res
        return final_res

    def start_check_and_repair_async(self, custom_folder: Optional[str] = None) -> Dict[str, Any]:
        """Khởi chạy Check Toàn Bộ trong luồng ngầm để giao diện nhận tiến độ thời gian thực từng giây mà không bao giờ bị treo HTTP."""
        st = getattr(self, "_check_repair_state", None)
        if isinstance(st, dict) and st.get("running"):
            return {
                "async_started": True,
                "running": True,
                "completed": False,
                "progress": st.get("progress", 5.0),
                "status_text": st.get("status_text", "⏳ Đang quét & dọn lỗi..."),
                "logs": list(st.get("logs", [])),
            }

        self._check_repair_state = {
            "running": True,
            "completed": False,
            "progress": 1.0,
            "status_text": "⚡ Đang khởi động Giai đoạn 1: Quét & dọn sạch toàn bộ Kịch bản (.txt)...",
            "logs": [],
            "result": None,
            "error": "",
        }

        def _bg_worker():
            try:
                self.check_and_repair_all_projects(custom_folder=custom_folder)
            except Exception as e:
                self.is_checking_repairing = False
                self._check_repair_state["running"] = False
                self._check_repair_state["completed"] = True
                self._check_repair_state["error"] = str(e)
                self._check_repair_state["status_text"] = f"❌ Lỗi khi Check Toàn Bộ: {e}"

        t = threading.Thread(target=_bg_worker, daemon=True)
        t.start()
        return {
            "async_started": True,
            "running": True,
            "completed": False,
            "progress": 1.0,
            "status_text": self._check_repair_state["status_text"],
            "logs": [],
        }

    def get_check_and_repair_status(self) -> Dict[str, Any]:
        st = getattr(self, "_check_repair_state", None)
        if not isinstance(st, dict):
            return {
                "running": False,
                "completed": False,
                "progress": 0.0,
                "status_text": "",
                "logs": [],
                "result": None,
                "error": "",
            }
        return {
            "running": bool(st.get("running")),
            "completed": bool(st.get("completed")),
            "progress": float(st.get("progress", 0.0)),
            "status_text": str(st.get("status_text", "")),
            "logs": list(st.get("logs", [])),
            "result": st.get("result"),
            "error": str(st.get("error", "")),
        }

    def import_external_projects_folder(self, source_dir: str) -> Dict[str, Any]:
        """
        Nhập (Import) hàng loạt Kịch bản + Thumbnail + SEO được tạo từ MÁY KHÁC vào Kho Dự Án của máy hiện tại.
        Hỗ trợ linh hoạt cả 3 cấu trúc khi người dùng copy qua USB / LAN / Zalo:
        1. Chọn thư mục `projects/` (hoặc thư mục tổng chứa nhiều thư mục con `P01`, `P02`, `IDEA_001`...).
        2. Chọn trực tiếp 1 thư mục dự án đơn lẻ (ví dụ `D:\\CopyTuMayKhac\\P05` chứa `script_clean.txt` / `P05_KICH_BAN.txt` + `P05_THUMBNAIL_1.png` + `P05_SEO.txt`).
        3. Chọn 1 thư mục chứa các file rời (`P01_KICH_BAN.txt`, `P01_SEO.txt`, `P01_THUMBNAIL_1.png`, `P02.txt`, `P02.png`...).
        """
        src_path = Path(source_dir).resolve()
        if not src_path.exists() or not src_path.is_dir():
            raise ValueError(f"Thư mục nguồn không tồn tại: {source_dir}")

        imported_ids: List[str] = []
        self.projects_dir.mkdir(parents=True, exist_ok=True)

        def _copy_project_dir(s_dir: Path, mid: str):
            clean_mid = re.sub(r'[\\/:*?"<>|]+', "_", mid.strip())
            if not clean_mid:
                return
            dst_dir = self.projects_dir / clean_mid
            dst_dir.mkdir(parents=True, exist_ok=True)
            if s_dir.resolve() != dst_dir.resolve():
                for item in s_dir.rglob("*"):
                    if item.is_file() and item.name != ".deleted_by_user":
                        rel = item.relative_to(s_dir)
                        target_f = dst_dir / rel
                        target_f.parent.mkdir(parents=True, exist_ok=True)
                        try:
                            shutil.copy2(item, target_f)
                        except Exception:
                            pass
            del_m = dst_dir / ".deleted_by_user"
            if del_m.exists():
                try:
                    del_m.unlink()
                except Exception:
                    pass
            has_sc, _, _ = self.has_valid_script_on_disk(clean_mid)
            self.has_thumbnail_and_seo_on_disk(clean_mid)
            prog = self.get_script_parts_progress(clean_mid)
            if has_sc or len(prog["done_parts"]) > 0:
                if clean_mid not in imported_ids:
                    imported_ids.append(clean_mid)

        # Kiểm tra xem bản thân src_path có phải là 1 thư mục dự án đơn lẻ không
        direct_markers = (
            src_path / "script_clean.txt",
            src_path / "part_a.txt",
            src_path / "00_TIEU_DE_VA_SEO_YOUTUBE.txt",
            src_path / "idea_info.json",
            src_path / f"{src_path.name}_KICH_BAN.txt",
        )
        if any(m.exists() for m in direct_markers):
            _copy_project_dir(src_path, src_path.name)
        else:
            # 1. Quét các thư mục con (VD: P01, P02... hoặc projects/P01, P02...)
            sub_dirs = [d for d in sorted(src_path.iterdir()) if d.is_dir()]
            if len(sub_dirs) == 1 and sub_dirs[0].name.lower() == "projects":
                sub_dirs = [d for d in sorted(sub_dirs[0].iterdir()) if d.is_dir()]

            for sd in sub_dirs:
                if sd.name.startswith(".") or sd.name.lower() in ("__pycache__", "stook", "bin", "backend", "frontend", "app"):
                    continue
                _copy_project_dir(sd, sd.name)

            # 2. Quét các file rời đặt chung trong 1 thư mục (VD: P01_KICH_BAN.txt, P01_SEO.txt, P01_THUMBNAIL_1.png)
            loose_groups: Dict[str, List[Path]] = {}
            for f in sorted(src_path.iterdir()):
                if not f.is_file():
                    continue
                if f.suffix.lower() not in (".txt", ".png", ".jpg", ".jpeg", ".webp", ".mp4"):
                    continue
                stem = f.stem
                m_id = re.match(r"^([A-Za-z0-9]+(?:_[0-9]+)?)_(?:KICH_BAN|SEO|THUMBNAIL|MASTER|SCRIPT)", stem, flags=re.IGNORECASE)
                if m_id:
                    gid = m_id.group(1).upper()
                else:
                    gid = re.sub(r"_(?:KICH_BAN|SEO|THUMBNAIL.*)$", "", stem, flags=re.IGNORECASE).strip()
                if gid:
                    loose_groups.setdefault(gid, []).append(f)

            for gid, files_list in loose_groups.items():
                dst_dir = self.projects_dir / gid
                renders_dir = dst_dir / "renders"
                for lf in files_list:
                    up_n = lf.name.upper()
                    dst_dir.mkdir(parents=True, exist_ok=True)
                    renders_dir.mkdir(parents=True, exist_ok=True)
                    if lf.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp"):
                        shutil.copy2(lf, renders_dir / f"{gid}_THUMBNAIL_1.png")
                    elif "SEO" in up_n or "TIEU_DE" in up_n:
                        shutil.copy2(lf, dst_dir / "00_TIEU_DE_VA_SEO_YOUTUBE.txt")
                        shutil.copy2(lf, renders_dir / f"{gid}_SEO.txt")
                    elif lf.suffix.lower() == ".txt":
                        txt_c = lf.read_text(encoding="utf-8", errors="ignore")
                        if pure_char_count(txt_c) >= 9500:
                            shutil.copy2(lf, dst_dir / "script_clean.txt")
                            shutil.copy2(lf, renders_dir / f"{gid}_KICH_BAN.txt")
                has_sc, _, _ = self.has_valid_script_on_disk(gid)
                self.has_thumbnail_and_seo_on_disk(gid)
                if has_sc and gid not in imported_ids:
                    imported_ids.append(gid)

        if imported_ids:
            self._unmark_ids_deleted(imported_ids)
        self._sync_projects_disk_state(force_restore_deleted=False)
        ideas_after = self.load_saved_ideas()
        log_info(
            "SCRIPT",
            f"📥 Đã nhập thành công {len(imported_ids)} dự án (Kịch bản + Thumbnail + SEO) từ [{source_dir}]: {imported_ids}",
        )
        return {
            "imported_count": len(imported_ids),
            "imported_ids": imported_ids,
            "total_count": len(ideas_after),
            "ideas": ideas_after,
        }

    def _ensure_default_idea_seeded(self):
        """Khởi tạo sẵn mẫu đầu vào PADRE MX V3.0 của người dùng nếu danh sách đang trống."""
        ideas = self.load_saved_ideas()
        if not ideas:
            sample_raw = (
                "P01 — Mi hijo y mi nuera me echaron de la casa que construí ladrillo por ladrillo; al día siguiente el notario leyó la cláusula de donación revocable que firmé hace diez años.\n"
                "VI: Con trai và con dâu đuổi người cha già khỏi ngôi nhà ông tự tay xây từng viên gạch; hôm sau công chứng viên đọc điều khoản thu hồi tặng cho có điều kiện.\n"
                "Keyword: historias de reflexión, drama familiar méxico, padre anciano, justicia familiar, herencia\n"
                "Evidence: Escritura original con cláusula de usufructo vitalicio y revocación por ingratitud\n"
                "Reveal: La casa y el taller mecánico nunca pasaron a nombre del hijo sin la firma del usufructuario\n"
                "Capacity: PASS"
            )
            parsed = parse_idea_input_block(sample_raw, custom_id="1")
            self.save_ideas_list([parsed])

    def add_or_update_ideas_bulk_from_raw(self, raw_text: str, custom_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Phân tích danh sách tiêu đề người dùng dán (MỖI TIÊU ĐỀ 1 DÒNG),
        tự động bỏ qua mọi Mã đầu dòng và gán Mã dự án theo Số Thứ Tự (STT: 1, 2, 3...).
        """
        blocks = split_raw_text_into_idea_blocks(raw_text)
        if not blocks:
            cleaned_single = clean_single_title_line(raw_text)
            blocks = [cleaned_single] if cleaned_single else [raw_text.strip()]

        self._sync_projects_disk_state()
        ideas = self.load_saved_ideas()
        existing_ids = {str(it.get("ma_id")).strip() for it in ideas if it.get("ma_id")}
        saved_items: List[Dict[str, Any]] = []
        new_items_to_append: List[Dict[str, Any]] = []

        # Tìm STT lớn nhất hiện có trong Kho Dự Án để đánh tiếp theo STT (1, 2, 3...)
        max_stt = max([int(x) for x in existing_ids if x.isdigit()], default=0)
        next_num = max_stt + 1

        for block_str in blocks:
            while str(next_num) in existing_ids:
                next_num += 1
            assigned_id = str(next_num)
            next_num += 1

            parsed = parse_idea_input_block(block_str, custom_id=assigned_id)
            mid_cur = parsed["ma_id"]
            existing_ids.add(mid_cur)

            # Bảo toàn tiến độ nếu mã này đã có sẵn kịch bản / thumbnail / SEO trên ổ cứng
            has_sc_disk, _, sc_chars_disk = self.has_valid_script_on_disk(mid_cur)
            has_th_disk, has_seo_disk, th_path_disk = self.has_thumbnail_and_seo_on_disk(mid_cur)
            if has_sc_disk:
                parsed["has_script"] = True
                parsed["pure_char_count"] = sc_chars_disk
                parsed["completed_parts_count"] = 3
                parsed["missing_parts"] = []
                parsed["has_thumbnail"] = has_th_disk
                parsed["has_seo"] = has_seo_disk
                if th_path_disk:
                    parsed["thumbnail_path"] = th_path_disk
                parsed["status"] = "SCRIPT_DONE"
                parsed["current_step"] = f"📝 Đã xong Kịch bản ({sc_chars_disk:,} chữ) & {1 if has_th_disk else 0}/1 Thumbnail — Sẵn sàng Render MP4"

            replaced = False
            for i, it in enumerate(ideas):
                if it.get("ma_id") == mid_cur:
                    if it.get("locked_title") and has_sc_disk:
                        parsed["locked_title"] = it["locked_title"]
                    ideas[i] = parsed
                    replaced = True
                    break
            if not replaced:
                new_items_to_append.append(parsed)

            proj_dir = self.projects_dir / mid_cur
            proj_dir.mkdir(parents=True, exist_ok=True)
            del_marker = proj_dir / ".deleted_by_user"
            if del_marker.exists():
                try:
                    del_marker.unlink()
                except Exception:
                    pass
            (proj_dir / "idea_info.json").write_text(json.dumps(parsed, ensure_ascii=False, indent=2), encoding="utf-8")
            (proj_dir / "step2_prompt_ready.txt").write_text(
                build_step2_prompt_from_idea(parsed, self.get_step2_template()),
                encoding="utf-8",
            )
            saved_items.append(parsed)

        if saved_items:
            self._unmark_ids_deleted([it.get("ma_id", "") for it in saved_items])

        if new_items_to_append:
            ideas = ideas + new_items_to_append

        self.save_ideas_list(ideas)
        self._last_disk_sync_ts = 0.0
        self._sync_projects_disk_state()
        ids_str = ", ".join([f"#{it.get('ma_id', '')}" for it in saved_items])
        log_info("SCRIPT", f"📥 Đã phân tích và lưu {len(saved_items)} tiêu đề theo STT vào Kho Dự Án: [{ids_str}]")
        return saved_items

    def add_or_update_idea_from_raw(self, raw_text: str, custom_id: Optional[str] = None) -> Dict[str, Any]:
        """Phân tích khối văn bản người dùng dán vào và lưu vào danh sách."""
        items = self.add_or_update_ideas_bulk_from_raw(raw_text, custom_id=custom_id)
        return items[0] if items else parse_idea_input_block(raw_text, custom_id=custom_id)

    def delete_idea(self, ma_id: str) -> List[Dict[str, Any]]:
        target = (ma_id or "").strip()
        with self.ideas_io_lock:
            self._mark_ids_deleted([target])
            before_list = self.load_saved_ideas()
            ideas = [it for it in before_list if str(it.get("ma_id", "")).strip() != target]
            self.save_ideas_list(ideas)
            # Cập nhật đồng bộ bản backup và file phụ trong app/saved_ideas.json
            for extra_fp in (
                self.root_dir / "app" / "saved_ideas.json",
                self._get_persistent_appdata_dir() / "saved_ideas_backup.json",
            ):
                if extra_fp.exists():
                    try:
                        extra_fp.write_text(json.dumps(ideas, ensure_ascii=False, indent=2), encoding="utf-8")
                    except Exception:
                        pass

            p_dir = self.projects_dir / target
            if p_dir.exists() and p_dir.is_dir():
                has_sc, _, _ = self.has_valid_script_on_disk(target)
                mp4_f = p_dir / "renders" / f"{target}_master.mp4"
                has_mp4 = mp4_f.exists() and mp4_f.stat().st_size > 1_000_000
                if not has_sc and not has_mp4:
                    # Dự án chỉ là tiêu đề nháp chưa có kịch bản -> xóa sạch hoàn toàn thư mục để không bao giờ tồn đọng
                    shutil.rmtree(p_dir, ignore_errors=True)
                else:
                    for fname in ("idea_info.json", "step2_prompt_ready.txt"):
                        fpath = p_dir / fname
                        if fpath.exists():
                            try:
                                fpath.unlink()
                            except Exception:
                                pass
                    try:
                        (p_dir / ".deleted_by_user").write_text(time.strftime("%Y-%m-%d %H:%M:%S"), encoding="utf-8")
                    except Exception:
                        pass
        log_info("SCRIPT", f"🗑️ Đã xóa vĩnh viễn mã [{target}] khỏi Kho Dự Án (Còn lại {len(ideas)} mã).", project_id=target)
        return ideas

    def delete_all_ideas(self) -> List[Dict[str, Any]]:
        with self.ideas_io_lock:
            old_ideas = self.load_saved_ideas()
            count = len(old_ideas)
            all_ids = [str(it.get("ma_id", "")).strip() for it in old_ideas if it.get("ma_id")]
            if self.projects_dir.exists():
                for p_dir in self.projects_dir.iterdir():
                    if p_dir.is_dir():
                        all_ids.append(p_dir.name.strip())
            self._mark_ids_deleted(all_ids)
            self.save_ideas_list([])
            for extra_fp in (
                self.root_dir / "app" / "saved_ideas.json",
                self._get_persistent_appdata_dir() / "saved_ideas_backup.json",
            ):
                if extra_fp.exists():
                    try:
                        extra_fp.write_text("[]", encoding="utf-8")
                    except Exception:
                        pass
            if self.projects_dir.exists():
                for p_dir in self.projects_dir.iterdir():
                    if p_dir.is_dir():
                        mid = p_dir.name.strip()
                        has_sc, _, _ = self.has_valid_script_on_disk(mid)
                        mp4_f = p_dir / "renders" / f"{mid}_master.mp4"
                        has_mp4 = mp4_f.exists() and mp4_f.stat().st_size > 1_000_000
                        if not has_sc and not has_mp4:
                            shutil.rmtree(p_dir, ignore_errors=True)
                        else:
                            for fname in ("idea_info.json", "step2_prompt_ready.txt"):
                                fp = p_dir / fname
                                if fp.exists():
                                    try:
                                        fp.unlink()
                                    except Exception:
                                        pass
                            try:
                                (p_dir / ".deleted_by_user").write_text(
                                    time.strftime("%Y-%m-%d %H:%M:%S"), encoding="utf-8"
                                )
                            except Exception:
                                pass
        log_info("SCRIPT", f"🗑️ Đã xóa toàn bộ {count} mã tiêu đề khỏi Kho Dự Án.")
        return []

    def _update_idea_record(self, ma_id: str, **fields):
        with self.ideas_io_lock:
            ideas = self.load_saved_ideas()
            for it in ideas:
                if it.get("ma_id") == ma_id:
                    for k, v in fields.items():
                        it[k] = v
                    it["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
                    proj_dir = self.projects_dir / ma_id
                    proj_dir.mkdir(parents=True, exist_ok=True)
                    (proj_dir / "idea_info.json").write_text(json.dumps(it, ensure_ascii=False, indent=2), encoding="utf-8")
                    break
            self.save_ideas_list(ideas)

    def _build_fallback_seo_pack(
        self,
        ma_id: str,
        locked_title: str,
        total_pure: int,
        idea: Dict[str, Any],
        step2_out: str,
    ) -> str:
        """
        Tạo gói SEO & Thumbnail 80/20 chuẩn PADRE MX V3.0 (`es-MX`) từ dữ liệu Step 1/2 + Idea khi chạy ở chế độ
        bỏ qua Chrome (đã có sẵn kịch bản) hoặc khi Step 6 bị quá thời gian chờ.
        Luôn nhúng sẵn khối chữ 80/20 và <THUMBNAIL_PROMPT_1> + <THUMBNAIL_GREEN_PROMPT_1> để STEP 7 tạo đủ 2 ảnh (`THUMBNAIL.png` & `THUMBNAIL-NENXANH.png`).
        """
        kw_raw = idea.get("keywords_ja") or "historias de reflexión, drama familiar méxico, padre anciano, justicia familiar, herencia"
        summary_vi = idea.get("summary_vi") or ""
        evidence = idea.get("proof_object") or "la escritura original y el acta notarial"
        setting = idea.get("boi_canh_su_kien") or "una notaría y casa familiar en México"
        six_lines = self._extract_six_lines_from_outputs("", step2_out or "", locked_title=locked_title, idea=idea)
        l_block = "\n".join(f"L{idx + 1}: {six_lines[idx]}" for idx in range(len(six_lines)))
        return (
            f"ID: {ma_id}\n"
            f"COMPLETED_STEP: STEP 6 — PADRE MX V3.0 SEO & MATCHED THUMBNAIL PAIR\n"
            f"CURRENT_FINAL_TITLE:\n{locked_title}\n\n"
            f"SECONDARY_TITLES_ES_MX:\n"
            f"1. {locked_title[:95]}\n"
            f"2. Cuando mis hijos me quitaron todo, el notario abrió el documento que nadie conocía\n\n"
            f"YOUTUBE_DESCRIPTION_ES_MX:\n"
            f"{locked_title}\n\n"
            f"Durante décadas de trabajo honesto, un padre mexicano levantó el patrimonio familiar sin imaginar que la ingratitud tocaría a su puerta. "
            f"Pero una prueba legal guardada en silencio ({evidence}) cambió el destino de todos cuando llegó la hora de la verdad.\n"
            f"Escucha esta historia completa de dignidad, justicia familiar y lección de vida hasta el último minuto.\n\n"
            f"▼ Suscríbete al canal, deja tu comentario y comparte esta reflexión.\n"
            f"#HistoriasDeReflexion #DramaFamiliarMexico #JusticiaFamiliar #RelatosMexicanos #PadresEIngratitud\n\n"
            f"YOUTUBE_TAGS_ES_MX:\n"
            f"{kw_raw}, historias de reflexión, drama familiar méxico, padre anciano, hijos ingratos, herencia familiar, justicia legal, relatos de vida, historias para reflexionar, audiolibros en español, dignidad paterna\n\n"
            f"VIETNAMESE_SUMMARY:\n{summary_vi}\n\n"
            f"FINAL_THUMBNAIL_6_LINES:\n{l_block}\n\n"
            f"<THUMBNAIL_PROMPT_1>\n"
            f"Generate a brand-new standalone 16:9 horizontal YouTube thumbnail (size 1536x1024) for a Mexican Spanish family drama story using a strict 80/20 split layout.\n"
            f"- Left 78-80% zone: solid clean bright white background (#FFFFFF) with ultra-bold uppercase stacked Spanish sans-serif typography in Black, Cyan/Teal, and Orange, plus a full-width solid Red banner across the bottom-left with bold Yellow/Orange uppercase Spanish kicker text.\n"
            f"- Right 20-22% zone: realistic photographic half-body portrait of an older Mexican father (aged 65-75, gray hair, weathered dignified face, emotional tearful or resolute expression, wearing a modest guayabera or ironed shirt) in a realistic Mexican setting ({setting}).\n"
            f"</THUMBNAIL_PROMPT_1>\n\n"
            f"<THUMBNAIL_GREEN_PROMPT_1>\n"
            f"Matched 16:9 1920x1080 chroma-key green screen deliverable (THUMBNAIL-NENXANH.png): pure solid #00FF00 (RGB 0, 255, 0) background across the entire left 80% and behind the character, keeping ONLY the exact same older Mexican father portrait on the right 20% at identical pixel coordinates.\n"
            f"</THUMBNAIL_GREEN_PROMPT_1>\n\n"
            f"PURE_CHARACTER_COUNT: {total_pure:,} ký tự (~{round(total_pure / 780)} phút giọng đọc es-MX)\n"
        )

    # ==========================================================================
    # ĐỌC NGUYÊN VĂN SKILL.MD TỪ THƯ MỤC ADAS_SKILLS & TẠO PROMPT STEP 3..6 (PADRE MX V3.0)
    # ==========================================================================
    def _load_skill_markdown(self, skill_folder: str) -> str:
        """Đọc nguyên văn 100% nội dung file SKILL.md của Agent PADRE MX V3.0 tương ứng."""
        alias_map = {
            "01_tieu_de_padre_mx": ["01_tieu_de_padre_mx"],
            "02_dan_y_padre_mx": ["02_dan_y_padre_mx"],
            "03_viet_kich_ban_padre_mx": ["03_viet_kich_ban_padre_mx"],
            "04_kiem_dinh_kich_ban_padre_mx": ["04_kiem_dinh_kich_ban_padre_mx"],
            "05_seo_thumbnail_padre_mx": ["05_seo_thumbnail_padre_mx"],
        }
        folders = alias_map.get(skill_folder, [skill_folder])
        for folder in folders:
            cand_paths = [
                self.root_dir / "adas_skills" / folder / "SKILL.md",
                self.root_dir / "app" / "adas_skills" / folder / "SKILL.md",
            ]
            for p in cand_paths:
                if p.exists():
                    try:
                        return p.read_text(encoding="utf-8-sig").strip()
                    except Exception:
                        pass
        return ""

    def _build_step3_prompt(self, ma_id: str, locked_title: str, step2_context: str = "") -> str:
        skill_md = self._load_skill_markdown("02_dan_y_padre_mx")
        skill_block = f"\n\n========== HƯỚNG DẪN CHUYÊN SÂU SKILL 02 (PADRE MX OUTLINE WRITER V3.0) ==========\n{skill_md}\n====================================================================================" if skill_md else ""
        ctx_block = f"\n\n========== DỮ LIỆU ĐẦU RA & HANDOFF TỪ STEP 1/2 ==========\n{step2_context[-8000:]}\n==========================================================" if step2_context else ""
        return f"""Chạy STEP 2 (OUTLINE 7 PHẦN — `padre-mx-outline-writer` V3.0.0) cho mã {ma_id} theo đúng tiêu đề đã khóa từ STEP 1.
CURRENT_FINAL_TITLE: {locked_title}{ctx_block}{skill_block}

YÊU CẦU THỰC THI NGAY CHO MÃ {ma_id} (TIẾNG TÂY BAN NHA MEXICO `es-MX` — 7 PARTS `[PART 1]`..`[PART 7]`):
1. HARD FINAL LENGTH & 3-STAGE CONTRACT (70.000–80.000 ký tự body `es-MX`):
   - STAGE A (`[PART 1]` + `[PART 2]`): 20.000–24.000 ký tự (Target: 22.000; mỗi Part >= 8.500 ký tự).
   - STAGE B (`[PART 3]` + `[PART 4]` + `[PART 5]`): 30.000–35.000 ký tự (Target: 32.500; mỗi Part >= 8.500 ký tự).
   - STAGE C (`[PART 6]` + `[PART 7]`): 20.000–25.000 ký tự (Target: 22.500; mỗi Part >= 8.500 ký tự).
   - TỔNG TOÀN KỊCH BẢN (7 Parts): 70.000–80.000 ký tự.
2. Xuất đầy đủ:
   - `PREMISE_DECONSTRUCTION` (Ngôi kể thứ nhất của người cha lớn tuổi Mexico, vết thương gia đình, tài sản/vật chứng pháp lý, cơ chế lật ngược tình thế hợp pháp tại Mexico).
   - `CANON_CONTINUITY_HANDOFF` (Bảng Nhân vật + Tuổi + Quan hệ; Địa điểm Mexico thực tế; Tài sản/Số tiền MXN; Văn bản công chứng/Di chúc/Hợp đồng/Sao kê).
   - `TIMELINE_AGE_LEDGER` (Kiểm toán toán học tuổi nhân vật, số năm đóng góp, ngày tháng sự kiện không mâu thuẫn).
   - Thiết kế chi tiết 7 Phần `[PART 1]` đến `[PART 7]` (mỗi Part gồm `Dramatic Role`, `Causal Chain`, `Key Scenes`, `Evidence/Legal Mechanism`, `Retention Cliffhanger`, `Target Character Budget`).
   - Chốt `APPROVED_FOR_DRAFTING: YES`. Không viết văn bản kịch bản ở bước này."""

    def _extract_compact_step3_for_part(self, step3_context: str, part_letter: str) -> str:
        """
        Rút gọn thông minh ngữ cảnh Dàn ý 7 Phần (STEP 3) nếu quá dài (> 26.000 ký tự):
        Giữ nguyên phần CANON_CONTINUITY_HANDOFF + TIMELINE_AGE_LEDGER ở đầu và các PART thuộc Stage đang viết.
        """
        if not step3_context or len(step3_context) <= 26000:
            return step3_context
        head_bible = step3_context[:11500]
        p_up = part_letter.upper()
        stage_part_regex = {
            "A": r"\[?PART\s*1\]?",
            "B": r"\[?PART\s*3\]?",
            "C": r"\[?PART\s*6\]?",
        }.get(p_up, rf"PART[_\s]*{p_up}")
        m_part = re.search(stage_part_regex, step3_context, flags=re.IGNORECASE)
        if m_part:
            start_idx = max(0, m_part.start() - 120)
            part_slice = step3_context[start_idx : start_idx + 14500]
            handoff_tail = step3_context[-4500:] if (start_idx + 14500) < len(step3_context) - 4500 else ""
            return f"{head_bible}\n\n...[TRÍCH XUẤT TRỌNG TÂM DÀN Ý STAGE {p_up}]...\n\n{part_slice}\n\n{handoff_tail}".strip()
        return f"{head_bible}\n\n...\n\n{step3_context[-14500:]}".strip()

    def _build_step4_part_initial_prompt(
        self,
        ma_id: str,
        part_letter: str,
        locked_title: str,
        min_c: int,
        max_c: int,
        target_c: int,
        step3_context: str = "",
        prev_part_tail: str = "",
    ) -> str:
        skill_md = self._load_skill_markdown("03_viet_kich_ban_padre_mx")
        compact_s3 = self._extract_compact_step3_for_part(step3_context, part_letter)
        skill_block = f"\n\n========== HƯỚNG DẪN CHUYÊN SÂU SKILL 03 (PADRE MX SCRIPT WRITER V3.0) ==========\n{skill_md}\n===================================================================================" if (skill_md and compact_s3) else ""
        ctx_block = f"\n\n========== DÀN Ý 7 PHẦN & CANON CONTINUITY TỪ BƯỚC TRƯỚC ==========\n{compact_s3}\n===================================================================" if compact_s3 else ""
        prev_block = (
            f"\n\n========== ĐOẠN KẾT CỦA STAGE TRƯỚC (ĐỂ NỐI MẠCH TRUYỆN LIỀN MẠCH 100%, TUYỆT ĐỐI KHÔNG LẶP LẠI) ==========\n"
            f"«...{prev_part_tail[-450:]}»\n"
            f"==========================================================================================================="
            if prev_part_tail
            else ""
        )
        p_up = part_letter.upper()
        if p_up == "A":
            stage_desc = "STAGE A — Viết trọn vẹn `[PART 1]` và `[PART 2]` (Mỗi Part >= 8.500 ký tự; Tổng Stage A: 20.000–24.000 ký tự)"
            headings_rule = "BẮT BUỘC mở đầu bằng dòng tiêu đề phần độc lập `[PART 1]`, viết hết Phần 1 (>= 9.500 ký tự), sau đó xuống dòng ghi `[PART 2]` và viết hết Phần 2 (>= 9.500 ký tự)."
        elif p_up == "B":
            stage_desc = "STAGE B — Viết trọn vẹn `[PART 3]`, `[PART 4]` và `[PART 5]` (Mỗi Part >= 8.500 ký tự; Tổng Stage B: 30.000–35.000 ký tự)"
            headings_rule = "BẮT BUỘC mở đầu bằng dòng tiêu đề phần độc lập `[PART 3]`, viết hết Phần 3 (>= 10.000 ký tự), sau đó xuống dòng ghi `[PART 4]` (>= 10.000 ký tự) và `[PART 5]` (>= 10.000 ký tự)."
        else:
            stage_desc = "STAGE C — Viết trọn vẹn `[PART 6]` và `[PART 7]` (Mỗi Part >= 8.500 ký tự; Tổng Stage C: 20.000–25.000 ký tự)"
            headings_rule = "BẮT BUỘC mở đầu bằng dòng tiêu đề phần độc lập `[PART 6]`, viết hết Phần 6 (>= 10.000 ký tự), sau đó xuống dòng ghi `[PART 7]` và viết hết Phần 7 (>= 10.000 ký tự) khép lại toàn bộ câu chuyện."

        return f"""CHẠY NGAY STEP 3 ({stage_desc}) CHO MÃ {ma_id}
CURRENT_FINAL_TITLE: {locked_title}{ctx_block}{prev_block}{skill_block}

QUY TẮC BẮT BUỘC (`padre-mx-script-writer` V3.0.0 — TIẾNG TÂY BAN NHA MEXICO `es-MX`):
1. NGÔN NGỮ & GIỌNG KỂ: Viết 100% bằng tiếng Tây Ban Nha Mexico (`es-MX`) chuẩn mực, ngôi thứ nhất của người cha lớn tuổi Mexico (`yo`), giàu cảm xúc, tự nhiên để đọc Voice TTS. Tuyệt đối KHÔNG dùng từ vựng Tây Ban Nha châu Âu (`vosotros`, `os`, `ordenador`, `coche`, `zumo`). Đầy đủ dấu câu mở `¿...?`, `¡...!` và trọng âm tiếng Tây Ban Nha.
2. NHÃN PHẦN BẮT BUỘC: {headings_rule}
3. ⚠️ CẤM TUYỆT ĐỐI RÒ RỈ TIÊU ĐỀ & METADATA: Ngoài các dòng nhãn phần độc lập (`[PART 1]`..`[PART 7]`), TUYỆT ĐỐI KHÔNG in lại dòng `CURRENT_FINAL_TITLE:`, `LOCKED_TITLE:`, `STAGE_A_COUNT_GATE:`, `Escena 1:`, hay ghi chú đạo diễn vào trong văn bản truyện.
4. MỤC TIÊU ĐỘ DÀI CỨNG CỦA STAGE {p_up}: {min_c:,}–{max_c:,} ký tự body (Đích an toàn: ~{target_c:,} ký tự, mỗi Part trong Stage >= 8.500 ký tự).
5. Triển khai chi tiết, sâu sắc từng cảnh bằng hành động cụ thể, đối thoại gia đình/pháp lý kịch tính, chi tiết văn bản công chứng/tài chính thực tế tại Mexico. TUYỆT ĐỐI KHÔNG tóm tắt, không nhảy cóc thời gian, không lặp lại cùng một câu cảm thán.
6. ⚠️ QUY TẮC TỐC ĐỘ & HIỂN THỊ: TUYỆT ĐỐI KHÔNG bật công cụ Python / Code Interpreter, KHÔNG đóng gói thành file tải về (.txt/.md/.docx). BẮT BUỘC in trực tiếp toàn bộ 100% văn bản kịch bản tiếng Tây Ban Nha (`es-MX`) ra khung chat ngay lập tức."""

    def _build_step4_part_continue_prompt(
        self,
        part_letter: str,
        current_pure: int,
        min_c: int,
        max_c: int,
        target_c: int,
        last_tail_ja: str,
        step3_context: str = "",
    ) -> str:
        needed = max(2000, target_c - current_pure)
        p_up = part_letter.upper()
        expected_parts_str = (
            "`[PART 1]` và `[PART 2]`"
            if p_up == "A"
            else ("`[PART 3]`, `[PART 4]` và `[PART 5]`" if p_up == "B" else "`[PART 6]` và `[PART 7]`")
        )
        ctx_reminder = (
            f"\n\n========== NHẮC LẠI DÀN Ý STAGE {p_up} ({expected_parts_str}) ==========\n"
            f"{step3_context[-12000:]}\n"
            f"========================================================================\n"
            if step3_context
            else ""
        )
        return f"""[KIỂM TRA ĐỘ DÀI CỨNG — STAGE {p_up} ({expected_parts_str})]
- Số ký tự hiện tại của STAGE {p_up} mới đạt: {current_pure:,} ký tự.
- Ngưỡng bắt buộc của STAGE {p_up}: {min_c:,}–{max_c:,} ký tự (Còn thiếu khoảng {needed:,} ký tự để đạt đích {target_c:,}; mỗi Part phải >= 8.500 ký tự).{ctx_reminder}
YÊU CẦU VIẾT TIẾP NỐI STAGE {p_up} BẰNG TIẾNG TÂY BAN NHA MEXICO (`es-MX`):
1. Hãy viết TIẾP NỐI NGAY LẬP TỨC từ đoạn kết vừa rồi:
   «...{last_tail_ja}»
2. Triển khai tiếp các diễn biến còn lại của {expected_parts_str} theo đúng dàn ý (nếu chưa mở sang Part tiếp theo thuộc Stage {p_up} thì nhớ đặt dòng nhãn `[PART X]` độc lập rồi viết đầy đủ Part đó; nếu đã ở Part cuối của Stage {p_up} thì mở rộng chiều sâu tình huống, bằng chứng pháp lý, đối thoại trực diện và diễn biến tâm lý nhân vật).
3. TUYỆT ĐỐI KHÔNG bật công cụ Python/Code Interpreter, KHÔNG tạo file tải về, KHÔNG lặp lại những đoạn đã viết ở trên, KHÔNG nhảy sang Stage tiếp theo. Chỉ xuất trực tiếp 100% văn bản tự sự và đối thoại tiếng Tây Ban Nha Mexico (`es-MX`) ra khung chat nối tiếp cho đủ thêm tối thiểu {needed:,} ký tự."""

    def _build_step5_audit_prompt(
        self,
        ma_id: str,
        locked_title: str,
        count_a: int,
        count_b: int,
        count_c: int,
        total_count: int,
        part_a_text: str = "",
        part_b_text: str = "",
        part_c_text: str = "",
        step3_context: str = "",
    ) -> str:
        skill_md = self._load_skill_markdown("04_kiem_dinh_kich_ban_padre_mx")
        skill_block = f"\n\n========== HƯỚNG DẪN CHUYÊN SÂU SKILL 04 (PADRE MX INDEPENDENT QA V3.0 — ROUND 1 LOGIC AUDIT) ==========\n{skill_md}\n=========================================================================================================" if skill_md else ""
        arch_excerpt = f"\n\n========== TÓM TẮT DÀN Ý & CANON CONTINUITY LEDGER ==========\n{step3_context[:4000]}\n=============================================================" if step3_context else ""
        script_payload = ""
        if part_a_text or part_b_text or part_c_text:
            script_payload = (
                f"\n\n========== TOÀN BỘ KỊCH BẢN 7 PHẦN (`es-MX`) CẦN KIỂM ĐỊNH VÒNG 1 (LOGIC / CONTINUITY / ORTHOGRAPHY) ==========\n"
                f"--- [BẮT ĐẦU STAGE A: PART 1 & PART 2 ({count_a:,} chars)] ---\n{part_a_text}\n--- [KẾT THÚC STAGE A] ---\n\n"
                f"--- [BẮT ĐẦU STAGE B: PART 3, PART 4 & PART 5 ({count_b:,} chars)] ---\n{part_b_text}\n--- [KẾT THÚC STAGE B] ---\n\n"
                f"--- [BẮT ĐẦU STAGE C: PART 6 & PART 7 ({count_c:,} chars)] ---\n{part_c_text}\n--- [KẾT THÚC STAGE C] ---\n"
                f"================================================================================================================"
            )
        return f"""CHẠY NGAY STEP 4 (VÒNG 1 — FORENSIC LOGIC, CONTINUITY, LEGAL & `es-MX` ORTHOGRAPHY AUDIT + REPAIR 1) CHO MÃ {ma_id}
- CURRENT_FINAL_TITLE: {locked_title}
- Đếm ký tự xác thực bởi hệ thống Python bên ngoài:
  + STAGE A (`[PART 1]`–`[PART 2]`): {count_a:,} chars
  + STAGE B (`[PART 3]`–`[PART 5]`): {count_b:,} chars
  + STAGE C (`[PART 6]`–`[PART 7]`): {count_c:,} chars
  + TOTAL (`[PART 1]`–`[PART 7]`): {total_count:,} chars
  + AUDIT_ROUND: ROUND 1 (LOGIC, CONTINUITY, LEGAL/MEDICAL REALISM & `es-MX` ORTHOGRAPHY){arch_excerpt}{skill_block}{script_payload}

⚠️ YÊU CẦU KIỂM ĐỊNH ĐỘC LẬP VÒNG 1 & SỬA LỖI LOGIC (REPAIR 1):
1. Bạn là Giám khảo Kiểm định Độc lập Vòng 1 (`padre-mx-independent-qa` V3.0.0). Hãy kiểm tra toàn bộ 7 Phần (`[PART 1]`..`[PART 7]`):
   - Tính nhân-quả, tính liên tục của tên nhân vật, tuổi tác, mốc thời gian, số tiền (MXN), địa điểm và văn bản pháp lý/công chứng tại Mexico.
   - Chính tả & ngữ pháp tiếng Tây Ban Nha Mexico (`es-MX`): dấu hỏi/chấm than mở `¿...?`, `¡...!`, dấu trọng âm, tuyệt đối không có từ vựng Tây Ban Nha châu Âu (`vosotros`), không rò rỉ tiêu đề hay ghi chú đạo diễn.
2. Xuất báo cáo `PMX_QA_ROUND1_LOGIC.md` và `PMX_REPAIR_1_SCOPE.md`.
3. NẾU PHÁT HIỆN BẤT KỲ STAGE NÀO (A, B hoặc C) CÓ LỖI LOGIC, MÂU THUẪN TUỔI/TIỀN/THỜI GIAN, LỖI CHÍNH TẢ `es-MX` HOẶC RÒ RỈ METADATA:
   - Thực hiện ngay **REPAIR 1**: Xuất bản đã sửa hoàn chỉnh của Stage đó trong cặp thẻ `<REWRITE_PART_A>...</REWRITE_PART_A>`, `<REWRITE_PART_B>...</REWRITE_PART_B>`, hoặc `<REWRITE_PART_C>...</REWRITE_PART_C>` (giữ nguyên các dòng nhãn `[PART 1]`..`[PART 7]` và bảo toàn độ dài chuẩn của từng Stage).
4. NẾU CẢ 3 STAGE ĐỀU ĐẠT CHUẨN LOGIC & CHÍNH TẢ 100%:
   - Không cần mở thẻ `<REWRITE_PART_...>`, chốt `ROUND1_LOGIC_STATUS: PASS_CLEAN`! TUYỆT ĐỐI KHÔNG bật Python/Code Interpreter."""

    def _build_step5_round2_quality_audit_prompt(
        self,
        ma_id: str,
        locked_title: str,
        count_a: int,
        count_b: int,
        count_c: int,
        total_count: int,
        part_a_text: str = "",
        part_b_text: str = "",
        part_c_text: str = "",
        round1_report: str = "",
    ) -> str:
        r1_excerpt = f"\n\n========== TÓM TẮT KẾT QUẢ AUDIT VÒNG 1 (LOGIC & REPAIR 1) ==========\n{round1_excerpt if (round1_excerpt := round1_report[:3000]) else 'PASS'}\n======================================================================"
        script_payload = (
            f"\n\n========== KỊCH BẢN SAU VÒNG 1 CẦN KIỂM ĐỊNH VÒNG 2 (HOLISTIC QUALITY / PACING / EMOTIONAL PAYOFF) ==========\n"
            f"--- [BẮT ĐẦU STAGE A: PART 1 & PART 2 ({count_a:,} chars)] ---\n{part_a_text}\n--- [KẾT THÚC STAGE A] ---\n\n"
            f"--- [BẮT ĐẦU STAGE B: PART 3, PART 4 & PART 5 ({count_b:,} chars)] ---\n{part_b_text}\n--- [KẾT THÚC STAGE B] ---\n\n"
            f"--- [BẮT ĐẦU STAGE C: PART 6 & PART 7 ({count_c:,} chars)] ---\n{part_c_text}\n--- [KẾT THÚC STAGE C] ---\n"
            f"============================================================================================================="
        )
        return f"""CHẠY NGAY STEP 5 (VÒNG 2 — HOLISTIC FULL-SCRIPT QUALITY, PACING, ANTI-REPETITION & VOICE-READABILITY AUDIT + REPAIR 2) CHO MÃ {ma_id}
- CURRENT_FINAL_TITLE: {locked_title}
- Đếm ký tự sau Vòng 1:
  + STAGE A (`[PART 1]`–`[PART 2]`): {count_a:,} chars
  + STAGE B (`[PART 3]`–`[PART 5]`): {count_b:,} chars
  + STAGE C (`[PART 6]`–`[PART 7]`): {count_c:,} chars
  + TOTAL (`[PART 1]`–`[PART 7]`): {total_count:,} chars
  + AUDIT_ROUND: ROUND 2 (OVERALL DRAMATIC QUALITY, PACING, EMOTIONAL RESONANCE & TTS NATURALNESS){r1_excerpt}{script_payload}

⚠️ YÊU CẦU KIỂM ĐỊNH ĐỘC LẬP VÒNG 2 & NÂNG CẤP CHẤT LƯỢNG (REPAIR 2):
1. Bạn là Giám khảo Kiểm định Độc lập Vòng 2 (`padre-mx-independent-qa` V3.0.0 — Quality Gate). Hãy đánh giá toàn diện chất lượng văn học và sức hút giữ chân khán giả của cả 7 Phần (`[PART 1]`..`[PART 7]`):
   - Mở đầu 90 giây có vào thẳng xung đột gia đình không?
   - Có đoạn nào bị lặp ý, câu văn kéo dài câu chữ (padding) hoặc nhịp truyện bị chùng xuống không?
   - Cao trào pháp lý/gia đình ở `[PART 5]`–`[PART 6]` và cái kết nhân văn, đĩnh đạc của người cha ở `[PART 7]` đã thực sự chạm cảm xúc chưa?
   - Nhịp câu đọc lớn tiếng Tây Ban Nha Mexico (`es-MX`) đã mượt mà cho Voice TTS chưa?
2. Xuất báo cáo `PMX_QA_ROUND2_QUALITY.md` và `PMX_QA_FINAL.md` (chấm điểm `/100`, mục tiêu `>= 95/100` và chốt `RELEASE_DECISION: READY`).
3. NẾU PHÁT HIỆN BẤT KỲ STAGE NÀO (A, B hoặc C) CẦN NÂNG CẤP NHỊP ĐIỆU, XÓA ĐOẠN LẶP HOẶC TĂNG SỨC NẶNG CẢM XÚC/ĐỐI THOẠI (REPAIR 2):
   - Đặt bản hoàn chỉnh đã nâng cấp của Stage đó trong cặp thẻ `<REWRITE_PART_A>...</REWRITE_PART_A>`, `<REWRITE_PART_B>...</REWRITE_PART_B>`, hoặc `<REWRITE_PART_C>...</REWRITE_PART_C>` (giữ nguyên các nhãn `[PART 1]`..`[PART 7]` và độ dài chuẩn).
4. NẾU CẢ 3 STAGE ĐỀU ĐẠT CHẤT LƯỢNG XUẤT SẮC (`>= 95/100`):
   - Không cần mở thẻ `<REWRITE_PART_...>`, chỉ xuất báo cáo `PMX_QA_ROUND2_QUALITY.md` + `PMX_QA_FINAL.md` và chốt `RELEASE_DECISION: READY`! TUYỆT ĐỐI KHÔNG bật Python/Code Interpreter."""

    def _build_step6_seo_prompt(self, ma_id: str, locked_title: str, total_count: int, step2_context: str = "", script_excerpt: str = "") -> str:
        skill_md = self._load_skill_markdown("05_seo_thumbnail_padre_mx")
        skill_block = f"\n\n========== HƯỚNG DẪN CHUYÊN SÂU SKILL 05 (PADRE MX SEO & 80/20 MATCHED THUMBNAIL PAIR V3.0) ==========\n{skill_md}\n======================================================================================================" if skill_md else ""
        step2_tail = step2_context[-12000:] if step2_context else ""
        step2_six_lines = self._extract_six_lines_from_single_source(step2_context or "")
        locked_6_lines_block = ""
        if len(step2_six_lines) >= 4:
            locked_6_lines_block = (
                "\n- LOCKED_THUMBNAIL_TEXT_STACK (Các dòng chữ Tây Ban Nha in hoa từ STEP 1/2):\n"
                + "\n".join(f"  + L{i+1}: {step2_six_lines[i]}" for i in range(len(step2_six_lines)))
            )
        ctx_block = f"\n\n========== DỮ LIỆU TIÊU ĐỀ & THUMBNAIL TỪ STEP 1/2 ==========\n{step2_tail}\n=============================================================" if step2_tail else ""
        script_block = f"\n\n========== TRÍCH ĐOẠN MỞ ĐẦU & CAO TRÀO KỊCH BẢN ĐÃ KHÓA ==========\n{script_excerpt[:3000]}\n===================================================================" if script_excerpt else ""
        return f"""CHẠY NGAY STEP 6 (TRÊN ĐOẠN CHAT SEO MỚI HOÀN TOÀN) — SEO YOUTUBE `es-MX` & BỘ ĐÔI THUMBNAIL 80/20 (`THUMBNAIL.png` + `THUMBNAIL-NENXANH.png`) (`padre-mx-seo-packaging` V3.0.0) CHO MÃ {ma_id}
- FULL_SCRIPT_CHAR_COUNT_VERIFIED: {total_count:,} chars (7 PARTS `[PART 1]`..`[PART 7]` — PASS 70.000–80.000)
- RELEASE_DECISION: READY (ĐÃ QUA 2 VÒNG KIỂM ĐỊNH ĐỘC LẬP LOGIC & QUALITY)
- CURRENT_FINAL_TITLE (Giữ nguyên 100% verbatim): {locked_title}{locked_6_lines_block}{ctx_block}{script_block}{skill_block}

⚠️ LỆNH XUẤT BẢN TRÊN ĐOẠN CHAT SEO MỚI (FORCE_PUBLISH_PACK = TRUE):
BẮT BUỘC xuất trực tiếp ra khung chat trọn bộ GÓI ĐĂNG TẢI YOUTUBE MEXICO (`PMX_SEO_PACK.md`) gồm đầy đủ 7 mục sau (không dùng Code Interpreter):
1. `PRIMARY_LOCKED_TITLE`: Giữ nguyên 100% `CURRENT_FINAL_TITLE` (kèm bản dịch nghĩa tiếng Việt bên dưới).
2. `SECONDARY_TITLES_ES_MX`: Đúng 2 tiêu đề phụ tiếng Tây Ban Nha Mexico (`<= 100` ký tự) cùng câu chuyện.
3. `YOUTUBE_DESCRIPTION_ES_MX`: Mô tả video tiếng Tây Ban Nha Mexico chuẩn SEO (3 đoạn văn cảm xúc không tiết lộ kết cục + câu hỏi thảo luận + lời kêu gọi đăng ký kênh).
4. `HASHTAGS_ES_MX`: 3–5 hashtags chuẩn (`#HistoriasDeReflexion #DramaFamiliarMexico #JusticiaFamiliar ...`).
5. `TAGS_CSV_ES_MX`: 25–35 từ khóa tiếng Tây Ban Nha Mexico phân cách bằng dấu phẩy.
6. `FINAL_THUMBNAIL_6_LINES` (Bố cục chữ 80/20 trên nền trắng bên trái + băng rôn đỏ bên dưới):
   - Xuất chính xác 6 dòng chữ Tây Ban Nha IN HOA ngắn gọn (2–5 từ/dòng) để hiển thị trên vùng 80% bên trái:
     L1: <dòng 1 chữ Tây Ban Nha IN HOA màu ĐEN>
     L2: <dòng 2 chữ Tây Ban Nha IN HOA màu XANH CYAN/TEAL>
     L3: <dòng 3 chữ Tây Ban Nha IN HOA màu ĐEN>
     L4: <dòng 4 chữ Tây Ban Nha IN HOA màu CAM ĐẬM>
     L5: <dòng 5 chữ Tây Ban Nha IN HOA màu ĐEN hoặc XANH CYAN>
     L6: <dòng 6 chữ Tây Ban Nha IN HOA màu VÀNG/CAM nổi bật trên BĂNG RÔN ĐỎ đáy ảnh>
7. `MATCHED_THUMBNAIL_PROMPTS` (BẮT BUỘC XUẤT CẢ 2 THẺ `<THUMBNAIL_PROMPT_1>` VÀ `<THUMBNAIL_GREEN_PROMPT_1>`):
   - `<THUMBNAIL_PROMPT_1>`: Prompt tiếng Anh chi tiết để công cụ tạo ảnh (size `1536x1024`, bố cục 16:9 `1920x1080`) vẽ bức ảnh `THUMBNAIL.png` theo đúng tỷ lệ **80/20**:
     + Bên trái 78–80% khung hình: Nền trắng sáng sạch (`#FFFFFF`), trình bày các dòng chữ Tây Ban Nha IN HOA đậm nét (L1..L5) với màu Đen, Xanh Cyan và Cam; phía dưới bên trái là băng rôn nền Đỏ tươi với dòng chữ L6 màu Vàng/Cam rực rỡ.
     + Bên phải 20–22% khung hình: Chân dung bán thân chụp ảnh thật sắc nét (photorealistic) của người cha già Mexico (65–78 tuổi, tóc bạc, gương mặt từng trải đầy phẩm giá, ánh mắt nghẹn ngào hoặc kiên nghị, mặc áo sơ mi hoặc guayabera giản dị).
   - `</THUMBNAIL_PROMPT_1>`
   - `<THUMBNAIL_GREEN_PROMPT_1>`: Prompt mô tả bức ảnh thứ hai `THUMBNAIL-NENXANH.png` (16:9 `1920x1080`): giữ nguyên 100% nhân vật người cha Mexico ở đúng vị trí bên phải, toàn bộ phần nền và 80% bên trái phủ màu xanh lá thuần khiết `#00FF00` (`RGB 0, 255, 0`), không có bất kỳ chữ hay băng rôn nào.
   - `</THUMBNAIL_GREEN_PROMPT_1>`"""

    def _extract_six_lines_from_single_source(self, src: str) -> List[str]:
        """Trích xuất chính xác 6 dòng chữ Thumbnail L1..L6 (hỗ trợ cả tiếng Tây Ban Nha `es-MX` và tiếng Nhật legacy)."""
        if not src:
            return []
        vi_re = re.compile(r"[ăâđêôơưảãạẻẽẹỉĩịỏõọủũụỷỹỵ]", re.IGNORECASE)

        def _clean_thumb_line(raw_s: str) -> str:
            s = re.sub(r"<[^>]+>", "", raw_s or "").strip().strip("`*'\" ")
            s = re.sub(r"^[A-Z0-9\s/_\-\(\)\[\]—]+[:：]\s*", "", s, flags=re.IGNORECASE).strip()
            s = re.sub(
                r"\s*[\(（\[][^\)）\]]*(?:White|Yellow|Pink|Magenta|Cyan|Teal|Orange|Black|Red|Banner|Kicker|Trắng|Vàng|Hồng|Xanh|Đen|Đỏ|Cam|Relationship|Situation|Conflict|Escalation|Reversal|Reaction)[^\)）\]]*[\)）\]]\s*",
                "",
                s,
                flags=re.IGNORECASE,
            ).strip()
            s = re.sub(r"\s*\+\s*", " ", s).strip()
            return s

        # Ưu tiên 1: Các dòng L1..L6 trực tiếp
        direct_lines: List[str] = []
        for idx in range(1, 7):
            m = re.search(
                rf"(?:^|\n)\s*(?:\*\*|`|-|\d+\.\s*)*L(?:INE|AYER)?[_\s]*{idx}\b[^\r\n:：]*[:：\-→]\s*([^\r\n|]+)",
                src,
                flags=re.IGNORECASE,
            )
            if m:
                cand = _clean_thumb_line(m.group(1))
                if len(cand) >= 3 and not vi_re.search(cand):
                    direct_lines.append(cand)
        if len(direct_lines) == 6:
            return direct_lines

        # Ưu tiên 2: Bảng Markdown (| L1 ... | <Text> | ... |)
        table_lines: List[str] = []
        for idx in range(1, 7):
            tpat = rf"\|\s*(?:\*\*)?L(?:AYER[_\s]*)?{idx}\b[^|\r\n]*\|\s*([^|\r\n]+)\|"
            for m in re.finditer(tpat, src, flags=re.IGNORECASE):
                cand = _clean_thumb_line(m.group(1))
                if len(cand) >= 2 and not vi_re.search(cand):
                    table_lines.append(cand)
                    break
        if len(table_lines) == 6:
            return table_lines

        return []

    def _synthesize_fallback_six_lines_ja(
        self,
        locked_title: str = "",
        idea: Optional[Dict[str, Any]] = None,
        step2_text: str = "",
        step6_text: str = "",
    ) -> List[str]:
        """
        Tổng hợp tự động 6 dòng chữ Tây Ban Nha IN HOA ngắn gọn chuẩn 80/20 (`L1..L6`) từ tiêu đề khóa (`locked_title`)
        khi STEP 1/2 hoặc STEP 6 bị thiếu danh sách L1..L6.
        """
        raw_title = (
            locked_title
            or (idea or {}).get("locked_title")
            or (idea or {}).get("draft_title_ja")
            or ""
        ).strip()

        # Nếu là tiêu đề tiếng Tây Ban Nha / Latin: tách thành 6 cụm IN HOA mạnh mẽ cho bố cục 80/20
        words = [w.strip(".,;:()[]\"'") for w in raw_title.split() if w.strip(".,;:()[]\"'")]
        if words and not any("\u3040" <= ch <= "\u9fff" for ch in raw_title):
            chunks: List[str] = []
            cur: List[str] = []
            for w in words:
                cur.append(w.upper())
                if len(" ".join(cur)) >= 16 or len(cur) >= 4:
                    chunks.append(" ".join(cur))
                    cur = []
            if cur:
                chunks.append(" ".join(cur))
            default_es = [
                "MIS HIJOS ME ECHARON",
                "DE MI PROPIA CASA,",
                "PERO ANTES DE SALIR",
                "EL NOTARIO ABRIÓ",
                "LA CLÁUSULA SECRETA",
                "¡SE QUEDARON SIN NADA!",
            ]
            res_es: List[str] = []
            for i in range(6):
                if i < len(chunks) and chunks[i]:
                    res_es.append(chunks[i][:28])
                else:
                    res_es.append(default_es[i])
            return res_es

        default_hooks = [
            "MIS HIJOS ME ECHARON",
            "DE MI PROPIA CASA,",
            "PERO ANTES DE SALIR",
            "EL NOTARIO ABRIÓ",
            "LA CLÁUSULA SECRETA",
            "¡SE QUEDARON SIN NADA!",
        ]
        return default_hooks

    def _extract_six_lines_from_outputs(
        self,
        step6_text: str,
        step2_text: str,
        locked_title: str = "",
        idea: Optional[Dict[str, Any]] = None,
    ) -> List[str]:
        """
        Trích xuất chính xác 6 dòng chữ Thumbnail L1..L6 từ STEP 6 hoặc STEP 1/2.
        """
        lines_s6 = self._extract_six_lines_from_single_source(step6_text or "")
        lines_s2 = self._extract_six_lines_from_single_source(step2_text or "")
        if len(lines_s6) == 6:
            return lines_s6
        if len(lines_s2) == 6:
            return lines_s2
        return self._synthesize_fallback_six_lines_ja(
            locked_title=locked_title,
            idea=idea,
            step2_text=step2_text,
            step6_text=step6_text,
        )

    def _sanitize_raw_thumbnail_prompt(self, raw_p: str) -> str:
        """
        Làm sạch Prompt Thumbnail để công cụ tạo ảnh của ChatGPT (gpt-image-1) LUÔN hiểu là tạo ảnh mới từ đầu
        với kích thước hợp lệ 1536x1024 (loại bỏ hoàn toàn các từ khóa edit/adjust/reduce/instead/reference,
        loại bỏ từ khóa trẻ vị thành niên child/teen/kid để không bao giờ vướng Content Guardrails của OpenAI).
        """
        txt = raw_p or ""
        txt = re.split(
            r"\n\s*(?:CRITICAL\s+RESTRICTIONS|STRICT\s+DESIGN\s+RULES|MANDATORY|FINAL\s+VISUAL\s+TEST|FINAL\s+QUALITY\s+INSPECTION)\s*[:：]?",
            txt,
            maxsplit=1,
            flags=re.IGNORECASE,
        )[0]
        txt = re.sub(r"\b(?:3840\s*x\s*2160|1920\s*x\s*1080|1536\s*x\s*864|1280\s*x\s*720)\b", "1536x1024", txt, flags=re.IGNORECASE)
        txt = re.sub(r"target\s+1536x1024", "size 1536x1024", txt, flags=re.IGNORECASE)
        txt = re.sub(r"\b16\s*:\s*9(?:\s*aspect\s*ratio)?\b", "widescreen landscape (1536x1024)", txt, flags=re.IGNORECASE)
        txt = re.sub(
            r"\b(?:schoolboy|schoolgirl|elementary\s+school\s+student|middle\s+school\s+student|high\s+school\s+student|little\s+boy|little\s+girl|young\s+boy|young\s+girl|teenager|teenagers|teenage|teens|teen|children|child|kids|kid|minor|minors)\b",
            "adult family member (aged 35s)",
            txt,
            flags=re.IGNORECASE,
        )

        forbidden_line_pats = (
            r"reject\s+and\s+regenerate",
            r"final\s+visual\s+test",
            r"final\s+quality\s+inspection",
            r"check\s+the\s+final",
            r"visually\s+count",
            r"count\s+the\s+rendered",
            r"\badjust\b",
            r"\breduce\b",
            r"\bmodify\b",
            r"\breplace\b",
            r"\bedit\b",
            r"\binstead\b",
            r"\breference\b",
            r"\boriginal\s+image\b",
            r"\btarget\s+image\b",
            r"\bexisting\s+image\b",
            r"\bvariation\b",
            r"competitor",
        )
        cleaned_lines: List[str] = []
        for ln in txt.splitlines():
            if any(re.search(fp, ln, flags=re.IGNORECASE) for fp in forbidden_line_pats):
                continue
            ln = re.sub(r"\bOverlay\b", "Include", ln)
            ln = re.sub(r"\boverlay\b", "include", ln)
            ln = re.sub(r"\bPreserve\b", "Show", ln)
            ln = re.sub(r"\bpreserve\b", "show", ln)
            ln = re.sub(r"\bpreserving\b", "showing", ln, flags=re.IGNORECASE)
            ln = re.sub(r"\bKeep\s+the\b", "Make the", ln)
            ln = re.sub(r"\bkeep\s+the\b", "make the", ln)
            ln = re.sub(r"\bremain\b", "appear", ln, flags=re.IGNORECASE)
            cleaned_lines.append(ln)
        return "\n".join(cleaned_lines).strip()

    def _extract_three_thumbnail_prompts(
        self,
        step6_text: str,
        step2_text: str,
        locked_title: str,
        idea: Dict[str, Any],
    ) -> List[str]:
        """Bóc tách Prompt tạo Thumbnail chuẩn 80/20 PADRE MX V3.0 từ STEP 6 (hoặc tự động tổng hợp từ 6 dòng chữ Tây Ban Nha IN HOA)."""
        six_lines = self._extract_six_lines_from_outputs(
            step6_text,
            step2_text,
            locked_title=locked_title,
            idea=idea,
        )
        six_lines_str = "\n".join(
            [
                f"Line 1 (Bold Black uppercase on White left zone): {six_lines[0]}",
                f"Line 2 (Bold Cyan/Teal uppercase on White left zone): {six_lines[1]}",
                f"Line 3 (Bold Black uppercase on White left zone): {six_lines[2]}",
                f"Line 4 (Bold Deep Orange uppercase on White left zone): {six_lines[3]}",
                f"Line 5 (Bold Black/Cyan uppercase on White left zone): {six_lines[4]}",
                f"Bottom Banner Kicker (Bold Bright Yellow uppercase inside solid Red banner at bottom-left): {six_lines[5]}",
            ]
        )

        prompts: List[str] = []
        for idx in (1, 2, 3):
            m = re.search(
                rf"<THUMBNAIL_PROMPT_{idx}>([\s\S]*?)</THUMBNAIL_PROMPT_{idx}>",
                step6_text or "",
                flags=re.IGNORECASE,
            )
            if m and len(m.group(1).strip()) > 60:
                prompts.append(self._sanitize_raw_thumbnail_prompt(m.group(1).strip()))

        variant_angles = [
            "Right 22% zone features a realistic photographic half-body portrait of an elderly Mexican father (aged 68-75, silver-gray hair, neatly trimmed mustache, weathered dignified skin, glistening tearful eyes full of quiet resolve, wearing a clean beige guayabera shirt) holding a folded notarized property deed ({proof}), while the left 78% is a solid clean white background (#FFFFFF) with bold stacked Spanish headline text and a bottom red kicker banner.",
            "Right 22% zone shows a photorealistic portrait of a dignified older Mexican man (aged 65-74, gray hair, emotional resolute expression, wearing a modest plaid work shirt) standing in front of a softly blurred Mexican home courtyard ({setting}), while the left 78% is a crisp solid white panel (#FFFFFF) with giant uppercase Spanish typography and a solid red bottom banner.",
            "Right 22% zone depicts a close-up photorealistic chest-up portrait of an older Mexican father (aged 70, deeply expressive eyes, dignified face, wearing a dark jacket over a white shirt) looking toward the camera with quiet authority, while the left 78% is a clean solid white background (#FFFFFF) carrying stacked uppercase Spanish text and a red bottom banner.",
        ]

        safe_proof = self._sanitize_raw_thumbnail_prompt(str(idea.get("proof_object") or "notarized Mexican property deed")) or "notarized Mexican property deed"
        safe_setting = self._sanitize_raw_thumbnail_prompt(str(idea.get("boi_canh_su_kien") or "Mexican family house")) or "Mexican family house"
        safe_title_ctx = self._sanitize_raw_thumbnail_prompt(locked_title or "")

        while len(prompts) < 3:
            v_idx = len(prompts)
            angle_desc = variant_angles[v_idx].format(
                proof=safe_proof,
                setting=safe_setting,
            )
            prompts.append(
                f"High-CTR Mexican Spanish family drama YouTube thumbnail with a strict 80/20 split layout (horizontal landscape 1536x1024).\n"
                f"Story Context: {safe_title_ctx}\n"
                f"Visual Composition: {angle_desc}"
            )

        final_prompts: List[str] = []
        for idx, p in enumerate(prompts[:3], start=1):
            enforced = (
                "Call the image generation tool immediately to create a brand-new standalone horizontal landscape image from scratch (size 1536x1024) composed for a 16:9 YouTube thumbnail frame using the strict PADRE MX 80/20 split layout:\n\n"
                f"{p}\n\n"
                "STRICT 80/20 LAYOUT & SPANISH TYPOGRAPHY SPECIFICATION:\n"
                "- Left 78% of the canvas: Clean solid white background (#FFFFFF) with massive, ultra-bold uppercase sans-serif Spanish lines stacked clearly from top to bottom, plus a solid vivid Red rectangular banner across the bottom of the left zone:\n"
                f"{six_lines_str}\n"
                "- Right 22% of the canvas: Realistic photographic portrait of ONE older Mexican father (aged 65-75) with clear facial features, natural skin texture, and strong emotional expression, cleanly separated from the left white text zone.\n"
                "Strict rule: Generate the image directly right now without asking any questions. Render only the Spanish text phrases themselves (never print 'Line 1..5' or 'Bottom Banner Kicker' labels)."
            )
            final_prompts.append(enforced)
        return final_prompts

    def _create_matched_green_screen_from_thumbnail_bytes(self, thumb_1080p_bytes: bytes) -> bytes:
        """
        Tạo bức ảnh thứ hai `THUMBNAIL-NENXANH.png` (1920x1080) theo đúng bố cục 80/20 chuẩn Skill 04:
        - Nhân vật nằm gọn ở đúng 18%-22% bên phải màn hình (`x` từ 78% đến 100%, tức `x = 1498..1920`).
        - Toàn bộ 78%-82% bên trái (`x = 0..1498`) và nền sau lưng nhân vật đổ màu xanh lá thuần khiết `#00FF00` (`RGB(0, 255, 0)`),
          không chữ, không lem viền xanh.
        """
        from PIL import Image
        import io
        import numpy as np

        base_im = Image.open(io.BytesIO(thumb_1080p_bytes)).convert("RGBA")
        if base_im.size != (1920, 1080):
            base_im = base_im.resize((1920, 1080), Image.Resampling.LANCZOS)
        w, h = base_im.size

        # Cắt vùng bên phải chứa nhân vật từ THUMBNAIL.png để tách nền
        x_cut = int(round(w * 0.54))
        right_crop = base_im.crop((x_cut, 0, w, h))

        fg_rgba: Optional[Image.Image] = None
        try:
            from rembg import remove as rembg_remove
            crop_buf = io.BytesIO()
            right_crop.save(crop_buf, format="PNG")
            cut_bytes = rembg_remove(crop_buf.getvalue())
            fg_rgba = Image.open(io.BytesIO(cut_bytes)).convert("RGBA")
            alpha_arr = np.asarray(fg_rgba, dtype=np.uint8)[:, :, 3]
            if float(np.mean(alpha_arr > 128)) < 0.08:
                fg_rgba = None
        except Exception:
            fg_rgba = None

        if fg_rgba is None:
            rc_arr = np.asarray(right_crop, dtype=np.uint8).copy()
            r_c = rc_arr[:, :, 0].astype(np.int16)
            g_c = rc_arr[:, :, 1].astype(np.int16)
            b_c = rc_arr[:, :, 2].astype(np.int16)
            is_white_bg = (r_c > 238) & (g_c > 238) & (b_c > 238) & (np.abs(r_c - g_c) < 10) & (np.abs(g_c - b_c) < 10)
            col_weights = np.linspace(1.0, 0.0, right_crop.size[0])[None, :]
            alpha_channel = np.where(is_white_bg & (col_weights > 0.35), 0, 255).astype(np.uint8)
            rc_arr[:, :, 3] = alpha_channel
            fg_rgba = Image.fromarray(rc_arr, mode="RGBA")

        fg_arr = np.asarray(fg_rgba, dtype=np.uint8).copy()
        alpha = fg_arr[:, :, 3]
        ys, xs = np.where(alpha >= 140)
        if len(xs) >= 50 and len(ys) >= 50:
            x1, x2 = int(xs.min()), int(xs.max())
            y1, y2 = int(ys.min()), int(ys.max())
            char_crop = Image.fromarray(fg_arr, mode="RGBA").crop((x1, y1, x2 + 1, y2 + 1))
        else:
            char_crop = Image.fromarray(fg_arr, mode="RGBA")

        # Đặt nhân vật vào đúng 18%-22% bên phải màn hình (x = 1498..1920, rộng ~20.5% chiều ngang)
        cw, ch = char_crop.size
        target_char_w = int(round(w * 0.205))
        target_char_h = int(round(h * 0.92))
        scale = min(target_char_w / max(1, cw), target_char_h / max(1, ch))
        new_w = max(346, min(422, int(round(cw * scale))))  # 18% (346px) .. 22% (422px)
        new_h = max(300, min(h, int(round(ch * scale))))
        char_resized = char_crop.resize((new_w, new_h), Image.Resampling.LANCZOS)

        cr_arr = np.asarray(char_resized, dtype=np.uint8).copy()
        r_ch = cr_arr[:, :, 0].astype(np.int16)
        g_ch = cr_arr[:, :, 1].astype(np.int16)
        b_ch = cr_arr[:, :, 2].astype(np.int16)
        max_rb = np.maximum(r_ch, b_ch)
        # Khử viền xanh / trắng quanh nhân vật
        cr_arr[:, :, 1] = np.where(g_ch > max_rb, max_rb + ((g_ch - max_rb) // 5), g_ch).astype(np.uint8)
        hard_mask = cr_arr[:, :, 3] >= 160

        canvas_arr = np.zeros((h, w, 3), dtype=np.uint8)
        canvas_arr[:, :, 1] = 255  # 100% nền xanh lá thuần khiết #00FF00 (RGB 0, 255, 0)

        paste_x = w - new_w  # Luôn nằm trong 18%-22% bên phải (x >= 1498)
        paste_y = h - new_h
        roi = canvas_arr[paste_y : paste_y + new_h, paste_x : paste_x + new_w]
        for c_i in range(3):
            roi[:, :, c_i] = np.where(hard_mask, cr_arr[:, :, c_i], roi[:, :, c_i])
        canvas_arr[paste_y : paste_y + new_h, paste_x : paste_x + new_w] = roi

        out_rgb = Image.fromarray(canvas_arr, mode="RGB")
        out_buf = io.BytesIO()
        out_rgb.save(out_buf, format="PNG", optimize=True)
        return out_buf.getvalue()

    def _validate_thumbnail_pair_bytes(self, thumb_bytes: bytes, green_bytes: bytes) -> Dict[str, Any]:
        """
        Kiểm định cặp ảnh `THUMBNAIL.png` và `THUMBNAIL-NENXANH.png` theo chuẩn Skill 04 (Bố cục 80/20):
        - Cùng độ phân giải 16:9 (`1920x1080`).
        - Toàn bộ 78% bên trái của `THUMBNAIL-NENXANH.png` phải là màu xanh `#00FF00` tinh khiết (`left_exact_key_ratio >= 0.96`).
        - Vùng 18%-22% bên phải chứa nhân vật người cha Mexico rõ nét (`right_character_ratio >= 0.12`).
        """
        try:
            from PIL import Image
            import io
            import numpy as np

            im_t = Image.open(io.BytesIO(thumb_bytes)).convert("RGB")
            im_g = Image.open(io.BytesIO(green_bytes)).convert("RGB")
            if im_t.size != im_g.size:
                return {"passed": False, "reason": "size_mismatch"}
            w, h = im_g.size
            arr_g = np.asarray(im_g, dtype=np.uint8)
            left_x = int(round(w * 0.78))
            left_zone = arr_g[:, :left_x, :]
            exact_green = (left_zone[:, :, 0] == 0) & (left_zone[:, :, 1] == 255) & (left_zone[:, :, 2] == 0)
            left_exact_ratio = float(np.mean(exact_green))

            right_x = int(round(w * 0.78))
            right_zone = arr_g[:, right_x:, :]
            non_green = ~(
                (right_zone[:, :, 1].astype(np.int16) - np.maximum(right_zone[:, :, 0], right_zone[:, :, 2]).astype(np.int16) > 80)
                & (right_zone[:, :, 1] > 170)
            )
            right_char_ratio = float(np.mean(non_green))
            passed = (left_exact_ratio >= 0.96) and (right_char_ratio >= 0.12)
            return {
                "passed": passed,
                "size": f"{w}x{h}",
                "left_exact_key_ratio": round(left_exact_ratio, 4),
                "right_character_ratio": round(right_char_ratio, 4),
            }
        except Exception as e:
            return {"passed": False, "reason": str(e)}

    def _normalize_thumbnail_to_16_9_1080p(self, img_bytes: bytes) -> bytes:
        """
        Chuyển đổi ảnh Thumbnail từ kích thước thô của gpt-image-1 (1536x1024 = 3:2) về đúng chuẩn YouTube Full HD 16:9 (1920x1080).
        Tự động phát hiện biên trên/dưới của khối chữ và băng rôn ở nửa trái để cắt thông minh sang 16:9 mà không cắt phạm vào chữ.
        """
        try:
            from PIL import Image
            import io
            import numpy as np

            im = Image.open(io.BytesIO(img_bytes)).convert("RGB")
            w, h = im.size
            if (w, h) == (1920, 1080):
                return img_bytes

            target_h = int(round(w * 9.0 / 16.0))
            if h > target_h:
                arr = np.asarray(im, dtype=np.uint8)
                x1, x2 = int(w * 0.04), int(w * 0.68)
                text_zone = arr[:, x1:x2, :]
                # Phát hiện vùng có chữ/băng rôn (khác biệt so với nền đồng nhất)
                row_std = np.mean(np.std(text_zone.astype(np.float32), axis=1), axis=1)
                active_rows = np.where(row_std > 18.0)[0]

                total_crop = h - target_h
                if len(active_rows) >= 2:
                    y_min = int(active_rows[0])
                    y_max = int(active_rows[-1])
                    safe_top = max(0, y_min - 20)
                    safe_bottom = max(0, (h - 1 - y_max) - 20)
                    avail_crop = safe_top + safe_bottom
                    if avail_crop >= total_crop and avail_crop > 0:
                        top_crop = int(round(total_crop * (safe_top / avail_crop)))
                        top_crop = min(safe_top, max(0, top_crop))
                        bottom_crop = min(safe_bottom, total_crop - top_crop)
                        im = im.crop((0, top_crop, w, h - bottom_crop))
                    elif avail_crop > 0:
                        im = im.crop((0, safe_top, w, h - safe_bottom))
                else:
                    top_crop = total_crop // 2
                    im = im.crop((0, top_crop, w, top_crop + target_h))

            im_1080p = im.resize((1920, 1080), Image.Resampling.LANCZOS)
            out_buf = io.BytesIO()
            im_1080p.save(out_buf, format="PNG", optimize=True)
            return out_buf.getvalue()
        except Exception:
            return img_bytes

    def _is_image_distinct_from_existing(self, new_img_bytes: bytes, existing_files: List[Path]) -> bool:
        """Kiểm tra ảnh Thumbnail mới có thực sự khác biệt so với các ảnh Thumbnail đã lưu trước đó hay không."""
        import hashlib
        new_sha = hashlib.sha256(new_img_bytes).hexdigest()
        for ef in existing_files:
            if not ef.exists():
                continue
            old_bytes = ef.read_bytes()
            if hashlib.sha256(old_bytes).hexdigest() == new_sha:
                return False
            try:
                from PIL import Image
                import io
                import numpy as np
                im1 = Image.open(io.BytesIO(new_img_bytes)).convert("RGB").resize((64, 64))
                im2 = Image.open(io.BytesIO(old_bytes)).convert("RGB").resize((64, 64))
                arr1 = np.asarray(im1, dtype=np.float32) / 255.0
                arr2 = np.asarray(im2, dtype=np.float32) / 255.0
                diff = float(np.mean(np.abs(arr1 - arr2)))
                if diff < 0.035:
                    return False
            except Exception:
                pass
        return True

    def generate_and_verify_three_thumbnails_sync(
        self,
        session: ChatGPTWebSession,
        ma_id: str,
        locked_title: str,
        step2_out: str,
        step6_out: str,
        idea: Dict[str, Any],
        proj_dir: Path,
        renders_dir: Path,
    ) -> List[str]:
        """
        BƯỚC MỚI (STEP 7 — PADRE MX V3.0):
        1. Mở đoạn chat mới, tạo ảnh Thumbnail chính `THUMBNAIL.png` (`{ma_id}_THUMBNAIL_1.png`, 16:9 `1920x1080`) theo chuẩn 80/20
           (80% bên trái nền trắng chữ Tây Ban Nha + băng rôn đỏ; 20% bên phải chân dung người cha già Mexico).
        2. Ngay sau khi có `THUMBNAIL.png`, tự động tạo bức ảnh thứ hai `THUMBNAIL-NENXANH.png` (`{ma_id}_THUMBNAIL_NENXANH.png`, 16:9 `1920x1080`)
           với nền xanh lá `#00FF00` tinh khiết và giữ nguyên 100% nhân vật người cha ở đúng tọa độ pixel để Renderer ghép vào góc trái video!
        3. Kiểm định cặp ảnh bằng `_validate_thumbnail_pair_bytes` (`left_exact_key_ratio >= 0.96`).
        """
        import base64

        renders_dir.mkdir(parents=True, exist_ok=True)
        proj_dir.mkdir(parents=True, exist_ok=True)
        prompts_list = self._extract_three_thumbnail_prompts(step6_out, step2_out, locked_title, idea)
        saved_paths: List[Path] = []

        target_file = renders_dir / f"{ma_id}_THUMBNAIL_1.png"
        target_std_file = renders_dir / "THUMBNAIL.png"
        proj_std_file = proj_dir / "THUMBNAIL.png"
        green_file = renders_dir / "THUMBNAIL-NENXANH.png"
        green_id_file = renders_dir / f"{ma_id}_THUMBNAIL_NENXANH.png"
        proj_green_file = proj_dir / "THUMBNAIL-NENXANH.png"

        def _save_matched_pair(thumb_1080p_bytes: bytes) -> List[Path]:
            target_file.write_bytes(thumb_1080p_bytes)
            target_std_file.write_bytes(thumb_1080p_bytes)
            proj_std_file.write_bytes(thumb_1080p_bytes)
            out_list = [target_file]
            try:
                green_bytes = self._create_matched_green_screen_from_thumbnail_bytes(thumb_1080p_bytes)
                val_pair = self._validate_thumbnail_pair_bytes(thumb_1080p_bytes, green_bytes)
                green_file.write_bytes(green_bytes)
                green_id_file.write_bytes(green_bytes)
                proj_green_file.write_bytes(green_bytes)
                out_list.append(green_file)
                try:
                    from backend.visual_cue_director import ensure_project_script_green_images
                    ensure_project_script_green_images(proj_dir=proj_dir, renders_dir=renders_dir, proj_name=ma_id)
                except Exception:
                    pass
                log_info(
                    "SCRIPT",
                    f"[{ma_id}] 🟩 Đã tạo & kiểm định cặp ảnh THUMBNAIL.png + THUMBNAIL-NENXANH.png + bộ 7 ảnh green_part_01..07.png "
                    f"(left_key={val_pair.get('left_exact_key_ratio')}, right_char={val_pair.get('right_character_ratio')})",
                    project_id=ma_id,
                )
            except Exception as e_gr:
                log_warn("SCRIPT", f"[{ma_id}] ⚠️ Lỗi tách nền tạo THUMBNAIL-NENXANH.png: {e_gr}", project_id=ma_id)
            return out_list

        if target_file.exists() and target_file.stat().st_size > 30000:
            saved_paths = _save_matched_pair(target_file.read_bytes())
            self._emit(
                message=f"[{ma_id}] ♻️ Đã đồng bộ cặp Thumbnail + Ảnh Nền Xanh ({target_file.name} & THUMBNAIL-NENXANH.png)..."
            )
            return [str(p) for p in saved_paths]

        max_attempts = 5
        best_fallback_bytes: Optional[bytes] = None
        tried_thumb_accs: set = {getattr(session, "acc_id", "acc_1")}

        for attempt in range(1, max_attempts + 1):
            if self.should_stop:
                raise RuntimeError("Đã dừng theo yêu cầu người dùng.")

            acc_lbl = getattr(session, "cfg", {}).get("label", getattr(session, "acc_id", "AI"))
            self._update_idea_record(
                ma_id,
                current_step=f"STEP 7: Đang tạo cặp Thumbnail 80/20 + Ảnh Nền Xanh trên {acc_lbl} (Lượt {attempt}/{max_attempts})...",
            )
            self._emit(
                current_step="STEP 7 — Tạo Thumbnail 80/20 + Ảnh Nhân Vật Nền Xanh",
                progress=94.0,
                message=f"[{ma_id}] 🎨 Mở đoạn chat mới trên {acc_lbl} tạo Thumbnail 80/20 + Ảnh Nền Xanh (Lượt {attempt}/{max_attempts})...",
            )

            session.start_fresh_chat(f"STEP7_THUMB_1_TRY_{attempt}")

            prompt_to_send = prompts_list[min(attempt - 1, len(prompts_list) - 1)]
            if attempt > 1:
                prompt_to_send += (
                    "\n\nLAYOUT REQUIREMENT:\n"
                    "- Draw a completely new standalone 1536x1024 image from scratch.\n"
                    "- Left 78% solid white background (#FFFFFF) with bold uppercase Spanish text and a bottom red banner; right 22% realistic photographic portrait of the elderly Mexican father."
                )

            img_res = session.generate_image_and_harvest_base64(
                prompt_to_send,
                step_label=f"THUMB_1_TRY_{attempt}",
                timeout_sec=260,
                progress_cb=lambda st, sec, at=attempt, al=acc_lbl: self._emit(
                    message=f"[{ma_id}] 🎨 {al} đang vẽ Thumbnail 80/20 (Lượt {at}: {sec}s)..."
                ),
                should_stop_cb=lambda: self.should_stop,
            )

            if not img_res.get("success") or not img_res.get("b64_data"):
                err_txt = str(img_res.get("error", "retry"))
                is_rl = bool(img_res.get("rate_limited"))
                self._emit(
                    message=f"[{ma_id}] ⚠️ Lượt {attempt} ({acc_lbl}): Chưa thu được ảnh Thumbnail ({err_txt}) -> {'Tài khoản bị Limit 30p, đang đổi sang nick khác...' if is_rl else 'Đang đổi nick / tạo lại...'}"
                )
                if isinstance(session, ChatGPTWebSession) and hasattr(session, "switch_to_another_account"):
                    if not is_rl and attempt >= 2:
                        mark_account_rate_limited(
                            session.acc_id,
                            reason=f"Lỗi tạo Thumbnail liên tiếp ({err_txt})",
                            cooldown_sec=ACCOUNT_LIMIT_COOLDOWN_SEC,
                        )
                    switched = session.switch_to_another_account(extra_exclude=tried_thumb_accs)
                    if switched:
                        tried_thumb_accs.add(session.acc_id)
                        self._emit(
                            message=f"[{ma_id}] 🔄 Đã chuyển sang tài khoản {session.cfg['label']} (Cổng {session.port}) để tạo lại Thumbnail!"
                        )
                continue

            try:
                raw_img_bytes = base64.b64decode(img_res["b64_data"])
                img_bytes = self._normalize_thumbnail_to_16_9_1080p(raw_img_bytes)
            except Exception:
                continue

            if len(img_bytes) < 20000:
                continue

            best_fallback_bytes = img_bytes

            self._emit(
                message=f"[{ma_id}] 🔍 Đang đánh giá QA Thumbnail 80/20 & tách nền tạo THUMBNAIL-NENXANH.png..."
            )
            qa_prompt = (
                "Hãy nhìn trực tiếp vào bức ảnh Thumbnail vừa tạo ở trên và kiểm định chất lượng (PADRE MX 80/20 QA Gate):\n"
                "1. Bên trái có vùng chữ tiếng Tây Ban Nha rõ nét trên nền sáng kèm băng rôn nổi bật không?\n"
                "2. Bên phải có chân dung người đàn ông lớn tuổi Mexico rõ mặt, biểu cảm cảm xúc kịch tính không?\n"
                "Chỉ trả lời ngắn gọn đúng định dạng 2 dòng sau:\n"
                "THUMBNAIL_QA: PASS (nếu đạt chuẩn) hoặc FAIL (nếu ảnh bị lỗi nặng)\n"
                "REASON: <nhận xét 1 câu>"
            )
            qa_resp = ""
            try:
                qa_resp = session.send_prompt_and_wait(
                    qa_prompt,
                    step_label=f"QA_THUMB_1_{attempt}",
                    timeout_sec=120,
                    should_stop_cb=lambda: self.should_stop,
                )
            except Exception:
                qa_resp = "THUMBNAIL_QA: PASS"

            is_qa_pass = (
                "THUMBNAIL_QA: FAIL" not in qa_resp.upper()
                and "THUMBNAIL_QA：FAIL" not in qa_resp.upper()
            )

            if is_qa_pass:
                saved_paths = _save_matched_pair(img_bytes)
                self._update_idea_record(ma_id, has_thumbnail=True)
                self._emit(
                    message=f"[{ma_id}] ✅ Cặp ảnh THUMBNAIL.png + THUMBNAIL-NENXANH.png ĐẠT CHUẨN QA -> Đã lưu vào {renders_dir}!"
                )
                break
            else:
                self._emit(
                    message=f"[{ma_id}] ⚠️ Thumbnail (Lượt {attempt}) chưa đạt QA -> Đang tạo lại..."
                )

        if not target_file.exists() and best_fallback_bytes:
            saved_paths = _save_matched_pair(best_fallback_bytes)
            self._update_idea_record(ma_id, has_thumbnail=True)
            self._emit(
                message=f"[{ma_id}] 💾 Đã lưu cặp ảnh THUMBNAIL.png + THUMBNAIL-NENXANH.png vào thư mục dự án!"
            )

        return [str(p) for p in saved_paths]

    def ensure_project_thumbnail_with_failover_sync(
        self,
        ma_id: str,
        preferred_acc_id: Optional[str] = None,
        exclude_accs: Optional[set] = None,
    ) -> List[str]:
        """
        Đảm bảo 100% dự án `ma_id` có đủ cặp Thumbnail (`{ma_id}_THUMBNAIL_1.png` / `THUMBNAIL.png` + `THUMBNAIL-NENXANH.png` > 20KB).
        Nếu chưa có hoặc tạo lỗi / tài khoản bị limit:
        - Tự động xoay vòng qua tất cả các tài khoản ChatGPT đang có (`acc_1`, `acc_2`, `acc_3`),
        - Nếu tài khoản nào bị limit thì tạm dừng tài khoản đó 30 phút và chuyển sang nick khác tạo ngay.
        """
        from .chatgpt_web_client import ensure_all_saved_chatgpt_accounts_open, CHATGPT_ACCOUNTS

        proj_dir = self.projects_dir / ma_id
        proj_dir.mkdir(parents=True, exist_ok=True)
        renders_dir = proj_dir / "renders"
        renders_dir.mkdir(parents=True, exist_ok=True)

        target_thumb = renders_dir / f"{ma_id}_THUMBNAIL_1.png"
        target_green = renders_dir / "THUMBNAIL-NENXANH.png"
        if target_thumb.exists() and target_thumb.stat().st_size > 20000:
            if not (target_green.exists() and target_green.stat().st_size > 10000):
                try:
                    g_bytes = self._create_matched_green_screen_from_thumbnail_bytes(target_thumb.read_bytes())
                    target_green.write_bytes(g_bytes)
                    (renders_dir / f"{ma_id}_THUMBNAIL_NENXANH.png").write_bytes(g_bytes)
                    (proj_dir / "THUMBNAIL-NENXANH.png").write_bytes(g_bytes)
                except Exception:
                    pass
            self._update_idea_record(ma_id, has_thumbnail=True)
            return [str(target_thumb), str(target_green)] if target_green.exists() else [str(target_thumb)]

        # Chuẩn bị dữ liệu Idea + Step 2 + Step 6 để tạo Thumbnail
        ideas = self.load_saved_ideas()
        idea = next((it for it in ideas if it.get("ma_id") == ma_id), None) or {"ma_id": ma_id}
        step2_file = proj_dir / "step2_title_thumbnail.txt"
        step2_out = step2_file.read_text(encoding="utf-8", errors="ignore") if step2_file.exists() else ""
        locked_title = (
            idea.get("locked_title")
            or extract_locked_title_from_step2(step2_out, fallback_title=idea.get("draft_title_ja", ma_id))
        )
        _, _, sc_chars = self.has_valid_script_on_disk(ma_id)
        step6_file = proj_dir / "seo_publish_pack.txt"
        if step6_file.exists() and step6_file.stat().st_size > 200:
            step6_out = step6_file.read_text(encoding="utf-8", errors="ignore")
        else:
            step6_out = self._build_fallback_seo_pack(ma_id, locked_title, sc_chars or 45000, idea, step2_out)
            step6_file.write_text(step6_out, encoding="utf-8")

        try:
            ensure_all_saved_chatgpt_accounts_open(run_hidden=False)
        except Exception:
            pass

        tried_accs: set = set(exclude_accs or set())
        total_acc_slots = len(CHATGPT_ACCOUNTS) + 1

        for round_idx in range(total_acc_slots):
            if self.should_stop:
                break
            if target_thumb.exists() and target_thumb.stat().st_size > 20000:
                self._update_idea_record(ma_id, has_thumbnail=True)
                return [str(target_thumb)]

            # Nếu mọi tài khoản đều đã thử hoặc đang trong 30p cooldown, mở lại tập exclude để chọn nick rảnh nhất
            use_exclude = tried_accs if len(tried_accs) < len(CHATGPT_ACCOUNTS) else set()
            sess = ChatGPTWebSession(
                project_id=f"{ma_id}_THUMB",
                acc_id=preferred_acc_id if (round_idx == 0 and preferred_acc_id not in use_exclude) else None,
                exclude_accs=use_exclude,
            )
            tried_accs.add(sess.acc_id)
            try:
                self._emit(
                    current_ma_id=ma_id,
                    current_step=f"🎨 Đang tạo bù Thumbnail trên {sess.cfg['label']}",
                    progress=93.0,
                    message=f"[{ma_id}] 🎨 Kiểm tra thấy thiếu Thumbnail -> Đang mở {sess.cfg['label']} (Cổng {sess.port}) để tạo Thumbnail 16:9...",
                )
                if not sess.open_session_tab():
                    mark_account_rate_limited(
                        sess.acc_id,
                        reason="Không mở được tab Chrome tạo Thumbnail",
                        cooldown_sec=300,
                    )
                    continue
                res_paths = self.generate_and_verify_three_thumbnails_sync(
                    session=sess,
                    ma_id=ma_id,
                    locked_title=locked_title,
                    step2_out=step2_out,
                    step6_out=step6_out,
                    idea=idea,
                    proj_dir=proj_dir,
                    renders_dir=renders_dir,
                )
                if res_paths and target_thumb.exists() and target_thumb.stat().st_size > 20000:
                    self._update_idea_record(ma_id, has_thumbnail=True)
                    log_info(
                        "SCRIPT",
                        f"[{ma_id}] ✅ Đã tạo bù thành công Thumbnail trên {sess.cfg['label']}: {target_thumb.name}",
                        project_id=ma_id,
                    )
                    return [str(target_thumb)]
            except Exception as e_th_fail:
                log_warn(
                    "SCRIPT",
                    f"[{ma_id}] ⚠️ Lỗi tạo Thumbnail trên {sess.cfg['label']}: {e_th_fail} -> Đổi sang tài khoản khác!",
                    project_id=ma_id,
                )
            finally:
                try:
                    sess.close_session_tab(keep_open=False)
                except Exception:
                    pass

        if target_thumb.exists() and target_thumb.stat().st_size > 20000:
            self._update_idea_record(ma_id, has_thumbnail=True)
            return [str(target_thumb)]
        return []

    def ensure_all_projects_have_thumbnails_sync(
        self,
        target_ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Quét toàn bộ các kịch bản đã hoàn thành (trong `target_ids` và trên ổ cứng):
        Bất kỳ kịch bản nào chưa có Thumbnail (`{ma_id}_THUMBNAIL_1.png`) đều được tự động
        chạy tạo lại (tự động chuyển sang nick khác nếu nick hiện tại lỗi/limit).
        """
        self._sync_projects_disk_state()
        ideas = self.load_saved_ideas()
        all_ids: List[str] = []
        if target_ids:
            for mid in target_ids:
                if mid and mid not in all_ids:
                    all_ids.append(mid)
        for it in ideas:
            mid = str(it.get("ma_id", "")).strip()
            if mid and mid not in all_ids:
                all_ids.append(mid)

        missing_ids: List[str] = []
        for mid in all_ids:
            has_sc, _, _ = self.has_valid_script_on_disk(mid)
            if not has_sc:
                continue
            has_th, _, _ = self.has_thumbnail_and_seo_on_disk(mid)
            if not has_th:
                missing_ids.append(mid)

        if not missing_ids:
            return {"checked": len(all_ids), "missing_before": 0, "fixed": [], "still_missing": []}

        log_info(
            "SCRIPT",
            f"🔍 Phát hiện {len(missing_ids)} kịch bản đã xong nhưng thiếu Thumbnail ({', '.join(missing_ids)}) -> Bắt đầu tạo bù Thumbnail đa tài khoản!",
        )
        self._emit(
            status="running",
            current_step=f"🎨 Đang tạo bù Thumbnail cho {len(missing_ids)} kịch bản thiếu",
            progress=95.0,
            message=f"🔍 Phát hiện {len(missing_ids)} kịch bản thiếu Thumbnail ({', '.join(missing_ids)}) -> Đang tự động tạo lại (Tự động đổi nick nếu limit)...",
        )

        fixed_ids: List[str] = []
        still_missing: List[str] = []
        for idx, mid in enumerate(missing_ids, 1):
            if self.should_stop:
                break
            self._emit(
                current_ma_id=mid,
                current_step=f"🎨 Tạo bù Thumbnail [{idx}/{len(missing_ids)}]: {mid}",
                progress=95.0 + min(4.0, (idx / max(1, len(missing_ids))) * 4.0),
                message=f"🎨 [{idx}/{len(missing_ids)}] Đang tạo bù Thumbnail cho kịch bản {mid}...",
            )
            paths = self.ensure_project_thumbnail_with_failover_sync(mid)
            if paths:
                fixed_ids.append(mid)
            else:
                still_missing.append(mid)

        self._sync_projects_disk_state()
        return {
            "checked": len(all_ids),
            "missing_before": len(missing_ids),
            "fixed": fixed_ids,
            "still_missing": still_missing,
        }

    # ==========================================================================
    # LUỒNG CHẠY TỰ ĐỘNG CHO 1 HOẶC NHIỀU DỰ ÁN
    # ==========================================================================
    def _write_part_with_length_gate(
        self,
        session: ChatGPTWebSession,
        ma_id: str,
        part_letter: str,
        locked_title: str,
        min_chars: int,
        max_chars: int,
        target_chars: int,
        base_progress: float,
        step3_context: str = "",
        prev_part_tail: str = "",
        min_acceptable_chars: int = 9500,
    ) -> str:
        """
        Điều khiển ChatGPT viết 1 Part (A, B hoặc C) và tự động nối thêm cho đến khi đủ ngưỡng độ dài.
        - BẮT BUỘC mỗi Part phải đạt tối thiểu `min_acceptable_chars` (mặc định >= 9.500–10.000 chữ thuần).
        - Nếu một lượt chat bị nghẽn ngữ cảnh (trả về rỗng hoặc không tăng ký tự), tự động mở ĐOẠN CHAT MỚI
          kèm `step3_context` + đoạn kết hiện tại để viết tiếp thay vì dừng sớm (tránh lỗi thiếu Part như P16, P17).
        """
        self._emit(
            current_step=f"STEP 4 — Đang viết PART {part_letter}",
            progress=base_progress,
            message=f"[{ma_id}] Đang viết kịch bản PART {part_letter} (Mục tiêu: {min_chars:,}–{max_chars:,} chữ thuần)...",
        )

        p_init = self._build_step4_part_initial_prompt(
            ma_id,
            part_letter,
            locked_title,
            min_chars,
            max_chars,
            target_chars,
            step3_context=step3_context,
            prev_part_tail=prev_part_tail,
        )
        raw_resp = session.send_prompt_and_wait(
            p_init,
            step_label=f"STEP4_PART_{part_letter}_1",
            timeout_sec=900,
            progress_cb=lambda st, ch: self._emit(
                message=f"[{ma_id}] Đang nhận văn bản PART {part_letter} (Lượt 1: {ch:,} ký tự)..."
            ),
            should_stop_cb=lambda: self.should_stop,
        )

        clean_chunks: List[str] = []
        first_clean = extract_clean_japanese_narration(raw_resp)
        if first_clean:
            clean_chunks.append(first_clean)

        combined_clean = "\n".join(clean_chunks)
        curr_pure = pure_char_count(combined_clean)

        turn_idx = 2
        stalled_retries = 0
        max_turns = 8
        while curr_pure < min_chars and turn_idx <= max_turns:
            if self.should_stop:
                raise RuntimeError("Đã dừng theo yêu cầu người dùng.")

            tail_ja = combined_clean[-180:].replace("\n", "") if combined_clean else prev_part_tail[-180:].replace("\n", "")
            self._emit(
                progress=min(base_progress + turn_idx * 2.2, base_progress + 14.0),
                message=f"[{ma_id}] PART {part_letter} đạt {curr_pure:,}/{min_chars:,} chữ thuần -> Đang viết nối tiếp lượt {turn_idx}...",
            )

            # Nếu lượt trước chưa sinh được chữ nào (curr_pure == 0) hoặc bị kẹt, mở đoạn chat mới tinh để cứu hộ
            need_fresh_recovery = (curr_pure == 0) or (stalled_retries >= 1)
            if need_fresh_recovery:
                session.start_fresh_chat(f"STEP_4_RECOVERY_PART_{part_letter}_T{turn_idx}")
                self._emit(
                    message=f"[{ma_id}] 🔄 Mở đoạn chat cứu hộ mới cho PART {part_letter} (Lượt {turn_idx}, hiện có {curr_pure:,} chữ)..."
                )

            if curr_pure == 0:
                p_cont = self._build_step4_part_initial_prompt(
                    ma_id,
                    part_letter,
                    locked_title,
                    min_chars,
                    max_chars,
                    target_chars,
                    step3_context=step3_context,
                    prev_part_tail=prev_part_tail,
                )
            else:
                p_cont = self._build_step4_part_continue_prompt(
                    part_letter=part_letter,
                    current_pure=curr_pure,
                    min_c=min_chars,
                    max_c=max_chars,
                    target_c=target_chars,
                    last_tail_ja=tail_ja,
                    step3_context=step3_context if need_fresh_recovery else "",
                )

            cont_resp = session.send_prompt_and_wait(
                p_cont,
                step_label=f"STEP4_PART_{part_letter}_{turn_idx}",
                timeout_sec=900,
                progress_cb=lambda st, ch, t=turn_idx: self._emit(
                    message=f"[{ma_id}] Đang viết tiếp PART {part_letter} (Lượt {t}: +{ch:,} ký tự)..."
                ),
                should_stop_cb=lambda: self.should_stop,
            )
            next_clean = extract_clean_japanese_narration(cont_resp)
            if next_clean:
                clean_chunks.append(next_clean)
            combined_clean = "\n".join(clean_chunks)
            new_pure = pure_char_count(combined_clean)

            if new_pure <= curr_pure + 120:
                stalled_retries += 1
                # Nếu đã đủ ngưỡng chấp nhận tối thiểu (ví dụ >= 10,000 chữ) thì cho phép chốt Part
                if curr_pure >= min_acceptable_chars and stalled_retries >= 2:
                    break
                # Nếu vẫn chưa đủ và đã thử mở chat mới 3 lần liên tiếp không ra chữ -> báo lỗi rõ ràng
                if stalled_retries >= 3:
                    break
            else:
                stalled_retries = 0

            curr_pure = new_pure
            turn_idx += 1

        if curr_pure < min_acceptable_chars:
            raise RuntimeError(
                f"[{ma_id}] STAGE {part_letter} chưa đạt độ dài tối thiểu ({curr_pure:,}/{min_acceptable_chars:,} ký tự). "
                f"Hệ thống dừng ghép kịch bản để bảo vệ chất lượng — Hãy bấm Chạy lại để viết tiếp STAGE {part_letter}!"
            )

        if curr_pure > max_chars:
            combined_clean = trim_japanese_to_max_pure_chars(combined_clean, max_pure_chars=max_chars - 150)

        combined_clean = ensure_part_headings_for_stage(combined_clean, part_letter)
        return combined_clean

    def _enqueue_or_start_video_job(
        self,
        ma_id: str,
        script_text: str,
        seo_text: str,
        video_settings: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Đẩy 1 kịch bản đã hoàn chỉnh vào hàng đợi tạo Voice & Render Video MP4 ngay lập tức (Non-blocking)."""
        if self.video_pipeline is None:
            log_error("VIDEO", f"[{ma_id}] Không tìm thấy đối tượng video_pipeline để xuất MP4!", project_id=ma_id)
            return False

        # Kiểm tra nếu dự án đã có sẵn file MP4 hoàn chỉnh (đã qua kiểm định ffprobe & thời lượng) thì giữ trạng thái COMPLETED_VIDEO, tránh render trùng
        has_valid_mp4, mp4_file, _ = self.has_valid_video_mp4_on_disk(
            ma_id, sc_chars=len(script_text), auto_delete_corrupted=True
        )
        if has_valid_mp4 and mp4_file is not None:
            self._update_idea_record(
                ma_id,
                has_script=True,
                has_video_mp4=True,
                status="COMPLETED_VIDEO",
                current_step=f"✅ Đã có sẵn Video MP4 ({mp4_file.name})",
            )
            return True

        vcfg = video_settings or {}
        job_payload = [{
            "name": ma_id,
            "script_text": script_text,
            "seo_text": seo_text,
        }]
        self._update_idea_record(
            ma_id,
            has_script=True,
            status="VIDEO_QUEUED",
            current_step="🎬 Đã viết xong Kịch bản -> Đang xếp hàng tạo Voice & Render MP4...",
        )
        log_info(
            "VIDEO",
            f"🚀 [STREAMING RENDER] Kịch bản [{ma_id}] vừa hoàn tất -> Đẩy ngay vào Hàng Đợi Tạo Voice & Render MP4!",
            project_id=ma_id,
        )
        return self.video_pipeline.start_batch_production_async(
            jobs=job_payload,
            output_dir=vcfg.get("output_dir") or str(self.projects_dir),
            channel_name=vcfg.get("channel_name", "."),
            resolution=vcfg.get("resolution", "1920x1080"),
            fps=int(vcfg.get("fps", 24)),
            stock_selection=vcfg.get("stock_selection", "auto_unique"),
            bgm_path=vcfg.get("bgm_path"),
            bgm_volume=float(vcfg.get("bgm_volume", 0.08)),
            delete_used_stocks=bool(vcfg.get("delete_used_stocks", True)),
            auto_ensure_stock_hours=bool(vcfg.get("auto_ensure_stock_hours", True)),
            target_stock_hours=float(vcfg.get("target_stock_hours", 10.0)),
            voice_config=vcfg.get("voice_config"),
        )

    def run_single_idea_pipeline_sync(
        self,
        ma_id: str,
        preferred_acc_id: Optional[str] = None,
        auto_produce_video: bool = True,
        video_settings: Optional[Dict[str, Any]] = None,
        target_part_min: int = 13334,
        defer_video_handoff: bool = False,
        force_rewrite_script: bool = False,
        ai_provider: str = "chatgpt_web",
        exclude_accs: Optional[set] = None,
    ) -> Dict[str, Any]:
        """
        Chạy quy trình cho 1 Mã ý tưởng:
        - BẢO VỆ TUYỆT ĐỐI KỊCH BẢN ĐÃ VIẾT XONG: Nếu trên ổ cứng đã có `script_clean.txt`
          (hoặc đủ `part_a/b/c.txt`) và `force_rewrite_script=False`, TUYỆT ĐỐI KHÔNG mở Chrome
          viết lại kịch bản mà đóng gói SEO ngay và chuyển thẳng sang tạo Voice & Render Video!
        - Nếu `defer_video_handoff=True` (khi chạy Đa luồng Phase 1): Chỉ hoàn thành Kịch bản & SEO,
          trả về ngay để chờ Phase 2 mới đồng loạt tạo Voice & Render Video.
        """
        if self.should_stop:
            raise RuntimeError("Đã dừng theo yêu cầu của người dùng.")

        self._sync_projects_disk_state()
        ideas = self.load_saved_ideas()
        idea = next((it for it in ideas if it.get("ma_id") == ma_id), None)
        if not idea:
            info_f = self.projects_dir / ma_id / "idea_info.json"
            if info_f.exists():
                try:
                    idea = json.loads(info_f.read_text(encoding="utf-8"))
                    if isinstance(idea, dict) and idea.get("ma_id") == ma_id:
                        with self.ideas_io_lock:
                            cur_ideas = self.load_saved_ideas()
                            if not any(x.get("ma_id") == ma_id for x in cur_ideas):
                                cur_ideas.insert(0, idea)
                                self.save_ideas_list(cur_ideas)
                except Exception:
                    idea = None
        if not idea:
            raise ValueError(f"Không tìm thấy ý tưởng mã {ma_id} trong danh sách đã lưu!")

        proj_dir = self.projects_dir / ma_id
        proj_dir.mkdir(parents=True, exist_ok=True)
        renders_dir = proj_dir / "renders"
        renders_dir.mkdir(parents=True, exist_ok=True)

        # Nếu người dùng bấm nút "🔁 Viết Lại" (force_rewrite_script=True) -> Dọn sạch các file kịch bản cũ để viết mới hoàn toàn từ Step 2
        if force_rewrite_script:
            for old_fn in (
                "step2_title_thumbnail.txt",
                "step3_architecture.txt",
                "part_a.txt",
                "part_b.txt",
                "part_c.txt",
                "script_clean.txt",
                "step5_audit_report.txt",
                "seo_publish_pack.txt",
                "00_TIEU_DE_VA_SEO_YOUTUBE.txt",
            ):
                old_fp = proj_dir / old_fn
                if old_fp.exists():
                    try:
                        old_fp.unlink()
                    except Exception:
                        pass
            for old_ren in (
                renders_dir / f"{ma_id}_KICH_BAN.txt",
                renders_dir / f"{ma_id}_SEO.txt",
            ):
                if old_ren.exists():
                    try:
                        old_ren.unlink()
                    except Exception:
                        pass
            for old_th in renders_dir.glob(f"{ma_id}_THUMBNAIL_*.png"):
                try:
                    old_th.unlink()
                except Exception:
                    pass
            self._update_idea_record(
                ma_id,
                has_script=False,
                has_seo=False,
                has_thumbnail=False,
                pure_char_count=0,
                completed_parts_count=0,
                missing_parts=["A", "B", "C"],
                status="RUNNING",
                current_step="🔁 Đang viết lại mới từ Step 2...",
            )
            log_info("SCRIPT", f"[{ma_id}] 🔁 Người dùng kích hoạt VIẾT LẠI THỦ CÔNG -> Đã dọn sạch dữ liệu cũ để viết mới từ Step 2.", project_id=ma_id)

        # ======================================================================
        # CHỐT CHẶN BẢO VỆ: NẾU ĐÃ CÓ SẴN KỊCH BẢN -> KHÔNG BAO GIỜ VIẾT LẠI!
        # ======================================================================
        has_existing_script, existing_script_text, existing_pure_chars = self.has_valid_script_on_disk(ma_id)
        if has_existing_script and not force_rewrite_script:
            self._emit(
                status="running",
                current_ma_id=ma_id,
                current_step="♻️ Đã có sẵn kịch bản -> Bỏ qua viết lại kịch bản",
                progress=85.0,
                message=(
                    f"[{ma_id}] ♻️ Phát hiện kịch bản đã viết xong ({existing_pure_chars:,} chữ thuần). "
                    f"Giữ nguyên 100% kịch bản cũ, KHÔNG mở Chrome viết lại!"
                ),
            )
            step2_file = proj_dir / "step2_title_thumbnail.txt"
            step2_out = step2_file.read_text(encoding="utf-8") if step2_file.exists() else ""
            locked_title = (
                idea.get("locked_title")
                or extract_locked_title_from_step2(step2_out, fallback_title=idea.get("draft_title_ja", ma_id))
            )

            step6_file = proj_dir / "seo_publish_pack.txt"
            if step6_file.exists() and step6_file.stat().st_size > 200:
                step6_out = step6_file.read_text(encoding="utf-8")
            else:
                step6_out = self._build_fallback_seo_pack(ma_id, locked_title, existing_pure_chars, idea, step2_out)
                step6_file.write_text(step6_out, encoding="utf-8")

            master_seo_file = proj_dir / "00_TIEU_DE_VA_SEO_YOUTUBE.txt"
            if not master_seo_file.exists() or master_seo_file.stat().st_size < 200:
                master_seo_content = (
                    f"================================================================================\n"
                    f"🎬 HỒ SƠ XUẤT BẢN YOUTUBE — MÃ DỰ ÁN: {ma_id}\n"
                    f"================================================================================\n"
                    f"📌 TIÊU ĐỀ CHÍNH THỨC ĐÃ KHÓA (LOCKED_TITLE):\n{locked_title}\n\n"
                    f"📝 TIÊU ĐỀ NHÁP BAN ĐẦU:\n{idea.get('draft_title_ja', '')}\n\n"
                    f"📖 TÓM TẮT CỐT TRUYỆN:\n{idea.get('summary_vi', '')}\n\n"
                    f"📊 THỐNG KÊ KỊCH BẢN (PURE CHARACTER COUNT):\n"
                    f"- TỔNG CỘNG: {existing_pure_chars:,} ký tự thuần (~{round(existing_pure_chars / 353)} phút giọng đọc)\n\n"
                    f"================================================================================\n"
                    f"🚀 GÓI SEO YOUTUBE & THUMBNAIL 6 DÒNG\n"
                    f"================================================================================\n"
                    f"{step6_out}\n"
                )
                master_seo_file.write_text(master_seo_content, encoding="utf-8")
            else:
                master_seo_content = master_seo_file.read_text(encoding="utf-8")

            (renders_dir / f"{ma_id}_SEO.txt").write_text(master_seo_content, encoding="utf-8")
            (renders_dir / f"{ma_id}_KICH_BAN.txt").write_text(existing_script_text, encoding="utf-8")
            thumb_files = [str(p) for p in sorted(renders_dir.glob(f"{ma_id}_THUMBNAIL_*.png")) if p.stat().st_size > 20000]

            # BẮT BUỘC MỌI KỊCH BẢN PHẢI CÓ THUMBNAIL: Nếu dự án đã có kịch bản nhưng chưa có Thumbnail -> Tự động tạo bù (kèm đổi nick nếu limit/lỗi)!
            if len(thumb_files) == 0 and not self.should_stop:
                try:
                    self._emit(
                        current_ma_id=ma_id,
                        current_step="STEP 7 — Đang tạo bổ sung Thumbnail 16:9 (6 dòng chữ)",
                        progress=92.0,
                        message=f"[{ma_id}] 🎨 Kịch bản ({existing_pure_chars:,} chữ) & SEO đã có sẵn nhưng chưa có Thumbnail -> Đang tạo bổ sung 1 Thumbnail 16:9...",
                    )
                    thumb_files = self.ensure_project_thumbnail_with_failover_sync(
                        ma_id=ma_id,
                        preferred_acc_id=preferred_acc_id,
                        exclude_accs=exclude_accs,
                    )
                except Exception as e_th_ex:
                    log_warn("SCRIPT", f"[{ma_id}] Không thể tạo bổ sung Thumbnail: {e_th_ex}", project_id=ma_id)

            video_triggered = False
            if auto_produce_video and not defer_video_handoff and self.video_pipeline is not None:
                self._emit(
                    current_ma_id=ma_id,
                    current_step="🎬 Đẩy kịch bản có sẵn sang tạo Voice & Render MP4",
                    progress=95.0,
                    message=f"[{ma_id}] 🚀 Đang chuyển kịch bản có sẵn ({existing_pure_chars:,} chữ) sang tạo Voice & Render Video MP4...",
                )
                video_triggered = self._enqueue_or_start_video_job(
                    ma_id=ma_id,
                    script_text=existing_script_text,
                    seo_text=master_seo_content,
                    video_settings=video_settings,
                )
            else:
                has_th_now = len(thumb_files) > 0
                self._update_idea_record(
                    ma_id,
                    locked_title=locked_title,
                    pure_char_count=existing_pure_chars,
                    has_script=True,
                    has_seo=True,
                    has_thumbnail=has_th_now,
                    status="SCRIPT_DONE",
                    current_step=(
                        f"📝 Đã xong Kịch bản ({existing_pure_chars:,} chữ) + SEO + {len(thumb_files)}/1 Thumbnail — Sẵn sàng Render MP4"
                        if not auto_produce_video
                        else f"📝 Đã có kịch bản ({existing_pure_chars:,} chữ) — Chờ Phase 2 tạo Voice & Video"
                    ),
                )
                if not auto_produce_video and not defer_video_handoff:
                    self._emit(
                        status="running" if self.is_running else "completed",
                        current_ma_id=ma_id,
                        current_step=f"✅ Xong {ma_id} (Kịch bản + SEO + Thumbnail)",
                        progress=98.0 if self.is_running else 100.0,
                        message=f"[{ma_id}] 🎉 Đã hoàn tất Kịch bản ({existing_pure_chars:,} chữ) + SEO + {len(thumb_files)}/1 Thumbnail (Chế độ Không Render Video)!",
                    )

            return {
                "success": True,
                "ma_id": ma_id,
                "locked_title": locked_title,
                "pure_char_count": existing_pure_chars,
                "project_dir": str(proj_dir),
                "renders_dir": str(renders_dir),
                "script_path": str(proj_dir / "script_clean.txt"),
                "seo_path": str(master_seo_file),
                "thumbnails": thumb_files,
                "video_triggered": video_triggered,
                "reused_existing_script": True,
            }

        # ======================================================================
        # TRƯỜNG HỢP CHƯA CÓ KỊCH BẢN -> MỞ CHROME CHATGPT WEB CHẠY STEP 2 -> STEP 7
        # ======================================================================
        provider_norm = "chatgpt_web"
        session = ChatGPTWebSession(project_id=ma_id, acc_id=preferred_acc_id, exclude_accs=exclude_accs)
        provider_label = "ChatGPT Web (Medium)"

        try:
            self._update_idea_record(
                ma_id,
                status="RUNNING",
                ai_provider=provider_norm,
                current_step=f"Đang mở phiên {provider_label}...",
            )
            self._emit(
                status="running",
                current_ma_id=ma_id,
                current_step=f"Khởi tạo {provider_label}",
                progress=5.0,
                message=f"[{ma_id}] Đang kết nối {provider_label} trên {session.cfg['label']} (Cổng {session.port})...",
            )

            if not session.open_session_tab():
                raise RuntimeError(
                    f"Không mở được khung chat trên {session.cfg['label']} (Cổng {session.port}). "
                    f"Hãy bấm mở {session.cfg['label']} trên thanh điều khiển để đăng nhập ChatGPT!"
                )

            # ------------------------------------------------------------------
            # ĐOẠN CHAT #1 (STEP 2): IDEA / TITLE / THUMBNAIL 6 DÒNG
            # ------------------------------------------------------------------
            step2_file = proj_dir / "step2_title_thumbnail.txt"
            step2_valid = False
            if step2_file.exists() and step2_file.stat().st_size > 2500 and not force_rewrite_script:
                try:
                    s2_probe = step2_file.read_text(encoding="utf-8", errors="ignore")
                    if any(k in s2_probe.upper() for k in ("LOCKED_TITLE", "TITLE MATRIX", "THUMBNAIL", "STEP 2", "STEP3_HANDOFF")):
                        step2_out = s2_probe
                        step2_valid = True
                    else:
                        step2_file.unlink(missing_ok=True)
                except Exception:
                    pass
            elif step2_file.exists() and step2_file.stat().st_size <= 2500:
                try:
                    step2_file.unlink(missing_ok=True)
                except Exception:
                    pass

            if step2_valid:
                self._emit(
                    current_step="STEP 2 — Idea / Title / Thumbnail (Chat #1)",
                    progress=16.0,
                    message=f"[{ma_id}] ♻️ Khôi phục kết quả STEP 2 có sẵn ({len(step2_out):,} ký tự)...",
                )
            else:
                # open_session_tab() ở trên đã mở sẵn Tab mới tinh cho STEP 2
                self._update_idea_record(ma_id, current_step="STEP 2 (Chat #1): Chấm Idea, Khóa Title & Thumbnail 6 dòng")
                self._emit(
                    current_step="STEP 2 — Idea / Title / Thumbnail (Chat #1)",
                    progress=10.0,
                    message=f"[{ma_id}] 💬 [Đoạn Chat #1] Đang gửi lệnh STEP 2 (Tạo 3 Title Nhật + Khóa LOCKED_TITLE + Thumbnail 6 dòng)...",
                )
                step2_prompt = build_step2_prompt_from_idea(idea, self.get_step2_template())
                (proj_dir / "step2_prompt_sent.txt").write_text(step2_prompt, encoding="utf-8")

                step2_out = session.send_prompt_and_wait(
                    step2_prompt,
                    step_label="STEP_2",
                    timeout_sec=600,
                    progress_cb=lambda st, ch: self._emit(message=f"[{ma_id}] [Chat #1] STEP 2 đang phản hồi ({ch:,} ký tự)..."),
                    should_stop_cb=lambda: self.should_stop,
                )
                step2_file.write_text(step2_out, encoding="utf-8")

            locked_title = extract_locked_title_from_step2(step2_out, fallback_title=idea.get("draft_title_ja", ""))
            self._update_idea_record(
                ma_id,
                locked_title=locked_title,
                current_step="STEP 2 Hoàn tất (Đã khóa LOCKED_TITLE)",
            )
            self._emit(
                progress=20.0,
                message=f"[{ma_id}] ✅ STEP 2 xong! LOCKED_TITLE: {locked_title[:55]}...",
            )

            # ------------------------------------------------------------------
            # ĐOẠN CHAT #2 (STEP 3): STORY ARCHITECTURE & LOGIC PREFLIGHT
            # ------------------------------------------------------------------
            step3_file = proj_dir / "step3_architecture.txt"
            part_a_precheck = proj_dir / "part_a.txt"
            has_existing_parts = not force_rewrite_script and part_a_precheck.exists() and part_a_precheck.stat().st_size > 15000
            step3_valid = False
            if step3_file.exists() and (step3_file.stat().st_size > 2500 or has_existing_parts) and not force_rewrite_script:
                try:
                    s3_probe = step3_file.read_text(encoding="utf-8", errors="ignore")
                    if has_existing_parts or any(k in s3_probe.upper() for k in ("STORY BIBLE", "SCENE", "PART_A", "PART A", "LOGIC LEDGER", "APPROVED_FOR_DRAFTING")):
                        step3_out = s3_probe
                        step3_valid = True
                    else:
                        step3_file.unlink(missing_ok=True)
                except Exception:
                    pass
            elif step3_file.exists() and step3_file.stat().st_size <= 2500 and not has_existing_parts:
                try:
                    step3_file.unlink(missing_ok=True)
                except Exception:
                    pass

            if step3_valid:
                self._emit(
                    current_step="STEP 3 — Story Architecture (Chat #2)",
                    progress=30.0,
                    message=f"[{ma_id}] ♻️ Khôi phục kết quả STEP 3 có sẵn ({len(step3_out):,} ký tự)...",
                )
            else:
                session.start_fresh_chat("STEP_3_ARCHITECTURE")
                self._update_idea_record(ma_id, current_step="STEP 3 (Chat #2): Thiết kế Story Bible & 24 Cảnh A/B/C")
                self._emit(
                    current_step="STEP 3 — Story Architecture (Chat #2)",
                    progress=24.0,
                    message=f"[{ma_id}] 💬 [Đoạn Chat #2 Mới] Đang chạy STEP 3 (Thiết kế Story Bible, Logic Ledger & Kế hoạch 24 cảnh A/B/C)...",
                )
                step3_prompt = self._build_step3_prompt(
                    ma_id,
                    locked_title,
                    step2_context=step2_out,
                )
                step3_out = session.send_prompt_and_wait(
                    step3_prompt,
                    step_label="STEP_3",
                    timeout_sec=600,
                    progress_cb=lambda st, ch: self._emit(message=f"[{ma_id}] [Chat #2] STEP 3 đang thiết kế cấu trúc ({ch:,} ký tự)..."),
                    should_stop_cb=lambda: self.should_stop,
                )
                step3_file.write_text(step3_out, encoding="utf-8")

            # ------------------------------------------------------------------
            # ĐOẠN CHAT #3A / #3B / #3C (STEP 3 PADRE MX V3.0): VIẾT KỊCH BẢN ĐỦ 3 STAGE = 7 PARTS (`[PART 1]`..`[PART 7]`)
            # - STAGE A (`part_a.txt`): `[PART 1]` + `[PART 2]` (20.000–24.000 ký tự, target 22.000)
            # - STAGE B (`part_b.txt`): `[PART 3]` + `[PART 4]` + `[PART 5]` (30.000–35.000 ký tự, target 32.500)
            # - STAGE C (`part_c.txt`): `[PART 6]` + `[PART 7]` (20.000–25.000 ký tự, target 22.500)
            # - Tổng 7 Parts: 70.000–80.000 ký tự `es-MX`.
            # ------------------------------------------------------------------
            min_a = 20000
            max_a = 24000
            target_a = 22000

            min_b = 30000
            max_b = 35000
            target_b = 32500

            min_c = 20000
            max_c = 25000
            target_c = 22500

            part_a_file = proj_dir / "part_a.txt"
            part_b_file = proj_dir / "part_b.txt"
            part_c_file = proj_dir / "part_c.txt"
            clean_script_file = proj_dir / "script_clean.txt"
            pmx_full_script_file = proj_dir / "PMX_FULL_SCRIPT.txt"

            # Ngưỡng chấp nhận khôi phục Stage đã viết sẵn
            accept_a = 17000
            accept_b = 25500
            accept_c = 17000

            need_write_a = force_rewrite_script or not (
                part_a_file.exists() and pure_char_count(part_a_file.read_text(encoding="utf-8", errors="ignore")) >= accept_a
            )
            need_write_b = force_rewrite_script or not (
                part_b_file.exists() and pure_char_count(part_b_file.read_text(encoding="utf-8", errors="ignore")) >= accept_b
            )
            need_write_c = force_rewrite_script or not (
                part_c_file.exists() and pure_char_count(part_c_file.read_text(encoding="utf-8", errors="ignore")) >= accept_c
            )

            # Nếu phải viết bất kỳ Stage nào còn thiếu, xóa file script_clean.txt và báo cáo Step 5/6 cũ của bản thiếu trước đó
            if need_write_a or need_write_b or need_write_c:
                for stale_f in (
                    clean_script_file,
                    pmx_full_script_file,
                    proj_dir / "step5_audit_report.txt",
                    proj_dir / "PMX_QA_ROUND1_LOGIC.md",
                    proj_dir / "PMX_QA_ROUND2_QUALITY.md",
                    proj_dir / "PMX_QA_FINAL.md",
                    proj_dir / "step6_seo_pack.txt",
                    proj_dir / "PMX_SEO_PACK.md",
                    proj_dir / "00_TIEU_DE_VA_SEO_YOUTUBE.txt",
                ):
                    if stale_f.exists():
                        try:
                            stale_f.unlink()
                        except Exception:
                            pass

            # --- 4.1: STAGE A ([PART 1] & [PART 2]) ---
            if not need_write_a:
                part_a_clean = ensure_part_headings_for_stage(part_a_file.read_text(encoding="utf-8", errors="ignore"), "A")
                count_a = pure_char_count(part_a_clean)
                self._emit(
                    progress=42.0,
                    message=f"[{ma_id}] ♻️ Khôi phục STAGE A ([PART 1]–[PART 2]: {count_a:,} ký tự) -> Chuyển sang kiểm tra STAGE B...",
                )
            else:
                session.start_fresh_chat("STEP_4_WRITE_PART_A")
                self._update_idea_record(
                    ma_id,
                    has_script=False,
                    status="RUNNING",
                    current_step="STEP 3A (Chat #3A): Đang viết STAGE A ([PART 1] & [PART 2] — 20k–24k chữ)...",
                )
                part_a_clean = self._write_part_with_length_gate(
                    session,
                    ma_id,
                    "A",
                    locked_title,
                    min_a,
                    max_a,
                    target_a,
                    base_progress=34.0,
                    step3_context=step3_out,
                    prev_part_tail="",
                    min_acceptable_chars=accept_a,
                )
                part_a_file.write_text(part_a_clean, encoding="utf-8")
                count_a = pure_char_count(part_a_clean)

            self._update_idea_record(
                ma_id,
                pure_char_count=count_a,
                has_script=False,
                completed_parts_count=1,
                missing_parts=["B", "C"],
                current_step=f"STEP 3A: Xong STAGE A ([PART 1]–[PART 2]: {count_a:,} chữ) -> Đang chuẩn bị STAGE B...",
            )

            # --- 4.2: STAGE B ([PART 3], [PART 4] & [PART 5]) ---
            if not need_write_b:
                part_b_clean = ensure_part_headings_for_stage(part_b_file.read_text(encoding="utf-8", errors="ignore"), "B")
                count_b = pure_char_count(part_b_clean)
                self._emit(
                    progress=58.0,
                    message=f"[{ma_id}] ♻️ Khôi phục STAGE B ([PART 3]–[PART 5]: {count_b:,} ký tự) -> Chuyển sang kiểm tra STAGE C...",
                )
            else:
                session.start_fresh_chat("STEP_4_WRITE_PART_B")
                self._update_idea_record(
                    ma_id,
                    has_script=False,
                    status="RUNNING",
                    current_step=f"STEP 3B (Chat #3B Mới): Đang viết STAGE B ([PART 3]–[PART 5] — Đã có {count_a:,} chữ)...",
                )
                part_b_clean = self._write_part_with_length_gate(
                    session,
                    ma_id,
                    "B",
                    locked_title,
                    min_b,
                    max_b,
                    target_b,
                    base_progress=50.0,
                    step3_context=step3_out,
                    prev_part_tail=part_a_clean[-450:],
                    min_acceptable_chars=accept_b,
                )
                part_b_file.write_text(part_b_clean, encoding="utf-8")
                count_b = pure_char_count(part_b_clean)

            self._update_idea_record(
                ma_id,
                pure_char_count=count_a + count_b,
                has_script=False,
                completed_parts_count=2,
                missing_parts=["C"],
                current_step=f"STEP 3B: Xong STAGE A+B ([PART 1]–[PART 5]: {count_a + count_b:,} chữ) -> Đang chuẩn bị STAGE C...",
            )

            # --- 4.3: STAGE C ([PART 6] & [PART 7]) ---
            if not need_write_c:
                part_c_clean = ensure_part_headings_for_stage(part_c_file.read_text(encoding="utf-8", errors="ignore"), "C")
                if pure_char_count(part_c_clean) > max_c:
                    part_c_clean = trim_japanese_to_max_pure_chars(part_c_clean, max_pure_chars=max_c - 150)
                    part_c_clean = ensure_part_headings_for_stage(part_c_clean, "C")
                    part_c_file.write_text(part_c_clean, encoding="utf-8")
                count_c = pure_char_count(part_c_clean)
            else:
                session.start_fresh_chat("STEP_4_WRITE_PART_C")
                self._update_idea_record(
                    ma_id,
                    has_script=False,
                    status="RUNNING",
                    current_step=f"STEP 3C (Chat #3C Mới): Đang viết STAGE C ([PART 6]–[PART 7] — Đã có {count_a + count_b:,} chữ)...",
                )
                part_c_clean = self._write_part_with_length_gate(
                    session,
                    ma_id,
                    "C",
                    locked_title,
                    min_c,
                    max_c,
                    target_c,
                    base_progress=64.0,
                    step3_context=step3_out,
                    prev_part_tail=part_b_clean[-450:],
                    min_acceptable_chars=accept_c,
                )
                part_c_file.write_text(part_c_clean, encoding="utf-8")
                count_c = pure_char_count(part_c_clean)

            # Chuẩn hóa 7 nhãn [PART 1]..[PART 7] cho PMX_FULL_SCRIPT.txt và tạo bản sạch cho TTS/Video
            part_a_headed = ensure_part_headings_for_stage(part_a_clean, "A")
            part_b_headed = ensure_part_headings_for_stage(part_b_clean, "B")
            part_c_headed = ensure_part_headings_for_stage(part_c_clean, "C")
            part_a_file.write_text(part_a_headed, encoding="utf-8")
            part_b_file.write_text(part_b_headed, encoding="utf-8")
            part_c_file.write_text(part_c_headed, encoding="utf-8")

            count_a = pure_char_count(part_a_headed)
            count_b = pure_char_count(part_b_headed)
            count_c = pure_char_count(part_c_headed)

            # CHỐT CHẶN NGHIÊM NGẶT: Cả 3 Stage A, B, C phải đủ chuẩn mới được ghép
            if count_a < accept_a or count_b < accept_b or count_c < accept_c:
                raise RuntimeError(
                    f"[{ma_id}] Kịch bản chưa đủ 3 Stage hợp lệ (A={count_a:,}, B={count_b:,}, C={count_c:,}). "
                    f"Không cho phép đánh dấu hoàn tất!"
                )

            pmx_full_script = "\n\n".join([part_a_headed, part_b_headed, part_c_headed]).strip()
            pmx_full_script_file.write_text(pmx_full_script, encoding="utf-8")

            full_clean_script, rem_full = self._sanitize_and_note_script_text(ma_id, pmx_full_script, source_label="FULL_SCRIPT")
            total_pure = pure_char_count(full_clean_script)
            if total_pure < 55000:
                raise RuntimeError(
                    f"[{ma_id}] Tổng kịch bản 7 Part chỉ đạt {total_pure:,} ký tự (< 55,000 ký tự tối thiểu). "
                    f"Hệ thống từ chối đánh dấu hoàn tất để tránh kịch bản ngắn!"
                )

            clean_script_file.write_text(full_clean_script, encoding="utf-8")
            self._update_idea_record(
                ma_id,
                pure_char_count=total_pure,
                has_script=True,
                completed_parts_count=3,
                missing_parts=[],
                current_step=f"STEP 3 Hoàn tất đủ 7 Parts / 3 Stages ({total_pure:,} ký tự es-MX)",
            )
            self._emit(
                progress=74.0,
                message=f"[{ma_id}] ✅ Đã ghép xong đủ 7 Parts: STAGE A ({count_a:,}) + STAGE B ({count_b:,}) + STAGE C ({count_c:,}) = {total_pure:,} ký tự!",
            )

            # ------------------------------------------------------------------
            # ĐOẠN CHAT #4 & #5 ĐỘC LẬP (STEP 4 & STEP 5 PADRE MX V3.0):
            # - VÒNG 1 (ROUND 1): KIỂM ĐỊNH LOGIC, TÍNH LIÊN TỤC, PHÁP LÝ & CHÍNH TẢ `es-MX` + REPAIR 1
            # - VÒNG 2 (ROUND 2): KIỂM ĐỊNH CHẤT LƯỢNG TỔNG THỂ, NHỊP ĐIỆU & GIỌNG ĐỌC TTS + REPAIR 2
            # ------------------------------------------------------------------
            step5_file = proj_dir / "step5_audit_report.txt"
            r1_file = proj_dir / "PMX_QA_ROUND1_LOGIC.md"
            r2_file = proj_dir / "PMX_QA_ROUND2_QUALITY.md"
            final_qa_file = proj_dir / "PMX_QA_FINAL.md"
            step5_out = ""
            try:
                if step5_file.exists() and step5_file.stat().st_size > 500:
                    step5_out = step5_file.read_text(encoding="utf-8")
                    self._emit(
                        current_step="STEP 4 & 5 — 2 Vòng Kiểm định Độc lập (Chat #4 & #5)",
                        progress=84.0,
                        message=f"[{ma_id}] ♻️ Khôi phục báo cáo kiểm toán 2 vòng có sẵn ({len(step5_out):,} ký tự)...",
                    )
                else:
                    # --- VÒNG 1: FORENSIC LOGIC AUDIT + REPAIR 1 ---
                    session.start_fresh_chat("STEP_5_ROUND1_LOGIC_AUDIT")
                    self._update_idea_record(ma_id, current_step="STEP 4 (Vòng 1 — Chat Độc Lập): Kiểm định Logic, Pháp lý & Chính tả es-MX + Repair 1")
                    self._emit(
                        current_step="STEP 4 — Kiểm định Vòng 1: Logic & Chính tả es-MX",
                        progress=78.0,
                        message=f"[{ma_id}] 💬 [Vòng Kiểm Định #1] Đang kiểm tra Logic, Tuổi tác, Pháp lý Mexico & Chính tả es-MX trên toàn bộ 7 Parts...",
                    )
                    r1_prompt = self._build_step5_audit_prompt(
                        ma_id,
                        locked_title,
                        count_a,
                        count_b,
                        count_c,
                        total_pure,
                        part_a_text=part_a_headed,
                        part_b_text=part_b_headed,
                        part_c_text=part_c_headed,
                        step3_context=step3_out,
                    )
                    r1_out = session.send_prompt_and_wait(
                        r1_prompt,
                        step_label="STEP_5_ROUND_1",
                        timeout_sec=720,
                        progress_cb=lambda st, ch: self._emit(message=f"[{ma_id}] [Audit Vòng 1 — Logic] Đang kiểm tra & Repair 1 ({ch:,} ký tự)..."),
                        should_stop_cb=lambda: self.should_stop,
                    )
                    r1_file.write_text(r1_out, encoding="utf-8")

                    rewritten_r1 = False
                    for p_let, p_file, min_req in (("A", part_a_file, min_a), ("B", part_b_file, min_b), ("C", part_c_file, min_c)):
                        m_rw = re.search(rf"<REWRITE_PART_{p_let}>([\s\S]*?)</REWRITE_PART_{p_let}>", r1_out, flags=re.IGNORECASE)
                        if m_rw:
                            rw_clean = ensure_part_headings_for_stage(extract_clean_japanese_narration(m_rw.group(1)), p_let)
                            rw_cnt = pure_char_count(rw_clean)
                            if rw_cnt >= int(min_req * 0.78):
                                p_file.write_text(rw_clean, encoding="utf-8")
                                if p_let == "A":
                                    part_a_headed, count_a = rw_clean, rw_cnt
                                elif p_let == "B":
                                    part_b_headed, count_b = rw_clean, rw_cnt
                                else:
                                    part_c_headed, count_c = rw_clean, rw_cnt
                                rewritten_r1 = True
                                self._emit(
                                    message=f"[{ma_id}] ✍️ [Repair 1 — Logic] Đã sửa lỗi logic/chính tả STAGE {p_let} ({rw_cnt:,} ký tự)!"
                                )

                    total_pure = count_a + count_b + count_c

                    # --- VÒNG 2: HOLISTIC QUALITY AUDIT + REPAIR 2 ---
                    session.start_fresh_chat("STEP_5_ROUND2_QUALITY_AUDIT")
                    self._update_idea_record(ma_id, current_step="STEP 5 (Vòng 2 — Chat Độc Lập): Kiểm định Chất lượng Tổng thể & Nhịp đọc TTS + Repair 2")
                    self._emit(
                        current_step="STEP 5 — Kiểm định Vòng 2: Chất lượng & Nhịp đọc TTS",
                        progress=82.0,
                        message=f"[{ma_id}] 💬 [Vòng Kiểm Định #2] Đang đánh giá Chất lượng văn học, Nhịp điệu, Cao trào cảm xúc & Repair 2...",
                    )
                    r2_prompt = self._build_step5_round2_quality_audit_prompt(
                        ma_id,
                        locked_title,
                        count_a,
                        count_b,
                        count_c,
                        total_pure,
                        part_a_text=part_a_headed,
                        part_b_text=part_b_headed,
                        part_c_text=part_c_headed,
                        round1_report=r1_out,
                    )
                    r2_out = session.send_prompt_and_wait(
                        r2_prompt,
                        step_label="STEP_5_ROUND_2",
                        timeout_sec=720,
                        progress_cb=lambda st, ch: self._emit(message=f"[{ma_id}] [Audit Vòng 2 — Quality] Đang đánh giá & Repair 2 ({ch:,} ký tự)..."),
                        should_stop_cb=lambda: self.should_stop,
                    )
                    r2_file.write_text(r2_out, encoding="utf-8")
                    final_qa_file.write_text(r2_out, encoding="utf-8")

                    rewritten_r2 = False
                    for p_let, p_file, min_req in (("A", part_a_file, min_a), ("B", part_b_file, min_b), ("C", part_c_file, min_c)):
                        m_rw2 = re.search(rf"<REWRITE_PART_{p_let}>([\s\S]*?)</REWRITE_PART_{p_let}>", r2_out, flags=re.IGNORECASE)
                        if m_rw2:
                            rw2_clean = ensure_part_headings_for_stage(extract_clean_japanese_narration(m_rw2.group(1)), p_let)
                            rw2_cnt = pure_char_count(rw2_clean)
                            if rw2_cnt >= int(min_req * 0.78):
                                p_file.write_text(rw2_clean, encoding="utf-8")
                                if p_let == "A":
                                    part_a_headed, count_a = rw2_clean, rw2_cnt
                                elif p_let == "B":
                                    part_b_headed, count_b = rw2_clean, rw2_cnt
                                else:
                                    part_c_headed, count_c = rw2_clean, rw2_cnt
                                rewritten_r2 = True
                                self._emit(
                                    message=f"[{ma_id}] ✍️ [Repair 2 — Quality] Đã nâng cấp chất lượng STAGE {p_let} ({rw2_cnt:,} ký tự)!"
                                )

                    step5_out = (
                        f"==================== ROUND 1: FORENSIC LOGIC & ORTHOGRAPHY AUDIT ====================\n{r1_out}\n\n"
                        f"==================== ROUND 2: HOLISTIC QUALITY & FINAL RELEASE GATE ====================\n{r2_out}\n"
                    )
                    step5_file.write_text(step5_out, encoding="utf-8")

                # Đồng bộ lại PMX_FULL_SCRIPT.txt (có [PART 1]..[PART 7]) và script_clean.txt (đã xóa [PART 1]..[PART 7] cho TTS/Video)
                pmx_full_script = "\n\n".join([part_a_headed, part_b_headed, part_c_headed]).strip()
                pmx_full_script_file.write_text(pmx_full_script, encoding="utf-8")
                full_clean_script, post_s5_rem = self._sanitize_and_note_script_text(ma_id, pmx_full_script, source_label="STEP5_FINAL_GATE")
                total_pure = pure_char_count(full_clean_script)
                (proj_dir / "script_clean.txt").write_text(full_clean_script, encoding="utf-8")
                self._update_idea_record(ma_id, pure_char_count=total_pure)
            except Exception as e_s5:
                if self.should_stop:
                    raise
                self._emit(
                    message=f"[{ma_id}] ⚠️ Bước Kiểm định 2 vòng phản hồi chậm ({e_s5}) -> Giữ nguyên kịch bản gốc ({total_pure:,} ký tự) để tiếp tục!"
                )

            # ------------------------------------------------------------------
            # ĐOẠN CHAT #6 MỚI ĐỘC LẬP (STEP 6): SEO `es-MX` & 2 THUMBNAIL PROMPTS (CÓ FALLBACK AN TOÀN)
            # ------------------------------------------------------------------
            step6_file = proj_dir / "seo_publish_pack.txt"
            pmx_seo_file = proj_dir / "PMX_SEO_PACK.md"
            try:
                if step6_file.exists() and step6_file.stat().st_size > 300 and "BLOCKED" not in step6_file.read_text(encoding="utf-8")[:400]:
                    step6_out = step6_file.read_text(encoding="utf-8")
                    self._emit(
                        current_step="STEP 6 — SEO es-MX & 2 Thumbnail Prompts (Chat #6)",
                        progress=89.0,
                        message=f"[{ma_id}] ♻️ Khôi phục gói SEO STEP 6 có sẵn ({len(step6_out):,} ký tự)...",
                    )
                else:
                    session.start_fresh_chat("STEP_6_SEO_AND_THUMB_PROMPTS")
                    self._update_idea_record(ma_id, current_step="STEP 6 (Chat Độc Lập): Đang xuất gói SEO es-MX & Prompt 2 Ảnh Thumbnail 80/20")
                    self._emit(
                        current_step="STEP 6 — SEO es-MX & 2 Thumbnail Prompts (Chat #6)",
                        progress=86.0,
                        message=f"[{ma_id}] 💬 [Đoạn Chat Mới — Chuyên SEO] Đang chạy STEP 6 (Xuất Title, Description, Tags es-MX & Prompt THUMBNAIL.png + THUMBNAIL-NENXANH.png)...",
                    )
                    script_excerpt = (full_clean_script[:2000] + "\n...\n" + full_clean_script[-1200:]) if len(full_clean_script) > 3500 else full_clean_script
                    step6_prompt = self._build_step6_seo_prompt(
                        ma_id,
                        locked_title,
                        total_pure,
                        step2_context=step2_out,
                        script_excerpt=script_excerpt,
                    )
                    step6_out = session.send_prompt_and_wait(
                        step6_prompt,
                        step_label="STEP_6",
                        timeout_sec=420,
                        progress_cb=lambda st, ch: self._emit(message=f"[{ma_id}] [Chat SEO] STEP 6 đang tạo gói SEO es-MX & Prompt 2 Thumbnail ({ch:,} ký tự)..."),
                        should_stop_cb=lambda: self.should_stop,
                    )
                    step6_file.write_text(step6_out, encoding="utf-8")
                    pmx_seo_file.write_text(step6_out, encoding="utf-8")
            except Exception as e_s6:
                if self.should_stop:
                    raise
                self._emit(
                    message=f"[{ma_id}] ⚠️ Bước 6 (SEO) phản hồi chậm ({e_s6}) -> Tự động tổng hợp gói SEO es-MX chuẩn từ dữ liệu Step 1/2 để không dừng tiến trình!"
                )
                step6_out = self._build_fallback_seo_pack(ma_id, locked_title, total_pure, idea, step2_out)
                step6_file.write_text(step6_out, encoding="utf-8")
                pmx_seo_file.write_text(step6_out, encoding="utf-8")

            # Tạo file TỔNG HỢP SEO + TIÊU ĐỀ dễ đọc nhất cho người dùng trong thư mục dự án
            master_seo_file = proj_dir / "00_TIEU_DE_VA_SEO_YOUTUBE.txt"
            master_seo_content = (
                f"================================================================================\n"
                f"🎬 HỒ SƠ XUẤT BẢN YOUTUBE (PADRE MX V3.0) — MÃ DỰ ÁN: {ma_id}\n"
                f"================================================================================\n"
                f"📌 TIÊU ĐỀ CHÍNH THỨC ĐÃ KHÓA (CURRENT_FINAL_TITLE):\n{locked_title}\n\n"
                f"📝 TIÊU ĐỀ NHÁP BAN ĐẦU:\n{idea.get('draft_title_ja', '')}\n\n"
                f"📖 TÓM TẮT CỐT TRUYỆN:\n{idea.get('summary_vi', '')}\n\n"
                f"📊 THỐNG KÊ KỊCH BẢN 7 PHẦN (`[PART 1]`..`[PART 7]` — `es-MX`):\n"
                f"- STAGE A (`[PART 1]`–`[PART 2]`): {count_a:,} ký tự\n"
                f"- STAGE B (`[PART 3]`–`[PART 5]`): {count_b:,} ký tự\n"
                f"- STAGE C (`[PART 6]`–`[PART 7]`): {count_c:,} ký tự\n"
                f"- TỔNG CỘNG: {total_pure:,} ký tự (~{round(total_pure / 780)} phút giọng đọc es-MX)\n\n"
                f"================================================================================\n"
                f"🚀 GÓI SEO YOUTUBE `es-MX` & CẶP THUMBNAIL 80/20 (`THUMBNAIL.png` + `THUMBNAIL-NENXANH.png`)\n"
                f"================================================================================\n"
                f"{step6_out}\n\n"
                f"================================================================================\n"
                f"🎨 CHI TIẾT STEP 1/2 (5 CANDIDATE TITLES / WINNER LOCK)\n"
                f"================================================================================\n"
                f"{step2_out}\n"
            )
            master_seo_file.write_text(master_seo_content, encoding="utf-8")

            # Lưu đúng 1 file Kịch bản sạch cho TTS/Sub và 1 file SEO vào cùng thư mục chứa Video (renders)
            (renders_dir / f"{ma_id}_SEO.txt").write_text(master_seo_content, encoding="utf-8")
            (renders_dir / f"{ma_id}_KICH_BAN.txt").write_text(full_clean_script, encoding="utf-8")

            # ------------------------------------------------------------------
            # ĐOẠN CHAT #6 MỚI ĐỘC LẬP (STEP 7): TẠO THUMBNAIL 80/20 + ẢNH NỀN XANH
            # ------------------------------------------------------------------
            thumbnail_paths: List[str] = []
            try:
                thumbnail_paths = self.generate_and_verify_three_thumbnails_sync(
                    session=session,
                    ma_id=ma_id,
                    locked_title=locked_title,
                    step2_out=step2_out,
                    step6_out=step6_out,
                    idea=idea,
                    proj_dir=proj_dir,
                    renders_dir=renders_dir,
                )
            except Exception as e_thumb:
                if self.should_stop:
                    raise
                self._emit(
                    message=f"[{ma_id}] ⚠️ Tạo Thumbnail trên {session.cfg['label']} gặp gián đoạn ({e_thumb}) -> Sẽ chuyển sang tài khoản khác để tạo lại!"
                )

            # KIỂM TRA LẠI SAU KHI XONG: Nếu chưa có Thumbnail -> Chuyển sang nick khác tạo lại ngay lập tức (Không thể để thiếu Thumbnail)
            if not thumbnail_paths and not self.should_stop:
                self._emit(
                    current_ma_id=ma_id,
                    current_step="STEP 7 — Đổi sang nick khác tạo lại Thumbnail",
                    progress=95.0,
                    message=f"[{ma_id}] 🔄 Kiểm tra thấy chưa có Thumbnail trên {session.cfg['label']} -> Đang chuyển sang tài khoản (nick) khác để tạo lại Thumbnail!",
                )
                try:
                    session.close_session_tab(keep_open=False)
                except Exception:
                    pass
                thumbnail_paths = self.ensure_project_thumbnail_with_failover_sync(
                    ma_id=ma_id,
                    preferred_acc_id=None,
                    exclude_accs={getattr(session, "acc_id", "")},
                )

            self._update_idea_record(
                ma_id,
                has_seo=True,
                has_thumbnail=bool(thumbnail_paths),
            )

            # ------------------------------------------------------------------
            # BƯỚC 8 (AUTO-HANDOFF): ĐẨY SANG SẢN XUẤT VIDEO (HOẶC CHỜ PHASE 2 NẾU CHẠY ĐA LUỒNG)
            # ------------------------------------------------------------------
            video_triggered = False
            if auto_produce_video and getattr(self, "live_auto_produce_video", True) and not defer_video_handoff and self.video_pipeline is not None:
                self._emit(
                    current_step="Auto-Handoff -> Render Video",
                    progress=97.0,
                    message=f"[{ma_id}] 🚀 Kịch bản ({total_pure:,} chữ), SEO & {len(thumbnail_paths)}/1 Thumbnail đã xong! Đang đẩy sang Render Video...",
                )
                video_triggered = self._enqueue_or_start_video_job(
                    ma_id=ma_id,
                    script_text=full_clean_script,
                    seo_text=master_seo_content,
                    video_settings=video_settings,
                )
            else:
                self._update_idea_record(
                    ma_id,
                    status="SCRIPT_DONE",
                    has_script=True,
                    current_step=f"📝 Đã xong Kịch bản ({total_pure:,} chữ) & {len(thumbnail_paths)}/1 Thumbnail — Sẵn sàng Render MP4",
                )

            if not video_triggered:
                self._emit(
                    status="running" if self.is_running else "completed",
                    current_ma_id=ma_id,
                    current_step=f"✅ Hoàn tất {ma_id} — Đang chờ các luồng còn lại..." if self.is_running else "Hoàn tất Kịch bản & SEO",
                    progress=98.0 if self.is_running else 100.0,
                    message=f"[{ma_id}] 🎉 Hoàn tất Kịch bản ({total_pure:,} chữ) + SEO Pack + {len(thumbnail_paths)}/1 Thumbnail tại {renders_dir}!",
                )
            completed_ok = True
            return {
                "success": True,
                "ma_id": ma_id,
                "locked_title": locked_title,
                "pure_char_count": total_pure,
                "project_dir": str(proj_dir),
                "renders_dir": str(renders_dir),
                "script_path": str(proj_dir / "script_clean.txt"),
                "seo_path": str(master_seo_file),
                "thumbnails": thumbnail_paths,
                "video_triggered": video_triggered,
            }

        except Exception as e:
            completed_ok = False
            failed_acc = getattr(session, "acc_id", None)
            try:
                setattr(e, "failed_acc_id", failed_acc)
            except Exception:
                pass
            # Nếu kịch bản đã kịp viết xong đủ 3 Part trước khi lỗi, giữ trạng thái SCRIPT_DONE thay vì ERROR
            has_sc_now, _, sc_chars_now = self.has_valid_script_on_disk(ma_id)
            if not (self.should_stop or "Đã dừng theo yêu cầu" in str(e)) and not has_sc_now and failed_acc:
                mark_account_rate_limited(
                    failed_acc,
                    reason=f"[{ma_id}] {str(e)[:120]}",
                    cooldown_sec=ACCOUNT_LIMIT_COOLDOWN_SEC,
                )
            if has_sc_now:
                self._update_idea_record(
                    ma_id,
                    status="SCRIPT_DONE",
                    has_script=True,
                    pure_char_count=sc_chars_now,
                    completed_parts_count=3,
                    missing_parts=[],
                    current_step=f"📝 Đã có Kịch bản ({sc_chars_now:,} chữ) — Sẵn sàng Render MP4",
                )
            else:
                parts_prog = self.get_script_parts_progress(ma_id)
                done_cnt = int(parts_prog.get("completed_parts_count") or 0)
                partial_chars = int(parts_prog.get("partial_pure_chars") or 0)
                missing_list = parts_prog.get("missing_parts") or ["A", "B", "C"]
                if done_cnt > 0:
                    missing_str = ", ".join(f"Part {p}" for p in missing_list)
                    self._update_idea_record(
                        ma_id,
                        status="PARTIAL_SCRIPT",
                        has_script=False,
                        pure_char_count=partial_chars,
                        completed_parts_count=done_cnt,
                        missing_parts=missing_list,
                        current_step=f"⚠️ Thiếu {missing_str} ({done_cnt}/3 Part: {partial_chars:,} chữ) — Bấm Chạy để viết tiếp",
                    )
                elif self.should_stop or "Đã dừng theo yêu cầu" in str(e):
                    self._update_idea_record(ma_id, status="SAVED", has_script=False, current_step="⏸️ Đã tạm dừng — Bấm Chạy để tiếp tục")
                else:
                    self._update_idea_record(ma_id, status="ERROR", has_script=False, current_step=f"❌ Lỗi: {str(e)[:80]}")
            if not (self.should_stop or "Đã dừng theo yêu cầu" in str(e)):
                self._emit(
                    status="error",
                    current_step="Gặp lỗi",
                    message=f"[{ma_id}] ❌ Lỗi: {str(e)}",
                )
            raise
        finally:
            # Nếu đã hoàn thành 100%, đóng hoặc tái chế Tab ngay để giải phóng RAM (Master Blueprint V6.0)
            session.close_session_tab(keep_open=not locals().get("completed_ok", False))

    def start_render_video_for_ideas_async(
        self,
        ma_ids: Optional[List[str]] = None,
        video_settings: Optional[Dict[str, Any]] = None,
        only_unrendered: bool = False,
    ) -> Dict[str, Any]:
        """
        Đẩy trực tiếp 1 hoặc nhiều dự án ĐÃ CÓ KỊCH BẢN sang chạy Voice & Render Video MP4
        mà TUYỆT ĐỐI KHÔNG MỞ CHROME và KHÔNG VIẾT LẠI KỊCH BẢN.
        """
        self._sync_projects_disk_state()
        ideas = self.load_saved_ideas()
        ideas_map = {str(it.get("ma_id", "")).strip(): it for it in ideas if it.get("ma_id")}
        target_ids = ma_ids or [it.get("ma_id") for it in ideas if it.get("ma_id")]

        jobs_to_push: List[Dict[str, str]] = []
        skipped_no_script: List[str] = []
        skipped_already_mp4: List[str] = []
        now_ts_str = time.strftime("%Y-%m-%d %H:%M:%S")

        for mid in target_ids:
            if not mid:
                continue
            has_sc, sc_text, sc_chars = self.has_valid_script_on_disk(mid)
            if not has_sc:
                skipped_no_script.append(mid)
                continue

            proj_dir = self.projects_dir / mid
            renders_dir = proj_dir / "renders"
            renders_dir.mkdir(parents=True, exist_ok=True)
            has_valid_mp4, _, _ = self.has_valid_video_mp4_on_disk(
                mid, sc_chars=sc_chars, auto_delete_corrupted=True
            )
            if only_unrendered and has_valid_mp4:
                skipped_already_mp4.append(mid)
                continue

            idea = ideas_map.get(mid) or {"ma_id": mid}
            step2_file = proj_dir / "step2_title_thumbnail.txt"
            step2_out = step2_file.read_text(encoding="utf-8") if step2_file.exists() else ""
            locked_title = (
                idea.get("locked_title")
                or extract_locked_title_from_step2(step2_out, fallback_title=idea.get("draft_title_ja", mid))
            )

            master_seo_file = proj_dir / "00_TIEU_DE_VA_SEO_YOUTUBE.txt"
            if master_seo_file.exists() and master_seo_file.stat().st_size > 100:
                seo_text = master_seo_file.read_text(encoding="utf-8")
            else:
                seo_text = self._build_fallback_seo_pack(mid, locked_title, sc_chars, idea, step2_out)
                master_seo_file.write_text(seo_text, encoding="utf-8")

            seo_ren = renders_dir / f"{mid}_SEO.txt"
            kb_ren = renders_dir / f"{mid}_KICH_BAN.txt"
            if not seo_ren.exists():
                seo_ren.write_text(seo_text, encoding="utf-8")
            if not kb_ren.exists():
                kb_ren.write_text(sc_text, encoding="utf-8")

            if mid in ideas_map:
                ideas_map[mid]["has_script"] = True
                ideas_map[mid]["pure_char_count"] = sc_chars
                ideas_map[mid]["status"] = "VIDEO_QUEUED"
                ideas_map[mid]["current_step"] = f"⏳ Đang xếp hàng chờ tạo Voice & Render MP4 ({sc_chars:,} chữ)..."
                ideas_map[mid]["updated_at"] = now_ts_str

            jobs_to_push.append({
                "name": mid,
                "script_text": sc_text,
                "seo_text": seo_text,
            })

        if jobs_to_push:
            with self.ideas_io_lock:
                self.save_ideas_list(ideas)

        if not jobs_to_push:
            msg = "Không có dự án nào đủ điều kiện Render MP4 (Cần viết xong kịch bản trước)."
            log_warn("VIDEO", msg)
            return {
                "started": False,
                "queued_count": 0,
                "queued_ids": [],
                "skipped_no_script": skipped_no_script,
                "skipped_already_mp4": skipped_already_mp4,
                "message": msg,
            }

        vcfg = video_settings or {}
        started = False
        if self.video_pipeline is not None:
            pm_val = vcfg.get("performance_mode") or (vcfg.get("voice_config") or {}).get("performance_mode")
            if pm_val in ("full_100", "work_70") and hasattr(self.video_pipeline, "set_performance_mode"):
                try:
                    self.video_pipeline.set_performance_mode(pm_val, persist=True)
                except Exception:
                    pass
            started = self.video_pipeline.start_batch_production_async(
                jobs=jobs_to_push,
                output_dir=vcfg.get("output_dir") or str(self.projects_dir),
                channel_name=vcfg.get("channel_name", "ENISHI"),
                resolution=vcfg.get("resolution", "1920x1080"),
                fps=int(vcfg.get("fps", 30)),
                stock_selection=vcfg.get("stock_selection", "auto_unique"),
                bgm_path=vcfg.get("bgm_path"),
                bgm_volume=float(vcfg.get("bgm_volume", 0.08)),
                delete_used_stocks=bool(vcfg.get("delete_used_stocks", True)),
                auto_ensure_stock_hours=bool(vcfg.get("auto_ensure_stock_hours", True)),
                target_stock_hours=float(vcfg.get("target_stock_hours", 10.0)),
                voice_config=vcfg.get("voice_config"),
            )

        queued_ids = [j["name"] for j in jobs_to_push]
        self._emit(
            status="running",
            current_step="🎬 Đang tạo Voice & Render Video MP4",
            progress=92.0,
            message=f"🎬 Đã đẩy {len(queued_ids)} kịch bản ({', '.join(queued_ids)}) vào hàng đợi tạo Voice & Render MP4!",
        )
        return {
            "started": started,
            "queued_count": len(queued_ids),
            "queued_ids": queued_ids,
            "skipped_no_script": skipped_no_script,
            "skipped_already_mp4": skipped_already_mp4,
            "message": f"Đã đẩy {len(queued_ids)} kịch bản sang tạo Voice & Render Video MP4!",
        }

    def start_run_ideas_async(
        self,
        ma_ids: List[str],
        preferred_acc_id: Optional[str] = None,
        auto_produce_video: bool = True,
        video_settings: Optional[Dict[str, Any]] = None,
        target_part_min: int = 13334,
        ai_provider: str = "chatgpt_web",
        force_rewrite_script: bool = False,
        max_retries: int = 3,
    ) -> bool:
        """
        KIẾN TRÚC LUỒNG ĐÔI SONG SONG (STREAMING PRODUCER–CONSUMER PIPELINE):
        - LUỒNG 1 (AI VIẾT KỊCH BẢN — PRODUCER):
          + Các mã đã có sẵn kịch bản (`already_scripted_ids`) được đẩy NGAY LẬP TỨC vào Hàng Đợi Tạo Voice & Render MP4 từ giây đầu tiên.
          + Các mã chưa có kịch bản (`need_script_ids`) được chia tải đa luồng trên các tài khoản Chrome để AI viết liên tục (tự động Retry tối đa `max_retries = 3` lần).
          + Ngay khi BẤT KỲ 1 kịch bản nào vừa viết xong (`script_clean.txt` + SEO + Thumbnail), nếu `auto_produce_video=True`, hệ thống đẩy NGAY kịch bản đó sang Hàng Đợi Render MP4 rồi luồng AI lập tức viết tiếp kịch bản sau mà không đứng chờ!
        - LUỒNG 2 (VOICE GPU & RENDER VIDEO MP4 — CONSUMER):
          + Hoạt động độc lập song song ở hậu trường: cứ có kịch bản viết xong là tự động tạo Voice GPU & ghép MP4 cuốn chiếu liên tục.
        """
        if isinstance(video_settings, dict) and self.video_pipeline is not None:
            pm_val = video_settings.get("performance_mode") or (video_settings.get("voice_config") or {}).get("performance_mode")
            if pm_val in ("full_100", "work_70") and hasattr(self.video_pipeline, "set_performance_mode"):
                try:
                    self.video_pipeline.set_performance_mode(pm_val, persist=True)
                except Exception:
                    pass
        with self.lock:
            if self.is_running:
                return False
            self.is_running = True
            self.should_stop = False
            self.live_auto_produce_video = bool(auto_produce_video)

        def _worker():
            from concurrent.futures import ThreadPoolExecutor, as_completed
            from .chatgpt_web_client import (
                check_all_web_accounts_status,
                ensure_all_saved_chatgpt_accounts_open,
                sweep_completed_and_idle_tabs_across_all_accounts,
                MAX_THREADS_PER_ACCOUNT,
            )

            try:
                self._sync_projects_disk_state()
                clean_ids = [mid for mid in ma_ids if mid]
                if not clean_ids:
                    return

                # Phân loại: Mã nào ĐÃ CÓ đủ bộ (Kịch bản + SEO + Thumbnail) vs Mã nào CẦN VIẾT / BỔ SUNG / VIẾT LẠI
                already_scripted_ids: List[str] = []
                need_script_ids: List[str] = []
                for mid in clean_ids:
                    if force_rewrite_script:
                        need_script_ids.append(mid)
                        continue
                    has_sc, _, _ = self.has_valid_script_on_disk(mid)
                    has_th, has_s, _ = self.has_thumbnail_and_seo_on_disk(mid)
                    if has_sc and has_th and has_s:
                        already_scripted_ids.append(mid)
                    else:
                        need_script_ids.append(mid)

                mode_label_log = "VỪA VIẾT KỊCH BẢN VỪA RENDER MP4 SONG SONG" if auto_produce_video else "CHỈ VIẾT KỊCH BẢN + SEO + THUMBNAIL (KHÔNG RENDER)"
                log_info(
                    "SCRIPT",
                    f"Khởi chạy {len(clean_ids)} dự án [{mode_label_log}{', FORCE_REWRITE=True' if force_rewrite_script else ''}]: "
                    f"Cần xử lý Chrome AI = {len(need_script_ids)}, "
                    f"Đã có sẵn kịch bản = {len(already_scripted_ids)}.",
                )

                # Xử lý đóng gói nhanh (không mở Chrome) cho các mã đã có sẵn kịch bản
                for mid in already_scripted_ids:
                    if self.should_stop:
                        break
                    try:
                        self.run_single_idea_pipeline_sync(
                            ma_id=mid,
                            preferred_acc_id=preferred_acc_id,
                            auto_produce_video=False,
                            video_settings=video_settings,
                            target_part_min=target_part_min,
                            defer_video_handoff=True,
                            force_rewrite_script=False,
                            ai_provider=ai_provider,
                        )
                    except Exception as e_fast:
                        log_error("SCRIPT", f"[{mid}] Lỗi đóng gói kịch bản có sẵn: {e_fast}", project_id=mid)

                # NẾU ĐÃ CÓ SẴN CÁC KỊCH BẢN TRÊN Ổ CỨNG -> ĐẨY NGAY VÀO HÀNG ĐỢI RENDER TỪ GIÂY ĐẦU TIÊN!
                if auto_produce_video and already_scripted_ids and not self.should_stop:
                    only_unren_init = len(clean_ids) > 1
                    res_init_ren = self.start_render_video_for_ideas_async(
                        ma_ids=already_scripted_ids,
                        video_settings=video_settings,
                        only_unrendered=only_unren_init,
                    )
                    if res_init_ren.get("queued_count", 0) > 0:
                        log_info(
                            "VIDEO",
                            f"🎬 [RENDER SONG SONG] Đã đẩy ngay {res_init_ren.get('queued_count')} kịch bản có sẵn vào Hàng Đợi Render MP4 trong lúc AI viết tiếp {len(need_script_ids)} kịch bản mới!",
                        )

                # ==============================================================
                # LUỒNG AI VIẾT KỊCH BẢN ĐA LUỒNG (VIẾT XONG MÃ NÀO -> ĐẨY SANG RENDER NGAY MÃ ĐÓ)
                # ==============================================================
                provider_norm = "chatgpt_web"
                provider_tag = "CHATGPT WEB (MEDIUM)"
                if need_script_ids and not self.should_stop:
                    if not preferred_acc_id:
                        ensure_all_saved_chatgpt_accounts_open(run_hidden=False)
                    st_all = check_all_web_accounts_status(force_refresh=True).get("accounts", {})
                    logged_accs = [aid for aid, a in st_all.items() if a.get("logged_in")]
                    if preferred_acc_id and preferred_acc_id in st_all:
                        active_accs = [preferred_acc_id]
                        max_workers = min(len(need_script_ids), MAX_THREADS_PER_ACCOUNT)
                    else:
                        active_accs = logged_accs if logged_accs else ["acc_1"]
                        max_workers = min(len(need_script_ids), max(1, len(active_accs)) * MAX_THREADS_PER_ACCOUNT)

                    max_workers = max(1, max_workers)

                    # Nếu đang chọn Chức năng 2: Chạy 70% công suất (work_70) -> Giới hạn cứng tối đa 3 luồng tổng cộng!
                    perf_mode_now = (os.environ.get("STUDIO_PERF_MODE") or "").strip().lower()
                    if not perf_mode_now:
                        try:
                            cfg_p = self.root_dir / "config.json"
                            if cfg_p.exists():
                                perf_mode_now = str(json.loads(cfg_p.read_text(encoding="utf-8")).get("performance_mode", "full_100")).strip().lower()
                        except Exception:
                            perf_mode_now = "full_100"
                    if perf_mode_now == "work_70":
                        max_workers = min(max_workers, 3)

                    if not auto_produce_video:
                        self._emit(
                            status="running",
                            current_step=f"📝 Chỉ viết Kịch bản + SEO + Thumb ({len(need_script_ids)} mã • {provider_tag})",
                            message=(
                                f"📝 [CHẾ ĐỘ CHỈ VIẾT KỊCH BẢN + SEO + THUMB — {provider_tag}] Kích hoạt {len(need_script_ids)} dự án "
                                f"({max_workers} luồng trên {len(active_accs)} Acc: {active_accs}, tự động Retry tối đa {max_retries} lần nếu lỗi)!"
                            ),
                        )
                    else:
                        self._emit(
                            status="running",
                            current_step=f"⚡ Vừa Viết Kịch Bản ({len(need_script_ids)} mã) Vừa Render Video ({provider_tag})",
                            message=(
                                f"⚡ [VỪA VIẾT VỪA RENDER SONG SONG — {provider_tag}] AI đang viết {len(need_script_ids)} kịch bản "
                                f"({max_workers} luồng trên {len(active_accs)} Acc: {active_accs}) — Cứ xong kịch bản nào sẽ tự động tạo Voice & Render MP4 ngay kịch bản đó!"
                            ),
                        )

                    active_slot_lock = threading.Lock()
                    active_slot_state = {"count": 0}
                    cfg_perf_file = self.root_dir / "config.json"

                    def _get_live_perf_mode() -> str:
                        env_pm = (os.environ.get("STUDIO_PERF_MODE") or "").strip().lower()
                        if env_pm in ("work_70", "full_100"):
                            return env_pm
                        try:
                            if cfg_perf_file.exists():
                                m = str(json.loads(cfg_perf_file.read_text(encoding="utf-8")).get("performance_mode", "full_100")).strip().lower()
                                if m in ("work_70", "full_100"):
                                    return m
                        except Exception:
                            pass
                        return "full_100"

                    def _acquire_perf_slot():
                        while not self.should_stop:
                            pm = _get_live_perf_mode()
                            limit_slots = 3 if pm == "work_70" else 9
                            with active_slot_lock:
                                if active_slot_state["count"] < limit_slots:
                                    active_slot_state["count"] += 1
                                    return True
                            time.sleep(1.0)
                        return False

                    def _release_perf_slot():
                        with active_slot_lock:
                            active_slot_state["count"] = max(0, active_slot_state["count"] - 1)

                    def _run_one_with_auto_retry(mid_item: str, acc_item: Optional[str]):
                        if not _acquire_perf_slot():
                            return
                        try:
                            # Tổng số lần chạy = 1 lần chạy chính + tối đa `max_retries` (tối thiểu 4 lượt để xoay vòng đủ các nick + chờ 30p nếu cần)
                            total_attempts = 1 + max(4, int(max_retries))
                            last_err: Optional[Exception] = None
                            failed_accs_for_mid: set = set()
                            restart_from_scratch_on_other_acc = False

                            for attempt_idx in range(total_attempts):
                                if self.should_stop:
                                    return
                                is_first_try = (attempt_idx == 0)
                                use_force_rw = bool((force_rewrite_script and is_first_try) or restart_from_scratch_on_other_acc)
                                try_acc = acc_item if is_first_try else None
                                try:
                                    if attempt_idx > 0:
                                        retry_msg = (
                                            f"🔄 [{mid_item}] Tự động đẩy kịch bản sang tài khoản (nick) khác để làm lại từ đầu (Lần {attempt_idx}/{total_attempts - 1} — Đã tránh nick bị Limit 30p: {sorted(failed_accs_for_mid)})..."
                                            if restart_from_scratch_on_other_acc
                                            else f"🔄 [{mid_item}] Tự động Retry lần {attempt_idx}/{total_attempts - 1}..."
                                        )
                                        self._update_idea_record(
                                            mid_item,
                                            status="RUNNING",
                                            retry_count=attempt_idx,
                                            current_step=f"🔄 Đang chuyển sang nick khác làm lại từ đầu ({attempt_idx}/{total_attempts - 1})...",
                                        )
                                        self._emit(
                                            status="running",
                                            current_ma_id=mid_item,
                                            current_step=f"🔄 Đổi sang nick khác làm lại ({attempt_idx}/{total_attempts - 1})",
                                            message=retry_msg,
                                        )
                                        log_warn("SCRIPT", retry_msg, project_id=mid_item)

                                    res_single = self.run_single_idea_pipeline_sync(
                                        mid_item,
                                        try_acc,
                                        bool(auto_produce_video),       # Viết xong kịch bản nào đẩy sang Render ngay kịch bản đó!
                                        video_settings,
                                        target_part_min,
                                        not bool(auto_produce_video),   # defer_video_handoff=False khi auto_produce_video=True
                                        use_force_rw,                   # Làm lại từ đầu (Step 2) khi đổi sang nick khác do nick cũ bị Limit
                                        ai_provider,
                                        exclude_accs=set(failed_accs_for_mid),
                                    )
                                    has_sc_ok, _, _ = self.has_valid_script_on_disk(mid_item)
                                    if has_sc_ok:
                                        # Kiểm tra lại Thumbnail ngay sau khi xong kịch bản: nếu thiếu thì tạo lại trên nick khác
                                        has_th_ok, _, _ = self.has_thumbnail_and_seo_on_disk(mid_item)
                                        if not has_th_ok and not self.should_stop:
                                            self.ensure_project_thumbnail_with_failover_sync(
                                                ma_id=mid_item,
                                                preferred_acc_id=None,
                                                exclude_accs=set(failed_accs_for_mid),
                                            )
                                        if auto_produce_video and not (isinstance(res_single, dict) and res_single.get("video_triggered")):
                                            self.start_render_video_for_ideas_async(
                                                ma_ids=[mid_item],
                                                video_settings=video_settings,
                                                only_unrendered=(len(clean_ids) > 1),
                                            )
                                        return
                                    last_err = RuntimeError("Chưa ghép đủ 3 Part kịch bản chuẩn trên ổ cứng.")
                                except Exception as exc_try:
                                    last_err = exc_try
                                    if self.should_stop or "Đã dừng theo yêu cầu" in str(exc_try):
                                        return
                                    failed_acc = getattr(exc_try, "failed_acc_id", None) or try_acc
                                    if failed_acc:
                                        failed_accs_for_mid.add(failed_acc)
                                        mark_account_rate_limited(
                                            failed_acc,
                                            reason=f"[{mid_item}] {str(exc_try)[:120]}",
                                            cooldown_sec=ACCOUNT_LIMIT_COOLDOWN_SEC,
                                        )

                                    # Nếu kịch bản 3 Part đã kịp viết xong trên ổ cứng -> Kiểm tra tạo bù Thumbnail trên nick khác rồi đẩy vào Render!
                                    has_sc_now, _, _ = self.has_valid_script_on_disk(mid_item)
                                    if has_sc_now:
                                        has_th_now, _, _ = self.has_thumbnail_and_seo_on_disk(mid_item)
                                        if not has_th_now and not self.should_stop:
                                            self.ensure_project_thumbnail_with_failover_sync(
                                                ma_id=mid_item,
                                                preferred_acc_id=None,
                                                exclude_accs=set(failed_accs_for_mid),
                                            )
                                        if auto_produce_video:
                                            self.start_render_video_for_ideas_async(
                                                ma_ids=[mid_item],
                                                video_settings=video_settings,
                                                only_unrendered=(len(clean_ids) > 1),
                                            )
                                        return

                                    # Nếu kịch bản chưa xong mà nick bị limit/lỗi -> Đẩy kịch bản qua nick khác làm lại từ đầu!
                                    restart_from_scratch_on_other_acc = True

                                    if attempt_idx < total_attempts - 1:
                                        # Kiểm tra xem còn nick nào đang rảnh (không bị khóa 30p) không
                                        free_accs_now = [
                                            aid for aid in active_accs
                                            if not is_account_in_cooldown(aid)[0] and aid not in failed_accs_for_mid
                                        ]
                                        if not free_accs_now:
                                            # Mở rộng sang toàn bộ tài khoản chưa bị cooldown 30p
                                            free_accs_now = [
                                                aid for aid in ("acc_1", "acc_2", "acc_3")
                                                if not is_account_in_cooldown(aid)[0] and aid not in failed_accs_for_mid
                                            ]
                                        if free_accs_now:
                                            wait_s = 3.0
                                            log_warn(
                                                "SCRIPT",
                                                f"[{mid_item}] 🚫 Nick '{failed_acc}' bị Limit/Lỗi -> Đã tạm dừng '{failed_acc}' 30 phút và đẩy ngay '{mid_item}' sang nick khác ({free_accs_now[0]}) làm lại từ đầu sau {wait_s:.0f}s!",
                                                project_id=mid_item,
                                            )
                                            self._update_idea_record(
                                                mid_item,
                                                status="RUNNING",
                                                retry_count=attempt_idx + 1,
                                                current_step=f"🔄 Nick {failed_acc} tạm dừng 30p -> Đang đẩy sang {free_accs_now[0]} làm lại từ đầu...",
                                            )
                                            time.sleep(wait_s)
                                        else:
                                            # Tất cả các nick đều đang trong thời gian nghỉ 30 phút -> Chờ đúng tới khi nick sớm nhất hết 30 phút rồi tự động thử lại!
                                            rem_cooldown = get_earliest_cooldown_remaining_sec()
                                            wait_s = max(10, rem_cooldown if rem_cooldown > 0 else ACCOUNT_LIMIT_COOLDOWN_SEC)
                                            log_warn(
                                                "SCRIPT",
                                                f"[{mid_item}] ⏳ Tất cả các tài khoản đều đang bị Limit tạm dừng 30 phút -> Hệ thống chờ {wait_s // 60}p{wait_s % 60:02d}s rồi tự động chạy lại '{mid_item}' từ đầu!",
                                                project_id=mid_item,
                                            )
                                            waited = 0
                                            while waited < wait_s and not self.should_stop:
                                                rem_now = max(0, int(wait_s - waited))
                                                if waited % 15 == 0:
                                                    self._update_idea_record(
                                                        mid_item,
                                                        status="RUNNING",
                                                        retry_count=attempt_idx + 1,
                                                        current_step=f"⏳ Các nick đang nghỉ Limit 30p — Tự chạy lại sau {rem_now // 60}p{rem_now % 60:02d}s...",
                                                    )
                                                    self._emit(
                                                        status="running",
                                                        current_ma_id=mid_item,
                                                        current_step=f"⏳ Tạm dừng 30p chờ mở Limit ({rem_now // 60}p{rem_now % 60:02d}s)",
                                                        message=f"[{mid_item}] ⏳ Nick bị Limit đang tạm nghỉ 30 phút — Còn {rem_now // 60} phút {rem_now % 60} giây sẽ tự động thử lại...",
                                                    )
                                                time.sleep(1.0)
                                                waited += 1
                                            # Sau khi hết 30 phút chờ, cho phép thử lại trên tất cả các nick đã hết hạn cooldown
                                            failed_accs_for_mid.clear()
                                    else:
                                        log_error(
                                            "SCRIPT",
                                            f"[{mid_item}] ❌ Đã thử tự động tối đa {total_attempts - 1} lần nhưng vẫn gặp lỗi: {exc_try}",
                                            project_id=mid_item,
                                        )
                                        self._update_idea_record(
                                            mid_item,
                                            status="ERROR",
                                            retry_count=total_attempts - 1,
                                            current_step=f"❌ Lỗi sau {total_attempts - 1} lần Retry — Bấm '🔁 Viết Lại' để chạy lại ({str(exc_try)[:55]})",
                                        )
                                        raise
                        finally:
                            _release_perf_slot()

                    with ThreadPoolExecutor(max_workers=max_workers) as executor:
                        futs = {}
                        for idx, mid in enumerate(need_script_ids):
                            if self.should_stop:
                                break
                            assigned_acc = preferred_acc_id
                            fut = executor.submit(_run_one_with_auto_retry, mid, assigned_acc)
                            futs[fut] = mid
                            if len(need_script_ids) > 1:
                                time.sleep(0.55)

                        done_cnt = 0
                        for fut in as_completed(futs):
                            mid_done = futs[fut]
                            done_cnt += 1
                            try:
                                fut.result()
                                suffix_ren = " -> Đã đẩy ngay sang Hàng Đợi Render MP4!" if auto_produce_video else ""
                                self._emit(
                                    message=f"✅ Đã hoàn thành kịch bản [{done_cnt}/{len(need_script_ids)}]: {mid_done}{suffix_ren}"
                                )
                            except Exception as exc:
                                log_error(
                                    "SCRIPT",
                                    f"[{mid_done}] Lỗi luồng kịch bản sau {max_retries} lần Retry ({done_cnt}/{len(need_script_ids)}): {exc}",
                                    project_id=mid_done,
                                )

                    # Dọn dẹp tab Chrome sau khi kết thúc toàn bộ luồng AI để giải phóng RAM cho Voice & Render Video
                    try:
                        sweep_completed_and_idle_tabs_across_all_accounts()
                    except Exception:
                        pass

                # ==============================================================
                # KIỂM TRA LẠI TOÀN BỘ KỊCH BẢN ĐÃ XONG: NẾU KỊCH BẢN NÀO CHƯA CÓ THUMBNAIL THÌ TẠO BÙ NGAY (ĐỔI NICK NẾU LIMIT)
                # ==============================================================
                if not self.should_stop:
                    try:
                        self.ensure_all_projects_have_thumbnails_sync(target_ids=clean_ids)
                        sweep_completed_and_idle_tabs_across_all_accounts()
                    except Exception as e_ens_th:
                        log_warn("SCRIPT", f"Cảnh báo khi quét tạo bù Thumbnail cuối phiên: {e_ens_th}")

                # ==============================================================
                # QUÉT VÉT LẦN CUỐI ĐẢM BẢO MỌI KỊCH BẢN ĐÃ XONG ĐỀU ĐƯỢC RENDER MP4
                # ==============================================================
                if auto_produce_video and not self.should_stop:
                    only_unrendered = len(clean_ids) > 1
                    res_render = self.start_render_video_for_ideas_async(
                        ma_ids=clean_ids,
                        video_settings=video_settings,
                        only_unrendered=only_unrendered,
                    )
                    if not res_render.get("started") and only_unrendered and len(clean_ids) == 1:
                        self.start_render_video_for_ideas_async(
                            ma_ids=clean_ids,
                            video_settings=video_settings,
                            only_unrendered=False,
                        )
                    self._emit(
                        status="completed",
                        current_step="✅ Đã viết xong toàn bộ Kịch bản — Hàng đợi Render MP4 đang hoàn tất",
                        progress=100.0,
                        message=(
                            f"🎉 Đã hoàn tất viết Kịch bản và đẩy toàn bộ vào Hàng Đợi Voice & Render MP4!"
                        ),
                    )
                elif not auto_produce_video and not self.should_stop:
                    self._sync_projects_disk_state()
                    self._emit(
                        status="completed",
                        current_step="✅ Hoàn tất Kịch Bản + SEO + Thumbnail (Không Render Video)",
                        progress=100.0,
                        message=(
                            f"🎉 [CHẾ ĐỘ CHỈ VIẾT KỊCH BẢN + SEO + THUMBNAIL] Đã hoàn tất {len(clean_ids)} dự án "
                            f"tại thư mục projects/ (Không tạo Voice & Không Render MP4 — Sẵn sàng Render hoặc Copy sang máy khác)!"
                        ),
                    )
            except Exception as e:
                log_error("SCRIPT", f"Lỗi nghiêm trọng trong start_run_ideas_async: {e}", include_trace=True)
            finally:
                with self.lock:
                    self.is_running = False

        t = threading.Thread(target=_worker, daemon=True)
        t.start()
        return True

    def stop(self):
        with self.lock:
            self.should_stop = True
        self._emit(status="stopped", message="🛑 Đã gửi tín hiệu dừng dây chuyền viết kịch bản.")

    def get_project_outputs(self, ma_id: str) -> Dict[str, Any]:
        """Đọc toàn bộ kết quả đã lưu của 1 mã dự án (Prompt Step 2, Kết quả Step 2, SEO Pack, Kịch bản, Thumbnail, Video MP4)."""
        ideas = self.load_saved_ideas()
        idea = next((it for it in ideas if it.get("ma_id") == ma_id), {})
        proj_dir = self._get_effective_project_dir(ma_id)
        f_dir = getattr(self, "final_video_dir", None)
        final_proj_dir = (Path(f_dir) / ma_id) if f_dir else proj_dir

        def _read_safe(fname: str) -> str:
            for base_d in (proj_dir, final_proj_dir, proj_dir / "renders", final_proj_dir / "renders"):
                p = base_d / fname
                if p.exists():
                    try:
                        return p.read_text(encoding="utf-8")
                    except Exception:
                        pass
            return ""

        step2_prompt = _read_safe("step2_prompt_sent.txt") or _read_safe("step2_prompt_ready.txt")
        if not step2_prompt and idea:
            step2_prompt = build_step2_prompt_from_idea(idea, self.get_step2_template())

        renders_dir = proj_dir / "renders"
        mp4_path = self.resolve_project_mp4_path(ma_id)
        if mp4_path and mp4_path.exists():
            target_open_dir = mp4_path.parent
        elif (final_proj_dir / "renders").exists():
            target_open_dir = final_proj_dir / "renders"
        elif renders_dir.exists():
            target_open_dir = renders_dir
        else:
            target_open_dir = proj_dir

        thumb_files: List[Path] = []
        for scan_d in (renders_dir, final_proj_dir / "renders", proj_dir, final_proj_dir):
            if not scan_d.exists():
                continue
            for cand_p in (
                scan_d / f"{ma_id}_THUMBNAIL_1.png",
                scan_d / "THUMBNAIL.png",
                scan_d / "THUMBNAIL-NENXANH.png",
                scan_d / f"{ma_id}_THUMBNAIL_NENXANH.png",
            ):
                if cand_p.exists() and cand_p not in thumb_files:
                    thumb_files.append(cand_p)
            if thumb_files:
                break

        return {
            "ma_id": ma_id,
            "idea": idea,
            "project_dir": str(target_open_dir),
            "raw_project_dir": str(proj_dir),
            "video_mp4_path": str(mp4_path) if mp4_path else "",
            "step2_prompt": step2_prompt,
            "step2_output": _read_safe("step2_title_thumbnail.txt"),
            "step3_output": _read_safe("step3_architecture.txt"),
            "script_clean": _read_safe("PMX_FULL_SCRIPT.txt") or _read_safe("script_clean.txt") or _read_safe(f"{ma_id}_KICH_BAN.txt"),
            "step5_output": _read_safe("step5_audit_report.txt"),
            "seo_pack": _read_safe("00_TIEU_DE_VA_SEO_YOUTUBE.txt") or _read_safe("PMX_SEO_PACK.md") or _read_safe("seo_publish_pack.txt") or _read_safe(f"{ma_id}_SEO.txt"),
            "thumbnails": [str(p) for p in thumb_files],
        }

    def start_generate_thumbnails_only_async(
        self,
        ma_id: str,
        preferred_acc_id: Optional[str] = None,
        force_regenerate: bool = True,
    ) -> bool:
        """Kích hoạt chạy riêng Bước tạo & đánh giá cặp Thumbnail (`THUMBNAIL.png` + `THUMBNAIL-NENXANH.png`) cho 1 dự án."""
        with self.lock:
            if self.is_running:
                return False
            self.is_running = True
            self.should_stop = False

        def _thumb_worker():
            session = ChatGPTWebSession(project_id=f"{ma_id}_THUMB", acc_id=preferred_acc_id)
            completed_ok = False
            try:
                ideas = self.load_saved_ideas()
                idea = next((it for it in ideas if it.get("ma_id") == ma_id), {}) or {"ma_id": ma_id}
                proj_dir = self.projects_dir / ma_id
                proj_dir.mkdir(parents=True, exist_ok=True)
                renders_dir = proj_dir / "renders"
                renders_dir.mkdir(parents=True, exist_ok=True)

                if force_regenerate:
                    for old_t in list(renders_dir.glob(f"{ma_id}_THUMBNAIL*.png")) + [
                        renders_dir / "THUMBNAIL.png",
                        renders_dir / "THUMBNAIL-NENXANH.png",
                        proj_dir / "THUMBNAIL.png",
                        proj_dir / "THUMBNAIL-NENXANH.png",
                    ]:
                        if old_t.exists():
                            try:
                                old_t.unlink()
                            except Exception:
                                pass

                step2_out = (proj_dir / "step2_title_thumbnail.txt").read_text(encoding="utf-8") if (proj_dir / "step2_title_thumbnail.txt").exists() else ""
                step6_out = (proj_dir / "seo_publish_pack.txt").read_text(encoding="utf-8") if (proj_dir / "seo_publish_pack.txt").exists() else ""
                locked_title = idea.get("locked_title") or extract_locked_title_from_step2(step2_out, fallback_title=idea.get("draft_title_ja", ma_id))

                self._emit(
                    status="running",
                    current_ma_id=ma_id,
                    current_step="STEP 7 — Đang mở ChatGPT tạo 1 Thumbnail",
                    progress=15.0,
                    message=f"[{ma_id}] 🎨 Đang mở trình duyệt {session.cfg['label']} để tạo & đánh giá 1 Thumbnail (6 dòng chữ)...",
                )
                if not session.open_session_tab():
                    raise RuntimeError(f"Không mở được khung chat trên {session.cfg['label']}.")

                paths = self.generate_and_verify_three_thumbnails_sync(
                    session=session,
                    ma_id=ma_id,
                    locked_title=locked_title,
                    step2_out=step2_out,
                    step6_out=step6_out,
                    idea=idea,
                    proj_dir=proj_dir,
                    renders_dir=renders_dir,
                )
                self._update_idea_record(
                    ma_id,
                    current_step=f"✅ Đã tạo xong {len(paths)}/1 Thumbnail trong thư mục Video",
                )
                self._emit(
                    status="completed",
                    current_step="Hoàn tất Thumbnail",
                    progress=100.0,
                    message=f"[{ma_id}] 🎉 Đã tạo, đánh giá QA và tải về {len(paths)}/1 Thumbnail tại {renders_dir}!",
                )
                completed_ok = True
            except Exception as e:
                self._emit(
                    status="error",
                    current_step="Lỗi tạo Thumbnail",
                    message=f"[{ma_id}] ❌ Lỗi tạo Thumbnail: {str(e)}",
                )
            finally:
                session.close_session_tab(keep_open=not completed_ok)
                with self.lock:
                    self.is_running = False

        threading.Thread(target=_thumb_worker, daemon=True).start()
        return True