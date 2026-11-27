# -*- coding: utf-8 -*-
"""
Chốt chất lượng kịch bản dùng chung cho 3 kênh (Padre MX, Homeless, Mafia).

Module này không gọi ChatGPT và không import phần còn lại của backend, để có thể
kiểm thử độc lập. Nó quản lý:
- định mức độ dài của từng kênh;
- kiểm tra máy bằng chính các công cụ nằm trong `adas_skills`;
- đọc kết luận QA và áp dụng bản vá theo từng đoạn nguyên văn;
- hồ sơ phát hành `QA_RELEASE.json` dùng để quyết định có được render hay không.
"""

from __future__ import annotations

import difflib
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import unicodedata
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

RELEASE_RECORD_NAME = "QA_RELEASE.json"
RELEASE_SCHEMA = "SCRIPT_RELEASE_V1"
DECISION_READY = "READY"
DECISION_NOT_READY = "NOT_READY"
DECISION_PENDING = "PENDING"

STAGE_PARTS: Dict[str, Tuple[int, ...]] = {"A": (1, 2), "B": (3, 4, 5), "C": (6, 7)}
_WORD_RX = re.compile(r"[A-Za-z0-9]+(?:[’'\-][A-Za-z0-9]+)*")
_HEADING_LINE_RX = re.compile(r"(?m)^[ \t]*\[\s*PART\s*([1-7])\s*\][ \t]*$", re.IGNORECASE)
_MAX_PATCH_CHARS = 6000
_MIN_PATCH_ANCHOR_CHARS = 12

SCRIPT_LENGTH_PROFILES: Dict[str, Dict[str, Any]] = {
    "padre_mx": {
        "label": "PADRE MX",
        "language": "es-MX",
        "language_name": "tiếng Tây Ban Nha Mexico",
        "audit_skill": "04_kiem_dinh_kich_ban_padre_mx",
        "total_min": 70000,
        "total_max": 80000,
        "total_target": 75000,
        "hard_floor": 55000,
        "min_part": 8500,
        "max_words": None,
        "target_words": None,
        "score_min": 95,
        "verifier": "03_viet_kich_ban_padre_mx/scripts/verify_full_script.py",
        "stages": {
            "A": {"min": 20000, "max": 24000, "target": 22000, "accept": 17000, "part_floor": 8500},
            "B": {"min": 30000, "max": 35000, "target": 32500, "accept": 25500, "part_floor": 8500},
            "C": {"min": 20000, "max": 25000, "target": 22500, "accept": 17000, "part_floor": 8500},
        },
        "logic_focus": (
            "tuổi, số năm, tiền MXN, địa điểm Mexico, ai biết gì từ khi nào, vòng đời vật chứng, "
            "thủ tục công chứng/ngân hàng/pháp lý Mexico, ngôi kể thứ nhất của người cha."
        ),
        "quality_focus": (
            "hook 90 giây vào thẳng bất công gia đình, nhịp truyện, đoạn lặp, cao trào pháp lý ở PART 5–6, "
            "kết nhân văn của người cha ở PART 7, tiếng es-MX tự nhiên khi đọc TTS."
        ),
    },
    "homeless": {
        "label": "HOMELESS",
        "language": "en-US",
        "language_name": "tiếng Anh Mỹ",
        "audit_skill": "04_auditor_homeless",
        "total_min": 70000,
        "total_max": 80000,
        "total_target": 75000,
        "hard_floor": 55000,
        "min_part": 200,
        "max_words": None,
        "target_words": None,
        "score_min": 98,
        "verifier": "03_writer_homeless/scripts/verify_full_script.py",
        "stages": {
            "A": {"min": 20000, "max": 23000, "target": 21500, "accept": 17000, "part_floor": 9500},
            "B": {"min": 30000, "max": 34000, "target": 32000, "accept": 25500, "part_floor": 9500},
            "C": {"min": 20000, "max": 23000, "target": 21500, "accept": 17000, "part_floor": 9500},
        },
        "logic_focus": (
            "tuổi, mốc năm, tiền USD, địa điểm tại Mỹ, ai biết gì từ khi nào, chuỗi manh mối, "
            "tính hợp lý của hồ sơ bất động sản/di sản và kỹ thuật phục chế."
        ),
        "quality_focus": (
            "90 giây đầu có đối đầu và mỏ neo tò mò, nhịp điều tra, đoạn lặp, cú lật di sản có gieo trước, "
            "cái kết chữa lành đĩnh đạc, tiếng Anh Mỹ tự nhiên khi đọc TTS."
        ),
    },
    "mafia": {
        "label": "MAFIA × MAID",
        "language": "en-US",
        "language_name": "tiếng Anh Mỹ",
        "audit_skill": "04_auditor_mafia",
        "total_min": 44000,
        "total_max": 48000,
        "total_target": 45000,
        "hard_floor": 40000,
        "min_part": 3000,
        "max_words": 7999,
        "target_words": 7600,
        "word_target_range": (7400, 7650),
        "score_min": None,
        "verifier": "03_writer_mafia/scripts/maid_pipeline.py",
        "stages": {
            "A": {"min": 12400, "max": 13800, "target": 12900, "accept": 10500, "part_floor": 5800, "words": 2180},
            "B": {"min": 18800, "max": 20400, "target": 19400, "accept": 16000, "part_floor": 5800, "words": 3280},
            "C": {"min": 12400, "max": 13800, "target": 12700, "accept": 10500, "part_floor": 5800, "words": 2140},
        },
        "logic_focus": (
            "tuổi, mốc thời gian, tiền USD, vị trí nhân vật, an ninh, thương tích, ai biết gì từ khi nào, "
            "vật chứng có gieo trước, nữ chính có hành động quyết định và ranh giới đồng thuận."
        ),
        "quality_focus": (
            "lời hứa của tiêu đề, hook đầu truyện, nhịp từng Part, đoạn lặp, nữ chính tự tạo cú lật, "
            "cái kết công lý và lãng mạn có đồng thuận, an toàn YouTube, tiếng Anh Mỹ tự nhiên khi đọc TTS."
        ),
    },
}

