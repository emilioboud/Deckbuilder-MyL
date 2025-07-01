#!/usr/bin/env python3
"""
Camelot-TCG & Fandom Automation Script (Four Modes)

Modes:
  1) [FULL]      Download ALL card images from a given .md file (Camelot site)
  2) [RETRY]     Re-attempt only the slugs listed in card_images/skipped_slugs.txt (Camelot site)
  3) [FETCH]     For each still_failed.txt in each subfolder under card_images, recover accented titles via API,
                 fetch and parse the Fandom infobox, output card_data.txt, and re-log any failures.
  4) [FANDOM IMG] For each still_failed.txt in each subfolder under card_images, recover accented titles via API,
                 fetch the Fandom page, find the main (largest) image on that page, and download it into the same subfolder.
                 Any slug that still fails is re-logged into still_failed.txt.
"""

import os
import sys
import requests
import urllib.parse
from bs4 import BeautifulSoup

# ─── CONFIGURATION ─────────────────────────────────────────────────────────────
BASE_URL_IMAGES    = "https://camelotcg.cl/producto"
BASE_URL_FANDOM    = "https://myl.fandom.com/es/wiki"
API_ENDPOINT       = "https://myl.fandom.com/es/api.php"

# Root directory containing card_images and its subfolders
CARD_IMAGES_DIR    = os.path.expanduser(r"E:\Scripts\deckbuilder\card_images")

# Log filenames in CARD_IMAGES_DIR
SKIPPED_LOG_NAME   = "skipped_slugs.txt"   # Option 1 logs
RETRY_LOG_NAME     = "still_failed.txt"    # Option 2 logs; overwritten by Option 3 and Option 4 in subfolders

# ─── HELPER FUNCTIONS ─────────────────────────────────────────────────────────

def extract_slugs_from_md(md_path):
    """
    Read all non-empty lines from the .md file.
    """
    slugs = []
    with open(md_path, "r", encoding="utf-8") as f:
        for raw in f:
            slug = raw.strip()
            if slug:
                slugs.append(slug)
    return slugs

