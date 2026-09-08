"""Broker-Gebuehrenmodell und Guenstigster-Ermittlung.

Rein: laedt nur die YAML-Datei, kein Netzwerkzugriff. Die Kostenformel ist
bewusst simpel und im Code nachvollziehbar (siehe order_cost), keine
Bibliotheks-Blackbox.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import yaml

OrderKind = Literal["einmalkauf", "sparplan"]

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


@dataclass(frozen=True)
class Broker:
    id: str
    name: str
    venue: str
    order_fixed: float
    order_pct: float
    order_min: float
    order_max: float | None
    free_above: float | None
    savings_plan_fixed: float
    savings_plan_pct: float
    subscription_eur: float
    affiliate_url: str | None
    note: str
    fee_basis: str


def load_brokers(path: Path | None = None) -> list[Broker]:
    """Liest data/brokers.yaml und gibt die Broker in Dateireihenfolge zurueck."""
    src = path or (DATA_DIR / "brokers.yaml")
    raw = yaml.safe_load(src.read_text(encoding="utf-8"))
    return [Broker(**entry) for entry in raw["brokers"]]


def order_cost(broker: Broker, volume: float, kind: OrderKind = "einmalkauf") -> float:
    """Kosten einer einzelnen Ausfuehrung in EUR.

    Formel (transparent):
        kosten = order_fixed + order_pct * volume
        danach auf order_min angehoben und auf order_max gedeckelt.
    Sonderfall free_above: ab diesem Ordervolumen 0 EUR (nur Einmalkauf).
    Sparplan nutzt savings_plan_fixed + savings_plan_pct * volume.

    Das monatliche Abo (subscription_eur) ist NICHT enthalten, da es nicht je
    Order anfaellt. Es wird separat ausgewiesen.
    """
    if volume < 0:
        raise ValueError("volume darf nicht negativ sein")

    if kind == "sparplan":
        return round(broker.savings_plan_fixed + broker.savings_plan_pct * volume, 2)

    if broker.free_above is not None and volume >= broker.free_above:
        return 0.0

    cost = broker.order_fixed + broker.order_pct * volume
    if broker.order_min:
        cost = max(cost, broker.order_min)
    if broker.order_max is not None:
        cost = min(cost, broker.order_max)
    return round(cost, 2)


@dataclass(frozen=True)
class Quote:
    broker: Broker
    cost: float
    cost_ratio: float  # cost / volume, 0.001 = 0,1 %
    is_cheapest: bool


def rank_brokers(
    brokers: list[Broker], volume: float, kind: OrderKind = "einmalkauf"
) -> list[Quote]:
    """Broker nach Kosten fuer die gegebene Order sortiert, guenstigste zuerst.

    Bei Gleichstand entscheidet der Name alphabetisch. Alle Broker mit den
    niedrigsten Kosten bekommen is_cheapest = True.
    """
    priced = [(b, order_cost(b, volume, kind)) for b in brokers]
    cheapest = min((c for _, c in priced), default=0.0)
    priced.sort(key=lambda r: (r[1], r[0].name.lower()))
    return [
        Quote(
            broker=b,
            cost=c,
            cost_ratio=(c / volume if volume else 0.0),
            is_cheapest=abs(c - cheapest) < 1e-9,
        )
        for b, c in priced
    ]


_UMLAUT = {"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"}


def slugify(name: str) -> str:
    """ASCII-Slug fuer URLs. Nur fuer Notfaelle, Slugs stehen in stocks.yaml."""
    text = name.lower()
    for src, dst in _UMLAUT.items():
        text = text.replace(src, dst)
    out: list[str] = []
    for ch in text:
        if ch.isalnum() and ch.isascii():
            out.append(ch)
        elif ch in " -_/.":
            out.append("-")
    slug = "".join(out)
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug.strip("-")
