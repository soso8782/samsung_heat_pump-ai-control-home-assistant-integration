"""Konštanty integrácie Kúrenie AI."""
from homeassistant.const import Platform

from .model import DEFAULT_INTERVAL, MAX_INTERVAL, MIN_INTERVAL  # noqa: F401

DOMAIN = "kurenie_ai"
MANUFACTURER = "Samsung"
CONF_URL = "url"
CONF_API_KEY = "api_key"
CONF_SCAN_INTERVAL = "scan_interval"
REQUEST_TIMEOUT = 15

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.SELECT,
    Platform.NUMBER,
    Platform.BUTTON,
]
