import sys
import json
import re
from pathlib import Path
from typing import Dict, List, Any

# Ensure UTF-8 output on Windows
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

sys.path.append(str(Path(__file__).resolve().parent.parent))
from src.learning_memory import save_storyboard

def construct_storyboard_script(topic: Dict[str, Any], champion_hook: Dict[str, Any], is_shorts: bool = True) -> List[Dict[str, Any]]:
    """
    Transforms the topic into a 5-beat retention-engineered storyboard:
    [0-2s] Hook -> [2-7s] Stakes/Mystery -> [7-15s] Core Discovery -> [15-25s] Twist -> [Loop/CTA]
    """
    title = topic.get("title", "")
    summary = topic.get("summary", "")
    category = topic.get("category", "SCIENCE").upper()
    hook_text = champion_hook["text"]

    # Clean summary into punchy sentences
    clean_s = re.sub(r'https?://\S+', '', summary)
    clean_s = re.sub(r'\s*-\s*[A-Za-z0-9\s]+$', '', clean_s)
    sentences = [s.strip() for s in re.split(r'[.!?]+', clean_s) if len(s.strip()) > 15]

    st_fact_1 = sentences[0] if len(sentences) > 0 else title
    st_fact_2 = sentences[1] if len(sentences) > 1 else "Researchers analyzing the data were astonished by the implications."

    blueprint = []

    clean_t = title.rstrip(".!? ").replace('"', '').replace("'", "")
    clean_t = re.sub(r'\s*-\s*[A-Za-z0-9\s]+$', '', clean_t)

    # BEAT 1: [0s - 2s] THE HOOK
    blueprint.append({
        "beat": "THE_HOOK",
        "time_range": "0.0s - 2.5s",
        "target_seconds": 2.5,
        "narration": hook_text,
        "screen_text": "WAIT FOR THIS...",
        "visual_prompt": f"Dramatic cinematic scene of {clean_t[:40]}, high contrast rim lighting, 8k hyper-detailed, suspenseful atmosphere",
        "camera_movement": "fast_zoom_in",
        "sound_fx": "sub_bass_drop",
        "color_tone": "dark_teal_orange"
    })

    # BEAT 2: [2s - 7s] THE CURIOSITY GAP / STAKES
    beat2_narr = f"Detailed reports confirm that {clean_t}."

    blueprint.append({
        "beat": "CURIOSITY_GAP",
        "time_range": "2.5s - 7.5s",
        "target_seconds": 5.0,
        "narration": beat2_narr,
        "screen_text": "THE REPORT",
        "visual_prompt": f"Close-up investigation shot of {clean_t[:40]}, detailed measurement instruments, glowing analytical HUD, intense focus",
        "camera_movement": "slow_pan_right",
        "sound_fx": "tension_riser",
        "color_tone": "cool_cyan"
    })

    # BEAT 3: [7s - 15s] THE CORE DISCOVERY
    blueprint.append({
        "beat": "CORE_DISCOVERY",
        "time_range": "7.5s - 15.0s",
        "target_seconds": 7.5,
        "narration": f"Here is what happened: {st_fact_1}.",
        "screen_text": "THE EVIDENCE",
        "visual_prompt": f"Epic wide-angle visual showing {clean_t[:40]}, photorealistic, sharp focus, vibrant volumetric lighting",
        "camera_movement": "dynamic_orbit",
        "sound_fx": "revelation_whoosh",
        "color_tone": "amber_gold"
    })

    # BEAT 4: [15s - 23s] THE DEEPER TWIST
    if st_fact_2 and st_fact_2 != st_fact_1 and len(st_fact_2) > 20:
        beat4_narr = f"Adding to the intrigue, {st_fact_2}."
    else:
        beat4_narr = f"Researchers and observers are tracking the broader impact of this finding closely."

    blueprint.append({
        "beat": "UNEXPECTED_TWIST",
        "time_range": "15.0s - 23.0s",
        "target_seconds": 8.0,
        "narration": beat4_narr,
        "screen_text": "KEY INSIGHT",
        "visual_prompt": f"Macro cinematic revelation angle of {clean_t[:40]}, sudden perspective shift, extreme depth of field, dramatic shadows",
        "camera_movement": "crash_zoom",
        "sound_fx": "echoing_pulse",
        "color_tone": "crimson_contrast"
    })

    # BEAT 5: [23s - 28s] THE SEAMLESS LOOP / CTA
    loop_narr = f"And that is why developments around {clean_t[:45]} continue to captivate observers worldwide."
    blueprint.append({
        "beat": "SEAMLESS_LOOP",
        "time_range": "23.0s - 28.0s",
        "target_seconds": 5.0,
        "narration": loop_narr,
        "screen_text": "STAY INFORMED",
        "visual_prompt": f"Stylized end card with glowing channel badge and subscribe indicator, ultra-clean aesthetic",
        "camera_movement": "slow_zoom_out",
        "sound_fx": "outro_hit",
        "color_tone": "slate_premium"
    })

    return blueprint

def plan_and_save_storyboard(topic: Dict[str, Any], champion_hook: Dict[str, Any], is_shorts: bool = True) -> Dict[str, Any]:
    """
    Builds the storyboard, extracts the full narration script and visual cues,
    and saves the production plan into the database.
    """
    blueprint = construct_storyboard_script(topic, champion_hook, is_shorts=is_shorts)

    total_duration = sum(b["target_seconds"] for b in blueprint)
    full_script = " ".join(b["narration"] for b in blueprint)

    visual_cues = [
        {
            "beat": b["beat"],
            "time_range": b["time_range"],
            "prompt": b["visual_prompt"],
            "camera": b["camera_movement"],
            "screen_text": b["screen_text"],
            "color": b["color_tone"]
        }
        for b in blueprint
    ]

    topic_id = topic.get("topic_id")
    hook_id = champion_hook.get("id", 1)

    sb_id = None
    if topic_id:
        sb_id = save_storyboard(
            topic_id=topic_id,
            champion_hook_id=hook_id,
            script=full_script,
            blueprint=blueprint,
            visual_cues=visual_cues,
            duration=total_duration
        )

    return {
        "storyboard_id": sb_id,
        "topic_id": topic_id,
        "target_duration": total_duration,
        "full_script": full_script,
        "blueprint": blueprint,
        "visual_cues": visual_cues
    }

if __name__ == "__main__":
    sample_topic = {
        "topic_id": 1,
        "title": "NASA's destroyed Swift Observatory took one of the best-ever photos before burning up",
        "summary": "The spacecraft gathered incredible ultraviolet observations across two decades. Its final data burst revealed previously invisible structures in nearby star clusters.",
        "category": "SPACE"
    }

    sample_hook = {
        "id": 1,
        "type": "paradox",
        "text": "Before it was completely destroyed, this space telescope captured something impossible!"
    }

    print("[*] Generating Retention Storyboard & Visual Direction Plan...")
    plan = plan_and_save_storyboard(sample_topic, sample_hook, is_shorts=True)

    print(f"\n[OK] Storyboard Created (Duration: {plan['target_duration']}s):")
    for b in plan["blueprint"]:
        print(f"  [{b['time_range']:12s}] {b['beat']:18s} | {b['narration'][:60]}...")
        print(f"      [Visual Cue]: {b['visual_prompt'][:70]}... (Camera: {b['camera_movement']})")
