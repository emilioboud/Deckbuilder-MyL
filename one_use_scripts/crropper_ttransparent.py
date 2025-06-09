import os
from PIL import Image

# Configuration
ROOT_DIR = r"E:\Scripts\deckbuilder\card_images"
LOG_FILE = os.path.join(ROOT_DIR, "crop_log.txt")

def is_crop_safe(original_img, cropped_img):
    # Compare dimensions — if different, we cropped
    if original_img.size == cropped_img.size:
        return False  # No crop needed
    
    # Accept getbbox crop as safe — simple heuristic
    return True

def crop_image(image_path):
    im = Image.open(image_path).convert("RGBA")
    bbox = im.getbbox()

    if bbox:
        cropped_im = im.crop(bbox)
        if is_crop_safe(im, cropped_im):
            cropped_im.save(image_path)  # overwrite original image
            return True
    return False

def main():
    cropped_count = 0
    with open(LOG_FILE, "w") as log:
        for root, dirs, files in os.walk(ROOT_DIR):
            for file in files:
                if file.lower().endswith(".png"):
                    image_path = os.path.join(root, file)
                    print(f"Processing: {image_path}")
                    try:
                        cropped = crop_image(image_path)
                        if cropped:
                            log.write(f"{image_path}\n")
                            print(f"  --> Cropped and logged: {image_path}")
                            cropped_count += 1
                        else:
                            print(f"  --> No crop needed or unsafe crop, skipped.")
                    except Exception as e:
                        print(f"  --> Error processing {image_path}: {e}")

    print(f"\nDone. Total cropped images: {cropped_count}")

if __name__ == "__main__":
    main()
