"""Čistá logika integrácie Samsung Heat Pump AI Control (bez závislosti na Home Assistantovi, preto testovateľná samostatne).

Parsuje odpoveď GET /api/ha/v1/state na hodnoty entít a zostavuje požiadavky akcií.
"""
from __future__ import annotations

from typing import Any, Callable
from urllib.parse import urlsplit

API_STATE = "/api/ha/v1/state"
API_MODE = "/api/ha/v1/mode"
API_ROOM_TARGET = "/api/ha/v1/room_target"
API_TUV_BOOST = "/api/ha/v1/tuv_boost"
API_RUN_NOW = "/api/ha/v1/run_now"

MODES = ("off", "advise", "control")
AGENT_STATES = ("ok", "pozor", "problem")
MIN_INTERVAL, MAX_INTERVAL, DEFAULT_INTERVAL = 15, 300, 30
ROOM_RANGE_FALLBACK = (15.0, 26.0)
TEXT_LIMIT = 255


def normalize_url(value: str) -> str:
    """'192.168.1.50' / 'http://192.168.1.50/' -> 'http://192.168.1.50'. ValueError pri neplatnej adrese."""
    v = (value or "").strip()
    if not v:
        raise ValueError("empty")
    if "://" not in v:
        v = "http://" + v
    p = urlsplit(v)
    if p.scheme not in ("http", "https") or not p.hostname:
        raise ValueError("invalid")
    try:
        port = p.port
    except ValueError as err:
        raise ValueError("invalid") from err
    host = "[%s]" % p.hostname if ":" in p.hostname else p.hostname
    return "%s://%s%s" % (p.scheme, host, ":%d" % port if port else "")


def clamp_interval(value: Any) -> int:
    try:
        v = int(float(value))
    except (TypeError, ValueError):
        return DEFAULT_INTERVAL
    return max(MIN_INTERVAL, min(MAX_INTERVAL, v))


def _dig(data: Any, *path: str) -> Any:
    for k in path:
        if not isinstance(data, dict):
            return None
        data = data.get(k)
    return data


def _num(v: Any) -> float | int | None:
    if isinstance(v, bool) or v is None:
        return None
    return v if isinstance(v, (int, float)) else None


def _text(v: Any) -> str | None:
    if v is None:
        return None
    s = str(v)
    return s if s else None


def validate_state(data: Any) -> bool:
    """Základná kontrola odpovede: slovník s verziou API 1."""
    return isinstance(data, dict) and data.get("api") == 1


# ---- hodnoty entít: kľúč -> funkcia(data) -> hodnota alebo None
SENSORS: dict[str, Callable[[dict], Any]] = {
    "outdoor_temperature": lambda d: _num(d.get("vonku")),
    "water_out": lambda d: _num(_dig(d, "voda", "vystup")),
    "water_return": lambda d: _num(_dig(d, "voda", "spiatocka")),
    "water_target": lambda d: _num(_dig(d, "voda", "ciel_krivky")),
    "water_delta_t": lambda d: _num(_dig(d, "voda", "delta_t")),
    "compressor_frequency": lambda d: _num(_dig(d, "kompresor", "frekvencia")),
    "curve_offset": lambda d: _num(d.get("posun")),
    "dhw_temperature": lambda d: _num(_dig(d, "tuv", "teplota")),
    "error_code": lambda d: _num(d.get("chyba_tc")),
    "agent_state": lambda d: _dig(d, "agent", "stav") if _dig(d, "agent", "stav") in AGENT_STATES else None,
    "agent_summary": lambda d: (_text(_dig(d, "agent", "zhrnutie")) or "")[:TEXT_LIMIT] or None,
    "alert_count": lambda d: len(alerts(d)),
}

