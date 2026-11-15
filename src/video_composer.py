import os
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import List, Dict

sys.path.append(str(Path(__file__).resolve().parent.parent))
import config
from src.visual_generator import (
    generate_longform_slide,
    generate_shorts_slide,
    generate_transition_slide
)
from src.tts_engine import (
    generate_voiceover_sync,
    format_longform_script,
    format_shorts_script,
    get_audio_duration
)

SWOOSH_AUDIO = config.MUSIC_DIR / "swoosh.mp3"

def ensure_swoosh_audio():
    if not SWOOSH_AUDIO.exists():
        try:
            SWOOSH_AUDIO.parent.mkdir(parents=True, exist_ok=True)
            cmd = [
                "ffmpeg", "-y",
                "-f", "lavfi",
                "-i", "sine=f=350:d=0.9,asplit[a][b];[a]lowpass=f=600[a1];[b]flanger[b1];[a1][b1]amix,afade=t=in:ss=0:d=0.15,afade=t=out:st=0.6:d=0.3,volume=0.5",
                "-ar", "44100",
                "-ac", "2",
                "-c:a", "libmp3lame",
                str(SWOOSH_AUDIO)
            ]
            subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        except Exception:
            pass

ensure_swoosh_audio()

def format_timestamp(seconds: float) -> str:
    m = int(seconds // 60)
    s = int(seconds % 60)
    return f"{m:02d}:{s:02d}"

def render_segment(
    img_path: Path,
    audio_path: Path,
    output_mp4: Path,
    duration: float,
    ass_path: Path = None
) -> bool:
    output_mp4.parent.mkdir(parents=True, exist_ok=True)
    
    vf_filters = []
    
    if ass_path and ass_path.exists():
        escaped_ass = str(ass_path.resolve()).replace("\\", "/").replace(":", "\\:")
        vf_filters.append(f"ass='{escaped_ass}'")
    
    vf_filters.append("setpts=PTS-STARTPTS")

    cmd = [
        "ffmpeg", "-y",
        "-loop", "1",
        "-framerate", "30",
        "-i", str(img_path),
        "-i", str(audio_path),
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-pix_fmt", "yuv420p",
        "-r", "30",
        "-g", "30",
        "-keyint_min", "30",
        "-c:a", "aac",
        "-ar", "44100",
        "-ac", "2",
        "-b:a", "192k",
        "-af", "asetpts=PTS-STARTPTS",
        "-t", f"{duration:.3f}",
        "-avoid_negative_ts", "make_zero",
        "-fflags", "+genpts",
    ]

    if vf_filters:
        cmd.extend(["-vf", ",".join(vf_filters)])

    cmd.append(str(output_mp4))

    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if res.returncode != 0:
        print(f"Segment render failed for {output_mp4.name}: {res.stderr[-300:]}")
        return False
    return True

def concatenate_segments(segment_files: List[Path], final_output: Path) -> bool:
    final_output.parent.mkdir(parents=True, exist_ok=True)
    concat_list_file = config.TEMP_DIR / f"concat_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.txt"
    with open(concat_list_file, "w", encoding="utf-8") as f:
        for seg in segment_files:
            escaped = str(seg.resolve()).replace("\\", "/")
            f.write(f"file '{escaped}'\n")

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_list_file),
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "192k",
        "-ar", "44100",
        "-ac", "2",
        "-avoid_negative_ts", "make_zero",
        "-fflags", "+genpts",
        "-movflags", "+faststart",
        str(final_output)
    ]

    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if concat_list_file.exists():
        concat_list_file.unlink()

    if res.returncode != 0:
        print(f"Concat failed: {res.stderr[-300:]}")
        return False
    return True

