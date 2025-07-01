# remove_duplicates_from_card_list.py

import os

# ─── HARD-CODED PATHS ───────────────────────────────────────────────
CARD_DATA_DIR = r"E:\Scripts\deckbuilder\card_data"
CARD_LIST_PATH = r"E:\Scripts\deckbuilder\card_pbx_from_official_doc.txt"
OUTPUT_PATH = r"E:\Scripts\deckbuilder\oldcards.txt"

def get_existing_card_names():
    """
    Return a set of base names (no extension) from .txt files in CARD_DATA_DIR.
    """
    existing = set()
    for filename in os.listdir(CARD_DATA_DIR):
        if filename.lower().endswith(".txt"):
            base_name = os.path.splitext(filename)[0]
            existing.add(base_name)
    return existing

def filter_card_list(existing_names):
    """
    Read card_list_pbx.txt and remove any lines that match names in existing_names.
    Return the cleaned list of lines.
    """
    with open(CARD_LIST_PATH, "r", encoding="utf-8") as f:
        lines = f.readlines()

    cleaned = []
    for line in lines:
        slug = line.strip()
        if slug and slug not in existing_names:
            cleaned.append(slug)

    return cleaned

def write_output(cleaned_lines):
    """
    Write the cleaned list to OUTPUT_PATH.
    """
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        for line in cleaned_lines:
            f.write(line + "\n")

def main():
    existing_names = get_existing_card_names()
    cleaned_list = filter_card_list(existing_names)
    write_output(cleaned_list)
    print(f"✔ Done. Cleaned list saved to:\n  {OUTPUT_PATH}")
    print(f"• Removed {len(existing_names)} potential duplicates (if matched).")
    print(f"• Final list contains {len(cleaned_list)} entries.")

if __name__ == "__main__":
    main()
