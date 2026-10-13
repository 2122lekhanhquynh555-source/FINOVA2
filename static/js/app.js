/* FINOVA app shell: layout, theme, guide, router */
(function (F) {
  const { $, $$, esc, api, icon, toast } = F;
  const S = F.S;
  const PUBLIC = ['', 'register', 'login', 'forgot'];
  const NAV = [['overview', 'Overview', 'home'], ['account', 'Customer Account', 'account'], ['finance', 'Financial Information', 'wallet'],
    ['savings', 'Savings & Investment', 'chart'], ['evaluation', 'Evaluation', 'star'], ['support', 'Contact & Support', 'help']];
  const APP = ['overview', 'account', 'finance', 'results', 'savings', 'evaluation', 'support'];

  /* ---------- theme ---------- */
  function setTheme(t, rerender) {
    document.documentElement.setAttribute('data-theme', t);
    try { localStorage.setItem('finova-theme', t); } catch (e) {}
    $('#themeBtn').innerHTML = icon(t === 'dark' ? 'sun' : 'moon');
    $('#themeBtn').title = t === 'dark' ? 'Switch to light mode' : 'Switch to dark mode';
    if (rerender) route();
  }
  $('#themeBtn').onclick = () => setTheme(document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark', true);

  /* ---------- header / sidebar ---------- */
  function drawChrome() {
    const u = S.user;
    document.body.classList.toggle('app', !!u);
    $('#userBtn').innerHTML = icon('user') + '<span class="dot" id="userDot"' + (u ? '' : ' hidden') + '></span>';
    $('#menuBtn').innerHTML = icon('menu');
    $('#brand').setAttribute('href', u ? '#/overview' : '#/');
    $('#userDrop').innerHTML = u
      ? `<div class="who">${esc(u.name)}<small>${esc(u.email)}</small></div><button id="logout">Log out</button>`
      : '<a href="#/register">Register</a><a href="#/login">Log in</a>';
    if (u) $('#logout').onclick = async () => { await api('/api/logout', { method: 'POST' }); S.user = null; S.sv = null; S.faq = null; drawChrome(); location.hash = '#/'; toast('You have been logged out.'); };
    $('#sidebar').innerHTML = u ? `<a href="#" id="collapse" title="Close the toolbar">${icon('left')}<span>Close toolbar</span></a>` + NAV.map(([id, label, ic]) => `<a href="#/${id}" data-r="${id}">${icon(ic)}<span>${label}</span></a>`).join('') : '';
    if (u) $('#collapse').onclick = (e) => { e.preventDefault(); toggleMenu(); };
  }
  function toggleMenu() {
    const b = document.body;
    if (window.innerWidth <= 860) b.classList.toggle('menu-open'); else b.classList.toggle('collapsed');
  }
  $('#menuBtn').onclick = toggleMenu; $('#scrim').onclick = () => document.body.classList.remove('menu-open');
  $('#userBtn').onclick = (e) => { e.stopPropagation(); $('#userMenu').classList.toggle('open'); };
  document.addEventListener('click', (e) => { if (!e.target.closest('#userMenu')) $('#userMenu').classList.remove('open'); });
  $('#userDrop').addEventListener('click', () => $('#userMenu').classList.remove('open'));

  F.setUser = (u, go) => { S.user = u; S.sv = null; drawChrome(); if (go) location.hash = '#/overview'; else route(); };

  /* ---------- guide ---------- */
  const GUIDE = `<h3>Create an account</h3><ol><li>Move your mouse over the <b>person icon</b> in the top-right corner (on a phone, tap it).</li><li>Choose <b>Register</b>.</li><li>Enter your <b>full name</b>, <b>email</b>, a <b>password</b> (at least 8 characters, with letters and numbers) and the same password again.</li><li>Click <b>Register</b>. You are signed in automatically and a green dot appears on the person icon.</li></ol>
  <h3>Log in</h3><ol><li>Hover over (or tap) the <b>person icon</b>.</li><li>Choose <b>Log in</b>.</li><li>Type the <b>email</b> and <b>password</b> you registered with. Use <b>Show</b> to check what you typed.</li><li>Click <b>Log in</b>. You return to the home page and your name appears in the account menu.</li></ol>
  <h3>Forgot your password</h3><ol><li>On the Log in page, click <b>Forgot password?</b></li><li>Enter your registered email and click <b>Verify email</b>.</li><li>Type a new password twice and click <b>Save new password</b>.</li><li>Log in with the new password.</li></ol>
  <h3>Log out</h3><ol><li>Hover over (or tap) the <b>person icon</b>. Your name is shown at the top of the menu.</li><li>Click <b>Log out</b>. Your session ends immediately.</li></ol><p>On a shared computer, always log out when you finish.</p>
  <h3>Light and dark mode</h3><ol><li>Click the <b>moon icon</b> to switch to dark mode. It turns into a sun.</li><li>Click the <b>sun icon</b> to return to light mode.</li></ol>`;
  $('#guideBody').innerHTML = GUIDE;
  const gm = $('#guideModal');
  $('#guideBtn').onclick = () => (gm.hidden = false); $('#guideClose').onclick = () => (gm.hidden = true);
  gm.onclick = (e) => { if (e.target === gm) gm.hidden = true; };
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape') gm.hidden = true; });

  /* ---------- router ---------- */
  function route() {
    if (F.onLeave) { F.onLeave(); F.onLeave = null; }
    F.killCharts();
    let r = (location.hash.replace(/^#\/?/, '') || '').split('?')[0];
    if (r === 'features') return;
    if (S.user && PUBLIC.includes(r)) return (location.hash = '#/overview');
    if (!S.user && APP.includes(r)) return (location.hash = '#/login');
    const name = r === '' ? 'home' : r;
    if (!F.views[name]) return (location.hash = S.user ? '#/overview' : '#/');
    $$('.sidebar a[data-r]').forEach((a) => a.classList.toggle('active', a.dataset.r === (r === 'results' ? 'finance' : r)));
    document.body.classList.remove('menu-open');
    const root = $('#view'); root.scrollTop = 0; window.scrollTo(0, 0);
    Promise.resolve(F.views[name](root)).then(() => { if (!$('.credits')) root.insertAdjacentHTML('beforeend', '<div class="footer"><div class="credits" style="font-size:.78rem"></div></div>'); return F.loadCredits(); }).catch((e) => { root.innerHTML = `<div class="pad"><div class="msg err">${esc(e.message || 'Something went wrong.')}</div></div>`; });
  }
  window.addEventListener('hashchange', route);

  (async function boot() {
    setTheme(document.documentElement.getAttribute('data-theme') || 'light');
    try { const me = await api('/api/me'); S.user = me.user; S.csrf = me.csrf; const cfg = await api('/api/config'); S.ai = cfg.ai_enabled; S.demoReset = cfg.demo_reset; } catch (e) {}
    drawChrome(); route();
  })();
})(window.FIN);
