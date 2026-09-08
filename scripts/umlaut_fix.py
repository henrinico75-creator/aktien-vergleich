"""Ersetzt ASCII-Umschriften (ae/oe/ue/ss) durch echte Umlaute im sichtbaren Text.

Arbeitet mit einer festen Wortstamm-Liste, nicht mit einer Blindregel, damit
Woerter wie "aktuell" (ue, aber kein Umlaut) unveraendert bleiben. Wird auf
Templates, Rechtstexte, config.yaml sowie brokers.yaml und etfs.yaml
angewendet. stocks.yaml wird bewusst NICHT verarbeitet, weil dort Slugs
(URL-Bestandteile) stehen, die ASCII bleiben muessen.

Aufruf:  python scripts/umlaut_fix.py [--check]
    --check  nur melden, welche Dateien sich aendern wuerden, nichts schreiben
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Wortstamm -> Ersetzung. Nur Kleinschreibung; Grossschreibung wird abgeleitet.
# Reihenfolge: laengere/spezifischere Staemme zuerst.
STEMS: list[tuple[str, str]] = [
    ("abschliessend", "abschließend"),
    ("massgeblich", "maßgeblich"),
    ("gemaess", "gemäß"),
    ("grundsaetzlich", "grundsätzlich"),
    ("tatsaechlich", "tatsächlich"),
    ("europaeisch", "europäisch"),
    ("vollstaendig", "vollständig"),
    ("veroeffentlich", "veröffentlich"),
    ("aufsichtsbehoerde", "aufsichtsbehörde"),
    ("einschraenkung", "einschränkung"),
    ("unabhaengig", "unabhängig"),
    ("volumenabhaengig", "volumenabhängig"),
    ("bruchstueckhandel", "bruchstückhandel"),
    ("sparplanausfuehrung", "sparplanausführung"),
    ("ausfuehrung", "ausführung"),
    ("ausschuett", "ausschütt"),
    ("schuett", "schütt"),
    ("aktualitaet", "aktualität"),
    ("verguetung", "vergütung"),
    ("muenchener", "münchener"),
    ("industrielaender", "industrieländer"),
    ("schwellenlaender", "schwellenländer"),
    ("rueckversicherung", "rückversicherung"),
    ("erklaerung", "erklärung"),
    ("zusaetzlich", "zusätzlich"),
    ("kuenftig", "künftig"),
    ("gekuerzte", "gekürzte"),
    ("depotgebuehr", "depotgebühr"),
    ("ordergebuehr", "ordergebühr"),
    ("mindestgebuehr", "mindestgebühr"),
    ("gebuehr", "gebühr"),
    ("guenstig", "günstig"),
    ("pruef", "prüf"),
    ("gepruef", "geprüf"),
    ("koenn", "könn"),
    ("muess", "müss"),
    ("boerse", "börse"),
    ("behoerde", "behörde"),
    ("eroeffn", "eröffn"),
    ("loeschung", "löschung"),
    ("moeglich", "möglich"),
    ("groess", "größ"),
    ("hoeher", "höher"),
    ("hoehere", "höhere"),
    ("ruestung", "rüstung"),
    ("vorzuege", "vorzüge"),
    ("sparplaene", "sparpläne"),
    ("plaene", "pläne"),
    ("fuell", "füll"),
    ("aeltest", "ältest"),
    ("haeufig", "häufig"),
    ("spaeter", "später"),
    ("regulaer", "regulär"),
    ("abhaengig", "abhängig"),
    ("enthaelt", "enthält"),
    ("entfaellt", "entfällt"),
    ("zaehlt", "zählt"),
    ("betraege", "beträge"),
    ("aendern", "ändern"),
    ("aenderung", "änderung"),
    ("ergaenz", "ergänz"),
    ("gewaehr", "gewähr"),
    ("fliess", "fließ"),
    ("schliess", "schließ"),
    ("geschaeft", "geschäft"),
    ("aehnlich", "ähnlich"),
    ("waehl", "wähl"),
    ("waehr", "währ"),
    ("laender", "länder"),
    ("laedt", "lädt"),
    ("laeuft", "läuft"),
    ("zulaessig", "zulässig"),
    ("buecher", "bücher"),
    ("rueck", "rück"),
    ("ueber", "über"),
    ("fuer", "für"),
]

TARGETS = [
    "templates/base.html",
    "templates/index.html",
    "templates/stock.html",
    "templates/etf.html",
    "templates/broker.html",
    "templates/legal.html",
    "templates/_calculator.html",
    "content/impressum.md",
    "content/datenschutz.md",
    "content/werbehinweis.md",
    "config.yaml",
    "data/brokers.yaml",
    "data/etfs.yaml",
]


def _variants(stem: str, repl: str) -> list[tuple[str, str]]:
    return [
        (stem, repl),
        (stem.capitalize(), repl.capitalize()),
        (stem.upper(), repl.upper()),
    ]


def fix_text(text: str) -> str:
    for stem, repl in STEMS:
        for a, b in _variants(stem, repl):
            text = text.replace(a, b)
    return text


def main() -> int:
    check = "--check" in sys.argv
    changed = []
    for rel in TARGETS:
        p = ROOT / rel
        if not p.exists():
            continue
        original = p.read_text(encoding="utf-8")
        fixed = fix_text(original)
        if fixed != original:
            changed.append(rel)
            if not check:
                p.write_text(fixed, encoding="utf-8")
    verb = "wuerde aendern" if check else "geaendert"
    for rel in changed:
        print(f"{verb}: {rel}")
    if not changed:
        print("nichts zu tun")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
