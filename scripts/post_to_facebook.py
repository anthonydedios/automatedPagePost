"""
Posts the next queued item to your Facebook Page's timeline.

Reads posts/queue.json, picks an item to post (weighted so long-unposted
items are favored but the exact pick is randomized - see pick_next_item),
publishes it to the Page via the Graph API using a freshly-generated caption,
then updates the queue file so state carries over between runs.

Each item can have one or more images (posts/queue.json "image_urls" list):
  - 1 image  -> a normal single-photo post.
  - 2+ images -> all images are uploaded as unpublished photos first, then
    attached to a single feed post (a Facebook "album"/multi-photo post),
    so a product with several angle shots goes out as ONE post instead of
    several separate ones.
  - 0 images -> a text-only post.

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

from caption_engine import generate_caption

QUEUE_PATH = "posts/queue.json"
GRAPH_API_VERSION = "v20.0"

# How many of the "stalest" (longest since posted) active items to randomly
# choose from each run. This is what keeps the posting order from being
# perfectly sequential/predictable (e.g. always item-002, item-003, ... in
# upload order) while still favoring items that haven't been posted in a
# while, so the whole catalog keeps rotating through.
SHUFFLE_POOL_SIZE = 8


def load_queue():
    with open(QUEUE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_queue(queue):
    with open(QUEUE_PATH, "w", encoding="utf-8") as f:
        json.dump(queue, f, indent=2, ensure_ascii=False)


def pick_next_item(queue):
    """
    Pick an item to post next.

    Sorts active items oldest-posted-first (never-posted items count as
    oldest), then randomly picks one from among the stalest SHUFFLE_POOL_SIZE
    of them. This keeps the rotation fair (nothing gets skipped for long)
    while breaking up the predictable, always-same-order sequence.
    """
    def sort_key(item):
        return item.get("last_posted_at") or ""

    active_items = [i for i in queue if i.get("active", True)]
    if not active_items:
        return None

    active_items.sort(key=sort_key)
    pool = active_items[:SHUFFLE_POOL_SIZE]
    return random.choice(pool)


def _get_image_urls(item):
    urls = item.get("image_urls")
    if urls:
        return [u for u in urls if u]
    # backward compat with the old single "image_url" field
    legacy = item.get("image_url")
    return [legacy] if legacy else []


def _upload_unpublished_photo(page_id, access_token, image_url):
    """Uploads one photo to the Page's photo library without publishing it,
    so it can be attached to a multi-photo feed post afterward. Returns the
    photo's id."""
    endpoint = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{page_id}/photos"
    payload = {
        "url": image_url,
        "published": "false",
        "access_token": access_token,
    }
    response = requests.post(endpoint, data=payload, timeout=30)
    if response.status_code != 200:
        print(f"Facebook API error (photo upload): {response.status_code} {response.text}", file=sys.stderr)
        response.raise_for_status()
    return response.json()["id"]


def post_to_page(page_id, access_token, item):
    caption = generate_caption(item)
    image_urls = _get_image_urls(item)

    if len(image_urls) == 0:
        endpoint = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{page_id}/feed"
        payload = {"message": caption, "access_token": access_token}
        response = requests.post(endpoint, data=payload, timeout=30)

    elif len(image_urls) == 1:
        endpoint = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{page_id}/photos"
        payload = {
            "url": image_urls[0],
            "caption": caption,
            "access_token": access_token,
        }
        response = requests.post(endpoint, data=payload, timeout=30)

    else:
        # Multi-photo post: upload each photo unpublished first, then create
        # one feed post that attaches all of them together.
        photo_ids = [_upload_unpublished_photo(page_id, access_token, url) for url in image_urls]
        endpoint = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{page_id}/feed"
        payload = {
            "message": caption,
            "access_token": access_token,
        }
        for i, photo_id in enumerate(photo_ids):
            payload[f"attached_media[{i}]"] = json.dumps({"media_fbid": photo_id})
        response = requests.post(endpoint, data=payload, timeout=30)

    if response.status_code != 200:
        print(f"Facebook API error: {response.status_code} {response.text}", file=sys.stderr)
        response.raise_for_status()
    result = response.json()
    result["_caption_used"] = caption
    result["_image_count"] = len(image_urls)
    return result


def main():
    page_id = os.environ.get("FB_PAGE_ID")
    access_token = os.environ.get("FB_PAGE_ACCESS_TOKEN")

    if not page_id or not access_token:
        print("Missing FB_PAGE_ID or FB_PAGE_ACCESS_TOKEN environment variables.", file=sys.stderr)
        sys.exit(1)

    queue = load_queue()
    item = pick_next_item(queue)

    if item is None:
        print("No active items in the queue. Nothing to post.")
        return

    print(f"Posting item id={item['id']} ({len(_get_image_urls(item))} image(s))")
    result = post_to_page(page_id, access_token, item)
    print(f"Caption used:\n{result['_caption_used']}\n")
    print("Facebook API response:", {k: v for k, v in result.items() if not k.startswith("_")})

    item["last_posted_at"] = datetime.now(timezone.utc).isoformat()
    item["times_posted"] = item.get("times_posted", 0) + 1
    save_queue(queue)


if __name__ == "__main__":
    main()
