/* Stylised landmark illustrations (self-contained SVG, no external image hosting).
   To use real photos instead, replace the `src` values below with image URLs. */
(function () {
  const wrap = (inner, defs = '') =>
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 600" preserveAspectRatio="xMidYMid slice"><defs>${defs}</defs>${inner}</svg>`;
  const uri = (s) => 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(s);
  const grad = (id, a, b) => `<linearGradient id="${id}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="${a}"/><stop offset="1" stop-color="${b}"/></linearGradient>`;

  const halong = wrap(`
    <rect width="1200" height="600" fill="url(#s)"/><circle cx="880" cy="190" r="70" fill="#fff5c2" opacity=".9"/>
    <rect y="330" width="1200" height="270" fill="url(#w)"/>
    <path d="M0 340 L70 250 L110 285 L170 190 L230 300 L260 340Z" fill="#3b7f6b"/>
    <path d="M200 345 L290 215 L330 260 L400 160 L470 290 L520 345Z" fill="#2f6e5c"/>
    <path d="M520 345 L590 260 L640 300 L700 205 L770 320 L800 345Z" fill="#3b7f6b"/>
    <path d="M740 345 L850 235 L900 285 L990 170 L1060 300 L1120 345Z" fill="#2a604f"/>
    <path d="M1000 345 L1080 270 L1130 310 L1200 250 L1200 345Z" fill="#3b7f6b"/>
    <path d="M300 470 q40 -60 90 0z" fill="#fff"/><path d="M345 470 v-95" stroke="#6b4a2f" stroke-width="4"/>
    <path d="M345 380 q55 25 40 80 h-40z" fill="#f4e3c1"/><path d="M0 520 q300 -30 600 0 t600 0 V600 H0z" fill="#ffffff" opacity=".12"/>`,
    grad('s', '#9fd8e8', '#e9f7f1') + grad('w', '#37a6a0', '#1d6f7a'));

  const sapa = wrap(`
    <rect width="1200" height="600" fill="url(#s)"/><circle cx="260" cy="140" r="55" fill="#fff8cf"/>
    <path d="M0 330 L220 160 L400 300 L640 110 L900 290 L1200 170 V600 H0Z" fill="#7da8b5" opacity=".7"/>
    <path d="M0 400 Q300 250 600 360 T1200 300 V600 H0Z" fill="#4f9c5a"/>
    ${[0, 1, 2, 3, 4, 5, 6].map((i) => `<path d="M0 ${420 + i * 28} Q300 ${300 + i * 36} 600 ${400 + i * 24} T1200 ${350 + i * 30}" fill="none" stroke="${i % 2 ? '#d9c95a' : '#2f7d44'}" stroke-width="16" opacity=".85"/>`).join('')}
    <path d="M0 560 Q300 500 600 545 T1200 520 V600 H0Z" fill="#2f7d44"/>`,
    grad('s', '#bfe3ff', '#f4fbf3'));

  const pagoda = wrap(`
    <rect width="1200" height="600" fill="url(#s)"/><rect y="400" width="1200" height="200" fill="url(#w)"/>
    <rect x="590" y="300" width="22" height="140" fill="#8a5a3b"/>
    <path d="M520 300 L601 240 L682 300Z" fill="#b5532f"/><rect x="545" y="300" width="112" height="46" fill="#e9c98f"/>
    <path d="M530 346 L601 296 L672 346Z" fill="#c8643a"/>
    <rect x="480" y="390" width="240" height="14" rx="7" fill="#d4a373" opacity=".6"/>
    ${[160, 300, 440, 780, 920, 1040].map((x, i) => `<ellipse cx="${x}" cy="${480 + (i % 3) * 30}" rx="46" ry="12" fill="#2d8f5a"/><circle cx="${x}" cy="${470 + (i % 3) * 30}" r="9" fill="#ffb6c8"/>`).join('')}
    <path d="M0 400 q60 -90 120 -10 q60 -90 130 0 q60 -80 120 0V400Z" fill="#3a8f58" opacity=".8"/>
    <path d="M830 400 q60 -100 130 -10 q70 -90 130 0 q60 -80 110 0V400Z" fill="#2f7d44" opacity=".8"/>`,
    grad('s', '#ffe2b5', '#fff7e6') + grad('w', '#5fb59a', '#2f8a78'));

  const hoian = wrap(`
    <rect width="1200" height="600" fill="url(#s)"/><rect y="420" width="1200" height="180" fill="url(#w)"/>
    <rect x="380" y="330" width="440" height="30" fill="#7a4a2c"/><path d="M360 330 L600 240 L840 330Z" fill="#b34a2a"/>
    <path d="M380 360 v70 M470 360 v70 M600 360 v70 M730 360 v70 M820 360 v70" stroke="#5a3820" stroke-width="12"/>
    <path d="M360 430 q240 -90 480 0" fill="none" stroke="#7a4a2c" stroke-width="14"/>
    ${[100, 220, 330, 900, 1010, 1110].map((x, i) => `<line x1="${x}" y1="0" x2="${x}" y2="${110 + (i % 3) * 40}" stroke="#a66" stroke-width="3"/><ellipse cx="${x}" cy="${140 + (i % 3) * 40}" rx="30" ry="38" fill="${['#e63946', '#f4a261', '#e9c46a'][i % 3]}"/><rect x="${x - 10}" y="${176 + (i % 3) * 40}" width="20" height="8" fill="#6b4a2f"/>`).join('')}
    <path d="M0 520 q150 -20 300 0 t300 0 t300 0 t300 0" fill="none" stroke="#fff" stroke-width="5" opacity=".3"/>
    <path d="M150 520 l60 -40 h70 l30 40z" fill="#8a5a3b"/>`,
    grad('s', '#ffd9a8', '#fff2dc') + grad('w', '#6ec1b8', '#2e8c8f'));

  const saigon = wrap(`
    <rect width="1200" height="600" fill="url(#s)"/><circle cx="260" cy="400" r="95" fill="#ffd27a" opacity=".9"/>
    <rect y="430" width="1200" height="170" fill="url(#w)"/>
    <path d="M610 430 V90 L640 40 L670 90 V430Z" fill="#35506b"/><path d="M628 430 V120 M652 430 V120" stroke="#8fb4d1" stroke-width="3"/>
    ${[[380, 280, 70], [470, 220, 80], [540, 300, 60], [730, 250, 85], [830, 310, 70], [920, 230, 80], [1010, 330, 70]].map(([x, h, w]) => `<rect x="${x}" y="${430 - h}" width="${w}" height="${h}" fill="#4a6a87"/><path d="M${x + 8} ${430 - h + 14} h${w - 16}" stroke="#9fc1dc" stroke-width="3" stroke-dasharray="8 8"/>`).join('')}
    <path d="M0 520 q150 -14 300 0 t300 0 t300 0 t300 0" fill="none" stroke="#ffe3a8" stroke-width="5" opacity=".5"/>
    <path d="M820 500 l80 -30 h110 l40 30z" fill="#2c3e50"/><path d="M910 470 v-60 l60 60z" fill="#f7e3b3"/>`,
    grad('s', '#ff9e7a', '#ffe9c9') + grad('w', '#3a7ca5', '#1f4e6b'));

  const svgs = [uri(halong), uri(sapa), uri(pagoda), uri(hoian), uri(saigon)];
  /* 8 slots. Real photos live in /static/img/scenes/1.jpg ... 8.jpg (downloaded from Wikimedia Commons at build time by
     tools/fetch_photos.py, or put your own files there). If a photo is missing the illustrated SVG shows instead. */
  const P = [['Ha Long Bay, Quang Ninh', 0], ['Hoan Kiem Lake, Hanoi', 2], ['Sa Pa terraced fields, Lao Cai', 1], ['Hoi An Ancient Town, Quang Nam',
             3], ['Ho Chi Minh City', 4], ['Trang An, Ninh Binh', 0], ['One Pillar Pagoda, Hanoi', 2], ['Phu Quoc Island, Kien Giang', 3]];
  window.FINOVA_SCENES = P.map(([caption, k], i) => ({ photo: `/static/img/scenes/${i + 1}.jpg`, src: svgs[k], caption }));
  window.FINOVA_BG = (i) => { const s = window.FINOVA_SCENES[((i % P.length) + P.length) % P.length]; return `url('${s.photo}'),url('${s.src}')`; };
})();