def read_slugs_from_log(log_path):
    """
    Read lines like "some-slug    # reason" and return ['some-slug', ...].
    Ignores blank lines.
    """
    slugs = []
    with open(log_path, "r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line:
                continue
            slug = line.split("#", 1)[0].strip()
            if slug:
                slugs.append(slug)
    return slugs

def log_failure(slug, reason, folder_path, log_name=RETRY_LOG_NAME):
    """
    Append "slug    # reason" to <folder_path>/<log_name>.
    Creates the file if it does not exist.
    """
    path = os.path.join(folder_path, log_name)
    with open(path, "a", encoding="utf-8") as wf:
        wf.write(f"{slug}    # {reason}\n")

def download_image(img_url, target_path):
    """
    Download img_url via HTTP streaming into target_path.
    Returns True on success, False on any failure.
    """
    try:
        resp = requests.get(img_url, stream=True, timeout=15)
        resp.raise_for_status()
    except Exception:
        return False

    with open(target_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)
    return True

def find_main_image_tag(soup):
    """
    Attempt to find the main product image via known CSS selectors.
    Returns (img_tag, method_name) or (None, None).
    """
    selectors = [
        ("product-gallery__image",       "div.woocommerce-product-gallery__image img"),
        ("gallery-wrapper",              "figure.woocommerce-product-gallery__wrapper img"),
        ("wp-post-image",                "img.wp-post-image"),
        ("fallback-product-div",         "div.product img"),
    ]
    for method, css in selectors:
        tag = soup.select_one(css)
        if tag and tag.get("src"):
            return tag, method

    # Fall back to largest-by-attribute if none found
    return find_largest_image_tag(soup)

def find_largest_image_tag(soup):
    """
    Scan all <img> tags and pick the one with the largest width or height attribute.
    Returns (img_tag, "largest-by-attribute") or (None, None).
    """
    best = None
    best_size = 0
    for img in soup.find_all("img"):
        src = img.get("src")
        if not src:
            continue
        w = img.get("width")
        h = img.get("height")
        try:
            size = int(w) if w else (int(h) if h else 0)
        except:
            size = 0
        if size > best_size:
            best = img
            best_size = size

    if best and best.get("src"):
        return best, "largest-by-attribute"
    return None, None

def get_accented_title(slug_without_accents):
    """
    Query the MediaWiki API to normalize "Romulo_Y_Remo" → "Rómulo y Remo".
    Returns the accented page title (with spaces) or None if no such page exists.
    """
    parts = slug_without_accents.split("-")
    guess = "_".join(word.capitalize() for word in parts)
    params = {
        "action": "query",
        "titles": guess,
        "redirects": "",
        "format": "json"
    }
    resp = requests.get(API_ENDPOINT, params=params, timeout=10)
    data = resp.json()

    pages = data.get("query", {}).get("pages", {})
    if not pages:
        return None

    page_info = next(iter(pages.values()))
    if page_info.get("missing") is not None:
        return None

    return page_info["title"]  # e.g. "Rómulo y Remo"

def build_fandom_url(accented_title):
    """
    Given "Rómulo y Remo", return "https://myl.fandom.com/es/wiki/R%C3%B3mulo_y_Remo"
    """
    slug = accented_title.replace(" ", "_")
    return BASE_URL_FANDOM + "/" + urllib.parse.quote(slug)

def parse_card_infobox(soup):
    """
    Locate a two-column info table on a Fandom page.
    Return a dict { "Tipo": "...", "Coste de oro": "...", "Raza": "...", ... } or {}.
    """
    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        if not rows:
            continue

        good = True
        for r in rows:
            cells = r.find_all(["th", "td"])
            if len(cells) != 2:
                good = False
                break
        if not good:
            continue

        info = {}
        for r in rows:
            cells = r.find_all(["th", "td"])
            if len(cells) == 2:
                key = cells[0].get_text(strip=True)
                val = cells[1].get_text(strip=True)
                info[key] = val
        if "Tipo" in info:
            return info

    return {}

def card_info_to_array(info):
    """
    Convert info dict into the required array rules:
      - If Tipo == "Oro"                → ["Oros"]
      - If Tipo in {"Talisman","Arma","Totem"} → [cost_int, Tipo + "s"]
      - If Tipo == "Aliado"             → [cost_int, "Aliado", "Aliados", raza]
      - Else                            → [cost_int, Tipo]
    """
    tipo_raw  = info.get("Tipo", "").strip()
    coste_raw = info.get("Coste de oro", "").strip()
    raza_raw  = info.get("Raza", "").strip()

    try:
        cost_int = int("".join(ch for ch in coste_raw if ch.isdigit()))
    except:
        cost_int = coste_raw or 0

    tipo_lower = tipo_raw.lower()
    if tipo_lower == "oro":
        return ["Oros"]
    if tipo_lower in {"talisman", "arma", "totem"}:
        plural = tipo_raw.capitalize() + "s"
        return [cost_int, plural]
    if tipo_lower == "aliado":
        return [cost_int, "Aliado", "Aliados", raza_raw]
    return [cost_int, tipo_raw]

# ─── OPTION 1: Download ALL images via CSS selectors ─────────────────────────

def option_download_all():
    md_path = input("\nEnter path to your card_list.md: ").strip()
    if not os.path.isfile(md_path):
        print("❌ That .md file does not exist. Exiting.")
        return

    slugs = extract_slugs_from_md(md_path)
    if not slugs:
        print("No slugs found in that .md file. Exiting.")
        return

    os.makedirs(CARD_IMAGES_DIR, exist_ok=True)
    skipped_log = os.path.join(CARD_IMAGES_DIR, SKIPPED_LOG_NAME)
    open(skipped_log, "w", encoding="utf-8").close()

    total = len(slugs)
    print(f"\n→ Downloading {total} cards from {md_path} …")
    for idx, slug in enumerate(slugs, start=1):
        product_url = f"{BASE_URL_IMAGES}/{slug}"
        print(f"[{idx}/{total}] {slug} → {product_url}", end=" … ")

        try:
            resp = requests.get(product_url, timeout=10)
        except Exception:
            print("NETWORK ERROR")
            with open(skipped_log, "a", encoding="utf-8") as f:
                f.write(f"{slug}    # network error\n")
            continue

        if resp.status_code == 404:
            print("404 Not Found")
            with open(skipped_log, "a", encoding="utf-8") as f:
                f.write(f"{slug}    # 404 Not Found\n")
            continue
        if resp.status_code != 200:
            print(f"HTTP {resp.status_code}")
            with open(skipped_log, "a", encoding="utf-8") as f:
                f.write(f"{slug}    # HTTP {resp.status_code}\n")
            continue

        soup = BeautifulSoup(resp.text, "html.parser")
        img_tag, method = find_main_image_tag(soup)
        if not img_tag or not img_tag.get("src"):
            print("❌ no <img>")
            with open(skipped_log, "a", encoding="utf-8") as f:
                f.write(f"{slug}    # no <img> found\n")
            continue

        img_url = img_tag["src"]
        if img_url.startswith("//"):
            img_url = "https:" + img_url
        elif img_url.startswith("/"):
            img_url = "https://camelotcg.cl" + img_url

        ext = os.path.splitext(img_url)[1].split("?")[0]
        if ext.lower() not in [".jpg", ".jpeg", ".png", ".gif", ".webp"]:
            ext = ".jpg"
        fname = f"{slug}{ext}"
        outpath = os.path.join(CARD_IMAGES_DIR, fname)

        if os.path.exists(outpath):
            print(f"✅ already exists ({fname})")
            continue

        print("Downloading…", end=" ")
        ok = download_image(img_url, outpath)
        if ok:
            print(f"✔ saved as {fname}")
        else:
            print("❌ download failed")
            with open(skipped_log, "a", encoding="utf-8") as f:
                f.write(f"{slug}    # download failed\n")

    print("\nOption 1 complete.")
    print(f"Any skipped slugs are in:\n  {os.path.join(CARD_IMAGES_DIR, SKIPPED_LOG_NAME)}")

# ─── OPTION 2: Retry ONLY the slugs in skipped_slugs.txt ──────────────────────

def option_retry_skipped():
    skipped_log = os.path.join(CARD_IMAGES_DIR, SKIPPED_LOG_NAME)
    if not os.path.isfile(skipped_log):
        print(f"ERROR: Cannot find {skipped_log}. Have you run Option 1 first?")
        return

    slugs = read_slugs_from_log(skipped_log)
    if not slugs:
        print("No slugs to retry in skipped_slugs.txt. Exiting.")
        return

    retry_log = os.path.join(CARD_IMAGES_DIR, RETRY_LOG_NAME)
    open(retry_log, "w", encoding="utf-8").close()

    total = len(slugs)
    print(f"\n→ Retrying {total} slugs from {skipped_log} …")
    for idx, slug in enumerate(slugs, start=1):
        product_url = f"{BASE_URL_IMAGES}/{slug}"
        print(f"[{idx}/{total}] {slug} → {product_url}", end=" … ")

        try:
            resp = requests.get(product_url, timeout=10)
        except Exception:
            print("NETWORK ERROR")
            log_failure(slug, "network error", CARD_IMAGES_DIR)
            continue

        if resp.status_code == 404:
            print("404 Not Found")
            log_failure(slug, "404 Not Found", CARD_IMAGES_DIR)
            continue
        if resp.status_code != 200:
            print(f"HTTP {resp.status_code}")
            log_failure(slug, f"HTTP {resp.status_code}", CARD_IMAGES_DIR)
            continue

        soup = BeautifulSoup(resp.text, "html.parser")
        img_tag, method = find_main_image_tag(soup)
        if not img_tag or not img_tag.get("src"):
            print("❌ no <img>")
            log_failure(slug, "no <img> found", CARD_IMAGES_DIR)
            continue

        img_url = img_tag["src"]
        if img_url.startswith("//"):
            img_url = "https:" + img_url
        elif img_url.startswith("/"):
            img_url = "https://camelotcg.cl" + img_url

        ext = os.path.splitext(img_url)[1].split("?")[0]
        if ext.lower() not in [".jpg", ".jpeg", ".png", ".gif", ".webp"]:
            ext = ".jpg"
        fname = f"{slug}{ext}"
        outpath = os.path.join(CARD_IMAGES_DIR, fname)

        if os.path.exists(outpath):
            print(f"✅ already exists ({fname})")
            continue

        print("Downloading…", end=" ")
        ok = download_image(img_url, outpath)
        if ok:
            print(f"✔ saved as {fname}")
        else:
            print("❌ download failed")
            log_failure(slug, "download failed", CARD_IMAGES_DIR)

    print("\nOption 2 complete.")
    print(f"Any still-failed slugs are in:\n  {os.path.join(CARD_IMAGES_DIR, RETRY_LOG_NAME)}")

# ─── OPTION 3: Fetch card info from Fandom for each still_failed.txt in subfolders ──

def option_fetch_data_from_fandom():
    """
    For each subfolder under CARD_IMAGES_DIR:
      - Read <subfolder>/still_failed.txt
      - For each slug: recover accented title via API, fetch page, parse infobox,
        convert to array, write to <subfolder>/card_data.txt.
      - If any step fails, re-log the slug into <subfolder>/still_failed.txt.
    """
    if not os.path.isdir(CARD_IMAGES_DIR):
        print(f"ERROR: '{CARD_IMAGES_DIR}' not found.")
        return

    subfolders = [
        os.path.join(CARD_IMAGES_DIR, d)
        for d in os.listdir(CARD_IMAGES_DIR)
        if os.path.isdir(os.path.join(CARD_IMAGES_DIR, d))
    ]
    if not subfolders:
        print(f"No subfolders found under {CARD_IMAGES_DIR}. Exiting.")
        return

    for folder in subfolders:
        print(f"\n--- Processing folder: {folder} ---")
        retry_log = os.path.join(folder, RETRY_LOG_NAME)
        if not os.path.isfile(retry_log):
            print("  (No still_failed.txt here → skipping.)")
            continue

        slugs = read_slugs_from_log(retry_log)
        if not slugs:
            print("  (still_failed.txt is empty → nothing to do.)")
            continue

        # Clear old still_failed.txt to accumulate new failures
        open(retry_log, "w", encoding="utf-8").close()

        data_out_path = os.path.join(folder, "card_data.txt")
        with open(data_out_path, "w", encoding="utf-8") as out_f:
            out_f.write("slug\tparsed_array\n")

            for idx, slug in enumerate(slugs, start=1):
                print(f"[{idx}/{len(slugs)}] Slug: {slug}")

                accented = get_accented_title(slug)
                if not accented:
                    print("   ✘ No such page (API lookup).")
                    log_failure(slug, "no page found (API)", folder)
                    continue

                page_slug = accented.replace(" ", "_")
                page_url  = BASE_URL_FANDOM + "/" + urllib.parse.quote(page_slug)
                print(f"   → Fetching: {page_url}")

                try:
                    resp = requests.get(page_url, timeout=10)
                except Exception:
                    print("   ✘ Network error fetching page.")
                    log_failure(slug, "network error", folder)
                    continue

                if resp.status_code == 404:
                    print("   ✘ 404 Not Found")
                    log_failure(slug, "404 Not Found", folder)
                    continue
                if resp.status_code != 200:
                    print(f"   ✘ HTTP {resp.status_code}")
                    log_failure(slug, f"HTTP {resp.status_code}", folder)
                    continue

                soup = BeautifulSoup(resp.text, "html.parser")
                info_dict = parse_card_infobox(soup)
                if not info_dict:
                    print("   ✘ No infobox/table found on page.")
                    log_failure(slug, "no infobox", folder)
                    continue

                parsed = card_info_to_array(info_dict)
                print(f"   ✔ Parsed array: {parsed}")
                out_f.write(f"{slug}\t{parsed}\n")

        print(f"  → Finished folder. See '{data_out_path}' and '{retry_log}' for any new failures.")

    print("\nOption 3 complete.")

# ─── OPTION 4: Download Fandom’s main image for each slug in still_failed.txt ────

def option_download_fandom_images():
    """
    For each subfolder under CARD_IMAGES_DIR:
      - Read <subfolder>/still_failed.txt
      - For each slug: recover accented title via API, fetch Fandom page, find largest <img>,
        download it to <subfolder>/<slug>.<ext>.
      - If any step fails, re-log that slug into <subfolder>/still_failed.txt.
    """
    if not os.path.isdir(CARD_IMAGES_DIR):
        print(f"ERROR: '{CARD_IMAGES_DIR}' not found.")
        return

    subfolders = [
        os.path.join(CARD_IMAGES_DIR, d)
        for d in os.listdir(CARD_IMAGES_DIR)
        if os.path.isdir(os.path.join(CARD_IMAGES_DIR, d))
    ]
    if not subfolders:
        print(f"No subfolders found under {CARD_IMAGES_DIR}. Exiting.")
        return

    for folder in subfolders:
        print(f"\n--- Processing folder: {folder} ---")
        retry_log = os.path.join(folder, RETRY_LOG_NAME)
        if not os.path.isfile(retry_log):
            print("  (No still_failed.txt here → skipping.)")
            continue

        slugs = read_slugs_from_log(retry_log)
        if not slugs:
            print("  (still_failed.txt is empty → nothing to do.)")
            continue

        # Clear old still_failed.txt to accumulate new failures
        open(retry_log, "w", encoding="utf-8").close()

        for idx, slug in enumerate(slugs, start=1):
            print(f"[{idx}/{len(slugs)}] Slug: {slug}")

            accented = get_accented_title(slug)
            if not accented:
                print("   ✘ No such page (API lookup).")
                log_failure(slug, "no page found (API)", folder)
                continue

            page_slug = accented.replace(" ", "_")
            page_url  = BASE_URL_FANDOM + "/" + urllib.parse.quote(page_slug)
            print(f"   → Fetching: {page_url}")

            try:
                resp = requests.get(page_url, timeout=10)
            except Exception:
                print("   ✘ Network error fetching page.")
                log_failure(slug, "network error", folder)
                continue

            if resp.status_code == 404:
                print("   ✘ 404 Not Found")
                log_failure(slug, "404 Not Found", folder)
                continue
            if resp.status_code != 200:
                print(f"   ✘ HTTP {resp.status_code}")
                log_failure(slug, f"HTTP {resp.status_code}", folder)
                continue

            soup = BeautifulSoup(resp.text, "html.parser")
            img_tag, method = find_largest_image_tag(soup)
            if not img_tag or not img_tag.get("src"):
                print("   ✘ No image found on page.")
                log_failure(slug, "no <img> found", folder)
                continue

            img_url = img_tag["src"]
            if img_url.startswith("//"):
                img_url = "https:" + img_url
            elif img_url.startswith("/"):
                img_url = "https://myl.fandom.com" + img_url

            ext = os.path.splitext(img_url)[1].split("?")[0]
            if ext.lower() not in [".jpg", ".jpeg", ".png", ".gif", ".webp"]:
                ext = ".jpg"
            fname = f"{slug}{ext}"
            outpath = os.path.join(folder, fname)

            if os.path.exists(outpath):
                print(f"   ✅ already exists ({fname})")
                continue

            print("   Downloading…", end=" ")
            ok = download_image(img_url, outpath)
            if ok:
                print(f"✔ saved as {fname}")
            else:
                print("❌ download failed")
                log_failure(slug, "download failed", folder)

        print(f"  → Finished folder. Any newly-failed slugs are in '{retry_log}'.")

    print("\nOption 4 complete.")

# ─── MAIN MENU ─────────────────────────────────────────────────────────────────

def main():
    print("=== Camelot-TCG & Fandom Automation Script ===\n")
    print("Choose one of the following options:")
    print("  1) [FULL]        Download ALL card images from a given .md file (Camelot site)")
    print("  2) [RETRY]       Re-attempt only the slugs listed in card_images/skipped_slugs.txt (Camelot site)")
    print("  3) [FETCH DATA]  For each still_failed.txt in each subfolder, fetch card info from Fandom")
    print("  4) [FANDOM IMG]  For each still_failed.txt in each subfolder, download the largest <img> from Fandom\n")

    choice = input("Enter 1, 2, 3, or 4: ").strip()
    if choice == "1":
        option_download_all()
    elif choice == "2":
        option_retry_skipped()
    elif choice == "3":
        option_fetch_data_from_fandom()
    elif choice == "4":
        option_download_fandom_images()
    else:
        print("Invalid choice. Please run again and enter 1, 2, 3, or 4.")

if __name__ == "__main__":
    main()
