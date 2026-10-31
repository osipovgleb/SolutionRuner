"""Validate annual interest-before-payment balances without rounding money."""

import sympy as sp

from .common import UnsupportedCondition


def balances(capital, factor, payments):
    debt, debts = capital, [capital]
    if capital <= 0 or factor <= 1 or any(p <= 0 for p in payments):
        raise UnsupportedCondition(
            "positive principal, interest and payments are required"
        )
    for payment in payments:
        debt = sp.simplify(debt * factor - payment)
        debts.append(debt)
    if debts[-1] != 0 or any(d <= 0 for d in debts[:-1]):
        raise UnsupportedCondition(
            "annual payments must close the debt exactly at maturity"
        )
    return tuple(debts)
