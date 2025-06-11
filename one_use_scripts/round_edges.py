#!/usr/bin/env python3
"""
round_corners.py – bulk-round card corners for the deck-builder

Put this file in:
    E:\Scripts\deckbuilder\one_use_scripts

Install Pillow once:
    py -m pip install pillow

Run:
    py round_corners.py
"""

import os
from pathlib import Path
from PIL import Image, ImageDraw

# === CONFIGURATION ===========================================================
ROOT_DIR   = Path(r"E:\Scripts\deckbuilder\edge_round")  # <- new root folder
RADIUS_RATIO = 0.06   # 6 % of the shorter side (unchanged)
BLEED_PX     = 2      # halo-removal padding (unchanged)
# ============================================================================

def round_card(im: Image.Image, radius_ratio: float, bleed: int) -> Image.Image:
    """Return a copy of *im* with rounded-transparent corners."""
    w, h   = im.size
    radius = int(min(w, h) * radius_ratio) + bleed

    # Pillow mask – white inside rounded rect, black outside
    mask = Image.new("L", (w, h), 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle([0, 0, w, h], radius=radius, fill=255)

    im_rgba = im.convert("RGBA")
    im_rgba.putalpha(mask)
    return im_rgba


def process_all():
    if not ROOT_DIR.exists():
        raise FileNotFoundError(f"Card‐image folder not found: {ROOT_DIR}")

    good, skipped = 0, 0
    # look for both png and jpg/jpeg
    for src_path in sorted(ROOT_DIR.rglob("*")):
        if src_path.suffix.lower() not in (".png", ".jpg", ".jpeg"):
            continue
        try:
            with Image.open(src_path) as im:
                result = round_card(im, RADIUS_RATIO, BLEED_PX)

                # always output as PNG
                dst_path = src_path.with_suffix(".png")
                tmp_path = dst_path.with_suffix(".tmp.png")
                result.save(tmp_path, format="PNG", optimize=True)
                tmp_path.replace(dst_path)  # atomic replace

                good += 1
                rel = dst_path.relative_to(ROOT_DIR)
                print(f"[✓] {rel}  – rounded")
        except Exception as e:
            skipped += 1
            rel = src_path.relative_to(ROOT_DIR)
            print(f"[!] Skipped {rel}: {e}")

    print(f"\nFinished – {good} image(s) processed, {skipped} skipped.")

if __name__ == "__main__":
    process_all()
