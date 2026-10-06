"""
Posts a random selection of photos from a local folder to your Facebook
Page as ONE multi-photo post, with a fixed caption used every time.

How it works:
  1. Every image file inside PHOTOS_DIR is uploaded to Facebook as an
     "unpublished" photo (published=false), sent as actual file bytes
     (not a URL) - this works for local repo files.
  2. The order the photos are uploaded/attached in is shuffled randomly
     on every run, so the post doesn't look identical each time.
  3. One feed post is created attaching all of those uploaded photos,
     with STATIC_CAPTION as the post's message - every run uses the
     exact same caption text.

Required environment variables (set as GitHub Secrets):
  FB_PAGE_ID             - your Facebook Page's numeric ID
  FB_PAGE_ACCESS_TOKEN   - a long-lived Page access token

Optional environment variable:
  PHOTOS_DIR             - overrides which local folder to post from
                            (defaults to photos/duster)
"""

import mimetypes
import os
import random
import sys

import requests

GRAPH_API_VERSION = "v20.0"
DEFAULT_PHOTOS_DIR = "photos/duster"
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}

STATIC_CAPTION = """NEW Duster Sleeve | 180 php | Freesize | Challis Korean

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


def list_photos(photos_dir):
    if not os.path.isdir(photos_dir):
        print(f"Photos folder not found: {photos_dir}", file=sys.stderr)
        sys.exit(1)

    files = [
        os.path.join(photos_dir, f)
        for f in os.listdir(photos_dir)
        if os.path.splitext(f)[1].lower() in ALLOWED_EXTENSIONS
    ]
    random.shuffle(files)
    return files


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


def post_photos(page_id, access_token, photos_dir):
    photo_paths = list_photos(photos_dir)

    if not photo_paths:
        return None, 0

    photo_ids = [
        upload_unpublished_photo(page_id, access_token, path)
        for path in photo_paths
    ]

    endpoint = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{page_id}/feed"
    payload = {"message": STATIC_CAPTION, "access_token": access_token}
    for i, photo_id in enumerate(photo_ids):
        payload[f"attached_media[{i}]"] = f'{{"media_fbid":"{photo_id}"}}'

    response = requests.post(endpoint, data=payload, timeout=30)
    if response.status_code != 200:
        print(f"Facebook API error (feed post): {response.status_code} {response.text}", file=sys.stderr)
        response.raise_for_status()

    return response.json(), len(photo_ids)


def main():
    page_id = os.environ.get("FB_PAGE_ID")
    access_token = os.environ.get("FB_PAGE_ACCESS_TOKEN")
    photos_dir = os.environ.get("PHOTOS_DIR", DEFAULT_PHOTOS_DIR)

    if not page_id or not access_token:
        print("Missing FB_PAGE_ID or FB_PAGE_ACCESS_TOKEN environment variables.", file=sys.stderr)
        sys.exit(1)

    result, photo_count = post_photos(page_id, access_token, photos_dir)

    if result is None:
        print(f"No image files found in {photos_dir}. Nothing to post.")
        return

    print(f"Posted {photo_count} photo(s) from {photos_dir} in random order.")
    print("Facebook API response:", result)


if __name__ == "__main__":
    main()
