import os
import sys
import ast
import random
import math
import tkinter as tk
from tkinter import messagebox
from collections import Counter, defaultdict
from PIL import Image, ImageTk

# =============================================================================
# 0) RESOURCE PATH HANDLING FOR SCRIPT VS. BUNDLED EXE
# =============================================================================
def get_base_path():
    """
    Return the folder where our resources (card_data/, card_images/) live.
    1) If running as a PyInstaller one-file EXE, sys.frozen=True and sys._MEIPASS
       points to a temp folder containing everything.
    2) Otherwise, check if card_data/ & card_images/ exist next to this script;
       if not, fall back to the current working directory.
    """
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return sys._MEIPASS

    script_dir = os.path.abspath(os.path.dirname(__file__))
    if os.path.isdir(os.path.join(script_dir, "card_data")) and os.path.isdir(os.path.join(script_dir, "card_images")):
        return script_dir

    cwd = os.getcwd()
    if os.path.isdir(os.path.join(cwd, "card_data")) and os.path.isdir(os.path.join(cwd, "card_images")):
        return cwd

    return script_dir

BASE_PATH = get_base_path()
CARD_DATA_DIR   = os.path.join(BASE_PATH, "card_data")
CARD_IMAGES_DIR = os.path.join(BASE_PATH, "card_images")
DECKS_DIR       = os.path.join(BASE_PATH, "decks")

def verify_data_folders():
    missing = []
    if not os.path.isdir(CARD_DATA_DIR):
        missing.append(f"  • {CARD_DATA_DIR}")
    if not os.path.isdir(CARD_IMAGES_DIR):
        missing.append(f"  • {CARD_IMAGES_DIR}")

    if missing:
        msg = "Cannot locate the required folder(s):\n" + "\n".join(missing) + (
            "\n\nMake sure you:\n"
            " • If running the EXE, built with\n"
            "   --add-data \"card_data;card_data\"\n"
            "   and --add-data \"card_images;card_images\"\n"
            " • If running as .py, ensure card_data/ and card_images/ exist\n"
            "   next to main.py or in your working directory."
        )
        if getattr(sys, "frozen", False):
            tk.Tk().withdraw()
            messagebox.showerror("Missing Data Folders", msg)
        else:
            print("ERROR:", msg)
        sys.exit(1)

verify_data_folders()

if not os.path.isdir(DECKS_DIR):
    os.makedirs(DECKS_DIR)

# =============================================================================
# 1) CARD CLASS: load metadata now, images later (after Tk root exists)
# =============================================================================
class Card:
    def __init__(self, name):
        """
        name: string, e.g. "Julio_Cesar" or "oro"
        Only loads textual data now. Delays loading PhotoImage until load_image() call.
        """
        self.name = name
        self.data_path = os.path.join(CARD_DATA_DIR, f"{name}.txt")
        self.image_path = os.path.join(CARD_IMAGES_DIR, f"{name}.png")
        self.cost = None
        self.strength = None
        self.category = None
        self.tk_image = None

        self._load_data()

    def _load_data(self):
        if not os.path.isfile(self.data_path):
            raise FileNotFoundError(f"Data file not found: {self.data_path}")
        with open(self.data_path, "r", encoding="utf-8") as f:
            arr = ast.literal_eval(f.read().strip())

        # 1) ["Oros"]
        if isinstance(arr, list) and len(arr) == 1 and arr[0] == "Oros":
            self.category = "Oros"
            self.cost = None
            self.strength = None
        # 2) [cost, category]  (Armas, Talismanes, Totems)
        elif isinstance(arr, list) and len(arr) == 2:
            self.cost = int(arr[0])
            self.strength = None
            self.category = arr[1]
        # 3) [cost, strength, category] (Aliados)
        elif isinstance(arr, list) and len(arr) == 3:
            self.cost = int(arr[0])
            self.strength = int(arr[1])
            self.category = arr[2]
        else:
            raise ValueError(
                f"Invalid format in '{self.data_path}'.\n"
                "Expected [\"Oros\"] or [cost, category] or [cost, strength, category]."
            )

    def load_image(self):
        """
        After the Tkinter root exists, call this to create a PhotoImage.
        """
        if not os.path.isfile(self.image_path):
            alt_jpg = os.path.join(CARD_IMAGES_DIR, f"{self.name}.jpg")
            if os.path.isfile(alt_jpg):
                self.image_path = alt_jpg
            else:
                raise FileNotFoundError(f"Image not found for '{self.name}': {self.image_path}")

        pil_img = Image.open(self.image_path)
        DISPLAY_WIDTH = 60
        w, h = pil_img.size
        ratio = DISPLAY_WIDTH / w
        new_h = int(h * ratio)
        pil_resized = pil_img.resize((DISPLAY_WIDTH, new_h), Image.LANCZOS)
        self.tk_image = ImageTk.PhotoImage(pil_resized)

