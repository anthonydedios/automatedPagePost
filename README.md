# Contact Closet De Emilia - Facebook Page Auto Poster

Posts a random selection of local photos to your own Facebook Page on a
schedule, using GitHub Actions + the Facebook Graph API, with one fixed
caption used on every post.

## How it works

- Drop product photos into `photos/duster/` (jpg/png/webp).
- Every run of the workflow:
  1. Lists all images in `photos/duster/`, shuffled into random order.
  2. Uploads each as an unpublished photo (actual file bytes, not a URL).
  3. Publishes one post attaching all of them, using the caption hardcoded
     in `scripts/post_to_facebook.py` (`STATIC_CAPTION`).
- The workflow is scheduled via cron in
  `.github/workflows/facebook-auto-post.yml` - edit the `cron:` line to
  change how often it posts.

To post from a different folder (e.g. a new product line), either rename
the folder and update `DEFAULT_PHOTOS_DIR` in
`scripts/post_to_facebook.py`, or set a `PHOTOS_DIR` repository/workflow
variable without touching code.

To change the caption, edit the `STATIC_CAPTION` string directly in
`scripts/post_to_facebook.py`.

## Setup

### 1. Get your Page ID and a long-lived Page access token
See the token-exchange steps you already have - in short:
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
photos/duster/duster1.jpg
photos/duster/duster2.jpg
photos/duster/duster3.jpg
```
Add/remove files here any time - the script always picks up whatever is
currently in the folder.

### 4. Test it
Actions tab -> "Facebook Page Auto Poster" -> **Run workflow**. Check your
Page afterward to confirm the post appeared with all photos and the
caption.

### 5. Visibility note
If posts only show up to you and not the public, that's Facebook's
`pages_manage_posts` Standard Access restriction, not a bug in this
script - see the App Review / Advanced Access notes you already have for
how to fix that separately.

## Bonus: caption generator for manual group posting

`scripts/generate_captions.py` is unrelated to the auto-poster above - it
helps you write varied captions fast for manually sharing into Facebook
Groups (which can't be automated). See that file's docstring for usage.
