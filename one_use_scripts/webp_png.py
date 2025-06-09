import os
from pathlib import Path
from PIL import Image

# CONFIGURATION
ROOT_DIR = Path(r"E:\Scripts\deckbuilder\card_images")

# IMAGE EXTENSIONS TO CONVERT
TARGET_EXTENSIONS = {".webp", ".jpg", ".jpeg"}

def convert_image_to_png(image_path: Path):
    png_path = image_path.with_suffix(".png")
    try:
        with Image.open(image_path) as img:
            # Convert with max quality
            img.save(png_path, format="PNG")

        # Verify PNG was created
        if png_path.exists():
            # Delete original image
            image_path.unlink()
            print(f"Converted and deleted: {image_path} -> {png_path}")
        else:
            print(f"[WARNING] PNG not created for: {image_path}")

    except Exception as e:
        print(f"[ERROR] Failed to convert {image_path}: {e}")

def convert_images():
    print(f"Starting conversion in: {ROOT_DIR}")

    count_total = 0
    count_converted = 0

    for dirpath, dirnames, filenames in os.walk(ROOT_DIR):
        for filename in filenames:
            ext = Path(filename).suffix.lower()
            if ext in TARGET_EXTENSIONS:
                count_total += 1
                image_path = Path(dirpath) / filename
                convert_image_to_png(image_path)
                count_converted += 1

    print(f"\nConversion complete. {count_converted}/{count_total} images converted.")

# ENTRY POINT
if __name__ == "__main__":
    convert_images()
