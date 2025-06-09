import os
import sys
import ast
import random
import math
import tkinter as tk
from tkinter import messagebox
from collections import Counter, defaultdict
from PIL import Image, ImageTk

print("DEBUG: cargando main.py desde:", __file__)

# =============================================================================
# 0) MANEJO DE RUTAS PARA SCRIPT VS. EXE
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

BASE_PATH = get_base_path()
CARD_DATA_DIR    = os.path.join(BASE_PATH, "card_data")
CARD_IMAGES_DIR  = os.path.join(BASE_PATH, "card_images")
DECKS_DIR        = os.path.join(BASE_PATH, "decks")
RESTRICTIONS_DIR = os.path.join(BASE_PATH, "restrictions")
UI_IMAGES_DIR    = os.path.join(BASE_PATH, "ui_images")

# =============================================================================
# CARGA DE IMÁGENES PARA BOTONES
# =============================================================================

class ImageButton(tk.Button):
    """
    Un botón que usa dos imágenes: una para estado normal y otra mientras
    el click izquierdo está presionado. Conserva el texto y el command.
    """
    def __init__(self, master, **kwargs):
        cmd = kwargs.pop("command", None)
        txt = kwargs.pop("text", "")
        fnt = kwargs.pop("font", None)
        width = kwargs.pop("width", None)
        super().__init__(master,
                         image=button_img,
                         text=txt,
                         command=cmd,
                         compound="center",
                         bd=0,
                         highlightthickness=0,
                         font=fnt,
                         width=width)
        self.image_default = button_img
        self.image_pressed = button_pressed_img
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)

    def _on_press(self, event):
        self.config(image=self.image_pressed)

    def _on_release(self, event):
        self.config(image=self.image_default)
        # invoke() para respetar la lógica de tk.Button
        if self["command"]:
            self.invoke()


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
# 5) CARGAR TODOS LOS CARDS
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
# 6) RESUMEN DE CATEGORÍAS
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
# 7) DATOS PARA CURVA DE MANÁ
# =============================================================================
cost_category_counts = {i: defaultdict(int) for i in range(0, 11)}

# =============================================================================
# 8) VARIABLES GLOBALES DE FILTROS
# =============================================================================
current_saga   = None
current_race   = None
current_format = None

# =============================================================================
# 9) FUNCIONES AUXILIARES DE VALIDACIÓN Y FILTRADO
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
            font=("Helvetica", 9, "bold")
        )
        total = sum(cost_category_counts[cost_idx].values())
        curve_canvas.create_text(
            x0 + BAR_WIDTH / 2,
            MARGIN_Y,
            text=str(total),
            anchor="s",
            font=("Helvetica", 9, "bold")
        )

image_id_to_name = {}
resized_images = {}
def card_sort_key(card_name):
    card = ALL_CARDS[card_name]
    cost_for_sort = card.cost if card.cost is not None else 999
    return (category_priority[card.category], cost_for_sort, card.name.lower())

