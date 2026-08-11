"""Config persistente: posición, tamaño, modo, stats, unlocks, etc."""
import json
from pathlib import Path
from datetime import date

CONFIG_PATH = Path(__file__).parent / "config.json"

DEFAULTS = {
    "pos_x": None,
    "pos_y": None,
    "scale": 1.0,
    "mode": "keyboard",
    "click_through": False,
    "sound_enabled": True,
    "volume": 0.6,
    "lifetime_keys": 0,
    "stats_date": str(date.today()),
    "keys_today": 0,
    "unlocked_modes": ["keyboard", "mania"],
}


def load_config():
    data = {}
    if CONFIG_PATH.exists():
        try:
            data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except Exception:
            data = {}
    cfg = DEFAULTS.copy()
    cfg.update(data)
    if cfg.get("stats_date") != str(date.today()):
        cfg["stats_date"] = str(date.today())
        cfg["keys_today"] = 0
    return cfg


def save_config(cfg):
    try:
        CONFIG_PATH.write_text(
            json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8"
        )
    except Exception as e:
        print("No se pudo guardar config.json:", e)
