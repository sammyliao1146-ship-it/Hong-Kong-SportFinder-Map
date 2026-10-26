"""Pure helpers for matching LCSD venue photos and rendering thumbnails."""
import re
import unicodedata
from io import BytesIO
from pathlib import Path
from urllib.parse import quote, urlsplit

from PIL import Image

PHOTO_FEEDS = {
    "sports_centres": "https://www.lcsd.gov.hk/datagovhk/facility/facility-sc.json",
    "sports_grounds": "https://www.lcsd.gov.hk/datagovhk/facility/facility-sg.json",
    "outdoor_fitness": "https://www.lcsd.gov.hk/datagovhk/facility/facility-ofe.json",
}

DISTRICT_CODES = {
    "centralwestern": "CW", "中西區": "CW", "中西区": "CW", "中西": "CW",
    "eastern": "E", "東區": "E", "东区": "E", "東": "E", "东": "E",
    "islands": "IS", "離島區": "IS", "离岛区": "IS", "離島": "IS", "离岛": "IS",
    "kowlooncity": "KC", "九龍城區": "KC", "九龙城区": "KC", "九龍城": "KC", "九龙城": "KC",
    "kwaitsing": "KWT", "葵青區": "KWT", "葵青区": "KWT", "葵青": "KWT",
    "kwuntong": "KT", "觀塘區": "KT", "观塘区": "KT", "觀塘": "KT", "观塘": "KT",
    "north": "N", "北區": "N", "北区": "N", "北": "N",
    "saikung": "SK", "西貢區": "SK", "西贡区": "SK", "西貢": "SK", "西贡": "SK",
    "shatin": "ST", "沙田區": "ST", "沙田区": "ST", "沙田": "ST",
    "shamshuipo": "SSP", "深水埗區": "SSP", "深水埗区": "SSP", "深水埗": "SSP",
    "southern": "S", "南區": "S", "南区": "S", "南": "S",
    "taipo": "TP", "大埔區": "TP", "大埔区": "TP", "大埔": "TP",
    "tsuenwan": "TW", "荃灣區": "TW", "荃湾区": "TW", "荃灣": "TW", "荃湾": "TW",
    "tuenmun": "TM", "屯門區": "TM", "屯门区": "TM", "屯門": "TM", "屯门": "TM",
    "wanchai": "WC", "灣仔區": "WC", "湾仔区": "WC", "灣仔": "WC", "湾仔": "WC",
    "wongtaisin": "WTS", "黃大仙區": "WTS", "黄大仙区": "WTS", "黃大仙": "WTS", "黄大仙": "WTS",
    "yautsimmong": "YTM", "油尖旺區": "YTM", "油尖旺区": "YTM", "油尖旺": "YTM",
    "yuenlong": "YL", "元朗區": "YL", "元朗区": "YL", "元朗": "YL",
}

PHOTO_PATH_PREFIXES = (
    "/file_upload_clpss/leisure_facilities/en/common/images/photo/facilities/",
    "/file_upload_clpss/leisure_facilities/en/common/images/facilities/facilitieslist/fitness/",
)
THUMBNAIL_SIZE = (900, 600)
MAX_DOWNLOAD_BYTES = 12 * 1024 * 1024
MAX_PIXELS = 20_000_000


def name_key(value: object) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).casefold()
    return re.sub(r"[^\w\u3400-\u9fff]", "", text)


def district_key(value: object) -> str:
    raw = unicodedata.normalize("NFKC", str(value or "")).casefold().strip()
    if raw in DISTRICT_CODES:
        return DISTRICT_CODES[raw]
    compact = re.sub(r"[^\w\u3400-\u9fff]", "", raw)
    if compact in DISTRICT_CODES:
        return DISTRICT_CODES[compact]
    # The current CSDI layer labels districts in Traditional Chinese.
    for name, code in DISTRICT_CODES.items():
        if name in compact:
            return code
    return compact


def is_allowed_photo_url(url: str) -> bool:
    parsed = urlsplit(url)
    return (
        parsed.scheme == "https"
        and parsed.hostname == "www.lcsd.gov.hk"
        and parsed.port is None
        and any(parsed.path.startswith(prefix) for prefix in PHOTO_PATH_PREFIXES)
    )


def photo_urls(record: dict) -> list[str]:
    district = district_key(record.get("District_en") or record.get("District_cn"))
    urls = []
    for field in ("Photo_1", "Photo_2", "Photo_3"):
        value = str(record.get(field) or "").strip()
        if not value:
            continue
        if value.startswith(("https://", "http://")):
            url = value
        else:
            if not district:
                continue
            filename = quote(Path(value).name, safe="()_.-~")
            url = f"https://www.lcsd.gov.hk/file_upload_clpss/leisure_facilities/en/common/images/photo/facilities/{district}/{filename}"
        if is_allowed_photo_url(url) and url not in urls:
            urls.append(url)
    return urls


def quality_rank(quality: dict | None) -> tuple:
    if quality is None:
        # New feed entries are still eligible until the next image audit.
        return (1, 0, 0, 0)
    if quality.get("available") is False:
        return (-1, 0, 0, 0)
    width = int(quality.get("width") or 0)
    height = int(quality.get("height") or 0)
    sharpness = float(quality.get("sharpness") or 0)
    pixels = width * height
    if width >= 300 and height >= 200:
        return (2, sharpness, pixels, 0)
    return (0, pixels, sharpness, 0)


def render_thumbnail(content: bytes) -> bytes:
    """Return a WebP thumbnail; raises ValueError for oversized or unreadable images."""
    try:
        with Image.open(BytesIO(content)) as original:
            if original.width * original.height > MAX_PIXELS:
                raise ValueError("oversized")
            original.thumbnail(THUMBNAIL_SIZE, Image.Resampling.LANCZOS)
            output = BytesIO()
            original.convert("RGB").save(output, format="WEBP", quality=78, method=5)
            return output.getvalue()
    except (OSError, Image.DecompressionBombError) as exc:
        raise ValueError("unreadable") from exc
