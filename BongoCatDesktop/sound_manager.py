"""Sonido de tecla: se corta solo a los 2 segundos y nunca se superpone
(si llega un evento nuevo mientras suena, corta el anterior y arranca
de nuevo en vez de mezclar dos audios a la vez)."""
from pathlib import Path
from PyQt5.QtCore import QUrl, QTimer
from PyQt5.QtMultimedia import QSoundEffect

MAX_DURATION_MS = 2000
SOUND_PATH = Path(__file__).parent / "assets" / "sounds" / "key.wav"


class KeySound:
    def __init__(self, path: Path = SOUND_PATH, volume: float = 0.6, enabled: bool = True):
        self.enabled = enabled
        self.effect = QSoundEffect()
        if path.exists():
            self.effect.setSource(QUrl.fromLocalFile(str(path)))
        self.effect.setVolume(max(0.0, min(1.0, volume)))

        self._stop_timer = QTimer()
        self._stop_timer.setSingleShot(True)
        self._stop_timer.timeout.connect(self.effect.stop)

    def play(self):
        if not self.enabled or not self.effect.source().isValid():
            return
        if self.effect.isPlaying():
            self.effect.stop()
        self.effect.play()
        self._stop_timer.start(MAX_DURATION_MS)  # corte duro a los 2s

    def set_volume(self, v: float):
        self.effect.setVolume(max(0.0, min(1.0, v)))

    def set_enabled(self, enabled: bool):
        self.enabled = enabled
        if not enabled:
            self.effect.stop()

    def set_source(self, path: Path):
        if path.exists():
            self.effect.setSource(QUrl.fromLocalFile(str(path)))