def update_deck_display():
    deck_canvas.delete("all")
    image_id_to_name.clear()

    flat_list = deck.list_all_copies()
    non_oro = [n for n in flat_list if ALL_CARDS[n].category != "Oros"]
    oros_counts = {n: cnt for n, cnt in deck.card_counts.items() if ALL_CARDS[n].category == "Oros"}

    sorted_non_oro = sorted(non_oro, key=card_sort_key)
    CANVAS_W = int(deck_canvas.cget("width"))

    CARD_W, CARD_H = 80, 120    # ← fixed width & height
    DUP_OFFSET = 20
    SAME_CAT_OFFSET = 60
    DIFF_CAT_OFFSET = CARD_W

    x, y = 0, 0
    cur_name = None
    cur_cat = None

    # dibujar no-oro
    for name in sorted_non_oro:
        card = ALL_CARDS[name]
        if cur_name is None:
            offset = 0
        else:
            if name == cur_name:
                offset = DUP_OFFSET
            elif card.category == cur_cat:
                offset = SAME_CAT_OFFSET
            else:
                offset = DIFF_CAT_OFFSET

        nx = x + offset
        if nx + CARD_W > CANVAS_W:
            nx, x = 0, 0
            y += CARD_H + 20
            cur_name = cur_cat = None

        if card.tk_image is None:
            try:
                card.load_image()
            except FileNotFoundError:
                continue

        img = card.tk_image
        img_id = deck_canvas.create_image(nx, y, image=img, anchor="nw", tags=("card",))
        image_id_to_name[img_id] = name

        cur_name, cur_cat, x = name, card.category, nx

    # dibujar oros al final
    if oros_counts:
        x = 0
        y += CARD_H + 20
        for name, cnt in oros_counts.items():
            card = ALL_CARDS[name]
            if card.tk_image is None:
                try:
                    card.load_image()
                except FileNotFoundError:
                    continue
            img = card.tk_image
            # si es oro, dibujar una sola imagen + texto
            if name.lower() == "oro":
                img_id = deck_canvas.create_image(x, y, image=img, anchor="nw", tags=("card",))
                image_id_to_name[img_id] = name
                deck_canvas.create_text(
                    x + CARD_W + 20,
                    y + CARD_H//2,
                    text=f"x{cnt}",
                    anchor="w",
                    font=("Helvetica", 16, "bold"),
                    fill="black"
                )
                x += CARD_W + 100
            else:
                # múltiples copias
                for _ in range(cnt):
                    img_id = deck_canvas.create_image(x, y, image=img, anchor="nw", tags=("card",))
                    image_id_to_name[img_id] = name
                    x += DUP_OFFSET
                x += CARD_W

    update_category_summary()


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

def display_hand(hand_list):
    deal_canvas.delete("all")
    cols = 4
    spacing = 10
    CARD_W = 60
    CARD_H = None
    count_aliados = 0
    count_oros = 0
    count_soporte = 0

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
        else:
            count_soporte += 1

    info_text.config(
        text=f"Aliados: {count_aliados}\nOros: {count_oros}\nSoporte: {count_soporte}"
    )

    if count_oros >= 2:
        lbl_two_oros.config(fg="green")
    else:
        lbl_two_oros.config(fg="red")

    has_1or2_ali = any(
        ALL_CARDS[n].category == "Aliados" and ALL_CARDS[n].cost in (1, 2)
        for n in hand_list
    )
    if has_1or2_ali:
        lbl_turn1.config(fg="green")
    else:
        lbl_turn1.config(fg="red")

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
    if saga == "Hijos de Daana":
        color = "#37eca5"
    elif saga == "Helenica":
        color = "#c5aa87"
    elif saga == "Espada Sagrada":
        color = "#acbcf7"
    elif saga == "Dominios de Ra":
        color = "#eccc37"
    else:
        color = BG_DEFAULT

    # Aplica a todos los contenedores principales
    root.configure(bg=color)
    left_container.configure(bg=color)
    right_panel.configure(bg=color)
    summary_frame.configure(bg=color)
    stats_frame.configure(bg=color)
    curve_canvas.configure(bg="#e0e0e0")  # curva siempre gris claro
    menu_frame.configure(bg=color)
    card_entry.configure(bg="white")
    saga_menu.configure(bg=color)
    race_menu.configure(bg=color)
    format_menu.configure(bg=color)
    qty_menu.configure(bg=color)
    deck_canvas.configure(bg=color)
    deck_option.configure(bg=color)
    deal_canvas.configure(bg=color)
    sim_frame.configure(bg=color)
    hand_frame.configure(bg=color)
    consistency_frame.configure(bg=color)

