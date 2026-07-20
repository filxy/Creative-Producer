"""
Filxy Auto-Poster — Instagram Graph API
Posts the 3 neon hoodie drop captions to an Instagram Business account.

Requirements:
    pip install requests python-dotenv schedule

.env file (filxy.env):
    INSTAGRAM_USER_ID=your_instagram_user_id
    INSTAGRAM_ACCESS_TOKEN=your_long_lived_access_token
    IMAGE_URL=https://your-cdn.com/filxy-hoodie.jpg
    VIDEO_URL=https://your-cdn.com/filxy-spin.mp4   # optional — enables Reels mode

Usage:
    python poster.py                        # post images immediately
    python poster.py --dry-run              # preview only, zero API calls
    python poster.py --schedule             # post images at peak hours
    python poster.py --schedule --dry-run   # preview schedule
    python poster.py --reel                 # post as Instagram Reel (video)
    python poster.py --reel --dry-run       # preview reel post
"""

import argparse
import os
import time
import datetime
import schedule
import requests
from dotenv import load_dotenv

load_dotenv("filxy.env")

IG_USER_ID = os.getenv("INSTAGRAM_USER_ID")
IG_ACCESS_TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN")
IMAGE_URL = os.getenv("IMAGE_URL")
VIDEO_URL = os.getenv("VIDEO_URL")

BASE_URL = "https://graph.facebook.com/v21.0"

CAPTIONS = [
    (
        "Your fit is mid. Filxy ice blue drop just hit. Electric. Limited. Cop now. 🖤💙\n"
        "#Filxy #StreetWear #NeonBlue #IceDrop #CopNow #ElectricFit"
    ),
    (
        "Walked into the function in Filxy. Ice glow on full send. Whole room froze. 🖤💙\n"
        "#Filxy #StreetStyle #Hoodie #IceGlow #FunctionFit #NeonBlue"
    ),
    (
        "Electric blue. Limited drop. 48hrs only. Cop it or stay mid forever. Crying. 🖤💙\n"
        "#Filxy #48HourDrop #LimitedEdition #StreetWear #IceHoodie #Cop"
    ),
]

# Peak hours for streetwear / Gen-Z audience (24h format, local time)
# Research: highest IG engagement windows are 9am, 12pm, and 6pm.
PEAK_SCHEDULE = [
    {"time": "09:00", "caption_index": 0, "label": "Morning drop alert"},
    {"time": "12:00", "caption_index": 1, "label": "Lunch scroll"},
    {"time": "18:00", "caption_index": 2, "label": "After-school/work peak"},
]


# ─── Dry-run ────────────────────────────────────────────────────────────────

def dry_run_preview(captions: list[str], scheduled: bool = False) -> None:
    """Print a full preview of every post — zero API calls, zero risk."""
    print("\n📋 DRY-RUN PREVIEW — nothing will be posted\n")
    print(f"  Image URL : {IMAGE_URL or '(not set)'}")
    print(f"  IG User ID: {IG_USER_ID or '(not set)'}")
    print(f"  API Token : {'SET ✓' if IG_ACCESS_TOKEN else 'NOT SET ✗'}")
    print()

    if scheduled:
        print("  📅 Scheduled peak-hour slots:\n")
        for slot in PEAK_SCHEDULE:
            caption = captions[slot["caption_index"]]
            first_line = caption.splitlines()[0]
            print(f"  {slot['time']}  [{slot['label']}]")
            print(f"    → {first_line}")
            print()
        print(f"{'─' * 40}")
        print("✅ Dry run complete. Run with --schedule (no --dry-run) to go live. 🖤💚")
        return

    for i, caption in enumerate(captions):
        print(f"{'─' * 40}")
        print(f"  Post {i + 1} of {len(captions)}")
        print(f"  Caption preview:\n")
        for line in caption.splitlines():
            print(f"    {line}")
        print(f"\n  → Would wait 5s then publish container")
        if i < len(captions) - 1:
            print(f"  → Would wait 30s before next post")
        print()

    print(f"{'─' * 40}")
    print("✅ Dry run complete. Looks clean? Run without --dry-run to go live. 🖤💚")


# ─── API helpers ────────────────────────────────────────────────────────────

def create_media_container(caption: str, reel: bool = False) -> str:
    """Step 1 — Upload media + caption to create a container.
    reel=True posts as an Instagram Reel using VIDEO_URL.
    """
    url = f"{BASE_URL}/{IG_USER_ID}/media"
    if reel:
        payload = {
            "media_type": "REELS",
            "video_url": VIDEO_URL,
            "caption": caption,
            "share_to_feed": "true",
            "access_token": IG_ACCESS_TOKEN,
        }
    else:
        payload = {
            "image_url": IMAGE_URL,
            "caption": caption,
            "access_token": IG_ACCESS_TOKEN,
        }
    response = requests.post(url, data=payload)
    if not response.ok:
        print(f"  ✗ API error {response.status_code}: {response.text}")
    response.raise_for_status()
    container_id = response.json()["id"]
    print(f"  ✓ Container created: {container_id}")
    return container_id