# =============================================================================
# 2) DECK CLASS: tracks card_name → count
# =============================================================================
class Deck:
    def __init__(self):
        self.card_counts = Counter()

    def total_cards(self):
        return sum(self.card_counts.values())

    def add_card(self, name, qty=1):
        self.card_counts[name] += qty

    def remove_card(self, name, qty=1):
        new_c = self.card_counts[name] - qty
        if new_c <= 0:
            if name in self.card_counts:
                del self.card_counts[name]
        else:
            self.card_counts[name] = new_c

    def list_all_copies(self):
        flat = []
        for name, cnt in self.card_counts.items():
            flat.extend([name] * cnt)
        return flat

    def as_save_lines(self):
        lines = []
        for name in sorted(self.card_counts.keys()):
            cnt = self.card_counts[name]
            if cnt > 0:
                lines.append(f"{cnt}x{name}")
        return lines

# =============================================================================
# 3) LOAD ALL_CARDS metadata (no images yet)
# =============================================================================
ALL_CARDS = {}
CARD_NAME_MAP = {}

for fname in os.listdir(CARD_DATA_DIR):
    if not fname.lower().endswith(".txt"):
        continue
    canonical = fname[:-4]
    lower_key = canonical.lower()
    try:
        ALL_CARDS[canonical] = Card(canonical)
        CARD_NAME_MAP[lower_key] = canonical
    except Exception as e:
        print(f"Warning: could not load card data for '{canonical}': {e}")

deck = Deck()

# =============================================================================
# 4) CATEGORY SUMMARY SETUP
# =============================================================================
category_order = ["Aliados", "Armas", "Talismanes", "Totems", "Oros", "Total"]
category_counts = {cat: 0 for cat in category_order}
category_labels = {}

# We also need a category_priority dict for sorting
category_priority = {
    "Aliados":    0,
    "Armas":      1,
    "Talismanes": 2,
    "Totems":     3,
    "Oros":       4
}

# =============================================================================
# 5) MANA CURVE DATA: cost 1..6 → {category: count}
# =============================================================================
cost_category_counts = {i: defaultdict(int) for i in range(1, 7)}

# =============================================================================
# 6) CALLBACK / UPDATE FUNCTIONS (must be defined before building GUI)
# =============================================================================

# 6.1) Update the category summary labels on the right
def update_category_summary():
    for cat in category_order:
        category_counts[cat] = 0
    for name, cnt in deck.card_counts.items():
        cat = ALL_CARDS[name].category
        category_counts[cat] += cnt
    category_counts["Total"] = deck.total_cards()
    for cat in category_order:
        category_labels[cat].config(text=str(category_counts[cat]))

# 6.2) Redraw the mana-curve histogram on the left
def update_mana_curve():
    for cost in range(1, 7):
        cost_category_counts[cost] = defaultdict(int)
    for name, cnt in deck.card_counts.items():
        card = ALL_CARDS[name]
        if card.cost is not None and 1 <= card.cost <= 6:
            cost_category_counts[card.cost][card.category] += cnt

    curve_canvas.delete("all")
    CANVAS_W = int(curve_canvas.cget("width"))
    CANVAS_H = int(curve_canvas.cget("height"))
    MARGIN_X = 20
    MARGIN_Y = 20
    BAR_SPACING = 10
    BAR_MAX = 20

    BAR_WIDTH = (CANVAS_W - 2*MARGIN_X - (6 - 1)*BAR_SPACING) / 6
    SEG_H = (CANVAS_H - 2*MARGIN_Y - 20) / BAR_MAX

    color_map = {
        "Aliados": "#FFA500",
        "Talismanes": "#ADD8E6",
        "Totems": "#006400",
        "Armas": "#800080"
    }

    for cost in range(1, 7):
        x0 = MARGIN_X + (cost - 1) * (BAR_WIDTH + BAR_SPACING)
        y_base = CANVAS_H - MARGIN_Y - 15
        stacked = 0
        for cat in ["Aliados", "Talismanes", "Totems", "Armas"]:
            n = cost_category_counts[cost].get(cat, 0)
            for i in range(n):
                y1 = y_base - (stacked + i) * SEG_H
                y0 = y1 - (SEG_H - 1)
                x1 = x0 + BAR_WIDTH
                curve_canvas.create_rectangle(
                    x0, y0, x1, y1, outline="black", fill=color_map[cat]
                )
            stacked += n

        # Draw cost label under each bar
        curve_canvas.create_text(
            x0 + BAR_WIDTH / 2,
            CANVAS_H - MARGIN_Y + 5,
            text=str(cost),
            anchor="n",
            font=("Helvetica", 9)
        )
        # Draw total count above each bar
        total = sum(cost_category_counts[cost].values())
        curve_canvas.create_text(
            x0 + BAR_WIDTH / 2,
            MARGIN_Y,
            text=str(total),
            anchor="s",
            font=("Helvetica", 9, "bold")
        )

# 6.3) Remove one copy of a clicked-on card in the deck display
def remove_card_by_click(event):
    clicked = deck_canvas.find_withtag("current")
    if not clicked:
        return
    item_id = clicked[0]
    if item_id not in image_id_to_name:
        return
    name = image_id_to_name[item_id]
    if deck.card_counts.get(name, 0) > 0:
        deck.remove_card(name, 1)
        update_category_summary()
        update_mana_curve()
        update_deck_display()
        update_consistency()

