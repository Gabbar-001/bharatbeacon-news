import os
import sys
import json
from pathlib import Path

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
from src.youtube_publisher import upload_video

def main():
    print("\n" + "=" * 65)
    print("   BHARATBEACON — YOUTUBE LONG-FORM BROADCAST PUBLISHER")
    print("=" * 65)

    # 1. Locate latest Long-Form video & metadata
    lf_files = list(config.LONGFORM_OUTPUT_DIR.glob("INDIA_NEWS_*.mp4"))
    if not lf_files:
        print("[X] No generated Long-Form videos found in output/longform/")
        return

    latest_video = max(lf_files, key=lambda f: f.stat().st_mtime)
    print(f"[*] Target Video: {latest_video.name}")

    # Look for matching metadata
    ts = latest_video.stem.replace("INDIA_NEWS_", "")
    meta_path = config.METADATA_DIR / f"METADATA_longform_{ts}.json"
    if meta_path.exists():
        with open(meta_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)
    else:
        metadata = {
            "format": "longform",
            "video_path": str(latest_video),
            "title": f"BharatBeacon | Top 10 News | India's Window to the World",
            "description": f"BharatBeacon — India's Window to the World\n\n#BharatBeacon #IndiaNews",
            "tags": ["BharatBeacon", "India News", "Top 10 News"]
        }

    print(f"[*] Title:       {metadata.get('title')}")
    print(f"[*] Visibility:  {config.YOUTUBE_PRIVACY.upper()}")
    print(f"[*] File Size:   {latest_video.stat().st_size / (1024*1024):.1f} MB")

    # 2. Upload to YouTube
    print("\n[*] Uploading bytes to YouTube Data API...")
    sys.stdout.flush()

    video_id = upload_video(metadata, privacy_status=config.YOUTUBE_PRIVACY)
    if video_id and video_id != "staged_locally":
        print(f"\n[✓] PUBLISHED SUCCESSFULLY!")
        print(f"👉 Watch on YouTube: https://youtu.be/{video_id}")
        return video_id
    else:
        print("\n[!] Upload was staged or incomplete.")
        return None

if __name__ == "__main__":
    main()
