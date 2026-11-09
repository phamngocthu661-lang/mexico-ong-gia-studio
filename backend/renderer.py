import sys

sys.modules["backend.visual_cue_director"] = sys.modules[__name__]
import json
import math
import os
import re
import shutil
import struct
import subprocess
import threading
import wave
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_BIN_DIR = Path(__file__).resolve().parent.parent / "bin"
if not _BIN_DIR.exists():
    _BIN_DIR = Path(__file__).resolve().parent.parent.parent / "bin"
if _BIN_DIR.exists():
    os.environ["PATH"] = str(_BIN_DIR) + os.pathsep + os.environ.get("PATH", "")
_FFMPEG_BIN = (
    str(_BIN_DIR / "ffmpeg.exe") if (_BIN_DIR / "ffmpeg.exe").exists() else "ffmpeg"
)
# Danh mục 8 bộ Icon Video Green (#00FF00) + Từ khóa kích hoạt đa ngôn ngữ (es-MX, VI, EN, JA)
GREEN_ICON_CATALOG: Dict[str, Dict[str, Any]] = {
    "gavel": {
        "video_name": "icon_green_gavel.mp4",
        "sfx_name": "sfx_gavel.wav",
        "label": "Búa tòa / Phán quyết pháp lý",
        "keywords": [
            "juez",
            "juzgado",
            "tribunal",
            "abogado",
            "abogada",
            "sentencia",
            "demanda",
            "audiencia",
            "notario",
            "notaría",
            "fiscal",
            "justicia",
            "ley",
            "juicio",
            "tòa án",
            "thẩm phán",
            "luật sư",
            "phán quyết",
            "kiện",
            "công lý",
            "court",
            "judge",
            "lawyer",
            "verdict",
            "lawsuit",
            "attorney",
            "裁判",
            "弁護士",
            "判事",
            "判決",
            "法廷",
        ],
    },
    "contract": {
        "video_name": "icon_green_contract.mp4",
        "sfx_name": "sfx_contract.wav",
        "label": "Hợp đồng / Sổ đỏ / Văn bản",
        "keywords": [
            "contrato",
            "escritura",
            "escrituras",
            "documento",
            "documentos",
            "firma",
            "firmar",
            "firmó",
            "papeles",
            "cláusula",
            "propiedad",
            "acta",
            " carpeta",
            "registro",
            "certificado",
            "título",
            "notarial",
            "hợp đồng",
            "sổ đỏ",
            "giấy tờ",
            "ký tên",
            "văn bản",
            "biên bản",
            "contract",
            "deed",
            "document",
            "signature",
            "signed",
            "papers",
            "契約書",
            "書類",
            "署名",
            "印鑑",
            "登記",
        ],
    },
    "will": {
        "video_name": "icon_green_will.mp4",
        "sfx_name": "sfx_will.wav",
        "label": "Di chúc / Thừa kế",
        "keywords": [
            "testamento",
            "herencia",
            "heredero",
            "herederos",
            "desheredar",
            "sucesión",
            "patrimonio",
            "legado",
            "bienes",
            "fortuna familiar",
            "última voluntad",
            "di chúc",
            "thừa kế",
            "tài sản",
            "chia gia tài",
            "will",
            "inheritance",
            "heir",
            "estate",
            "legacy",
            "遺言",
            "遺産",
            "相続",
            "財産",
        ],
    },
    "money": {
        "video_name": "icon_green_money.mp4",
        "sfx_name": "sfx_money.wav",
        "label": "Tiền bạc / Ngân hàng / Tài khoản",
        "keywords": [
            "dinero",
            "pesos",
            "millones",
            "millón",
            "banco",
            "bancaria",
            "cuenta",
            "fortuna",
            "pagar",
            "deuda",
            "cheque",
            "transferencia",
            "pensión",
            "ahorros",
            "efectivo",
            "dólares",
            "caja fuerte",
            "bóveda",
            "riqueza",
            "cobrar",
            "tiền",
            "triệu",
            "ngân hàng",
            "tài khoản",
            "nợ",
            "lương hưu",
            "séc",
            "money",
            "millions",
            "bank",
            "account",
            "debt",
            "check",
            "pension",
            "cash",
            "お金",
            "万円",
            "銀行",
            "口座",
            "年金",
            "借金",
            "貯金",
        ],
    },
    "heartbreak": {
        "video_name": "icon_green_heartbreak.mp4",
        "sfx_name": "sfx_heartbreak.wav",
        "label": "Tim vỡ / Phản bội / Nước mắt",
        "keywords": [
            "traición",
            "traicionar",
            "llorar",
            "lágrimas",
            "dolor",
            "corazón",
            "ingrato",
            "ingratos",
            "humillación",
            "desprecio",
            "abandono",
            "vergüenza",
            "herida",
            "pecho",
            "sollozo",
            "sufrimiento",
            "tristeza",
            "desagradecido",
            "estorbo",
            "phản bội",
            "nước mắt",
            "khóc",
            "đau đớn",
            "trái tim",
            "bất hiếu",
            "sỉ nhục",
            "betrayal",
            "tears",
            "crying",
            "heartbroken",
            "humiliation",
            "ungrateful",
            "裏切り",
            "涙",
            "泣く",
            "胸が痛",
            "絶望",
            "親不孝",
        ],
    },
    "warning": {
        "video_name": "icon_green_warning.mp4",
        "sfx_name": "sfx_warning.wav",
        "label": "Cảnh báo / Đuổi khỏi nhà / Nguy hiểm",
        "keywords": [
            "policía",
            "patrulla",
            "peligro",
            "amenaza",
            "calle",
            "maleta",
            "echaron",
            "correr",
            "alarma",
            "urgente",
            "golpe",
            "grito",
            "gritar",
            "fuera de aquí",
            "asilo",
            "anciano",
            "basura",
            "arresto",
            "guardia",
            "seguridad",
            "cảnh sát",
            "đuổi",
            "va li",
            "nguy hiểm",
            "đe dọa",
            "viện dưỡng lão",
            "police",
            "danger",
            "threat",
            "suitcase",
            "kicked out",
            "nursing home",
            "警察",
            "危険",
            "追い出",
            "スーツケース",
            "老人ホーム",
        ],
    },
    "house": {
        "video_name": "icon_green_house.mp4",
        "sfx_name": "sfx_house.wav",
        "label": "Ngôi nhà / Điền trang / Chìa khóa",
        "keywords": [
            "casa",
            "hogar",
            "llave",
            "llaves",
            "cerradura",
            "mansión",
            "terreno",
            "rancho",
            "hacienda",
            "techo",
            "puerta",
            "portón",
            "finca",
            "desalojo",
            "ngôi nhà",
            "chìa khóa",
            "ổ khóa",
            "biệt thự",
            "mảnh đất",
            "cổng",
            "house",
            "home",
            "keys",
            "lock",
            "mansion",
            "ranch",
            "eviction",
            "自宅",
            "鍵",
            "屋敷",
            "実家",
            "玄関",
        ],
    },
    "phone": {
        "video_name": "icon_green_phone.mp4",
        "sfx_name": "sfx_phone.wav",
        "label": "Điện thoại / Ghi âm / Bằng chứng",
        "keywords": [
            "teléfono",
            "llamada",
            "celular",
            "mensaje",
            "grabación",
            "audio",
            "cámara",
            "video",
            "evidencia",
            "prueba",
            "pruebas",
            "pantalla",
            "altavoz",
            "secreto",
            "điện thoại",
            "cuộc gọi",
            "tin nhắn",
            "ghi âm",
            "camera",
            "bằng chứng",
            "phone",
            "call",
            "recording",
            "camera",
            "evidence",
            "speakerphone",
            "電話",
            "録音",
            "カメラ",
            "証拠",
            "スマホ",
        ],
    },
}
ICON_DEFINITIONS: List[Dict[str, Any]] = [
    {"id": _k, **_v} for _k, _v in GREEN_ICON_CATALOG.items()
]
_GREEN_ICONS_LOCK = threading.Lock()
_DEEPLAB_CACHE: Dict[str, Any] = {"model": None, "preprocess": None, "device": "cpu"}


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
                    val += env * (
                        0.45 * math.sin(2 * math.pi * freq * dt)
                        + 0.20 * math.sin(2 * math.pi * (freq * 2.0) * dt)
                    )
        elif category == "money":
            # Tiếng đồng xu / chuông ngân cao (Coin / Cash Register Bell E6 -> B6)
            for st_t, freq in ((0.0, 1318.5), (0.09, 1975.5)):
                if t >= st_t:
                    dt = t - st_t
                    env = math.exp(-dt * 8.0) * min(1.0, dt * 120.0)
                    val += env * (
                        0.48 * math.sin(2 * math.pi * freq * dt)
                        + 0.22 * math.sin(2 * math.pi * (freq * 2.5) * dt)
                    )
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
                    val += env * (
                        0.42 * math.sin(2 * math.pi * 660.0 * dt)
                        + 0.25 * math.sin(2 * math.pi * 880.0 * dt)
                    )
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
        draw.rounded_rectangle(
            [cx - 52, cy - 48, cx + 18, cy - 16],
            radius=8,
            fill=(245, 196, 65),
            outline=(255, 235, 150),
            width=3,
        )
        draw.line(
            [(cx - 17, cy - 16), (cx + 42, cy + 42)], fill=(215, 155, 55), width=12
        )
        draw.rounded_rectangle(
            [cx - 56, cy + 36, cx + 16, cy + 54],
            radius=5,
            fill=(165, 65, 45),
            outline=(245, 196, 65),
            width=2,
        )
    elif category in ("contract", "will"):
        # Cuộn giấy / Văn bản pháp lý + dấu mộc đỏ
        doc_fill = (250, 244, 228) if category == "contract" else (248, 236, 200)
        draw.rounded_rectangle(
            [cx - 42, cy - 54, cx + 42, cy + 54],
            radius=8,
            fill=doc_fill,
            outline=(215, 165, 50),
            width=4,
        )
        for ly in range(cy - 34, cy + 22, 16):
            draw.line([(cx - 26, ly), (cx + 26, ly)], fill=(55, 60, 75), width=4)
        # Con dấu đỏ
        draw.ellipse(
            [cx + 4, cy + 12, cx + 32, cy + 40],
            fill=(210, 35, 35),
            outline=(255, 215, 100),
            width=2,
        )
    elif category == "money":
        # Thỏi vàng & đồng tiền vàng
        draw.rounded_rectangle(
            [cx - 50, cy - 28, cx + 50, cy + 30],
            radius=10,
            fill=(240, 185, 40),
            outline=(255, 235, 140),
            width=4,
        )
        draw.ellipse(
            [cx - 22, cy - 22, cx + 22, cy + 22],
            fill=(255, 215, 70),
            outline=(175, 120, 20),
            width=3,
        )
        draw.line([(cx, cy - 16), (cx, cy + 16)], fill=(140, 90, 10), width=5)
        draw.arc(
            [cx - 12, cy - 12, cx + 12, cy + 2],
            start=120,
            end=40,
            fill=(140, 90, 10),
            width=4,
        )
        draw.arc(
            [cx - 12, cy - 2, cx + 12, cy + 12],
            start=300,
            end=220,
            fill=(140, 90, 10),
            width=4,
        )
    elif category == "heartbreak":
        # Trái tim đỏ thẫm có vết nứt giữa
        draw.pieslice(
            [cx - 48, cy - 42, cx + 2, cy + 8], start=180, end=360, fill=(220, 38, 55)
        )
        draw.pieslice(
            [cx - 2, cy - 42, cx + 48, cy + 8], start=180, end=360, fill=(220, 38, 55)
        )
        draw.polygon(
            [(cx - 48, cy - 16), (cx + 48, cy - 16), (cx, cy + 52)], fill=(220, 38, 55)
        )
        # Đường nứt
        crack = [
            (cx + 2, cy - 34),
            (cx - 10, cy - 12),
            (cx + 8, cy + 6),
            (cx - 6, cy + 26),
            (cx + 2, cy + 50),
        ]
        draw.line(crack, fill=(24, 28, 38), width=6)
    elif category == "warning":
        # Tam giác cảnh báo vàng-đỏ + dấu chấm than
        draw.polygon(
            [(cx, cy - 54), (cx - 54, cy + 44), (cx + 54, cy + 44)],
            fill=(235, 55, 40),
            outline=(255, 215, 75),
            width=5,
        )
        draw.line([(cx, cy - 24), (cx, cy + 14)], fill=(255, 255, 255), width=9)
        draw.ellipse([cx - 6, cy + 24, cx + 6, cy + 36], fill=(255, 255, 255))
    elif category == "house":
        # Ngôi nhà / Điền trang ấm áp
        draw.polygon(
            [(cx, cy - 52), (cx - 54, cy - 4), (cx + 54, cy - 4)],
            fill=(205, 65, 45),
            outline=(255, 215, 95),
            width=3,
        )
        draw.rectangle(
            [cx - 38, cy - 4, cx + 38, cy + 48],
            fill=(245, 232, 205),
            outline=(185, 140, 55),
            width=3,
        )
        draw.rectangle([cx - 12, cy + 14, cx + 12, cy + 48], fill=(135, 75, 40))
    else:
        # Điện thoại / Bằng chứng ghi âm
        draw.rounded_rectangle(
            [cx - 28, cy - 52, cx + 28, cy + 52],
            radius=10,
            fill=(50, 60, 85),
            outline=(245, 196, 65),
            width=4,
        )
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
    tmp_dir = mp4_path.parent / f"_tmp_{category}_{os.getpid()}_{threading.get_ident()}"
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
            _FFMPEG_BIN,
            "-y",
            "-v",
            "error",
            "-framerate",
            str(fps),
            "-i",
            str(tmp_dir / "f_%03d.png"),
            "-c:v",
            "libx264",
            "-crf",
            "16",
            "-preset",
            "fast",
            "-pix_fmt",
            "yuv420p",
            "-t",
            f"{dur_sec:.2f}",
            str(mp4_path),
        ]
        subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
            creationflags=win_flags,
        )
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def ensure_green_icons_and_sfx_assets(
    root_dir: Optional[Path] = None,
) -> Dict[str, Dict[str, str]]:
    """
    Đảm bảo thư mục `assets/green_icons/icon_green_*.mp4` và `assets/sfx/sfx_*.wav` luôn sẵn sàng
    trên ổ cứng (tự động khởi tạo nếu chưa có).
    """
    if root_dir is None:
        root_dir = Path(__file__).resolve().parent.parent
        if root_dir.name.lower() == "app":
            root_dir = root_dir.parent
    root_dir = Path(root_dir)

    with _GREEN_ICONS_LOCK:
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
                    if v_path.exists() and (
                        not app_ic.exists()
                        or app_ic.stat().st_size != v_path.stat().st_size
                    ):
                        shutil.copy2(v_path, app_ic)
                    if a_path.exists() and (
                        not app_sf.exists()
                        or app_sf.stat().st_size != a_path.stat().st_size
                    ):
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


