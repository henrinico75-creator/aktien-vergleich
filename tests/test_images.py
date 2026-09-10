"""Tests fuer src/images.py. Kein Netzwerk, kein API-Schluessel noetig."""
import pytest

from src import images


def test_ohne_schluessel_kein_fehler(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    assert images.main([]) == 0
    assert images.main(["logo"]) == 0
    assert images.generate("egal") is None


def test_modell_ueberschreibbar(monkeypatch):
    monkeypatch.delenv("GEMINI_IMAGE_MODEL", raising=False)
    assert images._model() == images.DEFAULT_MODEL
    monkeypatch.setenv("GEMINI_IMAGE_MODEL", "gemini-3-pro-image")
    assert images._model() == "gemini-3-pro-image"


def test_logo_jobs():
    jobs = images.logo_jobs()
    assert len(jobs) == 3
    for name, prompt, ar in jobs:
        assert name.endswith(".png")
        assert "Aktien-Kosten" in prompt or "aktien-kosten" in prompt
        assert "#0e9f6e" in prompt  # Marken-Akzent steckt drin
        assert ar in ("1:1", "16:9", "9:16")


def test_marketing_jobs_vorhandener_ordner():
    jobs = images.marketing_jobs("2026-09-09")
    assert [n for n, _, _ in jobs] == ["instagram-1x1.png", "story-9x16.png"]
    assert all("do not invent" in p.lower() or "do not add" in p.lower() for _, p, _ in jobs)


def test_marketing_jobs_fehlender_ordner():
    with pytest.raises(SystemExit):
        images.marketing_jobs("1999-01-01")
