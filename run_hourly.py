import os
import sys
import json
import subprocess
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
from content_plan.day1_shorts_data import DAY1_SHORTS
from src.tech_animator import (
    render_code_card,
    render_shorts_frame,
    COLOR_PYTHON,
    COLOR_JAVA,
    COLOR_MONGO,
    COLOR_SQL
)
from src.tts_engine import generate_voiceover_sync
from src.youtube_publisher import upload_video

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

def execute_hourly_cycle():
    IST = timezone(timedelta(hours=5, minutes=30))
    start_time = datetime.now(IST)
    timestamp_str = start_time.strftime("%Y%m%d_%H%M")
    hour_display = start_time.strftime("%I:00 %p IST")
    date_display = start_time.strftime("%d %B %Y")
    hour_ist = start_time.hour

    logs_dir = config.OUTPUT_DIR / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_file = logs_dir / f"tech_broadcast_{timestamp_str}.log"
    sys.stdout = TeeLogger(log_file, sys.stdout)
    sys.stderr = TeeLogger(log_file, sys.stderr)

    print("\n" + "=" * 65)
    print(f"  [TECH MASTERCLASS ENGINE] 60-DAY BOOTCAMP BROADCAST")
    print(f"  Time: {hour_display} | {date_display} | Hour IST: {hour_ist}")
    print(f"  Log File: {log_file}")
    print("=" * 65)

    # 1. Load Playlist IDs
    pl_file = Path("playlists.json")
    playlist_map = {}
    if pl_file.exists():
        with open(pl_file, "r", encoding="utf-8") as f:
            playlist_map = json.load(f)

    # 2. Pick the Short for the current IST hour
    selected_short = None
    for s in DAY1_SHORTS:
        if s["hour_ist"] == hour_ist:
            selected_short = s
            break
    if not selected_short:
        selected_short = DAY1_SHORTS[hour_ist % len(DAY1_SHORTS)]

    track = selected_short["track"]
    pl_key = selected_short["playlist_key"]
    playlist_id = playlist_map.get(pl_key, {}).get("id")

    print(f"\n[1/3] Selected Short for {hour_display}:")
    print(f"      Track:    {track.upper()}")
    print(f"      Title:    {selected_short['title']}")
    print(f"      Playlist: {playlist_map.get(pl_key, {}).get('title')} ({playlist_id})")

    # 3. Generate Audio & Video
    temp_dir = config.TEMP_DIR / f"hourly_{hour_ist}"
    temp_dir.mkdir(parents=True, exist_ok=True)

    accent_map = {
        "python": COLOR_PYTHON,
        "java": COLOR_JAVA,
        "mongodb": COLOR_MONGO,
        "sql": COLOR_SQL
    }
    accent = accent_map.get(track, COLOR_PYTHON)

    print(f"\n[2/3] Generating Voiceover & 9:16 Video Frame...")
    audio_path = temp_dir / f"short_audio_{hour_ist}.mp3"
    dur = generate_voiceover_sync(
        selected_short["speech"],
        audio_path,
        is_shorts=True,
        voice="en-IN-NeerjaExpressiveNeural"
    )
    print(f"      Voiceover ready: {dur:.2f}s")

    code_card = render_code_card(
        selected_short["code"],
        language=track,
        width=920,
        height=380,
        filename=f"snippet_{track}.py",
        font_size=24
    )
    frame = render_shorts_frame(
        track_badge=selected_short["badge"],
        hook_text=selected_short["hook_text"],
        code_img=code_card,
        caption_text=selected_short["caption"],
        riddle_text=selected_short["riddle_text"],
        accent_color=accent
    )
    frame_path = temp_dir / f"short_frame_{hour_ist}.jpg"
    frame.save(frame_path, quality=95)

    shorts_dir = config.SHORTS_OUTPUT_DIR
    shorts_dir.mkdir(parents=True, exist_ok=True)
    out_mp4 = shorts_dir / f"SHORT_DAY01_H{hour_ist:02d}_{track.upper()}.mp4"

    cmd = [
        "ffmpeg", "-y",
        "-loop", "1",
        "-framerate", "30",
        "-i", str(frame_path),
        "-i", str(audio_path),
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-pix_fmt", "yuv420p",
        "-r", "30",
        "-c:a", "aac",
        "-ar", "44100",
        "-ac", "2",
        "-b:a", "192k",
        "-t", f"{dur:.3f}",
        "-movflags", "+faststart",
        str(out_mp4)
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    print(f"      Short Video Encoded: {out_mp4.name} ({dur:.1f}s)")

    # 4. Upload to YouTube as PUBLIC
    print(f"\n[3/3] Uploading Short to YouTube & Adding to Playlist...")
    description = f"""{selected_short['title']}

Day 1 of our 60-Day Tech Masterclass Bootcamp.
Master full-stack and database engineering with daily pro-tips, interview gotchas, and deep lectures!

📚 Playlist: {playlist_map.get(pl_key, {}).get('title')}
👉 Full Masterclasses drop daily across Python, Java, MongoDB, and SQL.
Subscribe now to join the 60-day challenge!

#Shorts #Coding #Programming #{track.capitalize()} #SoftwareEngineering #TechBootcamp #FAANG
"""
    metadata = {
        "title": selected_short["title"][:100],
        "description": description,
        "video_path": str(out_mp4),
        "tags": [track, "Coding", "Programming", "LearnToCode", "Shorts", "Tech", "SoftwareEngineering"],
        "playlist_id": playlist_id,
        "publish_at": None  # Instant Public on its scheduled hour!
    }

    video_id = upload_video(metadata, privacy_status="public")
    elapsed = (datetime.now(IST) - start_time).total_seconds()

    print("\n" + "=" * 65)
    if video_id:
        print(f"  HOURLY BROADCAST COMPLETED IN {elapsed:.1f}s!")
        print(f"  Video ID:    {video_id}")
        print(f"  YouTube URL: https://youtube.com/shorts/{video_id}")
        print(f"  Playlist:    {playlist_id}")
    else:
        print(f"  [NOTICE] Short rendered and saved locally, but YouTube upload failed (or daily channel limit reached).")
        print(f"  Local file: {out_mp4}")
    print("=" * 65)

if __name__ == "__main__":
    execute_hourly_cycle()