BINARY_SENSORS: dict[str, Callable[[dict], Any]] = {
    "compressor_running": lambda d: _dig(d, "kompresor", "bezi"),
    "defrost": lambda d: _dig(d, "kompresor", "odmrazovanie"),
    "dhw_heating": lambda d: _dig(d, "tuv", "ohrev_bezi"),
    "problem": lambda d: problem(d),
    "esp_online": lambda d: _dig(d, "online", "esp"),
    "collector_online": lambda d: _dig(d, "online", "zberac"),
    "ha_online": lambda d: _dig(d, "online", "ha"),
}


def alerts(d: dict) -> list[dict]:
    a = d.get("poplachy")
    return [x for x in a if isinstance(x, dict)] if isinstance(a, list) else []


def problem(d: dict) -> bool:
    """Problém = aktívny poplach alebo chybový kód TČ ≠ 0."""
    err = _num(d.get("chyba_tc"))
    return bool(alerts(d)) or (err is not None and err != 0)


def bool_or_none(v: Any) -> bool | None:
    return v if isinstance(v, bool) else None


def rooms(d: dict) -> list[dict]:
    r = d.get("izby")
    return [x for x in r if isinstance(x, dict) and x.get("kluc")] if isinstance(r, list) else []


def room_temperature(d: dict, key: str) -> float | int | None:
    for r in rooms(d):
        if r["kluc"] == key:
            return _num(r.get("teplota"))
    return None


def room_attributes(d: dict, key: str) -> dict:
    for r in rooms(d):
        if r["kluc"] == key:
            return {"min_target": _num(r.get("min")), "reference": bool(r.get("referencna"))}
    return {}


def room_name(d: dict, key: str) -> str:
    for r in rooms(d):
        if r["kluc"] == key:
            return str(r.get("nazov") or key)
    return key


def has_dhw(d: dict) -> bool:
    return isinstance(d.get("tuv"), dict)


def room_target(d: dict) -> float | int | None:
    return _num(d.get("ciel_izba"))


def room_target_range(d: dict) -> tuple[float, float]:
    r = d.get("ciel_rozsah")
    if isinstance(r, (list, tuple)) and len(r) == 2 and _num(r[0]) is not None and _num(r[1]) is not None and r[0] < r[1]:
        return float(r[0]), float(r[1])
    return ROOM_RANGE_FALLBACK


def agent_mode(d: dict) -> str | None:
    m = _dig(d, "agent", "rezim")
    return m if m in MODES else None


def agent_attributes(d: dict) -> dict:
    return {"summary": _text(_dig(d, "agent", "zhrnutie")), "last_run": _dig(d, "agent", "posledny_beh"),
            "next_run": _dig(d, "agent", "dalsi_beh")}


def alert_attributes(d: dict) -> dict:
    return {"alerts": [{"kind": a.get("druh"), "text": a.get("text")} for a in alerts(d)]}


def device_info(d: dict) -> dict:
    """Údaje pre DeviceInfo: name, model, sw_version."""
    name = _dig(d, "zariadenie", "nazov")
    return {"name": "Samsung Heat Pump AI Control", "model": _text(_dig(d, "zariadenie", "model")),
            "sw_version": _text(d.get("verzia"))}


def entry_title(d: dict) -> str:
    """Názov položky integrácie: názov projektu + názov zariadenia z profilu."""
    name = _dig(d, "zariadenie", "nazov")
    return "Samsung Heat Pump AI Control – %s" % name if name else "Samsung Heat Pump AI Control"


# ---- akcie: (cesta, telo)
def action_mode(option: str) -> tuple[str, dict]:
    if option not in MODES:
        raise ValueError("invalid mode: %s" % option)
    return API_MODE, {"mode": option}


def action_room_target(value: float) -> tuple[str, dict]:
    v = float(value)
    return API_ROOM_TARGET, {"value": round(v * 2) / 2}


def action_run_now() -> tuple[str, dict]:
    return API_RUN_NOW, {}


def action_tuv_boost() -> tuple[str, dict]:
    return API_TUV_BOOST, {}
