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


print("DEBUG: cargando main.py desde:", __file__)

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
            return False, "La baraja no puede exceder 50 cartas."
        return True, ""

    # ── NORMAL CASE FOR ALL OTHER CARDS ──
    if current_saga is None or current_race is None or current_format is None:
        return False, "Debes elegir Saga, Raza y Formato primero."

    carta = ALL_CARDS[name]
    if not is_card_valid_for_filters(name):
        return False, "Esta carta no cumple los filtros de Saga/Raza/Formato."

    total_actual = deck.total_cards()
    if total_actual + qty > 50:
        return False, "La baraja no puede exceder 50 cartas."

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

    lbl_avg_cost.config(text=f"Costo promedio (baraja): {avg_cost:.2f}")
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
    if choice == "Sin barajas":
        messagebox.showwarning("Error", "No hay barajas para importar.")
        return
    path = os.path.join(DECKS_DIR, choice)
    if not os.path.isfile(path):
        messagebox.showwarning("Error", f"No se encontró {path}")
        return

    deck.card_counts.clear()
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
            name = parts[1]
            lookup = name.lower()
            if lookup not in CARD_NAME_MAP:
                continue
            canonical = CARD_NAME_MAP[lookup]
            if not is_card_valid_for_filters(canonical):
                continue
            max_allowed = restricted_limits.get(canonical, CARD_MAX_DEFAULT)
            actual_add = min(qty, 50 - deck.total_cards(), max_allowed)
            if actual_add <= 0:
                continue
            deck.card_counts[canonical] = actual_add

    deck.is_saved = True
    update_category_summary()
    update_mana_curve()
    update_deck_display()
    update_consistency()
    update_stats()

