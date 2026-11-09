import os
import sys
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
from src.youtube_publisher import SECRETS_FILE, TOKEN_FILE, get_youtube_service, verify_channel, upload_video

def print_setup_instructions():
    print("\n" + "=" * 70)
    print("   YOUTUBE AUTOMATION SETUP - GOOGLE CLOUD PROJECT GUIDE")
    print("=" * 70)
    print("""
To allow this automated pipeline to publish videos directly to your YouTube
channel, you need a free Google Cloud OAuth credential file:

----------------------------------------------------------------------
STEP 1: Create a Google Cloud Project
----------------------------------------------------------------------
1. Open Google Cloud Console:
   👉 https://console.cloud.google.com/
2. Log in with the Google Account that owns your YouTube Channel.
3. Click 'Select a project' (top-left) -> 'New Project'.
4. Name it 'YouTube-News-Automation' and click 'Create'.

----------------------------------------------------------------------
STEP 2: Enable the YouTube Data API v3
----------------------------------------------------------------------
1. In Google Cloud Console, go to 'APIs & Services' -> 'Library':
   👉 https://console.cloud.google.com/apis/library/youtube.googleapis.com
2. Click the blue 'ENABLE' button.

----------------------------------------------------------------------
STEP 3: Configure the OAuth Consent Screen
----------------------------------------------------------------------
1. Go to 'APIs & Services' -> 'OAuth consent screen':
   👉 https://console.cloud.google.com/apis/credentials/consent
2. Choose 'External' and click 'Create'.
3. Enter:
   - App name: India Hourly News Bot
   - User support email: (Your email)
   - Developer contact email: (Your email)
4. Click 'Save and Continue'.
5. On the 'Scopes' step, click 'Save and Continue'.
6. On the 'Test users' step, click '+ ADD USERS' and add your Google email address.
   (⚠️ Important: Your channel's email must be added here as a Test User!)
7. Click 'Save and Continue' and finish.

----------------------------------------------------------------------
STEP 4: Create OAuth Client ID & Download Credentials
----------------------------------------------------------------------
1. Go to 'APIs & Services' -> 'Credentials':
   👉 https://console.cloud.google.com/apis/credentials
2. Click '+ CREATE CREDENTIALS' (at top) -> 'OAuth client ID'.
3. Application type: Select 'Desktop app'.
4. Name: 'Desktop Client'.
5. Click 'Create'.
6. In the popup dialog, click 'DOWNLOAD JSON'.
7. Rename the downloaded file to:
   👉 client_secrets.json
8. Move that file into this project folder:
   👉 """ + str(config.BASE_DIR) + """\\client_secrets.json

----------------------------------------------------------------------
STEP 5: Connect and Authorize
----------------------------------------------------------------------
Once you have copied 'client_secrets.json' to the project folder, run:
   python setup_youtube.py
This will open your browser once to authorize access and activate 100% automation!
======================================================================
""")

def main():
    print("\n" + "=" * 65)
    print("   INDIA HOURLY NEWS - YOUTUBE AUTOMATION MANAGER")
    print("=" * 65)

    if not SECRETS_FILE.exists():
        print(f"\n[!] 'client_secrets.json' not found in: {config.BASE_DIR}")
        print_setup_instructions()
        return

    print(f"\n[✓] Found credentials file: {SECRETS_FILE.name}")
    print("[*] Connecting to YouTube Data API...")

    service = get_youtube_service()
    if not service:
        print("[X] Failed to authenticate. Please verify your client_secrets.json file.")
        return

    print("[✓] Authentication successful! Token saved to 'token.json'.")
    print("[*] Retrieving linked YouTube channel information...\n")

    info = verify_channel()
    if info:
        print("-" * 55)
        print(f"  Channel Title:   {info['title']}")
        print(f"  Channel ID:      {info['id']}")
        if info.get('customUrl'):
            print(f"  Channel Handle:  {info['customUrl']}")
        print(f"  Subscribers:     {info['subscribers']}")
        print(f"  Total Videos:    {info['videoCount']}")
        print("-" * 55)
        print(f"\n[✓] CONNECTED: Videos will automatically upload to '{info['title']}'!")
        print(f"[*] Upload Visibility: {config.YOUTUBE_PRIVACY.upper()} (change in config.py)")
        print(f"[*] Schedule: Hourly automatic broadcast and upload active.")
    else:
        print("[!] Authenticated, but could not read channel profile.")

    # Check for existing generated videos to offer test upload
    existing_shorts = list(config.SHORTS_OUTPUT_DIR.glob("SHORTS_*.mp4"))
    if existing_shorts:
        latest_short = max(existing_shorts, key=lambda f: f.stat().st_mtime)
        print(f"\nFound existing generated video: {latest_short.name}")
        choice = input("\nWould you like to perform a test upload of this video now? (y/N): ").strip().lower()
        if choice in ("y", "yes"):
            test_meta = {
                "format": "shorts",
                "video_path": str(latest_short),
                "title": f"Top 10 India News (Test Upload) #Shorts",
                "description": "Automated test upload by India Hourly News pipeline.\n\n#Shorts #IndiaNews",
                "tags": ["Shorts", "India News", "Test Upload"]
            }
            upload_video(test_meta, privacy_status="unlisted")

if __name__ == "__main__":
    main()