# =============================================================================
# Funciones para poblar OptionMenus de Saga, Raza y Formato
# =============================================================================
def refresh_race_options(selected_saga):
    menu = race_menu["menu"]
    menu.delete(0, "end")
    if not selected_saga or selected_saga not in RACES_BY_SAGA:
        race_var.set("Seleccione")
        race_menu.config(state="disabled")
        format_var.set("Seleccione")
        format_menu.config(state="disabled")
        return
    race_var.set("Seleccione")
    for raza in RACES_BY_SAGA[selected_saga]:
        display = raza.capitalize()
        menu.add_command(label=display, command=lambda v=display: race_var.set(v))
    race_menu.config(state="normal")
    format_var.set("Seleccione")
    format_menu.config(state="disabled")

def refresh_format_options():
    menu = format_menu["menu"]
    menu.delete(0, "end")
    for fmt in ("Pbx", "Reborn"):
        menu.add_command(label=fmt, command=lambda v=fmt: format_var.set(v))
    format_var.set("Seleccione")
    format_menu.config(state="normal")

def update_label_highlight():
    if saga_var.get() == "Seleccione":
        lbl_saga.config(fg="red")
        lbl_raza.config(fg=BG_DEFAULT)
        lbl_formato.config(fg=BG_DEFAULT)
    elif race_var.get() == "Seleccione":
        lbl_saga.config(fg=BG_DEFAULT)
        lbl_raza.config(fg="red")
        lbl_formato.config(fg=BG_DEFAULT)
    elif format_var.get() == "Seleccione":
        lbl_saga.config(fg=BG_DEFAULT)
        lbl_raza.config(fg=BG_DEFAULT)
        lbl_formato.config(fg="red")
    else:
        lbl_saga.config(fg=BG_DEFAULT)
        lbl_raza.config(fg=BG_DEFAULT)
        lbl_formato.config(fg=BG_DEFAULT)

def on_saga_change(*args):
    global current_saga, current_race, current_format
    sel = saga_var.get()
    card_entry.delete(0, tk.END)
    current_race = None
    race_var.set("Seleccione")
    race_menu.config(state="disabled")
    current_format = None
    format_var.set("Seleccione")
    format_menu.config(state="disabled")

    if sel == "Seleccione":
        current_saga = None
    else:
        invalidas = [n for n in deck.card_counts if n.lower() != "oro" and ALL_CARDS[n].saga != sel]
        if invalidas and deck.total_cards() > 0:
            if deck.is_saved:
                if messagebox.askyesno("Cartas inválidas",
                                       "Tu baraja contiene cartas que no pertenecen a la saga seleccionada.\n¿Deseas guardar antes de vaciarla?"):
                    save_deck_gui()
            deck.card_counts.clear()
            deck.is_saved = False

        current_saga = sel
        set_background_color_for_saga(sel)

        menu = race_menu["menu"]
        menu.delete(0, "end")
        menu.add_command(label="Seleccione", command=lambda: race_var.set("Seleccione"))
        for raza in RACES_BY_SAGA[sel]:
            display = raza.capitalize()
            menu.add_command(label=display, command=lambda v=display: race_var.set(v))
        race_menu.config(state="normal")
        race_menu.grid_propagate(False)

    update_category_summary()
    update_mana_curve()
    update_deck_display()
    update_consistency()
    update_stats()
    update_label_highlight()

def on_race_change(*args):
    global current_race, current_format
    sel_raw = race_var.get()
    card_entry.delete(0, tk.END)
    current_format = None
    format_var.set("Seleccione")
    format_menu.config(state="disabled")

    if sel_raw == "Seleccione":
        current_race = None
    else:
        sel = sel_raw.lower()
        invalidas = [n for n in deck.card_counts
                     if ALL_CARDS[n].category == "Aliados" and ALL_CARDS[n].race != sel]
        if invalidas and deck.total_cards() > 0:
            if deck.is_saved:
                if messagebox.askyesno("Cartas inválidas",
                                       "Tu baraja contiene Aliados de otra raza.\n¿Deseas guardar antes de vaciarla?"):
                    save_deck_gui()
            deck.card_counts.clear()
            deck.is_saved = False

        current_race = sel
        menu = format_menu["menu"]
        menu.delete(0, "end")
        menu.add_command(label="Seleccione", command=lambda: format_var.set("Seleccione"))
        for fmt in ("Pbx", "Reborn"):
            menu.add_command(label=fmt, command=lambda v=fmt: format_var.set(v))
        format_menu.config(state="normal")

    update_category_summary()
    update_mana_curve()
    update_deck_display()
    update_consistency()
    update_stats()
    update_label_highlight()

