"""Optionaler Schritt: kurze eigene Zusammenfassungen der Meldungen.

Liest die von src/fetch.py erzeugten JSON-Dateien und ergaenzt je Meldung ein
Feld `summary`: ein bis zwei sachliche deutsche Saetze, in eigenen Worten auf
Basis von Schlagzeile und der Kurzbeschreibung der Quelle (`_snippet`). Kein
uebernommener Artikeltext.

Braucht einen Anthropic-API-Schluessel in der Umgebungsvariable
ANTHROPIC_API_KEY. Ohne Schluessel beendet sich das Skript ohne Fehler, der
Build laeuft dann mit den Schlagzeilen weiter.

Aufruf:  python -m src.summarize
"""
from __future__ import annotations

import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GEN_DIR = ROOT / "data" / "generated"

MODEL = "claude-opus-5"
MAX_WORKERS = 8

SYSTEM = (
    "Du bist Finanzredakteur. Fasse eine einzelne Unternehmensmeldung in ein "
    "bis zwei sachlichen deutschen Saetzen zusammen. Regeln: eigene Worte, kein "
    "uebernommener Wortlaut. Nuechtern, keine Wertung, keine Kauf- oder "
    "Verkaufsempfehlung, keine Superlative. Wenn die Meldung eine Aussage des "
    "Managements enthaelt, gib sie sinngemaess wieder und nenne die Funktion "
    "(z. B. Vorstandsvorsitzender). Nur der Zusammenfassungstext, keine "
    "Einleitung, keine Anfuehrungszeichen."
)


def _client():
    try:
        import anthropic
    except ImportError:
        print("anthropic-Paket fehlt (pip install anthropic)", file=sys.stderr)
        return None
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return None
    return anthropic.Anthropic()


def _summarize_one(client, company: str, item: dict) -> str:
    prompt = (
        f"Unternehmen: {company}\n"
        f"Schlagzeile: {item.get('title', '')}\n"
        f"Kurzbeschreibung der Quelle: {item.get('_snippet') or '(keine)'}\n\n"
        "Zusammenfassung:"
    )
    resp = client.messages.create(
        model=MODEL,
        max_tokens=400,
        system=SYSTEM,
        output_config={"effort": "low"},
        messages=[{"role": "user", "content": prompt}],
    )
    parts = [b.text for b in resp.content if b.type == "text"]
    return " ".join(" ".join(parts).split()).strip()


def process_file(client, path: Path) -> int:
    data = json.loads(path.read_text(encoding="utf-8"))
    news = data.get("news") or []
    todo = [n for n in news if not n.get("summary")]
    if not todo:
        return 0
    company = data.get("name", "")
    done = 0
    for item in todo:
        try:
            summary = _summarize_one(client, company, item)
            if summary:
                item["summary"] = summary
                item.pop("_snippet", None)
                done += 1
        except Exception as exc:  # noqa: BLE001
            print(f"  {path.name}: {exc}", file=sys.stderr)
    if done:
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    return done


def main() -> int:
    client = _client()
    if client is None:
        print(
            "kein ANTHROPIC_API_KEY gesetzt, ueberspringe Zusammenfassungen",
            file=sys.stderr,
        )
        return 0

    files = sorted(p for p in GEN_DIR.glob("*.json") if not p.name.startswith("etf-"))
    if not files:
        print("keine generierten Dateien, erst src.fetch ausfuehren", file=sys.stderr)
        return 0

    total = 0
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        for count in pool.map(lambda p: process_file(client, p), files):
            total += count
    print(f"fertig: {total} Zusammenfassungen ergaenzt", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
