# aktien-vergleich

Statisch generierte Info-Website: pro Aktie eine Seite mit der Frage "Wo kaufe ich
diese Aktie am guenstigsten?" plus Kennzahlen, Dividendendaten und aktuellen
Aussagen des Managements. Einnahmen ueber Broker-Affiliate und spaeter Display-Ads.

Kein Bestandteil des `Finanzen`-Repos. Anderes Ziel, anderer Rechtsrahmen.

## Status

Prototyp, gehostet auf Vercel. Der Seitengenerator laeuft, Broker-Gebuehren
und der Aktien- und ETF-Datensatz sind Startwerte und noch nicht geprueft.

## Stack

- Python 3.12, statischer Generator (Jinja2), kein Framework
- `yfinance` fuer Kurse und Kennzahlen, Stooq als Fallback
- Hosting: Vercel (Build aus `vercel.json`, Deploy bei Push auf `main`)
- CI: GitHub Actions `ci.yml` (Tests + Probebuild), `refresh.yml` stoesst
  taeglich einen Vercel Deploy Hook an (Secret `VERCEL_DEPLOY_HOOK`)

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
  images.py         optional: Bilder ueber Gemini "Nano Banana" (Logo,
                    Marketing-Grafiken), nur mit GEMINI_API_KEY, sonst no-op.
                    Laeuft nicht im Build, Ergebnisse werden committet.
  build.py          rendert templates/ nach dist/
templates/          base, index, stock, etf, broker, legal, _calculator,
                    _costtable, _answer (Jinja-Makros)
content/            Impressum, Datenschutz, Werbehinweis (Markdown)
marketing/          Social-/Blog-Entwuerfe (Subagent `marketing`), nichts live
scripts/umlaut_fix.py   ASCII-Umschrift -> echte Umlaute im sichtbaren Text
static/style.css    Design, ein Stylesheet, drei Theme-Zustaende (System/hell/dunkel)
static/app.js       Progressive Enhancement: Theme-Umschalter, Live-Suche im
                    Kopf und auf der Startseite, Listen-Filter/Sortierung,
                    Ordervolumen-Umschalter im Antwort-Block. Ohne JavaScript
                    bleibt jede Seite voll nutzbar.
static/brand/       Logo/Wortmarke aus src/images.py (falls erzeugt)
dist/               generierte Website, nicht in Git
vercel.json         Build- und Ausgabekonfiguration fuer Vercel
.github/workflows/  ci.yml (Tests), refresh.yml (taeglicher Deploy-Hook)
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

## Deploy (Vercel)

Einmalig, im Vercel-Konto:

1. **New Project** -> GitHub-Repo `aktien-vergleich` importieren.
2. Framework Preset **Other**. Build Command und Output Directory kommen aus
   `vercel.json` (Build: `src.build`, Output: `dist`).
3. **Environment Variables** setzen:
   - `SITE_BASE_URL` = die Vercel-Domain oder die eigene Domain
     (`https://…`, ohne Schraegstrich am Ende)
   - `SITE_PATH_PREFIX` leer lassen
4. Deploy. Danach loest jeder Push auf `main` automatisch einen Deploy aus.

Der Vercel-Build ruft `src.fetch` fuer frische Kurse und dann `src.build`.
`src.summarize` (eigene Meldungs-Zusammenfassungen) laeuft NICHT im Build,
um API-Kosten pro Deploy zu vermeiden: bei Bedarf lokal `python -m src.summarize`
vor einem Commit ausfuehren. Sauberer waere langfristig, `data/generated/` zu
versionieren und per Cron-Action zu aktualisieren.

Taeglicher Neubau fuer frische Kurse:

5. Vercel -> Settings -> Git -> **Deploy Hooks** anlegen, URL kopieren.
6. GitHub -> Settings -> Secrets and variables -> Actions -> Secret
   `VERCEL_DEPLOY_HOOK` = diese URL. `refresh.yml` ruft sie taeglich auf.

GitHub Pages wird nicht mehr verwendet (Workflow entfernt). Falls Pages im
Repo noch aktiv ist: Settings -> Pages -> Source auf **None**.

## Bilder (optional, Nano Banana)

`src/images.py` erzeugt Bilder ueber Google Gemini. Schluessel aus Google AI
Studio, dann in `.env` bzw. als Umgebungsvariable `GEMINI_API_KEY`.

```powershell
python -m src.images logo                     # Logo/Wortmarke -> static/brand/
python -m src.images marketing 2026-09-09      # Grafiken -> marketing/<datum>/img/
```

Laeuft nicht im Build. Ergebnisse sichten, dann committen. Ohne Schluessel
passiert nichts.

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
