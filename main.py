import os
import sys
import ast
import random
import math
from ttkthemes import ThemedTk
import tkinter as tk
from tkinter import ttk, messagebox
from collections import Counter, defaultdict
from PIL import Image, ImageTk

# =============================================================================
# MANEJO DE RUTAS PARA SCRIPT VS. EXE
# =============================================================================
def get_base_path():
    """
    Devuelve la carpeta donde residen nuestros recursos:
    - card_data/
    - card_images/
    - restrictions/
    - ui_images/
    """
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return sys._MEIPASS

    script_dir = os.path.abspath(os.path.dirname(__file__))
    for sub in ("card_data", "card_images", "restrictions", "ui_images"):
        if not os.path.isdir(os.path.join(script_dir, sub)):
            break
    else:
        return script_dir

    cwd = os.getcwd()
    for sub in ("card_data", "card_images", "restrictions", "ui_images"):
        if not os.path.isdir(os.path.join(cwd, sub)):
            break
    else:
        return cwd

    return script_dir
THUMB_W, THUMB_H = 80, 120  
BASE_PATH = get_base_path()
CARD_DATA_DIR    = os.path.join(BASE_PATH, "card_data")
CARD_IMAGES_DIR  = os.path.join(BASE_PATH, "card_images")
DECKS_DIR        = os.path.join(BASE_PATH, "decks")
RESTRICTIONS_DIR = os.path.join(BASE_PATH, "restrictions")
UI_IMAGES_DIR    = os.path.join(BASE_PATH, "ui_images")
DECK_CANVAS_LEFT_MARGIN = 14
DECK_CANVAS_TOP_MARGIN  = 10
DECK_CANVAS_RIGHT_MARGIN = 10
# Separación vertical entre filas
DECK_VERTICAL_GUTTER = 7
# =============================================================================
# IMPORTAR CLASE Card DESDE cards.py
# =============================================================================
from cards import Card, CARD_DATA_DIR, CARD_IMAGES_DIR, load_restricted_limits, SAGA_MAP, RACES_BY_SAGA

