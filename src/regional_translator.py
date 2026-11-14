import urllib.request
import urllib.parse
import json
import asyncio
from pathlib import Path
from typing import Dict, List, Optional
import edge_tts

# Regional Indian Voice Mapping (Microsoft Neural)
REGIONAL_VOICES = {
    "te": "te-IN-ShrutiNeural",       # Telugu (Female, natural, clear)
    "kn": "kn-IN-SapnaNeural",        # Kannada (Female, natural, clear)
    "hi": "hi-IN-SwaraNeural",        # Hindi (Female, news cadence)
    "en": "en-IN-NeerjaExpressiveNeural" # English India (Expressive)
}

def translate_text(text: str, target_lang: str) -> str:
    """
    Translates text to target language (e.g. 'te' for Telugu, 'kn' for Kannada, 'hi' for Hindi).
    Uses high-speed Google Translate endpoint with no API keys required.
    """
    if not text or target_lang == "en":
        return text
    try:
        url = "https://translate.googleapis.com/translate_a/single?client=gtx&sl=en&tl=" + target_lang + "&dt=t&q=" + urllib.parse.quote(text)
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        res = urllib.request.urlopen(req, timeout=10)
        data = json.loads(res.read())
        translated_segments = [seg[0] for seg in data[0] if seg and seg[0]]
        return "".join(translated_segments)
    except Exception as e:
        print(f"[TRANSLATE ERROR] {target_lang}: {e}")
        return text

def generate_youtube_localizations(title_en: str, description_en: str) -> Dict[str, Dict[str, str]]:
    """
    Generates the official YouTube localizations dictionary for Telugu, Kannada, and Hindi.
    YouTube uses this to automatically display the video title and description in the viewer's native language.
    """
    localizations = {}

    for lang in ["te", "kn", "hi"]:
        try:
            t_title = translate_text(title_en[:95], lang)[:100]
            # Translate first 400 chars of description
            desc_intro = description_en.split("\n\n")[0] if "\n\n" in description_en else description_en[:400]
            t_desc_intro = translate_text(desc_intro, lang)
            t_desc = f"{t_desc_intro}\n\n{description_en}"[:5000]

            localizations[lang] = {
                "title": t_title,
                "description": t_desc
            }
        except Exception as e:
            print(f"[LOCALIZATION ERROR] Failed for {lang}: {e}")

    return localizations

async def _synth_audio(text: str, voice: str, out_path: Path):
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(str(out_path))

def generate_regional_audio_tracks(news_script: str, base_out_dir: Path, timestamp_str: str) -> Dict[str, Path]:
    """
    Generates synchronized regional voiceover audio tracks for YouTube Multi-Language Audio:
    - Telugu (.mp3)
    - Kannada (.mp3)
    - Hindi (.mp3)
    """
    tracks_dir = base_out_dir / "audio_tracks"
    tracks_dir.mkdir(parents=True, exist_ok=True)
    results = {}

    for lang, voice in [("te", "te-IN-ShrutiNeural"), ("kn", "kn-IN-SapnaNeural"), ("hi", "hi-IN-SwaraNeural")]:
        try:
            translated_script = translate_text(news_script, lang)
            out_file = tracks_dir / f"AUDIO_{lang.upper()}_{timestamp_str}.mp3"
            asyncio.run(_synth_audio(translated_script, voice, out_file))
            if out_file.exists():
                results[lang] = out_file
                print(f"[REGIONAL AUDIO] Generated {lang.upper()} audio track ({voice}): {out_file.name}")
        except Exception as e:
            print(f"[REGIONAL AUDIO ERROR] Failed {lang}: {e}")

    return results

if __name__ == "__main__":
    sample = "India launches next-generation green energy initiative with massive solar capacity."
    print("Testing translation:")
    print("Telugu:", translate_text(sample, "te"))
    print("Kannada:", translate_text(sample, "kn"))
    print("Hindi:", translate_text(sample, "hi"))
    locs = generate_youtube_localizations("India Breaking News", sample)
    print("Localizations keys:", list(locs.keys()))
