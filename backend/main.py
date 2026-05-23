from fastapi import FastAPI
from backend.services.news_service import get_top_headlines
from backend.services.summarizer_service import summarize_text

from backend.db.database import engine
from backend.models.user_model import User

app = FastAPI()

try:
    User.metadata.create_all(bind=engine)
except Exception as e:
    print("DB connection failed:", e)



@app.get("/")
def home():
    return {"message": "SmartBrief AI running"}

@app.get("/news")
def fetch_news(category: str = "sports"):

    articles = get_top_headlines(category)

    summarized_articles = []

    for article in articles:

        description = article.get("description", "")

        summary = summarize_text(description)

        summarized_articles.append({
            "title": article.get("title"),
            "summary": summary,
            "url": article.get("url")
        })

    return {
        "category": category,
        "total_articles": len(summarized_articles),
        "articles": summarized_articles
    }