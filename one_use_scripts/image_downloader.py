import os
import sys
import requests
from bs4 import BeautifulSoup

# ─── CONFIG ───────────────────────────────────────────────────────────────────
BASE_URL      = "https://camelotcg.cl/producto"
OUTPUT_DIR    = os.path.expanduser(r"E:\Scripts\deckbuilder\card_images\liber_dominus")
LOG_PATH      = os.path.join(OUTPUT_DIR, "skipped_slugs.txt")

# ─── HELPERS ───────────────────────────────────────────────────────────────────
def extract_slug(line):
    """
    Given a line like "- julio-cesar" (possibly with leading spaces), return "julio-cesar".
    If it doesn’t start with "-", returns None.
    """
    line = line.strip()
    if not line.startswith("-"):
        return None
    slug = line.lstrip("-").strip()
    return slug if slug else None

def download_image(img_url, target_path):
    """
    Download a single image URL into target_path via HTTP.
    """
    try:
        resp = requests.get(img_url, stream=True, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        print(f"    ✘ Failed to download {img_url}: {e}")
        return False

    with open(target_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)
    return True

def log_skipped(slug, reason):
    """
    Append the slug and reason to LOG_PATH.
    """
    with open(LOG_PATH, "a", encoding="utf-8") as logfile:
        logfile.write(f"{slug}    # {reason}\n")

def find_main_image_tag(soup):
    """
    Try a cascade of selectors to find the most likely <img> for the main product card.
    Returns a tuple (img_tag, method) or (None, None) if nothing obvious was found.
    """

    # 1) WooCommerce “product gallery” single image:
    #    <div class="woocommerce-product-gallery__image"> <img ...> </div>
    selector_list = [
        ("product-gallery__image",       "div.woocommerce-product-gallery__image img"),
        ("gallery-wrapper",              "figure.woocommerce-product-gallery__wrapper img"),
        ("wp-post-image",                "img.wp-post-image"),
        ("first-img-inside-product-div", "div.product img"),  # falls back to any <img> inside a div.product
    ]

    for method_name, css in selector_list:
        tag = soup.select_one(css)
        if tag and tag.get("src"):
            return tag, method_name

    # 2) If none of the above, pick the <img> with the largest “width” attribute (if present)
    best = None
    best_size = 0
    for img in soup.find_all("img"):
        src = img.get("src")
        if not src:
            continue
        # Try to parse “width” or “height” from the tag’s attributes (if available)
        w = img.get("width")
        h = img.get("height")
        # Use whichever numeric attribute we can find; default to 0 if missing or non-numeric
        size = 0
        try:
            size = int(w) if w else (int(h) if h else 0)
        except:
            size = 0
        if size > best_size:
            best = img
            best_size = size

    if best:
        return best, "largest-by-attribute"

    return None, None

# ─── MAIN LOGIC ────────────────────────────────────────────────────────────────
def main(md_filepath):
    if not os.path.isfile(md_filepath):
        print(f"Error: File not found → {md_filepath}")
        return 1

    # 1) Ensure output folder exists & clear previous log
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    open(LOG_PATH, "w", encoding="utf-8").close()

    # 2) Read slugs from .md
    with open(md_filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()

    slugs = []
    for raw in lines:
        slug = extract_slug(raw)
        if slug:
            slugs.append(slug)

    if not slugs:
        print("No valid slugs (lines beginning with “-”) found in your .md file.")
        return 1

    total = len(slugs)
    print(f"Starting download of {total} possible images…")
    print(f"Any skipped slug will be appended to:\n  {LOG_PATH}\n")

    for idx, slug in enumerate(slugs, start=1):
        product_url = f"{BASE_URL}/{slug}"
        print(f"[{idx}/{total}] Checking URL: {product_url}")

        # ─── 1) Fetch the product page ─────────────────────────────────────────
        try:
            resp = requests.get(product_url, timeout=10)
        except Exception as e:
            print(f"  ✘ Network error for {product_url}: {e}")
            log_skipped(slug, "network error")
            continue

        if resp.status_code == 404:
            print(f"  – Page not found (404). Skipping “{slug}”.")
            log_skipped(slug, "404 Not Found")
            continue
        if resp.status_code != 200:
            print(f"  – Unexpected status {resp.status_code}. Skipping “{slug}”.")
            log_skipped(slug, f"HTTP {resp.status_code}")
            continue

        # ─── 2) Parse HTML → find the main <img> ────────────────────────────────
        soup = BeautifulSoup(resp.text, "html.parser")
        img_tag, method = find_main_image_tag(soup)

        if not img_tag or not img_tag.get("src"):
            print("  – No main <img> detected on page. Skipping “{}”.".format(slug))
            log_skipped(slug, "no main <img> found")
            continue

        img_url = img_tag["src"]
        # Convert relative URLs to absolute, if needed
        if img_url.startswith("//"):
            img_url = "https:" + img_url
        elif img_url.startswith("/"):
            img_url = "https://camelotcg.cl" + img_url

        print(f"  • Found image via [{method}]: {img_url}")

        # ─── 3) Build local filename and check for existing file ─────────────────
        ext = os.path.splitext(img_url)[1].split("?")[0]
        if ext.lower() not in [".jpg", ".jpeg", ".png", ".gif", ".webp"]:
            ext = ".jpg"
        filename = f"{slug}{ext}"
        outpath = os.path.join(OUTPUT_DIR, filename)

        if os.path.exists(outpath):
            print(f"  • Already downloaded → {filename}. Skipping.")
            continue

        # ─── 4) Download the image ───────────────────────────────────────────────
        print(f"  • Downloading image: {img_url}")
        success = download_image(img_url, outpath)
        if success:
            print(f"    ✔ Saved → {filename}")
        else:
            print(f"    ✘ Failed to save “{filename}”. Logging and continuing.")
            log_skipped(slug, "image download failed")

    print("\nAll done.")
    print(f"A list of skipped slugs is in:\n  {LOG_PATH}")
    return 0

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python download_camelot_images.py path\\to\\card_list.md")
        sys.exit(1)
    sys.exit(main(sys.argv[1]))