_REFERENCE_BUNDLES: Dict[Tuple[str, str], Tuple[str, Tuple[Tuple[str, int], ...]]] = {
    ("padre_mx", "outline"): (
        "02_gian_y_padre_mx",
        (("OUTLINE_CANON_HANDOFF.md", 1500), ("MEXICO_CHANNEL_DNA.md", 5500), ("CROSS_SKILL_QUALITY_CONTRACT.md", 6000)),
    ),
    ("homeless", "outline"): (
        "02_outline_homeless",
        (
            ("V3_OUTLINE_HANDOFF.md", 600),
            ("MASTER_OUTLINE_ENGINE.md", 5400),
            ("CANON_FORENSIC_HANDOFF.md", 8200),
            ("HOMELESS_V3_CROSS_SKILL_CONTRACT.md", 4200),
            ("DNA_A_CoyotFrontierHearts.md", 1800),
            ("DNA_B_Forgotten_Fables.md", 1800),
            ("DNA_C_Forgotten_Trails.md", 1800),
            ("DNA_D_Secret_Legacy.md", 1800),
            ("DNA_E_Silences_Narratives.md", 1800),
        ),
    ),
    ("mafia", "outline"): (
        "02_outline_mafia",
        (
            ("V2_0_INTEGRATION_CONTRACT.md", 7000),
            ("V2_0_CREATIVE_BLUEPRINT.md", 2800),
            ("MASTER_PROMPT_UNIVERSAL_DNA_TO_STORY_OUTLINE_ENGINE.md", 6000),
            ("DNA_A_Mafia_Boss_Archives.txt", 2200),
            ("DNA_B_Mafia_Boss_Romance.txt", 2200),
            ("DNA_C_The_Mafias_Hidden_Heart.txt", 2200),
        ),
    ),
    ("padre_mx", "writer"): (
        "03_viet_kich_ban_padre_mx",
        (("MEXICO_CHANNEL_DNA.md", 5500), ("CROSS_SKILL_QUALITY_CONTRACT.md", 5000)),
    ),
    ("homeless", "writer"): (
        "03_writer_homeless",
        (
            ("V3_WRITER_HANDOFF.md", 600),
            ("CANON_STATE_MATRIX.md", 5700),
            ("FORENSIC_LOGIC_GATE.md", 6000),
            ("PART_QA_CHECKLIST.md", 5000),
            ("MASTER_SCRIPT_ENGINE.md", 9000),
        ),
    ),
    ("mafia", "writer"): (
        "03_writer_mafia",
        (
            ("V2_0_INTEGRATION_CONTRACT.md", 7000),
            ("V2_0_COUNTING_METHOD.md", 1200),
            ("V2_0_CREATIVE_BLUEPRINT.md", 2800),
            ("SHARED_PRODUCTION_CONTRACT.md", 5200),
            ("MASTER_PROMPT_WRITE_SCRIPT_FROM_OUTLINE.md", 8000),
        ),
    ),
    ("padre_mx", "audit_logic"): (
        "04_kiem_dinh_kich_ban_padre_mx",
        (("QA_SCOPE_AND_FORMS_V4.md", 5000), ("MEXICO_CHANNEL_DNA.md", 5500)),
    ),
    ("homeless", "audit_logic"): (
        "04_auditor_homeless",
        (("LOGIC_CHECKLIST.md", 7000), ("FORENSIC_REVIEW_ENGINE.md", 7000)),
    ),
    ("mafia", "audit_logic"): (
        "04_auditor_mafia",
        (
            ("FORENSIC_SCORE_RUBRIC.md", 3700),
            ("LOGIC_CHECKLIST.md", 4800),
            ("FORENSIC_REVIEW_ENGINE.md", 6300),
            ("V2_0_QA_REPAIR_PROTOCOL.md", 3000),
        ),
    ),
    ("padre_mx", "audit_quality"): (
        "04_kiem_dinh_kich_ban_padre_mx",
        (("CROSS_SKILL_QUALITY_CONTRACT.md", 5000),),
    ),
    ("homeless", "audit_quality"): (
        "04_auditor_homeless",
        (("HUMAN_PROSE_CHECKLIST.md", 5500), ("YOUTUBE_AUDIENCE_READINESS.md", 6000)),
    ),
    ("mafia", "audit_quality"): (
        "04_auditor_mafia",
        (("HUMAN_PROSE_CHECKLIST.md", 3300), ("YOUTUBE_AUDIENCE_READINESS.md", 3800)),
    ),
}


