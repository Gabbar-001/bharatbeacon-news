import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

# Ensure UTF-8 output on Windows
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

sys.path.append(str(Path(__file__).resolve().parent.parent))
import config
from src.learning_memory import init_learning_tables, get_dimension_multiplier
from src.topic_discovery import discover_candidate_topics
from src.viral_scorer import score_and_filter_topics
from src.hook_generator import select_champion_hook
from src.storyboard_planner import plan_and_save_storyboard
from src.preflight_verifier import run_preflight_verification

def execute_pre_generation_pipeline(
    target_count: int = 10,
    min_score: float = 70.0,
    is_shorts: bool = True
) -> List[Dict[str, Any]]:
    """
    Executes the complete AI Pre-Generation Decision Pipeline:
    1. Trend & Curiosity Ingestion
    2. 6-Dimensional Viral Scoring Gate
    3. Multi-Angle Psychological Hook Generation
    4. Retention-Engineered Storyboarding & Visual Directing
    5. Pre-Flight Fact & Policy Verification
    
    Returns only certified, production-ready content packages.
    """
    start_time = datetime.now()
    print("\n" + "=" * 65)
    print("   🧠 AI PRE-GENERATION INTELLIGENCE ENGINE")
    print(f"   Mode: {'Shorts (9:16)' if is_shorts else 'Broadcast (16:9)'} | Cutoff Score: {min_score} pts")
    print("=" * 65)

    # Ensure DB tables are ready
    init_learning_tables()

    # 1. Topic Discovery
    print(f"\n[1/5] Ingesting trends, science, mysteries & breakout topics...")
    candidates = discover_candidate_topics(max_candidates=40)
    print(f"      Discovered {len(candidates)} raw candidate topics across 7 sources.")

    # 2. 6D Viral Scoring Gate
    print(f"\n[2/5] Evaluating candidates through 6D Viral Potential Gate...")
    approved, rejected = score_and_filter_topics(candidates, threshold=min_score)
    print(f"      Passed Score Gate: {len(approved)} | Filtered / Discarded: {len(rejected)}")

    if not approved:
        # Graceful fallback: lower threshold slightly if strict filter left 0
        print(f"      [Notice] No topics met {min_score} pts. Expanding cutoff to {min_score - 10.0} pts...")
        approved, _ = score_and_filter_topics(candidates, threshold=min_score - 10.0)

    # Enforce Editorial Diversity (Max 2 topics per category to prevent context overlap)
    selected_topics = []
    category_counts = {}
    
    # Pass 1: Select balanced top-scoring topics across diverse categories
    for topic in approved:
        cat = topic.get("category", "GENERAL").upper()
        if category_counts.get(cat, 0) < 2:
            selected_topics.append(topic)
            category_counts[cat] = category_counts.get(cat, 0) + 1
            if len(selected_topics) >= target_count:
                break
                
    # Pass 2: Fill remaining slots if needed
    if len(selected_topics) < target_count:
        for topic in approved:
            if topic not in selected_topics:
                selected_topics.append(topic)
                if len(selected_topics) >= target_count:
                    break

    print(f"      Curated {len(selected_topics)} diversified topics across categories:")
    for cat, cnt in category_counts.items():
        print(f"         • {cat}: {cnt} story")

    production_packages = []
    used_hook_types = set()

    # 3, 4, 5. Hook Generation, Storyboarding & Verification
    print(f"\n[3/5] Engineering Psychological Hooks & Retention Storyboards...")
    for idx, topic in enumerate(selected_topics, 1):
        # A. Hook Generation (Enforces distinct hook structures across consecutive stories)
        champion_hook, all_hooks = select_champion_hook(topic, excluded_types=used_hook_types)
        used_hook_types.add(champion_hook["type"])
        # Reset if all 5 types were used so we can cycle
        if len(used_hook_types) >= 5:
            used_hook_types = set()

        # B. Retention Storyboard & Visual Direction Plan
        storyboard = plan_and_save_storyboard(topic, champion_hook, is_shorts=is_shorts)

        # C. Pre-Flight Verification
        qc_report = run_preflight_verification(topic, champion_hook, storyboard)

        if not qc_report["passed"]:
            print(f"      [!] Topic {idx} failed pre-flight verification: {qc_report['recommendation']}. Skipping.")
            continue

        package = {
            "topic_id": topic.get("topic_id"),
            "category": topic["category"],
            "title": topic["title"],
            "summary": topic["summary"],
            "total_score": topic["total_score"],
            "champion_hook": champion_hook,
            "all_hooks": all_hooks,
            "storyboard": storyboard,
            "qc_report": qc_report,
            "local_image": topic.get("image_url", "")
        }

        production_packages.append(package)
        print(f"   {idx:2d}. [{topic['total_score']} pts] [{topic['category']:8s}] Hook: \"{champion_hook['text'][:55]}...\"")

    elapsed = (datetime.now() - start_time).total_seconds()
    print("\n" + "=" * 65)
    print(f"   [OK] PRE-GENERATION COMPLETED IN {elapsed:.1f}s")
    print(f"   {len(production_packages)} topics fully certified & ready for video generation.")
    print("=" * 65 + "\n")

    return production_packages

if __name__ == "__main__":
    packages = execute_pre_generation_pipeline(target_count=5, min_score=70.0, is_shorts=True)
    if packages:
        print("\nDETAILED PREVIEW OF WINNING TOPIC #1:")
        pkg = packages[0]
        print(f"Title:         {pkg['title']}")
        print(f"Category:      {pkg['category']} (Score: {pkg['total_score']} pts)")
        print(f"Champion Hook: {pkg['champion_hook']['text']} (Type: {pkg['champion_hook']['type'].upper()})")
        print(f"Script Beats:")
        for b in pkg["storyboard"]["blueprint"]:
            print(f"  - [{b['time_range']}] {b['beat']}: {b['narration'][:70]}...")
