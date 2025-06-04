import os
import sys
import ast
import json
from pathlib import Path

def add_expansion_and_reborn(card_data_dir, card_images_dir):
    """
    For each .txt in card_data_dir, read its array (1–4 elements),
    find the associated image under each subfolder of card_images_dir (ignoring 'test'),
    then append [initials, "Reborn"] unless the last element is already "reborn" or "pbx".
    """
    expansion_map = {
        "hijos_de_daana": "hdd",
        "tierras_altas": "hdd",
        "helenica": "hel",
        "imperio": "hel",
        "dominios_de_ra": "ddr",
        "encrucijada": "ddr",
        "espada_sagrada": "esp",
        "cruzadas": "esp",
    }
    image_exts = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}

    for txt_path in card_data_dir.glob("*.txt"):
        stem = txt_path.stem
        try:
            content = txt_path.read_text(encoding="utf-8").strip()
            if not content:
                current_array = []
            else:
                current_array = ast.literal_eval(content)
                if not isinstance(current_array, list):
                    print(f"Warning: {txt_path.name} does not contain a list. Skipping.")
                    continue
        except Exception as e:
            print(f"Error reading/parsing {txt_path.name}: {e}. Skipping.")
            continue

        # If last element is "reborn" or "pbx" (case-insensitive), skip
        if current_array and isinstance(current_array[-1], str) and current_array[-1].lower() in ("reborn", "pbx"):
            continue

        found_initial = None
        for subdir in card_images_dir.iterdir():
            if not subdir.is_dir() or subdir.name.lower() == "test":
                continue
            for ext in image_exts:
                candidate = subdir / (stem + ext)
                if candidate.exists():
                    folder_name = subdir.name.lower()
                    found_initial = expansion_map.get(folder_name)
                    break
            if found_initial:
                break

        if not found_initial:
            print(f"No associated image found for '{stem}'. Skipping expansion/Reborn addition.")
            continue

        updated_array = current_array + [found_initial, "Reborn"]
        new_content = json.dumps(updated_array, separators=(",", ":"), ensure_ascii=False)

        try:
            txt_path.write_text(new_content, encoding="utf-8")
            print(f"Updated {txt_path.name}: {new_content}")
        except Exception as e:
            print(f"Error writing to {txt_path.name}: {e}")

def create_missing_txt_and_handle_webp(card_data_dir, card_images_dir):
    """
    For each image under card_images_dir (one level deep in subfolders, ignoring 'test'):
      - Delete any .webp that has a non-.webp counterpart with same stem; otherwise,
        record orphaned .webp names in IMPORTANT MISSING.txt inside that subfolder.
      - For each non-.webp image missing a corresponding .txt in card_data_dir, create it,
        then prompt the user for array input (with autofill of "Aliados" when first two are numbers).
      - Skip prompting if the stem is already logged in fetch_processed.log.
    """
    script_dir = Path(__file__).parent
    fetch_log_path = script_dir / "fetch_processed.log"
    processed_stems = set()
    if fetch_log_path.exists():
        with open(fetch_log_path, "r", encoding="utf-8") as log_file:
            processed_stems = {line.strip() for line in log_file if line.strip()}

    image_exts = {".png", ".jpg", ".jpeg", ".gif", ".bmp"}
    webp_ext = ".webp"

    for subdir in card_images_dir.iterdir():
        if not subdir.is_dir() or subdir.name.lower() == "test":
            continue

        missing_webps = []
        # First: handle .webp cleanup
        for img_file in subdir.iterdir():
            if img_file.suffix.lower() == webp_ext:
                stem = img_file.stem
                has_other = any((subdir / (stem + ext)).exists() for ext in image_exts)
                if has_other:
                    try:
                        img_file.unlink()
                        print(f"Deleted redundant WebP: {img_file.name}")
                    except Exception as e:
                        print(f"Error deleting {img_file.name}: {e}")
                else:
                    missing_webps.append(img_file.name)

        if missing_webps:
            missing_path = subdir / "IMPORTANT MISSING.txt"
            try:
                with open(missing_path, "w", encoding="utf-8") as mfile:
                    for name in missing_webps:
                        mfile.write(f"{name}\n")
                print(f"Created {missing_path.relative_to(card_images_dir.parent)} "
                      f"listing missing WebP(s): {', '.join(missing_webps)}")
            except Exception as e:
                print(f"Error writing IMPORTANT MISSING.txt in {subdir.name}: {e}")

        # Second: for each non-.webp image, create missing .txt and prompt
        for img_file in subdir.iterdir():
            if img_file.is_file() and img_file.suffix.lower() in image_exts:
                stem = img_file.stem
                if stem in processed_stems:
                    continue

                txt_path = card_data_dir / f"{stem}.txt"
                if not txt_path.exists():
                    try:
                        txt_path.touch(exist_ok=False)
                        print(f"Created missing file: {txt_path.name}")
                    except Exception as e:
                        print(f"Error creating {txt_path.name}: {e}")
                        continue

                    # Prompt for data entry
                    def prompt_for_array():
                        # First element: integer or string; 'quit' to exit
                        first_input = input(f"Enter first element for '{stem}' (integer or string, or 'quit' to stop): ").strip()
                        if first_input.lower() == "quit":
                            sys.exit(0)
                        try:
                            first_elem = int(first_input)
                        except ValueError:
                            return [first_input]

                        # Second element: integer or string; 'quit' to exit
                        second_input = input(f"Enter second element for '{stem}' (integer or string, or 'quit' to stop): ").strip()
                        if second_input.lower() == "quit":
                            sys.exit(0)
                        try:
                            second_elem = int(second_input)
                            # Autofill third with "Aliados", prompt for fourth
                            third_elem = "Aliados"
                            fourth_input = input(f"Enter fourth element for '{stem}' (string, or 'quit' to stop): ").strip()
                            if fourth_input.lower() == "quit":
                                sys.exit(0)
                            if not fourth_input:
                                print("  Fourth element cannot be empty. Skipping this image.")
                                return []
                            return [first_elem, second_elem, third_elem, fourth_input]
                        except ValueError:
                            return [first_elem, second_input]

                    array = prompt_for_array()
                    if array == []:
                        try:
                            txt_path.unlink()
                            print(f"Skipped '{stem}'. File deleted, will be retried on next run.\n")
                        except Exception as e:
                            print(f"Error deleting file '{txt_path.name}': {e}")
                        continue

                    new_content = json.dumps(array, separators=(",", ":"), ensure_ascii=False)
                    try:
                        with open(txt_path, "w", encoding="utf-8") as f:
                            f.write(new_content)
                        print(f"  → Written to {txt_path.name}: {new_content}\n")
                        with open(fetch_log_path, "a", encoding="utf-8") as log_file:
                            log_file.write(f"{stem}\n")
                    except Exception as e:
                        print(f"Error writing to {txt_path.name}: {e}")
                        print("Please try again.")

def main():
    script_dir = Path(__file__).parent
    project_root = script_dir.parent  # deckbuilder folder

    card_data_dir = project_root / "card_data"
    card_images_dir = project_root / "card_images"

    if not card_data_dir.exists() or not card_images_dir.exists():
        print("Error: 'card_data' or 'card_images' folder not found under project root.")
        sys.exit(1)

    # 1) Update existing .txt with expansion initials + "Reborn", skipping if already up to date
    add_expansion_and_reborn(card_data_dir, card_images_dir)

    # 2) Handle missing .txt creation (with prompt) and WebP cleanup
    create_missing_txt_and_handle_webp(card_data_dir, card_images_dir)

if __name__ == "__main__":
    main()
