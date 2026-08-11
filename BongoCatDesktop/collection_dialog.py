from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QWidget
)
from PyQt5.QtCore import Qt
from assets_manager import MODE_ORDER, MODE_LABELS, MODE_UNLOCK_AT, MODE_PLAYABLE


class CollectionDialog(QDialog):
    """Ventana aparte: muestra los 5 gatitos, cuales estan desbloqueados
    segun las teclas totales tipeadas, y deja elegir uno (si esta
    disponible en esta version standalone)."""

    def __init__(self, parent, lifetime_keys: int, unlocked_modes: list, current_mode: str, on_select):
        super().__init__(parent)
        self.setWindowTitle("Coleccion de gatitos")
        self.setMinimumWidth(360)
        self.on_select = on_select

        layout = QVBoxLayout(self)
        title = QLabel(f"<b>Teclas tipeadas en total: {lifetime_keys}</b>")
        layout.addWidget(title)

        for mode in MODE_ORDER:
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 4, 0, 4)

            unlocked = mode in unlocked_modes
            playable = MODE_PLAYABLE[mode]
            needed = MODE_UNLOCK_AT[mode]

            if not playable:
                status = "no disponible (requiere modelo 3D)"
            elif unlocked:
                status = "desbloqueado" + (" - en uso" if mode == current_mode else "")
            else:
                status = f"bloqueado - falta{'n' if needed - lifetime_keys != 1 else ''}n {max(0, needed - lifetime_keys)} teclas"

            label = QLabel(f"{MODE_LABELS[mode]}\n<i>{status}</i>")
            row_layout.addWidget(label, stretch=1)

            btn = QPushButton("Usar" if mode == current_mode else "Elegir")
            btn.setEnabled(unlocked and playable and mode != current_mode)
            btn.clicked.connect(lambda _, m=mode: self._choose(m))
            row_layout.addWidget(btn)

            layout.addWidget(row)

        close_btn = QPushButton("Cerrar")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

    def _choose(self, mode):
        self.on_select(mode)
        self.accept()
