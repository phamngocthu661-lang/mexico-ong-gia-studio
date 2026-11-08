# -*- coding: utf-8 -*-
"""
Engine Render Video Tự Động Chuẩn Mới (Mexico Ông Già Studio):
1. Lớp Đáy (#4 - Thấp nhất): Video Stock có sẵn (`STOOK/`), chỉ làm tối nhẹ (`brightness=-0.12, contrast=1.05, saturation=0.92`).
2. Lớp Giữa (#3 - Kho Green): Các Video/Ảnh Green cố định từ `Kho_Green/` (tách lớp theo `zIndex`, chỉnh vị trí `x, y`, kích thước `w, h`, `opacity`),
   được nướng sẵn (Pre-Bake) thành 1 file Cache Alpha `.nut` (`yuva420p`) và Loop (`-stream_loop -1`) để tiết kiệm tài nguyên.
3. Lớp Trên (#2 - Ngay dưới Sub): Ảnh Green Theo Kịch Bản (`THUMBNAIL-NENXANH.png` / `green_part_01..07.png`)
   tách nền sạch, cắt sát chân dung, đặt ở bên phải SÁT ĐÁY DƯỚI CÙNG (`y = H - h`), độ mờ `opacity = 0.9`.
4. Lớp Cao Nhất (#1 - Topmost): Phụ đề chạy như Karaoke (`.ass` CapCut Karaoke Box) nhảy hộp màu theo từng từ đọc.
"""
import os
import sys
import re
import json
import time
import wave
import shutil
import hashlib
import threading
import subprocess
from pathlib import Path
from typing import Optional, Callable, Dict, Any, List, Tuple

from backend.karaoke_subtitle import generate_karaoke_ass_from_srt

_BIN_DIR = Path(__file__).resolve().parent.parent / "bin"
if not _BIN_DIR.exists():
    _BIN_DIR = Path(__file__).resolve().parent.parent.parent / "bin"
if _BIN_DIR.exists():
    os.environ["PATH"] = str(_BIN_DIR) + os.pathsep + os.environ.get("PATH", "")

_FFMPEG_BIN = str(_BIN_DIR / "ffmpeg.exe") if (_BIN_DIR / "ffmpeg.exe").exists() else "ffmpeg"
_FFPROBE_BIN = str(_BIN_DIR / "ffprobe.exe") if (_BIN_DIR / "ffprobe.exe").exists() else "ffprobe"

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

_NVENC_AVAILABLE: Optional[bool] = None
_NVENC_LAST_CHECK_TS: float = 0.0
_NVENC_LOCK = threading.Lock()
_GREEN_CACHE_LOCK = threading.Lock()


def get_root_dir() -> Path:
    p = Path(__file__).resolve().parent.parent
    if p.name.lower() == "app":
        return p.parent
    return p


