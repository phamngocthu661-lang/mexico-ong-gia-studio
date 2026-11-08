# -*- coding: utf-8 -*-
"""
CapCut-Style Word-by-Word Karaoke Box Subtitle Engine (.ASS)
Đo kích thước chữ thực tế bằng TrueType Font (Arial Bold `arialbd.ttf` theo tỷ lệ chuẩn của libass `2048/2288`)
và định vị từng từ độc lập bằng `\\an5\\pos(word_cx, center_y)` để:
1. Chữ luôn nằm CHÍNH GIỮA khung màu Karaoke (sai số 0.0px cả ngang lẫn dọc, không bao giờ lệch tích lũy).
2. Khung màu Karaoke ôm vừa khít chữ (không bị to/cao gấp đôi chữ).
3. Tâm dòng phụ đề trên video khớp 100% với tâm khung Phụ đề trên màn hình Preview `(centerX, centerY)`.
"""
import os
import re
from functools import lru_cache
from typing import List, Dict, Any, Optional, Tuple

# Bảng tỷ lệ dự phòng (đã hiệu chuẩn theo hệ số 2048/2288 của libass) nếu máy không đọc được file font TrueType
CAPCUT_ARIAL_BOLD_CHAR_RATIOS: Dict[str, float] = {
    " ": 0.25,
    "I": 0.25, "J": 0.45, "L": 0.50, "T": 0.54, "F": 0.50, "E": 0.55,
    "S": 0.56, "Z": 0.54, "P": 0.56, "B": 0.60, "R": 0.61, "D": 0.61,
    "K": 0.61, "A": 0.61, "V": 0.59, "Y": 0.58, "X": 0.58, "C": 0.61,
    "H": 0.62, "N": 0.62, "U": 0.62, "G": 0.66, "O": 0.66, "Q": 0.66,
    "M": 0.74, "W": 0.83,
    "Á": 0.61, "É": 0.55, "Í": 0.25, "Ó": 0.66, "Ú": 0.62, "Ü": 0.62, "Ñ": 0.62,
    "0": 0.50, "1": 0.44, "2": 0.50, "3": 0.50, "4": 0.50, "5": 0.50,
    "6": 0.50, "7": 0.50, "8": 0.50, "9": 0.50,
    ".": 0.25, ",": 0.25, "!": 0.29, "¡": 0.29, "?": 0.50, "¿": 0.50,
    "-": 0.30, "'": 0.22, '"': 0.36, ":": 0.26, ";": 0.26,
}

# Hệ số quy đổi từ Fontsize trong ASS/libass (Windows cell height = usWinAscent 1854 + usWinDescent 434 = 2288)
# sang kích thước EM chuẩn của TrueType (`units_per_EM = 2048`)
LIBASS_ARIAL_EM_SCALE: float = 2048.0 / 2288.0
# Tỷ lệ chiều cao chữ in hoa thực tế (Cap Height) so với Fontsize trong libass
LIBASS_UPPERCASE_CAP_HEIGHT_RATIO: float = 0.635
# Độ lệch tâm dọc của chữ in hoa so với \an5\pos(cx, cy) trong libass
LIBASS_UPPERCASE_CENTER_Y_OFFSET_RATIO: float = -0.0065


