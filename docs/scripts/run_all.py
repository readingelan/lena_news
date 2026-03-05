from naver_news import run as run_naver
from google_web import run as run_google
from youtube_search import run as run_youtube
from instagram_graph import run as run_instagram

def main():
    run_naver()
    run_google()
    run_youtube()
    run_instagram()

if __name__ == "__main__":
    main()