GREEN_PLATE_ENGINE_STAMP = "v1026_combined_deeplab_clean"


def _ensure_safe_torch_library_for_torchvision():
    try:
        import torch.library as _tl

        if not getattr(_tl, "_patched_safe_register_fake", False):
            _orig_rf = getattr(_tl, "register_fake", None)
            if callable(_orig_rf):

                def _safe_register_fake(op, *a, **kw):
                    try:
                        _dec = _orig_rf(op, *a, **kw)
                    except Exception:
                        return lambda fn: fn

                    def _wrap(fn):
                        try:
                            return _dec(fn)
                        except Exception:
                            return fn

                    return _wrap

                _tl.register_fake = _safe_register_fake
            _orig_lib_cls = getattr(_tl, "Library", None)
            if _orig_lib_cls is not None and hasattr(_orig_lib_cls, "impl"):
                _orig_impl = _orig_lib_cls.impl

                def _safe_lib_impl(self, op_name, fn=None, *a, **kw):
                    try:
                        return _orig_impl(self, op_name, fn, *a, **kw)
                    except Exception:
                        return fn if fn is not None else (lambda f: f)

                _orig_lib_cls.impl = _safe_lib_impl
            setattr(_tl, "_patched_safe_register_fake", True)
    except Exception:
        pass


def _get_person_segmentation_model():
    if _DEEPLAB_CACHE["model"] is None:
        import importlib
        import importlib.metadata
        import importlib.util as _ilu
        import subprocess
        import sys

        import torch

        _ensure_safe_torch_library_for_torchvision()

        _orig_fs = getattr(_ilu, "_orig_find_spec_for_omnivoice", None)
        if _orig_fs is not None:
            _ilu.find_spec = _orig_fs

        try:
            from torchvision.models.segmentation import (
                DeepLabV3_ResNet50_Weights,
                deeplabv3_resnet50,
            )
        except Exception:
            for _tv_k in [
                k
                for k in list(sys.modules.keys())
                if k == "torchvision" or k.startswith("torchvision.")
            ]:
                sys.modules.pop(_tv_k, None)

            _ensure_safe_torch_library_for_torchvision()
            try:
                from torchvision.models.segmentation import (
                    DeepLabV3_ResNet50_Weights,
                    deeplabv3_resnet50,
                )
            except Exception:
                real_torch_ver = str(getattr(torch, "_orig_real_version", "") or "")
                if not real_torch_ver:
                    _orig_ver_fn = getattr(
                        importlib.metadata,
                        "_orig_version_for_omnivoice",
                        importlib.metadata.version,
                    )
                    try:
                        real_torch_ver = str(_orig_ver_fn("torch"))
                    except Exception:
                        real_torch_ver = str(torch.__version__)

                tv_map = {
                    "2.6.": "torchvision==0.21.0",
                    "2.5.": "torchvision==0.20.1",
                    "2.4.": "torchvision==0.19.1",
                    "2.3.": "torchvision==0.18.1",
                }
                tv_ver = next(
                    (v for k, v in tv_map.items() if real_torch_ver.startswith(k)),
                    "torchvision==0.20.1",
                )
                cmd = [
                    sys.executable,
                    "-m",
                    "pip",
                    "install",
                    "--prefer-binary",
                    "--no-deps",
                    tv_ver,
                ]
                if "+cu" in real_torch_ver:
                    cu_tag = real_torch_ver.split("+")[-1].strip()
                    cmd += ["--index-url", f"https://download.pytorch.org/whl/{cu_tag}"]
                elif real_torch_ver.startswith("2.5.") and torch.cuda.is_available():
                    cmd += ["--index-url", "https://download.pytorch.org/whl/cu121"]
                subprocess.run(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=180
                )
                importlib.invalidate_caches()
                _ensure_safe_torch_library_for_torchvision()
                from torchvision.models.segmentation import (
                    DeepLabV3_ResNet50_Weights,
                    deeplabv3_resnet50,
                )

        weights = DeepLabV3_ResNet50_Weights.DEFAULT
        device = "cuda" if torch.cuda.is_available() else "cpu"
        model = deeplabv3_resnet50(weights=weights).eval().to(device)
        _DEEPLAB_CACHE["model"] = model
        _DEEPLAB_CACHE["preprocess"] = weights.transforms()
        _DEEPLAB_CACHE["device"] = device
    return (
        _DEEPLAB_CACHE["model"],
        _DEEPLAB_CACHE["preprocess"],
        _DEEPLAB_CACHE["device"],
    )


