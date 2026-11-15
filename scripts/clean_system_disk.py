import os
import shutil
from pathlib import Path

def clean_directory(dir_path: Path, keep_patterns=None):
    if not dir_path.exists():
        return 0, 0
    keep_patterns = keep_patterns or []
    bytes_freed = 0
    files_removed = 0

    for item in list(dir_path.iterdir()):
        # Check if should keep
        should_keep = any(item.name.endswith(p) or item.name == p for p in keep_patterns)
        if should_keep:
            continue

        try:
            if item.is_file():
                size = item.stat().st_size
                item.unlink(missing_ok=True)
                bytes_freed += size
                files_removed += 1
            elif item.is_dir():
                # calculate size
                for root, dirs, files in os.walk(item):
                    for f in files:
                        try:
                            bytes_freed += os.path.getsize(os.path.join(root, f))
                            files_removed += 1
                        except Exception:
                            pass
                shutil.rmtree(item, ignore_errors=True)
        except Exception as e:
            print(f"  [!] Notice cleaning {item}: {e}")

    return bytes_freed, files_removed

def run_master_cleanup():
    print("=" * 65)
    print("  EXECUTING COMPREHENSIVE DISK CLEANUP")
    print("  BharatBeacon News & 60-Day Tech Masterclasses")
    print("=" * 65)

    total_bytes = 0
    total_files = 0

    # 1. Clean News Channels directories
    news_dirs = [
        Path("D:/youtube news/output/longform"),
        Path("D:/youtube news/output/shorts"),
        Path("D:/youtube news/output/temp"),
        Path("D:/youtube news/output/samples"),
        Path("D:/youtube news/output/demos"),
        Path("D:/youtube news/output/audio_tracks"),
        Path("D:/youtube news/output/demo_frames"),
        Path("D:/youtube news/output/voice_samples")
    ]

    print("\n[1/2] Cleaning News Channel Build & Video Artifacts...")
    for nd in news_dirs:
        b, f = clean_directory(nd)
        total_bytes += b
        total_files += f
        if f > 0:
            print(f"  ✓ Cleaned {nd.name:15s}: {f:3d} files removed ({b / 1024 / 1024:.2f} MB)")

    # 2. Clean Programming Channel directories
    prog_dirs = [
        Path("D:/bharatbeacon-programming/output/temp"),
        Path("D:/bharatbeacon-programming/output/longform"),
        Path("D:/bharatbeacon-programming/output/shorts")
    ]

    print("\n[2/2] Cleaning Programming Masterclass Temp & Video Artifacts...")
    for pd in prog_dirs:
        b, f = clean_directory(pd)
        total_bytes += b
        total_files += f
        if f > 0:
            print(f"  ✓ Cleaned {pd.name:15s}: {f:3d} files removed ({b / 1024 / 1024:.2f} MB)")

    print("\n" + "=" * 65)
    print(f"  DISK CLEANUP COMPLETE!")
    print(f"  Total Files Removed: {total_files}")
    print(f"  Total Disk Space Reclaimed: {total_bytes / 1024 / 1024 / 1024:.2f} GB ({total_bytes / 1024 / 1024:.1f} MB)")
    print("=" * 65)

if __name__ == "__main__":
    run_master_cleanup()