def get_script_length_profile(channel_key: str) -> Dict[str, Any]:
    return SCRIPT_LENGTH_PROFILES.get(
        str(channel_key or "padre_mx").strip().lower(),
        SCRIPT_LENGTH_PROFILES["padre_mx"],
    )


def normalize_script_text(text: str) -> str:
    return unicodedata.normalize("NFC", text or "").replace("\r\n", "\n").replace("\r", "\n")


def assemble_stages(stages: Dict[str, str]) -> str:
    return "\n\n".join((stages.get(k) or "").strip() for k in ("A", "B", "C")).strip()


def split_script_parts(text: str) -> Tuple[List[int], Dict[int, str]]:
    norm = normalize_script_text(text)
    matches = list(_HEADING_LINE_RX.finditer(norm))
    numbers = [int(m.group(1)) for m in matches]
    parts: Dict[int, str] = {}
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(norm)
        parts[int(match.group(1))] = norm[match.end() : end].strip("\n")
    return numbers, parts


def count_script_metrics(text: str) -> Dict[str, Any]:
    """Đếm theo đúng quy ước của skill: body bỏ dòng [PART N], từ theo regex của Mafia V2."""
    norm = normalize_script_text(text)
    numbers, parts = split_script_parts(norm)
    body = _HEADING_LINE_RX.sub("", norm).strip()
    joined = "\n".join(parts.values()) if parts else body
    heading_chars = sum(len(f"PART {n} — Part {n}") for n in numbers)
    return {
        "headings": numbers,
        "body_chars": len(body),
        "visible_chars": len(joined.replace("\n", "")) + heading_chars,
        "words": len(_WORD_RX.findall(joined)),
        "part_chars": {n: len(p.strip()) for n, p in parts.items()},
    }


def _metric_chars(metrics: Dict[str, Any], channel_key: str) -> int:
    key = "visible_chars" if str(channel_key).lower() == "mafia" else "body_chars"
    return int(metrics[key])


def _run_verifier_script(tool_path: Path, text: str) -> Tuple[Optional[bool], List[str]]:
    canonical = normalize_script_text(text).strip() + "\n"
    handle, temp_path = tempfile.mkstemp(prefix="script_gate_", suffix=".txt")
    try:
        with os.fdopen(handle, "wb") as out:
            out.write(canonical.encode("utf-8"))
        env = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONDONTWRITEBYTECODE": "1"}
        proc = subprocess.run(
            [sys.executable, "-B", "-I", str(tool_path), temp_path],
            capture_output=True,
            timeout=30,
            env=env,
            creationflags=0x08000000 if os.name == "nt" else 0,
        )
        data = json.loads(proc.stdout.decode("utf-8", errors="replace"))
        return bool(data.get("pass")), [str(x) for x in data.get("failures", [])]
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        return None, [f"Không chạy được công cụ kiểm tra: {exc}"]
    finally:
        try:
            os.unlink(temp_path)
        except OSError:
            pass


