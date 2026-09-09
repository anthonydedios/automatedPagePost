"""
Generates a batch of ready-to-copy caption variations for manual posting
into Facebook Groups you're a member of.

Posting the exact same text into every group is what gets accounts flagged
as spam by group admins - this script gives you a few natural variations
per product so each group gets slightly different wording.

Input:  products.csv  (columns: name, price, description, link)
Output: captions_output.txt
"""

import csv
import sys

INPUT_CSV = "products.csv"
OUTPUT_FILE = "captions_output.txt"

OPENERS = [
    "New arrival! 🛍️",
    "Just in stock 👇",
    "Fresh drop today ✨",
    "Grab yours before it's gone!",
]

CLOSERS = [
    "DM us to order 💌",
    "Message our page to reserve yours!",
    "Comment 'MINE' to claim this 🙌",
    "Order now while stocks last!",
]

HASHTAG_SETS = [
    "#ContactClosetDeEmilia #OOTD #ClothingPH",
    "#AffordableFashionPH #ClosetSale #StyleFinds",
    "#PreLovedOrNew #FashionDeals #ShopPH",
]


def generate_variants(name, price, description, link):
    variants = []
    for i in range(3):
        opener = OPENERS[i % len(OPENERS)]
        closer = CLOSERS[i % len(CLOSERS)]
        tags = HASHTAG_SETS[i % len(HASHTAG_SETS)]
        price_line = f"Price: {price}" if price else ""
        link_line = f"Link: {link}" if link else ""
        text = f"{opener}\n{name}\n{description}\n{price_line}\n{closer}\n{tags}\n{link_line}".strip()
        variants.append(text)
    return variants


def main():
    try:
        with open(INPUT_CSV, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
    except FileNotFoundError:
        print(f"Could not find {INPUT_CSV}. Create it with columns: name,price,description,link", file=sys.stderr)
        sys.exit(1)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as out:
        for row in rows:
            out.write(f"=== {row['name']} ===\n\n")
            variants = generate_variants(
                row.get("name", ""),
                row.get("price", ""),
                row.get("description", ""),
                row.get("link", ""),
            )
            for idx, v in enumerate(variants, 1):
                out.write(f"--- Variant {idx} ---\n{v}\n\n")
            out.write("\n")

    print(f"Done. Open {OUTPUT_FILE} and copy/paste variants when posting manually to different groups.")


if __name__ == "__main__":
    main()
