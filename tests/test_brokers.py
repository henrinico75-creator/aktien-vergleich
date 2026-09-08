"""Tests fuer das Kostenmodell. Alle Werte sind von Hand nachrechenbar."""
import pytest

from src.brokers import Broker, load_brokers, order_cost, rank_brokers, slugify


def mk(**kw) -> Broker:
    base = dict(
        id="x", name="X", venue="v",
        order_fixed=0.0, order_pct=0.0, order_min=0.0, order_max=None,
        free_above=None, savings_plan_fixed=0.0, savings_plan_pct=0.0,
        subscription_eur=0.0, affiliate_url=None, note="", fee_basis="",
    )
    base.update(kw)
    return Broker(**base)


# ---------------------------------------------------------------- order_cost

def test_feste_gebuehr_ist_volumenunabhaengig():
    b = mk(order_fixed=1.00)
    assert order_cost(b, 100) == 1.00
    assert order_cost(b, 10_000) == 1.00


def test_prozentualer_anteil_plus_fix():
    # 4,90 + 0,25 % von 1.000 = 4,90 + 2,50 = 7,40
    b = mk(order_fixed=4.90, order_pct=0.0025)
    assert order_cost(b, 1_000) == 7.40


def test_deckel_greift():
    # 4,90 + 0,25 % von 100.000 = 254,90, gedeckelt bei 69,90
    b = mk(order_fixed=4.90, order_pct=0.0025, order_max=69.90)
    assert order_cost(b, 100_000) == 69.90


def test_mindestgebuehr_greift():
    # 4,95 + 0,25 % von 1.000 = 7,45, angehoben auf 9,95
    b = mk(order_fixed=4.95, order_pct=0.0025, order_min=9.95)
    assert order_cost(b, 1_000) == 9.95
    # 4,95 + 0,25 % von 5.000 = 17,45, ueber der Mindestgebuehr
    assert order_cost(b, 5_000) == 17.45


def test_free_above_setzt_kosten_auf_null():
    b = mk(order_fixed=1.00, free_above=500)
    assert order_cost(b, 499) == 1.00
    assert order_cost(b, 500) == 0.0
    assert order_cost(b, 750) == 0.0


def test_sparplan_nutzt_eigene_felder():
    b = mk(order_fixed=5.90, savings_plan_fixed=0.0)
    assert order_cost(b, 1_000, kind="sparplan") == 0.0
    b2 = mk(savings_plan_fixed=0.0, savings_plan_pct=0.015)
    assert order_cost(b2, 200, kind="sparplan") == 3.00


def test_negatives_volumen_wirft_fehler():
    with pytest.raises(ValueError):
        order_cost(mk(), -1)


# ---------------------------------------------------------------- rank_brokers

def test_ranking_sortiert_aufsteigend_und_markiert_guenstigsten():
    teuer = mk(name="Teuer", order_fixed=5.90)
    mittel = mk(name="Mittel", order_fixed=1.00)
    guenstig = mk(name="Guenstig", order_fixed=0.0)
    ranked = rank_brokers([teuer, mittel, guenstig], 1_000)
    assert [q.broker.name for q in ranked] == ["Guenstig", "Mittel", "Teuer"]
    assert ranked[0].is_cheapest is True
    assert ranked[1].is_cheapest is False


def test_ranking_gleichstand_mehrere_guenstigste_alphabetisch():
    a = mk(name="Bravo", order_fixed=0.0)
    b = mk(name="Alpha", order_fixed=0.0)
    c = mk(name="Charlie", order_fixed=1.0)
    ranked = rank_brokers([a, b, c], 1_000)
    assert [q.broker.name for q in ranked] == ["Alpha", "Bravo", "Charlie"]
    assert ranked[0].is_cheapest and ranked[1].is_cheapest
    assert not ranked[2].is_cheapest


def test_kostenquote_ist_kosten_durch_volumen():
    b = mk(order_fixed=10.0)
    q = rank_brokers([b], 1_000)[0]
    assert q.cost_ratio == pytest.approx(0.01)


# ---------------------------------------------------------------- slugify

@pytest.mark.parametrize(
    "name, expected",
    [
        ("Volkswagen Vorzuege", "volkswagen-vorzuege"),
        ("Coca-Cola", "coca-cola"),
        ("Johnson & Johnson", "johnson-johnson"),
        ("Mercedes-Benz Group", "mercedes-benz-group"),
        ("SAP", "sap"),
    ],
)
def test_slugify(name, expected):
    assert slugify(name) == expected


# ---------------------------------------------------------------- YAML laden

def test_load_brokers_liest_die_echte_datei():
    brokers = load_brokers()
    assert len(brokers) >= 10
    ids = {b.id for b in brokers}
    assert "trade-republic" in ids
    for b in brokers:
        assert b.name and b.venue and b.fee_basis
        assert b.order_fixed >= 0
