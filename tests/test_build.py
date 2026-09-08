"""Tests fuer die Formatierungshelfer im Seitengenerator."""
import pytest

from src.build import _de, _div_yield_pct, fmt_eur, fmt_mktcap, fmt_num, fmt_pct


def test_de_zahlenschreibweise():
    assert _de(1_234_567.89, 2) == "1.234.567,89"
    assert _de(7.4, 2) == "7,40"
    assert _de(1000, 0) == "1.000"


def test_fmt_helfer_mit_none():
    assert fmt_num(None) == "n/a"
    assert fmt_eur(None) == "n/a"
    assert fmt_pct(None) == "n/a"
    assert fmt_mktcap(None) == "n/a"


def test_fmt_eur_und_pct():
    assert fmt_eur(7.4) == "7,40 EUR"
    assert fmt_pct(0.25) == "0,25 %"


def test_fmt_mktcap_einheiten():
    assert fmt_mktcap(3.45e12) == "3,45 Bio."
    assert fmt_mktcap(1.33e11) == "133,00 Mrd."
    assert fmt_mktcap(4.7e6) == "4,70 Mio."


@pytest.mark.parametrize(
    "raw, expected",
    [(None, None), (3.82, 3.82), (0.34, 0.34), (5, 5.0)],
)
def test_div_yield_pct_reicht_prozentwert_durch(raw, expected):
    result = _div_yield_pct(raw)
    if expected is None:
        assert result is None
    else:
        assert result == pytest.approx(expected)
