# Contact Closet De Emilia - Facebook Page Auto Poster

Rotates through product folders on each scheduled run, posting a random
selection of that product's local photos as one multi-photo post, with a
fixed caption per product.

## How the rotation works

- `scripts/post_to_facebook.py` has a `PRODUCTS` list, in order:
  1. `duster` -> `photos/duster/`
  2. `ternosleeve` -> `photos/ternosleeve/`
  3. `smockdress` -> `photos/smockdress/`
- `posts/rotation_state.json` remembers which product was posted last.
  Each run moves to the next one in the list, wrapping back to `duster`
  after `smockdress`.
- The workflow commits the updated `posts/rotation_state.json` back to
  the repo after every run - this is what lets the rotation survive
  between separate GitHub Actions runs (each run starts from a fresh
  checkout, so without this the script would have no memory of what
  posted last).

### Why only 4 photos per post

Facebook's Graph API hard-caps a multi-photo feed post at **4 photos** -
this isn't adjustable. To still get every photo in a folder shown over
time instead of the same few repeating, each product keeps its own
shuffled "deck" of filenames inside `posts/rotation_state.json`
(`decks.duster`, `decks.ternosleeve`, `decks.smockdress`). Every time
it's that product's turn, the next 4 photos come off its deck; once a
deck runs out, it reshuffles from whatever's currently in that folder.
So with e.g. 57 duster photos, duster's turn comes up roughly every 3
rotations, and it takes about 14-15 of its turns to cycle through every
photo once before any repeat.

**To add another product to the rotation:** add its caption as a new
string constant, then add `{"key": "...", "dir": "photos/your-folder",
"caption": YOUR_CAPTION}` to the `PRODUCTS` list, in whatever position
you want it in the cycle.

**To change a caption:** edit the relevant `*_CAPTION` string directly in
`scripts/post_to_facebook.py`.

**To reset the rotation** (e.g. force the next run to post duster again):
edit `posts/rotation_state.json` to `{"last_index": -1}` and commit.

## Setup

### 1. Get your Page ID and a long-lived Page access token
1. Generate a short-lived User token in Graph API Explorer
   (`pages_show_list`, `pages_read_engagement`, `pages_manage_posts`).
2. Exchange it for a long-lived User token via `oauth/access_token`.
3. Call `/me/accounts` with that long-lived User token to get your Page's
   own long-lived access token.

### 2. Add GitHub secrets
Repo -> Settings -> Secrets and variables -> Actions:

| Secret name | Value |
|---|---|
| `FB_PAGE_ID` | Your Page's numeric ID |
| `FB_PAGE_ACCESS_TOKEN` | The Page access token from step 1 |

### 3. Confirm your photos are in place
```
photos/duster/...
photos/ternosleeve/...
photos/smockdress/...
```
Add/remove files in any of these folders any time - the script always
picks up whatever is currently there when it's that product's turn.

### 4. Test it
Actions tab -> "Facebook Page Auto Poster" -> **Run workflow**, three
times in a row, to confirm it cycles duster -> ternosleeve -> smockdress
with the right photos and caption each time.

### 5. Visibility note
If posts only show up to you and not the public, that's Facebook's
`pages_manage_posts` Standard Access restriction, not a bug in this
script - see the App Review / Advanced Access notes you already have for
how to fix that separately.

## Bonus: caption generator for manual group posting

`scripts/generate_captions.py` is unrelated to the auto-poster above - it
helps you write varied captions fast for manually sharing into Facebook
Groups (which can't be automated). See that file's docstring for usage.

## Refreshing the Page token without manual copy/paste

The `Refresh Facebook Page Token` workflow automates the whole token
exchange: give it a short-lived User token, and it writes the resulting
long-lived Page token straight into the `FB_PAGE_ACCESS_TOKEN` secret.

**One-time setup:**
1. Add secrets `FB_APP_ID` and `FB_APP_SECRET` (from App Dashboard ->
   Settings -> Basic).
2. Add a secret `GH_PAT` - a GitHub Personal Access Token (classic) with
   `repo` scope, from https://github.com/settings/tokens. This is what
   authorizes the workflow to update this repo's own secrets; it has
   nothing to do with Facebook.

**To refresh the token whenever it expires:**
1. Get a fresh short-lived User token from Graph API Explorer
   (`pages_show_list`, `pages_read_engagement`, `pages_manage_posts`).
2. Actions tab -> "Refresh Facebook Page Token" -> **Run workflow** ->
   paste the short-lived token into the input box -> Run.
3. The run exchanges it, looks up the Page token for `FB_PAGE_ID`, and
   overwrites the `FB_PAGE_ACCESS_TOKEN` secret directly - the token
   itself is never printed in the logs (masked), and nothing needs
   copying.

## Posting Reels (slideshow videos)

A separate workflow, `Facebook Reel Poster`, builds a short vertical
slideshow video from product photos and publishes it as a Facebook Reel.

**How it works:**
- `scripts/generate_reel.py` uses ffmpeg to turn a handful of photos into
  a 1080x1920 (9:16) video, ~2.5 seconds per photo with a slow zoom, and
  concatenates them into one MP4.
- `scripts/post_reel.py` picks the next product in the same
  duster -> ternosleeve -> smockdress rotation (tracked independently in
  `posts/reel_rotation_state.json`, so it doesn't interfere with the
  regular photo-post rotation), deals 5 never-repeated-until-exhausted
  photos from that product's deck, generates the video, and uploads it
  through Facebook's **Reels Publishing API** - a separate 3-step flow
  (start session -> upload video bytes -> finish & publish) from the
  regular photo/feed endpoint.
- The product's existing caption (same ones used for photo posts) is
  used as the Reel's description.

**Extra requirement:** your Page access token needs
`pages_manage_engagement` in addition to `pages_manage_posts` - add that
scope next time you generate/refresh a token in Graph API Explorer (or
through the `Refresh Facebook Page Token` workflow's exchange call).

**Schedule:** runs once a day by default (`cron: '0 0 * * *'` = 8am
Manila time) - edit `.github/workflows/facebook-reel-poster.yml` to
change the cadence, same as the photo-post workflow.

**To change how many photos per reel or how long each shows:** edit
`PHOTOS_PER_REEL` in `scripts/post_reel.py`, or `SECONDS_PER_PHOTO` in
`scripts/generate_reel.py`. Facebook Reels must be 3-90 seconds total.

**Background music:** drop royalty-free audio files into the `audio/`
folder and the generator automatically picks one at random, loops or
trims it to exactly match the video's length, and fades it out in the
last second. If `audio/` is empty, reels are generated silently instead
- no error, just no sound. See `audio/README.md` for where to legally
get free tracks (Meta's own Sound Collection is the safest option).
Only use audio you actually have rights to - Facebook's copyright
system actively scans Reels audio.