# =============================================================================
# CARGAR RESTRICCIONES
# =============================================================================
CARD_MAX_DEFAULT = 3
restricted_limits = {}
for sub in ("pbx", "reborn"):
    subdir = os.path.join(RESTRICTIONS_DIR, sub)
    filepath = os.path.join(subdir, "restricted_cards.txt")
    if os.path.isfile(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or "x" not in line:
                    continue
                parts = line.split("x", 1)
                try:
                    lim = int(parts[0])
                    name = parts[1].strip()
                    if name in restricted_limits:
                        restricted_limits[name] = min(restricted_limits[name], lim)
                    else:
                        restricted_limits[name] = lim
                except:
                    continue

# =============================================================================
# MAPEO DE SAGAS Y RAZAS
# =============================================================================
SAGA_FOLDERS = {
    "Espada Sagrada":    ["espada_sagrada", "cruzadas"],
    "Helenica":          ["helenica", "imperio"],
    "Hijos de Daana":    ["hijos_de_daana", "tierras_altas"],
    "Dominios de Ra":    ["dominios_de_ra", "encrucijada"]
}

SAGA_MAP = {
    "esp": "Espada Sagrada",
    "hel": "Helenica",
    "hdd": "Hijos de Daana",
    "ddr": "Dominios de Ra"
}

RACES_BY_SAGA = {
    "Espada Sagrada": ["dragon", "faerie", "caballero"],
    "Helenica":       ["heroe",   "olimpico", "titan"],
    "Hijos de Daana": ["defensor","desafiante","sombra"],
    "Dominios de Ra": ["faraon",  "eterno",    "sacerdote"]
}

# =============================================================================
# IMPORTAR CLASE DECK Y FUNCIONES DE deck.py
# =============================================================================
from deck import Deck, deck, ALL_CARDS, CARD_NAME_MAP
from deck import is_card_valid_for_filters, can_add_card
from deck import get_deck_files, load_deck_from_file, save_deck_to_file, restricted_limits

# =============================================================================
# CARGAR TODAS LAS CARTAS
# =============================================================================
ALL_CARDS     = {}
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
        print(f"Advertencia: no se pudo cargar datos de '{canonical}': {e}")
# =============================================================================
# RESUMEN DE CATEGORÍAS
# =============================================================================
category_order = ["Aliados", "Armas", "Talismanes", "Totems", "Oros", "Total"]
category_counts = {cat: 0 for cat in category_order}
category_labels = {}
category_priority = {
    "Aliados":    0,
    "Armas":      1,
    "Talismanes": 2,
    "Totems":     3,
    "Oros":       4
}

# =============================================================================
# DATOS PARA CURVA DE MANÁ
# =============================================================================
cost_category_counts = {i: defaultdict(int) for i in range(0, 11)}

# =============================================================================
# VARIABLES GLOBALES DE FILTROS
# =============================================================================
current_saga   = None
current_race   = None
current_format = None

# =============================================================================
# FUNCIONES AUXILIARES DE VALIDACIÓN Y FILTRADO
# =============================================================================
def is_card_valid_for_filters(name):
    if name.lower() == "oro":
        return True
    if current_saga is None or current_race is None or current_format is None:
        return False
    carta = ALL_CARDS[name]
    if carta.saga != current_saga:
        return False
    if carta.format != current_format:
        return False
    if carta.category == "Aliados" and carta.race != current_race:
        return False
    return True

def can_add_card(name, qty):
    internal = name.lower()
    # ── SPECIAL CASE: unlimited "oro" ──
    if internal == "oro":
        total_actual = deck.total_cards()
        if total_actual + qty > 50:
            return False, "El mazo no puede exceder 50 cartas."
        return True, ""

    # ── NORMAL CASE FOR ALL OTHER CARDS ──
    if current_saga is None or current_race is None or current_format is None:
        return False, "Debes elegir Saga, Raza y Formato primero."

    carta = ALL_CARDS[name]
    if not is_card_valid_for_filters(name):
        return False, "Esta carta no cumple los filtros de Saga/Raza/Formato."

    total_actual = deck.total_cards()
    if total_actual + qty > 50:
        return False, "El mazo no puede exceder 50 cartas."

    max_allowed = restricted_limits.get(name, CARD_MAX_DEFAULT)
    ya_tengo = deck.card_counts.get(name, 0)
    if ya_tengo + qty > max_allowed:
        return False, f"No puedes tener más de {max_allowed} copias de '{name}'."

    return True, ""


def update_stats():
    total_cost = 0
    total_count = 0
    total_strength = 0
    total_aliados = 0

    for nm, cnt in deck.card_counts.items():
        card = ALL_CARDS[nm]
        if card.cost is not None:
            total_cost += card.cost * cnt
            total_count += cnt
        if card.category == "Aliados":
            total_strength += card.strength * cnt
            total_aliados += cnt

    avg_cost = (total_cost / total_count) if total_count > 0 else 0.0
    avg_str  = (total_strength / total_aliados) if total_aliados > 0 else 0.0

    lbl_avg_cost.config(text=f"Costo promedio (mazo): {avg_cost:.2f}")
    lbl_avg_str.config(text=f"Fuerza aliados promedio: {avg_str:.2f}")

# =============================================================================
# FUNCIONES GUI: Añadir, Quitar, Importar, Guardar
# =============================================================================
def add_card_gui():
    display_name = card_entry.get().strip()
    if not display_name:
        messagebox.showwarning("Error", "Debes ingresar un nombre de carta.")
        return
    internal = display_name.lower().replace(" ", "-")
    if internal not in ALL_CARDS:
        messagebox.showwarning("No se encontró", f"Carta \"{display_name}\" no existe.")
        return
    can_add, reason = can_add_card(internal, int(qty_var.get()))
    if not can_add:
        messagebox.showwarning("No permitido", reason)
        return
    deck.add_card(internal, int(qty_var.get()))
    update_category_summary()
    update_mana_curve()
    update_deck_display()
    update_consistency()
    update_stats()

def remove_card_gui():
    display_name = card_entry.get().strip()
    if not display_name:
        messagebox.showwarning("Error", "Debes ingresar un nombre de carta.")
        return
    internal = display_name.lower().replace(" ", "-")
    if internal not in ALL_CARDS or deck.card_counts.get(internal, 0) == 0:
        messagebox.showwarning("Error", f"No hay copias de \"{display_name}\" para quitar.")
        return
    deck.remove_card(internal, int(qty_var.get()))
    update_category_summary()
    update_mana_curve()
    update_deck_display()
    update_consistency()
    update_stats()

def import_deck_dropdown():
    choice = deck_var.get()
    if choice == "Sin mazos":
        messagebox.showwarning("Error", "No hay mazos para importar.")
        return
    path = os.path.join(DECKS_DIR, choice)
    if not os.path.isfile(path):
        messagebox.showwarning("Error", f"No se encontró {path}")
        return

    # 1) Leer todas las líneas primero
    entries = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or "x" not in line:
                continue
            parts = line.split("x", 1)
            try:
                qty = int(parts[0])
            except ValueError:
                continue
            name = parts[1].strip()
            lookup = name.lower()
            if lookup not in CARD_NAME_MAP:
                messagebox.showwarning("No permitido", f"Carta \"{name}\" no existe.")
                return
            canonical = CARD_NAME_MAP[lookup]
            entries.append((canonical, qty))

    # 2) Validar filtros (salvo "oro")
    for canonical, _ in entries:
        if canonical.lower() != "oro" and not is_card_valid_for_filters(canonical):
            messagebox.showwarning(
                "No permitido",
                f"La carta \"{canonical}\" no cumple los filtros de Saga/Raza/Formato."
            )
            return

    # 3) Vaciar y recargar
    deck.card_counts.clear()
    for canonical, qty in entries:
        max_allowed = restricted_limits.get(canonical, CARD_MAX_DEFAULT)
        actual_add = min(qty, 50 - deck.total_cards(), max_allowed)
        if actual_add > 0:
            deck.card_counts[canonical] = actual_add

    deck.is_saved = True

    # 4) Actualizar la interfaz
    update_category_summary()
    update_mana_curve()
    update_deck_display()
    update_consistency()
    update_stats()

    # 5) Rellenar "Guardar como" con el nombre de mazo (sin extensión)
    save_entry.delete(0, tk.END)
    save_entry.insert(0, os.path.splitext(choice)[0])

    # 6) Refrescar lista de mazos
    refresh_deck_dropdown()

def save_deck_gui():
    fname = save_entry.get().strip()
    if not fname:
        messagebox.showerror("Error", "El nombre de archivo no puede estar vacío.")
        return

    path = save_deck_to_file(deck.card_counts, fname)
    messagebox.showinfo("Guardado", f"Mazo guardado en:\n{path}")
    deck.is_saved = True
    refresh_deck_dropdown()

# =============================================================================
# ACTUALIZACIÓN DE INTERFAZ: Categorías, Maná, Deck Display, Consistencia
# =============================================================================
def update_category_summary():
    for cat in category_order:
        category_counts[cat] = 0
    for nm, cnt in deck.card_counts.items():
        cat = ALL_CARDS[nm].category
        category_counts[cat] += cnt
    category_counts["Total"] = deck.total_cards()
    for cat in category_order:
        category_labels[cat].config(text=str(category_counts[cat]))

def update_mana_curve():
    for cost in range(0, 11):
        cost_category_counts[cost] = defaultdict(int)
    for nm, cnt in deck.card_counts.items():
        card = ALL_CARDS[nm]
        if card.cost is not None and 0 <= card.cost <= 10:
            cost_category_counts[card.cost][card.category] += cnt

    curve_canvas.delete("all")
    # ── draw horizontal divider above cost labels ──
    CANVAS_W = int(curve_canvas.cget("width"))
    CANVAS_H = int(curve_canvas.cget("height"))
    MARGIN_Y = 20
    y_div = CANVAS_H - MARGIN_Y
    curve_canvas.create_line(0, y_div, CANVAS_W, y_div, fill="black", width=2)

    CANVAS_W = int(curve_canvas.cget("width"))
    CANVAS_H = int(curve_canvas.cget("height"))
    MARGIN_X = 20
    MARGIN_Y = 20
    BAR_SPACING = 5
    BAR_MAX = 20
    BAR_COUNT = 11
    BAR_WIDTH = (CANVAS_W - 2*MARGIN_X - (BAR_COUNT - 1)*BAR_SPACING) / BAR_COUNT
    SEG_H = (CANVAS_H - 2*MARGIN_Y - 20) / BAR_MAX
    color_map = {
        "Aliados":    "#FFA500",
        "Talismanes": "#ADD8E6",
        "Totems":     "#006400",
        "Armas":      "#800080"
    }
    # ── draw vertical dividers ──
    bg_color = root.cget('bg')
    line_width = 2  # thickness in pixels
    for i in range(1, BAR_COUNT):
        x = MARGIN_X + i * (BAR_WIDTH + BAR_SPACING) - (BAR_SPACING / 2)
        curve_canvas.create_line(
            x, 0,
            x, CANVAS_H,
            fill=bg_color,
            width=line_width
        )
    for cost_idx in range(0, 11):
        x0 = MARGIN_X + cost_idx * (BAR_WIDTH + BAR_SPACING)
        y_base = CANVAS_H - MARGIN_Y - 15
        stacked = 0
        for cat in ["Aliados", "Talismanes", "Totems", "Armas"]:
            n = cost_category_counts[cost_idx].get(cat, 0)
            for i in range(n):
                y1 = y_base - (stacked + i) * SEG_H
                y0 = y1 - (SEG_H - 1)
                x1 = x0 + BAR_WIDTH
                curve_canvas.create_rectangle(
                    x0, y0, x1, y1, outline="black", fill=color_map[cat]
                )
            stacked += n
        curve_canvas.create_text(
            x0 + BAR_WIDTH / 2,
            CANVAS_H - MARGIN_Y + 5,
            text=str(cost_idx),
            anchor="n",
            font=("Tahoma", 9, "bold")
        )
        total = sum(cost_category_counts[cost_idx].values())
        curve_canvas.create_text(
            x0 + BAR_WIDTH / 2,
            MARGIN_Y,
            text=str(total),
            anchor="s",
            font=("Tahoma", 9, "bold")
        )

image_id_to_name = {}
resized_images = {}
def card_sort_key(card_name):
    card = ALL_CARDS[card_name]
    cost_for_sort = card.cost if card.cost is not None else 999
    return (category_priority[card.category], cost_for_sort, card.name.lower())

def update_deck_display():
    """Redraw the deck canvas; keep duplicates together, wrap before overflow,
       always draw Oro as the very last row, left-justified, with 'oro' last."""
    deck_canvas.delete("all")
    try:
        _draw_deck_bg()
    except:
        pass

    image_id_to_name.clear()
    flat = deck.list_all_copies()
    width_limit = deck_canvas.winfo_width() - DECK_CANVAS_RIGHT_MARGIN

    # Lazy-load any missing tk_images
    for name in set(flat):
        card = ALL_CARDS.get(name)
        if card and (not hasattr(card, "tk_image") or card.tk_image is None):
            try:
                card.load_image()
            except:
                pass

    x = DECK_CANVAS_LEFT_MARGIN
    y = DECK_CANVAS_TOP_MARGIN
    last_h = 0

    def place_block(name, count=1):
        """Place 'count' copies of 'name' without splitting them across rows."""
        nonlocal x, y, last_h
        card = ALL_CARDS[name]
        w, h = card.tk_image.width(), card.tk_image.height()
        last_h = max(last_h, h)

        total_block_width = w + (count - 1) * (w // 4)
        if x + total_block_width > width_limit:
            x = DECK_CANVAS_LEFT_MARGIN
            y += last_h + DECK_VERTICAL_GUTTER
            last_h = h

        for i in range(count):
            xi = x + i * (w // 4)
            img_id = deck_canvas.create_image(xi, y,
                                             image=card.tk_image,
                                             anchor="nw",
                                             tags=("card",))
            image_id_to_name[img_id] = name

        x += total_block_width

    # ── Draw NON-Oro cards ──
    from collections import Counter
    counts = Counter(flat)
    non_oros = [n for n in flat if ALL_CARDS[n].category != "Oros"]
    for name in sorted(set(non_oros), key=card_sort_key):
        place_block(name, counts[name])

    # ── Draw Oro cards in final row, left-justified, with 'oro' last ──
    oro_counts = [(n, c) for n, c in deck.card_counts.items()
                  if ALL_CARDS[n].category == "Oros"]
    if oro_counts:
        # new line
        x = DECK_CANVAS_LEFT_MARGIN
        y += last_h + DECK_VERTICAL_GUTTER
        last_h = 0

        # separate the big "oro" entry
        small_oros = [(n, c) for n, c in oro_counts if n.lower() != "oro"]
        big_oros   = [(n, c) for n, c in oro_counts if n.lower() == "oro"]

        # first draw all the non-“oro” Oros
        for name, cnt in small_oros:
            place_block(name, cnt)

        # then draw the special “oro” card entry last
        if big_oros:
            name, cnt = big_oros[0]
            card = ALL_CARDS[name]
            w, h = card.tk_image.width(), card.tk_image.height()
            last_h = max(last_h, h)
            if x + w > width_limit:
                x = DECK_CANVAS_LEFT_MARGIN
                y += h + DECK_VERTICAL_GUTTER
            img_id = deck_canvas.create_image(x, y,
                                             image=card.tk_image,
                                             anchor="nw",
                                             tags=("card",))
            image_id_to_name[img_id] = name
            deck_canvas.create_text(
                x + w + 20, y + h // 2,
                text=f"x{cnt}",
                anchor="w",
                font=("Tahoma", 16, "bold"),
                fill="black"
            )
            x += w + 100

    # ── Update stats & curves ──
    update_category_summary()
    update_mana_curve()
    update_consistency()
    update_stats()

from stats import cumulative_probabilities

def update_consistency():
    total = deck.total_cards()
    if total != 50:
        for lbl in (
            lbl8_ali2, lbl8_o2, lbl8_o3,
            lbl7_ali2, lbl7_o2, lbl7_o3,
            lbl6_ali2, lbl6_o2, lbl6_o3
        ):
            lbl.config(text="")
        return

    n_oros = category_counts["Oros"]
    n_ali2 = sum(
        deck.card_counts[n]
        for n in deck.card_counts
        if ALL_CARDS[n].category == "Aliados" and ALL_CARDS[n].cost == 2
    )
    probs = cumulative_probabilities(n_oros, n_ali2)

    PROB_LABELS["p8_ali2"        ].config(text=f"{probs['p8_ali2']*100:5.2f}%")
    PROB_LABELS["p8_o2"          ].config(text=f"{probs['p8_o2']*100:5.2f}%")
    PROB_LABELS["p8_o3"          ].config(text=f"{probs['p8_o3']*100:5.2f}%")
    PROB_LABELS["p8to7_ali2"     ].config(text=f"{probs['p8to7_ali2']*100:5.2f}%")
    PROB_LABELS["p8to7_o2"       ].config(text=f"{probs['p8to7_o2']*100:5.2f}%")
    PROB_LABELS["p8to7_o3"       ].config(text=f"{probs['p8to7_o3']*100:5.2f}%")
    PROB_LABELS["p8to7to6_ali2"  ].config(text=f"{probs['p8to7to6_ali2']*100:5.2f}%")
    PROB_LABELS["p8to7to6_o2"    ].config(text=f"{probs['p8to7to6_o2']*100:5.2f}%")
    PROB_LABELS["p8to7to6_o3"    ].config(text=f"{probs['p8to7to6_o3']*100:5.2f}%")

# =============================================================================
# Funciones de mano, mulligan y simulación
# =============================================================================
current_hand = []
hand_size = 0

def deal_hand():
    global current_hand, hand_size
    if deck.total_cards() != 50:
        messagebox.showerror("Error", "El mazo debe tener exactamente 50 cartas para repartir.")
        return
    hand_size = 8
    draw_new_hand(hand_size)

def mulligan():
    global current_hand, hand_size
    if not current_hand:
        messagebox.showerror("Error", "No hay mano para mulligan. Presiona ‘Repartir mano’ primero.")
        return
    if hand_size <= 1:
        messagebox.showerror("Error", "No podes hacer mulligan con menos de 1 carta.")
        return
    if deck.total_cards() != 50:
        messagebox.showerror("Error", "El mazo debe tener exactamente 50 cartas para mulligan.")
        return
    hand_size -= 1
    draw_new_hand(hand_size)

def draw_new_hand(size):
    global current_hand
    flat = deck.list_all_copies()
    random.shuffle(flat)
    current_hand = flat[:size]
    display_hand(current_hand)

def simulate_1000_hands():
    if deck.total_cards() != 50:
        messagebox.showerror("Error", "El mazo debe tener exactamente 50 cartas para simular.")
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

        if oros_in_hand >= 2:
            count_at_least_2_oros += 1
        if has_1or2_ali:
            count_turn1_play += 1
        if oros_in_hand >= 2 and has_1or2_ali:
            count_great += 1

    lbl_sim_two_oros.config(text=f"Manos ≥2 Oros: {count_at_least_2_oros}")
    lbl_sim_turn1   .config(text=f"Manos Turno1 Jugada: {count_turn1_play}")
    lbl_sim_great   .config(text=f"Manos excelentes: {count_great}")
    
# =============================================================================
# Cambia colores de fondo al elegir Saga
# =============================================================================
def set_background_color_for_saga(saga):
    """Pinta todo con el color de la saga menos la curva de maná."""
    global _bg_full

    saga_colors = {
        "Hijos de Daana":  "#37eca5",
        "Helenica":        "#c5aa87",
        "Espada Sagrada":  "#acbcf7",
        "Dominios de Ra":  "#F1D154",
        None:              BG_DEFAULT
    }
    color = saga_colors.get(saga, BG_DEFAULT)

    # ---- NUEVO: repintar los estilos ttk ----
    _repaint_ttk(color)

    # ---- resto de la función sin cambios ----
    _bg_full = bg_full_images.get(saga)
    _draw_deck_bg()

    def paint(widget):
        if widget is curve_canvas or isinstance(widget, tk.Entry):
            return
        try:
            widget.configure(bg=color)
            if isinstance(widget, tk.OptionMenu):
                widget["menu"].configure(bg=color)
        except Exception:
            pass
        for child in widget.winfo_children():
            paint(child)

    paint(root)
    card_entry.configure(background="white")   # entrada blanca fija
    divider.configure(bg="black")
    curve_canvas.configure(bg="#e0e0e0")
    update_label_highlight()

# =============================================================================
# Callbacks y helpers para Saga / Raza / Formato (con highlight al final)
# =============================================================================
def update_label_highlight():
    def tint(lbl, colour):
        # ttk.Label uses 'foreground' instead of 'fg'
        lbl.configure(foreground=colour)

    if saga_var.get() == "Seleccione":
        tint(lbl_saga,   "red")
        tint(lbl_raza,   "grey")
        tint(lbl_formato,"grey")
    elif race_var.get() == "Seleccione":
        tint(lbl_saga,   "black")
        tint(lbl_raza,   "red")
        tint(lbl_formato,"grey")
    elif format_var.get() == "Seleccione":
        tint(lbl_saga,   "black")
        tint(lbl_raza,   "black")
        tint(lbl_formato,"red")
    else:
        tint(lbl_saga,   "black")
        tint(lbl_raza,   "black")
        tint(lbl_formato,"black")

# ---------------------------------------------------------------------------
# on_saga_change  – Combobox version (works with ttk)
# ---------------------------------------------------------------------------
def on_saga_change(*args):
    global current_saga, current_race, current_format

    sel = saga_var.get().strip()
    card_entry.delete(0, tk.END)

    # --- reset both child filters ------------------------------------------------
    current_race   = None
    current_format = None

    race_var.set("Seleccione")
    race_menu.configure(state="disabled", values=())

    format_var.set("Seleccione")
    format_menu.configure(state="disabled", values=())

    # ---------------------------------------------------------------------------
    if sel == "Seleccione":                     # user cleared the saga
        current_saga = None
        set_background_color_for_saga(None)

    else:                                      # real saga chosen
        # purge cards from another saga (ask to save first)
        bad = [n for n in deck.card_counts if n.lower() != "oro"
               and ALL_CARDS[n].saga != sel]
        if bad and deck.total_cards() > 0 and deck.is_saved and \
           messagebox.askyesno("Cartas inválidas",
                               "Tu mazo contiene cartas de otra saga.\n"
                               "¿Queres guardar antes de vaciarla?"):
            save_deck_gui()
        if bad:
            deck.card_counts.clear()
            deck.is_saved = False

        current_saga = sel
        set_background_color_for_saga(sel)

        # --- populate & enable the Raza combobox --------------------------------
        race_menu.configure(values=[r.capitalize() for r in RACES_BY_SAGA[sel]],
                            state="readonly")
        lbl_raza.configure(foreground="red")          # highlight next step

    update_category_summary()
    update_mana_curve()
    update_deck_display()
    update_consistency()
    update_stats()
    update_label_highlight()
    refresh_search()

def on_race_change(*args):
    global current_race, current_format

    sel = race_var.get().strip()
    card_entry.delete(0, tk.END)

    # --- always reset Formato ----------------------------------------------------
    current_format = None
    format_var.set("Seleccione")
    format_menu.configure(state="disabled", values=())

    # ---------------------------------------------------------------------------
    if sel == "Seleccione":                      # no race selected
        current_race = None

    else:
        # purge allies of another race
        bad = [n for n in deck.card_counts
               if ALL_CARDS[n].category == "Aliados"
               and ALL_CARDS[n].race != sel.lower()]
        if bad and deck.total_cards() > 0 and deck.is_saved and \
           messagebox.askyesno("Cartas inválidas",
                               "Tu mazo contiene Aliados de otra raza.\n"
                               "Queres guardar antes de vaciarla?"):
            save_deck_gui()
        if bad:
            deck.card_counts.clear()
            deck.is_saved = False

        current_race = sel.lower()

        # --- populate & enable Formato combobox ---------------------------------
        format_menu.configure(values=("Pbx", "Reborn"), state="readonly")
        lbl_formato.configure(foreground="red")       # highlight next step

    update_category_summary()
    update_mana_curve()
    update_deck_display()
    update_consistency()
    update_stats()
    update_label_highlight()
    refresh_search()


def on_format_change(*args):
    global current_format
    sel = format_var.get()
    card_entry.delete(0, tk.END)

    # si no hay formato válido, reseteamos
    if sel == "Seleccione":
        current_format = None
    else:
        # limpiar cartas de otro formato (excepto "oro")
        low = sel.lower()
        invalidas = [
            n for n in deck.card_counts
            if n.lower() != "oro" and ALL_CARDS[n].format != low
        ]
        if invalidas and deck.total_cards() > 0:
            if deck.is_saved and messagebox.askyesno(
                "Cartas inválidas",
                "Tu mazo contiene cartas de otro formato.\n"
                "¿Queres guardar antes de vaciarla?"
            ):
                save_deck_gui()
            deck.card_counts.clear()
            deck.is_saved = False

        current_format = low

    # actualizar toda la UI
    update_category_summary()
    update_mana_curve()
    update_deck_display()
    update_consistency()
    update_stats()
    update_label_highlight()
    refresh_search()


# =============================================================================
# CONFIGURACIÓN DE LA INTERFAZ (GUI)
# =============================================================================
root = ThemedTk(theme="clearlooks")          # ventana themed

# ---------- PALETA BASE ----------
BG_DEFAULT = "#d3d3d3"                       # gris inicial
root.configure(bg=BG_DEFAULT)
root.option_add("*Font", "Tahoma 12")        # todo lo “tk” heredará Tahoma12
# ─────────────────────────────────────────────────────────────────────────────
# Helper functions – thumbnails & drawing the 8-card hand
# ─────────────────────────────────────────────────────────────────────────────

def _get_thumb(card):
    """
    Return a cached 80×120 thumbnail for `card`.
    If needed, walk CARD_IMAGES_DIR to find card.name.jpg/png,
    open it once, and cache both the PIL.Image and the PhotoImage.
    """
    # 1) Already made?
    if hasattr(card, "thumb80"):
        return card.thumb80

    # 2) Re-use full image if already loaded
    pil = getattr(card, "image", None)

    # 3) Otherwise, hunt for the file under CARD_IMAGES_DIR
    if pil is None:
        for root_dir, _, files in os.walk(CARD_IMAGES_DIR):
            jpg = f"{card.name}.jpg"
            png = f"{card.name}.png"
            if jpg in files:
                path = os.path.join(root_dir, jpg)
            elif png in files:
                path = os.path.join(root_dir, png)
            else:
                continue
            try:
                pil = Image.open(path).convert("RGBA")
                card.image = pil     # cache for next time
            except Exception:
                pil = None
            break

    # 4) If we now have a PIL image, resize it into our thumbnail box
    if pil:
        w, h = pil.size
        scale = min(THUMB_W / w, THUMB_H / h)
        new_w, new_h = int(w * scale), int(h * scale)
        thumb_pil = pil.resize((new_w, new_h), Image.LANCZOS)

        # center it on a transparent canvas
        canvas = Image.new("RGBA", (THUMB_W, THUMB_H), (0, 0, 0, 0))
        x_off = (THUMB_W - new_w) // 2
        y_off = (THUMB_H - new_h) // 2
        canvas.paste(thumb_pil, (x_off, y_off), thumb_pil)

        thumb = ImageTk.PhotoImage(canvas)
        card.thumb80 = thumb
        return thumb

    # 5) Fallback: blank if nothing found
    blank = Image.new("RGBA", (THUMB_W, THUMB_H), (0, 0, 0, 0))
    ph = ImageTk.PhotoImage(blank)
    card.thumb80 = ph
    return ph

# ─────────────────────────────────────────────────────────────────────────────
# SHOW SPLASH + PROGRESS BAR DURING PRELOAD (with true transparency)
# ─────────────────────────────────────────────────────────────────────────────
root.withdraw()

splash = tk.Toplevel()
splash.overrideredirect(True)

# 1) Magic key-color transparency
MAGENTA = "#FF00FF"
splash.configure(bg=MAGENTA)
splash.attributes("-transparentcolor", MAGENTA)
splash.attributes("-topmost", True)
splash.lift()
splash.update()

# 2) Load your RGBA logo and size the window slightly taller to fit the bar
logo_path = os.path.join(UI_IMAGES_DIR, "logo_myl.png")
pil_logo  = Image.open(logo_path).convert("RGBA")
logo_w, logo_h = pil_logo.size

BAR_HEIGHT = 20    # approximate height of the ttk Progressbar
PADDING    = 10    # bottom padding
total_h    = logo_h + BAR_HEIGHT + PADDING

# center on screen
screen_w = splash.winfo_screenwidth()
screen_h = splash.winfo_screenheight()
x = (screen_w - logo_w) // 2
y = (screen_h - total_h) // 2
splash.geometry(f"{logo_w}x{total_h}+{x}+{y}")

# 3) Build a hard mask so we don't get ugly semi-transparent borders
alpha        = pil_logo.split()[3]
binary_mask  = alpha.point(lambda p: 255 if p >= 128 else 0)
canvas       = Image.new("RGB", pil_logo.size, MAGENTA)
canvas.paste(pil_logo, mask=binary_mask)

# 4) Show the logo at the top
splash_img = ImageTk.PhotoImage(canvas)
lbl_logo   = tk.Label(splash, image=splash_img, bg=MAGENTA, bd=0)
lbl_logo.image = splash_img
lbl_logo.pack(side="top", fill="none")

# 5) Now the progress bar — it will appear *below* the logo
bar = ttk.Progressbar(splash, orient="horizontal", mode="determinate", length=logo_w-20)
bar.pack(side="top", fill="x", padx=10, pady=(5,0))
bar["maximum"] = len(ALL_CARDS)

# 6) Preload all thumbnails
for i, card in enumerate(ALL_CARDS.values(), start=1):
    _get_thumb(card)
    bar["value"] = i
    splash.update_idletasks()

# 7) Done—tear it down
splash.destroy()
root.deiconify()

# ─────────────────────────────────────────────────────────────────────────────
# ---------- ESTILO TTK GLOBAL ----------
# ─────────────────────────────────────────────────────────────────────────────
style = ttk.Style()
style.theme_use("clam")                      # plano y neutro

def _repaint_ttk(palette_bg, palette_fg="black"):
    """Aplica el colour-scheme a todos los widgets ttk."""
    # -- Labels
    style.configure("TLabel",
                    font=("Tahoma", 12),
                    background=palette_bg,
                    foreground=palette_fg)

    # -- Botones
    style.configure(
        "TButton",
        font=("Tahoma", 12, "bold"),
        padding=6,
        relief="raised",         # borde en relieve
        borderwidth=2,           # grosor del borde
        background=BG_DEFAULT,   # mismo color de fondo que la saga
        foreground="black"
    )
    style.configure(
    "Instr.TButton",
    font=("Tahoma", 12, "bold"),
    padding=6
)
    style.map(
    "TButton",
    background=[("active", BG_DEFAULT)],
    foreground=[("active", "black")],
    relief=[("pressed", "sunken"), ("!pressed", "raised")]
)

    # -- Combobox (campo y desplegable)
    style.configure("TCombobox",
                    font=("Tahoma", 12),
                    fieldbackground=palette_bg,
                    background=palette_bg,
                    foreground=palette_fg,
                    relief="flat")
    style.map("TCombobox",
              fieldbackground=[("readonly", palette_bg)],
              background=[("readonly", palette_bg)],
              foreground=[("readonly", palette_fg)],
              selectbackground=[("readonly", palette_bg)],
              selectforeground=[("readonly", palette_fg)])

# aplica la paleta por defecto al arrancar
_repaint_ttk(BG_DEFAULT)

root.title("Mitos y Leyendas: Constructor de Mazos")
root.geometry("1200x970")

# ─────────────────────────────────────────────────────────────────────────────
# =============================================================================
# Containers principales: left_container, divider, right_panel
# =============================================================================
left_container = tk.Frame(root, bg=BG_DEFAULT)
divider        = tk.Frame(root, bg="black", width=4)
right_panel    = tk.Frame(root, bg=BG_DEFAULT)

# Posicionar en grid:
left_container.grid(row=0, column=0, rowspan=4, sticky="nw")
divider       .grid(row=0, column=1, rowspan=4, sticky="ns")
right_panel   .grid(row=0, column=2, rowspan=4, sticky="nsew")

# Configurar pesos en root:
root.grid_columnconfigure(0, weight=0)  # left_container fijo
root.grid_columnconfigure(1, weight=0)  # divider fijo
root.grid_columnconfigure(2, weight=1)  # right_panel absorbe sobrante
root.grid_rowconfigure(0, weight=1)
root.grid_rowconfigure(1, weight=1)
root.grid_rowconfigure(2, weight=1)
root.grid_rowconfigure(3, weight=1)

# Dentro de left_container: no expandir columnas
left_container.grid_columnconfigure(0, weight=0)
left_container.grid_columnconfigure(1, weight=0)
left_container.grid_columnconfigure(2, weight=0)
left_container.grid_columnconfigure(4, weight=1)
# Filas internas solo ocupan lo necesario:
left_container.grid_rowconfigure(0, weight=0)  # deck_canvas
left_container.grid_rowconfigure(1, weight=0)  # curve_canvas + summary + form
left_container.grid_rowconfigure(2, weight=0)  # (vacío o futuro)
left_container.grid_rowconfigure(3, weight=0)  # card_menu_frame

# =============================================================================
# CANVAS PRINCIPAL de DECK (deck_canvas)  ── con fondo dinámico
# =============================================================================
# Precarga de imágenes de fondo
bg_full_images = {}
for key, fname in [
    (None,             "bg_default.png"),
    ("Espada Sagrada", "bg_espada_sagrada.png"),
    ("Helenica",       "bg_helenica.png"),
    ("Hijos de Daana", "bg_hijos_de_daana.png"),
    ("Dominios de Ra", "bg_dominios_de_ra.png"),
]:
    ruta = os.path.join(UI_IMAGES_DIR, fname)
    try:
        bg_full_images[key] = Image.open(ruta).convert("RGBA")
    except Exception:
        bg_full_images[key] = None

# Imagen PIL activa (empieza en default)
_bg_full = bg_full_images.get(None)

# Función para redibujar fondo
def _draw_deck_bg(event=None):
    w = deck_canvas.winfo_width()
    h = deck_canvas.winfo_height()
    deck_canvas.delete("bg")
    if _bg_full:
        pil = _bg_full.resize((w, h), Image.LANCZOS)
        deck_canvas._bg = ImageTk.PhotoImage(pil)
        deck_canvas.create_image(0, 0, image=deck_canvas._bg,
                                 anchor="nw", tags=("bg",))
        deck_canvas.tag_lower("bg")

# Canvas del mazo
CANVAS_FIXED_W = 1152
CANVAS_FIXED_H = 675
deck_canvas = tk.Canvas(left_container, width=CANVAS_FIXED_W,
                        height=CANVAS_FIXED_H, bd=0, highlightthickness=0)
deck_canvas.grid(row=0, column=0, columnspan=3,
                 padx=10, pady=10, sticky="nw")
deck_canvas.bind("<Configure>", _draw_deck_bg)
_draw_deck_bg()

# =============================================================================
# CURVA DE MANÁ (curve_canvas) justo debajo del deck_canvas
# =============================================================================
CURVE_W, CURVE_H = 400, 200
curve_canvas = tk.Canvas(left_container, width=CURVE_W, height=CURVE_H,
                         bg="#e0e0e0", bd=0, highlightthickness=0)
curve_canvas.grid(row=1, column=0, padx=(10,5), pady=(0,10), sticky="w")
# =============================================================================
# SUMMARY FRAME (Categorías + Estadísticas) — alineado a la izquierda, fuente +5
# =============================================================================
summary_strip = tk.Frame(left_container, bg=BG_DEFAULT)
summary_strip.grid(row=1, column=1, columnspan=3,        # right of curve
                   padx=(5,10), pady=(0,10), sticky="w")

# --- Categorías ----------------------------------------------------------------
cat_frame = tk.Frame(summary_strip, bg=BG_DEFAULT)
cat_frame.grid(row=0, column=0, sticky="nw")
for idx, cat in enumerate(category_order):
    lbl_name  = tk.Label(cat_frame, text=f"{cat}:", font=("Tahoma",15,"bold"),
                         bg=BG_DEFAULT, anchor="w")
    lbl_count = tk.Label(cat_frame, text="0",     font=("Tahoma",15),
                         bg=BG_DEFAULT, anchor="w")
    lbl_name .grid(row=idx, column=0, sticky="w")
    lbl_count.grid(row=idx, column=1, sticky="w", padx=(4,0))
    category_labels[cat] = lbl_count

def show_instructions_overlay():
    global _overlay
    _close_overlay()

    # overlay completo sobre right_panel
    _overlay = tk.Frame(right_panel, bg=right_panel.cget("bg"))
    _overlay.place(relx=0, rely=0, relwidth=1, relheight=1)

    # botón de cerrar
    ttk.Button(_overlay, text="❌  Cerrar", command=_close_overlay)\
       .pack(anchor="ne", padx=6, pady=6)

    # texto de instrucciones
    instrucciones = (
        "Instrucciones de uso\n\n"
        "1. Navegación y filtros\n"
        "   • Saga → Raza → Formato\n"
        "   • Tipo y Orden\n"
        "   • Scroll con rueda sobre Card Search\n\n"
        "2. Añadir / quitar cartas\n"
        "   • Botón Añadir carta (autocomplete + cantidad)\n"
        "   • Botón Eliminar carta\n\n"
        "3. Drag & Drop\n"
        "   • Arrastra miniatura al panel izquierdo para añadir\n\n"
        "4. Clics sobre mazo\n"
        "   • Izquierdo: quita 1 copia\n"
        "   • Derecho: añade 1 copia\n"
        "   • Central: abre detalle ampliado\n\n"
        "5. Guardar e importar mazos\n"
        "   • Guardar como: exporta mazo\n"
        "   • Importar mazo: carga desde archivo\n\n"
        "6. Atajos de teclado\n"
        "   • Esc o ❌ Cerrar: cierra overlay\n"
        "   • Alt+F4 o Salir: cierra la aplicación"
    )
    tk.Label(_overlay,
             text=instrucciones,
             justify="left",
             font=("Tahoma",12),
             bg=_overlay.cget("bg")
    ).pack(padx=20, pady=20)

# --- Estadísticas Adicionales --------------------------------------------------
stats_frame = tk.LabelFrame(
    summary_strip, text="Estadísticas Adicionales",
    bg=BG_DEFAULT, font=("Tahoma",15,"bold"),
    padx=5, pady=5, labelanchor="nw"
)
stats_frame.grid(row=0, column=1, padx=(15,15), sticky="n")

lbl_avg_cost = tk.Label(
    stats_frame,
    text="Costo promedio (mazo): 0.00",
    font=("Tahoma",15),
    bg=BG_DEFAULT,
    anchor="w"
)
lbl_avg_str = tk.Label(
    stats_frame,
    text="Fuerza aliados promedio: 0.00",
    font=("Tahoma",15),
    bg=BG_DEFAULT,
    anchor="w"
)
lbl_avg_cost.grid(row=0, column=0, sticky="w")
lbl_avg_str .grid(row=1, column=0, sticky="w")

# — Botón Instrucciones de uso (fuera del frame, justo debajo) —
instr_button = ttk.Button(
    summary_strip,
    text="Instrucciones de uso",
    style="Instr.TButton",
    command=show_instructions_overlay,
    width=20
)
# ahora en la misma fila que stats_frame, alineado al fondo (south), sin alterar los demás widgets
instr_button.grid(row=0, column=1, sticky="s", pady=(0,5))


# =============================================================================
# FRAME Saga / Raza / Formato — alineado a la izquierda, fuente +5
# =============================================================================
form_frame = tk.Frame(summary_strip, bg=BG_DEFAULT)
form_frame.grid(row=0, column=2, sticky="nw")

lbl_saga = tk.Label(form_frame, text="Saga:", font=("Tahoma",15,"bold"),
                    bg=BG_DEFAULT)
lbl_saga.grid(row=0, column=0, sticky="w")
saga_var  = tk.StringVar(value="Seleccione")
saga_menu = ttk.Combobox(form_frame, textvariable=saga_var,
                         values=list(SAGA_FOLDERS.keys()),
                         state="readonly", width=17)
saga_menu.grid(row=0, column=1, sticky="w", padx=(4,0))

lbl_raza = tk.Label(form_frame, text="Raza:", font=("Tahoma",15,"bold"),
                    bg=BG_DEFAULT, fg="grey")
lbl_raza.grid(row=1, column=0, sticky="w")
race_var  = tk.StringVar(value="Seleccione")
race_menu = ttk.Combobox(form_frame, textvariable=race_var,
                         state="disabled", width=17)
race_menu.grid(row=1, column=1, sticky="w", padx=(4,0))

lbl_formato = tk.Label(form_frame, text="Formato:", font=("Tahoma",15,"bold"),
                       bg=BG_DEFAULT, fg="grey")
lbl_formato.grid(row=2, column=0, sticky="w")
format_var  = tk.StringVar(value="Seleccione")
format_menu = ttk.Combobox(form_frame, textvariable=format_var,
                           state="disabled", width=17)
format_menu.grid(row=2, column=1, sticky="w", padx=(4,0))

# (callbacks stay the same)
saga_var.trace("w", on_saga_change)
race_var.trace("w", on_race_change)
format_var.trace("w", on_format_change)

# =============================================================================
# MENÚ INFERIOR: Carta, Cantidad, Botones
# =============================================================================
card_menu_frame = tk.Frame(left_container, bg=BG_DEFAULT)
card_menu_frame.grid(row=3, column=0, columnspan=3, padx=10, pady=(10,20), sticky="we")

# — Carta entry con autocomplete —
ttk.Label(card_menu_frame, text="Carta:", font=("Tahoma",12,"bold")
          ).grid(row=0, column=0, sticky="e")
card_entry = ttk.Entry(card_menu_frame, width=32)
card_entry.grid(row=0, column=1, sticky="w", padx=(5,10))

def autocomplete_card(event):
    if event.keysym in ("Right", "Return"):
        try:
            card_entry.select_clear()
            card_entry.icursor(tk.END)
        except tk.TclError:
            pass
        return
    if event.keysym == "BackSpace":
        try:
            card_entry.select_clear()
        except tk.TclError:
            pass
        return
    text = card_entry.get()
    try:
        sel_start = card_entry.index("sel.first")
        typed = text[:sel_start]
    except tk.TclError:
        typed = text
    if len(typed.strip()) < 2:
        try:
            card_entry.select_clear()
        except tk.TclError:
            pass
        return
    lookup = typed.strip().lower().replace(" ", "-")
    if current_saga is None or current_format is None:
        return
    matches = []
    for nm, card in ALL_CARDS.items():
        if not nm.startswith(lookup):
            continue
        if card.saga != current_saga or card.format != current_format:
            continue
        if card.category == "Aliados" and (current_race is None or card.race != current_race):
            continue
        matches.append(nm)
    if not matches:
        try:
            card_entry.select_clear()
        except tk.TclError:
            pass
        return
    matches.sort()
    full = matches[0]
    display = " ".join(part.capitalize() for part in full.split("-"))
    card_entry.delete(0, tk.END)
    card_entry.insert(0, display)
    start = len(typed)
    card_entry.select_range(start, tk.END)
    card_entry.icursor(start)

card_entry.bind("<KeyRelease>", autocomplete_card)

# — Cantidad dropdown —
ttk.Label(card_menu_frame, text="Cantidad:", font=("Tahoma",12,"bold")
          ).grid(row=0, column=2, sticky="e")
qty_var  = tk.StringVar(value="1")
qty_menu = ttk.Combobox(card_menu_frame, textvariable=qty_var,
                        values=("1","2","3"), state="readonly",
                        width=4)
qty_menu.grid(row=0, column=3, sticky="w", padx=(5,20))

# — Botones Añadir / Eliminar —
add_button    = ttk.Button(card_menu_frame, text="Añadir carta", command=add_card_gui)
remove_button = ttk.Button(card_menu_frame, text="Eliminar carta", command=remove_card_gui)
add_button.grid(   row=0, column=4, padx=(0,10))
remove_button.grid(row=0, column=5, padx=(0,0))

# — Guardar como —
ttk.Label(card_menu_frame, text="Guardar como:",
          font=("Tahoma",12,"bold")
          ).grid(row=1, column=0, sticky="e", pady=(8,0))
save_entry = ttk.Entry(card_menu_frame, width=24)
save_entry.grid(row=1, column=1, sticky="w", padx=(5,10), pady=(8,0))
save_button = ttk.Button(card_menu_frame, text="Guardar mazo",
                         command=save_deck_gui)
save_button.grid(row=1, column=2, padx=(0,20), pady=(8,0))

# — Importar mazo —
ttk.Label(card_menu_frame, text="Importar mazo:",
          font=("Tahoma",12,"bold")
          ).grid(row=1, column=3, sticky="e", pady=(8,0))
deck_var    = tk.StringVar(value="Sin mazos")
deck_option = ttk.Combobox(
    card_menu_frame,
    textvariable=deck_var,
    values=get_deck_files(),
    state="readonly",
    width=18
)
deck_option.grid(row=1, column=4, sticky="w", padx=(5,10), pady=(8,0))

def refresh_deck_dropdown():
    deck_option.configure(values=get_deck_files())

# ensure dropdown is up-to-date now and after imports
refresh_deck_dropdown()

import_button = ttk.Button(
    card_menu_frame,
    text="Importar mazo",
    command=lambda: (import_deck_dropdown(), refresh_deck_dropdown())
)
import_button.grid(row=1, column=5, padx=(10,10), pady=(8,0))

# — Salir —
quit_button = ttk.Button(card_menu_frame, text="Salir",
                         command=root.destroy)
quit_button.grid(row=1, column=6, padx=(0,0), pady=(8,0))

# ─────────────────────────────────────────────────────────────────────────────
# PANEL DERECHO – Probabilidades (alineadas, sin recortes)
# ─────────────────────────────────────────────────────────────────────────────
consistency_frame = tk.LabelFrame(
    right_panel, text="Probabilidades Mano Inicial",
    bg=BG_DEFAULT, font=("Tahoma", 10, "bold"),
    padx=5, pady=5
)
consistency_frame.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="nwe")

LABEL_FONT  = ("Tahoma", 9)
PROB_LABELS = {}                         # { key : lbl_val }

def build_column(parent, title, prefix):
    """
    Create one probability column and save the three value-labels
    into PROB_LABELS using keys  f'{prefix}ali2' / '{prefix}o2' / '{prefix}o3'.
    """
    col = tk.Frame(parent, bg=BG_DEFAULT)
    # ⬇ tighter padding so text never gets cropped
    col.pack(side="left", expand=True, fill="y", padx=12)

    # Header — now left-aligned
    tk.Label(col, text=title, font=("Tahoma", 10, "bold"),
             bg=BG_DEFAULT, anchor="w").pack(anchor="w", pady=(0, 4))

    # Helper → one row “description | value”
    def add_row(desc, key):
        row = tk.Frame(col, bg=BG_DEFAULT)
        row.pack(fill="x", pady=1)
        tk.Label(row, text=desc, font=LABEL_FONT,
                 bg=BG_DEFAULT).pack(side="left", anchor="w")
        val = tk.Label(row, text="–", font=LABEL_FONT,
                       bg=BG_DEFAULT, anchor="w")
        val.pack(side="left")            # glue immediately after the colon
        PROB_LABELS[key] = val

    add_row("Prob. ≥1 Aliado C2:", f"{prefix}ali2")
    add_row("Prob. ≥2 Oros:",      f"{prefix}o2")
    add_row("Prob. ≥3 Oros:",      f"{prefix}o3")

# Build the three aligned columns
build_column(consistency_frame, "Robar 8",            "p8_")
build_column(consistency_frame, "Robar 8 + 7",        "p8to7_")
build_column(consistency_frame, "Robar 8 + 7 + 6",    "p8to7to6_")

# Handy references for update_consistency()
lbl8_ali2 = PROB_LABELS["p8_ali2"];      lbl8_o2 = PROB_LABELS["p8_o2"];      lbl8_o3 = PROB_LABELS["p8_o3"]
lbl7_ali2 = PROB_LABELS["p8to7_ali2"];   lbl7_o2 = PROB_LABELS["p8to7_o2"];   lbl7_o3 = PROB_LABELS["p8to7_o3"]
lbl6_ali2 = PROB_LABELS["p8to7to6_ali2"];lbl6_o2 = PROB_LABELS["p8to7to6_o2"];lbl6_o3 = PROB_LABELS["p8to7to6_o3"]

# =============================================================================
# Repartir Mano Aleatoria (Right Panel)
# =============================================================================
hand_frame = tk.LabelFrame(
    right_panel, text="Repartir Mano Aleatoria",
    bg=BG_DEFAULT, font=("Tahoma", 13, "bold"),
    padx=8, pady=6
)
hand_frame.grid(row=3, column=0, padx=10, pady=(5, 10), sticky="nwe")
hand_frame.grid_columnconfigure(0, weight=0)   # canvas keeps its size
hand_frame.grid_columnconfigure(1, weight=1)   # remaining space grows

# ── Canvas con 8 miniaturas ──────────────────────────────────────────────────                  # ⬆️ tamaño de cada carta
_cols_, _rows_, _gap_ = 4, 2, 6     # 6-px gap instead of 12
deal_canvas = tk.Canvas(
    hand_frame,
    width = THUMB_W * _cols_ + (_cols_-1) * _gap_,
    height= THUMB_H * _rows_ + (_rows_-1) * _gap_,
    bg=BG_DEFAULT, bd=0, highlightthickness=0
)
deal_canvas.grid(row=0, column=0, rowspan=2,
                 padx=(5, 5), pady=(5, 5), sticky="nw")

info_text = tk.Label(
    hand_frame,
    text="Aliados: 0\nOros: 0\nSoporte: 0",
    justify="center",                # ← centered text
    bg=BG_DEFAULT,
    font=("Tahoma", 12, "bold")
)
info_text.grid(row=0, column=1, padx=(12, 12), pady=(5, 5), sticky="n")   # ← sticky north-center

# ── Simulación (1000 manos) ──────────────────────────────────────────────────
sim_frame = tk.Frame(hand_frame, bg=BG_DEFAULT)
sim_frame.grid(row=1, column=1, padx=(12, 12), pady=(5, 5), sticky="n")   # center, not east

thousand_button = ttk.Button(sim_frame, text="1000 Manos",
                             command=simulate_1000_hands)
thousand_button.grid(row=0, column=0, padx=(0, 6))

lbl_sim_two_oros = tk.Label(sim_frame, text="Manos ≥2 Oros: 0",
                            bg=BG_DEFAULT, font=("Tahoma", 11))
lbl_sim_turn1    = tk.Label(sim_frame, text="Manos Turno1 Jugada: 0",
                            bg=BG_DEFAULT, font=("Tahoma", 11))
lbl_sim_great    = tk.Label(sim_frame, text="Manos excelentes: 0",
                            bg=BG_DEFAULT, font=("Tahoma", 11))
lbl_sim_two_oros.grid(row=1, column=0, sticky="w")
lbl_sim_turn1   .grid(row=2, column=0, sticky="w")
lbl_sim_great   .grid(row=3, column=0, sticky="w")

# ── Botones Repartir / Mulligan ──────────────────────────────────────────────
hand_button_frame = tk.Frame(hand_frame, bg=BG_DEFAULT)
hand_button_frame.grid(row=2, column=0, columnspan=2,
                       pady=(8, 5), sticky="we")
for i in range(4):                          # botones centrados
    hand_button_frame.grid_columnconfigure(i, weight=1)

lbl_two_oros = tk.Label(hand_button_frame, text="2 Oros",
                        font=("Tahoma", 12, "bold"), bg=BG_DEFAULT)
lbl_two_oros.grid(row=0, column=0, padx=(0, 18), sticky="w")

deal_button = ttk.Button(hand_button_frame, text="Repartir mano",
                         command=deal_hand)
deal_button.grid(row=0, column=1, padx=(0, 12))

mulligan_button = ttk.Button(hand_button_frame, text="Mulligan",
                             command=mulligan)
mulligan_button.grid(row=0, column=2, padx=(0, 18))

lbl_turn1 = tk.Label(hand_button_frame, text="Jugada turno 1",
                     font=("Tahoma", 12, "bold"), bg=BG_DEFAULT)
lbl_turn1.grid(row=0, column=3, sticky="e")

def display_hand(hand_list):               # ← this is the single, valid one
    deal_canvas.delete("all")
    ali = oro = sop = 0
    cols, spacing = _cols_, _gap_

    # adaptar tamaño del canvas a la cantidad de filas realmente usada
    rows = math.ceil(len(hand_list) / cols)
    deal_canvas.config(
        width = THUMB_W * cols + (cols - 1) * spacing,
        height= THUMB_H * rows + (rows - 1) * spacing
    )

    for idx, cname in enumerate(hand_list):
        row, col = divmod(idx, cols)
        card = ALL_CARDS[cname]
        img  = _get_thumb(card)

        x = col * (THUMB_W + spacing)
        y = row * (THUMB_H + spacing)
        deal_canvas.create_image(x, y, image=img, anchor="nw")

        if card.category == "Aliados":
            ali += 1
        elif card.category == "Oros":
            oro += 1
        else:
            sop += 1

    info_text.config(text=f"Aliados: {ali}\nOros: {oro}\nSoporte: {sop}")
    lbl_two_oros.config(fg=("green" if oro >= 2 else "red"))
    lbl_turn1.config(fg=("green" if any(
        ALL_CARDS[c].category == "Aliados" and ALL_CARDS[c].cost in (1, 2)
        for c in hand_list) else "red"))
    
# ─────────────────────────────────────────────────────────────────────────────
# NEW: Divider + Card Search section (6-col vertical scroll + drag-and-drop)
# ─────────────────────────────────────────────────────────────────────────────

# Card Search frame
search_frame = tk.LabelFrame(
    right_panel, text="Card Search",
    bg=BG_DEFAULT, font=("Tahoma", 12, "bold"),
    padx=8, pady=6
)
search_frame.grid(row=2, column=0, sticky="nsew", padx=5, pady=(0,10))
right_panel.grid_rowconfigure(2, weight=1)
search_frame.grid_rowconfigure(1, weight=1)
search_frame.grid_columnconfigure(0, weight=1)

# 3) Filter dropdowns
tipo_var  = tk.StringVar(value="Tipo")
orden_var = tk.StringVar(value="Alfabético")

ttk.Label(search_frame, text="Tipo:", font=("Tahoma", 11, "bold"), background=BG_DEFAULT
         ).grid(row=0, column=0, sticky="w", padx=(0,10))
tipo_menu = ttk.Combobox(
    search_frame, textvariable=tipo_var,
    values=("Aliado","Talisman","Totem","Arma","Oro"),
    state="readonly", width=10
)
tipo_menu.grid(row=0, column=0, sticky="e")
ttk.Label(search_frame, text="Orden:", font=("Tahoma", 11, "bold"), background=BG_DEFAULT
         ).grid(row=0, column=1, sticky="w", padx=(20,10))
orden_menu = ttk.Combobox(
    search_frame, textvariable=orden_var,
    values=("Alfabético","Coste","Fuerza"),
    state="readonly", width=12
)
orden_menu.grid(row=0, column=1, sticky="e")

# 4) Scrollable canvas for results
search_canvas = tk.Canvas(search_frame, bg=BG_DEFAULT, bd=0, highlightthickness=0)
vscroll = ttk.Scrollbar(search_frame, orient="vertical", command=search_canvas.yview)
search_canvas.configure(yscrollcommand=vscroll.set)

vscroll.grid(row=1, column=1, sticky="ns")
search_canvas.grid(row=1, column=0, sticky="nsew")

_search_interior = tk.Frame(search_canvas, bg=BG_DEFAULT)
search_canvas.create_window((0,0), window=_search_interior, anchor="nw")

def _on_search_scroll(event):
    search_canvas.yview_scroll(int(-1*(event.delta/120)), "units")

# bind wheel anywhere on frame/canvas/scrollbar/interior
for widget in (search_frame, search_canvas, vscroll, _search_interior):
    widget.bind("<Enter>", lambda e: search_canvas.bind_all("<MouseWheel>", _on_search_scroll))
    widget.bind("<Leave>", lambda e: search_canvas.unbind_all("<MouseWheel>"))

def _on_search_configure(event):
    search_canvas.configure(scrollregion=search_canvas.bbox("all"))

_search_interior.bind("<Configure>", _on_search_configure)

# mapping from widget → card name
_search_id_to_name = {}

# 5) Populate function
def refresh_search():
    # 1) Clear out old results
    for w in _search_interior.winfo_children():
        w.destroy()
    _search_id_to_name.clear()

    tipo = tipo_var.get()
    # 2) Must pick a Tipo
    if tipo == "Tipo":
        return

    # 3) For non-"Oro" searches, require saga/race/format
    if tipo != "Oro" and not (current_saga and current_race and current_format):
        return

    # 4) Map UI “Tipo” → internal category
    tipo_map = {
        "Aliado":   "Aliados",
        "Talisman": "Talismanes",
        "Totem":    "Totems",
        "Arma":     "Armas",
        "Oro":      "Oros"
    }
    cat_filter = tipo_map[tipo]

    names = []
    if cat_filter == "Oros":
        # Always include the special "oro" card
        if "oro" in ALL_CARDS:
            names.append("oro")
        # Include any other Oros only if they match saga & formato
        for nm, card in ALL_CARDS.items():
            if nm == "oro" or card.category != "Oros":
                continue
            if card.saga == current_saga and card.format == current_format:
                names.append(nm)
    else:
        # Standard filtering for all other categories
        for nm, card in ALL_CARDS.items():
            if card.category != cat_filter:
                continue
            if card.saga   != current_saga:    continue
            if card.format != current_format: continue
            if cat_filter == "Aliados" and card.race != current_race:
                continue
            names.append(nm)

    # 5) Sort by Orden dropdown
    if orden_var.get() == "Coste":
        names.sort(key=lambda n: ALL_CARDS[n].cost or 0)
    elif orden_var.get() == "Fuerza":
        names.sort(key=lambda n: ALL_CARDS[n].strength or 0)
    else:
        names.sort()

    # 6) Render a 6‐across grid of thumbnails
    cols, gap = 6, 2
    bg = _search_interior.cget("bg")
    for idx, nm in enumerate(names):
        thumb = _get_thumb(ALL_CARDS[nm])
        row, col = divmod(idx, cols)
        lbl = tk.Label(_search_interior, image=thumb, bg=bg, cursor="hand2")
        lbl.image = thumb
        lbl.grid(row=row, column=col, padx=gap, pady=gap)
        _search_id_to_name[lbl] = nm
        lbl.bind("<ButtonPress-1>", start_search_drag)
        # ensure the wheel scrolling remains active even when over a card
        lbl.bind("<Enter>", lambda e: search_canvas.bind_all("<MouseWheel>", _on_search_scroll))
        lbl.bind("<Leave>", lambda e: search_canvas.unbind_all("<MouseWheel>"))

tipo_menu.bind("<<ComboboxSelected>>", lambda e: refresh_search())
orden_menu.bind("<<ComboboxSelected>>", lambda e: refresh_search())

# ── Drag & Drop support for Card Search ───────────────────────────────────────
_drag_data = {"widget": None, "card": None}

def start_search_drag(ev):
    lbl = ev.widget
    card_name = _search_id_to_name.get(lbl)
    if not card_name:
        return

    floater = tk.Label(root, image=lbl.image, bg=root.cget("bg"))
    floater.image = lbl.image
    _drag_data["widget"] = floater
    _drag_data["card"]   = card_name

    floater.place(x=ev.x_root - THUMB_W//2, y=ev.y_root - THUMB_H//2)
    root.bind("<B1-Motion>", on_search_drag)
    root.bind("<ButtonRelease-1>", on_search_release)

def on_search_drag(ev):
    floater = _drag_data["widget"]
    if floater:
        floater.place(x=ev.x_root - THUMB_W//2, y=ev.y_root - THUMB_H//2)

def on_search_release(ev):
    floater = _drag_data["widget"]
    card    = _drag_data["card"]

    root.unbind("<B1-Motion>")
    root.unbind("<ButtonRelease-1>")

    if floater:
        floater.place_forget()
        root.update_idletasks()

        tgt = root.winfo_containing(ev.x_root, ev.y_root)
        inside_left = False
        while tgt:
            if tgt is left_container:
                inside_left = True
                break
            tgt = getattr(tgt, "master", None)

        if inside_left:
            ok, reason = can_add_card(card, 1)
            if ok:
                deck.add_card(card, 1)
                update_category_summary()
                update_mana_curve()
                update_deck_display()
                update_consistency()
                update_stats()
            else:
                messagebox.showwarning("No permitido", reason)

        floater.destroy()

    _drag_data["widget"] = None
    _drag_data["card"]   = None

# =============================================================================
# Eventos de clic sobre carta  (izq-quita, dcha-añade, medio-detalle)
# =============================================================================
def remove_card_by_click(event):
    item = event.widget.find_withtag("current")
    if not item:
        return
    name = image_id_to_name.get(item[0])
    if name and deck.card_counts.get(name, 0) > 0:
        deck.remove_card(name, 1)
        update_category_summary(); update_mana_curve(); update_deck_display()
        update_consistency();       update_stats()


def add_card_by_right_click(event):
    item = event.widget.find_withtag("current")
    if not item:
        return
    name = image_id_to_name.get(item[0])
    if name:
        ok, reason = can_add_card(name, 1)
        if not ok:
            messagebox.showwarning("No permitido", reason)
            return
        deck.add_card(name, 1)
        update_category_summary(); update_mana_curve(); update_deck_display()
        update_consistency();       update_stats()

# -----------------------------------------------------------------------------  
# Overlay con detalle (clic central) – grid 3 filas, no solapamientos  
# -----------------------------------------------------------------------------
_overlay = None

def _close_overlay():
    """Cerrar y eliminar cualquier overlay anterior."""
    global _overlay
    if _overlay and _overlay.winfo_exists():
        _overlay.destroy()
    _overlay = None

def _find_image(card_name: str):
    """Busca card_name.jpg/png en CARD_IMAGES_DIR y subdirectorios."""
    for root_dir, _, files in os.walk(CARD_IMAGES_DIR):
        if f"{card_name}.jpg" in files:
            return os.path.join(root_dir, f"{card_name}.jpg")
        if f"{card_name}.png" in files:
            return os.path.join(root_dir, f"{card_name}.png")
    return None

def _show_card_overlay(card_name: str):
    """Muestra overlay en 3 filas: botón cerrar, imagen, estadísticas."""
    global _overlay
    _close_overlay()

    # 1) Crear overlay que cubre right_panel
    _overlay = tk.Frame(right_panel, bg=right_panel.cget("bg"))
    _overlay.place(relx=0, rely=0, relwidth=1, relheight=1)

    # 2) Configurar grid: 3 filas, 1 columna
    _overlay.grid_rowconfigure(0, weight=0)
    _overlay.grid_rowconfigure(1, weight=1)
    _overlay.grid_rowconfigure(2, weight=0)
    _overlay.grid_columnconfigure(0, weight=1)

    # 3) Botón cerrar en fila 0, esquina NE
    btn = ttk.Button(_overlay, text="✖", command=_close_overlay)
    btn.grid(row=0, column=0, sticky="ne", padx=10, pady=10)

    # 4) Cargar la imagen
    card = ALL_CARDS[card_name]
    # intenta imagen en disco
    path = _find_image(card_name)
    pil = None
    if path:
        try:
            pil = Image.open(path).convert("RGBA")
        except:
            pil = None
    # fallback a memoria
    if pil is None and hasattr(card, "image"):
        pil = card.image.copy()
    if pil:
        pil = pil.resize((507,727), Image.LANCZOS)
    else:
        pil = Image.new("RGBA", (507,727), (255,255,255,0))
    big_img = ImageTk.PhotoImage(pil)
    _overlay.big_ref = big_img  # evitar GC

    # 5) Mostrar imagen en fila 1, centrada
    img_lbl = tk.Label(_overlay, image=big_img, bd=5, relief="solid",
                       bg=_overlay.cget("bg"))
    img_lbl.grid(row=1, column=0, pady=(0,20))

    # 6) Preparar estadísticas
    stats = []
    if card.cost is not None:
        stats.append(("Coste", str(card.cost)))
    if getattr(card, "strength", None) is not None:
        stats.append(("Fuerza", str(card.strength)))
    stats.append(("Tipo", card.category))
    if getattr(card, "race", None):
        stats.append(("Raza", card.race.title()))

    # 7) Frame de stats en fila 2, centrado
    stats_frame = tk.Frame(_overlay, bg=_overlay.cget("bg"))
    stats_frame.grid(row=2, column=0, pady=(0,20))

    # 8) Grid interno para parámetros y valores
    stats_frame.grid_columnconfigure(0, weight=1, pad=10)
    stats_frame.grid_columnconfigure(2, weight=1, pad=10)
    sep = ttk.Separator(stats_frame, orient="vertical")
    sep.grid(row=0, column=1, rowspan=len(stats), sticky="ns", padx=5)

    for i, (param, val) in enumerate(stats):
        tk.Label(stats_frame, text=f"{param}:", font=("Tahoma",14,"bold"),
                 bg=_overlay.cget("bg")).grid(row=i, column=0, sticky="e", padx=(0,5))
        tk.Label(stats_frame, text=val, font=("Tahoma",12,"bold"),
                 bg=_overlay.cget("bg")).grid(row=i, column=2, sticky="w", padx=(5,0))

def show_detail_on_middle_click(event):
    item = event.widget.find_withtag("current")
    if not item:
        return
    name = image_id_to_name.get(item[0])
    if name:
        _show_card_overlay(name)

# -----------------------------------------------------------------------------
# Ajustes de layout en el panel derecho
# -----------------------------------------------------------------------------
right_panel.grid_columnconfigure(0, weight=1)        # frames ahora se expanden

# -----------------------------------------------------------------------------  
# Bindings on the deck canvas: left-click to remove, right-click to add,  
# middle-click on a card to show detail overlay  
# -----------------------------------------------------------------------------
# First, canvas-wide binds for background clicks (optional):
deck_canvas.bind("<Button-1>", remove_card_by_click)
deck_canvas.bind("<Button-3>", add_card_by_right_click)

# ---------------------------------------------------------------------------
# Hover: only bring card to front on enter, restore stacking on leave
# ---------------------------------------------------------------------------
_hover_stack = {}

def _on_card_enter(event):
    canvas = event.widget
    # find the hovered card item
    items = canvas.find_withtag("current")
    if not items:
        return
    item = items[0]

    # record what was above this card so we can restore later
    all_cards = list(canvas.find_withtag("card"))
    try:
        idx = all_cards.index(item)
    except ValueError:
        return
    _hover_stack[item] = all_cards[idx+1:]

    # bring this card above all others
    canvas.tag_raise(item)

def _on_card_leave(event):
    canvas = event.widget
    # restore original stacking order
    for item, was_above in _hover_stack.items():
        for other in was_above:
            canvas.tag_raise(other)
    _hover_stack.clear()


# ---------------------------------------------------------------------------
# Bindings on the deck canvas: remove/add/detail and hover
# ---------------------------------------------------------------------------
# Background clicks
deck_canvas.bind("<Button-1>", remove_card_by_click)
deck_canvas.bind("<Button-3>", add_card_by_right_click)

# Clear any old hover binds
deck_canvas.tag_unbind("card", "<Enter>")
deck_canvas.tag_unbind("card", "<Leave>")

# Hover binds on actual card items
deck_canvas.tag_bind("card", "<Enter>", _on_card_enter)
deck_canvas.tag_bind("card", "<Leave>", _on_card_leave)

# Middle-click on a card item → show detail overlay
deck_canvas.tag_bind("card", "<ButtonPress-2>", show_detail_on_middle_click)

# Inicializar display y arrancar loop
update_deck_display()
root.mainloop()
