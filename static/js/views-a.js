/* Views A: public home, auth, overview, account, financial information, results */
(function (F) {
  const { $, $$, esc, fmt, vnd, pct, dur, api, toast, md, table, badge } = F;
  const V = F.views;

  const FEATURES_SHORT = [
    ['Intelligent Profile & Goal Parsing', 'Instantly structure your financial profile—income, expenses, assets, liabilities, time horizon, and risk tolerance—from natural language while automatically highlighting missing details.', '🧠'],
    ['Multi-Scenario Cash Flow Modeling', 'Compare three distinct financial trajectories (Baseline, Conservative, and Optimistic) powered by precise mathematical calculation models rather than unpredictable AI guesses.', '📈'],
    ['Real-Time "What-If" & Stress Testing', 'Interactively adjust savings rates, target deadlines, or simulate economic shocks (such as a sudden income drop or expense surge) to evaluate your financial resilience in real time.', '🎛️'],
    ['AI Trade-Off & Risk Insights', 'Receive clear, objective AI explanations detailing potential trade-offs, risk limits, and opportunity costs across scenarios—helping you make confident, well-informed decisions.', '💡']
  ];
  const FEATURES = [
    ['01', 'Intelligent Financial Analysis', 'Smart Data Parsing & Financial Health Check', '🧠',
      'Organize your raw financial information effortlessly. FINOVA extracts and structures your income, expenses, cash flow, assets, and liabilities from natural language inputs or user profiles. Before running calculations, the system automatically identifies missing or conflicting data, ensuring your financial baseline is complete and accurate.',
      ['Automated Profile & Goal Normalization', 'Missing Data & Constraint Detection (Guardrails)', 'Comprehensive Monthly Cash-Flow Assessment']],
    ['02', 'Multi-Scenario Planning', 'Simulate 5 Distinct Financial Trajectories', '📈',
      'Never rely on a single optimistic projection. FINOVA generates and compares three mathematical scenarios simultaneously: <strong>Conservative</strong>, <strong>Baseline</strong>, and <strong>Optimistic</strong>. Powered by exact calculation algorithms rather than AI estimation, you can visualize precise timelines for reaching your target goals under varying financial conditions.',
      ['3-Pathway Wealth Projection Charts', 'Deterministic Mathematical Cash-Flow Engine', 'Clear Goal Feasibility Timelines']],
    ['03', 'What-If Analysis & Stress Testing', 'Interactive Modeling & Risk Resilience Check', '🎛️',
      'Take full control of your assumptions. Use interactive sliders to adjust savings rates, target deadlines, or expected yields in real time and see immediate live updates to your goal progress. Activate <strong>Financial Stress Testing</strong> to simulate economic shocks—such as a 20% income reduction or unexpected expense surges—to measure your portfolio\'s true resilience.',
      ['Real-Time Parameter Sliders (Savings, Timeline, Returns)', 'One-Click Income & Expense Shock Simulations', 'Instant Visual Feasibility Adjustments']],
    ['04', 'AI-Powered Financial Insights', 'Objective Trade-off Explanations & Risk Guidance', '💡',
      'Understand the logic behind the numbers. FINOVA’s AI acts as an objective advisor, explaining the trade-offs between different choices (e.g., reaching a goal 2 years earlier vs. increasing monthly savings). It highlights key risk factors, financial bottlenecks, and strategy alternatives without making deceptive promises or selling financial products.',
      ['Plain-Language Trade-Off Explanations', 'Transparent Assumption Auditing', 'Zero Hallucination & Objective Educational Focus']]
  ];
  const disclaimerBox = (long) => `<div class="disclaimer"><h4>⚖️ DISCLAIMER &amp; SAFETY NOTICE</h4><p style="margin:0">${long ? F.DISCLAIMER : '<strong>Disclaimer:</strong> FINOVA is a financial planning support platform designed strictly for educational and informational purposes. All calculation models and scenario projections rely entirely on user-provided data and underlying assumptions. They serve as estimated benchmarks, not guaranteed financial outcomes or personalized investment advice. FINOVA does not offer guaranteed yields or recommend specific securities.'}</p></div>`;
  const PH = (i) => `<div class="bgph" style="background-image:${FINOVA_BG(i)}"></div>`;
  const gallery = (t) => `<h2 style="margin-top:46px">${t}</h2><div class="gallery">${FINOVA_SCENES.map((s, i) => `<div class="ph" style="background-image:${FINOVA_BG(i)}"><span>📍 ${s.caption}</span></div>`).join('')}</div>`;
  const footer = '<div class="footer">© FINOVA · Group 7 · Educational use only<div class="credits" style="font-size:.78rem;margin-top:6px"></div></div>';
  const msgBox = (el, text, ok) => { el.innerHTML = text ? `<div class="msg ${ok ? 'ok' : 'err'}">${esc(text)}</div>` : ''; };

  /* ================= public home ================= */
  V.home = (root) => {
    root.innerHTML = `
    <section class="hero"><div class="bg" style="background-image:${FINOVA_BG(0)}"></div>
      <span class="eyebrow">Your Financial Goals. Your Plan. Your Future.</span>
      <h1>FINOVA — Plan Smarter. Achieve Your Goals.</h1>
      <p>FINOVA is an intelligent personal finance planning platform that transforms complex financial ambitions into clear, actionable roadmaps.</p>
      <p>By seamlessly integrating AI-driven goal parsing with a deterministic financial calculation engine, FINOVA helps you evaluate your financial health, model multi-scenario cash flows, and stress-test your strategy against real-world changes in income, savings rates, and market assumptions.</p>
      <p><strong>Plan with clarity. Explore your scenarios. Take total control of your financial future.</strong></p>
      <div class="cta"><a class="btn light" href="#/register">Get started ↗</a><a class="btn ghost" href="#features" id="explore">Explore FINOVA</a></div>
    </section>
    <section class="section" id="features"><h2>What can FINOVA do for you?</h2>
      <div class="grid2">${FEATURES_SHORT.map((f) => `<div class="card feature"><div class="ico">${f[2]}</div><h3>${f[0]}</h3><p>${f[1]}</p></div>`).join('')}</div>
      ${gallery('Discover Vietnam')}${disclaimerBox(false)}</section>${footer}`;
    $('#explore').onclick = (e) => { e.preventDefault(); $('#features').scrollIntoView({ behavior: 'smooth' }); };
  };

  /* ================= auth ================= */
  V.register = (root) => {
    root.innerHTML = `<div class="auth-wrap">${PH(2)}<form class="auth-card" id="f" novalidate><h2>Create your account</h2><p class="sub">Register to start planning with FINOVA.</p><div id="m"></div>
      <div class="field"><label for="n">Full name</label><input type="text" id="n" autocomplete="name"></div>
      <div class="field"><label for="e">Email</label><input type="email" id="e" autocomplete="email"></div>
      ${F.pwField('p', 'Password')}<span class="hint" style="display:block;margin:-10px 0 14px;color:var(--muted);font-size:.82rem">Use at least 8 characters with letters and numbers.</span>
      ${F.pwField('c', 'Confirm password')}
      <div class="center"><button class="btn" id="go" type="submit">Register</button></div>
      <p class="alt">Already have an account? <a href="#/login">Log in</a></p><p class="alt"><a href="#/">← Back to home</a></p></form></div>${footer}`;
    F.bindShow(root);
    $('#f').onsubmit = async (e) => {
      e.preventDefault(); const b = $('#go'); b.disabled = true;
      try { const d = await api('/api/register', { json: { name: F.val('n'), email: F.val('e'), password: F.val('p'), confirm: F.val('c') } }); FIN.setUser(d.user, true); toast('Welcome to FINOVA, ' + d.user.name + '!'); }
      catch (er) { msgBox($('#m'), er.message); b.disabled = false; }
    };
  };
  V.login = (root) => {
    root.innerHTML = `<div class="auth-wrap">${PH(3)}<form class="auth-card" id="f" novalidate><h2>Welcome back</h2><p class="sub">Log in to continue your financial plan.</p><div id="m"></div>
      <div class="field"><label for="e">Email</label><input type="email" id="e" autocomplete="email"></div>
      ${F.pwField('p', 'Password')}
      <p style="margin:-6px 0 16px;text-align:right"><a href="#/forgot">Forgot password?</a></p>
      <div class="center"><button class="btn" id="go" type="submit">Log in</button></div>
      <p class="alt">New to FINOVA? <a href="#/register">Register</a></p><p class="alt"><a href="#/">← Back to home</a></p></form></div>${footer}`;
    F.bindShow(root);
    $('#f').onsubmit = async (e) => {
      e.preventDefault(); const b = $('#go'); b.disabled = true;
      try { const d = await api('/api/login', { json: { email: F.val('e'), password: F.val('p') } }); FIN.setUser(d.user, true); toast('Logged in as ' + d.user.name); }
      catch (er) { msgBox($('#m'), er.message); b.disabled = false; }
    };
  };
  V.forgot = (root) => {
    root.innerHTML = `<div class="auth-wrap">${PH(4)}<div class="auth-card"><h2>Reset your password</h2><p class="sub" id="sub">Step 1 of 2: enter your registered email. We send a 6-digit code to it.</p><div id="m"></div>
      <form id="s1" novalidate><div class="field"><label for="e">Email</label><input type="email" id="e" autocomplete="email"></div><div class="center"><button class="btn" type="submit">Send verification code</button></div></form>
      <form id="s2" novalidate hidden><div class="field"><label for="cd">6-digit verification code</label><input type="text" id="cd" inputmode="numeric" maxlength="6" autocomplete="one-time-code"></div>${F.pwField('p', 'New password')}<span class="hint" style="display:block;margin:-10px 0 14px;color:var(--muted);font-size:.82rem">Use at least 8 characters with letters and numbers. The code expires in 10 minutes.</span>${F.pwField('c', 'Confirm new password')}<div class="center"><button class="btn" type="submit">Save new password</button></div></form>
      <p class="alt"><a href="#/login">← Back to log in</a></p></div></div>${footer}`;
    F.bindShow(root);
    $('#s1').onsubmit = async (e) => {
      e.preventDefault();
      try {
        const r = await api('/api/forgot/verify', { json: { email: F.val('e') } });
        $('#s1').hidden = true; $('#s2').hidden = false; $('#sub').textContent = 'Step 2 of 2: enter the code and choose a new password.';
        $('#m').innerHTML = `<div class="msg ok">${esc(r.message)}</div>` + (r.demo_code ? `<div class="notice warn"><b>Demo mode:</b> email delivery is not configured on this server, so your code is shown here: <b>${esc(r.demo_code)}</b></div>` : '');
      } catch (er) { msgBox($('#m'), er.message); }
    };
    $('#s2').onsubmit = async (e) => { e.preventDefault(); try { await api('/api/forgot/reset', { json: { email: F.val('e'), code: F.val('cd'), password: F.val('p'), confirm: F.val('c') } }); toast('Password updated. Please log in.'); location.hash = '#/login'; } catch (er) { msgBox($('#m'), er.message); } };
  };

  /* ================= overview ================= */
  V.overview = (root) => {
    const sc = FINOVA_SCENES.slice(0, 5);
    root.innerHTML = `
    <div class="carousel" id="car">${sc.map((s, i) => `<div class="slide${i ? '' : ' on'}" style="background-image:${FINOVA_BG(i)}"></div>`).join('')}
      <div class="over"><h1>GOAL-BASED PERSONAL FINANCE PLANNING ENGINE</h1></div>
      <div class="cap" id="cap">📍 ${sc[0].caption}</div><div class="dots">${sc.map((_, i) => `<button class="${i ? '' : 'on'}" aria-label="Slide ${i + 1}"></button>`).join('')}</div></div>
    <section class="hero light">
      <span class="eyebrow">Your Financial Goals. Your Plan. Your Future.</span>
      <h1>FINOVA — Plan Smarter. Achieve Your Goals.</h1>
      <p><strong>FINOVA</strong> is an intelligent personal finance planning platform designed to help individuals understand their current financial health and transform ambitious financial goals into realistic, actionable roadmaps.</p>
      <p>By seamlessly combining <strong>Artificial Intelligence (AI)</strong> with a <strong>deterministic financial calculation engine</strong>, FINOVA <strong>analyzes</strong> your income, expenses, savings, assets, and liabilities. The platform evaluates your overall financial capacity, detects missing data, and rigorously assesses the feasibility of your long-term goals—such as buying a home, funding education, or preparing for retirement.</p>
      <p>Through dynamic <strong>multi-scenario modeling</strong>, <strong>interactive what-if analysis</strong>, and <strong>financial stress testing</strong>, FINOVA empowers you to explore how real-world changes—in income, savings rates, inflation, or unexpected expenses—impact your financial timeline.</p>
      <p>Beyond numbers, FINOVA leverages AI to provide clear, objective explanations of <strong>financial trade-offs</strong>, potential risks, and alternative strategies—enabling you to make confident, well-informed decisions.</p>
      <p><strong>Plan with clarity. Explore your options. Build your financial future with FINOVA.</strong></p>
      <div class="cta"><a class="btn light" href="#/finance">🚀 Start Planning Your Goals</a><a class="btn ghost" href="#demo" id="tryDemo">📊 Try Demo Scenario</a></div>
      <div class="card" style="max-width:720px;margin:34px auto 0;text-align:left;color:var(--text)"><div class="flex"><b>Dashboard preview</b><span class="muted right">sample data</span></div>
        <div class="grid3" style="margin:12px 0"><div class="stat"><small>Net worth</small><b>1,250,000,000</b></div><div class="stat"><small>Savings rate</small><b>24.0%</b></div><div class="stat"><small>Goal progress</small><b>68%</b></div></div>
        <svg viewBox="0 0 400 80" style="width:100%;height:80px"><polyline fill="none" stroke="#2F8A58" stroke-width="4" stroke-linecap="round" points="0,70 50,62 100,58 150,48 200,44 250,30 300,24 350,14 400,6"/><polyline fill="none" stroke="#d98a00" stroke-width="3" stroke-dasharray="6 6" points="0,70 100,66 200,60 300,52 400,44"/></svg></div>
    </section>
    <section class="section"><h2>What Can FINOVA Do for You?</h2>
      <div class="grid2">${FEATURES.map((f) => `<div class="card feature"><div class="ico">${f[3]}</div><div class="num">${f[0]}</div><h3>${f[1]}</h3><h4>${f[2]}</h4><p>${f[4]}</p><ul>${f[5].map((x) => `<li>${x}</li>`).join('')}</ul></div>`).join('')}</div></section>
    <section class="section">${gallery('Discover Vietnam')}</section>
    <section class="section" id="demo"><h2>Interactive Demo</h2>
      <div class="card demo"><div><p class="muted" style="margin-top:0">Sample profile: monthly income of 25,000,000 VND. Move the sliders to feel how “what-if” planning works.</p>
        <div class="slider-row"><div class="top"><span>Savings rate</span><span id="dv1"></span></div><input type="range" id="s1" min="0" max="60" step="1" value="20"></div>
        <div class="slider-row"><div class="top"><span>Time horizon</span><span id="dv2"></span></div><input type="range" id="s2" min="1" max="30" step="1" value="10"></div>
        <div class="slider-row"><div class="top"><span>Assumed annual return (simulated)</span><span id="dv3"></span></div><input type="range" id="s3" min="0" max="15" step="0.5" value="6"></div>
        <div class="stat"><small>Projected balance (hypothetical)</small><span class="big" id="dout"></span></div></div>
        <div class="chart-box"><canvas id="demoChart"></canvas></div></div></section>
    <section class="section">${disclaimerBox(true)}</section>${footer}`;
    // carousel: 5 slides, one at a time, every 5 seconds, looping
    let i = 0; const slides = $$('.slide', root), dots = $$('.dots button', root);
    const show = (n) => { i = (n + slides.length) % slides.length; slides.forEach((s, k) => s.classList.toggle('on', k === i)); dots.forEach((d, k) => d.classList.toggle('on', k === i)); $('#cap').textContent = '📍 ' + sc[i].caption; };
    dots.forEach((d, k) => (d.onclick = () => { show(k); reset(); }));
    let timer; const reset = () => { clearInterval(timer); timer = setInterval(() => show(i + 1), 5000); }; reset();
    FIN.onLeave = () => clearInterval(timer);
    $('#tryDemo').onclick = (e) => { e.preventDefault(); $('#demo').scrollIntoView({ behavior: 'smooth' }); };
    // demo chart
    const calc = () => {
      const rate = +$('#s1').value / 100, yrs = +$('#s2').value, ret = +$('#s3').value / 100, mS = 25e6 * rate, r = ret / 12;
      const pts = [], flat = [];
      for (let y = 0; y <= yrs; y++) { const n = y * 12; pts.push(r ? mS * ((1 + r) ** n - 1) / r : mS * n); flat.push(mS * n); }
      $('#dv1').textContent = (rate * 100).toFixed(0) + '% (' + fmt(mS) + ' VND/mo)'; $('#dv2').textContent = yrs + ' years'; $('#dv3').textContent = (ret * 100).toFixed(1) + '%';
      $('#dout').textContent = fmt(pts[yrs]) + ' VND';
      return { pts, flat, labels: pts.map((_, y) => y) };
    };
    let d = calc();
    const ch = F.makeChart('demoChart', 'line', d.labels, [
      { label: 'With assumed return', data: d.pts, borderColor: '#2F8A58', backgroundColor: 'rgba(47,138,88,.15)', fill: true, tension: .3, pointRadius: 0 },
      { label: 'Savings only (0% return)', data: d.flat, borderColor: '#d98a00', borderDash: [6, 6], tension: .3, pointRadius: 0 }], { xTitle: 'Years' });
    ['s1', 's2', 's3'].forEach((id) => ($('#' + id).oninput = () => { d = calc(); if (!ch) return; ch.data.labels = d.labels; ch.data.datasets[0].data = d.pts; ch.data.datasets[1].data = d.flat; ch.update(); }));
  };

  /* ================= account ================= */
  V.account = (root) => {
    const u = F.S.user;
    root.innerHTML = `<div class="pad">${F.banner(3, 'Customer Account')}<h1 class="page-title">Customer Account</h1><p class="page-sub">Information entered when you created your account. Update it any time.</p>
    <div class="card"><div id="m"></div><form id="f" novalidate><div class="form-grid">
      <div class="field"><label for="n">Full name</label><input type="text" id="n" value="${esc(u.name)}"></div>
      <div class="field"><label for="e">Email</label><input type="email" id="e" value="${esc(u.email)}"></div>
      <div class="field"><label for="a">Age</label><input type="number" id="a" min="1" max="120" step="1" value="${u.age ?? ''}" placeholder="e.g. 28"></div>
      <div class="field"><label>Gender</label><div class="seg">${['Male', 'Female', 'Other'].map((g) => `<label><input type="radio" name="g" value="${g}" ${u.gender === g ? 'checked' : ''}>${g}</label>`).join('')}</div></div>
      <div class="field"><label for="c">Country</label><input type="text" id="c" value="${esc(u.country || '')}" placeholder="e.g. Vietnam"></div>
      <div class="field"><label for="pv">Province / City</label><input type="text" id="pv" value="${esc(u.province || '')}" placeholder="e.g. Ho Chi Minh City"></div>
      <div class="field"><label for="ph">Phone number <span class="muted">(optional)</span></label><input type="tel" id="ph" value="${esc(u.phone || '')}" placeholder="e.g. 0901 234 567"></div>
      <div class="field"><label for="o">Occupation</label><input type="text" id="o" value="${esc(u.occupation || '')}" placeholder="e.g. Software engineer"></div></div>
      <button class="btn" type="submit">Update information</button></form></div>
    <div class="card" style="margin-top:22px"><h3>Change password</h3><div id="pm"></div><form id="pf" novalidate><div class="form-grid">${F.pwField('po', 'Old password')}<div></div>${F.pwField('pn', 'New password')}${F.pwField('pc', 'Re-enter new password')}</div><button class="btn" type="submit">Change password</button></form></div></div>`;
    F.bindShow(root);
    $('#f').onsubmit = async (e) => {
      e.preventDefault(); const g = $('input[name=g]:checked');
      try { const d = await api('/api/profile', { method: 'PUT', json: { name: F.val('n'), email: F.val('e'), age: F.val('a'), gender: g ? g.value : '', country: F.val('c'), province: F.val('pv'), phone: F.val('ph'), occupation: F.val('o') } }); FIN.setUser(d.user); msgBox($('#m'), 'Your information was updated.', true); }
      catch (er) { msgBox($('#m'), er.message); }
    };
    $('#pf').onsubmit = async (e) => {
      e.preventDefault();
      try { await api('/api/password', { json: { old: F.val('po'), new: F.val('pn'), confirm: F.val('pc') } }); msgBox($('#pm'), 'Password changed successfully.', true); $('#pf').reset(); }
      catch (er) { msgBox($('#pm'), er.message); }
    };
  };

  /* ================= financial information ================= */
  const FIELDS = [
    ['income', 'Monthly income', '25,000,000', 'Salary, business and other regular income per month'],
    ['expenses', 'Monthly expenses', '12,000,000', 'Rent, food, transport, utilities and other living costs per month'],
    ['investments', 'Investments', '50,000,000', 'Current value of funds, stocks, gold or similar holdings'],
    ['assets', 'Assets', '120,000,000', 'Cash, savings and other liquid assets you own'],
    ['debt', 'Total current debt', '80,000,000', 'Remaining balance of all loans and credit cards'],
    ['debt_payment', 'Monthly debt payment', '3,000,000', 'What you pay toward debts every month']];
  const S_ai = () => F.S.ai;
  const showIssues = (list) => (list && list.length ? `<ul>${list.map((i) => `<li>${i.level === 'error' ? '⛔' : '⚠️'} ${esc(i.msg)}</li>`).join('')}</ul>` : '');
  const seg = (name, v) => `<div class="seg">${[['low', 'Low'], ['medium', 'Medium'], ['high', 'High']].map(([k, l]) => `<label><input type="radio" name="${name}" value="${k}" ${v === k ? 'checked' : ''}>${l}</label>`).join('')}</div>`;
  V.finance = async (root) => {
    let f = {}; try { f = (await api('/api/finance')).finance || {}; } catch (e) {}
    root.innerHTML = `<div class="pad">${F.banner(2, 'Financial Information')}<h1 class="page-title">Financial Information</h1><p class="page-sub">Enter your numbers in VND. Only 0 or positive amounts are accepted; thousands are separated by commas automatically (for example 5,000,000).</p>
    <div class="notice">💡 Not sure what to type? Each box shows a small example above it. Use 0 for anything that does not apply. You can also upload your data from Excel.</div>
    <div class="card" style="margin-bottom:22px"><h3 style="margin-top:0">✨ Describe your finances in your own words</h3><p class="muted" style="margin-top:0">AI reads your text (English or Vietnamese) and fills the form. Python then validates every value, and a number is accepted only if it appears in your text. Example: <i>I earn 25 million a month, spend 12 million, have 120 million in savings and a 80 million loan paying 3 million a month at 8%.</i></p>
      <textarea id="aiText" rows="3" maxlength="4000" placeholder="Type or paste a short description…"></textarea><div class="row-actions" style="margin-top:10px"><button class="btn small" id="aiParse" type="button">Fill the form with AI</button>${S_ai() ? '' : '<span class="muted">The AI model is not configured on this server.</span>'}</div><div id="aiOut" style="margin-top:10px"></div></div>
    <div class="card"><div id="m"></div><form id="f" novalidate><div class="form-grid">
      ${FIELDS.slice(0, 2).map(([k, l, ex, h]) => F.moneyHTML(k, { label: `${l} (VND/month)`, value: f[k], example: ex + ' VND per month', hint: h })).join('')}
      ${F.moneyHTML('investments', { label: 'Investments (VND)', value: f.investments, example: '50,000,000 VND', hint: FIELDS[2][3] })}
      ${F.moneyHTML('assets', { label: 'Assets (VND)', value: f.assets, example: '120,000,000 VND', hint: FIELDS[3][3] })}
      ${F.moneyHTML('debt', { label: 'Total current debt (VND)', value: f.debt, example: '80,000,000 VND', hint: FIELDS[4][3] })}
      ${F.moneyHTML('debt_payment', { label: 'Monthly debt payment (VND/month)', value: f.debt_payment, example: '3,000,000 VND per month', hint: FIELDS[5][3] })}
      <div class="field"><label for="debt_rate">Average debt interest rate (% per year) <span class="muted">(optional)</span></label><span class="ex">e.g. 8 for a loan at 8% per year; leave 0 if unknown</span><div class="suffix"><input type="text" inputmode="decimal" class="percent" id="debt_rate" value="${f.debt_rate ?? 0}"><span>% / yr</span></div><span class="hint">Used to model how your debt is repaid.</span></div>
      <div class="field" style="grid-column:1/-1"><label>Time horizon: <b id="yv">${f.years || 10}</b> years</label><span class="ex">e.g. 10 years for a home down-payment</span><input type="range" id="years" min="1" max="30" step="1" value="${f.years || 10}"><div class="flex muted" style="justify-content:space-between;font-size:.82rem"><span>1 year</span><span>30 years</span></div></div>
      <div class="field"><label>Liquidity need</label><span class="ex">e.g. Medium if you may need cash within a year</span>${seg('liquidity', f.liquidity || 'medium')}</div>
      <div class="field"><label>Risk level</label><span class="ex">e.g. Low if losses would worry you</span>${seg('risk', f.risk || 'medium')}</div></div>
      <div class="row-actions"><button class="btn ghost" type="button" id="save">💾 Save</button><button class="btn" type="submit">Confirm &amp; view results →</button></div></form></div>
    <div class="card" style="margin-top:22px"><h3>Excel import</h3><p class="muted">Download the template, fill in the Value column, then upload it. FINOVA parses the file and validates every field before filling the form.</p>
      <div class="row-actions" style="margin-top:6px"><button class="btn ghost small" id="tpl" type="button">⬇ Download Excel template</button><button class="btn ghost small" id="up" type="button">⬆ Upload Excel</button><input type="file" id="file" accept=".xlsx" hidden></div><div id="im" style="margin-top:12px"></div></div></div>`;
    F.bindMoney(root);
    $('#years').oninput = () => ($('#yv').textContent = $('#years').value);
    const read = () => ({ income: F.num('income'), expenses: F.num('expenses'), investments: F.num('investments'), assets: F.num('assets'), debt: F.num('debt'), debt_payment: F.num('debt_payment'), debt_rate: Number(F.val('debt_rate')) || 0,
      years: +$('#years').value, liquidity: $('input[name=liquidity]:checked').value, risk: $('input[name=risk]:checked').value });
    const save = async () => api('/api/finance', { method: 'PUT', json: read() });
    $('#save').onclick = async () => { try { const r = await save(); $('#m').innerHTML = `<div class="msg ok">Your financial information was saved.${showIssues(r.issues)}</div>`; } catch (e) { msgBox($('#m'), e.message); } };
    $('#f').onsubmit = async (e) => {
      e.preventDefault(); const d = read();
      if (!d.income && !d.expenses) return msgBox($('#m'), 'Please enter at least your monthly income or monthly expenses.');
      if (d.debt_payment && !d.income) return msgBox($('#m'), 'Debt payments were entered without any income. Please add your monthly income.');
      try { await save(); location.hash = '#/results'; } catch (er) { msgBox($('#m'), er.message); }
    };
    $('#tpl').onclick = () => F.download('/api/finance/template', {}, 'finova_input_template.xlsx').catch((e) => toast(e.message));
    $('#up').onclick = () => $('#file').click();
    const fillForm = (data) => Object.entries(data).forEach(([k, v]) => {
      if (k === 'years') { $('#years').value = Math.round(v); $('#yv').textContent = Math.round(v); }
      else if (k === 'liquidity' || k === 'risk') { const el = $(`input[name=${k}][value=${v}]`); if (el) el.checked = true; }
      else if (k === 'debt_rate') $('#debt_rate').value = v;
      else if ($('#' + k)) $('#' + k).value = fmt(v);
    });
    $('#aiParse').onclick = async () => {
      const out = $('#aiOut'); out.innerHTML = '<span class="loader"></span> Reading your description…';
      try {
        const r = await api('/api/ai/parse', { json: { text: F.val('aiText') } }); fillForm(r.fields);
        const names = Object.keys(r.fields);
        out.innerHTML = `<div class="msg ${names.length ? 'ok' : 'err'}">${names.length ? 'Filled ' + names.length + ' field(s): ' + names.join(', ') + '. Please review and save.' : 'No values could be verified in your text.'}` +
          (r.rejected.length ? `<br>Not accepted (not found in your text): ${r.rejected.join(', ')}` : '') + (r.missing.length ? `<br>Still missing: ${r.missing.join(', ')}` : '') + showIssues(r.issues) +
          (r.unclear.length ? `<br>Unclear: ${r.unclear.map(esc).join('; ')}` : '') + (r.questions.length ? `<br>The AI suggests clarifying: ${r.questions.map(esc).join(' ')}` : '') + '</div>';
      } catch (e) { out.innerHTML = `<div class="msg err">${esc(e.message)} You can still fill in the form manually.</div>`; }
    };
    $('#file').onchange = async () => {
      const fl = $('#file').files[0]; if (!fl) return; const fd = new FormData(); fd.append('file', fl);
      $('#im').innerHTML = '<span class="loader"></span> Reading the file…';
      try {
        const r = await api('/api/finance/import', { method: 'POST', body: fd }); fillForm(r.data);
        const li = (a) => a.map((x) => `<li>${esc(x)}</li>`).join(''), ai = r.ai || {};
        const bad = r.warnings.length || r.missing.length || r.issues.length;
        $('#im').innerHTML = `<div class="msg ${bad ? 'err' : 'ok'}">Imported ${Object.keys(r.data).length} field(s). Review the form, then save.<ul>${li(r.warnings)}${r.missing.length ? `<li>Missing fields: ${r.missing.join(', ')}</li>` : ''}${r.unrecognized.length ? `<li>Unrecognized rows: ${r.unrecognized.map((u) => esc(u.label)).join(', ')}</li>` : ''}</ul>${showIssues(r.issues)}
          ${ai.status === 'ok' ? `<b>AI review (validated by Python):</b><ul>${Object.keys(ai.applied || {}).length ? `<li>Mapped from unrecognized rows: ${Object.keys(ai.applied).join(', ')}</li>` : ''}${li(ai.remarks || [])}</ul>` : ''}${ai.status === 'error' ? `<i>AI review unavailable: ${esc(ai.error)}</i>` : ''}</div>`;
      } catch (e) { $('#im').innerHTML = `<div class="msg err">${esc(e.message)}</div>`; }
      $('#file').value = '';
    };
  };

  /* ================= results ================= */
  const WI = [
    ['income', 'Income adjustment', 'e.g. − 20% simulates losing part of your income'],
    ['expense', 'Living expense adjustment', 'e.g. + 10% simulates higher living costs'],
    ['unforeseen', 'Unforeseen expense adjustment', 'e.g. + 15% adds an emergency cost equal to 15% of monthly expenses; − gives zero emergency expenses'],
    ['savings', 'Savings rate adjustment', 'e.g. + 10% raises planned savings 10% above your current level'],
    ['debt', 'Debt repayment adjustment (optional)', 'e.g. + 20% models higher monthly debt payments']];
  const GN = { g1: 'Emergency Fund', g2: 'Debt Freedom', g3: 'Wealth Milestone' };

    const aiTag = (source, err) => source === 'gemini' ? '✨ AI-generated explanation (Gemini), figures verified against Python results' : source === 'partial' ? '⚠ Partly AI-generated: ' + (err ? err.message : 'some fields were replaced by Python explanations') : '🧮 Python-generated explanation' + (err && err.code !== 'not_configured' ? ' (AI unavailable: ' + err.message + ')' : '');
  F.aiTag = aiTag;
  function applyNarr(c, source, err) {
    const set = (id, t) => { const el = $('#' + id); if (el && t) el.innerHTML = md(t); };
    set('nar-table', c.table); set('nar-chart', c.chart); set('nar-guidance', c.guidance); set('nar-reco', c.recommendations);
    Object.entries(c.scenarios || {}).forEach(([k, t]) => set('nar-scn-' + k, t));
    const tag = $('#nar-tag'); if (tag) tag.textContent = aiTag(source, err);
  }

  V.results = async (root) => {
    root.innerHTML = '<div class="pad"><span class="loader"></span> Running the calculation engine…</div>';
    let a;
    try { a = await api('/api/analysis'); }
    catch (e) {
      root.innerHTML = `<div class="pad"><h1 class="page-title">Results</h1><div class="notice warn">${esc(e.message)}</div><a class="btn" href="#/finance">Go to Financial Information</a></div>`; return;
    }
    const m = a.metrics, p = a.profile, sc = Object.fromEntries(a.scenarios.map((s) => [s.key, s])), ranked = a.ranking.map((k) => sc[k]), n = p.years;
    const lvl = { good: 'good', warn: 'warn', bad: 'bad' };
    root.innerHTML = `<div class="pad">${F.banner(0, 'Results')}<h1 class="page-title">Results</h1><p class="page-sub">Calculated by FINOVA's Python engine from the information you saved. All figures are estimates.</p>
    <div class="sec" style="margin-top:0"><h2>1. Financial Summary Table</h2>${table(['Item', 'Value', 'Type'], [
      ['Total Monthly Income (VND/month)', vnd(m.income), 'Input'], ['Total Monthly Expenses (VND/month)', vnd(m.expenses), 'Input'], ['Investments', vnd(p.investments), 'Input'], ['Assets', vnd(p.assets), 'Input'],
      ['Time horizon', p.years + ' years', 'Input'], ['Liquidity need / Risk level', p.liquidity + ' / ' + p.risk, 'Input'], ['Total debt', vnd(p.debt), 'Input'], ['Monthly debt payment', vnd(p.debt_payment), 'Input'],
      ['Net Monthly Cash Flow (after living expenses and debt service)', vnd(m.net_cash_flow), 'Computed'], ['Expense-to-Income Ratio', pct(m.expense_ratio), 'Computed'], ['Debt-to-Income (DTI) Ratio', pct(m.dti), 'Computed'],
      ['Monthly Savings Capacity', vnd(m.savings_capacity), 'Computed'], ['Total Assets', vnd(m.total_assets), 'Computed'], ['Total Current Liabilities', vnd(m.liabilities), 'Computed'], ['Estimated Net Worth', vnd(m.net_worth), 'Computed']])}</div>
    <div class="sec"><h2>2. Financial Health Assessment</h2><div class="grid2">${a.health.items.map((i) => `<div class="card"><div class="flex"><h3 style="margin:0">${i.pillar}</h3><span class="right">${badge(lvl[i.level], i.status)}</span></div><p class="muted" style="margin:.6em 0 0">${esc(i.text)}</p></div>`).join('')}</div>
      <div class="card" style="margin-top:16px"><h3>Financial Strengths &amp; Vulnerabilities</h3><div class="grid2"><div><b>Strengths</b><ul>${(a.health.strengths.length ? a.health.strengths : ['None identified yet']).map((x) => `<li>${esc(x)}</li>`).join('')}</ul></div><div><b>Vulnerabilities</b><ul>${(a.health.vulnerabilities.length ? a.health.vulnerabilities : ['None identified']).map((x) => `<li>${esc(x)}</li>`).join('')}</ul></div></div><b>Prioritized action items</b><ol>${a.health.actions.map((x) => `<li>${esc(x)}</li>`).join('')}</ol></div></div>
    <div class="sec"><h2>3. Financial Scenario Simulation</h2><p class="muted">The Python engine simulates all five scenarios month by month for up to ${n} years and compares them side by side.</p>
      ${table(['Metric'].concat(ranked.map((s) => s.short)), [
        ['Income change'].concat(ranked.map((s) => pct(s.assumptions.income_change, 0))), ['Expense change'].concat(ranked.map((s) => pct(s.assumptions.expense_change, 0))),
        ['Simulated annual yield'].concat(ranked.map((s) => pct(s.assumptions.annual_return))), ['Net cash flow / month'].concat(ranked.map((s) => vnd(s.net_cash_flow))),
        ['Savings capacity / month'].concat(ranked.map((s) => vnd(s.savings_capacity))), [`Net worth after ${n} yr`].concat(ranked.map((s) => vnd(s.final_net_worth))),
        ['Emergency Fund reached'].concat(ranked.map((s) => dur(s.reach.g1))), ['Debt Freedom reached'].concat(ranked.map((s) => dur(s.reach.g2))), ['Wealth Milestone reached'].concat(ranked.map((s) => dur(s.reach.g3)))])}
      <div class="grid2" style="margin-top:18px"><div class="card"><h4>Net worth trajectory</h4><div class="chart-box tall"><canvas id="ch-nw"></canvas></div></div><div class="card"><h4>Total assets accumulation</h4><div class="chart-box tall"><canvas id="ch-as"></canvas></div></div></div>
      <div class="card" style="margin-top:16px"><h4>Mathematical assumptions (fully disclosed)</h4><ul>${a.assumption_notes.map((x) => `<li>${esc(x)}</li>`).join('')}</ul><ul>${a.scenarios.map((s) => `<li><b>${s.short}:</b> ${esc(s.desc)}</li>`).join('')}</ul></div>
      <h3 style="margin-top:26px">Detailed AI Analysis &amp; Ranking for 5 Financial Scenarios</h3><span class="ai-tag" id="nar-tag">🧮 Explanation generated from Python results</span>
      <h4>3.1. Scenario Ranking by Suitability</h4>${ranked.map((s, i) => `<div class="rank-card${i ? '' : ' first'}"><div class="n">${s.rank}</div><div><b>${esc(s.title)}</b><div class="bar" style="margin-top:6px"><i style="width:${s.score}%"></i></div></div><div>${badge(s.score >= 80 ? 'good' : s.score >= 60 ? 'warn' : 'bad', s.score + '%')}</div></div>`).join('')}
      <h4>3.2. Meticulous Word-by-Word Table &amp; Chart Interpretation</h4><div class="card"><b>Statistical table breakdown</b><div id="nar-table">${md(a.narrative.table)}</div><b>Visual chart analysis</b><div id="nar-chart">${md(a.narrative.chart)}</div></div>
      <h4>3.3. In-Depth Breakdown for Each Individual Scenario</h4>${ranked.map((s, i) => `<details class="scn${i ? '' : ' first'}" ${i === 0 ? 'open' : ''}><summary><span>${esc(s.title)}</span></summary><div class="body" id="nar-scn-${s.key}">${md(a.narrative.scenarios[s.key])}</div></details>`).join('')}
      <h4>3.4. Informed Client Decision Guidance</h4><div class="card" id="nar-guidance">${md(a.narrative.guidance)}</div></div>
    <div class="sec"><h2>4. What-If Analysis &amp; Stress Testing</h2><p class="muted">Evaluate the resilience of your position. For each item choose <b>+</b> (increase) or <b>−</b> (decrease) and type a percentage.</p>
      <div class="card">${WI.map(([k, l, ex]) => `<div class="wi-row"><div><b>${l}</b><div class="muted" style="font-size:.82rem">${ex}</div></div><select id="wi-s-${k}" aria-label="${l} direction"><option value="+">+</option><option value="-">−</option></select><div class="suffix"><input type="text" inputmode="decimal" class="percent" id="wi-p-${k}" placeholder="0" value="0"><span>%</span></div></div>`).join('')}
        <div class="row-actions"><button class="btn" id="wiRun">Run what-if analysis</button><button class="btn ghost" id="wiReset" type="button">Reset</button></div></div><div id="wiOut"></div></div>
    <div class="sec"><h2>5. General Financial Recommendations</h2><div class="card" id="nar-reco">${md(a.narrative.recommendations)}</div></div>
    <div class="sec"><h2>6. Additional Features</h2><div class="row-actions" style="margin-top:0"><button class="btn" id="exp">⬇ Export Financial Report (.xlsx)</button><a class="btn ghost" href="#/finance">✏️ Edit inputs &amp; recalculate</a><a class="btn" href="#/savings">Savings &amp; Investment →</a></div></div></div>`;
    F.bindMoney(root);
    const yrs = a.years, ds = (key) => ranked.slice().sort((x, y) => a.scenarios.indexOf(x) - a.scenarios.indexOf(y)).map((s) => ({ label: s.short, data: s[key].slice(0, yrs.length), borderColor: F.COLORS[a.scenarios.indexOf(s)], backgroundColor: F.COLORS[a.scenarios.indexOf(s)], tension: .25, pointRadius: 0, borderWidth: s.key === 'baseline' ? 4 : 2 }));
    F.makeChart('ch-nw', 'line', yrs, ds('net_worth_by_year'), { xTitle: 'Years' }); F.makeChart('ch-as', 'line', yrs, ds('assets_by_year'), { xTitle: 'Years' });
    $('#exp').onclick = () => F.download('/api/export/report', {}, 'finova_financial_report.xlsx').then(() => toast('Report exported')).catch((e) => toast(e.message));
    $('#wiReset').onclick = () => WI.forEach(([k]) => { $('#wi-p-' + k).value = '0'; $('#wi-s-' + k).value = '+'; });
    const adj = () => Object.fromEntries(WI.map(([k]) => [k, { sign: $('#wi-s-' + k).value, pct: Number($('#wi-p-' + k).value) || 0 }]));
    $('#wiRun').onclick = async () => {
      const out = $('#wiOut'); out.innerHTML = '<p><span class="loader"></span> Calculating…</p>';
      try {
        const w = await api('/api/whatif', { json: { adjustments: adj() } });
        out.innerHTML = `<h3 style="margin-top:22px">Post-adjustment results</h3>${table(['Metric', 'Baseline', 'After adjustment', 'Variance vs baseline'], w.rows.map((r) => { const u = r.unit === 'months' ? (x) => fmt(x, 1) + ' mo' : r.unit === 'dur' ? dur : vnd; const v = r.variance == null ? '–' : (r.variance > 0 ? '+' : '') + (r.unit === 'dur' ? fmt(r.variance) + ' mo' : u(r.variance)); return [r.label, u(r.baseline), u(r.adjusted), v]; }))}
          ${w.warnings.map((x) => `<div class="notice warn">${esc(x)}</div>`).join('')}
          <div class="card" style="margin-top:16px"><h4>Net worth: baseline vs adjusted</h4><div class="chart-box tall"><canvas id="ch-wi2"></canvas></div></div>
          <div class="card" style="margin-top:16px"><h4>Baseline vs adjusted</h4><div class="chart-box"><canvas id="ch-wi"></canvas></div></div>
          <div class="card" style="margin-top:16px"><span class="ai-tag" id="wi-tag">🧮 Trade-off &amp; risk explanation from Python results</span><div id="wi-nar">${md(w.narrative.text)}</div></div>`;
        F.makeChart('ch-wi2', 'line', w.series.labels, [{ label: 'Baseline', data: w.series.baseline, borderColor: '#9db8aa', backgroundColor: '#9db8aa', tension: .25, pointRadius: 0 }, { label: 'After adjustment', data: w.series.adjusted, borderColor: '#2F8A58', backgroundColor: '#2F8A58', tension: .25, pointRadius: 0 }], { xTitle: 'Years' });
        F.makeChart('ch-wi', 'bar', w.chart.labels, [{ label: 'Baseline', data: w.chart.baseline, backgroundColor: '#9db8aa' }, { label: 'After adjustment', data: w.chart.adjusted, backgroundColor: '#2F8A58' }]);
        out.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        if (F.S.ai) { $('#wi-tag').textContent = '⏳ AI is writing the trade-off explanation…'; api('/api/ai/explain', { json: { kind: 'whatif', adjustments: adj() } }).then((r) => { if (r.source === 'gemini' && r.content.text) $('#wi-nar').innerHTML = md(r.content.text); $('#wi-tag').textContent = aiTag(r.source, r.error); }).catch((e) => ($('#wi-tag').textContent = '🧮 Python-generated explanation (AI unavailable: ' + e.message + ')')); }
      } catch (e) { out.innerHTML = `<div class="msg err">${esc(e.message)}</div>`; }
    };
    if (F.S.ai) { $('#nar-tag').textContent = '⏳ AI is writing the explanation…'; api('/api/ai/explain', { json: { kind: 'analysis' } }).then((r) => applyNarr(r.source === 'rules' ? {} : r.content, r.source, r.error)).catch((e) => ($('#nar-tag').textContent = '🧮 Python-generated explanation (AI unavailable: ' + e.message + ')')); }
  };
})(window.FIN);
