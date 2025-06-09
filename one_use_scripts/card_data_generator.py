#!/usr/bin/env python3
import sys
import json
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import ast

def fetch_and_generate(card_data_dir, card_images_dir):
    # 1) Find new images
    script_dir = Path(__file__).parent
    fetch_log = script_dir / "fetch_processed.log"
    fetch_log.touch(exist_ok=True)

    processed = {l.strip() for l in fetch_log.read_text("utf-8").splitlines() if l.strip()}
    existing  = {p.stem for p in card_data_dir.glob("*.txt")}
    exts      = {".png", ".jpg", ".jpeg", ".gif", ".bmp"}

    images = []
    for sub in card_images_dir.iterdir():
        if sub.is_dir() and sub.name.lower() != "test":
            for f in sub.iterdir():
                if f.is_file() and f.suffix.lower() in exts:
                    images.append(f)

    new_images = [img for img in images if img.stem not in processed and img.stem not in existing]
    if not new_images:
        print("No new images found that need processing.")
        return

    # 2) Saga → raza options
    raza_map = {
        "hel": ["heroe", "olimpico", "titan"],
        "hdd": ["defensor", "desafiante", "sombra"],
        "ddr": ["faraon", "eterno", "sacerdote"],
        "esp": ["dragon", "faerie", "caballero"],
    }

    # 3) Build GUI
    root = tk.Tk()
    root.title("Card Data Entry")

    # Maximize window
    try:
        root.state('zoomed')
    except:
        root.attributes('-zoomed', True)

    screen_w = root.winfo_screenwidth()
    screen_h = root.winfo_screenheight()

    # Define fonts
    LABEL_FONT   = ("Arial", 16)
    ENTRY_FONT   = ("Arial", 16)
    COMBO_FONT   = ("Arial", 16)
    BUTTON_FONT  = ("Arial", 16)

    # Configure ttk styles for Combobox and Buttons
    style = ttk.Style(root)
    style.configure("TCombobox", font=COMBO_FONT)
    style.configure("TButton",   font=BUTTON_FONT)

    state = {"idx": 0, "photo": None}

    # Layout frames
    top    = tk.Frame(root); top.grid(row=0, column=0, padx=20, pady=20)
    left   = tk.Frame(top); left.grid(row=0, column=0)
    right  = tk.Frame(top); right.grid(row=0, column=1, padx=(40,0))
    bottom = tk.Frame(root); bottom.grid(row=1, column=0, pady=20)

    # Image display
    img_label = tk.Label(left)
    img_label.pack()

    # Form fields (Tipo first)
    tk.Label(right, text="Tipo:",   font=LABEL_FONT).grid(row=0, column=0, sticky="e", pady=5)
    tipo_cb = ttk.Combobox(
        right,
        values=["aliados","talismanes","totems","armas","oros"],
        state="readonly",
        width=25
    )
    tipo_cb.grid(row=0, column=1, pady=5)

    tk.Label(right, text="Coste:",  font=LABEL_FONT).grid(row=1, column=0, sticky="e", pady=5)
    coste_e = tk.Entry(right, state="disabled", font=ENTRY_FONT, width=27)
    coste_e.grid(row=1, column=1, pady=5)

    tk.Label(right, text="Fuerza:", font=LABEL_FONT).grid(row=2, column=0, sticky="e", pady=5)
    fuerza_e = tk.Entry(right, state="disabled", font=ENTRY_FONT, width=27)
    fuerza_e.grid(row=2, column=1, pady=5)

    tk.Label(right, text="Saga:",   font=LABEL_FONT).grid(row=3, column=0, sticky="e", pady=5)
    saga_cb = ttk.Combobox(
        right,
        values=list(raza_map.keys()),
        state="readonly",
        width=25
    )
    saga_cb.grid(row=3, column=1, pady=5)

    tk.Label(right, text="Raza:",   font=LABEL_FONT).grid(row=4, column=0, sticky="e", pady=5)
    raza_cb = ttk.Combobox(right, values=[], state="disabled", width=25)
    raza_cb.grid(row=4, column=1, pady=5)

    tk.Label(right, text="Formato:", font=LABEL_FONT).grid(row=5, column=0, sticky="e", pady=5)
    formato_e = tk.Entry(right, state="readonly", font=ENTRY_FONT, width=27)
    formato_e.grid(row=5, column=1, pady=5)
    formato_e.insert(0, "reborn")

    # 4) Enable/disable per Tipo (do not reset Saga)
    def on_tipo_change(event=None):
        t = tipo_cb.get()
        coste_e.delete(0, tk.END)
        fuerza_e.delete(0, tk.END)
        raza_cb.set("")
        if t == "aliados":
            coste_e.config(state="normal")
            fuerza_e.config(state="normal")
            saga_cb.config(state="readonly")
            raza_cb.config(state="readonly")
        elif t in {"talismanes","totems","armas"}:
            coste_e.config(state="normal")
            fuerza_e.config(state="disabled")
            saga_cb.config(state="readonly")
            raza_cb.config(state="disabled")
        elif t == "oros":
            coste_e.config(state="disabled")
            fuerza_e.config(state="disabled")
            saga_cb.config(state="readonly")
            raza_cb.config(state="disabled")

    tipo_cb.bind("<<ComboboxSelected>>", on_tipo_change)

    def on_saga_change(event=None):
        saga = saga_cb.get()
        raza_cb['values'] = raza_map.get(saga, [])
        if raza_cb.cget("state") == "readonly":
            raza_cb.set("")

    saga_cb.bind("<<ComboboxSelected>>", on_saga_change)

    # 5) Show each card (resize up to 70% width, 80% height)
    def show_card():
        idx = state['idx']
        img = new_images[idx]
        pil = Image.open(img)
        w, h = pil.size
        max_w = int(screen_w * 0.7)
        max_h = int(screen_h * 0.8)
        ratio = min(max_w / w, max_h / h)
        pil = pil.resize((int(w*ratio), int(h*ratio)), resample=Image.LANCZOS)

        photo = ImageTk.PhotoImage(pil)
        state['photo'] = photo
        img_label.config(image=photo)
        root.title(f"Card {idx+1}/{len(new_images)}: {img.stem}")

    show_card()

    # 6) Navigation & saving
    def next_card():
        if state['idx'] + 1 >= len(new_images):
            messagebox.showinfo("Done", "All cards processed.")
            root.destroy()
        else:
            state['idx'] += 1
            show_card()

    def save_and_next():
        t = tipo_cb.get().strip()
        if not t:
            return messagebox.showerror("Missing", "Please choose a Tipo.")

        s = saga_cb.get().strip()
        if not s:
            return messagebox.showerror("Missing", "Please choose a Saga.")

        fmt = "reborn"
        arr = []

        if t == "aliados":
            try:
                c = int(coste_e.get()); f = int(fuerza_e.get())
            except ValueError:
                return messagebox.showerror("Invalid", "Coste & Fuerza must be integers.")
            r = raza_cb.get().strip()
            if not r:
                return messagebox.showerror("Missing", "Please choose a Raza.")
            arr = [c, f, t, r, s, fmt]

        elif t in {"talismanes","totems","armas"}:
            try:
                c = int(coste_e.get())
            except ValueError:
                return messagebox.showerror("Invalid", "Coste must be an integer.")
            arr = [c, t, s, fmt]

        elif t == "oros":
            arr = [t, s, fmt]

        else:
            return messagebox.showerror("Invalid", "Unknown Tipo.")

        stem = new_images[state['idx']].stem
        out = card_data_dir / f"{stem}.txt"
        with open(out, "w", encoding="utf-8") as fo:
            json.dump(arr, fo, ensure_ascii=False)
        with open(fetch_log, "a", encoding="utf-8") as lg:
            lg.write(stem + "\n")

        next_card()

    def skip_and_next():
        next_card()

    # 7) Buttons (separate frame)
    btn_w = 20
    tk.Button(bottom, text="Save & Next", width=btn_w, font=BUTTON_FONT, command=save_and_next).pack(side="left", padx=10)
    tk.Button(bottom, text="Skip",       width=btn_w, font=BUTTON_FONT, command=skip_and_next).pack(side="left", padx=10)
    tk.Button(bottom, text="Quit",       width=btn_w, font=BUTTON_FONT, command=root.destroy).pack(side="left", padx=10)

    root.mainloop()

