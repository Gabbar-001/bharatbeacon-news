import sys
import re
from pathlib import Path
from typing import Dict, List, Any, Tuple

# Ensure UTF-8 output on Windows
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

sys.path.append(str(Path(__file__).resolve().parent.parent))
from src.learning_memory import get_dimension_multiplier, save_hook_experiments

# Power trigger words for YouTube retention hooks
POWER_TRIGGER_WORDS = [
    "never", "warning", "secret", "forbidden", "nobody", "impossible", "illegal", "hidden",
    "destroyed", "shocking", "banned", "deadly", "truth", "mystery", "stop", "look closely"
]

def clean_subject(title: str) -> str:
    """Extracts the clean core entity or phenomenon from a headline."""
    cleaned = title.rstrip(".!? ")
    # Remove quotes
    cleaned = cleaned.replace('"', '').replace("'", "")
    # Remove source attribution like " - ScienceDaily" or " - LiveScience"
    cleaned = re.sub(r'\s*-\s*[A-Za-z0-9\s]+$', '', cleaned)
    # Remove leading question words
    cleaned = re.sub(r'^(Why|How|What|Could|Does|When|Where)\s+', '', cleaned, flags=re.IGNORECASE)
    
    words = cleaned.split()
    if len(words) > 7:
        words = words[:7]
    
    # Strip trailing conjunctions/prepositions
    trailing_stopwords = {"as", "a", "an", "the", "in", "of", "to", "for", "with", "from", "by", "after", "and", "or", "over"}
    while words and words[-1].lower() in trailing_stopwords:
        words.pop()
        
    return " ".join(words)

def generate_hooks_for_topic(topic: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Synthesizes 5 distinct psychological hook angles for the given topic,
    strictly embedding the story's actual core subject so voice and visual match 100%.
    """
    title = topic.get("title", "")
    category = topic.get("category", "SCIENCE").upper()
    core = clean_subject(title)

    hooks = []

    # 1. The Impossible Paradox (forces cognitive dissonance grounded in this specific topic)
    h1 = f"Scientists just revealed that {core} completely contradicts what experts believed!"
    hooks.append({"type": "paradox", "text": h1})

    # 2. Pattern Interrupt & Direct Challenge
    h2 = f"Stop scrolling. Look closely at what was just discovered about {core}!"
    hooks.append({"type": "challenge", "text": h2})

    # 3. Forbidden / Stunned Curiosity
    h3 = f"Researchers were stunned after uncovering the truth behind {core}!"
    hooks.append({"type": "forbidden_curiosity", "text": h3})

    # 4. The Provocative Question
    h4 = f"Did you know the incredible reality behind {core}?"
    hooks.append({"type": "high_stakes_question", "text": h4})

    # 5. Shocking Contrast / Breakthrough
    h5 = f"For years, {core} was completely misunderstood... until this new discovery!"
    hooks.append({"type": "shocking_contrast", "text": h5})

    return hooks

def score_hook(hook: Dict[str, Any]) -> float:
    """
    Scores an opening hook from 0 to 100 based on brevity, power words, and historical channel weights.
    """
    text = hook["text"]
    htype = hook["type"]
    words = text.split()
    w_count = len(words)

    # 1. Brevity Score (Max 40 pts)
    # 6 to 11 words is the viral sweet spot for Shorts
    if 6 <= w_count <= 11:
        b_score = 40.0
    elif w_count < 6:
        b_score = 30.0
    elif 12 <= w_count <= 14:
        b_score = 28.0
    else:
        b_score = 15.0

    # 2. Power Word Score (Max 30 pts)
    matched_power = sum(1 for pw in POWER_TRIGGER_WORDS if pw in text.lower())
    p_score = min(30.0, matched_power * 10.0 + (10.0 if "!" in text else 0.0))

    # 3. Channel Historical Learning Weight (Max 30 pts)
    # Derived from channel_learning_memory
    mult = get_dimension_multiplier(htype)
    l_score = min(30.0, 20.0 * mult)

    total = round(b_score + p_score + l_score, 1)
    return total

def select_champion_hook(topic: Dict[str, Any], excluded_types: set = None) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Generates 5 hooks, scores them, marks the champion, and saves them for A/B analytics tracking.
    Enforces cross-story diversity by avoiding hook types already used in the same video.
    """
    hooks = generate_hooks_for_topic(topic)
    for h in hooks:
        h["predicted_score"] = score_hook(h)
        h["is_champion"] = False

    # Sort descending
    hooks.sort(key=lambda x: x["predicted_score"], reverse=True)

    # Pick top scoring hook of an unused type if available to prevent structural repetition
    champion = None
    if excluded_types:
        for h in hooks:
            if h["type"] not in excluded_types:
                champion = h
                break

    if not champion:
        champion = hooks[0]

    champion["is_champion"] = True

    # Persist in DB if topic has an ID
    topic_id = topic.get("topic_id")
    if topic_id:
        save_hook_experiments(topic_id, hooks)

    return champion, hooks

if __name__ == "__main__":
    sample_topic = {
        "topic_id": 1,
        "title": "'Stupendously large' primordial black holes ruled out as dark matter candidate",
        "category": "SPACE"
    }

    print("[*] Generating 5 Psychological Hook Variations...")
    champ, all_hooks = select_champion_hook(sample_topic)

    print(f"\n[OK] Selected Champion Hook ({champ['predicted_score']} pts - {champ['type'].upper()}):")
    print(f'     "{champ["text"]}"\n')

    print("ALL 5 EXPERIMENTAL HOOKS (Saved for A/B analytics):")
    for idx, h in enumerate(all_hooks, 1):
        tag = " [CHAMPION]" if h["is_champion"] else ""
        print(f"  {idx}. [{h['predicted_score']:4.1f} pts] ({h['type']:20s}): {h['text']}{tag}")
