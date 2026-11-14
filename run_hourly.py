import os
import sys
import json
from pathlib import Path
from datetime import datetime, timezone, timedelta

# Add project root to sys.path
sys.path.append(str(Path(__file__).resolve().parent))

# Ensure UTF-8 output on Windows
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

import config
from src.news_fetcher import fetch_top_news, init_db
from src.learning_memory import init_learning_tables
from src.video_composer import build_longform_video, build_shorts_video, clean_temp_files
from src.youtube_publisher import save_metadata, upload_video
from src.regional_translator import generate_youtube_localizations, generate_regional_audio_tracks

class TeeLogger:
    def __init__(self, log_path: Path, orig_stream):
        self.orig_stream = orig_stream
        self.log_file = open(log_path, "a", encoding="utf-8", errors="replace")
        self.encoding = getattr(orig_stream, "encoding", "utf-8")
        self.errors = getattr(orig_stream, "errors", "replace")

    def write(self, message):
        try:
            self.orig_stream.write(message)
        except Exception:
            pass
        try:
            self.log_file.write(message)
            self.log_file.flush()
        except Exception:
            pass

    def flush(self):
        try:
            self.orig_stream.flush()
        except Exception:
            pass
        try:
            self.log_file.flush()
        except Exception:
            pass

    def isatty(self):
        return getattr(self.orig_stream, "isatty", lambda: False)()

    def fileno(self):
        try:
            return self.orig_stream.fileno()
        except Exception:
            return self.log_file.fileno()

def sync_pending_backlog_uploads(playlist_map):
    """
    Checks for any pending/un-uploaded videos from previous hours in output/metadata
    and uploads them automatically.
    """
    history_file = config.OUTPUT_DIR / "uploaded_history.json"
    uploaded_paths = set()
    if history_file.exists():
        try:
            with open(history_file, "r", encoding="utf-8") as f:
                uploaded_paths = set(json.load(f))
        except Exception:
            pass

    meta_dir = config.OUTPUT_DIR / "metadata"
    if not meta_dir.exists():
        return

    for meta_file in sorted(meta_dir.glob("METADATA_*.json")):
        try:
            with open(meta_file, "r", encoding="utf-8") as f:
                meta = json.load(f)
            vpath = meta.get("video_path")
            if not vpath or not Path(vpath).exists() or str(vpath) in uploaded_paths:
                continue

            # Determine playlist
            fmt = meta.get("format", "shorts")
            pl_key = "news_longform" if fmt == "longform" else "news_shorts"
            meta["playlist_id"] = playlist_map.get(pl_key, {}).get("id")
            meta["category_id"] = "25"

            print(f"\n[BACKLOG SYNC] Auto-uploading pending before-hour video: {Path(vpath).name}...")
            vid = upload_video(meta, privacy_status="public")
            if vid:
                uploaded_paths.add(str(vpath))
                print(f"  [BACKLOG SYNC OK] Uploaded to YouTube: https://youtu.be/{vid}")
        except Exception as e:
            print(f"  [BACKLOG SYNC NOTICE] Could not sync {meta_file.name}: {e}")

    try:
        with open(history_file, "w", encoding="utf-8") as f:
            json.dump(list(uploaded_paths), f, indent=2)
    except Exception:
        pass

