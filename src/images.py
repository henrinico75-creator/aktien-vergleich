"""Optionaler Schritt: Bilder ueber Google Gemini ("Nano Banana") erzeugen.

Zwei Anwendungen:

    python -m src.images logo
        Logo und Wortmarke nach static/brand/.

    python -m src.images marketing 2026-09-09
        Grafiken passend zu den Entwuerfen in marketing/<datum>/ nach
        marketing/<datum>/img/.

Braucht GEMINI_API_KEY in der Umgebung (Schluessel aus Google AI Studio).
Ohne Schluessel beendet sich das Skript ohne Fehler und ohne Bild. Das Skript
laeuft NICHT automatisch im Build; die erzeugten Dateien werden nach Sichtung
committet.

Modell ueber GEMINI_IMAGE_MODEL, Vorgabe: gemini-2.5-flash-image.
"""
from __future__ import annotations

import base64
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BRAND_DIR = ROOT / "static" / "brand"
MARKETING_DIR = ROOT / "marketing"

DEFAULT_MODEL = "gemini-2.5-flash-image"
API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"

# Gemeinsame Bildsprache. Steckt in jedem Prompt, damit alle Bilder zur Seite
# passen. Bewusst nuechtern: die Seite ist ein Kostenvergleich, kein Hype.
BRAND = (
    "Brand: Aktien-Kosten, a cost-comparison tool for German retail investors "
    "that shows at which broker a given stock or ETF is cheapest to buy. "
    "Voice: precise, quiet, trustworthy, serious. Never flashy, never hype. "
    "Palette: emerald green #0e9f6e as the single accent, near-black ink "
    "#0c0f0e, warm off-white background #fbfbf9 (or near-black background for "
    "a dark version). Type feel: geometric grotesque (Space Grotesk), "
    "monospaced tabular figures for numbers. Signature motif: a set of "
    "ascending ranked bars, like a horizontal bar chart of order costs with "
    "the cheapest bar highlighted in emerald. "
    "Style: flat vector, generous whitespace, small sharp corner radius, no "
    "gradients as decoration, no 3D, no photorealism, no stock-photo people, "
    "no drop shadows, no purple. "
    "Rules: any text in the image must be in German and spelled correctly. "
    "Do not invent or depict real broker logos or official-looking marks. "
    "Do not add ratings, stars, or superlatives. Do not invent numbers."
)


# ---------------------------------------------------------------- API

def _api_key() -> str | None:
    return os.environ.get("GEMINI_API_KEY") or None


def _model() -> str:
    return os.environ.get("GEMINI_IMAGE_MODEL") or DEFAULT_MODEL


