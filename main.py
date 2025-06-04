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
    """
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return sys._MEIPASS

    script_dir = os.path.abspath(os.path.dirname(__file__))
    if (
        os.path.isdir(os.path.join(script_dir, "card_data"))
        and os.path.isdir(os.path.join(script_dir, "card_images"))
        and os.path.isdir(os.path.join(script_dir, "restrictions"))
    ):
        return script_dir

    cwd = os.getcwd()
    if (
        os.path.isdir(os.path.join(cwd, "card_data"))
        and os.path.isdir(os.path.join(cwd, "card_images"))
        and os.path.isdir(os.path.join(cwd, "restrictions"))
    ):
        return cwd

    return script_dir

BASE_PATH = get_base_path()
CARD_DATA_DIR    = os.path.join(BASE_PATH, "card_data")
CARD_IMAGES_DIR  = os.path.join(BASE_PATH, "card_images")
DECKS_DIR        = os.path.join(BASE_PATH, "decks")
RESTRICTIONS_DIR = os.path.join(BASE_PATH, "restrictions")

def verify_data_folders():
    faltantes = []
    if not os.path.isdir(CARD_DATA_DIR):
        faltantes.append(f"  • {CARD_DATA_DIR}")
    if not os.path.isdir(CARD_IMAGES_DIR):
        faltantes.append(f"  • {CARD_IMAGES_DIR}")
    if not os.path.isdir(RESTRICTIONS_DIR):
        faltantes.append(f"  • {RESTRICTIONS_DIR}")

    if faltantes:
        msg = (
            "No se pueden encontrar las carpetas requeridas:\n"
            + "\n".join(faltantes)
            + "\n\nPor favor, asegúrate de que:\n"
            " • Si estás usando el EXE compilado, se incluyeron correctamente\n"
            "   con PyInstaller usando:\n"
            "     --add-data \"card_data;card_data\"\n"
            "     --add-data \"card_images;card_images\"\n"
            "     --add-data \"restrictions;restrictions\"\n"
            " • Si ejecutas como .py, las carpetas card_data/, card_images/ y restrictions/\n"
            "   deben estar junto a main.py o en tu directorio de trabajo actual."
        )
        if getattr(sys, "frozen", False):
            tk.Tk().withdraw()
            messagebox.showerror("Carpetas faltantes", msg)
        else:
            print("ERROR:", msg)
        sys.exit(1)

verify_data_folders()

if not os.path.isdir(DECKS_DIR):
    os.makedirs(DECKS_DIR)

# =============================================================================
# 1) CARGAR RESTRICCIONES
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
# 2) ASOCIACIÓN DE SAGAS A CARPETAS DE IMÁGENES (_)
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
# 3) CLASE CARD: adapta al nuevo formato de los .txt
# =============================================================================
class Card:
    def __init__(self, name):
        """
        name: cadena, p. ej. "julio-cesar" o "oro"
        Carga datos desde card_data/<name>.txt con el siguiente esquema según tipo:
        
        - Oro:
          ["oros", "<saga_abrev>", "<formato>"]
        - Talismanes/Armas/Totems:
          [<coste:int>, "<tipo>", "<saga_abrev>", "<formato>"]
        - Aliados:
          [<coste:int>, <fuerza:int>, "aliados", "<raza>", "<saga_abrev>", "<formato>"]
        """
        self.name = name
        self.data_path = os.path.join(CARD_DATA_DIR, f"{name}.txt")
        self.image_path = None

        self.category = None    # "Aliados","Talismanes","Totems","Armas","Oros"
        self.cost = None        # int o None
        self.strength = None    # int o None
        self.race = None        # string o None
        self.saga = None        # nombre completo de saga
        self.format = None      # "pbx" o "reborn"
        self.tk_image = None    # PhotoImage cargada en load_image()

        self._load_data()

    def _load_data(self):
        if not os.path.isfile(self.data_path):
            raise FileNotFoundError(f"Archivo de datos no encontrado: {self.data_path}")
        with open(self.data_path, "r", encoding="utf-8") as f:
            arr = ast.literal_eval(f.read().strip())

        if not isinstance(arr, list):
            raise ValueError(f"Formato inválido en '{self.data_path}'")

        # Oro: ["oros", "<saga_abrev>", "<formato>"]
        if len(arr) == 3 and isinstance(arr[0], str) and arr[0].lower() == "oros":
            tipo = arr[0].lower()
            saga_ab = arr[1].lower()
            formato = arr[2].lower()

            if saga_ab not in SAGA_MAP:
                raise ValueError(f"Saga inválida en '{self.data_path}': '{saga_ab}'")
            if formato not in ("pbx", "reborn"):
                raise ValueError(f"Formato inválido en '{self.data_path}': '{formato}'")

            self.category = "Oros"
            self.cost = None
            self.strength = None
            self.race = None
            self.saga = SAGA_MAP[saga_ab]
            self.format = formato

        # Talismanes/Armas/Totems: [coste, "<tipo>", "<saga_abrev>", "<formato>"]
        elif len(arr) == 4 and isinstance(arr[0], int) and isinstance(arr[1], str):
            coste = arr[0]
            tipo = arr[1].lower()
            saga_ab = arr[2].lower()
            formato = arr[3].lower()

            if tipo not in ("talismanes", "armas", "totems"):
                raise ValueError(f"Tipo inválido en '{self.data_path}': '{tipo}'")
            if saga_ab not in SAGA_MAP:
                raise ValueError(f"Saga inválida en '{self.data_path}': '{saga_ab}'")
            if formato not in ("pbx", "reborn"):
                raise ValueError(f"Formato inválido en '{self.data_path}': '{formato}'")

            self.category = tipo.capitalize()  # "Talismanes","Armas","Totems"
            self.cost = coste
            self.strength = None
            self.race = None
            self.saga = SAGA_MAP[saga_ab]
            self.format = formato

        # Aliados: [coste, fuerza, "aliados", "<raza>", "<saga_abrev>", "<formato>"]
        elif len(arr) == 6 and isinstance(arr[0], int) and isinstance(arr[1], int) and isinstance(arr[2], str):
            coste = arr[0]
            fuerza = arr[1]
            tipo = arr[2].lower()
            raza = arr[3].lower()
            saga_ab = arr[4].lower()
            formato = arr[5].lower()

            if tipo != "aliados":
                raise ValueError(f"Tipo inválido en '{self.data_path}', se esperaba 'aliados' pero viene '{tipo}'")
            if raza not in (
                "dragon", "caballero", "faerie", "heroe",
                "olimpico", "titan", "defensor", "desafiante",
                "sombra", "faraon", "sacerdote", "eterno"
            ):
                raise ValueError(f"Raza inválida en '{self.data_path}': '{raza}'")
            if saga_ab not in SAGA_MAP:
                raise ValueError(f"Saga inválida en '{self.data_path}': '{saga_ab}'")
            if formato not in ("pbx", "reborn"):
                raise ValueError(f"Formato inválido en '{self.data_path}': '{formato}'")

            self.category = "Aliados"
            self.cost = coste
            self.strength = fuerza
            self.race = raza
            self.saga = SAGA_MAP[saga_ab]
            self.format = formato

        else:
            raise ValueError(
                f"Formato inválido en '{self.data_path}'.\n"
                "Revisa las reglas:\n"
                "  Oro → [\"oros\", saga_abrev, formato]\n"
                "  Talis/Armas/Totems → [coste, tipo, saga_abrev, formato]\n"
                "  Aliados → [coste, fuerza, \"aliados\", raza, saga_abrev, formato]\n"
            )

    def load_image(self):
        """
        Busca la imagen correspondiente (<name>.png o <name>.jpg)
        recorriendo recursivamente card_images/ (carpetas con _).
        Luego la redimensiona a ancho fijo (80 px) y guarda PhotoImage en self.tk_image.
        """
        found = False
        for root, dirs, files in os.walk(CARD_IMAGES_DIR):
            for fname in files:
                lower = fname.lower()
                if (lower.endswith(".png") or lower.endswith(".jpg")) and lower[:-4] == self.name.lower():
                    self.image_path = os.path.join(root, fname)
                    found = True
                    break
            if found:
                break

        if not found:
            raise FileNotFoundError(f"Imagen no encontrada para '{self.name}' en subcarpetas de {CARD_IMAGES_DIR}")

        pil_img = Image.open(self.image_path)
        DISPLAY_WIDTH = 80
        w, h = pil_img.size
        ratio = DISPLAY_WIDTH / w
        new_h = int(h * ratio)
        pil_resized = pil_img.resize((DISPLAY_WIDTH, new_h), Image.LANCZOS)
        self.tk_image = ImageTk.PhotoImage(pil_resized)

# =============================================================================
# 4) CLASE DECK: controla nombre_de_carta → cantidad, estado guardado
# =============================================================================
class Deck:
    def __init__(self):
        self.card_counts = Counter()
        self.is_saved = False  # para saber si el mazo fue guardado/importado sin cambios posteriores

    def total_cards(self):
        return sum(self.card_counts.values())

    def add_card(self, name, qty=1):
        self.card_counts[name] += qty
        self.is_saved = False

    def remove_card(self, name, qty=1):
        nuevo = self.card_counts[name] - qty
        if nuevo <= 0:
            if name in self.card_counts:
                del self.card_counts[name]
        else:
            self.card_counts[name] = nuevo
        self.is_saved = False

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

deck = Deck()

# =============================================================================
# 5) CARGAR TODOS LOS CARDS (sin imágenes aún)
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
# 7) DATOS PARA CURVA DE MANÁ: costo 0..10 → {categoría: cantidad}
# =============================================================================
cost_category_counts = {i: defaultdict(int) for i in range(0, 11)}

# =============================================================================
# 8) VARIABLES GLOBALES DE FILTROS
# =============================================================================
current_saga   = None  # p.ej. "Espada Sagrada", "Helenica", etc.
current_race   = None  # p.ej. "dragon", "caballero", etc.
current_format = None  # "pbx" o "reborn"

# =============================================================================
# 9) FUNCIONES AUXILIARES DE VALIDACIÓN Y FILTRADO
# =============================================================================
def is_card_valid_for_filters(name):
    """
    Verifica si la carta 'name' de ALL_CARDS cumple con:
    - current_saga   (comparar Card.saga)
    - current_race   (solo si category=="Aliados")
    - current_format (Card.format)
    """
    if current_saga is None or current_race is None or current_format is None:
        return False
    carta = ALL_CARDS[name]
    if carta.saga != current_saga:
        return False
    if carta.format != current_format:
        return False
    if carta.category == "Aliados":
        if carta.race != current_race:
            return False
    return True

def can_add_card(name, qty):
    """
    Verifica si se pueden añadir 'qty' copias de la carta 'name' bajo:
    1) Se deben haber seleccionado saga, raza y formato
    2) La carta debe ser válida para saga/raza/format
    3) No superar 50 cartas en total
    4) No superar el límite individual (3 por defecto o restricted_limits[name])
    """
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

# =============================================================================
# 10) ACTUALIZACIÓN DE INTERFAZ
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
    BAR_SPACING = 10
    BAR_MAX = 20

    BAR_COUNT = 6
    BAR_WIDTH = (CANVAS_W - 2*MARGIN_X - (BAR_COUNT - 1)*BAR_SPACING) / BAR_COUNT
    SEG_H = (CANVAS_H - 2*MARGIN_Y - 20) / BAR_MAX

    color_map = {
        "Aliados":    "#FFA500",
        "Talismanes": "#ADD8E6",
        "Totems":     "#006400",
        "Armas":      "#800080"
    }

    for cost_idx in range(1, 7):
        x0 = MARGIN_X + (cost_idx - 1) * (BAR_WIDTH + BAR_SPACING)
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
            font=("Helvetica", 9)
        )
        total = sum(cost_category_counts[cost_idx].values())
        curve_canvas.create_text(
            x0 + BAR_WIDTH / 2,
            MARGIN_Y,
            text=str(total),
            anchor="s",
            font=("Helvetica", 9, "bold")
        )

def card_sort_key(card_name):
    card = ALL_CARDS[card_name]
    cost_for_sort = card.cost if card.cost is not None else 999
    return (category_priority[card.category], cost_for_sort, card.name.lower())

image_id_to_name = {}

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

    if oros_counts:
        X = 0
        Y += (CARD_H + 20) if CARD_H else 140
        CUR_NAME = None
        CUR_CAT = None

        for name in sorted(oros_counts.keys()):
            cnt = oros_counts[name]
            card = ALL_CARDS[name]
            if name.lower() == "oro":
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

    n_oros = category_counts["Oros"]
    n_ali2 = sum(
        deck.card_counts[n] for n in deck.card_counts
        if ALL_CARDS[n].category == "Aliados" and ALL_CARDS[n].cost == 2
    )

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

    def hyper_at_least_one(total_type, draw_n, deck_size=50):
        if total_type == 0:
            return 0.0
        return 1 - (math.comb(deck_size - total_type, draw_n) / math.comb(deck_size, draw_n))

    total_cost_all = 0
    total_cost_count = 0
    for nm, cnt in deck.card_counts.items():
        c = ALL_CARDS[nm].cost
        if c is not None:
            total_cost_all += c * cnt
            total_cost_count += cnt
    avg_cost_deck = (total_cost_all / total_cost_count) if total_cost_count > 0 else 0.0
    avg_cost_text = f"Costo avg: {avg_cost_deck:.2f}"

    p8_o2   = hyper_at_least_k(n_oros, 8, 2)
    p8_o3   = hyper_at_least_k(n_oros, 8, 3)
    p8_ali2 = hyper_at_least_one(n_ali2, 8)

    p7_o2   = hyper_at_least_k(n_oros, 7, 2)
    p7_o3   = hyper_at_least_k(n_oros, 7, 3)
    p7_ali2 = hyper_at_least_one(n_ali2, 7)

    p6_o2   = hyper_at_least_k(n_oros, 6, 2)
    p6_o3   = hyper_at_least_k(n_oros, 6, 3)
    p6_ali2 = hyper_at_least_one(n_ali2, 6)

    def hyper_both(draw_n):
        prob = 0.0
        for i in range(2, draw_n + 1):
            if i > n_oros:
                continue
            for j in range(1, draw_n - i + 1):
                if j > n_ali2 or i + j > draw_n:
                    continue
                rest = draw_n - i - j
                if rest > (50 - n_oros - n_ali2):
                    continue
                prob += (
                    math.comb(n_oros, i)
                    * math.comb(n_ali2, j)
                    * math.comb(50 - n_oros - n_ali2, rest)
                    / math.comb(50, draw_n)
                )
        return prob

    p8_both = hyper_both(8)
    p7_both = hyper_both(7)
    p6_both = hyper_both(6)

    p8to7_o2   = p8_o2   + (1 - p8_o2)   * p7_o2
    p8to7_o3   = p8_o3   + (1 - p8_o3)   * p7_o3
    p8to7_ali2 = p8_ali2 + (1 - p8_ali2) * p7_ali2
    p8to7_both = p8_both + (1 - p8_both) * p7_both

    p8to7to6_o2   = p8_o2   + (1 - p8_o2)   * p7_o2   + (1 - p8_o2)   * (1 - p7_o2)   * p6_o2
    p8to7to6_o3   = p8_o3   + (1 - p8_o3)   * p7_o3   + (1 - p8_o3)   * (1 - p7_o3)   * p6_o3
    p8to7to6_ali2 = p8_ali2 + (1 - p8_ali2) * p7_ali2 + (1 - p8_ali2) * (1 - p7_ali2) * p6_ali2
    p8to7to6_both = p8_both + (1 - p8_both) * p7_both + (1 - p8_both) * (1 - p7_both) * p6_both

    lbl8_o2.config(text=f"P(≥2 Oros): {p8_o2*100:5.2f}%")
    lbl8_o3.config(text=f"P(≥3 Oros): {p8_o3*100:5.2f}%")
    lbl8_ali2.config(text=f"P(≥1 Aliado C2): {p8_ali2*100:5.2f}%")
    lbl8_avg.config(text=avg_cost_text)

    lbl7_o2.config(text=f"P(≥2 Oros): {p8to7_o2*100:5.2f}%")
    lbl7_o3.config(text=f"P(≥3 Oros): {p8to7to6_o3*100:5.2f}%")
    lbl7_ali2.config(text=f"P(≥1 Aliado C2): {p8to7_ali2*100:5.2f}%")
    lbl7_avg.config(text=avg_cost_text)

    lbl6_o2.config(text=f"P(≥2 Oros): {p8to7to6_o2*100:5.2f}%")
    lbl6_o3.config(text=f"P(≥3 Oros): {p8to7to6_o3*100:5.2f}%")
    lbl6_ali2.config(text=f"P(≥1 Aliado C2): {p8to7to6_ali2*100:5.2f}%")
    lbl6_avg.config(text=avg_cost_text)

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

        cond_oros = (oros_in_hand >= 2)
        cond_turn1 = has_1or2_ali

        if cond_oros:
            count_at_least_2_oros += 1
        if cond_turn1:
            count_turn1_play += 1
        if cond_oros and cond_turn1:
            count_great += 1

    lbl_sim_two_oros.config(text=f"Manos ≥2 Oros: {count_at_least_2_oros}")
    lbl_sim_turn1   .config(text=f"Manos Turno1 Jugada: {count_turn1_play}")
    lbl_sim_great   .config(text=f"Manos excelentes: {count_great}")

def save_deck_gui():
    fname = save_entry.get().strip()
    if not fname:
        messagebox.showerror("Error", "El nombre de archivo no puede estar vacío.")
        return
    decks_folder = DECKS_DIR
    if not os.path.isdir(decks_folder):
        os.makedirs(decks_folder)
    path = os.path.join(decks_folder, f"{fname}.txt")
    with open(path, "w", encoding="utf-8") as f:
        for line in deck.as_save_lines():
            f.write(line + "\n")
    messagebox.showinfo("Guardado", f"Baraja guardada en:\n{path}")
    deck.is_saved = True
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
        deck_var.set("Sin barajas")
    else:
        deck_var.set(files[-1])  # mostrar última por defecto
        for filename in files:
            menu.add_command(label=filename, command=lambda value=filename: deck_var.set(value))

    # Alineación a la derecha para mostrar fin del texto
    deck_option.config(justify="right", anchor="e")

def import_deck_dropdown():
    selected = deck_var.get()
    if not selected or selected in ("Sin barajas",):
        messagebox.showerror("Error", "No hay ninguna baraja seleccionada para importar.")
        return

    file_path = os.path.join(DECKS_DIR, selected)
    if not os.path.isfile(file_path):
        messagebox.showerror("Error", f"No se encontró el archivo de baraja:\n{file_path}")
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

            if not is_card_valid_for_filters(canonical):
                truncated = True
                continue

            max_allowed = restricted_limits.get(canonical, CARD_MAX_DEFAULT)
            cnt = min(cnt, max_allowed)
            capacity_left = 50 - total_added
            if capacity_left <= 0:
                truncated = True
                break
            actual_add = min(cnt, capacity_left)
            deck.card_counts[canonical] = actual_add
            total_added += actual_add
            if actual_add < cnt:
                truncated = True

    deck.is_saved = True
    update_category_summary()
    update_mana_curve()
    update_deck_display()
    update_consistency()

    if truncated:
        messagebox.showwarning("Importación parcial", "Algunas cartas no cumplieron filtros o límites; se omitieron o recortaron.")

# =============================================================================
# 11) CONFIGURACIÓN DE LA INTERFAZ (GUI)
# =============================================================================
root = tk.Tk()
root.title("Mitos y Leyendas: Constructor de Barajas")
BG_DEFAULT = "#d3d3d3"  # gris claro
root.configure(bg=BG_DEFAULT)
root.geometry("1200x970")

left_container = tk.Frame(root, bg=BG_DEFAULT)
divider        = tk.Frame(root, bg="black", width=4)
right_panel    = tk.Frame(root, bg=BG_DEFAULT)

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
# 12) Mostrar Baraja (Left Container) – REVISADO (ANCHO MAYOR PARA MÁS CARTAS)
# =============================================================================
deck_canvas = tk.Canvas(
    left_container,
    width=950,    # Antes era 700, ahora ampliamos a 1000px
    height=500,
    bg=BG_DEFAULT,
    bd=0,
    highlightthickness=0
)
deck_canvas.grid(row=0, column=0, padx=10, pady=10, sticky="nw")

# =============================================================================
# 13) Resumen de Categorías (Left Container)
# =============================================================================
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

# =============================================================================
# 14) Curva de Maná (Left Container)
#     ── Ahora en row=1, col=0 (sin columnspan), para dejar libre col=1 en esa fila
# =============================================================================
curve_canvas = tk.Canvas(
    left_container,
    width=400,
    height=200,
    bg="#e0e0e0",
    bd=0,
    highlightthickness=0
)
curve_canvas.grid(row=1, column=0, padx=10, pady=(0,10), sticky="nw")

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

    BAR_COUNT = 11  # de 0 a 10
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

        # Etiqueta costo abajo
        curve_canvas.create_text(
            x0 + BAR_WIDTH / 2,
            CANVAS_H - MARGIN_Y + 5,
            text=str(cost_idx),
            anchor="n",
            font=("Helvetica", 9, "bold")
        )
        # Total encima de la columna
        total = sum(cost_category_counts[cost_idx].values())
        curve_canvas.create_text(
            x0 + BAR_WIDTH / 2,
            MARGIN_Y,
            text=str(total),
            anchor="s",
            font=("Helvetica", 9, "bold")
        )

# =============================================================================
# 15) Menú Inferior (Left Container)
#     ── Ahora en row=2 (debajo de curva+estadísticas), con columnspan=2
# =============================================================================
menu_frame = tk.Frame(left_container, bg=BG_DEFAULT)
menu_frame.grid(row=2, column=0, columnspan=2, padx=10, pady=(10,20), sticky="w")

# --- Saga ---
tk.Label(menu_frame, text="Saga:", font=("Helvetica", 10, "bold"), bg=BG_DEFAULT).grid(row=0, column=0, sticky="e")
saga_var = tk.StringVar(value="— Seleccione —")
saga_menu = tk.OptionMenu(
    menu_frame, saga_var,
    "Espada Sagrada", "Helenica", "Hijos de Daana", "Dominios de Ra"
)
saga_menu.config(width=18, font=("Helvetica", 10))
saga_menu.grid(row=0, column=1, padx=(5,20))

# --- Raza ---
tk.Label(menu_frame, text="Raza:", font=("Helvetica", 10, "bold"), bg=BG_DEFAULT).grid(row=0, column=2, sticky="e")
race_var = tk.StringVar(value="— Seleccione —")
race_menu = tk.OptionMenu(menu_frame, race_var, "")  # se poblará luego
race_menu.config(width=15, font=("Helvetica", 10))
race_menu.grid(row=0, column=3, padx=(5,20))

# --- Formato ---
tk.Label(menu_frame, text="Formato:", font=("Helvetica", 10, "bold"), bg=BG_DEFAULT).grid(row=0, column=4, sticky="e")
format_var = tk.StringVar(value="— Seleccione —")
format_menu = tk.OptionMenu(menu_frame, format_var, "Pbx", "Reborn")
format_menu.config(width=10, font=("Helvetica", 10))
format_menu.grid(row=0, column=5, padx=(5,20))

# --- Campo “Carta” con Autocompletado en Línea ---
tk.Label(menu_frame, text="Carta:", font=("Helvetica", 10, "bold"), bg=BG_DEFAULT).grid(row=1, column=0, sticky="e")
card_entry = tk.Entry(menu_frame, width=30, font=("Helvetica", 10))
card_entry.grid(row=1, column=1, columnspan=3, padx=(5,20))

def autocomplete_card(event):
    key = event.keysym
    if key in ("BackSpace", "Delete", "Return"):
        return
    typed = card_entry.get().strip().lower()
    if not typed:
        return
    for nm in sorted(ALL_CARDS.keys()):
        if not is_card_valid_for_filters(nm):
            continue
        if nm.startswith(typed):
            display = nm.replace("-", " ").capitalize()
            card_entry.delete(0, tk.END)
            card_entry.insert(0, display)
            card_entry.select_range(len(typed), tk.END)
            card_entry.icursor(len(typed))
            break

card_entry.bind("<KeyRelease>", autocomplete_card)
def select_all_on_click(event):
    event.widget.select_range(0, tk.END)
card_entry.bind("<Button-1>", select_all_on_click)

# --- Cantidad ---
tk.Label(menu_frame, text="Cantidad:", font=("Helvetica", 10, "bold"), bg=BG_DEFAULT).grid(row=1, column=4, sticky="e")
qty_var = tk.StringVar(value="1")
qty_menu = tk.OptionMenu(menu_frame, qty_var, "1", "2", "3")
qty_menu.config(width=5, font=("Helvetica", 10))
qty_menu.grid(row=1, column=5, padx=(5,20))

# --- Botones Añadir / Eliminar ---
add_button = tk.Button(menu_frame, text="Añadir carta", font=("Helvetica", 10, "bold"), width=12,
                       command=lambda: add_card_gui())
add_button.grid(row=1, column=6, padx=(5,20))
remove_button = tk.Button(menu_frame, text="Eliminar carta", font=("Helvetica", 10, "bold"), width=12,
                          command=lambda: remove_card_gui())
remove_button.grid(row=1, column=7, padx=(5,20))

# --- Guardar / Importar / Salir ---
tk.Label(menu_frame, text="Guardar como:", font=("Helvetica", 10, "bold"), bg=BG_DEFAULT).grid(row=2, column=0, sticky="e", pady=(10,0))
save_entry = tk.Entry(menu_frame, width=20, font=("Helvetica", 10))
save_entry.grid(row=2, column=1, padx=(5,20), pady=(10,0))
save_button = tk.Button(menu_frame, text="Guardar baraja", font=("Helvetica", 10, "bold"), width=12, command=save_deck_gui)
save_button.grid(row=2, column=2, padx=(5,20), pady=(10,0))

tk.Label(menu_frame, text="Importar baraja:", font=("Helvetica", 10, "bold"), bg=BG_DEFAULT).grid(row=2, column=3, sticky="e", pady=(10,0))
deck_var = tk.StringVar()
deck_var.set("Sin barajas")
deck_option = tk.OptionMenu(menu_frame, deck_var, *get_deck_files())
deck_option.config(width=20, justify="right", anchor="e", font=("Helvetica", 10))
deck_option.grid(row=2, column=4, padx=(5,20), pady=(10,0))
refresh_deck_dropdown()
import_button = tk.Button(menu_frame, text="Importar baraja", font=("Helvetica", 10, "bold"), width=12,
                          command=import_deck_dropdown)
import_button.grid(row=2, column=5, padx=(5,20), pady=(10,0))

quit_button = tk.Button(menu_frame, text="Salir", font=("Helvetica", 10, "bold"), width=10, command=root.destroy)
quit_button.grid(row=2, column=6, padx=(5,0), pady=(10,0))

# =============================================================================
# 16) Sección de Consistencia (Panel Derecho)  ← ESTE ES EL BLOQUE NUEVO
# =============================================================================
consistency_frame = tk.LabelFrame(
    right_panel,
    text="Consistencia",
    bg=BG_DEFAULT,
    font=("Helvetica", 10, "bold"),
    padx=5,
    pady=5
)
consistency_frame.grid(row=0, column=0, padx=10, pady=(10,5), sticky="nwe")

# Columnas para “Robar 8”, “8 → 7 Mulligan” y “8 → 7 → 6 Mulligan”
col8 = tk.Frame(consistency_frame, bg=BG_DEFAULT)
col7 = tk.Frame(consistency_frame, bg=BG_DEFAULT)
col6 = tk.Frame(consistency_frame, bg=BG_DEFAULT)

col8.grid(row=0, column=0, padx=(0,10), sticky="nw")
col7.grid(row=0, column=1, padx=(0,10), sticky="nw")
col6.grid(row=0, column=2, sticky="nw")

LABEL_FONT = ("Helvetica", 9)

# “Robar 8 cartas”
tk.Label(col8, text="Robar 8 cartas", font=("Helvetica", 10, "bold"), bg=BG_DEFAULT).grid(row=0, column=0, sticky="w", pady=(0,4))
lbl8_o2   = tk.Label(col8, text="P(≥2 Oros): 0%",     font=LABEL_FONT, bg=BG_DEFAULT)
lbl8_o3   = tk.Label(col8, text="P(≥3 Oros): 0%",     font=LABEL_FONT, bg=BG_DEFAULT)
lbl8_ali2 = tk.Label(col8, text="P(≥1 Aliado C2): 0%", font=LABEL_FONT, bg=BG_DEFAULT)
lbl8_avg  = tk.Label(col8, text="Costo avg: 0.00",    font=LABEL_FONT, bg=BG_DEFAULT)
lbl8_o2.grid(row=1, column=0, sticky="w")
lbl8_o3.grid(row=2, column=0, sticky="w")
lbl8_ali2.grid(row=3, column=0, sticky="w")
lbl8_avg.grid(row=4, column=0, sticky="w", pady=(0,2))

# “8 → 7 Mulligan”
tk.Label(col7, text="8 → 7 Mulligan", font=("Helvetica", 10, "bold"), bg=BG_DEFAULT).grid(row=0, column=0, sticky="w", pady=(0,4))
lbl7_o2   = tk.Label(col7, text="P(≥2 Oros): 0%",     font=LABEL_FONT, bg=BG_DEFAULT)
lbl7_o3   = tk.Label(col7, text="P(≥3 Oros): 0%",     font=LABEL_FONT, bg=BG_DEFAULT)
lbl7_ali2 = tk.Label(col7, text="P(≥1 Aliado C2): 0%", font=LABEL_FONT, bg=BG_DEFAULT)
lbl7_avg  = tk.Label(col7, text="Costo avg: 0.00",    font=LABEL_FONT, bg=BG_DEFAULT)
lbl7_o2.grid(row=1, column=0, sticky="w")
lbl7_o3.grid(row=2, column=0, sticky="w")
lbl7_ali2.grid(row=3, column=0, sticky="w")
lbl7_avg.grid(row=4, column=0, sticky="w", pady=(0,2))

# “8 → 7 → 6 Mulligan”
tk.Label(col6, text="8 → 7 → 6 Mulligan", font=("Helvetica", 10, "bold"), bg=BG_DEFAULT).grid(row=0, column=0, sticky="w", pady=(0,4))
lbl6_o2   = tk.Label(col6, text="P(≥2 Oros): 0%",     font=LABEL_FONT, bg=BG_DEFAULT)
lbl6_o3   = tk.Label(col6, text="P(≥3 Oros): 0%",     font=LABEL_FONT, bg=BG_DEFAULT)
lbl6_ali2 = tk.Label(col6, text="P(≥1 Aliado C2): 0%", font=LABEL_FONT, bg=BG_DEFAULT)
lbl6_avg  = tk.Label(col6, text="Costo avg: 0.00",    font=LABEL_FONT, bg=BG_DEFAULT)
lbl6_o2.grid(row=1, column=0, sticky="w")
lbl6_o3.grid(row=2, column=0, sticky="w")
lbl6_ali2.grid(row=3, column=0, sticky="w")
lbl6_avg.grid(row=4, column=0, sticky="w", pady=(0,2))

# =============================================================================
# 17) ESTADÍSTICAS ADICIONALES (Left Container)
#     ── Ahora justo debajo de “Resumen de Categorías” (row=1, column=1)
# =============================================================================
stats_frame = tk.LabelFrame(
    left_container,
    text="Estadísticas Adicionales",
    bg=BG_DEFAULT,
    font=("Helvetica", 10, "bold"),
    padx=5,
    pady=5
)
stats_frame.grid(row=1, column=1, padx=10, pady=(0,10), sticky="nw")

lbl_avg_cost = tk.Label(
    stats_frame,
    text="Costo promedio (baraja): 0.00",
    font=("Helvetica", 10),
    bg=BG_DEFAULT
)
lbl_avg_str = tk.Label(
    stats_frame,
    text="Fuerza aliados promedio: 0.00",
    font=("Helvetica", 10),
    bg=BG_DEFAULT
)
lbl_avg_cost.grid(row=0, column=0, sticky="w", pady=(0,2))
lbl_avg_str.grid(row=1, column=0, sticky="w")

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
# 18) Repartir Mano Aleatoria (Panel Derecho) – ajuste de altura y botones más anchos
# =============================================================================
hand_frame = tk.LabelFrame(
    right_panel,
    text="Repartir Mano Aleatoria",
    bg=BG_DEFAULT,
    font=("Helvetica", 10, "bold"),
    padx=5,
    pady=5
)
hand_frame.grid(row=1, column=0, padx=10, pady=(5,10), sticky="nwe")

# Canvas agrandado para que quepan 8 cartas en 2 filas de 4, sin recorte
deal_canvas = tk.Canvas(
    hand_frame,
    width=300,
    height=200,        # <─ antes era 180; lo subimos a 200 para que no se recorten
    bg=BG_DEFAULT,
    bd=0,
    highlightthickness=0
)
deal_canvas.grid(row=0, column=0, rowspan=2, padx=(5,5), pady=(5,5), sticky="nw")

# Texto de conteos (Aliados / Oros / Soporte)
info_text = tk.Label(
    hand_frame,
    text="Aliados: 0\nOros: 0\nSoporte: 0",
    justify="left",
    bg=BG_DEFAULT,
    font=("Helvetica", 10, "bold")
)
info_text.grid(row=0, column=1, padx=(10,10), pady=(5,5), sticky="nw")

# Panel para simulación de 1000 manos
sim_frame = tk.Frame(hand_frame, bg=BG_DEFAULT)
sim_frame.grid(row=1, column=1, padx=(10,10), pady=(5,5), sticky="nw")

thousand_button = tk.Button(
    sim_frame,
    text="1000 Manos",
    width=10,
    font=("Helvetica", 10, "bold"),
    command=lambda: simulate_1000_hands()
)
thousand_button.grid(row=0, column=0, padx=(0,5))

lbl_sim_two_oros = tk.Label(sim_frame, text="Manos ≥2 Oros: 0", bg=BG_DEFAULT, font=("Helvetica", 10))
lbl_sim_turn1    = tk.Label(sim_frame, text="Manos Turno1 Jugada: 0", bg=BG_DEFAULT, font=("Helvetica", 10))
lbl_sim_great    = tk.Label(sim_frame, text="Manos excelentes: 0", bg=BG_DEFAULT, font=("Helvetica", 10))

lbl_sim_two_oros.grid(row=1, column=0, sticky="w")
lbl_sim_turn1   .grid(row=2, column=0, sticky="w")
lbl_sim_great   .grid(row=3, column=0, sticky="w")

# Botones “Repartir mano” / “Mulligan” con indicadores
hand_button_frame = tk.Frame(hand_frame, bg=BG_DEFAULT)
hand_button_frame.grid(row=2, column=0, columnspan=2, pady=(5,5), sticky="w")

lbl_two_oros = tk.Label(
    hand_button_frame,
    text="2 Oros",
    font=("Helvetica", 10, "bold"),
    fg="black",
    bg=BG_DEFAULT
)
lbl_two_oros.grid(row=0, column=0, padx=(0,20))

deal_button = tk.Button(
    hand_button_frame,
    text="Repartir mano",
    width=13,                     # <─ antes width era 10; lo subimos a 13 para que quepa el texto
    font=("Helvetica", 10, "bold"),
    command=lambda: deal_hand()
)
deal_button.grid(row=0, column=1, padx=(0,10))

mulligan_button = tk.Button(
    hand_button_frame,
    text="Mulligan",
    width=10,
    font=("Helvetica", 10, "bold"),
    command=lambda: mulligan()
)
mulligan_button.grid(row=0, column=2, padx=(0,20))

lbl_turn1 = tk.Label(
    hand_button_frame,
    text="Turno 1 jugada",
    font=("Helvetica", 10, "bold"),
    fg="black",
    bg=BG_DEFAULT
)
lbl_turn1.grid(row=0, column=3, padx=(0,0))


# Funciones relacionadas al Dealer de Manos:

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
    """
    Dibuja hasta 8 cartas en 2 filas de 4, con tamaño uniforme para no recortar.
    También actualiza contadores y colores en info_text.
    """
    deal_canvas.delete("all")
    cols = 4
    spacing = 8
    DISPLAY_W = 60

    count_aliados = 0
    count_oros = 0
    count_soporte = 0

    # 1) Recolectar imágenes redimensionadas
    temp_imgs = []
    for name in hand_list:
        card = ALL_CARDS.get(name)
        if not card:
            continue
        try:
            if card.tk_image is None:
                card.load_image()
        except FileNotFoundError:
            continue

        pil_img = Image.open(card.image_path)
        w, h = pil_img.size
        ratio = DISPLAY_W / w
        new_h = int(h * ratio)
        resized = pil_img.resize((DISPLAY_W, new_h), Image.LANCZOS)
        temp_imgs.append((name, resized))

    # 2) Fijar siempre 2 filas (aunque falten cartas)
    row_heights = [0, 0]

    # 3) Calcular altura máxima de cada fila
    for idx, (_, pil_img) in enumerate(temp_imgs):
        row_idx = idx // cols  # 0 ó 1
        h = pil_img.height
        if h > row_heights[row_idx]:
            row_heights[row_idx] = h

    # 4) Dibujar cada imagen en su posición
    for idx, (name, pil_img) in enumerate(temp_imgs):
        card = ALL_CARDS[name]
        tkimg = ImageTk.PhotoImage(pil_img)
        card.image_temp = tkimg  # mantener referencia para no perder la imagen

        row = idx // cols   # 0 ó 1
        col = idx % cols    # 0 a 3
        x = col * (DISPLAY_W + spacing)
        if row == 0:
            y = 0
        else:
            y = row_heights[0] + spacing

        deal_canvas.create_image(x, y, image=tkimg, anchor="nw")

        # Contar categorías para info_text
        if card.category == "Aliados":
            count_aliados += 1
        elif card.category == "Oros":
            count_oros += 1
        elif card.category in ("Armas", "Totems", "Talismanes"):
            count_soporte += 1

    info_text.config(
        text=f"Aliados: {count_aliados}\nOros: {count_oros}\nSoporte: {count_soporte}"
    )

    # Color “2 Oros”
    lbl_two_oros.config(fg="green" if count_oros >= 2 else "red")

    # Color “Turno 1 jugada”
    has_1or2_ali = any(
        ALL_CARDS[nm].category == "Aliados" and ALL_CARDS[nm].cost in (1, 2)
        for nm in hand_list
    )
    lbl_turn1.config(fg="green" if has_1or2_ali else "red")

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

        cond_oros = (oros_in_hand >= 2)
        cond_turn1 = has_1or2_ali

        if cond_oros:
            count_at_least_2_oros += 1
        if cond_turn1:
            count_turn1_play += 1
        if cond_oros and cond_turn1:
            count_great += 1

    lbl_sim_two_oros.config(text=f"Manos ≥2 Oros: {count_at_least_2_oros}")
    lbl_sim_turn1   .config(text=f"Manos Turno1 Jugada: {count_turn1_play}")
    lbl_sim_great   .config(text=f"Manos excelentes: {count_great}")

# =============================================================================
# 19) FUNCIONES DE AYUDA (highlight)
# =============================================================================
def highlight_if_unselected(var, menubutton):
    if var.get() == "— Seleccione —":
        menubutton.config(highlightthickness=2, highlightbackground="red")
    else:
        menubutton.config(highlightthickness=0)

# =============================================================================
# 20) CALLBACKS PARA DROPDOWNS (Saga, Raza, Formato) – SE AGREGAN TODOS LOS helpers
# =============================================================================

def set_background_color_for_saga(saga):
    """
    Asigna colores según la saga seleccionada:
    - Hijos de Daana → #37eca5
    - Helenica       → #c5aa87
    - Espada Sagrada → #acbcf7
    - Dominios de Ra → #eccc37
    """
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

    # Cambiamos background de todos los contenedores principales
    root.configure(bg=color)
    left_container.configure(bg=color)
    right_panel.configure(bg=color)
    summary_frame.configure(bg=color)
    curve_canvas.configure(bg=color)
    menu_frame.configure(bg=color)
    card_entry.configure(bg="white")

    race_menu.configure(bg=color)
    saga_menu.configure(bg=color)
    format_menu.configure(bg=color)
    qty_menu.configure(bg=color)
    deck_canvas.configure(bg=color)
    deck_option.configure(bg=color)
    hand_frame.configure(bg=color)
    sim_frame.configure(bg=color)
    consistency_frame.configure(bg=color)
    stats_frame.configure(bg=color)


def refresh_race_options(selected_saga):
    """
    Pobla el menú de 'Raza' según la saga seleccionada.
    Debe llamarse desde on_saga_change.
    """
    menu = race_menu["menu"]
    menu.delete(0, "end")
    race_var.set("— Seleccione —")
    if selected_saga in RACES_BY_SAGA:
        for raza in RACES_BY_SAGA[selected_saga]:
            display = raza.title()
            menu.add_command(
                label=display,
                command=lambda r=raza: race_var.set(r.title())
            )


def refresh_card_options():
    """
    Placeholder para futuros filtros dinámicos en 'Carta'.
    Por ahora no hace nada más que existir (evita NameError).
    """
    return


def on_saga_change(*args):
    global current_saga
    sel = saga_var.get()
    # Borrar texto de “Carta” para forzar a tipear de nuevo
    card_entry.delete(0, tk.END)

    if sel == "— Seleccione —":
        current_saga = None
    else:
        invalidas = [n for n in deck.card_counts if ALL_CARDS[n].saga != sel]
        if invalidas and deck.total_cards() > 0:
            if deck.is_saved:
                resp = messagebox.askyesno(
                    "Cartas inválidas",
                    "Tu baraja contiene cartas que no pertenecen a la saga seleccionada.\n"
                    "¿Deseas guardar antes de vaciarla?"
                )
                if resp:
                    save_deck_gui()
            deck.card_counts.clear()
            deck.is_saved = False

        current_saga = sel
        set_background_color_for_saga(sel)
        refresh_race_options(sel)
        refresh_card_options()

    update_category_summary()
    update_mana_curve()
    update_deck_display()
    update_consistency()
    update_stats()
    highlight_if_unselected(saga_var, saga_menu)
    highlight_if_unselected(race_var, race_menu)
    highlight_if_unselected(format_var, format_menu)


def on_race_change(*args):
    global current_race
    sel = race_var.get().lower()
    # Borrar texto de “Carta” para forzar a tipear de nuevo
    card_entry.delete(0, tk.END)

    if sel == "— seleccione —":
        current_race = None
    else:
        invalidas = [
            n for n in deck.card_counts
            if ALL_CARDS[n].category == "Aliados" and ALL_CARDS[n].race != sel
        ]
        if invalidas and deck.total_cards() > 0:
            if deck.is_saved:
                resp = messagebox.askyesno(
                    "Cartas inválidas",
                    "Tu baraja contiene Aliados de otra raza.\n"
                    "¿Deseas guardar antes de vaciarla?"
                )
                if resp:
                    save_deck_gui()
            deck.card_counts.clear()
            deck.is_saved = False

        current_race = sel
        refresh_card_options()

    update_category_summary()
    update_mana_curve()
    update_deck_display()
    update_consistency()
    update_stats()
    highlight_if_unselected(race_var, race_menu)


def on_format_change(*args):
    global current_format
    sel = format_var.get()
    # Borrar texto de “Carta” para forzar a tipear de nuevo
    card_entry.delete(0, tk.END)

    if sel == "— Seleccione —":
        current_format = None
    else:
        lowercase = sel.lower()
        invalidas = [n for n in deck.card_counts if ALL_CARDS[n].format != lowercase]
        if invalidas and deck.total_cards() > 0:
            if deck.is_saved:
                resp = messagebox.askyesno(
                    "Cartas inválidas",
                    "Tu baraja contiene cartas de otro formato.\n"
                    "¿Deseas guardar antes de vaciarla?"
                )
                if resp:
                    save_deck_gui()
            deck.card_counts.clear()
            deck.is_saved = False

        current_format = lowercase
        refresh_card_options()

    update_category_summary()
    update_mana_curve()
    update_deck_display()
    update_consistency()
    update_stats()
    highlight_if_unselected(format_var, format_menu)


# Registrar los trazos
saga_var.trace("w", on_saga_change)
race_var.trace("w", on_race_change)
format_var.trace("w", on_format_change)

# =============================================================================
# 21) FUNCIONES de BOTONES DEL MENÚ (Añadir, Eliminar, Guardar, Importar, Salir)
# =============================================================================
def highlight_if_unselected(var, widget):
    """
    Si 'var' está en su valor por defecto (“— Seleccione —”), dibuja un borde rojo.
    """
    if var.get() == "— Seleccione —":
        widget.config(highlightthickness=2, highlightbackground="red")
    else:
        widget.config(highlightthickness=0)

def add_card_gui():
    """
    Toma el texto de card_entry, lo formatea (minúsculas, guiones) y
    agrega la cantidad indicada (qty_var). Muestra warning si no existe o está inválido.
    """
    display_name = card_entry.get().strip()
    if not display_name:
        messagebox.showwarning("Error", "Debes ingresar un nombre de carta.")
        return

    # Convertir a nombre interno: minúscula + guiones
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
    """
    Similar a add_card_gui, pero quita cantidad.
    """
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

def save_deck_gui():
    """
    Genera el .txt con el nombre de save_entry, en carpeta 'decks/'.
    """
    fname = save_entry.get().strip()
    if not fname:
        messagebox.showwarning("Error", "Ingresa un nombre de archivo válido.")
        return
    if not os.path.exists("decks"):
        os.makedirs("decks")
    path = os.path.join("decks", f"{fname}.txt")
    lines = deck.as_save_lines()
    with open(path, "w", encoding="utf-8") as f:
        for line in lines:
            f.write(line + "\n")
    messagebox.showinfo("Guardado", f"Baraja guardada en:\n{path}")
    deck.is_saved = True
    refresh_deck_dropdown()

def import_deck_dropdown():
    """
    Importa la baraja seleccionada de deck_var (OptionMenu).
    """
    choice = deck_var.get()
    if choice == "Sin barajas":
        messagebox.showwarning("Error", "No hay barajas para importar.")
        return
    # El nombre mostrado en deck_var es “archivo.txt”
    path = os.path.join("decks", choice)
    if not os.path.isfile(path):
        messagebox.showwarning("Error", f"No se encontró {path}")
        return

    # Limpiar baraja actual
    deck.card_counts.clear()
    deck.is_saved = True
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split("x", 1)
            qty = int(parts[0])
            name = parts[1]
            deck.card_counts[name] = qty

    update_category_summary()
    update_mana_curve()
    update_deck_display()
    update_consistency()
    update_stats()

def refresh_deck_dropdown():
    """
    Vuelve a leer todos los .txt de 'decks/' y popula deck_option.
    """
    menu = deck_option["menu"]
    menu.delete(0, "end")
    files = [f for f in os.listdir("decks") if f.lower().endswith(".txt")]
    if not files:
        deck_var.set("Sin barajas")
        menu.add_command(label="Sin barajas", command=lambda: deck_var.set("Sin barajas"))
        return
    for fn in files:
        menu.add_command(label=fn, command=lambda f=fn: deck_var.set(f))

    deck_var.set(files[0])

# Botón “Salir”
def exit_app():
    root.destroy()
# Ya tienes quit_button.bind(root.destroy) en la UI


# =============================================================================
# 22) EVENTOS de CLIC SOBRE CARTA (Left Container)
#    - Clic izquierdo quita 1 copia
#    - Clic derecho agrega 1 copia
# =============================================================================
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
        update_stats()

def add_card_by_right_click(event):
    clicked = deck_canvas.find_withtag("current")
    if not clicked:
        return
    item_id = clicked[0]
    if item_id not in image_id_to_name:
        return
    name = image_id_to_name[item_id]
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

# Binds:
deck_canvas.bind("<Button-1>", remove_card_by_click)       # clic izq
deck_canvas.bind("<Button-3>", add_card_by_right_click)  # clic der

# =============================================================================
# 23) CARGAR Imágenes & DIBUJO INICIAL – load_image() con .png/.jpg/.jpeg y OROS al final
# =============================================================================
class Card:
    def __init__(self, name):
        self.name = name
        self.data_path = os.path.join(CARD_DATA_DIR, f"{name}.txt")
        self.image_path = None

        self.category = None
        self.cost = None
        self.strength = None
        self.race = None
        self.saga = None
        self.format = None
        self.tk_image = None

        self._load_data()

    def _load_data(self):
        if not os.path.isfile(self.data_path):
            raise FileNotFoundError(f"Archivo de datos no encontrado: {self.data_path}")
        with open(self.data_path, "r", encoding="utf-8") as f:
            arr = ast.literal_eval(f.read().strip())

        if len(arr) == 3 and isinstance(arr[0], str) and arr[0].lower() == "oros":
            tipo = arr[0].lower()
            saga_ab = arr[1].lower()
            formato = arr[2].lower()
            if saga_ab not in SAGA_MAP:
                raise ValueError(f"Saga inválida en '{self.data_path}': '{saga_ab}'")
            if formato not in ("pbx", "reborn"):
                raise ValueError(f"Formato inválido en '{self.data_path}': '{formato}'")

            self.category = "Oros"
            self.cost = None
            self.strength = None
            self.race = None
            self.saga = SAGA_MAP[saga_ab]
            self.format = formato

        elif len(arr) == 4 and isinstance(arr[0], int) and isinstance(arr[1], str):
            coste = arr[0]
            tipo = arr[1].lower()
            saga_ab = arr[2].lower()
            formato = arr[3].lower()
            if tipo not in ("talismanes", "armas", "totems"):
                raise ValueError(f"Tipo inválido en '{self.data_path}': '{tipo}'")
            if saga_ab not in SAGA_MAP:
                raise ValueError(f"Saga inválida en '{self.data_path}': '{saga_ab}'")
            if formato not in ("pbx", "reborn"):
                raise ValueError(f"Formato inválido en '{self.data_path}': '{formato}'")

            self.category = tipo.capitalize()
            self.cost = coste
            self.strength = None
            self.race = None
            self.saga = SAGA_MAP[saga_ab]
            self.format = formato

        elif len(arr) == 6 and isinstance(arr[0], int) and isinstance(arr[1], int) and isinstance(arr[2], str):
            coste = arr[0]
            fuerza = arr[1]
            tipo = arr[2].lower()
            raza = arr[3].lower()
            saga_ab = arr[4].lower()
            formato = arr[5].lower()
            if tipo != "aliados":
                raise ValueError(f"Tipo inválido en '{self.data_path}', se esperaba 'aliados' pero viene '{tipo}'")
            if raza not in (
                "dragon", "caballero", "faerie", "heroe",
                "olimpico", "titan", "defensor", "desafiante",
                "sombra", "faraon", "sacerdote", "eterno"
            ):
                raise ValueError(f"Raza inválida en '{self.data_path}': '{raza}'")
            if saga_ab not in SAGA_MAP:
                raise ValueError(f"Saga inválida en '{self.data_path}': '{saga_ab}'")
            if formato not in ("pbx", "reborn"):
                raise ValueError(f"Formato inválido en '{self.data_path}': '{formato}'")

            self.category = "Aliados"
            self.cost = coste
            self.strength = fuerza
            self.race = raza
            self.saga = SAGA_MAP[saga_ab]
            self.format = formato

        else:
            raise ValueError(
                f"Formato inválido en '{self.data_path}'.\n"
                "Revisa las reglas:\n"
                "  Oro → [\"oros\", saga_abrev, formato]\n"
                "  Talis/Armas/Totems → [coste, tipo, saga_abrev, formato]\n"
                "  Aliados → [coste, fuerza, \"aliados\", raza, saga_abrev, formato]\n"
            )

    def load_image(self):
        found = False
        for root_dir, dirs, files in os.walk(CARD_IMAGES_DIR):
            for fname in files:
                lower = fname.lower()
                if (lower.endswith(".png") or lower.endswith(".jpg") or lower.endswith(".jpeg")) and lower.split(".")[0] == self.name.lower():
                    self.image_path = os.path.join(root_dir, fname)
                    found = True
                    break
            if found:
                break

        if not found:
            raise FileNotFoundError(f"Imagen no encontrada para '{self.name}' en {CARD_IMAGES_DIR}")

        pil_img = Image.open(self.image_path)
        DISPLAY_WIDTH = 80
        w, h = pil_img.size
        ratio = DISPLAY_WIDTH / w
        new_h = int(h * ratio)
        pil_resized = pil_img.resize((DISPLAY_WIDTH, new_h), Image.LANCZOS)
        self.tk_image = ImageTk.PhotoImage(pil_resized)

# =============================================================================
# 24) update_deck_display() – FORZAR QUE "Oros" ESTÉN EN LA ÚLTIMA FILA + EJECUCIÓN FINAL
# =============================================================================
def update_deck_display():
    deck_canvas.delete("all")
    image_id_to_name.clear()

    flat_list = deck.list_all_copies()
    flat_list.sort(key=card_sort_key)

    x0 = 0
    y0 = 0
    max_h = 0
    canvas_width = int(deck_canvas.cget("width"))
    saw_oros = False

    for nm in flat_list:
        if nm not in ALL_CARDS:
            continue
        card = ALL_CARDS[nm]

        # Al encontrar la primera carta "Oros", forzamos salto de línea
        if card.category == "Oros" and not saw_oros:
            saw_oros = True
            x0 = 0
            y0 += max_h + 10
            max_h = 0

        # Asegurarnos de que la imagen esté cargada
        if card.tk_image is None:
            try:
                card.load_image()
            except FileNotFoundError:
                continue

        w = card.tk_image.width()
        h = card.tk_image.height()
        img_id = deck_canvas.create_image(x0, y0, image=card.tk_image, anchor="nw")
        image_id_to_name[img_id] = nm

        if h > max_h:
            max_h = h
        x0 += 45

        # Mientras no hayamos visto "Oros", si excede ancho, saltar fila
        if not saw_oros and (x0 + w > canvas_width):
            x0 = 0
            y0 += max_h + 10
            max_h = 0

    update_category_summary()

# Al final del archivo main.py, justo antes de terminar:
update_deck_display()
root.mainloop()
