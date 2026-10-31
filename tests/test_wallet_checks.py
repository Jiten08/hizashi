"""Wallet offer checks in order (section 6.3). Enable when R1.1 / R2.5 land."""
import pytest

pytestmark = pytest.mark.skip(reason="TODO(R1.1, R2.5): wallet/checks.check_offer")


def test_bid_above_max_is_refused():
    """The ₹40 bid: refused at check 4 with 'Your max is ₹5.50'."""


def test_wrong_token_refused_first():
    """Check 1 runs before everything else."""


def test_daily_budget():
    """Check 7: committed buys + kwh*price > daily_budget -> refused."""


def test_offer_above_approve_above_goes_pending():
    """Check 8: not covered by an approved/auto window and value > approve_above -> pending."""
