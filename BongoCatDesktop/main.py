"""
Bongo Cat de escritorio - version standalone (sin OBS)
--------------------------------------------------------
pip install -r requirements.txt
python main.py

Funciones:
- Reacciona a teclado y mouse GLOBAL (aunque el foco este en otra app).
- Sonido de tecla (max 2s, nunca se superpone).
- Reaccion distinta para click izquierdo / derecho / scroll.
- Combo: si tipeas muy rapido, cara de esfuerzo.
- Ctrl+C / Ctrl+V: animacion especial.
- Menu de "Coleccion" para elegir gatito (se desbloquean con el uso).
- Posicion/tamano/gatito se guardan solos en config.json.
- Click-through opcional (F9): los clicks pasan de largo, el gato solo
  reacciona pero no bloquea lo que esta debajo.
- Tooltip con teclas de hoy / totales.
- Modo "ronroneo": bamboleo suave si pasa mucho rato sin actividad.
"""
import sys
import time
import math
from collections import deque

from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QObject
from PyQt5.QtWidgets import (
    QApplication, QLabel, QWidget, QMenu, QAction, QSystemTrayIcon
)
from PyQt5.QtGui import QIcon, QPixmap

from pynput import keyboard, mouse

import config as cfgmod
from assets_manager import (
    ModeAssets, MODE_ORDER, MODE_LABELS, MODE_UNLOCK_AT, MODE_PLAYABLE,
    FACE_COOL, FACE_EFFORT, FACE_GAG, FACE_SURPRISED,
)
from sound_manager import KeySound
from collection_dialog import CollectionDialog

DOWN_HOLD_MS = 110
COMBO_WINDOW_SEC = 1.0
COMBO_THRESHOLD = 6
IDLE_PURR_SEC = 90


class InputSignals(QObject):
    """Puente entre los hooks globales (hilos aparte) y la GUI (hilo Qt)."""
    type_key = pyqtSignal()
    left_click = pyqtSignal()
    right_click = pyqtSignal()
    scroll = pyqtSignal()
    ctrl_c = pyqtSignal()
    ctrl_v = pyqtSignal()
    toggle_click_through = pyqtSignal()