def save_deck_gui():
    fname = save_entry.get().strip()
    if not fname:
        messagebox.showerror("Error", "El nombre de archivo no puede estar vacío.")
        return

    path = save_deck_to_file(deck.card_counts, fname)
    messagebox.showinfo("Guardado", f"Baraja guardada en:\n{path}")
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
    deck_canvas.delete("all")
    try: _draw_deck_bg()
    except: pass

    image_id_to_name.clear()
    flat = deck.list_all_copies()

    # NON-ORO
    x, y = DECK_CANVAS_LEFT_MARGIN, DECK_CANVAS_TOP_MARGIN
    cur_name = cur_cat = None
    last_h = 0
    CANVAS_W = int(deck_canvas.winfo_width())

    for name in sorted([n for n in flat if ALL_CARDS[n].category!="Oros"], key=card_sort_key):
        card = ALL_CARDS[name]
        # tk_image was preloaded at startup
        CARD_W = card.tk_image.width()
        CARD_H = card.tk_image.height()
        last_h = CARD_H

        DUP = CARD_W//4; SAME = CARD_W*3//4; DIFF = CARD_W
        offset = 0 if cur_name is None else (DUP if name==cur_name else SAME if card.category==cur_cat else DIFF)
        nx = x + offset

        if nx+CARD_W > CANVAS_W - DECK_CANVAS_RIGHT_MARGIN:
            nx = DECK_CANVAS_LEFT_MARGIN
            y += CARD_H + DECK_VERTICAL_GUTTER
            cur_name = cur_cat = None

        img_id = deck_canvas.create_image(nx, y, image=card.tk_image, anchor="nw", tags=("card",))
        image_id_to_name[img_id] = name
        cur_name, cur_cat, x = name, card.category, nx

    # OROS
    if any(ALL_CARDS[n].category=="Oros" for n in deck.card_counts):
        x = DECK_CANVAS_LEFT_MARGIN
        y += last_h + DECK_VERTICAL_GUTTER
        for name, cnt in ((n,c) for n,c in deck.card_counts.items() if ALL_CARDS[n].category=="Oros"):
            card = ALL_CARDS[name]
            CARD_W=card.tk_image.width(); CARD_H=card.tk_image.height(); DUP=CARD_W//4
            if name.lower()=="oro":
                img_id=deck_canvas.create_image(x,y,image=card.tk_image,anchor="nw",tags=("card",))
                image_id_to_name[img_id]=name
                deck_canvas.create_text(x+CARD_W+20, y+CARD_H//2, text=f"x{cnt}", anchor="w", font=("Tahoma",16,"bold"), fill="black")
                x+=CARD_W+100
            else:
                for _ in range(cnt):
                    img_id=deck_canvas.create_image(x,y,image=card.tk_image,anchor="nw",tags=("card",))
                    image_id_to_name[img_id]=name
                    x+=DUP
                x+=CARD_W

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

    lbl8_ali2.config(text=f"Prob. ≥1 Aliado C2: {probs['p8_ali2']*100:5.2f}%")
    lbl8_o2  .config(text=f"Prob. ≥2 Oros:            {probs['p8_o2']*100:5.2f}%")
    lbl8_o3  .config(text=f"Prob. ≥3 Oros:            {probs['p8_o3']*100:5.2f}%")

    lbl7_ali2.config(text=f"Prob. ≥1 Aliado C2: {probs['p8to7_ali2']*100:5.2f}%")
    lbl7_o2  .config(text=f"Prob. ≥2 Oros:            {probs['p8to7_o2']*100:5.2f}%")
    lbl7_o3  .config(text=f"Prob. ≥3 Oros:            {probs['p8to7_o3']*100:5.2f}%")

    lbl6_ali2.config(text=f"Prob. ≥1 Aliado C2: {probs['p8to7to6_ali2']*100:5.2f}%")
    lbl6_o2  .config(text=f"Prob. ≥2 Oros:            {probs['p8to7to6_o2']*100:5.2f}%")
    lbl6_o3  .config(text=f"Prob. ≥3 Oros:            {probs['p8to7to6_o3']*100:5.2f}%")

# =============================================================================
# Funciones de mano, mulligan y simulación
# =============================================================================
current_hand = []
hand_size = 0

def deal_hand():
    global current_hand, hand_size
    if deck.total_cards() != 50:
        messagebox.showerror("Error", "La baraja debe tener exactamente 50 cartas para repartir.")
        return
    hand_size = 8
    draw_new_hand(hand_size)

def mulligan():
    global current_hand, hand_size
    if not current_hand:
        messagebox.showerror("Error", "No hay mano para mulligan. Presiona ‘Repartir mano’ primero.")
        return
    if hand_size <= 1:
        messagebox.showerror("Error", "No puedes hacer mulligan con menos de 1 carta.")
        return
    if deck.total_cards() != 50:
        messagebox.showerror("Error", "La baraja debe tener exactamente 50 cartas para mulligan.")
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
        messagebox.showerror("Error", "La baraja debe tener exactamente 50 cartas para simular.")
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
                               "Tu baraja contiene cartas de otra saga.\n"
                               "¿Deseas guardar antes de vaciarla?"):
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
                               "Tu baraja contiene Aliados de otra raza.\n"
                               "¿Deseas guardar antes de vaciarla?"):
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
                "Tu baraja contiene cartas de otro formato.\n"
                "¿Deseas guardar antes de vaciarla?"
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
    """Return a cached thumbnail; uses card.image_path set by splash."""
    thumb = getattr(card, "thumb80", None)
    if thumb:
        return thumb

    if getattr(card, "image_path", None) and os.path.isfile(card.image_path):
        pil = Image.open(card.image_path).convert("RGBA")
        w, h = pil.size
        scale = min(THUMB_W / w, THUMB_H / h)
        new_size = (int(w * scale), int(h * scale))
        pil_thumb = pil.resize(new_size, Image.LANCZOS)

        canvas = Image.new("RGBA", (THUMB_W, THUMB_H), (0, 0, 0, 0))
        x_off = (THUMB_W - new_size[0]) // 2
        y_off = (THUMB_H - new_size[1]) // 2
        canvas.paste(pil_thumb, (x_off, y_off), pil_thumb)

        thumb = ImageTk.PhotoImage(canvas)
        card.thumb80 = thumb
        return thumb

    ph = ImageTk.PhotoImage(Image.new("RGBA", (THUMB_W, THUMB_H), (0,0,0,0)))
    card.thumb80 = ph
    return ph

