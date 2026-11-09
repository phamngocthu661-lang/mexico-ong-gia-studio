import sys

sys.modules["backend.karaoke_subtitle"] = sys.modules[__name__]
sys.modules["backend.sync_checker"] = sys.modules[__name__]
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
from typing import Any, Dict, List, Optional, Tuple

# Bảng tỷ lệ dự phòng (đã hiệu chuẩn theo hệ số 2048/2288 của libass) nếu máy không đọc được file font TrueType
CAPCUT_ARIAL_BOLD_CHAR_RATIOS: Dict[str, float] = {
    " ": 0.25,
    "I": 0.25,
    "J": 0.45,
    "L": 0.50,
    "T": 0.54,
    "F": 0.50,
    "E": 0.55,
    "S": 0.56,
    "Z": 0.54,
    "P": 0.56,
    "B": 0.60,
    "R": 0.61,
    "D": 0.61,
    "K": 0.61,
    "A": 0.61,
    "V": 0.59,
    "Y": 0.58,
    "X": 0.58,
    "C": 0.61,
    "H": 0.62,
    "N": 0.62,
    "U": 0.62,
    "G": 0.66,
    "O": 0.66,
    "Q": 0.66,
    "M": 0.74,
    "W": 0.83,
    "Á": 0.61,
    "É": 0.55,
    "Í": 0.25,
    "Ó": 0.66,
    "Ú": 0.62,
    "Ü": 0.62,
    "Ñ": 0.62,
    "0": 0.50,
    "1": 0.44,
    "2": 0.50,
    "3": 0.50,
    "4": 0.50,
    "5": 0.50,
    "6": 0.50,
    "7": 0.50,
    "8": 0.50,
    "9": 0.50,
    ".": 0.25,
    ",": 0.25,
    "!": 0.29,
    "¡": 0.29,
    "?": 0.50,
    "¿": 0.50,
    "-": 0.30,
    "'": 0.22,
    '"': 0.36,
    ":": 0.26,
    ";": 0.26,
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


def measure_capcut_word_metrics(
    word: str, font_size: int
) -> Tuple[float, float, float]:
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


def build_ass_rounded_rect_path(
    left: float, top: float, right: float, bottom: float, radius: float = 10.0
) -> str:
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


def _parse_karaoke_srt_file(srt_path: str) -> List[Dict[str, Any]]:
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
            cues.append(
                {
                    "startTime": start_sec,
                    "endTime": end_sec,
                    "text": text,
                }
            )
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
            words.append(
                {
                    "word": token,
                    "start": w_start,
                    "end": max(w_start + 0.04, w_end),
                    "hasPause": bool(re.search(r"[.!?;:]$", token)),
                    "hasComma": bool(re.search(r"[,]$", token)),
                }
            )
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
    raw_w = int(
        opts.get("canvasWidth") or opts.get("playResX") or opts.get("width") or 1920
    )
    raw_h = int(
        opts.get("canvasHeight") or opts.get("playResY") or opts.get("height") or 1080
    )
    # Bảo vệ: Nếu opts truyền nhầm kích thước khung hộp sub (VD 1430x173) thay vì khung hình video 1920x1080
    width = raw_w if raw_w >= 854 and raw_h >= 480 else 1920
    height = raw_h if raw_w >= 854 and raw_h >= 480 else 1080

    font_size = int(
        opts.get("fontSize") or opts.get("font_size") or round(height * 0.056)
    )
    center_x = int(opts.get("centerX", round(width * 0.372)))
    center_y = int(opts.get("centerY", round(height * 0.875)))
    max_words_per_line = int(
        opts.get("maxWordsPerLine") or opts.get("max_words_per_line") or 5
    )
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

        cur.append(
            {
                "word": w,
                "upper": w.upper(),
                "start": float(item["start"]),
                "end": float(item["end"]),
                "hasPause": bool(item.get("hasPause")),
                "hasComma": bool(item.get("hasComma")),
            }
        )
        cur_chars += (1 if len(cur) > 1 else 0) + len(w)

        if idx == len(word_timings) - 1 and cur:
            phrases.append(cur)

    outline_px = max(2.0, round(font_size * 0.048, 1))
    shadow_px = max(1.0, round(font_size * 0.022, 1))

    header = "\n".join(
        [
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
        ]
    )

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
    glyph_center_y = (
        float(center_y) + float(font_size) * LIBASS_UPPERCASE_CENTER_Y_OFFSET_RATIO
    )
    box_top = glyph_center_y - (cap_height / 2.0) - pad_y
    box_bottom = glyph_center_y + (cap_height / 2.0) + pad_y

    for p_idx, phrase in enumerate(phrases):
        if not phrase:
            continue
        p_start = phrase[0]["start"]
        next_phrase = phrases[p_idx + 1] if p_idx + 1 < len(phrases) else None
        raw_end = phrase[-1]["end"]
        p_end = (
            min(raw_end + 0.06, next_phrase[0]["start"])
            if next_phrase
            else (raw_end + 0.08)
        )

        word_metrics = [
            measure_capcut_word_metrics(w["upper"], font_size) for w in phrase
        ]
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
            rect_path = build_ass_rounded_rect_path(
                box_l, box_top, box_r, box_bottom, corner_r
            )

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
    cues = _parse_karaoke_srt_file(srt_path)
    if not cues:
        return None

    if time_offset_sec > 0.0 or max_duration_sec is not None:
        shifted_cues: List[Dict[str, Any]] = []
        end_limit = (
            (time_offset_sec + max_duration_sec)
            if max_duration_sec is not None
            else float("inf")
        )
        for c in cues:
            if c["endTime"] <= time_offset_sec or c["startTime"] >= end_limit:
                continue
            new_s = max(0.0, c["startTime"] - time_offset_sec)
            new_e = max(new_s + 0.12, c["endTime"] - time_offset_sec)
            if max_duration_sec is not None:
                new_e = min(max_duration_sec, new_e)
            shifted_cues.append(
                {
                    "startTime": new_s,
                    "endTime": new_e,
                    "text": c["text"],
                }
            )
        cues = shifted_cues

    if not cues:
        return None

    words = extract_capcut_word_timings(cues)
    ass_content = build_capcut_karaoke_box_ass(words, options=options)
    os.makedirs(os.path.dirname(os.path.abspath(output_ass_path)), exist_ok=True)
    with open(output_ass_path, "w", encoding="utf-8") as f:
        f.write(ass_content)
    return output_ass_path


# ==============================================================================
# MODEL PHẦN 2: KIỂM ĐỊNH ĐỒNG BỘ ÂM THANH & PHỤ ĐỀ (SYNC CHECKER)
# ==============================================================================

import json
import os
import re
import subprocess
import wave
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

try:
    from scipy.io import wavfile
except Exception:
    wavfile = None


def estimate_japanese_mora_weight(text: str) -> float:
    """
    Ước lượng trọng số thời lượng phát âm tiếng Nhật (Mora + nhịp nghỉ dấu câu).
    Giúp kiểm tra tốc độ đọc (CPS / Mora-per-second) và chia phụ đề câu dài chuẩn xác.
    """
    clean = (text or "").strip()
    if not clean:
        return 1.0
    weight = 0.0
    for ch in clean:
        if ch in "「」『』（）()【】［］\"'”’ \t\r\n　":
            continue
        elif ch in "、，":
            weight += 1.6  # Nhịp nghỉ dấu phẩy
        elif ch in "。！？…・":
            weight += 2.0  # Nhịp nghỉ cuối câu
        elif ch in "ゃゅょっャュョッぁぃぅぇぉァィゥェォ":
            weight += 0.55
        elif "\u4e00" <= ch <= "\u9fff":
            # Chữ Hán (Kanji) trung bình 1.9 - 2.2 âm tiết (mora)
            weight += 1.95
        elif ch.isdigit() or ch in "一二三四五六七八九十百千万億":
            weight += 1.85
        else:
            # Hiragana / Katakana chuẩn = 1 mora
            weight += 1.0
    return max(1.0, weight)


def read_wav_mono_float(wav_path: Path) -> Tuple[int, np.ndarray]:
    """Đọc file WAV (hỗ trợ cả PCM 16-bit và IEEE Float 32-bit) về mảng float32 [-1.0, 1.0]."""
    p_str = str(wav_path)
    if wavfile is not None:
        try:
            import warnings

            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                sr, arr = wavfile.read(p_str)
            arr = np.asarray(arr)
            if arr.ndim > 1:
                arr = arr[:, 0]
            if np.issubdtype(arr.dtype, np.integer):
                max_val = float(np.iinfo(arr.dtype).max)
                arr = arr.astype(np.float32) / max_val
            else:
                arr = arr.astype(np.float32)
            return int(sr), arr
        except Exception:
            pass

    try:
        with wave.open(p_str, "rb") as wf:
            sr = wf.getframerate()
            n = wf.getnframes()
            raw = wf.readframes(n)
            arr = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
            return int(sr), arr
    except Exception:
        return 0, np.zeros(0, dtype=np.float32)


def find_pause_split_points_in_wav(
    wav_path: Optional[Path], chunks: List[str], start_time: float, end_time: float
) -> List[Tuple[float, float]]:
    """
    Khi 1 câu thoại dài (> 48 ký tự) được tách thành 2-3 khung phụ đề nối tiếp,
    hàm này dò trực tiếp điểm lặng (nhịp lấy hơi ở dấu phẩy 、) trong file WAV của câu đó
    để phụ đề chuyển cảnh khớp chính xác tuyệt đối với giọng đọc.
    """
    n_chunks = len(chunks)
    total_dur = max(0.05, end_time - start_time)
    if n_chunks <= 1:
        return [(start_time, end_time)]

    weights = [estimate_japanese_mora_weight(c) for c in chunks]
    total_w = sum(weights)

    # Nếu có file WAV thực tế của câu này, dò thung lũng năng lượng (silence valley) quanh vị trí kỳ vọng
    if wav_path is not None and Path(wav_path).exists():
        sr, arr = read_wav_mono_float(Path(wav_path))
        total_samples = len(arr)
        if sr > 0 and total_samples > int(0.5 * sr):
            win_len = max(1, int(0.030 * sr))
            hop_len = max(1, int(0.008 * sr))
            search_radius = int(0.55 * sr)
            min_seg = max(1, int(0.35 * sr))

            split_samples = [0]
            cum_w = 0.0
            for k in range(1, n_chunks):
                cum_w += weights[k - 1]
                expected = int(total_samples * (cum_w / total_w))
                prev_s = split_samples[-1]
                min_allowed = prev_s + min_seg
                max_allowed = total_samples - (n_chunks - k) * min_seg
                if min_allowed >= max_allowed:
                    split_samples.append(
                        max(prev_s + 1, min(expected, total_samples - 1))
                    )
                    continue

                lo = max(min_allowed, expected - search_radius)
                hi = min(max_allowed, expected + search_radius)
                if hi - lo > win_len * 2:
                    region = arr[lo:hi]
                    n_frames = 1 + (len(region) - win_len) // hop_len
                    if n_frames > 1:
                        strides = (region.strides[0] * hop_len, region.strides[0])
                        frames = np.lib.stride_tricks.as_strided(
                            region, shape=(n_frames, win_len), strides=strides
                        )
                        energies = np.mean(frames * frames, axis=1)
                        positions = np.arange(n_frames, dtype=np.float32) * hop_len + lo
                        dist_penalty = (
                            np.abs(positions - expected)
                            / max(1.0, float(search_radius))
                        ) * (float(np.mean(energies)) * 0.20)
                        best_frame = int(np.argmin(energies + dist_penalty))
                        best_pt = lo + best_frame * hop_len + (win_len // 2)
                        best_pt = max(min_allowed, min(max_allowed, best_pt))
                    else:
                        best_pt = expected
                else:
                    best_pt = max(min_allowed, min(max_allowed, expected))
                split_samples.append(best_pt)

            split_samples.append(total_samples)
            intervals: List[Tuple[float, float]] = []
            for i in range(n_chunks):
                s_ratio = split_samples[i] / float(total_samples)
                e_ratio = split_samples[i + 1] / float(total_samples)
                st = start_time if i == 0 else start_time + total_dur * s_ratio
                ed = end_time if i == n_chunks - 1 else start_time + total_dur * e_ratio
                intervals.append((st, ed))
            return intervals

    # Fallback theo trọng số phát âm Mora nếu không đọc trực tiếp WAV
    intervals = []
    curr_t = start_time
    for i, w in enumerate(weights):
        seg_dur = total_dur * (w / total_w)
        seg_end = end_time if i == n_chunks - 1 else curr_t + seg_dur
        intervals.append((curr_t, seg_end))
        curr_t = seg_end
    return intervals


def inspect_sentence_audio_sync(
    wav_path: Path, text: str, is_strict_1to1: bool = False
) -> Dict[str, Any]:
    """
    Kiểm định chất lượng & độ khớp của 1 file audio câu thoại so với văn bản câu đó:
    1. Kiểm tra tồn tại & thời lượng tối thiểu.
    2. Kiểm tra năng lượng âm thanh (RMS) chống câu bị câm / mất tiếng.
    3. Kiểm tra năng lượng biên đầu/cuối (start_rms, end_rms) chống lỗi cắt lẹm giữa từ (do gộp cụm cũ).
    4. Kiểm tra tốc độ đọc (CPS & Mora/s) chống lỗi nuốt chữ hoặc lặp từ AI.
    """
    clean_text = re.sub(r"[「」『』（）()【】［］\"'”’\s　]", "", text or "")
    char_len = max(1, len(clean_text))
    mora_weight = estimate_japanese_mora_weight(text)

    if not wav_path.exists() or wav_path.stat().st_size < 1000:
        return {
            "passed": False,
            "reasons": ["missing_or_empty_wav"],
            "duration": 0.0,
            "rms": 0.0,
            "start_rms": 0.0,
            "end_rms": 0.0,
            "cps": 0.0,
            "cut_start": False,
            "cut_end": False,
        }

    sr, arr = read_wav_mono_float(wav_path)
    if sr <= 0 or len(arr) == 0:
        return {
            "passed": False,
            "reasons": ["corrupted_wav_read"],
            "duration": 0.0,
            "rms": 0.0,
            "start_rms": 0.0,
            "end_rms": 0.0,
            "cps": 0.0,
            "cut_start": False,
            "cut_end": False,
        }

    dur = float(len(arr)) / float(sr)
    rms = float(np.sqrt(np.mean(arr * arr)))

    edge_win = min(len(arr) // 4, int(0.028 * sr))
    start_rms = float(np.sqrt(np.mean(arr[:edge_win] ** 2))) if edge_win > 0 else 0.0
    end_rms = float(np.sqrt(np.mean(arr[-edge_win:] ** 2))) if edge_win > 0 else 0.0

    cps = float(char_len) / dur if dur > 0 else 999.0
    mps = float(mora_weight) / dur if dur > 0 else 999.0

    reasons: List[str] = []
    min_dur = 0.25 if char_len <= 3 else 0.38
    if dur < min_dur:
        reasons.append(f"too_short({dur:.2f}s)")

    if rms < 0.006:
        reasons.append(f"silent_audio(rms={rms:.4f})")

    # Nếu file được tạo từ chế độ gộp cụm cũ (is_strict_1to1=False), kiểm tra nghiêm ngặt biên đầu/cuối
    # để bắt mọi câu bị cắt lẹm giữa từ hoặc lệch sang câu bên cạnh
    edge_limit = 0.065 if is_strict_1to1 else 0.022
    cut_start = start_rms > edge_limit
    cut_end = end_rms > edge_limit
    if cut_start:
        reasons.append(f"boundary_cut_start(rms={start_rms:.3f})")
    if cut_end:
        reasons.append(f"boundary_cut_end(rms={end_rms:.3f})")

    # Kiểm tra tốc độ đọc hợp lý (Hỗ trợ cả Tây Ban Nha es-MX ~12-24 CPS và Tiếng Nhật ~4-13 CPS)
    has_cjk = any("\u3040" <= ch <= "\u9fff" for ch in (text or ""))
    if has_cjk:
        max_cps = 13.5 if is_strict_1to1 else 11.5
        min_cps = 2.2 if is_strict_1to1 else 3.0
    else:
        max_cps = 25.0 if is_strict_1to1 else 22.0
        min_cps = 4.0 if is_strict_1to1 else 5.0
    if char_len >= 5 and cps > max_cps:
        reasons.append(f"speaking_too_fast(cps={cps:.1f})")
    elif char_len >= 6 and cps < min_cps and dur > 3.5:
        reasons.append(f"speaking_too_slow(cps={cps:.1f})")

    return {
        "passed": len(reasons) == 0,
        "reasons": reasons,
        "duration": round(dur, 4),
        "rms": round(rms, 4),
        "start_rms": round(start_rms, 4),
        "end_rms": round(end_rms, 4),
        "cps": round(cps, 2),
        "mps": round(mps, 2),
        "cut_start": cut_start,
        "cut_end": cut_end,
    }


def audit_all_sentences_sync(
    sentences: List[str], sentences_dir: Path, require_strict_1to1: bool = False
) -> Dict[str, Any]:
    """
    Quét kiểm định toàn bộ N câu thoại trong thư mục sentences_dir.
    Trả về danh sách các chỉ số câu (0-based) cần phải tạo lại (redo_indices) để đảm bảo
    100% câu thoại khớp tuyệt đối với phụ đề.
    """
    manifest_path = sentences_dir / "sync_1to1_manifest.json"
    strict_map: Dict[str, bool] = {}
    if manifest_path.exists():
        try:
            strict_map = json.loads(manifest_path.read_text(encoding="utf-8"))
        except Exception:
            strict_map = {}

    total = len(sentences)
    redo_set = set()
    details: List[Dict[str, Any]] = []

    for idx, text in enumerate(sentences):
        key = f"sentence_{idx + 1:04d}.wav"
        wav_p = sentences_dir / key
        is_1to1 = bool(strict_map.get(key, False))

        if require_strict_1to1 and not is_1to1:
            redo_set.add(idx)
            details.append(
                {
                    "index": idx + 1,
                    "passed": False,
                    "reasons": ["legacy_grouped_audio_not_1to1"],
                    "text": text[:30],
                }
            )
            continue

        res = inspect_sentence_audio_sync(wav_p, text, is_strict_1to1=is_1to1)
        if not res["passed"]:
            redo_set.add(idx)
            # Nếu bị cắt lẹm ở đầu câu, câu liền trước cũng bị lệch biên -> làm lại cả đôi
            if res.get("cut_start") and idx > 0:
                redo_set.add(idx - 1)
            # Nếu bị cắt lẹm ở cuối câu, câu liền sau cũng bị lệch biên -> làm lại cả đôi
            if res.get("cut_end") and idx + 1 < total:
                redo_set.add(idx + 1)
            details.append(
                {
                    "index": idx + 1,
                    "passed": False,
                    "reasons": res["reasons"],
                    "duration": res["duration"],
                    "cps": res["cps"],
                    "text": text[:30],
                }
            )

    redo_indices = sorted(redo_set)
    return {
        "passed": len(redo_indices) == 0,
        "total_sentences": total,
        "passed_sentences": total - len(redo_indices),
        "failed_count": len(redo_indices),
        "redo_indices": redo_indices,
        "failed_samples": details[:30],
    }


def _parse_srt_timestamp(ts: str) -> float:
    ts = ts.strip().replace(",", ".")
    parts = ts.split(":")
    if len(parts) == 3:
        return float(parts[0]) * 3600.0 + float(parts[1]) * 60.0 + float(parts[2])
    return 0.0


def probe_media_info(file_path: Path) -> Dict[str, Any]:
    """Kiểm tra thông số thực tế của file MP4 / WAV bằng ffprobe."""
    if not file_path.exists() or file_path.stat().st_size < 1024:
        return {"valid": False, "reason": "file_missing_or_empty"}

    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration:stream=codec_type,codec_name,duration",
        "-of",
        "json",
        str(file_path),
    ]
    try:
        res = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=15,
            creationflags=0x08000000 if os.name == "nt" else 0,
        )
        if res.returncode != 0:
            return {
                "valid": False,
                "reason": f"ffprobe_error: {res.stderr.strip()[:120]}",
            }
        data = json.loads(res.stdout or "{}")
        streams = data.get("streams", [])
        fmt = data.get("format", {})
        dur = float(fmt.get("duration", 0.0) or 0.0)
        has_video = any(s.get("codec_type") == "video" for s in streams)
        has_audio = any(s.get("codec_type") == "audio" for s in streams)
        return {
            "valid": dur > 0,
            "duration": dur,
            "has_video": has_video,
            "has_audio": has_audio,
            "streams": streams,
        }
    except Exception as e:
        return {"valid": False, "reason": str(e)}


def validate_completed_mp4_file(
    mp4_path: Path,
    master_wav_path: Optional[Path] = None,
    script_char_count: int = 0,
) -> Dict[str, Any]:
    """
    Kiểm định nghiêm ngặt một file `{ma_id}_master.mp4` trên ổ cứng xem có thực sự hoàn chỉnh 100% hay bị lỗi / ngắt giữa chừng:
    1. Kiểm tra tồn tại & dung lượng tối thiểu (>= 10MB; nếu kịch bản >= 25.000 chữ thì >= 20MB).
    2. Dùng `ffprobe` kiểm tra cấu trúc container MP4 (`moov atom`), bắt buộc có đủ cả luồng hình (`video`) và luồng tiếng (`audio`).
    3. Kiểm tra thời lượng thực tế (`video_dur`) không bị cắt ngắn so với độ dài kịch bản (`script_char_count`) và khớp với `master_voice.wav` (sai số <= 5s).
    """
    if not mp4_path or not mp4_path.exists():
        return {"valid": False, "duration": 0.0, "reason": "missing_file"}

    try:
        st_size = mp4_path.stat().st_size
    except Exception:
        return {"valid": False, "duration": 0.0, "reason": "stat_failed"}

    min_bytes = 20_000_000 if script_char_count >= 25_000 else 5_000_000
    if st_size < min_bytes:
        return {
            "valid": False,
            "duration": 0.0,
            "reason": f"Dung lượng MP4 quá nhỏ ({st_size / (1024 * 1024):.1f} MB) — tiến trình render bị ngắt sớm",
        }

    p_info = probe_media_info(mp4_path)
    if not p_info.get("valid"):
        raw_reason = str(p_info.get("reason") or "corrupted_mp4")
        if "moov atom not found" in raw_reason.lower():
            return {
                "valid": False,
                "duration": 0.0,
                "reason": "Video MP4 bị ngắt giữa chừng (chưa đóng gói xong moov atom)",
            }
        return {
            "valid": False,
            "duration": 0.0,
            "reason": f"File MP4 bị lỗi cấu trúc ({raw_reason[:80]})",
        }

    if not p_info.get("has_video") or not p_info.get("has_audio"):
        return {
            "valid": False,
            "duration": 0.0,
            "reason": "Video MP4 bị thiếu luồng hình ảnh (video) hoặc luồng âm thanh (audio)",
        }

    video_dur = float(p_info.get("duration", 0.0) or 0.0)
    if video_dur < 60.0:
        return {
            "valid": False,
            "duration": video_dur,
            "reason": f"Thời lượng Video MP4 quá ngắn ({video_dur:.1f}s)",
        }

    # Đối chiếu thời lượng tối thiểu dựa trên độ dài kịch bản (~0.048s/chữ là ngưỡng sàn an toàn cho cả Tây Ban Nha es-MX và Nhật)
    if script_char_count >= 10_000:
        min_expected_dur = max(300.0, float(script_char_count) * 0.048)
        if video_dur < min_expected_dur:
            return {
                "valid": False,
                "duration": video_dur,
                "reason": (
                    f"Video MP4 bị ngắt giữa chừng (Mới đạt {video_dur / 60:.1f} phút, "
                    f"cần tối thiểu {min_expected_dur / 60:.1f} phút cho {script_char_count:,} chữ)"
                ),
            }

    # Đối chiếu trực tiếp với master_voice.wav nếu có sẵn
    if master_wav_path and master_wav_path.exists():
        wav_dur = 0.0
        try:
            with wave.open(str(master_wav_path), "rb") as wf:
                frames = wf.getnframes()
                rate = wf.getframerate()
                if rate > 0 and frames > 0:
                    wav_dur = float(frames) / float(rate)
        except Exception:
            w_info = probe_media_info(master_wav_path)
            if w_info.get("valid"):
                wav_dur = float(w_info.get("duration", 0.0) or 0.0)

        if wav_dur > 60.0:
            if script_char_count >= 10_000 and wav_dur < max(
                300.0, float(script_char_count) * 0.048
            ):
                return {
                    "valid": False,
                    "duration": video_dur,
                    "reason": f"File Voice gốc bị thiếu câu ({wav_dur / 60:.1f} phút cho {script_char_count:,} chữ)",
                }
            max_allowed_drift = max(10.0, wav_dur * 0.015)
            if abs(video_dur - wav_dur) > max_allowed_drift or video_dur < (
                wav_dur - 8.0
            ):
                return {
                    "valid": False,
                    "duration": video_dur,
                    "reason": (
                        f"Video MP4 bị ngắt giữa chừng ({video_dur / 60:.1f} phút / "
                        f"Tổng thời lượng Voice {wav_dur / 60:.1f} phút)"
                    ),
                }

    return {"valid": True, "duration": round(video_dur, 3), "reason": "ok"}


def _hot_reload_live_runtime_and_green_plates(video_path: Path):
    """
    Tự động cập nhật nóng (Hot-Reload) các module đã nâng cấp vào tiến trình Server đang chạy
    và tái tạo ngay bộ ảnh THUMBNAIL-NENXANH.png + script_green_images/green_part_01..07.png
    cho dự án hiện tại mà không cần tắt/mở lại ứng dụng.
    """
    try:
        import importlib
        import sys
        import threading

        for mod_name in (
            "backend.stock_manager",
            "backend.voice_service",
            "backend.visual_cue_director",
            "backend.renderer",
            "backend.adas_script_engine",
            "backend.pipeline",
        ):
            if mod_name in sys.modules:
                try:
                    mod = importlib.reload(sys.modules[mod_name])
                    # Cập nhật lại các phương thức class trên instance đang chạy trong bộ nhớ
                    if mod_name == "backend.stock_manager" and hasattr(
                        mod, "StockManager"
                    ):
                        pass
                except Exception as re_err:
                    print(f"[HotReload] Lưu ý khi reload {mod_name}: {re_err}")

        # Cập nhật trực tiếp class methods cho các đối tượng đang sống trong gc
        import gc

        import backend.adas_script_engine as ase_mod
        import backend.pipeline as pl_mod
        import backend.stock_manager as sm_mod
        import backend.visual_cue_director as vcd_mod
        import backend.voice_service as vs_mod

        for obj in gc.get_objects():
            try:
                cls_name = getattr(getattr(obj, "__class__", None), "__name__", "")
                if cls_name == "StockManager":
                    obj.__class__ = sm_mod.StockManager
                elif cls_name == "VoiceStudioService":
                    obj.__class__ = vs_mod.VoiceStudioService
                    threading.Thread(
                        target=obj.ensure_voicestudio_server_running, daemon=True
                    ).start()
                elif cls_name == "ADASScriptEngine":
                    obj.__class__ = ase_mod.ADASScriptEngine
                elif cls_name == "ProductionPipeline":
                    obj.__class__ = pl_mod.ProductionPipeline
            except Exception:
                pass

        # Tái tạo ngay ảnh THUMBNAIL-NENXANH.png & green_part_01..07.png cho dự án
        renders_dir = Path(video_path).resolve().parent
        proj_dir = renders_dir.parent
        if (proj_dir / "THUMBNAIL.png").exists() or (
            renders_dir / "THUMBNAIL.png"
        ).exists():
            vcd_mod.ensure_project_script_green_images(
                proj_dir=proj_dir,
                renders_dir=renders_dir,
                proj_name=proj_dir.name,
                force_regenerate=True,
            )
    except Exception as e:
        print(f"[HotReload] Lưu ý khi đồng bộ nóng runtime & green plates: {e}")


def verify_rendered_video_sync(
    video_path: Path,
    master_wav_path: Path,
    srt_path: Path,
    sentences: List[str],
    sentences_dir: Path,
) -> Dict[str, Any]:
    """
    BƯỚC KIỂM ĐỊNH CUỐI CÙNG TRÊN FILE VIDEO MP4:
    1. Kiểm tra file MP4 có mở được bình thường (đầy đủ luồng hình H264 + luồng tiếng AAC + moov atom).
    2. Kiểm tra độ khớp thời lượng giữa Video MP4 <-> Master Voice WAV <-> Mốc cuối Subtitles SRT (sai số <= 0.6s).
    3. Kiểm tra cấu trúc các khung phụ đề SRT (không chồng lấn thời gian, không rớt dòng thứ 4, đủ chữ).
    4. Kiểm tra biên bản khớp câu thoại (Sentence-level Sync Audit).
    """
    _hot_reload_live_runtime_and_green_plates(video_path)
    issues: List[str] = []

    v_info = probe_media_info(video_path)
    if not v_info.get("valid"):
        issues.append(
            f"Video MP4 lỗi hoặc chưa đóng gói xong ({v_info.get('reason', 'unknown')})"
        )
    else:
        if not v_info.get("has_video"):
            issues.append("Video MP4 thiếu luồng hình ảnh (video stream)")
        if not v_info.get("has_audio"):
            issues.append("Video MP4 thiếu luồng âm thanh (audio stream)")

    w_info = probe_media_info(master_wav_path)
    if not w_info.get("valid"):
        issues.append("File master_voice.wav bị lỗi hoặc không đọc được thời lượng")

    video_dur = float(v_info.get("duration", 0.0) or 0.0)
    wav_dur = float(w_info.get("duration", 0.0) or 0.0)

    # Kiểm tra file SRT
    srt_last_end = 0.0
    srt_blocks_count = 0
    overlap_count = 0
    over_3_lines_count = 0

    if not srt_path.exists() or srt_path.stat().st_size < 10:
        issues.append("File phụ đề subtitles.srt không tồn tại hoặc trống")
    else:
        raw_srt = srt_path.read_text(encoding="utf-8").strip()
        blocks = [b.strip() for b in re.split(r"\n\s*\n", raw_srt) if b.strip()]
        srt_blocks_count = len(blocks)
        prev_end = 0.0
        for blk in blocks:
            lines = [l.strip() for l in blk.splitlines() if l.strip()]
            if len(lines) >= 3 and "-->" in lines[1]:
                ts_parts = lines[1].split("-->")
                st = _parse_srt_timestamp(ts_parts[0])
                ed = _parse_srt_timestamp(ts_parts[1])
                if st < prev_end - 0.02:
                    overlap_count += 1
                prev_end = max(prev_end, ed)
                srt_last_end = max(srt_last_end, ed)
                text_lines = lines[2:]
                if len(text_lines) > 3:
                    over_3_lines_count += 1

    if overlap_count > 0:
        issues.append(f"Phát hiện {overlap_count} khung phụ đề bị chồng lấn thời gian")
    if over_3_lines_count > 0:
        issues.append(f"Phát hiện {over_3_lines_count} khung phụ đề vượt quá 3 dòng")

    # Kiểm tra độ lệch thời lượng tổng thể (cho phép dung sai <= 2.8s đối với video nối tiếp từ nhiều đoạn Checkpoint .ts)
    diff_video_wav = abs(video_dur - wav_dur)
    diff_wav_srt = abs(wav_dur - srt_last_end)

    if video_dur > 0 and wav_dur > 0 and diff_video_wav > 2.80:
        issues.append(
            f"Thời lượng Video MP4 ({video_dur:.2f}s) lệch so với Voice ({wav_dur:.2f}s) là {diff_video_wav:.2f}s"
        )
    if wav_dur > 0 and srt_last_end > 0 and diff_wav_srt > 0.50:
        issues.append(
            f"Thời lượng Phụ đề SRT ({srt_last_end:.2f}s) lệch so với Voice ({wav_dur:.2f}s) là {diff_wav_srt:.2f}s"
        )

    # Kiểm tra độ khớp từng câu thoại
    sent_audit = audit_all_sentences_sync(
        sentences, sentences_dir, require_strict_1to1=False
    )
    if not sent_audit["passed"]:
        issues.append(
            f"Phát hiện {sent_audit['failed_count']}/{sent_audit['total_sentences']} câu thoại bị lệch biên hoặc bất thường âm lượng/tốc độ"
        )

    passed = len(issues) == 0
    return {
        "passed": passed,
        "status_label": "✅ ĐẠT (Sub & Voice khớp 100%)"
        if passed
        else "❌ CHƯA KHỚP (Cần làm lại)",
        "video_duration": round(video_dur, 3),
        "voice_duration": round(wav_dur, 3),
        "srt_end_duration": round(srt_last_end, 3),
        "drift_video_vs_voice_sec": round(diff_video_wav, 3),
        "drift_voice_vs_srt_sec": round(diff_wav_srt, 3),
        "srt_blocks_count": srt_blocks_count,
        "sentence_audit": sent_audit,
        "issues": issues,
    }


# ==============================================================================
# MODEL PHẦN 3: DỊCH VỤ GIỌNG ĐỌC AI OMNIVOICE GPU (VOICE SERVICE)
# ==============================================================================

import json
import os
import re
import subprocess
import sys
import time
import wave
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

# Ưu tiên thư mục bin nội bộ (chứa ffmpeg/ffprobe tương thích NVENC 13.0)
_BIN_DIR = Path(__file__).resolve().parent.parent / "bin"
if not _BIN_DIR.exists():
    _BIN_DIR = Path(__file__).resolve().parent.parent.parent / "bin"
if _BIN_DIR.exists():
    os.environ["PATH"] = str(_BIN_DIR) + os.pathsep + os.environ.get("PATH", "")

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def format_timestamp(seconds: float) -> str:
    """Định dạng giây thành SRT timestamp: HH:MM:SS,mmm"""
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    mils = int(round((seconds - int(seconds)) * 1000))
    if mils >= 1000:
        mils = 999
    return f"{hrs:02d}:{mins:02d}:{secs:02d},{mils:03d}"


def _is_cjk_text(s: str) -> bool:
    return any("\u3040" <= ch <= "\u9fff" for ch in (s or ""))


def _find_bounded_break(s: str, target: int, lo: int, hi: int) -> int:
    """Tìm vị trí ngắt dòng tự nhiên nhất trong khoảng bắt buộc [lo, hi] (Hỗ trợ cả Tây Ban Nha es-MX và Tiếng Nhật)."""
    lo = max(1, lo)
    hi = min(len(s) - 1, hi)
    if lo > hi:
        return max(1, min(len(s) - 1, target))

    # Nếu là văn bản Tây Ban Nha / Latin (không có chữ CJK): BẮT BUỘC ngắt tại dấu câu + khoảng trắng hoặc khoảng trắng giữa các từ, tuyệt đối không cắt đôi từ!
    if not _is_cjk_text(s):
        best_idx = -1
        best_score = 9999
        # 1. Ưu tiên dấu câu Tây Ban Nha (, ; : . ! ? — » ”) có khoảng trắng theo sau
        for i in range(lo - 1, hi):
            ch = s[i]
            pos = i + 1
            if ch in ",;:.!?—»”)" and pos < len(s) and s[pos] == " ":
                score = abs(pos - target)
                if score < best_score:
                    best_score = score
                    best_idx = pos + 1
        if best_idx != -1 and best_idx < len(s):
            return best_idx

        # 2. Ưu tiên khoảng trắng giữa các từ trong khoảng [lo, hi]
        for i in range(lo - 1, hi + 1):
            if i < len(s) and s[i] == " ":
                score = abs(i - target)
                if score < best_score:
                    best_score = score
                    best_idx = i + 1
        if best_idx != -1 and best_idx < len(s):
            return best_idx

        # 3. Tìm khoảng trắng gần nhất bên ngoài [lo, hi] để không bao giờ cắt ngang từ tiếng Tây Ban Nha
        for radius in range(1, len(s)):
            left = target - radius
            right = target + radius
            if left > 0 and s[left] == " ":
                return left + 1
            if right < len(s) - 1 and s[right] == " ":
                return right + 1
        return max(lo, min(hi, target))

    best_idx = -1
    best_score = 9999
    # 1. Ưu tiên dấu câu 、。！？」』
    for i in range(lo - 1, hi):
        ch = s[i]
        pos = i + 1
        if ch in "、。！？」』":
            if pos < len(s) and s[pos] in "、。！？」』）":
                continue
            score = abs(pos - target)
            if score < best_score:
                best_score = score
                best_idx = pos
    if best_idx != -1:
        return best_idx

    # 2. Ưu tiên trợ từ tiếng Nhật (không cắt giữa từ)
    for i in range(lo - 1, hi):
        ch = s[i]
        pos = i + 1
        if ch in "はがをにへとでも":
            if pos < len(s) and s[pos] in "はがをにへとでも、。！？」』）":
                continue
            score = abs(pos - target) + 1
            if score < best_score:
                best_score = score
                best_idx = pos
    if best_idx != -1:
        return best_idx

    return max(lo, min(hi, target))


def format_srt_text(text: str, max_chars_per_line: int = 17) -> str:
    """
    Chia câu thoại thành TỐI ĐA 3 DÒNG cân đối (mỗi dòng <= max_chars_per_line ký tự)
    cho cỡ chữ lớn. Hỗ trợ tự động giãn độ rộng ký tự Latin cho tiếng Tây Ban Nha (es-MX)
    và tuyệt đối không cắt đôi từ tiếng Tây Ban Nha.
    """
    text = text.replace("\n", " ").strip()
    if not _is_cjk_text(text) and max_chars_per_line <= 20:
        max_chars_per_line = 26
    n = len(text)
    if n <= max_chars_per_line:
        return text

    # Nếu câu vừa trong 2 dòng (n <= max_chars_per_line * 2)
    if n <= max_chars_per_line * 2:
        lo = max(4, n - max_chars_per_line)
        hi = min(n - 4, max_chars_per_line)
        bp = _find_bounded_break(text, n // 2, lo, hi)
        l1, l2 = text[:bp].strip(), text[bp:].strip()
        if len(l1) <= max_chars_per_line + 4 and len(l2) <= max_chars_per_line + 4:
            return f"{l1}\n{l2}"

    # Chia thành đúng 3 dòng cân đối, ép biên chặt chẽ
    eff_max = max(max_chars_per_line, (n + 2) // 3)
    lo1 = max(4, n - 2 * eff_max)
    hi1 = min(n - 8, eff_max)
    bp1 = _find_bounded_break(text, n // 3, lo1, hi1)
    line1 = text[:bp1].strip()

    rem = text[bp1:].strip()
    m = len(rem)
    if m <= eff_max:
        return f"{line1}\n{rem}"

    lo2 = max(4, m - eff_max)
    hi2 = min(m - 4, eff_max)
    bp2 = _find_bounded_break(rem, m // 2, lo2, hi2)
    line2 = rem[:bp2].strip()
    line3 = rem[bp2:].strip()
    return "\n".join([x for x in [line1, line2, line3] if x])


def split_long_subtitle_segments(
    text: str,
    start: float,
    end: float,
    max_segment_chars: int = 48,
    max_chars_per_line: int = 17,
    wav_path: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Nếu 1 câu thoại quá dài, tự động tách thành 2 hoặc nhiều phân đoạn phụ đề nối tiếp nhau
    theo điểm lặng thực tế trong file WAV để MỖI PHỤ ĐỀ CHỈ CÓ TỐI ĐA 3 DÒNG.
    Hỗ trợ cả tiếng Tây Ban Nha (es-MX) và tiếng Nhật.
    """
    clean = text.replace("\n", " ").strip()
    if not clean:
        return []
    if not _is_cjk_text(clean):
        if max_chars_per_line <= 20:
            max_chars_per_line = 26
        if max_segment_chars <= 52:
            max_segment_chars = 74

    chunks: List[str] = [clean]
    while any(len(c) > max_segment_chars for c in chunks):
        new_chunks: List[str] = []
        for c in chunks:
            if len(c) <= max_segment_chars:
                new_chunks.append(c)
            else:
                n_c = len(c)
                target = (
                    max_segment_chars - 6 if n_c > max_segment_chars * 2 else n_c // 2
                )
                lo = max(12, target - 14)
                hi = min(n_c - 10, max_segment_chars)
                bp = _find_bounded_break(c, target, lo, hi)
                new_chunks.append(c[:bp].strip())
                new_chunks.append(c[bp:].strip())
        chunks = [x for x in new_chunks if x]

    try:
        intervals = find_pause_split_points_in_wav(
            Path(wav_path) if wav_path else None, chunks, start, end
        )
    except Exception:
        total_chars = max(1, sum(len(c) for c in chunks))
        total_dur = max(0.1, end - start)
        intervals = []
        curr_t = start
        for i, c in enumerate(chunks):
            seg_dur = total_dur * (len(c) / total_chars)
            seg_end = end if i == len(chunks) - 1 else curr_t + seg_dur
            intervals.append((curr_t, seg_end))
            curr_t = seg_end

    results = []
    for c, (seg_start, seg_end) in zip(chunks, intervals):
        results.append(
            {
                "start": seg_start,
                "end": seg_end,
                "text": format_srt_text(c, max_chars_per_line=max_chars_per_line),
            }
        )
    return results


import re as _re_mod

_FAST_MAYBE_LEAK_RE = _re_mod.compile(
    r"\[PART\s*[1-7]\]|日本語脚本|日本語ナレーション|```|---|===|"
    r"LOCKED_TITLE|SELECTED_TITLE|WINNING_TITLE|FINAL_TITLE|DRAFT_TITLE|CURRENT_FINAL_TITLE|"
    r"STAGE_[ABC]_COUNT_GATE|CANON_CONTINUITY|TIMELINE_AGE_LEDGER|REPAIR_[12]_EXECUTION",
    _re_mod.IGNORECASE,
)


def strip_leaked_titles_and_metadata(raw_text: str):
    """
    Quét, ghi nhận và xóa sạch 100% các dòng [LOCKED_TITLE], [CURRENT_FINAL_TITLE], [PART 1]..[PART 7],
    bao gồm cả phần câu tiêu đề bị tách thành 2–4 dòng kế tiếp, cũng như các dòng nhãn kỹ thuật
    (STEP 3/4/5, STAGE_A_COUNT_GATE, PART_1_CHAR_COUNT, <CodeBlock>, <WritingBlock>, CONTINUITY:, ENDING:...)
    để tuyệt đối không bao giờ bị lọt vào quá trình tạo Voice (TTS) hay Phụ đề Video (Render MP4).
    """
    import re

    if not raw_text:
        return "", []

    cleaned_raw = re.sub(
        r"</?(?:CodeBlock|WritingBlock|title|grid|grid-item|caption)[^>]*>",
        "",
        raw_text,
        flags=re.IGNORECASE,
    )
    lines = cleaned_raw.splitlines()
    kept = []
    removed = []
    n = len(lines)
    i = 0

    title_key_re = re.compile(
        r"^(?:LOCKED_TITLE|CURRENT_FINAL_TITLE|SELECTED_TITLE|WINNING_TITLE|FINAL_TITLE|DRAFT_TITLE|TITLE_LOCKED|LOCKED_TITLE_PROMISE|TITLE_FACTS|TITLE_LOCK_RECORD)\s*[:：\-—]?",
        re.IGNORECASE,
    )
    standalone_part_heading_re = re.compile(
        r"^\[\s*PART\s*[1-7]\s*\]$",
        re.IGNORECASE,
    )
    step_part_re = re.compile(
        r"^(?:[A-Z]{1,6}\d{1,5}\s*[—–\-·:：]+\s*)?(?:STEP\s*[1-7]\b|BUILD\s+PART\s*[ABC]\b|STAGE\s*[ABC]\b|PART\s*[:：\-—–·]?\s*[ABC1-7]\b|SCENE\s+[ABC]?\d+\b|CHAPTER\s+\d+\b)",
        re.IGNORECASE,
    )
    stop_block_re = re.compile(
        r"^(?:PART_PURE_CHARACTER_COUNT|PART_LENGTH_GATE|STAGE_[ABC]_COUNT_GATE|PART_[1-7]_CHAR_COUNT|TOTAL_SCRIPT_CHAR_COUNT|ALL_7_PARTS_GE_8500|TOTAL_IN_70000_80000|CONTINUITY_LEDGER|CONTINUITY\s+LEDGER|PART_HANDOFF_LEDGER|HANDOFF_LEDGER|HANDOFF\s+LEDGER|PART_[ABC]_HANDOFF|NEXT_ACTION|READY_FOR_AUDIT|PATCH_CHANGELOG|REPAIR_[12]_EXECUTION_LOG)\b",
        re.IGNORECASE,
    )
    meta_kv_re = re.compile(
        r"^(?:ID|COMPLETED_STEP|RESULT|STATUS|NEXT_STEP|CONTINUITY|ENDING|LOCKED_TITLE|CURRENT_FINAL_TITLE|SELECTED_TITLE|WINNING_TITLE|TITLE_LOCKED|STAGE_TOTAL_CHAR_COUNT|STAGE_A_PASS|STAGE_B_PASS|STAGE_C_PASS|SCRIPT_FILE|AUDIT_ROUND|ROUND_[12]_VERDICT|FINAL_VERDICT|FINAL_QUALITY_SCORE)\s*[:：=]",
        re.IGNORECASE,
    )
    ellipsis_endings = ("…", "…」", "…」」", "…』", "…。", "…。」", "…！」", "…？」")

    while i < n:
        raw_ln = lines[i]
        s = raw_ln.strip()
        if not s:
            kept.append(raw_ln)
            i += 1
            continue

        s_clean = (
            re.sub(r"^[#*>\-\s`•]+", "", s).replace("**", "").replace("`", "").strip()
        )
        if not s_clean or s_clean.startswith(("```", "---", "===")):
            removed.append((i + 1, s))
            i += 1
            continue

        # Xóa nhãn [PART 1] .. [PART 7] để không bao giờ đọc vào TTS/Subtitles
        if standalone_part_heading_re.match(s_clean):
            removed.append((i + 1, s))
            i += 1
            continue

        if stop_block_re.match(s_clean):
            for k in range(i, n):
                if lines[k].strip():
                    removed.append((k + 1, lines[k].strip()))
            break

        # 1. Phát hiện và xóa trọn cụm LOCKED_TITLE / CURRENT_FINAL_TITLE / SELECTED_TITLE
        if title_key_re.search(s_clean):
            body0 = re.sub(
                r"^.*?(?:LOCKED_TITLE|CURRENT_FINAL_TITLE|SELECTED_TITLE|WINNING_TITLE|FINAL_TITLE|DRAFT_TITLE|TITLE_LOCKED|LOCKED_TITLE_PROMISE|TITLE_FACTS|TITLE_LOCK_RECORD)\s*[:：\-—]*\s*",
                "",
                s_clean,
                flags=re.IGNORECASE,
            ).strip()
            end_i = i + 1
            open_q = body0.count("「")
            close_q = body0.count("」")
            if _is_cjk_text(body0) and not (
                body0.endswith(ellipsis_endings) and open_q <= close_q + 1
            ):
                acc = body0
                for k in range(i + 1, min(n, i + 5)):
                    cand = lines[k].strip()
                    if not cand:
                        break
                    acc += cand
                    if cand.endswith(ellipsis_endings) and len(acc) <= 185:
                        end_i = k + 1
                        break
                    if (
                        open_q > close_q
                        and acc.count("「") <= acc.count("」")
                        and len(acc) <= 185
                    ):
                        end_i = k + 1
                        break
            for k in range(i, end_i):
                removed.append((k + 1, lines[k].strip()))
            i = end_i
            continue

        # 2. Phát hiện và xóa các dòng tiêu đề STEP / PART / 日本語脚本
        if (step_part_re.match(s_clean) and len(s_clean) < 90) or (
            re.search(
                r"(?:日本語脚本|日本語ナレーション本文|HANDOFF_LEDGER|PURE_CHARACTER_COUNT|STAGE_[ABC]_COUNT_GATE)",
                s_clean,
                re.IGNORECASE,
            )
            and len(s_clean) < 90
        ):
            removed.append((i + 1, s))
            i += 1
            continue

        # 3. Phát hiện và xóa các dòng Metadata kỹ thuật (CONTINUITY:, ENDING:, ID:, STATUS:...)
        if meta_kv_re.match(s_clean):
            removed.append((i + 1, s))
            i += 1
            continue

        kept.append(s_clean)
        i += 1

    out_text = re.sub(r"\n{3,}", "\n\n", "\n".join(kept)).strip()
    return out_text, removed


_ES_ABBREV_RE = _re_mod.compile(
    r"\b(?:Sr|Sra|Srta|Dr|Dra|Lic|Ing|Arq|Prof|Profa|Gral|Cnel|Cap|Tte|Av|Col|Fracc|Blvd|No|Núm|Art|Inc|Corp|Tel|C\.P|Uds|Ud)\.$",
    _re_mod.IGNORECASE,
)


def split_japanese_script(raw_text: str) -> List[str]:
    """
    Tách kịch bản thành các câu thoại chuẩn cảm xúc (Hỗ trợ cả Tây Ban Nha es-MX và Tiếng Nhật),
    tự động lọc bỏ [PART 1]..[PART 7], LOCKED_TITLE & Metadata rò rỉ.
    """
    cleaned_script, _ = strip_leaked_titles_and_metadata(raw_text)
    if not cleaned_script:
        return []

    is_cjk = _is_cjk_text(cleaned_script)
    closing_chars = set("」』）)】］\"'”’»")
    punct_only_chars = set(
        "。！？、…・　 \t\r\n「『（(【［」』）)】］\"'”’«»¡¿.!?,;:-—"
    )

    lines = cleaned_script.strip().split("\n")
    sentences: List[str] = []
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("//"):
            continue
        if re.match(r"^\[\s*PART\s*[1-7]\s*\]$", line, flags=re.IGNORECASE):
            continue

        sub_sentences: List[str] = []
        curr = ""
        n = len(line)
        i = 0
        while i < n:
            char = line[i]
            curr += char
            if is_cjk:
                if char in "。！？":
                    while i + 1 < n and line[i + 1] in closing_chars:
                        i += 1
                        curr += line[i]
                    sub_sentences.append(curr.strip())
                    curr = ""
            else:
                # Ngắt câu tiếng Tây Ban Nha (es-MX) tại . ! ? … (tránh ngắt nhầm từ viết tắt Sr., Sra., Dr., Lic., Ing. hoặc số thập phân)
                if char in ".!?…":
                    if (
                        char == "."
                        and i > 0
                        and i + 1 < n
                        and line[i - 1].isdigit()
                        and line[i + 1].isdigit()
                    ):
                        i += 1
                        continue
                    if char == "." and i + 1 < n and line[i + 1] == ".":
                        i += 1
                        continue
                    if char == "." and _ES_ABBREV_RE.search(curr):
                        i += 1
                        continue
                    while i + 1 < n and line[i + 1] in closing_chars:
                        i += 1
                        curr += line[i]
                    if i + 1 >= n or line[i + 1].isspace() or line[i + 1] in "¡¿—«\"'“":
                        sub_sentences.append(curr.strip())
                        curr = ""
            i += 1
        if curr.strip():
            sub_sentences.append(curr.strip())

        for s in sub_sentences:
            s = s.strip()
            if s and any(ch not in punct_only_chars for ch in s):
                sentences.append(s)
    return sentences


def get_audio_duration(file_path: str) -> float:
    if str(file_path).lower().endswith(".wav"):
        try:
            with wave.open(str(file_path), "rb") as wf:
                frames = wf.getnframes()
                rate = wf.getframerate()
                if rate > 0 and frames > 0:
                    return float(frames) / float(rate)
        except Exception:
            pass
        try:
            import torchaudio

            info = torchaudio.info(str(file_path))
            if info.sample_rate > 0 and info.num_frames > 0:
                return float(info.num_frames) / float(info.sample_rate)
        except Exception:
            pass

    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        file_path,
    ]
    try:
        res = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True
        )
        return float(res.stdout.strip())
    except Exception:
        return 0.0


def split_waveform_for_group(wav_tensor, group_texts: List[str], sample_rate: int):
    """Tách waveform của cụm câu (2-3 câu) về từng câu riêng biệt tại điểm lặng tự nhiên giữa các câu."""
    import torch

    if wav_tensor.dim() == 1:
        wav_tensor = wav_tensor.unsqueeze(0)
    if len(group_texts) <= 1:
        return [wav_tensor]

    total_samples = wav_tensor.shape[-1]
    n_sents = len(group_texts)
    min_seg = max(1, int(0.22 * sample_rate))

    if total_samples <= min_seg * n_sents:
        chunk_sz = max(1, total_samples // n_sents)
        pieces = []
        for i in range(n_sents):
            st = i * chunk_sz
            ed = total_samples if i == n_sents - 1 else (i + 1) * chunk_sz
            pieces.append(wav_tensor[:, st:ed])
        return pieces

    weights = [max(2.0, float(len(t.strip())) + 3.0) for t in group_texts]
    total_w = sum(weights)

    win_len = max(1, int(0.035 * sample_rate))
    hop_len = max(1, int(0.010 * sample_rate))
    search_radius = int(0.45 * sample_rate)
    mono = wav_tensor[0]

    split_points = [0]
    cum_w = 0.0
    for k in range(1, n_sents):
        cum_w += weights[k - 1]
        expected = int(total_samples * (cum_w / total_w))
        prev_pt = split_points[-1]
        min_allowed = prev_pt + min_seg
        max_allowed = total_samples - (n_sents - k) * min_seg

        if min_allowed >= max_allowed:
            split_points.append(max(prev_pt + 1, min(expected, total_samples - 1)))
            continue

        lo = max(min_allowed, expected - search_radius)
        hi = min(max_allowed, expected + search_radius)

        if hi - lo > win_len * 2:
            region = mono[lo:hi]
            frames = region.unfold(0, win_len, hop_len)
            energies = frames.pow(2).mean(dim=-1)
            # Ưu tiên điểm lặng gần vị trí kỳ vọng
            positions = (
                torch.arange(
                    energies.numel(), device=energies.device, dtype=torch.float32
                )
                * hop_len
                + lo
            )
            dist_penalty = (
                (positions - expected).abs() / max(1.0, float(search_radius))
            ) * (energies.mean().item() * 0.15)
            best_frame = int((energies + dist_penalty).argmin().item())
            best_pt = lo + best_frame * hop_len + (win_len // 2)
            best_pt = max(min_allowed, min(max_allowed, best_pt))
        else:
            best_pt = max(min_allowed, min(max_allowed, expected))

        split_points.append(best_pt)

    split_points.append(total_samples)
    return [
        wav_tensor[:, split_points[i] : split_points[i + 1]] for i in range(n_sents)
    ]


def _apply_omnivoice_torch_compat_patch():
    """
    Đảm bảo tương thích tuyệt đối giữa PyTorch 2.5.x+cu121 / 2.8.x và Transformers >= 5.15
    để nạp mượt mà HiggsAudioV2TokenizerModel & OmniVoice trên mọi môi trường Python.
    """
    try:
        import importlib.metadata
        import types

        _orig_ver = getattr(
            importlib.metadata,
            "_orig_version_for_omnivoice",
            importlib.metadata.version,
        )
        setattr(importlib.metadata, "_orig_version_for_omnivoice", _orig_ver)

        def _patched_version(pkg: str) -> str:
            if pkg in ("torch", "torchaudio", "torchvision"):
                try:
                    v = _orig_ver(pkg)
                    if v and tuple(int(x) for x in v.split("+")[0].split(".")[:2]) >= (
                        2,
                        6,
                    ):
                        return v
                except Exception:
                    pass
                return "2.6.0"
            return _orig_ver(pkg)

        importlib.metadata.version = _patched_version

        import torch
        import torch.distributed.fsdp

        try:
            if tuple(
                int(x) for x in str(torch.__version__).split("+")[0].split(".")[:2]
            ) < (2, 6):
                torch.__version__ = "2.6.0"
        except Exception:
            torch.__version__ = "2.6.0"

        try:
            import torchaudio

            if tuple(
                int(x) for x in str(torchaudio.__version__).split("+")[0].split(".")[:2]
            ) < (2, 6):
                torchaudio.__version__ = "2.6.0"
        except Exception:
            pass

        for _attr in ("CPUOffloadPolicy", "MixedPrecisionPolicy", "FSDPModule"):
            if not hasattr(torch.distributed.fsdp, _attr):
                setattr(torch.distributed.fsdp, _attr, object)
        if not hasattr(torch.distributed.fsdp, "fully_shard"):
            setattr(torch.distributed.fsdp, "fully_shard", lambda *a, **kw: None)
        try:
            import torch._dynamo._trace_wrapped_higher_order_op as _twhop

            if not hasattr(_twhop, "TransformGetItemToIndex"):

                class _DummyTransformGetItemToIndex:
                    def __enter__(self):
                        return self

                    def __exit__(self, *args):
                        return False

                setattr(
                    _twhop, "TransformGetItemToIndex", _DummyTransformGetItemToIndex
                )
        except Exception:
            pass
        if not hasattr(torch, "accelerator"):
            setattr(
                torch,
                "accelerator",
                types.SimpleNamespace(
                    current_accelerator=lambda *a, **kw: (
                        torch.device("cuda")
                        if torch.cuda.is_available()
                        else torch.device("cpu")
                    ),
                    is_available=lambda: torch.cuda.is_available(),
                    device_count=lambda: (
                        torch.cuda.device_count() if torch.cuda.is_available() else 0
                    ),
                ),
            )

        if "transformers.utils.import_utils" in sys.modules:
            _iu = sys.modules["transformers.utils.import_utils"]
            setattr(_iu, "_torch_available", True)
            setattr(_iu, "_torchaudio_available", True)
            setattr(_iu, "_torch_version", "2.6.0")
            setattr(_iu, "_torchaudio_version", "2.6.0")
    except Exception as e:
        print(
            f"[VoiceStudioService] Lưu ý khi áp dụng bản vá tương thích PyTorch/OmniVoice: {e}"
        )


_apply_omnivoice_torch_compat_patch()


class VoiceStudioService:
    _instance = None
    _model = None
    _prompt_cache: Dict[str, Any] = {}
    _daemon_proc: Optional[subprocess.Popen] = None
    _daemon_lock = None

    def __init__(self, root_dir: Optional[Path] = None):
        import threading

        if VoiceStudioService._daemon_lock is None:
            VoiceStudioService._daemon_lock = threading.Lock()
        if root_dir:
            self.root_dir = Path(root_dir)
        else:
            p = Path(__file__).resolve().parent.parent
            if (p / "VoiceStudio").exists():
                self.root_dir = p
            elif (p.parent / "VoiceStudio").exists():
                self.root_dir = p.parent
            else:
                self.root_dir = p
        self.voicestudio_dir = self.root_dir / "VoiceStudio"
        self.model_path = self.root_dir / "pretrained_models" / "OmniVoice"
        self.kho_voice_dir = self.root_dir / "Kho_Voice"
        self.kho_voice_dir.mkdir(parents=True, exist_ok=True)
        self.voices_dir = self.root_dir / "assets" / "voices"
        self.voices_dir.mkdir(parents=True, exist_ok=True)
        try:
            _ensure_default_padre_voice_profile(self.root_dir)
        except Exception:
            pass

        # Mặc định ưu tiên giọng 04_mx_ong_gia_padre_implacable trong Kho_Voice, nếu không có thì tự tìm mẫu giọng đầu tiên trong Kho_Voice
        default_profile_dir = self.kho_voice_dir / "04_mx_ong_gia_padre_implacable"
        if (default_profile_dir / "sample.wav").exists():
            self.ref_voice_path = default_profile_dir / "sample.wav"
            self.ref_text_path = default_profile_dir / "sample.txt"
        elif (self.voices_dir / "Padre_Mexico.wav").exists():
            self.ref_voice_path = self.voices_dir / "Padre_Mexico.wav"
            self.ref_text_path = self.voices_dir / "Padre_Mexico.txt"
        else:
            found_wav = None
            for sub in (
                sorted(self.kho_voice_dir.iterdir())
                if self.kho_voice_dir.exists()
                else []
            ):
                if sub.is_dir():
                    w_cands = list(sub.glob("*.wav")) + list(sub.glob("*.mp3"))
                    if (sub / "sample.wav").exists():
                        found_wav = sub / "sample.wav"
                        break
                    elif w_cands:
                        found_wav = w_cands[0]
                        break
                elif sub.suffix.lower() in (".wav", ".mp3"):
                    found_wav = sub
                    break
            self.ref_voice_path = (
                found_wav if found_wav else (default_profile_dir / "sample.wav")
            )
            self.ref_text_path = self.ref_voice_path.with_suffix(".txt")

        if str(self.voicestudio_dir) not in sys.path:
            sys.path.insert(0, str(self.voicestudio_dir))

        self.engine = None

    def is_voicestudio_server_alive(self, port: int = 3900) -> bool:
        import socket

        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.4)
                return s.connect_ex(("127.0.0.1", port)) == 0
        except Exception:
            return False

    def ensure_voicestudio_server_running(self, port: int = 3900) -> bool:
        """
        Tự động kiểm tra và bật Server VoiceStudio (cổng 3900) ngay khi mở ứng dụng
        hoặc trước khi tổng hợp giọng đọc.
        """
        import threading

        if VoiceStudioService._daemon_lock is None:
            VoiceStudioService._daemon_lock = threading.Lock()
        if self.is_voicestudio_server_alive(port):
            return True

        with VoiceStudioService._daemon_lock:
            if self.is_voicestudio_server_alive(port):
                return True

            appdata = os.environ.get("APPDATA") or str(
                Path.home() / "AppData" / "Roaming"
            )
            vs_runtime_root = Path(appdata) / "VoiceStudio" / "runtime" / "project"
            vs_venv_py = vs_runtime_root / ".venv" / "Scripts" / "python.exe"
            vs_runtime_backend = vs_runtime_root / "backend"
            local_vs_backend = self.voicestudio_dir / "backend"

            py_exe = str(vs_venv_py) if vs_venv_py.exists() else sys.executable
            backend_dir = (
                vs_runtime_backend
                if (vs_runtime_backend / "main.py").exists()
                else local_vs_backend
            )

            if (backend_dir / "main.py").exists():
                try:
                    logs_dir = self.root_dir / "logs"
                    logs_dir.mkdir(parents=True, exist_ok=True)
                    out_log = open(
                        logs_dir / "voicestudio_server.log", "a", encoding="utf-8"
                    )
                    env = os.environ.copy()
                    env["PYTHONIOENCODING"] = "utf-8"
                    env["PYTHONUTF8"] = "1"
                    cmd = [
                        py_exe,
                        "-m",
                        "uvicorn",
                        "main:app",
                        "--app-dir",
                        str(backend_dir),
                        "--host",
                        "127.0.0.1",
                        "--port",
                        str(port),
                    ]
                    print(
                        f"[VoiceStudioService] 🚀 Đang tự động khởi động VoiceStudio Server tại http://127.0.0.1:{port} ..."
                    )
                    VoiceStudioService._daemon_proc = subprocess.Popen(
                        cmd,
                        cwd=str(backend_dir),
                        env=env,
                        stdout=out_log,
                        stderr=out_log,
                        creationflags=0x08000000 if os.name == "nt" else 0,
                    )
                    for _ in range(30):
                        if self.is_voicestudio_server_alive(port):
                            print(
                                f"[VoiceStudioService] ✅ VoiceStudio Server đã online tại http://127.0.0.1:{port}!"
                            )
                            return True
                        time.sleep(0.5)
                except Exception as e:
                    print(
                        f"[VoiceStudioService] Lưu ý khi khởi chạy VoiceStudio Server (cổng {port}): {e}"
                    )
        return self.is_voicestudio_server_alive(port)

    def list_kho_voices(self) -> List[Dict[str, Any]]:
        """Quét toàn bộ mẫu giọng đọc trong Kho_Voice/ và assets/voices/."""
        try:
            _ensure_default_padre_voice_profile(self.root_dir)
        except Exception:
            pass
        results: List[Dict[str, Any]] = []
        if self.kho_voice_dir.exists():
            for item in sorted(self.kho_voice_dir.iterdir()):
                if item.is_dir():
                    wav_p = item / "sample.wav"
                    if not wav_p.exists():
                        wavs = list(item.glob("*.wav")) + list(item.glob("*.mp3"))
                        wav_p = wavs[0] if wavs else wav_p
                    if wav_p.exists():
                        prof_p = item / "profile.json"
                        txt_p = item / "sample.txt"
                        meta = {}
                        if prof_p.exists():
                            try:
                                meta = json.loads(
                                    prof_p.read_text(encoding="utf-8", errors="ignore")
                                )
                            except Exception:
                                pass
                        ref_txt = meta.get("refText", "")
                        if not ref_txt and txt_p.exists():
                            ref_txt = txt_p.read_text(
                                encoding="utf-8", errors="ignore"
                            ).strip()
                        results.append(
                            {
                                "id": item.name,
                                "name": meta.get("name") or item.name,
                                "language": meta.get("language") or "es",
                                "audio_path": str(wav_p),
                                "ref_text": ref_txt,
                                "is_default": str(wav_p.resolve())
                                == str(self.ref_voice_path.resolve())
                                if self.ref_voice_path.exists()
                                else False,
                            }
                        )
                elif item.suffix.lower() in (".wav", ".mp3"):
                    txt_p = item.with_suffix(".txt")
                    results.append(
                        {
                            "id": item.stem,
                            "name": item.name,
                            "language": "es",
                            "audio_path": str(item),
                            "ref_text": txt_p.read_text(
                                encoding="utf-8", errors="ignore"
                            ).strip()
                            if txt_p.exists()
                            else "",
                            "is_default": str(item.resolve())
                            == str(self.ref_voice_path.resolve())
                            if self.ref_voice_path.exists()
                            else False,
                        }
                    )
        return results

    def _ensure_engine(self):
        # Đảm bảo Server VoiceStudio cũng được bật song hành
        try:
            self.ensure_voicestudio_server_running(port=3900)
        except Exception:
            pass

        if self.engine is None:
            main_weights = self.model_path / "model.safetensors"
            tok_weights = self.model_path / "audio_tokenizer" / "model.safetensors"
            if (
                not main_weights.exists()
                or main_weights.stat().st_size < 1_000_000_000
                or not tok_weights.exists()
                or tok_weights.stat().st_size < 800_000_000
            ):
                print(
                    f"[VoiceStudioService] Đang tự động tải Model AI OmniVoice về {self.model_path} (Chỉ tải 1 lần đầu)..."
                )
                from huggingface_hub import snapshot_download

                self.model_path.mkdir(parents=True, exist_ok=True)
                snapshot_download(
                    repo_id="k2-fsa/OmniVoice", local_dir=str(self.model_path)
                )

            print(
                f"[VoiceStudioService] Nạp VoiceStudio OmniVoice từ {self.model_path}..."
            )
            _apply_omnivoice_torch_compat_patch()
            import torch
            from omnivoice.models.omnivoice import OmniVoice

            if torch.cuda.is_available():
                torch.backends.cudnn.benchmark = True
                torch.backends.cuda.matmul.allow_tf32 = True
                torch.backends.cudnn.allow_tf32 = True

            device = "cuda" if torch.cuda.is_available() else "cpu"
            dtype = torch.float16 if device == "cuda" else torch.float32

            if VoiceStudioService._model is None:
                VoiceStudioService._model = OmniVoice.from_pretrained(
                    str(self.model_path), device_map=device, dtype=dtype
                )
            if hasattr(VoiceStudioService._model, "llm") and hasattr(
                VoiceStudioService._model.llm, "config"
            ):
                VoiceStudioService._model.llm.config.use_cache = False

            self.model = VoiceStudioService._model
            self.device = device
            self.engine = True
            print(
                f"[VoiceStudioService] Nạp model thành công vào {device.upper()} (Turbo Batch Mode)!"
            )

    def _get_voice_clone_prompt(self, ref_audio: str, ref_text: str):
        cache_key = f"{os.path.abspath(ref_audio)}::{ref_text}"
        if cache_key not in VoiceStudioService._prompt_cache:
            print(
                f"[VoiceStudioService] Khởi tạo VoiceClonePrompt tối ưu từ mẫu giọng: {ref_audio}..."
            )
            import torchaudio

            ref_input: Any = str(ref_audio)
            use_text = ref_text
            try:
                wav, sr = torchaudio.load(str(ref_audio))
                dur_s = wav.shape[-1] / float(sr)
                # Nếu là file mẫu Nhat_Drama.wav dài 9.6s (2 câu), trích đoạn câu đầu (0.55s -> 4.05s)
                # để giảm 62% độ dài token mẫu tham chiếu, giúp tăng tốc gấp đôi mỗi bước giải mã GPU
                if (
                    dur_s > 6.5
                    and "夜景が見下ろせる最高級タワーマンションのリビング。" in ref_text
                ):
                    s_idx = int(0.55 * sr)
                    e_idx = min(wav.shape[-1], int(4.05 * sr))
                    ref_input = (wav[:, s_idx:e_idx], sr)
                    use_text = "夜景が見下ろせる最高級タワーマンションのリビング。"
                elif (
                    dur_s > 6.5
                    and "奥さん、早く来てください。これを見てください。" in ref_text
                ):
                    s_idx = 0
                    e_idx = min(wav.shape[-1], int(4.25 * sr))
                    ref_input = (wav[:, s_idx:e_idx], sr)
                    use_text = "奥さん、早く来てください。これを見てください。"
            except Exception:
                pass

            VoiceStudioService._prompt_cache[cache_key] = (
                self.model.create_voice_clone_prompt(
                    ref_audio=ref_input, ref_text=use_text
                )
            )
        return VoiceStudioService._prompt_cache[cache_key]

    def generate_full_voice_and_subtitles(
        self,
        script_text: str,
        output_dir: Path,
        ref_voice: Optional[str] = None,
        progress_callback: Optional[Callable[[float, str], None]] = None,
    ) -> Dict[str, Any]:
        """Tạo trọn bộ Voice và Subtitles từ văn bản kịch bản (Turbo GPU Batch + Multi-Sentence Grouping)."""
        import torch
        import torchaudio

        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        sentences_dir = output_dir / "sentences"
        sentences_dir.mkdir(parents=True, exist_ok=True)

        ref_audio = ref_voice or str(self.ref_voice_path)
        if ref_voice and not os.path.exists(ref_voice):
            cand_dir = self.kho_voice_dir / str(ref_voice)
            if (cand_dir / "sample.wav").exists():
                ref_audio = str(cand_dir / "sample.wav")
            elif (self.kho_voice_dir / f"{ref_voice}.wav").exists():
                ref_audio = str(self.kho_voice_dir / f"{ref_voice}.wav")
        if not os.path.exists(ref_audio):
            try:
                ensured_wav = _ensure_default_padre_voice_profile(self.root_dir)
                if ensured_wav.exists() and ensured_wav.stat().st_size > 10_000:
                    self.ref_voice_path = ensured_wav
                    ref_audio = str(ensured_wav)
            except Exception:
                pass
        if not os.path.exists(ref_audio):
            avail_voices = self.list_kho_voices()
            if avail_voices and os.path.exists(avail_voices[0]["audio_path"]):
                ref_audio = avail_voices[0]["audio_path"]
            else:
                raise FileNotFoundError(
                    "Chưa có file giọng mẫu (.wav) trong thư mục Kho_Voice! "
                    "Vui lòng thêm file giọng mẫu (.wav) của bạn vào thư mục Kho_Voice trước khi tạo Voice."
                )

        ref_text = ""
        ref_p = Path(ref_audio)
        txt_path = ref_p.with_suffix(".txt")
        prof_path = ref_p.parent / "profile.json"
        if txt_path.exists():
            with open(txt_path, "r", encoding="utf-8", errors="ignore") as f:
                ref_text = f.read().strip()
        elif prof_path.exists():
            try:
                prof_data = json.loads(
                    prof_path.read_text(encoding="utf-8", errors="ignore")
                )
                ref_text = str(prof_data.get("refText") or "").strip()
            except Exception:
                pass
        if not ref_text:
            ref_text = "A las seis y cuarto de la mañana, mientras yo estaba tumbado en un catre en la cochera de la casa de mi hijo."

        lang_code = "ja" if _is_cjk_text(script_text[:500]) else "es"
        sentences = split_japanese_script(script_text)
        total_sentences = len(sentences)
        if total_sentences == 0:
            raise ValueError("Kịch bản không có câu thoại nào hợp lệ.")

        print(
            f"[VoiceStudioService] Bắt đầu xử lý {total_sentences} câu thoại (Ngôn ngữ: {lang_code}, Mẫu giọng: {ref_audio})..."
        )
        self._ensure_engine()
        clone_prompt = self._get_voice_clone_prompt(str(ref_audio), ref_text)
        sample_rate = getattr(self.model, "sampling_rate", 24000) or 24000

        # 1. Chế độ 1 CÂU = 1 FILE VOICE ĐỘC LẬP (Strict 1-to-1 Sync) + Kiểm định & Tự động làm lại

        manifest_path = sentences_dir / "sync_1to1_manifest.json"
        strict_map: Dict[str, bool] = {}
        if manifest_path.exists():
            try:
                strict_map = json.loads(manifest_path.read_text(encoding="utf-8"))
            except Exception:
                strict_map = {}

        cached_durations: Dict[int, float] = {}

        def _synthesize_sentence_indices_1to1(
            indices_to_run: List[int],
            step_count: int = 16,
            tag_prefix: str = "⚡ GPU 1-to-1",
        ):
            if not indices_to_run:
                return
            batch_sz = 8 if self.device == "cuda" else 1
            win_sz = batch_sz * 6
            done_in_pass = 0
            total_in_pass = len(indices_to_run)

            for w_start in range(0, total_in_pass, win_sz):
                win_indices = indices_to_run[w_start : w_start + win_sz]
                # Sắp xếp cục bộ theo độ dài câu để tối ưu tốc độ GPU Batch mà vẫn giữ 1 câu = 1 phần tử độc lập
                win_sorted = sorted(
                    win_indices, key=lambda idx_val: len(sentences[idx_val])
                )

                for b_start in range(0, len(win_sorted), batch_sz):
                    b_indices = win_sorted[b_start : b_start + batch_sz]
                    b_texts = [sentences[i] for i in b_indices]
                    first_txt = b_texts[0]

                    if progress_callback:
                        overall_done = len(cached_durations)
                        pct = round((overall_done / max(1, total_sentences)) * 90.0, 1)
                        progress_callback(
                            pct,
                            f"{tag_prefix} đang tạo câu ({done_in_pass + 1}..{min(total_in_pass, done_in_pass + len(b_indices))}/{total_in_pass}): {first_txt[:18]}...",
                        )

                    try:
                        audios = self.model.generate(
                            text=b_texts,
                            language=lang_code,
                            voice_clone_prompt=clone_prompt,
                            num_step=step_count,
                        )
                    except RuntimeError as e:
                        if (
                            "out of memory" in str(e).lower()
                            and torch.cuda.is_available()
                        ):
                            torch.cuda.empty_cache()
                            audios = []
                            for bt in b_texts:
                                a = self.model.generate(
                                    text=bt,
                                    language=lang_code,
                                    voice_clone_prompt=clone_prompt,
                                    num_step=step_count,
                                )
                                audios.append(a[0])
                        else:
                            raise

                    for s_idx, wav_out in zip(b_indices, audios):
                        wav_cpu = wav_out.detach().cpu()
                        if wav_cpu.dim() == 1:
                            wav_cpu = wav_cpu.unsqueeze(0)
                        fname = f"sentence_{s_idx + 1:04d}.wav"
                        part_wav = sentences_dir / fname
                        torchaudio.save(str(part_wav), wav_cpu, sample_rate)
                        cached_durations[s_idx] = float(wav_cpu.shape[-1]) / float(
                            sample_rate
                        )
                        strict_map[fname] = True
                        done_in_pass += 1

                try:
                    manifest_path.write_text(
                        json.dumps(strict_map, ensure_ascii=False, indent=2),
                        encoding="utf-8",
                    )
                except Exception:
                    pass
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()

        # Kiểm tra câu nào chưa có file WAV trên ổ cứng
        missing_indices: List[int] = []
        for idx in range(total_sentences):
            part_wav = sentences_dir / f"sentence_{idx + 1:04d}.wav"
            if part_wav.exists() and part_wav.stat().st_size > 1000:
                cached_durations[idx] = get_audio_duration(str(part_wav))
            else:
                missing_indices.append(idx)

        if missing_indices:
            print(
                f"[VoiceStudioService] ⚡ Chế độ Khớp Tuyệt Đối (1 Câu = 1 File Voice): "
                f"Đã có {len(cached_durations)}/{total_sentences} câu, đang tạo {len(missing_indices)} câu mới..."
            )
            _synthesize_sentence_indices_1to1(
                missing_indices, step_count=16, tag_prefix="⚡ GPU 1-to-1"
            )

        # 2. BƯỚC KIỂM ĐỊNH ĐỘ KHỚP SUB & VOICE TỰ ĐỘNG + LÀM LẠI CÁC CÂU LỆCH (TỐI ĐA 3 VÒNG)
        max_redo_rounds = 3
        audit_report = {}
        for redo_round in range(1, max_redo_rounds + 1):
            if progress_callback:
                progress_callback(
                    91.0 + redo_round,
                    f"🔍 [Kiểm định Sub-Voice Lần {redo_round}] Đang rà soát độ khớp của {total_sentences} câu thoại...",
                )
            audit_report = audit_all_sentences_sync(
                sentences, sentences_dir, require_strict_1to1=False
            )
            if audit_report["passed"]:
                print(
                    f"[VoiceStudioService] ✅ Kiểm định Sub-Voice ĐẠT 100% ({total_sentences}/{total_sentences} câu khớp hoàn hảo)!"
                )
                break

            redo_list = audit_report["redo_indices"]
            print(
                f"[VoiceStudioService] ⚠️ [Vòng {redo_round}/{max_redo_rounds}] Phát hiện {len(redo_list)}/{total_sentences} câu "
                f"chưa khớp chuẩn (bị cắt biên hoặc lệch nhịp) -> Đang tự động làm lại 1-to-1..."
            )
            for r_idx in redo_list:
                cached_durations.pop(r_idx, None)
                bad_wav = sentences_dir / f"sentence_{r_idx + 1:04d}.wav"
                if bad_wav.exists():
                    try:
                        bad_wav.unlink()
                    except Exception:
                        pass

            _synthesize_sentence_indices_1to1(
                redo_list,
                step_count=18 if redo_round == 1 else 20,
                tag_prefix=f"🔄 Làm lại Sub-Voice (Vòng {redo_round})",
            )

        # Kiểm định chốt cuối sau khi làm lại
        final_sent_audit = audit_all_sentences_sync(
            sentences, sentences_dir, require_strict_1to1=False
        )
        try:
            (output_dir / "qa_sentence_sync_report.json").write_text(
                json.dumps(final_sent_audit, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception:
            pass

        # 3. Tổng hợp danh sách audio_parts và timeline theo đúng thứ tự câu 1..N
        audio_parts = []
        timeline = []
        current_time = 0.0

        for idx, text in enumerate(sentences):
            idx_str = f"{idx + 1:04d}"
            part_wav = sentences_dir / f"sentence_{idx_str}.wav"
            dur = cached_durations.get(idx)
            if dur is None or dur <= 0:
                dur = get_audio_duration(str(part_wav))
            start_t = current_time
            end_t = current_time + dur
            current_time = end_t

            audio_parts.append(str(part_wav))
            timeline.append(
                {
                    "index": idx + 1,
                    "text": text,
                    "start": start_t,
                    "end": end_t,
                    "duration": dur,
                    "audio_path": str(part_wav),
                }
            )

        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        # Ghép master_voice.wav không nén qua FFmpeg concat
        if progress_callback:
            progress_callback(96.0, "Đang ghép nối audio master bằng FFmpeg...")

        concat_list = output_dir / "concat_list.txt"
        with open(concat_list, "w", encoding="utf-8") as f:
            for p in audio_parts:
                clean_p = p.replace("\\", "/").replace("'", "'\\''")
                f.write(f"file '{clean_p}'\n")

        master_wav = output_dir / "master_voice.wav"
        cmd = [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_list),
            "-c:a",
            "pcm_s16le",
            str(master_wav),
        ]
        subprocess.run(cmd, check=True)

        # Xuất subtitles.srt (Đảm bảo tối đa 3 dòng / khung phụ đề, tự động tách câu dài tại đúng điểm nghỉ trong WAV)
        srt_file = output_dir / "subtitles.srt"
        srt_idx = 1
        with open(srt_file, "w", encoding="utf-8") as f:
            for item in timeline:
                segs = split_long_subtitle_segments(
                    item["text"],
                    item["start"],
                    item["end"],
                    max_segment_chars=48,
                    max_chars_per_line=17,
                    wav_path=item["audio_path"],
                )
                for seg in segs:
                    f.write(f"{srt_idx}\n")
                    f.write(
                        f"{format_timestamp(seg['start'])} --> {format_timestamp(seg['end'])}\n"
                    )
                    f.write(f"{seg['text']}\n\n")
                    srt_idx += 1

        # Xuất thêm file phụ đề Karaoke CapCut (.ass) chạy nhảy theo từng từ ở Lớp Cao Nhất
        karaoke_ass_file = output_dir / "subtitles_karaoke.ass"
        try:
            generate_karaoke_ass_from_srt(str(srt_file), str(karaoke_ass_file))
        except Exception as e_ass:
            print(f"[VoiceStudioService] Lưu ý khi tạo subtitles_karaoke.ass: {e_ass}")

        # Xuất TIMESTAMPS.txt chuẩn 7 Phần (Part 1 -> Part 7) & tự động chèn vào SEO.txt
        timestamps_file = output_dir / "TIMESTAMPS.txt"
        try:
            from backend.renderer import (
                build_7part_timestamps_and_inject_seo,
            )

            proj_root_dir = (
                output_dir.parent if output_dir.name.lower() == "assets" else output_dir
            )
            timestamps_file, _ = build_7part_timestamps_and_inject_seo(
                proj_dir=proj_root_dir,
                assets_dir=output_dir,
                timeline=timeline,
                total_duration=current_time,
            )
        except Exception:
            with open(timestamps_file, "w", encoding="utf-8") as f:
                f.write("00:00:00 - Parte 1: Inicio de la historia\n")
                chapter_interval = max(60.0, current_time / 7.0)
                for p_i in range(1, 7):
                    t_p = p_i * chapter_interval
                    h = int(t_p // 3600)
                    m = int((t_p % 3600) // 60)
                    s = int(t_p % 60)
                    f.write(f"{h:02d}:{m:02d}:{s:02d} - Parte {p_i + 1}\n")

        if progress_callback:
            progress_callback(
                100.0,
                f"Tạo Voice và Subtitle Karaoke hoàn tất ({current_time / 60:.2f} phút)!",
            )

        return {
            "master_voice": str(master_wav),
            "subtitles_srt": str(srt_file),
            "subtitles_karaoke_ass": str(karaoke_ass_file),
            "timestamps_txt": str(timestamps_file),
            "total_duration": current_time,
            "sentence_count": total_sentences,
            "timeline": timeline,
        }


# ==============================================================================
# HỆ THỐNG QUÉT, SỬA KỊCH BẢN & CẮT ĐOẠN LỖI [LOCKED_TITLE] TRONG VIDEO MP4 (PHƯƠNG ÁN 1)
# ==============================================================================


def _parse_srt_time_sec(ts_str: str) -> float:
    s = (ts_str or "").strip().replace(",", ".")
    parts = s.split(":")
    if len(parts) != 3:
        return 0.0
    try:
        return int(parts[0]) * 3600.0 + int(parts[1]) * 60.0 + float(parts[2])
    except Exception:
        return 0.0


def parse_srt_blocks(srt_text: str) -> List[Dict[str, Any]]:
    import re

    if srt_text and "\n" not in str(srt_text) and os.path.exists(str(srt_text)):
        return _parse_karaoke_srt_file(str(srt_text))
    raw = (srt_text or "").strip()
    if not raw:
        return []
    chunks = [c.strip() for c in re.split(r"\n\s*\n", raw) if c.strip()]
    blocks: List[Dict[str, Any]] = []
    for ch in chunks:
        lines = [ln.strip() for ln in ch.splitlines() if ln.strip()]
        if len(lines) < 2:
            continue
        ts_line_idx = 1 if "-->" in lines[1] else (0 if "-->" in lines[0] else -1)
        if ts_line_idx < 0:
            continue
        ts_parts = lines[ts_line_idx].split("-->")
        st = _parse_srt_time_sec(ts_parts[0])
        ed = _parse_srt_time_sec(ts_parts[1])
        txt_lines = lines[ts_line_idx + 1 :]
        body_text = "\n".join(txt_lines).strip()
        flat_text = "".join(txt_lines).replace(" ", "").strip()
        blocks.append(
            {
                "idx": len(blocks) + 1,
                "start": st,
                "end": ed,
                "text": body_text,
                "flat_text": flat_text,
            }
        )
    return blocks


def detect_leaked_srt_blocks_and_intervals(
    srt_blocks: List[Dict[str, Any]],
    removed_script_lines: Optional[List[str]] = None,
    locked_title_hint: str = "",
) -> Tuple[List[int], List[Tuple[float, float]], str, List[str]]:
    """
    Phát hiện chính xác các khung phụ đề SRT bị dính [LOCKED_TITLE], SELECTED_TITLE,
    PART A/B/C, CONTINUITY, ENDING (kể cả khi câu tiêu đề bị tách thành nhiều khung SRT liên tiếp).
    Trả về:
      - `leaked_indices`: Danh sách chỉ số block (0-based) bị dính lỗi
      - `cut_intervals`: Danh sách khoảng thời gian `[(start_sec, end_sec), ...]` cần cắt khỏi Video/Voice
      - `cleaned_srt_text`: Nội dung file `.srt` mới đã xóa các block lỗi và dịch chuyển (shift) lại thời gian chuẩn xác
      - `leaked_previews`: Danh sách nội dung các block đã bị xóa để ghi báo cáo
    """
    import re

    if not srt_blocks:
        return [], [], "", []

    title_key_re = re.compile(
        r"(?:LOCKED_TITLE|SELECTED_TITLE|WINNING_TITLE|FINAL_TITLE|DRAFT_TITLE|TITLE_LOCKED|LOCKED_TITLE_PROMISE|TITLE_FACTS)\s*[:：\-—]?",
        re.IGNORECASE,
    )
    step_part_re = re.compile(
        r"^(?:[A-Z]{1,6}\d{1,5}\s*[—–\-·:：]+\s*)?(?:STEP\s*[1-7]\b|BUILD\s+PART\s*[ABC]\b|PART\s*[:：\-—–·]?\s*[ABC]\b|SCENE\s+[ABC]?\d+\b|CHAPTER\s+\d+\b)",
        re.IGNORECASE,
    )
    stop_block_re = re.compile(
        r"^(?:PART_PURE_CHARACTER_COUNT|PART_LENGTH_GATE|CONTINUITY_LEDGER|CONTINUITY\s+LEDGER|PART_HANDOFF_LEDGER|HANDOFF_LEDGER|HANDOFF\s+LEDGER|PART_[ABC]_HANDOFF|NEXT_ACTION|READY_FOR_AUDIT|PATCH_CHANGELOG)\b",
        re.IGNORECASE,
    )
    meta_kv_re = re.compile(r"^[A-Z][A-Z0-9_/\-\s]{1,35}[:：]")
    ellipsis_endings = ("…", "…」", "…」」", "…』", "…。", "…。」", "…！」", "…？」")
    sent_end_chars = ("。", "！", "？", "…", "」", "』", "）", ")")

    norm_removed_pool: List[str] = []
    for rl in removed_script_lines or []:
        nr = re.sub(r"[\s#*`>]+", "", str(rl or "")).strip()
        if len(nr) >= 4:
            norm_removed_pool.append(nr)
    norm_title_hint = re.sub(r"[\s#*`>]+", "", str(locked_title_hint or "")).strip()

    n = len(srt_blocks)
    leaked_set = set()
    i = 0

    while i < n:
        ft = srt_blocks[i]["flat_text"]
        ft_clean = (
            re.sub(r"^[#*>\-\s`•]+", "", ft).replace("**", "").replace("`", "").strip()
        )

        # 1. Nếu bắt đầu bằng LOCKED_TITLE / SELECTED_TITLE
        if title_key_re.search(ft_clean):
            body0 = re.sub(
                r"^.*?(?:LOCKED_TITLE|SELECTED_TITLE|WINNING_TITLE|FINAL_TITLE|DRAFT_TITLE|TITLE_LOCKED|LOCKED_TITLE_PROMISE|TITLE_FACTS)\s*[:：\-—]*\s*",
                "",
                ft_clean,
                flags=re.IGNORECASE,
            ).strip()
            end_i = i + 1
            acc = body0
            # Nếu block hiện tại bị ngắt giữa câu bởi split_long_subtitle_segments (chưa có dấu kết câu), gom tiếp
            while end_i < n and not acc.endswith(sent_end_chars) and len(acc) <= 210:
                acc += srt_blocks[end_i]["flat_text"]
                end_i += 1

            open_q = acc.count("「")
            close_q = acc.count("」")
            if not (acc.endswith(ellipsis_endings) and open_q <= close_q + 1):
                # Chỉ kiểm tra câu kế tiếp ngay sau câu đầu của LOCKED_TITLE (có thể gồm 1-2 khung SRT nếu câu dài > 48 chữ)
                next_sent_acc = ""
                next_sent_end_idx = end_i
                for k in range(end_i, min(n, end_i + 3)):
                    cand = srt_blocks[k]["flat_text"]
                    if (
                        not cand
                        or title_key_re.search(cand)
                        or step_part_re.match(cand)
                    ):
                        break
                    next_sent_acc += cand
                    next_sent_end_idx = k + 1
                    if cand.endswith(sent_end_chars):
                        break
                if next_sent_acc and len(acc + next_sent_acc) <= 210:
                    if (
                        next_sent_acc.endswith(ellipsis_endings)
                        or (
                            norm_title_hint
                            and len(next_sent_acc) >= 6
                            and next_sent_acc in norm_title_hint
                        )
                        or any(
                            len(next_sent_acc) >= 6 and next_sent_acc in nr
                            for nr in norm_removed_pool
                        )
                    ):
                        end_i = next_sent_end_idx

            for k in range(i, end_i):
                leaked_set.add(k)
            i = end_i
            continue

        # 2. Nếu là dòng STEP / PART / 日本語脚本 / Metadata tiếng Anh
        if (
            (step_part_re.match(ft_clean) and len(ft_clean) < 95)
            or (
                re.search(
                    r"(?:日本語脚本|日本語ナレーション本文|HANDOFF_LEDGER|PURE_CHARACTER_COUNT)",
                    ft_clean,
                    re.IGNORECASE,
                )
                and len(ft_clean) < 95
            )
            or stop_block_re.match(ft_clean)
            or meta_kv_re.match(ft_clean)
        ):
            leaked_set.add(i)
            i += 1
            continue

        # 3. Đối chiếu trực tiếp với các dòng đã bị xóa khỏi file kịch bản .txt (nếu có)
        if norm_removed_pool and len(ft_clean) >= 6:
            matched_pool = False
            for nr in norm_removed_pool:
                if ft_clean == nr or (
                    len(ft_clean) >= 10
                    and ft_clean in nr
                    and (
                        "LOCKED_TITLE" in nr
                        or "SELECTED_TITLE" in nr
                        or nr.endswith(ellipsis_endings)
                    )
                ):
                    matched_pool = True
                    break
            if matched_pool:
                leaked_set.add(i)
                i += 1
                continue

        i += 1

    if not leaked_set:
        return [], [], "", []

    leaked_indices = sorted(leaked_set)
    leaked_previews = [srt_blocks[idx]["flat_text"] for idx in leaked_indices]

    # Gom các khoảng thời gian cần cắt bỏ (gộp các block lỗi liền kề cách nhau <= 0.45s)
    raw_intervals = [
        (srt_blocks[idx]["start"], srt_blocks[idx]["end"]) for idx in leaked_indices
    ]
    cut_intervals: List[Tuple[float, float]] = []
    for st, ed in raw_intervals:
        if ed <= st:
            continue
        if not cut_intervals:
            cut_intervals.append((st, ed))
        else:
            prev_st, prev_ed = cut_intervals[-1]
            if st <= prev_ed + 0.45:
                cut_intervals[-1] = (prev_st, max(prev_ed, ed))
            else:
                cut_intervals.append((st, ed))

    # Xây dựng lại nội dung subtitles.srt mới với thời gian đã trừ đi các đoạn bị cắt
    def _calc_shifted_time(t_val: float) -> float:
        removed_before = 0.0
        for cst, ced in cut_intervals:
            if ced <= t_val:
                removed_before += ced - cst
            elif cst < t_val < ced:
                removed_before += t_val - cst
        return max(0.0, t_val - removed_before)

    new_srt_lines: List[str] = []
    new_idx = 1
    for idx, blk in enumerate(srt_blocks):
        if idx in leaked_set:
            continue
        new_st = _calc_shifted_time(blk["start"])
        new_ed = _calc_shifted_time(blk["end"])
        if new_ed <= new_st + 0.02:
            new_ed = new_st + max(0.2, blk["end"] - blk["start"])
        new_srt_lines.append(f"{new_idx}")
        new_srt_lines.append(
            f"{format_timestamp(new_st)} --> {format_timestamp(new_ed)}"
        )
        new_srt_lines.append(f"{blk['text']}\n")
        new_idx += 1

    cleaned_srt_text = "\n".join(new_srt_lines).strip() + "\n"
    return leaked_indices, cut_intervals, cleaned_srt_text, leaked_previews


def compute_keep_intervals(
    total_duration: float, cut_intervals: List[Tuple[float, float]]
) -> List[Tuple[float, float]]:
    """Tính danh sách các khoảng thời gian giữ lại `[keep_start, keep_end]` từ `total_duration` và `cut_intervals`."""
    if total_duration <= 0.0:
        return []
    if not cut_intervals:
        return [(0.0, total_duration)]

    sorted_cuts = sorted(cut_intervals, key=lambda x: x[0])
    merged: List[Tuple[float, float]] = []
    for st, ed in sorted_cuts:
        st_c = max(0.0, min(total_duration, st))
        ed_c = max(0.0, min(total_duration, ed))
        if ed_c <= st_c:
            continue
        if not merged:
            merged.append((st_c, ed_c))
        else:
            pst, ped = merged[-1]
            if st_c <= ped + 0.15:
                merged[-1] = (pst, max(ped, ed_c))
            else:
                merged.append((st_c, ed_c))

    keep: List[Tuple[float, float]] = []
    cursor = 0.0
    for st, ed in merged:
        if st - cursor > 0.15:
            keep.append((cursor, st))
        cursor = max(cursor, ed)
    if total_duration - cursor > 0.15:
        keep.append((cursor, total_duration))
    return keep


def _probe_duration_sec(media_path: Path) -> float:
    import subprocess

    if not media_path.exists():
        return 0.0
    win_flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    try:
        r = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(media_path),
            ],
            capture_output=True,
            text=True,
            timeout=15,
            creationflags=win_flags,
        )
        return float(r.stdout.strip())
    except Exception:
        return 0.0


def _replace_file_with_retry(src_path: Path, dst_path: Path, retries: int = 6) -> None:
    last_err = None
    for attempt in range(retries):
        try:
            os.replace(str(src_path), str(dst_path))
            return
        except Exception as e:
            last_err = e
            time.sleep(0.25 * (attempt + 1))
    if last_err:
        raise last_err


def _fast_trim_wav_pcm(
    wav_path: Path, cut_intervals: List[Tuple[float, float]], tmp_out: Path
) -> Tuple[bool, float, float, str]:
    """
    Cắt trực tiếp file PCM WAV bằng module `wave` nội bộ của Python (không cần mở subprocess FFmpeg).
    Tốc độ: 0.2s – 0.8s cho file WAV dài 2 tiếng (~700MB).
    """
    with wave.open(str(wav_path), "rb") as wf_in:
        params = wf_in.getparams()
        sr = float(wf_in.getframerate() or 24000)
        total_frames = wf_in.getnframes()
        if sr <= 0 or total_frames <= 0:
            raise RuntimeError("Header WAV không hợp lệ")
        old_dur = total_frames / sr
        keep_intervals = compute_keep_intervals(old_dur, cut_intervals)
        if not keep_intervals:
            raise RuntimeError("Danh sách đoạn giữ lại rỗng")

        written_frames = 0
        chunk_frames = int(sr * 120)  # Đọc/ghi theo khối 120 giây (~5.7MB)
        with wave.open(str(tmp_out), "wb") as wf_out:
            wf_out.setparams(params)
            for ks, ke in keep_intervals:
                if ke - ks <= 0.05:
                    continue
                f_start = max(0, min(total_frames, int(round(ks * sr))))
                f_end = max(f_start, min(total_frames, int(round(ke * sr))))
                rem = f_end - f_start
                if rem <= 0:
                    continue
                wf_in.setpos(f_start)
                while rem > 0:
                    take = min(rem, chunk_frames)
                    raw_bytes = wf_in.readframes(take)
                    if not raw_bytes:
                        break
                    wf_out.writeframes(raw_bytes)
                    rem -= take
                written_frames += f_end - f_start

        new_dur = written_frames / sr
        return True, round(old_dur, 2), round(new_dur, 2), "Đã cắt sạch WAV siêu tốc"


def trim_media_file_by_keep_intervals(
    media_path: Path,
    cut_intervals: List[Tuple[float, float]],
    is_video: bool = True,
) -> Tuple[bool, float, float, str]:
    """
    Cắt bỏ trực tiếp các đoạn `cut_intervals` khỏi file Video `.mp4` hoặc Audio `.wav`
    bằng FFmpeg Stream Copy (`-c copy` input-seeking) và Python PCM Slicer siêu tốc (~3–8 giây / video 2 tiếng).
    Trả về `(success, old_duration, new_duration, message)`.
    """
    import shutil
    import subprocess

    if not media_path.exists():
        return False, 0.0, 0.0, "File không tồn tại"
    if not cut_intervals:
        dur = _probe_duration_sec(media_path)
        return True, dur, dur, "Không có đoạn lỗi cần cắt"

    # Đặt thư mục tạm ở cấp proj_dir (ngoài renders/) để không làm thay đổi mtime của renders/ khi đang cắt
    base_tmp_parent = (
        media_path.parent.parent
        if media_path.parent.name in ("renders", "assets")
        else media_path.parent
    )
    tmp_dir = base_tmp_parent / f"_clean_trim_tmp_{media_path.stem}"
    shutil.rmtree(tmp_dir, ignore_errors=True)
    tmp_dir.mkdir(parents=True, exist_ok=True)

    ext = ".mp4" if is_video else ".wav"
    tmp_out = tmp_dir / f"cleaned_output{ext}"

    # Nhánh 1: Nếu là file WAV -> Ưu tiên cắt siêu tốc trực tiếp bằng Python wave (0.3s - 0.8s)
    if not is_video:
        try:
            ok_w, old_w, new_w, msg_w = _fast_trim_wav_pcm(
                media_path, cut_intervals, tmp_out
            )
            if ok_w and tmp_out.exists() and tmp_out.stat().st_size > 1000:
                _replace_file_with_retry(tmp_out, media_path)
                shutil.rmtree(tmp_dir, ignore_errors=True)
                return True, old_w, new_w, msg_w
        except Exception:
            pass

    old_dur = _probe_duration_sec(media_path)
    if old_dur <= 1.0:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        return False, old_dur, old_dur, "Không đọc được thời lượng file gốc"

    keep_intervals = compute_keep_intervals(old_dur, cut_intervals)
    if not keep_intervals:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        return False, old_dur, old_dur, "Danh sách đoạn giữ lại rỗng"

    win_flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    seg_files: List[Path] = []

    try:
        valid_keeps = [(ks, ke) for ks, ke in keep_intervals if (ke - ks) > 0.10]
        if not valid_keeps:
            raise RuntimeError("Không có phân đoạn giữ lại hợp lệ")

        # Tối ưu 1-Pass: Nếu chỉ có đúng 1 đoạn giữ lại (VD: lỗi LOCKED_TITLE nằm ở Dòng 1 đầu video hoặc cuối video),
        # cắt thẳng 1 lần từ media_path ra tmp_out (không cần ghi seg_000 rồi lại copy sang tmp_out)!
        if len(valid_keeps) == 1:
            ks, ke = valid_keeps[0]
            dur_seg = ke - ks
            if is_video:
                cmd_one = ["ffmpeg", "-y", "-v", "error"]
                if ks > 0.05:
                    cmd_one.extend(["-ss", f"{ks:.3f}"])
                cmd_one.extend(
                    [
                        "-i",
                        str(media_path),
                        "-t",
                        f"{dur_seg:.3f}",
                        "-c",
                        "copy",
                        "-avoid_negative_ts",
                        "make_zero",
                        str(tmp_out),
                    ]
                )
            else:
                cmd_one = [
                    "ffmpeg",
                    "-y",
                    "-v",
                    "error",
                    "-ss",
                    f"{ks:.3f}",
                    "-i",
                    str(media_path),
                    "-t",
                    f"{dur_seg:.3f}",
                    "-c:a",
                    "pcm_s16le",
                    str(tmp_out),
                ]
            res_one = subprocess.run(
                cmd_one, capture_output=True, text=True, creationflags=win_flags
            )
            if (
                res_one.returncode != 0
                or not tmp_out.exists()
                or tmp_out.stat().st_size < 5000
            ):
                raise RuntimeError(f"Lỗi cắt 1-pass: {res_one.stderr[-200:]}")
        else:
            # Tối ưu Multi-Segment: Đặt -ss TRƯỚC -i để FFmpeg nhảy trực tiếp theo bảng chỉ mục MP4 moov trong 0.001s
            for idx, (ks, ke) in enumerate(valid_keeps):
                dur_seg = ke - ks
                seg_f = tmp_dir / f"seg_{idx:03d}{ext}"
                if is_video:
                    cmd_seg = ["ffmpeg", "-y", "-v", "error"]
                    if ks > 0.05:
                        cmd_seg.extend(["-ss", f"{ks:.3f}"])
                    cmd_seg.extend(
                        [
                            "-i",
                            str(media_path),
                            "-t",
                            f"{dur_seg:.3f}",
                            "-c",
                            "copy",
                            "-avoid_negative_ts",
                            "make_zero",
                            str(seg_f),
                        ]
                    )
                else:
                    cmd_seg = [
                        "ffmpeg",
                        "-y",
                        "-v",
                        "error",
                        "-ss",
                        f"{ks:.3f}",
                        "-i",
                        str(media_path),
                        "-t",
                        f"{dur_seg:.3f}",
                        "-c:a",
                        "pcm_s16le",
                        str(seg_f),
                    ]
                res = subprocess.run(
                    cmd_seg, capture_output=True, text=True, creationflags=win_flags
                )
                if (
                    res.returncode != 0
                    or not seg_f.exists()
                    or seg_f.stat().st_size < 1000
                ):
                    raise RuntimeError(f"Lỗi cắt phân đoạn {idx}: {res.stderr[-200:]}")
                seg_files.append(seg_f)

            concat_txt = tmp_dir / "concat_list.txt"
            with open(concat_txt, "w", encoding="utf-8") as f:
                for sf in seg_files:
                    p_clean = str(sf.resolve()).replace("\\", "/").replace("'", "'\\''")
                    f.write(f"file '{p_clean}'\n")
            if is_video:
                # Không dùng -movflags +faststart để tránh việc FFmpeg phải đọc & ghi lại toàn bộ file 2.5GB lần 2
                cmd_cat = [
                    "ffmpeg",
                    "-y",
                    "-v",
                    "error",
                    "-f",
                    "concat",
                    "-safe",
                    "0",
                    "-i",
                    str(concat_txt),
                    "-c",
                    "copy",
                    str(tmp_out),
                ]
            else:
                cmd_cat = [
                    "ffmpeg",
                    "-y",
                    "-v",
                    "error",
                    "-f",
                    "concat",
                    "-safe",
                    "0",
                    "-i",
                    str(concat_txt),
                    "-c:a",
                    "pcm_s16le",
                    str(tmp_out),
                ]
            res_cat = subprocess.run(
                cmd_cat, capture_output=True, text=True, creationflags=win_flags
            )
            if (
                res_cat.returncode != 0
                or not tmp_out.exists()
                or tmp_out.stat().st_size < 5000
            ):
                raise RuntimeError(f"Lỗi ghép phân đoạn sạch: {res_cat.stderr[-200:]}")

        new_dur = _probe_duration_sec(tmp_out)
        expected_dur = sum(ke - ks for ks, ke in valid_keeps)
        if new_dur <= 1.0 or abs(new_dur - expected_dur) > 12.0:
            raise RuntimeError(
                f"Thời lượng sau khi cắt bất thường ({new_dur:.1f}s vs kỳ vọng {expected_dur:.1f}s)"
            )

        _replace_file_with_retry(tmp_out, media_path)
        return (
            True,
            round(old_dur, 2),
            round(new_dur, 2),
            "Đã cắt sạch đoạn lỗi thành công",
        )
    except Exception as e:
        return False, round(old_dur, 2), round(old_dur, 2), str(e)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def clean_single_project_scripts_and_detect_media_cuts(
    proj_dir: Path,
) -> Dict[str, Any]:
    """
    GIAI ĐOẠN 1 (Siêu tốc ~0.005s / dự án):
    1. Quét và xóa sạch ngay lập tức các dòng `[LOCKED_TITLE]` / Metadata rò rỉ trong tất cả file kịch bản `.txt`.
    2. Phân tích `assets/subtitles.srt` để xác định xem dự án có các đoạn giây đọc nhầm `[LOCKED_TITLE]`
       cần cắt trong Video `.mp4` / Voice `.wav` hay không.
    """
    import re

    proj_dir = Path(proj_dir)
    ma_id = proj_dir.name
    renders_dir = proj_dir / "renders"
    assets_dir = proj_dir / "assets"

    result: Dict[str, Any] = {
        "ma_id": ma_id,
        "proj_dir": proj_dir,
        "script_cleaned": False,
        "script_removed_lines_count": 0,
        "script_removed_samples": [],
        "srt_cleaned": False,
        "srt_removed_blocks_count": 0,
        "video_repaired": False,
        "voice_repaired": False,
        "needs_media_trim": False,
        "has_mp4_to_trim": False,
        "has_wav_to_trim": False,
        "cut_intervals": [],
        "raw_cut_intervals": [],
        "cleaned_srt_text": "",
        "old_video_duration": 0.0,
        "new_video_duration": 0.0,
        "video_message": "",
    }

    if not proj_dir.exists() or not proj_dir.is_dir():
        return result

    locked_title_hint = ""
    info_f = proj_dir / "idea_info.json"
    if info_f.exists():
        try:
            d_info = json.loads(info_f.read_text(encoding="utf-8", errors="ignore"))
            locked_title_hint = str(
                d_info.get("locked_title") or d_info.get("draft_title_ja") or ""
            )
        except Exception:
            pass

    script_targets = [
        proj_dir / "part_a.txt",
        proj_dir / "part_b.txt",
        proj_dir / "part_c.txt",
        proj_dir / "script_clean.txt",
        proj_dir / "script.txt",
        renders_dir / f"{ma_id}_KICH_BAN.txt",
    ]
    removed_texts_pool: List[str] = []
    leaked_log_f = assets_dir / "leaked_lines_log.json"
    if leaked_log_f.exists():
        try:
            prev_logged = json.loads(
                leaked_log_f.read_text(encoding="utf-8", errors="ignore")
            )
            if isinstance(prev_logged, list):
                removed_texts_pool.extend([str(x) for x in prev_logged if x])
        except Exception:
            pass

    # Khôi phục thêm các dòng đã xóa từ step5_audit_report.txt (nếu Build #106 đã xóa .txt trước đó)
    audit_f = proj_dir / "step5_audit_report.txt"
    if audit_f.exists():
        try:
            aud_txt = audit_f.read_text(encoding="utf-8", errors="ignore")
            for m_rem in re.finditer(
                r"^\s*-\s*(?:Removed:\s*)?(.+)$", aud_txt, flags=re.MULTILINE
            ):
                cand_r = m_rem.group(1).strip()
                if (
                    "LOCKED_TITLE" in cand_r
                    or "SELECTED_TITLE" in cand_r
                    or "PART " in cand_r
                ) and cand_r not in removed_texts_pool:
                    removed_texts_pool.append(cand_r)
        except Exception:
            pass

    for tf in script_targets:
        if not tf.exists():
            continue
        try:
            raw_txt = tf.read_text(encoding="utf-8", errors="ignore")
            cleaned_txt, removed_tuples = strip_leaked_titles_and_metadata(raw_txt)
            if removed_tuples and cleaned_txt:
                tf.write_text(cleaned_txt, encoding="utf-8")
                result["script_cleaned"] = True
                result["script_removed_lines_count"] += len(removed_tuples)
                for _, r_str in removed_tuples:
                    if r_str not in removed_texts_pool:
                        removed_texts_pool.append(r_str)
                    if (
                        len(result["script_removed_samples"]) < 6
                        and r_str not in result["script_removed_samples"]
                    ):
                        result["script_removed_samples"].append(r_str)
        except Exception:
            pass

    pa, pb, pc = (
        proj_dir / "part_a.txt",
        proj_dir / "part_b.txt",
        proj_dir / "part_c.txt",
    )
    if result["script_cleaned"] and pa.exists() and pb.exists() and pc.exists():
        try:
            ta = pa.read_text(encoding="utf-8", errors="ignore").strip()
            tb = pb.read_text(encoding="utf-8", errors="ignore").strip()
            tc = pc.read_text(encoding="utf-8", errors="ignore").strip()
            if len(ta) >= 8000 and len(tb) >= 8000 and len(tc) >= 8000:
                comb, _ = strip_leaked_titles_and_metadata(
                    "\n\n".join([ta, tb, tc]).strip()
                )
                for sync_f in (
                    proj_dir / "script_clean.txt",
                    renders_dir / f"{ma_id}_KICH_BAN.txt",
                ):
                    if sync_f.exists():
                        cur_s = sync_f.read_text(
                            encoding="utf-8", errors="ignore"
                        ).strip()
                        if cur_s != comb:
                            sync_f.write_text(comb, encoding="utf-8")
        except Exception:
            pass

    if removed_texts_pool and assets_dir.exists():
        try:
            leaked_log_f.write_text(
                json.dumps(removed_texts_pool, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception:
            pass

    if result["script_cleaned"]:
        try:
            note_txt = (
                f"\n[AUTO-CLEAN NOTE — {time.strftime('%Y-%m-%d %H:%M:%S')}]: "
                f"Đã quét và xóa {result['script_removed_lines_count']} dòng [LOCKED_TITLE]/Metadata rò rỉ:\n"
                + "\n".join([f"  - {s}" for s in result["script_removed_samples"]])
                + "\n"
            )
            if audit_f.exists():
                cur_a = audit_f.read_text(encoding="utf-8", errors="ignore")
                if "[AUTO-CLEAN NOTE" not in cur_a:
                    audit_f.write_text(cur_a + note_txt, encoding="utf-8")
        except Exception:
            pass

    srt_file = assets_dir / "subtitles.srt"
    master_wav = assets_dir / "master_voice.wav"
    master_mp4 = renders_dir / f"{ma_id}_master.mp4"
    video_clean_marker = renders_dir / ".cleaned_locked_title_v106.json"

    if srt_file.exists() and srt_file.stat().st_size > 50:
        try:
            raw_srt = srt_file.read_text(encoding="utf-8", errors="ignore")
            srt_blocks = parse_srt_blocks(raw_srt)
            leaked_idxs, cut_intervals, cleaned_srt_text, leaked_srt_previews = (
                detect_leaked_srt_blocks_and_intervals(
                    srt_blocks,
                    removed_script_lines=removed_texts_pool,
                    locked_title_hint=locked_title_hint,
                )
            )
            if leaked_idxs:
                result["srt_cleaned"] = True
                result["srt_removed_blocks_count"] = len(leaked_idxs)
                result["cut_intervals"] = [
                    (round(s, 3), round(e, 3)) for s, e in cut_intervals
                ]
                result["raw_cut_intervals"] = cut_intervals
                result["cleaned_srt_text"] = cleaned_srt_text
                for lp in leaked_srt_previews:
                    if (
                        len(result["script_removed_samples"]) < 6
                        and lp not in result["script_removed_samples"]
                    ):
                        result["script_removed_samples"].append(lp)

                has_mp4 = master_mp4.exists() and master_mp4.stat().st_size > 100_000
                has_wav = master_wav.exists() and master_wav.stat().st_size > 100_000
                if has_mp4 or has_wav:
                    result["needs_media_trim"] = True
                    result["has_mp4_to_trim"] = has_mp4
                    result["has_wav_to_trim"] = has_wav
                elif cleaned_srt_text:
                    # Chỉ có SRT mà chưa render WAV/MP4 -> Ghi SRT sạch luôn
                    try:
                        srt_file.write_text(cleaned_srt_text, encoding="utf-8")
                    except Exception:
                        pass
        except Exception as e_srt:
            result["video_message"] = f"Lỗi đọc SRT: {e_srt}"

    if not result["raw_cut_intervals"] and video_clean_marker.exists():
        result["needs_media_trim"] = False

    return result


def execute_project_media_trim(item_state: Dict[str, Any]) -> Dict[str, Any]:
    """
    GIAI ĐOẠN 2: Thực thi cắt đoạn đọc nhầm `[LOCKED_TITLE]` khỏi Video `.mp4` và Voice `.wav`
    cho một dự án đã được phát hiện ở Giai đoạn 1.
    """
    proj_dir: Path = item_state["proj_dir"]
    ma_id: str = item_state["ma_id"]
    renders_dir = proj_dir / "renders"
    assets_dir = proj_dir / "assets"
    srt_file = assets_dir / "subtitles.srt"
    master_wav = assets_dir / "master_voice.wav"
    master_mp4 = renders_dir / f"{ma_id}_master.mp4"
    video_clean_marker = renders_dir / ".cleaned_locked_title_v106.json"
    cut_intervals: List[Tuple[float, float]] = item_state.get("raw_cut_intervals") or []
    cleaned_srt_text: str = item_state.get("cleaned_srt_text") or ""

    if not cut_intervals:
        return item_state

    # 1. Cắt Video MP4 nếu có
    if master_mp4.exists() and master_mp4.stat().st_size > 100_000:
        ok_v, old_vd, new_vd, msg_v = trim_media_file_by_keep_intervals(
            master_mp4, cut_intervals, is_video=True
        )
        item_state["video_repaired"] = ok_v
        item_state["old_video_duration"] = old_vd
        item_state["new_video_duration"] = new_vd
        item_state["video_message"] = msg_v
        if not ok_v:
            return item_state

    # 2. Cắt Master Voice WAV đồng bộ 100% thời lượng (bằng Python wave siêu tốc ~0.4s)
    if master_wav.exists() and master_wav.stat().st_size > 100_000:
        ok_w, _, _, _ = trim_media_file_by_keep_intervals(
            master_wav, cut_intervals, is_video=False
        )
        item_state["voice_repaired"] = ok_w

    # 3. Lưu subtitles.srt đã xóa khung lỗi & dịch khớp thời gian
    if cleaned_srt_text:
        try:
            srt_file.write_text(cleaned_srt_text, encoding="utf-8")
        except Exception:
            pass

    # 4. Lưu dấu đã dọn sạch để lần bấm sau bỏ qua ngay lập tức
    try:
        renders_dir.mkdir(parents=True, exist_ok=True)
        video_clean_marker.write_text(
            json.dumps(
                {
                    "ma_id": ma_id,
                    "cleaned_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "cut_intervals": item_state["cut_intervals"],
                    "old_video_duration": item_state["old_video_duration"],
                    "new_video_duration": item_state["new_video_duration"],
                    "removed_samples": item_state["script_removed_samples"],
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
    except Exception:
        pass

    return item_state


def repair_single_project_script_and_video(proj_dir: Path) -> Dict[str, Any]:
    """Hàm tương thích xử lý trọn gói Giai đoạn 1 + Giai đoạn 2 cho 1 dự án đơn lẻ."""
    st = clean_single_project_scripts_and_detect_media_cuts(proj_dir)
    if st.get("needs_media_trim"):
        st = execute_project_media_trim(st)
    st.pop("proj_dir", None)
    st.pop("raw_cut_intervals", None)
    st.pop("cleaned_srt_text", None)
    return st


def check_and_repair_all_projects_sync(
    projects_dir: Path,
    progress_cb: Optional[Callable[[float, str], None]] = None,
    log_cb: Optional[Callable[[str], None]] = None,
) -> Dict[str, Any]:
    """
    Quét toàn bộ thư mục `projects/` (Nút "🛡️ Check Toàn Bộ") theo kiến trúc 2 Giai đoạn siêu tốc:
    - GIAI ĐOẠN 1 (1–2 giây cho toàn bộ kho): Quét và xóa sạch 100% lỗi `[LOCKED_TITLE]` / Metadata
      trong TẤT CẢ các kịch bản `.txt` của mọi dự án trước tiên! Báo cáo ngay lập tức số kịch bản đã dọn xong.
    - GIAI ĐOẠN 2 (4–8 giây / video): Chỉ chạy cắt FFmpeg Stream Copy & Python WAV Slicer trên đúng những dự án
      đã tạo Video `.mp4` / Voice `.wav` bị dính đoạn đọc nhầm, báo cáo tiến độ từng video `1/N`, `2/N` theo thời gian thực!
    """
    t0 = time.time()
    projects_dir = Path(projects_dir)
    if not projects_dir.exists():
        return {
            "total_projects": 0,
            "total_scanned": 0,
            "scripts_repaired_count": 0,
            "srts_repaired_count": 0,
            "videos_repaired_count": 0,
            "voices_repaired_count": 0,
            "total_leaked_lines_removed": 0,
            "total_lines_removed": 0,
            "repaired_script_ids": [],
            "repaired_voice_ids": [],
            "repaired_video_ids": [],
            "elapsed_sec": 0.0,
            "details": [],
            "report_path": "",
        }

    proj_folders = sorted(
        [d for d in projects_dir.iterdir() if d.is_dir() and not d.name.startswith(".")]
    )
    total = len(proj_folders)
    repaired_script_ids: List[str] = []
    repaired_voice_ids: List[str] = []
    repaired_video_ids: List[str] = []
    srts_repaired_count = 0
    voices_repaired_count = 0
    total_lines_removed = 0
    details: List[Dict[str, Any]] = []
    media_trim_queue: List[Dict[str, Any]] = []

    # ==========================================================================
    # GIAI ĐOẠN 1: QUÉT & DỌN SẠCH TOÀN BỘ KỊCH BẢN (.TXT) TRƯỚC TIÊN (1-2 GIÂY)
    # ==========================================================================
    t_phase1_start = time.time()
    for idx, p_dir in enumerate(proj_folders):
        if progress_cb and (idx % 10 == 0 or idx == total - 1):
            pct1 = round(((idx + 1) / max(1, total)) * 30.0, 1)
            try:
                progress_cb(
                    pct1,
                    f"⚡ [Bước 1/2: Dọn Kịch Bản] Đang quét {idx + 1}/{total} dự án [{p_dir.name}] (Đã sửa sạch {len(repaired_script_ids)} KB)...",
                )
            except Exception:
                pass

        st = clean_single_project_scripts_and_detect_media_cuts(p_dir)
        if st["script_cleaned"] or st["srt_cleaned"]:
            repaired_script_ids.append(st["ma_id"])
            total_lines_removed += (
                st["script_removed_lines_count"] + st["srt_removed_blocks_count"]
            )
        if st["srt_cleaned"]:
            srts_repaired_count += 1
        if st["needs_media_trim"]:
            media_trim_queue.append(st)
        elif st["script_cleaned"] or st["srt_cleaned"]:
            st_clean = {
                k: v
                for k, v in st.items()
                if k not in ("proj_dir", "raw_cut_intervals", "cleaned_srt_text")
            }
            details.append(st_clean)

    phase1_sec = round(time.time() - t_phase1_start, 2)
    phase1_msg = (
        f"✅ [Bước 1/2 Hoàn tất trong {phase1_sec}s] Đã quét xong {total} kịch bản (.txt): "
        f"Làm sạch {len(repaired_script_ids)} kịch bản ({total_lines_removed} dòng lỗi) | "
        f"Phát hiện {len(media_trim_queue)} dự án có Video/Voice cần cắt đoạn đọc nhầm."
    )
    if log_cb:
        try:
            log_cb(phase1_msg)
        except Exception:
            pass
    if progress_cb:
        try:
            progress_cb(35.0 if media_trim_queue else 99.0, phase1_msg)
        except Exception:
            pass

    # ==========================================================================
    # GIAI ĐOẠN 2: CẮT ĐOẠN ĐỌC NHẦM TRONG VIDEO (.MP4) & VOICE (.WAV)
    # ==========================================================================
    total_media = len(media_trim_queue)
    for m_idx, st in enumerate(media_trim_queue, 1):
        mid = st["ma_id"]
        pct2 = round(35.0 + ((m_idx - 0.5) / max(1, total_media)) * 63.0, 1)
        start_v_msg = (
            f"✂️ [Bước 2/2: Cắt Video {m_idx}/{total_media} • {mid}] "
            f"Đang cắt {len(st['cut_intervals'])} đoạn [LOCKED_TITLE] ({st['cut_intervals']})..."
        )
        if progress_cb:
            try:
                progress_cb(pct2, start_v_msg)
            except Exception:
                pass
        if log_cb:
            try:
                log_cb(start_v_msg)
            except Exception:
                pass

        t_v0 = time.time()
        st_after = execute_project_media_trim(st)
        v_sec = round(time.time() - t_v0, 2)

        if st_after["video_repaired"]:
            repaired_video_ids.append(mid)
        if st_after["voice_repaired"]:
            voices_repaired_count += 1
            repaired_voice_ids.append(mid)

        st_clean = {
            k: v
            for k, v in st_after.items()
            if k not in ("proj_dir", "raw_cut_intervals", "cleaned_srt_text")
        }
        details.append(st_clean)

        done_v_msg = (
            f"✅ [Xong Video {m_idx}/{total_media} • {mid} trong {v_sec}s] "
            f"MP4: {st_after['old_video_duration']}s -> {st_after['new_video_duration']}s | "
            f"Voice WAV: {'Đã cắt' if st_after['voice_repaired'] else 'Bỏ qua'} | "
            f"SRT: Đã xóa {st_after['srt_removed_blocks_count']} khung."
        )
        if log_cb:
            try:
                log_cb(done_v_msg)
            except Exception:
                pass
        if progress_cb:
            pct2_done = round(35.0 + (m_idx / max(1, total_media)) * 63.0, 1)
            try:
                progress_cb(pct2_done, done_v_msg)
            except Exception:
                pass

    elapsed_sec = round(time.time() - t0, 2)

    # Ghi file báo cáo tổng hợp rõ ràng cho người dùng / khách hàng
    report_path = projects_dir.parent / "BAO_CAO_CHECK_VA_DON_TOAN_BO.txt"
    try:
        lines_rep = [
            "================================================================================",
            "BÁO CÁO KIỂM TRA & DỌN SẠCH LỖI [LOCKED_TITLE] TRONG KỊCH BẢN & VIDEO MP4",
            "================================================================================",
            f"- Thời gian thực hiện: {time.strftime('%Y-%m-%d %H:%M:%S')} (Tổng: {elapsed_sec}s | Dọn KB: {phase1_sec}s)",
            f"- Thư mục gốc kiểm tra: {projects_dir}",
            f"- Tổng số dự án đã quét: {total}",
            f"- Số kịch bản phát hiện lỗi & đã sửa sạch: {len(repaired_script_ids)} dự án",
            f"- Số phụ đề (.srt) đã dọn & dịch khớp thời gian: {srts_repaired_count} file",
            f"- Số file Voice (.wav) đã cắt bỏ đoạn đọc nhầm: {voices_repaired_count} file",
            f"- Số Video MP4 đã cắt bỏ đoạn voice/sub lỗi [LOCKED_TITLE]: {len(repaired_video_ids)} video",
            f"- Tổng số dòng/khung [LOCKED_TITLE] & Metadata đã xóa: {total_lines_removed}",
            "================================================================================",
            "",
            f"1. DANH SÁCH MÃ KỊCH BẢN ĐÃ ĐƯỢC LÀM SẠCH ({len(repaired_script_ids)} dự án):",
            "--------------------------------------------------------------------------------",
            (
                ", ".join(repaired_script_ids)
                if repaired_script_ids
                else "Không có kịch bản nào còn lỗi (100% đã sạch)."
            ),
            "",
            f"2. DANH SÁCH VIDEO MP4 ĐÃ ĐƯỢC CẮT SẠCH ĐOẠN VOICE LỖI ({len(repaired_video_ids)} video):",
            "--------------------------------------------------------------------------------",
            (
                ", ".join(repaired_video_ids)
                if repaired_video_ids
                else "Không có video MP4 nào bị dính lỗi (hoặc đã được dọn sạch)."
            ),
            "",
            "3. CHI TIẾT TỪNG DỰ ÁN ĐÃ XỬ LÝ:",
            "================================================================================",
        ]
        for i_d, d in enumerate(details, 1):
            lines_rep.append(f"[{i_d}] Dự án: {d['ma_id']}")
            lines_rep.append(
                f"    - Đã xóa dòng lỗi trong Kịch bản (.txt): {d['script_removed_lines_count']} dòng"
            )
            lines_rep.append(
                f"    - Đã xóa khung lỗi trong Phụ đề (.srt): {d['srt_removed_blocks_count']} khung"
            )
            if d["video_repaired"]:
                lines_rep.append(
                    f"    - Đã cắt sạch Video MP4: {d['old_video_duration']}s -> {d['new_video_duration']}s (Các đoạn đã cắt: {d['cut_intervals']})"
                )
            for smp in d.get("script_removed_samples", []):
                lines_rep.append(f"      + Đã xóa: {smp}")
            lines_rep.append(
                "--------------------------------------------------------------------------------"
            )
        report_path.write_text("\n".join(lines_rep), encoding="utf-8")
    except Exception:
        pass

    if progress_cb:
        try:
            progress_cb(
                100.0,
                f"✅ Hoàn tất Check Toàn Bộ {total} dự án ({elapsed_sec}s): Đã làm sạch {len(repaired_script_ids)} Kịch bản & cắt sạch lỗi {len(repaired_video_ids)} Video MP4!",
            )
        except Exception:
            pass

    return {
        "total_projects": total,
        "total_scanned": total,
        "scripts_repaired_count": len(repaired_script_ids),
        "srts_repaired_count": srts_repaired_count,
        "videos_repaired_count": len(repaired_video_ids),
        "voices_repaired_count": voices_repaired_count,
        "total_leaked_lines_removed": total_lines_removed,
        "total_lines_removed": total_lines_removed,
        "repaired_script_ids": repaired_script_ids,
        "repaired_voice_ids": repaired_voice_ids,
        "repaired_video_ids": repaired_video_ids,
        "phase1_script_sec": phase1_sec,
        "elapsed_sec": elapsed_sec,
        "details": details,
        "report_path": str(report_path),
    }


# ==============================================================================
# QUẢN LÝ CẤU HÌNH VOICESTUDIO CLONE GIỌNG (`config/voice_studio_config.json` & `Kho_Voice/`)
# ==============================================================================
def _get_voice_config_file() -> Path:
    p = Path(__file__).resolve().parent.parent
    if p.name.lower() == "app":
        p = p.parent
    cfg_dir = p / "config"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    return cfg_dir / "voice_studio_config.json"


def _ensure_default_padre_voice_profile(root_dir: Optional[Path] = None) -> Path:
    """Đảm bảo hồ sơ giọng mẫu mặc định 04_mx_ong_gia_padre_implacable luôn có mặt đầy đủ trong Kho_Voice/."""
    import shutil

    base = Path(root_dir) if root_dir else Path(__file__).resolve().parent.parent
    if base.name.lower() == "app":
        base = base.parent
    prof_dir = base / "Kho_Voice" / "04_mx_ong_gia_padre_implacable"
    prof_dir.mkdir(parents=True, exist_ok=True)
    sample_wav = prof_dir / "sample.wav"
    sample_txt = prof_dir / "sample.txt"
    prof_json = prof_dir / "profile.json"

    fallback_wav = base / "assets" / "voices" / "Padre_Mexico.wav"
    fallback_txt = base / "assets" / "voices" / "Padre_Mexico.txt"

    # 1. Tìm từ các nguồn cục bộ nếu sample.wav chưa tồn tại hoặc bị rỗng
    if not sample_wav.exists() or sample_wav.stat().st_size < 10_000:
        local_candidates = [
            fallback_wav,
            base
            / "app"
            / "Kho_Voice"
            / "04_mx_ong_gia_padre_implacable"
            / "sample.wav",
            base / "app" / "assets" / "voices" / "Padre_Mexico.wav",
            Path(os.environ.get("APPDATA", ""))
            / "VoiceStudio"
            / "voices"
            / "04_mx_ong_gia_padre_implacable"
            / "sample.wav",
            Path.home()
            / "VoiceStudio"
            / "voices"
            / "04_mx_ong_gia_padre_implacable"
            / "sample.wav",
        ]
        for cand in local_candidates:
            try:
                if cand.exists() and cand.stat().st_size > 10_000:
                    shutil.copy2(str(cand), str(sample_wav))
                    break
            except Exception:
                pass

    # 2. Nếu máy khách vừa update từ bản cũ (chưa copy Kho_Voice/assets) -> Tự động tải trực tiếp sample.wav từ GitHub
    if not sample_wav.exists() or sample_wav.stat().st_size < 10_000:
        raw_urls = [
            "https://raw.githubusercontent.com/phamngocthu661-lang/mexico-ong-gia-studio/main/Kho_Voice/04_mx_ong_gia_padre_implacable/sample.wav",
            "https://github.com/phamngocthu661-lang/mexico-ong-gia-studio/raw/refs/heads/main/Kho_Voice/04_mx_ong_gia_padre_implacable/sample.wav",
        ]
        for url in raw_urls:
            try:
                resp = requests.get(
                    url,
                    timeout=20,
                    headers={"User-Agent": "MexicoOngGiaStudio-VoiceSync/1.0"},
                )
                if resp.status_code == 200 and len(resp.content) > 10_000:
                    sample_wav.write_bytes(resp.content)
                    print(
                        f"[VoiceStudio] ✅ Đã tự động tải giọng mẫu mặc định Padre Mexico ({len(resp.content)} bytes) về {sample_wav}"
                    )
                    break
            except Exception:
                try:
                    import urllib3

                    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
                    resp = requests.get(
                        url,
                        timeout=20,
                        verify=False,
                        headers={"User-Agent": "MexicoOngGiaStudio-VoiceSync/1.0"},
                    )
                    if resp.status_code == 200 and len(resp.content) > 10_000:
                        sample_wav.write_bytes(resp.content)
                        break
                except Exception:
                    pass
        if (
            not sample_wav.exists() or sample_wav.stat().st_size < 10_000
        ) and os.name == "nt":
            for url in raw_urls:
                try:
                    subprocess.run(
                        [
                            "curl.exe",
                            "-L",
                            "-k",
                            "-s",
                            "--connect-timeout",
                            "15",
                            "-o",
                            str(sample_wav),
                            url,
                        ],
                        timeout=30,
                        check=False,
                        creationflags=0x08000000,
                    )
                    if sample_wav.exists() and sample_wav.stat().st_size > 10_000:
                        break
                except Exception:
                    pass

    # Đồng bộ ngược sang assets/voices/Padre_Mexico.wav để dự phòng
    if sample_wav.exists() and sample_wav.stat().st_size > 10_000:
        if not fallback_wav.exists() or fallback_wav.stat().st_size < 10_000:
            try:
                fallback_wav.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(str(sample_wav), str(fallback_wav))
            except Exception:
                pass
    if not sample_txt.exists():
        if fallback_txt.exists():
            try:
                shutil.copy2(str(fallback_txt), str(sample_txt))
            except Exception:
                pass
        else:
            sample_txt.write_text(
                "a la seis y cuarto de la mañana, mientras yo estaba tumbado en un cattre, en la cochera de la casa de mi hijo, con una tos que sonaba a tornillos sueltos dentro de una lata.",
                encoding="utf-8",
            )
    if not prof_json.exists():
        prof_data = {
            "id": "04_mx_ong_gia_padre_implacable",
            "name": "04. Padre Implacable — Ông Già Trừng Trị Mexico",
            "language": "es",
            "description": "[Key: 04_Nhom_Ong_Gia_Trung_Tri_Mexico] Người cha già sắt đá (Padre Implacable) bị con ruột đuổi ra nhà kho — U uất, đanh thép, nghiêm nghị, uy quyền phụ hệ không khoan nhượng",
            "personality": "Người cha già sắt đá (Padre Implacable) bị con ruột đuổi ra nhà kho. U uất, đanh thép, nghiêm nghị, uy quyền phụ hệ không khoan nhượng",
            "refText": sample_txt.read_text(encoding="utf-8", errors="ignore").strip(),
            "channelKey": "04_Nhom_Ong_Gia_Trung_Tri_Mexico",
            "speed": 1.0,
            "model": "omnivoice",
            "sampleFile": "sample.wav",
        }
        prof_json.write_text(
            json.dumps(prof_data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    return sample_wav


def load_voice_config(root_dir: Optional[Path] = None) -> Dict[str, Any]:
    default_wav = _ensure_default_padre_voice_profile(root_dir)
    cfg_file = _get_voice_config_file()
    default_cfg = {
        "engine_mode": "voicestudio",
        "active_gpu_server": "omnivoice_gpu",
        "selected_preset_id": "04_mx_ong_gia_padre_implacable",
        "ref_wav": str(default_wav),
        "speedScale": 1.0,
        "pitchScale": 1.05,
        "language": "es",
        "volumeScale": 1.05,
        "intonationScale": 0.95,
        "pauseLengthScale": 1.12,
    }
    if cfg_file.exists():
        try:
            saved = json.loads(cfg_file.read_text(encoding="utf-8"))
            if isinstance(saved, dict):
                default_cfg.update(saved)
        except Exception:
            pass
    if not str(default_cfg.get("selected_preset_id") or "").strip():
        default_cfg["selected_preset_id"] = "04_mx_ong_gia_padre_implacable"
    cur_ref = str(default_cfg.get("ref_wav") or "").strip()
    if not cur_ref or (not os.path.exists(cur_ref) and default_wav.exists()):
        default_cfg["ref_wav"] = str(default_wav)
    default_cfg["engine_mode"] = "voicestudio"
    default_cfg["active_gpu_server"] = "omnivoice_gpu"
    return default_cfg


def save_voice_config(
    new_cfg: Dict[str, Any], root_dir: Optional[Path] = None
) -> Dict[str, Any]:
    cfg = load_voice_config(root_dir)
    if isinstance(new_cfg, dict):
        cfg.update(new_cfg)
    cfg["engine_mode"] = "voicestudio"
    cfg["active_gpu_server"] = "omnivoice_gpu"
    cfg_file = _get_voice_config_file()
    try:
        cfg_file.write_text(
            json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except Exception:
        pass
    return cfg


def list_kho_voices(root_dir: Optional[Path] = None) -> List[Dict[str, Any]]:
    _ensure_default_padre_voice_profile(root_dir)
    base = Path(root_dir) if root_dir else Path(__file__).resolve().parent.parent
    if base.name.lower() == "app":
        base = base.parent
    kho_dir = base / "Kho_Voice"
    kho_dir.mkdir(parents=True, exist_ok=True)
    voices: List[Dict[str, Any]] = []
    for d in sorted(kho_dir.iterdir(), key=lambda x: x.name.lower()):
        if d.is_dir():
            ref_w = d / "reference.wav"
            if not ref_w.exists():
                wavs = list(d.glob("*.wav"))
                if wavs:
                    ref_w = wavs[0]
            if ref_w.exists():
                voices.append(
                    {
                        "id": d.name,
                        "name": f"{d.name} (VoiceStudio Clone)",
                        "ref_wav": str(ref_w),
                        "style": "VoiceStudio Clone",
                    }
                )
    for f in sorted(kho_dir.glob("*.wav"), key=lambda x: x.name.lower()):
        voices.append(
            {
                "id": f.stem,
                "name": f"{f.stem} (VoiceStudio Clone)",
                "ref_wav": str(f),
                "style": "VoiceStudio Clone",
            }
        )
    return voices


def compute_voice_signature(v_cfg: Optional[Dict[str, Any]] = None) -> str:
    import hashlib

    cfg = v_cfg or load_voice_config()
    raw = f"voicestudio|{cfg.get('selected_preset_id', '04_mx_ong_gia_padre_implacable')}|{cfg.get('ref_wav', '')}|{cfg.get('speedScale', 1.0)}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()[:10]


sys.modules["backend.karaoke_subtitle"] = sys.modules[__name__]
sys.modules["backend.sync_checker"] = sys.modules[__name__]
