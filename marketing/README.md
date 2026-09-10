# marketing/

Entwuerfe fuer Social Media und Blog. Erstellt vom Subagenten `marketing`
(`.claude/agents/marketing.md`). Nichts hier wird automatisch veroeffentlicht.

## Aufruf

In Claude Code:

```
> nutze den marketing-Subagenten und entwirf die Posts fuer diese Woche
```

oder gezielt:

```
> marketing-Subagent: Blogartikel zum Thema Sparplan-Kosten
```

## Ablage

Je Lauf ein Ordner `marketing/JJJJ-MM-TT/` mit:

- `plan.md`       Thema der Woche, welche Posts, warum
- `blog.md`       Artikelentwurf inkl. SEO-Titel, Meta-Description, Slug
- `x-twitter.md`  2 bis 4 Kurzposts
- `linkedin.md`   1 Post
- `reddit.md`     0 bis 1 Post plus Regel-Hinweise
- `instagram.md`  Grafik-Spezifikation plus Caption

## Regeln

Gelten fuer alle Entwuerfe, siehe `.claude/agents/marketing.md`:
keine Kaufempfehlungen, kein Hype, Zahlen nur aus `data/`, Werbung
kennzeichnen, kein kopierter Fremdtext, solange der Prototyp-Banner steht
Gebuehrenaussagen als vorlaeufig markieren.

## Grafiken erzeugen (optional)

Nach dem Entwurf, wenn ein `GEMINI_API_KEY` gesetzt ist:

```
python -m src.images marketing 2026-09-09
```

Erzeugt aus `plan.md` und `instagram.md` je ein 1:1- und ein 9:16-Bild in
`marketing/2026-09-09/img/`. Nutzt nur Wortlaut und Zahlen aus den Entwuerfen,
erfindet nichts. Ergebnis vor Verwendung sichten.

## Nach dem Entwurf

Du postest selbst. Was gepostet wurde, kannst du in der jeweiligen Datei
abhaken oder den Ordner nach `marketing/archiv/` verschieben.