def _run_mafia_pipeline_check(tool_path: Path, text: str) -> Tuple[Optional[bool], List[str], List[str]]:
    try:
        spec = importlib.util.spec_from_file_location("maid_pipeline_release_gate", tool_path)
        if spec is None or spec.loader is None:
            return None, ["Không nạp được maid_pipeline.py"], []
        module = importlib.util.module_from_spec(spec)
        previous = sys.dont_write_bytecode
        sys.dont_write_bytecode = True
        try:
            spec.loader.exec_module(module)
        finally:
            sys.dont_write_bytecode = previous
        converted = _HEADING_LINE_RX.sub(
            lambda m: f"PART {m.group(1)} — Part {m.group(1)}",
            normalize_script_text(text).strip(),
        )
        metrics = module.metrics(converted)
        failures: List[str] = []
        warnings: List[str] = []
        for finding in module.length_findings(metrics):
            if finding.get("id") == "LENGTH_HARD":
                failures.append(str(finding.get("reason")))
            elif 44000 <= metrics["visible_characters"] <= 48000 and metrics["spoken_words"] < 8000:
                warnings.append(str(finding.get("reason")))
            else:
                failures.append(str(finding.get("reason")))
        return not failures, failures, warnings
    except Exception as exc:  # GateError của skill cũng là lỗi kịch bản cần báo lại.
        return False, [f"Kiểm tra Mafia không đạt: {exc}"], []


def run_machine_script_gate(full_script: str, channel_key: str, root_dir: Path) -> Dict[str, Any]:
    """Kiểm tra độ dài, cấu trúc bằng code; không đánh giá chất lượng văn."""
    profile = get_script_length_profile(channel_key)
    metrics = count_script_metrics(full_script)
    chars = _metric_chars(metrics, channel_key)
    failures: List[str] = []
    warnings: List[str] = []

    if metrics["headings"] != list(range(1, 8)):
        failures.append(f"Sai cấu trúc 7 PART: {metrics['headings']}")
    if not profile["total_min"] <= chars <= profile["total_max"]:
        failures.append(f"Độ dài {chars:,} ngoài {profile['total_min']:,}–{profile['total_max']:,} ký tự")
    short_parts = {n: c for n, c in metrics["part_chars"].items() if c < profile["min_part"]}
    if short_parts:
        failures.append(f"Có Part dưới {profile['min_part']:,} ký tự: {short_parts}")
    if profile["max_words"] and metrics["words"] > profile["max_words"]:
        failures.append(f"{metrics['words']:,} từ vượt giới hạn dưới 8.000 từ")
    word_range = profile.get("word_target_range")
    if word_range and not word_range[0] <= metrics["words"] <= word_range[1]:
        warnings.append(f"{metrics['words']:,} từ ngoài vùng khuyến nghị {word_range[0]:,}–{word_range[1]:,}")

    tool_path = Path(root_dir) / "adas_skills" / profile["verifier"]
    tool_status = "NOT_RUN"
    if not tool_path.is_file():
        failures.append(f"Thiếu công cụ kiểm tra: {profile['verifier']}")
    elif str(channel_key).lower() == "mafia":
        tool_ok, tool_failures, tool_warnings = _run_mafia_pipeline_check(tool_path, full_script)
        tool_status = "PASS" if tool_ok else ("NOT_RUN" if tool_ok is None else "FAIL")
        failures.extend(x for x in tool_failures if x not in failures)
        warnings.extend(x for x in tool_warnings if x not in warnings)
    else:
        tool_ok, tool_failures = _run_verifier_script(tool_path, full_script)
        tool_status = "PASS" if tool_ok else ("NOT_RUN" if tool_ok is None else "FAIL")
        failures.extend(x for x in tool_failures if x not in failures)

    return {
        "passed": not failures and tool_status == "PASS",
        "failures": failures,
        "warnings": warnings,
        "metrics": metrics,
        "chars": chars,
        "tool_status": tool_status,
    }


