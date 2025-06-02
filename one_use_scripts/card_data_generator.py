import os
import sys
import ast
import json
from pathlib import Path

def fetch_and_generate(card_data_dir, card_images_dir):
    # Log file in the same directory as this script
    script_dir = Path(__file__).parent
    fetch_log_path = script_dir / "fetch_processed.log"

    processed_stems = set()
    if fetch_log_path.exists():
        with open(fetch_log_path, "r", encoding="utf-8") as log_file:
            processed_stems = {line.strip() for line in log_file if line.strip()}

    existing_stems = {f.stem for f in card_data_dir.glob("*.txt")}
    image_extensions = {".png", ".jpg", ".jpeg", ".gif", ".bmp"}

    images = []
    for subdir in card_images_dir.iterdir():
        if subdir.is_dir() and subdir.name.lower() != "test":
            for img_file in subdir.iterdir():
                if img_file.is_file() and img_file.suffix.lower() in image_extensions:
                    images.append(img_file)

    new_images = [
        img for img in images
        if img.stem not in existing_stems and img.stem not in processed_stems
    ]

    if not new_images:
        print("No new images found that lack corresponding .txt files or have already been processed.")
        return

    for img in new_images:
        txt_path = card_data_dir / (img.stem + ".txt")
        try:
            txt_path.touch(exist_ok=False)
            print(f"Created empty file: {txt_path.name}")
        except FileExistsError:
            print(f"File already exists (skipping creation): {txt_path.name}")

        def prompt_for_array():
            # First element: if integer, continue; if string, return [string]; if 'quit', exit.
            first_input = input(f"Enter first element for '{img.stem}' (integer or string, or 'quit' to stop): ").strip()
            if first_input.lower() == "quit":
                sys.exit(0)
            try:
                first_elem = int(first_input)
            except ValueError:
                # First element is a string → return single-element array
                return [first_input]

            # Second element (integer or string)
            second_input = input(f"Enter second element for '{img.stem}' (integer or string, or 'quit' to stop): ").strip()
            if second_input.lower() == "quit":
                sys.exit(0)

            try:
                second_elem = int(second_input)
                # If second is integer, prompt for two more strings
                third_input = input(f"Enter third element for '{img.stem}' (string, or 'quit' to stop): ").strip()
                if third_input.lower() == "quit":
                    sys.exit(0)
                if not third_input:
                    print("  Third element cannot be empty. Skipping this image.")
                    return []

                fourth_input = input(f"Enter fourth element for '{img.stem}' (string, or 'quit' to stop): ").strip()
                if fourth_input.lower() == "quit":
                    sys.exit(0)
                if not fourth_input:
                    print("  Fourth element cannot be empty. Skipping this image.")
                    return []

                return [first_elem, second_elem, third_input, fourth_input]

            except ValueError:
                # Second element is a string → return [first_elem, second_elem]
                return [first_elem, second_input]

        array = prompt_for_array()
        if array == []:
            # Skip this image: delete the .txt so it will be retried next run
            try:
                txt_path.unlink()
                print(f"Skipped '{img.stem}'. File deleted, will be retried on next run.\n")
            except Exception as e:
                print(f"Error deleting file '{txt_path.name}': {e}")
            continue

        # Write array as JSON (strings automatically quoted)
        new_content = json.dumps(array, separators=(",", ":"), ensure_ascii=False)
        try:
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write(new_content)
            print(f"  → Written to {txt_path.name}: {new_content}\n")
            # Log this stem as processed
            with open(fetch_log_path, "a", encoding="utf-8") as log_file:
                log_file.write(f"{img.stem}\n")
        except Exception as e:
            print(f"  Error writing to file {txt_path.name}: {e}")
            print("  Please try again.")


def add_raza(card_data_dir):
    all_txts = list(card_data_dir.glob("*.txt"))
    if not all_txts:
        print("No .txt files found in card_data directory.")
        return

    for txt_path in all_txts:
        stem = txt_path.stem
        try:
            with open(txt_path, "r", encoding="utf-8") as f:
                content_str = f.read().strip()
            if not content_str:
                continue

            try:
                array = ast.literal_eval(content_str)
            except (ValueError, SyntaxError):
                print(f"Warning: Could not parse contents of {txt_path.name}. Skipping.")
                continue

            # Skip if array already has 4 or more elements
            if isinstance(array, list) and len(array) >= 4:
                continue

            if "Aliados" in array:
                print(f"\nFile '{txt_path.name}' contains 'Aliados' in its array: {array}")
                new_element = input(f"Enter a new element to add to '{txt_path.name}' (or 'quit' to stop): ").strip()
                if new_element.lower() == "quit":
                    sys.exit(0)
                if not new_element:
                    print("  No input provided. Skipping this file.")
                    continue

                array.append(new_element)
                new_content = json.dumps(array, separators=(",", ":"), ensure_ascii=False)
                with open(txt_path, "w", encoding="utf-8") as f:
                    f.write(new_content)
                print(f"  → Updated {txt_path.name}: {new_content}")
        except Exception as e:
            print(f"Error handling file {txt_path.name}: {e}")


def main():
    # Derive project root from this script's location
    script_dir = Path(__file__).parent
    project_root = script_dir.parent  # deckbuilder folder

    # Relative paths under project root
    card_data_dir = project_root / "card_data"
    card_images_dir = project_root / "card_images"

    if not card_data_dir.exists():
        print(f"Error: Card data directory does not exist: {card_data_dir}")
        sys.exit(1)
    if not card_images_dir.exists():
        print(f"Error: Card images directory does not exist: {card_images_dir}")
        sys.exit(1)

    while True:
        choice = input(
            "Choose mode:\n"
            "  1) fetch and generate\n"
            "  2) add raza\n"
            "Enter '1' or '2' (or type 'quit' to exit): "
        ).strip()
        if choice.lower() == "quit":
            print("Exiting script.")
            sys.exit(0)
        elif choice == "1":
            fetch_and_generate(card_data_dir, card_images_dir)
            break
        elif choice == "2":
            add_raza(card_data_dir)
            break
        else:
            print("Invalid choice. Please enter '1', '2', or 'quit'.")


if __name__ == "__main__":
    main()
