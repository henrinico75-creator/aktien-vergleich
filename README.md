# aktien-vergleich

Statisch generierte Info-Website: pro Aktie eine Seite mit der Frage "Wo kaufe ich
diese Aktie am guenstigsten?" plus Kennzahlen, Dividendendaten und aktuellen
Aussagen des Managements. Einnahmen ueber Broker-Affiliate und spaeter Display-Ads.

Kein Bestandteil des `Finanzen`-Repos. Anderes Ziel, anderer Rechtsrahmen.

## Status

Prototyp, live auf GitHub Pages. Der Seitengenerator laeuft, Broker-Gebuehren
und der Aktien- und ETF-Datensatz sind Startwerte und noch nicht geprueft.

## Stack

- Python 3.12, statischer Generator (Jinja2), kein Framework
- `yfinance` fuer Kurse und Kennzahlen, Stooq als Fallback
- Hosting: GitHub Pages (kostenlos), Alternative Cloudflare Pages
- Automatik: GitHub Actions, taeglicher Cron baut die Seite neu

## Aufbau

```
data/
  brokers.yaml      Gebuehrenmodelle je Broker (Hand, quartalsweise pruefen)
  stocks.yaml       beobachtete Aktien (Ticker, WKN, ISIN, Slug) -- Slugs bleiben ASCII
  etfs.yaml         beobachtete ETFs (TER, Replikation, Ertragsverwendung, Domizil)
  generated/        Ausgabe von src/fetch.py, nicht in Git
src/
  brokers.py        Kostenmodell und Guenstigster-Berechnung
  etfs.py           ETF-Stammdaten laden
  fetch.py          Datenbeschaffung yfinance -> Stooq, schreibt data/generated/*.json
                    (ETFs als etf-<slug>.json, ohne Meldungen)
  summarize.py      optional: eigene Kurzzusammenfassungen je Meldung,
                    nur mit ANTHROPIC_API_KEY, sonst no-op
  build.py          rendert templates/ nach dist/
templates/          base, index, stock, etf, broker, legal, _calculator,
                    _costtable (Jinja-Makro fuer die Kostentabelle je Volumen)
content/            Impressum, Datenschutz, Werbehinweis (Markdown)
scripts/umlaut_fix.py   ASCII-Umschrift -> echte Umlaute im sichtbaren Text
static/style.css    Design, ein Stylesheet, drei Theme-Zustaende (System/hell/dunkel)
static/app.js       Progressive Enhancement: Theme-Umschalter, Suche/Filter/
                    Sortierung der Listen, Ordervolumen-Umschalter im Ergebnis-
                    Panel. Ohne JavaScript bleibt jede Seite voll nutzbar.
dist/               generierte Website, nicht in Git
.github/workflows/  build-deploy.yml
```

## Lokal bauen (Windows, PowerShell)

Voraussetzung: Python 3.12. Falls nicht vorhanden:

```powershell
winget install --id Python.Python.3.12 -e --source winget
```

Danach:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m src.fetch      # holt Kurse und Kennzahlen nach data/generated/
python -m src.build      # baut die Website nach dist/
python -m http.server -d dist 8000   # http://localhost:8000
```

Ohne `fetch` baut `build` trotzdem, dann mit Platzhaltern statt echten Zahlen.

## Tests

```powershell
pytest                       # alle Tests
pytest tests/test_brokers.py  # Kostenmodell
```

## Vor einer Veroeffentlichung offen (nicht startklar)

1. **Broker-Gebuehren pruefen.** Werte in `data/brokers.yaml` sind grobe
   Startwerte mit Stand-Vermerk. Jede Zeile gegen das Preis- und
   Leistungsverzeichnis des Anbieters abgleichen. Danach quartalsweise.
2. **Datenlizenz klaeren.** Die Yahoo-Nutzungsbedingungen beschraenken die
   kommerzielle Weiterverbreitung von Kursdaten. Vor echtem Launch entweder
   eine Datenquelle mit Weiterverbreitungsrecht lizenzieren oder die Anzeige
   auf abgeleitete bzw. aggregierte Werte plus Quellenlink beschraenken.
3. **Impressum.** `content/impressum.md` braucht echten Namen, Anschrift und
   Kontakt. Ohne vollstaendiges Impressum kein Betrieb in Deutschland.
4. **Management-Aussagen.** Immer eigene, kurze Zusammenfassung mit
   Quellenlink. Nie kopierter Artikeltext (Urheberrecht).
5. **Affiliate-Links.** Erst nach Aufnahme in ein Partnerprogramm
   (financeAds, Awin) die echten Links in `data/brokers.yaml` eintragen.
   Werbekennzeichnung ist Pflicht, siehe `content/werbehinweis.md`.
6. **Reichweite.** Finanzthemen ranken bei Google langsam. Realistisch 3 bis
   6 Monate bis nennenswerter Traffic.

## Kein Anlageberater

Die Website liefert Fakten und Vergleiche, keine Kaufempfehlungen. Keine
Kursziele ohne Bandbreite, keine Order- oder Zahlungsfunktion.
