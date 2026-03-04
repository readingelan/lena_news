import json, requests, datetime
from bs4 import BeautifulSoup
from dateutil import parser as dateparser

CHANNEL_ID = "UCecuhoxAW8HvAnGaNX2yE4g"
RSS = f"https://www.youtube.com/feeds/videos.xml?channel_id={CHANNEL_ID}"

def strip_html(s: str) -> str:
    return BeautifulSoup(s or "", "html.parser").get_text(" ", strip=True)

def to_kst(utc_dt):
    return utc_dt + datetime.timedelta(hours=9)

def main():
    r = requests.get(RSS, headers={"User-Agent":"Mozilla/5.0"}, timeout=20)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "xml")

    out = []
    for entry in soup.find_all("entry")[:4]:
        title = strip_html(entry.title.text if entry.title else "")
        link_tag = entry.find("link")
        link = link_tag["href"] if link_tag and link_tag.get("href") else ""
        published_raw = strip_html(entry.published.text if entry.published else "")

        published_kst = ""
        try:
            dt_utc = dateparser.parse(published_raw)
            published_kst = to_kst(dt_utc).strftime("%Y-%m-%d %H:%M")
        except Exception:
            pass

        thumb = ""
        media = entry.find("media:group")
        if media:
            t = media.find("media:thumbnail")
            if t and t.get("url"):
                thumb = t["url"]

        out.append({
            "title": title,
            "link": link,
            "published_kst": published_kst,
            "thumbnail": thumb,
        })

    with open("data/youtube_channel.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
