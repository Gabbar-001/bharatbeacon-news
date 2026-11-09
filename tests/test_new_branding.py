import os
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from src.tts_engine import generate_voiceover_sync
from src.video_composer import render_segment
from src.visual_generator import generate_shorts_slide, generate_longform_slide
import config

test_dir = config.TEMP_DIR / "test_branding"
test_dir.mkdir(parents=True, exist_ok=True)

# 1. Shorts Test
sh_story = {
    "title": "BHARATBEACON LIVE: INDIA'S WINDOW TO THE WORLD",
    "category": "SPECIAL",
    "summary": "",
    "local_image": None
}
sh_slide = test_dir / "sh_test.png"
generate_shorts_slide(sh_story, 1, 10, sh_slide)

sh_audio = test_dir / "sh_test.mp3"
sh_ass = test_dir / "sh_test.ass"
sh_text = "Welcome to BharatBeacon — India's Window to the World! Here are your top 10 headlines this hour."
dur_sh = generate_voiceover_sync(sh_text, sh_audio, output_ass=sh_ass, is_shorts=True)

sh_mp4 = test_dir / "sh_test.mp4"
render_segment(sh_slide, sh_audio, sh_mp4, dur_sh, ass_path=sh_ass)
print(f"Shorts test rendered: {dur_sh:.1f}s")

# 2. Longform Test
lf_story = {
    "title": "BHARATBEACON HOURLY BULLETIN",
    "category": "SPECIAL",
    "summary": "Live hourly update covering the biggest developments across India and the globe.",
    "local_image": None
}
lf_slide = test_dir / "lf_test.png"
generate_longform_slide(lf_story, 1, 10, lf_slide)

lf_audio = test_dir / "lf_test.mp3"
lf_ass = test_dir / "lf_test.ass"
lf_text = "Namaste and welcome to BharatBeacon — India's Window to the World. Bringing you the top ten major developments across the nation and the world this hour."
dur_lf = generate_voiceover_sync(lf_text, lf_audio, output_ass=lf_ass, is_shorts=False)

lf_mp4 = test_dir / "lf_test.mp4"
render_segment(lf_slide, lf_audio, lf_mp4, dur_lf, ass_path=lf_ass)
print(f"Longform test rendered: {dur_lf:.1f}s")
