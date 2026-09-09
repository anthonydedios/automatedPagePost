"""
Posts the next queued item to your Facebook Page's timeline.

Reads posts/queue.json, finds the item that has been waiting longest
(or has never been posted), publishes it to the Page via the Graph API,
then updates the queue file so the same item won't go out again right away.

Required environment variables (set as GitHub Secrets):
  FB_PAGE_ID             - your Facebook Page's numeric ID
  FB_PAGE_ACCESS_TOKEN   - a long-lived Page access token
"""

import json
import os
import sys
from datetime import datetime, timezone

import requests

QUEUE_PATH = "posts/queue.json"
GRAPH_API_VERSION = "v20.0"


def load_queue():
    with open(QUEUE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_queue(queue):
    with open(QUEUE_PATH, "w", encoding="utf-8") as f:
        json.dump(queue, f, indent=2, ensure_ascii=False)


def pick_next_item(queue):
    """Pick the item that was posted longest ago (or never)."""
    def sort_key(item):
        return item.get("last_posted_at") or ""
    active_items = [i for i in queue if i.get("active", True)]
    if not active_items:
        return None
    active_items.sort(key=sort_key)
    return active_items[0]


def post_to_page(page_id, access_token, item):
    caption = item["caption"]
    image_url = item.get("image_url")

    if image_url:
        endpoint = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{page_id}/photos"
        payload = {
            "url": image_url,
            "caption": caption,
            "access_token": access_token,
        }
    else:
        endpoint = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{page_id}/feed"
        payload = {
            "message": caption,
            "access_token": access_token,
        }

    response = requests.post(endpoint, data=payload, timeout=30)
    if response.status_code != 200:
        print(f"Facebook API error: {response.status_code} {response.text}", file=sys.stderr)
        response.raise_for_status()
    return response.json()


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

    print(f"Posting item id={item['id']}: {item['caption'][:60]}...")
    result = post_to_page(page_id, access_token, item)
    print("Facebook API response:", result)

    item["last_posted_at"] = datetime.now(timezone.utc).isoformat()
    item["times_posted"] = item.get("times_posted", 0) + 1
    save_queue(queue)


if __name__ == "__main__":
    main()
