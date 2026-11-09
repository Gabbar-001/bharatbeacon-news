import sys
import os
import re
import html
import requests
import feedparser
from pathlib import Path
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup

# Ensure UTF-8 output on Windows
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

sys.path.append(str(Path(__file__).resolve().parent.parent))
import config
from src.learning_memory import get_connection

DISCOVERY_FEEDS = [
    # Curiosity, Science & Mystery Feeds (High viral & retention potential)
    {"name": "LiveScience", "category": "MYSTERY", "url": "https://www.livescience.com/feeds/all"},
    {"name": "PhysOrgSpace", "category": "SPACE", "url": "https://phys.org/rss-feed/breaking/space-news/"},
    {"name": "ScienceDaily", "category": "SCIENCE", "url": "https://www.sciencedaily.com/rss/top/science.xml"},
    
    # Trending Searches in India (Google Trends breakout queries)
    {"name": "GoogleTrendsIN", "category": "TRENDING", "url": "https://trends.google.com/trending/rss?geo=IN"},
    
    # National & Breaking Updates
    {"name": "GoogleNewsIN", "category": "NATIONAL", "url": "https://news.google.com/rss?hl=en-IN&gl=IN&ceid=IN:en"},
    {"name": "NDTVTop", "category": "NATIONAL", "url": "https://feeds.feedburner.com/ndtvnews-top-stories"},
    {"name": "IE_Tech", "category": "TECH", "url": "https://indianexpress.com/section/technology/feed/"},
]

def clean_html(raw_html: str) -> str:
    if not raw_html:
        return ""
    text = html.unescape(raw_html)
    text = BeautifulSoup(text, "html.parser").get_text(separator=" ")
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def detect_category(title: str, summary: str, default_cat: str) -> str:
    combined = f"{title} {summary}".lower()
    if any(w in combined for w in ["space", "nasa", "isro", "planet", "galaxy", "asteroid", "telescope", "moon", "mars", "cosmic", "universe"]):
        return "SPACE"
    if any(w in combined for w in ["ancient", "baffled", "unexplained", "mystery", "archaeologist", "discovery", "secret", "tomb", "curse", "alien", "ocean"]):
        return "MYSTERY"
    if any(w in combined for w in ["quantum", "brain", "human body", "genetics", "dopamine", "scientists discover", "physics", "dna", "biology"]):
        return "SCIENCE"
    if any(w in combined for w in ["ai", "robot", "apple", "google", "cyber", "software", "tech", "gadget", "chip", "nvidia"]):
        return "TECH"
    if any(w in combined for w in ["cricket", "ipl", "match", "world cup", "football", "goal", "tournament"]):
        return "SPORTS"
    if any(w in combined for w in ["sensex", "nifty", "economy", "market", "rbi", "bank", "stock", "gdp", "rupee"]):
        return "BUSINESS"
    return default_cat

def is_duplicate(title: str, existing_titles: set) -> bool:
    clean_t = re.sub(r'[^a-zA-Z0-9]', '', title.lower())
    for ext in existing_titles:
        ext_clean = re.sub(r'[^a-zA-Z0-9]', '', ext.lower())
        if clean_t in ext_clean or ext_clean in clean_t:
            return True
        # Check token similarity
        words_a = set(clean_t[:40].split())
        words_b = set(ext_clean[:40].split())
        if words_a and words_b and len(words_a & words_b) / max(len(words_a), len(words_b)) > 0.7:
            return True
    return False

def discover_candidate_topics(max_candidates: int = 40) -> List[Dict[str, Any]]:
    """
    Ingests trending facts, science, mysteries, and national stories across 7 sources.
    Deduplicates against previous productions and returns scored candidate topics.
    """
    conn = get_connection()
    cur = conn.cursor()

    # Load seen titles
    cur.execute("SELECT title FROM seen_stories ORDER BY id DESC LIMIT 200")
    seen_db = {r["title"] for r in cur.fetchall()}

    cur.execute("SELECT title FROM topic_pool WHERE status = 'produced' ORDER BY id DESC LIMIT 200")
    for r in cur.fetchall():
        seen_db.add(r["title"])

    conn.close()

    candidates = []
    collected_titles = set(seen_db)

    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

    for feed_info in DISCOVERY_FEEDS:
        feed_name = feed_info["name"]
        feed_cat = feed_info["category"]
        feed_url = feed_info["url"]

        try:
            # Custom request with timeout and proper User-Agent
            resp = requests.get(feed_url, headers=headers, timeout=8)
            if resp.status_code != 200:
                continue

            parsed = feedparser.parse(resp.content)
            entries = parsed.entries[:10]  # Take top 10 per feed

            for entry in entries:
                raw_title = clean_html(entry.get("title", ""))
                if not raw_title or len(raw_title) < 15:
                    continue

                if is_duplicate(raw_title, collected_titles):
                    continue

                raw_summary = clean_html(entry.get("summary", entry.get("description", "")))
                link = entry.get("link", "")

                # Image extraction if available
                img_url = ""
                if "media_content" in entry and entry.media_content:
                    img_url = entry.media_content[0].get("url", "")
                elif "enclosures" in entry and entry.enclosures:
                    img_url = entry.enclosures[0].get("href", "")

                cat = detect_category(raw_title, raw_summary, feed_cat)

                candidate = {
                    "source": feed_name,
                    "title": raw_title,
                    "clean_title": raw_title,
                    "summary": raw_summary[:400] if raw_summary else raw_title,
                    "category": cat,
                    "url": link,
                    "link": link,
                    "image_url": img_url,
                }

                candidates.append(candidate)
                collected_titles.add(raw_title)

                if len(candidates) >= max_candidates:
                    break

        except Exception as e:
            # Continue gracefully to next feed
            continue

        if len(candidates) >= max_candidates:
            break

    return candidates

if __name__ == "__main__":
    print("[*] Running AI Trend & Curiosity Discovery...")
    discovered = discover_candidate_topics(max_candidates=25)
    print(f"[OK] Discovered {len(discovered)} fresh candidate topics across categories:")
    for idx, item in enumerate(discovered[:10], 1):
        print(f"  {idx:2d}. [{item['category']:8s}] {item['title'][:65]}... ({item['source']})")