def extract_clean_large_green_character_bytes(
    thumb_bytes: bytes,
    part_index: int = 1,
) -> bytes:
    """
    Tách & chuẩn hóa chân dung người cha Mexico sang ảnh nền xanh #00FF00 (1920x1080):
    - Hỗ trợ cả 2 nguồn đầu vào:
      (A) Ảnh nền xanh do ChatGPT vẽ riêng từ Thumbnail 1 (đầy đủ 2 vai, không chữ) -> chuẩn hóa nền #00FF00 tuyệt đối & khử sạch viền.
      (B) Ảnh Thumbnail 80/20 có chữ hoặc ảnh nền xanh cũ -> dùng AI DeepLabV3_ResNet50 với ngưỡng tách riêng vùng đầu/tai/hốc cổ (0.56)
          và vùng thân áo (0.42), xóa bỏ hoàn toàn lỗi kẻ dọc từ tai xuống vai làm kẹt chậu cây/tường mờ ở cổ.
    """
    import io

    import numpy as np
    from PIL import Image, ImageEnhance
    from scipy import ndimage as ndi

    im = Image.open(io.BytesIO(thumb_bytes)).convert("RGB")
    if im.size != (1920, 1080):
        im = im.resize((1920, 1080), Image.Resampling.LANCZOS)
    w, h = im.size
    arr = np.asarray(im, dtype=np.uint8)

    # Phát hiện xem ảnh đầu vào đã là ảnh nền xanh (do ChatGPT vẽ lượt 2 hoặc ảnh nền xanh cũ cần làm sạch hốc cổ)
    left_test = arr[:, : int(w * 0.55), :]
    left_is_green = (left_test[:, :, 1].astype(int) > 160) & (
        (
            left_test[:, :, 1].astype(int)
            - np.maximum(left_test[:, :, 0], left_test[:, :, 2]).astype(int)
        )
        > 40
    )
    is_green_input = float(np.mean(left_is_green)) >= 0.72

    if is_green_input:
        is_green_px = (arr[:, :, 1].astype(int) > 155) & (
            (
                arr[:, :, 1].astype(int)
                - np.maximum(arr[:, :, 0], arr[:, :, 2]).astype(int)
            )
            > 38
        )
        fg_cols = np.where(np.mean(~is_green_px, axis=0) > 0.05)[0]
        fg_cols = fg_cols[fg_cols >= int(w * 0.42)]
        x_crop_start = int(fg_cols.min()) if len(fg_cols) > 0 else int(w * 0.62)
        x_crop_start = max(int(w * 0.45), min(int(w * 0.76), x_crop_start - 12))
    else:
        # 1. Phát hiện chính xác mép phải của băng rôn đỏ & khối chữ bên trái
        bottom_strip = arr[int(h * 0.75) :, : int(w * 0.84), :]
        is_red = (
            (bottom_strip[:, :, 0].astype(int) > 155)
            & (bottom_strip[:, :, 1].astype(int) < 75)
            & (bottom_strip[:, :, 2].astype(int) < 75)
            & (
                (bottom_strip[:, :, 0].astype(int) - bottom_strip[:, :, 1].astype(int))
                > 90
            )
        )
        red_cols = np.where(np.mean(is_red, axis=0) > 0.12)[0]
        x_text_end = int(red_cols.max()) + 6 if len(red_cols) > 0 else int(w * 0.72)

        x_crop_start = max(int(w * 0.68), x_text_end)
        while x_crop_start < int(w * 0.80):
            col = arr[:, x_crop_start, :]
            if (
                np.mean((col[:, 0] > 230) & (col[:, 1] > 230) & (col[:, 2] > 230))
                > 0.72
            ):
                x_crop_start += 1
            else:
                break

    crop_arr = arr[:, x_crop_start:, :].copy()
    ch_raw, cw_raw, _ = crop_arr.shape

    # Đánh dấu các pixel đã là nền xanh hoặc cột viền đen dọc ở mép phải ảnh chụp màn hình
    crop_green_bg = (crop_arr[:, :, 1].astype(int) > 155) & (
        (
            crop_arr[:, :, 1].astype(int)
            - np.maximum(crop_arr[:, :, 0], crop_arr[:, :, 2]).astype(int)
        )
        > 38
    )
    col_black_ratio = np.mean(
        (crop_arr[:, :, 0] < 14) & (crop_arr[:, :, 1] < 14) & (crop_arr[:, :, 2] < 14),
        axis=0,
    )
    black_border_cols = (col_black_ratio > 0.82) & (
        np.arange(cw_raw) >= int(cw_raw * 0.90)
    )
    crop_black_edge = np.broadcast_to(black_border_cols[None, :], (ch_raw, cw_raw))

    # 2. Chạy AI DeepLabV3_ResNet50 (class 15 = person) trên nửa phải ảnh (có cache theo ảnh gốc)
    thumb_md5 = hashlib.md5(
        thumb_bytes[:65536] + str(len(thumb_bytes)).encode()
    ).hexdigest()
    cached_probs = (
        _DEEPLAB_CACHE.get("last_probs_crop")
        if _DEEPLAB_CACHE.get("last_thumb_md5") == thumb_md5
        else None
    )
    probs_crop = cached_probs
    if probs_crop is None or probs_crop.shape != (ch_raw, cw_raw):
        try:
            import torch

            model, preprocess, device = _get_person_segmentation_model()
            x_wide = int(w * 0.44)
            wide_arr = arr[:, x_wide:, :].copy()
            wide_green = (wide_arr[:, :, 1].astype(int) > 155) & (
                (
                    wide_arr[:, :, 1].astype(int)
                    - np.maximum(wide_arr[:, :, 0], wide_arr[:, :, 2]).astype(int)
                )
                > 38
            )
            w_col_black = np.mean(
                (wide_arr[:, :, 0] < 14)
                & (wide_arr[:, :, 1] < 14)
                & (wide_arr[:, :, 2] < 14),
                axis=0,
            )
            w_black_cols = (w_col_black > 0.82) & (
                np.arange(wide_arr.shape[1]) >= int(wide_arr.shape[1] * 0.92)
            )
            wide_arr[wide_green | w_black_cols[None, :]] = (128, 128, 128)
            wide_im = Image.fromarray(wide_arr, mode="RGB")
            inp = preprocess(wide_im).unsqueeze(0).to(device)
            with torch.no_grad():
                out = model(inp)["out"][0]
            probs_wide = torch.softmax(out, dim=0)[15].detach().cpu().numpy()
            probs_wide_full = np.asarray(
                Image.fromarray(probs_wide.astype(np.float32), mode="F").resize(
                    wide_im.size, Image.Resampling.BICUBIC
                ),
                dtype=np.float32,
            )
            probs_crop = probs_wide_full[:, (x_crop_start - x_wide) :]
            _DEEPLAB_CACHE["last_thumb_md5"] = thumb_md5
            _DEEPLAB_CACHE["last_probs_crop"] = probs_crop
            _DEEPLAB_CACHE["last_used_deeplab"] = True
        except Exception as e:
            print(
                f"[VisualCueDirector] Lưu ý khi chạy DeepLabV3 tách nền nhân vật: {e}"
            )
            probs_crop = None
            _DEEPLAB_CACHE["last_used_deeplab"] = False
    else:
        _DEEPLAB_CACHE["last_used_deeplab"] = True

    if probs_crop is not None:
        # Ngưỡng 0.56 ở vùng đầu, tai và hốc cổ (y < 68%) để cắt sạch 100% chậu cây/tường mờ dưới 2 tai;
        # ngưỡng 0.42 ở vùng vai và thân áo (y >= 68%).
        yy_grid = np.arange(ch_raw)[:, None]
        thresh_map = np.where(yy_grid < int(ch_raw * 0.68), 0.56, 0.42)
        fg_bool = (probs_crop >= thresh_map) & (~crop_green_bg) & (~crop_black_edge)
    else:
        fg_bool = (~crop_green_bg) & (~crop_black_edge)

    # Xóa nền trắng/sáng kết nối với viền trên hoặc viền trái bằng SciPy ndimage.label
    is_white = (
        (crop_arr[:, :, 0] > 232)
        & (crop_arr[:, :, 1] > 232)
        & (crop_arr[:, :, 2] > 232)
        & (np.abs(crop_arr[:, :, 0].astype(int) - crop_arr[:, :, 1].astype(int)) < 14)
    )
    lbl_w, num_w = ndi.label(is_white, structure=np.ones((3, 3), dtype=np.int32))
    if num_w > 0:
        border_w = np.zeros_like(is_white, dtype=bool)
        border_w[:6, :] = True
        border_w[: int(ch_raw * 0.65), :6] = True
        w_ids = np.unique(lbl_w[border_w & is_white])
        w_ids = w_ids[w_ids > 0]
        if len(w_ids) > 0:
            fg_bool[np.isin(lbl_w, w_ids)] = False

    # Lấp các lỗ hổng nhỏ bên trong khuôn mặt/áo (TUYỆT ĐỐI KHÔNG kẻ dọc từ tai xuống vai!)
    fg_bool = ndi.binary_fill_holes(fg_bool)
    mask = (fg_bool.astype(np.uint8)) * 255

    # Xác định vùng cắt đáy nếu có cầm giấy tờ văn bản hoặc có bảng tên (như DON ERNESTO)
    y_cut_bottom = (
        int(round(ch_raw * 0.94)) if is_green_input else int(round(ch_raw * 0.86))
    )
    if probs_crop is not None:
        y_paper_scan = int(ch_raw * 0.52)
        lower_probs = probs_crop[y_paper_scan:, :]
        low_prob_rows = np.where(np.mean(lower_probs > 0.35, axis=1) < 0.45)[0]
        if len(low_prob_rows) > 18:
            y_cut_bottom = min(ch_raw, y_paper_scan + int(low_prob_rows[0]) - 54)
            y_cut_bottom = max(int(ch_raw * 0.44), y_cut_bottom)

    # Quét bổ sung bảng tên ngang nền sáng có chữ tối (như "DON ERNESTO") ở vùng đáy (y >= 72% chiều cao)
    y_badge_scan_start = int(ch_raw * 0.72)
    if y_badge_scan_start < y_cut_bottom:
        lower_rgb = crop_arr[y_badge_scan_start:y_cut_bottom, :, :].astype(np.int16)
        luma = (
            lower_rgb[:, :, 0] * 299
            + lower_rgb[:, :, 1] * 587
            + lower_rgb[:, :, 2] * 114
        ) // 1000
        bright_neutral = (
            (lower_rgb[:, :, 0] > 195)
            & (lower_rgb[:, :, 1] > 195)
            & (lower_rgb[:, :, 2] > 185)
            & (
                (
                    np.maximum(
                        np.maximum(lower_rgb[:, :, 0], lower_rgb[:, :, 1]),
                        lower_rgb[:, :, 2],
                    )
                    - np.minimum(
                        np.minimum(lower_rgb[:, :, 0], lower_rgb[:, :, 1]),
                        lower_rgb[:, :, 2],
                    )
                )
                < 35
            )
        )
        sharp_edges = np.abs(np.diff(luma, axis=1)) > 55
        badge_rows = np.where(
            (np.mean(bright_neutral, axis=1) > 0.40)
            & (np.sum(sharp_edges, axis=1) >= 6)
        )[0]
        if len(badge_rows) >= 8:
            y_cut_bottom = min(
                y_cut_bottom,
                max(int(ch_raw * 0.48), y_badge_scan_start + int(badge_rows[0]) - 14),
            )

    # Chỉ lấp đầy phần thân áo bên dưới đường vai thực sự (y >= 70% chiều cao, tức dưới cổ)
    y_true_torso = min(int(ch_raw * 0.70), max(0, y_cut_bottom - 40))
    if y_true_torso < y_cut_bottom:
        for x in range(cw_raw):
            if black_border_cols[x]:
                continue
            fg_ys_torso = np.where(mask[y_true_torso:y_cut_bottom, x] > 127)[0]
            if len(fg_ys_torso) > 0:
                y_st = y_true_torso + int(fg_ys_torso[0])
                mask[y_st:y_cut_bottom, x] = 255

    # Xóa lại nền trắng sát biên trái nếu có
    if num_w > 0:
        border_w2 = np.zeros_like(is_white, dtype=bool)
        border_w2[:6, :] = True
        border_w2[: int(ch_raw * 0.68), :6] = True
        w_ids2 = np.unique(lbl_w[border_w2 & is_white])
        w_ids2 = w_ids2[w_ids2 > 0]
        if len(w_ids2) > 0:
            mask[np.isin(lbl_w, w_ids2)] = 0

    crop_arr = crop_arr[:y_cut_bottom, :, :]
    mask = mask[:y_cut_bottom, :]

    # Giữ khối nhân vật chính lớn nhất bằng SciPy ndimage.label
    labels, num_labels = ndi.label(
        mask > 127, structure=np.ones((3, 3), dtype=np.int32)
    )
    if num_labels > 0:
        counts = np.bincount(labels.ravel())
        counts[0] = 0
        largest_lbl = int(np.argmax(counts))
        clean_mask = np.where(labels == largest_lbl, 255, 0).astype(np.uint8)
    else:
        clean_mask = mask

    # Làm mịn biên và co nhẹ 1px ở vùng đầu/tai/cổ để khử sạch viền hồng/nền mờ quanh tóc & dưới tai
    y_g, x_g = np.ogrid[-2:3, -2:3]
    disk2 = (x_g * x_g + y_g * y_g) <= 4
    m_bool = ndi.binary_closing(clean_mask > 127, structure=disk2)
    m_bool = ndi.binary_opening(m_bool, structure=disk2)
    m_eroded = ndi.binary_erosion(m_bool, structure=disk2, iterations=1)
    head_neck_limit = min(m_bool.shape[0], int(ch_raw * 0.68))
    m_bool[:head_neck_limit, :] = m_eroded[:head_neck_limit, :]

    clean_mask = ndi.gaussian_filter(
        m_bool.astype(np.float32) * 255.0, sigma=1.1
    ).astype(np.uint8)

    ys, xs = np.where(clean_mask >= 140)
    if len(xs) >= 40 and len(ys) >= 40:
        x1, x2 = int(xs.min()), int(xs.max())
        y1, y2 = int(ys.min()), int(ys.max())
        char_rgb = crop_arr[y1 : y2 + 1, x1 : x2 + 1]
        char_a = clean_mask[y1 : y2 + 1, x1 : x2 + 1]
    else:
        char_rgb = crop_arr
        char_a = clean_mask

    # Áp dụng biến thiên ánh sáng cảm xúc nhẹ theo Part 1..7
    part_grades = {
        1: (1.00, 1.00, 1.00),
        2: (0.96, 1.06, 0.92),
        3: (0.94, 1.10, 0.88),
        4: (1.02, 1.08, 0.96),
        5: (1.04, 1.05, 1.04),
        6: (1.03, 1.12, 1.02),
        7: (1.05, 1.02, 1.08),
    }
    br_f, ct_f, sat_f = part_grades.get(int(part_index), (1.0, 1.0, 1.0))
    if (br_f, ct_f, sat_f) != (1.0, 1.0, 1.0):
        pil_rgb = Image.fromarray(char_rgb, mode="RGB")
        pil_rgb = ImageEnhance.Brightness(pil_rgb).enhance(br_f)
        pil_rgb = ImageEnhance.Contrast(pil_rgb).enhance(ct_f)
        pil_rgb = ImageEnhance.Color(pil_rgb).enhance(sat_f)
        char_rgb = np.asarray(pil_rgb, dtype=np.uint8)

    # Khử viền xanh nếu có
    r_ch = char_rgb[:, :, 0].astype(np.int16)
    g_ch = char_rgb[:, :, 1].astype(np.int16)
    b_ch = char_rgb[:, :, 2].astype(np.int16)
    max_rb = np.maximum(r_ch, b_ch)
    char_rgb = char_rgb.copy()
    char_rgb[:, :, 1] = np.where(
        g_ch > max_rb, max_rb + ((g_ch - max_rb) // 5), g_ch
    ).astype(np.uint8)

    ch_c, cw_c = char_a.shape
    target_h = int(round(h * 0.96))
    target_w = int(round(w * 0.36))
    scale = max(
        target_w / max(1, cw_c), min(target_h / max(1, ch_c), (w * 0.42) / max(1, cw_c))
    )
    new_w = max(580, min(800, int(round(cw_c * scale))))
    new_h = max(
        720, min(int(round(h * 0.97)), int(round(ch_c * (new_w / max(1, cw_c)))))
    )
    if new_h > int(round(h * 0.97)):
        new_h = int(round(h * 0.97))
        new_w = max(560, min(800, int(round(cw_c * (new_h / max(1, ch_c))))))

    char_rgb_res = np.asarray(
        Image.fromarray(char_rgb, mode="RGB").resize(
            (new_w, new_h), Image.Resampling.LANCZOS
        ),
        dtype=np.uint8,
    )
    char_a_res = np.asarray(
        Image.fromarray(char_a, mode="L").resize(
            (new_w, new_h), Image.Resampling.BILINEAR
        ),
        dtype=np.uint8,
    )
    hard_mask = char_a_res >= 145

    canvas_arr = np.zeros((h, w, 3), dtype=np.uint8)
    canvas_arr[:, :, 1] = 255  # 100% nền xanh lá thuần khiết #00FF00 (RGB 0, 255, 0)

    paste_x = w - new_w
    paste_y = h - new_h
    roi = canvas_arr[paste_y : paste_y + new_h, paste_x : paste_x + new_w]
    for c_i in range(3):
        roi[:, :, c_i] = np.where(hard_mask, char_rgb_res[:, :, c_i], roi[:, :, c_i])
    canvas_arr[paste_y : paste_y + new_h, paste_x : paste_x + new_w] = roi

    out_buf = io.BytesIO()
    Image.fromarray(canvas_arr, mode="RGB").save(out_buf, format="PNG", optimize=True)
    return out_buf.getvalue()


def _write_green_plate_stamp(target_path: Path) -> None:
    if not _DEEPLAB_CACHE.get("last_used_deeplab", False):
        return
    try:
        target_path = Path(target_path)
        for st_dir in (
            target_path.parent,
            target_path.parent / "script_green_images",
            target_path.parent.parent / "script_green_images",
        ):
            if st_dir.exists() and st_dir.is_dir():
                (st_dir / "green_plate_version.txt").write_text(
                    GREEN_PLATE_ENGINE_STAMP, encoding="utf-8"
                )
    except Exception:
        pass


def normalize_character_to_strict_80_20_green_plate(
    source_image_path: Path,
    output_plate_path: Path,
    part_index: int = 1,
) -> Optional[Path]:
    """
    Chuẩn hóa ảnh Nhân vật Green Screen (1920x1080):
    - Loại bỏ 100% chữ tiêu đề, băng rôn đỏ, giấy tờ văn bản và bảng tên phía dưới.
    - Tách sạch phông nền sau đầu/vai nhân vật sang màu xanh lá thuần khiết #00FF00 (RGB 0,255,0).
    - Phóng to chân dung nhân vật rõ nét ở bên phải khung hình.
    """
    if not source_image_path or not Path(source_image_path).exists():
        return None
    try:
        raw_bytes = Path(source_image_path).read_bytes()
        green_bytes = extract_clean_large_green_character_bytes(
            raw_bytes, part_index=part_index
        )
        output_plate_path = Path(output_plate_path)
        output_plate_path.parent.mkdir(parents=True, exist_ok=True)
        output_plate_path.write_bytes(green_bytes)
        _write_green_plate_stamp(output_plate_path)
        return output_plate_path
    except Exception as e:
        print(f"[VisualCueDirector] Lưu ý khi chuẩn hóa ảnh Green: {e}")
        return None


def _is_green_plate_clean_and_large(plate_path: Path) -> bool:
    """Kiểm tra xem file THUMBNAIL-NENXANH.png / green_part_01.png đã được tách bằng AI DeepLabV3 chuẩn V1.0.25 và sạch chữ chưa."""
    if not plate_path or not plate_path.exists() or plate_path.stat().st_size < 5_000:
        return False
    try:
        plate_path = Path(plate_path)
        stamp_candidates = (
            plate_path.parent / "green_plate_version.txt",
            plate_path.parent / "script_green_images" / "green_plate_version.txt",
            plate_path.parent.parent
            / "script_green_images"
            / "green_plate_version.txt",
        )
        has_valid_stamp = any(
            sc.exists()
            and sc.read_text(encoding="utf-8", errors="ignore").strip()
            == GREEN_PLATE_ENGINE_STAMP
            for sc in stamp_candidates
        )
        if not has_valid_stamp:
            return False

        import numpy as np
        from PIL import Image

        im = Image.open(plate_path).convert("RGB")
        if im.size != (1920, 1080):
            return False
        arr = np.asarray(im, dtype=np.uint8)
        w, h = im.size
        # 1. Toàn bộ vùng x = 0..1100 bắt buộc phải là màu xanh #00FF00 thuần khiết (không dính chữ cắt dở)
        left_zone = arr[:, : int(w * 0.57), :]
        left_green_ratio = float(
            np.mean(
                (left_zone[:, :, 0] == 0)
                & (left_zone[:, :, 1] == 255)
                & (left_zone[:, :, 2] == 0)
            )
        )
        if left_green_ratio < 0.99:
            return False
        # 2. Vùng nhân vật bên phải (x = 1220..1920) phải đủ lớn (>= 42% diện tích vùng phải)
        right_zone = arr[:, int(w * 0.64) :, :]
        non_green = ~(
            (right_zone[:, :, 0] == 0)
            & (right_zone[:, :, 1] == 255)
            & (right_zone[:, :, 2] == 0)
        )
        if float(np.mean(non_green)) < 0.42:
            return False
        # 3. Kiểm tra vùng đáy bên phải (y >= 80%) không bị dính bảng tên trắng chữ đen (như DON ERNESTO)
        bot_right = arr[int(h * 0.80) :, int(w * 0.68) :, :].astype(np.int16)
        luma_br = (
            bot_right[:, :, 0] * 299
            + bot_right[:, :, 1] * 587
            + bot_right[:, :, 2] * 114
        ) // 1000
        bright_br = (
            (bot_right[:, :, 0] > 195)
            & (bot_right[:, :, 1] > 195)
            & (bot_right[:, :, 2] > 185)
            & (
                (
                    np.maximum(
                        np.maximum(bot_right[:, :, 0], bot_right[:, :, 1]),
                        bot_right[:, :, 2],
                    )
                    - np.minimum(
                        np.minimum(bot_right[:, :, 0], bot_right[:, :, 1]),
                        bot_right[:, :, 2],
                    )
                )
                < 35
            )
        )
        edges_br = np.abs(np.diff(luma_br, axis=1)) > 55
        bad_badge_rows = np.where(
            (np.mean(bright_br, axis=1) > 0.42) & (np.sum(edges_br, axis=1) >= 6)
        )[0]
        if len(bad_badge_rows) >= 8:
            return False
        return True
    except Exception:
        return False


def ensure_project_script_green_images(
    proj_dir: Path,
    renders_dir: Optional[Path] = None,
    proj_name: str = "",
    force_regenerate: bool = False,
) -> List[Path]:
    """
    Đảm bảo dự án có đủ:
    - `THUMBNAIL-NENXANH.png` (không có chữ, nhân vật kích thước lớn sắc nét trên nền #00FF00)
    - Bộ 7 ảnh `script_green_images/green_part_01.png` .. `green_part_07.png` theo 7 Phần của kịch bản.
    """
    proj_dir = Path(proj_dir)
    if renders_dir is None:
        renders_dir = proj_dir / "renders"
    if not proj_name:
        proj_name = proj_dir.name

    green_dir = proj_dir / "script_green_images"
    green_dir.mkdir(parents=True, exist_ok=True)

    # LUÔN ưu tiên ảnh gốc THUMBNAIL.png để tách nhân vật sạch 100% chữ & phóng to chuẩn
    src_candidates = [
        proj_dir / "THUMBNAIL.png",
        renders_dir / "THUMBNAIL.png",
        renders_dir / f"{proj_name}_THUMBNAIL_1.png",
        proj_dir / f"{proj_name}_THUMBNAIL_1.png",
        renders_dir / "THUMBNAIL-NENXANH.png",
        proj_dir / "THUMBNAIL-NENXANH.png",
        renders_dir / f"{proj_name}_THUMBNAIL_NENXANH.png",
        proj_dir / f"{proj_name}_THUMBNAIL_NENXANH.png",
    ]
    base_src = next(
        (p for p in src_candidates if p.exists() and p.stat().st_size > 5_000), None
    )

    need_rebuild = force_regenerate or not _is_green_plate_clean_and_large(
        proj_dir / "THUMBNAIL-NENXANH.png"
    )

    part_paths: List[Path] = []
    for p_idx in range(1, 8):
        part_file = green_dir / f"green_part_{p_idx:02d}.png"
        if need_rebuild or not _is_green_plate_clean_and_large(part_file):
            if base_src is not None:
                normalize_character_to_strict_80_20_green_plate(
                    base_src, part_file, part_index=p_idx
                )
        if part_file.exists() and part_file.stat().st_size >= 5_000:
            part_paths.append(part_file)

    # Đồng bộ ngược lại THUMBNAIL-NENXANH.png ở cả proj_dir và renders_dir
    if part_paths:
        for gs_target in (
            proj_dir / "THUMBNAIL-NENXANH.png",
            renders_dir / "THUMBNAIL-NENXANH.png",
            renders_dir / f"{proj_name}_THUMBNAIL_NENXANH.png",
            proj_dir / f"{proj_name}_THUMBNAIL_NENXANH.png",
        ):
            if need_rebuild or not _is_green_plate_clean_and_large(gs_target):
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
        pa, pb, pc = (
            proj_dir / "part_a.txt",
            proj_dir / "part_b.txt",
            proj_dir / "part_c.txt",
        )
        if pa.exists() and pb.exists() and pc.exists():
            try:
                raw_full = "\n\n".join(
                    [
                        pa.read_text(encoding="utf-8", errors="ignore"),
                        pb.read_text(encoding="utf-8", errors="ignore"),
                        pc.read_text(encoding="utf-8", errors="ignore"),
                    ]
                )
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
            best_item = min(
                timeline, key=lambda it: abs(float(it.get("start", 0.0)) - target_sec)
            )
            if p_idx == 0:
                start_sec = 0.0
                best_item = timeline[0]
            else:
                start_sec = float(best_item.get("start", target_sec))
            raw_sent = str(best_item.get("text") or "").strip().replace("\n", " ")
            if raw_sent:
                short_s = raw_sent[:42].rstrip(" ,.;:") + (
                    "..." if len(raw_sent) > 42 else ""
                )
                snippet = f"Parte {p_idx + 1}: {short_s}"

        part_entries.append(
            {
                "part": p_idx + 1,
                "start": round(start_sec, 3),
                "end": round(total_duration, 3),
                "hms": _format_hms(start_sec),
                "label": snippet,
            }
        )

    # Đảm bảo thứ tự thời gian tăng dần nghiêm ngặt và gán `end` của mỗi Part = `start` của Part kế tiếp
    for i in range(1, len(part_entries)):
        if part_entries[i]["start"] <= part_entries[i - 1]["start"] + 5.0:
            part_entries[i]["start"] = round(
                min(
                    total_duration - 1.0,
                    part_entries[i - 1]["start"] + max(10.0, total_duration / 7.0),
                ),
                3,
            )
            part_entries[i]["hms"] = _format_hms(part_entries[i]["start"])
        part_entries[i - 1]["end"] = part_entries[i]["start"]
    if part_entries:
        part_entries[-1]["end"] = round(
            max(part_entries[-1]["start"] + 1.0, total_duration), 3
        )

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


def parse_timestamps_txt_to_parts(
    timestamps_path: Path, total_duration: float
) -> List[Dict[str, Any]]:
    """Đọc `TIMESTAMPS.txt` và trả về 7 khoảng thời gian `[start, end]` cho Part 1..7."""
    entries: List[Dict[str, Any]] = []
    if timestamps_path and Path(timestamps_path).exists():
        try:
            lines = [
                ln.strip()
                for ln in Path(timestamps_path)
                .read_text(encoding="utf-8", errors="ignore")
                .splitlines()
                if ln.strip()
            ]
            for ln in lines:
                m = re.match(r"^(\d{1,2}:\d{2}(?::\d{2})?)\s*[-–—:]\s*(.+)$", ln)
                if m:
                    t_raw = m.group(1)
                    if t_raw.count(":") == 1:
                        t_raw = "00:" + t_raw
                    sec = _parse_srt_time_to_sec(t_raw)
                    entries.append(
                        {
                            "part": len(entries) + 1,
                            "start": round(sec, 3),
                            "end": round(total_duration, 3),
                            "hms": _format_hms(sec),
                            "label": m.group(2).strip(),
                        }
                    )
        except Exception:
            entries = []

    if len(entries) < 2:
        entries = []
        for idx in range(7):
            st = round((total_duration * idx) / 7.0, 3)
            ed = round((total_duration * (idx + 1)) / 7.0, 3)
            entries.append(
                {
                    "part": idx + 1,
                    "start": st,
                    "end": ed,
                    "hms": _format_hms(st),
                    "label": f"Parte {idx + 1}",
                }
            )
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
    green_plates = ensure_project_script_green_images(
        proj_dir=proj_dir, proj_name=proj_dir.name
    )
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

        character_cues.append(
            {
                "part": p_info["part"],
                "start": p_info["start"],
                "end": p_info["end"],
                "hms": p_info["hms"],
                "label": p_info["label"],
                "image_path": plate_path,
                "layout": "80_20_right_18_22pct",
                "colorkey": "0x00FF00:0.28:0.08",
            }
        )

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
            ts_line = (
                lines[1]
                if "-->" in lines[1]
                else (lines[0] if "-->" in lines[0] else "")
            )
            if "-->" not in ts_line:
                continue
            ts_parts = ts_line.split("-->")
            s_sec = _parse_srt_time_to_sec(ts_parts[0])
            if s_sec < next_allowed_time or (s_sec + icon_duration_sec) > (
                total_duration - 2.0
            ):
                continue

            text_joined = " ".join(
                lines[2:] if "-->" in lines[1] else lines[1:]
            ).lower()
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
                cooldown_step = cooldown_min_sec + (
                    (len(icon_cues) * 7)
                    % int(max(1.0, cooldown_max_sec - cooldown_min_sec + 1))
                )
                next_allowed_time = cue_start + cooldown_step
                last_category = matched_cat

                icon_cues.append(
                    {
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
                    }
                )

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
    cues_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    try:
        (proj_dir / "visual_cues.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
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
    active_cues = [
        c
        for c in icon_cues
        if float(c.get("end", 0.0)) > offset_sec + 0.1
        and c.get("sfx_path")
        and os.path.exists(c["sfx_path"])
    ]
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
                mixed = track[start_idx:end_idx].astype(np.int32) + clip[:take].astype(
                    np.int32
                )
                track[start_idx:end_idx] = np.clip(mixed, -32767, 32767).astype(
                    np.int16
                )

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


# ==============================================================================
# MODEL PHẦN 2: ENGINE DỰNG VIDEO FFMPEG NVENC & KEN BURNS (RENDERER)
# ==============================================================================

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

import hashlib
import os
import sys
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from backend.voice_service import generate_karaoke_ass_from_srt

_BIN_DIR = Path(__file__).resolve().parent.parent / "bin"
if not _BIN_DIR.exists():
    _BIN_DIR = Path(__file__).resolve().parent.parent.parent / "bin"
if _BIN_DIR.exists():
    os.environ["PATH"] = str(_BIN_DIR) + os.pathsep + os.environ.get("PATH", "")

_FFMPEG_BIN = (
    str(_BIN_DIR / "ffmpeg.exe") if (_BIN_DIR / "ffmpeg.exe").exists() else "ffmpeg"
)
_FFPROBE_BIN = (
    str(_BIN_DIR / "ffprobe.exe") if (_BIN_DIR / "ffprobe.exe").exists() else "ffprobe"
)

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
                    _FFMPEG_BIN,
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-f",
                    "lavfi",
                    "-i",
                    "color=c=black:s=256x256:d=0.2:r=30",
                    "-pix_fmt",
                    "yuv420p",
                    "-c:v",
                    "h264_nvenc",
                    "-f",
                    "null",
                    "-",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=10,
                creationflags=0x08000000 if os.name == "nt" else 0,
            )
            _NVENC_AVAILABLE = res.returncode == 0
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
        _FFPROBE_BIN,
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(file_path),
    ]
    try:
        res = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True
        )
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
        default_layers.append(
            {
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
            }
        )
    if (kho_green / "SONG6.mp4").exists():
        default_layers.append(
            {
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
            }
        )
    if (kho_green / "SUB.mp4").exists():
        default_layers.append(
            {
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
            }
        )

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
    fs_raw = (
        sub_cfg.get("fontSize")
        if sub_cfg.get("fontSize") is not None
        else sub_cfg.get("font_size", 68)
    )
    fs = max(20, min(120, int(round(float(fs_raw or 68)))))
    mw_raw = (
        sub_cfg.get("maxWordsPerLine")
        if sub_cfg.get("maxWordsPerLine") is not None
        else sub_cfg.get("max_words_per_line", 5)
    )
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
                for section in (
                    "canvas",
                    "stock_background",
                    "script_green_character",
                    "karaoke_subtitle",
                ):
                    if isinstance(saved.get(section), dict):
                        default_cfg[section].update(saved[section])
                if isinstance(saved.get("stock_darken"), dict):
                    default_cfg["stock_background"].update(saved["stock_darken"])
                if isinstance(saved.get("script_character_green"), dict):
                    default_cfg["script_green_character"].update(
                        saved["script_character_green"]
                    )
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
    char_cfg["opacity"] = round(
        max(0.1, min(1.0, float(char_cfg.get("opacity", 0.90)))), 2
    )
    char_cfg["zIndex"] = 500
    _normalize_karaoke_subtitle_cfg(default_cfg["karaoke_subtitle"])
    # Đồng bộ cả 2 tên khóa để tương thích 100% giữa Frontend Preview và FFmpeg Renderer
    default_cfg["green_video_layers"] = default_cfg["green_layers"]
    default_cfg["script_character_green"] = default_cfg["script_green_character"]
    default_cfg["subtitle_karaoke"] = default_cfg["karaoke_subtitle"]
    default_cfg["stock_darken"] = default_cfg["stock_background"]
    return default_cfg


