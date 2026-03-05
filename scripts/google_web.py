import os
import time
import requests
from typing import List, Dict, Any
from readability import Document

from common import (
    UA, strip_html, contains_all, get_must_words,
    MAX_SAVE, RECENT_DAYS, SLEEP_SEC, is_recent, to_kst_str, safe_write_json, dedupe_by_title
)

TIMEOUT = 25
SEARCH_RESULTS = int(os.getenv("SEARCH_RESULTS", "60"))  # 10단위, 최대 100 권장
MAX_FETCH = int(os.getenv("MAX_FETCH", "80"))

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "").strip()
GOOGLE_CX = os.getenv("GOOGLE_CX", "").strip()

def google_web_search(query: str, total_results: int = 30) -> List[Dict[str, Any]]:
    if not GOOGLE_API_KEY or not GOOGLE_CX:
        raise RuntimeError("GOOGLE_API_KEY / GOOGLE_CX가 설정되어 있어야 합니다. (GitHub Secrets)")

    out = []
    for start in range(1, min(total_results, 100) + 1, 10):
        params = {
            "key": GOOGLE_API_KEY,
            "cx": GOOGLE_CX,
            "q": query,
            "num": 10,
            "start": start,
            "hl": "ko",
            "gl": "kr",
        }
        r = requests.get("https://www.googleapis.com/customsearch/v1", params=params, timeout=TIMEOUT)
        r.raise_for_status()
        data = r.json()
        items = data.get("items", []) or []
        for it in items:
            out.append({
                "title": it.get("title", ""),
                "link": it.get("link", ""),
                "snippet": it.get("snippet", ""),
                "displayLink": it.get("displayLink", ""),
            })
        time.sleep(0.2)
    return out

def extract_main_text(url: str) -> str:
    try:
        resp = requests.get(url, headers=UA, timeout=TIMEOUT, allow_redirects=True)
        resp.raise_for_status()
        doc = Document(resp.text)
        main_html = doc.summary(html_partial=True)
        return strip_html(main_html)
    except Exception:
        return ""

def run(out_path: str = "docs/data/google_web.json") -> List[Dict[str, Any]]:
    must = get_must_words()
    query = " ".join(must)

    candidates = google_web_search(query, total_results=SEARCH_RESULTS)

    results = []
    seen_links = set()
    fetched = 0

    for it in candidates:
        if len(results) >= MAX_SAVE:
            break

        url = (it.get("link") or "").strip()
        if not url:
            continue
        if url in seen_links:
            continue
        seen_links.add(url)

        fetched += 1
        if fetched > MAX_FETCH:
            break

        time.sleep(SLEEP_SEC)

        body = extract_main_text(url)
        if not body:
            continue
        if not contains_all(body, must):
            continue

        published_iso = ""  # 웹검색은 날짜가 없는 경우가 많아 공란 처리(프론트에서 최신 정렬은 날짜 없는 건 뒤로 감)
        if published_iso and (not is_recent(published_iso, RECENT_DAYS)):
            continue

        results.append({
            "title": it.get("title", ""),
            "link": url,
            "source": it.get("displayLink", "") or "Google Web",
            "published_iso": published_iso,
            "published_kst": to_kst_str(published_iso),
            "platform": "google_web",
            "snippet": it.get("snippet", ""),
        })

    results = dedupe_by_title(results)
    results.sort(key=lambda x: (1 if x.get("published_iso") else 0, x.get("published_iso","")), reverse=True)

    safe_write_json(out_path, results[:MAX_SAVE])
    return results[:MAX_SAVE]

if __name__ == "__main__":
    run()