def add_raza(card_data_dir):
    all_txts = list(card_data_dir.glob("*.txt"))
    if not all_txts:
        print("No .txt files found.")
        return

    for txt in all_txts:
        content = txt.read_text("utf-8").strip()
        if not content:
            continue
        try:
            arr = ast.literal_eval(content)
        except Exception:
            print(f"Could not parse {txt.name}; skipping.")
            continue
        if not (isinstance(arr, list) and len(arr) < 4 and "Aliados" in arr):
            continue

        print(f"\n{txt.name} → {arr}")
        new_el = input("Enter a new element (or 'quit'): ").strip()
        if new_el.lower() == "quit":
            sys.exit(0)
        if not new_el:
            print("No input; skip.")
            continue

        arr.append(new_el)
        txt.write_text(json.dumps(arr, separators=",", ensure_ascii=False), encoding="utf-8")
        print(f"Updated {txt.name}: {arr}")

def main():
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    cd = project_root / "card_data"
    ci = project_root / "card_images"
    if not cd.exists() or not ci.exists():
        print("card_data or card_images missing."); sys.exit(1)

    while True:
        choice = input("Mode: 1) GUI  2) add raza  (or 'quit'): ").strip().lower()
        if choice == "quit":
            sys.exit(0)
        if choice == "1":
            fetch_and_generate(cd, ci)
            break
        if choice == "2":
            add_raza(cd)
            break
        print("Enter 1, 2 or quit.")

if __name__ == "__main__":
    main()
