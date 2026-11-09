# 🇮🇳 India Hourly YouTube News Automation Pipeline

A fully automated, broadcast-grade pipeline that collects the top 10 news stories across India every hour and produces two video formats ready for YouTube:
1. **YouTube Shorts (9:16 vertical, <60 seconds)** — Fast-paced "Top 10 in 60s" with burned-in animated subtitles.
2. **Long-Form Broadcast (16:9 horizontal, ~5 minutes)** — In-depth bulletin with story cards, chapter markers, and categorized lower-thirds.

Powered by **Microsoft Edge Neural Voice (`en-IN-NeerjaNeural`)**, providing a sweet, natural, polite Indian female news anchor voice.

---

## 📁 Project Structure

```
d:\youtube news\
├── config.py                 # Core configurations & AI Engine thresholds
├── run_hourly.py             # Single execution orchestrator (pre-generation -> video -> stage/upload)
├── scheduler.py              # Background hourly scheduler (runs every hour at :00 IST)
├── setup_youtube.py          # 1-click YouTube OAuth connection & test tool
├── news_tracker.db           # SQLite database (topics, hooks, storyboards, learning memory)
│
├── src/
│   ├── pre_generation_engine.py # Master AI intelligence orchestrator
│   ├── topic_discovery.py       # Ingests trending facts, space, science & mysteries
│   ├── viral_scorer.py          # 6-Dimensional viral potential gate (0-100 scoring)
│   ├── hook_generator.py        # Generates 5 distinct psychological hooks & picks champion
│   ├── storyboard_planner.py    # Retention-engineered script (0-2s, 2-7s, 7-15s, loop) & visual director
│   ├── preflight_verifier.py    # Fact checking, clickbait integrity & YouTube policy check
│   ├── learning_memory.py       # Closed-loop performance memory & algorithmic weights
│   ├── news_fetcher.py          # Scrapes & deduplicates top India news stories
│   ├── visual_generator.py      # Renders news cards, headlines & category badges
│   ├── tts_engine.py            # Neerja voiceover synthesis + word-chunked dynamic captions
│   ├── video_composer.py        # FFmpeg-based seamless 44.1kHz stereo video rendering
│   └── youtube_publisher.py     # YouTube Data API direct uploader & metadata generator
│
├── assets/
│   ├── fonts/                # Bold news typography
│   ├── music/                # Swoosh sound effects and audio assets
│   ├── overlays/             # Channel logos and badges
│   └── stock/                # Category fallback image library (100% photo guarantee)
│
└── output/
    ├── longform/             # Rendered 16:9 MP4 broadcasts
    ├── shorts/               # Rendered 9:16 MP4 Shorts
    └── metadata/             # JSON files with titles, descriptions, chapters & tags
```

---

## 🧠 The AI Pre-Generation Intelligence Engine

Before rendering any video, the system runs through a **6-stage decision gate**:

1. **Trend & Curiosity Discovery (`src/topic_discovery.py`):** Ingests 40 candidate topics from LiveScience, Phys.org, ScienceDaily, Google Trends, and breaking news feeds.
2. **6-Dimensional Viral Scoring Gate (`src/viral_scorer.py`):** Scores topics (0–100) on Curiosity Gap, Surprise Factor, Visual Storytelling Potential, Audience Resonance, Saturation Penalty, and Channel Learning Weights. **Topics below 70 pts are discarded**.
3. **5-Angle Psychological Hook Generator (`src/hook_generator.py`):** Crafts 5 distinct opening angles per topic (*Paradox, Pattern Interrupt, Forbidden Curiosity, High-Stakes Question, Micro-Story*) and selects the Champion Hook.
4. **Retention Storyboard & Visual Director (`src/storyboard_planner.py`):** Maps the script to a 5-beat emotional retention curve (*Hook -> Curiosity Gap -> The Reveal -> Unexpected Twist -> Seamless Loop*) and sets camera motions and visual cues.
5. **Pre-Flight Fact & Policy Check (`src/preflight_verifier.py`):** Validates sources against verified domains and verifies 100% compliance with YouTube Community Guidelines.
6. **Closed-Loop Learning Memory (`src/learning_memory.py`):** Tracks topic scores, hook experiments, and weights categories so the engine improves after every upload.

To test the pre-generation engine independently without rendering:
```powershell
python src/pre_generation_engine.py
```

---

## ⚡ Quick Start

### 1. Run a single hourly cycle manually:
```powershell
python run_hourly.py
```
This fetches the latest 10 news stories, generates the audio, builds both videos, and saves them to `output/shorts/` and `output/longform/`.

### 2. Start the automated background scheduler:
```powershell
# Runs automatically every hour at :00 IST
python scheduler.py

# Or run one immediately and then continue hourly:
python scheduler.py --now

# Or test with custom intervals (e.g., every 30 minutes):
python scheduler.py --interval 30
```

---

## ⚙️ Configuration (`config.py`)

You can customize everything in [config.py](file:///d:/youtube%20news/config.py):
* **Voiceover:** Change `TTS_VOICE` to any Indian neural voice (e.g., `en-IN-NeerjaNeural`, `en-IN-KavyaNeural`, or `hi-IN-SwaraNeural` for Hindi).
* **Speed:** Adjust `TTS_RATE` (`+3%` is default for crisp news delivery).
* **News Sources:** Add or modify RSS feeds in `NEWS_FEEDS` (National, Business, Sports/Cricket, Tech, etc.).
* **Channel Branding:** Customize `CHANNEL_NAME` and `CHANNEL_HANDLE`.

---

## 🚀 YouTube Auto-Upload Setup

To have all generated Shorts and Long-Form bulletins automatically publish to your YouTube channel:

1. Follow the 3-minute Google Cloud setup by running:
   ```powershell
   python setup_youtube.py
   ```
2. Download your credentials file from Google Cloud Console and place it in the project root as `client_secrets.json`.
3. Run `python setup_youtube.py` again. A browser window will open once to authenticate your channel.
4. Your token will be securely saved to `token.json` and automatically refreshed in the background for unattended 24/7 uploads!
5. In `config.py`, customize your upload visibility:
   * `YOUTUBE_PRIVACY = "public"` (instant publish to feed and subscribers)
   * `YOUTUBE_PRIVACY = "unlisted"` (test links before going live)
   * `YOUTUBE_PRIVACY = "private"` (draft mode)
