import os
import glob

# Folder containing your .txt files
folder = r"E:\Scripts\deckbuilder\card_data"

for path in glob.glob(os.path.join(folder, "*.txt")):
    # Read the entire file
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()

    # Replace "" → "
    new_text = text.replace('""', '"')

    # Only rewrite if something changed
    if new_text != text:
        with open(path, "w", encoding="utf-8") as f:
            f.write(new_text)