class BongoCat(QWidget):
    def __init__(self):
        super().__init__()
        self.cfg = cfgmod.load_config()

        mode = self.cfg.get("mode", "keyboard")
        if not MODE_PLAYABLE.get(mode, False):
            mode = "keyboard"
        self.assets = ModeAssets(mode)

        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, self.cfg["click_through"])

        w, h = self.assets.size
        self.resize(int(w * self.cfg["scale"]), int(h * self.cfg["scale"]))

        self.label = QLabel(self)
        self.label.setGeometry(0, 0, self.width(), self.height())
        self.label.setScaledContents(True)

        self.sound = KeySound(volume=self.cfg["volume"], enabled=self.cfg["sound_enabled"])

        self.revert_timer = QTimer(self)
        self.revert_timer.setSingleShot(True)
        self.revert_timer.timeout.connect(self.show_idle)

        self.key_timestamps = deque()
        self.combo_active = False
        self.last_activity = time.time()
        self.purr_active = False
        self.purr_phase = 0.0
        self.purr_timer = QTimer(self)
        self.purr_timer.timeout.connect(self._purr_tick)
        self.idle_check_timer = QTimer(self)
        self.idle_check_timer.timeout.connect(self._idle_check)
        self.idle_check_timer.start(2000)

        self.tooltip_timer = QTimer(self)
        self.tooltip_timer.timeout.connect(self._update_tooltip)
        self.tooltip_timer.start(1000)

        self._rebuild_cycles()

        # posicion guardada, o esquina inferior derecha por defecto
        screen = QApplication.primaryScreen().availableGeometry()
        if self.cfg["pos_x"] is not None and self.cfg["pos_y"] is not None:
            self.move(self.cfg["pos_x"], self.cfg["pos_y"])
        else:
            self.move(screen.width() - self.width() - 20, screen.height() - self.height() - 20)

        self._drag_pos = None
        self.ctrl_down = False

        self.tray = self._build_tray()
        self.signals = InputSignals()
        self._connect_signals()
        self.start_global_hooks()

    # ---------- ciclo de frames por modo ----------
    def _rebuild_cycles(self):
        self.left_idx = 0
        self.right_idx = 0
        self.next_hand_is_left = True
        self.current_base_pil = self.assets.idle_pil
        self.label.setPixmap(self.assets.idle)

    def _next_left(self):
        i = self.left_idx
        self.left_idx = (self.left_idx + 1) % len(self.assets.left_down)
        return i

    def _next_right(self):
        i = self.right_idx
        self.right_idx = (self.right_idx + 1) % len(self.assets.right_down)
        return i

    def switch_mode(self, mode):
        if mode == self.assets.mode:
            return
        self.assets = ModeAssets(mode)
        self.cfg["mode"] = mode
        w, h = self.assets.size
        self.resize(int(w * self.cfg["scale"]), int(h * self.cfg["scale"]))
        self.label.setGeometry(0, 0, self.width(), self.height())
        self._rebuild_cycles()

    # ---------- mostrar frames ----------
    def show_idle(self):
        self.label.setPixmap(self.assets.idle)
        self.current_base_pil = self.assets.idle_pil

    def _show_frame(self, pixmap: QPixmap, base_pil=None):
        self.label.setPixmap(pixmap)
        if base_pil is not None:
            self.current_base_pil = base_pil
        self.revert_timer.start(DOWN_HOLD_MS)

    # ---------- eventos de teclado "normales" ----------
    def on_type_key(self):
        self._register_keystroke()
        self._register_combo_timestamp()

        if self.next_hand_is_left:
            i = self._next_left()
            pix = self.assets.left_down_effort[i] if self.combo_active else self.assets.left_down[i]
        else:
            i = self._next_right()
            pix = self.assets.right_down_effort[i] if self.combo_active else self.assets.right_down[i]
        self.next_hand_is_left = not self.next_hand_is_left

        self._show_frame(pix)
        self.sound.play()

    def on_ctrl_c(self):
        self._register_keystroke()
        self._show_frame(self.assets.idle_by_face[FACE_COOL])
        self.sound.play()

    def on_ctrl_v(self):
        self._register_keystroke()
        self._show_frame(self.assets.idle_by_face[FACE_SURPRISED])
        self.sound.play()

    # ---------- eventos de mouse ----------
    def on_left_click(self):
        self.last_activity = time.time()
        i = self._next_left()
        self._show_frame(self.assets.left_down[i])

    def on_right_click(self):
        self.last_activity = time.time()
        i = self._next_right()
        self._show_frame(self.assets.right_down_surprised[i])

    def on_scroll(self):
        now = time.time()
        # la rueda del mouse puede tirar decenas de eventos por segundo:
        # frenamos la reaccion visual para no saturar la GUI
        if now - getattr(self, "_last_scroll", 0) < 0.15:
            return
        self._last_scroll = now
        self.last_activity = now
        self._show_frame(self.assets.idle_by_face[FACE_GAG])

    # ---------- combo (tipeo rapido) ----------
    def _register_combo_timestamp(self):
        now = time.time()
        self.key_timestamps.append(now)
        while self.key_timestamps and now - self.key_timestamps[0] > COMBO_WINDOW_SEC:
            self.key_timestamps.popleft()
        self.combo_active = len(self.key_timestamps) >= COMBO_THRESHOLD

    # ---------- stats + desbloqueos ----------
    def _register_keystroke(self):
        self.cfg["lifetime_keys"] += 1
        self.cfg["keys_today"] += 1
        self.last_activity = time.time()
        self._check_unlocks()

    def _check_unlocks(self):
        lifetime = self.cfg["lifetime_keys"]
        for mode in MODE_ORDER:
            if not MODE_PLAYABLE[mode]:
                continue
            if mode in self.cfg["unlocked_modes"]:
                continue
            if lifetime >= MODE_UNLOCK_AT[mode]:
                self.cfg["unlocked_modes"].append(mode)
                self._notify(f"Nuevo gatito desbloqueado: {MODE_LABELS[mode]}")

    def _update_tooltip(self):
        self.setToolTip(
            f"Teclas hoy: {self.cfg['keys_today']}\n"
            f"Teclas en total: {self.cfg['lifetime_keys']}"
        )

    def _notify(self, text):
        if self.tray and self.tray.isVisible():
            self.tray.showMessage("Bongo Cat", text, QSystemTrayIcon.Information, 4000)

    # ---------- modo ronroneo (idle largo) ----------
    def _idle_check(self):
        idle_for = time.time() - self.last_activity
        if idle_for > IDLE_PURR_SEC and not self.purr_active:
            self.purr_active = True
            self.purr_timer.start(60)
        elif idle_for <= IDLE_PURR_SEC and self.purr_active:
            self.purr_active = False
            self.purr_timer.stop()
            self.label.setGeometry(0, 0, self.width(), self.height())

    def _purr_tick(self):
        self.purr_phase += 0.25
        offset = int(math.sin(self.purr_phase) * 3)
        self.label.setGeometry(0, offset, self.width(), self.height())

    # ---------- click-through ----------
    def toggle_click_through(self):
        self.cfg["click_through"] = not self.cfg["click_through"]
        self.setAttribute(Qt.WA_TransparentForMouseEvents, self.cfg["click_through"])
        estado = "activado" if self.cfg["click_through"] else "desactivado"
        self._notify(f"Click-through {estado} (F9 para cambiarlo de nuevo)")

    # ---------- hooks globales ----------
    def _connect_signals(self):
        self.signals.type_key.connect(self.on_type_key)
        self.signals.left_click.connect(self.on_left_click)
        self.signals.right_click.connect(self.on_right_click)
        self.signals.scroll.connect(self.on_scroll)
        self.signals.ctrl_c.connect(self.on_ctrl_c)
        self.signals.ctrl_v.connect(self.on_ctrl_v)
        self.signals.toggle_click_through.connect(self.toggle_click_through)

    def start_global_hooks(self):
        self.kb_listener = keyboard.Listener(on_press=self._on_press, on_release=self._on_release)
        self.mouse_listener = mouse.Listener(on_click=self._on_click, on_scroll=self._on_scroll)
        self.kb_listener.start()
        self.mouse_listener.start()

        self.hotkeys = keyboard.GlobalHotKeys({
            "<f9>": lambda: self.signals.toggle_click_through.emit()
        })
        self.hotkeys.start()

    def _on_press(self, key):
        if key in (keyboard.Key.ctrl_l, keyboard.Key.ctrl_r):
            self.ctrl_down = True
            return
        char = getattr(key, "char", None)
        if self.ctrl_down and char and char.lower() == "c":
            self.signals.ctrl_c.emit()
            return
        if self.ctrl_down and char and char.lower() == "v":
            self.signals.ctrl_v.emit()
            return
        self.signals.type_key.emit()

    def _on_release(self, key):
        if key in (keyboard.Key.ctrl_l, keyboard.Key.ctrl_r):
            self.ctrl_down = False

    def _on_click(self, x, y, button, pressed):
        if not pressed:
            return
        if button == mouse.Button.right:
            self.signals.right_click.emit()
        else:
            self.signals.left_click.emit()

    def _on_scroll(self, x, y, dx, dy):
        self.signals.scroll.emit()

    # ---------- arrastrar / escalar ----------
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
        elif event.button() == Qt.RightButton:
            self.show_context_menu(event.globalPos())

    def mouseMoveEvent(self, event):
        if self._drag_pos is not None and event.buttons() & Qt.LeftButton:
            self.move(event.globalPos() - self._drag_pos)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None

    def wheelEvent(self, event):
        delta = 0.1 if event.angleDelta().y() > 0 else -0.1
        self.cfg["scale"] = max(0.4, min(3.0, self.cfg["scale"] + delta))
        w, h = self.assets.size
        new_w, new_h = int(w * self.cfg["scale"]), int(h * self.cfg["scale"])
        self.resize(new_w, new_h)
        self.label.setGeometry(0, 0, new_w, new_h)

    # ---------- menus ----------
    def show_context_menu(self, pos):
        menu = QMenu(self)

        coleccion = QAction("Coleccion de gatitos...", self)
        coleccion.triggered.connect(self.open_collection)
        menu.addAction(coleccion)

        sonido = QAction("Sonido activado", self, checkable=True)
        sonido.setChecked(self.cfg["sound_enabled"])
        sonido.triggered.connect(self.toggle_sound)
        menu.addAction(sonido)

        click_through = QAction("Click-through (F9)", self, checkable=True)
        click_through.setChecked(self.cfg["click_through"])
        click_through.triggered.connect(lambda: self.signals.toggle_click_through.emit())
        menu.addAction(click_through)

        menu.addSeparator()
        quit_action = QAction("Salir", self)
        quit_action.triggered.connect(self.close_app)
        menu.addAction(quit_action)

        menu.exec_(pos)

    def toggle_sound(self):
        self.cfg["sound_enabled"] = not self.cfg["sound_enabled"]
        self.sound.set_enabled(self.cfg["sound_enabled"])

    def open_collection(self):
        dlg = CollectionDialog(
            self,
            lifetime_keys=self.cfg["lifetime_keys"],
            unlocked_modes=self.cfg["unlocked_modes"],
            current_mode=self.assets.mode,
            on_select=self.switch_mode,
        )
        dlg.exec_()

    def _build_tray(self):
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return None
        tray = QSystemTrayIcon(self)
        # icono simple generado a partir del propio gatito
        tray.setIcon(QIcon(self.assets.idle))
        tray.setToolTip("Bongo Cat")

        menu = QMenu()
        coleccion = menu.addAction("Coleccion de gatitos...")
        coleccion.triggered.connect(self.open_collection)
        click_through = menu.addAction("Alternar click-through (F9)")
        click_through.triggered.connect(lambda: self.signals.toggle_click_through.emit())
        sonido = menu.addAction("Alternar sonido")
        sonido.triggered.connect(self.toggle_sound)
        menu.addSeparator()
        salir = menu.addAction("Salir")
        salir.triggered.connect(self.close_app)

        tray.setContextMenu(menu)
        tray.show()
        return tray

    # ---------- salida ----------
    def close_app(self):
        self.cfg["pos_x"] = self.x()
        self.cfg["pos_y"] = self.y()
        self.cfg["mode"] = self.assets.mode
        cfgmod.save_config(self.cfg)

        self.kb_listener.stop()
        self.mouse_listener.stop()
        self.hotkeys.stop()
        QApplication.quit()


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(True)
    cat = BongoCat()
    cat.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