# 6.4) Add one copy of a clicked-on card in the deck display
def add_card_by_click(event):
    clicked = deck_canvas.find_withtag("current")
    if not clicked:
        return
    item_id = clicked[0]
    if item_id not in image_id_to_name:
        return
    name = image_id_to_name[item_id]
    current_total = deck.total_cards()
    if current_total >= 50:
        messagebox.showwarning("Max Deck Size", "Deck already has 50 cards. Cannot add more.")
        return
    deck.add_card(name, 1)
    update_category_summary()
    update_mana_curve()
    update_deck_display()
    update_consistency()

# 6.5) Redraw the deck as overlapping card images on the left
image_id_to_name = {}  # maps Canvas image IDs → card name

def card_sort_key(card_name):
    card = ALL_CARDS[card_name]
    cost_for_sort = card.cost if card.cost is not None else 999
    return (category_priority[card.category], cost_for_sort, card.name.lower())

def update_deck_display():
    flat_list = deck.list_all_copies()
    non_oro_list = [n for n in flat_list if ALL_CARDS[n].category != "Oros"]
    oros_counts = {n: cnt for n, cnt in deck.card_counts.items() if ALL_CARDS[n].category == "Oros"}

    sorted_non_oros = sorted(non_oro_list, key=card_sort_key)

    deck_canvas.delete("all")
    image_id_to_name.clear()

    CANVAS_W = int(deck_canvas.cget("width"))
    CARD_W = 60
    CARD_H = None

    DUP_OFFSET = 20
    SAME_CAT_OFFSET = 30
    DIFF_CAT_OFFSET = CARD_W

    X, Y = 0, 0
    CUR_CAT = None
    CUR_NAME = None

    # Draw all non-Oros cards in sorted order
    for name in sorted_non_oros:
        card = ALL_CARDS[name]
        if CUR_NAME is None:
            offset = 0
        else:
            if name == CUR_NAME:
                offset = DUP_OFFSET
            elif card.category == CUR_CAT:
                offset = SAME_CAT_OFFSET
            else:
                offset = DIFF_CAT_OFFSET

        cand_x = X + offset
        if cand_x + CARD_W > CANVAS_W:
            X = 0
            Y += (CARD_H + 20) if CARD_H else 140
            CUR_NAME = None
            CUR_CAT = None
            offset = 0
            cand_x = 0

        img = card.tk_image
        image_id = deck_canvas.create_image(cand_x, Y, image=img, anchor="nw", tags=("card",))
        image_id_to_name[image_id] = name

        CUR_NAME = name
        CUR_CAT = card.category
        CARD_H = img.height()
        X = cand_x

    # Force all “Oros” cards onto a new row
    if oros_counts:
        X = 0
        Y += (CARD_H + 20) if CARD_H else 140
        CUR_NAME = None
        CUR_CAT = None

        for name in sorted(oros_counts.keys()):
            cnt = oros_counts[name]
            card = ALL_CARDS[name]
            if name == "oro":
                img = card.tk_image
                oro_id = deck_canvas.create_image(X, Y, image=img, anchor="nw", tags=("card",))
                image_id_to_name[oro_id] = name
                deck_canvas.create_text(
                    X + CARD_W + 20,
                    Y + img.height() // 2,
                    text=f"x{cnt}",
                    anchor="w",
                    font=("Helvetica", 16, "bold"),
                    fill="black"
                )
                X += CARD_W + 100
            else:
                for i in range(cnt):
                    img = card.tk_image
                    image_id = deck_canvas.create_image(X, Y, image=img, anchor="nw", tags=("card",))
                    image_id_to_name[image_id] = name
                    X += DUP_OFFSET
                X += CARD_W

