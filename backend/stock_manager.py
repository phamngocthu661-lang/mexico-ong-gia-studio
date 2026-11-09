import glob
import http.cookiejar
import json
import os
import random
import re
import shutil
import subprocess
import time
import urllib.parse
import urllib.request
from typing import Dict, List, Optional

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_STOOK_DIR = os.path.join(BASE_DIR, "STOOK")
STOOK_CONFIG_FILE = os.path.join(BASE_DIR, "config", "stook_config.json")
GLOBAL_USED_LINKS_FILE = os.path.join(BASE_DIR, "config", "used_stock_links.json")
YT_COOKIES_FILE = os.path.join(BASE_DIR, "config", "youtube_cookies.txt")

# Link File Note Online RIÊNG BIỆT của Mexico Ông Già Studio (Không đồng bộ với Key Nhật cũ, tải lại từ đầu & theo dõi chống trùng độc lập)
DEFAULT_CLOUD_NOTE_SLUG = "mexico-ong-gia-stock-8a9b2c"
DEFAULT_CLOUD_NOTE_EDIT_CODE = "mexico2026"
CLOUD_KV_NAMESPACE_PREFIX = "mexico_ong_gia"

# API Key mặc định Pexels & Pixabay (Kho video miễn phí bản quyền 100%, tải trực tiếp CDN tốc độ cao)
DEFAULT_PEXELS_API_KEY = os.environ.get(
    "PEXELS_API_KEY", "563492ad6f91700001000001a4c8d1f2e7a948a3b8e9f6c5d4e3b2a1"
)
DEFAULT_PIXABAY_API_KEY = os.environ.get(
    "PIXABAY_API_KEY", "43463603-8d9f7b5c6a1e2f3d4c5b6a7e8"
)

# Bộ từ khóa tìm kiếm video cảnh thiên nhiên / đồng quê / đường phố / phong cảnh phù hợp dự án Mexico Ông Già trên Pexels & Pixabay
PEXELS_PIXABAY_QUERIES = [
    "countryside road nature landscape",
    "mountain valley clouds timelapse",
    "autumn forest trees wind",
    "sunset desert horizon landscape",
    "peaceful village street morning",
    "river stream forest nature",
    "rain window city night",
    "ocean waves sunset beach",
    "aerial nature mountains forest",
    "rural farm field golden hour",
    "cinematic clouds sky sunset",
    "quiet park trees walking path",
]

# Các trình duyệt hỗ trợ tự động trích xuất Cookie YouTube
SUPPORTED_COOKIE_BROWSERS = ["chrome", "edge", "brave", "firefox"]

# Tìm ffmpeg & ffprobe trong thư mục bin nội bộ
LOCAL_FFMPEG = os.path.join(BASE_DIR, "bin", "ffmpeg.exe")
LOCAL_FFPROBE = os.path.join(BASE_DIR, "bin", "ffprobe.exe")
FFMPEG_CMD = LOCAL_FFMPEG if os.path.exists(LOCAL_FFMPEG) else "ffmpeg"
FFPROBE_CMD = LOCAL_FFPROBE if os.path.exists(LOCAL_FFPROBE) else "ffprobe"

# Mục tiêu số giờ video stock luôn có sẵn trong kho (Mặc định: 30 giờ = 60 part 30 phút)
DEFAULT_TARGET_STOCK_HOURS = 30.0
DEFAULT_SLICE_MINUTES = 30
# Chế độ 1 (auto_download): dùng đúng 1 lần rồi tự xóa. Chế độ 2 (local_available): xoay vòng kho sẵn có không giới hạn.
MAX_STOCK_USAGES = 1

# Hai chế độ nguồn Stock:
# - "auto_download": 1. Dùng Stock Tải Về Tự Động (Pexels / Pixabay / YouTube • Theo dõi link chống trùng, dùng xong tự xóa)
# - "local_available": 2. Dùng Stock Sẵn Có Trong Máy (Xoay vòng kho STOOK • Không tải mạng, giữ nguyên file)
STOCK_MODE_AUTO_DOWNLOAD = "auto_download"
STOCK_MODE_LOCAL_AVAILABLE = "local_available"

# Bộ từ khóa tự động tìm kiếm video cảnh thiên nhiên / phong cảnh dài trên YouTube để tải 720p làm Stock nền
AUTO_SEARCH_QUERIES = [
    "4K nature relaxation film drone landscape no copyright",
    "scenic countryside driving 4k relaxing nature",
    "peaceful mountain forest river 4k ambient video",
    "aerial view mountains valleys nature 4k",
    "cinematic nature landscapes 4k 60fps",
    "relaxing nature scenery forest stream 4k",
    "sunset clouds timelapse 4k nature",
    "desert canyon aerial 4k landscape",
    "autumn forest walk 4k nature video",
    "ocean waves coastline 4k relaxing scenery",
    "countryside road trip scenic drive 4k",
    "rainy day nature forest window 4k",
]


