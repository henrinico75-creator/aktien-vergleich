"""Statischer Seitengenerator. Liest YAML und data/generated/, rendert nach dist/.

Aufruf:  python -m src.build
Baut auch ohne data/generated/ (dann Platzhalter statt echter Zahlen).

Verlinkung:
    cfg["path_prefix"]  Pfad-Prefix fuer Links und Assets in den Seiten.
                        Lokal leer, auf GitHub Project Pages z. B. /aktien-vergleich.
                        Override ueber Umgebungsvariable SITE_PATH_PREFIX.
    cfg["base_url"]     vollstaendige URL (Origin + Pfad) fuer sitemap und canonical.
                        Override ueber SITE_BASE_URL.
"""
from __future__ import annotations

import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape

try:
    import markdown as _md
except ImportError:  # markdown ist optional, Fallback weiter unten
    _md = None

from src.brokers import Broker, load_brokers, order_cost, rank_brokers
from src.etfs import Etf, load_etfs

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
GEN_DIR = DATA_DIR / "generated"
TPL_DIR = ROOT / "templates"
STATIC_DIR = ROOT / "static"
CONTENT_DIR = ROOT / "content"
DIST = ROOT / "dist"


def load_config() -> dict:
    cfg = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
    # Leere Umgebungsvariablen zaehlen als "nicht gesetzt". GitHub Actions
    # setzt nicht definierte Repository-Variablen als leeren String, ein
    # os.environ.get(name, default) wuerde dann "" statt des Defaults liefern.
    cfg["base_url"] = (os.environ.get("SITE_BASE_URL") or cfg["base_url"]).rstrip("/")
    prefix = (os.environ.get("SITE_PATH_PREFIX") or cfg.get("path_prefix", "")).strip()
    cfg["path_prefix"] = ("/" + prefix.strip("/")) if prefix.strip("/") else ""
    return cfg


def load_stocks() -> list[dict]:
    return yaml.safe_load((DATA_DIR / "stocks.yaml").read_text(encoding="utf-8"))["stocks"]


def load_generated(slug: str, prefix: str = "") -> dict | None:
    p = GEN_DIR / f"{prefix}{slug}.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


# ---------------------------------------------------------------- Formatierung

def _de(value: float, digits: int) -> str:
    """Deutsche Zahlenschreibweise ohne locale: 1234567.89 -> 1.234.567,89."""
    s = f"{value:,.{digits}f}"
    return s.translate(str.maketrans({",": ".", ".": ","}))


def fmt_num(value, digits: int = 2) -> str:
    return "n/a" if value is None else _de(float(value), digits)


def fmt_eur(value, digits: int = 2) -> str:
    return "n/a" if value is None else _de(float(value), digits) + " EUR"


def fmt_pct(value, digits: int = 2) -> str:
    return "n/a" if value is None else _de(float(value), digits) + " %"


def fmt_mktcap(value) -> str:
    if value is None:
        return "n/a"
    value = float(value)
    for unit, factor in (("Bio.", 1e12), ("Mrd.", 1e9), ("Mio.", 1e6)):
        if abs(value) >= factor:
            return f"{_de(value / factor, 2)} {unit}"
    return _de(value, 0)


def _div_yield_pct(raw):
    """Dividendenrendite in Prozent.

    Aktuelles yfinance liefert `dividendYield` bereits als Prozentwert
    (z. B. 3.82 fuer 3,82 %), nicht als Bruch. Daher nur durchreichen. Wenn
    Yahoo das Format wieder aendert, hier anpassen und Tests nachziehen.
    """
    return None if raw is None else float(raw)


# ---------------------------------------------------------------- Build

