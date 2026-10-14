"""Estado persistente del HMI (ultimo perfil de PLC seleccionado).

Se guarda en `config/hmi_state.json` (fuera de `app_config.json`) para recordar
el ultimo perfil entre reinicios sin ensuciar la configuracion versionada.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
STATE_FILE = PROJECT_ROOT / "config" / "hmi_state.json"


def load_state() -> dict:
    """Lee el estado persistido; devuelve {} si no existe o esta corrupto."""
    if not STATE_FILE.exists():
        return {}
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError) as e:
        logger.warning("No se pudo leer %s: %s", STATE_FILE, e)
        return {}


def save_active_profile(profile_name: str) -> None:
    """Guarda el nombre (stem) del perfil activo para el proximo arranque."""
    state = load_state()
    state["active_profile"] = profile_name
    try:
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=4)
    except OSError as e:
        logger.warning("No se pudo guardar %s: %s", STATE_FILE, e)
