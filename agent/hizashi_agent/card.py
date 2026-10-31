"""AgentCard for a house (a2a-sdk 1.2.1 types, as in agent/examples/negotiation_sample.py)."""
from a2a.types import AgentCapabilities, AgentCard, AgentInterface, AgentSkill

from hizashi_shared.models import HouseInfo


def build_card(house: HouseInfo) -> AgentCard:
    sells = "sells spare rooftop solar and buys" if house.roof else "buys"
    return AgentCard(
        name=f"Hizashi agent · {house.label}",
        description=f"Trades energy for {house.label}: {sells} from neighbours, inside the owner's limits",
        version="0.1.0",
        supported_interfaces=[
            AgentInterface(url=house.agent_url, protocol_binding="JSONRPC", protocol_version="1.0")
        ],
        capabilities=AgentCapabilities(streaming=False),
        default_input_modes=["application/json"],
        default_output_modes=["application/json"],
        skills=[
            AgentSkill(
                id="trade_block",
                name="Trade energy for one 15-minute block",
                description="Replies to an ask with a bid, an accept or a refusal",
                tags=["energy", "p2p"],
            )
        ],
    )
