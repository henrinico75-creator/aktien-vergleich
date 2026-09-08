"""ETF-Stammdaten laden. Rein, nur YAML lesen.

Die Vergleichsdaten (TER, Replikation, Ertragsverwendung, Domizil) sind
handgepflegt in data/etfs.yaml. Kurse holt src/fetch.py ueber den Ticker.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


@dataclass(frozen=True)
class Etf:
    slug: str
    name: str
    ticker: str
    wkn: str
    isin: str
    currency: str
    ter: float
    index: str
    replication: str
    distribution: str
    domicile: str
    note: str


def load_etfs(path: Path | None = None) -> list[Etf]:
    src = path or (DATA_DIR / "etfs.yaml")
    raw = yaml.safe_load(src.read_text(encoding="utf-8"))
    return [Etf(**entry) for entry in raw["etfs"]]