# 6.6) CONSISTENCY CALCULATIONS (8-card→7-card→6-card)
def update_consistency():
    total = deck.total_cards()
    if total != 50:
        for lbl in (
            lbl8_o2, lbl8_o3, lbl8_ali2, lbl8_avg,
            lbl7_o2, lbl7_o3, lbl7_ali2, lbl7_avg,
            lbl6_o2, lbl6_o3, lbl6_ali2, lbl6_avg
        ):
            lbl.config(text="")
        return

    # Count how many Oros and how many 2-cost Aliados are in the deck
    n_oros = category_counts["Oros"]
    n_ali2 = sum(
        deck.card_counts[name]
        for name in deck.card_counts
        if ALL_CARDS[name].category == "Aliados" and ALL_CARDS[name].cost == 2
    )

    # Hypergeometric helper: P(draw_n cards contains ≥ k items of that “total_type”)
    def hyper_at_least_k(total_type, draw_n, k, deck_size=50):
        prob = 0.0
        for i in range(k, draw_n + 1):
            if i > total_type or (draw_n - i) > (deck_size - total_type):
                continue
            prob += (
                math.comb(total_type, i)
                * math.comb(deck_size - total_type, draw_n - i)
                / math.comb(deck_size, draw_n)
            )
        return prob

    # Hypergeometric helper: P(draw_n cards contains ≥1 of that “total_type”)
    def hyper_at_least_one(total_type, draw_n, deck_size=50):
        if total_type == 0:
            return 0.0
        return 1 - (math.comb(deck_size - total_type, draw_n) / math.comb(deck_size, draw_n))

    # Average cost of deck (identical for any sample size)
    total_cost_all = 0
    total_cost_count = 0
    for name, cnt in deck.card_counts.items():
        c = ALL_CARDS[name].cost
        if c is not None:
            total_cost_all += c * cnt
            total_cost_count += cnt
    avg_cost_deck = (total_cost_all / total_cost_count) if total_cost_count > 0 else 0.0
    avg_cost_text = f"Avg cost: {avg_cost_deck:.2f}"

    # 8-card single-draw probabilities
    p8_o2   = hyper_at_least_k(n_oros, 8, 2)
    p8_o3   = hyper_at_least_k(n_oros, 8, 3)
    p8_ali2 = hyper_at_least_one(n_ali2, 8)

    # 7-card single-draw probabilities
    p7_o2   = hyper_at_least_k(n_oros, 7, 2)
    p7_o3   = hyper_at_least_k(n_oros, 7, 3)
    p7_ali2 = hyper_at_least_one(n_ali2, 7)

    # 6-card single-draw probabilities
    p6_o2   = hyper_at_least_k(n_oros, 6, 2)
    p6_o3   = hyper_at_least_k(n_oros, 6, 3)
    p6_ali2 = hyper_at_least_one(n_ali2, 6)

    # “Both” = ≥2 Oros AND ≥1 Ali2, computed via double-sum for each sample size
    def hyper_both(draw_n):
        prob = 0.0
        for i in range(2, draw_n + 1):               # i = # of Oros
            if i > n_oros:
                continue
            for j in range(1, draw_n - i + 1):       # j = # of Ali2
                if j > n_ali2 or i + j > draw_n:
                    continue
                rest_needed = draw_n - i - j
                if rest_needed > (50 - n_oros - n_ali2):
                    continue
                prob += (
                    math.comb(n_oros, i)
                    * math.comb(n_ali2, j)
                    * math.comb(50 - n_oros - n_ali2, rest_needed)
                    / math.comb(50, draw_n)
                )
        return prob

    p8_both = hyper_both(8)
    p7_both = hyper_both(7)
    p6_both = hyper_both(6)

    # ─── Combine for “8 → 7” (one mulligan) and “8 → 7 → 6” (two mulligans) ───
    # Combined “8 then (if fail) 7”:
    p8to7_o2   = p8_o2   + (1 - p8_o2)   * p7_o2
    p8to7_o3   = p8_o3   + (1 - p8_o3)   * p7_o3
    p8to7_ali2 = p8_ali2 + (1 - p8_ali2) * p7_ali2
    p8to7_both = p8_both + (1 - p8_both) * p7_both

    # Combined “8 then (if fail) 7 then (if that fails) 6”:
    p8to7to6_o2   = p8_o2   + (1 - p8_o2)   * p7_o2   + (1 - p8_o2)   * (1 - p7_o2)   * p6_o2
    p8to7to6_o3   = p8_o3   + (1 - p8_o3)   * p7_o3   + (1 - p8_o3)   * (1 - p7_o3)   * p6_o3
    p8to7to6_ali2 = p8_ali2 + (1 - p8_ali2) * p7_ali2 + (1 - p8_ali2) * (1 - p7_ali2) * p6_ali2
    p8to7to6_both = p8_both + (1 - p8_both) * p7_both + (1 - p8_both) * (1 - p7_both) * p6_both

    # ─── Update Labels (convert to percentage or text) ───
    lbl8_o2.  config(text=f"P(≥2 Oros): {p8_o2*100:5.2f}%")
    lbl8_o3.  config(text=f"P(≥3 Oros): {p8_o3*100:5.2f}%")
    lbl8_ali2.config(text=f"P(≥1 2-cost Aliados): {p8_ali2*100:5.2f}%")
    lbl8_avg. config(text=avg_cost_text)

    lbl7_o2.  config(text=f"P(≥2 Oros): {p8to7_o2*100:5.2f}%")
    lbl7_o3.  config(text=f"P(≥3 Oros): {p8to7_o3*100:5.2f}%")
    lbl7_ali2.config(text=f"P(≥1 2-cost Aliados): {p8to7_ali2*100:5.2f}%")
    lbl7_avg. config(text=avg_cost_text)

    lbl6_o2.  config(text=f"P(≥2 Oros): {p8to7to6_o2*100:5.2f}%")
    lbl6_o3.  config(text=f"P(≥3 Oros): {p8to7to6_o3*100:5.2f}%")
    lbl6_ali2.config(text=f"P(≥1 2-cost Aliados): {p8to7to6_ali2*100:5.2f}%")
    lbl6_avg. config(text=avg_cost_text)

# 6.7) Random-hand dealer: deal, mulligan, redraw functions
current_hand = []
hand_size = 0

def deal_hand():
    global current_hand, hand_size
    if deck.total_cards() != 50:
        messagebox.showerror("Error", "Deck must have exactly 50 cards to deal a hand.")
        return
    hand_size = 8
    draw_new_hand(hand_size)

def mulligan():
    global current_hand, hand_size
    if not current_hand:
        messagebox.showerror("Error", "No hand to mulligan. Press 'Deal Hand' first.")
        return
    if hand_size <= 1:
        messagebox.showerror("Error", "Cannot mulligan below 1 card.")
        return
    if deck.total_cards() != 50:
        messagebox.showerror("Error", "Deck must have exactly 50 cards to mulligan.")
        return
    hand_size -= 1
    draw_new_hand(hand_size)