class StockManager:
    """
    Quản lý kho video nền (STOOK) cho Mexico Ông Già Studio với 2 chế độ:
    1. 'auto_download' (Dùng Stock Tải Về):
       - Tự động tải video từ Pexels / Pixabay / YouTube và cắt thành các cuộn 30 phút.
       - Lưu lịch sử link trên File Note Online riêng (https://rentry.co/mexico-ong-gia-stock-8a9b2c) & used_stock_links.json để chống trùng lặp 100%.
       - Mỗi cuộn dùng 1 lần và tự động xóa sau khi xuất xong video để giải phóng ổ cứng.
    2. 'local_available' (Dùng Stock Sẵn Có):
       - Sử dụng các file video (.mp4, .mov, .mkv) đang có sẵn trong thư mục STOOK.
       - Không tự động tải từ mạng và KHÔNG BAO GIỜ xóa file gốc sau khi render (xoay vòng lượt dùng thông minh).
    """

    def __init__(self, stook_dir: str = None):
        resolved_dir = None
        if stook_dir is not None:
            cand = os.path.abspath(str(stook_dir))
            # Nếu truyền vào root_dir của dự án (chứa thư mục con STOOK), tự động đọc _load_custom_stook_dir() hoặc trỏ vào STOOK
            if os.path.normcase(cand) == os.path.normcase(BASE_DIR) or os.path.isdir(
                os.path.join(cand, "STOOK")
            ):
                resolved_dir = self._load_custom_stook_dir()
            else:
                resolved_dir = cand
        self.stook_dir = str(resolved_dir or self._load_custom_stook_dir())
        os.makedirs(self.stook_dir, exist_ok=True)
        self.inventory_file = os.path.join(self.stook_dir, "stock_inventory.json")
        self.local_used_links_file = os.path.join(
            self.stook_dir, "used_stock_links.json"
        )
        self._ensure_mexico_cloud_note_config()
        self.inventory = self._load_inventory()

    def _load_config_dict(self) -> Dict:
        if os.path.exists(STOOK_CONFIG_FILE):
            try:
                with open(STOOK_CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        return data
            except Exception as e:
                print(f"[StockManager] Lỗi đọc cấu hình stook_config.json: {e}")
        return {}

    def _save_config_dict(self, data: Dict):
        try:
            with open(STOOK_CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[StockManager] Lỗi lưu stook_config.json: {e}")

    def _ensure_mexico_cloud_note_config(self):
        """Đảm bảo cấu hình Note Online dùng link riêng của Mexico Ông Già (không dính link Key Nhật cũ)."""
        cfg = self._load_config_dict()
        changed = False
        slug = str(cfg.get("cloud_note_slug", "")).strip()
        if not slug or "nhat-drama" in slug:
            cfg["cloud_note_slug"] = DEFAULT_CLOUD_NOTE_SLUG
            cfg["cloud_note_edit_code"] = DEFAULT_CLOUD_NOTE_EDIT_CODE
            changed = True
        if cfg.get("stock_source_mode") not in (
            STOCK_MODE_AUTO_DOWNLOAD,
            STOCK_MODE_LOCAL_AVAILABLE,
        ):
            cfg["stock_source_mode"] = STOCK_MODE_AUTO_DOWNLOAD
            changed = True
        if changed:
            self._save_config_dict(cfg)

    def _load_custom_stook_dir(self) -> str:
        """Đọc đường dẫn kho STOOK tùy chỉnh nếu người dùng đã cấu hình."""
        data = self._load_config_dict()
        custom_dir = data.get("stook_dir", "").strip()
        if custom_dir:
            norm_custom = os.path.abspath(custom_dir)
            norm_default = os.path.abspath(DEFAULT_STOOK_DIR)
            # Nếu đường dẫn cũ không còn tồn tại trong khi DEFAULT_STOOK_DIR có sẵn
            if norm_custom != norm_default and not os.path.exists(norm_custom):
                if os.path.exists(norm_default):
                    data["stook_dir"] = norm_default
                    self._save_config_dict(data)
                    return norm_default
            try:
                os.makedirs(norm_custom, exist_ok=True)
                return norm_custom
            except Exception:
                pass
        return DEFAULT_STOOK_DIR

    def get_stock_source_mode(self) -> str:
        """Lấy chế độ nguồn Stock hiện tại ('auto_download' hoặc 'local_available')."""
        data = self._load_config_dict()
        mode = str(data.get("stock_source_mode", STOCK_MODE_AUTO_DOWNLOAD)).strip()
        if mode not in (STOCK_MODE_AUTO_DOWNLOAD, STOCK_MODE_LOCAL_AVAILABLE):
            return STOCK_MODE_AUTO_DOWNLOAD
        return mode

    def set_stock_source_mode(self, mode: str) -> Dict:
        """Chuyển đổi giữa 2 chế độ: 'auto_download' (1. Dùng Stock Tải Về) và 'local_available' (2. Dùng Stock Sẵn Có)."""
        clean_mode = str(mode or "").strip().lower()
        if clean_mode not in (STOCK_MODE_AUTO_DOWNLOAD, STOCK_MODE_LOCAL_AVAILABLE):
            clean_mode = STOCK_MODE_AUTO_DOWNLOAD
        data = self._load_config_dict()
        data["stock_source_mode"] = clean_mode
        self._save_config_dict(data)
        self.scan_and_sync()
        return self.get_all_stocks_info()

    def set_stook_dir(self, new_dir: str) -> Dict:
        """Thay đổi thư mục STOOK và quét lại dữ liệu."""
        if not new_dir or not new_dir.strip():
            raise ValueError("Đường dẫn thư mục không được để trống.")
        clean_dir = os.path.abspath(new_dir.strip())
        os.makedirs(clean_dir, exist_ok=True)

        self.stook_dir = clean_dir
        self.inventory_file = os.path.join(self.stook_dir, "stock_inventory.json")
        self.local_used_links_file = os.path.join(
            self.stook_dir, "used_stock_links.json"
        )

        data = self._load_config_dict()
        data["stook_dir"] = clean_dir
        self._save_config_dict(data)

        self.inventory = self._load_inventory()
        return self.get_all_stocks_info()

    def get_stook_dir(self) -> str:
        return self.stook_dir

    # =========================================================================
    # QUẢN LÝ LỊCH SỬ LINK YOUTUBE / PEXELS / PIXABAY ĐÃ TẢI & ĐỒNG BỘ CLOUD NOTE
    # =========================================================================
    def _get_cloud_note_config(self) -> Dict[str, str]:
        """Lấy cấu hình URL Note Online riêng của Mexico Ông Già Studio."""
        data = self._load_config_dict()
        slug = str(data.get("cloud_note_slug", DEFAULT_CLOUD_NOTE_SLUG)).strip()
        edit_code = str(
            data.get("cloud_note_edit_code", DEFAULT_CLOUD_NOTE_EDIT_CODE)
        ).strip()
        if not slug or "nhat-drama" in slug:
            slug = DEFAULT_CLOUD_NOTE_SLUG
            edit_code = DEFAULT_CLOUD_NOTE_EDIT_CODE
        return {
            "slug": slug,
            "edit_code": edit_code,
            "url": f"https://rentry.co/{slug}",
            "raw_url": f"https://rentry.co/{slug}/raw",
        }

    def get_cloud_note_info(self) -> Dict:
        """Trả về thông tin hiển thị của File Note Online chống trùng."""
        cfg = self._get_cloud_note_config()
        used_ids = self.load_used_yt_links()
        return {
            "cloud_note_url": cfg["url"],
            "cloud_note_raw_url": cfg["raw_url"],
            "cloud_note_slug": cfg["slug"],
            "total_used_links": len(used_ids),
        }

    def _format_cloud_note_markdown(self, used_ids: Dict[str, Dict]) -> str:
        """Định dạng nội dung bảng danh sách link Stock đã tải để ghi lên File Note Online."""
        lines = [
            "# 🎬 MEXICO ÔNG GIÀ STUDIO — KHO LƯU TRỮ LINK STOCK CHỐNG TRÙNG LẶP",
            f"- **Tổng số Video đã khóa (Không tải lại):** `{len(used_ids)}`",
            f"- **Cập nhật lần cuối:** `{time.strftime('%Y-%m-%d %H:%M:%S')}`",
            "",
            "| # | Mã Video ID | Thời Gian Tải | Nguồn / Tiêu Đề | Link Gốc |",
            "|---|---|---|---|---|",
        ]
        sorted_items = sorted(
            used_ids.values(),
            key=lambda x: str(x.get("downloaded_at", "")),
            reverse=True,
        )
        for idx, info in enumerate(sorted_items, start=1):
            vid = str(info.get("id", "")).strip()
            if not vid:
                continue
            dt = str(info.get("downloaded_at", "")).strip() or "N/A"
            title = (
                str(info.get("title", ""))
                .replace("|", "-")
                .replace("\n", " ")
                .strip()[:65]
            )
            url = str(info.get("url", f"https://www.youtube.com/watch?v={vid}")).strip()
            lines.append(f"| {idx} | `{vid}` | {dt} | {title} | {url} |")
        return "\n".join(lines) + "\n"

    def _get_cloud_kv_url(self, slug: str) -> str:
        """Tạo URL khóa KV đám mây dự phòng riêng cho Mexico Ông Già Studio (tách biệt hoàn toàn khỏi Key Nhật)."""
        safe_key = re.sub(r"[^a-zA-Z0-9]", "", slug) or "mexicoonggiastock"
        return f"https://keyvalue.immanuel.co/api/KeyVal/GetValue/4x9b2k8m/{CLOUD_KV_NAMESPACE_PREFIX}_{safe_key}"

    def _get_cloud_kv_update_url(self, slug: str, val_encoded: str) -> str:
        safe_key = re.sub(r"[^a-zA-Z0-9]", "", slug) or "mexicoonggiastock"
        return f"https://keyvalue.immanuel.co/api/KeyVal/UpdateValue/4x9b2k8m/{CLOUD_KV_NAMESPACE_PREFIX}_{safe_key}/{val_encoded}"

    def _pull_from_rentry(self, slug: str) -> Optional[Dict[str, Dict]]:
        """Đọc danh sách ID từ trang Note Online (https://rentry.co/<slug>) và Cloud KV dự phòng."""
        pulled: Dict[str, Dict] = {}
        got_response = False

        # 1. Đọc từ Rentry (thử API và trang HTML của Note)
        for target_url in [
            f"https://rentry.co/api/raw/{slug}",
            f"https://rentry.co/{slug}",
        ]:
            try:
                req = urllib.request.Request(
                    target_url,
                    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
                )
                with urllib.request.urlopen(req, timeout=10) as resp:
                    if resp.status == 200:
                        body = resp.read().decode("utf-8", errors="ignore")
                        if target_url.endswith(f"/api/raw/{slug}"):
                            data = json.loads(body)
                            text = data.get("content", "")
                        else:
                            text = body
                        if text and "Access Code Required" not in text:
                            got_response = True
                            # Parse dòng Markdown chuẩn: | 1 | `683p4Ubg2NU` | 2026-... | Title | URL |
                            for line in text.splitlines():
                                line = line.strip()
                                if line.startswith("|") and "`" in line:
                                    parts = [
                                        p.strip() for p in line.strip("|").split("|")
                                    ]
                                    if len(parts) >= 5:
                                        vid_match = re.search(r"`([^`]+)`", parts[1])
                                        if vid_match:
                                            vid = vid_match.group(1).strip()
                                            pulled[vid] = {
                                                "id": vid,
                                                "downloaded_at": parts[2],
                                                "title": parts[3],
                                                "url": parts[4],
                                            }
                            # Nếu là HTML trang Rentry: quét thêm thẻ <code>VID</code>
                            for m in re.finditer(
                                r"<code>([A-Za-z0-9_-]{6,24})</code>", text
                            ):
                                vid = m.group(1).strip()
                                if vid and vid not in pulled and vid != "0":
                                    pulled[vid] = {
                                        "id": vid,
                                        "downloaded_at": "Synced from Cloud Note",
                                        "title": "Synced from Rentry Note",
                                        "url": f"https://www.youtube.com/watch?v={vid}",
                                    }
                        if pulled:
                            break
            except Exception:
                pass

        # 2. Đọc bổ sung từ Cloud KV (JSON đồng bộ tức thời giữa các máy Mexico Ông Già)
        try:
            kv_url = self._get_cloud_kv_url(slug)
            req = urllib.request.Request(kv_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                if resp.status == 200:
                    got_response = True
                    raw_val = (
                        resp.read().decode("utf-8", errors="ignore").strip().strip('"')
                    )
                    if raw_val and raw_val != "null":
                        ids_list = [x.strip() for x in raw_val.split(",") if x.strip()]
                        for vid in ids_list:
                            if vid not in pulled:
                                pulled[vid] = {
                                    "id": vid,
                                    "downloaded_at": "Synced from Cloud",
                                    "title": "Synced from Multi-Machine Cloud Note",
                                    "url": f"https://www.youtube.com/watch?v={vid}",
                                }
        except Exception:
            pass

        return pulled if got_response else None

    def _push_to_rentry(
        self,
        slug: str,
        edit_code: str,
        markdown_text: str,
        used_ids: Dict[str, Dict] = None,
    ) -> bool:
        """Cập nhật (hoặc tạo mới) nội dung lên File Note Online (Rentry.co) và Cloud KV."""
        rentry_ok = False
        try:
            cj = http.cookiejar.CookieJar()
            opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                "Referer": f"https://rentry.co/{slug}",
            }

            req_get = urllib.request.Request("https://rentry.co", headers=headers)
            with opener.open(req_get, timeout=10) as resp:
                html = resp.read().decode("utf-8", errors="ignore")

            csrf_match = re.search(
                r'name=["\']csrfmiddlewaretoken["\']\s+value=["\']([^"\']+)["\']', html
            )
            if csrf_match:
                csrf_token = csrf_match.group(1)
                form_data = urllib.parse.urlencode(
                    {
                        "csrfmiddlewaretoken": csrf_token,
                        "text": markdown_text,
                        "edit_code": edit_code,
                    }
                ).encode("utf-8")

                req_edit = urllib.request.Request(
                    f"https://rentry.co/api/edit/{slug}",
                    data=form_data,
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                        "Referer": f"https://rentry.co/{slug}/edit",
                        "Content-Type": "application/x-www-form-urlencoded",
                    },
                    method="POST",
                )
                with opener.open(req_edit, timeout=12) as resp_edit:
                    res_json = json.loads(
                        resp_edit.read().decode("utf-8", errors="ignore")
                    )
                    if str(res_json.get("status")) == "200":
                        rentry_ok = True
        except Exception as e:
            print(f"[StockManager] Lưu ý khi đẩy lên Rentry Note ({slug}): {e}")

        # Đồng bộ song song danh sách mã ID lên Cloud KV riêng của Mexico Ông Già
        kv_ok = False
        if used_ids is not None:
            try:
                compact_ids = ",".join(list(used_ids.keys())[-300:])
                if compact_ids:
                    val_encoded = urllib.parse.quote(compact_ids, safe="")
                    kv_update_url = self._get_cloud_kv_update_url(slug, val_encoded)
                    req_kv = urllib.request.Request(
                        kv_update_url,
                        data=b"",
                        headers={"User-Agent": "Mozilla/5.0"},
                        method="POST",
                    )
                    with urllib.request.urlopen(req_kv, timeout=8) as r_kv:
                        if r_kv.status == 200:
                            kv_ok = True
            except Exception:
                pass

        return rentry_ok or kv_ok

    def sync_cloud_used_links(self, push_if_needed: bool = True) -> Dict:
        """
        Đồng bộ 2 chiều giữa danh sách link đã tải trên máy cục bộ và File Note Online (https://rentry.co/mexico-ong-gia-stock-8a9b2c).
        Đảm bảo các máy Mexico Ông Già dùng chung hoặc cài lại máy không bao giờ tải trùng lại video cũ,
        nhưng tách biệt 100% với dự án Key Nhật cũ.
        """
        cfg = self._get_cloud_note_config()
        slug = cfg["slug"]
        edit_code = cfg["edit_code"]

        local_ids = self._load_local_used_yt_links_only()
        cloud_ids = self._pull_from_rentry(slug)

        merged_ids = dict(local_ids)
        new_from_cloud = 0
        if cloud_ids is not None:
            for vid, info in cloud_ids.items():
                if vid not in merged_ids:
                    merged_ids[vid] = info
                    new_from_cloud += 1

        if new_from_cloud > 0:
            self._save_local_used_links(merged_ids)

        pushed = False
        if push_if_needed:
            if cloud_ids is None or len(merged_ids) > len(cloud_ids):
                md_text = self._format_cloud_note_markdown(merged_ids)
                pushed = self._push_to_rentry(
                    slug, edit_code, md_text, used_ids=merged_ids
                )

        return {
            "success": True,
            "cloud_note_url": cfg["url"],
            "cloud_note_raw_url": cfg["raw_url"],
            "total_synced_ids": len(merged_ids),
            "new_from_cloud": new_from_cloud,
            "pushed_to_cloud": pushed,
        }

    def _load_local_used_yt_links_only(self) -> Dict[str, Dict]:
        """Chỉ đọc lịch sử các video ID đã từng tải trên ổ cứng cục bộ."""
        used_ids: Dict[str, Dict] = {}
        for fpath in [GLOBAL_USED_LINKS_FILE, self.local_used_links_file]:
            if os.path.exists(fpath):
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        if isinstance(data, dict):
                            items = data.get("used_video_ids", data)
                            if isinstance(items, dict):
                                used_ids.update(items)
                except Exception as e:
                    print(f"[StockManager] Lỗi đọc {fpath}: {e}")

        # Quét thêm các file thực tế đang có trong STOOK (trường hợp file tải trước đó)
        if os.path.exists(self.stook_dir):
            for fname in os.listdir(self.stook_dir):
                m = re.match(r"^stock_([A-Za-z0-9_-]{6,15})_part\d+\.mp4$", fname)
                if m:
                    vid = m.group(1)
                    if vid not in used_ids and not vid.startswith("PXPB_"):
                        used_ids[vid] = {
                            "id": vid,
                            "url": f"https://www.youtube.com/watch?v={vid}",
                            "title": f"Existing Stock ({fname})",
                            "downloaded_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                        }
        return used_ids

    def _save_local_used_links(self, used_ids: Dict[str, Dict]):
        """Ghi danh sách link đã tải xuống cả 2 file JSON cục bộ."""
        cfg = self._get_cloud_note_config()
        payload = {
            "cloud_note_url": cfg["url"],
            "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_used_videos": len(used_ids),
            "used_video_ids": used_ids,
        }
        for fpath in [GLOBAL_USED_LINKS_FILE, self.local_used_links_file]:
            try:
                with open(fpath, "w", encoding="utf-8") as f:
                    json.dump(payload, f, ensure_ascii=False, indent=2)
            except Exception as e:
                print(f"[StockManager] Không thể ghi lịch sử link vào {fpath}: {e}")

    def load_used_yt_links(self) -> Dict[str, Dict]:
        """Đọc toàn bộ lịch sử các video ID đã từng tải về."""
        return self._load_local_used_yt_links_only()

    def record_used_yt_link(
        self, video_id: str, url: str, title: str = "", license_str: str = ""
    ):
        """Ghi nhận vĩnh viễn ID và đường dẫn video đã tải vào cả ổ cứng VÀ File Note Online."""
        if not video_id:
            return
        used_ids = self._load_local_used_yt_links_only()
        used_ids[video_id] = {
            "id": video_id,
            "url": url or f"https://www.youtube.com/watch?v={video_id}",
            "title": title,
            "license": license_str,
            "downloaded_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        self._save_local_used_links(used_ids)

        # Đẩy ngay danh sách mới lên File Note Online (Rentry.co)
        try:
            cfg = self._get_cloud_note_config()
            md_text = self._format_cloud_note_markdown(used_ids)
            self._push_to_rentry(
                cfg["slug"], cfg["edit_code"], md_text, used_ids=used_ids
            )
        except Exception as e:
            print(f"[StockManager] Lỗi đồng bộ Note Online khi ghi link mới: {e}")

    # =========================================================================
    # QUẢN LÝ INVENTORY KHO STOOK
    # =========================================================================
    def _load_inventory(self) -> Dict:
        """Tải sổ quản lý kho stock từ JSON, nếu chưa có thì khởi tạo."""
        if os.path.exists(self.inventory_file):
            try:
                with open(self.inventory_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"[StockManager] Lỗi đọc file inventory: {e}")
        return {"stocks": {}, "history": []}

    def _save_inventory(self):
        """Lưu trạng thái kho stock xuống đĩa."""
        try:
            with open(self.inventory_file, "w", encoding="utf-8") as f:
                json.dump(self.inventory, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[StockManager] Lỗi lưu file inventory: {e}")

    def _probe_video_duration(self, filepath: str) -> float:
        """Lấy thời lượng thực tế của video bằng ffprobe (giây)."""
        try:
            cmd = [
                FFPROBE_CMD,
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                filepath,
            ]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            return round(float(res.stdout.strip()), 2)
        except Exception:
            return 0.0

    def scan_and_sync(self) -> List[Dict]:
        """
        Quét thư mục STOOK để cập nhật các file video (.mp4, .mov, .mkv).
        - Ở chế độ 'auto_download': mỗi file tải về dùng tối đa 1 lần (max_uses=1), dùng xong đánh dấu 'used' và tự xóa.
        - Ở chế độ 'local_available': toàn bộ file có mặt trên ổ đĩa đều mở khóa 'available' để xoay vòng không giới hạn.
        """
        mode = self.get_stock_source_mode()
        extensions = ("*.mp4", "*.mov", "*.mkv")
        found_files = []
        for ext in extensions:
            found_files.extend(glob.glob(os.path.join(self.stook_dir, ext)))

        found_files = sorted(
            list(set(found_files)),
            key=lambda x: os.path.getmtime(x) if os.path.exists(x) else 0,
            reverse=True,
        )
        stocks_dict = self.inventory.get("stocks", {})

        active_filenames = set()
        for filepath in found_files:
            filename = os.path.basename(filepath)
            # Bỏ qua các file tạm đang tải/nối
            if filename.startswith("_") or ".temp." in filename or ".part" in filename:
                continue
            active_filenames.add(filename)

            try:
                size_bytes = os.path.getsize(filepath)
                size_mb = round(size_bytes / (1024 * 1024), 2)
            except Exception:
                size_bytes = 0
                size_mb = 0.0

            # Bỏ qua các file rỗng hoặc hỏng (< 1MB)
            if size_bytes < 1 * 1024 * 1024:
                continue

            if filename not in stocks_dict:
                duration = self._probe_video_duration(filepath)
                if duration < 5.0:
                    continue
                stocks_dict[filename] = {
                    "id": filename,
                    "name": filename,
                    "path": filepath,
                    "abs_path": filepath,
                    "rel_path": filename,
                    "size_mb": size_mb,
                    "duration_sec": duration,
                    "duration_formatted": self._format_duration(duration),
                    "status": "available",
                    "usage_count": 0,
                    "max_uses": MAX_STOCK_USAGES
                    if mode == STOCK_MODE_AUTO_DOWNLOAD
                    else 999999,
                    "used_in_projects": [],
                    "last_used_at": None,
                    "added_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                }
            else:
                stocks_dict[filename]["path"] = filepath
                stocks_dict[filename]["abs_path"] = filepath
                stocks_dict[filename]["rel_path"] = filename
                stocks_dict[filename]["size_mb"] = size_mb
                if stocks_dict[filename].get("duration_sec", 0) <= 0:
                    dur = self._probe_video_duration(filepath)
                    stocks_dict[filename]["duration_sec"] = dur
                    stocks_dict[filename]["duration_formatted"] = self._format_duration(
                        dur
                    )

                used_cnt = stocks_dict[filename].get("usage_count", 0)
                if mode == STOCK_MODE_LOCAL_AVAILABLE:
                    # Chế độ 2 (Dùng Stock Sẵn Có): Luôn giữ trạng thái 'available' để xoay vòng kho sẵn có
                    stocks_dict[filename]["max_uses"] = 999999
                    stocks_dict[filename]["status"] = "available"
                else:
                    # Chế độ 1 (Dùng Stock Tải Về): Chỉ dùng 1 lần rồi khóa/xóa
                    stocks_dict[filename]["max_uses"] = MAX_STOCK_USAGES
                    if used_cnt >= MAX_STOCK_USAGES or stocks_dict[filename].get(
                        "status"
                    ) in ("used", "deleted_after_use"):
                        stocks_dict[filename]["status"] = "used"
                    else:
                        stocks_dict[filename]["status"] = "available"

        for k in list(stocks_dict.keys()):
            if k not in active_filenames:
                item = stocks_dict[k]
                if item.get("usage_count", 0) > 0 or item.get("status") in (
                    "used",
                    "deleted_after_use",
                ):
                    item["status"] = "deleted_after_use"
                    item["size_mb"] = 0.0
                else:
                    del stocks_dict[k]

        self.inventory["stocks"] = stocks_dict
        self._save_inventory()
        return list(stocks_dict.values())

    def get_all_stocks_info(self) -> Dict:
        """Lấy toàn bộ danh sách stock và thống kê kho (kèm chế độ nguồn Stock hiện tại)."""
        mode = self.get_stock_source_mode()
        items = self.scan_and_sync()
        visible_items = [x for x in items if x.get("status") != "deleted_after_use"]

        if mode == STOCK_MODE_LOCAL_AVAILABLE:
            available = list(visible_items)
            used = []
            deleted_after_use = []
            total_avail_uses = len(available)
        else:
            available = [
                x
                for x in visible_items
                if x.get("usage_count", 0) < MAX_STOCK_USAGES
                and x.get("status") == "available"
            ]
            used = [
                x
                for x in visible_items
                if x.get("usage_count", 0) >= MAX_STOCK_USAGES
                or x.get("status") == "used"
            ]
            deleted_after_use = [
                x for x in items if x.get("status") == "deleted_after_use"
            ]
            total_avail_uses = sum(
                max(0, MAX_STOCK_USAGES - x.get("usage_count", 0)) for x in available
            )

        raw_avail_sec = sum(float(x.get("duration_sec", 0.0)) for x in available)
        effective_avail_sec = raw_avail_sec

        used_links = self.load_used_yt_links()
        cloud_info = self._get_cloud_note_config()

        return {
            "stock_source_mode": mode,
            "current_stook_dir": self.stook_dir,
            "total": len(visible_items),
            "available_count": len(available),
            "available_uses_count": total_avail_uses,
            "available_raw_hours": round(raw_avail_sec / 3600.0, 2),
            "available_effective_hours": round(effective_avail_sec / 3600.0, 2),
            "target_stock_hours": DEFAULT_TARGET_STOCK_HOURS,
            "used_count": len(used),
            "deleted_count": len(deleted_after_use),
            "used_links_count": len(used_links),
            "cloud_note_url": cloud_info["url"],
            "cloud_note_slug": cloud_info["slug"],
            "items": visible_items,
        }

    def select_best_stock(self, selection: str = "auto_unique") -> Optional[Dict]:
        """
        Chọn 1 file stock cho dự án mới theo đúng chế độ người dùng chọn:
        - Nếu selection == 'auto_download' hoặc đang ở chế độ 1 ('auto_download'):
          Chỉ lấy file mới chưa dùng (usage_count == 0). Dùng xong 1 lần sẽ xóa.
        - Nếu selection == 'local_available' hoặc đang ở chế độ 2 ('local_available'):
          Lấy file sẵn có trong thư mục STOOK có số lần dùng ít nhất (xoay vòng đều, lần chẵn lật ngang nhẹ để tạo sự mới mẻ, tuyệt đối không xóa file).
        """
        mode = self.get_stock_source_mode()
        if selection in (STOCK_MODE_AUTO_DOWNLOAD, STOCK_MODE_LOCAL_AVAILABLE):
            mode = selection
            self.set_stock_source_mode(mode)

        items = self.scan_and_sync()
        visible_items = [
            x
            for x in items
            if x.get("status") != "deleted_after_use"
            and os.path.exists(x.get("path", ""))
        ]

        # Nếu người dùng chọn đích danh 1 file cụ thể trong dropdown
        if selection and selection not in (
            "auto_unique",
            STOCK_MODE_AUTO_DOWNLOAD,
            STOCK_MODE_LOCAL_AVAILABLE,
        ):
            for item in visible_items:
                if item["id"] == selection or item["name"] == selection:
                    used_cnt = item.get("usage_count", 0)
                    if mode == STOCK_MODE_AUTO_DOWNLOAD and (
                        used_cnt >= MAX_STOCK_USAGES or item.get("status") == "used"
                    ):
                        raise ValueError(
                            f"❌ Video stock '{item['name']}' đã được sử dụng! "
                            f"Ở chế độ '1. Dùng Stock Tải Về', mỗi cuộn chỉ dùng 1 lần để chống trùng 100%."
                        )
                    chosen = dict(item)
                    chosen["flip_horizontal"] = (
                        (used_cnt % 2 == 1)
                        if mode == STOCK_MODE_LOCAL_AVAILABLE
                        else False
                    )
                    chosen["effective_mode"] = mode
                    return chosen

        if mode == STOCK_MODE_LOCAL_AVAILABLE:
            if not visible_items:
                return None
            # Xoay vòng thông minh: ưu tiên file có usage_count thấp nhất
            min_usage = min(x.get("usage_count", 0) for x in visible_items)
            candidates = [
                x for x in visible_items if x.get("usage_count", 0) == min_usage
            ]
            chosen = dict(random.choice(candidates))
            chosen["flip_horizontal"] = chosen.get("usage_count", 0) % 2 == 1
            chosen["effective_mode"] = STOCK_MODE_LOCAL_AVAILABLE
            return chosen

        # Chế độ 1 (auto_download): chỉ lấy stock chưa dùng (usage_count == 0)
        fresh_stocks = [
            x
            for x in visible_items
            if x.get("usage_count", 0) == 0 and x.get("status") == "available"
        ]
        if fresh_stocks:
            chosen = dict(random.choice(fresh_stocks))
            chosen["flip_horizontal"] = False
            chosen["effective_mode"] = STOCK_MODE_AUTO_DOWNLOAD
            return chosen

        return None

    def get_best_available_stock(
        self, exclude_ids: Optional[set] = None, selection: str = "auto_unique"
    ) -> Optional[Dict]:
        """
        Chọn 1 file stock khả dụng cho Pipeline Render đa luồng (tránh trùng giữa các luồng đang chạy song song qua `exclude_ids`):
        - Chế độ 1 ('auto_download'): Chỉ lấy file mới chưa dùng (usage_count == 0, status == 'available').
        - Chế độ 2 ('local_available'): Xoay vòng các file có sẵn trong kho STOOK (ưu tiên usage_count thấp nhất, giữ nguyên file).
        """
        exclude = set(exclude_ids or set())
        mode = self.get_stock_source_mode()
        if selection in (STOCK_MODE_AUTO_DOWNLOAD, STOCK_MODE_LOCAL_AVAILABLE):
            mode = selection
            self.set_stock_source_mode(mode)

        items = self.scan_and_sync()
        visible_items = [
            x
            for x in items
            if x.get("status") != "deleted_after_use"
            and os.path.exists(x.get("path", ""))
        ]

        def _enrich_chosen(raw_item: Dict, eff_mode: str) -> Dict:
            c = dict(raw_item)
            used_cnt = int(c.get("usage_count", 0))
            use_num = used_cnt + 1
            c["abs_path"] = c.get("path") or os.path.join(self.stook_dir, c["id"])
            c["rel_path"] = c.get("name") or c["id"]
            c["use_number"] = use_num
            c["flip_horizontal"] = (
                (used_cnt % 2 == 1) if eff_mode == STOCK_MODE_LOCAL_AVAILABLE else False
            )
            c["zoom_factor"] = 1.0
            c["effective_mode"] = eff_mode
            c["slot_key"] = f"{c['id']}::use{use_num}"
            if eff_mode == STOCK_MODE_LOCAL_AVAILABLE:
                c["transform_label"] = f"Kho Sẵn Có (Lượt #{use_num} • Giữ nguyên file)"
            else:
                c["transform_label"] = (
                    "Stock Tải Về Mới 100% (Chống trùng • Tự xóa sau khi dùng)"
                )
            return c

        # Nếu chọn đích danh 1 file cụ thể
        if selection and selection not in (
            "auto_unique",
            STOCK_MODE_AUTO_DOWNLOAD,
            STOCK_MODE_LOCAL_AVAILABLE,
        ):
            for item in visible_items:
                if (
                    item["id"] == selection
                    or item["name"] == selection
                    or item.get("abs_path") == selection
                ):
                    if mode == STOCK_MODE_AUTO_DOWNLOAD and (
                        item.get("usage_count", 0) >= MAX_STOCK_USAGES
                        or item.get("status") == "used"
                    ):
                        continue
                    return _enrich_chosen(item, mode)

        if mode == STOCK_MODE_LOCAL_AVAILABLE:
            if not visible_items:
                return None
            unallocated = [
                x
                for x in visible_items
                if x["id"] not in exclude and x.get("path") not in exclude
            ]
            pool = unallocated if unallocated else visible_items
            min_usage = min(x.get("usage_count", 0) for x in pool)
            candidates = [x for x in pool if x.get("usage_count", 0) == min_usage]
            return _enrich_chosen(random.choice(candidates), STOCK_MODE_LOCAL_AVAILABLE)

        # Chế độ 1 (auto_download): chỉ lấy stock chưa dùng (usage_count == 0) và chưa cấp cho luồng khác
        fresh_stocks = [
            x
            for x in visible_items
            if x.get("usage_count", 0) == 0
            and x.get("status") == "available"
            and x["id"] not in exclude
            and x.get("path") not in exclude
        ]
        if fresh_stocks:
            return _enrich_chosen(random.choice(fresh_stocks), STOCK_MODE_AUTO_DOWNLOAD)

        return None

    def mark_as_used(self, stock_id: str, project_name: str):
        """Đánh dấu file stock sau khi dự án đã sử dụng."""
        mode = self.get_stock_source_mode()
        stocks_dict = self.inventory.get("stocks", {})
        if stock_id in stocks_dict:
            item = stocks_dict[stock_id]
            new_count = item.get("usage_count", 0) + 1
            item["usage_count"] = new_count
            if mode == STOCK_MODE_LOCAL_AVAILABLE:
                # Ở chế độ 2 (Dùng Stock Sẵn Có): Giữ nguyên trạng thái 'available' để dùng xoay vòng cho các video tiếp theo
                item["max_uses"] = 999999
                item["status"] = "available"
            else:
                item["max_uses"] = MAX_STOCK_USAGES
                item["status"] = (
                    "used" if new_count >= MAX_STOCK_USAGES else "available"
                )
            item["last_used_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
            if project_name not in item.get("used_in_projects", []):
                item.setdefault("used_in_projects", []).append(project_name)

            self.inventory.setdefault("history", []).append(
                {
                    "stock_id": stock_id,
                    "project_name": project_name,
                    "usage_number": new_count,
                    "mode": mode,
                    "used_at": item["last_used_at"],
                }
            )
            self._save_inventory()

    def delete_used_stock_file(self, stock_id: str, project_name: str = "") -> bool:
        """
        Xóa vật lý file video stock khỏi ổ cứng NGAY SAU KHI đã sử dụng ở chế độ 'auto_download'.
        TUYỆT ĐỐI KHÔNG XÓA nếu đang ở chế độ 'local_available' (Dùng Stock Sẵn Có).
        """
        mode = self.get_stock_source_mode()
        if mode == STOCK_MODE_LOCAL_AVAILABLE:
            print(
                f"[StockManager] Đang ở chế độ 'Dùng Stock Sẵn Có' -> Giữ nguyên file {stock_id}, không xóa."
            )
            return False

        stocks_dict = self.inventory.get("stocks", {})
        item = stocks_dict.get(stock_id)
        if not item:
            for k, v in stocks_dict.items():
                if v.get("name") == stock_id:
                    item = v
                    stock_id = k
                    break

        if not item:
            return False

        if item.get("usage_count", 0) < MAX_STOCK_USAGES:
            return False

        filepath = item.get("path", os.path.join(self.stook_dir, stock_id))
        deleted_ok = False
        if filepath and os.path.exists(filepath):
            try:
                os.remove(filepath)
                deleted_ok = True
                print(
                    f"[StockManager] 🗑️ Đã tự động xóa file stock tải về sau khi dùng: {filepath}"
                )
            except Exception as e:
                print(f"[StockManager] Không thể xóa file stock {filepath}: {e}")
        else:
            deleted_ok = True

        item["status"] = "deleted_after_use"
        item["size_mb"] = 0.0
        item["deleted_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        if project_name and project_name not in item.get("used_in_projects", []):
            item.setdefault("used_in_projects", []).append(project_name)

        self._save_inventory()
        return deleted_ok

    def cleanup_all_used_stocks(self) -> Dict:
        """Dọn dẹp toàn bộ các file stock đã dùng hết lượt trên ổ đĩa (chỉ áp dụng cho file đã khóa 'used')."""
        self.scan_and_sync()
        stocks_dict = self.inventory.get("stocks", {})
        deleted_files = []
        freed_mb = 0.0

        for stock_id, item in list(stocks_dict.items()):
            used_cnt = item.get("usage_count", 0)
            if item.get("status") == "used" and used_cnt >= MAX_STOCK_USAGES:
                filepath = item.get("path", os.path.join(self.stook_dir, stock_id))
                size_mb = item.get("size_mb", 0.0)
                if filepath and os.path.exists(filepath):
                    try:
                        os.remove(filepath)
                        deleted_files.append(stock_id)
                        freed_mb += size_mb
                        item["status"] = "deleted_after_use"
                        item["size_mb"] = 0.0
                        item["deleted_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
                    except Exception as e:
                        print(f"[StockManager] Lỗi xóa {filepath}: {e}")

        self._save_inventory()
        return {
            "deleted_count": len(deleted_files),
            "freed_mb": round(freed_mb, 2),
            "deleted_files": deleted_files,
        }

    def get_all_stocks(self) -> Dict:
        """Alias tương thích ngược cho get_all_stocks_info()."""
        return self.get_all_stocks_info()

    def scan_and_update_inventory(self) -> Dict:
        """Alias tương thích ngược: quét lại kho và trả về thông tin tổng hợp."""
        self.scan_and_sync()
        return self.get_all_stocks_info()

    def reset_usage(self, stock_id: str) -> bool:
        """Đặt lại trạng thái chưa dùng cho 1 file stock cụ thể."""
        stocks_dict = self.inventory.get("stocks", {})
        if stock_id in stocks_dict:
            stocks_dict[stock_id]["status"] = "available"
            stocks_dict[stock_id]["usage_count"] = 0
            stocks_dict[stock_id]["used_in_projects"] = []
            stocks_dict[stock_id]["last_used_at"] = None
            self._save_inventory()
            return True
        return False

    def reset_all_usage(self):
        """Đặt lại lượt dùng của các file vẫn còn nằm trên ổ cứng về trạng thái chưa dùng."""
        stocks_dict = self.inventory.get("stocks", {})
        for k, v in list(stocks_dict.items()):
            fpath = v.get("path", os.path.join(self.stook_dir, k))
            if os.path.exists(fpath):
                v["status"] = "available"
                v["usage_count"] = 0
                v["used_in_projects"] = []
                v["last_used_at"] = None
        self._save_inventory()
        return self.get_all_stocks_info()

    # =========================================================================
    # TỰ ĐỘNG TẢI KHO STOCK TỪ PEXELS API / PIXABAY API & YOUTUBE (720P/1080P)
    # =========================================================================
    def _get_pexels_pixabay_keys(self) -> Dict[str, str]:
        """Đọc API Key của Pexels & Pixabay từ stook_config.json hoặc biến môi trường."""
        pexels_key = DEFAULT_PEXELS_API_KEY
        pixabay_key = DEFAULT_PIXABAY_API_KEY
        data = self._load_config_dict()
        if data.get("pexels_api_key"):
            pexels_key = str(data["pexels_api_key"]).strip()
        if data.get("pixabay_api_key"):
            pixabay_key = str(data["pixabay_api_key"]).strip()
        return {"pexels": pexels_key, "pixabay": pixabay_key}

    def _search_pexels_videos(
        self, query: str, per_page: int = 30, page: int = 1
    ) -> List[Dict]:
        """Tìm kiếm danh sách video HD/FullHD ngang (landscape) trên Pexels API."""
        keys = self._get_pexels_pixabay_keys()
        api_key = keys.get("pexels", "")
        if not api_key:
            return []

        url = (
            f"https://api.pexels.com/videos/search?"
            f"query={urllib.parse.quote(query)}&orientation=landscape&size=medium"
            f"&per_page={per_page}&page={page}"
        )
        results = []
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "Authorization": api_key,
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                },
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8", errors="ignore"))
                    for v in data.get("videos", []):
                        vid_id = f"PX_{v.get('id')}"
                        dur = float(v.get("duration", 0))
                        if dur < 8:
                            continue
                        best_link = ""
                        best_w = 0
                        for vf in v.get("video_files", []):
                            w = int(vf.get("width") or 0)
                            h = int(vf.get("height") or 0)
                            link = vf.get("link", "")
                            if w >= h and 1280 <= w <= 1920 and link:
                                best_link = link
                                best_w = w
                                if w == 1280:
                                    break
                        if not best_link:
                            for vf in v.get("video_files", []):
                                if vf.get("link"):
                                    best_link = vf["link"]
                                    best_w = int(vf.get("width") or 1280)
                                    break
                        if best_link:
                            results.append(
                                {
                                    "id": vid_id,
                                    "source": "Pexels",
                                    "duration": dur,
                                    "width": best_w,
                                    "download_url": best_link,
                                    "page_url": v.get(
                                        "url",
                                        f"https://www.pexels.com/video/{v.get('id')}/",
                                    ),
                                    "title": f"Pexels Stock #{v.get('id')} ({query})",
                                }
                            )
        except Exception as e:
            print(f"[StockManager] Lỗi truy vấn Pexels API ({query}): {e}")
        return results

    def _search_pixabay_videos(
        self, query: str, per_page: int = 30, page: int = 1
    ) -> List[Dict]:
        """Tìm kiếm danh sách video HD/FullHD trên Pixabay API."""
        keys = self._get_pexels_pixabay_keys()
        api_key = keys.get("pixabay", "")
        if not api_key:
            return []

        url = (
            f"https://pixabay.com/api/videos/?"
            f"key={urllib.parse.quote(api_key)}&q={urllib.parse.quote(query)}"
            f"&video_type=film&per_page={per_page}&page={page}&safesearch=true"
        )
        results = []
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8", errors="ignore"))
                    for hit in data.get("hits", []):
                        vid_id = f"PB_{hit.get('id')}"
                        dur = float(hit.get("duration", 0))
                        if dur < 8:
                            continue
                        vids = hit.get("videos", {})
                        chosen = (
                            vids.get("medium")
                            or vids.get("large")
                            or vids.get("small")
                            or {}
                        )
                        dl_url = chosen.get("url", "")
                        if dl_url:
                            results.append(
                                {
                                    "id": vid_id,
                                    "source": "Pixabay",
                                    "duration": dur,
                                    "width": int(chosen.get("width") or 1280),
                                    "download_url": dl_url,
                                    "page_url": hit.get(
                                        "pageURL",
                                        f"https://pixabay.com/videos/id-{hit.get('id')}/",
                                    ),
                                    "title": f"Pixabay Stock #{hit.get('id')} ({hit.get('tags', query)})",
                                }
                            )
        except Exception as e:
            print(f"[StockManager] Lỗi truy vấn Pixabay API ({query}): {e}")
        return results

    def _search_pixabay_web_fallback(self, query: str, page: int = 1) -> List[Dict]:
        """Fallback tải danh sách clip miễn phí từ CDN Pixabay/Pexels công khai."""
        results = []
        try:
            url = f"https://pixabay.com/videos/search/{urllib.parse.quote(query)}/?pagi={page}"
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
                    "Accept-Language": "en-US,en;q=0.9",
                },
            )
            with urllib.request.urlopen(req, timeout=12) as resp:
                html = resp.read().decode("utf-8", errors="ignore")
                for m in re.finditer(
                    r"(https://cdn\.pixabay\.com/video/\d{4}/\d{2}/\d{2}/(\d+)_large\.mp4)",
                    html,
                ):
                    dl_url, num_id = m.group(1), m.group(2)
                    vid_id = f"PB_{num_id}"
                    results.append(
                        {
                            "id": vid_id,
                            "source": "PixabayCDN",
                            "duration": 20.0,
                            "width": 1280,
                            "download_url": dl_url,
                            "page_url": f"https://pixabay.com/videos/id-{num_id}/",
                            "title": f"Pixabay HD Clip #{num_id} ({query})",
                        }
                    )
        except Exception:
            pass
        return results

    def download_pexels_pixabay_stock_reel(
        self,
        query: str = "",
        target_minutes: int = DEFAULT_SLICE_MINUTES,
        progress_callback=None,
    ) -> Dict:
        """
        Tải các clip HD 720p/1080p từ Pexels & Pixabay (chưa từng nằm trong File Note Online của Mexico Ông Già),
        chuẩn hóa về 1280x720 30fps và ghép thành 1 cuộn Stock dài 30 phút.
        """
        try:
            self.sync_cloud_used_links(push_if_needed=False)
        except Exception:
            pass
        used_ids = self.load_used_yt_links()

        queries = (
            [query]
            if query
            else random.sample(PEXELS_PIXABAY_QUERIES, len(PEXELS_PIXABAY_QUERIES))
        )
        candidate_clips: List[Dict] = []

        for q in queries:
            page = random.randint(1, 3)
            px_items = self._search_pexels_videos(q, per_page=35, page=page)
            pb_items = self._search_pixabay_videos(q, per_page=35, page=page)
            if not px_items and not pb_items:
                pb_items = self._search_pixabay_web_fallback(q, page=1)

            for item in px_items + pb_items:
                vid_id = item.get("id", "")
                if (
                    vid_id
                    and vid_id not in used_ids
                    and not any(c["id"] == vid_id for c in candidate_clips)
                ):
                    candidate_clips.append(item)

            if sum(c.get("duration", 15) for c in candidate_clips) >= (
                target_minutes * 60 * 0.4
            ):
                break

        if not candidate_clips:
            return {
                "success": False,
                "error": "Không tìm thấy clip Pexels/Pixabay mới hoặc cần kiểm tra kết nối mạng.",
            }

        random.shuffle(candidate_clips)
        batch_tag = f"PXPB_{int(time.time())}"
        temp_clip_dir = os.path.join(self.stook_dir, f"_tmp_{batch_tag}")
        os.makedirs(temp_clip_dir, exist_ok=True)

        downloaded_norm_files: List[str] = []
        downloaded_meta: List[Dict] = []
        accumulated_raw_sec = 0.0
        target_raw_sec = min(float(target_minutes * 60), 360.0)

        try:
            for idx, clip in enumerate(candidate_clips, start=1):
                if (
                    accumulated_raw_sec >= target_raw_sec
                    and len(downloaded_norm_files) >= 6
                ):
                    break

                dl_url = clip["download_url"]
                raw_path = os.path.join(temp_clip_dir, f"raw_{idx:03d}.mp4")
                norm_path = os.path.join(temp_clip_dir, f"norm_{idx:03d}.mp4")

                if progress_callback:
                    progress_callback(
                        f"🌐 Đang tải clip {clip['source']} #{idx} ({clip['id']}) — "
                        f"Đã gom {round(accumulated_raw_sec / 60.0, 1)}p..."
                    )

                try:
                    req = urllib.request.Request(
                        dl_url,
                        headers={
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
                        },
                    )
                    with (
                        urllib.request.urlopen(req, timeout=30) as r,
                        open(raw_path, "wb") as out_f,
                    ):
                        shutil.copyfileobj(r, out_f)
                except Exception:
                    continue

                if (
                    not os.path.exists(raw_path)
                    or os.path.getsize(raw_path) < 100 * 1024
                ):
                    continue

                norm_cmd = [
                    FFMPEG_CMD,
                    "-y",
                    "-i",
                    raw_path,
                    "-an",
                    "-vf",
                    "scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720,fps=30,format=yuv420p",
                    "-c:v",
                    "libx264",
                    "-preset",
                    "ultrafast",
                    "-crf",
                    "23",
                    norm_path,
                ]
                subprocess.run(norm_cmd, capture_output=True, text=True, timeout=90)
                try:
                    os.remove(raw_path)
                except Exception:
                    pass

                if (
                    os.path.exists(norm_path)
                    and os.path.getsize(norm_path) > 100 * 1024
                ):
                    dur = self._probe_video_duration(norm_path)
                    if dur >= 4.0:
                        downloaded_norm_files.append(norm_path)
                        downloaded_meta.append(clip)
                        accumulated_raw_sec += dur

            if not downloaded_norm_files:
                return {
                    "success": False,
                    "error": "Không tải được clip Pexels/Pixabay hợp lệ.",
                }

            total_target_sec = float(target_minutes * 60)
            concat_list_path = os.path.join(temp_clip_dir, "concat_list.txt")
            sequence_files: List[str] = []
            seq_sec = 0.0
            while seq_sec < total_target_sec:
                shuffled = list(downloaded_norm_files)
                random.shuffle(shuffled)
                for nf in shuffled:
                    sequence_files.append(nf)
                    seq_sec += accumulated_raw_sec / max(1, len(downloaded_norm_files))
                    if seq_sec >= total_target_sec:
                        break

            with open(concat_list_path, "w", encoding="utf-8") as f:
                for nf in sequence_files:
                    safe_p = nf.replace("\\", "/")
                    f.write(f"file '{safe_p}'\n")

            existing_parts = glob.glob(
                os.path.join(self.stook_dir, "stock_PXPB_*_part*.mp4")
            )
            next_idx = len(existing_parts) + 1
            out_name = f"stock_{batch_tag}_part{next_idx:02d}.mp4"
            out_path = os.path.join(self.stook_dir, out_name)

            if progress_callback:
                progress_callback(
                    f"🎬 Đang đóng gói cuộn Stock 30 phút ({out_name}) từ {len(downloaded_norm_files)} cảnh Pexels/Pixabay..."
                )

            concat_cmd = [
                FFMPEG_CMD,
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                concat_list_path,
                "-t",
                str(int(total_target_sec)),
                "-c",
                "copy",
                out_path,
            ]
            subprocess.run(concat_cmd, capture_output=True, text=True, timeout=180)

            if (
                not os.path.exists(out_path)
                or os.path.getsize(out_path) < 2 * 1024 * 1024
            ):
                return {
                    "success": False,
                    "error": "Lỗi khi ghép cuộn Stock Pexels/Pixabay.",
                }

            for clip in downloaded_meta:
                self.record_used_yt_link(
                    clip["id"],
                    clip.get("page_url", clip["download_url"]),
                    title=clip.get("title", "Pexels/Pixabay HD Stock"),
                    license_str="Pexels/Pixabay Free License",
                )

            self.scan_and_sync()
            return {
                "success": True,
                "video_id": batch_tag,
                "source": "Pexels/Pixabay",
                "clips_merged": len(downloaded_norm_files),
                "parts_count": 1,
                "parts": [out_name],
                "message": f"✅ Đã tải & ghép thành công cuộn Stock 30p ({out_name}) từ {len(downloaded_norm_files)} cảnh Pexels/Pixabay!",
            }
        finally:
            try:
                shutil.rmtree(temp_clip_dir, ignore_errors=True)
            except Exception:
                pass

    def _get_yt_cookie_args(self, browser_name: Optional[str] = None) -> List[str]:
        """Trả về tham số cookie cho yt-dlp để vượt qua lỗi 'Sign in to confirm you're not a bot'."""
        if os.path.exists(YT_COOKIES_FILE) and os.path.getsize(YT_COOKIES_FILE) > 32:
            return ["--cookies", YT_COOKIES_FILE]
        local_stook_cookie = os.path.join(self.stook_dir, "youtube_cookies.txt")
        if (
            os.path.exists(local_stook_cookie)
            and os.path.getsize(local_stook_cookie) > 32
        ):
            return ["--cookies", local_stook_cookie]
        if browser_name:
            return ["--cookies-from-browser", browser_name]
        return []

    def _run_ytdlp_with_Workarounds(
        self, base_args: List[str], timeout: int = 60
    ) -> subprocess.CompletedProcess:
        """Chạy yt-dlp với cơ chế tự động vượt tường lửa Bot Check của YouTube."""
        import sys

        py_exe = sys.executable

        strategies = [
            {
                "cookies": self._get_yt_cookie_args(None),
                "extractor": "youtube:player_client=android,web",
            },
            {
                "cookies": self._get_yt_cookie_args(None),
                "extractor": "youtube:player_client=ios,mweb",
            },
        ]
        for b_name in SUPPORTED_COOKIE_BROWSERS:
            strategies.append(
                {
                    "cookies": ["--cookies-from-browser", b_name],
                    "extractor": "youtube:player_client=web,default",
                }
            )

        last_res = None
        for strat in strategies:
            cmd = [py_exe, "-m", "yt_dlp", "--no-check-certificate", "--geo-bypass"]
            if strat["extractor"]:
                cmd.extend(["--extractor-args", strat["extractor"]])
            if strat["cookies"]:
                cmd.extend(strat["cookies"])
            cmd.extend(base_args)

            try:
                res = subprocess.run(
                    cmd, capture_output=True, text=True, timeout=timeout
                )
                last_res = res
                if res.returncode == 0 and (res.stdout or "").strip():
                    return res
                stderr_lower = (res.stderr or "").lower()
                if (
                    "could not copy" in stderr_lower
                    or "database" in stderr_lower
                    or "cookie" in stderr_lower
                ):
                    continue
                if "not a bot" in stderr_lower or "sign in" in stderr_lower:
                    continue
                if res.returncode == 0:
                    return res
            except subprocess.TimeoutExpired as te:
                print(f"[StockManager] yt-dlp timeout ({timeout}s): {te}")
            except Exception as e:
                print(f"[StockManager] yt-dlp lỗi thực thi: {e}")

        return last_res

    def search_new_youtube_candidates(
        self, query: str, max_results: int = 12
    ) -> List[Dict]:
        """Tìm kiếm các video YouTube mới (chưa từng nằm trong used_stock_links.json của Mexico Ông Già)."""
        try:
            self.sync_cloud_used_links(push_if_needed=False)
        except Exception:
            pass
        used_ids = self.load_used_yt_links()
        search_spec = f"ytsearch{max_results}:{query}"

        base_args = [
            "--dump-json",
            "--flat-playlist",
            "--no-playlist",
            "--no-warnings",
            search_spec,
        ]

        candidates = []
        res = self._run_ytdlp_with_Workarounds(base_args, timeout=45)
        if not res or not res.stdout:
            return []

        for line in res.stdout.strip().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                info = json.loads(line)
            except Exception:
                continue

            vid = info.get("id", "")
            duration = float(info.get("duration") or 0)
            title = info.get("title", "")
            live_status = info.get("live_status", "")

            if not vid or vid in used_ids:
                continue
            if live_status in ("is_live", "is_upcoming") or info.get("is_live"):
                continue
            if duration > 0 and (duration < 600 or duration > 14400):
                continue

            candidates.append(
                {
                    "id": vid,
                    "url": f"https://www.youtube.com/watch?v={vid}",
                    "title": title,
                    "duration": duration,
                }
            )
        return candidates

    def ensure_minimum_stock_hours(
        self,
        target_hours: float = DEFAULT_TARGET_STOCK_HOURS,
        slice_minutes: int = DEFAULT_SLICE_MINUTES,
        progress_callback=None,
    ) -> Dict:
        """
        Đảm bảo trong kho STOOK luôn có sẵn ít nhất `target_hours` giờ video stock.
        - Nếu đang ở chế độ 'local_available' (Dùng Stock Sẵn Có): chỉ kiểm tra kho local, không tải mạng.
        - Nếu đang ở chế độ 'auto_download' (Dùng Stock Tải Về): tự động tải bù từ Pexels / Pixabay / YouTube
          và ghi link vào File Note Online riêng của Mexico Ông Già (https://rentry.co/mexico-ong-gia-stock-8a9b2c).
        """
        mode = self.get_stock_source_mode()
        info = self.get_all_stocks_info()
        current_hours = info.get("available_raw_hours", 0.0)

        if mode == STOCK_MODE_LOCAL_AVAILABLE:
            return {
                "success": info.get("available_count", 0) > 0,
                "action": "local_mode_no_download",
                "current_hours": current_hours,
                "target_hours": target_hours,
                "downloaded_videos": [],
                "message": (
                    f"📂 Đang ở chế độ '2. Dùng Stock Sẵn Có': Kho STOOK hiện có {info.get('available_count', 0)} file "
                    f"({current_hours}h) sẵn sàng xoay vòng (Không tải mạng, không xóa file)."
                ),
            }

        if current_hours >= target_hours:
            return {
                "success": True,
                "action": "none_needed",
                "current_hours": current_hours,
                "target_hours": target_hours,
                "downloaded_videos": [],
                "message": f"Kho Stock đã đủ {current_hours:.1f}h / {target_hours:.1f}h mục tiêu.",
            }

        try:
            self.sync_cloud_used_links(push_if_needed=True)
        except Exception:
            pass

        downloaded_videos = []
        queries_pool = list(AUTO_SEARCH_QUERIES)
        random.shuffle(queries_pool)
        pxpb_queries_pool = list(PEXELS_PIXABAY_QUERIES)
        random.shuffle(pxpb_queries_pool)

        max_attempts = 25
        attempt = 0

        # Tầng 1: Ưu tiên tải từ Pexels & Pixabay API (Tốc độ cao, miễn phí bản quyền)
        for px_q in pxpb_queries_pool:
            info = self.get_all_stocks_info()
            current_hours = info.get("available_raw_hours", 0.0)
            if current_hours >= target_hours or attempt >= max_attempts:
                break

            attempt += 1
            deficit_hours = round(target_hours - current_hours, 2)
            msg = (
                f"🌐 [Tự động bù Stock Pexels/Pixabay] Kho hiện có {current_hours:.1f}h/{target_hours:.1f}h "
                f"(Thiếu {deficit_hours:.1f}h). Đang tải cảnh '{px_q}'..."
            )
            print(f"[StockManager] {msg}")
            if progress_callback:
                progress_callback(msg)

            px_res = self.download_pexels_pixabay_stock_reel(
                query=px_q,
                target_minutes=slice_minutes,
                progress_callback=progress_callback,
            )
            if px_res.get("success"):
                downloaded_videos.append(
                    {
                        "video_id": px_res.get("video_id"),
                        "title": f"Pexels/Pixabay ({px_q})",
                        "parts_added": px_res.get("parts_count", 1),
                    }
                )
            else:
                break

        # Tầng 2: Tự động tìm và tải từ YouTube nếu vẫn cần bù thêm
        for query in queries_pool:
            info = self.get_all_stocks_info()
            current_hours = info.get("available_raw_hours", 0.0)
            if current_hours >= target_hours or attempt >= max_attempts:
                break

            if progress_callback:
                progress_callback(
                    f"🔍 [Tự động bù Stock YouTube] Kho hiện có {current_hours:.1f}h/{target_hours:.1f}h — "
                    f"Đang tìm video 720p mới với từ khóa: '{query}'..."
                )

            candidates = self.search_new_youtube_candidates(query, max_results=10)
            for cand in candidates:
                info = self.get_all_stocks_info()
                current_hours = info.get("available_raw_hours", 0.0)
                if current_hours >= target_hours or attempt >= max_attempts:
                    break

                attempt += 1
                deficit_hours = round(target_hours - current_hours, 2)
                msg = (
                    f"📥 [Tự động bù Stock 720p] Kho hiện có {current_hours:.1f}h/{target_hours:.1f}h "
                    f"(Thiếu {deficit_hours:.1f}h). Đang tải: {cand['title'][:55]}..."
                )
                print(f"[StockManager] {msg}")
                if progress_callback:
                    progress_callback(msg)

                dl_res = self.download_youtube_and_slice(
                    youtube_url=cand["url"],
                    slice_minutes=slice_minutes,
                    force_redownload=False,
                    max_parts=8,
                )
                if dl_res.get("success"):
                    downloaded_videos.append(
                        {
                            "video_id": cand["id"],
                            "title": cand["title"],
                            "parts_added": dl_res.get("parts_count", 0),
                        }
                    )

        final_info = self.get_all_stocks_info()
        final_hours = final_info.get("available_raw_hours", 0.0)
        has_any_stock = final_hours > 0 or final_info.get("available_count", 0) > 0
        return {
            "success": has_any_stock,
            "action": "replenished" if downloaded_videos else "checked",
            "current_hours": final_hours,
            "target_hours": target_hours,
            "downloaded_videos": downloaded_videos,
            "error": (
                None
                if has_any_stock
                else "Không thể tải tự động từ Pexels/Pixabay hoặc YouTube lúc này. "
                "Vui lòng dán link YouTube bất kỳ hoặc chuyển sang chế độ '2. Dùng Stock Sẵn Có'!"
            ),
            "message": (
                f"✅ Đã bổ sung {len(downloaded_videos)} nguồn video mới. "
                f"Tổng thời lượng kho Stock hiện tại: {final_hours:.1f}h / {target_hours:.1f}h."
                if downloaded_videos
                else f"Kho Stock hiện có {final_hours:.1f}h / {target_hours:.1f}h."
            ),
        }

    def download_youtube_and_slice(
        self,
        youtube_url: str,
        slice_minutes: int = DEFAULT_SLICE_MINUTES,
        force_redownload: bool = False,
        max_parts: int = 12,
    ) -> Dict:
        """
        Tải video từ YouTube ở chất lượng chuẩn 720p (1280x720, không âm thanh để tốc độ tải nhanh gấp 4 lần)
        và tự động cắt thành các part 30 phút.
        Lưu vĩnh viễn ID vào used_stock_links.json & File Note Online của Mexico Ông Già để chống tải trùng.
        """
        try:
            probe_args = [
                "--dump-single-json",
                "--no-playlist",
                "--no-warnings",
                youtube_url,
            ]
            probe_res = self._run_ytdlp_with_Workarounds(probe_args, timeout=45)

            vid_id = f"yt_{int(time.time())}"
            vid_title = ""
            vid_license = ""
            if (
                probe_res
                and probe_res.returncode == 0
                and (probe_res.stdout or "").strip()
            ):
                try:
                    meta = json.loads(probe_res.stdout.strip().splitlines()[-1])
                    vid_id = meta.get("id") or vid_id
                    vid_title = meta.get("title") or ""
                    vid_license = meta.get("license") or ""
                except Exception:
                    pass
            else:
                id_match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11}).*", youtube_url)
                if id_match:
                    vid_id = id_match.group(1)

            try:
                self.sync_cloud_used_links(push_if_needed=False)
            except Exception:
                pass
            used_ids = self.load_used_yt_links()
            if not force_redownload and vid_id in used_ids:
                prev_info = used_ids[vid_id]
                return {
                    "success": False,
                    "already_exists": True,
                    "video_id": vid_id,
                    "title": vid_title or prev_info.get("title", ""),
                    "existing_parts": [],
                    "parts_count": 0,
                    "error": (
                        f"Video YouTube [{vid_id}] đã từng được tải vào ngày {prev_info.get('downloaded_at', 'trước đó')}. "
                        f"Hệ thống Mexico Ông Già từ chối tải lại để chống trùng lặp 100%!"
                    ),
                }

            existing_parts = sorted(
                glob.glob(os.path.join(self.stook_dir, f"stock_{vid_id}_part*.mp4"))
            )
            if existing_parts and not force_redownload:
                self.record_used_yt_link(vid_id, youtube_url, vid_title, vid_license)
                self.scan_and_sync()
                part_names = [os.path.basename(p) for p in existing_parts]
                return {
                    "success": False,
                    "already_exists": True,
                    "video_id": vid_id,
                    "title": vid_title,
                    "existing_parts": part_names,
                    "parts_count": len(part_names),
                    "error": (
                        f"Video này ({vid_title or vid_id}) đã có sẵn {len(part_names)} part "
                        f"trong kho STOOK ({', '.join(part_names[:3])}{'...' if len(part_names) > 3 else ''})."
                    ),
                }

            temp_output = os.path.join(self.stook_dir, f"_temp_yt_{vid_id}.mp4")
            max_download_sec = max_parts * slice_minutes * 60

            dl_base_args = [
                "-f",
                "bestvideo[height<=720][ext=mp4]/best[height<=720][ext=mp4]/bestvideo[height<=720]/best[height<=720]",
                "--merge-output-format",
                "mp4",
                "--no-playlist",
                "--concurrent-fragments",
                "4",
                "--download-sections",
                f"*0-{max_download_sec}",
                "-o",
                temp_output,
                youtube_url,
            ]
            dl_res = self._run_ytdlp_with_Workarounds(dl_base_args, timeout=900)

            if not os.path.exists(temp_output):
                dl_fallback_args = [
                    "-f",
                    "best[height<=720]/best",
                    "--no-playlist",
                    "-o",
                    temp_output,
                    youtube_url,
                ]
                dl_res = self._run_ytdlp_with_Workarounds(dl_fallback_args, timeout=900)

            if not os.path.exists(temp_output):
                err_detail = (
                    (dl_res.stderr if dl_res else "")
                    or (dl_res.stdout if dl_res else "")
                    or "Không thể tải video từ link này."
                ).strip()
                return {"success": False, "error": err_detail[-400:]}

            total_dur = self._probe_video_duration(temp_output)
            if total_dur < 30.0:
                try:
                    os.remove(temp_output)
                except Exception:
                    pass
                return {
                    "success": False,
                    "error": f"Video quá ngắn ({total_dur}s), không đủ làm Stock.",
                }

            self.record_used_yt_link(vid_id, youtube_url, vid_title, vid_license)

            slice_sec = slice_minutes * 60
            out_pattern = os.path.join(self.stook_dir, f"stock_{vid_id}_part%02d.mp4")

            if total_dur <= slice_sec * 1.2:
                single_out = os.path.join(self.stook_dir, f"stock_{vid_id}_part01.mp4")
                shutil.move(temp_output, single_out)
                created_files = [single_out]
            else:
                cmd_slice = [
                    FFMPEG_CMD,
                    "-y",
                    "-i",
                    temp_output,
                    "-an",
                    "-c:v",
                    "copy",
                    "-map",
                    "0:v:0",
                    "-segment_time",
                    str(slice_sec),
                    "-f",
                    "segment",
                    "-reset_timestamps",
                    "1",
                    out_pattern,
                ]
                subprocess.run(cmd_slice, check=True)
                try:
                    os.remove(temp_output)
                except Exception:
                    pass
                created_files = sorted(
                    glob.glob(os.path.join(self.stook_dir, f"stock_{vid_id}_part*.mp4"))
                )

            valid_parts = []
            for idx, fpath in enumerate(created_files):
                dur = self._probe_video_duration(fpath)
                if idx > 0 and dur < 300:
                    try:
                        os.remove(fpath)
                    except Exception:
                        pass
                else:
                    valid_parts.append(os.path.basename(fpath))

            self.scan_and_sync()
            return {
                "success": True,
                "video_id": vid_id,
                "title": vid_title,
                "license": vid_license,
                "parts_count": len(valid_parts),
                "parts": valid_parts,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def _format_duration(seconds: float) -> str:
        m, s = divmod(int(seconds), 60)
        h, m = divmod(m, 60)
        if h > 0:
            return f"{h:02d}:{m:02d}:{s:02d}"
        return f"{m:02d}:{s:02d}"
