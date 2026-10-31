"""Household use profiles: 96 blocks of mean and std kWh, from data/profiles/<name>.json."""
import json
from functools import lru_cache
from pathlib import Path

from . import config


@lru_cache(maxsize=None)
def _load(path: str) -> tuple[tuple[float, ...], tuple[float, ...]]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    mean, std = raw["mean"], raw["std"]
    if len(mean) != config.BLOCKS_PER_DAY or len(std) != config.BLOCKS_PER_DAY:
        raise ValueError(f"profile {path}: need {config.BLOCKS_PER_DAY} values")
    return tuple(float(x) for x in mean), tuple(float(x) for x in std)


def load_profile(name: str, profiles_dir: Path | None = None) -> tuple[list[float], list[float]]:
    """(mean kWh per block, std kWh per block), 96 each."""
    path = Path(profiles_dir or config.PROFILES_DIR) / f"{name}.json"
    mean, std = _load(str(path))
    return list(mean), list(std)