def draw_new_hand(size):
    global current_hand
    flat = deck.list_all_copies()
    random.shuffle(flat)
    current_hand = flat[:size]
    display_hand(current_hand)

def display_hand(hand_list):
    deal_canvas.delete("all")

    cols = 4
    spacing = 10
    CARD_W = 60
    CARD_H = None

    count_aliados = 0
    count_oros = 0
    count_soporte = 0  # armas + totems + talismanes

    for idx, name in enumerate(hand_list):
        row = idx // cols
        col = idx % cols
        card = ALL_CARDS[name]
        img = card.tk_image
        if CARD_H is None:
            CARD_H = img.height()
        x = col * (CARD_W + spacing)
        y = row * (CARD_H + spacing)
        deal_canvas.create_image(x, y, image=img, anchor="nw")

        if card.category == "Aliados":
            count_aliados += 1
        elif card.category == "Oros":
            count_oros += 1
        elif card.category in ("Armas", "Totems", "Talismanes"):
            count_soporte += 1

    info_text.config(
        text=f"Aliados: {count_aliados}\nOros: {count_oros}\nSoporte: {count_soporte}"
    )

    if count_oros >= 2:
        lbl_two_oros.config(fg="green")
    else:
        lbl_two_oros.config(fg="red")

    has_1or2_ali = any(
        ALL_CARDS[name].category == "Aliados" and ALL_CARDS[name].cost in (1, 2)
        for name in hand_list
    )

    if has_1or2_ali:
        lbl_turn1.config(fg="green")
    else:
        lbl_turn1.config(fg="red")

# 6.8) Simulate 1000 random hands
def simulate_1000_hands():
    if deck.total_cards() != 50:
        messagebox.showerror("Error", "Deck must have exactly 50 cards to simulate.")
        return

    flat_deck_base = deck.list_all_copies()
    count_at_least_2_oros = 0
    count_turn1_play = 0
    count_great = 0

    for _ in range(1000):
        random.shuffle(flat_deck_base)
        hand = flat_deck_base[:8]

        oros_in_hand = sum(1 for n in hand if ALL_CARDS[n].category == "Oros")
        has_1or2_ali = any(
            ALL_CARDS[n].category == "Aliados" and ALL_CARDS[n].cost in (1, 2)
            for n in hand
        )

        cond_oros = (oros_in_hand >= 2)
        cond_turn1 = has_1or2_ali

        if cond_oros:
            count_at_least_2_oros += 1
        if cond_turn1:
            count_turn1_play += 1
        if cond_oros and cond_turn1:
            count_great += 1

    lbl_sim_two_oros.config(text=f"Hands ≥2 Oros: {count_at_least_2_oros}")
    lbl_sim_turn1   .config(text=f"Hands Turn1 Play: {count_turn1_play}")
    lbl_sim_great   .config(text=f"Great hands: {count_great}")

# 6.9) Save / Import Deck Callbacks
def save_deck_gui():
    fname = save_entry.get().strip()
    if not fname:
        messagebox.showerror("Error", "Filename cannot be empty.")
        return
    decks_folder = DECKS_DIR
    if not os.path.isdir(decks_folder):
        os.makedirs(decks_folder)
    path = os.path.join(decks_folder, f"{fname}.txt")
    with open(path, "w", encoding="utf-8") as f:
        for line in deck.as_save_lines():
            f.write(line + "\n")
    messagebox.showinfo("Saved", f"Deck saved to {path}")
    refresh_deck_dropdown()

def get_deck_files():
    files = []
    for f in os.listdir(DECKS_DIR):
        if f.lower().endswith(".txt"):
            files.append(f)
    return sorted(files)

def refresh_deck_dropdown():
    menu = deck_option["menu"]
    menu.delete(0, "end")
    files = get_deck_files()
    if not files:
        deck_var.set("No decks")
    else:
        deck_var.set(files[0])
        for filename in files:
            menu.add_command(label=filename, command=lambda value=filename: deck_var.set(value))

def import_deck_dropdown():
    selected = deck_var.get()
    if not selected or selected in ("Select deck", "No decks"):
        messagebox.showerror("Error", "No deck selected to import.")
        return

    file_path = os.path.join(DECKS_DIR, selected)
    if not os.path.isfile(file_path):
        messagebox.showerror("Error", f"Deck file not found:\n{file_path}")
        return

    deck.card_counts.clear()
    total_added = 0
    truncated = False

    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or "x" not in line:
                continue
            parts = line.split("x", 1)
            try:
                cnt = int(parts[0])
            except ValueError:
                continue
            card_name = parts[1]
            lookup = card_name.lower()
            if lookup not in CARD_NAME_MAP:
                continue
            canonical = CARD_NAME_MAP[lookup]
            capacity_left = 50 - total_added
            if capacity_left <= 0:
                truncated = True
                break
            if cnt > capacity_left:
                deck.card_counts[canonical] = capacity_left
                total_added += capacity_left
                truncated = True
                break
            else:
                deck.card_counts[canonical] = cnt
                total_added += cnt

    update_category_summary()
    update_mana_curve()
    update_deck_display()
    update_consistency()

    if truncated:
        messagebox.showwarning("Import Truncated", "Deck exceeded 50 cards; extras omitted.")
    else:
        messagebox.showinfo("Import Complete", f"Imported deck from:\n{selected}")

