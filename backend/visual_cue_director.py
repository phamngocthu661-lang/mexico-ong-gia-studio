import os
import re
import io
import math
import json
import wave
import struct
import shutil
import hashlib
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

_BIN_DIR = Path(__file__).resolve().parent.parent / "bin"
if not _BIN_DIR.exists():
    _BIN_DIR = Path(__file__).resolve().parent.parent.parent / "bin"
if _BIN_DIR.exists():
    os.environ["PATH"] = str(_BIN_DIR) + os.pathsep + os.environ.get("PATH", "")

_FFMPEG_BIN = str(_BIN_DIR / "ffmpeg.exe") if (_BIN_DIR / "ffmpeg.exe").exists() else "ffmpeg"

# Danh mục 8 bộ Icon Video Green (#00FF00) + Từ khóa kích hoạt đa ngôn ngữ (es-MX, VI, EN, JA)
GREEN_ICON_CATALOG: Dict[str, Dict[str, Any]] = {
    "gavel": {
        "video_name": "icon_green_gavel.mp4",
        "sfx_name": "sfx_gavel.wav",
        "label": "Búa tòa / Phán quyết pháp lý",
        "keywords": [
            "juez", "juzgado", "tribunal", "abogado", "abogada", "sentencia", "demanda",
            "audiencia", "notario", "notaría", "fiscal", "justicia", "ley", "juicio",
            "tòa án", "thẩm phán", "luật sư", "phán quyết", "kiện", "công lý",
            "court", "judge", "lawyer", "verdict", "lawsuit", "attorney",
            "裁判", "弁護士", "判事", "判決", "法廷",
        ],
    },
    "contract": {
        "video_name": "icon_green_contract.mp4",
        "sfx_name": "sfx_contract.wav",
        "label": "Hợp đồng / Sổ đỏ / Văn bản",
        "keywords": [
            "contrato", "escritura", "escrituras", "documento", "documentos", "firma",
            "firmar", "firmó", "papeles", "cláusula", "propiedad", "acta", " carpeta",
            "registro", "certificado", "título", "notarial",
            "hợp đồng", "sổ đỏ", "giấy tờ", "ký tên", "văn bản", "biên bản",
            "contract", "deed", "document", "signature", "signed", "papers",
            "契約書", "書類", "署名", "印鑑", "登記",
        ],
    },
    "will": {
        "video_name": "icon_green_will.mp4",
        "sfx_name": "sfx_will.wav",
        "label": "Di chúc / Thừa kế",
        "keywords": [
            "testamento", "herencia", "heredero", "herederos", "desheredar", "sucesión",
            "patrimonio", "legado", "bienes", "fortuna familiar", "última voluntad",
            "di chúc", "thừa kế", "tài sản", "chia gia tài",
            "will", "inheritance", "heir", "estate", "legacy",
            "遺言", "遺産", "相続", "財産",
        ],
    },
    "money": {
        "video_name": "icon_green_money.mp4",
        "sfx_name": "sfx_money.wav",
        "label": "Tiền bạc / Ngân hàng / Tài khoản",
        "keywords": [
            "dinero", "pesos", "millones", "millón", "banco", "bancaria", "cuenta",
            "fortuna", "pagar", "deuda", "cheque", "transferencia", "pensión", "ahorros",
            "efectivo", "dólares", "caja fuerte", "bóveda", "riqueza", "cobrar",
            "tiền", "triệu", "ngân hàng", "tài khoản", "nợ", "lương hưu", "séc",
            "money", "millions", "bank", "account", "debt", "check", "pension", "cash",
            "お金", "万円", "銀行", "口座", "年金", "借金", "貯金",
        ],
    },
    "heartbreak": {
        "video_name": "icon_green_heartbreak.mp4",
        "sfx_name": "sfx_heartbreak.wav",
        "label": "Tim vỡ / Phản bội / Nước mắt",
        "keywords": [
            "traición", "traicionar", "llorar", "lágrimas", "dolor", "corazón", "ingrato",
            "ingratos", "humillación", "desprecio", "abandono", "vergüenza", "herida",
            "pecho", "sollozo", "sufrimiento", "tristeza", "desagradecido", "estorbo",
            "phản bội", "nước mắt", "khóc", "đau đớn", "trái tim", "bất hiếu", "sỉ nhục",
            "betrayal", "tears", "crying", "heartbroken", "humiliation", "ungrateful",
            "裏切り", "涙", "泣く", "胸が痛", "絶望", "親不孝",
        ],
    },
    "warning": {
        "video_name": "icon_green_warning.mp4",
        "sfx_name": "sfx_warning.wav",
        "label": "Cảnh báo / Đuổi khỏi nhà / Nguy hiểm",
        "keywords": [
            "policía", "patrulla", "peligro", "amenaza", "calle", "maleta", "echaron",
            "correr", "alarma", "urgente", "golpe", "grito", "gritar", "fuera de aquí",
            "asilo", "anciano", "basura", "arresto", "guardia", "seguridad",
            "cảnh sát", "đuổi", "va li", "nguy hiểm", "đe dọa", "viện dưỡng lão",
            "police", "danger", "threat", "suitcase", "kicked out", "nursing home",
            "警察", "危険", "追い出", "スーツケース", "老人ホーム",
        ],
    },
    "house": {
        "video_name": "icon_green_house.mp4",
        "sfx_name": "sfx_house.wav",
        "label": "Ngôi nhà / Điền trang / Chìa khóa",
        "keywords": [
            "casa", "hogar", "llave", "llaves", "cerradura", "mansión", "terreno",
            "rancho", "hacienda", "techo", "puerta", "portón", "finca", "desalojo",
            "ngôi nhà", "chìa khóa", "ổ khóa", "biệt thự", "mảnh đất", "cổng",
            "house", "home", "keys", "lock", "mansion", "ranch", "eviction",
            "自宅", "鍵", "屋敷", "実家", "玄関",
        ],
    },
    "phone": {
        "video_name": "icon_green_phone.mp4",
        "sfx_name": "sfx_phone.wav",
        "label": "Điện thoại / Ghi âm / Bằng chứng",
        "keywords": [
            "teléfono", "llamada", "celular", "mensaje", "grabación", "audio", "cámara",
            "video", "evidencia", "prueba", "pruebas", "pantalla", "altavoz", "secreto",
            "điện thoại", "cuộc gọi", "tin nhắn", "ghi âm", "camera", "bằng chứng",
            "phone", "call", "recording", "camera", "evidence", "speakerphone",
            "電話", "録音", "カメラ", "証拠", "スマホ",
        ],
    },
}


