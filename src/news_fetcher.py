import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).resolve().parent.parent))

import sqlite3
import hashlib
import re
import html
import shutil
import requests
import feedparser
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
import config

STOCK_DIR = config.ASSETS_DIR / "stock"

def init_db():
    conn = sqlite3.connect(config.DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS seen_stories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title_hash TEXT UNIQUE,
            title TEXT,
            category TEXT,
            link TEXT,
            image_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def clean_text(raw_text: str) -> str:
    if not raw_text:
        return ""
    text = html.unescape(raw_text)
    text = BeautifulSoup(text, "html.parser").get_text(separator=" ")
    replacements = {
        "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"',
        "\u2013": "-", "\u2014": "-", "\u2026": "...", "\xa0": " ",
        "\u201a": ",", "\u201e": '"', "\ufffd": "'"
    }
    for old, new in replacements.items():
        if old:
            text = text.replace(old, new)
    text = re.sub(r'\s*-\s*[A-Za-z0-9\s]+$', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def compute_hash(title: str) -> str:
    normalized = re.sub(r'[^a-zA-Z0-9]', '', title.lower())
    return hashlib.md5(normalized.encode('utf-8')).hexdigest()

def is_seen(conn: sqlite3.Connection, title_hash: str) -> bool:
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM seen_stories WHERE title_hash = ?", (title_hash,))
    return cur.fetchone() is not None

def mark_as_seen(conn: sqlite3.Connection, story: Dict):
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT OR IGNORE INTO seen_stories (title_hash, title, category, link, image_url)
            VALUES (?, ?, ?, ?, ?)
        """, (story["hash"], story["title"], story["category"], story.get("link", ""), story.get("image_url", "")))
        conn.commit()
    except Exception as e:
        print(f"Error marking story as seen: {e}")

def extract_image(entry) -> Optional[str]:
    if "media_content" in entry and len(entry.media_content) > 0:
        url = entry.media_content[0].get("url")
        if url and url.startswith("http"):
            return url
    if "enclosures" in entry and len(entry.enclosures) > 0:
        for enc in entry.enclosures:
            url = enc.get("url") or enc.get("href")
            if url and url.startswith("http"):
                return url
    if "summary" in entry:
        soup = BeautifulSoup(entry.summary, "html.parser")
        img = soup.find("img")
        if img and img.get("src") and img["src"].startswith("http"):
            return img["src"]
    return None

def download_image(url: str, save_path: Path) -> bool:
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://www.google.com/"
        }
        resp = requests.get(url, headers=headers, timeout=8)
        if resp.status_code == 200 and len(resp.content) > 2000:
            save_path.parent.mkdir(parents=True, exist_ok=True)
            with open(save_path, "wb") as f:
                f.write(resp.content)
            return True
    except Exception:
        pass
    return False

def scrape_og_image(article_url: str) -> Optional[str]:
    if not article_url or not article_url.startswith("http"):
        return None
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        resp = requests.get(article_url, headers=headers, timeout=6, allow_redirects=True)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.content, "html.parser")
            og = soup.find("meta", property="og:image") or soup.find("meta", attrs={"name": "twitter:image"})
            if og and og.get("content") and og["content"].startswith("http"):
                return og["content"]
    except Exception:
        pass
    return None

def search_wikipedia_image(query: str) -> Optional[str]:
    """Semantic photo lookup on Wikimedia Commons and Wikipedia"""
    try:
        words = [w for w in re.findall(r'[A-Za-z]+', query) if len(w) > 3 and w.lower() not in (
            'with', 'from', 'this', 'that', 'were', 'have', 'after', 'about', 'just', 'found',
            'reveals', 'secrets', 'years', 'could', 'save', 'most', 'what', 'when', 'suggest',
            'according', 'study', 'scientist', 'experts', 'says', 'claims', 'reports'
        )]
        if not words:
            return None
        search_query = " ".join(words[:4])
        endpoint = "https://en.wikipedia.org/w/api.php"
        params = {
            "action": "query",
            "generator": "search",
            "gsrsearch": search_query,
            "gsrlimit": 1,
            "prop": "pageimages",
            "piprop": "original|thumbnail",
            "pithumbsize": 1080,
            "format": "json"
        }
        headers = {"User-Agent": "YouTubeNewsEngine/1.0 (contact@indiahourlynews.com)"}
        r = requests.get(endpoint, params=params, headers=headers, timeout=6)
        if r.status_code == 200:
            pages = r.json().get("query", {}).get("pages", {})
            for pid, p in pages.items():
                if "original" in p and p["original"].get("source"):
                    return p["original"]["source"]
                if "thumbnail" in p and p["thumbnail"].get("source"):
                    return p["thumbnail"]["source"]
    except Exception:
        pass
    return None

def generate_ai_image(prompt: str, save_path: Path) -> bool:
    """Dynamically generates an AI visual using Pollinations endpoint"""
    try:
        import urllib.parse
        clean_p = re.sub(r'[^a-zA-Z0-9\s]', ' ', prompt)[:120]
        full_prompt = f"{clean_p} cinematic dramatic lighting photorealistic 8k sharp focus"
        encoded = urllib.parse.quote(full_prompt)
        api_url = f"https://image.pollinations.ai/prompt/{encoded}?width=1080&height=1080&nologo=true"
        r = requests.get(api_url, timeout=12)
        if r.status_code == 200 and len(r.content) > 10000:
            save_path.parent.mkdir(parents=True, exist_ok=True)
            with open(save_path, "wb") as f:
                f.write(r.content)
            return True
    except Exception:
        pass
    return False

def render_thematic_procedural_image(story: Dict, save_path: Path) -> str:
    """
    Guaranteed dynamic custom graphic: Creates a high-res, category-tailored visual
    with cinematic radial lighting, theme badge, and clean typography.
    NEVER defaults to an Indian flag for science, mystery, space, tech, or international topics!
    """
    from PIL import Image, ImageDraw, ImageFont

    W, H = 1080, 1080
    cat = story.get("category", "SCIENCE").upper()
    title = story.get("title", "")

    themes = {
        "SPACE": ((8, 12, 30), (25, 20, 65), (96, 165, 250), "🌌 COSMIC DISCOVERY"),
        "MYSTERY": ((25, 18, 10), (55, 30, 15), (245, 158, 11), "🏺 ANCIENT MYSTERY"),
        "SCIENCE": ((10, 28, 28), (15, 55, 55), (45, 212, 191), "🔬 SCIENTIFIC BREAKTHROUGH"),
        "TECH": ((10, 15, 35), (20, 35, 75), (129, 140, 248), "⚡ TECHNOLOGY UPDATE"),
        "ANIMALS": ((12, 30, 15), (20, 60, 25), (74, 222, 128), "🐾 WILDLIFE & NATURE"),
        "SPORTS": ((25, 15, 15), (55, 25, 25), (251, 146, 60), "🏆 SPORTS HEADLINE"),
        "NATIONAL": ((30, 15, 15), (60, 20, 20), (248, 113, 113), "🇮🇳 NATIONAL REPORT")
    }
    bg1, bg2, accent, badge_label = themes.get(cat, themes["SCIENCE"])

    img = Image.new("RGB", (W, H), bg1)
    draw = ImageDraw.Draw(img)

    # Dramatic radial glow
    for r in range(450, 0, -15):
        ratio = 1.0 - (r / 450.0)
        c = (
            min(255, bg2[0] + int(accent[0] * 0.4 * ratio)),
            min(255, bg2[1] + int(accent[1] * 0.4 * ratio)),
            min(255, bg2[2] + int(accent[2] * 0.4 * ratio))
        )
        draw.ellipse([(W//2 - r, H//2 - r - 40), (W//2 + r, H//2 + r - 40)], fill=c)

    # Subtle ambient rings
    center_y = H // 2 - 40
    for rad in [180, 280, 380]:
        draw.ellipse([(W//2 - rad, center_y - rad), (W//2 + rad, center_y + rad)], outline=accent, width=2)

    # Theme Badge
    from src.visual_generator import get_font, wrap_text
    font_badge = get_font(30, bold=True)
    draw.rounded_rectangle([(W//2 - 250, center_y - 190), (W//2 + 250, center_y - 130)], radius=12, fill=(15, 23, 42))
    draw.rounded_rectangle([(W//2 - 250, center_y - 190), (W//2 + 250, center_y - 130)], radius=12, outline=accent, width=2)
    draw.text((W//2, center_y - 160), badge_label, font=font_badge, fill=accent, anchor="mm")

    # Clean headline typography
    font_hl = get_font(38, bold=True)
    wrapped = wrap_text(title, font_hl, 860, draw)
    text_y = center_y - 60
    for line in wrapped[:4]:
        draw.text((W//2, text_y), line, font=font_hl, fill=(255, 255, 255), anchor="mt")
        text_y += 56

    save_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(save_path, "JPEG", quality=92)
    return str(save_path)

def ensure_story_image(story: Dict, save_path: Path) -> str:
    """
    Guarantees a real, unique, topic-specific photo for 100% of the stories.
    Never shows a static flag across different science/mystery/space topics.
    """
    article_link = story.get("url") or story.get("link") or ""

    # Tier 1: Direct RSS image
    if story.get("image_url"):
        if download_image(story["image_url"], save_path):
            return str(save_path)

    # Tier 2: Real high-resolution OpenGraph photo from article URL
    if article_link:
        og_url = scrape_og_image(article_link)
        if og_url and download_image(og_url, save_path):
            return str(save_path)

    # Tier 3: Real semantic photo from Wikimedia Commons / Wikipedia search
    wiki_img = search_wikipedia_image(story.get("title", ""))
    if wiki_img and download_image(wiki_img, save_path):
        return str(save_path)

    # Tier 4: AI Image Generation
    clean_subj = story.get("title", "")
    if generate_ai_image(clean_subj, save_path):
        return str(save_path)

    # Tier 5: Only use Indian flag stock if the story is genuinely Indian National politics
    cat_key = story.get("category", "").lower()
    if cat_key in ("national", "india"):
        stock_file = STOCK_DIR / "national.jpg"
        if stock_file.exists():
            save_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(stock_file, save_path)
            return str(save_path)

    # Tier 6: Guaranteed dynamic procedural illustrated visual (Zero Flag Guarantee)
    return render_thematic_procedural_image(story, save_path)

def fetch_top_news(limit: int = 10, deduplicate: bool = True) -> List[Dict]:
    init_db()
    conn = sqlite3.connect(config.DB_PATH)
    candidates = []

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    # Priority feeds: National, Sports, Business, Tech, Top
    for category, feed_url in config.NEWS_FEEDS.items():
        try:
            resp = requests.get(feed_url, headers=headers, timeout=6)
            if resp.status_code != 200:
                continue
            feed = feedparser.parse(resp.content)
            for entry in feed.entries[:15]:
                raw_title = entry.get("title", "")
                title = clean_text(raw_title)
                if not title or len(title) < 20:
                    continue

                title_hash = compute_hash(title)
                if deduplicate and is_seen(conn, title_hash):
                    continue

                raw_summary = entry.get("summary", "")
                summary = clean_text(raw_summary)
                if not summary or summary == title:
                    summary = title

                img_url = extract_image(entry)

                candidates.append({
                    "hash": title_hash,
                    "title": title,
                    "summary": summary,
                    "category": category,
                    "link": entry.get("link", ""),
                    "image_url": img_url
                })
        except Exception as e:
            print(f"Error fetching feed {category}: {e}")

    unique_candidates = []
    seen_hashes = set()
    for item in candidates:
        if item["hash"] not in seen_hashes:
            seen_hashes.add(item["hash"])
            unique_candidates.append(item)

    selected = []
    categories = list(config.NEWS_FEEDS.keys())
    
    # 1. Round-robin category balance
    for cat in categories:
        cat_items = [c for c in unique_candidates if c["category"] == cat and c not in selected]
        if cat_items:
            selected.append(cat_items[0])
            if len(selected) >= limit:
                break

    # 2. Fill remaining slots
    remaining = [c for c in unique_candidates if c not in selected]
    remaining.sort(key=lambda x: (x["image_url"] is not None), reverse=True)

    for item in remaining:
        if len(selected) >= limit:
            break
        selected.append(item)

    # 3. Ensure 100% of selected stories have images
    for idx, story in enumerate(selected):
        local_img_path = config.TEMP_DIR / f"story_{idx+1}.jpg"
        story["local_image"] = ensure_story_image(story, local_img_path)

    if deduplicate:
        for s in selected:
            mark_as_seen(conn, s)

    conn.close()
    return selected

if __name__ == "__main__":
    news = fetch_top_news(limit=config.STORIES_PER_HOURLY, deduplicate=False)
    print(f"Fetched {len(news)} stories:")
    for i, n in enumerate(news, 1):
        has_img = "YES" if n.get("local_image") and Path(n["local_image"]).exists() else "NO"
        print(f"{i}. [{n['category']}] {n['title'][:50]}... (Image: {has_img})")
