# cards.py

import os
import sys
import ast
from PIL import Image, ImageTk

# =============================================================================
# Constantes y rutas base (igual lógica que en main.py)
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
CARD_DATA_DIR   = os.path.join(BASE_PATH, "card_data")
CARD_IMAGES_DIR = os.path.join(BASE_PATH, "card_images")
RESTRICTIONS_DIR= os.path.join(BASE_PATH, "restrictions")

# =============================================================================
# Mapas de saga y razas (idénticos a main.py)
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
# Carga de límites restringidos (para uso externo)
# =============================================================================
CARD_MAX_DEFAULT = 3

def load_restricted_limits():
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
    return restricted_limits

# =============================================================================
# Clase Card: maneja datos e imágenes de cada carta
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

        self.category = None   # "Aliados","Talismanes","Totems","Armas","Oros"
        self.cost = None       # int o None
        self.strength = None   # int o None
        self.race = None       # string o None
        self.saga = None       # nombre completo de saga
        self.format = None     # "pbx" o "reborn"
        self.tk_image = None   # PhotoImage cargada en load_image()

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
        Busca la imagen correspondiente (<name>.png o <name>.jpg) en las subcarpetas de CARD_IMAGES_DIR,
        la redimensiona a ancho fijo (80 px), guarda una PhotoImage en self.tk_image y la almacena en
        un cache global para no volver a leerla de disco la próxima vez.
        """
        # Si ya existe en el cache global, la reutiliza directamente
        global _IMAGE_CACHE
        if "_IMAGE_CACHE" not in globals():
            _IMAGE_CACHE = {}

        if self.name in _IMAGE_CACHE:
            # Ya había sido cargada, solo asignarla
            self.tk_image = _IMAGE_CACHE[self.name]
            return

        # Buscar el archivo de imagen en carpetas de CARD_IMAGES_DIR
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

        # Abrir, redimensionar y convertir a PhotoImage
        pil_img = Image.open(self.image_path)
        DISPLAY_WIDTH = 80
        w, h = pil_img.size
        ratio = DISPLAY_WIDTH / w
        new_h = int(h * ratio)
        pil_resized = pil_img.resize((DISPLAY_WIDTH, new_h), Image.LANCZOS)
        photo = ImageTk.PhotoImage(pil_resized)

        # Guardar en cache y asignar a self.tk_image
        _IMAGE_CACHE[self.name] = photo
        self.tk_image = photo