# ─────────────────────────────────────────────────────────────────────────────
# SHOW SPLASH + PROGRESS BAR DURING PRELOAD
# ─────────────────────────────────────────────────────────────────────────────
root.withdraw()

splash = tk.Toplevel()
splash.overrideredirect(True)
splash.configure(bg=BG_DEFAULT)
# keep splash on top so it’s visible
splash.attributes("-topmost", True)
splash.lift()
splash.update()
w, h = 300, 60
x = (splash.winfo_screenwidth() - w)//2
y = (splash.winfo_screenheight() - h)//2
splash.geometry(f"{w}x{h}+{x}+{y}")

tk.Label(splash, text="Cargando imágenes…",
         font=("Tahoma", 12, "bold"), bg=BG_DEFAULT).pack(pady=(10,0))
bar = ttk.Progressbar(splash, orient="horizontal", length=260, mode="determinate")
bar.pack(pady=(5,10))
bar["maximum"] = len(ALL_CARDS) * 2

# 1) Preload all full-size images
for i, card in enumerate(ALL_CARDS.values(), start=1):
    try:
        card.load_image()
    except FileNotFoundError:
        pass
    bar["value"] = i
    splash.update_idletasks()

# 2) Pre-generate all thumbnails
for i, card in enumerate(ALL_CARDS.values(), start=1):
    _get_thumb(card)
    bar["value"] = len(ALL_CARDS) + i
    splash.update_idletasks()

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

root.title("Mitos y Leyendas: Constructor de Barajas")
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

# Canvas de la baraja
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

# --- Estadísticas Adicionales --------------------------------------------------
stats_frame = tk.LabelFrame(summary_strip, text="Estadísticas Adicionales",
                            bg=BG_DEFAULT, font=("Tahoma",15,"bold"),
                            padx=5, pady=5, labelanchor="nw")
stats_frame.grid(row=0, column=1, padx=(15,15), sticky="n")
lbl_avg_cost = tk.Label(stats_frame, text="Costo promedio (baraja): 0.00",
                        font=("Tahoma",15), bg=BG_DEFAULT, anchor="w")
lbl_avg_str  = tk.Label(stats_frame, text="Fuerza aliados promedio: 0.00",
                        font=("Tahoma",15), bg=BG_DEFAULT, anchor="w")
lbl_avg_cost.grid(row=0, column=0, sticky="w")
lbl_avg_str .grid(row=1, column=0, sticky="w")

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
save_button = ttk.Button(card_menu_frame, text="Guardar baraja",
                         command=save_deck_gui)
save_button.grid(row=1, column=2, padx=(0,20), pady=(8,0))

# — Importar baraja —
ttk.Label(card_menu_frame, text="Importar baraja:",
          font=("Tahoma",12,"bold")
          ).grid(row=1, column=3, sticky="e", pady=(8,0))
deck_var    = tk.StringVar(value="Sin barajas")
deck_option = ttk.Combobox(card_menu_frame, textvariable=deck_var,
                           values=get_deck_files(), state="readonly",
                           width=18)
deck_option.grid(row=1, column=4, sticky="w", padx=(5,10), pady=(8,0))

def refresh_deck_dropdown():
    deck_option.configure(values=get_deck_files())
refresh_deck_dropdown()

import_button = ttk.Button(card_menu_frame, text="Importar baraja",
                           command=import_deck_dropdown)
import_button.grid(row=1, column=5, padx=(10,10), pady=(8,0))

# — Salir —
quit_button = ttk.Button(card_menu_frame, text="Salir",
                         command=root.destroy)
quit_button.grid(row=1, column=6, padx=(0,0), pady=(8,0))

