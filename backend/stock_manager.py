# -*- coding: utf-8 -*-
"""
Quản lý Kho Video Stock Có Sẵn (Local STOOK Directory)
Đã loại bỏ hoàn toàn phần tải Stock tự động (YouTube / Pexels / Pixabay / Cloud Note).
Chỉ quét, xoay vòng và cấp phát từ kho STOOK có sẵn trên máy.
"""
import os
import sys
import json
import time
import threading
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def get_video_duration(file_path: str) -> float:
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        file_path,
    ]
    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        return float(res.stdout.strip())
    except Exception:
        return 0.0


class StockManager:
    """Quản lý kho video Stock có sẵn trên ổ cứng (STOOK/)."""

    def __init__(self, base_dir: Path):
        self.base_dir = Path(base_dir)
        self.config_file = self.base_dir / "stook_config.json"
        self.used_history_file = self.base_dir / "used_stocks_history.json"
        self._lock = threading.Lock()

        saved_dir = self._load_saved_stook_dir()
        if saved_dir and Path(saved_dir).exists():
            self.stook_dir = Path(saved_dir)
        else:
            self.stook_dir = self.base_dir / "STOOK"
            self.stook_dir.mkdir(parents=True, exist_ok=True)

        self.inventory_file = self.stook_dir / "stock_inventory.json"

    def _load_saved_stook_dir(self) -> Optional[str]:
        if self.config_file.exists():
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    return json.load(f).get("stook_dir")
            except Exception:
                pass
        return None

    def save_stook_dir(self, dir_path: str):
        try:
            data = {}
            if self.config_file.exists():
                with open(self.config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
            data["stook_dir"] = str(dir_path)
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def set_stook_dir(self, new_dir: str) -> Dict[str, Any]:
        p = Path(new_dir)
        if not p.exists() or not p.is_dir():
            raise ValueError(f"Thư mục không tồn tại: {new_dir}")
        self.stook_dir = p
        self.inventory_file = self.stook_dir / "stock_inventory.json"
        self.save_stook_dir(str(p))
        return self.scan_and_update_inventory()

    def load_inventory(self) -> Dict[str, Any]:
        if self.inventory_file.exists():
            try:
                with open(self.inventory_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {"items": {}}

    def save_inventory(self, data: Dict[str, Any]):
        try:
            self.stook_dir.mkdir(parents=True, exist_ok=True)
            with open(self.inventory_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def load_used_history(self) -> Dict[str, Any]:
        if self.used_history_file.exists():
            try:
                with open(self.used_history_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {"used_items": {}}

    def save_used_history(self, data: Dict[str, Any]):
        try:
            with open(self.used_history_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def scan_and_update_inventory(self) -> Dict[str, Any]:
        """Quét toàn bộ file video có sẵn trong thư mục STOOK."""
        with self._lock:
            current_data = self.load_inventory()
            items = current_data.get("items", {})
            video_extensions = {".mp4", ".mov", ".mkv", ".webm"}
            found_files: List[Path] = []

            if self.stook_dir.exists():
                for root, _, files in os.walk(self.stook_dir):
                    for file in files:
                        if file.startswith("_") or file.endswith((".tmp", ".part")):
                            continue
                        if os.path.splitext(file)[1].lower() in video_extensions:
                            found_files.append(Path(root) / file)

            used_history = self.load_used_history().get("used_items", {})
            updated_items: Dict[str, Any] = {}

            for p in found_files:
                try:
                    file_size_bytes = p.stat().st_size
                    if file_size_bytes < 50_000:
                        continue
                except Exception:
                    continue

                rel_path = str(p.relative_to(self.stook_dir)).replace("\\", "/")
                item_id = rel_path.replace("/", "_").replace(".", "_")
                existing = items.get(item_id, {})

                duration = float(existing.get("duration", 0.0) or 0.0)
                if duration <= 0:
                    duration = get_video_duration(str(p))

                hist_entry = used_history.get(p.name) or used_history.get(rel_path) or used_history.get(item_id) or {}
                usage_count = max(int(hist_entry.get("usage_count", 0)), int(existing.get("usage_count", 0)))
                used_projects = hist_entry.get("used_in_projects") or existing.get("used_in_projects") or []
                last_used = hist_entry.get("last_used_at") or existing.get("last_used_at")

                updated_items[item_id] = {
                    "id": item_id,
                    "name": p.name,
                    "rel_path": rel_path,
                    "abs_path": str(p),
                    "duration": duration,
                    "duration_formatted": f"{int(duration // 60):02d}:{int(duration % 60):02d}",
                    "size_mb": round(file_size_bytes / (1024 * 1024), 2),
                    "size_bytes": file_size_bytes,
                    "usage_count": usage_count,
                    "used_in_projects": used_projects,
                    "last_used_at": last_used,
                    "status": "available",
                }

            current_data["items"] = updated_items
            current_data["last_scan"] = time.strftime("%Y-%m-%d %H:%M:%S")
            self.save_inventory(current_data)
            return current_data

    def get_all_stocks(self) -> Dict[str, Any]:
        data = self.load_inventory()
        raw_items = data.get("items", {})
        valid_items = [
            x for x in raw_items.values()
            if x.get("abs_path") and os.path.exists(x["abs_path"])
        ]
        if len(valid_items) != len(raw_items) or (not valid_items and self.stook_dir.exists()):
            data = self.scan_and_update_inventory()
            valid_items = list(data.get("items", {}).values())

        # Sắp xếp ưu tiên file ít dùng nhất lên đầu
        valid_items.sort(key=lambda x: (int(x.get("usage_count", 0)), x.get("rel_path", "")))
        raw_seconds = sum(float(x.get("duration", 0.0)) for x in valid_items)
        raw_hours = round(raw_seconds / 3600.0, 2)

        return {
            "total": len(valid_items),
            "available_count": len(valid_items),
            "available_uses_count": len(valid_items),
            "available_raw_hours": raw_hours,
            "available_effective_hours": round(raw_hours * 1.5, 2),
            "used_count": sum(1 for x in valid_items if int(x.get("usage_count", 0)) > 0),
            "current_stook_dir": str(self.stook_dir),
            "items": valid_items,
        }

    def get_best_available_stock(self, exclude_ids: Optional[set] = None) -> Optional[Dict[str, Any]]:
        """
        Chọn video Stock có sẵn trong kho STOOK (ưu tiên file có số lần dùng thấp nhất và chưa nằm trong exclude_ids).
        Nếu tất cả file trong kho đều nằm trong exclude_ids của cùng 1 video dài, tự động cho phép xoay vòng kèm lật ngang (hflip).
        """
        stocks = self.get_all_stocks()
        items = [
            x for x in stocks.get("items", [])
            if x.get("abs_path") and os.path.exists(x["abs_path"])
        ]
        if not items:
            return None

        ex = exclude_ids or set()
        fresh_candidates = [
            x for x in items
            if x["id"] not in ex and x["abs_path"] not in ex and f"{x['id']}::use1" not in ex
        ]
        if fresh_candidates:
            chosen = dict(fresh_candidates[0])
            chosen["use_number"] = 1
            chosen["flip_horizontal"] = False
            chosen["zoom_factor"] = 1.0
            chosen["transform_label"] = "Bản Gốc (Kho STOOK có sẵn)"
            chosen["slot_key"] = f"{chosen['id']}::use1"
            return chosen

        # Xoay vòng lượt 2 (lật ngang) nếu kịch bản dài hơn tổng các file hiện có
        flipped_candidates = [
            x for x in items
            if f"{x['id']}::use2" not in ex
        ]
        chosen = dict(flipped_candidates[0] if flipped_candidates else items[0])
        chosen["use_number"] = 2
        chosen["flip_horizontal"] = True
        chosen["zoom_factor"] = 1.05
        chosen["transform_label"] = "Xoay vòng Lật Ngang (hflip)"
        chosen["slot_key"] = f"{chosen['id']}::use2"
        return chosen

    def mark_as_used(self, stock_id_or_path: str, project_name: str) -> int:
        """Ghi nhận lượt sử dụng để xoay vòng đều các file trong kho STOOK (KHÔNG xóa file)."""
        with self._lock:
            data = self.load_inventory()
            items = data.get("items", {})
            target_id = None
            target_item = None
            for k, v in items.items():
                if k == stock_id_or_path or v.get("abs_path") == stock_id_or_path or v.get("name") == stock_id_or_path:
                    target_id = k
                    target_item = v
                    break

            now_str = time.strftime("%Y-%m-%d %H:%M:%S")
            new_count = 1
            if target_id and target_id in items:
                new_count = int(items[target_id].get("usage_count", 0)) + 1
                items[target_id]["usage_count"] = new_count
                if project_name not in items[target_id].get("used_in_projects", []):
                    items[target_id].setdefault("used_in_projects", []).append(project_name)
                items[target_id]["last_used_at"] = now_str
                self.save_inventory(data)

            history = self.load_used_history()
            used_items = history.setdefault("used_items", {})
            lookup_key = target_item["name"] if target_item else Path(stock_id_or_path).name
            entry = used_items.get(lookup_key, {})
            entry["name"] = lookup_key
            entry["usage_count"] = new_count
            entry["last_used_at"] = now_str
            if project_name not in entry.get("used_in_projects", []):
                entry.setdefault("used_in_projects", []).append(project_name)
            used_items[lookup_key] = entry
            self.save_used_history(history)
            return new_count

    def reset_all_usage(self) -> Dict[str, Any]:
        """Đặt lại bộ đếm lượt dùng về 0 cho toàn bộ kho STOOK."""
        with self._lock:
            self.save_used_history({"used_items": {}})
            data = self.load_inventory()
            for item in data.get("items", {}).values():
                item["usage_count"] = 0
                item["used_in_projects"] = []
                item["last_used_at"] = None
            self.save_inventory(data)
        return self.get_all_stocks()
