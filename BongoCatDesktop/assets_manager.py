"""Carga y compone los sprites del gatito para cada 'modo' (gatito)."""
from pathlib import Path
from PIL import Image
from PyQt5.QtGui import QPixmap, QImage

ASSETS_DIR = Path(__file__).parent / "assets"
MODES_DIR = ASSETS_DIR / "modes"
FACES_DIR = ASSETS_DIR / "faces"

# Los 5 "gatitos" existen en el plugin original de OBS, pero standard /
# feixue / bilibiliduo dibujan la pata derecha con un modelo 3D Live2D
# (Cubism SDK) que esta version no reproduce -> se muestran en la
# Coleccion pero marcados como no disponibles, en vez de mostrar un
# gatito roto/incompleto.
MODE_ORDER = ["keyboard", "mania", "standard", "feixue", "bilibiliduo"]

MODE_LABELS = {
    "keyboard": "Clasico (2 manos)",
    "mania": "Mania",
    "standard": "Standard",
    "feixue": "Feixue",
    "bilibiliduo": "Bilibili Duo",
}

MODE_UNLOCK_AT = {
    "keyboard": 0,
    "mania": 300,
    "standard": 1500,
    "feixue": 3000,
    "bilibiliduo": 6000,
}

# Solo estos dos vienen 100% en PNG (sin modelo 3D) -> son los que se
# pueden jugar de verdad en esta version standalone.
MODE_PLAYABLE = {
    "keyboard": True,
    "mania": True,
    "standard": False,
    "feixue": False,
    "bilibiliduo": False,
}

# Faces (F1-F4 en el plugin original): las reciclamos como reacciones
# 0 = lentes "cool" (Ctrl+C)      1 = sonrojado/esfuerzo (combo tipeo rapido)
# 2 = "dame plata" (gag, scroll)  3 = sorprendido (Ctrl+V / click derecho)
FACE_COOL = 0
FACE_EFFORT = 1
FACE_GAG = 2
FACE_SURPRISED = 3


def pil_to_qpixmap(img: Image.Image) -> QPixmap:
    img = img.convert("RGBA")
    data = img.tobytes("raw", "RGBA")
    qimg = QImage(data, img.width, img.height, QImage.Format_RGBA8888)
    return QPixmap.fromImage(qimg.copy())


class ModeAssets:
    """Compone y cachea los frames PIL/QPixmap de un modo jugable."""

    def __init__(self, mode: str):
        if not MODE_PLAYABLE.get(mode, False):
            raise ValueError(f"El modo '{mode}' no esta disponible en esta version (requiere modelo 3D)")
        self.mode = mode
        folder = MODES_DIR / mode

        bg = Image.open(folder / "bg.png").convert("RGBA")
        cat = Image.open(folder / "catbg.png").convert("RGBA")
        self.base = Image.alpha_composite(bg, cat)
        self.size = self.base.size

        self.left_up = Image.open(folder / "lefthand" / "leftup.png").convert("RGBA")
        self.right_up = Image.open(folder / "righthand" / "rightup.png").convert("RGBA")

        self.left_downs = [
            Image.open(p).convert("RGBA")
            for p in sorted((folder / "lefthand").glob("[0-9]*.png"))
        ]
        self.right_downs = [
            Image.open(p).convert("RGBA")
            for p in sorted((folder / "righthand").glob("[0-9]*.png"))
        ]

        self.faces = [Image.open(FACES_DIR / f"{i}.png").convert("RGBA") for i in range(4)]

        # PIL de cada estado (sin cara) - se guardan solo para precalcular,
        # no se tocan mas en tiempo real (eso es lo que causaba el lag)
        self.idle_pil = self._compose(self.left_up, self.right_up)
        self.left_down_pil = [self._compose(l, self.right_up) for l in self.left_downs]
        self.right_down_pil = [self._compose(self.left_up, r) for r in self.right_downs]

        # QPixmap listos para mostrar directo, SIN cara
        self.idle = pil_to_qpixmap(self.idle_pil)
        self.left_down = [pil_to_qpixmap(f) for f in self.left_down_pil]
        self.right_down = [pil_to_qpixmap(f) for f in self.right_down_pil]

        # --- Todas las combinaciones con cara, precalculadas UNA sola vez ---
        # (antes esto se recomponia con Pillow en cada tecla -> lag al
        # tipear rapido; ahora tipear rapido solo hace un lookup a una lista)
        self.idle_by_face = [self._compose_face(self.idle_pil, i) for i in range(4)]
        self.left_down_effort = [self._compose_face(f, FACE_EFFORT) for f in self.left_down_pil]
        self.right_down_effort = [self._compose_face(f, FACE_EFFORT) for f in self.right_down_pil]
        self.right_down_surprised = [self._compose_face(f, FACE_SURPRISED) for f in self.right_down_pil]

    def _fit(self, img: Image.Image) -> Image.Image:
        """Algunos frames sueltos del pack original vienen 1-2px mas chicos
        que el canvas base -> los pegamos sobre un lienzo transparente del
        mismo tamano para poder componerlos sin error."""
        if img.size == self.size:
            return img
        canvas = Image.new("RGBA", self.size, (0, 0, 0, 0))
        canvas.paste(img, (0, 0))
        return canvas

    def _compose(self, left_img, right_img):
        img = Image.alpha_composite(self.base, self._fit(left_img))
        img = Image.alpha_composite(img, self._fit(right_img))
        return img

    def _compose_face(self, base_pil: Image.Image, face_index: int) -> QPixmap:
        """Uso interno SOLO durante la carga (precalculo). No llamar en
        tiempo real: la composicion con Pillow es lenta para hacerla en
        cada evento de teclado/mouse."""
        face = self.faces[face_index]
        if face.size != base_pil.size:
            face = face.resize(base_pil.size)
        comp = Image.alpha_composite(base_pil, face)
        return pil_to_qpixmap(comp)