def execute_hourly_cycle(deduplicate: bool = True):
    IST = timezone(timedelta(hours=5, minutes=30))
    start_time = datetime.now(IST)
    timestamp_str = start_time.strftime("%Y%m%d_%H%M")

    # Broadcast Target: represents the completed 'before hour' news cycle
    # E.g. when executing at 09:15 AM IST, this covers the 08:00 AM - 09:00 AM hour
    target_time = start_time - timedelta(hours=1) if start_time.minute >= 10 else start_time
    hour_display = target_time.strftime("%I:00 %p IST")
    date_display = target_time.strftime("%d %B %Y")

    logs_dir = config.OUTPUT_DIR / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_file = logs_dir / f"broadcast_{timestamp_str}.log"
    sys.stdout = TeeLogger(log_file, sys.stdout)
    sys.stderr = TeeLogger(log_file, sys.stderr)

    print("\n" + "=" * 65)
    print(f"  [BHARATBEACON] BHARATBEACON — India's Window to the World")
    print(f"  Broadcast Target: {hour_display} (Before-Hour News Cycle) | {date_display}")
    print(f"  Execution Time:   {start_time.strftime('%I:%M %p IST')}")
    print(f"  Log File:         {log_file}")
    print("=" * 65)

    # 0. Initialize Database Tables
    init_db()
    init_learning_tables()

    # 1. Load Playlist IDs
    pl_file = Path("playlists.json")
    playlist_map = {}
    if pl_file.exists():
        with open(pl_file, "r", encoding="utf-8") as f:
            playlist_map = json.load(f)

    shorts_playlist_id = playlist_map.get("news_shorts", {}).get("id")
    longform_playlist_id = playlist_map.get("news_longform", {}).get("id")

    # Auto-upload any pending before-hour videos
    print("\n[SYNC] Checking for pending before-hour videos to upload...")
    sync_pending_backlog_uploads(playlist_map)

    # 2. Fetch Top News Stories (AI Intelligence Engine or Feeds)
    if getattr(config, "USE_AI_INTELLIGENCE_ENGINE", False):
        print(f"\n[1/5] Running AI Pre-Generation Engine (Viral Discovery & Hook Engineering)...")
        from src.pre_generation_engine import execute_pre_generation_pipeline
        from src.news_fetcher import ensure_story_image
        stories = execute_pre_generation_pipeline(
            target_count=config.STORIES_PER_HOURLY,
            min_score=config.VIRAL_SCORE_THRESHOLD,
            is_shorts=True
        )
        if not stories:
            print("[!] AI Engine returned 0 approved topics. Falling back to breaking feeds.")
            stories = fetch_top_news(limit=config.STORIES_PER_HOURLY, deduplicate=deduplicate)
        else:
            for idx, story in enumerate(stories):
                local_img_path = config.TEMP_DIR / f"story_{idx+1}.jpg"
                story["local_image"] = ensure_story_image(story, local_img_path)
    else:
        print(f"\n[1/5] Fetching top {config.STORIES_PER_HOURLY} verified breaking stories across India...")
        stories = fetch_top_news(limit=config.STORIES_PER_HOURLY, deduplicate=deduplicate)

    if not stories:
        print("[!] No fresh stories found this cycle. Skipping.")
        return

    print(f"[OK] Retrieved {len(stories)} stories for broadcast:")
    for idx, s in enumerate(stories, 1):
        has_img = "Image" if s.get("local_image") else "Graphic"
        print(f"   {idx:2d}. [{s.get('category', 'NEWS'):8s}] {s['title'][:55]}... ({has_img})")

    # 15-Minute Scheduled Publishing on YouTube
    now_ist = datetime.now(IST)
    minute = now_ist.minute
    remainder = minute % 15
    mins_to_add = 15 - remainder
    if mins_to_add < 4:
        mins_to_add += 15
    scheduled_dt = (now_ist + timedelta(minutes=mins_to_add)).replace(second=0, microsecond=0)
    publish_at_iso = scheduled_dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    scheduled_display = scheduled_dt.strftime("%I:%M %p IST")
    print(f"\n[SCHEDULE] Videos will be SCHEDULED for YouTube release at: {scheduled_display} ({publish_at_iso})")

    # 3. Build YouTube Shorts (9:16)
    print("\n[2/5] Generating 9:16 YouTube Shorts video with animated captions...")
    shorts_meta = build_shorts_video(stories, timestamp_str)
    shorts_meta["playlist_id"] = shorts_playlist_id
    shorts_meta["category_id"] = "25"  # News & Politics
    shorts_meta["publish_at"] = publish_at_iso

    # 4. Build Long-Form Broadcast (16:9)
    print("\n[3/5] Generating 16:9 Long-Form broadcast video with chapter cards...")
    longform_meta = build_longform_video(stories, timestamp_str)
    longform_meta["playlist_id"] = longform_playlist_id
    longform_meta["category_id"] = "25"  # News & Politics
    longform_meta["publish_at"] = publish_at_iso

    # 5. AI Regional Multi-Language Localization (Telugu, Kannada, Hindi)
    print("\n[4/5] Engineering AI Regional Multi-Language Localizations & Audio Tracks...")
    # Telugu, Kannada, Hindi Localizations for Shorts
    shorts_locs = generate_youtube_localizations(shorts_meta["title"], shorts_meta["description"])
    shorts_meta["localizations"] = shorts_locs
    print(f"      [OK] Attached Telugu, Kannada & Hindi title localizations for Shorts")

    # Telugu, Kannada, Hindi Localizations for Long-form
    lf_locs = generate_youtube_localizations(longform_meta["title"], longform_meta["description"])
    longform_meta["localizations"] = lf_locs
    print(f"      [OK] Attached Telugu, Kannada & Hindi title localizations for Long-Form")

    # Generate Synchronized Regional Audio Tracks (for YouTube Multi-Track Audio)
    combined_script = " ".join([s.get("summary", s["title"]) for s in stories[:5]])
    generate_regional_audio_tracks(combined_script, config.OUTPUT_DIR, timestamp_str)

    # Save metadata files
    shorts_meta_file = save_metadata(shorts_meta, timestamp_str)
    longform_meta_file = save_metadata(longform_meta, timestamp_str)

    # 6. Publish to YouTube (INSTANT PUBLIC into Dedicated Playlists)
    print("\n[5/5] Publishing Videos to YouTube...")
    clean_temp_files()

    print(f"  Uploading Shorts to Playlist: {playlist_map.get('news_shorts', {}).get('title')} ({shorts_playlist_id})...")
    shorts_vid = upload_video(shorts_meta, privacy_status="public")

    print(f"  Uploading Long-form to Playlist: {playlist_map.get('news_longform', {}).get('title')} ({longform_playlist_id})...")
    longform_vid = upload_video(longform_meta, privacy_status="public")

    # Record successfully uploaded videos to history
    history_file = config.OUTPUT_DIR / "uploaded_history.json"
    uploaded_paths = set()
    if history_file.exists():
        try:
            with open(history_file, "r", encoding="utf-8") as f:
                uploaded_paths = set(json.load(f))
        except Exception:
            pass
    if shorts_vid and shorts_meta.get("video_path"):
        uploaded_paths.add(str(shorts_meta["video_path"]))
    if longform_vid and longform_meta.get("video_path"):
        uploaded_paths.add(str(longform_meta["video_path"]))
    try:
        with open(history_file, "w", encoding="utf-8") as f:
            json.dump(list(uploaded_paths), f, indent=2)
    except Exception:
        pass

    elapsed = (datetime.now(IST) - start_time).total_seconds()
    print("\n" + "=" * 65)
    print(f"  HOURLY NEWS BROADCAST COMPLETED IN {elapsed:.1f}s!")
    print(f"  Shorts Video:     https://youtube.com/shorts/{shorts_vid}")
    print(f"  Long-form Video:  https://youtu.be/{longform_vid}")
    print(f"  Shorts Playlist:  {playlist_map.get('news_shorts', {}).get('url')}")
    print(f"  Long Playlist:    {playlist_map.get('news_longform', {}).get('url')}")
    print("=" * 65 + "\n")

if __name__ == "__main__":
    execute_hourly_cycle(deduplicate=True)
