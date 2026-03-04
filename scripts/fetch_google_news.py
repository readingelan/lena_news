import json
import time
import datetime
import requests
from bs4 import BeautifulSoup
from dateutil import parser as dateparser
from readability import Document

MUST = ["박정현", "가수"]
QUERY = " ".join(MUST)
RSS = f"https://news.google.com/rss/search?q={requests.utils.quote(QUERY)}&hl=ko&gl=KR&ceid=KR:ko"

MAX_SAVE = 20
CANDIDATES = 120
MAX_FETCH = 60
RECENT_DAYS = 60      # 너무 옛날 뉴스 방지. “일주일만 보기”는 프론트 체크박스로 처리.
SLEEP_SEC = 0.6

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36"}

def strip_html(s: str) -> str:
    return BeautifulSoup(s or "", "html.parser").get_text(" ", strip=True)

def contains_all(text: str, must):
    t = (text or "").lower()
    return all(m.lower() in t for m in must)

def parse_rss():
    r = requests.get(RSS, headers=UA, timeout=25)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "xml")
    items = soup.find_all("item")[:CANDIDATES]
    out = []
    for it in items:
        title = strip_html(it.title.text if it.title else "")
        link = strip_html(it.link.text if it.link else "")
        pub = strip_html(it.pubDate.text if it.pubDate else "")
        source = strip_html(it.source.text if it.source else "")
        desc = strip_html(it.description.text if it.description else "")

        published_iso = ""
        try:
            dt = dateparser.parse(pub)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=datetime.timezone.utc)
            published_iso = dt.isoformat()
        except Exception:
            published_iso = ""

        out.append({
            "title": title,
            "link": link,
            "source": source,
            "desc": desc,
            "published_iso": published_iso,
        })
    return out

def is_recent(published_iso: str) -> bool:
    if not published_iso:
        return True
    try:
        dt = dateparser.parse(published_iso)
    except Exception:
        return True
    cutoff = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc) - datetime.timedelta(days=RECENT_DAYS)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    return dt >= cutoff

def to_kst_str(published_iso: str) -> str:
    if not published_iso:
        return ""
    try:
        dt = dateparser.parse(published_iso)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.timezone.utc)
        kst = dt.astimezone(datetime.timezone(datetime.timedelta(hours=9)))
        return kst.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return ""

def extract_article_text(url: str) -> str:
    try:
        resp = requests.get(url, headers=UA, timeout=25, allow_redirects=True)
        resp.raise_for_status()
        doc = Document(resp.text)
        main_html = doc.summary(html_partial=True)
        return strip_html(main_html)
    except Exception:
        return ""

def main():
    rss_items = parse_rss()

    results = []
    seen = set()
    fetched = 0

    for it in rss_items:
        if len(results) >= MAX_SAVE:
            break
        if not is_recent(it["published_iso"]):
            continue

        link = it["link"]
        if not link or link in seen:
            continue
        seen.add(link)

        fetched += 1
        if fetched > MAX_FETCH:
            break

        time.sleep(SLEEP_SEC)
        body = extract_article_text(link)

        full_text = f"{it['title']} {it['desc']} {body}"
        if not contains_all(full_text, MUST):
            continue

        results.append({
            "title": it["title"],
            "link": link,
            "source": it["source"] or "Google News",
            "published_iso": it["published_iso"],
            "published_kst": to_kst_str(it["published_iso"]),
            "platform": "google",
        })

    results.sort(key=lambda x: x.get("published_iso",""), reverse=True)

    with open("data/google_news.json", "w", encoding="utf-8") as f:
        json.dump(results[:MAX_SAVE], f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
