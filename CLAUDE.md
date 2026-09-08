# CLAUDE.md

Leitfaden fuer Claude Code in diesem Repo.

Dieses Repo ist eine oeffentliche Info-Website, statisch generiert. Pro Aktie
eine Seite: "Wo am guenstigsten kaufen" plus Kennzahlen, Dividenden und
Management-Aussagen. Monetarisierung ueber Broker-Affiliate und spaeter Ads.
Es ist getrennt vom `Finanzen`-Repo (persoenliches Analyse-Tooling).

## Kommunikationsstil

- Deutsch, direkt, kurze Saetze. Keine Floskeln, kein Sales-Ton.
- Keine Em-Dashes.
- Keine Uebertreibungen ("Rakete", "todsicher").
- Zahlen mit Einheit und Zeitbezug.
- Wenn Daten veraltet oder unsicher sind, das dazuschreiben.

## Grundregeln (nicht verhandelbar)

1. **Keine Kaufempfehlungen.** Die Seite zeigt Fakten und Vergleiche.
   Keine "jetzt kaufen", keine Kursziele ohne Bandbreite und Annahmen.
2. **Nur seriose Quellen** fuer Zahlen: Yahoo Finance (yfinance), Stooq,
   Geschaeftsberichte, EZB, FRED. Keine Foren, keine Influencer als
   Zahlengrundlage.
3. **Urheberrecht bei Nachrichten.** Management-Aussagen erscheinen als
   eigene kurze Zusammenfassung mit Quellenlink, nie als kopierter Text.
4. **Nachvollziehbarkeit vor Eleganz.** Das Kostenmodell in `brokers.py`
   bleibt eine transparente Formel, keine Black-Box.
5. **Ehrlich ueber Grenzen.** Datenlizenz, SEO-Dauer, Gebuehren-Stand offen
   benennen, nicht beschoenigen.

## Architektur

Datenfluss in eine Richtung, strikte Schichtentrennung:

```
fetch (Daten holen) -> data/generated/*.json -> build (rendern) -> dist/
brokers.py (Kostenmodell) wird von build genutzt
```

- `src/fetch.py`: einzige Stelle mit Netzwerkzugriff. yfinance zuerst, bei
  Ausfall Stooq. Fehler klar melden, nicht verschlucken. Schreibt je Aktie
  ein JSON mit `fetched_at` und `source`.
- `src/brokers.py`: rein, keine I/O ausser YAML laden. Kostenformel plus
  Guenstigster-Ermittlung. Jede Formel mit Kommentar zur Quelle.
- `src/build.py`: liest YAML und `data/generated/`, rendert Jinja2-Templates
  nach `dist/`. Baut auch ohne `data/generated/` (dann Platzhalter).
- Kein Business-Code in Templates.

## Entwicklungsbefehle (Windows, PowerShell)

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m src.fetch
python -m src.build
python -m http.server -d dist 8000
pytest
```

## Tests

- Jede Aenderung am Kostenmodell braucht einen Test mit von Hand
  nachrechenbaren Werten in `tests/test_brokers.py`.
- Slug-Erzeugung und YAML-Ladepfade testen, wenn sie sich aendern.

## Daten pflegen

- `data/brokers.yaml`: Gebuehren quartalsweise gegen das Preis- und
  Leistungsverzeichnis des Anbieters pruefen. Feld `fee_basis` mit Stand
  aktualisieren.
- `data/stocks.yaml`: neue Titel mit Ticker (Yahoo-Schreibweise), WKN, ISIN
  und eindeutigem Slug. Slug ist die URL, nicht nachtraeglich aendern ohne
  Redirect.

## Was offen ist, bevor die Seite live geht

Siehe README, Abschnitt "Vor einer Veroeffentlichung offen". Kurz: Gebuehren
pruefen, Datenlizenz klaeren, Impressum fuellen, Affiliate-Programme
aufnehmen.
