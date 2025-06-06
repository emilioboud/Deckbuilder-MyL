# deck.py

import os
from collections import Counter, defaultdict

# Importamos desde cards.py las clases y constantes necesarias
from cards import Card, CARD_DATA_DIR, load_restricted_limits, SAGA_MAP, RACES_BY_SAGA

# =============================================================================
# 1) CARGAR TODA LAS CARTAS
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
        print(f"Advertencia: no se pudo cargar datos de '{canonical}': {e}")

# =============================================================================
# 2) CARGAR LÍMITES RESTRINGIDOS
# =============================================================================
restricted_limits = load_restricted_limits()
CARD_MAX_DEFAULT = 3

# =============================================================================
# 3) CLASE Deck: maneja contenido del mazo y serialización
# =============================================================================
class Deck:
    def __init__(self):
        self.card_counts = Counter()
        self.is_saved = False

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
# 4) FUNCIONES DE FILTRADO Y VALIDACIÓN DE CARTAS
# =============================================================================
current_saga = None
current_race = None
current_format = None

def is_card_valid_for_filters(name):
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
    if current_saga is None or current_race is None or current_format is None:
        return False, "Debes elegir Saga, Raza y Formato primero."
    carta = ALL_CARDS.get(name)
    if carta is None or not is_card_valid_for_filters(name):
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
# 5) FUNCIONES AUXILIARES PARA IMPORTAR/EXPORTAR DECK
# =============================================================================
DECKS_DIR = os.path.join(os.getcwd(), "decks")

def get_deck_files():
    if not os.path.isdir(DECKS_DIR):
        os.makedirs(DECKS_DIR)
    files = []
    for f in os.listdir(DECKS_DIR):
        if f.lower().endswith(".txt"):
            files.append(f)
    return sorted(files)

def load_deck_from_file(filepath, saga, race, fmt):
    """
    Carga un mazo desde el archivo 'filepath' (decks/<nombre>.txt),
    aplicando los filtros de 'saga', 'race' y 'fmt' (formato).
    Devuelve un Counter con los nombres canonical y cantidades válidas.
    """
    nuevo_counts = Counter()
    total_added = 0

    with open(filepath, "r", encoding="utf-8") as f:
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

            # Aplicar filtros con los parámetros recibidos:
            card = ALL_CARDS.get(canonical)
            if card is None:
                continue
            if card.saga != saga or card.format != fmt:
                continue
            if card.category == "Aliados" and card.race != race:
                continue

            # Límite por carta
            max_allowed = restricted_limits.get(canonical, CARD_MAX_DEFAULT)
            cantidad = min(cnt, max_allowed)

            # Capacidad restante del mazo (50 cartas)
            capacity_left = 50 - total_added
            if capacity_left <= 0:
                break
            actual_add = min(cantidad, capacity_left)
            if actual_add <= 0:
                continue

            nuevo_counts[canonical] = actual_add
            total_added += actual_add

    return nuevo_counts


def save_deck_to_file(deck_counts, fname):
    if not os.path.isdir(DECKS_DIR):
        os.makedirs(DECKS_DIR)
    path = os.path.join(DECKS_DIR, f"{fname}.txt")
    with open(path, "w", encoding="utf-8") as f:
        for name in sorted(deck_counts.keys()):
            cnt = deck_counts[name]
            if cnt > 0:
                f.write(f"{cnt}x{name}\n")
    return path