def wait_for_reel_ready(container_id: str, timeout: int = 120) -> None:
    """Reels need processing time before publish. Poll until STATUS=FINISHED."""
    print(f"  ⏳ Waiting for reel to process...")
    deadline = time.time() + timeout
    while time.time() < deadline:
        resp = requests.get(
            f"{BASE_URL}/{container_id}",
            params={"fields": "status_code", "access_token": IG_ACCESS_TOKEN},
        )
        status = resp.json().get("status_code", "")
        if status == "FINISHED":
            print(f"  ✓ Reel ready")
            return
        if status == "ERROR":
            raise RuntimeError(f"Reel processing failed: {resp.text}")
        time.sleep(10)
    raise TimeoutError("Reel did not finish processing within timeout.")


def publish_container(container_id: str) -> str:
    """Step 2 — Publish the media container as a post."""
    url = f"{BASE_URL}/{IG_USER_ID}/media_publish"
    payload = {
        "creation_id": container_id,
        "access_token": IG_ACCESS_TOKEN,
    }
    response = requests.post(url, data=payload)
    response.raise_for_status()
    post_id = response.json()["id"]
    print(f"  ✓ Published post: {post_id}")
    return post_id


def post_caption(caption: str, index: int, reel: bool = False) -> None:
    """Create container then publish — with processing wait for Reels."""
    label = "reel" if reel else "post"
    print(f"\n🖤 Posting {label} {index + 1}/{len(CAPTIONS)}...")
    container_id = create_media_container(caption, reel=reel)
    if reel:
        wait_for_reel_ready(container_id)
    else:
        time.sleep(5)  # Instagram recommends waiting before publishing
    post_id = publish_container(container_id)
    print(f"  💙 Done — post ID: {post_id}")


# ─── Immediate posting ───────────────────────────────────────────────────────

def post_all_immediately(reel: bool = False) -> None:
    """Fire all 3 captions right now with 30s gaps."""
    for i, caption in enumerate(CAPTIONS):
        post_caption(caption, i, reel=reel)
        if i < len(CAPTIONS) - 1:
            print("  ⏳ Waiting 30s before next post...")
            time.sleep(30)
    print("\n🖤💙 All 3 posts live. Vibe secured.")


# ─── Scheduled posting ───────────────────────────────────────────────────────

def build_scheduled_job(caption_index: int, label: str, reel: bool = False):
    """Return a zero-argument callable for schedule to invoke."""
    def job():
        now = datetime.datetime.now().strftime("%H:%M:%S")
        print(f"\n⏰ [{now}] Scheduled slot fired: {label}")
        post_caption(CAPTIONS[caption_index], caption_index, reel=reel)
        return schedule.CancelJob
    return job


def run_scheduled(reel: bool = False) -> None:
    """Register all peak-hour slots and block until all jobs have fired."""
    print("\n📅 Scheduling peak-hour posts (local time):\n")
    for slot in PEAK_SCHEDULE:
        t = slot["time"]
        job_fn = build_scheduled_job(slot["caption_index"], slot["label"], reel=reel)
        schedule.every().day.at(t).do(job_fn)
        print(f"  ✓ {t}  — {slot['label']} (caption {slot['caption_index'] + 1})")

    total_jobs = len(PEAK_SCHEDULE)
    fired = [0]

    print(f"\n  Waiting for {total_jobs} scheduled slots... (Ctrl+C to cancel)\n")

    initial_count = len(schedule.jobs)

    while True:
        schedule.run_pending()
        remaining = len(schedule.jobs)
        completed = initial_count - remaining
        if completed != fired[0]:
            fired[0] = completed
            if fired[0] == total_jobs:
                print("\n🖤💙 All scheduled posts fired. Vibe delivered on time.")
                break
        time.sleep(20)


# ─── Entry point ─────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Filxy IG Auto-Poster")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview posts without making any API calls",
    )
    parser.add_argument(
        "--schedule",
        action="store_true",
        help="Post at peak hours (09:00, 12:00, 18:00) instead of immediately",
    )
    parser.add_argument(
        "--reel",
        action="store_true",
        help="Post as Instagram Reel using VIDEO_URL from filxy.env",
    )
    args = parser.parse_args()

    print("💙 Filxy Auto-Poster — Ice Drop")
    print("=" * 40)

    if args.dry_run:
        mode = "reel" if args.reel else "image"
        url = VIDEO_URL if args.reel else IMAGE_URL
        print(f"  Mode      : {mode.upper()}")
        print(f"  Media URL : {url or '(not set)'}")
        dry_run_preview(CAPTIONS, scheduled=args.schedule)
        return

    if args.reel and not VIDEO_URL:
        raise EnvironmentError("VIDEO_URL not set in filxy.env — required for --reel mode")

    if not all([IG_USER_ID, IG_ACCESS_TOKEN]):
        raise EnvironmentError(
            "Missing env vars. Set INSTAGRAM_USER_ID and INSTAGRAM_ACCESS_TOKEN in filxy.env"
        )

    if args.schedule:
        run_scheduled(reel=args.reel)
    else:
        post_all_immediately(reel=args.reel)


if __name__ == "__main__":
    main()
