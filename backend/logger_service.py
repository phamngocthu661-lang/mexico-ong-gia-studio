import sys

sys.modules["backend.license_manager"] = sys.modules[__name__]
sys.modules["backend.updater_service"] = sys.modules[__name__]
# -*- coding: utf-8 -*-
"""
HỆ THỐNG GHI LOG & CHẨN ĐOÁN LỖI TOÀN DIỆN (SYSTEM LOGGER & DIAGNOSTICS)
========================================================================
Ghi nhận toàn bộ hoạt động và lỗi của:
1. Khởi động Server (main.py / FastAPI / Uvicorn) -> logs/server_startup.log
2. Toàn bộ tiến trình chạy Đa luồng Kịch bản, Chrome CDP, Voice AI, Stock, FFmpeg Render -> logs/system_runtime.log
3. Riêng các lỗi / nguyên nhân bị dừng -> logs/error_diagnostic.log
4. Cung cấp bộ đệm Ring-Buffer trong RAM để hiển thị thời gian thực trên giao diện Web/Desktop.
"""

import importlib.util
import os
import subprocess
import sys
import threading
import time
import traceback
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

ROOT_DIR = Path(__file__).resolve().parent.parent
if ROOT_DIR.name.lower() == "app":
    ROOT_DIR = ROOT_DIR.parent
elif not (ROOT_DIR / "bin").exists() and (ROOT_DIR.parent / "bin").exists():
    ROOT_DIR = ROOT_DIR.parent

LOGS_DIR = ROOT_DIR / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

RUNTIME_LOG_FILE = LOGS_DIR / "system_runtime.log"
ERROR_LOG_FILE = LOGS_DIR / "error_diagnostic.log"
STARTUP_LOG_FILE = LOGS_DIR / "server_startup.log"


