import os
import time
import requests
from typing import List, Dict, Any
from readability import Document
from dateutil import parser as dateparser

from common import (
    UA, strip_html, contains_all, get_must_words,
    MAX_SAVE, RECENT_DAYS, SLEEP_SEC, is_recent, to_kst_str, safe_write_json, dedupe_by_title
)

TIMEOUT = 25
DISPLAY = int(os.getenv("NAVER_DISPLAY", "100"))
MAX_FETCH = int(os.getenv("MAX_FETCH", "80"))

NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID", "").strip()
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET", "").strip()

def naver_search_news(query: str, display: int = 100) -> List[Dict[str, Any]]:
    if not NAVER_CLIENT_ID or not NAVER_CLIENT_SECRET:
        raise RuntimeError("NAVER_CLIENT_ID / NAVER_CLIENT_SECRET가 설정되어 있어야 합니다. (GitHub Secrets)")

    url = "https://openapi.naver.com/v1/search/news.json"
    headers = {
        "X-Naver-Client-Id": NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": NAVER_CLIENT_SECRET,
    }
    params = {"query": query, "display": min(display, 100), "sort": "date"}
    r = requests.get(url, headers=headers, params=params, timeout=TIMEOUT)
    r.raise_for_status()
    return (r.json() or {}).get("items", []) or []

def extract_main_text(url: str) -> str:
    try:
        resp = requests.get(url, headers=UA, timeout=TIMEOUT, allow_redirects=True)
        resp.raise_for_status()
        doc = Document(resp.text)
        main_html = doc.summary(html_partial=True)
        return strip_html(main_html)
    except Exception:
        return ""

def run(out_path: str = "docs/data/naver_news.json") -> List[Dict[str, Any]]:
    must = get_must_words()
    query = " ".join(must)

    items = naver_search_news(query, display=DISPLAY)

    results = []
    seen = set()
    fetched = 0

    for it in items:
        if len(results) >= MAX_SAVE:
            break

        title = strip_html(it.get("title", ""))
        link = (it.get("originallink") or it.get("link") or "").strip()
        desc = strip_html(it.get("description", ""))
        pub = (it.get("pubDate") or "").strip()

        published_iso = ""
        try:
            dt = dateparser.parse(pub)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=datetime.timezone.utc)
            published_iso = dt.isoformat()
        except Exception:
            published_iso = ""

        if published_iso and (not is_recent(published_iso, RECENT_DAYS)):
            continue

        if not link or link in seen:
            continue
        seen.add(link)

        fetched += 1
        if fetched > MAX_FETCH:
            break

        time.sleep(SLEEP_SEC)

        body = extract_main_text(link)
        if not body:
            continue
        if not contains_all(body, must):
            continue

        results.append({
            "title": title,
            "link": link,
            "source": "Naver News",
            "published_iso": published_iso,
            "published_kst": to_kst_str(published_iso),
            "platform": "naver",
            "snippet": desc,
        })

    results = dedupe_by_title(results)
    results.sort(key=lambda x: x.get("published_iso",""), reverse=True)
    safe_write_json(out_path, results[:MAX_SAVE])
    return results[:MAX_SAVE]

if __name__ == "__main__":
    run()
