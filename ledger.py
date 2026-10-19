"""Pure, auditable average-cost portfolio accounting (economic, not tax advice)."""
from collections import defaultdict
from datetime import date
from decimal import Decimal

D = lambda value: Decimal(str(value))

class LedgerError(ValueError):
    pass


def calculate(transactions):
    """Transactions sorted by trade date then id, with cancelled entries excluded.

    FX is EUR per currency unit at trade time. SELL realizes gains using average cost.
    Returns positions, realized EUR, dividends EUR, fees EUR and cashflow EUR.
    """
    positions = defaultdict(lambda: {"quantity": D(0), "cost": D(0), "realized": D(0)})
    income = D(0)
    fees_total = D(0)
    cashflow = D(0)
    for t in sorted((x for x in transactions if not x.get("deleted", False)), key=lambda x: (str(x["trade_date"]), int(x["id"]))):
        kind = t["kind"]
        currency = str(t["currency"]).upper()
        fx = D(t["fx_eur"])
        if fx <= 0:
            raise LedgerError("Il cambio EUR deve essere positivo.")
        qty = D(t["quantity"])
        price = D(t["unit_price"])
        fee = D(t["fee"])
        if qty < 0 or price < 0 or fee < 0:
            raise LedgerError("Quantità, prezzo e commissioni non possono essere negativi.")
        if kind in ("BUY", "SELL") and qty <= 0:
            raise LedgerError("Acquisti e vendite richiedono quantità positiva.")
        if kind not in ("BUY", "SELL", "DIVIDEND"):
            raise LedgerError("Tipo operazione non valido.")
        key = (t["portfolio"], t["ticker"], currency, str(t.get("broker", "") or "").strip())
        p = positions[key]
        fee_eur = fee * fx
        fees_total += fee_eur
        if kind == "BUY":
            cost = (qty * price + fee) * fx
            p["quantity"] += qty
            p["cost"] += cost
            cashflow -= cost
        elif kind == "SELL":
            if qty > p["quantity"] + D("0.0000000001"):
                raise LedgerError(f"Vendita senza quote sufficienti: {t['portfolio']} / {t['ticker']} ({t['trade_date']}).")
            basis = p["cost"] * qty / p["quantity"]
            proceeds = (qty * price - fee) * fx
            p["realized"] += proceeds - basis
            p["quantity"] -= qty
            p["cost"] -= basis
            if abs(p["quantity"]) <= D("0.0000000001"):
                p["quantity"] = D(0)
                p["cost"] = D(0)
            cashflow += proceeds
        else:
            # Dividend amount entered as gross total in price; fee stores withholding/expenses.
            net = (price - fee) * fx
            income += net
            cashflow += net
    return {"positions": dict(positions), "realized": sum((p["realized"] for p in positions.values()), D(0)),
            "dividends": income, "fees": fees_total, "cashflow": cashflow}