def check_nvenc_available() -> bool:
    global _NVENC_AVAILABLE, _NVENC_LAST_CHECK_TS
    if _NVENC_AVAILABLE is True:
        return True
    now = time.time()
    if _NVENC_AVAILABLE is False and (now - _NVENC_LAST_CHECK_TS) < 15.0:
        return False
    with _NVENC_LOCK:
        if _NVENC_AVAILABLE is True:
            return True
        if _NVENC_AVAILABLE is False and (time.time() - _NVENC_LAST_CHECK_TS) < 15.0:
            return False
        _NVENC_LAST_CHECK_TS = time.time()
        try:
            res = subprocess.run(
                [
                    _FFMPEG_BIN, "-hide_banner", "-loglevel", "error",
                    "-f", "lavfi", "-i", "color=c=black:s=256x256:d=0.2:r=30",
                    "-pix_fmt", "yuv420p", "-c:v", "h264_nvenc", "-f", "null", "-",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=10,
                creationflags=0x08000000 if os.name == "nt" else 0,
            )
            _NVENC_AVAILABLE = (res.returncode == 0)
        except Exception:
            _NVENC_AVAILABLE = False
        return bool(_NVENC_AVAILABLE)


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
    cmd = [
        _FFPROBE_BIN, "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(file_path),
    ]
    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        return float(res.stdout.strip())
    except Exception:
        return 0.0


def parse_time_to_seconds(time_str: str) -> float:
    try:
        parts = time_str.split(":")
        if len(parts) == 3:
            h, m, s = parts
            return float(h) * 3600 + float(m) * 60 + float(s)
    except Exception:
        pass
    return 0.0


# ==============================================================================
# QUẢN LÝ CẤU HÌNH BỐ CỤC PREVIEW & LAYER GREEN (`config/video_layout_config.json`)
# ==============================================================================
def get_default_video_layout_config(root_dir: Optional[Path] = None) -> Dict[str, Any]:
    root = Path(root_dir) if root_dir else get_root_dir()
    kho_green = root / "Kho_Green"
    default_layers: List[Dict[str, Any]] = []

    if (kho_green / "NÈN DEN.jpg").exists():
        default_layers.append({
            "id": "layer_nen_den",
            "name": "NÈN DEN.jpg (Dải tối đáy màn hình)",
            "file": "NÈN DEN.jpg",
            "type": "image",
            "enabled": True,
            "x": 0,
            "y": 830,
            "width": 1920,
            "height": 250,
            "opacity": 0.78,
            "zIndex": 10,
            "chromaKey": False,
            "keyColor": "#00FF00",
            "similarity": 0.26,
            "blend": 0.08,
        })
    if (kho_green / "SONG6.mp4").exists():
        default_layers.append({
            "id": "layer_song_am",
            "name": "SONG6.mp4 (Sóng nhạc Green)",
            "file": "SONG6.mp4",
            "type": "video",
            "enabled": True,
            "x": 55,
            "y": 205,
            "width": 310,
            "height": 125,
            "opacity": 0.95,
            "zIndex": 20,
            "chromaKey": True,
            "keyColor": "#00FF00",
            "similarity": 0.28,
            "blend": 0.08,
        })
    if (kho_green / "SUB.mp4").exists():
        default_layers.append({
            "id": "layer_nut_sub",
            "name": "SUB.mp4 (Nút Đăng Ký Green)",
            "file": "SUB.mp4",
            "type": "video",
            "enabled": True,
            "x": 45,
            "y": 45,
            "width": 330,
            "height": 145,
            "opacity": 1.0,
            "zIndex": 30,
            "chromaKey": True,
            "keyColor": "#00FF00",
            "similarity": 0.28,
            "blend": 0.08,
        })

    return {
        "canvas": {"width": 1920, "height": 1080},
        "stock_background": {
            "brightness": -0.12,
            "contrast": 1.05,
            "saturation": 0.92,
            "stock_speed": 0.75,
        },
        "green_layers": default_layers,
        "script_green_character": {
            "enabled": True,
            "x": 1410,
            "y": 300,
            "width": 490,
            "height": 780,
            "opacity": 0.90,
            "snapBottom": True,
            "zIndex": 500,
            "keyColor": "#00FF00",
            "similarity": 0.26,
            "blend": 0.08,
        },
        "karaoke_subtitle": {
            "enabled": True,
            "x": 30,
            "y": 900,
            "width": 1360,
            "height": 90,
            "centerX": 710,
            "centerY": 945,
            "fontSize": 68,
            "font_size": 68,
            "textColor": "#FFFF00",
            "boxColor": "#7C00FF",
            "outlineColor": "#000000",
            "maxWordsPerLine": 5,
            "max_words_per_line": 5,
            "maxCharsPerLine": 26,
            "zIndex": 1000,
        },
    }


def _normalize_karaoke_subtitle_cfg(sub_cfg: Dict[str, Any]) -> Dict[str, Any]:
    w = max(260, min(1880, int(sub_cfg.get("width", 1360))))
    h = max(48, min(380, int(sub_cfg.get("height", 90))))
    x = max(0, min(1920 - w, int(sub_cfg.get("x", 30))))
    y = max(0, min(1080 - h, int(sub_cfg.get("y", 900))))
    fs_raw = sub_cfg.get("fontSize") if sub_cfg.get("fontSize") is not None else sub_cfg.get("font_size", 68)
    fs = max(20, min(120, int(round(float(fs_raw or 68)))))
    mw_raw = sub_cfg.get("maxWordsPerLine") if sub_cfg.get("maxWordsPerLine") is not None else sub_cfg.get("max_words_per_line", 5)
    mw = max(2, min(12, int(mw_raw or 5)))
    sub_cfg["x"] = x
    sub_cfg["y"] = y
    sub_cfg["width"] = w
    sub_cfg["height"] = h
    sub_cfg["centerX"] = int(round(x + w / 2.0))
    sub_cfg["centerY"] = int(round(y + h / 2.0))
    sub_cfg["fontSize"] = fs
    sub_cfg["font_size"] = fs
    sub_cfg["maxWordsPerLine"] = mw
    sub_cfg["max_words_per_line"] = mw
    sub_cfg["zIndex"] = 1000
    return sub_cfg


def load_video_layout_config(root_dir: Optional[Path] = None) -> Dict[str, Any]:
    root = Path(root_dir) if root_dir else get_root_dir()
    cfg_file = root / "config" / "video_layout_config.json"
    default_cfg = get_default_video_layout_config(root)
    if cfg_file.exists():
        try:
            saved = json.loads(cfg_file.read_text(encoding="utf-8"))
            if isinstance(saved, dict):
                for section in ("canvas", "stock_background", "script_green_character", "karaoke_subtitle"):
                    if isinstance(saved.get(section), dict):
                        default_cfg[section].update(saved[section])
                if isinstance(saved.get("stock_darken"), dict):
                    default_cfg["stock_background"].update(saved["stock_darken"])
                if isinstance(saved.get("script_character_green"), dict):
                    default_cfg["script_green_character"].update(saved["script_character_green"])
                if isinstance(saved.get("subtitle_karaoke"), dict):
                    default_cfg["karaoke_subtitle"].update(saved["subtitle_karaoke"])
                if isinstance(saved.get("green_layers"), list):
                    default_cfg["green_layers"] = saved["green_layers"]
                elif isinstance(saved.get("green_video_layers"), list):
                    default_cfg["green_layers"] = saved["green_video_layers"]
        except Exception as e:
            print(f"[Renderer] Lưu ý khi đọc video_layout_config.json: {e}")

    # Bắt buộc quy tắc:
    # 1. Ảnh Green Kịch Bản luôn sát đáy dưới cùng (y = 1080 - height) và Opacity mặc định 0.9
    char_cfg = default_cfg["script_green_character"]
    char_h = max(120, min(1080, int(char_cfg.get("height", 780))))
    char_w = max(100, min(1200, int(char_cfg.get("width", 490))))
    char_cfg["width"] = char_w
    char_cfg["height"] = char_h
    if char_cfg.get("snapBottom", True):
        char_cfg["y"] = 1080 - char_h
    char_cfg["opacity"] = round(max(0.1, min(1.0, float(char_cfg.get("opacity", 0.90)))), 2)
    char_cfg["zIndex"] = 500
    _normalize_karaoke_subtitle_cfg(default_cfg["karaoke_subtitle"])
    # Đồng bộ cả 2 tên khóa để tương thích 100% giữa Frontend Preview và FFmpeg Renderer
    default_cfg["green_video_layers"] = default_cfg["green_layers"]
    default_cfg["script_character_green"] = default_cfg["script_green_character"]
    default_cfg["subtitle_karaoke"] = default_cfg["karaoke_subtitle"]
    default_cfg["stock_darken"] = default_cfg["stock_background"]
    return default_cfg


def save_video_layout_config(config_data: Dict[str, Any], root_dir: Optional[Path] = None) -> Dict[str, Any]:
    root = Path(root_dir) if root_dir else get_root_dir()
    cfg_dir = root / "config"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    cfg_file = cfg_dir / "video_layout_config.json"

    merged = load_video_layout_config(root)
    for section in ("canvas", "stock_background", "script_green_character", "karaoke_subtitle"):
        if isinstance(config_data.get(section), dict):
            merged[section].update(config_data[section])
    if isinstance(config_data.get("stock_darken"), dict):
        merged["stock_background"].update(config_data["stock_darken"])
    if isinstance(config_data.get("script_character_green"), dict):
        merged["script_green_character"].update(config_data["script_character_green"])
    if isinstance(config_data.get("subtitle_karaoke"), dict):
        s_in = dict(config_data["subtitle_karaoke"])
        if "font_size" in s_in and "fontSize" not in s_in:
            s_in["fontSize"] = s_in["font_size"]
        elif "fontSize" in s_in:
            s_in["font_size"] = s_in["fontSize"]
        merged["karaoke_subtitle"].update(s_in)
    if isinstance(config_data.get("green_video_layers"), list):
        merged["green_layers"] = config_data["green_video_layers"]
    elif isinstance(config_data.get("green_layers"), list):
        merged["green_layers"] = config_data["green_layers"]

    # Đảm bảo Ảnh Green Kịch Bản sát đáy dưới cùng & Sub Karaoke ở lớp cao nhất
    char_cfg = merged["script_green_character"]
    char_h = max(120, min(1080, int(char_cfg.get("height", 780))))
    char_cfg["height"] = char_h
    if char_cfg.get("snapBottom", True):
        char_cfg["y"] = 1080 - char_h
    char_cfg["zIndex"] = 500
    _normalize_karaoke_subtitle_cfg(merged["karaoke_subtitle"])

    merged["green_video_layers"] = merged["green_layers"]
    merged["script_character_green"] = merged["script_green_character"]
    merged["subtitle_karaoke"] = merged["karaoke_subtitle"]
    merged["stock_darken"] = merged["stock_background"]

    cfg_file.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
    return merged


# ==============================================================================
# 1. TÁCH NỀN & ĐẶT ẢNH GREEN KỊCH BẢN SÁT ĐÁY DƯỚI CÙNG (OPACITY = 0.9)
# ==============================================================================
def prepare_script_green_character_cutout(
    green_screen_path: Optional[str],
    target_w: int,
    target_h: int,
    char_cfg: Dict[str, Any],
    cache_dir: Path,
) -> Optional[str]:
    """
    Tách sạch nền xanh `#00FF00` từ `THUMBNAIL-NENXANH.png` (hoặc `green_part_01..07.png`),
    cắt sát khung nhân vật (loại bỏ khoảng trống phía dưới chân),
    co giãn theo đúng khung `(width, height)` người dùng chọn trên Preview,
    đặt SÁT ĐÁY DƯỚI CÙNG (`paste_y = target_h - new_h`), và áp dụng `opacity = 0.9`.
    """
    if not green_screen_path or not os.path.exists(green_screen_path):
        return None
    try:
        src_p = Path(green_screen_path).resolve()
        if src_p.stat().st_size < 5_000:
            return None
        cache_dir.mkdir(parents=True, exist_ok=True)

        scale_x = target_w / 1920.0
        scale_y = target_h / 1080.0
        box_x = int(round(float(char_cfg.get("x", 1410)) * scale_x))
        box_w = max(80, int(round(float(char_cfg.get("width", 490)) * scale_x)))
        box_h = max(120, int(round(float(char_cfg.get("height", 780)) * scale_y)))
        opacity = max(0.1, min(1.0, float(char_cfg.get("opacity", 0.90))))

        sig = (
            f"char_bottom_v3|{src_p}|{src_p.stat().st_mtime_ns}|{src_p.stat().st_size}|"
            f"{target_w}x{target_h}|x{box_x}_w{box_w}_h{box_h}_op{opacity:.2f}"
        )
        sig_hash = hashlib.md5(sig.encode("utf-8")).hexdigest()[:12]
        out_png = cache_dir / f"script_char_bottom_{target_w}x{target_h}_{sig_hash}.png"
        if out_png.exists() and out_png.stat().st_size > 5_000:
            return str(out_png)

        from PIL import Image, ImageFilter
        import numpy as np

        im = Image.open(src_p).convert("RGBA")
        arr = np.asarray(im, dtype=np.float32)
        r, g, b, a = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2], arr[:, :, 3]

        max_rb = np.maximum(r, b)
        green_excess = g - max_rb
        dist_to_key = np.sqrt((r - 0.0) ** 2 + (g - 255.0) ** 2 + (b - 0.0) ** 2)

        chroma_alpha = np.clip((dist_to_key - 66.0) / 70.0, 0.0, 1.0)
        excess_mask = np.clip(1.0 - ((green_excess - 32.0) / 62.0), 0.0, 1.0)
        fg_alpha = np.minimum(chroma_alpha, excess_mask) * (a / 255.0)

        # Khử ám xanh (Green Spill Suppression) trên tóc bạc, da và viền áo
        spill_zone = (g > max_rb) & (fg_alpha > 0.01)
        g_clean = np.where(spill_zone, max_rb + (g - max_rb) * 0.22, g)

        alpha_u8 = np.clip(fg_alpha * 255.0, 0, 255).astype(np.uint8)
        alpha_img = Image.fromarray(alpha_u8).filter(ImageFilter.GaussianBlur(radius=0.75))
        alpha_u8 = np.asarray(alpha_img, dtype=np.uint8)
        alpha_u8 = np.where(alpha_u8 < 14, 0, alpha_u8)

        # Áp dụng độ mờ Opacity (mặc định 0.9)
        if opacity < 0.999:
            alpha_u8 = np.clip(alpha_u8.astype(np.float32) * opacity, 0, 255).astype(np.uint8)

        ys, xs = np.where(alpha_u8 > 20)
        if len(xs) < 40 or len(ys) < 40:
            return None

        x1, x2 = int(xs.min()), int(xs.max())
        y1, y2 = int(ys.min()), int(ys.max())

        rgba_clean = np.stack(
            [
                np.clip(r, 0, 255).astype(np.uint8),
                np.clip(g_clean, 0, 255).astype(np.uint8),
                np.clip(b, 0, 255).astype(np.uint8),
                alpha_u8,
            ],
            axis=2,
        )
        char_crop = Image.fromarray(rgba_clean).crop((x1, y1, x2 + 1, y2 + 1))
        cw, ch = char_crop.size

        scale = min(box_w / max(1, cw), box_h / max(1, ch))
        new_w = max(64, int(round(cw * scale)))
        new_h = max(64, int(round(ch * scale)))
        char_resized = char_crop.resize((new_w, new_h), Image.Resampling.LANCZOS)

        canvas = Image.new("RGBA", (target_w, target_h), (0, 0, 0, 0))
        # Căn giữa theo chiều ngang trong khung box_x..box_x+box_w, và BẮT BUỘC SÁT ĐÁY DƯỚI CÙNG (paste_y = target_h - new_h)
        paste_x = max(0, min(target_w - new_w, box_x + (box_w - new_w) // 2))
        paste_y = max(0, target_h - new_h)
        canvas.paste(char_resized, (paste_x, paste_y), char_resized)
        canvas.save(out_png, format="PNG", optimize=True)
        return str(out_png)
    except Exception as e:
        print(f"[Renderer] Lưu ý khi chuẩn bị Ảnh Green Kịch Bản sát đáy: {e}")
        return None


# ==============================================================================
# 2. PRE-BAKE CACHE CÁC LỚP VIDEO GREEN CỐ ĐỊNH (`Kho_Green/`) ĐỂ LOOP TIẾT KIỆM GPU/CPU
# ==============================================================================
def build_or_get_fixed_green_layers_cache(
    layout_cfg: Dict[str, Any],
    target_w: int = 1920,
    target_h: int = 1080,
    work_fps: int = 12,
    root_dir: Optional[Path] = None,
    cache_duration_sec: float = 12.0,
    ffmpeg_bin: Optional[Path] = None,
) -> Optional[str]:
    """
    Nướng sẵn (Pre-Bake) toàn bộ các lớp Video/Ảnh Green cố định từ `Kho_Green/`
    theo đúng thứ tự lớp `zIndex` (thấp ở dưới, cao ở trên), tọa độ `(x, y)`,
    kích thước `(width, height)` và `opacity` thành 1 file video Alpha `.nut` (`yuva420p`)
    để khi render video chính dài 90 phút chỉ cần `-stream_loop -1`.
    """
    root = Path(root_dir) if root_dir else get_root_dir()
    kho_green = root / "Kho_Green"
    cache_dir = root / "cache" / "green_layer_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    raw_layers = layout_cfg.get("green_layers") or []
    active_layers: List[Dict[str, Any]] = []
    for lyr in raw_layers:
        if not isinstance(lyr, dict) or not lyr.get("enabled", True):
            continue
        rel_f = str(lyr.get("file") or "").strip()
        if not rel_f:
            continue
        cand_p = Path(rel_f) if os.path.isabs(rel_f) else (kho_green / rel_f)
        if cand_p.exists() and cand_p.is_file():
            item = dict(lyr)
            item["abs_path"] = str(cand_p.resolve())
            item["mtime_ns"] = cand_p.stat().st_mtime_ns
            item["size"] = cand_p.stat().st_size
            active_layers.append(item)

    if not active_layers:
        return None

    # Sắp xếp từ lớp thấp lên lớp cao theo zIndex
    active_layers.sort(key=lambda x: int(x.get("zIndex", 10)))

    sig_payload = json.dumps(
        {
            "res": f"{target_w}x{target_h}",
            "fps": work_fps,
            "dur": cache_duration_sec,
            "layers": [
                {
                    "path": x["abs_path"],
                    "mtime": x["mtime_ns"],
                    "x": int(x.get("x", 0)),
                    "y": int(x.get("y", 0)),
                    "w": int(x.get("width", 300)),
                    "h": int(x.get("height", 150)),
                    "op": round(float(x.get("opacity", 1.0)), 2),
                    "z": int(x.get("zIndex", 10)),
                    "ck": bool(x.get("chromaKey", True)),
                    "kc": str(x.get("keyColor", "#00FF00")),
                    "sim": round(float(x.get("similarity", 0.28)), 2),
                    "bld": round(float(x.get("blend", 0.08)), 2),
                }
                for x in active_layers
            ],
        },
        sort_keys=True,
    )
    sig_hash = hashlib.sha256(sig_payload.encode("utf-8")).hexdigest()[:14]
    cached_nut = cache_dir / f"fixed_green_layers_{target_w}x{target_h}_{work_fps}fps_{sig_hash}.nut"
    if cached_nut.exists() and cached_nut.stat().st_size > 50_000:
        return str(cached_nut)

    with _GREEN_CACHE_LOCK:
        if cached_nut.exists() and cached_nut.stat().st_size > 50_000:
            return str(cached_nut)

        tmp_nut = cached_nut.with_suffix(".tmp.nut")
        scale_x = target_w / 1920.0
        scale_y = target_h / 1080.0

        cmd: List[str] = [
            _FFMPEG_BIN, "-y", "-hide_banner", "-loglevel", "error",
            "-f", "lavfi",
            "-i", f"color=c=black@0.0:s={target_w}x{target_h}:r={work_fps}:d={cache_duration_sec:.1f},format=yuva420p",
        ]

        filter_parts: List[str] = ["[0:v]format=yuva420p[base0]"]
        cur_label = "[base0]"

        for idx, lyr in enumerate(active_layers, start=1):
            abs_p = lyr["abs_path"]
            ext = os.path.splitext(abs_p)[1].lower()
            is_img = ext in (".png", ".jpg", ".jpeg", ".webp", ".bmp")
            if is_img:
                cmd.extend(["-loop", "1", "-t", f"{cache_duration_sec:.1f}", "-i", abs_p])
            else:
                cmd.extend(["-stream_loop", "-1", "-t", f"{cache_duration_sec:.1f}", "-i", abs_p])

            lx = int(round(float(lyr.get("x", 0)) * scale_x))
            ly = int(round(float(lyr.get("y", 0)) * scale_y))
            lw = max(16, (int(round(float(lyr.get("width", 300)) * scale_x)) // 2) * 2)
            lh = max(16, (int(round(float(lyr.get("height", 150)) * scale_y)) // 2) * 2)
            opacity = max(0.05, min(1.0, float(lyr.get("opacity", 1.0))))
            use_ck = bool(lyr.get("chromaKey", not is_img))
            key_hex = re.sub(r"[^0-9A-Fa-f]", "", str(lyr.get("keyColor", "#00FF00"))) or "00FF00"
            sim = max(0.05, min(0.70, float(lyr.get("similarity", 0.28))))
            bld = max(0.0, min(0.40, float(lyr.get("blend", 0.08))))

            chain = [
                f"fps={work_fps}",
                f"scale={lw}:{lh}:flags=fast_bilinear",
                "format=rgba",
            ]
            if use_ck:
                chain.append(f"colorkey=0x{key_hex}:{sim:.2f}:{bld:.2f}")
                chain.append("despill=type=green")
            if opacity < 0.995:
                chain.append(f"colorchannelmixer=aa={opacity:.2f}")
            chain.append("format=yuva420p")

            lyr_label = f"[gl_{idx}]"
            next_base = f"[base{idx}]"
            filter_parts.append(f"[{idx}:v]{','.join(chain)}{lyr_label}")
            filter_parts.append(f"{cur_label}{lyr_label}overlay=x={lx}:y={ly}:shortest=1:format=auto,format=yuva420p{next_base}")
            cur_label = next_base

        cmd.extend([
            "-filter_complex", ";".join(filter_parts),
            "-map", cur_label,
            "-c:v", "ffv1", "-level", "3", "-threads", "4",
            "-pix_fmt", "yuva420p",
            "-t", f"{cache_duration_sec:.1f}",
            "-f", "nut",
            str(tmp_nut),
        ])

        try:
            print(f"[Renderer] ⚡ Đang tạo Cache cho {len(active_layers)} lớp Video Green cố định -> {cached_nut.name}...")
            res = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=60,
                creationflags=0x08000000 if os.name == "nt" else 0,
            )
            if res.returncode == 0 and tmp_nut.exists() and tmp_nut.stat().st_size > 50_000:
                os.replace(str(tmp_nut), str(cached_nut))
                print(f"[Renderer] ✅ Đã lưu Cache Green cố định: {cached_nut.name} ({cached_nut.stat().st_size / (1024*1024):.2f} MB)")
                return str(cached_nut)
            else:
                print(f"[Renderer] ⚠️ Lưu ý khi tạo Cache Green: {res.stderr[-300:] if res.stderr else ''}")
        except Exception as e:
            print(f"[Renderer] ⚠️ Lỗi tạo Cache Green: {e}")
        finally:
            if tmp_nut.exists():
                try:
                    tmp_nut.unlink()
                except Exception:
                    pass
    return None


# ==============================================================================
# CƠ CHẾ SSD STAGING & CHECKPOINT RESUME
# ==============================================================================
def get_default_ssd_staging_dir() -> Tuple[Path, bool]:
    appdata = Path(os.environ.get("LOCALAPPDATA") or (Path.home() / "AppData" / "Local")) / "Mexico_Ong_Gia_Studio"
    default_ssd = appdata / "SSD_Render_Staging"
    workspace_staging = get_root_dir() / "cache" / "SSD_Render_Staging"
    use_ssd = True
    custom_ssd = ""

    for cfg_cand in (
        appdata / "storage_paths.json",
        get_root_dir() / "config.json",
    ):
        if cfg_cand.exists():
            try:
                d = json.loads(cfg_cand.read_text(encoding="utf-8"))
                if isinstance(d, dict):
                    if "use_ssd_staging" in d:
                        use_ssd = bool(d["use_ssd_staging"])
                    if d.get("ssd_staging_dir"):
                        custom_ssd = str(d["ssd_staging_dir"]).strip()
                    break
            except Exception:
                pass

    target_ssd = Path(custom_ssd) if custom_ssd else default_ssd
    try:
        target_ssd.mkdir(parents=True, exist_ok=True)
    except Exception:
        target_ssd = workspace_staging
        target_ssd.mkdir(parents=True, exist_ok=True)

    # Tự động chuyển ổ đệm Staging sang ổ chứa ứng dụng (D:) nếu ổ C: còn trống dưới 10 GB (tránh lỗi ENOSPC -28)
    try:
        free_bytes = shutil.disk_usage(str(target_ssd)).free
        if free_bytes < 10 * 1024 * 1024 * 1024:
            workspace_staging.mkdir(parents=True, exist_ok=True)
            if shutil.disk_usage(str(workspace_staging)).free > free_bytes:
                target_ssd = workspace_staging
    except Exception:
        pass
    return target_ssd, use_ssd


def get_saved_render_progress(output_path: str, total_dur: float = 0.0) -> Dict[str, Any]:
    try:
        out_dir = os.path.dirname(os.path.abspath(output_path))
        base_stem = os.path.splitext(os.path.basename(output_path))[0]
        ssd_root, _ = get_default_ssd_staging_dir()
        cand_dirs = [
            ssd_root / f"_{base_stem}_resume_cache",
            Path(out_dir) / f"_{base_stem}_resume_cache",
        ]
        resume_dir = next((d for d in cand_dirs if d.exists()), cand_dirs[0])
        if not resume_dir.exists():
            return {"has_checkpoint": False, "completed_sec": 0.0, "percent": 0.0}
        meta_file = resume_dir / "resume_meta.json"
        if total_dur <= 0 and meta_file.exists():
            try:
                total_dur = float(json.loads(meta_file.read_text(encoding="utf-8")).get("total_dur", 0.0) or 0.0)
            except Exception:
                total_dur = 0.0
        comp_sec = 0.0
        for ts_f in sorted(resume_dir.glob("seg_clean_*.ts")):
            if ts_f.stat().st_size > 100_000:
                comp_sec += get_audio_duration(str(ts_f))
        for raw_f in sorted(resume_dir.glob("seg_raw_*.ts")):
            if raw_f.stat().st_size > 100_000:
                d_r = get_audio_duration(str(raw_f))
                if d_r >= 4.0:
                    comp_sec += max(0.0, d_r - 1.5)
        pct = min(99.0, round((comp_sec / total_dur) * 100.0, 1)) if total_dur > 0 else 0.0
        return {
            "has_checkpoint": comp_sec >= 3.0,
            "completed_sec": round(comp_sec, 2),
            "total_dur": round(total_dur, 2),
            "percent": pct,
        }
    except Exception:
        return {"has_checkpoint": False, "completed_sec": 0.0, "percent": 0.0}


# ==============================================================================
# 3. HÀM RENDER CHÍNH: STOCK TỐI NHẸ + CACHE GREEN LOOP + ẢNH GREEN ĐÁY PHẢI (0.9) + SUB KARAOKE CAO NHẤT
# ==============================================================================
def render_drama_nhat_video(
    audio_path: str,
    subtitle_path: str,
    stock_video_path: str,
    output_path: str,
    channel_name: str = ".",
    resolution: str = "1920x1080",
    fps: int = 24,
    font_name: str = "Arial",
    font_size: int = 52,
    outline: float = 3.5,
    sub_color: str = "&H0000FFFF",
    watermark_opacity: float = 0.0,
    box_opacity: float = 0.0,
    stock_speed: float = 0.75,
    brightness: float = -0.12,
    contrast: float = 1.05,
    vignette_param: str = "",
    flip_horizontal: bool = False,
    zoom_factor: float = 1.0,
    extend_with_flip_zoom: bool = True,
    particles_clip: Optional[str] = None,
    fonts_dir: Optional[str] = None,
    bgm_path: Optional[str] = None,
    bgm_volume: float = 0.08,
    progress_callback: Optional[Callable[[float, str], None]] = None,
    performance_mode: Optional[str] = None,
    ssd_staging_dir: Optional[str] = None,
    use_ssd_staging: Optional[bool] = None,
    green_screen_image_path: Optional[str] = None,
    visual_cues_path: Optional[str] = None,
) -> Dict[str, Any]:
    start_time = time.time()
    root_dir = get_root_dir()
    out_dir = os.path.dirname(os.path.abspath(output_path))

    try:
        w_str, h_str = resolution.lower().split("x")
        target_w, target_h = int(w_str), int(h_str)
    except Exception:
        target_w, target_h = 1920, 1080

    scale_factor = target_h / 1080.0
    dur = get_audio_duration(audio_path)
    if dur <= 0:
        raise ValueError(f"Không thể đo thời lượng audio: {audio_path}")

    # Nạp cấu hình bố cục đã lưu từ màn hình Preview
    layout_cfg = load_video_layout_config(root_dir)
    bg_cfg = layout_cfg.get("stock_background") or {}
    char_cfg = layout_cfg.get("script_green_character") or {}
    sub_cfg = layout_cfg.get("karaoke_subtitle") or {}

    # Chỉ làm tối nhẹ theo cấu hình (mặc định brightness = -0.12, contrast = 1.05, saturation = 0.92)
    eff_brightness = float(bg_cfg.get("brightness", -0.12))
    eff_contrast = float(bg_cfg.get("contrast", 1.05))
    eff_saturation = float(bg_cfg.get("saturation", 0.92))
    eff_stock_speed = float(bg_cfg.get("stock_speed", 0.75))

    perf_mode = (performance_mode or os.environ.get("STUDIO_PERF_MODE") or "full_100").strip().lower()
    is_work_70 = perf_mode == "work_70"
    total_cores = os.cpu_count() or 8
    win_flags = 0x08000000 if os.name == "nt" else 0
    cpu_threads = max(4, int(round(total_cores * 0.65))) if is_work_70 else max(4, total_cores - 1)
    filter_threads = max(2, cpu_threads // 2)

    base_stem = os.path.splitext(os.path.basename(output_path))[0]
    proj_prefix = re.sub(r"_master$", "", base_stem, flags=re.IGNORECASE)

    # Tự động dò tìm Ảnh Green Theo Kịch Bản (`THUMBNAIL-NENXANH.png` / `{ma_id}_THUMBNAIL_NENXANH.png`)
    if not green_screen_image_path or not os.path.exists(green_screen_image_path):
        out_p = Path(out_dir)
        audio_p = Path(audio_path).resolve()
        proj_root_from_audio = audio_p.parent.parent if audio_p.parent.name.lower() == "assets" else out_p.parent
        gs_candidates = [
            out_p / "THUMBNAIL-NENXANH.png",
            out_p / f"{proj_prefix}_THUMBNAIL_NENXANH.png",
            proj_root_from_audio / "renders" / "THUMBNAIL-NENXANH.png",
            proj_root_from_audio / "renders" / f"{proj_prefix}_THUMBNAIL_NENXANH.png",
            proj_root_from_audio / "THUMBNAIL-NENXANH.png",
            proj_root_from_audio / f"{proj_prefix}_THUMBNAIL_NENXANH.png",
            out_p.parent / "THUMBNAIL-NENXANH.png",
            out_p.parent / f"{proj_prefix}_THUMBNAIL_NENXANH.png",
            root_dir / "THUMBNAIL-NENXANH.png",
            root_dir / "adas_skills" / "05_seo_thumbnail_padre_mx" / "references" / "example_green_screen.png",
        ]
        for gsc in gs_candidates:
            if gsc.exists() and gsc.stat().st_size > 5_000:
                green_screen_image_path = str(gsc)
                break

    default_ssd_dir, default_use_ssd = get_default_ssd_staging_dir()
    active_use_ssd = default_use_ssd if use_ssd_staging is None else bool(use_ssd_staging)
    active_ssd_root = Path(ssd_staging_dir) if (ssd_staging_dir and str(ssd_staging_dir).strip()) else default_ssd_dir

    work_parent_dir = active_ssd_root if active_use_ssd else Path(out_dir)
    work_parent_dir.mkdir(parents=True, exist_ok=True)
    temp_output_path = str(work_parent_dir / f"_{base_stem}_rendering_tmp.mp4")
    resume_dir = work_parent_dir / f"_{base_stem}_resume_cache"
    resume_dir.mkdir(parents=True, exist_ok=True)
    meta_file = resume_dir / "resume_meta.json"

    # Kiểm tra & tự phục hồi nếu file Stock bị di chuyển
    if not stock_video_path or not os.path.exists(stock_video_path):
        from backend.stock_manager import StockManager
        sm = StockManager(root_dir)
        best = sm.get_best_available_stock()
        if best and best.get("abs_path") and os.path.exists(best["abs_path"]):
            stock_video_path = str(best["abs_path"])

    audio_size = os.path.getsize(audio_path) if os.path.exists(audio_path) else 0
    current_meta = {
        "audio_size": audio_size,
        "total_dur": round(dur, 3),
        "resolution": f"{target_w}x{target_h}",
        "fps": int(fps),
        "stock_video_path": stock_video_path,
    }
    if meta_file.exists():
        try:
            old_meta = json.loads(meta_file.read_text(encoding="utf-8"))
            same_job = (
                old_meta.get("audio_size") == audio_size
                and abs(float(old_meta.get("total_dur", 0.0)) - dur) < 2.0
                and old_meta.get("resolution") == current_meta["resolution"]
            )
            if not same_job:
                for f_old in resume_dir.glob("*.ts"):
                    try:
                        f_old.unlink()
                    except Exception:
                        pass
        except Exception:
            pass
    try:
        meta_file.write_text(json.dumps(current_meta, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass

    # Thu hồi các đoạn .ts dở dang nếu có
    existing_clean_count = len(list(resume_dir.glob("seg_clean_*.ts")))
    for raw_ts in sorted(resume_dir.glob("seg_raw_*.ts")):
        d_raw = get_audio_duration(str(raw_ts))
        if d_raw >= 4.0 and raw_ts.stat().st_size > 150_000:
            safe_dur = max(2.0, round(d_raw - 1.5, 2))
            clean_target = resume_dir / f"seg_clean_{existing_clean_count:04d}.ts"
            existing_clean_count += 1
            try:
                subprocess.run(
                    [
                        _FFMPEG_BIN, "-y", "-v", "error",
                        "-i", str(raw_ts),
                        "-t", f"{safe_dur:.2f}",
                        "-c", "copy", "-f", "mpegts", str(clean_target),
                    ],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=win_flags,
                    timeout=30,
                )
            except Exception:
                pass
        try:
            raw_ts.unlink()
        except Exception:
            pass

    valid_clean_segments: List[str] = []
    completed_sec = 0.0
    for c_ts in sorted(resume_dir.glob("seg_clean_*.ts")):
        d_c = get_audio_duration(str(c_ts))
        if d_c >= 2.0 and c_ts.stat().st_size > 100_000:
            valid_clean_segments.append(str(c_ts))
            completed_sec += d_c
        else:
            try:
                c_ts.unlink()
            except Exception:
                pass

    remaining_dur = max(0.0, dur - completed_sec)
    work_fps = int(fps)
    pts_factor = round(1.0 / eff_stock_speed, 3) if eff_stock_speed > 0 else 1.0
    stock_dur = get_audio_duration(stock_video_path)

    # 1. Tạo Cache cho các lớp Video Green cố định từ Kho_Green (nếu có)
    fixed_green_cache_nut = build_or_get_fixed_green_layers_cache(
        layout_cfg=layout_cfg,
        target_w=target_w,
        target_h=target_h,
        work_fps=work_fps,
        root_dir=root_dir,
    )

    # 2. Chuẩn bị Ảnh Green Theo Kịch Bản đặt sát đáy dưới cùng (y = H - h), Opacity = 0.9
    char_cutout_png: Optional[str] = None
    if char_cfg.get("enabled", True) and green_screen_image_path and os.path.exists(green_screen_image_path):
        char_cutout_png = prepare_script_green_character_cutout(
            green_screen_path=green_screen_image_path,
            target_w=target_w,
            target_h=target_h,
            char_cfg=char_cfg,
            cache_dir=root_dir / "cache" / "script_char_cutouts",
        )

    # 3. Chuẩn bị Phụ đề Karaoke CapCut (.ass) ở Lớp Cao Nhất
    karaoke_ass_path = resume_dir / "karaoke_subtitles_active.ass"
    karaoke_opts = {
        "width": target_w,
        "height": target_h,
        "fontSize": int(round(float(sub_cfg.get("fontSize", 52)) * scale_factor)),
        "centerX": int(round(float(sub_cfg.get("centerX", 740)) * (target_w / 1920.0))),
        "centerY": int(round(float(sub_cfg.get("centerY", 965)) * scale_factor)),
        "textColor": sub_cfg.get("textColor", "#FFFF00"),
        "boxColor": sub_cfg.get("boxColor", "#7C00FF"),
        "outlineColor": sub_cfg.get("outlineColor", "#000000"),
        "maxWordsPerLine": int(sub_cfg.get("maxWordsPerLine", 5)),
        "maxCharsPerLine": int(sub_cfg.get("maxCharsPerLine", 26)),
    }
    generated_ass = generate_karaoke_ass_from_srt(
        srt_path=subtitle_path,
        output_ass_path=str(karaoke_ass_path),
        options=karaoke_opts,
        time_offset_sec=completed_sec,
    )

    print("================================================================================")
    print("🎬 [MEXICO ÔNG GIÀ RENDERER V2] DỰNG VIDEO ĐA LỚP + KARAOKE SUB + CACHE GREEN")
    print(f"📐 Độ phân giải: {target_w}x{target_h} | 🎞️ FPS: {fps} | 🎵 Thời lượng: {dur/60:.2f} phút")
    print(f"🌑 Lớp #4 (Đáy): Stock làm tối nhẹ (brightness={eff_brightness}, contrast={eff_contrast})")
    print(f"🟩 Lớp #3 (Giữa): Cache Video Green cố định: {Path(fixed_green_cache_nut).name if fixed_green_cache_nut else 'Không bật'}")
    print(f"👴 Lớp #2 (Trên Green): Ảnh Green Kịch Bản sát đáy phải (Opacity={char_cfg.get('opacity', 0.9)}): {Path(char_cutout_png).name if char_cutout_png else 'Chưa có'}")
    print(f"🔥 Lớp #1 (Cao nhất): Phụ đề Karaoke CapCut (.ASS): {karaoke_ass_path.name if generated_ass else subtitle_path}")
    print("================================================================================")

    use_nvenc = check_nvenc_available()
    gop_size = str(max(24, int(fps) * 2))
    nvenc_codec_args = [
        "-c:v", "h264_nvenc",
        "-preset", "p1" if is_work_70 else "p2",
        "-tune", "hq",
        "-rc", "vbr",
        "-cq", "21",
        "-b:v", "0",
        "-g", gop_size,
        "-pix_fmt", "yuv420p",
    ]
    cpu_codec_args = [
        "-c:v", "libx264",
        "-preset", "superfast",
        "-crf", "21",
        "-g", gop_size,
        "-threads", str(cpu_threads),
        "-pix_fmt", "yuv420p",
    ]
    v_codec_args = nvenc_codec_args if use_nvenc else cpu_codec_args
    encoder_label = "NVIDIA GPU NVENC" if use_nvenc else f"CPU Multi-Thread ({cpu_threads} threads)"

    if remaining_dur > 1.5:
        filters: List[str] = []
        base_inputs_cmd: List[str] = [_FFMPEG_BIN, "-y"]
        input_idx = 0

        # LỚP #4 (ĐÁY): Video Stock có sẵn — Chỉ làm tối nhẹ
        stock_seek_raw = round((completed_sec / pts_factor) % max(1.0, stock_dur), 2) if (completed_sec > 0 and stock_dur > 0) else 0.0
        stock_seek_args = ["-ss", f"{stock_seek_raw:.2f}"] if stock_seek_raw > 0.1 else []
        base_inputs_cmd.extend(["-stream_loop", "-1", *stock_seek_args, "-i", stock_video_path])
        stock_in_idx = input_idx
        input_idx += 1

        flip_filter = "hflip," if flip_horizontal else ""
        filters.append(
            f"[{stock_in_idx}:v]setpts={pts_factor}*PTS,fps={work_fps},{flip_filter}"
            f"scale={target_w}:{target_h}:force_original_aspect_ratio=increase:flags=fast_bilinear,"
            f"crop={target_w}:{target_h},setsar=1,"
            f"eq=brightness={eff_brightness:.2f}:contrast={eff_contrast:.2f}:saturation={eff_saturation:.2f},"
            f"format=yuv420p[v_bg]"
        )
        current_v = "[v_bg]"

        # LỚP #3 (GIỮA): Cache các Video Green cố định từ Kho_Green (Loop -stream_loop -1)
        if fixed_green_cache_nut and os.path.exists(fixed_green_cache_nut):
            base_inputs_cmd.extend(["-stream_loop", "-1", "-i", fixed_green_cache_nut])
            green_cache_idx = input_idx
            input_idx += 1
            filters.append(f"{current_v}[{green_cache_idx}:v]overlay=x=0:y=0:shortest=1:format=yuv420[v_with_green]")
            current_v = "[v_with_green]"

        # LỚP #2 (TRÊN VIDEO GREEN, DƯỚI SUB): Ảnh Green Theo Kịch Bản đặt sát đáy dưới cùng (Opacity = 0.9)
        if char_cutout_png and os.path.exists(char_cutout_png):
            base_inputs_cmd.extend(["-loop", "1", "-i", char_cutout_png])
            char_in_idx = input_idx
            input_idx += 1
            filters.append(f"[{char_in_idx}:v]fps={work_fps},format=yuva420p[char_rgba]")
            filters.append(f"{current_v}[char_rgba]overlay=x=0:y=0:shortest=1:format=yuv420[v_with_char]")
            current_v = "[v_with_char]"

        # LỚP #1 (CAO NHẤT - TOPMOST): Phụ đề chạy như Karaoke (.ASS)
        if generated_ass and os.path.exists(generated_ass):
            abs_ass = os.path.abspath(generated_ass).replace("\\", "/").replace(":", r"\:").replace("'", r"\'")
            filters.append(f"{current_v}subtitles=filename='{abs_ass}':original_size={target_w}x{target_h},fps={fps},format=yuv420p[v_out]")
        elif subtitle_path and os.path.exists(subtitle_path):
            abs_srt = os.path.abspath(subtitle_path).replace("\\", "/").replace(":", r"\:").replace("'", r"\'")
            filters.append(f"{current_v}subtitles=filename='{abs_srt}',fps={fps},format=yuv420p[v_out]")
        else:
            filters.append(f"{current_v}fps={fps},format=yuv420p[v_out]")

        # Đầu vào Audio (Voice + Nhạc nền BGM tùy chọn)
        voice_input_idx = input_idx
        if completed_sec > 0.1:
            base_inputs_cmd.extend(["-ss", f"{completed_sec:.3f}", "-i", audio_path])
        else:
            base_inputs_cmd.extend(["-i", audio_path])
        input_idx += 1

        has_bgm = bool(bgm_path and os.path.exists(str(bgm_path)))
        if has_bgm:
            bgm_seek_args = ["-ss", f"{(completed_sec % 180.0):.2f}"] if completed_sec > 0.1 else []
            base_inputs_cmd.extend(["-stream_loop", "-1", *bgm_seek_args, "-i", str(bgm_path)])
            bgm_in_idx = input_idx
            input_idx += 1
            filters.append(
                f"[{voice_input_idx}:a]volume=1.0[voice];"
                f"[{bgm_in_idx}:a]volume={bgm_volume}[bgm];"
                f"[voice][bgm]amix=inputs=2:duration=first:dropout_transition=0,volume=2.0[a_out]"
            )
        else:
            filters.append(f"[{voice_input_idx}:a]volume=1.0[a_out]")

        fc = ";".join(filters)
        next_seg_idx = len(valid_clean_segments)
        current_raw_seg = str(resume_dir / f"seg_raw_{next_seg_idx:04d}.ts")

        def _build_encode_cmd(codec_args_list: List[str]) -> List[str]:
            return [
                *base_inputs_cmd,
                "-t", f"{remaining_dur:.3f}",
                "-filter_complex_threads", str(filter_threads),
                "-filter_complex", fc,
                "-map", "[v_out]",
                "-map", "[a_out]",
                *codec_args_list,
                "-threads", str(cpu_threads),
                "-r", str(fps),
                "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
                "-progress", "pipe:1",
                "-f", "mpegts",
                current_raw_seg,
            ]

        time_regex = re.compile(r"out_time=(\d{2}:\d{2}:\d{2}\.\d+)")
        log_tail: List[str] = []

        for enc_try in range(2):
            active_codec_args = v_codec_args if enc_try == 0 else cpu_codec_args
            cmd = _build_encode_cmd(active_codec_args)
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                encoding="utf-8",
                errors="replace",
                creationflags=win_flags,
            )

            log_tail.clear()
            last_cb_ts = 0.0
            max_seg_sec_reached = 0.0

            try:
                while True:
                    line = process.stdout.readline()
                    if not line and process.poll() is not None:
                        break
                    line = line.strip()
                    if line:
                        log_tail.append(line)
                        if len(log_tail) > 25:
                            log_tail.pop(0)
                    if "out_time=" in line:
                        match = time_regex.search(line)
                        if match:
                            curr_seg_sec = parse_time_to_seconds(match.group(1))
                            if curr_seg_sec > max_seg_sec_reached:
                                max_seg_sec_reached = curr_seg_sec
                            total_done_sec = min(dur, completed_sec + curr_seg_sec)
                            percent = min(99.9, round((total_done_sec / dur) * 100, 1))
                            now_cb = time.time()
                            if progress_callback and (now_cb - last_cb_ts >= 0.8 or percent >= 99.9):
                                last_cb_ts = now_cb
                                progress_callback(percent, f"Đang render video ({encoder_label}): {percent}% ({total_done_sec:.0f}s / {dur:.0f}s)")
            except BaseException:
                try:
                    process.kill()
                    process.wait(timeout=3)
                except Exception:
                    pass
                raise

            rc = process.poll()
            if rc == 0:
                break
            if enc_try == 0 and use_nvenc and max_seg_sec_reached < 3.0:
                print(f"⚠️ [NVENC FALLBACK] Chuyển sang CPU Multi-Thread ({cpu_threads} threads)...")
                continue
            err_detail = "\n".join(log_tail[-8:])
            raise RuntimeError(f"FFmpeg render lỗi (mã {rc}): {err_detail}")

        final_clean_seg = str(resume_dir / f"seg_clean_{next_seg_idx:04d}.ts")
        if os.path.exists(current_raw_seg):
            os.replace(current_raw_seg, final_clean_seg)
            valid_clean_segments.append(final_clean_seg)

    if not valid_clean_segments:
        raise RuntimeError("Không tìm thấy dữ liệu phân đoạn video nào sau khi encode.")

    if len(valid_clean_segments) == 1:
        remux_cmd = [
            _FFMPEG_BIN, "-y", "-v", "error",
            "-i", valid_clean_segments[0],
            "-t", f"{dur:.3f}",
            "-c", "copy", "-bsf:a", "aac_adtstoasc",
            temp_output_path,
        ]
    else:
        concat_list_file = resume_dir / "concat_segments.txt"
        with open(concat_list_file, "w", encoding="utf-8") as f_cat:
            for seg_p in valid_clean_segments:
                clean_seg_p = os.path.abspath(seg_p).replace("\\", "/").replace("'", "'\\''")
                f_cat.write(f"file '{clean_seg_p}'\n")
        remux_cmd = [
            _FFMPEG_BIN, "-y", "-v", "error",
            "-f", "concat", "-safe", "0",
            "-i", str(concat_list_file),
            "-t", f"{dur:.3f}",
            "-c", "copy", "-bsf:a", "aac_adtstoasc",
            temp_output_path,
        ]

    remux_res = subprocess.run(remux_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, creationflags=win_flags)
    if remux_res.returncode != 0:
        raise RuntimeError(f"Lỗi đóng gói MP4: {remux_res.stderr[-300:]}")

    rendered_dur = get_audio_duration(temp_output_path)
    os.makedirs(out_dir, exist_ok=True)
    shutil.move(temp_output_path, output_path)
    shutil.rmtree(resume_dir, ignore_errors=True)

    cost = time.time() - start_time
    if progress_callback:
        progress_callback(100.0, f"Render video hoàn tất trong {cost:.1f}s!")

    return {
        "output_path": output_path,
        "duration": rendered_dur,
        "render_time": cost,
        "resolution": f"{target_w}x{target_h}",
        "fps": fps,
    }
