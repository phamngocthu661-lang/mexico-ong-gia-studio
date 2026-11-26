# -*- coding: utf-8 -*-
"""
Xác minh và cài đặt an toàn gói cập nhật OTA.

Module này chỉ dùng thư viện chuẩn và `cryptography`, không import phần còn lại của
backend, để `Cap_Nhat_Nhanh.bat` vẫn chạy được khi code ứng dụng đang hỏng:

    python -B -I backend/ota_security.py verify --package <thu_muc_goi> --root <thu_muc_app>
    python -B -I backend/ota_security.py install --package <thu_muc_goi> --root <thu_muc_app>
"""

from __future__ import annotations

import argparse
import base64
import binascii
import hashlib
import json
import os
import re
import shutil
import sys
import time
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Dict, Iterable, List, Optional

OTA_PUBLIC_KEY_B64 = "0wbsjrjklWxjt2GTCZAcKT9W9jrNvoxuIWqG5dK7fe8="

MANIFEST_NAME = "update_manifest.json"
SIGNATURE_NAME = "update_manifest.sig"
MANIFEST_FORMAT = 1
BACKUP_DIR_NAME = "_ota_backup"
BACKUP_INDEX_NAME = "backup_manifest.json"
ROLLBACK_MARKER_NAME = "_ota_pending_rollback.json"

MAX_UNPACKED_BYTES = 6 * 1024 * 1024 * 1024
MAX_ZIP_ENTRIES = 20_000
MIN_FREE_BYTES = 200 * 1024 * 1024

MANAGED_DIRS = (
    "backend",
    "frontend",
    "adas_skills",
    "Kho_Voice",
    "Kho_Green",
    "assets",
    "VoiceStudio",
    "bin",
)
LAYOUT_FILES = (
    "video_layout_config.json",
    "video_layout_padre_mx.json",
    "video_layout_homeless.json",
    "video_layout_mafia.json",
)
APP_MIRROR_ROOT_FILES = (
    "main.py",
    "install_setup.py",
    "requirements.txt",
    "version.json",
    "QUY_TRINH_HOAT_DONG.md",
    "TIEN_DO_CODE.md",
    "HUONG_DAN_CAI_DAT_KHACH_HANG.txt",
)
LOCKED_EXECUTABLES = ("mexico_ong_gia.exe", "drama_nhat_studio.exe")

