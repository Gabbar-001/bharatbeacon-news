import sqlite3
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any

import sys
from pathlib import Path

# Ensure UTF-8 output on Windows
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

sys.path.append(str(Path(__file__).resolve().parent.parent))
import config

DB_PATH = getattr(config, "DB_PATH", Path("news_tracker.db"))

def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_learning_tables():
    """Initializes tables for the AI Pre-Generation Engine and Self-Learning System."""
    conn = get_connection()
    cur = conn.cursor()

    # 1. Topic Pool: Records all discovered topics, 6D scores, status & reasoning
    cur.execute("""
        CREATE TABLE IF NOT EXISTS topic_pool (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT,
            title TEXT,
            clean_title TEXT,
            summary TEXT,
            category TEXT,
            url TEXT,
            image_url TEXT,
            curiosity_score REAL,
            surprise_score REAL,
            visual_score REAL,
            resonance_score REAL,
            saturation_score REAL,
            channel_fit_score REAL,
            total_score REAL,
            status TEXT DEFAULT 'pending', -- 'approved', 'rejected', 'produced'
            rejection_reason TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 2. Hook Experiments: Stores the 5 psychological hook angles per topic
    cur.execute("""
        CREATE TABLE IF NOT EXISTS hook_experiments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic_id INTEGER,
            hook_text TEXT,
            hook_type TEXT, -- 'paradox', 'challenge', 'forbidden_curiosity', 'high_stakes_question', 'shocking_contrast'
            predicted_score REAL,
            is_champion BOOLEAN DEFAULT 0,
            actual_views INTEGER DEFAULT 0,
            actual_viewed_pct REAL DEFAULT 0.0,
            actual_swipe_rate REAL DEFAULT 0.0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(topic_id) REFERENCES topic_pool(id)
        )
    """)

    # 3. Storyboards: Stores the retention-engineered script structure & visual cues
    cur.execute("""
        CREATE TABLE IF NOT EXISTS storyboards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic_id INTEGER,
            champion_hook_id INTEGER,
            target_duration REAL,
            full_script TEXT,
            retention_blueprint_json TEXT,
            visual_cues_json TEXT,
            status TEXT DEFAULT 'ready',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(topic_id) REFERENCES topic_pool(id),
            FOREIGN KEY(champion_hook_id) REFERENCES hook_experiments(id)
        )
    """)

    # 4. Channel Learning Memory: Cumulative algorithmic weights updated by performance
    cur.execute("""
        CREATE TABLE IF NOT EXISTS channel_learning_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dimension_type TEXT, -- 'category', 'hook_type', 'duration_bracket'
            dimension_key TEXT UNIQUE, -- e.g. 'SCIENCE', 'MYSTERY', 'paradox', '30_60s'
            weight_multiplier REAL DEFAULT 1.0,
            avg_view_duration_pct REAL DEFAULT 65.0,
            avg_swipe_rate REAL DEFAULT 30.0,
            sample_count INTEGER DEFAULT 0,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Seed initial industry-benchmark weights if empty
    cur.execute("SELECT COUNT(*) FROM channel_learning_memory")
    if cur.fetchone()[0] == 0:
        initial_weights = [
            # Categories
            ("category", "SCIENCE", 1.25, 74.0, 22.0, 5),
            ("category", "SPACE", 1.30, 78.0, 19.0, 5),
            ("category", "MYSTERY", 1.35, 82.0, 16.0, 5),
            ("category", "HISTORY", 1.15, 68.0, 26.0, 5),
            ("category", "TECH", 1.10, 66.0, 28.0, 5),
            ("category", "NATIONAL", 0.90, 58.0, 36.0, 5),
            ("category", "BUSINESS", 0.85, 52.0, 42.0, 5),
            ("category", "SPORTS", 1.05, 64.0, 31.0, 5),

            # Hook Types
            ("hook_type", "paradox", 1.30, 80.0, 18.0, 5),
            ("hook_type", "forbidden_curiosity", 1.25, 76.0, 21.0, 5),
            ("hook_type", "shocking_contrast", 1.20, 73.0, 24.0, 5),
            ("hook_type", "challenge", 1.15, 70.0, 26.0, 5),
            ("hook_type", "high_stakes_question", 1.10, 67.0, 29.0, 5)
        ]
        cur.executemany("""
            INSERT INTO channel_learning_memory 
            (dimension_type, dimension_key, weight_multiplier, avg_view_duration_pct, avg_swipe_rate, sample_count)
            VALUES (?, ?, ?, ?, ?, ?)
        """, initial_weights)

    conn.commit()
    conn.close()

