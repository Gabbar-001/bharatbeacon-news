import os
import sys
from pathlib import Path
from datetime import datetime

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
from src.news_fetcher import fetch_top_news
from src.video_composer import build_longform_video, build_shorts_video, clean_temp_files
from src.youtube_publisher import save_metadata, upload_video

class TeeLogger:
    def __init__(self, log_path: Path, orig_stream):
        self.orig_stream = orig_stream
        self.log_file = open(log_path, "a", encoding="utf-8", errors="replace")

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

def execute_hourly_cycle(deduplicate: bool = True):
    start_time = datetime.now()
    timestamp_str = start_time.strftime("%Y%m%d_%H%M")
    hour_display = start_time.strftime("%I:00 %p IST")
    date_display = start_time.strftime("%d %B %Y")

    logs_dir = config.OUTPUT_DIR / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_file = logs_dir / f"broadcast_{timestamp_str}.log"
    sys.stdout = TeeLogger(log_file, sys.stdout)
    sys.stderr = TeeLogger(log_file, sys.stderr)

    print("\n" + "=" * 65)
    print(f"  [BHARATBEACON] BHARATBEACON — India's Window to the World - {hour_display} | {date_display}")
    print(f"  Log File: {log_file}")
    print("=" * 65)

    # 1. Fetch Top Stories (AI Intelligence Engine or Standard News)
    if getattr(config, "USE_AI_INTELLIGENCE_ENGINE", False):
        print(f"\n[1/4] Running AI Pre-Generation Engine (Discovery, 6D Viral Gate & Hook Engineering)...")
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
            # Guarantee 100% of stories have high-res visuals
            for idx, story in enumerate(stories):
                local_img_path = config.TEMP_DIR / f"story_{idx+1}.jpg"
                story["local_image"] = ensure_story_image(story, local_img_path)
    else:
        print(f"\n[1/4] Fetching and deduplicating top {config.STORIES_PER_HOURLY} stories across India...")
        stories = fetch_top_news(limit=config.STORIES_PER_HOURLY, deduplicate=deduplicate)
    if not stories:
        print("[!] No fresh stories found this hour. Skipping cycle.")
        return

    print(f"[OK] Retrieved {len(stories)} stories:")
    for idx, s in enumerate(stories, 1):
        has_img = "Image" if s.get("local_image") else "Graphic"
        print(f"   {idx:2d}. [{s.get('category', 'NEWS'):8s}] {s['title'][:55]}... ({has_img})")

    # 2. Build YouTube Shorts (9:16)
    print("\n[2/4] Generating 9:16 YouTube Shorts video with synced captions...")
    shorts_meta = build_shorts_video(stories, timestamp_str)
    shorts_meta_file = save_metadata(shorts_meta, timestamp_str)
    print(f"[OK] Shorts ready: {shorts_meta['video_path']} ({shorts_meta['duration_seconds']:.1f}s)")

    # 3. Build Long-Form Broadcast (16:9)
    print("\n[3/4] Generating 16:9 Long-Form broadcast video with chapter cards...")
    longform_meta = build_longform_video(stories, timestamp_str)
    longform_meta_file = save_metadata(longform_meta, timestamp_str)
    m = int(longform_meta['duration_seconds'] // 60)
    s = int(longform_meta['duration_seconds'] % 60)
    print(f"[OK] Long-form ready: {longform_meta['video_path']} ({m:02d}:{s:02d})")

    # 4. Cleanup & Staging / Upload
    print("\n[4/4] Staging videos and cleaning intermediate assets...")
    clean_temp_files()

    # Stage / Upload Shorts
    upload_video(shorts_meta)
    # Stage / Upload Long-form
    upload_video(longform_meta)

    elapsed = (datetime.now() - start_time).total_seconds()
    print("\n" + "=" * 65)
    print(f"  HOURLY CYCLE COMPLETED IN {elapsed:.1f}s!")
    print(f"  Output Shorts:    {shorts_meta['video_path']}")
    print(f"  Output Long-form: {longform_meta['video_path']}")
    print(f"  Metadata:         {shorts_meta_file.parent}")
    print("=" * 65 + "\n")

if __name__ == "__main__":
    execute_hourly_cycle(deduplicate=True)
