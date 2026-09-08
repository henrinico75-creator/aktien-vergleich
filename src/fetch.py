"""Datenbeschaffung: Kurse, Kennzahlen, Dividenden, Meldungen.

Einzige Stelle mit Netzwerkzugriff. Reihenfolge: yfinance zuerst, bei Ausfall
Stooq (nur Kurs). Fehler gehen auf stderr und werden im JSON als data_status
vermerkt, nicht verschluckt.

Aufruf:
    python -m src.fetch                 alle Titel aus data/stocks.yaml
    python -m src.fetch --only apple sap  nur diese Slugs
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import yaml

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
OUT_DIR = DATA_DIR / "generated"


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_stocks(path: Path | None = None) -> list[dict]:
    src = path or (DATA_DIR / "stocks.yaml")
    return yaml.safe_load(src.read_text(encoding="utf-8"))["stocks"]


def _safe(fn: Callable[[], Any]) -> Any:
    """Ruft fn auf, gibt None bei Fehler oder NaN zurueck."""
    try:
        v = fn()
    except Exception:  # noqa: BLE001
        return None
    if v is None:
        return None
    if isinstance(v, float) and v != v:  # NaN
        return None
    return v


def _news_date(raw: Any) -> str | None:
    """Normalisiert das Meldungsdatum auf YYYY-MM-DD.

    yfinance liefert je nach Antwortformat entweder einen ISO-String
    (content.pubDate) oder einen Unix-Zeitstempel (providerPublishTime).
    Ohne Normalisierung landet der rohe Zeitstempel als Datum im Template.
    """
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        try:
            return datetime.fromtimestamp(float(raw), timezone.utc).strftime("%Y-%m-%d")
        except (OverflowError, OSError, ValueError):
            return None
    text = str(raw).strip()
    if not text:
        return None
    if text.isdigit():
        try:
            return datetime.fromtimestamp(int(text), timezone.utc).strftime("%Y-%m-%d")
        except (OverflowError, OSError, ValueError):
            return None
    return text[:10]


def _stooq_symbol(ticker: str) -> str:
    if ticker.endswith(".DE"):
        return ticker[:-3].lower() + ".de"
    return ticker.lower().replace(".", "-") + ".us"


def fetch_from_stooq(ticker: str) -> dict:
    """Nur Schlusskurs, als Fallback. CSV-Endpunkt von Stooq."""
    import requests

    sym = _stooq_symbol(ticker)
    url = f"https://stooq.com/q/l/?s={sym}&f=sd2t2ohlcv&h&e=csv"
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    lines = resp.text.strip().splitlines()
    if len(lines) < 2:
        raise RuntimeError(f"Stooq ohne Daten fuer {sym}")
    row = dict(zip(lines[0].split(","), lines[1].split(",")))
    close = row.get("Close")
    if not close or close in {"N/D", ""}:
        raise RuntimeError(f"Stooq ohne Schlusskurs fuer {sym}")
    return {"price": float(close), "price_date": row.get("Date"), "source": "stooq"}


_NAME_STOPWORDS = {
    "group", "holding", "holdings", "vorzuege", "vz", "ag", "se", "nv", "plc",
    "inc", "co", "corp", "the", "und", "and",
}


def _name_keywords(name: str) -> list[str]:
    """Kernbegriffe aus dem Firmennamen fuer den Relevanzfilter der Meldungen."""
    words = name.lower().replace("&", " ").replace("-", " ").replace("(", " ").replace(")", " ").split()
    kw = [w for w in words if len(w) >= 3 and w not in _NAME_STOPWORDS]
    return kw or [name.lower()]


def fetch_from_yfinance(ticker: str, name: str = "") -> dict:
    import yfinance as yf

    t = yf.Ticker(ticker)
    out: dict = {"source": "yfinance"}
    keywords = _name_keywords(name) if name else []

    fi = _safe(lambda: t.fast_info)
    if fi is not None:
        out["price"] = _safe(lambda: float(fi["lastPrice"]))
        out["market_cap"] = _safe(lambda: float(fi["marketCap"]))
        out["currency"] = _safe(lambda: str(fi["currency"]))

    info: dict = {}
    try:
        info = t.get_info() or {}
    except Exception as exc:  # noqa: BLE001
        print(f"  info nicht verfuegbar ({ticker}): {exc}", file=sys.stderr)

    out["pe_trailing"] = _safe(lambda: float(info["trailingPE"]))
    out["pe_forward"] = _safe(lambda: float(info["forwardPE"]))
    out["price_to_book"] = _safe(lambda: float(info["priceToBook"]))
    out["dividend_yield"] = _safe(lambda: float(info["dividendYield"]))
    out["payout_ratio"] = _safe(lambda: float(info["payoutRatio"]))
    out["long_name"] = info.get("longName") or info.get("shortName")
    if out.get("price") is None:
        out["price"] = _safe(lambda: float(info["currentPrice"]))
    if out.get("market_cap") is None:
        out["market_cap"] = _safe(lambda: float(info["marketCap"]))

    # Dividenden: letzte bis zu 6 Zahlungen
    try:
        div = t.dividends
        if div is not None and len(div) > 0:
            out["dividends"] = [
                {"date": d.strftime("%Y-%m-%d"), "amount": round(float(v), 4)}
                for d, v in div.tail(6).items()
            ]
    except Exception as exc:  # noqa: BLE001
        print(f"  dividends nicht verfuegbar ({ticker}): {exc}", file=sys.stderr)

    # Meldungen: nur Titel, Quelle, Link, Datum. Kein Fliesstext (Urheberrecht).
    # Yahoo liefert zu einem Ticker viel Randrauschen (Makro, andere Firmen).
    # Daher nur Meldungen behalten, deren Titel einen Kernbegriff des
    # Firmennamens enthaelt. Ohne Treffer bleibt die Meldungsliste leer.
    try:
        raw_news = _safe(lambda: t.news) or []
        items = []
        seen_titles: set[str] = set()
        for entry in raw_news[:30]:
            content = entry.get("content", entry)
            title = content.get("title") or entry.get("title")
            if not title or title.lower() in seen_titles:
                continue
            if keywords and not any(kw in title.lower() for kw in keywords):
                continue
            seen_titles.add(title.lower())
            link = (
                (content.get("canonicalUrl") or {}).get("url")
                or (content.get("clickThroughUrl") or {}).get("url")
                or entry.get("link")
            )
            provider = (content.get("provider") or {}).get("displayName") or entry.get(
                "publisher"
            )
            published = _news_date(
                content.get("pubDate") or entry.get("providerPublishTime")
            )
            items.append(
                {"title": title, "url": link, "provider": provider, "published": published}
            )
            if len(items) >= 5:
                break
        if items:
            out["news"] = items
    except Exception as exc:  # noqa: BLE001
        print(f"  news nicht verfuegbar ({ticker}): {exc}", file=sys.stderr)

    if out.get("price") is None:
        raise RuntimeError("yfinance ohne Kurs")
    return out


def fetch_stock(stock: dict) -> dict:
    ticker = stock["ticker"]
    record: dict = {
        "slug": stock["slug"],
        "name": stock["name"],
        "ticker": ticker,
        "wkn": stock["wkn"],
        "isin": stock["isin"],
        "fetched_at": _now_iso(),
        "data_status": "ok",
    }
    try:
        record.update(fetch_from_yfinance(ticker, stock["name"]))
    except Exception as exc:  # noqa: BLE001
        print(f"{ticker}: yfinance fehlgeschlagen ({exc}), versuche Stooq", file=sys.stderr)
        try:
            record.update(fetch_from_stooq(ticker))
            record["data_status"] = "nur_kurs_stooq"
        except Exception as exc2:  # noqa: BLE001
            print(f"{ticker}: auch Stooq fehlgeschlagen ({exc2})", file=sys.stderr)
            record["data_status"] = "fehlgeschlagen"
    return record


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Kurse und Kennzahlen holen")
    parser.add_argument("--only", nargs="*", default=None, help="nur diese Slugs")
    args = parser.parse_args(argv)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stocks = load_stocks()
    if args.only:
        wanted = set(args.only)
        stocks = [s for s in stocks if s["slug"] in wanted]

    failed: list[str] = []
    for stock in stocks:
        print(f"hole {stock['ticker']} ...", file=sys.stderr)
        rec = fetch_stock(stock)
        (OUT_DIR / f"{stock['slug']}.json").write_text(
            json.dumps(rec, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        if rec["data_status"] == "fehlgeschlagen":
            failed.append(stock["slug"])

    print(f"fertig: {len(stocks)} Titel, {len(failed)} fehlgeschlagen", file=sys.stderr)
    if failed:
        print("fehlgeschlagen: " + ", ".join(failed), file=sys.stderr)
    # Kein harter Exit-Fehler: der Build soll auch mit Luecken laufen.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
