"""Household use profiles: 96 blocks of mean and std kWh, from data/profiles/<name>.json."""
import json
from functools import lru_cache
from pathlib import Path

import numpy as np

from . import config

PROFILE_ANCHORS: dict[str, list[tuple[float, float]]] = {
    "couple_away_day": [(0, .05), (6, .05), (6.75, .25), (8.25, .25), (9.5, .14), (10, .12),
                        (13.5, .16), (17, .14), (18.5, .35), (22, .35), (23.5, .08), (24, .05)],
    "wfh_ac": [(0, .10), (6, .10), (6.75, .25), (8.25, .25), (9.5, .28), (10, .30),
               (17, .30), (18.5, .40), (22, .40), (23.5, .15), (24, .10)],
    "family_medium": [(0, .06), (6, .06), (6.75, .30), (8.25, .30), (9.5, .20), (10, .18),
                      (17, .18), (18.5, .40), (22, .40), (23.5, .10), (24, .06)],
    "heavy_appliances": [(0, .08), (6, .08), (6.75, .30), (8.25, .30), (9.5, .28), (10, .28),
                         (13, .35), (17, .30), (18.5, .45), (22, .45), (23.5, .12), (24, .08)],
}


def synthesize_profile(name: str) -> tuple[tuple[float, ...], tuple[float, ...]]:
    """Synthesize 96-block mean and std curves based on Prayas eMARC load curves."""
    if name not in PROFILE_ANCHORS:
        raise FileNotFoundError(f"Unknown profile: {name}")
    hours, values = zip(*PROFILE_ANCHORS[name])
    mids = (np.arange(config.BLOCKS_PER_DAY) + 0.5) * config.BLOCK_MINUTES / 60
    mean = np.interp(mids, hours, values)
    kernel = np.ones(5) / 5
    for _ in range(2):
        padded = np.concatenate([mean[-2:], mean, mean[:2]])
        mean = np.convolve(padded, kernel, mode="valid")
    mean_list = [round(float(x), 4) for x in mean]
    std_list = [round(float(x) * 0.20, 4) for x in mean_list]
    return tuple(mean_list), tuple(std_list)


@lru_cache(maxsize=None)
def _load(path_str: str, name: str) -> tuple[tuple[float, ...], tuple[float, ...]]:
    path = Path(path_str)
    if path.exists():
        raw = json.loads(path.read_text(encoding="utf-8"))
        mean, std = raw["mean"], raw["std"]
        if len(mean) != config.BLOCKS_PER_DAY or len(std) != config.BLOCKS_PER_DAY:
            raise ValueError(f"profile {path}: need {config.BLOCKS_PER_DAY} values")
        return tuple(float(x) for x in mean), tuple(float(x) for x in std)
    return synthesize_profile(name)


def load_profile(name: str, profiles_dir: Path | None = None) -> tuple[list[float], list[float]]:
    """(mean kWh per block, std kWh per block), 96 each."""
    path = Path(profiles_dir or config.PROFILES_DIR) / f"{name}.json"
    mean, std = _load(str(path), name)
    return list(mean), list(std)
