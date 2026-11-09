# -*- coding: utf-8 -*-
"""
Khởi tạo gói Backend của Mexico Ông Già Studio (Kiến trúc 7 Model Hợp Nhất).
Tự động di chuyển (auto-migrate) cấu hình/dữ liệu của máy khách sang `config/`
và dọn dẹp các file lẻ cũ sau khi khách hàng bấm Cập nhật từ GitHub.
"""

import shutil
import sys
from pathlib import Path

_ROOT_DIR = Path(__file__).resolve().parent.parent
_BIN_DIR = _ROOT_DIR / "bin"
if _BIN_DIR.exists() and str(_BIN_DIR) not in sys.path:
    sys.path.insert(0, str(_BIN_DIR))


def migrate_customer_workspace_layout(root_dir: Path | None = None) -> None:
    """
    Đảm bảo khi máy khách cập nhật từ phiên bản cũ lên kiến trúc 7 Model mới:
    1. Toàn bộ file dữ liệu/bản quyền (`license.json`, `saved_ideas.json`, `config.json`...) ở thư mục gốc
       được tự động chuyển an toàn vào `config/` (không bao giờ mất Key hay Kịch bản).
    2. Toàn bộ `BROWSER_PROFILE*` ở thư mục gốc được chuyển vào `config/browser_profiles/`.
    3. Tự động xóa các file `.py` lẻ cũ đã được gộp (`chatgpt_web_client.py`, `karaoke_subtitle.py`...)
       và thư mục `app/` dư thừa trên máy khách.
    """
    r = Path(root_dir) if root_dir else _ROOT_DIR
    cfg_dir = r / "config"
    cfg_dir.mkdir(parents=True, exist_ok=True)

    # 1. Di chuyển các file trạng thái/bản quyền từ thư mục gốc vào config/
    state_files = (
        "license.json",
        "saved_ideas.json",
        "deleted_ideas.json",
        "storage_paths.json",
        "config.json",
        "settings.json",
        "stook_config.json",
        "stock_inventory.json",
        "used_stocks_history.json",
        "used_stock_links.json",
        "python_path.txt",
        "youtube_cookies.txt",
    )
    for fname in state_files:
        src = r / fname
        dst = cfg_dir / fname
        if src.exists() and src.is_file():
            try:
                if not dst.exists() or src.stat().st_mtime > dst.stat().st_mtime:
                    shutil.copy2(str(src), str(dst))
                src.unlink()
            except Exception:
                pass

    # 2. Di chuyển BROWSER_PROFILE* vào config/browser_profiles/
    prof_root = cfg_dir / "browser_profiles"
    for p in r.glob("BROWSER_PROFILE*"):
        if p.is_dir():
            try:
                prof_root.mkdir(parents=True, exist_ok=True)
                dst_p = prof_root / p.name
                if not dst_p.exists():
                    shutil.move(str(p), str(dst_p))
            except Exception:
                pass

    # 3. Xóa các file .py cũ đã được hợp nhất vào 7 Model để tránh xung đột trên máy khách
    b_dir = r / "backend"
    legacy_backend_files = (
        "chatgpt_web_client.py",
        "karaoke_subtitle.py",
        "sync_checker.py",
        "visual_cue_director.py",
        "license_manager.py",
        "updater_service.py",
        "install_setup.py",
    )
    for old_f in legacy_backend_files:
        fp = b_dir / old_f
        if fp.exists():
            try:
                fp.unlink()
            except Exception:
                pass

    old_inst = r / "install_setup.py"
    if old_inst.exists():
        try:
            old_inst.unlink()
        except Exception:
            pass

    old_app = r / "app"
    if old_app.exists() and old_app.is_dir():
        try:
            shutil.rmtree(str(old_app), ignore_errors=True)
        except Exception:
            pass


migrate_customer_workspace_layout(_ROOT_DIR)
