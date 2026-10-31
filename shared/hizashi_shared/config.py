"""Tariffs, fee, thresholds, ports, paths. Values come from .env (python-dotenv) with defaults."""
import os
from datetime import time
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")


def _s(name: str, default: str) -> str:
    return os.environ.get(name, default)


def _f(name: str, default: float) -> float:
    return float(os.environ.get(name, default))


def _i(name: str, default: int) -> int:
    return int(os.environ.get(name, default))


# Paths
DATA_DIR = ROOT / "data"
STREET_FILE = DATA_DIR / "street.json"
PROFILES_DIR = DATA_DIR / "profiles"
WEATHER_DIR = DATA_DIR / "weather"
KEYS_DIR = ROOT / "keys"
DB_PATH = ROOT / "hub" / "hizashi.db"
WEB_DIST = ROOT / "web" / "dist"

# Time
TZ_NAME = "Asia/Kolkata"
TZ = ZoneInfo(TZ_NAME)
DAY_START = time(5, 0)
DAY_END = time(19, 0)
BLOCK_MINUTES = 15
BLOCKS_PER_DAY = 96

# Simulation
SIM_DAY = _s("SIM_DAY", "2026-10-31")
SIM_SPEED = _i("SIM_SPEED", 60)
SIM_SEED = _i("SIM_SEED", 31)
ALLOWED_SPEEDS = (1, 60, 300)
LAT = _f("LAT", 12.93)
LON = _f("LON", 77.55)
ALT = _f("ALT", 900)

# Tariff and market
RETAIL_ENERGY_CHARGE = _f("RETAIL_ENERGY_CHARGE", 5.80)   # R
FEE_PER_KWH = _f("FEE_PER_KWH", 0.14)                     # F
MIN_TRADE_KWH = _f("MIN_TRADE_KWH", 0.05)
SELLER_OPEN_DISCOUNT = _f("SELLER_OPEN_DISCOUNT", 0.40)
BUYER_OPEN_PRICE = _f("BUYER_OPEN_PRICE", 4.00)
MAX_ROUNDS = _i("MAX_ROUNDS", 6)
CONCESSION_BETA = _f("CONCESSION_BETA", 1.0)
EXPECTED_P2P_PRICE = _f("EXPECTED_P2P_PRICE", 4.68)

# BESCOM buyback for exported solar (KERC). PM Surya Ghar subsidised systems get a lower rate.
BUYBACK_UNSUBSIDISED = _f("BUYBACK_UNSUBSIDISED", 3.89)
BUYBACK_SUBSIDISED_2KW = _f("BUYBACK_SUBSIDISED_2KW", 1.96)    # up to 2 kW
BUYBACK_SUBSIDISED = _f("BUYBACK_SUBSIDISED", 2.14)            # above 2 kW


def buyback_rate(kwp: float, subsidised: bool) -> float:
    if not subsidised:
        return BUYBACK_UNSUBSIDISED
    return BUYBACK_SUBSIDISED_2KW if kwp <= 2.0 else BUYBACK_SUBSIDISED
NEGOTIATION_ROUND_DELAY_MS = _i("NEGOTIATION_ROUND_DELAY_MS", 700)

# Network
HUB_URL = _s("HUB_URL", "http://127.0.0.1:8000").rstrip("/")
PUBLIC_URL = _s("PUBLIC_URL", "").rstrip("/")
HUB_PORT = 8000
AGENT_PORTS = {"h12": 9012, "h14": 9014, "h16": 9016, "h18": 9018}

AGENT_TOKENS = {h: _s(f"AGENT_TOKEN_{h.upper()}", f"dev-{h}") for h in AGENT_PORTS}

# Phase 3
GEMINI_API_KEY = _s("GEMINI_API_KEY", "")
GROQ_API_KEY = _s("GROQ_API_KEY", "")
TWILIO_ACCOUNT_SID = _s("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = _s("TWILIO_AUTH_TOKEN", "")
TWILIO_WHATSAPP_FROM = _s("TWILIO_WHATSAPP_FROM", "")
OWNER_WHATSAPP = {
    "h12": _s("OWNER_WHATSAPP_H12", ""),
    "h14": _s("OWNER_WHATSAPP_H14", ""),
}


def ws_url(path: str = "/ws") -> str:
    return HUB_URL.replace("http://", "ws://").replace("https://", "wss://") + path