def build_longform_video(stories: List[Dict], timestamp_str: str) -> Dict:
    print(f"--- Building 16:9 Long-Form Bulletin ({len(stories)} stories) ---")
    segments_script = format_longform_script(stories)
    segment_mp4s = []
    chapter_timestamps = []
    current_time = 0.0

    total_stories = len(stories)

    for i, seg in enumerate(segments_script):
        seg_id = f"lf_{timestamp_str}_{i:02d}"
        slide_png = config.TEMP_DIR / f"{seg_id}.png"
        audio_mp3 = config.TEMP_DIR / f"{seg_id}.mp3"
        ass_file = config.TEMP_DIR / f"{seg_id}.ass"
        seg_mp4 = config.TEMP_DIR / f"{seg_id}.mp4"

        # 1. Slide Graphic
        if seg["type"] == "intro":
            intro_story = {
                "title": "TOP 10 DEVELOPMENTS ACROSS INDIA THIS HOUR",
                "category": "BULLETIN",
                "summary": "Live hourly update covering the biggest stories in National politics, Business, Sports, and Tech.",
                "local_image": None
            }
            generate_longform_slide(intro_story, 0, total_stories, slide_png)
            chapter_timestamps.append((format_timestamp(current_time), "Headlines Overview"))
        elif seg["type"] == "outro":
            outro_story = {
                "title": "STAY INFORMED • NEXT UPDATE IN 60 MINUTES",
                "category": "UPDATE",
                "summary": "Subscribe to BharatBeacon — India's Window to the World for real-time coverage and breaking hourly broadcasts.",
                "local_image": None
            }
            generate_longform_slide(outro_story, total_stories, total_stories, slide_png)
            chapter_timestamps.append((format_timestamp(current_time), "Conclusion & Wrap-Up"))
        else:
            # Play transition slide before switching to the next story (Story 2 onwards)
            if seg["index"] > 1:
                trans_png = config.TEMP_DIR / f"lf_trans_{timestamp_str}_{i:02d}.png"
                trans_mp4 = config.TEMP_DIR / f"lf_trans_{timestamp_str}_{i:02d}.mp4"
                generate_transition_slide(seg["story"], seg["index"], total_stories, trans_png, is_shorts=False)
                if SWOOSH_AUDIO.exists():
                    t_dur = 0.9
                    if render_segment(trans_png, SWOOSH_AUDIO, trans_mp4, duration=t_dur):
                        segment_mp4s.append(trans_mp4)
                        current_time += t_dur

            generate_longform_slide(seg["story"], seg["index"], total_stories, slide_png)
            chapter_timestamps.append((format_timestamp(current_time), f"Story {seg['index']}: {seg['display_title'][:40]}..."))

        # 2. Voiceover Synthesis & Styled Closed Captions
        dur = generate_voiceover_sync(seg["text"], audio_mp3, output_ass=ass_file, is_shorts=False)

        # 3. Render Segment
        success = render_segment(slide_png, audio_mp3, seg_mp4, dur, ass_path=ass_file)
        if success:
            segment_mp4s.append(seg_mp4)
            current_time += dur

    final_mp4 = config.LONGFORM_OUTPUT_DIR / f"INDIA_NEWS_{timestamp_str}.mp4"
    concatenate_segments(segment_mp4s, final_mp4)
    print(f"Long-form video rendered: {final_mp4} (Duration: {format_timestamp(current_time)})")

    IST = timezone(timedelta(hours=5, minutes=30))
    now_ist = datetime.now(IST)
    before_dt = now_ist - timedelta(hours=1)
    before_label = before_dt.strftime("%I %p").lstrip("0")
    curr_label = now_ist.strftime("%I %p IST").lstrip("0")
    hour_label = f"{before_label} - {curr_label}"
    date_label = now_ist.strftime("%d %b %Y")
    
    title = f"{config.CHANNEL_NAME} | Top News ({hour_label}) | {config.CHANNEL_TAGLINE}"
    
    desc_lines = [
        f"🔴 {config.CHANNEL_NAME} — {config.CHANNEL_TAGLINE}",
        f"Top Major News Developments Across India and the World for {hour_label}, {date_label}.",
        "Fast, factual, and verified hourly bulletins.\n",
        "TIMESTAMPS:"
    ]
    for ts, ch_name in chapter_timestamps:
        desc_lines.append(f"{ts} - {ch_name}")
    
    desc_lines.extend([
        f"\n#BharatBeacon #IndiaNews #BreakingNews #Top10News #DailyNews #NewsUpdate #CurrentAffairs",
        f"\nSubscribe to {config.CHANNEL_NAME} — {config.CHANNEL_TAGLINE} for hourly news summaries."
    ])

    metadata = {
        "format": "longform",
        "video_path": str(final_mp4),
        "duration_seconds": current_time,
        "title": title,
        "description": "\n".join(desc_lines),
        "tags": ["BharatBeacon", "India News", "Top 10 News", "Breaking News India", "Hourly News", "Current Affairs", "World News", "Science", "Tech"]
    }

    return metadata

