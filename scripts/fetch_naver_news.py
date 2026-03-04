import os, json, time, datetime
import requests
from bs4 import BeautifulSoup
from readability import Document
from dateutil import parser as dateparser

CLIENT_ID = os.environ.get("NAVER_CLIENT_ID", "").strip()
CLIENT_SECRET = os.environ.get("NAVER_CLIENT_SECRET", "").strip()

MUST = ["박정현", "가수"]
QUERY = " ".join(MUST)

MAX_SAVE = 20
DISPLAY = 100
MAX_FETCH = 60
SLEEP_SEC = 0.6

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36"}

def strip_html(s: str) -> str:
    return BeautifulSoup(s or "", "html.parser").get_text(" ", strip=True)

def contains_all(text: str, must):
    t = (text or "").lower()
    return all(m.lower() in t for m in must)

def extract_article_text(url: str) -> str:
    try:
        resp = requests.get(url, headers=UA, timeout=25, allow_redirects=True)
        resp.raise_for_status()
        doc = Document(resp.text)
        main_html = doc.summary(html_partial=True)
        return strip_html(main_html)
    except Exception:
        return ""

def pub_to_iso(pub: str) -> str:
    if not pub:
        return ""
    try:
        dt = dateparser.parse(pub)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.timezone.utc)
        return dt.isoformat()
    except Exception:
        return ""

def pub_to_kst(pub: str) -> str:
    iso = pub_to_iso(pub)
    if not iso:
        return ""
    try:
        dt = dateparser.parse(iso)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.timezone.utc)
        kst = dt.astimezone(datetime.timezone(datetime.timedelta(hours=9)))
        return kst.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return ""

def main():
    if not CLIENT_ID or not CLIENT_SECRET:
        with open("data/naver_news.json", "w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False, indent=2)
        return

    url = "https://openapi.naver.com/v1/search/news.json"
    headers = {
        "X-Naver-Client-Id": CLIENT_ID,
        "X-Naver-Client-Secret": CLIENT_SECRET,
    }
    params = {
        "query": QUERY,
        "display": DISPLAY,
        "start": 1,
        "sort": "date",
    }

    r = requests.get(url, headers=headers, params=params, timeout=25)
    r.raise_for_status()
    data = r.json()

    results = []
    seen = set()
    fetched = 0

    for it in data.get("items", []):
        if len(results) >= MAX_SAVE:
            break

        title = strip_html(it.get("title", ""))
        desc = strip_html(it.get("description", ""))
        link = it.get("link") or it.get("originallink") or ""
        pub = it.get("pubDate", "")

        if not link or link in seen:
            continue
        seen.add(link)

        fetched += 1
        if fetched > MAX_FETCH:
            break

        time.sleep(SLEEP_SEC)
        body = extract_article_text(link)

        full_text = f"{title} {desc} {body}"
        if not contains_all(full_text, MUST):
            continue

        results.append({
            "title": title,
            "link": link,
            "source": "Naver",
            "published_iso": pub_to_iso(pub),
            "published_kst": pub_to_kst(pub),
            "platform": "naver",
        })

    results.sort(key=lambda x: x.get("published_iso",""), reverse=True)

    with open("data/naver_news.json", "w", encoding="utf-8") as f:
        json.dump(results[:MAX_SAVE], f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
