import os
import time
import requests
from typing import List, Dict, Any

from common import (
    contains_all, get_must_words, MAX_SAVE, safe_write_json, dedupe_by_title
)

TIMEOUT = 25
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "").strip()

def youtube_search(query: str, max_results: int = 40) -> List[Dict[str, Any]]:
    if not YOUTUBE_API_KEY:
        raise RuntimeError("YOUTUBE_API_KEY가 설정되어 있어야 합니다. (GitHub Secrets)")

    params = {
        "key": YOUTUBE_API_KEY,
        "part": "snippet",
        "q": query,
        "type": "video",
        "maxResults": min(max_results, 50),
        "relevanceLanguage": "ko",
        "regionCode": "KR",
        "order": "date",
    }
    r = requests.get("https://www.googleapis.com/youtube/v3/search", params=params, timeout=TIMEOUT)
    r.raise_for_status()
    return (r.json() or {}).get("items", []) or []

def run(out_path: str = "docs/data/youtube.json") -> List[Dict[str, Any]]:
    must = get_must_words()
    query = " ".join(must)

    items = youtube_search(query, max_results=40)

    results = []
    for it in items:
        sn = it.get("snippet", {}) or {}
        vid = (it.get("id", {}) or {}).get("videoId", "")
        title = sn.get("title", "")
        desc = sn.get("description", "")
        published_at = sn.get("publishedAt", "")

        if not vid:
            continue
        if not contains_all(title + "\n" + desc, must):
            continue

        results.append({
            "title": title,
            "link": f"https://www.youtube.com/watch?v={vid}",
            "source": sn.get("channelTitle", "YouTube"),
            "published_iso": published_at,
            "published_kst": "",
            "platform": "youtube",
            "snippet": desc,
        })
        if len(results) >= MAX_SAVE:
            break
        time.sleep(0.1)

    results = dedupe_by_title(results)
    safe_write_json(out_path, results[:MAX_SAVE])
    return results[:MAX_SAVE]

if __name__ == "__main__":
    run()
