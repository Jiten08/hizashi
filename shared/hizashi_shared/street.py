"""Load data/street.json into models."""
import json
from pathlib import Path

from . import config
from .models import HouseInfo, Mandate


def load_raw(path: Path | None = None) -> dict:
    return json.loads(Path(path or config.STREET_FILE).read_text(encoding="utf-8"))


def load_houses(path: Path | None = None) -> dict[str, HouseInfo]:
    raw = load_raw(path)
    return {h["id"]: HouseInfo.model_validate(h) for h in raw["houses"]}


def load_mandates(path: Path | None = None) -> dict[str, Mandate]:
    raw = load_raw(path)
    return {m["house"]: Mandate.model_validate(m) for m in raw.get("mandates", [])}


def load_transformers(path: Path | None = None) -> list[str]:
    raw = load_raw(path)
    return raw.get("transformers") or sorted({h["transformer"] for h in raw["houses"]})


def neighbours(houses: dict[str, HouseInfo], house: str, same_transformer: bool = True) -> list[HouseInfo]:
    """Other houses in registry order, optionally only on the same transformer."""
    me = houses[house]
    return [
        h for h in houses.values()
        if h.id != house and (not same_transformer or h.transformer == me.transformer)
    ]
