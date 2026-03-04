import os, json, requests, datetime
from dateutil import parser as dateparser

API_KEY = os.environ.get("YT_API_KEY", "").strip()
QUERY = "박정현"
MAX_RESULTS = 10

def to_kst(utc_dt):
    return utc_dt + datetime.timedelta(hours=9)

def main():
    if not API_KEY:
        with open("data/youtube_search.json", "w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False, indent=2)
        return

    url = "https://www.googleapis.com/youtube/v3/search"
    params = {
        "part": "snippet",
        "q": QUERY,
        "type": "video",
        "order": "date",
        "maxResults": MAX_RESULTS,
        "key": API_KEY,
        "regionCode": "KR",
        "relevanceLanguage": "ko",
    }

    r = requests.get(url, params=params, timeout=20)
    r.raise_for_status()
    data = r.json()

    out = []
    for item in data.get("items", []):
        vid = item.get("id", {}).get("videoId", "")
        sn = item.get("snippet", {}) or {}
        title = sn.get("title", "")
        published_at = sn.get("publishedAt", "")
        thumb = (sn.get("thumbnails", {}).get("high", {}) or {}).get("url", "")
        link = f"https://www.youtube.com/watch?v={vid}" if vid else ""

        published_kst = ""
        try:
            dt_utc = dateparser.parse(published_at)
            published_kst = to_kst(dt_utc).strftime("%Y-%m-%d %H:%M")
        except Exception:
            pass

        out.append({
            "title": title,
            "link": link,
            "published_kst": published_kst,
            "thumbnail": thumb,
        })

    with open("data/youtube_search.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