# =============================================================================
# PANEL DERECHO
# =============================================================================

#  Sección CONSISTENCIA

consistency_frame = tk.LabelFrame(right_panel, text="Consistencia", bg=BG_DEFAULT, font=("Tahoma",10,"bold"), padx=5, pady=5)
consistency_frame.grid(row=0, column=0, padx=10, pady=(10,5), sticky="nwe")

col8 = tk.Frame(consistency_frame, bg=BG_DEFAULT)
col7 = tk.Frame(consistency_frame, bg=BG_DEFAULT)
col6 = tk.Frame(consistency_frame, bg=BG_DEFAULT)
col8.grid(row=0, column=0, padx=(0,10), sticky="nw")
col7.grid(row=0, column=1, padx=(0,10), sticky="nw")
col6.grid(row=0, column=2, sticky="nw")

LABEL_FONT = ("Tahoma", 9)
tk.Label(col8, text="Robar 8 cartas", font=("Tahoma",10,"bold"), bg=BG_DEFAULT).grid(row=0, column=0, sticky="w", pady=(0,4))
lbl8_ali2 = tk.Label(col8, text="Prob. ≥1 Aliado C2: 0%", font=LABEL_FONT, bg=BG_DEFAULT)
lbl8_o2   = tk.Label(col8, text="Prob. ≥2 Oros: 0%",      font=LABEL_FONT, bg=BG_DEFAULT)
lbl8_o3   = tk.Label(col8, text="Prob. ≥3 Oros: 0%",      font=LABEL_FONT, bg=BG_DEFAULT)
lbl8_ali2.grid(row=1, column=0, sticky="w")
lbl8_o2.grid(row=2, column=0, sticky="w")
lbl8_o3.grid(row=3, column=0, sticky="w")

tk.Label(col7, text="8 → 7 Mulligan", font=("Tahoma",10,"bold"), bg=BG_DEFAULT).grid(row=0, column=0, sticky="w", pady=(0,4))
lbl7_ali2 = tk.Label(col7, text="Prob. ≥1 Aliado C2: 0%", font=LABEL_FONT, bg=BG_DEFAULT)
lbl7_o2   = tk.Label(col7, text="Prob. ≥2 Oros: 0%",      font=LABEL_FONT, bg=BG_DEFAULT)
lbl7_o3   = tk.Label(col7, text="Prob. ≥3 Oros: 0%",      font=LABEL_FONT, bg=BG_DEFAULT)
lbl7_ali2.grid(row=1, column=0, sticky="w")
lbl7_o2.grid(row=2, column=0, sticky="w")
lbl7_o3.grid(row=3, column=0, sticky="w")

tk.Label(col6, text="8 → 7 → 6 Mulligan", font=("Tahoma",10,"bold"), bg=BG_DEFAULT).grid(row=0, column=0, sticky="w", pady=(0,4))
lbl6_ali2 = tk.Label(col6, text="Prob. ≥1 Aliado C2: 0%", font=LABEL_FONT, bg=BG_DEFAULT)
lbl6_o2   = tk.Label(col6, text="Prob. ≥2 Oros: 0%",      font=LABEL_FONT, bg=BG_DEFAULT)
lbl6_o3   = tk.Label(col6, text="Prob. ≥3 Oros: 0%",      font=LABEL_FONT, bg=BG_DEFAULT)
lbl6_ali2.grid(row=1, column=0, sticky="w")
lbl6_o2.grid(row=2, column=0, sticky="w")
lbl6_o3.grid(row=3, column=0, sticky="w")

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
# NEW: Divider + Card Search section (5-col vertical scroll + drag-and-drop)
# ─────────────────────────────────────────────────────────────────────────────

# 1) horizontal divider line
divider2 = tk.Frame(right_panel, height=2, bg="black")
divider2.grid(row=1, column=0, sticky="we", padx=5, pady=(10,5))

# 2) Card Search frame
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

def _on_search_configure(event):
    search_canvas.configure(scrollregion=search_canvas.bbox("all"))
