"""The tradable window matches when the roofs produce, and the agent fallback forecast uses the solar model."""
import pytest

from hizashi_shared import blocks, config, solar
from hizashi_shared.models import HouseInfo, Roof

pytestmark = pytest.mark.filterwarnings("ignore::DeprecationWarning")

DAY = config.SIM_DAY
ROOF = Roof(kwp=5, tilt=13, azimuth=180, inverter_kw=5)


@pytest.fixture(scope="module")
def clear_kwh():
    return solar.roof_kwh_per_block(ROOF, solar.clear_sky_frame(DAY))


def test_clear_sky_frame_shape():
    frame = solar.clear_sky_frame(DAY)
    assert len(frame) == config.BLOCKS_PER_DAY
    assert list(frame.columns) == ["ghi", "dni", "dhi", "temp_air", "cloud_cover"]


def test_tradable_is_exactly_the_producing_blocks(clear_kwh):
    producing = [i for i, kwh in enumerate(clear_kwh) if kwh > 0.001]
    assert producing == list(blocks.TRADABLE)


def test_peak_near_solar_noon(clear_kwh):
    peak = max(range(config.BLOCKS_PER_DAY), key=lambda i: clear_kwh[i])
    assert peak in (47, 48)          # 11:45-12:15; solar noon in Bengaluru ~12:05
    assert 24 < sum(clear_kwh) < 28  # ~5.2 peak-sun hours on 5 kWp


def test_agent_fallback_forecast_uses_solar_model(clear_kwh):
    from hizashi_agent.runtime import Runtime

    rt = Runtime("h12")
    house = HouseInfo(id="h12", label="House 12", transformer="T1", roof=ROOF, profile="none",
                      buyback_rate=3.89, metering="net", agent_url="http://x/")
    fcs = rt.fallback_forecast(house, DAY)
    assert len(fcs) == config.BLOCKS_PER_DAY
    assert [f.solar_p50 for f in fcs] == [round(k, 4) for k in clear_kwh]
    f = fcs[48]
    assert f.solar_p10 < f.solar_p50 < f.solar_p90
    assert all(f.solar_p50 == 0 for f in fcs if f.block.index not in blocks.TRADABLE)