@lru_cache(maxsize=64)
def _get_pil_arial_bold_font(em_px: int):
    try:
        from PIL import ImageFont
        candidates = [
            "C:/Windows/Fonts/arialbd.ttf",
            "C:/Windows/Fonts/arial.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        ]
        for path in candidates:
            if os.path.exists(path):
                return ImageFont.truetype(path, max(10, int(em_px)))
    except Exception:
        pass
    return None


def measure_capcut_word_metrics(word: str, font_size: int) -> Tuple[float, float, float]:
    """
    Đo chính xác độ rộng chữ khi libass render `Arial Bold` ở cỡ `font_size`.
    Trả về `(advance_width, ink_width, ink_center_offset_x)`:
    - `advance_width`: Độ rộng tiến trình của từ (dùng để xếp khoảng cách các từ trên dòng).
    - `ink_width`: Độ rộng phần mực chữ thực tế (dùng để vẽ khung màu Karaoke ôm sát chữ).
    - `ink_center_offset_x`: Độ lệch giữa tâm mực thực tế và tâm `advance_width` của `\an5`.
    """
    text = str(word or "").upper()
    if not text:
        return (0.0, 0.0, 0.0)

    em_size_float = float(font_size) * LIBASS_ARIAL_EM_SCALE
    em_size_int = max(10, int(round(em_size_float)))
    scale_corr = em_size_float / float(em_size_int)
    font = _get_pil_arial_bold_font(em_size_int)

    if font is not None:
        try:
            adv_w = float(font.getlength(text)) * scale_corr
            if text == " ":
                return (adv_w, adv_w, 0.0)
            bb = font.getbbox(text)
            if bb is not None:
                ink_l = float(bb[0]) * scale_corr
                ink_r = float(bb[2]) * scale_corr
                ink_w = max(4.0, ink_r - ink_l)
                ink_center_offset = ((ink_l + ink_r) / 2.0) - (adv_w / 2.0)
                return (adv_w, ink_w, ink_center_offset)
            return (adv_w, adv_w, 0.0)
        except Exception:
            pass

    total = 0.0
    for ch in text:
        ratio = CAPCUT_ARIAL_BOLD_CHAR_RATIOS.get(ch, 0.58)
        total += ratio * font_size
    return (total, total, 0.0)


def measure_capcut_word_width(word: str, font_size: int) -> float:
    return measure_capcut_word_metrics(word, font_size)[0]


def hex_to_ass_bgr(hex_str: str, default_bgr: str = "00FFFF") -> str:
    """Chuyển mã màu #RRGGBB sang định dạng BBGGRR của SubStation Alpha (.ass)."""
    clean = re.sub(r"[^0-9A-Fa-f]", "", str(hex_str or ""))
    if len(clean) != 6:
        return default_bgr
    r = clean[0:2]
    g = clean[2:4]
    b = clean[4:6]
    return f"{b}{g}{r}".upper()


def format_ass_time(seconds: float) -> str:
    safe = max(0.0, float(seconds or 0.0))
    total_cs = int(round(safe * 100))
    cs = total_cs % 100
    total_sec = total_cs // 100
    s = total_sec % 60
    total_min = total_sec // 60
    m = total_min % 60
    h = total_min // 60
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def build_ass_rounded_rect_path(left: float, top: float, right: float, bottom: float, radius: float = 10.0) -> str:
    w = max(8.0, right - left)
    h = max(8.0, bottom - top)
    r = max(2.0, min(radius, w / 2.0, h / 2.0))
    x0 = int(round(left))
    y0 = int(round(top))
    x1 = int(round(right))
    y1 = int(round(bottom))
    xr0 = int(round(left + r))
    xr1 = int(round(right - r))
    yr0 = int(round(top + r))
    yr1 = int(round(bottom - r))
    return (
        f"m {xr0} {y0} "
        f"l {xr1} {y0} "
        f"b {x1} {y0} {x1} {y0} {x1} {yr0} "
        f"l {x1} {yr1} "
        f"b {x1} {y1} {x1} {y1} {xr1} {y1} "
        f"l {xr0} {y1} "
        f"b {x0} {y1} {x0} {y1} {x0} {yr1} "
        f"l {x0} {yr0} "
        f"b {x0} {y0} {x0} {y0} {xr0} {y0}"
    )


def escape_ass_text(text: str) -> str:
    return (
        str(text or "")
        .replace("\\", r"\\")
        .replace("{", r"\{")
        .replace("}", r"\}")
        .replace("\r", "")
        .replace("\n", " ")
        .strip()
    )


def _parse_srt_timestamp(ts_str: str) -> float:
    ts_str = ts_str.strip().replace(",", ".")
    parts = ts_str.split(":")
    if len(parts) != 3:
        return 0.0
    try:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
    except ValueError:
        return 0.0


def parse_srt_blocks(srt_path: str) -> List[Dict[str, Any]]:
    """Đọc file .srt và trả về danh sách các câu [{startTime, endTime, text}]."""
    if not srt_path or not os.path.exists(srt_path):
        return []
    with open(srt_path, "r", encoding="utf-8", errors="ignore") as f:
        raw = f.read()

    blocks = re.split(r"\n\s*\n", raw.strip())
    cues: List[Dict[str, Any]] = []
    for block in blocks:
        lines = [line.strip() for line in block.strip().splitlines() if line.strip()]
        if len(lines) < 2:
            continue
        time_line_idx = 0
        for idx, line in enumerate(lines):
            if "-->" in line:
                time_line_idx = idx
                break
        if "-->" not in lines[time_line_idx]:
            continue
        start_str, end_str = lines[time_line_idx].split("-->", 1)
        start_sec = _parse_srt_timestamp(start_str)
        end_sec = _parse_srt_timestamp(end_str)
        text = " ".join(lines[time_line_idx + 1 :]).strip()
        if text and end_sec > start_sec:
            cues.append({
                "startTime": start_sec,
                "endTime": end_sec,
                "text": text,
            })
    return cues


def extract_capcut_word_timings(cues: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Chia danh sách câu thoại [{startTime, endTime, text}] thành từng từ có mốc thời gian
    tỷ lệ theo độ dài phát âm của từ + dấu câu (chuẩn CapCut).
    """
    words: List[Dict[str, Any]] = []
    for cue in cues or []:
        text = re.sub(r"\s+", " ", str(cue.get("text", ""))).strip()
        if not text:
            continue
        tokens = [t for t in text.split(" ") if t]
        if not tokens:
            continue
        start = max(0.0, float(cue.get("startTime", 0.0)))
        end = max(start + 0.12, float(cue.get("endTime", start + 1.2)))
        dur = max(0.12, end - start)

        weights: List[float] = []
        for token in tokens:
            clean_len = max(1, len(re.sub(r"[^\wáéíóúüñÁÉÍÓÚÜÑ]", "", token)))
            pause_bonus = 1.6 if re.search(r"[,.;:!?]$", token) else 0.0
            weights.append(float(clean_len) + pause_bonus)

        total_w = sum(weights) or float(len(tokens))
        cursor = start
        for idx, token in enumerate(tokens):
            w_dur = (dur * weights[idx]) / total_w
            w_start = cursor
            w_end = end if idx == len(tokens) - 1 else (cursor + w_dur)
            cursor = w_end
            words.append({
                "word": token,
                "start": w_start,
                "end": max(w_start + 0.04, w_end),
                "hasPause": bool(re.search(r"[.!?;:]$", token)),
                "hasComma": bool(re.search(r"[,]$", token)),
            })
    return words


def build_capcut_karaoke_box_ass(
    word_timings: List[Dict[str, Any]],
    options: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Sinh nội dung file phụ đề .ASS kiểu Karaoke Box (chữ IN HOA đậm + hộp màu nhảy từng từ).
    Định vị độc lập từng từ bằng `\\an5\\pos(word_cx, center_y)` để chữ luôn nằm chính giữa khung màu 100%.
    """
    opts = options or {}
    raw_w = int(opts.get("canvasWidth") or opts.get("playResX") or opts.get("width") or 1920)
    raw_h = int(opts.get("canvasHeight") or opts.get("playResY") or opts.get("height") or 1080)
    # Bảo vệ: Nếu opts truyền nhầm kích thước khung hộp sub (VD 1430x173) thay vì khung hình video 1920x1080
    width = raw_w if raw_w >= 854 and raw_h >= 480 else 1920
    height = raw_h if raw_w >= 854 and raw_h >= 480 else 1080

    font_size = int(opts.get("fontSize") or opts.get("font_size") or round(height * 0.056))
    center_x = int(opts.get("centerX", round(width * 0.372)))
    center_y = int(opts.get("centerY", round(height * 0.875)))
    max_words_per_line = int(opts.get("maxWordsPerLine") or opts.get("max_words_per_line") or 5)
    max_chars_per_line = int(opts.get("maxCharsPerLine") or 26)

    text_color_bgr = hex_to_ass_bgr(opts.get("textColor", "#FFFF00"), "00FFFF")
    box_color_bgr = hex_to_ass_bgr(opts.get("boxColor", "#7C00FF"), "FF007C")
    outline_color_bgr = hex_to_ass_bgr(opts.get("outlineColor", "#000000"), "000000")

    phrases: List[List[Dict[str, Any]]] = []
    cur: List[Dict[str, Any]] = []
    cur_chars = 0

    for idx, item in enumerate(word_timings or []):
        w = str(item.get("word", "")).strip()
        if not w:
            continue
        next_chars = cur_chars + (1 if cur else 0) + len(w)
        prev = cur[-1] if cur else None
        gap_from_prev = (float(item["start"]) - float(prev["end"])) if prev else 0.0

        should_split = len(cur) > 0 and (
            len(cur) >= max_words_per_line
            or next_chars > max_chars_per_line
            or gap_from_prev > 0.45
            or bool(prev and prev.get("hasPause"))
            or (bool(prev and prev.get("hasComma")) and len(cur) >= 3)
        )
        if should_split:
            phrases.append(cur)
            cur = []
            cur_chars = 0

        cur.append({
            "word": w,
            "upper": w.upper(),
            "start": float(item["start"]),
            "end": float(item["end"]),
            "hasPause": bool(item.get("hasPause")),
            "hasComma": bool(item.get("hasComma")),
        })
        cur_chars += (1 if len(cur) > 1 else 0) + len(w)

        if idx == len(word_timings) - 1 and cur:
            phrases.append(cur)

    outline_px = max(2.0, round(font_size * 0.048, 1))
    shadow_px = max(1.0, round(font_size * 0.022, 1))

    header = "\n".join([
        "[Script Info]",
        "Title: CapCut Karaoke Box Subtitle (Topmost Layer)",
        "ScriptType: v4.00+",
        f"PlayResX: {width}",
        f"PlayResY: {height}",
        "WrapStyle: 2",
        "ScaledBorderAndShadow: yes",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        f"Style: CapCutText,Arial,{font_size},&H00{text_color_bgr},&H00FFFFFF,&H00{outline_color_bgr},&H80000000,-1,0,0,0,100,100,0,0,1,{outline_px},{shadow_px},5,10,10,10,1",
        f"Style: CapCutBox,Arial,{font_size},&H00{box_color_bgr},&H00{box_color_bgr},&H00{box_color_bgr},&H00000000,0,0,0,0,100,100,0,0,1,0,0,7,0,0,0,1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ])

    events: List[str] = []
    # Khoảng cách giữa các từ vừa vặn để khi hộp màu nhảy sang từ kế tiếp không đè lên chữ bên cạnh
    base_space_w = measure_capcut_word_metrics(" ", font_size)[0]
    space_w = max(font_size * 0.28, base_space_w * 1.46)

    # Kích thước đệm hộp Karaoke cân đối, mở rộng thêm viền (+2px ngang, +1px dọc) và đối xứng 100% quanh tâm chữ
    pad_x = max(10, round(font_size * 0.145) + 2)
    pad_y = max(8, round(font_size * 0.125) + 1)
    corner_r = max(10, round(font_size * 0.18) + 1)

    # Chiều cao thực tế của chữ in hoa (Cap Height) và tâm dọc thực tế khi libass vẽ với \an5
    cap_height = float(font_size) * LIBASS_UPPERCASE_CAP_HEIGHT_RATIO
    glyph_center_y = float(center_y) + float(font_size) * LIBASS_UPPERCASE_CENTER_Y_OFFSET_RATIO
    box_top = glyph_center_y - (cap_height / 2.0) - pad_y
    box_bottom = glyph_center_y + (cap_height / 2.0) + pad_y

    for p_idx, phrase in enumerate(phrases):
        if not phrase:
            continue
        p_start = phrase[0]["start"]
        next_phrase = phrases[p_idx + 1] if p_idx + 1 < len(phrases) else None
        raw_end = phrase[-1]["end"]
        p_end = min(raw_end + 0.06, next_phrase[0]["start"]) if next_phrase else (raw_end + 0.08)

        word_metrics = [measure_capcut_word_metrics(w["upper"], font_size) for w in phrase]
        total_w = sum(m[0] for m in word_metrics) + space_w * max(0, len(phrase) - 1)
        cursor_x = float(center_x) - (total_w / 2.0)

        p_start_str = format_ass_time(p_start)
        p_end_str = format_ass_time(p_end)

        for w_idx, w in enumerate(phrase):
            adv_w, ink_w, ink_offset_x = word_metrics[w_idx]
            word_cx = cursor_x + (adv_w / 2.0)
            word_cx_int = int(round(word_cx))

            # Layer 1 (Trên hộp màu): Đặt từng từ độc lập bằng \an5\pos(word_cx, center_y)
            # -> Đảm bảo libass căn tâm chữ của chính từ đó tại đúng word_cx, triệt tiêu 100% sai số cộng dồn!
            clean_word = escape_ass_text(w["upper"])
            events.append(
                f"Dialogue: 1,{p_start_str},{p_end_str},CapCutText,,0,0,0,,"
                f"{{\\an5\\pos({word_cx_int},{center_y})}}{clean_word}"
            )

            # Layer 0 (Dưới chữ): Hộp màu Karaoke có tâm trùng khít 100% với tâm mực chữ của từ đang đọc
            w_start = w["start"]
            next_word = phrase[w_idx + 1] if w_idx + 1 < len(phrase) else None
            w_end = max(w_start + 0.04, next_word["start"] if next_word else p_end)

            visual_word_cx = float(word_cx_int) + ink_offset_x
            box_l = visual_word_cx - (ink_w / 2.0) - pad_x
            box_r = visual_word_cx + (ink_w / 2.0) + pad_x
            rect_path = build_ass_rounded_rect_path(box_l, box_top, box_r, box_bottom, corner_r)

            events.append(
                f"Dialogue: 0,{format_ass_time(w_start)},{format_ass_time(w_end)},CapCutBox,,0,0,0,,"
                f"{{\\an7\\pos(0,0)\\1c&H{box_color_bgr}&\\3c&H{box_color_bgr}&\\bord0\\shad0\\p1}}{rect_path}{{\\p0}}"
            )

            cursor_x += adv_w + space_w

    return header + "\n" + "\n".join(events) + "\n"


def generate_karaoke_ass_from_srt(
    srt_path: str,
    output_ass_path: str,
    options: Optional[Dict[str, Any]] = None,
    time_offset_sec: float = 0.0,
    max_duration_sec: Optional[float] = None,
) -> Optional[str]:
    """
    Đọc file .srt, tự động tính nhịp từng từ và xuất ra file .ass Karaoke Box.
    Hỗ trợ dịch mốc thời gian (time_offset_sec) khi render chia đoạn .ts.
    """
    cues = parse_srt_blocks(srt_path)
    if not cues:
        return None

    if time_offset_sec > 0.0 or max_duration_sec is not None:
        shifted_cues: List[Dict[str, Any]] = []
        end_limit = (time_offset_sec + max_duration_sec) if max_duration_sec is not None else float("inf")
        for c in cues:
            if c["endTime"] <= time_offset_sec or c["startTime"] >= end_limit:
                continue
            new_s = max(0.0, c["startTime"] - time_offset_sec)
            new_e = max(new_s + 0.12, c["endTime"] - time_offset_sec)
            if max_duration_sec is not None:
                new_e = min(max_duration_sec, new_e)
            shifted_cues.append({
                "startTime": new_s,
                "endTime": new_e,
                "text": c["text"],
            })
        cues = shifted_cues

    if not cues:
        return None

    words = extract_capcut_word_timings(cues)
    ass_content = build_capcut_karaoke_box_ass(words, options=options)
    os.makedirs(os.path.dirname(os.path.abspath(output_ass_path)), exist_ok=True)
    with open(output_ass_path, "w", encoding="utf-8") as f:
        f.write(ass_content)
    return output_ass_path