_search_interior.bind("<Configure>", _on_search_configure)

# mapping from widget → card name
_search_id_to_name = {}

# 5) Populate function
def refresh_search():
    # clear old thumbnails
    for w in _search_interior.winfo_children():
        w.destroy()
    _search_id_to_name.clear()

    # debug: show current filter state
    print(f"[DEBUG] Filters → Saga={current_saga}, Raza={current_race}, Formato={current_format}, Tipo={tipo_var.get()}, Orden={orden_var.get()}")

    # only build grid once all four filters are chosen
    if not (current_saga and current_race and current_format and tipo_var.get() != "Tipo"):
        print("[DEBUG] Not all filters set; skipping grid build")
        return

    # map singular menu choice → internal plural category
    tipo_map = {
        "Aliado":   "Aliados",
        "Talisman": "Talismanes",
        "Totem":    "Totems",
        "Arma":     "Armas",
        "Oro":      "Oros"
    }
    cat_filter = tipo_map.get(tipo_var.get(), None)
    print(f"[DEBUG] Category filter → {cat_filter}")

    # gather & filter
    names = []
    for nm, card in ALL_CARDS.items():
        if card.saga   != current_saga:    continue
        if card.format != current_format:  continue
        if cat_filter and card.category != cat_filter:
            continue
        if card.category == "Aliados" and card.race != current_race:
            continue
        names.append(nm)

    print(f"[DEBUG] {len(names)} cards passed initial filters")

    # sort
    if orden_var.get() == "Coste":
        names.sort(key=lambda n: ALL_CARDS[n].cost or 0)
    elif orden_var.get() == "Fuerza":
        names.sort(key=lambda n: ALL_CARDS[n].strength or 0)
    else:  # Alfabético
        names.sort()
    print(f"[DEBUG] First 5 after sort: {names[:5]}")

    # draw in 5-col grid
    cols, gap = 5, 6
    for idx, nm in enumerate(names):
        card = ALL_CARDS[nm]
        thumb = _get_thumb(card)
        if not hasattr(card, "thumb80"):
            print(f"[DEBUG] Missing thumbnail for {nm}")

        row, col = divmod(idx, cols)
        lbl = tk.Label(_search_interior, image=thumb, bg=BG_DEFAULT, cursor="hand2")
        lbl.image = thumb
        lbl.grid(row=row, column=col, padx=gap, pady=gap)

        _search_id_to_name[lbl] = nm
        lbl.bind("<ButtonPress-1>",  start_search_drag)
        lbl.bind("<B1-Motion>",      on_search_drag)
        lbl.bind("<ButtonRelease-1>", on_search_release)

    print("[DEBUG] Grid built successfully")

# dynamic refresh on filter changes
tipo_menu.bind("<<ComboboxSelected>>", lambda e: refresh_search())
orden_menu.bind("<<ComboboxSelected>>", lambda e: refresh_search())
# also call refresh_search() at the end of on_saga_change, on_race_change, on_format_change

# 6) Drag & Drop handlers
_drag_data = {"widget": None, "card": None}

def start_search_drag(ev):
    lbl = ev.widget
    card_name = _search_id_to_name.get(lbl)
    if not card_name: return

    _drag_data["widget"] = tk.Label(root, image=lbl.image)
    _drag_data["widget"].image = lbl.image
    _drag_data["widget"].place(x=ev.x_root-40, y=ev.y_root-60)
    _drag_data["card"]   = card_name

def on_search_drag(ev):
    w = _drag_data["widget"]
    if w:
        w.place(x=ev.x_root-40, y=ev.y_root-60)

