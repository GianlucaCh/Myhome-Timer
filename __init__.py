"""
MyHome Timer - Custom component per Home Assistant
Espone il servizio myhome_timer.turn_on_timed che:
  1. Accetta un'entità luce myhome
  2. Ne preleva gli attributi A e PL
  3. Accetta una durata (modalità WHAT semplice o Dimension=2 avanzata)
  4. Compila il frame OWN e lo invia via myhome.send_message

Protocollo OpenWebNet WHO=1 - BTicino/Legrand MyHome SCS
"""
import logging
import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity_component import EntityComponent

_LOGGER = logging.getLogger(__name__)

DOMAIN = "myhome_timer"

# -------------------------------------------------------------------
# Mappa dei timer WHAT semplici (WHO=1, sezione 3.1 del doc OWN)
# Frame: *1*<WHAT>*<WHERE>##
# -------------------------------------------------------------------
TIMER_WHAT_MAP = {
    "0.5sec":  18,   # ON timed 0.5 sec  - What = 18
    "30sec":   17,   # ON timed 30 sec   - What = 17
    "1min":    11,   # ON timed 1 min    - What = 11
    "2min":    12,   # ON timed 2 min    - What = 12
    "3min":    13,   # ON timed 3 min    - What = 13
    "4min":    14,   # ON timed 4 min    - What = 14
    "5min":    15,   # ON timed 5 min    - What = 15
    "15min":   16,   # ON timed 15 min   - What = 16
    # Per durate arbitrarie usa il metodo "custom" (Dimension=2)
}

# Etichette human-readable per il frontend
TIMER_LABELS = {
    "0.5sec":  "0.5 secondi",
    "30sec":   "30 secondi",
    "1min":    "1 minuto",
    "2min":    "2 minuti",
    "3min":    "3 minuti",
    "4min":    "4 minuti",
    "5min":    "5 minuti",
    "15min":   "15 minuti",
    "custom":  "Durata personalizzata (ore/min/sec)",
}

# Schema servizio myhome_timer.turn_on_timed
SERVICE_SCHEMA = vol.Schema({
    vol.Required("entity_id"): cv.entity_id,
    vol.Required("timer_mode"): vol.In(list(TIMER_WHAT_MAP.keys()) + ["custom"]),
    # Usati solo se timer_mode == "custom" (Dimension=2)
    vol.Optional("hours",   default=0): vol.All(int, vol.Range(min=0, max=255)),
    vol.Optional("minutes", default=0): vol.All(int, vol.Range(min=0, max=59)),
    vol.Optional("seconds", default=0): vol.All(int, vol.Range(min=0, max=59)),
})


def _build_where(entity) -> str | None:
    """
    Costruisce la stringa WHERE (A+PL concatenati) dagli attributi
    dell'entità luce myhome.

    Il componente anotherjulien/MyHOME espone gli attributi come 'A' e 'PL'
    (maiuscoli). Proviamo tutte le varianti per robustezza.

    Regole WHERE Table OWN (§2.3 WHO=1):
      A=00 → PL [01-15] → WHERE = "00" + PL a 2 cifre  es. A=00,PL=15 → "0015"
      A=[1-9] → PL [1-9] → WHERE = A + PL  es. A=1,PL=6 → "16"
      A=10 → PL [01-15] → WHERE = "10" + PL a 2 cifre  es. A=10,PL=3 → "1003"
      A=[01-09] → PL [10-15] → WHERE = A a 2 cifre + PL  es. A=1,PL=12 → "0112"
    """
    attrs = entity.attributes

    # Prova attributo diretto 'where' (già pronto)
    if "where" in attrs:
        return str(attrs["where"])

    # Cerca A con fallback maiuscolo/minuscolo/alias
    a_raw = (
        attrs.get("A") or attrs.get("a") or
        attrs.get("Area") or attrs.get("area")
    )
    # Cerca PL con fallback
    pl_raw = (
        attrs.get("PL") or attrs.get("pl") or
        attrs.get("Point_light") or attrs.get("point_light") or
        attrs.get("light_point")
    )

    if a_raw is None or pl_raw is None:
        return None

    a  = int(a_raw)
    pl = int(pl_raw)

    # Se uno dei due attributi è >= 10, entrambi vanno a 2 cifre (WHERE a 4 char)
    # Esempi: A=00,PL=15 → "0015" | A=10,PL=3 → "1003" | A=1,PL=12 → "0112"
    # Altrimenti 1 cifra ciascuno (WHERE a 2 char): A=2,PL=2 → "22" | A=1,PL=6 → "16"
    if a >= 10 or pl >= 10:
        return f"{a:02d}{pl:02d}"
    return f"{a}{pl}"


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Setup del componente myhome_timer."""

    async def handle_turn_on_timed(call: ServiceCall) -> None:
        entity_id   = call.data["entity_id"]
        timer_mode  = call.data["timer_mode"]
        hours       = call.data.get("hours",   0)
        minutes     = call.data.get("minutes", 0)
        seconds     = call.data.get("seconds", 0)

        # Recupera lo stato dell'entità
        entity = hass.states.get(entity_id)
        if entity is None:
            _LOGGER.error("myhome_timer: entità '%s' non trovata", entity_id)
            return

        # Ricava WHERE dagli attributi
        where = _build_where(entity)
        if where is None:
            _LOGGER.error(
                "myhome_timer: impossibile ricavare A/PL dall'entità '%s'. "
                "Attributi disponibili: %s",
                entity_id, dict(entity.attributes)
            )
            return

        # -----------------------------------------------------------
        # Costruzione del frame OWN
        # -----------------------------------------------------------
        if timer_mode == "custom":
            # Dimension=2: *#1*<WHERE>*#2*<hour>*<min>*<sec>##
            frame = f"*#1*{where}*#2*{hours}*{minutes}*{seconds}##"
            _LOGGER.info(
                "myhome_timer: invio temporizzazione custom %dh%dm%ds → %s",
                hours, minutes, seconds, frame
            )
        else:
            # WHAT semplice: *1*<WHAT>*<WHERE>##
            what  = TIMER_WHAT_MAP[timer_mode]
            frame = f"*1*{what}*{where}##"
            _LOGGER.info(
                "myhome_timer: invio timer '%s' (WHAT=%d) → %s",
                timer_mode, what, frame
            )

        # -----------------------------------------------------------
        # Invio tramite myhome.send_message
        # -----------------------------------------------------------
        await hass.services.async_call(
            "myhome",
            "send_message",
            {"message": frame},
            blocking=True,
        )

    hass.services.async_register(
        DOMAIN,
        "turn_on_timed",
        handle_turn_on_timed,
        schema=SERVICE_SCHEMA,
    )

    _LOGGER.info("myhome_timer: servizio 'myhome_timer.turn_on_timed' registrato")
    return True
