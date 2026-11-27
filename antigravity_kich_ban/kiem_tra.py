"""
CÔNG CỤ TỰ KIỂM TRA KỊCH BẢN PADRE MX CHO ANTIGRAVITY (chỉ đọc kịch bản, không sinh chữ).

Cách dùng (chạy trong terminal):
  python kiem_tra.py --thu-muc                    -> in thư mục dự án của app + mã dự án gợi ý (chạy ĐẦU TIÊN)
  python kiem_tra.py "<thư mục dự án>"            -> kiểm tra toàn bộ (part_1.txt..part_7.txt)
  python kiem_tra.py "<thư mục dự án>" --part 3   -> chỉ kiểm tra PART 3 vừa viết
  python kiem_tra.py "<thư mục dự án>" --dong-goi -> khi đã ĐẠT hết: ghép part_a/b/c, PMX_FULL_SCRIPT.txt,
                                                    script_clean.txt, QA_RELEASE.json, idea_info.json để app
                                                    quét ("Cập Nhật Folder") và render

Thoát mã 0 = ĐẠT, mã 1 = còn LỖI (in rõ từng lỗi kèm câu trích để sửa).
"""

import collections
import json
import re
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
APP_ROOT = Path(__file__).resolve().parent.parent  # thư mục app (chứa backend/)
sys.path.insert(0, str(APP_ROOT))
try:
    from backend.script_quality_gate import (  # noqa: E402
        assemble_stages,
        decide_script_release,
        parse_qa_verdict,
        run_machine_script_gate,
        write_script_release_record,
    )
except Exception as exc:  # pragma: no cover
    raise SystemExit(f"Không nạp được bộ kiểm tra của app tại {APP_ROOT}: {exc}")

# ---------------------------------------------------------------- NGƯỠNG
PART_MIN, PART_MAX = 9_500, 11_500          # mỗi PART (ký tự thân bài, không tính nhãn)
TOTAL_MIN, TOTAL_MAX = 70_000, 80_000
MAX_WORDS_SENTENCE = 38                      # câu dài hơn = LỖI (giọng đọc máy hụt hơi)
SOFT_WORDS_SENTENCE = 30                     # 31–38 từ: cho phép tối đa 6 câu/PART
AVG_WORDS_RANGE = (11.0, 19.0)               # trung bình từ/câu: tránh câu cụt kiểu ChatGPT (8,6) và câu dài lê thê
MIN_DIALOGUE_PER_1K = 2.5                    # số đoạn thoại (dòng mở bằng —) trên 1.000 ký tự ≈ 25 lượt thoại/PART
MAX_SAME_MONEY_PHRASE = 4                    # cùng 1 số tiền viết đầy đủ tối đa 4 lần cả kịch bản
MAX_REPEAT_5GRAM = 6                         # cụm 5 từ lặp quá 6 lần = LỖI
MIN_MX_MARKERS_TOTAL = 12                    # tối thiểu số lượt từ đặc trưng Mexico cả kịch bản

