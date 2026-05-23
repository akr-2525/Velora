import feedparser

# Map your app's categories to direct, high-quality RSS feeds
RSS_FEEDS = {
    "technology": "https://www.thehindu.com/sci-tech/technology/feeder/default.rss",
    "sports": "https://www.thehindu.com/sport/feeder/default.rss",
    "business": "https://www.thehindu.com/business/feeder/default.rss",
    "health": "https://timesofindia.indiatimes.com/rssfeeds/3908999.cms",
    "entertainment": "https://www.thehindu.com/entertainment/feeder/default.rss"
}

def get_top_headlines(category):
    # Default to technology if the category isn't found
    feed_url = RSS_FEEDS.get(category.lower(), RSS_FEEDS["technology"])
    
    try:
        print(f"Fetching RSS feed from: {feed_url}")
        feed = feedparser.parse(feed_url)
        
        articles = []
        # Grab the top 5 most recent articles from the feed
        for entry in feed.entries[:5]:
            articles.append({
                "title": entry.title,
                # RSS feeds usually put the article summary in 'summary' or 'description'
                "description": entry.get("summary", entry.get("description", "")), 
                "url": entry.link
            })
            
        return articles
    except Exception as e:
        print(f"Error fetching RSS news: {e}")
        return []