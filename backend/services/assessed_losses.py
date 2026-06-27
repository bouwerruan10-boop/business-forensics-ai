"""
assessed_losses.py - deterministic SA assessed-loss set-off (s20 / s20A).

Pure functions; the LLM only narrates. Two regimes:

- COMPANIES (s20(1)(a) proviso, years of assessment ending on/after 31 Mar
  2023): the balance of assessed loss brought forward that may be set off is
  limited to the HIGHER of R1,000,000 or 80% of taxable income (before set-off).
  So a profitable company can no longer wipe taxable income to nil with old
  losses - at least (taxable income - that cap) stays taxable. The unutilised
  balance carries forward.

- INDIVIDUALS / TRUSTS: no 80% cap - the loss sets off in full against income.
  But s20A "ring-fences" a loss from a SUSPECT TRADE for a natural person whose
  taxable income (before the loss) is at/above the point where the maximum
  marginal rate applies: such a loss may only be set off against income from the
  same trade and is otherwise carried forward.

Figures come from the dated `sa_rates`; the top-bracket threshold is derived from
the single `SA_BRACKETS` source. Re-verify against SARS each year of assessment.
"""

from services import sa_rates
from services.income_tax import _num
from services.relocation_tax import SA_BRACKETS


# The s20A threshold: the taxable-income level at which the MAXIMUM marginal rate
# first applies = the upper bound of the second-to-last bracket. Derived (not
# hardcoded) so it tracks the single dated bracket source.
def ring_fence_threshold():
    """Taxable income at/above which s20A ring-fencing can bite (top-rate point)."""
    try:
        return float(SA_BRACKETS[-2][0])
    except (IndexError, TypeError):
        return float("inf")


def company_loss_setoff(taxable_income_before, balance_brought_forward):
    """Apply the s20 80%/R1m company cap.

    Returns the allowed set-off, taxable income after set-off, and the loss
    balance carried forward. Set-off is limited to the HIGHER of R1m or 80% of
    taxable income, and never more than the available loss or the income itself.
    """
    ti = _num(taxable_income_before)
    loss = _num(balance_brought_forward)
    cap = max(sa_rates.ASSESSED_LOSS_SETOFF_FLOOR,
              sa_rates.ASSESSED_LOSS_SETOFF_CAP_PCT * ti)
    allowed = min(loss, cap, ti)            # cannot create/deepen a loss via set-off
    return {
        "allowed_setoff": round(allowed, 2),
        "cap_applied": round(cap, 2),
        "taxable_income_after": round(ti - allowed, 2),
        "carried_forward": round(loss - allowed, 2),
        "capped": loss > allowed and ti > 0,   # some loss left unused because of the cap
    }


def individual_loss_setoff(taxable_income_before, balance_brought_forward,
                           suspect_trade=False, fails_facts_test=False):
    """Set off an individual's assessed loss (no 80% cap).

    If the loss is from a suspect trade (or fails the facts test) AND taxable
    income before the loss is at/above the top-rate threshold, s20A ring-fences
    it: no set-off this year, full balance carried forward against that trade.
    """
    ti = _num(taxable_income_before)
    loss = _num(balance_brought_forward)
    ring_fenced = bool(suspect_trade or fails_facts_test) and ti >= ring_fence_threshold()
    if ring_fenced:
        return {
            "allowed_setoff": 0.0,
            "taxable_income_after": round(ti, 2),
            "carried_forward": round(loss, 2),
            "ring_fenced": True,
        }
    allowed = min(loss, ti)
    return {
        "allowed_setoff": round(allowed, 2),
        "taxable_income_after": round(ti - allowed, 2),
        "carried_forward": round(loss - allowed, 2),
        "ring_fenced": False,
    }


def assess_assessed_loss(taxable_income_before=0, balance_brought_forward=0,
                         taxpayer="company", suspect_trade=False,
                         fails_facts_test=False, **_ignored):
    """Full assessed-loss assessment for a company or an individual/trust."""
    tp = taxpayer if taxpayer in ("company", "individual", "trust") else "company"
    if tp == "company":
        r = company_loss_setoff(taxable_income_before, balance_brought_forward)
        regime = ("s20 company set-off - limited to the higher of R1,000,000 or "
                  "80% of taxable income; balance carried forward.")
    else:
        # trusts are taxed like individuals for set-off (no 80% cap); s20A applies
        # specifically to natural persons but the math is the same shape.
        r = individual_loss_setoff(taxable_income_before, balance_brought_forward,
                                   suspect_trade, fails_facts_test)
        regime = ("s20 full set-off (no 80% cap); s20A ring-fences a suspect-trade "
                  "loss for a top-bracket natural person.")
    return {
        "as_of": "SA 2026/27 tax year",
        "taxpayer": tp,
        "taxable_income_before": round(_num(taxable_income_before), 2),
        "balance_brought_forward": round(_num(balance_brought_forward), 2),
        "ring_fence_threshold": ring_fence_threshold(),
        "regime": regime,
        **r,
        "disclaimer": "Decision-support only - not tax advice; confirm with a tax practitioner.",
    }
