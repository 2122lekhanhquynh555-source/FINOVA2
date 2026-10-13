/* FINOVA front-end core helpers (shared namespace: window.FIN) */
window.FIN = (function () {
  const F = { S: { user: null, ai: false, faq: null, charts: [], sv: null }, views: {} };
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const fmt = (n, d = 0) => (n == null || isNaN(n) ? '–' : Number(n).toLocaleString('en-US', { maximumFractionDigits: d, minimumFractionDigits: d }));
  const vnd = (n) => (n == null ? '–' : fmt(n) + ' VND');
  const pct = (x, d = 1) => (x == null ? 'n/a' : (x * 100).toFixed(d) + '%');
  const dur = (m) => {
    if (m == null) return 'not within 50 years';
    const y = Math.floor(m / 12), mo = Math.round(m % 12);
    return y && mo ? `${y} yr ${mo} mo` : y ? `${y} yr` : mo ? `${mo} mo` : 'already achieved';
  };
  const abbr = (n) => {
    const a = Math.abs(n);
    return (n < 0 ? '-' : '') + (a >= 1e12 ? (a / 1e12).toFixed(1) + 'T' : a >= 1e9 ? (a / 1e9).toFixed(1) + 'B' : a >= 1e6 ? (a / 1e6).toFixed(a >= 1e8 ? 0 : 1) + 'M' : a >= 1e3 ? (a / 1e3).toFixed(0) + 'K' : a.toFixed(0));
  };

  async function api(url, opts = {}) {
    const o = { credentials: 'same-origin', ...opts };
    o.method = (o.method || (o.json !== undefined || o.body ? 'POST' : 'GET')).toUpperCase();
    o.headers = { ...(o.headers || {}) };
    if (o.json !== undefined) { o.headers['Content-Type'] = 'application/json'; o.body = JSON.stringify(o.json); }
    if (o.method !== 'GET') o.headers['X-CSRF-Token'] = F.S.csrf || '';
    let r;
    try { r = await fetch(url, o); } catch (e) { throw new Error('Network error. Please check your connection and try again.'); }
    if (o.raw) return r;
    let d = {};
    try { d = await r.json(); } catch (e) { /* non-JSON */ }
    if (d && d.csrf) F.S.csrf = d.csrf;
    if (!r.ok) { const er = new Error(d.error || 'Something went wrong.'); er.status = r.status; er.data = d; throw er; }
    return d;
  }
  async function download(url, opts, name) {
    const r = await api(url, { ...opts, raw: true });
    if (!r.ok) { let m = 'Export failed.'; try { m = (await r.json()).error || m; } catch (e) {} throw new Error(m); }
    const b = await r.blob(), a = document.createElement('a');
    a.href = URL.createObjectURL(b); a.download = name; document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 4000);
  }
  let tt;
  function toast(msg) { const t = $('#toast'); t.textContent = msg; t.classList.add('show'); clearTimeout(tt); tt = setTimeout(() => t.classList.remove('show'), 3200); }

  /* ---------- icons ---------- */
  const P = {
    user: '<circle cx="12" cy="8" r="4"/><path d="M4 21c0-4 4-6 8-6s8 2 8 6"/>',
    moon: '<path d="M21 13A9 9 0 1 1 11 3a7 7 0 0 0 10 10z"/>',
    sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
    menu: '<path d="M4 6h16M4 12h16M4 18h16"/>',
    home: '<path d="M3 11l9-8 9 8v10a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z"/>',
    account: '<rect x="3" y="4" width="18" height="16" rx="3"/><circle cx="9" cy="11" r="2.5"/><path d="M5.5 17c.5-2 2-3 3.5-3s3 1 3.5 3M15 9h3M15 13h3"/>',
    wallet: '<path d="M3 7a2 2 0 0 1 2-2h13v4"/><path d="M3 7v11a2 2 0 0 0 2 2h15a1 1 0 0 0 1-1V9a1 1 0 0 0-1-1H5a2 2 0 0 1-2-1z"/><circle cx="17" cy="14" r="1.2"/>',
    chart: '<path d="M3 3v18h18"/><path d="M7 15l4-5 3 3 5-7"/>',
    star: '<path d="M12 3l2.8 5.7 6.2.9-4.5 4.4 1 6.2L12 17.2 6.5 20.2l1-6.2L3 9.6l6.2-.9z"/>',
    help: '<circle cx="12" cy="12" r="9"/><path d="M9.5 9.5a2.5 2.5 0 1 1 3.5 2.3c-.7.4-1 .9-1 1.7M12 17h.01"/>',
    left: '<path d="M15 6l-6 6 6 6"/>'
  };
  const icon = (n) => `<svg viewBox="0 0 24 24" aria-hidden="true">${P[n]}</svg>`;

  /* ---------- inputs ---------- */
  function moneyHTML(id, o = {}) {
    return `<div class="field">${o.label ? `<label for="${id}">${o.label}</label>` : ''}${o.example ? `<span class="ex">e.g. ${o.example}</span>` : ''}
      <div class="suffix"><input type="text" inputmode="numeric" autocomplete="off" class="money" id="${id}" value="${o.value != null && o.value !== '' ? fmt(o.value) : ''}" placeholder="${o.placeholder || '0'}"><span>${o.unit || 'VND'}</span></div>${o.hint ? `<span class="hint">${o.hint}</span>` : ''}</div>`;
  }
  /* digits only, never negative, thousands separated by commas as you type */
  function bindMoney(root = document) {
    $$('.money', root).forEach((el) => {
      if (el.dataset.bound) return; el.dataset.bound = 1;
      el.addEventListener('input', () => {
        const pos = el.selectionStart, before = el.value.length;
        const digits = el.value.replace(/\D/g, '').replace(/^0+(?=\d)/, '').slice(0, 15);
        el.value = digits.replace(/\B(?=(\d{3})+(?!\d))/g, ',');
        const np = Math.max(0, pos + (el.value.length - before)); try { el.setSelectionRange(np, np); } catch (e) {}
        el.dispatchEvent(new CustomEvent('money', { bubbles: true }));
      });
    });
    $$('.percent', root).forEach((el) => {
      if (el.dataset.bound) return; el.dataset.bound = 1;
      el.addEventListener('input', () => { let v = el.value.replace(/[^\d.]/g, ''); const i = v.indexOf('.'); if (i >= 0) v = v.slice(0, i + 1) + v.slice(i + 1).replace(/\./g, ''); el.value = v; });
    });
  }
  const num = (id) => { const el = typeof id === 'string' ? $('#' + id) : id; return el ? Number(String(el.value).replace(/,/g, '')) || 0 : 0; };
  const val = (id) => ($('#' + id) ? $('#' + id).value : '');
  const pwField = (id, label, ph = '') => `<div class="field"><label for="${id}">${label}</label><div class="pw"><input type="password" id="${id}" autocomplete="off" placeholder="${ph}"><button type="button" data-show="${id}">Show</button></div></div>`;
  function bindShow(root = document) {
    $$('[data-show]', root).forEach((b) => b.addEventListener('click', () => {
      const i = $('#' + b.dataset.show); const show = i.type === 'password'; i.type = show ? 'text' : 'password'; b.textContent = show ? 'Hide' : 'Show';
    }));
  }
  const stars = (id, value = 0) => `<div class="stars" id="${id}" data-value="${value}">${[1, 2, 3, 4, 5].map((i) => `<button type="button" data-v="${i}" aria-label="${i} star${i > 1 ? 's' : ''}" class="${i <= value ? 'on' : ''}">★</button>`).join('')}</div>`;
  function bindStars(root = document) {
    $$('.stars', root).forEach((s) => s.addEventListener('click', (e) => {
      const b = e.target.closest('button'); if (!b) return; s.dataset.value = b.dataset.v;
      $$('button', s).forEach((x) => x.classList.toggle('on', +x.dataset.v <= +b.dataset.v)); s.dispatchEvent(new CustomEvent('rate', { bubbles: true }));
    }));
  }
  const starMeter = (v) => `<span class="star-meter" aria-label="${v} out of 5 stars">★★★★★<i style="width:${(v / 5) * 100}%">★★★★★</i></span>`;

  /* ---------- markdown (small subset) ---------- */
  function inline(s) { return esc(s).replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>').replace(/\*(.+?)\*/g, '<em>$1</em>').replace(/`(.+?)`/g, '<code>$1</code>'); }
  function md(t) {
    if (!t) return '';
    const out = []; let list = 0;
    const close = () => { while (list > 0) { out.push('</ul>'); list--; } };
    String(t).split('\n').forEach((raw) => {
      const line = raw.replace(/\s+$/, '');
      const m = line.match(/^(\s*)[-*•]\s+(.*)$/);
      if (m) { const lvl = Math.min(Math.floor(m[1].length / 2) + 1, 3); while (list < lvl) { out.push('<ul>'); list++; } while (list > lvl) { out.push('</ul>'); list--; } out.push('<li>' + inline(m[2]) + '</li>'); return; }
      close();
      if (!line.trim()) return;
      const h = line.match(/^#{1,4}\s+(.*)$/);
      out.push(h ? '<h4>' + inline(h[1]) + '</h4>' : '<p>' + inline(line) + '</p>');
    });
    close();
    return '<div class="md">' + out.join('') + '</div>';
  }

  /* ---------- charts ---------- */
  const css = (v) => getComputedStyle(document.documentElement).getPropertyValue(v).trim();
  const COLORS = ['#c94444', '#d9962b', '#2F8A58', '#3b7fb8', '#8a6fc7'];
  function makeChart(id, type, labels, datasets, o = {}) {
    const el = document.getElementById(id); if (!el || !window.Chart) return null;
    const grid = css('--border'), txt = css('--muted');
    const ch = new Chart(el, {
      type, data: { labels, datasets },
      options: {
        responsive: true, maintainAspectRatio: false, interaction: { mode: 'index', intersect: false },
        plugins: { legend: { labels: { color: txt, boxWidth: 14 } }, tooltip: { callbacks: { label: (c) => ` ${c.dataset.label}: ${fmt(c.parsed.y, o.unit === '%' ? 1 : 0)} ${o.unit || 'VND'}` } } },
        scales: { x: { grid: { color: grid }, ticks: { color: txt }, title: o.xTitle ? { display: true, text: o.xTitle, color: txt } : {} },
                  y: { grid: { color: grid }, ticks: { color: txt, callback: (v) => (o.unit === '%' ? v + '%' : abbr(v)) }, title: { display: true, text: o.yTitle || o.unit || 'VND', color: txt } } }
      }
    });
    F.S.charts.push(ch); return ch;
  }
  const killCharts = () => { F.S.charts.forEach((c) => { try { c.destroy(); } catch (e) {} }); F.S.charts = []; };

  const table = (head, rows, cls = '') => `<div class="tbl"><table class="${cls}"><thead><tr>${head.map((h, i) => `<th${i ? ' class="num"' : ''}>${h}</th>`).join('')}</tr></thead><tbody>${rows.map((r) => `<tr>${r.map((c, i) => `<td${i ? ' class="num"' : ''}>${c}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`;
  const badge = (lvl, t) => `<span class="badge ${lvl}">${esc(t)}</span>`;
  const DISCLAIMER = 'FINOVA is a financial planning support platform designed strictly for educational and informational purposes. All calculations, projection charts, and scenario outcomes depend entirely on user-provided information and stated financial assumptions. Results generated by FINOVA are mathematical estimates and decision-support tools, not guarantees of future financial outcomes, certified financial audits, or personalized investment advice. FINOVA does not promise or guarantee investment yields, nor does it recommend purchasing or selling specific financial products, securities, or assets.';

  const banner = (i, title) => `<div class="strip" style="background-image:${window.FINOVA_BG(i)}"><b>${title}</b><small>📍 ${window.FINOVA_SCENES[i % window.FINOVA_SCENES.length].caption}</small></div>`;
  let creditsCache;
  async function loadCredits() {
    const els = $$('.credits'); if (!els.length) return;
    if (creditsCache === undefined) { try { const r = await fetch('/static/img/scenes/credits.json'); creditsCache = r.ok ? await r.json() : null; } catch (e) { creditsCache = null; } }
    const html = creditsCache && Object.keys(creditsCache).length ? 'Photos: ' + Object.entries(creditsCache).map(([k, c]) => `<a href="${esc(c.page)}" target="_blank" rel="noopener">${esc(window.FINOVA_SCENES[k - 1].caption.split(',')[0])}</a> by ${esc(c.artist)} (${esc(c.license)})`).join(' · ') + ' — via Wikimedia Commons' : '';
    els.forEach((e) => (e.innerHTML = html));
  }
  Object.assign(F, { banner, loadCredits, $, $$, esc, fmt, vnd, pct, dur, abbr, api, download, toast, icon, moneyHTML, bindMoney, num, val, pwField, bindShow, stars, bindStars, starMeter, md, makeChart, killCharts, table, badge, COLORS, DISCLAIMER });
  return F;
})();