def on_search_release(ev):
    w = _drag_data["widget"]
    card = _drag_data["card"]
    if w:
        tgt = deck_canvas.winfo_containing(ev.x_root, ev.y_root)
        if tgt == deck_canvas or (hasattr(tgt, "find_withtag") and "card" in deck_canvas.gettags(tgt)):
            ok, reason = can_add_card(card, 1)
            if ok:
                deck.add_card(card, 1)
                update_category_summary(); update_mana_curve()
                update_deck_display(); update_consistency(); update_stats()
            else:
                messagebox.showwarning("No permitido", reason)
        w.destroy()
    _drag_data["widget"] = None
    _drag_data["card"]   = None

# (Removed initial refresh_search() call to avoid startup freeze)

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
# Overlay con detalle (clic central)  -- fuente grande + imagen 507×727
# -----------------------------------------------------------------------------
_overlay = None


def _close_overlay():
    global _overlay
    if _overlay and _overlay.winfo_exists():
        _overlay.destroy()
    _overlay = None


def _find_image(card_name: str):
    """Busca .jpg / .png en cualquier sub-carpeta de card_images/."""
    for root_dir, _, files in os.walk(CARD_IMAGES_DIR):
        if f"{card_name}.jpg" in files:
            return os.path.join(root_dir, f"{card_name}.jpg")
        if f"{card_name}.png" in files:
            return os.path.join(root_dir, f"{card_name}.png")
    return None


def _show_card_overlay(card_name: str):
    global _overlay
    _close_overlay()

    card = ALL_CARDS[card_name]

    # capa sobre right_panel
    _overlay = tk.Frame(right_panel, bg=right_panel.cget("bg"))
    _overlay.place(relx=0, rely=0, relwidth=1, relheight=1)

    ttk.Button(_overlay, text="❌  Cerrar", command=_close_overlay
               ).pack(anchor="ne", padx=6, pady=6)

    # ---------- imagen grande ----------
    img_path = _find_image(card_name)
    try:
        pil = Image.open(img_path) if img_path else None
    except Exception:
        pil = None
    if pil is None:                       # fallback: miniatura ampliada
        pil = card.tk_image._PhotoImage__photo.zoom(3)

    pil = pil.resize((507, 727), Image.LANCZOS)
    big = ImageTk.PhotoImage(pil)
    tk.Label(_overlay, image=big, bg=_overlay.cget("bg")
             ).pack(pady=10)
    # mantener referencia
    _overlay.big_ref = big

    # ---------- stats ----------
    singular = {
        "aliados": "Aliado", "talismanes": "Talisman",
        "totems": "Totem",  "armas": "Arma", "oros": "Oro"
    }
    lines = []
    if card.cost is not None:
        lines.append(f"Coste  : {card.cost}")
    if getattr(card, "strength", None) is not None:
        lines.append(f"Fuerza : {card.strength}")
    cat = getattr(card, "category", "").lower()
    lines.append(f"Tipo   : {singular.get(cat, card.category.title())}")
    if getattr(card, "race", None):
        lines.append(f"Raza   : {card.race.title()}")

    tk.Label(_overlay, text="\n".join(lines),
             font=("Tahoma", 20, "bold"),
             bg=_overlay.cget("bg")
             ).pack(pady=(0, 18))


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
# Bindings
# -----------------------------------------------------------------------------
deck_canvas.bind("<Button-1>", remove_card_by_click)
deck_canvas.bind("<Button-3>", add_card_by_right_click)
deck_canvas.bind("<Button-2>", show_detail_on_middle_click)

# =============================================================================
# Hover: only bring card to front on enter, restore stacking on leave
# =============================================================================
_hover_stack = {}

def _on_card_enter(event):
    canvas = event.widget
    # find the hovered card item
    items = canvas.find_withtag("current")
    if not items:
        return
    item = items[0]

    # record whatever was above this card so we can restore later
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

# rebind handlers (removes any old glow bindings)
deck_canvas.tag_unbind("card", "<Enter>")
deck_canvas.tag_unbind("card", "<Leave>")
deck_canvas.tag_bind("card", "<Enter>", _on_card_enter)
deck_canvas.tag_bind("card", "<Leave>", _on_card_leave)

# Inicializar display y arrancar loop
update_deck_display()
root.mainloop()
