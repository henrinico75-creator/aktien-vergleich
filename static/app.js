/* Progressive Enhancement. Ohne dieses Script bleibt jede Seite nutzbar:
   volle Listen sichtbar, feste Ordervolumina maßgeblich, Suche per Formular
   an die Startseite. Das Script ergänzt Theme-Umschalter, Live-Suche im Kopf
   und auf der Startseite, Listen-Filter/Sortierung und den Ordervolumen-
   Umschalter im Antwort-Block. */
(function () {
  "use strict";

  var deEUR = new Intl.NumberFormat("de-DE", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  var deInt = new Intl.NumberFormat("de-DE");
  var dePct = new Intl.NumberFormat("de-DE", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  var norm = function (s) { return String(s || "").toLowerCase(); };

  /* ---------------------------------------------------------------- Theme */
  (function () {
    var btn = document.querySelector("[data-theme-toggle]");
    if (!btn) return;
    var order = ["system", "light", "dark"];
    var glyph = { system: "◐", light: "☀️", dark: "☾" };
    var label = { system: "System", light: "Hell", dark: "Dunkel" };
    function current() {
      try { var t = localStorage.getItem("theme"); return t === "light" || t === "dark" ? t : "system"; }
      catch (e) { return "system"; }
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
      btn.title = "Farbschema: " + label[mode];
    }
    apply(current());
    btn.addEventListener("click", function () {
      apply(order[(order.indexOf(current()) + 1) % order.length]);
    });
  })();

  /* ---------------------------------------------------------------- Live-Suche (Kopf + Startseite) */
  function wireSearch(form, inputSel, resultsSel, limit) {
    var index = window.__searchIndex;
    if (!Array.isArray(index) || !index.length) return;
    var input = form.querySelector(inputSel);
    var box = form.querySelector(resultsSel);
    if (!input || !box) return;
    var items = [];
    var active = -1;

    function esc(s) { return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;"); }

    function close() { box.hidden = true; box.innerHTML = ""; items = []; active = -1; input.setAttribute("aria-expanded", "false"); }

    function open(list) {
      if (!list.length) {
        box.innerHTML = '<p class="empty">Kein Treffer.</p>';
        box.hidden = false; items = []; active = -1; return;
      }
      box.innerHTML = list.map(function (it) {
        return '<a role="option" href="' + esc(it.u) + '"><span class="k">' + esc(it.k) +
          '</span><span>' + esc(it.n) + '</span></a>';
      }).join("");
      items = Array.prototype.slice.call(box.querySelectorAll("a"));
      active = -1;
      box.hidden = false;
      input.setAttribute("aria-expanded", "true");
    }

    function query() {
      var q = norm(input.value).trim();
      if (q.length < 2) { close(); return; }
      var hits = [];
      for (var i = 0; i < index.length && hits.length < limit; i++) {
        if ((index[i].q || norm(index[i].n)).indexOf(q) !== -1) hits.push(index[i]);
      }
      open(hits);
    }

    function highlight(n) {
      items.forEach(function (el, i) { el.setAttribute("aria-selected", i === n ? "true" : "false"); });
      active = n;
      if (items[n]) items[n].scrollIntoView({ block: "nearest" });
    }

    input.setAttribute("role", "combobox");
    input.setAttribute("aria-autocomplete", "list");
    input.setAttribute("aria-expanded", "false");

    input.addEventListener("input", query);
    input.addEventListener("focus", function () { if (input.value.trim().length >= 2) query(); });
    input.addEventListener("keydown", function (e) {
      if (box.hidden) return;
      if (e.key === "ArrowDown") { e.preventDefault(); highlight(Math.min(active + 1, items.length - 1)); }
      else if (e.key === "ArrowUp") { e.preventDefault(); highlight(Math.max(active - 1, 0)); }
      else if (e.key === "Enter" && active >= 0 && items[active]) { e.preventDefault(); window.location.href = items[active].href; }
      else if (e.key === "Escape") { close(); }
    });
    form.addEventListener("submit", function (e) {
      if (items.length) { e.preventDefault(); window.location.href = (items[active] || items[0]).href; }
    });
    document.addEventListener("click", function (e) { if (!form.contains(e.target)) close(); });
  }

  var hs = document.querySelector("[data-hsearch]");
  if (hs) wireSearch(hs, "[data-hsearch-input]", "[data-hsearch-results]", 8);
  var fd = document.querySelector("[data-finder]");
  if (fd) wireSearch(fd, "[data-finder-input]", "[data-finder-results]", 12);

  /* ---------------------------------------------------------------- Listen: filtern und sortieren */
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

    function ensureEmpty() {
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
      rows.forEach(function (r) { var s = r.getAttribute("data-sector"); if (s) seen[s] = 1; });
      Object.keys(seen).sort(function (a, b) { return a.localeCompare(b, "de"); }).forEach(function (s) {
        var o = document.createElement("option"); o.value = s; o.textContent = s; sectorSel.appendChild(o);
      });
    }

    function apply() {
      var q = norm(search && search.value).trim();
      var sec = (sectorSel && sectorSel.value) || "";
      var shown = 0;
      rows.forEach(function (r) {
        var hay = norm(r.getAttribute("data-search") || r.textContent);
        var ok = (!q || hay.indexOf(q) !== -1) && (!sec || r.getAttribute("data-sector") === sec);
        r.hidden = !ok;
        if (ok) shown++;
      });
      if (emptyRow && emptyRow.parentNode) emptyRow.parentNode.removeChild(emptyRow);
      if (shown === 0) body.appendChild(ensureEmpty());
      if (count) count.textContent = shown === total ? total + " Einträge" : shown + " von " + total + " Einträgen";
    }

    if (search) search.addEventListener("input", apply);
    if (sectorSel) sectorSel.addEventListener("change", apply);

    if (table.tHead) {
      Array.prototype.forEach.call(table.tHead.rows[0].cells, function (th) {
        var key = th.getAttribute("data-sort");
        if (!key) return;
        th.classList.add("sortable"); th.tabIndex = 0; th.setAttribute("role", "button");
        var dir = 0;
        function sort() {
          dir = dir === 1 ? -1 : 1;
          Array.prototype.forEach.call(table.tHead.rows[0].cells, function (o) { o.removeAttribute("aria-sort"); });
          th.setAttribute("aria-sort", dir === 1 ? "ascending" : "descending");
          rows.slice().sort(function (a, b) {
            var av = a.getAttribute("data-" + key) || "", bv = b.getAttribute("data-" + key) || "";
            var an = parseFloat(av.replace(",", ".")), bn = parseFloat(bv.replace(",", "."));
            var c = (!isNaN(an) && !isNaN(bn)) ? an - bn : av.localeCompare(bv, "de");
            return dir * c;
          }).forEach(function (r) { body.appendChild(r); });
        }
        th.addEventListener("click", sort);
        th.addEventListener("keydown", function (e) { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); sort(); } });
      });
    }
    apply();
  });

  /* ---------------------------------------------------------------- Antwort-Block: Ordervolumen umschalten */
  (function () {
    var panel = document.querySelector("[data-answer]");
    var brokers = window.__brokers;
    if (!panel || !Array.isArray(brokers)) return;
    var seg = panel.querySelector("[data-answer-seg]");
    var whoEl = panel.querySelector("[data-answer-who]");
    var costEl = panel.querySelector("[data-answer-cost]");
    var subEl = panel.querySelector("[data-answer-sub]");
    var chart = panel.querySelector("[data-chart]");
    var refEl = panel.querySelector("[data-ref-size]");
    if (!seg || !chart) return;

    function esc(s) { return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;"); }
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
      var max = Math.max.apply(null, list.map(function (x) { return x.c; }));
      var best = list.filter(function (x) { return Math.abs(x.c - min) < 1e-9; });

      costEl.textContent = deEUR.format(min) + " EUR";
      if (refEl) refEl.textContent = deInt.format(v) + " EUR";
      if (best.length > 1) {
        whoEl.textContent = best.length + " Broker gleichauf";
        subEl.textContent = best.slice(0, 3).map(function (x) { return x.b.name; }).join(", ") + (best.length > 3 ? " und weitere" : "");
      } else {
        whoEl.textContent = best[0].b.name;
        subEl.textContent = best[0].b.venue + ", " + dePct.format(v ? (min / v * 100) : 0) + " % vom Ordervolumen";
      }

      chart.innerHTML = list.map(function (x, i) {
        var isMin = Math.abs(x.c - min) < 1e-9;
        var w = x.c === 0 ? 3 : (max > 0 ? (x.c / max * 100) : 0);
        var tag = i === 0 ? '<span class="chart-tag">' + (x.c > 0 ? "günstigster" : "0 EUR") + "</span>" : "";
        var sub = (x.b.subscription_eur && x.b.subscription_eur > 0)
          ? '<span class="chart-sub-tag">+ ' + deEUR.format(x.b.subscription_eur).replace(",00", "") + " EUR/Mon.</span>" : "";
        return '<div class="chart-row' + (isMin ? " is-best" : "") + '">' +
          '<span class="chart-name">' + esc(x.b.name) + tag + sub + "</span>" +
          '<span class="chart-track"><span class="chart-fill" style="width:' + w.toFixed(1) + '%"></span></span>' +
          '<span class="chart-cost">' + deEUR.format(x.c) + " EUR</span></div>";
      }).join("");
    }

    seg.hidden = false;
    seg.querySelectorAll("button[data-size]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        seg.querySelectorAll("button[data-size]").forEach(function (o) { o.setAttribute("aria-pressed", "false"); });
        btn.setAttribute("aria-pressed", "true");
        render(parseInt(btn.getAttribute("data-size"), 10));
      });
    });
    var pre = seg.querySelector('button[aria-pressed="true"]');
    if (pre) render(parseInt(pre.getAttribute("data-size"), 10));
  })();
})();
