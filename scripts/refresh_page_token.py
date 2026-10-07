"""
Exchanges a short-lived Facebook User access token for a long-lived Page
access token, then writes that Page token directly into this repo's
FB_PAGE_ACCESS_TOKEN GitHub Actions secret - no manual copy/paste needed.

Required environment variables:
  SHORT_LIVED_TOKEN   - the short-lived User token you just generated in
                        Graph API Explorer
  FB_APP_ID           - from App Dashboard -> Settings -> Basic
  FB_APP_SECRET       - same page, "Show" button
  FB_PAGE_ID          - your Page's numeric ID
  GH_PAT              - a GitHub Personal Access Token with "repo" scope,
                        used only to update this repo's own secret
  GITHUB_REPOSITORY   - auto-provided by GitHub Actions ("owner/repo")
"""

import base64
import os
import sys

import requests
from nacl import encoding, public

GRAPH_API_VERSION = "v20.0"


def exchange_for_long_lived_user_token(app_id, app_secret, short_lived_token):
    url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/oauth/access_token"
    params = {
        "grant_type": "fb_exchange_token",
        "client_id": app_id,
        "client_secret": app_secret,
        "fb_exchange_token": short_lived_token,
    }
    response = requests.get(url, params=params, timeout=30)
    if response.status_code != 200:
        print(f"Error exchanging for long-lived user token: {response.text}", file=sys.stderr)
        response.raise_for_status()
    return response.json()["access_token"]


def get_page_access_token(long_lived_user_token, page_id):
    url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/me/accounts"
    response = requests.get(url, params={"access_token": long_lived_user_token}, timeout=30)
    if response.status_code != 200:
        print(f"Error fetching /me/accounts: {response.text}", file=sys.stderr)
        response.raise_for_status()

    pages = response.json().get("data", [])
    for page in pages:
        if page.get("id") == str(page_id):
            return page["access_token"]

    print(f"Page ID {page_id} not found in /me/accounts response. "
          f"Pages returned: {[p.get('id') for p in pages]}", file=sys.stderr)
    sys.exit(1)


def encrypt_secret(public_key_b64, secret_value):
    public_key = public.PublicKey(public_key_b64.encode("utf-8"), encoding.Base64Encoder())
    sealed_box = public.SealedBox(public_key)
    encrypted = sealed_box.encrypt(secret_value.encode("utf-8"))
    return base64.b64encode(encrypted).decode("utf-8")


def update_github_secret(repo, gh_pat, secret_name, secret_value):
    headers = {
        "Authorization": f"Bearer {gh_pat}",
        "Accept": "application/vnd.github+json",
    }

    key_resp = requests.get(
        f"https://api.github.com/repos/{repo}/actions/secrets/public-key",
        headers=headers, timeout=30,
    )
    if key_resp.status_code != 200:
        print(f"Error fetching repo public key: {key_resp.text}", file=sys.stderr)
        key_resp.raise_for_status()
    key_data = key_resp.json()

    encrypted_value = encrypt_secret(key_data["key"], secret_value)

    put_resp = requests.put(
        f"https://api.github.com/repos/{repo}/actions/secrets/{secret_name}",
        headers=headers, timeout=30,
        json={"encrypted_value": encrypted_value, "key_id": key_data["key_id"]},
    )
    if put_resp.status_code not in (201, 204):
        print(f"Error updating secret {secret_name}: {put_resp.text}", file=sys.stderr)
        put_resp.raise_for_status()


def main():
    short_lived_token = os.environ.get("SHORT_LIVED_TOKEN")
    app_id = os.environ.get("FB_APP_ID")
    app_secret = os.environ.get("FB_APP_SECRET")
    page_id = os.environ.get("FB_PAGE_ID")
    gh_pat = os.environ.get("GH_PAT")
    repo = os.environ.get("GITHUB_REPOSITORY")

    missing = [name for name, val in [
        ("SHORT_LIVED_TOKEN", short_lived_token), ("FB_APP_ID", app_id),
        ("FB_APP_SECRET", app_secret), ("FB_PAGE_ID", page_id),
        ("GH_PAT", gh_pat), ("GITHUB_REPOSITORY", repo),
    ] if not val]
    if missing:
        print(f"Missing required environment variables: {', '.join(missing)}", file=sys.stderr)
        sys.exit(1)

    print("Exchanging short-lived token for a long-lived user token...")
    long_lived_user_token = exchange_for_long_lived_user_token(app_id, app_secret, short_lived_token)
    # Prevent accidental log exposure if anything below ever echoes it.
    print(f"::add-mask::{long_lived_user_token}")

    print(f"Fetching the Page access token for Page ID {page_id}...")
    page_token = get_page_access_token(long_lived_user_token, page_id)
    print(f"::add-mask::{page_token}")

    print("Writing the new Page token into the FB_PAGE_ACCESS_TOKEN secret...")
    update_github_secret(repo, gh_pat, "FB_PAGE_ACCESS_TOKEN", page_token)

    print("Done. FB_PAGE_ACCESS_TOKEN has been updated - no copy/paste needed.")


if __name__ == "__main__":
    main()
