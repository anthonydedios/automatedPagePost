# Closet De Emilia - Facebook Page Auto Poster

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

### 1. Generate long term token via github actions

GENERATE SHORT TERM TOKEN LINK
https://developers.facebook.com/tools/explorer/

### 2. Add photos under photos folder, then update the post_to_facebook.py captions and add new entry in PRODUCT variable (line 98)
