"""
Posts a product in rotation (duster -> ternosleeve -> smockdress -> repeat)
each run, using up to MAX_PHOTOS_PER_POST photos from that product's
folder, with a fixed caption per product.

Facebook's Graph API caps a single multi-photo feed post at 4 photos -
this is a hard platform limit, not something this script can raise. To
still get full folder coverage over time instead of repeatedly showing
the same handful, each product keeps its own shuffled "deck" of photo
filenames in posts/rotation_state.json:
  - Each run deals the next MAX_PHOTOS_PER_POST photos off that
    product's deck.
  - A photo is never dealt again until every other photo in the same
    folder has also been dealt at least once.
  - Once a product's deck is empty, it's reshuffled fresh from whatever
    files currently exist in that folder (so adding/removing photos is
    picked up automatically on the next reshuffle).

Required environment variables (set as GitHub Secrets):
  FB_PAGE_ID             - your Facebook Page's numeric ID
  FB_PAGE_ACCESS_TOKEN   - a long-lived Page access token
"""

import json
import mimetypes
import os
import random
import sys

import requests

GRAPH_API_VERSION = "v20.0"
STATE_PATH = "posts/rotation_state.json"
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
MAX_PHOTOS_PER_POST = 4  # Facebook's hard cap for attached_media in one feed post

DUSTER_CAPTION = """NEW Duster Sleeve | 180 php | Freesize | Challis Korean

Warehouse Location:
Tatala Binangonan Rizal (Near AlfaMart Tatala)

Store Locations:

- All Star Taytay Tiangge
Stall 97 and 98

- Binangonan Tiangge
Stall 19

- Tanay Tiangge

Delivery:
Lalamove, LBC or J&T

#taytay #tiangge #taytaytianggeph #taytaytianggesupplier #ternoset #terno #ternoshorts #taytaymanufacturer #challisprinted #challis #rtw #bagpipesofinstagram #Duster"""

TERNOSLEEVE_CAPTION = """NEW Terno | 150 php | Freesize | Challis Korean
Warehouse Location:
Tatala Binangonan Rizal (Near AlfaMart Tatala)
Store Locations:
- All Star Taytay Tiangge
Stall 97 and 98
- Binangonan Tiangge
Stall A-10, B-10
- Tanay Tiangge
Delivery:
Lalamove, LBC or J&T
#taytay #tiangge #taytaytianggeph #taytaytianggesupplier #ternoset #terno #ternoshorts #taytaymanufacturer #challisprinted #challis #rtw #bagpipesofinstagram #Duster"""

SMOCKDRESS_CAPTION = """NEW SMOCKED DRESS | Freesize | Challis Korean

Warehouse Location:
Tatala Binangonan Rizal (Near AlfaMart Tatala)
Store Locations:
- All Star Taytay Tiangge
Stall 97 and 98
- Binangonan Tiangge
Stall A-10, B-10
- Tanay Tiangge
Delivery:
Lalamove, LBC or J&T
#taytay #tiangge #taytaytianggeph #taytaytianggesupplier #ternoset #terno #ternoshorts #taytaymanufacturer #challisprinted #challis #rtw #bagpipesofinstagram #Duster"""

# Rotation order - add/reorder entries here to change the cycle.
PRODUCTS = [
    {"key": "duster", "dir": "photos/duster", "caption": DUSTER_CAPTION},
    {"key": "ternosleeve", "dir": "photos/ternosleeve", "caption": TERNOSLEEVE_CAPTION},
    {"key": "smockdress", "dir": "photos/smockdress", "caption": SMOCKDRESS_CAPTION},
]


def load_state():
    if not os.path.exists(STATE_PATH):
        return {"last_index": -1, "decks": {}}
    try:
        with open(STATE_PATH, "r", encoding="utf-8") as f:
            state = json.load(f)
            state.setdefault("decks", {})
            return state
    except (json.JSONDecodeError, OSError):
        return {"last_index": -1, "decks": {}}


def save_state(state):
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


def list_folder_files(photos_dir):
    if not os.path.isdir(photos_dir):
        return []
    return [
        f for f in os.listdir(photos_dir)
        if os.path.splitext(f)[1].lower() in ALLOWED_EXTENSIONS
    ]


def deal_photos(state, product):
    """
    Returns up to MAX_PHOTOS_PER_POST full file paths for this product,
    drawing from (and updating) its shuffled deck in `state`.
    """
    key = product["key"]
    deck = state["decks"].get(key, [])

    # Refill the deck if it's empty, or if it references files that no
    # longer exist (folder contents changed since last run).
    current_files = list_folder_files(product["dir"])
    if not deck or not set(deck).issubset(set(current_files)):
        deck = current_files[:]
        random.shuffle(deck)

    dealt = deck[:MAX_PHOTOS_PER_POST]
    remaining = deck[MAX_PHOTOS_PER_POST:]

    # If the deck ran out mid-deal, top up from a fresh shuffle of the
    # rest of the folder so this post still gets a full batch where
    # possible, without repeating anything already dealt this round.
    if len(dealt) < MAX_PHOTOS_PER_POST and current_files:
        leftover_pool = [f for f in current_files if f not in dealt]
        random.shuffle(leftover_pool)
        need = MAX_PHOTOS_PER_POST - len(dealt)
        top_up = leftover_pool[:need]
        dealt += top_up
        remaining = [f for f in leftover_pool[need:]]

    state["decks"][key] = remaining
    return [os.path.join(product["dir"], f) for f in dealt]


def upload_unpublished_photo(page_id, access_token, file_path):
    endpoint = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{page_id}/photos"
    mime_type = mimetypes.guess_type(file_path)[0] or "image/jpeg"

    with open(file_path, "rb") as f:
        files = {"source": (os.path.basename(file_path), f, mime_type)}
        data = {"published": "false", "access_token": access_token}
        response = requests.post(endpoint, data=data, files=files, timeout=60)

    if response.status_code != 200:
        print(f"Facebook API error (photo upload - {file_path}): "
              f"{response.status_code} {response.text}", file=sys.stderr)
        response.raise_for_status()

    return response.json()["id"]


def post_product(page_id, access_token, photo_paths, caption):
    if not photo_paths:
        return None

    photo_ids = [
        upload_unpublished_photo(page_id, access_token, path)
        for path in photo_paths
    ]

    endpoint = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{page_id}/feed"
    payload = {"message": caption, "access_token": access_token}
    for i, photo_id in enumerate(photo_ids):
        payload[f"attached_media[{i}]"] = f'{{"media_fbid":"{photo_id}"}}'

    response = requests.post(endpoint, data=payload, timeout=30)
    if response.status_code != 200:
        print(f"Facebook API error (feed post): {response.status_code} {response.text}", file=sys.stderr)
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

    print(f"Rotation: posting index={next_index} ({product['key']})")

    photo_paths = deal_photos(state, product)
    if not photo_paths:
        print(f"No image files found in {product['dir']}. Skipping without advancing rotation.")
        return

    result = post_product(page_id, access_token, photo_paths, product["caption"])

    print(f"Posted {len(photo_paths)} photo(s) from {product['dir']} ({product['key']}):")
    for p in photo_paths:
        print(f"  - {p}")
    print("Facebook API response:", result)

    deck_remaining = len(state["decks"].get(product["key"], []))
    print(f"{deck_remaining} photo(s) left in {product['key']}'s deck before it reshuffles.")

    state["last_index"] = next_index
    save_state(state)


if __name__ == "__main__":
    main()
