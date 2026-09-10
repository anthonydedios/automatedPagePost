"""
Posts ALL active items in posts/queue.json to your Facebook Page as ONE
single multi-photo post (every photo across every active item, bundled
together, in randomized order).

How it works, per Facebook Graph API mechanics:
  1. Every photo from every active item is uploaded as an "unpublished"
     photo (published=false) - each upload can carry its own caption, built
     from that item's name/price/description via caption_engine.
  2. One feed post is then created that attaches all of those uploaded
     photo ids together (attached_media), with a single overall caption
     (caption_engine.generate_batch_caption) as the post's message.
  3. Every item that contributed a photo has its last_posted_at/times_posted
     updated in the queue file.

Note: Facebook may enforce an undocumented practical limit on how many
photos can be attached to a single post. If you have a large catalog and
the API rejects the request, check the run's error output - you may need
to split posting into smaller batches.

Required environment variables (set as GitHub Secrets):
  FB_PAGE_ID             - your Facebook Page's numeric ID
  FB_PAGE_ACCESS_TOKEN   - a long-lived Page access token
"""

import json
import os
import random
import sys
from datetime import datetime, timezone

import requests

from caption_engine import generate_caption, generate_batch_caption

QUEUE_PATH = "posts/queue.json"
GRAPH_API_VERSION = "v20.0"


def load_queue():
    with open(QUEUE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_queue(queue):
    with open(QUEUE_PATH, "w", encoding="utf-8") as f:
        json.dump(queue, f, indent=2, ensure_ascii=False)


def _get_image_urls(item):
    urls = item.get("image_urls")
    if urls:
        return [u for u in urls if u]
    legacy = item.get("image_url")  # backward compat
    return [legacy] if legacy else []


def build_photo_list(queue):
    """
    Flattens every active item's photos into a single (item, url) list and
    shuffles it, so the order photos appear in the post isn't the same
    every run and isn't grouped strictly by item.
    """
    active_items = [i for i in queue if i.get("active", True)]
    photo_list = []
    for item in active_items:
        for url in _get_image_urls(item):
            photo_list.append((item, url))
    random.shuffle(photo_list)
    return active_items, photo_list


def _upload_unpublished_photo(page_id, access_token, image_url, caption):
    endpoint = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{page_id}/photos"
    payload = {
        "url": image_url,
        "published": "false",
        "caption": caption,
        "access_token": access_token,
    }
    response = requests.post(endpoint, data=payload, timeout=30)
    if response.status_code != 200:
        print(f"Facebook API error (photo upload): {response.status_code} {response.text}", file=sys.stderr)
        response.raise_for_status()
    return response.json()["id"]


def post_all_as_one(page_id, access_token, queue):
    active_items, photo_list = build_photo_list(queue)

    if not photo_list:
        return None, active_items

    photo_ids = []
    for item, url in photo_list:
        caption = generate_caption(item)
        photo_ids.append(_upload_unpublished_photo(page_id, access_token, url, caption))

    message = generate_batch_caption(active_items)

    endpoint = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{page_id}/feed"
    payload = {"message": message, "access_token": access_token}
    for i, photo_id in enumerate(photo_ids):
        payload[f"attached_media[{i}]"] = json.dumps({"media_fbid": photo_id})

    response = requests.post(endpoint, data=payload, timeout=30)
    if response.status_code != 200:
        print(f"Facebook API error (feed post): {response.status_code} {response.text}", file=sys.stderr)
        response.raise_for_status()

    result = response.json()
    result["_caption_used"] = message
    result["_photo_count"] = len(photo_ids)
    return result, active_items


def main():
    page_id = os.environ.get("FB_PAGE_ID")
    access_token = os.environ.get("FB_PAGE_ACCESS_TOKEN")

    if not page_id or not access_token:
        print("Missing FB_PAGE_ID or FB_PAGE_ACCESS_TOKEN environment variables.", file=sys.stderr)
        sys.exit(1)

    queue = load_queue()
    result, active_items = post_all_as_one(page_id, access_token, queue)

    if result is None:
        print("No active items with photos in the queue. Nothing to post.")
        return

    print(f"Posted {result['_photo_count']} photo(s) across {len(active_items)} item(s) in one post.")
    print(f"Post caption:\n{result['_caption_used']}\n")
    print("Facebook API response:", {k: v for k, v in result.items() if not k.startswith("_")})

    now = datetime.now(timezone.utc).isoformat()
    for item in active_items:
        item["last_posted_at"] = now
        item["times_posted"] = item.get("times_posted", 0) + 1
    save_queue(queue)


if __name__ == "__main__":
    main()
