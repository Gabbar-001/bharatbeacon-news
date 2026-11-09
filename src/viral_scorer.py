import sys
import re
from pathlib import Path
from typing import Dict, Any, Tuple

# Ensure UTF-8 output on Windows
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

sys.path.append(str(Path(__file__).resolve().parent.parent))
from src.learning_memory import get_dimension_multiplier, save_topic

# High-curiosity trigger terms
CURIOSITY_KEYWORDS = {
    "high": ["why", "how", "secret", "mystery", "hidden", "unexplained", "baffled", "impossible",
             "bizarre", "strange", "never seen", "warning", "forbidden", "dark truth", "real reason",
             "what happens", "can you", "did you know", "turns out", "rare"],
    "medium": ["discovered", "ancient", "shocking", "reveals", "first time", "unusual", "deep",
               "tracks", "found", "study", "could", "search", "looking for", "theory", "predicting"]
}

# Concrete visual trigger terms
VISUAL_KEYWORDS = [
    "giant", "tiny", "deep", "space", "planet", "galaxy", "tomb", "gold", "ocean", "artifact",
    "skeleton", "animal", "creature", "cat", "dog", "brain", "blood", "fire", "ice", "water",
    "camera", "photo", "burial", "weapon", "poison", "telescope", "black hole", "cave", "pyramid",
    "moon", "mars", "earth", "sun", "stars", "stellar", "light", "skull", "mirror", "flying"
]

# Negative saturation triggers (routine, boring corporate/political bureau news)
SATURATION_PENALTIES = [
    "quarterly profit", "q2 results", "sensex closes", "nifty rises", "press briefing",
    "court adjourned", "inaugurated", "signs mou", "bureau meeting", "shares gain", "price targets"
]

def evaluate_curiosity_gap(title: str, summary: str) -> float:
    score = 12.0  # Calibrated base score
    text = f"{title} {summary}".lower()

    if "?" in title:
        score += 5.0
    for kw in CURIOSITY_KEYWORDS["high"]:
        if kw in text:
            score += 4.0
            break
    for kw in CURIOSITY_KEYWORDS["medium"]:
        if kw in text:
            score += 2.5
            break

    # Paradox / contrast indicators
    if any(p in text for p in ["but", "despite", "even though", "until now", "turned out", "actually", "without"]):
        score += 3.0

    return min(25.0, round(score, 1))

def evaluate_surprise_factor(title: str, summary: str) -> float:
    score = 9.0
    text = f"{title} {summary}".lower()

    # Extreme words or cognitive dissonance
    if any(w in text for w in ["poisoned", "destroyed", "deadliest", "thousands of years", "million years", "accidentally", "bizarre", "stupendously", "hate", "almost died"]):
        score += 5.0
    if re.search(r'\b\d{2,}\s*(years|centuries|feet|miles|billion|million|times|events)\b', text):
        score += 4.0
    if any(w in text for w in ["scientists baffled", "thought to be extinct", "hiding in plain sight", "could destroy", "older universe", "primordial"]):
        score += 3.0

    return min(20.0, round(score, 1))

def evaluate_visual_potential(title: str, summary: str) -> float:
    score = 8.0
    text = f"{title} {summary}".lower()

    matched_visuals = sum(1 for kw in VISUAL_KEYWORDS if kw in text)
    score += min(11.0, matched_visuals * 3.0)

    if any(w in text for w in ["photo", "image", "recorded", "captured on camera", "satellite", "remains", "magnified"]):
        score += 2.5

    return min(20.0, round(score, 1))

def evaluate_resonance(category: str, title: str) -> float:
    # Categories with universal human intrigue score higher
    cat_base = {
        "MYSTERY": 14.0,
        "SPACE": 13.5,
        "SCIENCE": 12.5,
        "TECH": 11.0,
        "SPORTS": 10.5,
        "NATIONAL": 9.0,
        "BUSINESS": 7.0,
        "TRENDING": 12.0
    }
    score = cat_base.get(category.upper(), 9.0)
    return min(15.0, score)

def evaluate_saturation(title: str) -> float:
    text = title.lower()
    for sat in SATURATION_PENALTIES:
        if sat in text:
            return 2.0  # Massive penalty for routine corporate/court updates
    return 9.5

def evaluate_channel_fit(category: str) -> float:
    multiplier = get_dimension_multiplier(category)
    base = 7.0
    return min(10.0, round(base * multiplier, 1))

def score_topic(topic: Dict[str, Any], threshold: float = 70.0) -> Dict[str, Any]:
    """
    Evaluates candidate topic across all 6 dimensions.
    Returns enriched topic dictionary with scores, breakdown, and pass/fail status.
    """
    title = topic.get("title", "")
    summary = topic.get("summary", "")
    category = topic.get("category", "GENERAL")

    c_score = evaluate_curiosity_gap(title, summary)
    s_score = evaluate_surprise_factor(title, summary)
    v_score = evaluate_visual_potential(title, summary)
    r_score = evaluate_resonance(category, title)
    sat_score = evaluate_saturation(title)
    fit_score = evaluate_channel_fit(category)

    total = round(c_score + s_score + v_score + r_score + sat_score + fit_score, 1)

    is_approved = total >= threshold

    rejection_reasons = []
    if c_score < 14:
        rejection_reasons.append("Low curiosity gap")
    if v_score < 11:
        rejection_reasons.append("Weak visual storytelling")
    if sat_score < 5:
        rejection_reasons.append("Oversaturated routine news")
    if total < threshold:
        rejection_reasons.append(f"Total score ({total}) below {threshold} cutoff")

    enriched = dict(topic)
    enriched.update({
        "curiosity_score": c_score,
        "surprise_score": s_score,
        "visual_score": v_score,
        "resonance_score": r_score,
        "saturation_score": sat_score,
        "channel_fit_score": fit_score,
        "total_score": total,
        "status": "approved" if is_approved else "rejected",
        "rejection_reason": "; ".join(rejection_reasons) if not is_approved else ""
    })

    return enriched

def score_and_filter_topics(candidates: list, threshold: float = 70.0) -> Tuple[list, list]:
    """Scores all candidate topics and partitions into approved and rejected pools."""
    approved = []
    rejected = []

    for c in candidates:
        scored = score_topic(c, threshold=threshold)
        # Record into database topic pool
        topic_id = save_topic(scored)
        scored["topic_id"] = topic_id

        if scored["status"] == "approved":
            approved.append(scored)
        else:
            rejected.append(scored)

    # Sort approved by highest total score first
    approved.sort(key=lambda x: x["total_score"], reverse=True)
    return approved, rejected

if __name__ == "__main__":
    from src.topic_discovery import discover_candidate_topics

    print("[*] Testing AI 6D Viral Scoring Gate...")
    candidates = discover_candidate_topics(max_candidates=15)
    approved, rejected = score_and_filter_topics(candidates, threshold=70.0)

    print(f"\n[OK] Scored {len(candidates)} topics:")
    print(f"     Approved for production: {len(approved)}")
    print(f"     Rejected / Filtered:    {len(rejected)}\n")

    print("TOP APPROVED CANDIDATES:")
    for i, a in enumerate(approved[:5], 1):
        print(f"  {i}. [{a['total_score']} pts] [{a['category']}] {a['title'][:60]}...")
        print(f"     (Curiosity: {a['curiosity_score']}/25, Visual: {a['visual_score']}/20, Surprise: {a['surprise_score']}/20)")

    if rejected:
        print("\nSAMPLE FILTERED TOPIC:")
        rej = rejected[0]
        print(f"  - [{rej['total_score']} pts] {rej['title'][:60]}... Reason: {rej['rejection_reason']}")