# =============================================================================
# 7) GUI SETUP STARTS HERE
# =============================================================================
root = tk.Tk()
root.title("Mitos y Leyendas Deck Builder")
root.configure(bg="#f5f1e6")
root.geometry("1200x970")

# ─ Layout: left_container, divider, right_panel ─
left_container = tk.Frame(root, bg="#f5f1e6")
divider        = tk.Frame(root, bg="black", width=4)
right_panel    = tk.Frame(root, bg="#f5f1e6")

left_container.grid(row=0, column=0, rowspan=4, sticky="nsew")
divider       .grid(row=0, column=1, rowspan=4, sticky="ns")
right_panel   .grid(row=0, column=2, rowspan=4, sticky="nsew")

root.grid_columnconfigure(0, weight=0)
root.grid_columnconfigure(1, weight=0)
root.grid_columnconfigure(2, weight=1)
root.grid_rowconfigure(0, weight=6)
root.grid_rowconfigure(1, weight=3)
root.grid_rowconfigure(2, weight=3)
root.grid_rowconfigure(3, weight=1)

# =============================================================================
# 8) Deck Display (Left Container)
# =============================================================================
deck_canvas = tk.Canvas(left_container, width=700, height=300, bg="#f5f1e6", bd=0, highlightthickness=0)
deck_canvas.grid(row=0, column=0, padx=10, pady=10, sticky="nw")
deck_canvas.bind("<Button-1>", lambda e: remove_card_by_click(e))
deck_canvas.bind("<Button-3>", lambda e: add_card_by_click(e))

# =============================================================================
# 9) Category Summary (Left Container)
# =============================================================================
summary_frame = tk.Frame(left_container, bg="#f5f1e6")
summary_frame.grid(row=0, column=1, padx=(0,20), pady=10, sticky="ne")

for idx, cat in enumerate(category_order):
    lbl_name = tk.Label(
        summary_frame,
        text=f"{cat}:",
        font=("Helvetica", 10, "bold"),
        bg="#f5f1e6"
    )
    lbl_count = tk.Label(
        summary_frame,
        text="0",
        font=("Helvetica", 10),
        bg="#f5f1e6"
    )
    lbl_name.grid(row=idx, column=0, sticky="w")
    lbl_count.grid(row=idx, column=1, sticky="e")
    category_labels[cat] = lbl_count

# =============================================================================
# 10) Mana Curve (Left Container)
# =============================================================================
curve_canvas = tk.Canvas(left_container, width=400, height=200, bg="#e0dacd", bd=0, highlightthickness=0)
curve_canvas.grid(row=1, column=0, columnspan=2, padx=10, pady=(0,10), sticky="nw")

# =============================================================================
# 11) Bottom Menu (Left Container)
# =============================================================================
menu_frame = tk.Frame(left_container, bg="#f5f1e6")
menu_frame.grid(row=3, column=0, columnspan=2, pady=(10,20), sticky="w")

tk.Label(menu_frame, text="Card name:", bg="#f5f1e6").grid(row=0, column=0, sticky="e")
card_name_entry = tk.Entry(menu_frame, width=25)
card_name_entry.grid(row=0, column=1, padx=(5,20))

def select_all_on_focus(event):
    event.widget.selection_range(0, tk.END)
card_name_entry.bind("<FocusIn>", select_all_on_focus)

def autocomplete(event):
    key = event.keysym
    if key in ("BackSpace", "Left", "Right", "Delete", "Return", "Tab",
               "Shift_L", "Shift_R", "Control_L", "Control_R"):
        return
    typed = card_name_entry.get()
    low = typed.lower()
    matches = [n for n in CARD_NAME_MAP.keys() if n.startswith(low)]
    if matches and typed:
        full = CARD_NAME_MAP[matches[0]]
        if full.lower().startswith(low) and full != typed:
            card_name_entry.delete(0, tk.END)
            card_name_entry.insert(0, full)
            card_name_entry.selection_range(len(typed), tk.END)

def accept_autocomplete(event):
    card_name_entry.icursor(tk.END)
    card_name_entry.selection_clear()

card_name_entry.bind("<KeyRelease>", autocomplete)
card_name_entry.bind("<Return>", accept_autocomplete)

tk.Label(menu_frame, text="Quantity:", bg="#f5f1e6").grid(row=0, column=2, sticky="e")
qty_entry = tk.Entry(menu_frame, width=5)
qty_entry.grid(row=0, column=3, padx=(5,20))

def add_card_gui():
    user_input = card_name_entry.get().strip()
    lookup = user_input.lower()
    if lookup not in CARD_NAME_MAP:
        messagebox.showerror("Error", f"Card '{user_input}' not found.")
        return
    canonical = CARD_NAME_MAP[lookup]
    try:
        qty = int(qty_entry.get().strip())
        if qty <= 0:
            raise ValueError
    except ValueError:
        messagebox.showerror("Error", "Quantity must be a positive integer.")
        return

    current_total = deck.total_cards()
    capacity_left = 50 - current_total
    if capacity_left <= 0:
        messagebox.showwarning("Max Deck Size", "Deck already has 50 cards.")
        return

    if qty > capacity_left:
        deck.add_card(canonical, capacity_left)
        messagebox.showwarning(
            "Partial Add",
            f"Only {capacity_left} card(s) added to reach 50. Deck is now full."
        )
    else:
        deck.add_card(canonical, qty)

    update_category_summary()
    update_mana_curve()
    update_deck_display()
    update_consistency()