def _generate_sfx_wav_file(sfx_path: Path, category: str) -> None:
    """
    Tổng hợp hiệu ứng âm thanh (SFX) sắc nét chuẩn 24000Hz Mono 16-bit PCM WAV
    cho từng loại Icon Video Green (búa tòa, hợp đồng, di chúc, tiền, tim vỡ, cảnh báo...).
    """
    sfx_path.parent.mkdir(parents=True, exist_ok=True)
    sr = 24000
    dur = 0.85
    n_samples = int(sr * dur)
    samples: List[int] = []

    for i in range(n_samples):
        t = i / float(sr)
        val = 0.0
        if category == "gavel":
            # 2 nhịp búa gõ trầm ấm + vang nhẹ
            for hit_t in (0.02, 0.24):
                if t >= hit_t:
                    dt = t - hit_t
                    env = math.exp(-dt * 18.0)
                    val += env * (
                        0.55 * math.sin(2 * math.pi * 145.0 * dt)
                        + 0.30 * math.sin(2 * math.pi * 290.0 * dt)
                        + 0.15 * math.sin(2 * math.pi * 520.0 * dt)
                    )
        elif category in ("contract", "will"):
            # Tiếng chuông pha lê đôi sang trọng (Chime C5 -> G5)
            for idx_n, (st_t, freq) in enumerate(((0.0, 523.25), (0.14, 783.99))):
                if t >= st_t:
                    dt = t - st_t
                    env = math.exp(-dt * 6.5) * min(1.0, dt * 80.0)
                    val += env * (0.45 * math.sin(2 * math.pi * freq * dt) + 0.20 * math.sin(2 * math.pi * (freq * 2.0) * dt))
        elif category == "money":
            # Tiếng đồng xu / chuông ngân cao (Coin / Cash Register Bell E6 -> B6)
            for st_t, freq in ((0.0, 1318.5), (0.09, 1975.5)):
                if t >= st_t:
                    dt = t - st_t
                    env = math.exp(-dt * 8.0) * min(1.0, dt * 120.0)
                    val += env * (0.48 * math.sin(2 * math.pi * freq * dt) + 0.22 * math.sin(2 * math.pi * (freq * 2.5) * dt))
        elif category == "heartbreak":
            # Hợp âm thứ trầm lắng đi xuống (A4 -> E4 -> C4)
            for st_t, freq in ((0.0, 440.0), (0.16, 329.63), (0.32, 261.63)):
                if t >= st_t:
                    dt = t - st_t
                    env = math.exp(-dt * 5.5) * min(1.0, dt * 60.0)
                    val += env * 0.38 * math.sin(2 * math.pi * freq * dt)
        elif category == "warning":
            # Tín hiệu cảnh báo kịch tính 2 nhịp (Alert Pulse)
            for st_t in (0.0, 0.22):
                if st_t <= t <= st_t + 0.18:
                    dt = t - st_t
                    env = math.sin(math.pi * (dt / 0.18))
                    val += env * (0.42 * math.sin(2 * math.pi * 660.0 * dt) + 0.25 * math.sin(2 * math.pi * 880.0 * dt))
        else:
            # Pop / Notification êm dịu (House / Phone)
            for st_t, freq in ((0.0, 587.33), (0.12, 880.0)):
                if t >= st_t:
                    dt = t - st_t
                    env = math.exp(-dt * 7.5) * min(1.0, dt * 90.0)
                    val += env * 0.45 * math.sin(2 * math.pi * freq * dt)

        pcm_val = max(-32000, min(32000, int(val * 12500)))
        samples.append(pcm_val)

    with wave.open(str(sfx_path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(struct.pack(f"<{len(samples)}h", *samples))


def _draw_icon_symbol(draw, category: str, cx: int, cy: int, radius: int) -> None:
    """Vẽ biểu tượng đồ họa sắc nét trên huy hiệu tròn cho từng loại Icon Video Green."""
    # Huy hiệu nền tối viền vàng kim sang trọng (không dùng màu xanh lá để colorkey #00FF00 tách tuyệt đối sạch)
    draw.ellipse(
        [cx - radius, cy - radius, cx + radius, cy + radius],
        fill=(24, 28, 38),
        outline=(245, 196, 65),
        width=8,
    )
    inner_r = radius - 14
    draw.ellipse(
        [cx - inner_r, cy - inner_r, cx + inner_r, cy + inner_r],
        outline=(180, 135, 35),
        width=3,
    )

    if category == "gavel":
        # Búa thẩm phán vàng kim + đế gỗ đỏ sẫm
        draw.rounded_rectangle([cx - 52, cy - 48, cx + 18, cy - 16], radius=8, fill=(245, 196, 65), outline=(255, 235, 150), width=3)
        draw.line([(cx - 17, cy - 16), (cx + 42, cy + 42)], fill=(215, 155, 55), width=12)
        draw.rounded_rectangle([cx - 56, cy + 36, cx + 16, cy + 54], radius=5, fill=(165, 65, 45), outline=(245, 196, 65), width=2)
    elif category in ("contract", "will"):
        # Cuộn giấy / Văn bản pháp lý + dấu mộc đỏ
        doc_fill = (250, 244, 228) if category == "contract" else (248, 236, 200)
        draw.rounded_rectangle([cx - 42, cy - 54, cx + 42, cy + 54], radius=8, fill=doc_fill, outline=(215, 165, 50), width=4)
        for ly in range(cy - 34, cy + 22, 16):
            draw.line([(cx - 26, ly), (cx + 26, ly)], fill=(55, 60, 75), width=4)
        # Con dấu đỏ
        draw.ellipse([cx + 4, cy + 12, cx + 32, cy + 40], fill=(210, 35, 35), outline=(255, 215, 100), width=2)
    elif category == "money":
        # Thỏi vàng & đồng tiền vàng
        draw.rounded_rectangle([cx - 50, cy - 28, cx + 50, cy + 30], radius=10, fill=(240, 185, 40), outline=(255, 235, 140), width=4)
        draw.ellipse([cx - 22, cy - 22, cx + 22, cy + 22], fill=(255, 215, 70), outline=(175, 120, 20), width=3)
        draw.line([(cx, cy - 16), (cx, cy + 16)], fill=(140, 90, 10), width=5)
        draw.arc([cx - 12, cy - 12, cx + 12, cy + 2], start=120, end=40, fill=(140, 90, 10), width=4)
        draw.arc([cx - 12, cy - 2, cx + 12, cy + 12], start=300, end=220, fill=(140, 90, 10), width=4)
    elif category == "heartbreak":
        # Trái tim đỏ thẫm có vết nứt giữa
        draw.pieslice([cx - 48, cy - 42, cx + 2, cy + 8], start=180, end=360, fill=(220, 38, 55))
        draw.pieslice([cx - 2, cy - 42, cx + 48, cy + 8], start=180, end=360, fill=(220, 38, 55))
        draw.polygon([(cx - 48, cy - 16), (cx + 48, cy - 16), (cx, cy + 52)], fill=(220, 38, 55))
        # Đường nứt
        crack = [(cx + 2, cy - 34), (cx - 10, cy - 12), (cx + 8, cy + 6), (cx - 6, cy + 26), (cx + 2, cy + 50)]
        draw.line(crack, fill=(24, 28, 38), width=6)
    elif category == "warning":
        # Tam giác cảnh báo vàng-đỏ + dấu chấm than
        draw.polygon([(cx, cy - 54), (cx - 54, cy + 44), (cx + 54, cy + 44)], fill=(235, 55, 40), outline=(255, 215, 75), width=5)
        draw.line([(cx, cy - 24), (cx, cy + 14)], fill=(255, 255, 255), width=9)
        draw.ellipse([cx - 6, cy + 24, cx + 6, cy + 36], fill=(255, 255, 255))
    elif category == "house":
        # Ngôi nhà / Điền trang ấm áp
        draw.polygon([(cx, cy - 52), (cx - 54, cy - 4), (cx + 54, cy - 4)], fill=(205, 65, 45), outline=(255, 215, 95), width=3)
        draw.rectangle([cx - 38, cy - 4, cx + 38, cy + 48], fill=(245, 232, 205), outline=(185, 140, 55), width=3)
        draw.rectangle([cx - 12, cy + 14, cx + 12, cy + 48], fill=(135, 75, 40))
    else:
        # Điện thoại / Bằng chứng ghi âm
        draw.rounded_rectangle([cx - 28, cy - 52, cx + 28, cy + 52], radius=10, fill=(50, 60, 85), outline=(245, 196, 65), width=4)
        draw.rectangle([cx - 20, cy - 36, cx + 20, cy + 30], fill=(225, 235, 250))
        draw.ellipse([cx - 10, cy - 14, cx + 10, cy + 6], fill=(220, 45, 45))
        draw.ellipse([cx - 4, cy + 36, cx + 4, cy + 44], fill=(245, 196, 65))


def _generate_green_icon_mp4(mp4_path: Path, category: str) -> None:
    """
    Tạo video Icon Green (`assets/green_icons/icon_green_*.mp4`) dài đúng 4.0 giây
    trên nền xanh lá thuần khiết `#00FF00` (RGB 0,255,0) có hiệu ứng Pop-in & nhịp thở nhẹ.
    """
    from PIL import Image, ImageDraw

    mp4_path.parent.mkdir(parents=True, exist_ok=True)
    fps = 12
    dur_sec = 4.0
    total_frames = int(fps * dur_sec)
    size = 240
    tmp_dir = mp4_path.parent / f"_tmp_{category}"
    shutil.rmtree(tmp_dir, ignore_errors=True)
    tmp_dir.mkdir(parents=True, exist_ok=True)

    try:
        for f_idx in range(total_frames):
            t = f_idx / float(fps)
            # Hiệu ứng bật nảy 0.35s đầu, nhịp thở ở giữa, thu nhẹ 0.35s cuối
            if t < 0.30:
                scale = 0.55 + 0.50 * math.sin((t / 0.30) * (math.pi / 2.0))
            elif t > dur_sec - 0.30:
                rem = max(0.0, dur_sec - t)
                scale = 0.55 + 0.45 * (rem / 0.30)
            else:
                scale = 1.0 + 0.045 * math.sin(2.0 * math.pi * 1.5 * (t - 0.30))

            img = Image.new("RGB", (size, size), (0, 255, 0))
            draw = ImageDraw.Draw(img)
            rad = max(36, min(106, int(round(92 * scale))))
            _draw_icon_symbol(draw, category, size // 2, size // 2, rad)
            img.save(tmp_dir / f"f_{f_idx:03d}.png", format="PNG")

        win_flags = 0x08000000 if os.name == "nt" else 0
        cmd = [
            _FFMPEG_BIN, "-y", "-v", "error",
            "-framerate", str(fps),
            "-i", str(tmp_dir / "f_%03d.png"),
            "-c:v", "libx264",
            "-crf", "16",
            "-preset", "fast",
            "-pix_fmt", "yuv420p",
            "-t", f"{dur_sec:.2f}",
            str(mp4_path),
        ]
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, creationflags=win_flags)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def ensure_green_icons_and_sfx_assets(root_dir: Optional[Path] = None) -> Dict[str, Dict[str, str]]:
    """
    Đảm bảo thư mục `assets/green_icons/icon_green_*.mp4` và `assets/sfx/sfx_*.wav` luôn sẵn sàng
    trên ổ cứng (tự động khởi tạo nếu chưa có).
    """
    if root_dir is None:
        root_dir = Path(__file__).resolve().parent.parent
        if root_dir.name.lower() == "app":
            root_dir = root_dir.parent
    root_dir = Path(root_dir)

    icons_dir = root_dir / "assets" / "green_icons"
    sfx_dir = root_dir / "assets" / "sfx"
    icons_dir.mkdir(parents=True, exist_ok=True)
    sfx_dir.mkdir(parents=True, exist_ok=True)

    resolved: Dict[str, Dict[str, str]] = {}
    for cat, meta in GREEN_ICON_CATALOG.items():
        v_path = icons_dir / meta["video_name"]
        a_path = sfx_dir / meta["sfx_name"]
        if not v_path.exists() or v_path.stat().st_size < 2_000:
            try:
                _generate_green_icon_mp4(v_path, cat)
            except Exception as e:
                print(f"[VisualCueDirector] Lưu ý khi tạo {v_path.name}: {e}")
        if not a_path.exists() or a_path.stat().st_size < 2_000:
            try:
                _generate_sfx_wav_file(a_path, cat)
            except Exception as e:
                print(f"[VisualCueDirector] Lưu ý khi tạo {a_path.name}: {e}")

        # Đồng bộ sang app/assets nếu có thư mục app/
        app_root = root_dir / "app"
        if app_root.exists() and app_root.is_dir():
            try:
                app_ic = app_root / "assets" / "green_icons" / meta["video_name"]
                app_sf = app_root / "assets" / "sfx" / meta["sfx_name"]
                app_ic.parent.mkdir(parents=True, exist_ok=True)
                app_sf.parent.mkdir(parents=True, exist_ok=True)
                if v_path.exists() and (not app_ic.exists() or app_ic.stat().st_size != v_path.stat().st_size):
                    shutil.copy2(v_path, app_ic)
                if a_path.exists() and (not app_sf.exists() or app_sf.stat().st_size != a_path.stat().st_size):
                    shutil.copy2(a_path, app_sf)
            except Exception:
                pass

        resolved[cat] = {
            "category": cat,
            "label": meta["label"],
            "video_path": str(v_path),
            "sfx_path": str(a_path),
            "keywords": meta["keywords"],
        }
    return resolved


def normalize_character_to_strict_80_20_green_plate(
    source_image_path: Path,
    output_plate_path: Path,
    part_index: int = 1,
) -> Optional[Path]:
    """
    Chuẩn hóa ảnh Nhân vật Green Screen theo đúng bố cục 80/20 chuẩn Skill 04 (1920x1080):
    - Nhân vật nằm ở đúng 18%-22% bên phải màn hình (`x` từ 78% đến 100%, tức `x = 1498..1920`).
    - Toàn bộ 78%-82% bên trái (`x = 0..1498`) và nền xung quanh nhân vật đổ màu xanh lá thuần khiết `#00FF00` (RGB 0,255,0),
      không chữ, không lem viền xanh.
    - Hỗ trợ biến thiên sắc thái ánh sáng nhẹ theo từng Part (Part 1..7) khi tạo bộ `script_green_images/green_part_01..07.png`.
    """
    if not source_image_path or not Path(source_image_path).exists():
        return None
    try:
        from PIL import Image, ImageEnhance
        import numpy as np

        im = Image.open(source_image_path).convert("RGBA").resize((1920, 1080), Image.Resampling.LANCZOS)
        w, h = im.size
        arr = np.asarray(im, dtype=np.float32)

        # Chỉ lấy vùng bên phải (nơi chứa chân dung nhân vật) để tránh 100% chữ tiêu đề ở bên trái
        x_scan_start = int(round(w * 0.52))
        sub = arr[:, x_scan_start:, :]
        r, g, b, a = sub[:, :, 0], sub[:, :, 1], sub[:, :, 2], sub[:, :, 3]

        max_rb = np.maximum(r, b)
        green_excess = g - max_rb
        dist_to_green = np.sqrt((r - 0.0) ** 2 + (g - 255.0) ** 2 + (b - 0.0) ** 2)

        # Kiểm tra xem ảnh nguồn đã là ảnh nền xanh #00FF00 hay là ảnh THUMBNAIL.png nền thường
        is_green_source = float(np.mean(dist_to_green < 75.0)) > 0.12
        if is_green_source:
            fg_mask = (dist_to_green >= 72.0) & (green_excess <= 42.0) & (a > 128.0)
        else:
            # Dùng rembg hoặc tách khỏi nền trắng/sáng của THUMBNAIL.png
            fg_mask = None
            try:
                from rembg import remove as rembg_remove
                crop_pil = Image.fromarray(sub.astype(np.uint8), mode="RGBA")
                buf = io.BytesIO()
                crop_pil.save(buf, format="PNG")
                cut_bytes = rembg_remove(buf.getvalue())
                cut_im = Image.open(io.BytesIO(cut_bytes)).convert("RGBA")
                cut_a = np.asarray(cut_im, dtype=np.uint8)[:, :, 3]
                if float(np.mean(cut_a > 140)) >= 0.06:
                    fg_mask = cut_a > 140
            except Exception:
                fg_mask = None

            if fg_mask is None:
                is_white = (r > 236) & (g > 236) & (b > 236) & (np.abs(r - g) < 12) & (np.abs(g - b) < 12)
                col_w = np.linspace(1.0, 0.0, sub.shape[1])[None, :]
                fg_mask = ~(is_white & (col_w > 0.25))

        # Khử hoàn toàn lem viền xanh (despill) trên nhân vật trước khi đặt lên nền #00FF00
        spill = (g > max_rb) & fg_mask
        g_clean = np.where(spill, max_rb + (g - max_rb) * 0.15, g)

        ys, xs = np.where(fg_mask)
        if len(xs) < 50 or len(ys) < 50:
            return None

        x1, x2 = int(xs.min()), int(xs.max())
        y1, y2 = int(ys.min()), int(ys.max())

        char_rgb = np.stack(
            [
                np.clip(r, 0, 255).astype(np.uint8),
                np.clip(g_clean, 0, 255).astype(np.uint8),
                np.clip(b, 0, 255).astype(np.uint8),
                np.where(fg_mask, 255, 0).astype(np.uint8),
            ],
            axis=2,
        )
        char_crop = Image.fromarray(char_rgb, mode="RGBA").crop((x1, y1, x2 + 1, y2 + 1))

        # Biến thiên sắc thái cảm xúc/ánh sáng tinh tế cho từng Part 1..7 (nếu tạo từ cùng 1 ảnh gốc)
        part_grades = {
            1: (1.00, 1.00, 1.00),  # Part 1: Gốc chân thực
            2: (0.96, 1.06, 0.92),  # Part 2: Trầm buồn khi bị hắt hủi
            3: (0.94, 1.10, 0.88),  # Part 3: Đau đớn nội tâm
            4: (1.02, 1.08, 0.96),  # Part 4: Bình tĩnh thu thập chứng cứ
            5: (1.04, 1.05, 1.04),  # Part 5: Chuẩn bị pháp lý đanh thép
            6: (1.03, 1.12, 1.02),  # Part 6: Đối chất tại tòa / công bố sự thật
            7: (1.05, 1.02, 1.08),  # Part 7: Bình yên & công lý viên mãn
        }
        br_f, ct_f, sat_f = part_grades.get(int(part_index), (1.0, 1.0, 1.0))
        if (br_f, ct_f, sat_f) != (1.0, 1.0, 1.0):
            rgb_only = char_crop.convert("RGB")
            alpha_only = char_crop.getchannel("A")
            rgb_only = ImageEnhance.Brightness(rgb_only).enhance(br_f)
            rgb_only = ImageEnhance.Contrast(rgb_only).enhance(ct_f)
            rgb_only = ImageEnhance.Color(rgb_only).enhance(sat_f)
            char_crop = rgb_only.convert("RGBA")
            char_crop.putalpha(alpha_only)

        # Đặt nhân vật nằm gọn trong đúng 18%-22% bên phải màn hình (x từ 1498..1920, rộng ~384..416px)
        target_char_w = int(round(w * 0.205))  # 20.5% chiều ngang (nằm đúng giữa khoảng 18%-22%)
        target_char_h = int(round(h * 0.92))
        cw, ch = char_crop.size
        scale = min(target_char_w / max(1, cw), target_char_h / max(1, ch))
        new_w = max(345, min(422, int(round(cw * scale))))  # 345px (18%) .. 422px (22%)
        new_h = max(300, min(h, int(round(ch * scale))))
        char_resized = char_crop.resize((new_w, new_h), Image.Resampling.LANCZOS)

        # Làm cứng biên alpha (threshold 160) để TUYỆT ĐỐI KHÔNG có pixel bán trong suốt gây lem viền xanh
        cr_arr = np.asarray(char_resized, dtype=np.uint8).copy()
        hard_mask = cr_arr[:, :, 3] >= 160

        canvas_arr = np.zeros((h, w, 3), dtype=np.uint8)
        canvas_arr[:, :, 1] = 255  # Toàn bộ khung 1920x1080 mặc định là #00FF00 (RGB 0, 255, 0)

        paste_x = w - new_w  # Luôn >= 1920 - 422 = 1498 (tức >= 78% bên phải)
        paste_y = h - new_h  # Sát đáy khung hình

        roi = canvas_arr[paste_y : paste_y + new_h, paste_x : paste_x + new_w]
        for c_i in range(3):
            roi[:, :, c_i] = np.where(hard_mask, cr_arr[:, :, c_i], roi[:, :, c_i])
        canvas_arr[paste_y : paste_y + new_h, paste_x : paste_x + new_w] = roi

        output_plate_path = Path(output_plate_path)
        output_plate_path.parent.mkdir(parents=True, exist_ok=True)
        Image.fromarray(canvas_arr, mode="RGB").save(output_plate_path, format="PNG", optimize=True)
        return output_plate_path
    except Exception as e:
        print(f"[VisualCueDirector] Lưu ý khi chuẩn hóa ảnh Green 80/20: {e}")
        return None


def ensure_project_script_green_images(
    proj_dir: Path,
    renders_dir: Optional[Path] = None,
    proj_name: str = "",
) -> List[Path]:
    """
    Đảm bảo dự án có đủ:
    - `THUMBNAIL-NENXANH.png` (chuẩn bố cục 80/20: 78%-82% trái #00FF00, 18%-22% phải là nhân vật)
    - Bộ 7 ảnh `script_green_images/green_part_01.png` .. `green_part_07.png` theo 7 Phần của kịch bản.
    """
    proj_dir = Path(proj_dir)
    if renders_dir is None:
        renders_dir = proj_dir / "renders"
    if not proj_name:
        proj_name = proj_dir.name

    green_dir = proj_dir / "script_green_images"
    green_dir.mkdir(parents=True, exist_ok=True)

    # Tìm ảnh nguồn (ưu tiên THUMBNAIL-NENXANH.png, sau đó đến THUMBNAIL.png)
    src_candidates = [
        renders_dir / "THUMBNAIL-NENXANH.png",
        renders_dir / f"{proj_name}_THUMBNAIL_NENXANH.png",
        proj_dir / "THUMBNAIL-NENXANH.png",
        proj_dir / f"{proj_name}_THUMBNAIL_NENXANH.png",
        renders_dir / "THUMBNAIL.png",
        renders_dir / f"{proj_name}_THUMBNAIL_1.png",
        proj_dir / "THUMBNAIL.png",
        proj_dir / f"{proj_name}_THUMBNAIL_1.png",
    ]
    base_src = next((p for p in src_candidates if p.exists() and p.stat().st_size > 5_000), None)

    part_paths: List[Path] = []
    for p_idx in range(1, 8):
        part_file = green_dir / f"green_part_{p_idx:02d}.png"
        if not part_file.exists() or part_file.stat().st_size < 5_000:
            if base_src is not None:
                normalize_character_to_strict_80_20_green_plate(base_src, part_file, part_index=p_idx)
        if part_file.exists() and part_file.stat().st_size >= 5_000:
            part_paths.append(part_file)

    # Đồng bộ ngược lại THUMBNAIL-NENXANH.png nếu chưa chuẩn 80/20 hoặc chưa tồn tại
    if part_paths:
        for gs_target in (
            renders_dir / "THUMBNAIL-NENXANH.png",
            renders_dir / f"{proj_name}_THUMBNAIL_NENXANH.png",
            proj_dir / "THUMBNAIL-NENXANH.png",
        ):
            if not gs_target.exists() or gs_target.stat().st_size < 5_000:
                try:
                    gs_target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(part_paths[0], gs_target)
                except Exception:
                    pass

    return part_paths


def _format_hms(sec: float) -> str:
    sec = max(0.0, float(sec))
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = int(sec % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def build_7part_timestamps_and_inject_seo(
    proj_dir: Path,
    assets_dir: Path,
    timeline: List[Dict[str, Any]],
    total_duration: float,
) -> Tuple[Path, List[Dict[str, Any]]]:
    """
    Tính mốc thời gian bắt đầu & kết thúc của từng Phần (Part 1 -> Part 7) khớp với kịch bản,
    xuất ra `TIMESTAMPS.txt` và tự động chèn vào `SEO.txt` (`00_TIEU_DE_VA_SEO_YOUTUBE.txt` / `{proj}_SEO.txt`).
    """
    proj_dir = Path(proj_dir)
    assets_dir = Path(assets_dir)
    assets_dir.mkdir(parents=True, exist_ok=True)

    # Đọc kịch bản có nhãn [PART 1]..[PART 7] (ưu tiên PMX_FULL_SCRIPT.txt hoặc ghép từ part_a/b/c.txt)
    raw_full = ""
    for cand in (
        proj_dir / "PMX_FULL_SCRIPT.txt",
        proj_dir / "script_with_parts.txt",
        proj_dir / "script.txt",
    ):
        if cand.exists():
            try:
                txt = cand.read_text(encoding="utf-8", errors="ignore")
                if "[PART " in txt.upper():
                    raw_full = txt
                    break
            except Exception:
                pass

    if not raw_full:
        pa, pb, pc = proj_dir / "part_a.txt", proj_dir / "part_b.txt", proj_dir / "part_c.txt"
        if pa.exists() and pb.exists() and pc.exists():
            try:
                raw_full = "\n\n".join([
                    pa.read_text(encoding="utf-8", errors="ignore"),
                    pb.read_text(encoding="utf-8", errors="ignore"),
                    pc.read_text(encoding="utf-8", errors="ignore"),
                ])
            except Exception:
                raw_full = ""

    part_char_ratios: List[float] = []
    part_titles_default = [
        "Parte 1: El desprecio en silencio",
        "Parte 2: La herida en la familia",
        "Parte 3: Lo que nadie vio venir",
        "Parte 4: Las pruebas ocultas",
        "Parte 5: El documento decisivo",
        "Parte 6: El momento de la verdad",
        "Parte 7: Justicia y dignidad",
    ]

    if raw_full and re.search(r"\[\s*PART\s*[1-7]\s*\]", raw_full, flags=re.IGNORECASE):
        splits = re.split(r"\[\s*PART\s*([1-7])\s*\]", raw_full, flags=re.IGNORECASE)
        part_lengths: Dict[int, int] = {}
        for idx_s in range(1, len(splits) - 1, 2):
            try:
                p_num = int(splits[idx_s])
                p_body = splits[idx_s + 1].strip()
                part_lengths[p_num] = max(100, len(p_body))
            except Exception:
                pass
        if len(part_lengths) >= 2:
            lengths_7 = [part_lengths.get(i, 10000) for i in range(1, 8)]
            tot_c = float(sum(lengths_7))
            cum = 0.0
            for l_val in lengths_7:
                part_char_ratios.append(cum / tot_c)
                cum += l_val

    if len(part_char_ratios) != 7:
        part_char_ratios = [i / 7.0 for i in range(7)]

    # Ánh xạ tỷ lệ từng Part sang câu thoại gần nhất trong `timeline` để lấy đúng giây bắt đầu câu
    part_entries: List[Dict[str, Any]] = []
    for p_idx in range(7):
        target_sec = total_duration * part_char_ratios[p_idx]
        start_sec = 0.0 if p_idx == 0 else round(target_sec, 2)
        snippet = part_titles_default[p_idx]

        if timeline:
            best_item = min(timeline, key=lambda it: abs(float(it.get("start", 0.0)) - target_sec))
            if p_idx == 0:
                start_sec = 0.0
                best_item = timeline[0]
            else:
                start_sec = float(best_item.get("start", target_sec))
            raw_sent = str(best_item.get("text") or "").strip().replace("\n", " ")
            if raw_sent:
                short_s = raw_sent[:42].rstrip(" ,.;:") + ("..." if len(raw_sent) > 42 else "")
                snippet = f"Parte {p_idx + 1}: {short_s}"

        part_entries.append({
            "part": p_idx + 1,
            "start": round(start_sec, 3),
            "end": round(total_duration, 3),
            "hms": _format_hms(start_sec),
            "label": snippet,
        })

    # Đảm bảo thứ tự thời gian tăng dần nghiêm ngặt và gán `end` của mỗi Part = `start` của Part kế tiếp
    for i in range(1, len(part_entries)):
        if part_entries[i]["start"] <= part_entries[i - 1]["start"] + 5.0:
            part_entries[i]["start"] = round(min(total_duration - 1.0, part_entries[i - 1]["start"] + max(10.0, total_duration / 7.0)), 3)
            part_entries[i]["hms"] = _format_hms(part_entries[i]["start"])
        part_entries[i - 1]["end"] = part_entries[i]["start"]
    if part_entries:
        part_entries[-1]["end"] = round(max(part_entries[-1]["start"] + 1.0, total_duration), 3)

    ts_lines = [f"{pe['hms']} - {pe['label']}" for pe in part_entries]
    ts_text = "\n".join(ts_lines) + "\n"

    ts_file = assets_dir / "TIMESTAMPS.txt"
    ts_file.write_text(ts_text, encoding="utf-8")
    try:
        (proj_dir / "TIMESTAMPS.txt").write_text(ts_text, encoding="utf-8")
    except Exception:
        pass

    # Tự động chèn TIMESTAMPS.txt vào các file SEO trong dự án
    seo_candidates = [
        proj_dir / "00_TIEU_DE_VA_SEO_YOUTUBE.txt",
        proj_dir / "PMX_SEO_PACK.md",
        proj_dir / "SEO.txt",
        proj_dir / "renders" / f"{proj_dir.name}_SEO.txt",
    ]
    ts_block = (
        "\n\n================================================================================\n"
        "⏱️ TIMESTAMPS / CAPÍTULOS (PART 1 -> PART 7)\n"
        "================================================================================\n"
        f"{ts_text}"
    )
    for seo_f in seo_candidates:
        if seo_f.exists():
            try:
                cur_seo = seo_f.read_text(encoding="utf-8", errors="ignore")
                if "TIMESTAMPS / CAPÍTULOS (PART 1 -> PART 7)" in cur_seo:
                    cur_seo = re.sub(
                        r"\n*=+\n⏱️ TIMESTAMPS / CAPÍTULOS \(PART 1 -> PART 7\)\n=+\n[\s\S]*$",
                        ts_block,
                        cur_seo,
                    )
                else:
                    cur_seo = cur_seo.rstrip() + ts_block
                seo_f.write_text(cur_seo, encoding="utf-8")
            except Exception:
                pass

    return ts_file, part_entries


def _parse_srt_time_to_sec(ts_str: str) -> float:
    ts_str = (ts_str or "").strip().replace(",", ".")
    parts = ts_str.split(":")
    if len(parts) == 3:
        try:
            return int(parts[0]) * 3600.0 + int(parts[1]) * 60.0 + float(parts[2])
        except Exception:
            pass
    return 0.0


def parse_timestamps_txt_to_parts(timestamps_path: Path, total_duration: float) -> List[Dict[str, Any]]:
    """Đọc `TIMESTAMPS.txt` và trả về 7 khoảng thời gian `[start, end]` cho Part 1..7."""
    entries: List[Dict[str, Any]] = []
    if timestamps_path and Path(timestamps_path).exists():
        try:
            lines = [ln.strip() for ln in Path(timestamps_path).read_text(encoding="utf-8", errors="ignore").splitlines() if ln.strip()]
            for ln in lines:
                m = re.match(r"^(\d{1,2}:\d{2}(?::\d{2})?)\s*[-–—:]\s*(.+)$", ln)
                if m:
                    t_raw = m.group(1)
                    if t_raw.count(":") == 1:
                        t_raw = "00:" + t_raw
                    sec = _parse_srt_time_to_sec(t_raw)
                    entries.append({
                        "part": len(entries) + 1,
                        "start": round(sec, 3),
                        "end": round(total_duration, 3),
                        "hms": _format_hms(sec),
                        "label": m.group(2).strip(),
                    })
        except Exception:
            entries = []

    if len(entries) < 2:
        entries = []
        for idx in range(7):
            st = round((total_duration * idx) / 7.0, 3)
            ed = round((total_duration * (idx + 1)) / 7.0, 3)
            entries.append({
                "part": idx + 1,
                "start": st,
                "end": ed,
                "hms": _format_hms(st),
                "label": f"Parte {idx + 1}",
            })
    else:
        for i in range(len(entries) - 1):
            entries[i]["end"] = entries[i + 1]["start"]
        entries[-1]["end"] = round(max(entries[-1]["start"] + 1.0, total_duration), 3)

    return entries[:7]


def build_visual_cues_schedule(
    proj_dir: Path,
    assets_dir: Path,
    srt_path: Path,
    timestamps_path: Path,
    total_duration: float,
    root_dir: Optional[Path] = None,
    icon_duration_sec: float = 4.0,
    cooldown_min_sec: float = 45.0,
    cooldown_max_sec: float = 60.0,
    icon_x: int = 120,
    icon_y: int = 90,
) -> Dict[str, Any]:
    """
    Xây dựng Bộ Điều Phối Hình Ảnh Theo Kịch Bản (`visual_cues.json`):
    1. Ánh xạ 7 Phần (`Part 1 -> Part 7`) trong `TIMESTAMPS.txt` với bộ Ảnh Nhân Vật Green
       (`script_green_images/green_part_01..07.png` hoặc `THUMBNAIL-NENXANH.png`).
    2. Quét nội dung từng câu trong `subtitles.srt` để tự động bật các Icon Video Green
       (`assets/green_icons/icon_green_*.mp4` nền `#00FF00`) kéo dài 4 giây tại tọa độ góc trên bên trái (`x=120, y=90`)
       kèm tiếng hiệu ứng SFX (`assets/sfx/sfx_*.wav`), có thời gian nghỉ (cooldown) 45-60 giây giữa 2 lần bật icon.
    """
    proj_dir = Path(proj_dir)
    assets_dir = Path(assets_dir)
    assets_dir.mkdir(parents=True, exist_ok=True)

    icon_assets = ensure_green_icons_and_sfx_assets(root_dir=root_dir)
    green_plates = ensure_project_script_green_images(proj_dir=proj_dir, proj_name=proj_dir.name)
    part_intervals = parse_timestamps_txt_to_parts(timestamps_path, total_duration)

    # 1. Lịch đổi Ảnh Nhân Vật Green theo từng Part 1..7
    character_cues: List[Dict[str, Any]] = []
    for idx, p_info in enumerate(part_intervals):
        plate_path = ""
        if green_plates:
            plate_path = str(green_plates[min(idx, len(green_plates) - 1)])
        else:
            for fallback_gs in (
                proj_dir / "renders" / "THUMBNAIL-NENXANH.png",
                proj_dir / "THUMBNAIL-NENXANH.png",
            ):
                if fallback_gs.exists():
                    plate_path = str(fallback_gs)
                    break

        character_cues.append({
            "part": p_info["part"],
            "start": p_info["start"],
            "end": p_info["end"],
            "hms": p_info["hms"],
            "label": p_info["label"],
            "image_path": plate_path,
            "layout": "80_20_right_18_22pct",
            "colorkey": "0x00FF00:0.28:0.08",
        })

    # 2. Quét `subtitles.srt` để lập lịch bật Icon Video Green + SFX với Cooldown 45-60s
    icon_cues: List[Dict[str, Any]] = []
    next_allowed_time = 6.0  # Không bật ngay ở 5 giây đầu tiên để ưu tiên câu mở màn
    last_category = ""

    if srt_path and Path(srt_path).exists():
        raw_srt = Path(srt_path).read_text(encoding="utf-8", errors="ignore")
        blocks = [b.strip() for b in re.split(r"\n\s*\n", raw_srt.strip()) if b.strip()]

        for b_idx, blk in enumerate(blocks):
            lines = [ln.strip() for ln in blk.splitlines() if ln.strip()]
            if len(lines) < 2:
                continue
            ts_line = lines[1] if "-->" in lines[1] else (lines[0] if "-->" in lines[0] else "")
            if "-->" not in ts_line:
                continue
            ts_parts = ts_line.split("-->")
            s_sec = _parse_srt_time_to_sec(ts_parts[0])
            e_sec = _parse_srt_time_to_sec(ts_parts[1])
            if s_sec < next_allowed_time or (s_sec + icon_duration_sec) > (total_duration - 2.0):
                continue

            text_joined = " ".join(lines[2:] if "-->" in lines[1] else lines[1:]).lower()
            matched_cat = None
            matched_kw = ""

            # Ưu tiên danh mục khác với danh mục vừa bật liền trước để hình ảnh đa dạng
            cat_order = list(icon_assets.keys())
            if last_category in cat_order:
                cat_order.remove(last_category)
                cat_order.append(last_category)

            for cat in cat_order:
                cat_meta = icon_assets[cat]
                for kw in cat_meta["keywords"]:
                    kw_low = kw.lower()
                    if len(kw_low) <= 4:
                        if re.search(rf"\b{re.escape(kw_low)}\b", text_joined):
                            matched_cat = cat
                            matched_kw = kw
                            break
                    elif kw_low in text_joined:
                        matched_cat = cat
                        matched_kw = kw
                        break
                if matched_cat:
                    break

            if matched_cat:
                cat_meta = icon_assets[matched_cat]
                cue_start = round(s_sec, 3)
                cue_end = round(s_sec + icon_duration_sec, 3)
                # Cooldown xác định trong khoảng [45.0s .. 60.0s]
                cooldown_step = cooldown_min_sec + ((len(icon_cues) * 7) % int(max(1.0, cooldown_max_sec - cooldown_min_sec + 1)))
                next_allowed_time = cue_start + cooldown_step
                last_category = matched_cat

                icon_cues.append({
                    "cue_index": len(icon_cues) + 1,
                    "category": matched_cat,
                    "label": cat_meta["label"],
                    "matched_keyword": matched_kw,
                    "subtitle_excerpt": text_joined[:80],
                    "start": cue_start,
                    "end": cue_end,
                    "duration": icon_duration_sec,
                    "x": icon_x,
                    "y": icon_y,
                    "video_path": cat_meta["video_path"],
                    "sfx_path": cat_meta["sfx_path"],
                    "colorkey": "0x00FF00:0.28:0.08",
                    "cooldown_sec": cooldown_step,
                })

    payload = {
        "schema": "SKILL_04_VISUAL_CUES_V1",
        "project": proj_dir.name,
        "total_duration": round(total_duration, 3),
        "subtitle_style": {
            "Alignment": 4,
            "MarginL": 70,
            "MarginR": 430,
            "max_lines_per_block": 3,
        },
        "colorkey_filter": "colorkey=0x00FF00:0.28:0.08,despill=type=green",
        "icon_overlay_config": {
            "x": icon_x,
            "y": icon_y,
            "duration_sec": icon_duration_sec,
            "cooldown_range_sec": [cooldown_min_sec, cooldown_max_sec],
        },
        "character_cues": character_cues,
        "icon_cues": icon_cues,
    }

    cues_path = assets_dir / "visual_cues.json"
    cues_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        (proj_dir / "visual_cues.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass
    return payload


def build_sfx_timeline_wav(
    icon_cues: List[Dict[str, Any]],
    total_duration: float,
    output_wav_path: Path,
    offset_sec: float = 0.0,
    sfx_gain: float = 0.55,
) -> Optional[Path]:
    """
    Ghép toàn bộ âm thanh hiệu ứng SFX của các Icon Video Green vào đúng mốc thời gian `start - offset_sec`
    trên một đường tiếng WAV duy nhất (`icon_sfx_track.wav`, 24000Hz Mono PCM) trong < 0.25 giây.
    Giúp FFmpeg trộn SFX vào video chính xác 100% đến từng mili-giây mà không cần mở hàng chục luồng audio input.
    """
    if not icon_cues or total_duration <= offset_sec + 1.0:
        return None
    active_cues = [c for c in icon_cues if float(c.get("end", 0.0)) > offset_sec + 0.1 and c.get("sfx_path") and os.path.exists(c["sfx_path"])]
    if not active_cues:
        return None

    try:
        import numpy as np

        sr = 24000
        rem_dur = max(1.0, total_duration - offset_sec)
        total_samples = int(rem_dur * sr)
        track = np.zeros(total_samples, dtype=np.int16)

        sfx_cache: Dict[str, np.ndarray] = {}
        for cue in active_cues:
            sp = str(cue["sfx_path"])
            if sp not in sfx_cache:
                with wave.open(sp, "rb") as wf:
                    raw_frames = wf.readframes(wf.getnframes())
                    arr = np.frombuffer(raw_frames, dtype=np.int16).astype(np.float32)
                    if wf.getnchannels() > 1:
                        arr = arr.reshape(-1, wf.getnchannels()).mean(axis=1)
                    arr = np.clip(arr * sfx_gain, -32000, 32000).astype(np.int16)
                    sfx_cache[sp] = arr

            clip = sfx_cache.get(sp)
            if clip is None or len(clip) == 0:
                continue
            rel_start = max(0.0, float(cue["start"]) - offset_sec)
            start_idx = int(round(rel_start * sr))
            if start_idx >= total_samples:
                continue
            end_idx = min(total_samples, start_idx + len(clip))
            take = end_idx - start_idx
            if take > 0:
                mixed = track[start_idx:end_idx].astype(np.int32) + clip[:take].astype(np.int32)
                track[start_idx:end_idx] = np.clip(mixed, -32767, 32767).astype(np.int16)

        output_wav_path = Path(output_wav_path)
        output_wav_path.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(output_wav_path), "wb") as wf_out:
            wf_out.setnchannels(1)
            wf_out.setsampwidth(2)
            wf_out.setframerate(sr)
            wf_out.writeframes(track.tobytes())
        return output_wav_path
    except Exception as e:
        print(f"[VisualCueDirector] Lưu ý khi tạo đường tiếng SFX: {e}")
        return None