def save_topic(topic: Dict[str, Any]) -> int:
    """Inserts a candidate topic with its 6D scores into the topic pool."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO topic_pool (
            source, title, clean_title, summary, category, url, image_url,
            curiosity_score, surprise_score, visual_score, resonance_score,
            saturation_score, channel_fit_score, total_score, status, rejection_reason
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        topic.get("source", "unknown"),
        topic.get("title", ""),
        topic.get("clean_title", topic.get("title", "")),
        topic.get("summary", ""),
        topic.get("category", "GENERAL").upper(),
        topic.get("url", ""),
        topic.get("image_url", ""),
        topic.get("curiosity_score", 0.0),
        topic.get("surprise_score", 0.0),
        topic.get("visual_score", 0.0),
        topic.get("resonance_score", 0.0),
        topic.get("saturation_score", 0.0),
        topic.get("channel_fit_score", 0.0),
        topic.get("total_score", 0.0),
        topic.get("status", "pending"),
        topic.get("rejection_reason", "")
    ))
    topic_id = cur.lastrowid
    conn.commit()
    conn.close()
    return topic_id

def save_hook_experiments(topic_id: int, hooks: List[Dict[str, Any]]) -> List[int]:
    """Saves the 5 psychological hook variations and tags the champion."""
    conn = get_connection()
    cur = conn.cursor()
    hook_ids = []
    for h in hooks:
        cur.execute("""
            INSERT INTO hook_experiments (
                topic_id, hook_text, hook_type, predicted_score, is_champion
            ) VALUES (?, ?, ?, ?, ?)
        """, (
            topic_id,
            h.get("text", ""),
            h.get("type", "general"),
            h.get("predicted_score", 0.0),
            1 if h.get("is_champion") else 0
        ))
        hook_ids.append(cur.lastrowid)
    conn.commit()
    conn.close()
    return hook_ids

def save_storyboard(topic_id: int, champion_hook_id: int, script: str, blueprint: List[Dict], visual_cues: List[Dict], duration: float) -> int:
    """Saves the retention storyboard and visual direction plan."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO storyboards (
            topic_id, champion_hook_id, target_duration, full_script,
            retention_blueprint_json, visual_cues_json, status
        ) VALUES (?, ?, ?, ?, ?, ?, 'ready')
    """, (
        topic_id,
        champion_hook_id,
        duration,
        script,
        json.dumps(blueprint, ensure_ascii=False),
        json.dumps(visual_cues, ensure_ascii=False)
    ))
    sb_id = cur.lastrowid
    conn.commit()
    conn.close()
    return sb_id

def get_dimension_multiplier(dim_key: str) -> float:
    """Retrieves the learned multiplier for a given category or hook type."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT weight_multiplier FROM channel_learning_memory WHERE dimension_key = ?", (dim_key.upper(),))
    row = cur.fetchone()
    conn.close()
    return float(row["weight_multiplier"]) if row else 1.0

def update_learning_memory(dim_key: str, view_pct: float, swipe_rate: float):
    """
    Feeds YouTube Analytics performance back into memory:
    Adjusts weight multiplier up or down based on actual audience retention.
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM channel_learning_memory WHERE dimension_key = ?", (dim_key.upper(),))
    row = cur.fetchone()

    if row:
        curr_samples = row["sample_count"]
        new_samples = curr_samples + 1
        curr_mult = row["weight_multiplier"]

        # Calculate performance ratio against baseline
        # Average retention > 70% or swipe < 25% boosts weight
        perf_factor = (view_pct / 65.0) * (30.0 / max(swipe_rate, 10.0))
        target_mult = max(0.5, min(2.0, curr_mult * 0.8 + perf_factor * 0.2))

        cur.execute("""
            UPDATE channel_learning_memory
            SET weight_multiplier = ?,
                avg_view_duration_pct = (avg_view_duration_pct * ? + ?) / ?,
                avg_swipe_rate = (avg_swipe_rate * ? + ?) / ?,
                sample_count = ?,
                last_updated = CURRENT_TIMESTAMP
            WHERE dimension_key = ?
        """, (
            round(target_mult, 3),
            curr_samples, view_pct, new_samples,
            curr_samples, swipe_rate, new_samples,
            new_samples,
            dim_key.upper()
        ))
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_learning_tables()
    print("[OK] Learning memory database initialized successfully.")
    print("    Sample Category Multipliers:")
    for cat in ["SPACE", "MYSTERY", "SCIENCE", "NATIONAL", "BUSINESS"]:
        print(f"    - {cat:10s}: {get_dimension_multiplier(cat):.2f}x")
