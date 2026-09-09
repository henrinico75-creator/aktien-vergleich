/* Progressive Enhancement fuer alle Seiten.
   Ohne dieses Script bleibt jede Seite voll benutzbar:
   - alle Aktien sichtbar, Reihenfolge aus dem HTML
   - feste Ordervolumina in den Tabellen sind massgeblich
   Das Script ergaenzt Theme-Umschalter, Suche/Filter/Sortierung und den
   Ordervolumen-Umschalter im Ergebnis-Panel. */
(function () {
  "use strict";

  var deInt = new Intl.NumberFormat("de-DE");
  var deEUR = new Intl.NumberFormat("de-DE", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  var dePct = new Intl.NumberFormat("de-DE", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

  /* ---------------------------------------------------------------- Theme */
  (function theme() {
    var btn = document.querySelector("[data-theme-toggle]");
    if (!btn) return;
    var order = ["system", "light", "dark"];
    var glyph = { system: "◐", light: "☀️", dark: "☾" };
    var labelText = { system: "System", light: "Hell", dark: "Dunkel" };

    function current() {
      try {
        var t = localStorage.getItem("theme");
        return t === "light" || t === "dark" ? t : "system";
      } catch (e) { return "system"; }
    }
    function apply(mode) {
      if (mode === "system") {
        document.documentElement.removeAttribute("data-theme");
        try { localStorage.removeItem("theme"); } catch (e) {}
      } else {
        document.documentElement.setAttribute("data-theme", mode);
        try { localStorage.setItem("theme", mode); } catch (e) {}
      }
      btn.textContent = glyph[mode];
      btn.title = "Farbschema: " + labelText[mode];
    }
    apply(current());
    btn.addEventListener("click", function () {
      apply(order[(order.indexOf(current()) + 1) % order.length]);
    });
  })();

  /* ---------------------------------------------------------------- Listen filtern und sortieren */
  document.querySelectorAll("[data-listing]").forEach(function (root) {
    var table = root.querySelector("table");
    var body = table && table.tBodies[0];
    if (!body) return;
    var rows = Array.prototype.slice.call(body.rows).filter(function (r) { return !r.classList.contains("no-match"); });
    var search = root.querySelector("[data-filter-search]");
    var sectorSel = root.querySelector("[data-filter-sector]");
    var count = root.querySelector("[data-filter-count]");
    var total = rows.length;

    var emptyRow = null;
    function ensureEmptyRow() {
      if (emptyRow) return emptyRow;
      emptyRow = document.createElement("tr");
      emptyRow.className = "no-match";
      var td = document.createElement("td");
      td.colSpan = table.tHead ? table.tHead.rows[0].cells.length : 1;
      td.textContent = "Kein Treffer. Suche oder Filter anpassen.";
      emptyRow.appendChild(td);
      return emptyRow;
    }

    if (sectorSel) {
      var seen = {};
      rows.forEach(function (r) {
        var s = r.getAttribute("data-sector");
        if (s && !seen[s]) { seen[s] = 1; }
      });
      Object.keys(seen).sort(function (a, b) { return a.localeCompare(b, "de"); }).forEach(function (s) {
        var o = document.createElement("option");
        o.value = s; o.textContent = s;
        sectorSel.appendChild(o);
      });
    }

    function applyFilter() {
      var q = (search && search.value || "").trim().toLowerCase();
      var sec = sectorSel && sectorSel.value || "";
      var shown = 0;
      rows.forEach(function (r) {
        var hay = (r.getAttribute("data-search") || r.textContent).toLowerCase();
        var ok = (!q || hay.indexOf(q) !== -1) && (!sec || r.getAttribute("data-sector") === sec);
        r.hidden = !ok;
        if (ok) shown++;
      });
      if (emptyRow && emptyRow.parentNode) emptyRow.parentNode.removeChild(emptyRow);
      if (shown === 0) body.appendChild(ensureEmptyRow());
      if (count) count.textContent = shown === total
        ? total + " Einträge"
        : shown + " von " + total + " Einträgen";
    }

    if (search) search.addEventListener("input", applyFilter);
    if (sectorSel) sectorSel.addEventListener("change", applyFilter);

    if (table.tHead) {
      Array.prototype.forEach.call(table.tHead.rows[0].cells, function (th, idx) {
        var key = th.getAttribute("data-sort");
        if (!key) return;
        th.classList.add("sortable");
        th.setAttribute("role", "button");
        th.tabIndex = 0;
        var dir = 0;
        function sort() {
          dir = dir === 1 ? -1 : 1;
          Array.prototype.forEach.call(table.tHead.rows[0].cells, function (o) { o.removeAttribute("aria-sort"); });
          th.setAttribute("aria-sort", dir === 1 ? "ascending" : "descending");
          var sorted = rows.slice().sort(function (a, b) {
            var av = a.getAttribute("data-" + key) || "";
            var bv = b.getAttribute("data-" + key) || "";
            var an = parseFloat(av.replace(",", ".")), bn = parseFloat(bv.replace(",", "."));
            var cmp = (!isNaN(an) && !isNaN(bn)) ? an - bn : av.localeCompare(bv, "de");
            return dir * cmp;
          });
          sorted.forEach(function (r) { body.appendChild(r); });
        }
        th.addEventListener("click", sort);
        th.addEventListener("keydown", function (e) {
          if (e.key === "Enter" || e.key === " ") { e.preventDefault(); sort(); }
        });
      });
    }

    applyFilter();
  });

  /* ---------------------------------------------------------------- Startseite: Sprung in die Suche */
  document.querySelectorAll("[data-jump-search]").forEach(function (link) {
    link.addEventListener("click", function () {
      var target = document.querySelector((link.getAttribute("href") || "") + " [data-filter-search]");
      if (target) setTimeout(function () { target.focus({ preventScroll: true }); }, 350);
    });
  });

  /* ---------------------------------------------------------------- Ergebnis-Panel: Ordervolumen umschalten */
  (function resultSizes() {
    var panel = document.querySelector("[data-result]");
    if (!panel || !window.__brokers) return;
    var brokers = window.__brokers;
    var box = panel.querySelector("[data-result-sizes]");
    var whoEl = panel.querySelector("[data-result-who]");
    var costEl = panel.querySelector("[data-result-cost]");
    var metaEl = panel.querySelector("[data-result-meta]");
    var altEl = panel.querySelector("[data-result-alt]");
    var refSizeEl = panel.querySelector("[data-ref-size]");
    if (!box) return;

    function cost(b, v) {
      if (b.free_above != null && v >= b.free_above) return 0;
      var c = b.order_fixed + b.order_pct * v;
      if (b.order_min) c = Math.max(c, b.order_min);
      if (b.order_max != null) c = Math.min(c, b.order_max);
      return Math.round(c * 100) / 100;
    }
    function render(v) {
      var list = brokers.map(function (b) { return { b: b, c: cost(b, v) }; })
        .sort(function (a, b) { return a.c - b.c || a.b.name.localeCompare(b.b.name, "de"); });
      var min = list[0].c;
      var best = list.filter(function (x) { return Math.abs(x.c - min) < 1e-9; });
      costEl.textContent = deEUR.format(min) + " EUR";
      if (refSizeEl) refSizeEl.textContent = deInt.format(v) + " EUR";
      if (best.length > 1) {
        whoEl.textContent = best.length + " Broker gleichauf";
        metaEl.textContent = best.slice(0, 3).map(function (x) { return x.b.name; }).join(", ")
          + (best.length > 3 ? " und weitere" : "");
      } else {
        whoEl.textContent = best[0].b.name;
        metaEl.textContent = best[0].b.venue + ", "
          + dePct.format(v ? (min / v * 100) : 0) + " % vom Ordervolumen";
      }
      var rest = list.slice(best.length, best.length + 3).map(function (x) { return x.b.name; });
      altEl.innerHTML = rest.length
        ? "Danach: <strong>" + rest.map(esc).join("</strong>, <strong>") + "</strong>."
        : "";
    }
    function esc(s) {
      return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
    }
    box.hidden = false;
    box.querySelectorAll("button[data-size]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        box.querySelectorAll("button[data-size]").forEach(function (o) { o.setAttribute("aria-pressed", "false"); });
        btn.setAttribute("aria-pressed", "true");
        render(parseInt(btn.getAttribute("data-size"), 10));
      });
    });
    var pre = box.querySelector('button[aria-pressed="true"]');
    if (pre) render(parseInt(pre.getAttribute("data-size"), 10));
  })();
})();
