import os
import json
import datetime
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
from dateutil import parser as dateparser

UA = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
    "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.6",
}

def env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except Exception:
        return default

MAX_SAVE = env_int("MAX_SAVE", 20)
RECENT_DAYS = env_int("RECENT_DAYS", 90)
SLEEP_SEC = float(os.getenv("SLEEP_SEC", "0.6"))

def get_must_words() -> List[str]:
    raw = os.getenv("MUST_WORDS", "박정현,가수")
    return [x.strip() for x in raw.split(",") if x.strip()]

def strip_html(s: str) -> str:
    return BeautifulSoup(s or "", "html.parser").get_text(" ", strip=True)

def contains_all(text: str, must: List[str]) -> bool:
    t = (text or "").lower()
    return all(m.lower() in t for m in must)

def parse_dt_iso(dt_str: str) -> Optional[datetime.datetime]:
    if not dt_str:
        return None
    try:
        dt = dateparser.parse(dt_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.timezone.utc)
        return dt
    except Exception:
        return None

def is_recent(published_iso: str, days: int) -> bool:
    dt = parse_dt_iso(published_iso)
    if not dt:
        return True
    cutoff = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc) - datetime.timedelta(days=days)
    return dt >= cutoff

def to_kst_str(published_iso: str) -> str:
    dt = parse_dt_iso(published_iso)
    if not dt:
        return ""
    kst = dt.astimezone(datetime.timezone(datetime.timedelta(hours=9)))
    return kst.strftime("%Y-%m-%d %H:%M")

def safe_write_json(path: str, data: Any) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def dedupe_by_title(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    out = []
    for it in items:
        t = (it.get("title") or "").strip().lower()
        if not t:
            continue
        if t in seen:
            continue
        seen.add(t)
        out.append(it)
    return out