# Phải trùng với PROTECTED_CUSTOMER_PATHS trong logger_service.py.
DEFAULT_PROTECTED_NAMES = frozenset(
    {
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
        "idea_id_counter.json",
        "_idea_id_counter.json",
        "machine_code.json",
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
)


class UpdateVerificationError(RuntimeError):
    """Gói cập nhật không chứng minh được là bản phát hành chính thức."""


class UpdateInstallError(RuntimeError):
    """Không cài được gói cập nhật; file cũ đã được khôi phục nếu có thể."""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _is_safe_relative_path(rel_path: str) -> bool:
    if not rel_path or "\\" in rel_path or ":" in rel_path or "\0" in rel_path:
        return False
    pure = PurePosixPath(rel_path)
    return not pure.is_absolute() and all(p not in ("", ".", "..") for p in pure.parts)


def verify_manifest_signature(
    manifest_bytes: bytes,
    signature_b64: bytes,
    public_key_b64: Optional[str] = None,
) -> Dict[str, Any]:
    """Kiểm tra chữ ký Ed25519 trên đúng từng byte của manifest rồi kiểm tra cấu trúc."""
    try:
        from cryptography.exceptions import InvalidSignature
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    except ImportError as exc:
        raise UpdateVerificationError(
            "Thiếu thư viện cryptography nên không thể xác minh gói cập nhật."
        ) from exc

    try:
        signature = base64.b64decode(signature_b64.strip(), validate=True)
        key_raw = base64.b64decode(public_key_b64 or OTA_PUBLIC_KEY_B64, validate=True)
        Ed25519PublicKey.from_public_bytes(key_raw).verify(signature, manifest_bytes)
    except (InvalidSignature, binascii.Error, ValueError) as exc:
        raise UpdateVerificationError(
            "Chữ ký gói cập nhật không hợp lệ. Đã từ chối cài đặt."
        ) from exc

    try:
        manifest = json.loads(manifest_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise UpdateVerificationError("Manifest cập nhật bị lỗi định dạng.") from exc

    files = manifest.get("files") if isinstance(manifest, dict) else None
    if (
        not isinstance(files, dict)
        or manifest.get("format") != MANIFEST_FORMAT
        or not isinstance(manifest.get("build_number"), int)
    ):
        raise UpdateVerificationError("Manifest cập nhật sai cấu trúc.")
    for rel_path, digest in files.items():
        if not _is_safe_relative_path(rel_path) or not (
            isinstance(digest, str) and re.fullmatch(r"[0-9a-f]{64}", digest)
        ):
            raise UpdateVerificationError(f"Manifest có mục không hợp lệ: {rel_path!r}")
    return manifest


def verify_update_package(
    src_root: Path,
    local_build: int = 0,
    public_key_b64: Optional[str] = None,
) -> Dict[str, Any]:
    """Chỉ trả về manifest khi gói đúng chữ ký, không hạ cấp và khớp từng file."""
    src_root = Path(src_root)
    manifest_path = src_root / MANIFEST_NAME
    signature_path = src_root / SIGNATURE_NAME
    if not manifest_path.is_file() or not signature_path.is_file():
        raise UpdateVerificationError(
            "Gói cập nhật chưa được ký. Đã từ chối cài đặt."
        )

    manifest = verify_manifest_signature(
        manifest_path.read_bytes(), signature_path.read_bytes(), public_key_b64
    )
    if manifest["build_number"] < int(local_build):
        raise UpdateVerificationError(
            f"Từ chối hạ cấp từ Build #{local_build} xuống Build #{manifest['build_number']}."
        )

    expected: Dict[str, str] = manifest["files"]
    actual = {
        item.relative_to(src_root).as_posix()
        for item in src_root.rglob("*")
        if item.is_file()
    } - {MANIFEST_NAME, SIGNATURE_NAME}

    missing = sorted(set(expected) - actual)
    extra = sorted(actual - set(expected))
    if missing or extra:
        sample = (missing + extra)[0]
        raise UpdateVerificationError(
            f"Gói cập nhật không khớp manifest ({len(missing)} thiếu, {len(extra)} thừa, ví dụ: {sample})."
        )
    for rel_path, digest in expected.items():
        if sha256_file(src_root / rel_path) != digest:
            raise UpdateVerificationError(f"File bị thay đổi trong gói: {rel_path}")

    try:
        version_info = json.loads((src_root / "version.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise UpdateVerificationError("Gói cập nhật thiếu version.json hợp lệ.") from exc
    if int(version_info.get("build_number", -1)) != manifest["build_number"]:
        raise UpdateVerificationError("version.json không khớp manifest đã ký.")
    return manifest


def safe_extract_zip(zip_path: Path, dest_dir: Path) -> None:
    """Giải nén sau khi chặn đường dẫn nguy hiểm và gói phình quá lớn."""
    with zipfile.ZipFile(zip_path, "r") as archive:
        members = archive.infolist()
        if len(members) > MAX_ZIP_ENTRIES:
            raise UpdateVerificationError("Gói cập nhật có quá nhiều file.")
        if sum(m.file_size for m in members) > MAX_UNPACKED_BYTES:
            raise UpdateVerificationError("Gói cập nhật vượt giới hạn dung lượng.")
        for member in members:
            if not _is_safe_relative_path(member.filename.rstrip("/")):
                raise UpdateVerificationError(
                    f"Gói cập nhật có đường dẫn không an toàn: {member.filename!r}"
                )
        archive.extractall(dest_dir)


def build_install_plan(
    src_root: Path,
    root_dir: Path,
    manifest: Dict[str, Any],
    protected_names: Optional[Iterable[str]] = None,
    skip_root_files: Iterable[str] = (),
) -> List[Dict[str, Any]]:
    """Liệt kê file sẽ cài, giữ nguyên phạm vi cập nhật và vùng dữ liệu khách hàng."""
    src_root, root_dir = Path(src_root), Path(root_dir)
    protected = set(
        DEFAULT_PROTECTED_NAMES if protected_names is None else protected_names
    )
    skipped = {name.lower() for name in skip_root_files}
    hashes: Dict[str, str] = manifest["files"]
    app_dir = root_dir / "app"
    has_app_mirror = app_dir.is_dir()
    plan: Dict[str, Dict[str, Any]] = {}

    def add(rel_src: str, dst: Path) -> None:
        plan[os.path.normcase(str(dst))] = {
            "src": src_root / rel_src,
            "dst": dst,
            "rel": dst.relative_to(root_dir).as_posix(),
            "sha256": hashes[rel_src],
        }

    for rel_src in sorted(hashes):
        parts = PurePosixPath(rel_src).parts
        if len(parts) > 1 and parts[0] in MANAGED_DIRS:
            if "__pycache__" in parts or rel_src.endswith(".pyc"):
                continue
            add(rel_src, root_dir.joinpath(*parts))
            if has_app_mirror:
                add(rel_src, app_dir.joinpath(*parts))
        elif len(parts) == 1:
            name = parts[0]
            if (
                name in protected
                or name.startswith(".git")
                or name.lower() in LOCKED_EXECUTABLES
                or name.lower() in skipped
            ):
                continue
            add(rel_src, root_dir / name)
            if has_app_mirror and name in APP_MIRROR_ROOT_FILES:
                add(rel_src, app_dir / name)

    for layout_name in LAYOUT_FILES:
        for candidate in (
            f"config/{layout_name}",
            f"assets/default_layouts/{layout_name}",
        ):
            if candidate in hashes:
                add(candidate, root_dir / "config" / layout_name)
                break
    return list(plan.values())


def _copy_with_lock_fallback(src_file: Path, dst_file: Path) -> bool:
    try:
        dst_file.parent.mkdir(parents=True, exist_ok=True)
        if dst_file.exists():
            try:
                os.chmod(dst_file, 0o666)
            except OSError:
                pass
        shutil.copy2(src_file, dst_file)
        return True
    except PermissionError:
        try:
            locked = dst_file.with_suffix(dst_file.suffix + ".old_locked")
            if locked.exists():
                locked.unlink()
            dst_file.rename(locked)
            shutil.copy2(src_file, dst_file)
            return True
        except OSError:
            return False
    except OSError:
        return False


def restore_backup(backup_dir: Path, root_dir: Path) -> List[str]:
    """Trả toàn bộ file về trạng thái trước khi cập nhật; trả về danh sách file lỗi."""
    backup_dir, root_dir = Path(backup_dir), Path(root_dir)
    index = json.loads((backup_dir / BACKUP_INDEX_NAME).read_text(encoding="utf-8"))
    errors: List[str] = []
    for rel_path in index.get("created", []):
        target = root_dir / rel_path
        try:
            if target.is_file():
                os.chmod(target, 0o666)
                target.unlink()
        except OSError:
            errors.append(rel_path)
    for rel_path in index.get("saved", []):
        if not _copy_with_lock_fallback(backup_dir / "files" / rel_path, root_dir / rel_path):
            errors.append(rel_path)
    return errors


def _prune_backups(backup_root: Path, keep: int) -> None:
    backups = sorted(
        (p for p in backup_root.iterdir() if p.is_dir()),
        key=lambda p: p.name,
        reverse=True,
    )
    for old_backup in backups[max(keep, 1) :]:
        shutil.rmtree(old_backup, ignore_errors=True)


def apply_install_plan(
    plan: List[Dict[str, Any]],
    root_dir: Path,
    from_version: str = "",
    copy_func: Optional[Callable[[Path, Path], bool]] = None,
    keep_backups: int = 2,
) -> Dict[str, Any]:
    """Sao lưu file sắp đổi, cài file mới và tự khôi phục nếu có bất kỳ lỗi nào."""
    root_dir = Path(root_dir)
    copier = copy_func or _copy_with_lock_fallback
    changed = [
        item
        for item in plan
        if not item["dst"].is_file() or sha256_file(item["dst"]) != item["sha256"]
    ]
    if not changed:
        return {"changed_count": 0, "backup_dir": ""}

    saved = [item for item in changed if item["dst"].is_file()]
    needed = sum(item["src"].stat().st_size for item in changed)
    needed += sum(item["dst"].stat().st_size for item in saved)
    if shutil.disk_usage(root_dir).free < needed + MIN_FREE_BYTES:
        raise UpdateInstallError("Ổ đĩa không đủ dung lượng để cập nhật an toàn.")

    safe_version = re.sub(r"[^A-Za-z0-9._-]", "_", from_version or "unknown")
    backup_root = root_dir / BACKUP_DIR_NAME
    backup_dir = backup_root / f"{time.strftime('%Y%m%d_%H%M%S')}_{safe_version}"
    suffix = 1
    while backup_dir.exists():
        suffix += 1
        backup_dir = backup_root / f"{time.strftime('%Y%m%d_%H%M%S')}_{safe_version}_{suffix}"
    try:
        for item in saved:
            target = backup_dir / "files" / item["rel"]
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item["dst"], target)
        backup_dir.mkdir(parents=True, exist_ok=True)
        (backup_dir / BACKUP_INDEX_NAME).write_text(
            json.dumps(
                {
                    "from_version": from_version,
                    "saved": [item["rel"] for item in saved],
                    "created": [item["rel"] for item in changed if item not in saved],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
    except OSError as exc:
        shutil.rmtree(backup_dir, ignore_errors=True)
        raise UpdateInstallError(f"Không sao lưu được bản hiện tại: {exc}") from exc

    for item in changed:
        copied = False
        try:
            copied = bool(copier(item["src"], item["dst"])) and (
                sha256_file(item["dst"]) == item["sha256"]
            )
        except OSError:
            copied = False
        if not copied:
            restore_errors = restore_backup(backup_dir, root_dir)
            if restore_errors:
                raise UpdateInstallError(
                    f"Không cài được {item['rel']} và còn {len(restore_errors)} file chưa khôi phục. "
                    f"Bản sao lưu nằm tại: {backup_dir}"
                )
            raise UpdateInstallError(
                f"Không cài được {item['rel']}. Đã khôi phục nguyên trạng bản cũ."
            )

    _prune_backups(backup_root, keep_backups)
    return {"changed_count": len(changed), "backup_dir": str(backup_dir)}


def write_rollback_marker(root_dir: Path, backup_dir: str, from_version: str, to_version: str) -> None:
    """Đánh dấu bản mới chưa khởi động thành công để helper tự khôi phục nếu cần."""
    logs_dir = Path(root_dir) / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    (logs_dir / ROLLBACK_MARKER_NAME).write_text(
        json.dumps(
            {
                "backup_dir": str(backup_dir),
                "from_version": from_version,
                "to_version": to_version,
                "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def _read_local_version(root_dir: Path) -> Dict[str, Any]:
    try:
        data = json.loads((Path(root_dir) / "version.json").read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _main(argv: Optional[List[str]] = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Xác minh và cài gói cập nhật OTA")
    parser.add_argument("command", choices=("verify", "install"))
    parser.add_argument("--package", required=True, type=Path)
    parser.add_argument("--root", required=True, type=Path)
    args = parser.parse_args(argv)

    local_info = _read_local_version(args.root)
    try:
        manifest = verify_update_package(
            args.package, local_build=int(local_info.get("build_number", 0) or 0)
        )
        if args.command == "verify":
            print(f"OK: gói Build #{manifest['build_number']} đúng chữ ký.")
            return 0
        # Không ghi đè chính file .bat đang chạy vì cmd.exe đọc file theo từng dòng.
        plan = build_install_plan(
            args.package,
            args.root,
            manifest,
            skip_root_files=("Cap_Nhat_Nhanh.bat",),
        )
        result = apply_install_plan(
            plan, args.root, from_version=str(local_info.get("version", ""))
        )
        print(f"OK: đã cài {result['changed_count']} file thay đổi.")
        return 0
    except (UpdateVerificationError, UpdateInstallError) as exc:
        print(f"LỖI: {exc}")
        return 2


if __name__ == "__main__":
    sys.exit(_main())