class SystemLogger:
    _instance = None
    _lock = threading.Lock()

    def __init__(self):
        self.entries: List[Dict[str, Any]] = []
        self.max_entries = 600
        self.file_lock = threading.Lock()
        self.subscribers: List[Callable[[Dict[str, Any]], None]] = []
        self._load_recent_logs_from_disk()

    def subscribe(self, cb: Callable[[Dict[str, Any]], None]):
        if cb not in self.subscribers:
            self.subscribers.append(cb)

    @classmethod
    def get_instance(cls) -> "SystemLogger":
        with cls._lock:
            if cls._instance is None:
                cls._instance = SystemLogger()
            return cls._instance

    def _load_recent_logs_from_disk(self):
        """Khôi phục 150 dòng log gần nhất từ ổ cứng khi khởi động lại app để không mất dấu lỗi cũ."""
        if not RUNTIME_LOG_FILE.exists():
            return
        try:
            lines = RUNTIME_LOG_FILE.read_text(
                encoding="utf-8", errors="replace"
            ).splitlines()[-150:]
            for ln in lines:
                ln = ln.strip()
                if not ln:
                    continue
                level = (
                    "ERROR"
                    if "[ERROR]" in ln or "❌" in ln
                    else ("WARN" if "[WARN]" in ln or "⚠️" in ln else "INFO")
                )
                cat = "SYSTEM"
                for c_candidate in (
                    "SCRIPT",
                    "VOICE",
                    "RENDER",
                    "CHROME",
                    "SERVER",
                    "STOCK",
                ):
                    if f"[{c_candidate}]" in ln:
                        cat = c_candidate
                        break
                self.entries.append(
                    {
                        "ts": ln[1:20]
                        if ln.startswith("[20") and len(ln) > 21
                        else time.strftime("%Y-%m-%d %H:%M:%S"),
                        "timestamp": ln[1:20]
                        if ln.startswith("[20") and len(ln) > 21
                        else time.strftime("%Y-%m-%d %H:%M:%S"),
                        "level": level,
                        "category": cat,
                        "project_id": "",
                        "message": ln,
                        "detail": "",
                    }
                )
        except Exception:
            pass

    def _trim_log_file_if_huge(self, file_path: Path, max_bytes: int = 5 * 1024 * 1024):
        try:
            if file_path.exists() and file_path.stat().st_size > max_bytes:
                content = file_path.read_text(encoding="utf-8", errors="replace")
                kept = "\n".join(content.splitlines()[-2500:]) + "\n"
                file_path.write_text(kept, encoding="utf-8")
        except Exception:
            pass

    def log(
        self,
        message: str,
        level: str = "INFO",
        category: str = "SYSTEM",
        project_id: str = "",
        exc: Optional[BaseException] = None,
        detail: str = "",
    ):
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        lvl = (level or "INFO").upper()
        cat = (category or "SYSTEM").upper()
        proj_tag = f"[{project_id}] " if project_id else ""

        tb_str = ""
        if exc is not None:
            tb_str = "".join(
                traceback.format_exception(type(exc), exc, exc.__traceback__)
            ).strip()
        if detail:
            tb_str = f"{detail}\n{tb_str}".strip() if tb_str else detail

        formatted_line = f"[{ts}] [{lvl}] [{cat}] {proj_tag}{message}"

        entry = {
            "ts": ts,
            "timestamp": ts,
            "level": lvl,
            "category": cat,
            "project_id": project_id or "",
            "message": f"{proj_tag}{message}",
            "detail": tb_str,
            "raw_line": formatted_line,
        }

        with self.file_lock:
            self.entries.append(entry)
            if len(self.entries) > self.max_entries:
                self.entries = self.entries[-self.max_entries :]

            try:
                self._trim_log_file_if_huge(RUNTIME_LOG_FILE)
                with open(RUNTIME_LOG_FILE, "a", encoding="utf-8") as f:
                    f.write(formatted_line + "\n")
                    if tb_str:
                        for tbl in tb_str.splitlines():
                            f.write(f"    | {tbl}\n")

                if lvl in ("ERROR", "CRITICAL", "WARN", "WARNING") or "❌" in message:
                    self._trim_log_file_if_huge(ERROR_LOG_FILE)
                    with open(ERROR_LOG_FILE, "a", encoding="utf-8") as ef:
                        ef.write(formatted_line + "\n")
                        if tb_str:
                            for tbl in tb_str.splitlines():
                                ef.write(f"    | {tbl}\n")
                            ef.write("-" * 72 + "\n")

                if cat == "SERVER" or cat == "STARTUP":
                    with open(STARTUP_LOG_FILE, "a", encoding="utf-8") as sf:
                        sf.write(formatted_line + "\n")
                        if tb_str:
                            sf.write(tb_str + "\n")
            except Exception:
                pass

        for cb in list(self.subscribers):
            try:
                cb({"type": "sys_log", "entry": entry})
            except Exception:
                pass

    def get_logs(
        self,
        limit: int = 200,
        level_filter: Optional[str] = None,
        category_filter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        with self.file_lock:
            items = list(self.entries)

        if level_filter and level_filter.upper() != "ALL":
            lf = level_filter.upper()
            if lf == "ERROR":
                items = [
                    x
                    for x in items
                    if x["level"] in ("ERROR", "CRITICAL", "WARN", "WARNING")
                    or "❌" in x["message"]
                    or "⚠️" in x["message"]
                ]
            else:
                items = [x for x in items if x["level"] == lf]

        if category_filter and category_filter.upper() != "ALL":
            cf = category_filter.upper()
            if cf == "VIDEO":
                items = [
                    x
                    for x in items
                    if x["category"] in ("VIDEO", "VOICE", "RENDER", "STOCK")
                ]
            else:
                items = [x for x in items if x["category"] == cf]

        return items[-max(1, min(limit, 600)) :]

    def get_recent_logs(
        self,
        limit: int = 200,
        level_filter: Optional[str] = None,
        category_filter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        return self.get_logs(
            limit=limit, level_filter=level_filter, category_filter=category_filter
        )

    def clear_logs(self):
        with self.file_lock:
            self.entries.clear()
            for fp in (RUNTIME_LOG_FILE, ERROR_LOG_FILE):
                try:
                    if fp.exists():
                        fp.write_text("", encoding="utf-8")
                except Exception:
                    pass
        self.log(
            "Đã xóa trắng lịch sử nhật ký theo yêu cầu người dùng.",
            level="INFO",
            category="SYSTEM",
        )

    def clear_memory_logs(self):
        self.clear_logs()

    def get_log_file_paths(self) -> Dict[str, str]:
        return {
            "logs_dir": str(LOGS_DIR),
            "runtime_log_file": str(RUNTIME_LOG_FILE),
            "error_log_file": str(ERROR_LOG_FILE),
            "startup_log_file": str(STARTUP_LOG_FILE),
        }


_KNOWN_CATEGORIES = {
    "SYSTEM",
    "SERVER",
    "STARTUP",
    "SCRIPT",
    "VIDEO",
    "VOICE",
    "RENDER",
    "STOCK",
    "CHROME",
}


def _normalize_cat_and_msg(arg1: str, arg2: str = "SYSTEM") -> tuple[str, str]:
    """Hỗ trợ cả 2 kiểu gọi: log_info(msg, category) hoặc log_info(category, msg)."""
    a1 = (arg1 or "").strip()
    a2 = (arg2 or "SYSTEM").strip()
    if a1.upper() in _KNOWN_CATEGORIES and a2.upper() not in _KNOWN_CATEGORIES:
        return a2, a1.upper()
    return a1, (a2.upper() if a2.upper() in _KNOWN_CATEGORIES else "SYSTEM")


def get_logger(root_dir: Optional[Path] = None) -> SystemLogger:
    return SystemLogger.get_instance()


def log_info(
    arg1: str,
    arg2: str = "SYSTEM",
    category: Optional[str] = None,
    project_id: str = "",
    detail: str = "",
):
    msg, cat = _normalize_cat_and_msg(arg1, category or arg2)
    SystemLogger.get_instance().log(
        msg, level="INFO", category=cat, project_id=project_id, detail=detail
    )


def log_warn(
    arg1: str,
    arg2: str = "SYSTEM",
    category: Optional[str] = None,
    project_id: str = "",
    detail: str = "",
):
    msg, cat = _normalize_cat_and_msg(arg1, category or arg2)
    SystemLogger.get_instance().log(
        msg, level="WARN", category=cat, project_id=project_id, detail=detail
    )


def log_error(
    arg1: str,
    arg2: str = "SYSTEM",
    category: Optional[str] = None,
    project_id: str = "",
    exc: Optional[BaseException] = None,
    detail: str = "",
    include_trace: bool = False,
):
    msg, cat = _normalize_cat_and_msg(arg1, category or arg2)
    if include_trace and exc is None:
        tb_cur = traceback.format_exc()
        if tb_cur and "NoneType: None" not in tb_cur:
            detail = f"{detail}\n{tb_cur}".strip() if detail else tb_cur
    SystemLogger.get_instance().log(
        msg, level="ERROR", category=cat, project_id=project_id, exc=exc, detail=detail
    )


REQUIRED_PYTHON_LIBRARIES = [
    ("torch", "torch", "PyTorch (Nhân AI & GPU CUDA)"),
    ("torchaudio", "torchaudio", "TorchAudio (Xử lý âm thanh GPU)"),
    ("transformers", "transformers", "Transformers (Model ngôn ngữ & Voice)"),
    ("accelerate", "accelerate", "Accelerate (Tối ưu nạp Model GPU)"),
    ("safetensors", "safetensors", "SafeTensors (Đọc trọng số Model)"),
    ("huggingface_hub", "huggingface-hub", "HuggingFace Hub (Tải Model AI)"),
    ("soundfile", "soundfile", "SoundFile (Xuất file WAV chất lượng cao)"),
    ("scipy", "scipy", "SciPy (Xử lý tín hiệu âm thanh)"),
    ("numpy", "numpy", "NumPy (Tính toán ma trận)"),
    ("einops", "einops", "Einops (Biến đổi Tensor cho VoiceStudio)"),
    ("fastapi", "fastapi", "FastAPI (Máy chủ Backend)"),
    ("uvicorn", "uvicorn", "Uvicorn (ASGI Server)"),
    ("websockets", "websockets", "WebSockets (Đồng bộ Log & Chrome CDP)"),
    ("requests", "requests", "Requests (Giao tiếp HTTP)"),
    ("webview", "pywebview", "PyWebView (Giao diện cửa sổ Desktop)"),
]


def _detect_nvidia_hardware() -> Dict[str, Any]:
    """Kiểm tra phần cứng Card rời NVIDIA và Driver qua nvidia-smi."""
    info = {
        "has_nvidia_gpu": False,
        "gpu_name": "",
        "driver_version": "",
        "vram_total_mb": 0,
        "raw_error": "",
    }
    try:
        res = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,driver_version,memory.total",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=5,
            encoding="utf-8",
            errors="replace",
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        if res.returncode == 0 and res.stdout.strip():
            first_line = res.stdout.strip().splitlines()[0]
            parts = [p.strip() for p in first_line.split(",")]
            info["has_nvidia_gpu"] = True
            if len(parts) >= 1:
                info["gpu_name"] = parts[0]
            if len(parts) >= 2:
                info["driver_version"] = parts[1]
            if len(parts) >= 3:
                try:
                    info["vram_total_mb"] = int(float(parts[2]))
                except Exception:
                    pass
    except FileNotFoundError:
        info["raw_error"] = (
            "Không tìm thấy nvidia-smi (Chưa cài NVIDIA Driver hoặc máy không có card NVIDIA)."
        )
    except Exception as e:
        info["raw_error"] = str(e)
    return info


def _check_ffmpeg_nvenc_support(ffmpeg_bin: Path) -> bool:
    """Kiểm tra xem FFmpeg có hỗ trợ bộ mã hóa phần cứng h264_nvenc hay không."""
    if not ffmpeg_bin.exists():
        return False
    try:
        res = subprocess.run(
            [str(ffmpeg_bin), "-hide_banner", "-encoders"],
            capture_output=True,
            text=True,
            timeout=5,
            encoding="utf-8",
            errors="replace",
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        return "h264_nvenc" in (res.stdout or "")
    except Exception:
        return False


def run_system_diagnostics(
    root_dir: Optional[Path] = None, pipeline: Any = None, adas_engine: Any = None
) -> Dict[str, Any]:
    """
    Chạy kiểm tra sức khỏe toàn diện 7 hạng mục (bao gồm Phần cứng GPU, Driver NVIDIA, CUDA, Thư viện Python, FFmpeg NVENC, Model Voice, Kho Stock, Chrome):
    Thông báo rõ những thành phần nào máy khách hàng CHƯA CÓ để yêu cầu tải về hoặc bấm cài đặt tự động.
    """
    base = Path(root_dir) if root_dir else ROOT_DIR
    if base.name.lower() == "app":
        base = base.parent
    elif not (base / "bin").exists() and (base.parent / "bin").exists():
        base = base.parent

    checks: List[Dict[str, Any]] = []
    missing_requirements: List[Dict[str, str]] = []
    overall_ok = True

    # 1. Kiểm tra Phần cứng Card đồ họa NVIDIA & Driver + CUDA PyTorch
    nv_hw = _detect_nvidia_hardware()
    cuda_ok = False
    torch_ver = "Chưa cài"
    cuda_ver = "Không có"
    cudnn_ok = False
    gpu_name = nv_hw.get("gpu_name") or "CPU Mode"

    try:
        import torch

        torch_ver = getattr(torch, "__version__", "Đã cài")
        cuda_ok = bool(torch.cuda.is_available())
        cuda_ver = getattr(torch.version, "cuda", None) or "CPU-only"
        if cuda_ok:
            gpu_name = torch.cuda.get_device_name(0)
            cudnn_ok = bool(torch.backends.cudnn.is_available())
    except Exception as e:
        torch_ver = f"Lỗi ({e})"

    if cuda_ok:
        vram_gb = (
            round(nv_hw.get("vram_total_mb", 0) / 1024.0, 1)
            if nv_hw.get("vram_total_mb")
            else "?"
        )
        checks.append(
            {
                "name": "1. Tối Ưu Hóa GPU & Thư Viện NVIDIA CUDA",
                "ok": True,
                "detail": (
                    f"✅ ĐÃ BẬT TĂNG TỐC GPU: {gpu_name} ({vram_gb} GB VRAM) | "
                    f"NVIDIA Driver: {nv_hw.get('driver_version', 'OK')} | "
                    f"PyTorch: {torch_ver} (CUDA {cuda_ver}, cuDNN: {'Bật' if cudnn_ok else 'Tắt'})"
                ),
            }
        )
    elif nv_hw.get("has_nvidia_gpu"):
        overall_ok = False
        missing_requirements.append(
            {
                "id": "pytorch_cuda",
                "title": f"Thư viện PyTorch CUDA cho Card rời {nv_hw.get('gpu_name')}",
                "reason": f"Máy của bạn có Card NVIDIA ({nv_hw.get('gpu_name')}, Driver {nv_hw.get('driver_version')}) nhưng Python đang chạy PyTorch bản thường ({torch_ver}) chưa có CUDA nên chưa tối ưu được GPU!",
                "action_label": "⚡ Bấm nút [Tự Động Cài Thư Viện Thiếu & CUDA] bên dưới hoặc tải CUDA PyTorch",
                "download_url": "https://pytorch.org/get-started/locally/",
                "command": f'"{sys.executable}" -m pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu124 --upgrade',
            }
        )
        checks.append(
            {
                "name": "1. Tối Ưu Hóa GPU & Thư Viện NVIDIA CUDA",
                "ok": False,
                "detail": (
                    f"⚠️ PHÁT HIỆN CARD RỜI {nv_hw.get('gpu_name')} (Driver {nv_hw.get('driver_version')}) NHƯNG THIẾU THƯ VIỆN PYTORCH CUDA! "
                    f"Hiện đang chạy {torch_ver} (Chế độ CPU chậm). Vui lòng bấm nút [⚡ Cài Đặt CUDA & Thư Viện Thiếu] để kích hoạt tối ưu GPU!"
                ),
            }
        )
    else:
        missing_requirements.append(
            {
                "id": "nvidia_driver_cuda",
                "title": "Driver Card Đồ Họa NVIDIA & CUDA Toolkit",
                "reason": "Không phát hiện Card đồ họa rời NVIDIA (hoặc máy chưa cài đặt NVIDIA Driver). Hệ thống sẽ chạy bằng CPU (tốc độ tạo Voice và Render sẽ chậm hơn GPU).",
                "action_label": "Nếu máy có Card rời NVIDIA, vui lòng tải và cài đặt NVIDIA Driver + CUDA",
                "download_url": "https://www.nvidia.com/Download/index.aspx",
                "command": "",
            }
        )
        checks.append(
            {
                "name": "1. Tối Ưu Hóa GPU & Thư Viện NVIDIA CUDA",
                "ok": False,
                "detail": (
                    "⚠️ CHƯA PHÁT HIỆN GPU NVIDIA / DRIVER CUDA: Máy đang chạy chế độ CPU. "
                    "Nếu máy có card rời NVIDIA, hãy tải và cài đặt NVIDIA Game Ready / Studio Driver tại https://www.nvidia.com/Download/index.aspx để mở khóa tăng tốc GPU!"
                ),
            }
        )

    # 2. Kiểm tra đầy đủ 16 Thư viện Python cần thiết để chạy Tool
    installed_libs: List[str] = []
    missing_libs: List[Dict[str, str]] = []
    for mod_name, pip_name, desc in REQUIRED_PYTHON_LIBRARIES:
        spec = importlib.util.find_spec(mod_name)
        if spec is not None:
            installed_libs.append(mod_name)
        else:
            missing_libs.append({"module": mod_name, "pip": pip_name, "desc": desc})

    if not missing_libs:
        checks.append(
            {
                "name": f"2. Thư Viện Python Hệ Thống ({len(installed_libs)}/{len(REQUIRED_PYTHON_LIBRARIES)} thư viện)",
                "ok": True,
                "detail": f"✅ Đầy đủ 100% ({len(installed_libs)}/{len(REQUIRED_PYTHON_LIBRARIES)}) thư viện bắt buộc: {', '.join(installed_libs[:10])}...",
            }
        )
    else:
        overall_ok = False
        missing_names = ", ".join([f"{x['pip']} ({x['desc']})" for x in missing_libs])
        pip_pkgs = " ".join([x["pip"] for x in missing_libs])
        missing_requirements.append(
            {
                "id": "missing_python_libs",
                "title": f"Thiếu {len(missing_libs)} thư viện Python bắt buộc",
                "reason": f"Máy chưa có các thư viện: {missing_names}",
                "action_label": "Bấm nút [⚡ Cài Đặt CUDA & Thư Viện Thiếu] để tải tự động",
                "download_url": "https://pypi.org/",
                "command": f'"{sys.executable}" -m pip install {pip_pkgs}',
            }
        )
        checks.append(
            {
                "name": f"2. Thư Viện Python Hệ Thống ({len(installed_libs)}/{len(REQUIRED_PYTHON_LIBRARIES)} thư viện)",
                "ok": False,
                "detail": f"❌ THIẾU {len(missing_libs)} THƯ VIỆN CẦN TẢI VỀ: {missing_names}",
            }
        )

    # 3. Kiểm tra FFmpeg & FFprobe & Mã hóa GPU h264_nvenc
    ffmpeg_bin = base / "bin" / "ffmpeg.exe"
    ffprobe_bin = base / "bin" / "ffprobe.exe"
    ffmpeg_ok = ffmpeg_bin.exists() and ffprobe_bin.exists()
    nvenc_ok = _check_ffmpeg_nvenc_support(ffmpeg_bin) if ffmpeg_ok else False
    if not ffmpeg_ok:
        overall_ok = False
        missing_requirements.append(
            {
                "id": "ffmpeg_bin",
                "title": "Bộ công cụ Render Video FFmpeg & FFprobe",
                "reason": f"Thiếu file thực thi ffmpeg.exe hoặc ffprobe.exe trong thư mục {base / 'bin'}.",
                "action_label": "Tải FFmpeg Windows Build (gyan.dev / BtbN) và giải nén vào thư mục bin/",
                "download_url": "https://github.com/BtbN/FFmpeg-Builds/releases",
                "command": "",
            }
        )
    checks.append(
        {
            "name": "3. Bộ Kết Xuất Video (FFmpeg & Mã Hóa GPU NVENC)",
            "ok": ffmpeg_ok,
            "detail": (
                f"✅ Đã sẵn sàng tại {base / 'bin'} | Hỗ trợ Render GPU (h264_nvenc): {'🟢 Có' if nvenc_ok else '🟡 Không'}"
                if ffmpeg_ok
                else f"❌ Thiếu ffmpeg.exe hoặc ffprobe.exe trong {base / 'bin'}! Vui lòng tải về bổ sung."
            ),
        }
    )

    # 4. Kiểm tra Bộ Clone Giọng Đọc AI (VoiceStudio — Kho_Voice)
    kho_voices_cnt = 0
    try:
        from .voice_service import list_kho_voices, load_voice_config

        voices_list = list_kho_voices(base)
        kho_voices_cnt = len(voices_list)
        v_cfg = load_voice_config(base)
        sel_voice = v_cfg.get("selected_preset_id", "04_mx_ong_gia_padre_implacable")
        vv_detail = f"Kho_Voice: {kho_voices_cnt} giọng mẫu (Đang chọn: {sel_voice} | Speed={v_cfg.get('speedScale', 1.0)}x)"
    except Exception as e:
        vv_detail = f"Lỗi kiểm tra Kho_Voice: {e}"

    model_dir = base / "pretrained_models" / "OmniVoice"
    main_w = model_dir / "model.safetensors"
    tok_w = model_dir / "audio_tokenizer" / "model.safetensors"
    weights_ready = (
        main_w.exists() and main_w.stat().st_size > 1_000_000_000 and tok_w.exists()
    )
    voice_ok = kho_voices_cnt > 0 or weights_ready
    checks.append(
        {
            "name": "4. Bộ Clone Giọng Đọc AI (VoiceStudio — Kho_Voice)",
            "ok": voice_ok,
            "detail": (
                f"✅ {vv_detail} | VoiceStudio Clone: {'Đã sẵn sàng' if weights_ready else 'Tự tải khi cần'}"
                if voice_ok
                else f"⚠️ {vv_detail} | Chưa tải sẵn Model VoiceStudio tại {model_dir}"
            ),
        }
    )

    # 5. Kiểm tra Kho Video Stock (STOOK)
    try:
        if pipeline and hasattr(pipeline, "stock_manager"):
            st_info = pipeline.stock_manager.get_all_stocks()
            avail_cnt = st_info.get("available_count", 0)
            avail_h = st_info.get("available_raw_hours", 0.0)
            stook_path = st_info.get("stook_dir", "")
            stock_ok = avail_cnt > 0
            checks.append(
                {
                    "name": "5. Kho Video Nền 720p (STOOK)",
                    "ok": stock_ok,
                    "detail": (
                        f"✅ Sẵn sàng {avail_cnt} video khả dụng ({avail_h:.1f} giờ) tại {stook_path}"
                        if stock_ok
                        else f"⚠️ Kho STOOK ({stook_path}) đang trống (0 video khả dụng) — Hệ thống sẽ tự động tải 720p từ YouTube khi chạy!"
                    ),
                }
            )
    except Exception as e:
        checks.append(
            {
                "name": "5. Kho Video Nền 720p (STOOK)",
                "ok": False,
                "detail": f"❌ Lỗi đọc kho Stock: {e}",
            }
        )

    # 6. Kiểm tra 3 Tài khoản Chrome ChatGPT Web
    try:
        from .adas_script_engine import check_all_web_accounts_status

        acc_st = check_all_web_accounts_status(force_refresh=False).get("accounts", {})
        logged_in_labels = [
            v.get("label", k) for k, v in acc_st.items() if v.get("logged_in")
        ]
        open_labels = [
            v.get("label", k) for k, v in acc_st.items() if v.get("browser_open")
        ]
        checks.append(
            {
                "name": "6. Trạm Chrome ChatGPT Web (3 Tài Khoản)",
                "ok": len(logged_in_labels) > 0,
                "detail": (
                    f"✅ Đã đăng nhập {len(logged_in_labels)}/3 tài khoản: {', '.join(logged_in_labels)}"
                    if logged_in_labels
                    else (
                        f"⚠️ Đang mở {len(open_labels)} trình duyệt nhưng chưa đăng nhập ChatGPT!"
                        if open_labels
                        else "⚪ Chưa mở trình duyệt Chrome ChatGPT (Chỉ cần mở khi viết kịch bản mới; chạy Voice/Render không cần mở Chrome)."
                    )
                ),
            }
        )
    except Exception as e:
        checks.append(
            {
                "name": "6. Trạm Chrome ChatGPT Web",
                "ok": False,
                "detail": f"Lỗi kiểm tra Chrome: {e}",
            }
        )

    # 7. Kiểm tra các Dự án đã có Kịch bản chờ Render hoặc bị lỗi
    script_ready_list = []
    projects_ready_for_video = []
    video_done_list = []
    error_list = []
    try:
        if adas_engine:
            adas_engine._sync_projects_disk_state()
            ideas = adas_engine.load_saved_ideas()
            for it in ideas:
                mid = it.get("ma_id", "")
                has_script, _, sc_chars = adas_engine.has_valid_script_on_disk(mid)
                has_mp4, _, _ = adas_engine.has_valid_video_mp4_on_disk(
                    mid, sc_chars=sc_chars
                )
                if has_mp4:
                    video_done_list.append(mid)
                elif has_script:
                    script_ready_list.append(mid)
                    projects_ready_for_video.append(
                        {"ma_id": mid, "pure_chars": sc_chars}
                    )
                if "ERROR" in str(it.get("status", "")).upper() and not has_mp4:
                    error_list.append(f"{mid} ({it.get('current_step', '')})")
    except Exception:
        pass

    checks.append(
        {
            "name": "7. Trạng Thái Kho Dự Án & Hàng Đợi Render",
            "ok": len(error_list) == 0,
            "detail": (
                f"🎬 Đã xuất MP4: {len(video_done_list)} mã | "
                f"📝 Đã có sẵn Kịch bản (Chờ Render MP4): {len(script_ready_list)} mã ({', '.join(script_ready_list[:8]) or 'Không có'}) | "
                f"❌ Dự án báo lỗi gần nhất: {len(error_list)} ({'; '.join(error_list[:3]) or 'Không có lỗi'})"
            ),
        }
    )

    for c in checks:
        c["status"] = (
            "OK"
            if c.get("ok")
            else (
                "WARN"
                if "⚠️" in str(c.get("detail", "")) or "⚪" in str(c.get("detail", ""))
                else "ERROR"
            )
        )

    overall_status = (
        "OK"
        if all(c["status"] == "OK" for c in checks)
        else ("ERROR" if any(c["status"] == "ERROR" for c in checks) else "WARN")
    )
    ts_now = time.strftime("%Y-%m-%d %H:%M:%S")

    log_info(
        f"🔍 Chẩn Đoán Hệ Thống & GPU: GPU={'CUDA (' + gpu_name + ')' if cuda_ok else 'Chưa có CUDA'}, "
        f"Thư viện={len(installed_libs)}/{len(REQUIRED_PYTHON_LIBRARIES)}, "
        f"MP4={len(video_done_list)}, Chờ Render={len(script_ready_list)}",
        category="SYSTEM",
    )

    return {
        "overall_ok": overall_ok,
        "overall_status": overall_status,
        "checked_at": ts_now,
        "timestamp": ts_now,
        "logs_dir": str(LOGS_DIR),
        "runtime_log_file": str(RUNTIME_LOG_FILE),
        "error_log_file": str(ERROR_LOG_FILE),
        "startup_log_file": str(STARTUP_LOG_FILE),
        "checks": checks,
        "gpu_hardware": nv_hw,
        "cuda_available": cuda_ok,
        "torch_version": torch_ver,
        "cuda_version": cuda_ver,
        "missing_libs": missing_libs,
        "missing_requirements": missing_requirements,
        "script_ready_ids": script_ready_list,
        "projects_ready_for_video": projects_ready_for_video,
        "video_done_ids": video_done_list,
        "error_projects": error_list,
    }


def install_missing_libraries_async(install_cuda: bool = True) -> Dict[str, Any]:
    """
    Tự động tải và cài đặt các thư viện Python còn thiếu và/hoặc bản PyTorch CUDA tối ưu GPU
    trong luồng nền, đồng thời đẩy thông báo tiến trình trực tiếp lên bảng Nhật Ký Hệ Thống (System Logs).
    """
    missing_pkgs: List[str] = []
    for mod_name, pip_name, _ in REQUIRED_PYTHON_LIBRARIES:
        if importlib.util.find_spec(mod_name) is None:
            missing_pkgs.append(pip_name)

    nv_hw = _detect_nvidia_hardware()
    need_cuda_torch = False
    try:
        import torch

        if nv_hw.get("has_nvidia_gpu") and not torch.cuda.is_available():
            need_cuda_torch = True
    except Exception:
        need_cuda_torch = bool(nv_hw.get("has_nvidia_gpu"))

    if not missing_pkgs and not (install_cuda and need_cuda_torch):
        log_info(
            "SYSTEM",
            "✅ Máy đã cài đặt đầy đủ 100% thư viện Python và tối ưu GPU CUDA, không cần tải thêm!",
        )
        return {
            "started": False,
            "message": "Máy đã có đầy đủ thư viện và tối ưu GPU CUDA!",
        }

    def _worker():
        try:
            if missing_pkgs:
                log_info(
                    "SYSTEM",
                    f"⏳ Đang tự động tải và cài đặt {len(missing_pkgs)} thư viện thiếu: {', '.join(missing_pkgs)}...",
                )
                cmd = [sys.executable, "-m", "pip", "install", *missing_pkgs]
                proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                )
                if proc.stdout:
                    for line in proc.stdout:
                        ln = line.strip()
                        if ln:
                            log_info("SYSTEM", f"[PIP] {ln}")
                proc.wait()
                if proc.returncode == 0:
                    log_info(
                        "SYSTEM",
                        f"✅ Đã cài đặt xong các thư viện: {', '.join(missing_pkgs)}",
                    )
                else:
                    log_error(
                        "SYSTEM", f"❌ Lỗi khi cài thư viện (Mã lỗi {proc.returncode})."
                    )

            if install_cuda and need_cuda_torch:
                log_info(
                    "SYSTEM",
                    "🚀 Đang tải và cài đặt bộ thư viện PyTorch CUDA 12.4 để tối ưu GPU NVIDIA (Dung lượng ~2.4GB, vui lòng đợi)...",
                )
                cmd_cuda = [
                    sys.executable,
                    "-m",
                    "pip",
                    "install",
                    "torch",
                    "torchaudio",
                    "--index-url",
                    "https://download.pytorch.org/whl/cu124",
                    "--upgrade",
                ]
                proc_c = subprocess.Popen(
                    cmd_cuda,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                )
                if proc_c.stdout:
                    for line in proc_c.stdout:
                        ln = line.strip()
                        if ln:
                            log_info("SYSTEM", f"[CUDA-PIP] {ln}")
                proc_c.wait()
                if proc_c.returncode == 0:
                    log_info(
                        "SYSTEM",
                        "✅ Đã cài đặt thành công PyTorch CUDA! Vui lòng khởi động lại ứng dụng để nhận GPU CUDA.",
                    )
                else:
                    log_error(
                        "SYSTEM",
                        f"❌ Cài đặt PyTorch CUDA thất bại (Mã lỗi {proc_c.returncode}).",
                    )
        except Exception as e:
            log_error(
                "SYSTEM", f"❌ Lỗi trong quá trình tự động cài đặt thư viện: {e}", exc=e
            )

    threading.Thread(target=_worker, daemon=True).start()
    return {
        "started": True,
        "message": "Đã bắt đầu tải và cài đặt thư viện thiếu / CUDA trong nền. Xem tiến trình tại bảng Nhật Ký Hệ Thống!",
    }


# ==============================================================================
# MODEL PHẦN 2: QUẢN LÝ BẢN QUYỀN KHÓA MÁY (LICENSE MANAGER)
# ==============================================================================

import datetime
import hashlib
import hmac
import json
import re
import secrets
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

# Khóa bí mật HMAC-SHA256 dùng riêng cho Mexico Ông Già Studio (Tách biệt 100% với Key Nhật)
_MASTER_SECRET = b"MEXICO_ONG_GIA_STUDIO_2026_MASTER_SECRET_KEY_#8899001122_PADRE_MX"
PLAN_LABELS = {
    "D07": "Dùng Thử 7 Ngày",
    "M01": "Gói 1 Tháng (30 Ngày)",
    "M03": "Gói 3 Tháng (90 Ngày)",
    "M06": "Gói 6 Tháng (180 Ngày)",
    "Y01": "Gói 1 Năm (365 Ngày)",
    "Y02": "Gói 2 Năm (730 Ngày)",
    "Y99": "Gói Vĩnh Viễn (Trọn Đời)",
    "VIP": "Gói Tùy Chỉnh Thời Hạn",
}


class LicenseManager:
    def __init__(self, root_dir: Optional[Path] = None):
        if root_dir:
            self.root_dir = Path(root_dir)
        else:
            p = Path(__file__).resolve().parent.parent
            self.root_dir = p.parent if p.name == "app" else p

        self.license_file = self.root_dir / "config" / "license.json"
        local_appdata = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
        self.backup_dir = Path(local_appdata) / "MexicoOngGiaStudio"
        try:
            self.backup_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
        self.backup_file = self.backup_dir / "license_state.json"
        self.hwid = get_machine_hwid()
        self.hwid_tag = normalize_hwid_tag(self.hwid)

    def _load_saved_data(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {}
        app_lic = self.root_dir / "license.json"
        for fpath in [self.license_file, self.backup_file, app_lic]:
            if fpath.exists():
                try:
                    with open(fpath, "r", encoding="utf-8-sig") as f:
                        d = json.load(f)
                        if isinstance(d, dict) and d.get("license_key"):
                            prev_ts = int(data.get("last_seen_ts", 0) or 0)
                            cur_ts = int(d.get("last_seen_ts", 0) or 0)
                            if not data or cur_ts >= prev_ts:
                                data = dict(d)
                                data["last_seen_ts"] = max(prev_ts, cur_ts)
                except Exception:
                    pass
        return data

    def _save_data(self, data: Dict[str, Any]):
        targets = [self.license_file, self.backup_file]
        if (self.root_dir / "app").exists():
            targets.append(self.root_dir / "app" / "license.json")
        for fpath in targets:
            try:
                with open(fpath, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            except Exception:
                pass

    def verify_key_string(
        self, key_str: str, check_online_time: bool = True
    ) -> Dict[str, Any]:
        """Kiểm tra tính hợp lệ, chữ ký số, mã máy HWID và thời hạn của một License Key Mexico Ông Già."""
        if not key_str or not key_str.strip():
            return {
                "valid": False,
                "status": "missing",
                "hwid": self.hwid,
                "message": "Chưa kích hoạt Key bản quyền. Vui lòng nhập Key Mexico Ông Già Studio để mở khóa ứng dụng.",
            }

        clean_key = key_str.strip().upper()
        pattern = (
            r"^MEXICO-(\d{8})-([A-Z0-9]{3})-([A-Z0-9]{8})-([A-Z0-9]{4})-([A-Z0-9]{12})$"
        )
        m = re.match(pattern, clean_key)
        if not m:
            return {
                "valid": False,
                "status": "invalid_format",
                "hwid": self.hwid,
                "message": "❌ Định dạng Key không hợp lệ! Vui lòng nhập đúng Key của Mexico Ông Già Studio (VD: MEXICO-YYYYMMDD-...).",
            }

        expiry_ymd, plan_code, key_hwid_tag, nonce, sig = m.groups()
        expected_sig = _compute_signature(expiry_ymd, plan_code, key_hwid_tag, nonce)
        if not hmac.compare_digest(sig, expected_sig):
            return {
                "valid": False,
                "status": "invalid_signature",
                "hwid": self.hwid,
                "message": "❌ Mã Key không hợp lệ hoặc đã bị chỉnh sửa sai chữ ký bảo mật!",
            }

        # Kiểm tra khóa Mã Máy (HWID)
        if key_hwid_tag != "ANYPC000" and key_hwid_tag != self.hwid_tag:
            bound_display = f"MXG-{key_hwid_tag[:4]}-{key_hwid_tag[4:8]}"
            return {
                "valid": False,
                "status": "hwid_mismatch",
                "hwid": self.hwid,
                "message": f"❌ Key này được cấp riêng cho Mã Máy [{bound_display}], không khớp với Mã Máy hiện tại [{self.hwid}]!",
            }

        # Phân tích ngày hết hạn (23:59:59 của ngày expiry_ymd)
        try:
            exp_year = int(expiry_ymd[:4])
            exp_month = int(expiry_ymd[4:6])
            exp_day = int(expiry_ymd[6:8])
            exp_date = datetime.date(exp_year, exp_month, exp_day)
            exp_dt_end = datetime.datetime(exp_year, exp_month, exp_day, 23, 59, 59)
            exp_ts = int(exp_dt_end.timestamp())
        except Exception:
            return {
                "valid": False,
                "status": "invalid_date",
                "hwid": self.hwid,
                "message": "❌ Ngày hết hạn trong Key không hợp lệ!",
            }

        # Kiểm tra thời gian thực tế & chống chỉnh lùi giờ hệ thống
        sys_ts = int(time.time())
        net_ts = get_network_timestamp(timeout=2.0) if check_online_time else None
        effective_ts = net_ts if net_ts is not None else sys_ts

        saved = self._load_saved_data()
        last_seen_ts = int(saved.get("last_seen_ts", 0) or 0)

        if net_ts is None and last_seen_ts > 0 and sys_ts < (last_seen_ts - 21600):
            return {
                "valid": False,
                "status": "clock_tampered",
                "hwid": self.hwid,
                "expiry_formatted": exp_date.strftime("%d/%m/%Y"),
                "message": "⚠️ Phát hiện đồng hồ máy tính bị chỉnh lùi ngày giờ! Vui lòng chỉnh lại đúng ngày giờ thực tế hoặc kết nối Internet.",
            }

        now_dt = datetime.datetime.fromtimestamp(effective_ts)
        today_date = now_dt.date()

        if effective_ts > exp_ts or today_date > exp_date:
            return {
                "valid": False,
                "status": "expired",
                "hwid": self.hwid,
                "license_key": clean_key,
                "plan_code": plan_code,
                "plan_label": PLAN_LABELS.get(plan_code, "Gói Bản Quyền"),
                "expiry_ymd": expiry_ymd,
                "expiry_formatted": exp_date.strftime("%d/%m/%Y"),
                "days_remaining": 0,
                "message": f"⏰ Key bản quyền của bạn đã HẾT HẠN vào ngày {exp_date.strftime('%d/%m/%Y')}. Vui lòng liên hệ Admin để gia hạn Key mới!",
            }

        days_left = (exp_date - today_date).days + 1
        mode_label = (
            "Đa Máy (Multi-PC)"
            if key_hwid_tag == "ANYPC000"
            else f"Khóa Máy ({self.hwid})"
        )
        plan_label = PLAN_LABELS.get(plan_code, "Gói Bản Quyền")

        return {
            "valid": True,
            "status": "active",
            "hwid": self.hwid,
            "license_key": clean_key,
            "plan_code": plan_code,
            "plan_label": plan_label,
            "mode_label": mode_label,
            "expiry_ymd": expiry_ymd,
            "expiry_formatted": exp_date.strftime("%d/%m/%Y"),
            "days_remaining": days_left,
            "effective_ts": max(effective_ts, last_seen_ts),
            "message": f"✅ Bản quyền hợp lệ ({plan_label}) — Hạn dùng đến hết {exp_date.strftime('%d/%m/%Y')} (Còn {days_left} ngày).",
        }

    def activate_license(self, key_str: str) -> Dict[str, Any]:
        """Kích hoạt và lưu Key bản quyền vào máy."""
        res = self.verify_key_string(key_str, check_online_time=True)
        if not res.get("valid"):
            return res

        now_ts = int(res.get("effective_ts") or time.time())
        clean_key = res["license_key"]
        save_payload = {
            "license_key": clean_key,
            "hwid": self.hwid,
            "plan_code": res["plan_code"],
            "plan_label": res["plan_label"],
            "expiry_ymd": res["expiry_ymd"],
            "expiry_formatted": res["expiry_formatted"],
            "activated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "last_seen_ts": now_ts,
            "state_mac": _compute_state_mac(clean_key, now_ts),
        }
        self._save_data(save_payload)
        return res

    def get_license_status(self, check_online_time: bool = False) -> Dict[str, Any]:
        """Kiểm tra trạng thái bản quyền hiện tại của ứng dụng."""
        saved = self._load_saved_data()
        key_str = saved.get("license_key", "")
        if not key_str:
            return {
                "valid": False,
                "status": "missing",
                "hwid": self.hwid,
                "plan_label": "Chưa kích hoạt",
                "expiry_formatted": "--/--/----",
                "days_remaining": 0,
                "message": "Vui lòng nhập Key bản quyền để sử dụng Mexico Ông Già Studio.",
            }

        res = self.verify_key_string(key_str, check_online_time=check_online_time)
        if res.get("valid"):
            now_ts = int(res.get("effective_ts") or time.time())
            prev_ts = int(saved.get("last_seen_ts", 0) or 0)
            if now_ts > prev_ts:
                saved["last_seen_ts"] = now_ts
                saved["state_mac"] = _compute_state_mac(key_str, now_ts)
                self._save_data(saved)
        return res


def get_machine_hwid() -> str:
    """
    Lấy Mã Máy (Hardware ID) cố định của máy tính hiện tại theo định dạng: MXG-XXXX-XXXX.
    Kết hợp MachineGuid trong Registry của Windows và muối riêng của Mexico Ông Già Studio.
    """
    raw_id = ""
    if os.name == "nt":
        try:
            import winreg

            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\Microsoft\Cryptography",
                0,
                winreg.KEY_READ | winreg.KEY_WOW64_64KEY,
            )
            val, _ = winreg.QueryValueEx(key, "MachineGuid")
            winreg.CloseKey(key)
            if val:
                raw_id = str(val).strip()
        except Exception:
            pass

    if not raw_id:
        try:
            raw_id = f"{uuid.getnode()}-{os.environ.get('COMPUTERNAME', 'PC')}"
        except Exception:
            raw_id = "DEFAULT-MEXICO-PC"

    digest = (
        hashlib.sha256((raw_id + "|MEXICO_ONG_GIA_HWID_SALT").encode("utf-8"))
        .hexdigest()
        .upper()
    )
    part1 = digest[:4]
    part2 = digest[4:8]
    return f"MXG-{part1}-{part2}"


def normalize_hwid_tag(hwid_input: Optional[str]) -> str:
    """
    Chuẩn hóa Mã Máy về 8 ký tự (VD: 'MXG-8F4A-92C1' -> '8F4A92C1').
    Nếu để trống hoặc 'ANY' -> trả về 'ANYPC000' (dùng cho mọi máy).
    """
    if not hwid_input:
        return "ANYPC000"
    cleaned = re.sub(r"[^0-9A-Za-z]", "", hwid_input.upper())
    if cleaned in ("", "ANY", "ALL", "ANYPC", "ANYPC000", "MULTIPC"):
        return "ANYPC000"
    if (cleaned.startswith("MXG") or cleaned.startswith("DNS")) and len(cleaned) >= 11:
        cleaned = cleaned[3:]
    if len(cleaned) >= 8:
        return cleaned[:8]
    return cleaned.ljust(8, "0")


def _compute_signature(
    expiry_ymd: str, plan_code: str, hwid_tag: str, nonce: str
) -> str:
    payload = f"MEXICO|{expiry_ymd}|{plan_code}|{hwid_tag}|{nonce}".encode("utf-8")
    sig = hmac.new(_MASTER_SECRET, payload, hashlib.sha256).hexdigest().upper()
    return sig[:12]


def _compute_state_mac(key_str: str, last_seen_ts: int) -> str:
    payload = f"STATE|{key_str}|{last_seen_ts}".encode("utf-8")
    return hmac.new(_MASTER_SECRET, payload, hashlib.sha256).hexdigest().upper()[:16]


def generate_license_key(
    plan_code: str = "M01",
    expiry_date_str: Optional[str] = None,
    days: Optional[int] = None,
    hwid_input: Optional[str] = None,
    nonce: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Tạo mã License Key bản quyền có chữ ký số HMAC-SHA256 chuyên cho Mexico Ông Già Studio.
    Định dạng Key: MEXICO-YYYYMMDD-PLAN-HWIDTAG8-NONCE4-SIG12
    """
    plan_code = (plan_code or "M01").upper().strip()[:3]
    if plan_code not in PLAN_LABELS:
        plan_code = "VIP"

    now_dt = datetime.date.today()
    if expiry_date_str:
        clean_ymd = re.sub(r"[^0-9]", "", expiry_date_str)
        if len(clean_ymd) == 8:
            expiry_ymd = clean_ymd
            exp_dt = datetime.date(
                int(clean_ymd[:4]), int(clean_ymd[4:6]), int(clean_ymd[6:8])
            )
        else:
            raise ValueError("Ngày hết hạn phải có định dạng YYYY-MM-DD hoặc YYYYMMDD.")
    else:
        plan_days_map = {
            "D07": 7,
            "M01": 30,
            "M03": 90,
            "M06": 180,
            "Y01": 365,
            "Y02": 730,
            "Y99": 36500,
        }
        add_days = (
            days
            if (days is not None and days > 0)
            else plan_days_map.get(plan_code, 30)
        )
        exp_dt = now_dt + datetime.timedelta(days=add_days)
        expiry_ymd = exp_dt.strftime("%Y%m%d")

    hwid_tag = normalize_hwid_tag(hwid_input)
    if not nonce:
        nonce = secrets.token_hex(2).upper()
    else:
        nonce = re.sub(r"[^0-9A-F]", "", nonce.upper())[:4].ljust(4, "A")

    sig = _compute_signature(expiry_ymd, plan_code, hwid_tag, nonce)
    full_key = f"MEXICO-{expiry_ymd}-{plan_code}-{hwid_tag}-{nonce}-{sig}"

    return {
        "key": full_key,
        "plan_code": plan_code,
        "plan_label": PLAN_LABELS.get(plan_code, "Gói Tùy Chỉnh"),
        "expiry_ymd": expiry_ymd,
        "expiry_formatted": exp_dt.strftime("%d/%m/%Y"),
        "hwid_tag": hwid_tag,
        "hwid_display": "Mọi Máy (Multi-PC)"
        if hwid_tag == "ANYPC000"
        else f"MXG-{hwid_tag[:4]}-{hwid_tag[4:8]}",
        "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def get_network_timestamp(timeout: float = 2.5) -> Optional[int]:
    """
    Lấy thời gian thực từ Header Date của Google / Cloudflare để chống gian lận chỉnh lùi ngày giờ Windows.
    Nếu không có mạng, trả về None (sẽ đối chiếu với mốc thời gian monotonic lưu trên máy).
    """
    import email.utils
    import urllib.request

    urls = ["https://www.google.com", "https://1.1.1.1", "https://rentry.co"]
    for url in urls:
        try:
            req = urllib.request.Request(
                url, method="HEAD", headers={"User-Agent": "Mozilla/5.0"}
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                date_hdr = resp.headers.get("Date")
                if date_hdr:
                    dt = email.utils.parsedate_to_datetime(date_hdr)
                    return int(dt.timestamp())
        except Exception:
            continue
    return None


# ==============================================================================
# MODEL PHẦN 3: CẬP NHẬT TỰ ĐỘNG OTA TỪ GITHUB (UPDATER SERVICE)
# ==============================================================================

import importlib
import shutil
import sys
import threading
import zipfile
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import requests

DEFAULT_GITHUB_REPO = "phamngocthu661-lang/mexico-ong-gia-studio"
DEFAULT_GITHUB_BRANCH = "main"
DEFAULT_VERSION = "V1.0.0"
DEFAULT_BUILD_NUMBER = 100

_update_check_cache: Dict[str, Any] = {
    "ts": 0.0,
    "data": None,
}
_update_lock = threading.Lock()

# Các thư mục & file dữ liệu riêng của máy khách TUYỆT ĐỐI KHÔNG BAO GIỜ GHI ĐÈ khi cập nhật
PROTECTED_CUSTOMER_PATHS = {
    "projects",
    "STOOK",
    "VIDEO XONG",
    "Kho_Green",
    "Kho_Voice",
    "config",
    "VoiceStudio",
    "pretrained_models",
    "bin",
    "assets",
    "logs",
    "ADMIN_KEYGEN",
    "BROWSER_PROFILE",
    "BROWSER_PROFILE_2",
    "BROWSER_PROFILE_3",
    "GEMINI_PROFILE_1",
    "saved_ideas.json",
    "deleted_ideas.json",
    "license.json",
    "settings.json",
    "used_stocks_history.json",
    "used_stock_links.json",
    "youtube_cookies.txt",
    "python_path.txt",
    "config.json",
    "storage_paths.json",
    ".git",
}


def parse_version_tuple(ver_str: str) -> Tuple[int, int, int]:
    """Chuyển chuỗi phiên bản (VD: 'V1.0.0', 'v1.2.3') thành bộ số (1, 0, 0) để so sánh chính xác."""
    nums = [int(x) for x in re.findall(r"\d+", str(ver_str or ""))]
    while len(nums) < 3:
        nums.append(0)
    return (nums[0], nums[1], nums[2])


def _resolve_root_dir(root_dir: Optional[Path] = None) -> Path:
    r = (
        Path(os.path.abspath(str(root_dir)))
        if root_dir
        else Path(os.path.abspath(__file__)).parent.parent
    )
    if r.name.lower() == "app":
        r = r.parent
    elif not (r / "STOOK").exists() and (r.parent / "STOOK").exists():
        r = r.parent
    return r


def get_local_version_info(root_dir: Optional[Path] = None) -> Dict[str, Any]:
    """Đọc thông tin phiên bản hiện tại của ứng dụng từ file version.json."""
    root_dir = _resolve_root_dir(root_dir)
    candidates = [
        root_dir / "version.json",
        root_dir / "app" / "version.json",
    ]
    for vf in candidates:
        if vf.exists():
            try:
                data = json.loads(vf.read_text(encoding="utf-8"))
                if isinstance(data, dict) and data.get("version"):
                    return {
                        "version": str(data.get("version", DEFAULT_VERSION)).strip(),
                        "build_number": int(
                            data.get("build_number", DEFAULT_BUILD_NUMBER)
                        ),
                        "released_at": str(data.get("released_at", "")).strip(),
                        "repo": str(data.get("repo", DEFAULT_GITHUB_REPO)).strip(),
                        "branch": str(
                            data.get("branch", DEFAULT_GITHUB_BRANCH)
                        ).strip(),
                        "changelog": str(data.get("changelog", "")).strip(),
                    }
            except Exception:
                pass

    return {
        "version": DEFAULT_VERSION,
        "build_number": DEFAULT_BUILD_NUMBER,
        "released_at": "2026-11-03 16:30:00",
        "repo": DEFAULT_GITHUB_REPO,
        "branch": DEFAULT_GITHUB_BRANCH,
        "changelog": "Phiên bản chính thức V1.0.0.",
    }


def _fetch_remote_version_json(
    repo: str, branch: str = "main", timeout: float = 8.0
) -> Optional[Dict[str, Any]]:
    """
    Lấy file version.json mới nhất trực tiếp từ GitHub.
    Ưu tiên GitHub REST API (không bị trễ cache CDN) và dự phòng sang raw.githubusercontent.com + bỏ qua lỗi SSL nếu máy khách thiếu chứng chỉ.
    """
    try:
        import urllib3

        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    except Exception:
        pass

    headers_api = {
        "Accept": "application/vnd.github.v3.raw",
        "Cache-Control": "no-cache, no-store, must-revalidate",
        "Pragma": "no-cache",
        "User-Agent": "DramaNhatStudio-Updater/1.0",
    }
    api_url = f"https://api.github.com/repos/{repo}/contents/version.json?ref={branch}&_t={int(time.time())}"
    raw_url = f"https://raw.githubusercontent.com/{repo}/{branch}/version.json?t={int(time.time())}"

    for url, hdrs in [
        (api_url, headers_api),
        (
            raw_url,
            {"Cache-Control": "no-cache", "User-Agent": "DramaNhatStudio-Updater/1.0"},
        ),
    ]:
        for verify_ssl in (True, False):
            try:
                resp = requests.get(
                    url, headers=hdrs, timeout=timeout, verify=verify_ssl
                )
                if resp.status_code == 200:
                    data = resp.json()
                    if isinstance(data, dict) and data.get("version"):
                        return data
            except Exception:
                continue

    return None


def check_for_github_update(
    root_dir: Optional[Path] = None, force_refresh: bool = False
) -> Dict[str, Any]:
    """
    Kiểm tra xem trên GitHub đã có phiên bản mới hơn phiên bản đang chạy ở máy khách hay chưa.
    """
    root_dir = _resolve_root_dir(root_dir)
    local_info = get_local_version_info(root_dir)
    now = time.time()

    if (
        not force_refresh
        and _update_check_cache["data"] is not None
        and (now - _update_check_cache["ts"]) < 15.0
    ):
        cached = dict(_update_check_cache["data"])
        cached["current_version"] = local_info["version"]
        cached["current_build"] = local_info["build_number"]
        local_tuple = parse_version_tuple(local_info["version"])
        remote_tuple = parse_version_tuple(
            cached.get("latest_version", local_info["version"])
        )
        cached["update_available"] = (
            int(cached.get("latest_build", 0)) > int(local_info["build_number"])
            or remote_tuple > local_tuple
        )
        return cached

    repo = local_info.get("repo") or DEFAULT_GITHUB_REPO
    branch = local_info.get("branch") or DEFAULT_GITHUB_BRANCH

    remote_info = _fetch_remote_version_json(repo=repo, branch=branch)
    if not remote_info:
        return {
            "success": False,
            "current_version": local_info["version"],
            "current_build": local_info["build_number"],
            "latest_version": local_info["version"],
            "latest_build": local_info["build_number"],
            "update_available": False,
            "released_at": local_info.get("released_at", ""),
            "changelog": local_info.get("changelog", ""),
            "repo": repo,
            "error": "Không thể kết nối tới máy chủ cập nhật GitHub (Kiểm tra mạng Internet).",
        }

    latest_ver = str(remote_info.get("version", local_info["version"])).strip()
    latest_build = int(remote_info.get("build_number", local_info["build_number"]))
    local_ver = local_info["version"]
    local_build = int(local_info["build_number"])

    is_newer = latest_build > local_build or parse_version_tuple(
        latest_ver
    ) > parse_version_tuple(local_ver)

    result = {
        "success": True,
        "current_version": local_ver,
        "current_build": local_build,
        "latest_version": latest_ver,
        "latest_build": latest_build,
        "update_available": is_newer,
        "released_at": str(remote_info.get("released_at", "")).strip(),
        "changelog": str(remote_info.get("changelog", "")).strip(),
        "repo": repo,
        "branch": branch,
    }
    _update_check_cache["ts"] = now
    _update_check_cache["data"] = dict(result)
    return result


def _hot_reload_backend_modules(adas_engine: Any = None, pipeline: Any = None):
    """
    Nạp nóng (Hot-Reload) các module và phương thức mới vừa tải về ngay trong bộ nhớ
    để máy khách áp dụng code mới ngay lập tức mà không làm gián đoạn cửa sổ đang mở.
    """
    module_names = [
        "backend.voice_service",
        "backend.sync_checker",
        "backend.renderer",
        "backend.stock_manager",
        "backend.voicevox_service",
        "backend.pipeline",
        "backend.adas_script_engine",
    ]
    reloaded_mods = {}
    for m_name in module_names:
        if m_name in sys.modules:
            try:
                reloaded_mods[m_name] = importlib.reload(sys.modules[m_name])
            except Exception as e:
                log_warn("UPDATER", f"Lưu ý khi hot-reload module {m_name}: {e}")

    # Cập nhật các phương thức (methods) mới lên các instance singleton đang chạy
    try:
        if "backend.adas_script_engine" in reloaded_mods and adas_engine is not None:
            new_cls = getattr(
                reloaded_mods["backend.adas_script_engine"], "ADASScriptEngine", None
            )
            if new_cls is not None:
                for attr_name, attr_val in vars(new_cls).items():
                    if callable(attr_val) and not attr_name.startswith("__"):
                        setattr(adas_engine.__class__, attr_name, attr_val)
    except Exception as e:
        log_warn("UPDATER", f"Lưu ý khi cập nhật nóng ADASScriptEngine: {e}")

    try:
        if "backend.pipeline" in reloaded_mods and pipeline is not None:
            new_p_cls = getattr(
                reloaded_mods["backend.pipeline"], "ProductionPipeline", None
            )
            if new_p_cls is not None:
                for attr_name, attr_val in vars(new_p_cls).items():
                    if not attr_name.startswith("__"):
                        setattr(pipeline.__class__, attr_name, attr_val)
            new_rb_cls = getattr(
                reloaded_mods["backend.pipeline"], "HardwareResourceBalancer", None
            )
            rb_inst = getattr(pipeline, "resource_balancer", None)
            if new_rb_cls is not None and rb_inst is not None:
                for attr_name, attr_val in vars(new_rb_cls).items():
                    if not attr_name.startswith("__"):
                        setattr(rb_inst.__class__, attr_name, attr_val)
            if hasattr(pipeline, "_ensure_hot_reload_compat"):
                pipeline._ensure_hot_reload_compat()
    except Exception as e:
        log_warn("UPDATER", f"Lưu ý khi cập nhật nóng ProductionPipeline: {e}")

    try:
        if "backend.voice_service" in reloaded_mods:
            vs_mod = reloaded_mods["backend.voice_service"]
            if hasattr(vs_mod, "_ensure_omnivoice_package_files"):
                try:
                    vs_mod._ensure_omnivoice_package_files(_resolve_root_dir())
                except Exception:
                    pass
            if (
                pipeline is not None
                and getattr(pipeline, "voice_service", None) is not None
            ):
                new_vs_cls = getattr(vs_mod, "VoiceStudioService", None)
                if new_vs_cls is not None:
                    for attr_name, attr_val in vars(new_vs_cls).items():
                        if not attr_name.startswith("__") and callable(attr_val):
                            setattr(
                                pipeline.voice_service.__class__, attr_name, attr_val
                            )
    except Exception as e:
        log_warn("UPDATER", f"Lưu ý khi cập nhật nóng VoiceStudioService: {e}")

    try:
        if (
            "backend.stock_manager" in reloaded_mods
            and pipeline is not None
            and getattr(pipeline, "stock_manager", None) is not None
        ):
            new_s_cls = getattr(
                reloaded_mods["backend.stock_manager"], "StockManager", None
            )
            if new_s_cls is not None:
                for attr_name, attr_val in vars(new_s_cls).items():
                    if callable(attr_val) and not attr_name.startswith("__"):
                        setattr(pipeline.stock_manager.__class__, attr_name, attr_val)
    except Exception as e:
        log_warn("UPDATER", f"Lưu ý khi cập nhật nóng StockManager: {e}")


def _safe_copy_file(src_file: Path, dst_file: Path) -> bool:
    """
    Sao chép file an toàn trên Windows:
    - Tự động gỡ cờ Read-Only nếu có.
    - Nếu file đích đang bị khóa bởi tiến trình đang chạy (VD: Drama_Nhat_Studio.exe),
      tự động đổi tên file đang chạy sang `.old_locked` rồi chép file mới vào để không bao giờ văng PermissionError!
    """
    try:
        dst_file.parent.mkdir(parents=True, exist_ok=True)
        if dst_file.exists():
            try:
                os.chmod(dst_file, 0o666)
            except Exception:
                pass
        shutil.copy2(src_file, dst_file)
        return True
    except PermissionError:
        try:
            old_locked = dst_file.with_suffix(dst_file.suffix + ".old_locked")
            if old_locked.exists():
                try:
                    old_locked.unlink()
                except Exception:
                    pass
            dst_file.rename(old_locked)
            shutil.copy2(src_file, dst_file)
            return True
        except Exception as e2:
            log_warn("UPDATER", f"Bỏ qua file đang khóa {dst_file.name}: {e2}")
            return False
    except Exception as e:
        log_warn("UPDATER", f"Lưu ý khi chép file {dst_file.name}: {e}")
        return False


def _stop_all_tasks_and_subprocesses(adas_engine: Any = None, pipeline: Any = None):
    """
    Đóng sạch 100% mọi tác vụ đang chạy (Render FFmpeg, Tạo Voice VOICEVOX, Dây chuyền ADAS AI, tải Stock yt-dlp)
    trước khi áp dụng bản cập nhật và Reset ứng dụng để không còn bất kỳ tiến trình cũ nào bị treo hoặc giữ khóa file.
    """
    import subprocess

    log_info(
        "UPDATER",
        "🛑 Đang đóng toàn bộ tác vụ đang chạy (Render FFmpeg, Voice Engine, ADAS AI) để cập nhật chuẩn xác...",
    )

    try:
        if pipeline is not None and hasattr(pipeline, "stop"):
            pipeline.stop()
    except Exception as e:
        log_warn("UPDATER", f"Lưu ý khi dừng Pipeline: {e}")

    try:
        if adas_engine is not None:
            setattr(adas_engine, "live_auto_produce_video", False)
            if hasattr(adas_engine, "stop"):
                adas_engine.stop()
    except Exception as e:
        log_warn("UPDATER", f"Lưu ý khi dừng ADAS Engine: {e}")

    try:
        from backend.voicevox_service import VoicevoxStandaloneService

        VoicevoxStandaloneService.shutdown_all_workers()
    except Exception:
        pass

    if os.name == "nt":
        for img in ("ffmpeg.exe", "ffprobe.exe", "run.exe", "yt-dlp.exe"):
            try:
                subprocess.run(
                    ["taskkill", "/F", "/IM", img, "/T"],
                    capture_output=True,
                    timeout=3,
                    creationflags=0x08000000,
                )
            except Exception:
                pass


def _schedule_full_application_reset(root_dir: Path):
    """
    Khởi chạy tiến trình phụ độc lập (_ota_restart_helper.py) tách biệt hoàn toàn khỏi cây tiến trình cũ:
    1. Chờ 1.2s cho Server trả xong phản hồi HTTP về giao diện.
    2. Tắt tiến trình Server cũ (PID cũ & cổng 8900) và Drama_Nhat_Studio.exe KHÔNG dùng cờ /T (để không bao giờ tự tắt chính _ota_restart_helper.py).
    3. Đóng sạch toàn bộ tác vụ con (run.exe, ffmpeg.exe, ffprobe.exe, yt-dlp.exe) và cửa sổ Desktop UI cũ.
    4. Khởi động lại main.py và tự động kiểm tra đảm bảo cả Server cổng 8900 lẫn cửa sổ giao diện Desktop App đều mở lên 100%.
    """
    import subprocess

    try:
        logs_dir = root_dir / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        helper_path = logs_dir / "_ota_restart_helper.py"
        lock_path = logs_dir / "_ota_restart.lock"
        try:
            if lock_path.exists():
                lock_path.unlink()
        except Exception:
            pass

        helper_code = """import os
import sys
import time
import socket
import subprocess
import urllib.request

old_pid = int(sys.argv[1]) if len(sys.argv) > 1 else 0
root_dir = sys.argv[2] if len(sys.argv) > 2 else os.getcwd()
my_pid = os.getpid()

logs_dir = os.path.join(root_dir, "logs")
os.makedirs(logs_dir, exist_ok=True)
log_file = os.path.join(logs_dir, "ota_restart.log")
lock_file = os.path.join(logs_dir, "_ota_restart.lock")

def wlog(msg):
    try:
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"[{ts}] [PID={my_pid}] {msg}\\n")
    except Exception:
        pass

# Đảm bảo chỉ 1 tiến trình helper duy nhất chạy nếu được kích hoạt song song qua cả WMI và Popen
try:
    if os.path.exists(lock_file):
        age = time.time() - os.path.getmtime(lock_file)
        if age < 15.0:
            sys.exit(0)
    with open(lock_file, "w", encoding="utf-8") as lf:
        lf.write(str(my_pid))
except Exception:
    pass

wlog(f"Bắt đầu quy trình Full Reset ứng dụng (old_pid={old_pid}, root_dir={root_dir})")
time.sleep(1.2)

# 1. Đóng sạch toàn bộ tiến trình tác vụ con (Voice Engine run.exe, FFmpeg, ffprobe, yt-dlp)
for img in ("run.exe", "ffmpeg.exe", "ffprobe.exe", "yt-dlp.exe"):
    try:
        subprocess.run(["taskkill", "/F", "/IM", img, "/T"], capture_output=True, timeout=3, creationflags=0x08000000)
    except Exception:
        pass

# 2. Tắt Launcher Mexico_Ong_Gia.exe và tiến trình Server cũ (KHÔNG dùng /T để không bao giờ tự giết tiến trình helper!)
try:
    subprocess.run(["taskkill", "/F", "/IM", "Mexico_Ong_Gia.exe"], capture_output=True, timeout=3, creationflags=0x08000000)
except Exception:
    pass

if old_pid > 0 and old_pid != my_pid:
    try:
        subprocess.run(["taskkill", "/F", "/PID", str(old_pid)], capture_output=True, timeout=4, creationflags=0x08000000)
    except Exception:
        pass

try:
    ps_kill_port = (
        f"Get-NetTCPConnection -LocalPort 8900 -State Listen -ErrorAction SilentlyContinue | "
        f"Where-Object {{ $_.OwningProcess -ne {my_pid} }} | "
        f"ForEach-Object {{ Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }}"
    )
    subprocess.run(["powershell", "-NoProfile", "-Command", ps_kill_port], capture_output=True, timeout=4, creationflags=0x08000000)
except Exception:
    pass

# 3. Đóng cửa sổ Desktop UI cũ và chờ giải phóng khóa Profile Chrome
try:
    ps_close_ui = (
        "Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object { "
        "$_.Name -in @('chrome.exe','msedge.exe') -and "
        "($_.CommandLine -like '*MexicoUI_Profile_V*' -or $_.CommandLine -like '*--app=http://127.0.0.1:8900*') "
        "} | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
    )
    subprocess.run(["powershell", "-NoProfile", "-Command", ps_close_ui], capture_output=True, timeout=4, creationflags=0x08000000)
except Exception:
    pass

# 4. Đợi cổng 8900 được giải phóng hoàn toàn
for _ in range(25):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        if s.connect_ex(("127.0.0.1", 8900)) != 0:
            break
    time.sleep(0.25)

time.sleep(0.8)

# 5. Khởi động lại ứng dụng hoàn toàn mới từ main.py
env = os.environ.copy()
env["DRAMA_PYTHON_SWITCHED"] = "1"
main_py = os.path.join(root_dir, "main.py")
wlog(f"Đang khởi chạy lại main.py bằng {sys.executable}...")

def spawn_main():
    try:
        return subprocess.Popen(
            [sys.executable, main_py],
            cwd=root_dir,
            env=env,
            creationflags=0x08000000 | 0x00000200,
        )
    except Exception as e:
        wlog(f"Lỗi khi gọi Popen main.py: {e}")
        return None

spawn_main()

# 6. Kiểm tra đảm bảo Server cổng 8900 đã sống dậy và cửa sổ giao diện Desktop đã mở trên màn hình
server_up = False
for i in range(50):
    time.sleep(0.5)
    if i == 18 and not server_up:
        wlog("Sau 9s cổng 8900 chưa lên, đang kích hoạt lại main.py lần 2...")
        spawn_main()
    try:
        proxy_handler = urllib.request.ProxyHandler({})
        opener = urllib.request.build_opener(proxy_handler)
        with opener.open("http://127.0.0.1:8900/api/status", timeout=1.2) as resp:
            if resp.status == 200:
                server_up = True
                break
    except Exception:
        pass

wlog(f"Trạng thái Server 8900 sau khi khởi động lại: server_up={server_up}")

if server_up:
    time.sleep(2.5)
    try:
        ps_check_ui = (
            "$p = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object { "
            "$_.Name -in @('chrome.exe','msedge.exe') -and "
            "($_.CommandLine -like '*MexicoUI_Profile_V*' -or $_.CommandLine -like '*--app=http://127.0.0.1:8900*') "
            "}; if ($p) { Write-Output 'UI_OPEN' }"
        )
        r_ui = subprocess.run(["powershell", "-NoProfile", "-Command", ps_check_ui], capture_output=True, text=True, timeout=4, creationflags=0x08000000)
        if "UI_OPEN" not in (r_ui.stdout or ""):
            wlog("Phát hiện cửa sổ UI chưa hiển thị -> Đang chủ động mở cửa sổ App Native...")
            local_app = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
            ui_profile_dir = os.path.join(local_app, "Mexico_Ong_Gia_Studio", "MexicoUI_Profile_V6")
            os.makedirs(ui_profile_dir, exist_ok=True)
            url_open = f"http://127.0.0.1:8900/?v={int(time.time())}"
            browser_exe = ""
            for cand_b in (
                os.path.join(os.environ.get("ProgramFiles", r"C:\\Program Files"), "Google", "Chrome", "Application", "chrome.exe"),
                os.path.join(os.environ.get("ProgramFiles(x86)", r"C:\\Program Files (x86)"), "Google", "Chrome", "Application", "chrome.exe"),
                os.path.join(local_app, "Google", "Chrome", "Application", "chrome.exe"),
                os.path.join(os.environ.get("ProgramFiles(x86)", r"C:\\Program Files (x86)"), "Microsoft", "Edge", "Application", "msedge.exe"),
                os.path.join(os.environ.get("ProgramFiles", r"C:\\Program Files"), "Microsoft", "Edge", "Application", "msedge.exe"),
            ):
                if os.path.isfile(cand_b):
                    browser_exe = cand_b
                    break
            if browser_exe:
                subprocess.Popen(
                    [
                        browser_exe,
                        f"--app={url_open}",
                        f"--user-data-dir={ui_profile_dir}",
                        "--window-size=1480,920",
                        "--window-position=60,30",
                        "--disk-cache-size=1",
                        "--media-cache-size=1",
                        "--no-first-run",
                        "--no-default-browser-check",
                        "--disable-features=Translate,CalculateNativeWinOcclusion",
                        "--disable-gpu-sandbox",
                        "--proxy-bypass-list=<-loopback>",
                    ],
                    cwd=root_dir,
                )
            else:
                os.startfile(url_open)
    except Exception as ui_err:
        wlog(f"Lưu ý khi kiểm tra/mở lại cửa sổ UI: {ui_err}")

wlog("Hoàn tất 100% quy trình Reset & mở lại ứng dụng!")
"""
        helper_path.write_text(helper_code, encoding="utf-8")
        env = os.environ.copy()
        env["DRAMA_PYTHON_SWITCHED"] = "1"
        curr_pid = os.getpid()

        # Cách 1: Khởi chạy qua WMI Win32_Process.Create để tiến trình helper thuộc về WmiPrvSE.exe (tách khỏi 100% cây tiến trình và Job Object cũ)
        if os.name == "nt":
            try:
                cmd_line = f'"{sys.executable}" "{helper_path}" {curr_pid} "{root_dir}"'
                ps_wmi = (
                    f"Invoke-CimMethod -ClassName Win32_Process -MethodName Create "
                    f"-Arguments @{{ CommandLine = '{cmd_line.replace(chr(39), chr(39) + chr(39))}'; CurrentDirectory = '{str(root_dir).replace(chr(39), chr(39) + chr(39))}' }} | Out-Null"
                )
                r_wmi = subprocess.run(
                    ["powershell", "-NoProfile", "-Command", ps_wmi],
                    capture_output=True,
                    timeout=3,
                    creationflags=0x08000000,
                )
                if r_wmi.returncode == 0:
                    pass
            except Exception:
                pass

        # Cách 2: Dự phòng Popen tách Job/Group (có file lock _ota_restart.lock chống chạy trùng)
        for flags in (
            0x08000000
            | 0x00000200
            | 0x01000000,  # CREATE_NO_WINDOW | CREATE_NEW_PROCESS_GROUP | CREATE_BREAKAWAY_FROM_JOB
            0x08000000 | 0x00000200,  # CREATE_NO_WINDOW | CREATE_NEW_PROCESS_GROUP
        ):
            try:
                subprocess.Popen(
                    [sys.executable, str(helper_path), str(curr_pid), str(root_dir)],
                    cwd=str(root_dir),
                    env=env,
                    creationflags=flags,
                    close_fds=True,
                )
                break
            except Exception:
                continue

        def _force_self_exit():
            time.sleep(1.5)
            os._exit(0)

        threading.Thread(target=_force_self_exit, daemon=True).start()
    except Exception as e:
        log_warn("UPDATER", f"Lưu ý khi lên lịch khởi động lại ứng dụng: {e}")


def apply_github_update(
    root_dir: Optional[Path] = None,
    adas_engine: Any = None,
    pipeline: Any = None,
    restart_app: bool = True,
) -> Dict[str, Any]:
    """
    Tải gói cập nhật mới nhất từ GitHub, đóng toàn bộ tác vụ đang chạy, nâng cấp toàn bộ mã nguồn
    (backend, frontend, adas_skills, version.json...) và Reset khởi động lại toàn bộ ứng dụng từ đầu.
    Giữ nguyên 100% dữ liệu dự án, Checkpoint đang render dở, kho Stock, bản quyền và cấu hình của máy khách.
    """
    with _update_lock:
        try:
            import subprocess

            try:
                import urllib3

                urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            except Exception:
                pass

            root_dir = _resolve_root_dir(root_dir)

            local_info = get_local_version_info(root_dir)
            old_version = local_info.get("version", DEFAULT_VERSION)
            repo = local_info.get("repo") or DEFAULT_GITHUB_REPO
            branch = local_info.get("branch") or DEFAULT_GITHUB_BRANCH

            log_info(
                "UPDATER",
                f"🚀 Bắt đầu tải bản cập nhật mới nhất từ GitHub ({repo}@{branch})...",
            )

            if restart_app:
                _stop_all_tasks_and_subprocesses(
                    adas_engine=adas_engine, pipeline=pipeline
                )

            tmp_dir = root_dir / "_ota_update_tmp"
            if tmp_dir.exists():
                shutil.rmtree(tmp_dir, ignore_errors=True)
            try:
                from backend import migrate_customer_workspace_layout

                migrate_customer_workspace_layout(root_dir)
            except Exception:
                pass
            tmp_dir.mkdir(parents=True, exist_ok=True)
            zip_path = tmp_dir / "update_package.zip"

            download_urls = [
                f"https://codeload.github.com/{repo}/zip/refs/heads/{branch}?t={int(time.time())}",
                f"https://api.github.com/repos/{repo}/zipball/{branch}",
            ]

            downloaded = False
            last_err = ""
            for d_url in download_urls:
                for verify_ssl in (True, False):
                    try:
                        resp = requests.get(
                            d_url,
                            headers={
                                "User-Agent": "DramaNhatStudio-Updater/1.0",
                                "Cache-Control": "no-cache",
                            },
                            stream=True,
                            timeout=60,
                            verify=verify_ssl,
                        )
                        if resp.status_code == 200:
                            with open(zip_path, "wb") as f:
                                for chunk in resp.iter_content(chunk_size=256 * 1024):
                                    if chunk:
                                        f.write(chunk)
                            if zip_path.exists() and zip_path.stat().st_size > 10_000:
                                downloaded = True
                                break
                        else:
                            last_err = f"HTTP {resp.status_code}"
                    except Exception as e:
                        last_err = str(e)
                if downloaded:
                    break

            # Dự phòng tải bằng curl.exe có sẵn trên Windows nếu Python requests bị chặn bởi Firewall/SSL máy khách
            if not downloaded:
                try:
                    subprocess.run(
                        [
                            "curl.exe",
                            "-L",
                            "-k",
                            "-s",
                            "-o",
                            str(zip_path),
                            download_urls[0],
                        ],
                        timeout=60,
                        check=False,
                    )
                    if zip_path.exists() and zip_path.stat().st_size > 10_000:
                        downloaded = True
                except Exception as e_curl:
                    last_err = f"{last_err} | curl: {e_curl}"

            if not downloaded:
                shutil.rmtree(tmp_dir, ignore_errors=True)
                try:
                    from backend import migrate_customer_workspace_layout

                    migrate_customer_workspace_layout(root_dir)
                except Exception:
                    pass
                msg = f"Không thể tải gói cập nhật từ GitHub ({last_err}). Vui lòng kiểm tra kết nối mạng!"
                log_error("UPDATER", msg)
                return {"success": False, "error": msg}

            extract_dir = tmp_dir / "extracted"
            extract_dir.mkdir(parents=True, exist_ok=True)
            try:
                with zipfile.ZipFile(zip_path, "r") as zf:
                    zf.extractall(extract_dir)
            except Exception as e:
                shutil.rmtree(tmp_dir, ignore_errors=True)
                try:
                    from backend import migrate_customer_workspace_layout

                    migrate_customer_workspace_layout(root_dir)
                except Exception:
                    pass
                msg = f"Gói cập nhật tải về bị lỗi giải nén: {e}"
                log_error("UPDATER", msg)
                return {"success": False, "error": msg}

            # Tìm thư mục gốc bên trong file zip của GitHub (thường là <repo>-<branch>/)
            sub_dirs = [d for d in extract_dir.iterdir() if d.is_dir()]
            src_root = sub_dirs[0] if len(sub_dirs) == 1 else extract_dir

            if (
                not (src_root / "backend").exists()
                or not (src_root / "frontend").exists()
            ):
                shutil.rmtree(tmp_dir, ignore_errors=True)
                try:
                    from backend import migrate_customer_workspace_layout

                    migrate_customer_workspace_layout(root_dir)
                except Exception:
                    pass
                msg = "Gói cập nhật không hợp lệ (Thiếu thư mục backend/frontend)."
                log_error("UPDATER", msg)
                return {"success": False, "error": msg}

            updated_files_count = 0
            app_subdir = root_dir / "app"

            # 1. Cập nhật các thư mục code: backend, frontend, adas_skills, Kho_Voice, assets, VoiceStudio, bin
            for folder_name in (
                "backend",
                "frontend",
                "adas_skills",
                "Kho_Voice",
                "assets",
                "VoiceStudio",
                "bin",
            ):
                s_folder = src_root / folder_name
                if not s_folder.exists():
                    continue
                for src_file in s_folder.rglob("*"):
                    if (
                        src_file.is_file()
                        and "__pycache__" not in src_file.parts
                        and not src_file.name.endswith(".pyc")
                    ):
                        rel_path = src_file.relative_to(s_folder)
                        dst_main = root_dir / folder_name / rel_path
                        if _safe_copy_file(src_file, dst_main):
                            updated_files_count += 1
                        if app_subdir.exists():
                            dst_app = app_subdir / folder_name / rel_path
                            _safe_copy_file(src_file, dst_app)

            # 2. Cập nhật các file lẻ ở thư mục gốc (trừ các file cấu hình/dữ liệu khách hàng trong PROTECTED_CUSTOMER_PATHS,
            #    và bỏ qua Mexico_Ong_Gia.exe đang chạy để không chạm vào file thực thi đang mở)
            for item in src_root.iterdir():
                if (
                    item.is_file()
                    and item.name not in PROTECTED_CUSTOMER_PATHS
                    and not item.name.startswith(".git")
                    and item.name.lower()
                    not in ("mexico_ong_gia.exe", "drama_nhat_studio.exe")
                ):
                    if _safe_copy_file(item, root_dir / item.name):
                        updated_files_count += 1
                    if app_subdir.exists() and item.name in (
                        "main.py",
                        "install_setup.py",
                        "requirements.txt",
                        "version.json",
                        "QUY_TRINH_HOAT_DONG.md",
                        "TIEN_DO_CODE.md",
                        "HUONG_DAN_CAI_DAT_KHACH_HANG.txt",
                    ):
                        _safe_copy_file(item, app_subdir / item.name)

            # 3. Khởi tạo config mặc định nếu máy khách chưa có file cấu hình bố cục
            s_cfg = src_root / "config" / "video_layout_config.json"
            d_cfg = root_dir / "config" / "video_layout_config.json"
            if s_cfg.exists() and not d_cfg.exists():
                _safe_copy_file(s_cfg, d_cfg)

            shutil.rmtree(tmp_dir, ignore_errors=True)
            try:
                from backend import migrate_customer_workspace_layout

                migrate_customer_workspace_layout(root_dir)
            except Exception:
                pass
            try:
                from backend.voice_service import _ensure_default_padre_voice_profile

                _ensure_default_padre_voice_profile(root_dir)
            except Exception:
                pass

            # Làm mới cache kiểm tra phiên bản
            _update_check_cache["ts"] = 0.0
            _update_check_cache["data"] = None

            new_info = get_local_version_info(root_dir)
            new_version = new_info.get("version", DEFAULT_VERSION)
            changelog = new_info.get("changelog", "")

            # Hot-reload các module backend đang chạy (phòng hờ nếu gọi với restart_app=False)
            _hot_reload_backend_modules(adas_engine=adas_engine, pipeline=pipeline)

            if restart_app:
                log_info(
                    "UPDATER",
                    f"🎉 Đã cập nhật [{old_version}] -> [{new_version}] ({updated_files_count} file). Đang đóng toàn bộ tác vụ và RESET khởi động lại ứng dụng hoàn toàn...",
                )
                _schedule_full_application_reset(root_dir)
            else:
                log_info(
                    "UPDATER",
                    f"🎉 Đã cập nhật ứng dụng thành công từ [{old_version}] lên [{new_version}] ({updated_files_count} file được nâng cấp)!",
                )

            return {
                "success": True,
                "restarting": bool(restart_app),
                "old_version": old_version,
                "new_version": new_version,
                "build_number": new_info.get("build_number", DEFAULT_BUILD_NUMBER),
                "changelog": changelog,
                "updated_files_count": updated_files_count,
                "message": (
                    f"🎉 Đã cập nhật lên {new_version} (Build #{new_info.get('build_number', DEFAULT_BUILD_NUMBER)})! Đang đóng toàn bộ tác vụ và Reset ứng dụng..."
                    if restart_app
                    else f"🎉 Đã cập nhật thành công lên phiên bản {new_version}!"
                ),
            }
        except Exception as fatal_err:
            err_msg = f"Lỗi khi áp dụng bản cập nhật: {fatal_err}"
            log_error("UPDATER", err_msg, exc=fatal_err)
            return {"success": False, "error": err_msg}


sys.modules["backend.license_manager"] = sys.modules[__name__]
sys.modules["backend.updater_service"] = sys.modules[__name__]
