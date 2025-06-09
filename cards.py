import os
import sys
import ast
from PIL import Image, ImageTk

# =============================================================================
# Constantes y rutas base
# =============================================================================
def get_base_path():
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

BASE_PATH        = get_base_path()
CARD_DATA_DIR    = os.path.join(BASE_PATH, "card_data")
CARD_IMAGES_DIR  = os.path.join(BASE_PATH, "card_images")
RESTRICTIONS_DIR = os.path.join(BASE_PATH, "restrictions")
CARD_DISPLAY_W = 104 # ancho deseado en píxeles
CARD_DISPLAY_H = 156# alto deseado en píxeles

# =============================================================================
# Función para cargar límites restringidos
# =============================================================================
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
                        restricted_limits[name] = min(restricted_limits.get(name, lim), lim)
                    except:
                        continue
    return restricted_limits

# =============================================================================
# Mapas de saga y razas
# =============================================================================
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
# Clase Card
# =============================================================================
class Card:
    def __init__(self, name):
        self.name       = name
        self.data_path  = os.path.join(CARD_DATA_DIR, f"{name}.txt")
        self.image_path = None

        self.category   = None   # "Aliados","Talismanes","Totems","Armas","Oros"
        self.cost       = None   # int or None
        self.strength   = None   # int or None
        self.race       = None   # string or None
        self.saga       = None   # full saga name
        self.format     = None   # "pbx" or "reborn"
        self.tk_image   = None   # PhotoImage

        self._load_data()

    def _load_data(self):
        if not os.path.isfile(self.data_path):
            raise FileNotFoundError(f"Data file not found: {self.data_path}")
        with open(self.data_path, "r", encoding="utf-8") as f:
            arr = ast.literal_eval(f.read().strip())

        # Oro
        if len(arr) == 3 and isinstance(arr[0], str) and arr[0].lower() == "oros":
            _, saga_ab, fmt = arr
            self.category = "Oros"
            self.saga     = SAGA_MAP[saga_ab.lower()]
            self.format   = fmt.lower()

        # Talismanes/Armas/Totems
        elif len(arr) == 4 and isinstance(arr[0], int) and isinstance(arr[1], str):
            coste, tipo, saga_ab, fmt = arr
            self.category = tipo.capitalize()
            self.cost     = coste
            self.saga     = SAGA_MAP[saga_ab.lower()]
            self.format   = fmt.lower()

        # Aliados
        elif len(arr) == 6 and isinstance(arr[0], int) and isinstance(arr[1], int):
            coste, fuerza, _, raza, saga_ab, fmt = arr
            self.category = "Aliados"
            self.cost     = coste
            self.strength = fuerza
            self.race     = raza.lower()
            self.saga     = SAGA_MAP[saga_ab.lower()]
            self.format   = fmt.lower()

        else:
            raise ValueError(f"Invalid format in {self.data_path}")

    def load_image(self):
        """
        Busca la imagen (<name>.png/.jpg), la redimensiona manteniendo aspect ratio
        dentro de CARD_DISPLAY_W×CARD_DISPLAY_H, la centra en un lienzo de ese tamaño,
        y guarda PhotoImage en self.tk_image.
        """
        global _IMAGE_CACHE
        try:
            _IMAGE_CACHE
        except NameError:
            _IMAGE_CACHE = {}

        # Reutilizar cache
        if self.name in _IMAGE_CACHE:
            self.tk_image = _IMAGE_CACHE[self.name]
            return

        # Localizar archivo de imagen
        found = False
        for root, dirs, files in os.walk(CARD_IMAGES_DIR):
            for fname in files:
                low = fname.lower()
                if (low.endswith(".png") or low.endswith(".jpg")) and low[:-4] == self.name.lower():
                    self.image_path = os.path.join(root, fname)
                    found = True
                    break
            if found:
                break
        if not found:
            raise FileNotFoundError(f"No image for '{self.name}' in {CARD_IMAGES_DIR}")

        # --- abrir y redimensionar manteniendo aspect ratio dentro de CARD_DISPLAY_W×CARD_DISPLAY_H ---
        pil_img = Image.open(self.image_path).convert("RGBA")
        DISPLAY_W, DISPLAY_H = CARD_DISPLAY_W, CARD_DISPLAY_H
        w, h = pil_img.size

        # calcular escala para caber en ambos ejes
        scale_w = DISPLAY_W / w
        scale_h = DISPLAY_H / h
        scale = min(scale_w, scale_h)

        new_w = int(w * scale)
        new_h = int(h * scale)
        pil_resized = pil_img.resize((new_w, new_h), Image.LANCZOS)

        # crear lienzo transparente y centrar la imagen redimensionada
        canvas = Image.new("RGBA", (DISPLAY_W, DISPLAY_H), (0, 0, 0, 0))
        x_off = (DISPLAY_W - new_w) // 2
        y_off = (DISPLAY_H - new_h) // 2
        canvas.paste(pil_resized, (x_off, y_off), pil_resized)

        # cachear PhotoImage
        photo = ImageTk.PhotoImage(canvas)
        _IMAGE_CACHE[self.name] = photo
        self.tk_image = photo

