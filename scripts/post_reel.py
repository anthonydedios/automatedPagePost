"""
Generates a slideshow Reel from one product's photos (rotating through
the same duster -> ternosleeve -> smockdress cycle, independently from
the photo-post rotation) and publishes it as a Facebook Reel.

Reels use a different, 3-step upload flow than regular photo posts:
  1. Start an upload session  -> POST /{page_id}/video_reels (upload_phase=start)
  2. Upload the video bytes   -> POST to the returned upload_url
  3. Finish & publish         -> POST /{page_id}/video_reels (upload_phase=finish)

Requires the Page access token to have BOTH pages_manage_posts AND
pages_manage_engagement.

Required environment variables (set as GitHub Secrets):
  FB_PAGE_ID             - your Facebook Page's numeric ID
  FB_PAGE_ACCESS_TOKEN   - a long-lived Page access token with Reels scopes
"""

import json
import os
import random
import sys
import tempfile
import time

import requests

from generate_reel import generate_reel
from post_to_facebook import PRODUCTS, ALLOWED_EXTENSIONS

GRAPH_API_VERSION = "v20.0"
REEL_STATE_PATH = "posts/reel_rotation_state.json"
PHOTOS_PER_REEL = 5  # 5 x 2.5s = ~12.5s reel; stays well inside FB's 3-90s window


def load_state():
    if not os.path.exists(REEL_STATE_PATH):
        return {"last_index": -1, "decks": {}}
    try:
        with open(REEL_STATE_PATH, "r", encoding="utf-8") as f:
            state = json.load(f)
            state.setdefault("decks", {})
            return state
    except (json.JSONDecodeError, OSError):
        return {"last_index": -1, "decks": {}}


def save_state(state):
    os.makedirs(os.path.dirname(REEL_STATE_PATH), exist_ok=True)
    with open(REEL_STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


def list_folder_files(photos_dir):
    if not os.path.isdir(photos_dir):
        return []
    return [
        f for f in os.listdir(photos_dir)
        if os.path.splitext(f)[1].lower() in ALLOWED_EXTENSIONS
    ]


def deal_photos(state, product, count):
    """Same no-repeat-until-exhausted deck logic as post_to_facebook.py,
    kept independent here so reels and photo-posts don't drain the same
    deck or interfere with each other's rotation state."""
    key = product["key"]
    deck = state["decks"].get(key, [])

    current_files = list_folder_files(product["dir"])
    if not deck or not set(deck).issubset(set(current_files)):
        deck = current_files[:]
        random.shuffle(deck)

    dealt = deck[:count]
    remaining = deck[count:]

    if len(dealt) < count and current_files:
        leftover_pool = [f for f in current_files if f not in dealt]
        random.shuffle(leftover_pool)
        need = count - len(dealt)
        top_up = leftover_pool[:need]
        dealt += top_up
        remaining = [f for f in leftover_pool[need:]]

    state["decks"][key] = remaining
    return [os.path.join(product["dir"], f) for f in dealt]


def start_upload_session(page_id, access_token):
    url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{page_id}/video_reels"
    response = requests.post(url, data={"upload_phase": "start", "access_token": access_token}, timeout=30)
    if response.status_code != 200:
        print(f"Error starting reel upload session: {response.text}", file=sys.stderr)
        response.raise_for_status()
    data = response.json()
    return data["video_id"], data["upload_url"]


def upload_video_bytes(upload_url, access_token, video_path):
    file_size = os.path.getsize(video_path)
    with open(video_path, "rb") as f:
        video_bytes = f.read()

    headers = {
        "Authorization": f"OAuth {access_token}",
        "offset": "0",
        "file_size": str(file_size),
    }
    response = requests.post(upload_url, headers=headers, data=video_bytes, timeout=300)
    if response.status_code != 200:
        print(f"Error uploading reel video bytes: {response.text}", file=sys.stderr)
        response.raise_for_status()
    return response.json()


def wait_for_processing(page_id, video_id, access_token, timeout_seconds=180):
    url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{video_id}"
    params = {"fields": "status", "access_token": access_token}
    start = time.time()
    while time.time() - start < timeout_seconds:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        status = response.json().get("status", {})
        phase = status.get("video_status") or status.get("uploading_phase", {}).get("status")
        print(f"Processing status: {status}")
        if phase == "ready" or status.get("uploading_phase", {}).get("status") == "complete":
            return
        time.sleep(5)
    print("Timed out waiting for reel to finish processing - attempting to publish anyway.")


def finish_and_publish(page_id, access_token, video_id, caption):
    url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{page_id}/video_reels"
    payload = {
        "upload_phase": "finish",
        "video_id": video_id,
        "description": caption,
        "video_state": "PUBLISHED",
        "access_token": access_token,
    }
    response = requests.post(url, data=payload, timeout=60)
    if response.status_code != 200:
        print(f"Error publishing reel: {response.text}", file=sys.stderr)
        response.raise_for_status()
    return response.json()


def main():
    page_id = os.environ.get("FB_PAGE_ID")
    access_token = os.environ.get("FB_PAGE_ACCESS_TOKEN")

    if not page_id or not access_token:
        print("Missing FB_PAGE_ID or FB_PAGE_ACCESS_TOKEN environment variables.", file=sys.stderr)
        sys.exit(1)

    state = load_state()
    next_index = (state["last_index"] + 1) % len(PRODUCTS)
    product = PRODUCTS[next_index]
    print(f"Reel rotation: posting index={next_index} ({product['key']})")

    photo_paths = deal_photos(state, product, PHOTOS_PER_REEL)
    if not photo_paths:
        print(f"No image files found in {product['dir']}. Skipping without advancing rotation.")
        return

    print(f"Using {len(photo_paths)} photo(s) for this reel:")
    for p in photo_paths:
        print(f"  - {p}")

    with tempfile.TemporaryDirectory() as tmpdir:
        video_path = os.path.join(tmpdir, "reel.mp4")
        print("Generating slideshow video with ffmpeg...")
        generate_reel(photo_paths, video_path)

        print("Starting Facebook upload session...")
        video_id, upload_url = start_upload_session(page_id, access_token)

        print("Uploading video bytes...")
        upload_video_bytes(upload_url, access_token, video_path)

        print("Waiting for Facebook to finish processing the video...")
        wait_for_processing(page_id, video_id, access_token)

        print("Publishing reel...")
        result = finish_and_publish(page_id, access_token, video_id, product["caption"])

    print("Facebook API response:", result)

    state["last_index"] = next_index
    save_state(state)


if __name__ == "__main__":
    main()