def save_video_layout_config(
    config_data: Dict[str, Any], root_dir: Optional[Path] = None
) -> Dict[str, Any]:
    root = Path(root_dir) if root_dir else get_root_dir()
    cfg_dir = root / "config"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    cfg_file = cfg_dir / "video_layout_config.json"

    merged = load_video_layout_config(root)
    for section in (
        "canvas",
        "stock_background",
        "script_green_character",
        "karaoke_subtitle",
    ):
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

    cfg_file.write_text(
        json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8"
    )
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
    tự động kiểm tra và làm sạch chữ thừa nếu ảnh cũ chưa chuẩn,
    phóng to nhân vật sắc nét theo khung Preview và đặt SÁT ĐÁY DƯỚI CÙNG (`paste_y = target_h - new_h`).
    """
    if not green_screen_path or not os.path.exists(green_screen_path):
        return None
    try:
        src_p = Path(green_screen_path).resolve()
        if src_p.stat().st_size < 5_000:
            return None

        # Tự động kiểm tra xem ảnh nền xanh hiện tại có bị dính chữ cắt dở hoặc nhân vật nhỏ không; nếu có thì tái tạo ngay từ THUMBNAIL.png!
        try:
            if not _is_green_plate_clean_and_large(src_p):
                for cand_thumb in (
                    src_p.parent / "THUMBNAIL.png",
                    src_p.parent.parent / "THUMBNAIL.png",
                    src_p.parent.parent / "renders" / "THUMBNAIL.png",
                ):
                    if cand_thumb.exists() and cand_thumb.stat().st_size > 5_000:
                        normalize_character_to_strict_80_20_green_plate(
                            cand_thumb, src_p, part_index=1
                        )
                        break
        except Exception:
            pass

        cache_dir.mkdir(parents=True, exist_ok=True)

        scale_x = target_w / 1920.0
        scale_y = target_h / 1080.0
        box_x = int(round(float(char_cfg.get("x", 1260)) * scale_x))
        box_w = max(
            int(round(580 * scale_x)),
            int(round(float(char_cfg.get("width", 660)) * scale_x)),
        )
        box_h = max(
            int(round(880 * scale_y)),
            int(round(float(char_cfg.get("height", 1020)) * scale_y)),
        )
        opacity = max(0.1, min(1.0, float(char_cfg.get("opacity", 0.90))))

        sig = (
            f"char_bottom_v11_combined|{src_p}|{src_p.stat().st_mtime_ns}|{src_p.stat().st_size}|"
            f"{target_w}x{target_h}|x{box_x}_w{box_w}_h{box_h}_op{opacity:.2f}"
        )
        sig_hash = hashlib.md5(sig.encode("utf-8")).hexdigest()[:12]
        out_png = cache_dir / f"script_char_bottom_{target_w}x{target_h}_{sig_hash}.png"
        if out_png.exists() and out_png.stat().st_size > 5_000:
            return str(out_png)

        import numpy as np
        from PIL import Image, ImageFilter

        im = Image.open(src_p).convert("RGBA")
        arr = np.asarray(im, dtype=np.float32)
        # Chỉ lấy vùng nhân vật bên phải (x >= 55% chiều ngang) để tuyệt đối không bao giờ lấy nhầm chữ bên trái
        w_src = arr.shape[1]
        x_min_safe = int(round(w_src * 0.55))
        arr[:, :x_min_safe, 3] = 0.0

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
        alpha_img = Image.fromarray(alpha_u8).filter(
            ImageFilter.GaussianBlur(radius=0.75)
        )
        alpha_u8 = np.asarray(alpha_img, dtype=np.uint8)
        alpha_u8 = np.where(alpha_u8 < 14, 0, alpha_u8)

        # Áp dụng độ mờ Opacity (mặc định 0.9)
        if opacity < 0.999:
            alpha_u8 = np.clip(alpha_u8.astype(np.float32) * opacity, 0, 255).astype(
                np.uint8
            )

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

        scale = max(
            box_w / max(1, cw), min(box_h / max(1, ch), (target_w * 0.38) / max(1, cw))
        )
        new_w = max(
            int(round(540 * scale_x)),
            min(int(round(740 * scale_x)), int(round(cw * scale))),
        )
        new_h = max(
            int(round(720 * scale_y)),
            min(int(round(target_h * 0.96)), int(round(ch * (new_w / max(1, cw))))),
        )
        if new_h > int(round(target_h * 0.96)):
            new_h = int(round(target_h * 0.96))
            new_w = max(
                int(round(520 * scale_x)),
                min(int(round(740 * scale_x)), int(round(cw * (new_h / max(1, ch))))),
            )

        char_resized = char_crop.resize((new_w, new_h), Image.Resampling.LANCZOS)

        canvas = Image.new("RGBA", (target_w, target_h), (0, 0, 0, 0))
        # Đặt sát mép phải và BẮT BUỘC SÁT ĐÁY DƯỚI CÙNG (paste_y = target_h - new_h)
        paste_x = max(0, target_w - new_w)
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
    cached_nut = (
        cache_dir
        / f"fixed_green_layers_{target_w}x{target_h}_{work_fps}fps_{sig_hash}.nut"
    )
    if cached_nut.exists() and cached_nut.stat().st_size > 50_000:
        return str(cached_nut)

    with _GREEN_CACHE_LOCK:
        if cached_nut.exists() and cached_nut.stat().st_size > 50_000:
            return str(cached_nut)

        tmp_nut = cached_nut.with_suffix(".tmp.nut")
        scale_x = target_w / 1920.0
        scale_y = target_h / 1080.0

        cmd: List[str] = [
            _FFMPEG_BIN,
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            f"color=c=black@0.0:s={target_w}x{target_h}:r={work_fps}:d={cache_duration_sec:.1f},format=yuva420p",
        ]

        filter_parts: List[str] = ["[0:v]format=yuva420p[base0]"]
        cur_label = "[base0]"

        for idx, lyr in enumerate(active_layers, start=1):
            abs_p = lyr["abs_path"]
            ext = os.path.splitext(abs_p)[1].lower()
            is_img = ext in (".png", ".jpg", ".jpeg", ".webp", ".bmp")
            if is_img:
                cmd.extend(
                    ["-loop", "1", "-t", f"{cache_duration_sec:.1f}", "-i", abs_p]
                )
            else:
                cmd.extend(
                    [
                        "-stream_loop",
                        "-1",
                        "-t",
                        f"{cache_duration_sec:.1f}",
                        "-i",
                        abs_p,
                    ]
                )

            lx = int(round(float(lyr.get("x", 0)) * scale_x))
            ly = int(round(float(lyr.get("y", 0)) * scale_y))
            lw = max(16, (int(round(float(lyr.get("width", 300)) * scale_x)) // 2) * 2)
            lh = max(16, (int(round(float(lyr.get("height", 150)) * scale_y)) // 2) * 2)
            opacity = max(0.05, min(1.0, float(lyr.get("opacity", 1.0))))
            use_ck = bool(lyr.get("chromaKey", not is_img))
            key_hex = (
                re.sub(r"[^0-9A-Fa-f]", "", str(lyr.get("keyColor", "#00FF00")))
                or "00FF00"
            )
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
            filter_parts.append(
                f"{cur_label}{lyr_label}overlay=x={lx}:y={ly}:shortest=1:format=auto,format=yuva420p{next_base}"
            )
            cur_label = next_base

        cmd.extend(
            [
                "-filter_complex",
                ";".join(filter_parts),
                "-map",
                cur_label,
                "-c:v",
                "ffv1",
                "-level",
                "3",
                "-threads",
                "4",
                "-pix_fmt",
                "yuva420p",
                "-t",
                f"{cache_duration_sec:.1f}",
                "-f",
                "nut",
                str(tmp_nut),
            ]
        )

        try:
            print(
                f"[Renderer] ⚡ Đang tạo Cache cho {len(active_layers)} lớp Video Green cố định -> {cached_nut.name}..."
            )
            res = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=60,
                creationflags=0x08000000 if os.name == "nt" else 0,
            )
            if (
                res.returncode == 0
                and tmp_nut.exists()
                and tmp_nut.stat().st_size > 50_000
            ):
                os.replace(str(tmp_nut), str(cached_nut))
                print(
                    f"[Renderer] ✅ Đã lưu Cache Green cố định: {cached_nut.name} ({cached_nut.stat().st_size / (1024 * 1024):.2f} MB)"
                )
                return str(cached_nut)
            else:
                print(
                    f"[Renderer] ⚠️ Lưu ý khi tạo Cache Green: {res.stderr[-300:] if res.stderr else ''}"
                )
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
    appdata = (
        Path(os.environ.get("LOCALAPPDATA") or (Path.home() / "AppData" / "Local"))
        / "Mexico_Ong_Gia_Studio"
    )
    default_ssd = appdata / "SSD_Render_Staging"
    workspace_staging = get_root_dir() / "cache" / "SSD_Render_Staging"
    use_ssd = True
    custom_ssd = ""

    for cfg_cand in (
        appdata / "storage_paths.json",
        get_root_dir() / "config" / "config.json",
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


def get_saved_render_progress(
    output_path: str, total_dur: float = 0.0
) -> Dict[str, Any]:
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
                total_dur = float(
                    json.loads(meta_file.read_text(encoding="utf-8")).get(
                        "total_dur", 0.0
                    )
                    or 0.0
                )
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
        pct = (
            min(99.0, round((comp_sec / total_dur) * 100.0, 1))
            if total_dur > 0
            else 0.0
        )
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

    perf_mode = (
        (performance_mode or os.environ.get("STUDIO_PERF_MODE") or "full_100")
        .strip()
        .lower()
    )
    is_work_70 = perf_mode == "work_70"
    total_cores = os.cpu_count() or 8
    win_flags = 0x08000000 if os.name == "nt" else 0
    cpu_threads = (
        max(4, int(round(total_cores * 0.65)))
        if is_work_70
        else max(4, total_cores - 1)
    )
    filter_threads = max(2, cpu_threads // 2)

    base_stem = os.path.splitext(os.path.basename(output_path))[0]
    proj_prefix = re.sub(r"_master$", "", base_stem, flags=re.IGNORECASE)

    # Tự động dò tìm Ảnh Green Theo Kịch Bản (`THUMBNAIL-NENXANH.png` / `{ma_id}_THUMBNAIL_NENXANH.png`)
    if not green_screen_image_path or not os.path.exists(green_screen_image_path):
        out_p = Path(out_dir)
        audio_p = Path(audio_path).resolve()
        proj_root_from_audio = (
            audio_p.parent.parent
            if audio_p.parent.name.lower() == "assets"
            else out_p.parent
        )
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
            root_dir
            / "adas_skills"
            / "05_seo_thumbnail_padre_mx"
            / "references"
            / "example_green_screen.png",
        ]
        for gsc in gs_candidates:
            if gsc.exists() and gsc.stat().st_size > 5_000:
                green_screen_image_path = str(gsc)
                break

    default_ssd_dir, default_use_ssd = get_default_ssd_staging_dir()
    active_use_ssd = (
        default_use_ssd if use_ssd_staging is None else bool(use_ssd_staging)
    )
    active_ssd_root = (
        Path(ssd_staging_dir)
        if (ssd_staging_dir and str(ssd_staging_dir).strip())
        else default_ssd_dir
    )

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
        meta_file.write_text(
            json.dumps(current_meta, ensure_ascii=False, indent=2), encoding="utf-8"
        )
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
                        _FFMPEG_BIN,
                        "-y",
                        "-v",
                        "error",
                        "-i",
                        str(raw_ts),
                        "-t",
                        f"{safe_dur:.2f}",
                        "-c",
                        "copy",
                        "-f",
                        "mpegts",
                        str(clean_target),
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
    if (
        char_cfg.get("enabled", True)
        and green_screen_image_path
        and os.path.exists(green_screen_image_path)
    ):
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

    print(
        "================================================================================"
    )
    print(
        "🎬 [MEXICO ÔNG GIÀ RENDERER V2] DỰNG VIDEO ĐA LỚP + KARAOKE SUB + CACHE GREEN"
    )
    print(
        f"📐 Độ phân giải: {target_w}x{target_h} | 🎞️ FPS: {fps} | 🎵 Thời lượng: {dur / 60:.2f} phút"
    )
    print(
        f"🌑 Lớp #4 (Đáy): Stock làm tối nhẹ (brightness={eff_brightness}, contrast={eff_contrast})"
    )
    print(
        f"🟩 Lớp #3 (Giữa): Cache Video Green cố định: {Path(fixed_green_cache_nut).name if fixed_green_cache_nut else 'Không bật'}"
    )
    print(
        f"👴 Lớp #2 (Trên Green): Ảnh Green Kịch Bản sát đáy phải (Opacity={char_cfg.get('opacity', 0.9)}): {Path(char_cutout_png).name if char_cutout_png else 'Chưa có'}"
    )
    print(
        f"🔥 Lớp #1 (Cao nhất): Phụ đề Karaoke CapCut (.ASS): {karaoke_ass_path.name if generated_ass else subtitle_path}"
    )
    print(
        "================================================================================"
    )

    use_nvenc = check_nvenc_available()
    gop_size = str(max(24, int(fps) * 2))
    nvenc_codec_args = [
        "-c:v",
        "h264_nvenc",
        "-preset",
        "p1" if is_work_70 else "p2",
        "-tune",
        "hq",
        "-rc",
        "vbr",
        "-cq",
        "21",
        "-b:v",
        "0",
        "-g",
        gop_size,
        "-pix_fmt",
        "yuv420p",
    ]
    cpu_codec_args = [
        "-c:v",
        "libx264",
        "-preset",
        "superfast",
        "-crf",
        "21",
        "-g",
        gop_size,
        "-threads",
        str(cpu_threads),
        "-pix_fmt",
        "yuv420p",
    ]
    v_codec_args = nvenc_codec_args if use_nvenc else cpu_codec_args
    encoder_label = (
        "NVIDIA GPU NVENC" if use_nvenc else f"CPU Multi-Thread ({cpu_threads} threads)"
    )

    if remaining_dur > 1.5:
        filters: List[str] = []
        base_inputs_cmd: List[str] = [_FFMPEG_BIN, "-y"]
        input_idx = 0

        # LỚP #4 (ĐÁY): Video Stock có sẵn — Chỉ làm tối nhẹ
        stock_seek_raw = (
            round((completed_sec / pts_factor) % max(1.0, stock_dur), 2)
            if (completed_sec > 0 and stock_dur > 0)
            else 0.0
        )
        stock_seek_args = (
            ["-ss", f"{stock_seek_raw:.2f}"] if stock_seek_raw > 0.1 else []
        )
        base_inputs_cmd.extend(
            ["-stream_loop", "-1", *stock_seek_args, "-i", stock_video_path]
        )
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
            filters.append(
                f"{current_v}[{green_cache_idx}:v]overlay=x=0:y=0:shortest=1:format=yuv420[v_with_green]"
            )
            current_v = "[v_with_green]"

        # LỚP #2 (TRÊN VIDEO GREEN, DƯỚI SUB): Ảnh Green Theo Kịch Bản đặt sát đáy dưới cùng (Opacity = 0.9)
        if char_cutout_png and os.path.exists(char_cutout_png):
            base_inputs_cmd.extend(["-loop", "1", "-i", char_cutout_png])
            char_in_idx = input_idx
            input_idx += 1
            filters.append(
                f"[{char_in_idx}:v]fps={work_fps},format=yuva420p[char_rgba]"
            )
            filters.append(
                f"{current_v}[char_rgba]overlay=x=0:y=0:shortest=1:format=yuv420[v_with_char]"
            )
            current_v = "[v_with_char]"

        # LỚP #1 (CAO NHẤT - TOPMOST): Phụ đề chạy như Karaoke (.ASS)
        if generated_ass and os.path.exists(generated_ass):
            abs_ass = (
                os.path.abspath(generated_ass)
                .replace("\\", "/")
                .replace(":", r"\:")
                .replace("'", r"\'")
            )
            filters.append(
                f"{current_v}subtitles=filename='{abs_ass}':original_size={target_w}x{target_h},fps={fps},format=yuv420p[v_out]"
            )
        elif subtitle_path and os.path.exists(subtitle_path):
            abs_srt = (
                os.path.abspath(subtitle_path)
                .replace("\\", "/")
                .replace(":", r"\:")
                .replace("'", r"\'")
            )
            filters.append(
                f"{current_v}subtitles=filename='{abs_srt}',fps={fps},format=yuv420p[v_out]"
            )
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
            bgm_seek_args = (
                ["-ss", f"{(completed_sec % 180.0):.2f}"] if completed_sec > 0.1 else []
            )
            base_inputs_cmd.extend(
                ["-stream_loop", "-1", *bgm_seek_args, "-i", str(bgm_path)]
            )
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
                "-t",
                f"{remaining_dur:.3f}",
                "-filter_complex_threads",
                str(filter_threads),
                "-filter_complex",
                fc,
                "-map",
                "[v_out]",
                "-map",
                "[a_out]",
                *codec_args_list,
                "-threads",
                str(cpu_threads),
                "-r",
                str(fps),
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                "-ar",
                "48000",
                "-ac",
                "2",
                "-progress",
                "pipe:1",
                "-f",
                "mpegts",
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
                            if progress_callback and (
                                now_cb - last_cb_ts >= 0.8 or percent >= 99.9
                            ):
                                last_cb_ts = now_cb
                                progress_callback(
                                    percent,
                                    f"Đang render video ({encoder_label}): {percent}% ({total_done_sec:.0f}s / {dur:.0f}s)",
                                )
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
                print(
                    f"⚠️ [NVENC FALLBACK] Chuyển sang CPU Multi-Thread ({cpu_threads} threads)..."
                )
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
            _FFMPEG_BIN,
            "-y",
            "-v",
            "error",
            "-i",
            valid_clean_segments[0],
            "-t",
            f"{dur:.3f}",
            "-c",
            "copy",
            "-bsf:a",
            "aac_adtstoasc",
            temp_output_path,
        ]
    else:
        concat_list_file = resume_dir / "concat_segments.txt"
        with open(concat_list_file, "w", encoding="utf-8") as f_cat:
            for seg_p in valid_clean_segments:
                clean_seg_p = (
                    os.path.abspath(seg_p).replace("\\", "/").replace("'", "'\\''")
                )
                f_cat.write(f"file '{clean_seg_p}'\n")
        remux_cmd = [
            _FFMPEG_BIN,
            "-y",
            "-v",
            "error",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_list_file),
            "-t",
            f"{dur:.3f}",
            "-c",
            "copy",
            "-bsf:a",
            "aac_adtstoasc",
            temp_output_path,
        ]

    remux_res = subprocess.run(
        remux_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        creationflags=win_flags,
    )
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


sys.modules["backend.visual_cue_director"] = sys.modules[__name__]