def on_format_change(*args):
    global current_format
    sel = format_var.get()
    card_entry.delete(0, tk.END)
    if sel == "Seleccione":
        current_format = None
    else:
        lowercase = sel.lower()
        invalidas = [n for n in deck.card_counts if n.lower() != "oro" and ALL_CARDS[n].format != lowercase]
        if invalidas and deck.total_cards() > 0:
            if deck.is_saved:
                if messagebox.askyesno("Cartas inválidas",
                                       "Tu baraja contiene cartas de otro formato.\n¿Deseas guardar antes de vaciarla?"):
                    save_deck_gui()
            deck.card_counts.clear()
            deck.is_saved = False
        current_format = lowercase

    update_category_summary()
    update_mana_curve()
    update_deck_display()
    update_consistency()
    update_stats()
    update_label_highlight()

# =============================================================================
# CONFIGURACIÓN DE LA INTERFAZ (GUI)
# =============================================================================
root = tk.Tk()
BTN_W, BTN_H = 120, 30
# load & resize the default state
_raw = Image.open(os.path.join(UI_IMAGES_DIR, "button.png"))
_resized = _raw.resize((BTN_W, BTN_H), Image.LANCZOS)
button_img = ImageTk.PhotoImage(_resized)

# load & resize the pressed state
_raw2 = Image.open(os.path.join(UI_IMAGES_DIR, "button_pressed.png"))
_resized2 = _raw2.resize((BTN_W, BTN_H), Image.LANCZOS)
button_pressed_img = ImageTk.PhotoImage(_resized2)
root.title("Mitos y Leyendas: Constructor de Barajas")
BG_DEFAULT = "#d3d3d3"
root.configure(bg=BG_DEFAULT)
root.geometry("1200x970")

left_container = tk.Frame(root, bg=BG_DEFAULT)
divider        = tk.Frame(root, bg="black", width=4)
right_panel    = tk.Frame(root, bg=BG_DEFAULT)

left_container.grid(row=0, column=0, rowspan=4, sticky="nsew")
divider       .grid(row=0, column=1, rowspan=4, sticky="ns")
right_panel   .grid(row=0, column=2, rowspan=4, sticky="nsew")

root.grid_columnconfigure(0, weight=1)
root.grid_columnconfigure(1, weight=0)
root.grid_columnconfigure(2, weight=1)
root.grid_rowconfigure(0, weight=5)
root.grid_rowconfigure(1, weight=2)
root.grid_rowconfigure(2, weight=2)
root.grid_rowconfigure(3, weight=1)

left_container.grid_columnconfigure(0, weight=3)
left_container.grid_columnconfigure(1, weight=1)
left_container.grid_rowconfigure(0, weight=5)
left_container.grid_rowconfigure(1, weight=2)
left_container.grid_rowconfigure(2, weight=2)
left_container.grid_rowconfigure(3, weight=1)

right_panel.grid_columnconfigure(0, weight=1)
right_panel.grid_rowconfigure(0, weight=2)
right_panel.grid_rowconfigure(1, weight=3)
right_panel.grid_rowconfigure(2, weight=4)
right_panel.grid_rowconfigure(3, weight=1)

# 12) Deck Canvas
deck_canvas = tk.Canvas(
    left_container,
    width=950,
    height=500,
    bg=BG_DEFAULT,
    bd=0,
    highlightthickness=0
)
deck_canvas.grid(row=0, column=0, padx=10, pady=10, sticky="nw")

