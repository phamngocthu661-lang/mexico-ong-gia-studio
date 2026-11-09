import os
import socket
import subprocess
import sys
import threading
import time
import traceback
import webbrowser
from pathlib import Path

if sys.stdout is None:
    sys.stdout = open(os.devnull, "w", encoding="utf-8")
elif hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

if sys.stderr is None:
    sys.stderr = open(os.devnull, "w", encoding="utf-8")
elif hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Đảm bảo đường dẫn gốc chính xác dù chạy từ bất kỳ đâu (ưu tiên ROOT_DIR trước APP_DIR)
CURRENT_DIR = Path(__file__).resolve().parent
if CURRENT_DIR.name.lower() == "app":
    ROOT_DIR = CURRENT_DIR.parent
else:
    ROOT_DIR = CURRENT_DIR

PYTHON_EXE = sys.executable


def run_pip(args, desc=""):
    if desc:
        print(f"\n>>> {desc}")
    cmd = [PYTHON_EXE, "-m", "pip"] + args
    print("    Lệnh:", " ".join(cmd))
    res = subprocess.run(cmd)
    return res.returncode == 0


def check_module(mod_name: str) -> bool:
    res = subprocess.run(
        [PYTHON_EXE, "-c", f"import {mod_name}"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return res.returncode == 0


def run_install_setup():
    print(
        "================================================================================"
    )
    print("🚀 [MEXICO ÔNG GIÀ STUDIO] TRÌNH TỰ ĐỘNG TẢI & CÀI ĐẶT THƯ VIỆN CHO MÁY MỚI")
    print(f"🐍 Python đang dùng: {PYTHON_EXE}")
    print(f"📂 Thư mục gốc:      {ROOT_DIR}")
    print(
        "================================================================================"
    )

    # Lưu đường dẫn Python chuẩn vào python_path.txt và %LOCALAPPDATA% để khi cập nhật hoặc giải nén thư mục mới vẫn nhớ đúng bản Python đã cài thư viện
    try:
        with open(ROOT_DIR / "config" / "python_path.txt", "w", encoding="utf-8") as f:
            f.write(PYTHON_EXE.strip())
        local_app = Path(
            os.environ.get("LOCALAPPDATA") or (Path.home() / "AppData" / "Local")
        )
        for app_sub in ("Mexico_Ong_Gia_Studio", "MexicoOngGiaStudio"):
            d_sub = local_app / app_sub
            d_sub.mkdir(parents=True, exist_ok=True)
            (d_sub / "python_path.txt").write_text(PYTHON_EXE.strip(), encoding="utf-8")
    except Exception:
        pass

    # 1. Đảm bảo pip hoạt động và được nâng cấp
    print("\n[BƯỚC 1/4] Kiểm tra và nâng cấp trình quản lý gói PIP...")
    subprocess.run(
        [PYTHON_EXE, "-m", "ensurepip", "--upgrade"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    run_pip(
        ["install", "--upgrade", "pip", "setuptools", "wheel"],
        "Đang nâng cấp pip, setuptools, wheel...",
    )

    # 2. Cài đặt PyTorch + TorchAudio (Ưu tiên CUDA GPU, dự phòng bản chuẩn nếu máy không hỗ trợ)
    print("\n[BƯỚC 2/4] Kiểm tra và cài đặt PyTorch + TorchAudio (GPU CUDA)...")
    has_nvidia_gpu = False
    try:
        gpu_res = subprocess.run(
            ["nvidia-smi"], stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        has_nvidia_gpu = gpu_res.returncode == 0
    except Exception:
        has_nvidia_gpu = False

    has_torch = check_module("torch") and check_module("torchaudio")
    if has_torch and has_nvidia_gpu:
        cuda_ok = (
            subprocess.run(
                [
                    PYTHON_EXE,
                    "-c",
                    "import torch; raise SystemExit(0 if torch.cuda.is_available() else 1)",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            ).returncode
            == 0
        )
        if not cuda_ok:
            print(
                "[!] Phát hiện card rời NVIDIA nhưng PyTorch hiện tại là bản CPU. Đang nâng cấp lên bản GPU CUDA..."
            )
            has_torch = False

    if not has_torch:
        ok_cu121 = run_pip(
            [
                "install",
                "--prefer-binary",
                "torch==2.5.1",
                "torchaudio==2.5.1",
                "--index-url",
                "https://download.pytorch.org/whl/cu121",
            ],
            "Đang tải PyTorch 2.5.1 GPU (CUDA 12.1)...",
        )
        if not ok_cu121 or not check_module("torch"):
            print("[!] Đang chuyển sang tải PyTorch GPU (CUDA 12.4)...")
            ok_cu124 = run_pip(
                [
                    "install",
                    "--prefer-binary",
                    "torch>=2.5.0,<2.9.0",
                    "torchaudio>=2.5.0,<2.9.0",
                    "--index-url",
                    "https://download.pytorch.org/whl/cu124",
                ],
                "Đang tải PyTorch GPU (CUDA 12.4)...",
            )
            if not ok_cu124 or not check_module("torch"):
                run_pip(
                    [
                        "install",
                        "--prefer-binary",
                        "torch>=2.5.0,<2.9.0",
                        "torchaudio>=2.5.0,<2.9.0",
                    ],
                    "Đang tải PyTorch bản tiêu chuẩn...",
                )
    else:
        print("✅ PyTorch & TorchAudio (GPU CUDA) đã được cài đặt sẵn!")

    # 3. Cài đặt toàn bộ thư viện trong requirements.txt
    print("\n[BƯỚC 3/4] Đang tải và cài đặt các thư viện AI VoiceStudio & Giao diện...")
    req_file = ROOT_DIR / "requirements.txt"
    if req_file.exists():
        ok_req = run_pip(
            ["install", "--prefer-binary", "-r", str(req_file)],
            "Đang cài đặt danh sách thư viện từ requirements.txt...",
        )
        if not ok_req:
            print("[!] Đang thử cài đặt từng thư viện quan trọng...")
            with open(req_file, "r", encoding="utf-8") as f:
                for line in f:
                    pkg = line.strip()
                    if pkg and not pkg.startswith("#"):
                        run_pip(["install", "--prefer-binary", pkg])
    else:
        essential_pkgs = [
            "fastapi",
            "uvicorn",
            "websockets",
            "websocket-client",
            "pywebview",
            "yt-dlp[default]",
            "yt-dlp-ejs",
            "loguru",
            "pyyaml",
            "pydantic",
            "aiofiles",
            "requests",
            "transformers",
            "accelerate",
            "safetensors",
            "huggingface-hub",
            "librosa",
            "soundfile",
            "pydub",
            "scipy",
            "numpy",
            "tqdm",
            "playwright",
            "Pillow",
            "cryptography",
            "faster-whisper",
        ]
        run_pip(
            ["install", "--prefer-binary"] + essential_pkgs,
            "Đang cài đặt các thư viện thiết yếu...",
        )

    # Kiểm tra lại các thư viện cốt lõi
    critical_mods = [
        "torch",
        "torchaudio",
        "fastapi",
        "uvicorn",
        "webview",
        "yt_dlp",
        "transformers",
        "huggingface_hub",
        "playwright",
        "PIL",
        "cryptography",
        "faster_whisper",
    ]
    missing = [m for m in critical_mods if not check_module(m)]
    if missing:
        print(f"⚠️ Đang cài bổ sung các gói còn thiếu: {missing}")
        pkg_map = {
            "webview": "pywebview",
            "yt_dlp": "yt-dlp",
            "huggingface_hub": "huggingface-hub",
            "PIL": "Pillow",
            "faster_whisper": "faster-whisper",
        }
        for m in missing:
            run_pip(["install", "--prefer-binary", pkg_map.get(m, m)])

    # Tự động đảm bảo onnxruntime-gpu được kích hoạt trên máy có card NVIDIA RTX/GTX
    if has_nvidia_gpu:
        has_ort_gpu = (
            subprocess.run(
                [
                    PYTHON_EXE,
                    "-c",
                    "import onnxruntime as ort; raise SystemExit(0 if 'CUDAExecutionProvider' in ort.get_available_providers() else 1)",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            ).returncode
            == 0
        )
        if not has_ort_gpu:
            print(
                "⚡ Phát hiện GPU NVIDIA: Đang nâng cấp onnxruntime sang bản onnxruntime-gpu (CUDA)..."
            )
            subprocess.run(
                [PYTHON_EXE, "-m", "pip", "uninstall", "-y", "onnxruntime"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            run_pip(
                ["install", "--prefer-binary", "onnxruntime-gpu"],
                "Đang cài đặt onnxruntime-gpu...",
            )

    # 4. Kiểm tra và tự động tải Model AI OmniVoice (1.6 GB) nếu chưa có
    print("\n[BƯỚC 4/4] Kiểm tra bộ não giọng đọc AI Tây Ban Nha Mexico (OmniVoice)...")
    model_dir = ROOT_DIR / "pretrained_models" / "OmniVoice"
    main_weights = model_dir / "model.safetensors"
    tok_weights = model_dir / "audio_tokenizer" / "model.safetensors"

    model_ready = (
        main_weights.exists()
        and main_weights.stat().st_size > 1_000_000_000
        and tok_weights.exists()
        and tok_weights.stat().st_size > 800_000_000
    )
    if not model_ready:
        print(
            "📥 Đang tự động tải Model AI OmniVoice từ HuggingFace về máy (Khoảng 1.6 GB)..."
        )
        print("   Vui lòng đợi cho đến khi tải xong 100%...")
        try:
            from huggingface_hub import snapshot_download

            model_dir.mkdir(parents=True, exist_ok=True)
            snapshot_download(repo_id="k2-fsa/OmniVoice", local_dir=str(model_dir))
            print("✅ Đã tải hoàn tất Model AI OmniVoice!")
        except Exception as e:
            print(f"⚠️ Lưu ý khi tải trước Model AI: {e}")
            print(
                "   (Hệ thống sẽ tự động tải lại khi bạn bấm chạy sản xuất video đầu tiên)."
            )
    else:
        print("✅ Model AI OmniVoice đã có sẵn đầy đủ trong máy!")

    print(
        "\n================================================================================"
    )
    print("🎉 [HOÀN TẤT 100%] ĐÃ CÀI ĐẶT XONG TOÀN BỘ THƯ VIỆN & MODEL AI!")
    print("👉 Bây giờ ứng dụng Mexico_Ong_Gia.exe sẽ tự động mở lên.")
    print(
        "================================================================================"
    )
    return 0


if "--setup" in sys.argv:
    raise SystemExit(run_install_setup())


def _ensure_preferred_python_runtime():
    """
    Nếu trên máy có nhiều phiên bản Python (ví dụ cả Python 3.14 và Python 3.11),
    tự động ưu tiên chuyển sang bản Python đã cài đặt đầy đủ thư viện & PyTorch CUDA
    (được lưu trong python_path.txt hoặc Python311) để không bao giờ báo thiếu thư viện nhầm!
    """
    if os.environ.get("DRAMA_PYTHON_SWITCHED") == "1":
        return

    local_appdata = os.environ.get("LOCALAPPDATA") or str(
        Path.home() / "AppData" / "Local"
    )
    candidates = []

    for pf in [
        ROOT_DIR / "config" / "python_path.txt",
        Path(local_appdata) / "Mexico_Ong_Gia_Studio" / "python_path.txt",
        Path(local_appdata) / "MexicoOngGiaStudio" / "python_path.txt",
    ]:
        if pf.exists():
            try:
                saved = pf.read_text(encoding="utf-8").strip().strip('"')
                if saved and os.path.exists(saved):
                    candidates.append(saved)
            except Exception:
                pass

    for std_py in [
        os.path.join(local_appdata, "Programs", "Python", "Python311", "python.exe"),
        os.path.join(local_appdata, "Programs", "Python", "Python312", "python.exe"),
        os.path.join(local_appdata, "Programs", "Python", "Python310", "python.exe"),
        r"C:\Program Files\Python311\python.exe",
        r"C:\Python311\python.exe",
    ]:
        if os.path.exists(std_py) and std_py not in candidates:
            candidates.append(std_py)

    cur_exe = os.path.normcase(os.path.abspath(sys.executable))
    for cand in candidates:
        cand_norm = os.path.normcase(os.path.abspath(cand))
        if cand_norm == cur_exe:
            try:
                (ROOT_DIR / "config" / "python_path.txt").write_text(
                    cand, encoding="utf-8"
                )
            except Exception:
                pass
            return
        # Kiểm tra nhanh xem bản Python ưu tiên này đã có đủ thư viện cốt lõi chưa
        try:
            chk = subprocess.run(
                [
                    cand,
                    "-c",
                    "import importlib.util as u; raise SystemExit(0 if all(u.find_spec(m) for m in ('fastapi','uvicorn','webview','torch')) else 1)",
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=8,
            )
            if chk.returncode == 0:
                try:
                    (ROOT_DIR / "config" / "python_path.txt").write_text(
                        cand, encoding="utf-8"
                    )
                except Exception:
                    pass
                env = os.environ.copy()
                env["DRAMA_PYTHON_SWITCHED"] = "1"
                res = subprocess.run(
                    [cand, str(Path(__file__).resolve()), *sys.argv[1:]], env=env
                )
                raise SystemExit(res.returncode)
        except SystemExit:
            raise
        except Exception:
            continue


_ensure_preferred_python_runtime()

APP_DIR = ROOT_DIR / "app"
BIN_DIR = ROOT_DIR / "bin"
LOGS_DIR = ROOT_DIR / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)
STARTUP_LOG_PATH = LOGS_DIR / "server_startup.log"

if BIN_DIR.exists():
    os.environ["PATH"] = str(BIN_DIR) + os.pathsep + os.environ.get("PATH", "")

for p in [APP_DIR, ROOT_DIR]:
    if p.exists():
        p_str = str(p)
        if p_str in sys.path:
            sys.path.remove(p_str)
        sys.path.insert(0, p_str)


def _write_startup_log(msg: str, is_error: bool = False):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    lvl = "ERROR" if is_error else "INFO"
    line = f"[{ts}] [{lvl}] [STARTUP] {msg}"
    print(line)
    try:
        with open(STARTUP_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(line + "\n")
        if is_error:
            with open(LOGS_DIR / "error_diagnostic.log", "a", encoding="utf-8") as ef:
                ef.write(line + "\n")
    except Exception:
        pass


os.environ.pop("HTTP_PROXY", None)
os.environ.pop("HTTPS_PROXY", None)
os.environ.pop("http_proxy", None)
os.environ.pop("https_proxy", None)
os.environ["NO_PROXY"] = "127.0.0.1,localhost"
os.environ["no_proxy"] = "127.0.0.1,localhost"

_write_startup_log(
    f"Bắt đầu khởi chạy Mexico Ông Già Studio (Python: {sys.executable}, Root: {ROOT_DIR})"
)

try:
    import fastapi  # noqa: F401
    import uvicorn
except ImportError as imp_err:
    _write_startup_log(
        f"Phát hiện thiếu thư viện cốt lõi ({imp_err}). Đang tự động chạy trình cài đặt (install_setup.py)...",
        is_error=False,
    )
    run_install_setup()
    import uvicorn

try:
    from backend.logger_service import log_error, log_info
    from backend.server import create_app
except ImportError:
    from app.backend.logger_service import log_error, log_info
    from app.backend.server import create_app


SERVER_BOOT_ERROR: list[str] = []


def find_free_port(start_port=8900):
    for port in range(start_port, start_port + 50):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", port)) != 0:
                return port
    return start_port


def start_server(port: int, root_dir: Path):
    try:
        _write_startup_log(
            f"Đang khởi tạo FastAPI Application trên cổng 127.0.0.1:{port}..."
        )
        app = create_app(root_dir)
        config = uvicorn.Config(
            app=app,
            host="127.0.0.1",
            port=port,
            log_level="warning",
            access_log=False,
            log_config=None,
        )
        server = uvicorn.Server(config)
        log_info(
            f"Server FastAPI đã khởi tạo thành công tại http://127.0.0.1:{port}",
            category="SERVER",
        )
        server.run()
    except Exception as e:
        tb = traceback.format_exc()
        err_msg = f"Lỗi nghiêm trọng khi khởi động Server trên cổng {port}: {e}\n{tb}"
        SERVER_BOOT_ERROR.append(err_msg)
        _write_startup_log(err_msg, is_error=True)
        try:
            log_error(
                f"Không thể bật Server trên cổng {port}: {e}", category="SERVER", exc=e
            )
        except Exception:
            pass


def is_local_server_responding(port=8900) -> bool:
    """Kiểm tra nhanh Server nội bộ đã sẵn sàng nhận kết nối HTTP chưa (không bao giờ kill tiến trình)."""
    try:
        import urllib.request

        proxy_handler = urllib.request.ProxyHandler({})
        opener = urllib.request.build_opener(proxy_handler)
        with opener.open(f"http://127.0.0.1:{port}/api/status", timeout=1.5) as resp:
            return resp.status == 200
    except Exception:
        return False


def is_existing_studio_running(port=8900) -> bool:
    if not is_local_server_responding(port):
        return False

    # Server đang chạy sẵn từ phiên trước trên cổng 8900 -> kiểm tra nhanh xem có phản hồi bình thường không
    try:
        import urllib.request

        proxy_handler = urllib.request.ProxyHandler({})
        opener = urllib.request.build_opener(proxy_handler)
        with opener.open(
            f"http://127.0.0.1:{port}/api/chatgpt/status", timeout=3.0
        ) as resp_chk:
            return resp_chk.status == 200
    except Exception:
        # Chỉ tắt tiến trình cũ nếu ĐÓ KHÔNG PHẢI là chính tiến trình Python hiện tại (os.getpid())
        my_pid = os.getpid()
        try:
            ps_kill = (
                f"Get-NetTCPConnection -LocalPort {port} -State Listen -ErrorAction SilentlyContinue | "
                f"Where-Object {{ $_.OwningProcess -ne {my_pid} }} | "
                f"ForEach-Object {{ Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }}"
            )
            subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps_kill],
                capture_output=True,
                timeout=3,
                creationflags=0x08000000,
            )
            time.sleep(0.5)
        except Exception:
            pass
        return False


def is_frontend_html_ready(port=8900) -> bool:
    try:
        import urllib.request

        proxy_handler = urllib.request.ProxyHandler({})
        opener = urllib.request.build_opener(proxy_handler)
        with opener.open(f"http://127.0.0.1:{port}/", timeout=1.5) as resp:
            if resp.status != 200:
                return False
            body = resp.read(2048).decode("utf-8", errors="ignore")
            return "DRAMA" in body.upper() or "<HTML" in body.upper()
    except Exception:
        return False


def _find_chromium_app_browser() -> str:
    """Tìm trình duyệt Google Chrome hoặc Microsoft Edge trên máy khách để mở cửa sổ App Native."""
    candidates = []
    local_app = os.environ.get("LOCALAPPDATA", "")
    prog_files = os.environ.get("ProgramFiles", r"C:\Program Files")
    prog_x86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")

    for base in (prog_files, prog_x86, local_app):
        if base:
            candidates.append(
                os.path.join(base, "Google", "Chrome", "Application", "chrome.exe")
            )
            candidates.append(
                os.path.join(base, "Microsoft", "Edge", "Application", "msedge.exe")
            )

    for p in candidates:
        if p and os.path.isfile(p):
            return p

    try:
        import winreg

        for exe_name in ("chrome.exe", "msedge.exe"):
            for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
                try:
                    with winreg.OpenKey(
                        hive,
                        rf"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\{exe_name}",
                    ) as k:
                        val, _ = winreg.QueryValueEx(k, "")
                        if val and os.path.isfile(val):
                            return val
                except Exception:
                    pass
    except Exception:
        pass
    return ""


def _is_non_default_desktop() -> bool:
    """Kiểm tra xem tiến trình có đang chạy trong Sandbox/Background Desktop (khác Default) hay không."""
    try:
        import ctypes

        u32 = ctypes.windll.user32
        k32 = ctypes.windll.kernel32
        h_desk = u32.GetThreadDesktop(k32.GetCurrentThreadId())
        buf = ctypes.create_unicode_buffer(256)
        if u32.GetUserObjectInformationW(h_desk, 2, buf, 512, None):
            desk_name = (buf.value or "").strip()
            if desk_name and desk_name.lower() != "default":
                return True
    except Exception:
        pass
    return False


def open_native_pywebview_window(url: str) -> str:
    """
    Mở cửa sổ Desktop App Native thật sự bằng PyWebView (Edge WebView2).
    Không có thanh địa chỉ trình duyệt hay chữ localhost/127.0.0.1.
    Tự động cấu hình WEBVIEW2_USER_DATA_FOLDER riêng để tránh lỗi màn hình đen khi chạy quyền Admin.
    Trả về: 'closed' | 'failed'
    """
    if _is_non_default_desktop():
        return "failed"

    try:
        local_app = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
        wv2_profile = os.path.join(
            local_app, "Mexico_Ong_Gia_Studio", "WebView2_Native_Profile_V3"
        )
        os.makedirs(wv2_profile, exist_ok=True)
        os.environ["WEBVIEW2_USER_DATA_FOLDER"] = wv2_profile
        os.environ["WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS"] = (
            "--disable-gpu-sandbox --no-first-run --no-default-browser-check "
            "--disk-cache-size=1 --media-cache-size=1 --proxy-bypass-list=<-loopback>"
        )

        import webview

        cache_bust_url = f"{url}/?v={int(time.time())}"
        _write_startup_log(
            f"Đang mở cửa sổ Desktop App Native (PyWebView EdgeChromium) -> {cache_bust_url}"
        )
        webview.create_window(
            title="ZC Team - MEXICO ÔNG GIÀ | Workstation Studio",
            url=cache_bust_url,
            width=1480,
            height=920,
            min_size=(1180, 760),
            background_color="#0b0f12",
            js_api=DesktopBridge(),
        )
        webview.start(gui="edgechromium", debug=False)
        return "closed"
    except Exception as e:
        _write_startup_log(
            f"Lưu ý khi mở PyWebView Native ({e}), tự động chuyển sang Chromium App mode...",
            is_error=False,
        )
        return "failed"


def _close_stale_desktop_ui_windows():
    """Đóng các cửa sổ giao diện DesktopUI_Profile cũ (nếu có) để cửa sổ mới nạp code mới nhất ngay lập tức."""
    try:
        ps_cmd = (
            "Get-CimInstance Win32_Process | Where-Object { "
            "$_.Name -in @('chrome.exe','msedge.exe') -and "
            "($_.CommandLine -like '*MexicoUI_Profile_V*' -or $_.CommandLine -like '*--app=http://127.0.0.1:8900*') "
            "} | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
        )
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_cmd],
            capture_output=True,
            timeout=4,
            creationflags=0x08000000,
        )
        time.sleep(0.6)
    except Exception:
        pass


def _is_desktop_ui_window_alive() -> bool:
    """Kiểm tra xem còn bất kỳ tiến trình cửa sổ Desktop UI (Chrome/Edge App) nào đang mở hay không."""
    try:
        ps_check = (
            "$p = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object { "
            "$_.Name -in @('chrome.exe','msedge.exe') -and "
            "($_.CommandLine -like '*MexicoUI_Profile_V*' -or $_.CommandLine -like '*--app=http://127.0.0.1:8900*') "
            "}; if ($p) { Write-Output 'ALIVE' }"
        )
        r = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_check],
            capture_output=True,
            text=True,
            timeout=4,
            creationflags=0x08000000,
        )
        return "ALIVE" in (r.stdout or "")
    except Exception:
        return True


def open_desktop_ui_window(url: str):
    """
    Mở giao diện Mexico Ông Già Studio bằng cửa sổ Chromium App Native (--app=...)
    hiển thị trực tiếp trên màn hình chính của người dùng với bộ đệm được làm mới 100%.
    """
    cache_bust_url = f"{url}/?v={int(time.time())}"
    browser_exe = _find_chromium_app_browser()
    if browser_exe:
        try:
            _close_stale_desktop_ui_windows()
            in_bg_desktop = _is_non_default_desktop()
            local_app = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
            ui_profile_dir = os.path.join(
                local_app, "Mexico_Ong_Gia_Studio", "MexicoUI_Profile_V6"
            )
            os.makedirs(ui_profile_dir, exist_ok=True)

            if in_bg_desktop:
                bat_path = os.path.join(
                    local_app, "Mexico_Ong_Gia_Studio", "open_ui_window.bat"
                )
                bat_content = (
                    f"@echo off\r\n"
                    f'start "" "{browser_exe}" --app="{cache_bust_url}" '
                    f'--user-data-dir="{ui_profile_dir}" '
                    f"--window-size=1480,920 --window-position=60,30 "
                    f"--disk-cache-size=1 --media-cache-size=1 "
                    f"--no-first-run --no-default-browser-check "
                    f"--disable-features=Translate,CalculateNativeWinOcclusion "
                    f'--disable-gpu-sandbox "--proxy-bypass-list=<-loopback>"\r\n'
                )
                with open(bat_path, "w", encoding="utf-8") as bf:
                    bf.write(bat_content)
                subprocess.run(
                    [
                        "schtasks",
                        "/Create",
                        "/TN",
                        "MexicoOngGiaAppUI",
                        "/TR",
                        f'"{bat_path}"',
                        "/SC",
                        "ONCE",
                        "/ST",
                        "00:00",
                        "/IT",
                        "/F",
                    ],
                    capture_output=True,
                    timeout=5,
                )
                subprocess.run(
                    ["schtasks", "/Run", "/TN", "MexicoOngGiaAppUI"],
                    capture_output=True,
                    timeout=5,
                )
                _write_startup_log(
                    f"Đang mở cửa sổ App Native trên màn hình chính (schtasks /IT): {browser_exe} -> {cache_bust_url}"
                )
                return None

            cmd = [
                browser_exe,
                f"--app={cache_bust_url}",
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
            ]
            _write_startup_log(
                f"Đang mở cửa sổ App Native bằng: {browser_exe} -> {cache_bust_url} (bg_desktop={in_bg_desktop})"
            )
            proc = subprocess.Popen(cmd, cwd=str(ROOT_DIR))
            return proc
        except Exception as e:
            _write_startup_log(
                f"Lưu ý khi mở Chromium App mode ({e}), chuyển sang webbrowser.open...",
                is_error=False,
            )

    _write_startup_log(f"Đang mở giao diện qua trình duyệt mặc định: {cache_bust_url}")
    webbrowser.open(cache_bust_url)
    return None


class DesktopBridge:
    """Cầu nối trực tiếp từ cửa sổ Desktop App sang Windows Explorer của người dùng."""

    def open_folder(self, path: str) -> dict:
        try:
            if not path:
                return {"success": False, "error": "Chưa có đường dẫn thư mục"}
            p = os.path.abspath(str(path).strip())
            os.makedirs(p, exist_ok=True)
            if os.path.isdir(p):
                renders_dir = os.path.join(p, "renders")
                if os.path.isdir(renders_dir):
                    mp4s = [
                        os.path.join(renders_dir, f)
                        for f in os.listdir(renders_dir)
                        if f.lower().endswith(".mp4")
                    ]
                    if mp4s:
                        subprocess.Popen(f'explorer.exe /select,"{mp4s[0]}"')
                        return {"success": True, "opened": mp4s[0]}
                subprocess.Popen(f'explorer.exe "{p}"')
                return {"success": True, "opened": p}
            elif os.path.isfile(p):
                subprocess.Popen(f'explorer.exe /select,"{p}"')
                return {"success": True, "opened": p}
            return {"success": False, "error": f"Không tìm thấy thư mục: {p}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def open_video(self, path: str) -> dict:
        try:
            if not path:
                return {"success": False, "error": "Chưa có đường dẫn video"}
            p = os.path.abspath(str(path).strip())
            if os.path.isfile(p):
                os.startfile(p)
                return {"success": True}
            return {"success": False, "error": f"File video chưa tồn tại: {p}"}
        except Exception as e:
            return {"success": False, "error": str(e)}


def shutdown_all_studio_processes():
    """Tắt sạch 100% mọi tiến trình con (FFmpeg, Launcher) khi người dùng bấm nút X đóng ứng dụng."""
    _write_startup_log("🛑 Đang tắt toàn bộ tiến trình Mexico Ông Già Studio...")
    if os.name == "nt":
        for img in ("ffmpeg.exe", "Mexico_Ong_Gia.exe"):
            try:
                subprocess.run(
                    ["taskkill", "/F", "/IM", img, "/T"],
                    capture_output=True,
                    timeout=3,
                    creationflags=0x08000000,
                )
            except Exception:
                pass


def main():
    import atexit

    default_port = 8900
    reuse_existing = is_existing_studio_running(default_port)
    if not reuse_existing:
        atexit.register(shutdown_all_studio_processes)
    port = default_port if reuse_existing else find_free_port(default_port)
    url = f"http://127.0.0.1:{port}"

    print(
        "================================================================================"
    )
    print("🎬 [MEXICO ÔNG GIÀ STUDIO] KHỞI ĐỘNG ỨNG DỤNG DESKTOP ĐỘC LẬP")
    print(f"📍 Thư mục làm việc: {ROOT_DIR}")
    print(f"📋 File Log khởi động: {STARTUP_LOG_PATH}")
    print(
        f"🌐 Server Backend cục bộ: {url}"
        + (" (Kết nối lại tiến trình đang chạy ngầm)" if reuse_existing else "")
    )
    print(
        "================================================================================"
    )

    if not reuse_existing:
        server_thread = threading.Thread(
            target=start_server,
            args=(port, ROOT_DIR),
            daemon=True,
        )
        server_thread.start()

        server_ready = False
        for _ in range(150):
            if SERVER_BOOT_ERROR:
                break
            if is_local_server_responding(port) and is_frontend_html_ready(port):
                server_ready = True
                break
            time.sleep(0.2)

        if not server_ready:
            boot_err = (
                SERVER_BOOT_ERROR[0]
                if SERVER_BOOT_ERROR
                else "Quá thời gian chờ (30s) nhưng Server Backend chưa phản hồi."
            )
            _write_startup_log(
                f"CHƯA BẬT ĐƯỢC SERVER BACKEND:\n{boot_err}", is_error=True
            )
            try:
                import ctypes

                ctypes.windll.user32.MessageBoxW(
                    0,
                    f"❌ Không thể bật được Server Backend (Cổng {port})!\n\n"
                    f"Chi tiết lỗi:\n{boot_err[:600]}\n\n"
                    f"👉 Toàn bộ log chi tiết đã được lưu tại:\n{STARTUP_LOG_PATH}",
                    "Mexico Ông Già Studio — Lỗi Khởi Động Server",
                    0x10,
                )
            except Exception:
                pass
            return
        else:
            _write_startup_log(
                f"✅ Server Backend & Giao diện HTML đã sẵn sàng 100% tại {url}"
            )

    print(f"-> Đang mở cửa sổ ứng dụng Desktop Mexico Ông Già Studio...")
    ui_proc = open_desktop_ui_window(url)

    if reuse_existing:
        # Nếu kết nối vào Server đang chạy sẵn thì chỉ cần mở cửa sổ giao diện mới rồi thoát launcher phụ
        time.sleep(2.0)
        return

    print(
        "================================================================================"
    )
    print(f"✅ GIAO DIỆN DESKTOP ĐÃ MỞ THÀNH CÔNG")
    print(
        "💡 Khi đóng cửa sổ ứng dụng bằng nút [X], toàn bộ Server Backend & Server Voice (run.exe) sẽ tự động tắt sạch 100%!"
    )
    print(
        "================================================================================"
    )

    try:
        ui_start_ts = time.time()
        reopen_attempted = False
        while True:
            time.sleep(1.5)
            if ui_proc is not None and ui_proc.poll() is not None:
                elapsed_ui = time.time() - ui_start_ts
                rc = ui_proc.returncode
                ui_proc = None

                # Nếu tiến trình launcher của Chrome thoát sớm (< 10s sau khi bật) do profile cũ vừa đóng xong
                # hoặc do Chrome chuyển tiếp cửa sổ sang tiến trình nền:
                if elapsed_ui < 10.0:
                    time.sleep(1.0)
                    if _is_desktop_ui_window_alive():
                        _write_startup_log(
                            "Cửa sổ App Native đã chuyển tiếp sang tiến trình Chrome chính và đang hiển thị bình thường.",
                            is_error=False,
                        )
                        continue
                    if not reopen_attempted:
                        reopen_attempted = True
                        _write_startup_log(
                            f"Tiến trình cửa sổ đầu tiên đóng sớm ({elapsed_ui:.1f}s, rc={rc}), đang tự động mở lại cửa sổ App...",
                            is_error=False,
                        )
                        time.sleep(1.0)
                        ui_start_ts = time.time()
                        ui_proc = open_desktop_ui_window(url)
                        if ui_proc is None and not _is_desktop_ui_window_alive():
                            webbrowser.open(f"{url}/?v={int(time.time())}")
                        continue
                else:
                    if not _is_desktop_ui_window_alive():
                        # Người dùng đã bấm nút X đóng cửa sổ ứng dụng -> Tắt sạch toàn bộ hệ thống & Server Voice!
                        shutdown_all_studio_processes()
                        os._exit(0)
    except KeyboardInterrupt:
        print("\nĐã đóng Mexico Ông Già Studio.")
        shutdown_all_studio_processes()
        os._exit(0)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        _write_startup_log(
            f"LỖI NGHIÊM TRỌNG KHI CHẠY MAIN.PY:\n{traceback.format_exc()}",
            is_error=True,
        )
        raise