def _env() -> Environment:
    env = Environment(
        loader=FileSystemLoader(str(TPL_DIR)),
        autoescape=select_autoescape(["html", "xml"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters["num"] = fmt_num
    env.filters["eur"] = fmt_eur
    env.filters["pct"] = fmt_pct
    env.filters["mktcap"] = fmt_mktcap
    return env


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _cost_matrix(brokers: list[Broker], sizes: list[int], kind: str = "einmalkauf"):
    return [{"size": s, "rows": rank_brokers(brokers, s, kind)} for s in sizes]


def _js_json(payload) -> str:
    """JSON fuer die direkte Einbettung in einen <script>-Block.
    < > & als Unicode-Escapes, damit Textinhalte den Block nicht beenden.
    """
    text = json.dumps(payload, ensure_ascii=False)
    return text.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")


def _search_index_json(cfg: dict, stocks: list[dict], etfs: list[Etf]) -> str:
    """Kompakter Suchindex fuer das Kopf-Suchfeld auf jeder Seite.
    q ist der klein geschriebene Suchtext (Name, WKN, ISIN, Branche/Index).
    """
    p = cfg["path_prefix"]
    items = [
        {
            "n": s["name"], "k": "Aktie", "u": f"{p}/aktie/{s['slug']}/",
            "q": f"{s['name']} {s['wkn']} {s['isin']} {s['sector']}".lower(),
        }
        for s in stocks
    ]
    items += [
        {
            "n": e.name, "k": "ETF", "u": f"{p}/etf/{e.slug}/",
            "q": f"{e.name} {e.wkn} {e.isin} {e.index}".lower(),
        }
        for e in etfs
    ]
    return _js_json(items)


def _write_sitemap(
    cfg: dict, stocks: list[dict], etfs: list[Etf], brokers: list[Broker]
) -> None:
    base = cfg["base_url"]
    urls = [f"{base}/"]
    urls += [f"{base}/aktie/{s['slug']}/" for s in stocks]
    urls += [f"{base}/etf/{e.slug}/" for e in etfs]
    urls += [f"{base}/broker/{b.id}/" for b in brokers]
    urls += [f"{base}/{p}/" for p in ("impressum", "datenschutz", "werbehinweis")]
    body = "\n".join(f"  <url><loc>{u}</loc></url>" for u in urls)
    _write(
        DIST / "sitemap.xml",
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{body}\n</urlset>\n",
    )


def build() -> None:
    cfg = load_config()
    brokers = load_brokers()
    stocks = load_stocks()
    etfs = load_etfs()
    sizes = cfg.get("default_order_sizes", [250, 1000, 5000])
    env = _env()
    env.globals["search_index_json"] = _search_index_json(cfg, stocks, etfs)
    built_at = datetime.now(timezone.utc).strftime("%d.%m.%Y %H:%M UTC")

    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir(parents=True)
    if STATIC_DIR.exists():
        shutil.copytree(STATIC_DIR, DIST / "static")
    _write(DIST / ".nojekyll", "")

    matrix = _cost_matrix(brokers, sizes)
    leaderboard = [{"size": s, "rows": rank_brokers(brokers, s)[:3]} for s in sizes]

    stock_tpl = env.get_template("stock.html")
    overview = []
    for s in stocks:
        gen = load_generated(s["slug"]) or {}
        gen["dividend_yield_pct"] = _div_yield_pct(gen.get("dividend_yield"))
        has_data = bool(gen) and gen.get("data_status") not in (None, "fehlgeschlagen")
        overview.append({"stock": s, "data": gen, "has_data": has_data})
        _write(
            DIST / "aktie" / s["slug"] / "index.html",
            stock_tpl.render(
                cfg=cfg,
                built_at=built_at,
                stock=s,
                data=gen,
                has_data=has_data,
                brokers=brokers,
                brokers_json=_brokers_json(brokers),
                matrix=matrix,
                sizes=sizes,
            ),
        )

    etf_tpl = env.get_template("etf.html")
    etf_overview = []
    for e in etfs:
        gen = load_generated(e.slug, prefix="etf-") or {}
        gen["dividend_yield_pct"] = _div_yield_pct(gen.get("dividend_yield"))
        has_data = bool(gen) and gen.get("data_status") not in (None, "fehlgeschlagen")
        etf_overview.append({"etf": e, "data": gen, "has_data": has_data})
        _write(
            DIST / "etf" / e.slug / "index.html",
            etf_tpl.render(
                cfg=cfg,
                built_at=built_at,
                etf=e,
                data=gen,
                has_data=has_data,
                brokers=brokers,
                brokers_json=_brokers_json(brokers),
                matrix=matrix,
                sizes=sizes,
            ),
        )

    _write(
        DIST / "index.html",
        env.get_template("index.html").render(
            cfg=cfg,
            built_at=built_at,
            overview=overview,
            etf_overview=etf_overview,
            brokers=brokers,
            leaderboard=leaderboard,
        ),
    )

    broker_tpl = env.get_template("broker.html")
    for b in brokers:
        _write(
            DIST / "broker" / b.id / "index.html",
            broker_tpl.render(
                cfg=cfg,
                built_at=built_at,
                broker=b,
                sample=[(s, order_cost(b, s)) for s in sizes],
            ),
        )

    legal_tpl = env.get_template("legal.html")
    for name, title in (
        ("impressum", "Impressum"),
        ("datenschutz", "Datenschutzerklaerung"),
        ("werbehinweis", "Werbehinweis"),
    ):
        md_path = CONTENT_DIR / f"{name}.md"
        raw = md_path.read_text(encoding="utf-8") if md_path.exists() else ""
        if _md and raw:
            html = _md.markdown(raw, extensions=["extra"])
        else:
            html = "<pre>" + raw.replace("<", "&lt;") + "</pre>"
        _write(
            DIST / name / "index.html",
            legal_tpl.render(
                cfg=cfg, built_at=built_at, title=title, slug=name, body=html
            ),
        )

    _write_sitemap(cfg, stocks, etfs, brokers)
    _write(
        DIST / "robots.txt",
        f"User-agent: *\nAllow: /\nSitemap: {cfg['base_url']}/sitemap.xml\n",
    )
    print(
        f"gebaut: {len(stocks)} Aktienseiten, {len(etfs)} ETF-Seiten, "
        f"{len(brokers)} Brokerseiten -> {DIST}"
    )


def _brokers_json(brokers: list[Broker]) -> str:
    """Broker-Kostenmodell fuer den clientseitigen Rechner auf den Aktienseiten."""
    payload = [
        {
            "name": b.name,
            "venue": b.venue,
            "order_fixed": b.order_fixed,
            "order_pct": b.order_pct,
            "order_min": b.order_min,
            "order_max": b.order_max,
            "free_above": b.free_above,
            "subscription_eur": b.subscription_eur,
            "affiliate_url": b.affiliate_url,
            "note": b.note,
        }
        for b in brokers
    ]
    text = json.dumps(payload, ensure_ascii=False)
    # Das Ergebnis wird per |safe direkt in einen <script>-Block geschrieben.
    # < > & als Unicode-Escapes, damit z. B. ein "</script>" in einem Feld den
    # Block nicht vorzeitig beendet. JSON-Semantik bleibt unveraendert.
    return (
        text.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    )


if __name__ == "__main__":
    build()
