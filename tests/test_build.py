"""Tests fuer Formatierung, Konfiguration und die Script-Einbettung im Build.

Alle Werte sind von Hand nachrechenbar. Netzwerk wird nicht benoetigt.
"""
from src.brokers import Broker
from src.build import (
    _brokers_json,
    fmt_eur,
    fmt_mktcap,
    fmt_num,
    fmt_pct,
    load_config,
)
from src.fetch import _name_keywords, _news_date


def mk(**kw) -> Broker:
    base = dict(
        id="x", name="X", venue="v",
        order_fixed=0.0, order_pct=0.0, order_min=0.0, order_max=None,
        free_above=None, savings_plan_fixed=0.0, savings_plan_pct=0.0,
        subscription_eur=0.0, affiliate_url=None, note="", fee_basis="",
    )
    base.update(kw)
    return Broker(**base)


# ---------------------------------------------------------------- Formatierung

def test_deutsche_zahlenschreibweise():
    assert fmt_num(1234567.89) == "1.234.567,89"
    assert fmt_num(1000, 0) == "1.000"
    assert fmt_eur(3.9) == "3,90 EUR"
    assert fmt_pct(0.25) == "0,25 %"


def test_none_wird_zu_na():
    assert fmt_num(None) == "n/a"
    assert fmt_eur(None) == "n/a"
    assert fmt_mktcap(None) == "n/a"


def test_marktkapitalisierung_skaliert():
    assert fmt_mktcap(2.5e12) == "2,50 Bio."
    assert fmt_mktcap(3.4e9) == "3,40 Mrd."
    assert fmt_mktcap(7.0e6) == "7,00 Mio."


# ---------------------------------------------------------------- Konfiguration

def test_leere_env_variable_faellt_auf_config_zurueck(monkeypatch):
    # GitHub Actions setzt nicht definierte Repository-Variablen als leeren
    # String. Der Build darf daraus keine leere base_url machen.
    monkeypatch.setenv("SITE_BASE_URL", "")
    monkeypatch.setenv("SITE_PATH_PREFIX", "")
    cfg = load_config()
    assert cfg["base_url"].startswith("http")


def test_gesetzte_env_variable_gewinnt(monkeypatch):
    monkeypatch.setenv("SITE_BASE_URL", "https://example.org/seite/")
    monkeypatch.setenv("SITE_PATH_PREFIX", "seite")
    cfg = load_config()
    assert cfg["base_url"] == "https://example.org/seite"
    assert cfg["path_prefix"] == "/seite"


# ---------------------------------------------------------------- Script-Daten

def test_brokers_json_escaped_spitze_klammern():
    # Das JSON landet per |safe in einem <script>-Block. Ein "</script>" in
    # einem Textfeld darf den Block nicht beenden.
    payload = _brokers_json([mk(note="Ende </script> Mitte & Rest")])
    assert "<" not in payload
    assert ">" not in payload
    assert "\\u003c" in payload


# ---------------------------------------------------------------- Meldungsdatum

def test_news_datum_normalisiert_unix_zeitstempel():
    assert _news_date(1735689600) == "2025-01-01"
    assert _news_date("1735689600") == "2025-01-01"


def test_news_datum_kuerzt_iso_string():
    assert _news_date("2026-03-04T10:00:00Z") == "2026-03-04"


def test_news_datum_ohne_wert():
    assert _news_date(None) is None
    assert _news_date("") is None


# ---------------------------------------------------------------- Namensfilter

def test_name_keywords_wirft_rechtsformen_und_kurze_woerter_raus():
    assert _name_keywords("Mercedes-Benz Group") == ["mercedes", "benz"]
    assert _name_keywords("Johnson & Johnson") == ["johnson", "johnson"]
    assert _name_keywords("Volkswagen Vorzuege") == ["volkswagen"]


def test_name_keywords_faellt_auf_ganzen_namen_zurueck():
    assert _name_keywords("SAP") == ["sap"]