def refresh_deck_dropdown():
    menu = deck_option["menu"]
    menu.delete(0, "end")
    files = get_deck_files()
    if not files:
        deck_var.set("Sin barajas")
    else:
        deck_var.set(files[-1])    # mostrar la última por defecto
        for filename in files:
            menu.add_command(
                label=filename,
                command=lambda value=filename: deck_var.set(value)
            )
    deck_option.config(justify="right", anchor="e")

# 13) Category Summary
summary_frame = tk.Frame(left_container, bg=BG_DEFAULT)
summary_frame.grid(row=0, column=1, padx=(0,20), pady=10, sticky="ne")
for idx, cat in enumerate(category_order):
    lbl_name = tk.Label(
        summary_frame,
        text=f"{cat}:",
        font=("Helvetica", 10, "bold"),
        bg=BG_DEFAULT
    )
    lbl_count = tk.Label(
        summary_frame,
        text="0",
        font=("Helvetica", 10),
        bg=BG_DEFAULT
    )
    lbl_name.grid(row=idx, column=0, sticky="w")
    lbl_count.grid(row=idx, column=1, sticky="e")
    category_labels[cat] = lbl_count

# Mana Curve
curve_canvas = tk.Canvas(left_container, width=400, height=200, bg="#e0e0e0", bd=0, highlightthickness=0)
curve_canvas.grid(row=1, column=0, padx=10, pady=(0,10), sticky="nw")

# =============================================================================
# Estadísticas Adicionales
# =============================================================================
stats_frame = tk.LabelFrame(
    left_container,
    text="Estadísticas Adicionales",
    bg=BG_DEFAULT,
    font=("Helvetica", 10, "bold"),
    padx=5,
    pady=5
)
stats_frame.grid(row=2, column=1, padx=10, pady=(0,10), sticky="nw")

lbl_avg_cost = tk.Label(
    stats_frame,
    text="Costo promedio (baraja): 0.00",
    font=("Helvetica", 10),
    bg=BG_DEFAULT
)
lbl_avg_str  = tk.Label(
    stats_frame,
    text="Fuerza aliados promedio: 0.00",
    font=("Helvetica", 10),
    bg=BG_DEFAULT
)
lbl_avg_cost.grid(row=0, column=0, sticky="w", pady=(0,2))
lbl_avg_str .grid(row=1, column=0, sticky="w")

# Lower menu: Saga, Raza, Formato, Carta, Cantidad, Botones
menu_frame = tk.Frame(left_container, bg=BG_DEFAULT)
menu_frame.grid(row=3, column=0, columnspan=2, padx=10, pady=(10,20), sticky="w")

# Saga
lbl_saga = tk.Label(menu_frame, text="Saga:", font=("Helvetica",10,"bold"), bg=BG_DEFAULT, fg="red")
lbl_saga.grid(row=0, column=0, sticky="e")
saga_var = tk.StringVar(value="Seleccione")
saga_options = ["Seleccione"] + list(SAGA_FOLDERS.keys())
saga_menu = tk.OptionMenu(menu_frame, saga_var, *saga_options)
saga_menu.config(width=18, font=("Helvetica", 10), bg=BG_DEFAULT)
saga_menu.grid(row=0, column=1, padx=(5,20))
saga_menu.grid_propagate(False)

# Raza
lbl_raza = tk.Label(menu_frame, text="Raza:", font=("Helvetica",10,"bold"), bg=BG_DEFAULT, fg=BG_DEFAULT)
lbl_raza.grid(row=0, column=2, sticky="e")
race_var = tk.StringVar(value="Seleccione")
race_menu = tk.OptionMenu(menu_frame, race_var, "Seleccione")
race_menu.config(width=15, font=("Helvetica",10), bg=BG_DEFAULT, state="disabled")
race_menu.grid(row=0, column=3, padx=(5,20))
race_menu.grid_propagate(False)

