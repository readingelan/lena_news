import json, requests
from bs4 import BeautifulSoup
from dateutil import parser as dateparser

MUST = ["박정현", "가수"]
QUERY = " ".join(MUST)
RSS = f"https://news.google.com/rss/search?q={requests.utils.quote(QUERY)}&hl=ko&gl=KR&ceid=KR:ko"

def strip_html(s: str) -> str:
    return BeautifulSoup(s or "", "html.parser").get_text(" ", strip=True)

def contains_all(text: str, must):
    t = (text or "").lower()
    return all(m.lower() in t for m in must)

def main():
    r = requests.get(RSS, headers={"User-Agent":"Mozilla/5.0"}, timeout=20)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "xml")

    out = []
    for it in soup.find_all("item")[:80]:
        title = strip_html(it.title.text if it.title else "")
        link = strip_html(it.link.text if it.link else "")
        pub = strip_html(it.pubDate.text if it.pubDate else "")
        source = strip_html(it.source.text if it.source else "")
        desc = strip_html(it.description.text if it.description else "")

        if not contains_all(f"{title} {desc}", MUST):
            continue

        published = ""
        try:
            published = dateparser.parse(pub).strftime("%Y-%m-%d %H:%M")
        except Exception:
            pass

        out.append({
            "title": title,
            "link": link,
            "source": source,
            "published": published,
        })

    with open("data/news.json", "w", encoding="utf-8") as f:
        json.dump(out[:20], f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