def build_shorts_video(stories: List[Dict], timestamp_str: str) -> Dict:
    print(f"--- Building 9:16 YouTube Short ({len(stories)} stories) ---")
    segments_script = format_shorts_script(stories)
    segment_mp4s = []
    current_time = 0.0
    total_stories = len(stories)

    for i, seg in enumerate(segments_script):
        seg_id = f"sh_{timestamp_str}_{i:02d}"
        slide_png = config.TEMP_DIR / f"{seg_id}.png"
        audio_mp3 = config.TEMP_DIR / f"{seg_id}.mp3"
        ass_file = config.TEMP_DIR / f"{seg_id}.ass"
        seg_mp4 = config.TEMP_DIR / f"{seg_id}.mp4"

        # 1. Slide Graphic
        if seg["type"] == "intro":
            intro_story = {
                "title": "TOP 10 HEADLINES IN 60 SECONDS",
                "category": "HOURLY",
                "summary": "",
                "local_image": None
            }
            generate_shorts_slide(intro_story, 0, total_stories, slide_png)
        elif seg["type"] == "outro":
            outro_story = {
                "title": "SUBSCRIBE FOR HOURLY UPDATES",
                "category": "SUBSCRIBE",
                "summary": "",
                "local_image": None
            }
            generate_shorts_slide(outro_story, total_stories, total_stories, slide_png)
        else:
            # Play transition slide before switching to the next story (Story 2 onwards)
            if seg["index"] > 1:
                trans_png = config.TEMP_DIR / f"sh_trans_{timestamp_str}_{i:02d}.png"
                trans_mp4 = config.TEMP_DIR / f"sh_trans_{timestamp_str}_{i:02d}.mp4"
                generate_transition_slide(seg["story"], seg["index"], total_stories, trans_png, is_shorts=True)
                if SWOOSH_AUDIO.exists():
                    t_dur = 0.6
                    if render_segment(trans_png, SWOOSH_AUDIO, trans_mp4, duration=t_dur):
                        segment_mp4s.append(trans_mp4)
                        current_time += t_dur

            generate_shorts_slide(seg["story"], seg["index"], total_stories, slide_png)

        # 2. Voiceover Synthesis & Dynamic Captions
        dur = generate_voiceover_sync(seg["text"], audio_mp3, output_ass=ass_file, is_shorts=True)

        # 3. Render Segment (With burned high-impact subtitles)
        success = render_segment(slide_png, audio_mp3, seg_mp4, dur, ass_path=ass_file)
        if success:
            segment_mp4s.append(seg_mp4)
            current_time += dur

    final_mp4 = config.SHORTS_OUTPUT_DIR / f"SHORTS_{timestamp_str}.mp4"
    concatenate_segments(segment_mp4s, final_mp4)
    print(f"Shorts video rendered: {final_mp4} (Duration: {current_time:.1f}s)")

    IST = timezone(timedelta(hours=5, minutes=30))
    now_ist = datetime.now(IST)
    before_dt = now_ist - timedelta(hours=1)
    before_label = before_dt.strftime("%I %p").lstrip("0")
    curr_label = now_ist.strftime("%I %p").lstrip("0")
    hour_label = f"{before_label} - {curr_label}"
    date_label = now_ist.strftime("%d %b")

    title = f"{config.CHANNEL_NAME} Top News in 60s ({hour_label}) | {config.CHANNEL_TAGLINE} #Shorts"
    description = (
        f"{config.CHANNEL_NAME} — {config.CHANNEL_TAGLINE}\n"
        f"Top breaking news headlines for {hour_label} IST ({date_label}).\n\n"
        "#Shorts #BharatBeacon #IndiaNews #BreakingNews #Top10 #DailyNews #ViralNews #India"
    )

    metadata = {
        "format": "shorts",
        "video_path": str(final_mp4),
        "duration_seconds": current_time,
        "title": title,
        "description": description,
        "tags": ["Shorts", "BharatBeacon", "India News", "Top 10 in 60 Seconds", "Breaking News", "News Shorts"]
    }

    return metadata

def clean_temp_files():
    """Thoroughly cleans temporary files, intermediate audio tracks, and segments to keep disk space lean"""
    import shutil
    # 1. Clean TEMP_DIR contents
    if config.TEMP_DIR.exists():
        for item in config.TEMP_DIR.iterdir():
            try:
                if item.is_file():
                    item.unlink(missing_ok=True)
                elif item.is_dir():
                    shutil.rmtree(item, ignore_errors=True)
            except Exception:
                pass

    # 2. Clean temporary regional audio tracks
    audio_dir = config.OUTPUT_DIR / "audio_tracks"
    if audio_dir.exists():
        for af in audio_dir.glob("*.*"):
            try:
                af.unlink(missing_ok=True)
            except Exception:
                pass

if __name__ == "__main__":
    from src.news_fetcher import fetch_top_news
    test_stories = fetch_top_news(limit=3, deduplicate=False)
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    meta_sh = build_shorts_video(test_stories, ts)
    print("New Shorts metadata:", meta_sh["title"])