add_button = tk.Button(menu_frame, text="Add Card", command=add_card_gui)
add_button.grid(row=0, column=4, padx=(5,20))

def remove_card_gui():
    user_input = card_name_entry.get().strip()
    lookup = user_input.lower()
    if lookup not in CARD_NAME_MAP:
        messagebox.showerror("Error", f"Card '{user_input}' not found.")
        return
    canonical = CARD_NAME_MAP[lookup]
    if canonical not in deck.card_counts or deck.card_counts[canonical] == 0:
        messagebox.showerror("Error", f"Card '{canonical}' is not in deck.")
        return
    try:
        qty = int(qty_entry.get().strip())
        if qty <= 0:
            raise ValueError
    except ValueError:
        messagebox.showerror("Error", "Quantity must be a positive integer.")
        return

    deck.remove_card(canonical, qty)
    update_category_summary()
    update_mana_curve()
    update_deck_display()
    update_consistency()

remove_button = tk.Button(menu_frame, text="Remove Card", command=remove_card_gui)
remove_button.grid(row=0, column=5, padx=(5,20))

tk.Label(menu_frame, text="Save as:", bg="#f5f1e6").grid(row=1, column=0, sticky="e", pady=(10,0))
save_entry = tk.Entry(menu_frame, width=20)
save_entry.grid(row=1, column=1, padx=(5,20), pady=(10,0))

save_button = tk.Button(menu_frame, text="Save Deck", command=save_deck_gui)
save_button.grid(row=1, column=2, padx=(5,20), pady=(10,0))

tk.Label(menu_frame, text="Import deck:", bg="#f5f1e6").grid(row=1, column=3, sticky="e", pady=(10,0))

deck_var = tk.StringVar()
deck_var.set("Select deck")

deck_option = tk.OptionMenu(menu_frame, deck_var, *get_deck_files())
deck_option.config(width=20)
deck_option.grid(row=1, column=4, padx=(5,20), pady=(10,0))

refresh_deck_dropdown()

import_button = tk.Button(menu_frame, text="Import Deck", command=import_deck_dropdown)
import_button.grid(row=1, column=5, padx=(5,20), pady=(10,0))

quit_button = tk.Button(menu_frame, text="Quit", command=root.destroy)
quit_button.grid(row=1, column=6, padx=(5,0), pady=(10,0))

# =============================================================================
# 12) CONSISTENCY SECTION (Right Panel)
# =============================================================================
consistency_frame = tk.LabelFrame(
    right_panel,
    text="Consistency",
    bg="#f5f1e6",
    font=("Helvetica", 10, "bold"),
    padx=5,
    pady=5
)
consistency_frame.grid(row=0, column=0, padx=10, pady=(10,5), sticky="nwe")

# Build three side-by-side columns: 8-card, 7-card, 6-card
col8 = tk.Frame(consistency_frame, bg="#f5f1e6")
col7 = tk.Frame(consistency_frame, bg="#f5f1e6")
col6 = tk.Frame(consistency_frame, bg="#f5f1e6")

col8.grid(row=0, column=0, padx=(0,10), sticky="nw")
col7.grid(row=0, column=1, padx=(0,10), sticky="nw")
col6.grid(row=0, column=2, sticky="nw")

LABEL_FONT = ("Helvetica", 9)

# 8-card column
tk.Label(col8, text="8-card draw", font=("Helvetica", 10, "bold"), bg="#f5f1e6").grid(row=0, column=0, sticky="w", pady=(0,4))
lbl8_o2   = tk.Label(col8, text="P(≥2 Oros): 0.00%",         font=LABEL_FONT, bg="#f5f1e6")
lbl8_o3   = tk.Label(col8, text="P(≥3 Oros): 0.00%",         font=LABEL_FONT, bg="#f5f1e6")
lbl8_ali2 = tk.Label(col8, text="P(≥1 2-cost Aliados): 0.00%", font=LABEL_FONT, bg="#f5f1e6")
lbl8_avg  = tk.Label(col8, text="Avg cost: 0.00",             font=LABEL_FONT, bg="#f5f1e6")

lbl8_o2.grid(row=1, column=0, sticky="w")
lbl8_o3.grid(row=2, column=0, sticky="w")
lbl8_ali2.grid(row=3, column=0, sticky="w")
lbl8_avg.grid(row=4, column=0, sticky="w", pady=(0,2))

# 7-card column (one mulligan)
tk.Label(col7, text="8→7 mulligan", font=("Helvetica", 10, "bold"), bg="#f5f1e6").grid(row=0, column=0, sticky="w", pady=(0,4))
lbl7_o2   = tk.Label(col7, text="P(≥2 Oros): 0.00%",         font=LABEL_FONT, bg="#f5f1e6")
lbl7_o3   = tk.Label(col7, text="P(≥3 Oros): 0.00%",         font=LABEL_FONT, bg="#f5f1e6")
lbl7_ali2 = tk.Label(col7, text="P(≥1 2-cost Aliados): 0.00%", font=LABEL_FONT, bg="#f5f1e6")
lbl7_avg  = tk.Label(col7, text="Avg cost: 0.00",             font=LABEL_FONT, bg="#f5f1e6")

