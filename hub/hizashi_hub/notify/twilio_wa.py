"""WhatsApp approvals: on approval.requested for a house with OWNER_WHATSAPP_<H>, send the
summary + "Reply YES 4821 or NO 4821". The webhook parses replies."""
from hizashi_shared.models import Approval


def send_approval(approval: Approval) -> None:
    raise NotImplementedError("TODO(N1, Prajval)")


def parse_reply(body: str) -> tuple[str, str] | None:
    """'YES 4821' -> ("approve", "4821"); 'NO 4821' -> ("decline", "4821")."""
    raise NotImplementedError("TODO(N1, Prajval)")
