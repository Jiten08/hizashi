from pathlib import Path
from hizashi_hub.sim import weather

test_dir = Path(__file__).resolve().parent / "_manual_test_cache"

async def test_direct():
    test_dir.mkdir(exist_ok=True)
    async def mock_offline(day):
        raise RuntimeError("simulated offline")

    orig = weather.fetch_open_meteo
    try:
        weather.fetch_open_meteo = mock_offline
        frame, source = await weather.load_weather("2026-10-31", cache_dir=test_dir)
        assert source == "clear-sky fallback"
        assert len(frame) == 96
        assert (test_dir / "2026-10-31.json").exists()
    finally:
        weather.fetch_open_meteo = orig
        import shutil
        shutil.rmtree(test_dir, ignore_errors=True)