lbl7_o2.grid(row=1, column=0, sticky="w")
lbl7_o3.grid(row=2, column=0, sticky="w")
lbl7_ali2.grid(row=3, column=0, sticky="w")
lbl7_avg.grid(row=4, column=0, sticky="w", pady=(0,2))

# 6-card column (two mulligans)
tk.Label(col6, text="8→7→6 mulligan", font=("Helvetica", 10, "bold"), bg="#f5f1e6").grid(row=0, column=0, sticky="w", pady=(0,4))
lbl6_o2   = tk.Label(col6, text="P(≥2 Oros): 0.00%",         font=LABEL_FONT, bg="#f5f1e6")
lbl6_o3   = tk.Label(col6, text="P(≥3 Oros): 0.00%",         font=LABEL_FONT, bg="#f5f1e6")
lbl6_ali2 = tk.Label(col6, text="P(≥1 2-cost Aliados): 0.00%", font=LABEL_FONT, bg="#f5f1e6")
lbl6_avg  = tk.Label(col6, text="Avg cost: 0.00",             font=LABEL_FONT, bg="#f5f1e6")

lbl6_o2.grid(row=1, column=0, sticky="w")
lbl6_o3.grid(row=2, column=0, sticky="w")
lbl6_ali2.grid(row=3, column=0, sticky="w")
lbl6_avg.grid(row=4, column=0, sticky="w", pady=(0,2))

# =============================================================================
# 13) RANDOM HAND DEALER (Right Panel)
# =============================================================================
hand_frame = tk.LabelFrame(
    right_panel,
    text="Random Hand Dealer",
    bg="#f5f1e6",
    font=("Helvetica", 10, "bold"),
    padx=5,
    pady=5
)
hand_frame.grid(row=1, column=0, padx=10, pady=(5,10), sticky="nwe")

# Two-row canvas (height=180 so both rows fit)
deal_canvas = tk.Canvas(hand_frame, width=380, height=180, bg="#f5f1e6", bd=0, highlightthickness=0)
deal_canvas.grid(row=0, column=0, rowspan=2, padx=(5,5), pady=(5,5), sticky="nw")

# Info text box (next to first row of cards)
info_text = tk.Label(
    hand_frame,
    text="Aliados: 0\nOros: 0\nSoporte: 0",
    justify="left",
    bg="#f5f1e6",
    font=("Helvetica", 10, "bold")
)
info_text.grid(row=0, column=1, padx=(5,10), pady=(5,5), sticky="nw")

# Simulation box (next to second row of cards)
sim_frame = tk.Frame(hand_frame, bg="#f5f1e6")
sim_frame.grid(row=1, column=1, padx=(5,10), pady=(5,5), sticky="nw")

hundred_button = tk.Button(sim_frame, text="1000 Hands", width=10, command=lambda: simulate_1000_hands())
hundred_button.grid(row=0, column=0, padx=(0,5))

lbl_sim_two_oros = tk.Label(sim_frame, text="Hands ≥2 Oros: 0", bg="#f5f1e6", font=("Helvetica", 10))
lbl_sim_turn1    = tk.Label(sim_frame, text="Hands Turn1 Play: 0", bg="#f5f1e6", font=("Helvetica", 10))
lbl_sim_great    = tk.Label(sim_frame, text="Great hands: 0", bg="#f5f1e6", font=("Helvetica", 10))

lbl_sim_two_oros.grid(row=1, column=0, sticky="w")
lbl_sim_turn1   .grid(row=2, column=0, sticky="w")
lbl_sim_great   .grid(row=3, column=0, sticky="w")

# Bottom row (2 Oros, Deal, Mulligan, Turn 1 play)
hand_button_frame = tk.Frame(hand_frame, bg="#f5f1e6")
hand_button_frame.grid(row=2, column=0, columnspan=2, pady=(5,5), sticky="w")

lbl_two_oros = tk.Label(
    hand_button_frame,
    text="2 Oros",
    font=("Helvetica", 10, "bold"),
    fg="black",
    bg="#f5f1e6"
)
lbl_two_oros.grid(row=0, column=0, padx=(0,20))

deal_button = tk.Button(hand_button_frame, text="Deal Hand", width=10, command=lambda: deal_hand())
deal_button.grid(row=0, column=1, padx=(0,10))

mulligan_button = tk.Button(hand_button_frame, text="Mulligan", width=10, command=lambda: mulligan())
mulligan_button.grid(row=0, column=2, padx=(0,20))

lbl_turn1 = tk.Label(
    hand_button_frame,
    text="Turn 1 play",
    font=("Helvetica", 10, "bold"),
    fg="black",
    bg="#f5f1e6"
)
lbl_turn1.grid(row=0, column=3, padx=(0,0))

# =============================================================================
# 14) LOAD ALL CARD IMAGES & INITIAL DRAW
# =============================================================================
for card in ALL_CARDS.values():
    try:
        card.load_image()
    except Exception as e:
        print(f"Warning: could not load image for '{card.name}': {e}")

update_category_summary()
update_mana_curve()
update_deck_display()
update_consistency()

root.mainloop()
