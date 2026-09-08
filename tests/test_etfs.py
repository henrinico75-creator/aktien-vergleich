"""Tests fuer das Laden der ETF-Stammdaten."""
from src.etfs import Etf, load_etfs


def test_load_etfs_liest_die_echte_datei():
    etfs = load_etfs()
    assert len(etfs) >= 10
    slugs = [e.slug for e in etfs]
    assert len(slugs) == len(set(slugs)), "ETF-Slugs muessen eindeutig sein"
    for e in etfs:
        assert isinstance(e, Etf)
        assert e.name and e.ticker and e.isin and e.index
        assert 0 < e.ter < 3, f"TER unplausibel bei {e.slug}: {e.ter}"
        assert e.distribution in {"thesaurierend", "ausschüttend"}


def test_etf_und_aktien_slugs_kollidieren_nicht():
    from src.fetch import load_stocks

    etf_slugs = {e.slug for e in load_etfs()}
    stock_slugs = {s["slug"] for s in load_stocks()}
    assert not (etf_slugs & stock_slugs)
