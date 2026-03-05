import os
import requests
from typing import List, Dict, Any

from common import (
    contains_all, get_must_words, MAX_SAVE, safe_write_json, dedupe_by_title
)

TIMEOUT = 25
IG_ACCESS_TOKEN = os.getenv("IG_ACCESS_TOKEN", "").strip()
IG_USER_ID = os.getenv("IG_USER_ID", "").strip()

def ig_list_media(user_id: str, access_token: str, limit: int = 50) -> List[Dict[str, Any]]:
    url = f"https://graph.facebook.com/v19.0/{user_id}/media"
    params = {
        "access_token": access_token,
        "fields": "id,caption,permalink,timestamp,media_type,username",
        "limit": min(limit, 50),
    }
    r = requests.get(url, params=params, timeout=TIMEOUT)
    r.raise_for_status()
    return (r.json() or {}).get("data", []) or []

def run(out_path: str = "docs/data/instagram.json") -> List[Dict[str, Any]]:
    # 설정 없으면 그냥 빈 배열 저장(사이트는 정상 작동)
    if not IG_ACCESS_TOKEN or not IG_USER_ID:
        safe_write_json(out_path, [])
        return []

    must = get_must_words()
    items = ig_list_media(IG_USER_ID, IG_ACCESS_TOKEN, limit=50)

    results = []
    for it in items:
        caption = it.get("caption", "") or ""
        if not caption:
            continue
        if not contains_all(caption, must):
            continue

        results.append({
            "title": caption[:60].replace("\n", " ") + ("…" if len(caption) > 60 else ""),
            "link": it.get("permalink", ""),
            "source": it.get("username", "Instagram"),
            "published_iso": it.get("timestamp", ""),
            "published_kst": "",
            "platform": "instagram",
            "snippet": caption,
        })
        if len(results) >= MAX_SAVE:
            break

    results = dedupe_by_title(results)
    safe_write_json(out_path, results[:MAX_SAVE])
    return results[:MAX_SAVE]

if __name__ == "__main__":
    run()
