# Contact Closet De Emilia - Facebook Page Auto Poster

Automatically posts items from `posts/queue.json` to your **own Facebook Page**
on a schedule, using GitHub Actions + the Facebook Graph API.

This does **not** and cannot post into Facebook Groups you don't administer -
Facebook's API has no endpoint for that, and automating it would risk your
account being banned. See `scripts/generate_captions.py` below for a safe way
to speed up manual group posting instead.

## 1. Get your Page ID

1. Go to your Page: https://www.facebook.com/ContactClosetDeEmilia
2. Go to **Settings > Page transparency**, or open
   `https://www.facebook.com/ContactClosetDeEmilia/about` - your numeric Page
   ID is shown there. You can also find it via
   https://developers.facebook.com/tools/explorer/ (see step 2).

## 2. Create a Facebook App + get a long-lived Page access token

1. Go to https://developers.facebook.com/apps and create a new App
   (type: "Business").
2. Add the **Facebook Login** and **Pages API** products to the app.
3. Go to https://developers.facebook.com/tools/explorer/
   - Select your app from the dropdown.
   - Click **Get Token > Get User Access Token**.
   - Check these permissions: `pages_manage_posts`, `pages_read_engagement`,
     `pages_show_list`.
   - Generate the token.
4. Exchange it for a **long-lived user token** (60 days) by calling:
   ```
   https://graph.facebook.com/v20.0/oauth/access_token?
     grant_type=fb_exchange_token&
     client_id=YOUR_APP_ID&
     client_secret=YOUR_APP_SECRET&
     fb_exchange_token=SHORT_LIVED_USER_TOKEN
   ```
5. Use that long-lived user token to get your **Page access token** (this one
   does not expire as long as it's used regularly):
   ```
   https://graph.facebook.com/v20.0/me/accounts?access_token=LONG_LIVED_USER_TOKEN
   ```
   This returns a list of Pages you manage, each with its own
   `access_token` - copy the one for Contact Closet De Emilia.

> Note: for a Page tied to a personal profile (not a verified Business), Meta
> may still require periodic re-authentication. If the token stops working
> after a while, repeat steps 3-5 to get a fresh one.

## 3. Push this code to a new GitHub repo

```bash
git init
git add .
git commit -m "Set up Facebook Page auto poster"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
git push -u origin main
```

## 4. Add your secrets in GitHub

In your repo: **Settings > Secrets and variables > Actions > New repository secret**

| Secret name | Value |
|---|---|
| `FB_PAGE_ID` | Your Page's numeric ID from step 1 |
| `FB_PAGE_ACCESS_TOKEN` | The Page access token from step 2 |

## 5. Fill in your real posts

Edit `posts/queue.json` - it's your whole active catalog. **Every run posts
ALL active items together, as one single Facebook post** with every photo
attached (Facebook's multi-photo/album post format), in shuffled order.
Add one object per product you're selling, e.g.:

```json
{
  "id": "item-002",
  "name": "Denim Jacket",
  "price": "PHP 650",
  "description": "Oversized fit, great for layering, size M",
  "image_urls": [
    "https://your-image-host.com/jacket-front.jpg",
    "https://your-image-host.com/jacket-back.jpg"
  ],
  "active": true,
  "last_posted_at": null,
  "times_posted": 0
}
```

Fill in `name`, `price`, and `description` per item - `scripts/caption_engine.py`
uses those to write a fresh, differently-worded caption **for that item's
photo(s) individually**, every run. If you leave those blank, it falls back
to wrapping the old `caption` field with randomized phrasing instead.

`image_urls` is a **list** - if you have several photos of the *same*
product (front/back/detail shots), put them all under that one item's list.
If a photo doesn't clearly show a product on its own (has no obvious front
shot, etc.), just leave it as its own single-photo item.

Each URL must be **publicly reachable** (Imgur, your own hosting, a GitHub
raw file link, etc.) - Facebook fetches the image from that URL directly.

### How one run works

`scripts/post_to_facebook.py` does the following each time it runs:

1. Collects every photo from every `"active": true` item, shuffles the
   order.
2. Uploads each photo to the Page as "unpublished" (not visible yet), each
   with its own randomized caption built from that item's `name`/`price`/
   `description`.
3. Creates **one** feed post attaching all of those photos together, with a
   single overall randomized caption on top (a "new arrivals" style intro +
   CTA + hashtags).
4. Marks every included item's `last_posted_at`/`times_posted` in the queue.

**Two things to be aware of with this "everything in one post" approach:**

- **Facebook may cap how many photos one post can hold.** There's no
  guaranteed number - if the API rejects the request for having too many
  attached photos, you'll see the error in the Actions run log, and you'll
  need to split your catalog across a few smaller `queue.json`-driven runs
  instead of one giant one.
- **The cron schedule still runs hourly** (`.github/workflows/facebook-auto-post.yml`).
  Since every run now posts your *entire* active catalog as one post, an
  hourly schedule means a near-duplicate 56-photo post every hour. You'll
  likely want to change the cron to something much less frequent (daily or
  a few times a week) - edit the `cron:` line in the workflow file.

## 6. Test it

Go to the **Actions** tab in your repo > "Facebook Page Auto Poster" >
**Run workflow** to trigger it manually and confirm a post appears on your
Page. Once that works, it will run automatically every hour via the cron
schedule in `.github/workflows/facebook-auto-post.yml`.

## Bonus: caption generator for manual group posting

Since groups can't be automated, use this to prep varied captions fast so
manual posting takes seconds per group:

```bash
pip install -r requirements.txt   # only needs csv, which is built-in
python scripts/generate_captions.py
```

Fill in `products.csv` with your items, run the script, then open
`captions_output.txt` - it has 3 differently-worded caption variants per
product, ready to copy/paste. Using different wording per group also helps
you avoid getting flagged as a spam duplicate poster by group admins.