# Formato
lbl_formato = tk.Label(menu_frame, text="Formato:", font=("Helvetica",10,"bold"), bg=BG_DEFAULT, fg=BG_DEFAULT)
lbl_formato.grid(row=0, column=4, sticky="e")
format_var = tk.StringVar(value="Seleccione")
format_menu = tk.OptionMenu(menu_frame, format_var, "Seleccione")
format_menu.config(width=10, font=("Helvetica",10), bg=BG_DEFAULT, state="disabled")
format_menu.grid(row=0, column=5, padx=(5,20))
format_menu.grid_propagate(False)

# Carta entry with autocomplete
tk.Label(menu_frame, text="Carta:", font=("Helvetica",10,"bold"), bg=BG_DEFAULT).grid(row=1, column=0, sticky="e")
card_entry = tk.Entry(menu_frame, width=30, font=("Helvetica",10))
card_entry.grid(row=1, column=1, columnspan=3, padx=(5,20))
card_entry.bind("<KeyRelease>", lambda e: None)  # keep original autocomplete logic

# Cantidad
tk.Label(menu_frame, text="Cantidad:", font=("Helvetica",10,"bold"), bg=BG_DEFAULT).grid(row=1, column=4, sticky="e")
qty_var = tk.StringVar(value="1")
qty_menu = tk.OptionMenu(menu_frame, qty_var, "1","2","3")
qty_menu.config(width=5, font=("Helvetica",10), bg=BG_DEFAULT)
qty_menu.grid(row=1, column=5, padx=(5,20))

# Botones Añadir / Eliminar
add_button = ImageButton(menu_frame, text="Añadir carta", font=("Helvetica",10,"bold"), command=add_card_gui)
add_button.grid(row=1, column=6, padx=(5,20))
remove_button = ImageButton(menu_frame, text="Eliminar carta", font=("Helvetica",10,"bold"), command=remove_card_gui)
remove_button.grid(row=1, column=7, padx=(5,20))

# Guardar / Importar / Salir
tk.Label(menu_frame, text="Guardar como:", font=("Helvetica",10,"bold"), bg=BG_DEFAULT).grid(row=2, column=0, sticky="e", pady=(10,0))
save_entry = tk.Entry(menu_frame, width=20, font=("Helvetica",10))
save_entry.grid(row=2, column=1, padx=(5,20), pady=(10,0))
save_button = ImageButton(menu_frame, text="Guardar baraja", font=("Helvetica",10,"bold"), command=save_deck_gui)
save_button.grid(row=2, column=2, padx=(5,20), pady=(10,0))

tk.Label(menu_frame, text="Importar baraja:", font=("Helvetica",10,"bold"), bg=BG_DEFAULT).grid(row=2, column=3, sticky="e", pady=(10,0))
deck_var = tk.StringVar(value="Sin barajas")
deck_option = tk.OptionMenu(menu_frame, deck_var, *get_deck_files())
deck_option.config(width=20, justify="right", anchor="e", font=("Helvetica",10), bg=BG_DEFAULT)
deck_option.grid(row=2, column=4, padx=(5,20), pady=(10,0))
refresh_deck_dropdown()
import_button = ImageButton(menu_frame, text="Importar baraja", font=("Helvetica",10,"bold"), command=import_deck_dropdown)
import_button.grid(row=2, column=5, padx=(5,20), pady=(10,0))
quit_button = ImageButton(menu_frame, text="Salir", font=("Helvetica",10,"bold"), command=root.destroy)
quit_button.grid(row=2, column=6, padx=(5,0), pady=(10,0))

# Callbacks
saga_var.trace("w", on_saga_change)
race_var.trace("w", on_race_change)
format_var.trace("w", on_format_change)