# Chỉ những từ chắc chắn là Tây Ban Nha châu Âu (hoặc tục ở Mexico như "coger"); tránh báo nhầm "piso", "tío"...
SPAIN_WORDS = {
    "coche": "carro", "coches": "carros", "móvil": "celular", "ordenador": "computadora",
    "ordenadores": "computadoras", "¡vale": "¡órale / está bien", "vale,": "está bien,",
    "vosotros": "ustedes", "vuestro": "su", "vuestra": "su", "vuestros": "sus",
    "zumo": "jugo", "coger": "agarrar / tomar (ở Mexico là từ tục)", "cogió": "agarró / tomó",
    "aparcar": "estacionar", "aparqué": "estacioné", "gafas": "lentes", "patatas": "papas",
    "chaval": "chamaco", "enfadado": "enojado", "enfadada": "enojada", "enfadó": "enojó",
    "cabreado": "enojado", "guay": "padre / chido",
}
MX_MARKERS = [
    "mijo", "mija", "ahorita", "platicar", "platicamos", "platiqué", "órale", "ándale", "mande",
    "híjole", "ni modo", "chamba", "lana", "compadre", "comadre", "padrino", "madrina", "neta",
    "fíjate", "qué pena", "con permiso", "de volada", "camión", "colonia", "licenciado", "licenciada",
    "señito", "don ", "doña ", "jefa", "jefecita", "pues sí", "a poco",
]
LEAK_PATTERNS = [
    (r"\d", "chữ số (TTS đọc sai) — viết số bằng chữ"),
    (r"[$%#&@*_`|<>{}]", "ký hiệu/markdown"),
    (r"\[(?!PART \d\])[^\]]*\]", "ngoặc vuông ngoài nhãn [PART n]"),
    (r"\([^)]*\)", "ngoặc đơn (ghi chú đạo diễn?)"),
    (r"\b(?:LOCKED_TITLE|CURRENT_FINAL_TITLE|LEDGER|ESCENA \w+:|Escena\s+\d|PART\s+\d\s*:)", "rò rỉ nhãn/metadata"),
    (r"\b(?:MXN|USD|pesos mexicanos)\b", "đơn vị tiền dạng ký hiệu (MXN/USD)"),
]
HEADING_RX = re.compile(r"(?m)^\s*\[PART (\d)\]\s*$")
SENT_RX = re.compile(r"[^.!?…]+[.!?…]+[»”\"]?")
WORD_RX = re.compile(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+")
MONEY_RX = re.compile(
    r"(?i)\b((?:(?:un|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|once|doce|quince|veinte|treinta|cuarenta|cincuenta|sesenta|setenta|ochenta|noventa|cien|ciento|doscientos|trescientos|cuatrocientos|quinientos|seiscientos|setecientos|ochocientos|novecientos|mil|millón|millones|y)\s+){2,}pesos)"
)


def app_projects_dir() -> Path:
    """Thư mục dự án mà app đang dùng (config/config.json -> projects_dir), mặc định APP_ROOT/projects."""
    try:
        cfg = json.loads((APP_ROOT / "config" / "config.json").read_text(encoding="utf-8"))
        p = str(cfg.get("projects_dir") or "").strip()
        if p:
            return Path(p)
    except (OSError, ValueError):
        pass
    return APP_ROOT / "projects"


def write_idea_info(proj: Path, title: str, total_chars: int) -> None:
    """Ghi idea_info.json để app nhận dự án là kênh Padre MX, tiêu đề đã khóa, kịch bản đã xong."""
    info_path = proj / "idea_info.json"
    try:
        info = json.loads(info_path.read_text(encoding="utf-8")) if info_path.exists() else {}
    except ValueError:
        info = {}
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    info.update(
        {
            "ma_id": proj.name,
            "channel_key": "padre_mx",
            "raw_input_text": info.get("raw_input_text") or title,
            "draft_title_ja": info.get("draft_title_ja") or title,
            "locked_title": title,
            "use_original_title": True,
            "status": "SCRIPT_DONE",
            "current_step": f"📝 Antigravity đã viết xong kịch bản ({total_chars:,} chữ) — Chờ vẽ Thumbnail & Render",
            "pure_char_count": total_chars,
            "has_script": True,
            "has_seo": True,
            "completed_parts_count": 3,
            "missing_parts": [],
            "thumb_mode": info.get("thumb_mode") or "both",
            "ai_provider": "antigravity",
            "created_at": info.get("created_at") or now,
            "updated_at": now,
        }
    )
    info_path.write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")


def read(p: Path) -> str:
    return p.read_text(encoding="utf-8-sig").replace("\r\n", "\n").replace("\r", "\n").strip()


def body_of(text: str) -> str:
    return HEADING_RX.sub("", text).strip()


def sentences(text: str):
    return [s.strip() for s in SENT_RX.findall(body_of(text)) if WORD_RX.search(s)]


def check_part(n: int, text: str, errors: list, warns: list):
    tag = f"PART {n}"
    heads = [int(x) for x in HEADING_RX.findall(text)]
    if heads != [n]:
        errors.append(f"{tag}: nhãn phải đúng 1 dòng `[PART {n}]` ở đầu file (đang có {heads})")
    size = len(body_of(text))
    if not PART_MIN <= size <= PART_MAX:
        errors.append(f"{tag}: dài {size:,} ký tự, cần {PART_MIN:,}–{PART_MAX:,}")
    sents = sentences(text)
    lens = [len(WORD_RX.findall(s)) for s in sents]
    too_long = [s for s, n_w in zip(sents, lens) if n_w > MAX_WORDS_SENTENCE]
    for s in too_long[:5]:
        errors.append(f"{tag}: câu {len(WORD_RX.findall(s))} từ (> {MAX_WORDS_SENTENCE}) — tách ra: «{s[:110]}…»")
    if len(too_long) > 5:
        errors.append(f"{tag}: còn {len(too_long) - 5} câu > {MAX_WORDS_SENTENCE} từ nữa")
    soft = sum(1 for n_w in lens if SOFT_WORDS_SENTENCE < n_w <= MAX_WORDS_SENTENCE)
    if soft > 6:
        errors.append(f"{tag}: {soft} câu dài {SOFT_WORDS_SENTENCE + 1}–{MAX_WORDS_SENTENCE} từ (tối đa 6)")
    avg = sum(lens) / max(1, len(lens))
    if not AVG_WORDS_RANGE[0] <= avg <= AVG_WORDS_RANGE[1]:
        errors.append(f"{tag}: trung bình {avg:.1f} từ/câu, cần {AVG_WORDS_RANGE[0]:.0f}–{AVG_WORDS_RANGE[1]:.0f}")
    dlg = len(re.findall(r"(?m)^\s*—", body_of(text))) * 1000 / max(1, size)
    if dlg < MIN_DIALOGUE_PER_1K:
        errors.append(f"{tag}: thoại quá ít ({dlg:.1f} lượt/1.000 ký tự, cần ≥ {MIN_DIALOGUE_PER_1K}) — diễn bằng đối thoại, bớt kể")
    b = body_of(text)
    for rx, label in LEAK_PATTERNS:
        hits = re.findall(r".{0,25}(?:" + rx + r").{0,25}", b, flags=re.IGNORECASE)
        if hits:
            errors.append(f"{tag}: {label} ×{len(hits)} — ví dụ «{hits[0].strip()}»")
    low = " " + b.lower() + " "
    for w, fix in SPAIN_WORDS.items():
        c = len(re.findall(r"(?<![a-záéíóúüñ])" + re.escape(w) + r"(?![a-záéíóúüñ])", low))
        if c:
            errors.append(f"{tag}: từ Tây Ban Nha châu Âu «{w}» ×{c} → dùng «{fix}»")
    if not re.search(r"[?!…]\s*$|[.]\s*$", b):
        warns.append(f"{tag}: câu cuối chưa có dấu kết")
    return size, lens


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    if sys.argv[1] == "--thu-muc":
        pdir = app_projects_dir()
        print(f"THU_MUC_DU_AN_APP: {pdir}")
        print(f"MA_GOI_Y: AG_MXC_{time.strftime('%Y%m%d_%H%M')}")
        print(f"=> Tạo thư mục: {pdir / ('AG_MXC_' + time.strftime('%Y%m%d_%H%M'))}")
        sys.exit(0)
    proj = Path(sys.argv[1])
    only = int(sys.argv[sys.argv.index("--part") + 1]) if "--part" in sys.argv else None
    pack = "--dong-goi" in sys.argv
    errors, warns = [], []
    texts = {}
    for n in range(1, 8):
        f = proj / f"part_{n}.txt"
        if f.exists():
            texts[n] = read(f)
        elif only is None:
            errors.append(f"Thiếu file part_{n}.txt")
    targets = [only] if only else sorted(texts)
    all_lens = []
    for n in targets:
        if n not in texts:
            errors.append(f"Thiếu file part_{n}.txt")
            continue
        _, lens = check_part(n, texts[n], errors, warns)
        all_lens += lens

    if only is None and len(texts) == 7:
        full = "\n\n".join(texts[n] for n in range(1, 8))
        gate = run_machine_script_gate(full, "padre_mx", APP_ROOT)
        for f in gate["failures"]:
            errors.append(f"Cổng máy của app: {f}")
        total = gate["chars"]
        if not TOTAL_MIN <= total <= TOTAL_MAX:
            errors.append(f"Tổng {total:,} ký tự, cần {TOTAL_MIN:,}–{TOTAL_MAX:,}")
        low = " " + body_of(full).lower() + " "
        money = collections.Counter(m.group(1).lower() for m in MONEY_RX.finditer(low))
        for phrase, c in money.most_common():
            if c > MAX_SAME_MONEY_PHRASE:
                errors.append(f"Số tiền «{phrase}» nhắc đầy đủ {c} lần (tối đa {MAX_SAME_MONEY_PHRASE}) — lần sau gọi là «esa deuda», «el pagaré», «ese dinero»…")
        words = WORD_RX.findall(low)
        grams = collections.Counter(" ".join(words[i:i + 5]) for i in range(len(words) - 4))
        for g, c in grams.most_common(5):
            if c > MAX_REPEAT_5GRAM and not MONEY_RX.search(g + " pesos"):
                errors.append(f"Cụm «{g}» lặp {c} lần (tối đa {MAX_REPEAT_5GRAM}) — đổi cách nói")
        mx = sum(len(re.findall(r"(?<![a-záéíóúüñ])" + re.escape(w.strip()) + r"(?![a-záéíóúüñ])", low)) for w in MX_MARKERS)
        if mx < MIN_MX_MARKERS_TOTAL:
            errors.append(f"Chất Mexico mỏng: {mx} lượt từ đặc trưng (cần ≥ {MIN_MX_MARKERS_TOTAL}) — thêm tự nhiên: mijo/mija, ahorita, platicar, ni modo, híjole, don/doña…")
        canon = proj / "CANON.json"
        if canon.exists():
            try:
                names = json.loads(canon.read_text(encoding="utf-8")).get("nhan_vat", [])
                for nv in names:
                    ten = str(nv.get("ten") or "").strip()
                    if ten and ten.split()[0].lower() not in low:
                        warns.append(f"Nhân vật trong CANON không xuất hiện: {ten}")
            except ValueError:
                errors.append("CANON.json không phải JSON hợp lệ")
        else:
            errors.append("Thiếu CANON.json (sổ cái tên/tuổi/tiền/mốc thời gian)")

    print("=" * 70)
    if all_lens:
        print(f"Câu: {len(all_lens)} | trung bình {sum(all_lens) / len(all_lens):.1f} từ | dài nhất {max(all_lens)} từ")
    for w in warns:
        print("CẢNH BÁO:", w)
    for e in errors:
        print("LỖI:", e)
    ok = not errors
    print("KẾT QUẢ:", "ĐẠT" if ok else f"CHƯA ĐẠT ({len(errors)} lỗi) — sửa hết rồi chạy lại")
    print("=" * 70)

    if pack:
        if not ok or only is not None:
            raise SystemExit("Chưa đóng gói: kịch bản còn lỗi (hoặc đang kiểm tra 1 PART).")
        audit = proj / "KIEM_DINH.md"
        verdict = parse_qa_verdict(read(audit)) if audit.exists() else None
        if verdict is None:
            raise SystemExit("Chưa đóng gói: KIEM_DINH.md thiếu dòng QA_VERDICT: {...} hợp lệ.")
        seo = proj / "00_TIEU_DE_VA_SEO_YOUTUBE.txt"
        seo_txt = read(seo) if seo.exists() else ""
        if "## Imagen THUMBNAIL\n" not in seo_txt + "\n" or "## Imagen THUMBNAIL-NENXANH" not in seo_txt:
            raise SystemExit("Chưa đóng gói: thiếu 00_TIEU_DE_VA_SEO_YOUTUBE.txt hoặc thiếu 2 mục '## Imagen THUMBNAIL' / '## Imagen THUMBNAIL-NENXANH'.")
        try:
            title = str(json.loads((proj / "CANON.json").read_text(encoding="utf-8")).get("tieu_de") or "").strip()
        except (OSError, ValueError):
            title = ""
        if not title:
            raise SystemExit("Chưa đóng gói: CANON.json thiếu 'tieu_de' (tiêu đề khóa).")
        stages = {
            "A": "\n\n".join(texts[n] for n in (1, 2)),
            "B": "\n\n".join(texts[n] for n in (3, 4, 5)),
            "C": "\n\n".join(texts[n] for n in (6, 7)),
        }
        for k, v in stages.items():
            (proj / f"part_{k.lower()}.txt").write_text(v + "\n", encoding="utf-8")
        full = assemble_stages(stages)
        (proj / "PMX_FULL_SCRIPT.txt").write_text(full + "\n", encoding="utf-8")
        clean = body_of(full)
        clean = re.sub(r"\n{3,}", "\n\n", clean)
        (proj / "script_clean.txt").write_text(clean + "\n", encoding="utf-8")
        gate = run_machine_script_gate(full, "padre_mx", APP_ROOT)
        record = decide_script_release("padre_mx", clean, gate, verdict)
        record["nguon"] = "ANTIGRAVITY + kiem_tra.py"
        write_script_release_record(proj, record)
        write_idea_info(proj, title, len(clean))
        print(f"ĐÓNG GÓI: QA_RELEASE.json = {record['release_decision']}" + (f" | lý do: {record['reasons']}" if record["reasons"] else ""))
        if record["release_decision"] != "READY":
            sys.exit(1)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
