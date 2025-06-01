import os
import sys
from pathlib import Path

def main():
    # Define the directories
    card_data_dir = Path(r"E:\Scripts\deckbuilder\card_data")
    card_images_dir = Path(r"E:\Scripts\deckbuilder\card_images")

    # Check that directories exist
    if not card_data_dir.exists():
        print(f"Error: Card data directory does not exist: {card_data_dir}")
        sys.exit(1)
    if not card_images_dir.exists():
        print(f"Error: Card images directory does not exist: {card_images_dir}")
        sys.exit(1)

    # Collect all existing stems (filenames without extension) in card_data_dir that end with .txt
    existing_stems = {f.stem for f in card_data_dir.glob("*.txt")}

    # Define which image extensions to consider
    image_extensions = {".png", ".jpg", ".jpeg", ".gif", ".bmp"}

    # List all image files in card_images_dir with one of the allowed extensions
    images = [
        p for p in card_images_dir.iterdir()
        if p.is_file() and p.suffix.lower() in image_extensions
    ]

    # Filter down to those images whose stem isn't already in existing_stems
    new_images = [img for img in images if img.stem not in existing_stems]

    if not new_images:
        print("No new images found that lack corresponding .txt files in card_data.")
        return

    # Create a .txt file for each new image (in card_data_dir)
    for img in new_images:
        txt_path = card_data_dir / (img.stem + ".txt")
        try:
            txt_path.touch(exist_ok=False)
            print(f"Created empty file: {txt_path.name}")
        except FileExistsError:
            # In the unlikely event it was created between our checks, skip it
            print(f"File already exists (skipping): {txt_path.name}")

    print("\nNow prompting for data entry into each newly created .txt file...\n")

    # For each newly created .txt, prompt the user to enter data
    for img in new_images:
        txt_path = card_data_dir / (img.stem + ".txt")
        while True:
            # Prompt instructions updated to allow any of the three valid formats:
            #   1) "string"
            #   2) int,"string"
            #   3) int,int,"string"
            user_input = input(
                f"Enter data for '{img.stem}'\n"
                f"  (format: \"string\"  OR  int,\"string\"  OR  int,int,\"string\"): "
            ).strip()
            if not user_input:
                print("  Input cannot be empty. Please try again.")
                continue

            # Wrap whatever the user typed inside [ and ]
            content = f"[{user_input}]"
            try:
                with open(txt_path, "w", encoding="utf-8") as f:
                    f.write(content)
                print(f"  → Written to {txt_path.name}: {content}\n")
                break
            except Exception as e:
                print(f"  Error writing to file {txt_path.name}: {e}")
                print("  Please try again.")

if __name__ == "__main__":
    main()