# =============================================================================
#  Sección CONSISTENCIA (Right Panel)
# =============================================================================
consistency_frame = tk.LabelFrame(right_panel, text="Consistencia", bg=BG_DEFAULT, font=("Helvetica",10,"bold"), padx=5, pady=5)
consistency_frame.grid(row=0, column=0, padx=10, pady=(10,5), sticky="nwe")

col8 = tk.Frame(consistency_frame, bg=BG_DEFAULT)
col7 = tk.Frame(consistency_frame, bg=BG_DEFAULT)
col6 = tk.Frame(consistency_frame, bg=BG_DEFAULT)
col8.grid(row=0, column=0, padx=(0,10), sticky="nw")
col7.grid(row=0, column=1, padx=(0,10), sticky="nw")
col6.grid(row=0, column=2, sticky="nw")

LABEL_FONT = ("Helvetica", 9)
tk.Label(col8, text="Robar 8 cartas", font=("Helvetica",10,"bold"), bg=BG_DEFAULT).grid(row=0, column=0, sticky="w", pady=(0,4))
lbl8_ali2 = tk.Label(col8, text="Prob. ≥1 Aliado C2: 0%", font=LABEL_FONT, bg=BG_DEFAULT)
lbl8_o2   = tk.Label(col8, text="Prob. ≥2 Oros: 0%",      font=LABEL_FONT, bg=BG_DEFAULT)
lbl8_o3   = tk.Label(col8, text="Prob. ≥3 Oros: 0%",      font=LABEL_FONT, bg=BG_DEFAULT)
lbl8_ali2.grid(row=1, column=0, sticky="w")
lbl8_o2.grid(row=2, column=0, sticky="w")
lbl8_o3.grid(row=3, column=0, sticky="w")

tk.Label(col7, text="8 → 7 Mulligan", font=("Helvetica",10,"bold"), bg=BG_DEFAULT).grid(row=0, column=0, sticky="w", pady=(0,4))
lbl7_ali2 = tk.Label(col7, text="Prob. ≥1 Aliado C2: 0%", font=LABEL_FONT, bg=BG_DEFAULT)
lbl7_o2   = tk.Label(col7, text="Prob. ≥2 Oros: 0%",      font=LABEL_FONT, bg=BG_DEFAULT)
lbl7_o3   = tk.Label(col7, text="Prob. ≥3 Oros: 0%",      font=LABEL_FONT, bg=BG_DEFAULT)
lbl7_ali2.grid(row=1, column=0, sticky="w")
lbl7_o2.grid(row=2, column=0, sticky="w")
lbl7_o3.grid(row=3, column=0, sticky="w")

tk.Label(col6, text="8 → 7 → 6 Mulligan", font=("Helvetica",10,"bold"), bg=BG_DEFAULT).grid(row=0, column=0, sticky="w", pady=(0,4))
lbl6_ali2 = tk.Label(col6, text="Prob. ≥1 Aliado C2: 0%", font=LABEL_FONT, bg=BG_DEFAULT)
lbl6_o2   = tk.Label(col6, text="Prob. ≥2 Oros: 0%",      font=LABEL_FONT, bg=BG_DEFAULT)
lbl6_o3   = tk.Label(col6, text="Prob. ≥3 Oros: 0%",      font=LABEL_FONT, bg=BG_DEFAULT)
lbl6_ali2.grid(row=1, column=0, sticky="w")
lbl6_o2.grid(row=2, column=0, sticky="w")
lbl6_o3.grid(row=3, column=0, sticky="w")

# =============================================================================
# Repartir Mano Aleatoria (Right Panel)
# =============================================================================
hand_frame = tk.LabelFrame(right_panel, text="Repartir Mano Aleatoria", bg=BG_DEFAULT, font=("Helvetica",10,"bold"), padx=5, pady=5)
hand_frame.grid(row=1, column=0, padx=10, pady=(5,10), sticky="nwe")

deal_canvas = tk.Canvas(hand_frame, width=300, height=240, bg=BG_DEFAULT, bd=0, highlightthickness=0)
deal_canvas.grid(row=0, column=0, rowspan=2, padx=(5,5), pady=(5,5), sticky="nw")