def generate(prompt: str, aspect_ratio: str | None = None) -> bytes | None:
    """Ein Bild erzeugen. Gibt die Bilddaten (PNG/JPEG) zurueck oder None."""
    key = _api_key()
    if not key:
        return None

    body: dict = {"contents": [{"parts": [{"text": prompt}]}],
                  "generationConfig": {"responseModalities": ["TEXT", "IMAGE"]}}
    if aspect_ratio:
        body["generationConfig"]["imageConfig"] = {"aspectRatio": aspect_ratio}

    req = urllib.request.Request(
        f"{API_BASE}/{_model()}:generateContent",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", "x-goog-api-key": key},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:500]
        print(f"  API-Fehler {exc.code}: {detail}", file=sys.stderr)
        return None
    except urllib.error.URLError as exc:
        print(f"  Netzfehler: {exc}", file=sys.stderr)
        return None

    for cand in payload.get("candidates", []):
        for part in cand.get("content", {}).get("parts", []):
            inline = part.get("inlineData") or part.get("inline_data")
            if inline and inline.get("data"):
                return base64.b64decode(inline["data"])

    reason = payload.get("promptFeedback", {}).get("blockReason")
    print(f"  kein Bild in der Antwort{f' (blockiert: {reason})' if reason else ''}",
          file=sys.stderr)
    return None


def _save(data: bytes, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    print(f"  geschrieben: {path.relative_to(ROOT)} ({len(data) // 1024} KB)",
          file=sys.stderr)


# ---------------------------------------------------------------- Logo

def logo_jobs() -> list[tuple[str, str, str | None]]:
    """(Dateiname, Prompt, Seitenverhaeltnis)."""
    base = (
        f"{BRAND}\n\n"
        "Task: a compact logo mark plus the wordmark \"Aktien-Kosten\". "
        "The mark is three flush-left horizontal bars stacked with equal gaps, "
        "each shorter than the one above (descending right edge, like a small "
        "ranked bar chart trending down). Top bar ink at full strength, middle "
        "bar ink at about half strength, bottom (shortest) bar solid emerald. "
        "Wordmark set tight in a geometric grotesque, ink color, to the right "
        "of the mark, vertically centered on it. Generous clear space. "
        "Flat, single scale, no tagline, no container shape, no outline."
    )
    return [
        ("logo.png", base + " Background: the warm off-white #fbfbf9.", "16:9"),
        ("logo-dark.png", base + " Background: near-black #0c0f0e, wordmark and "
         "the two ink bars in off-white, bottom bar emerald.", "16:9"),
        ("mark.png", f"{BRAND}\n\nTask: only the icon, no text. Three flush-left "
         "horizontal bars stacked with equal gaps, each shorter than the one "
         "above, top bar ink, middle bar ink at half strength, bottom shortest "
         "bar emerald. On an off-white square, centered, generous padding.", "1:1"),
    ]


def cmd_logo() -> int:
    made = 0
    for name, prompt, ar in logo_jobs():
        print(f"erzeuge {name} ...", file=sys.stderr)
        data = generate(prompt, ar)
        if data:
            _save(data, BRAND_DIR / name)
            made += 1
    print(f"fertig: {made} Datei(en) in static/brand/", file=sys.stderr)
    return 0


# ---------------------------------------------------------------- Marketing

def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def marketing_jobs(date: str) -> list[tuple[str, str, str]]:
    """(Dateiname, Prompt, Seitenverhaeltnis) fuer marketing/<date>/img/."""
    folder = MARKETING_DIR / date
    if not folder.is_dir():
        raise SystemExit(f"Ordner fehlt: marketing/{date}/ (erst den marketing-Subagenten laufen lassen)")

    plan = _read(folder / "plan.md").strip()
    insta = _read(folder / "instagram.md").strip()
    brief = (
        f"{BRAND}\n\n"
        "Task: a social graphic for this week's post. Use ONLY the wording and "
        "any figures from the brief below; do not add your own numbers or "
        "claims. Put a short German headline (max 7 words) and, if the brief "
        "gives one, a single supporting line. Leave room at the bottom for a "
        "small \"aktien-kosten\" wordmark. Keep it calm and legible.\n\n"
        f"--- Wochenthema ---\n{plan or '(kein plan.md)'}\n\n"
        f"--- Instagram-Entwurf ---\n{insta or '(kein instagram.md)'}"
    )
    return [
        ("instagram-1x1.png", brief + "\n\nFormat: square feed post.", "1:1"),
        ("story-9x16.png", brief + "\n\nFormat: vertical story / reel cover, "
         "headline in the upper third.", "9:16"),
    ]


def cmd_marketing(date: str) -> int:
    out = MARKETING_DIR / date / "img"
    made = 0
    for name, prompt, ar in marketing_jobs(date):
        print(f"erzeuge {name} ...", file=sys.stderr)
        data = generate(prompt, ar)
        if data:
            _save(data, out / name)
            made += 1
    print(f"fertig: {made} Datei(en) in marketing/{date}/img/", file=sys.stderr)
    return 0


# ---------------------------------------------------------------- CLI

USAGE = "Aufruf: python -m src.images logo | python -m src.images marketing <JJJJ-MM-TT>"


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv

    if not _api_key():
        print("kein GEMINI_API_KEY gesetzt, ueberspringe Bildgenerierung", file=sys.stderr)
        return 0

    if not args or args[0] in ("-h", "--help"):
        print(USAGE, file=sys.stderr)
        return 0 if args else 2

    if args[0] == "logo":
        return cmd_logo()
    if args[0] == "marketing":
        if len(args) < 2:
            print(USAGE, file=sys.stderr)
            return 2
        return cmd_marketing(args[1])

    print(f"unbekannter Befehl: {args[0]}\n{USAGE}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
