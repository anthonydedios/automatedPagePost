"""
Generates a fresh, naturally-varied caption for each post instead of reusing
one static line. Every call mixes different openers, phrasing, price framing,
CTAs, and hashtags in a different order/combination, so posts don't read like
a template being filled in - which is what makes repeated posts look spammy
or AI-generated.

Used by post_to_facebook.py at post time (not stored ahead of time), so even
if the same item gets reposted weeks later, the wording won't be identical.
"""

import random
import re

_HASHTAG_RE = re.compile(r"#\S+")


def _strip_hashtags(text):
    return re.sub(r"\s{2,}", " ", _HASHTAG_RE.sub("", text)).strip(" ,\n")


OPENERS = [
    "Sis, may bago na naman kami 🛍️",
    "Okay this one's a must-see 👀",
    "New stock alert!",
    "Look what just came in ✨",
    "Bagong drop na 'to!",
    "Hindi namin ma-resist i-post 'to, ang ganda talaga 😍",
    "Okay bestie, sulit na sulit itong isang ito",
    "Straight from our latest haul 👇",
    "This just landed sa closet namin",
    "Warning: baka ma-in love ka dito 👀",
    "Fresh pick for today",
    "Quick post bago maubos 'to",
    "Kada linggo may bago, ito na naman 🙌",
    "Todo ganda, todo sulit",
    "Isa 'to sa mga paborito namin ngayong linggo",
]

# {name} and {description} may or may not both be present - templates below
# are written so they still read naturally if description is empty.
HOOKS = [
    "{name} - {description}",
    "Meet the {name}. {description}",
    "{description} Say hi to the {name} 👋",
    "Sobrang bagay nito for everyday wear: {name}. {description}",
    "{name} lovers, this one's for you. {description}",
    "{description} Perfect kung ganito talaga ang hanap mo.",
    "Introducing: {name}. {description}",
]

HOOKS_NO_DESC = [
    "Check out our {name}",
    "{name} is now up for grabs",
    "Sobrang bet namin itong {name}",
    "{name} - ready to ship na 'to",
    "One of our best sellers, {name}",
]

PRICE_PHRASES = [
    "Yours for just {price}",
    "Tag: {price} lang!",
    "Grab it for {price}",
    "{price} only, sulit na sulit",
    "Presyo: {price}",
    "On sale at {price}",
    "Steal deal at {price}",
    "Investment piece for {price}",
]

CTAS = [
    "Comment 'MINE' or DM us to claim it 💌",
    "Order now before someone else grabs it!",
    "Message us to reserve yours 🙌",
    "DM na bago maubos!",
    "First to message, first to get it - order na 🛍️",
    "Tara, order na?",
    "Send us a message and we'll take it from there 💬",
    "Reserve yours today, limited lang ang stock",
    "Available na for order, DM lang po",
]

HASHTAG_POOL = [
    "#ContactClosetDeEmilia", "#OOTD", "#ClothingPH", "#AffordableFashionPH",
    "#ClosetSale", "#StyleFinds", "#PreLovedOrNew", "#FashionDeals",
    "#ShopPH", "#OnlineShopPH", "#FashionFinds", "#SuludPH", "#OOTDPH",
    "#ThriftPH", "#WardrobeGoals", "#StyleInspo",
]

_last_signature = {}


def _fill(template, name, description, price):
    return (
        template.format(name=name, description=description, price=price)
        .replace("  ", " ")
        .strip()
    )


def _build_hook(name, description):
    description = (description or "").strip()
    name = (name or "").strip()
    if not name and not description:
        return ""
    if description and name:
        template = random.choice(HOOKS)
        return _fill(template, name, description, "")
    if name:
        template = random.choice(HOOKS_NO_DESC)
        return _fill(template, name, "", "")
    return description


def generate_caption(item):
    """
    Build one randomized caption for a queue item.

    item may have: name, description, price, caption (legacy fallback),
    link, id. Only `id` is required.
    """
    name = (item.get("name") or "").strip()
    description = (item.get("description") or "").strip()
    price = (item.get("price") or "").strip()
    link = (item.get("link") or "").strip()
    legacy_caption = (item.get("caption") or "").strip()

    parts = []

    # If we don't have structured product fields, fall back to wrapping the
    # legacy static caption with fresh opener/CTA/hashtags instead of
    # reposting it verbatim.
    hook = _build_hook(name, description)
    if not hook and legacy_caption:
        hook = _strip_hashtags(legacy_caption)

    opener = random.choice(OPENERS)
    parts.append(opener)

    if hook:
        parts.append(hook)

    if price:
        parts.append(random.choice(PRICE_PHRASES).format(price=price))

    parts.append(random.choice(CTAS))

    if random.random() < 0.85:
        tag_count = random.randint(2, 4)
        tags = " ".join(random.sample(HASHTAG_POOL, k=min(tag_count, len(HASHTAG_POOL))))
        parts.append(tags)

    if link:
        parts.append(link)

    caption = "\n".join(p for p in parts if p)

    # Avoid producing the exact same text twice in a row for the same item.
    item_id = item.get("id", "")
    if _last_signature.get(item_id) == caption and legacy_caption:
        random.shuffle(parts)
        caption = "\n".join(p for p in dict.fromkeys(parts) if p)
    _last_signature[item_id] = caption

    return caption