info_text = tk.Label(hand_frame, text="Aliados: 0\nOros: 0\nSoporte: 0", justify="left", bg=BG_DEFAULT, font=("Helvetica",10,"bold"))
info_text.grid(row=0, column=1, padx=(10,10), pady=(5,5), sticky="nw")

sim_frame = tk.Frame(hand_frame, bg=BG_DEFAULT)
sim_frame.grid(row=1, column=1, padx=(10,10), pady=(5,5), sticky="nw")

thousand_button = ImageButton(
    sim_frame,
    text="1000 Manos",
    font=("Helvetica", 10, "bold"),
    command=simulate_1000_hands
)
thousand_button.grid(row=0, column=0, padx=(0,5))
lbl_sim_two_oros = tk.Label(sim_frame, text="Manos ≥2 Oros: 0", bg=BG_DEFAULT, font=("Helvetica",10))
lbl_sim_turn1    = tk.Label(sim_frame, text="Manos Turno1 Jugada: 0", bg=BG_DEFAULT, font=("Helvetica",10))
lbl_sim_great    = tk.Label(sim_frame, text="Manos excelentes: 0", bg=BG_DEFAULT, font=("Helvetica",10))
lbl_sim_two_oros.grid(row=1, column=0, sticky="w")
lbl_sim_turn1   .grid(row=2, column=0, sticky="w")
lbl_sim_great   .grid(row=3, column=0, sticky="w")

hand_button_frame = tk.Frame(hand_frame, bg=BG_DEFAULT)
hand_button_frame.grid(row=2, column=0, columnspan=2, pady=(5,5), sticky="we")
lbl_two_oros = tk.Label(hand_button_frame, text="2 Oros", font=("Helvetica",10,"bold"), fg="black", bg=BG_DEFAULT)
lbl_two_oros.grid(row=0, column=0, padx=(0,20), sticky="w")
deal_button = ImageButton(
    hand_button_frame,
    text="Repartir mano",
    font=("Helvetica", 10, "bold"),
    command=deal_hand
)
deal_button.grid(row=0, column=1, padx=(0,10))
mulligan_button = ImageButton(
    hand_button_frame,
    text="Mulligan",
    font=("Helvetica", 10, "bold"),
    command=mulligan
)
mulligan_button.grid(row=0, column=2, padx=(0,20))
lbl_turn1 = tk.Label(hand_button_frame, text="Turno 1 jugada", font=("Helvetica",10,"bold"), fg="black", bg=BG_DEFAULT)
lbl_turn1.grid(row=0, column=3, sticky="e")
for i in range(4):
    hand_button_frame.grid_columnconfigure(i, weight=1)

# =============================================================================
# Eventos de clic sobre carta
# =============================================================================
def remove_card_by_click(event):
    clicked = deck_canvas.find_withtag("current")
    if not clicked:
        return
    item_id = clicked[0]
    name = image_id_to_name.get(item_id)
    if name and deck.card_counts.get(name, 0) > 0:
        deck.remove_card(name, 1)
        update_category_summary()
        update_mana_curve()
        update_deck_display()
        update_consistency()
        update_stats()

def add_card_by_right_click(event):
    clicked = deck_canvas.find_withtag("current")
    if not clicked:
        return
    item_id = clicked[0]
    name = image_id_to_name.get(item_id)
    if name:
        can_add, reason = can_add_card(name, 1)
        if not can_add:
            messagebox.showwarning("No permitido", reason)
            return
        deck.add_card(name, 1)
        update_category_summary()
        update_mana_curve()
        update_deck_display()
        update_consistency()
        update_stats()

deck_canvas.bind("<Button-1>", remove_card_by_click)
deck_canvas.bind("<Button-3>", add_card_by_right_click)

# Inicializar display y arrancar loop
update_deck_display()
root.mainloop()
