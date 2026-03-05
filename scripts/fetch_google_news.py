

import json
import time
import datetime
import base64
import requests
from bs4 import BeautifulSoup
from dateutil import parser as dateparser
from readability import Document
from urllib.parse import urlparse

MUST = ["박정현", "가수"]
QUERY = " ".join(MUST)
RSS = f"https://news.google.com/rss/search?q={requests.utils.quote(QUERY)}&hl=ko&gl=KR&ceid=KR:ko"

MAX_SAVE = 20
CANDIDATES = 150
MAX_FETCH = 80
RECENT_DAYS = 90
SLEEP_SEC = 0.6

UA = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
    "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.6",
}

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

def decode_google_news_url(gn_url: str) -> str:
    """
    Google News RSS 링크(news.google.com/rss/articles/CBMi...)는 내부 인코딩된 URL인 경우가 많아
    그대로 본문을 긁으면 consent/리다이렉트 문제로 실패할 수 있음.  [oai_citation:1‡Stack Overflow](https://stackoverflow.com/questions/78838849/how-to-handle-google-consent-page-when-scrapping-article-data-using-google-news?utm_source=chatgpt.com)
    토큰을 base64(urlsafe)로 디코딩해서 원문 URL을 뽑아내는 '실용' 디코더.
    (완벽 100%는 아니지만 성공률이 확 올라감)
    """
    try:
        u = urlparse(gn_url)
        parts = u.path.split("/")
        if "articles" not in parts:
            return gn_url
        idx = parts.index("articles")
        token = parts[idx + 1] if idx + 1 < len(parts) else ""
        if not token:
            return gn_url

        # urlsafe base64 padding
        pad = "=" * (-len(token) % 4)
        raw = base64.urlsafe_b64decode(token + pad)

        # decoded bytes 안에 http(s) URL이 들어있음 → 첫 http부터 끝까지 추출 시도
        s = raw.decode("utf-8", errors="ignore")
        p = s.find("http")
        if p == -1:
            return gn_url
        url = s[p:].strip()

        # 이상한 문자 뒤는 잘라내기
        for cut in ["\x00", "\n", " "]:
            if cut in url:
                url = url.split(cut)[0]
        return url
    except Exception:
        return gn_url

def extract_article_text(url: str) -> str:
    try:
        resp = requests.get(url, headers=UA, timeout=25, allow_redirects=True)
        resp.raise_for_status()

        # 구글 동의/컨센트 페이지로 빠진 경우 본문 없음 → 빈 문자열
        if "consent.google" in resp.url or "consent" in resp.url:
            return ""

        doc = Document(resp.text)
        main_html = doc.summary(html_partial=True)
        return strip_html(main_html)
    except Exception:
        return ""

def main():
    rss_items = parse_rss()

    results = []
    seen_links = set()
    fetched = 0

    for it in rss_items:
        if len(results) >= MAX_SAVE:
            break
        if not is_recent(it["published_iso"]):
            continue

        gn_link = it["link"]
        if not gn_link:
            continue

        # 1) 구글 내부 링크 → 원문 URL 디코딩
        real_link = decode_google_news_url(gn_link)

        if real_link in seen_links:
            continue
        seen_links.add(real_link)

        fetched += 1
        if fetched > MAX_FETCH:
            break

        time.sleep(SLEEP_SEC)

        # 2) 원문 페이지에서 본문 추출
        body = extract_article_text(real_link)

        # 3) 본문 기준 키워드 검사 (본문이 비어있으면 탈락)
        if not body:
            continue

        if not contains_all(body, MUST):
            continue

        results.append({
            "title": it["title"],
            "link": real_link,
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
