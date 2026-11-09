import os
from pathlib import Path

# Base Paths
BASE_DIR = Path(__file__).resolve().parent
SRC_DIR = BASE_DIR / "src"
ASSETS_DIR = BASE_DIR / "assets"
OUTPUT_DIR = BASE_DIR / "output"

FONTS_DIR = ASSETS_DIR / "fonts"
MUSIC_DIR = ASSETS_DIR / "music"
OVERLAYS_DIR = ASSETS_DIR / "overlays"

LONGFORM_OUTPUT_DIR = OUTPUT_DIR / "longform"
SHORTS_OUTPUT_DIR = OUTPUT_DIR / "shorts"
TEMP_DIR = OUTPUT_DIR / "temp"
METADATA_DIR = OUTPUT_DIR / "metadata"

DB_PATH = BASE_DIR / "news_tracker.db"

# Create directories if not exist
for p in [LONGFORM_OUTPUT_DIR, SHORTS_OUTPUT_DIR, TEMP_DIR, METADATA_DIR, FONTS_DIR, MUSIC_DIR, OVERLAYS_DIR]:
    p.mkdir(parents=True, exist_ok=True)

# Voiceover Settings (Sweet Indian Female Voice)
TTS_VOICE = "en-IN-NeerjaNeural"  # Clear, natural, polite Indian female voice
TTS_RATE = "+3%"                   # Crisp news delivery cadence
TTS_PITCH = "+0Hz"

# Video Specifications
LONGFORM_WIDTH = 1920
LONGFORM_HEIGHT = 1080
SHORTS_WIDTH = 1080
SHORTS_HEIGHT = 1920
FPS = 30

# Font Configuration
local_font = FONTS_DIR / "segoeuib.ttf"
if local_font.exists():
    FONT_PATH = str(local_font)
elif os.path.exists("C:/Windows/Fonts/segoeuib.ttf"):
    FONT_PATH = "C:/Windows/Fonts/segoeuib.ttf"
elif (FONTS_DIR / "arialbd.ttf").exists():
    FONT_PATH = str(FONTS_DIR / "arialbd.ttf")
else:
    FONT_PATH = "C:/Windows/Fonts/arialbd.ttf"

# Color Palette (Modern Indian News Network Style)
COLOR_BG_DARK = (15, 23, 42)       # Slate 900
COLOR_CARD = (30, 41, 59)          # Slate 800
COLOR_PRIMARY_RED = (220, 38, 38)  # Breaking Red
COLOR_GOLD = (245, 158, 11)        # Gold/Amber
COLOR_TEXT_WHITE = (255, 255, 255)
COLOR_TEXT_MUTED = (148, 163, 184)

# Channel Branding
CHANNEL_NAME = "BharatBeacon"
CHANNEL_HANDLE = "@BharatBeacon"
CHANNEL_TAGLINE = "India's Window to the World"

# India RSS Feeds
NEWS_FEEDS = {
    "TOP": "https://news.google.com/rss?hl=en-IN&gl=IN&ceid=IN:en",
    "NATIONAL": "https://feeds.feedburner.com/ndtvnews-top-stories",
    "INDIA": "https://indianexpress.com/section/india/feed/",
    "BUSINESS": "https://indianexpress.com/section/business/feed/",
    "SPORTS": "https://indianexpress.com/section/sports/feed/",
    "TECH": "https://indianexpress.com/section/technology/feed/",
}

# Number of stories to include in the hourly broadcast
STORIES_PER_HOURLY = 10

# YouTube Automation Settings
YOUTUBE_AUTO_UPLOAD = True
YOUTUBE_PRIVACY = "public"  # "public", "unlisted", or "private"

# AI Pre-Generation & Self-Learning Engine
USE_AI_INTELLIGENCE_ENGINE = True   # Evaluates topics via 6D scoring, generates 5 hooks & storyboards
VIRAL_SCORE_THRESHOLD = 70.0        # Minimum score (0-100) required to enter video production
AI_DISCOVERY_POOL_SIZE = 40         # Number of candidate topics mined per cycle

