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


GENERATE SHORT TERM TOKEN LINK
https://developers.facebook.com/tools/explorer/