def plan_stage_resize(
    stages: Dict[str, str], channel_key: str, gate: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """Chọn đúng một Stage cần viết gọn hoặc mở rộng; trả về None nếu lỗi không phải độ dài."""
    profile = get_script_length_profile(channel_key)
    metrics = gate["metrics"]
    if metrics["headings"] != list(range(1, 8)):
        return None
    chars = int(gate["chars"])
    current = {k: len(normalize_script_text(v).strip()) for k, v in stages.items()}
    cfg = profile["stages"]

    for part, size in sorted(metrics["part_chars"].items()):
        if size < profile["min_part"]:
            letter = next(k for k, nums in STAGE_PARTS.items() if part in nums)
            target = min(cfg[letter]["max"], current[letter] + profile["min_part"] - size + 400)
            return {"stage": letter, "target_chars": target, "action": "expand"}

    over_words = 0
    if profile["max_words"] and metrics["words"] > profile["max_words"]:
        ratio = chars / max(1, metrics["words"])
        over_words = int((metrics["words"] - profile["target_words"]) * ratio)
    if chars > profile["total_max"] or over_words > 0:
        excess = max(chars - profile["total_target"], over_words)
        letter = max(cfg, key=lambda k: current[k] - cfg[k]["target"])
        target = max(cfg[letter]["min"], current[letter] - excess)
        if target >= current[letter]:
            return None
        return {"stage": letter, "target_chars": target, "action": "condense"}
    if chars < profile["total_min"]:
        deficit = profile["total_target"] - chars
        letter = min(cfg, key=lambda k: current[k] - cfg[k]["target"])
        target = min(cfg[letter]["max"], current[letter] + deficit)
        if target <= current[letter]:
            return None
        return {"stage": letter, "target_chars": target, "action": "expand"}
    return None


def extract_resized_stage(
    response: str,
    stage: str,
    original: str,
    target_chars: int,
    clean_func: Callable[[str], str],
    previous_chars: Optional[int] = None,
) -> Tuple[Optional[str], str]:
    """Chỉ nhận bản đủ marker, đúng nhãn Part, đúng độ dài và giữ đoạn kết của Stage.

    Nếu truyền `previous_chars`, nhận thêm bản đi được >= 40% quãng đường tới đích (không vượt qua đích quá 12%)
    để vòng biên tập kế tiếp tiếp tục thu gọn/mở rộng thay vì bỏ phí cả lượt.
    """
    match = re.search(r"@@STAGE_BEGIN\s*(.*?)\s*@@STAGE_END", response or "", re.S)
    if not match:
        return None, "Phản hồi thiếu @@STAGE_BEGIN/@@STAGE_END hoặc bị cắt giữa chừng"
    # Giao diện chat có thể gộp dòng nhãn với câu đầu tiên của Part.
    separated = re.sub(
        r"(?m)^[ \t]*\[\s*PART\s*([1-7])\s*\][ \t]+(?=\S)", r"[PART \1]\n", match.group(1)
    )
    cleaned = normalize_script_text(clean_func(separated)).strip()
    numbers, _ = split_script_parts(cleaned)
    if tuple(numbers) != STAGE_PARTS[stage]:
        return None, f"Sai nhãn Part của Stage {stage}: {numbers}"
    size = len(cleaned)
    in_window = int(target_chars * 0.88) <= size <= int(target_chars * 1.12)
    if not in_window:
        gap_before = abs(int(previous_chars or 0) - target_chars)
        gap_after = abs(size - target_chars)
        same_side = (size - target_chars) * (int(previous_chars or 0) - target_chars) > 0
        made_progress = (
            previous_chars is not None
            and gap_before > 0
            and gap_after <= gap_before * 0.6
            and (same_side or in_window)
        )
        if not made_progress:
            return None, f"Độ dài {size:,} lệch xa đích {target_chars:,}"
    old_tail = re.sub(r"\s+", " ", normalize_script_text(original).strip())[-220:]
    new_tail = re.sub(r"\s+", " ", cleaned)[-320:]
    matcher = difflib.SequenceMatcher(None, old_tail, new_tail, autojunk=False)
    if matcher.find_longest_match(0, len(old_tail), 0, len(new_tail)).size < 40:
        return None, "Bản mới không giữ đoạn kết của Stage"
    return cleaned, ""


def parse_qa_verdict(text: str) -> Optional[Dict[str, Any]]:
    """Đọc kết luận máy `QA_VERDICT: {...}` cuối cùng hợp lệ trong phản hồi."""
    normalized = (text or "").replace("“", '"').replace("”", '"')
    for raw in reversed(re.findall(r"QA_VERDICT\s*[:=]\s*(\{[^{}]*\})", normalized)):
        try:
            data = json.loads(raw)
            status = str(data.get("status", "")).strip().upper()
            if status not in ("PASS", "NEEDS_REPAIR", "FAIL"):
                continue
            return {
                "status": status,
                "score": int(data.get("score", 0)),
                "p0": int(data.get("p0", 0)),
                "p1": int(data.get("p1", 0)),
                "remaining_issues": int(data.get("remaining_issues", 0)),
            }
        except (ValueError, TypeError):
            continue
    return None


def extract_patch_ledger(text: str) -> Tuple[List[Dict[str, str]], int]:
    """Trả về các bản vá hoàn chỉnh và số khối bị cắt dở."""
    body = normalize_script_text(text)
    patches: List[Dict[str, str]] = []
    # Không phụ thuộc xuống dòng vì giao diện chat có thể gộp các dòng liền nhau.
    pattern = re.compile(
        r"@@PATCH\s+(\S+)\s+STAGE=([ABC])\s+@@OLD\s+(.*?)\s+@@NEW\s*(.*?)\s*@@END",
        re.S | re.I,
    )
    for match in pattern.finditer(body):
        patches.append(
            {
                "id": match.group(1),
                "stage": match.group(2).upper(),
                "old": match.group(3).strip(),
                "new": match.group(4).strip(),
            }
        )
    opened = len(re.findall(r"@@PATCH\b", body))
    return patches, max(0, opened - len(patches))


def apply_patch_ledger(
    stages: Dict[str, str], patches: List[Dict[str, str]]
) -> Tuple[Dict[str, str], List[str], List[str]]:
    """Chỉ thay đúng đoạn nguyên văn xuất hiện một lần; đoạn đã đạt không bị đụng tới."""
    updated = {k: normalize_script_text(v) for k, v in stages.items()}
    applied: List[str] = []
    failed: List[str] = []
    for patch in patches:
        pid, old, new = patch["id"], patch["old"], patch["new"]
        stage_text = updated.get(patch["stage"], "")
        if len(old) < _MIN_PATCH_ANCHOR_CHARS or len(old) > _MAX_PATCH_CHARS or len(new) > _MAX_PATCH_CHARS:
            failed.append(f"{pid}: độ dài đoạn sửa không hợp lệ")
            continue
        if _HEADING_LINE_RX.search(old) or _HEADING_LINE_RX.search(new) or "[PART" in new.upper():
            failed.append(f"{pid}: không được sửa nhãn PART")
            continue
        flexible = r"\s+".join(re.escape(token) for token in old.split())
        found = list(re.finditer(flexible, stage_text))
        if len(found) != 1:
            failed.append(f"{pid}: đoạn gốc xuất hiện {len(found)} lần")
            continue
        start, end = found[0].span()
        updated[patch["stage"]] = stage_text[:start] + new + stage_text[end:]
        applied.append(pid)
    return updated, applied, failed


def build_reference_block(root_dir: Path, channel_key: str, step: str) -> str:
    """Gửi bản rút gọn của tài liệu cốt lõi theo từng bước, không nhồi toàn bộ thư viện."""
    bundle = _REFERENCE_BUNDLES.get((str(channel_key).lower(), step))
    if not bundle:
        return ""
    folder, items = bundle
    blocks: List[str] = []
    for file_name, cap in items:
        path = Path(root_dir) / "adas_skills" / folder / "references" / file_name
        try:
            content = path.read_text(encoding="utf-8-sig").strip()
        except OSError:
            continue
        if len(content) > cap:
            cut = content.rfind("\n\n", 0, cap)
            content = content[: cut if cut > cap * 0.6 else cap].rstrip() + "\n[... phần sau được rút gọn ...]"
        blocks.append(f"--- TÀI LIỆU: {file_name} ---\n{content}")
    if not blocks:
        return ""
    return "\n\n========== TÀI LIỆU CỐT LÕI CỦA SKILL ==========\n" + "\n\n".join(blocks) + "\n================================================"


def build_runtime_adapter(channel_key: str, step: str) -> str:
    """Giải thích điều kiện chạy thật trong app để skill không tự nhận đã chạy công cụ."""
    profile = get_script_length_profile(channel_key)
    lines = [
        "",
        "",
        "========== QUY TẮC CHẠY TRONG ỨNG DỤNG (ƯU TIÊN CAO HƠN SKILL KHI MÂU THUẪN) ==========",
        "- Bạn đang ở ChatGPT Web, không có file cục bộ. Bỏ qua các lệnh `python scripts/...`, không tạo file và không tuyên bố đã chạy công cụ, đã lưu file hay đã khóa SHA.",
        "- Ứng dụng tự đếm ký tự, đếm từ và chạy công cụ kiểm tra sau khi nhận văn bản. Chỉ dùng các tài liệu được đính kèm trong tin nhắn này.",
        "- Ứng dụng luôn sản xuất đúng 7 PART `[PART 1]`..`[PART 7]`, viết theo 3 Stage: A = PART 1–2, B = PART 3–5, C = PART 6–7.",
        f"- Độ dài toàn kịch bản: {profile['total_min']:,}–{profile['total_max']:,} ký tự.",
    ]
    if profile.get("max_words"):
        low, high = profile["word_target_range"]
        lines.append(
            f"- Bắt buộc dưới 8.000 từ, nhắm {low:,}–{high:,} từ. Quy tắc độ dài này thay cho mọi con số 70.000–80.000 hoặc yêu cầu số Beat khác."
        )
        lines.append("- Quy tắc viết trọn trong một phản hồi không áp dụng vì ứng dụng chia 3 Stage.")
    if step == "audit":
        lines.append("- Giám khảo không viết lại cả Part hay Stage. Mọi sửa đổi phải ở dạng bản vá đúng định dạng bên dưới.")
    lines.append("=" * 86)
    return "\n".join(lines)


def build_audit_output_contract(channel_key: str, allow_patches: bool = True) -> str:
    profile = get_script_length_profile(channel_key)
    score_rule = (
        f"score >= {profile['score_min']}"
        if profile.get("score_min") is not None
        else "không còn lỗi có thể hành động"
    )
    lines = ["ĐỊNH DẠNG ĐẦU RA BẮT BUỘC:", "1. Liệt kê lỗi đã xác nhận theo mức P0/P1/P2/P3, kèm trích dẫn và nguyên nhân."]
    verdict_step = 4 if allow_patches else 3
    if allow_patches:
        lines.extend(
            [
                "2. Chỉ sửa đúng đoạn lỗi. Mỗi bản vá viết thành một khối văn bản thường, không đặt trong bảng:",
                "@@PATCH L1 STAGE=B",
                "@@OLD",
                "(chép nguyên văn đoạn cần sửa, tối thiểu 30 ký tự, xuất hiện đúng 1 lần trong Stage đó)",
                "@@NEW",
                "(đoạn thay thế)",
                "@@END",
                "3. Không chép lại đoạn đã đạt, không sửa nhãn `[PART N]`, không làm tổng độ dài ra ngoài định mức.",
            ]
        )
    else:
        lines.append("2. Đây là lượt xác minh cuối: CHỈ ĐỌC, tuyệt đối không viết bản vá hay sửa văn bản.")
    lines.extend(
        [
            f"{verdict_step}. Dòng cuối cùng của phản hồi phải đúng một dòng JSON theo mẫu:",
            'QA_VERDICT: {"status":"<PASS|NEEDS_REPAIR|FAIL>","score":<0-100>,"p0":<số lỗi P0>,"p1":<số lỗi P1>,"remaining_issues":<số lỗi còn lại>}',
            "Thay mọi phần trong dấu <> bằng giá trị thật; chấm độc lập, không mặc định là đạt.",
            f"`status` chỉ được là PASS, NEEDS_REPAIR hoặc FAIL. Chỉ ghi PASS khi {score_rule} và không còn lỗi P0/P1. `remaining_issues` là số lỗi còn lại sau các bản vá của lượt này.",
        ]
    )
    return "\n".join(lines)


def script_fingerprint(text: str) -> str:
    norm = _HEADING_LINE_RX.sub("", normalize_script_text(text))
    return hashlib.sha256(re.sub(r"\s+", " ", norm).strip().encode("utf-8")).hexdigest()


def build_pending_release_record(channel_key: str, script_text: str, reason: str) -> Dict[str, Any]:
    return {
        "schema": RELEASE_SCHEMA,
        "channel_key": channel_key,
        "release_decision": DECISION_PENDING,
        "script_fingerprint": script_fingerprint(script_text),
        "reasons": [reason],
        "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }


def decide_script_release(
    channel_key: str,
    script_text: str,
    machine_gate: Dict[str, Any],
    verdict: Optional[Dict[str, Any]],
    audit_error: str = "",
    patches_applied: int = 0,
    patches_failed: Optional[List[str]] = None,
    final_verify_ran: bool = False,
) -> Dict[str, Any]:
    profile = get_script_length_profile(channel_key)
    reasons: List[str] = list(machine_gate.get("failures") or [])
    decision = DECISION_READY

    if audit_error:
        reasons.append(f"Vòng kiểm định chưa hoàn tất: {audit_error[:180]}")
        decision = DECISION_PENDING
    elif not machine_gate.get("passed"):
        decision = DECISION_PENDING
    elif verdict is None:
        reasons.append("Không đọc được kết luận QA_VERDICT từ giám khảo")
        decision = DECISION_PENDING
    else:
        if verdict["status"] != "PASS":
            reasons.append(f"Giám khảo kết luận {verdict['status']}")
        if verdict["p0"] or verdict["p1"]:
            reasons.append(f"Còn lỗi nghiêm trọng: P0={verdict['p0']}, P1={verdict['p1']}")
        if verdict["remaining_issues"]:
            reasons.append(f"Còn {verdict['remaining_issues']} lỗi chưa xử lý")
        if profile.get("score_min") is not None and verdict["score"] < profile["score_min"]:
            reasons.append(f"Điểm {verdict['score']} dưới ngưỡng {profile['score_min']}")
        if reasons:
            decision = DECISION_NOT_READY

    return {
        "schema": RELEASE_SCHEMA,
        "channel_key": channel_key,
        "release_decision": decision,
        "script_fingerprint": script_fingerprint(script_text),
        "reasons": reasons,
        "warnings": list(machine_gate.get("warnings") or []),
        "machine_gate": {
            "passed": bool(machine_gate.get("passed")),
            "tool_status": machine_gate.get("tool_status"),
            "chars": machine_gate.get("chars"),
            "words": (machine_gate.get("metrics") or {}).get("words"),
        },
        "verdict": verdict,
        "patches_applied": patches_applied,
        "patches_failed": patches_failed or [],
        "final_verify_ran": final_verify_ran,
        "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }


def write_script_release_record(proj_dir: Path, record: Dict[str, Any]) -> None:
    target = Path(proj_dir) / RELEASE_RECORD_NAME
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_suffix(".json.tmp")
    temp.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temp, target)


def read_script_release_record(proj_dir: Path) -> Optional[Dict[str, Any]]:
    path = Path(proj_dir) / RELEASE_RECORD_NAME
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) and data.get("schema") == RELEASE_SCHEMA else None


def evaluate_render_gate(record: Optional[Dict[str, Any]], script_text: str) -> Dict[str, Any]:
    """Dự án cũ chưa có hồ sơ mới vẫn được render để không làm kẹt dữ liệu khách hàng."""
    if record is None:
        return {"allowed": True, "state": "LEGACY", "reason": ""}
    fingerprint = script_fingerprint(script_text)
    override = record.get("human_override")
    if isinstance(override, dict) and override.get("script_fingerprint") == fingerprint:
        return {"allowed": True, "state": "HUMAN_OVERRIDE", "reason": ""}
    if record.get("script_fingerprint") != fingerprint:
        return {
            "allowed": False,
            "state": "CHANGED",
            "reason": "Kịch bản đã thay đổi sau lần kiểm định",
        }
    decision = record.get("release_decision")
    if decision == DECISION_READY:
        return {"allowed": True, "state": DECISION_READY, "reason": ""}
    reasons = record.get("reasons") or []
    return {
        "allowed": False,
        "state": str(decision or DECISION_PENDING),
        "reason": "; ".join(str(x) for x in reasons[:3]) or "Chưa có kết luận kiểm định",
    }


def apply_human_override(proj_dir: Path, script_text: str) -> Optional[Dict[str, Any]]:
    """Ghi nhận người dùng chủ động cho render đúng phiên bản kịch bản này."""
    record = read_script_release_record(proj_dir)
    if record is None:
        return None
    record["human_override"] = {
        "script_fingerprint": script_fingerprint(script_text),
        "at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    write_script_release_record(proj_dir, record)
    return record
