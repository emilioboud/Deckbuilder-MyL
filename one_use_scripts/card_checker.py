#!/usr/bin/env python3
import os
import sys

def main():
    # determine paths
    script_dir     = os.path.dirname(os.path.abspath(__file__))
    nuevas_path    = os.path.join(script_dir, "nuevas.txt")
    card_data_dir  = os.path.abspath(os.path.join(script_dir, os.pardir, "card_data"))

    # sanity checks
    if not os.path.isdir(card_data_dir):
        print(f"ERROR: card_data directory not found at {card_data_dir}", file=sys.stderr)
        sys.exit(1)
    if not os.path.isfile(nuevas_path):
        print(f"ERROR: nuevas.txt not found at {nuevas_path}", file=sys.stderr)
        sys.exit(1)

    # build a set of existing .txt basenames in card_data
    existing = {
        os.path.splitext(fname)[0]
        for fname in os.listdir(card_data_dir)
        if fname.lower().endswith(".txt")
    }

    # read each line in nuevas.txt and report
    with open(nuevas_path, encoding="utf-8") as f:
        for raw in f:
            name = raw.strip()
            if not name or name.startswith("#"):
                continue

            if name in existing:
                print(f"{name} is present.")
            else:
                print(f"{name} is missing.")

if __name__ == "__main__":
    main()
