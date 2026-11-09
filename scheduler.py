import sys
import argparse
from datetime import datetime
from pathlib import Path
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

# Add project root to sys.path
sys.path.append(str(Path(__file__).resolve().parent))

# Ensure UTF-8 output on Windows
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

from run_hourly import execute_hourly_cycle

def main():
    parser = argparse.ArgumentParser(description="Automated Hourly YouTube News Scheduler")
    parser.add_argument("--now", action="store_true", help="Run a cycle immediately before starting schedule")
    parser.add_argument("--interval", type=int, default=None, help="Run every N minutes instead of hourly at :00")
    args = parser.parse_args()

    print("\n" + "=" * 65)
    print("  🚀 STARTING INDIA HOURLY NEWS SCHEDULER")
    print("=" * 65)

    if args.now:
        print("\n[INFO] --now flag detected. Executing initial cycle now...")
        execute_hourly_cycle(deduplicate=True)

    scheduler = BlockingScheduler()

    if args.interval:
        print(f"[INFO] Running on interval: Every {args.interval} minutes.")
        scheduler.add_job(
            execute_hourly_cycle,
            IntervalTrigger(minutes=args.interval),
            id="interval_news_cycle",
            replace_existing=True
        )
    else:
        print("[INFO] Running on hourly schedule: Every hour at :00 IST.")
        scheduler.add_job(
            execute_hourly_cycle,
            CronTrigger(minute="0"),
            id="hourly_news_cycle",
            replace_existing=True
        )

    print("[STATUS] Scheduler is running in background. Press Ctrl+C to stop.")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        print("\n[INFO] Scheduler stopped cleanly.")

if __name__ == "__main__":
    main()
