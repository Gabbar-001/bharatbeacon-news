import os
import sys
import json
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).resolve().parent))

# Ensure UTF-8 output on Windows
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

import config
from src.youtube_publisher import SECRETS_FILE, upload_video

def main():
    print("\n" + "=" * 65)
    print("   BHARATBEACON — YOUTUBE SHORTS PUBLISHER")
    print("=" * 65)

    # 1. Locate latest Shorts video & metadata
    shorts_files = list(config.SHORTS_OUTPUT_DIR.glob("SHORTS_*.mp4"))
    if not shorts_files:
        print("[X] No generated Shorts videos found in output/shorts/")
        return

    latest_video = max(shorts_files, key=lambda f: f.stat().st_mtime)
    print(f"[*] Target Video: {latest_video.name}")

    # Look for matching metadata
    ts = latest_video.stem.replace("SHORTS_", "")
    meta_path = config.METADATA_DIR / f"METADATA_shorts_{ts}.json"
    if meta_path.exists():
        with open(meta_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)
    else:
        metadata = {
            "format": "shorts",
            "video_path": str(latest_video),
            "title": f"BharatBeacon Top 10 Headlines #Shorts",
            "description": f"BharatBeacon — India's Window to the World\n\n#Shorts #BharatBeacon #IndiaNews",
            "tags": ["Shorts", "BharatBeacon", "India News"]
        }

    print(f"[*] Title:       {metadata.get('title')}")
    print(f"[*] Visibility:  {config.YOUTUBE_PRIVACY.upper()}")

    # 2. Check credentials
    if not SECRETS_FILE.exists():
        print("\n" + "-" * 65)
        print("[!] YouTube API Credentials ('client_secrets.json') Not Found!")
        print("-" * 65)
        print("To enable automatic API upload directly to your YouTube channel:")
        print("1. Download your OAuth Client ID JSON from Google Cloud Console.")
        print(f"2. Save it as: {SECRETS_FILE}")
        print("3. Run: python setup_youtube.py")
        print("\nAlternatively, you can upload manually right now via YouTube Studio:")
        print(f"👉 File: {latest_video}")
        print("=" * 65 + "\n")
        return

    # 3. Publish via YouTube Data API
    print("\n[*] Uploading to YouTube...")
    video_id = upload_video(metadata, privacy_status=config.YOUTUBE_PRIVACY)
    if video_id and video_id != "staged_locally":
        print(f"\n[✓] PUBLISHED SUCCESSFULLY!")
        print(f"👉 Watch on YouTube: https://youtube.com/shorts/{video_id}")
    else:
        print("\n[!] Upload was staged or incomplete. Check setup_youtube.py.")

if __name__ == "__main__":
    main()
