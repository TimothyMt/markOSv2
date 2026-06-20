/* Marketing OS — web app demo (client-side SPA, mock data) */
(function () {
  const M = window.MOCK;
  const css = getComputedStyle(document.documentElement);
  const C = (n) => css.getPropertyValue(n).trim();
  const PRIMARY = C('--primary'), PRIMARY2 = C('--primary-2'),
        GREEN = C('--green'), CYAN = C('--cyan'), AMBER = C('--amber'),
        RED = C('--red'), TXT2 = C('--txt-2'), STROKE = C('--stroke');
  const hasChart = !!window.Chart;
  if (hasChart) {
    Chart.defaults.color = TXT2;
    Chart.defaults.font.family = "'Inter', sans-serif";
    Chart.defaults.font.size = 11;
  }
  let charts = [];
  const reg = (c) => { charts.push(c); return c; };
  const killCharts = () => { charts.forEach((c) => c.destroy()); charts = []; };

  const grid = { color: STROKE, drawTicks: false };
  const noGrid = { display: false };
  const fill = (hex) => (ctx) => {
    const { ctx: g, chartArea } = ctx.chart;
    if (!chartArea) return hex + '22';
    const grad = g.createLinearGradient(0, chartArea.top, 0, chartArea.bottom);
    grad.addColorStop(0, hex + '55'); grad.addColorStop(1, hex + '00');
    return grad;
  };
  const days = ['T2','T3','T4','T5','T6','T7','CN'];
  const num = (n) => n.toLocaleString('vi-VN');

  /* ── small component helpers ─────────────────────────── */
  const card = (title, body, opts = {}) => `
    <article class="card ${opts.cls || ''}">
      ${title ? `<div class="card-head"><h3>${title}</h3>${opts.action || ''}</div>` : ''}
      ${body}
    </article>`;
  const badge = (txt, kind = '') => `<span class="tag ${kind}">${txt}</span>`;
  const pageHead = (title, sub, actions = '') => `
    <div class="page-head">
      <div><h1>${title}</h1><p class="muted">${sub}</p></div>
      <div class="page-actions">${actions}</div>
    </div>`;
  const cv = (id, h = 220) => `<div class="chart-box" style="height:${h}px"><canvas id="${id}"></canvas></div>`;

  /* ════════════ PAGES ════════════ */
  const P = {};

  /* ---- Max — cố vấn CMO (trung tâm, conversation-first) ---- */
  const STAGE_INDEX = { discovery:0, diagnosis:1, strategy:2, execution:3, run:4 };
  let _chatMsgs = [];        // [{role, content}]
  let _chatStage = 'discovery';
  let _chatSuggest = [];
  let _chatBusy = false;

  const CHAT_EXAMPLES = [
    { icon:'☕', text:'Shop mình bán cà phê specialty ở Q.1 TP.HCM, muốn tăng đơn online trong 3 tháng.' },
    { icon:'🛍️', text:'Mình mở shop thời trang nữ online, ngân sách ads 10tr/tháng — nên bắt đầu từ đâu?' },
    { icon:'📊', text:'Phân tích giúp mình đối thủ trong ngành trà sữa khu vực Hà Nội.' },
    { icon:'🎯', text:'Mình cần một chiến lược marketing 90 ngày cho phòng gym mới mở.' },
  ];

  // Thanh tiến trình hành trình — gọn như breadcrumb, không phải 5 hộp lớn
  function journeyMini(activeStage) {
    const J = M.journey || [];
    const ai = STAGE_INDEX[activeStage] ?? 0;
    return `<div class="jmini">${J.map((s,i)=>`
      <a class="jm ${i<ai?'done':i===ai?'on':''}" href="#${s.page}" title="${s.desc}">
        <span class="jm-dot">${i<ai?'✓':s.icon}</span><span class="jm-label">${s.label}</span>
      </a>${i<J.length-1?'<span class="jm-sep">›</span>':''}`).join('')}</div>`;
  }

  P.home = {
    title: 'Max', sub: '',
    render: () => `
      <div class="maxchat">
        <div class="maxchat-top">${journeyMini(_chatStage)}</div>
        <div class="maxchat-stream" id="chatStream"></div>
        <div class="maxchat-foot">
          <div class="chat-suggest" id="chatSuggest"></div>
          <div class="composer">
            <textarea id="chatBox" rows="1" placeholder="Nhắn cho Max…"></textarea>
            <button class="composer-send" data-act="chat-send" title="Gửi" aria-label="Gửi">↑</button>
          </div>
          <p class="composer-hint">Max là CMO ảo · có thể sai sót — hãy kiểm chứng thông tin quan trọng</p>
        </div>
      </div>`,
    mount: () => { initChat(); },
  };

  /* ---- Overview ---- */
  P.overview = {
    title: 'Tổng quan', sub: 'Cập nhật lần cuối: hôm nay, 09:42',
    actions: `<button class="primary-btn" data-act="add-campaign">＋ Tạo chiến dịch</button>`,
    render: () => `
      <section class="kpis">
        ${kpi('💸','spend','Tổng chi tiêu','12.540.000 ₫','▲ 8,2%','up')}
        ${kpi('💰','rev','Doanh thu','36.750.000 ₫','▲ 12,4%','up')}
        ${kpi('🎯','roas','ROAS','3,09x','▲ 0,21','up')}
        ${kpi('👆','click','Lượt click','42.350','▼ 1,8%','down')}
      </section>
      <section class="grid">
        ${card('Chiến dịch đang chạy', cv('lineChart',240), {cls:'span-8',
          action:`<div class="legend"><span><i class="dot a"></i>Chi tiêu</span><span><i class="dot b"></i>Doanh thu</span></div>`})}
        ${card('Phễu chuyển đổi', donut('donutChart','3,8%','Tỷ lệ CR',
          [['Hiển thị','1,2M'],['Click','42.350'],['Chuyển đổi','1.610']]), {cls:'span-4'})}
        ${card('Hiệu suất theo thời gian', cv('barChart',220), {cls:'span-8'})}
        ${card('Phân bổ ngân sách', donut('budgetChart','6.500.000 ₫','Ngân sách/ngày',
          [['Khách mới','45%'],['Re-targeting','30%'],['Lookalike','25%']]), {cls:'span-4'})}
        ${card('Chiến dịch gần đây', table(['Chiến dịch','Mục tiêu','Ngân sách','Trạng thái',''],
          (M.campaigns||[]).map(c=>[c.name, c.objective, c.budget,
            c.status==='running'?badge('Đang chạy','green'):badge('Nháp','amber'),
            c.id?`<button class="icon-btn" data-act="del-campaign" data-id="${c.id}" title="Xoá">✕</button>`:''])),
          {cls:'span-12', action:`<button class="ghost-line sm" data-act="add-campaign">＋ Thêm</button>`})}
      </section>`,
    mount: () => {
      line('lineChart', [
        {label:'Chi tiêu', data:[1.4,1.7,1.6,2.1,1.9,2.3,1.5], color:PRIMARY},
        {label:'Doanh thu', data:[4.2,5.1,4.8,6.4,5.7,7.1,4.4], color:GREEN}], 'M');
      doughnut('donutChart',[62,26,12]);
      bar('barChart',[180,240,210,320,280,360,220]);
      doughnut('budgetChart',[45,30,25]);
      sparks();
    },
  };

  /* ---- AI Agent & dữ liệu thật ---- */
  const fmtNum = (n) => (n == null ? '—' : Number(n).toLocaleString('vi-VN'));
  const profRow = (k, v) => v ? `<div class="kv"><span>${k}</span><b>${v}</b></div>` : '';
  const runBtn = (task, label, cls = 'primary-btn sm') =>
    `<button class="${cls}" data-act="run-agent" data-task="${task}">${label}</button>`;

  function jobStatusTag(s) {
    return s === 'done' ? badge('Hoàn tất', 'green')
      : s === 'error' ? badge('Lỗi', 'red')
      : badge('Đang chạy', 'amber');
  }

  // Thanh AI agent gắn vào đầu các trang phân tích: chạy thật + xem output thật
  function agentBar(task, skillKey) {
    if (!M.bizEnabled) return '';
    const latest = (M.bizLatest || {})[skillKey];
    const running = (M.agentJobs || []).some(j => j.status === 'running' && (j.task === task || j.task === 'full'));
    const body = `
      <div class="agent-bar">
        <div class="agent-bar-info">
          ${running ? `<span class="tag amber">⏳ AI đang chạy…</span>`
            : latest ? `<span class="tag green">✓ Đã có output thật</span>
                <span class="muted">v${latest.version} · ${fmtNum(latest.length)} ký tự · ${(latest.created_at||'').slice(0,10)}</span>`
            : `<span class="muted">Chưa có output thật cho mục này</span>`}
        </div>
        <div class="agent-bar-act">
          ${latest ? `<button class="ghost-line sm" data-act="view-skillrun" data-id="${latest.id}">Xem output</button>` : ''}
          ${runBtn(task, running ? '↻ Đang chạy' : '⚡ Chạy bằng AI')}
        </div>
      </div>`;
    return card('AI Agent (dữ liệu thật)', body, {cls:'span-12'});
  }

  // Nhúng trình đọc/sửa text NGAY trong trang chi tiết → 1 trang có cả "bảng" lẫn text.
  function agentSection(task, skillKey) {
    const hasRun = (M.bizSkillRuns || []).some(r => r.skill_name === skillKey);
    if (!M.bizEnabled && !hasRun) return agentBar(task, skillKey);   // demo chưa có mẫu → chỉ thanh chạy
    const running = (M.agentJobs || []).some(j => j.status === 'running' && (j.task === task || j.task === 'full'));
    return card('Nội dung chi tiết (AI) — đọc & chỉnh sửa', `
      <div class="agent-bar">
        <div class="agent-bar-info">${running ? '<span class="tag amber">⏳ AI đang chạy…</span>'
          : '<span class="muted">Bản text do AI tạo — sửa tay / nhờ Max chỉnh ngay bên dưới</span>'}</div>
        <div class="agent-bar-act">${runBtn(task, running ? '↻ Đang chạy' : (hasRun ? '↻ Tạo lại bản mới' : '⚡ Chạy bằng AI'))}</div>
      </div>
      <div id="docView" class="doc-wrap doc-embed" data-doc-skill="${skillKey}" data-doc-task="${task}"><p class="muted">Đang tải…</p></div>
    `, {cls:'span-12'});
  }

  // Đổ full content của skill_run vào các slot .ai-output (gọi sau mỗi route)
  // D-034 #1: render markdown block-aware — hỗ trợ BẢNG + blockquote + list (trước
  // đây thiếu bảng → output competitor/SWOT/pricing hiện pipe thô).
  function renderAIContent(txt) {
    const raw = (txt || '').trim();
    if (raw.startsWith('<')) return raw;          // skill xuất HTML → render trực tiếp
    const esc = s => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    const inline = s => esc(s)
      .replace(/\*\*(.+?)\*\*/g, '<b>$1</b>')
      .replace(/\*(.+?)\*/g, '<i>$1</i>')
      .replace(/(^|[\s(>])_([^_\n]+?)_(?=[\s).,;:!?]|$)/g, '$1<i>$2</i>');   // _nghiêng_ (không đụng snake_case)
    const isRow = l => /^\s*\|.*\|\s*$/.test(l);
    const isSep = l => /^\s*\|?[\s:|-]*-[\s:|-]*\|?\s*$/.test(l) && l.includes('-');
    const cells = l => l.trim().replace(/^\|/, '').replace(/\|$/, '').split('|').map(c => c.trim());
    const lines = raw.split('\n');
    const out = [];
    let i = 0;
    while (i < lines.length) {
      const line = lines[i];
      // Code fence ``` … ``` (giữ nguyên ASCII, vd Positioning Map) → <pre>
      if (/^\s*```/.test(line)) {
        const buf = [];
        i++;
        while (i < lines.length && !/^\s*```/.test(lines[i])) { buf.push(lines[i]); i++; }
        i++; // bỏ dòng ``` đóng
        out.push('<pre class="ai-pre">' + esc(buf.join('\n')) + '</pre>');
        continue;
      }
      // Bảng: hàng | … | + hàng phân cách |---|
      if (isRow(line) && i + 1 < lines.length && isSep(lines[i + 1])) {
        const head = cells(line); i += 2;
        const rows = [];
        while (i < lines.length && isRow(lines[i])) { rows.push(cells(lines[i])); i++; }
        out.push('<div class="tbl-wrap"><table class="tbl"><thead><tr>' +
          head.map(h => `<th>${inline(h)}</th>`).join('') + '</tr></thead><tbody>' +
          rows.map(r => `<tr>${r.map(c => `<td>${inline(c)}</td>`).join('')}</tr>`).join('') +
          '</tbody></table></div>');
        continue;
      }
      // Blockquote
      if (/^\s*>\s?/.test(line)) {
        const buf = [];
        while (i < lines.length && /^\s*>\s?/.test(lines[i])) { buf.push(lines[i].replace(/^\s*>\s?/, '')); i++; }
        out.push('<blockquote>' + buf.map(inline).join('<br>') + '</blockquote>');
        continue;
      }
      // Heading
      let m;
      if ((m = line.match(/^####\s+(.*)/))) { out.push(`<h5>${inline(m[1])}</h5>`); i++; continue; }
      if ((m = line.match(/^###\s+(.*)/)))  { out.push(`<h4>${inline(m[1])}</h4>`); i++; continue; }
      if ((m = line.match(/^##\s+(.*)/)))   { out.push(`<h3>${inline(m[1])}</h3>`); i++; continue; }
      if ((m = line.match(/^#\s+(.*)/)))    { out.push(`<h2>${inline(m[1])}</h2>`); i++; continue; }
      // Horizontal rule
      if (/^\s*---+\s*$/.test(line)) { out.push('<hr>'); i++; continue; }
      // Bullet list
      if (/^\s*[-*]\s+/.test(line)) {
        const buf = [];
        while (i < lines.length && /^\s*[-*]\s+/.test(lines[i])) { buf.push(lines[i].replace(/^\s*[-*]\s+/, '')); i++; }
        out.push('<ul>' + buf.map(b => `<li>${inline(b)}</li>`).join('') + '</ul>');
        continue;
      }
      // Numbered list
      if (/^\s*\d+\.\s+/.test(line)) {
        const buf = [];
        while (i < lines.length && /^\s*\d+\.\s+/.test(lines[i])) { buf.push(lines[i].replace(/^\s*\d+\.\s+/, '')); i++; }
        out.push('<ol>' + buf.map(b => `<li>${inline(b)}</li>`).join('') + '</ol>');
        continue;
      }
      // Dòng trống
      if (!line.trim()) { i++; continue; }
      // Đoạn văn (gom các dòng thường liên tiếp)
      const buf = [];
      while (i < lines.length && lines[i].trim() && !isRow(lines[i]) && !/^\s*>/.test(lines[i])
             && !/^#{1,4}\s/.test(lines[i]) && !/^\s*[-*]\s/.test(lines[i])
             && !/^\s*\d+\.\s/.test(lines[i]) && !/^\s*---+\s*$/.test(lines[i])) {
        buf.push(lines[i]); i++;
      }
      out.push('<p>' + buf.map(inline).join('<br>') + '</p>');
    }
    return out.join('\n');
  }
  // D-034 #4: chuyển ASCII Positioning Map (trong <pre>) → visual 4 góc (port từ bot)
  function enhancePosMaps(root) {
    if (!root) return;
    const isMap = t => t.indexOf('^') >= 0 && /GÓC/i.test(t);
    const roman = n => ['I', 'II', 'III', 'IV'][n - 1] || String(n);
    const fromRoman = s => ({ I: 1, II: 2, III: 3, IV: 4 }[(s || '').toUpperCase().trim()] || 0);
    const mk = (tag, cls, text) => { const el = document.createElement(tag); if (cls) el.className = cls; if (text !== undefined) el.textContent = text; return el; };
    function parseMap(text) {
      const lines = text.split('\n'), n = lines.length;
      let hIdx = -1;
      for (let i = 0; i < n; i++) { if (/[-─]{4,}/.test(lines[i])) { hIdx = i; break; } }
      if (hIdx < 0) return null;
      const cols = {}; let vCol = 0, mx = 0;
      lines.forEach(l => { for (let j = 0; j < l.length; j++) if (l[j] === '|') cols[j] = (cols[j] || 0) + 1; });
      Object.keys(cols).forEach(j => { if (cols[j] > mx) { mx = cols[j]; vCol = +j; } });
      if (!mx) vCol = Math.floor((lines[hIdx] || '').length / 2);
      let yTop = '', yBottom = '', xRight = '', xLeft = '';
      for (let i = 0; i < hIdx; i++) {
        if (lines[i].indexOf('^') >= 0) { const t = lines[i].replace(/\^/g, '').replace(/\|/g, '').trim(); yTop = t || (i > 0 ? lines[i - 1].replace(/\|/g, '').trim() : ''); break; }
      }
      for (let i = hIdx + 1; i < n; i++) {
        if (/^\s*v\s*$/.test(lines[i]) || lines[i].trim() === 'v') { yBottom = (i + 1 < n ? lines[i + 1] : '').replace(/\|/g, '').trim(); break; }
      }
      const axL = lines[hIdx] || '';
      const ar = axL.match(/[-─>]+\s*(.+)$/); if (ar) xRight = ar[1].trim();
      const lr = axL.match(/^([^─\-|+]+)[-─]/); if (lr) xLeft = lr[1].trim();
      const qdesc = { 1: '', 2: '', 3: '', 4: '' };
      const gr = /GÓC\s*(IV|III|II|I)\s*[:\-—(]?\s*([^\n|)]{0,60})/gi; let gm;
      while ((gm = gr.exec(text)) !== null) { const num = fromRoman(gm[1]); if (num >= 1 && num <= 4) qdesc[num] = gm[2].replace(/[)\]]/g, '').trim(); }
      const items = { 1: [], 2: [], 3: [], 4: [] }, seen = { 1: [], 2: [], 3: [], 4: [] };
      for (let row = 0; row < n; row++) {
        if (row === hIdx) continue;
        const line = lines[row], isTop = row < hIdx;
        const ir = /(?:[•·●♦★→]|\[)([^\]•·●♦★→\n|]{2,35})(?:\])?/g; let im;
        while ((im = ir.exec(line)) !== null) {
          const item = im[1].trim().replace(/[[\]()]/g, '');
          if (!item || /GÓC|TRỐNG/i.test(item)) continue;
          const q = isTop ? (im.index >= vCol ? 1 : 2) : (im.index >= vCol ? 4 : 3);
          if (seen[q].indexOf(item) < 0) { seen[q].push(item); items[q].push(item); }
        }
      }
      return { yTop, yBottom, xRight, xLeft, qdesc, items };
    }
    function buildEl(map) {
      const w = mk('div', 'pos-map-wrap');
      w.appendChild(mk('div', 'pos-map-title', '📍 Bản đồ Định vị Cạnh tranh'));
      if (map.yTop) w.appendChild(mk('div', 'pos-y-lbl', '↑ ' + map.yTop));
      const qg = mk('div', 'pos-quads');
      [[2, 'pq2'], [1, 'pq1'], [3, 'pq3'], [4, 'pq4']].forEach(p => {
        const q = mk('div', 'pos-q ' + p[1]);
        q.appendChild(mk('div', 'pos-q-lbl', 'GÓC ' + roman(p[0])));
        if (map.qdesc[p[0]]) q.appendChild(mk('div', 'pos-q-desc', map.qdesc[p[0]]));
        const qi = mk('div', 'pos-q-items');
        map.items[p[0]].forEach(it => { const self = /SếP|sếp|★|self/.test(it); qi.appendChild(mk('span', 'pos-item' + (self ? ' pos-item-self' : ''), self ? '★ ' + it.replace(/^★\s*/, '') + ' (Bạn ở đây)' : it)); });
        q.appendChild(qi); qg.appendChild(q);
      });
      w.appendChild(qg);
      if (map.yBottom) w.appendChild(mk('div', 'pos-y-lbl', '↓ ' + map.yBottom));
      if (map.xLeft || map.xRight) {
        const xa = mk('div', 'pos-x-axis');
        if (map.xLeft) xa.appendChild(mk('span', 'pos-x-l', '← ' + map.xLeft));
        xa.appendChild(mk('div', 'pos-x-line'));
        if (map.xRight) xa.appendChild(mk('span', 'pos-x-r', map.xRight + ' →'));
        w.appendChild(xa);
      }
      return w;
    }
    root.querySelectorAll('pre').forEach(pre => {
      const text = pre.textContent || '';
      if (!isMap(text)) return;
      const map = parseMap(text); if (!map) return;
      pre.parentNode.replaceChild(buildEl(map), pre);
    });
  }
  // Đổ trình đọc/sửa vào ô nhúng #docView.doc-embed trên trang chi tiết (gọi sau route)
  async function fillDocEmbeds() {
    const host = document.getElementById('docView');
    if (!host || !host.classList.contains('doc-embed')) return;
    const skill = host.dataset.docSkill;
    const run = (M.bizSkillRuns || []).find(r => r.skill_name === skill);
    if (!run) { host.innerHTML = '<p class="muted">Chưa có nội dung — bấm “Chạy bằng AI” phía trên để tạo.</p>'; return; }
    _docEdit = false; _docId = run.id;
    await loadDoc();   // render vào chính #docView này
  }

  // Form nhập hồ sơ doanh nghiệp — điểm khởi đầu cho user mới (thay ô chat)
  let _editProfile = false;
  // Onboarding wizard — hỏi từng câu một (kiểu Typeform), thân thiện với user mới
  let _intakeStep = 0, _intakeData = {}, _intakeProv = {};
  let _intakeSuggest = {}, _intakeSuggestBusy = false, _intakeSuggestDone = false;
  // D-032 step 2: sinh chip gợi ý cho câu chiến lược, bám ngành/sản phẩm/khách đã nhập
  async function fetchIntakeSuggestions() {
    if (_intakeSuggestDone || _intakeSuggestBusy || !apiAvailable) return;
    _intakeSuggestBusy = true;
    try {
      const core = {};
      ['business_name', 'industry', 'location', 'product_service', 'target_customer'].forEach(k => {
        if (_intakeData[k]) core[k] = _intakeData[k];
      });
      const r = await API.post('api/biz/intake/suggest', { fields: core, user_id: _bizUserId });
      _intakeSuggest = (r && r.suggestions) || {};
    } catch (e) { _intakeSuggest = {}; }
    _intakeSuggestBusy = false; _intakeSuggestDone = true;
    route();
  }
  // D-032: intake web đa-level. tier: core (bắt buộc) | strategic (tầng CMO,
  // skip→AI suy, có chip gợi ý) | context (optional, chọn khoảng).
  // strategic=true → hiện helper bình dân + nút "để Max đoán"; skip = field giả định.
  const INTAKE_STEPS = [
    // ── Khối nền (bắt buộc) ──
    { key: 'business_name', tier: 'core', q: 'Doanh nghiệp của bạn tên là gì?', ph: 'vd: Cà phê An' },
    { key: 'industry', tier: 'core', q: 'Bạn kinh doanh trong ngành nào?', ph: 'vd: F&B — Quán cà phê' },
    { key: 'location', tier: 'core', q: 'Bạn kinh doanh ở khu vực nào?', ph: 'vd: TP.HCM, Quận 1', optional: true },
    { key: 'product_service', tier: 'core', q: 'Bạn bán sản phẩm/dịch vụ gì, và nó giải quyết vấn đề gì cho khách?', ph: 'vd: Cà phê specialty — đồ uống chất cho dân văn phòng cần tỉnh táo' },
    { key: 'target_customer', tier: 'core', q: 'Khách hàng mục tiêu của bạn là ai?', ph: 'vd: Dân văn phòng 25–34, Q.1' },
    { key: 'main_challenge', tier: 'core', q: 'Thách thức lớn nhất hiện tại của bạn là gì?', ph: 'vd: cạnh tranh chuỗi lớn, chi phí ads cao' },

    // ── Khối chiến lược (tầng CMO — skip→AI suy, sẽ có chip gợi ý) ──
    { key: 'jtbd', tier: 'strategic', strategic: true,
      q: 'Khách hàng "thuê" sản phẩm của bạn để hoàn thành việc gì?',
      helper: 'Tức là: họ mua vào lúc/dịp nào, để giải quyết chuyện gì trong cuộc sống của họ?',
      ph: 'vd: cần ly cà phê ngon để tỉnh táo & "thưởng" cho buổi sáng bận rộn' },
    { key: 'competitive_alternative', tier: 'strategic', strategic: true,
      q: 'Nếu không có bạn, khách sẽ dùng giải pháp thay thế nào?',
      helper: 'Họ hay so sánh bạn với ai, hoặc trước khi biết bạn họ mua ở đâu?',
      ph: 'vd: Highlands, cà phê pha sẵn ở nhà, hoặc trà sữa' },
    { key: 'differentiation', tier: 'strategic', strategic: true,
      q: 'Điểm khác biệt bền vững của bạn là gì, và bằng chứng cho điều đó?',
      helper: 'Khách hay khen bạn điểm gì nhất? Vì sao họ quay lại?',
      note: 'Nếu chưa biết thì ghi "chưa biết" — Max sẽ tự tìm/đề xuất định vị giúp bạn.' },
    { key: 'objection', tier: 'strategic', strategic: true,
      q: 'Rào cản / nỗi sợ lớn nhất khiến khách chần chừ là gì?',
      helper: 'Khách hay lo gì, hay hỏi gì, hay từ chối vì lý do nào trước khi mua?',
      ph: 'vd: "giá cao hơn cà phê thường", "sợ đặt online nguội"' },
    { key: 'competitors', tier: 'strategic', strategic: true, optional: true,
      q: 'Có đối thủ nào bạn đang để ý không? (tên cụ thể nếu có)',
      helper: 'Nêu tên giúp Max nghiên cứu đúng đối thủ đó — không có thì để trống.',
      ph: 'vd: Highlands, Phúc Long, The Coffee House' },

    // ── Khối bối cảnh (optional — chọn khoảng) ──
    { key: 'price_point', tier: 'context', optional: true, q: 'Giá bán / giá trị đơn hàng trung bình tầm bao nhiêu?',
      choices: ['Dưới 100k', '100–300k', '300k–1 triệu', '1–5 triệu', 'Trên 5 triệu', 'Chưa rõ'],
      note: 'Giúp Max tư vấn giá & ước lượng đúng — chọn khoảng gần đúng là được.' },
    { key: 'monthly_revenue', tier: 'context', optional: true, q: 'Doanh thu mỗi tháng khoảng bao nhiêu?',
      choices: ['Mới mở, chưa có doanh thu', 'Dưới 50 triệu', '50–200 triệu', '200 triệu–1 tỷ', 'Trên 1 tỷ', 'Không tiện chia sẻ'],
      note: 'Giúp Max ước lượng giai đoạn doanh nghiệp. Không tiện thì cứ bỏ qua.' },
    { key: 'monthly_marketing_budget', tier: 'context', optional: true, q: 'Ngân sách marketing mỗi tháng khoảng bao nhiêu?',
      choices: ['Chưa chạy quảng cáo', 'Dưới 5 triệu', '5–20 triệu', '20–50 triệu', 'Trên 50 triệu', 'Không tiện chia sẻ'],
      note: 'Để Max đề xuất kênh & phân bổ khả thi với túi tiền của bạn.' },
    { key: 'current_channels', tier: 'context', optional: true, q: 'Hiện bạn đang dùng kênh marketing nào?', ph: 'vd: Facebook, TikTok, Zalo OA' },
    { key: 'primary_goal', tier: 'context', q: '90 ngày tới bạn muốn ưu tiên điều gì nhất?',
      choices: ['Tăng nhận diện thương hiệu', 'Ra nhiều đơn / doanh thu', 'Giữ chân & chăm khách cũ', 'Ra mắt sản phẩm mới'],
      note: 'Chọn hướng ưu tiên — con số cụ thể sẽ chốt khi bạn lập từng chiến dịch theo dịp.' },
  ];
  // Field nào có cột riêng trong profile; còn lại gói vào intake_extra.answers (D-032)
  const PROFILE_COLUMN_KEYS = new Set(['business_name', 'industry', 'location', 'product_service',
    'target_customer', 'main_challenge', 'competitors', 'monthly_revenue',
    'monthly_marketing_budget', 'current_channels', 'primary_goal']);
  // AI-adaptive intake (Max phỏng vấn thông minh) — dùng khi có backend thật
  let _aiQ = '', _aiBusy = false, _aiStarted = false, _aiFailed = false;
  function aiIntakeView() {
    return `
      <div class="intake">
        <div class="intake-max"><span class="cav">🤖</span><b>Max phỏng vấn nhanh</b></div>
        <h3 class="intake-q">${_aiQ || 'Đang kết nối Max…'}</h3>
        ${_aiBusy ? '<div class="cbub typing" style="margin:6px 0"><i></i><i></i><i></i></div>'
          : `<input id="intakeBox" class="intake-input" placeholder="Trả lời Max…" autocomplete="off">
             <div class="intake-nav"><span></span>
               <button class="primary-btn" data-act="ai-intake-send" ${_aiQ ? '' : 'disabled'}>Trả lời →</button></div>`}
        <p class="muted intake-note">Max hỏi vài câu rồi tự lập hồ sơ — trả lời tự nhiên.</p>
      </div>`;
  }
  async function aiIntakeStart() {
    _aiStarted = true; _aiBusy = true;
    try {
      const r = await API.post('api/biz/intake', { message: '', user_id: _bizUserId });
      _aiBusy = false;
      if (r.error) { _aiFailed = true; route(); return; }
      _aiQ = r.question || ''; route();
    } catch (e) { _aiBusy = false; _aiFailed = true; route(); }
  }
  async function aiIntakeSend() {
    const box = document.getElementById('intakeBox');
    const msg = box ? box.value.trim() : '';
    if (!msg || _aiBusy) return;
    _aiBusy = true; route();
    try {
      const r = await API.post('api/biz/intake', { message: msg, user_id: _bizUserId });
      _aiBusy = false;
      if (r.error) { toast(r.error); route(); return; }
      if (r.mode === 'complete') {
        _aiQ = ''; _aiStarted = false;
        toast('Max đã đủ thông tin — hồ sơ tạo xong, chạy chẩn đoán được rồi');
        await refreshBiz(); renderRail(); renderTopbar(); route();
        return;
      }
      _aiQ = r.question || ''; route();
    } catch (e) { _aiBusy = false; toast('Lỗi kết nối Max'); route(); }
  }

  function intakeWizard() {
    // D-032: wizard có bước là luồng CHÍNH (kể cả khi có backend) — để gắn được
    // chip gợi ý + skip + provenance per-câu. AI-hội-thoại để dành/bỏ sau.
    return staticWizard();
  }
  function staticWizard() {
    const n = INTAKE_STEPS.length;
    const i = Math.min(_intakeStep, n - 1);
    const st = INTAKE_STEPS[i];
    // textarea content cần escape & < > (D-032 §11)
    const val = (_intakeData[st.key] || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    const preview = (!apiAvailable || !M.bizEnabled);
    const canSkip = st.optional || st.strategic;   // strategic skip → AI suy (giả định)
    const body = st.choices
      ? `<div class="intake-choices">${st.choices.map(c =>
          `<button class="intake-choice${_intakeData[st.key] === c || (c === 'Không tiện chia sẻ' && _intakeData[st.key] === 'chưa rõ') ? ' on' : ''}" data-act="intake-choice" data-val="${c.replace(/"/g, '&quot;')}">${c}</button>`).join('')}</div>`
      : `<textarea id="intakeBox" class="intake-input" rows="1" placeholder="${st.strategic ? 'Trả lời, hoặc bấm gợi ý bên dưới…' : 'Nhập câu trả lời…'}">${val}</textarea>`;
    // D-032 step 2: câu chiến lược → fetch + render chip gợi ý (recognition, chọn nhiều được)
    let chips = '';
    if (st.strategic) {
      if (!_intakeSuggestDone && apiAvailable) fetchIntakeSuggestions();
      const sug = _intakeSuggest[st.key] || [];
      if (sug.length) {
        chips = `<div class="intake-sug"><span class="intake-sug-lbl">Gợi ý phổ biến trong ngành — bấm để chọn (chọn nhiều được):</span>
          <div class="intake-sug-chips">${sug.map(s =>
            `<button class="intake-sug-chip" data-act="intake-suggest" data-val="${s.replace(/"/g, '&quot;')}">+ ${s}</button>`).join('')}</div></div>`;
      } else if (_intakeSuggestBusy) {
        chips = `<div class="intake-sug muted">💡 Đang gợi ý theo ngành của bạn…</div>`;
      }
    }
    const tag = st.strategic ? ' · để Max đoán nếu chưa chắc' : (st.optional ? ' · không bắt buộc' : '');
    return `
      <div class="intake">
        <div class="intake-prog"><div class="intake-bar" style="width:${Math.round(i / n * 100)}%"></div></div>
        <p class="intake-count">Câu ${i + 1}/${n}${tag}</p>
        <h3 class="intake-q">${st.q}</h3>
        ${st.helper ? `<p class="intake-helper">💬 ${st.helper}</p>` : ''}
        ${body}
        ${chips}
        ${st.note ? `<p class="muted intake-note">${st.note}</p>` : ''}
        <div class="intake-nav">
          ${i > 0 ? '<button class="ghost-line" data-act="intake-back">← Quay lại</button>' : '<span></span>'}
          <div style="display:flex;gap:8px">
            ${canSkip ? `<button class="ghost-line" data-act="intake-skip">${st.strategic ? '🤖 Để Max đoán' : 'Bỏ qua'}</button>` : ''}
            ${st.choices ? '' : `<button class="primary-btn" data-act="intake-next">${i === n - 1 ? '✓ Hoàn tất' : 'Tiếp →'}</button>`}
          </div>
        </div>
        ${preview ? '<p class="muted intake-note">⚠️ Xem trước — cần kết nối Supabase để lưu khi hoàn tất.</p>' : ''}
      </div>`;
  }
  const PROFILE_FIELDS = [
    ['business_name', 'Tên doanh nghiệp', 'vd: Cà phê An'],
    ['industry', 'Ngành', 'vd: F&B — Quán cà phê'],
    ['product_service', 'Sản phẩm / Dịch vụ', 'vd: Cà phê specialty'],
    ['target_customer', 'Khách hàng mục tiêu', 'vd: Dân văn phòng 25–34, Q.1'],
    ['location', 'Khu vực', 'vd: TP.HCM, Quận 1'],
    ['monthly_revenue', 'Doanh thu/tháng', "vd: 50–200 triệu (hoặc 'chưa rõ')"],
    ['monthly_marketing_budget', 'Ngân sách marketing/tháng', 'vd: 15 triệu'],
    ['primary_goal', 'Mục tiêu chính (định hướng)', 'vd: tăng nhận diện / ra đơn / giữ chân khách'],
    ['current_channels', 'Kênh đang dùng', 'vd: Facebook, TikTok, Zalo OA'],
    ['main_challenge', 'Thách thức lớn nhất', 'vd: cạnh tranh chuỗi lớn'],
    ['competitors', 'Đối thủ chính', 'vd: Highlands, Phúc Long'],
  ];
  function profileForm(p) {
    const note = (apiAvailable && M.bizEnabled)
      ? 'Điền hồ sơ để Max chẩn đoán & lập chiến lược cho đúng doanh nghiệp của bạn.'
      : '⚠️ Đang ở chế độ xem trước — cần kết nối Supabase (server) để Lưu hồ sơ & chạy phân tích.';
    return `
      <p class="muted" style="margin-bottom:12px">${note}</p>
      <div class="form">${PROFILE_FIELDS.map(([k, l, ph]) =>
        `<label class="fld"><span>${l}</span><input id="pf_${k}" value="${(p[k] || '').replace(/"/g, '&quot;')}" placeholder="${ph}"></label>`).join('')}</div>
      <div style="display:flex;gap:8px;margin-top:14px">
        <button class="primary-btn" data-act="save-profile">💾 Lưu hồ sơ</button>
        ${(_editProfile && Object.keys(p).length) ? '<button class="ghost-line" data-act="cancel-profile">Huỷ</button>' : ''}
      </div>`;
  }

  P.dossier = {
    title: 'Hồ sơ doanh nghiệp',
    sub: 'Tủ hồ sơ — mọi thứ Max tạo ra được lưu ở đây: hồ sơ, chẩn đoán, kết quả phân tích, lịch sử chạy',
    get actions() {
      const users = M.bizUsers || [];
      const sel = users.length
        ? `<div class="sel" data-act="switch-user" title="Đổi người dùng đang xem">${
            (M.bizUser && (M.bizUser.name || M.bizUser.user_id)) || M.bizUserId || 'Chọn user'} ▾</div>`
        : '';
      return sel + runBtn('full', '▶ Chạy phân tích toàn diện', 'primary-btn');
    },
    render: () => {
      const p = M.bizProfile || {};
      const jobs = M.agentJobs || [];
      const runs = M.bizSkillRuns || [];
      const camps = M.bizCampaigns || [];
      const comps = M.bizCompetitors || [];
      const bv = M.bizBrandVoice;
      const u = M.bizUser || {};
      const hasProfile = Object.keys(p).length > 0;
      // Form-first: chưa có hồ sơ → hiện form điền (kể cả chưa nối backend). Có rồi → xem + Sửa.
      const showForm = _editProfile || !hasProfile;

      const profileBody = !hasProfile ? intakeWizard()
        : _editProfile ? profileForm(p)
        : `
          ${profRow('Doanh nghiệp', p.business_name)}
          ${profRow('Ngành', p.industry)}
          ${profRow('Giai đoạn', p.stage)}
          ${profRow('Sản phẩm/Dịch vụ', p.product_service)}
          ${profRow('Khách hàng mục tiêu', p.target_customer)}
          ${profRow('Doanh thu/tháng', p.monthly_revenue)}
          ${profRow('Ngân sách marketing', p.monthly_marketing_budget)}
          ${profRow('Mục tiêu chính', p.primary_goal)}
          ${profRow('Kênh đang dùng', p.current_channels)}
          ${profRow('Thách thức', p.main_challenge)}
          ${profRow('USP', p.usp)}
          ${profRow('Khu vực', p.location)}
          <button class="ghost-line full" data-act="edit-profile" style="margin-top:12px">✎ Sửa hồ sơ</button>`;

      // 1 khối thống nhất: mỗi phân tích = 1 dòng, trạng thái + đúng 1 hành động.
      const ANALYSES = [
        ['market_research','market','🌐','Nghiên cứu thị trường','TAM/SAM/SOM + động lực'],
        ['competitor','competitor','🥊','Phân tích đối thủ','8 đối thủ × 8 chiều'],
        ['customer_insight','customer','👤','Customer Insight','ICP + JTBD + tâm lý'],
        ['psychology_pricing','pricing','💲','Định giá & Tâm lý','Mô hình giá + tâm lý'],
        ['swot','swot','⚖️','SWOT','Ma trận chiến lược'],
        ['synthesis','strategy','🎯','Chiến lược tổng hợp','SAVE + định hướng 90 ngày'],
      ];
      const isRunning = (t) => jobs.some(j => j.status === 'running' && (j.task === t || j.task === 'full'));
      const diagBody = `<div class="diag-list">${ANALYSES.map(([k, task, ic, name, desc]) => {
        const run = runs.find(r => r.skill_name === k);
        const running = isRunning(task);
        const st = run ? 'done' : running ? 'running' : 'pending';
        const rate = (run && run.rating) ? (run.rating >= 4 ? ' 👍' : run.rating <= 2 ? ' 👎' : ' ★' + run.rating) : '';
        const act = running ? badge('Đang chạy', 'amber')
          : run ? `<a class="primary-btn sm" href="#${task}">Xem & sửa</a>
                   <button class="icon-btn" data-act="run-agent" data-task="${task}" title="Chạy lại bản mới">↻</button>`
          : `<button class="ghost-line sm" data-act="run-agent" data-task="${task}">▶ Chạy</button>`;
        return `<div class="diag-row ${st}">
          <span class="diag-ic">${st === 'done' ? '✓' : ic}</span>
          <div class="diag-main"><p><a class="diag-link" href="#${task}" title="Mở trang phân tích chi tiết">${name}</a></p><span class="muted">${desc}</span></div>
          <div class="diag-state muted">${run ? 'v' + run.version + rate : ''}</div>
          <div class="diag-act">${act}</div>
        </div>`;
      }).join('')}</div>`;

      return `
      <section class="grid">
        ${card('Hồ sơ doanh nghiệp', profileBody, {cls:'span-5', action: u.user_id ? badge('user ' + u.user_id) : ''})}

        ${card('Chẩn đoán & kết quả', diagBody, {cls:'span-7',
          action: `<span class="muted">Chạy từng mục, hoặc “Toàn diện” ở góc trên</span>`})}

        ${jobs.length ? card('Tiến trình Agent (realtime)', `
          <ul class="rows">${jobs.map(j=>`
            <li class="row">
              <div class="row-main"><p>${j.label} <span class="muted">· user ${j.userId}</span></p>
                <span class="muted">${j.status==='running'? (j.progress||'…') : (j.error || j.summary || '')}</span></div>
              ${jobStatusTag(j.status)}
            </li>`).join('')}</ul>`, {cls:'span-12'}) : ''}

        ${card('Tài khoản & quota', `
          ${profRow('User', u.name || u.user_id)}
          ${profRow('Gói', u.plan)}
          ${profRow('Token đã dùng', u.token_used!=null ? fmtNum(u.token_used) : null)}
          ${profRow('Quota token', u.token_quota!=null ? fmtNum(u.token_quota) : null)}
          ${bv ? `<div class="kv"><span>Brand Voice</span><b>${badge('v'+bv.version,'green')}</b></div>`
               : `<div class="kv"><span>Brand Voice</span><b>${badge('Chưa setup','amber')}</b></div>`}
        `, {cls:'span-4'})}

        ${card(`Chiến dịch (${camps.length})`, camps.length ? table(
          ['Tên','Mục tiêu','Trạng thái'],
          camps.map(c=>[c.name||'(chưa đặt tên)', c.primary_goal||'—',
            badge(c.status||'draft', c.status==='active'?'green':c.status==='archived'?'':'amber')])) :
          `<p class="muted">Chưa có chiến dịch.</p>`, {cls:'span-4'})}

        ${card(`Đối thủ theo dõi (${comps.length})`, comps.length ? table(
          ['Fanpage','Chu kỳ (h)','Ads'],
          comps.map(c=>[c.page_name||'—', c.interval_hours||24, (c.last_ad_ids||[]).length])) :
          `<p class="muted">Chưa theo dõi đối thủ nào.</p>`, {cls:'span-4'})}
      </section>`;
    },
    mount: () => {
      const aiMode = apiAvailable && M.bizEnabled && !_aiFailed && !(M.bizProfile && Object.keys(M.bizProfile).length);
      if (aiMode && !_aiStarted) { aiIntakeStart(); return; }
      const box = document.getElementById('intakeBox');
      if (box) {
        box.focus();
        // D-032 §11: textarea tự giãn cao + Enter=Tiếp, Shift+Enter=xuống dòng
        const grow = () => { if (box.tagName === 'TEXTAREA') { box.style.height = 'auto'; box.style.height = box.scrollHeight + 'px'; } };
        grow();
        box.oninput = grow;
        box.onkeydown = (e) => {
          if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); aiMode ? aiIntakeSend() : handleIntake('next'); }
        };
      }
    },
  };

  // điều khiển wizard intake (giữ giá trị ô đang gõ trước khi chuyển bước)
  // D-032: gói _intakeData → field cột + intake_extra{answers, provenance}
  function buildProfilePayload() {
    const cols = {}, answers = {};
    for (const k in _intakeData) {
      const v = _intakeData[k];
      if (v == null || v === '') continue;
      if (PROFILE_COLUMN_KEYS.has(k)) cols[k] = v; else answers[k] = v;
    }
    const extra = {};
    if (Object.keys(answers).length) extra.answers = answers;
    if (Object.keys(_intakeProv).length) extra.provenance = _intakeProv;
    if (Object.keys(extra).length) cols.intake_extra = extra;
    return cols;
  }
  async function handleIntake(action, choiceVal) {
    const box = document.getElementById('intakeBox');
    const st = INTAKE_STEPS[Math.min(_intakeStep, INTAKE_STEPS.length - 1)];
    if (box) _intakeData[st.key] = box.value.trim();
    // Chọn khoảng/hướng: "Không tiện chia sẻ" → lưu "chưa rõ" (khớp AI-adaptive mode)
    if (action === 'choice') {
      _intakeData[st.key] = (choiceVal === 'Không tiện chia sẻ') ? 'chưa rõ' : choiceVal;
      _intakeProv[st.key] = 'typed';
    }
    if (action === 'suggest') {        // bấm chip gợi ý → thêm vào câu trả lời (chọn nhiều, MỖI dòng 1 ý)
      const cur = (_intakeData[st.key] || '').trim();
      const add = (choiceVal || '').trim();
      const has = cur.split(/\n/).some(p => p.trim() === add);
      _intakeData[st.key] = has ? cur : (cur ? cur + '\n' + add : add);
      _intakeProv[st.key] = 'suggested';
      route(); return;
    }
    if (action === 'back') { _intakeStep = Math.max(0, _intakeStep - 1); route(); return; }
    if (action === 'skip') {
      if (st.strategic) {            // tầng CMO bỏ qua → AI suy → gắn nhãn "(giả định)"
        _intakeProv[st.key] = 'inferred'; delete _intakeData[st.key];
      } else if (st.key === 'monthly_revenue') {
        _intakeData[st.key] = 'chưa rõ';   // không bao giờ rỗng (A1b)
      }
      _intakeStep++; route(); return;
    }
    // action === 'next'
    const v = _intakeData[st.key];
    if (st.strategic) _intakeProv[st.key] = v ? 'typed' : 'inferred';  // empty → AI suy
    else if (v) _intakeProv[st.key] = 'typed';
    // Bắt buộc: core không-optional, không-strategic phải có giá trị
    if (!st.optional && !st.strategic && !v) { toast('Vui lòng nhập, hoặc bấm "Để Max đoán/Bỏ qua"'); return; }
    if (_intakeStep < INTAKE_STEPS.length - 1) { _intakeStep++; route(); return; }
    if (!apiAvailable) { toast('Đây là bản xem trước — cần backend + Supabase để lưu'); return; }
    try {
      const r = await API.post('api/biz/profile', { fields: buildProfilePayload(), user_id: _bizUserId });
      if (r.error) { toast(r.error); return; }
      _intakeStep = 0; _intakeData = {}; _intakeProv = {};
      toast('Đã tạo hồ sơ — giờ chạy chẩn đoán được rồi');
      await refreshBiz(); renderRail(); renderTopbar(); route();
    } catch (e) { toast('Lưu hồ sơ thất bại'); }
  }

  /* ---- Trang đọc & chỉnh sửa output research (#doc/<id>) ---- */
  let _docId = null, _docRun = null, _docVersions = [], _docEdit = false, _docPatching = false, _docAsk = '';
  P.doc = {
    title: 'Đọc & chỉnh sửa output',
    sub: '',
    actions: `<a class="ghost-line" href="#dossier">← Quay lại Hồ sơ</a>`,
    render: () => `<div id="docView" class="doc-wrap"><p class="muted">Đang tải…</p></div>`,
    mount: () => { _docEdit = false; loadDoc(); },
  };
  async function loadDoc() {
    _docRun = null; _docVersions = []; _docAsk = '';
    if (!_docId) { renderDoc(); return; }
    if (!apiAvailable) {                       // bản demo tĩnh → dùng output mẫu
      _docRun = (M.sampleDocs || {})[_docId] || null;
      _docVersions = _docRun ? (M.bizSkillRuns || []).filter(v => v.skill_name === _docRun.skill_name) : [];
      renderDoc(); return;
    }
    try { _docRun = await API.get('api/biz/skillrun/' + _docId); } catch (e) { _docRun = null; }
    if (_docRun && _docRun.skill_name) {
      try {
        const v = await API.get('api/biz/skillruns?skill=' + encodeURIComponent(_docRun.skill_name) +
          (_bizUserId != null ? '&user_id=' + _bizUserId : ''));
        _docVersions = v.versions || [];
      } catch (e) { _docVersions = []; }
    }
    renderDoc();
  }
  function renderDoc() {
    const el = document.getElementById('docView');
    if (!el) return;
    if (!_docRun || !_docRun.id) {
      el.innerHTML = `<div class="card"><p class="muted">Không tải được nội dung. Cần backend + Supabase, hoặc output chưa tồn tại.</p></div>`;
      return;
    }
    const r = _docRun;
    const when = (r.created_at || '').replace('T', ' ').slice(0, 16);
    const bodyOrEditor = _docEdit
      ? `<div class="doc-editor">
           <textarea id="docEditBox" class="doc-edit-area">${(r.content || '').replace(/</g,'&lt;')}</textarea>
           <div class="doc-edit-act">
             <button class="ghost-line sm" data-act="doc-edit-cancel">Huỷ</button>
             <button class="primary-btn sm" data-act="doc-edit-save">💾 Lưu thành version mới</button>
           </div>
         </div>`
      : `<article class="doc-body">${renderAIContent(r.content || '(trống)')}</article>`;
    const versions = _docVersions.length > 1 ? `
      <aside class="doc-versions">
        <h4>Lịch sử version (${_docVersions.length})</h4>
        <ul class="ver-list">${_docVersions.map(v => `
          <li class="${v.id===r.id?'cur':''}">
            <a href="#" data-act="doc-open" data-id="${v.id}">v${v.version}</a>
            <span class="muted">${(v.created_at||'').slice(0,10)} · ${v.rating?'★'+v.rating:'—'}</span>
            ${v.id!==r.id ? `<button class="ghost-line sm" data-act="doc-set-current" data-content-id="${v.id}">Đặt hiện hành</button>` : '<span class="tag green">hiện hành</span>'}
          </li>`).join('')}</ul>
      </aside>` : '';
    el.innerHTML = `
      <div class="doc-head">
        <div>
          <h2 class="doc-title">${r.skill_name || 'Output'} <span class="tag">v${r.version || 1}</span></h2>
          <p class="muted">${when}${r.model_used ? ' · ' + r.model_used : ''}</p>
        </div>
        <div class="doc-actions">
          <button class="rate-btn ${r.rating>=4?'on up':''}" data-act="rate-skillrun" data-rating="5" title="Tốt">👍</button>
          <button class="rate-btn ${(r.rating&&r.rating<=2)?'on down':''}" data-act="rate-skillrun" data-rating="1" title="Chưa đạt">👎</button>
          <button class="ghost-line sm" data-act="copy-skillrun">📋 Copy</button>
          ${_docEdit ? '' : '<button class="ghost-line sm" data-act="doc-edit">✎ Sửa tay</button>'}
        </div>
      </div>
      ${_docEdit ? '' : `<div class="doc-patch">
        <input id="docPatchBox" type="text" placeholder="Nhờ Max chỉnh: vd 'viết lại phần định giá ngắn hơn'…">
        <button class="primary-btn sm" data-act="doc-patch" ${_docPatching?'disabled':''}>${_docPatching?'Đang sửa…':'🤖 Nhờ Max chỉnh'}</button>
      </div>
      ${_docAsk ? `<p class="doc-ask">🤖 Max cần rõ thêm: ${_docAsk}</p>` : ''}`}
      <div class="doc-grid">${bodyOrEditor}${versions}</div>`;
    enhancePosMaps(el);   // D-034 #4: ASCII map → visual
  }

  /* ---- Market research ---- */
  P.market = {
    title: 'Nghiên cứu thị trường', sub: 'TAM / SAM / SOM + động lực thị trường',
    actions: `<a class="ghost-line" href="#dossier">← Hồ sơ</a>`,
    render: () => `
      <section class="grid">
        ${agentSection('market','market_research')}
      </section>`,
    mount: () => {},
  };

  /* ---- Competitor ---- */
  P.competitor = {
    title: 'Phân tích đối thủ', sub: '8 chiều cạnh tranh + theo dõi Ads Library',
    actions: `<a class="ghost-line" href="#dossier">← Hồ sơ</a> <button class="primary-btn" data-act="add-tracked">＋ Thêm đối thủ theo dõi</button>`,
    render: () => `
      <section class="grid">
        ${agentSection('competitor','competitor')}
        ${(M.tracked||[]).length ? card('Đối thủ đang theo dõi (Ads Library)', `
          <ul class="rows">
            ${M.tracked.map(t=>`
              <li class="row">
                <span class="s-dot ${t.status==='online'?'online':''}"></span>
                <div class="row-main"><p>${t.name}</p><span class="muted">${t.last}</span></div>
                <span class="tag">${t.ads} ads</span>
                ${t.id?`<button class="icon-btn" data-act="del-tracked" data-id="${t.id}" title="Bỏ theo dõi">✕</button>`:''}
              </li>`).join('')}
          </ul>`, {cls:'span-12'}) : ''}
      </section>`,
    mount: () => {},
  };

  /* ---- Customer insight ---- */
  P.customer = {
    title: 'Customer Insight', sub: 'ICP · Jobs-to-be-Done · Pain / Gain / Motivation',
    actions: `<a class="ghost-line" href="#dossier">← Hồ sơ</a>`,
    render: () => `
      <section class="grid">
        ${agentSection('customer','customer_insight')}
      </section>`,
    mount: () => {},
  };

  /* ---- Pricing ---- */
  P.pricing = {
    title: 'Định giá & Tâm lý', sub: 'Mô hình giá theo phân khúc + chiến thuật tâm lý',
    actions: `<a class="ghost-line" href="#dossier">← Hồ sơ</a>`,
    render: () => `
      <section class="grid">
        ${agentSection('pricing','psychology_pricing')}
      </section>`,
    mount: () => {},
  };

  /* ---- SWOT ---- */
  P.swot = {
    title: 'SWOT', sub: 'Ma trận chiến lược + TOWS (SO/ST/WO/WT)',
    actions: `<a class="ghost-line" href="#dossier">← Hồ sơ</a>`,
    render: () => `
      <section class="grid">
        ${agentSection('swot','swot')}
      </section>`,
    mount: () => {},
  };

  /* ---- Strategy (M0: chiến lược thật, tóm-tắt-trước) ---- */
  const strategyMock = () => `
        ${card('SAVE Framework', `
          <div class="save">${M.saveFramework.map(s=>`
            <div class="save-item"><div class="save-k">${s.k}</div>
              <div><p>${s.name}</p><span class="muted">${s.text}</span></div></div>`).join('')}</div>`, {cls:'span-6'})}
        ${card('Mục tiêu định hướng theo giai đoạn', `<ul class="bullet">${M.directionalGoals.map(g=>`<li>🧭 ${g}</li>`).join('')}</ul>
          <p class="muted" style="margin-top:8px">Số cụ thể (SMART, deadline) chốt khi lập chiến dịch theo dịp.</p>`, {cls:'span-6'})}
        ${card('Roadmap 90 ngày', `
          <div class="roadmap">${M.roadmap.map(r=>`
            <div class="rm-phase"><span class="rm-tag">${r.phase}</span><p class="rm-title">${r.title}</p>
              <ul class="bullet">${r.items.map(i=>`<li>${i}</li>`).join('')}</ul></div>`).join('')}</div>`, {cls:'span-12'})}`;
  // Banner 2 tầng: Synthesis = la bàn (định hướng); số cụ thể chốt ở chiến dịch (B1)
  const directionalBanner = `
        <div class="card span-12 dir-banner">
          🧭 Đây là <b>ĐỊNH HƯỚNG</b> chiến lược 90 ngày (la bàn): định vị, trục nội dung,
          kênh, ưu tiên từng giai đoạn. Con số cụ thể — SMART, ngân sách đợt, deadline —
          sẽ được <b>chốt khi bạn lập từng chiến dịch theo dịp</b>.
        </div>`;
  // D-032 step 3: thanh minh bạch — Max tự suy bao nhiêu mục chiến lược (founder bỏ trống)
  const _STRAT_KEYS = ['jtbd', 'competitive_alternative', 'differentiation', 'objection', 'competitors'];
  function inferredMeter() {
    const prov = ((M.bizProfile || {}).intake_extra || {}).provenance || {};
    const inferred = _STRAT_KEYS.filter(k => prov[k] === 'inferred');
    if (!inferred.length) return '';
    return `<div class="card span-12 infer-banner">🤖 Max đã <b>tự suy ${inferred.length}/${_STRAT_KEYS.length} mục chiến lược</b> (bạn để trống) —
      phần phân tích dựa vào chúng được đánh dấu <b>(giả định — cần kiểm chứng)</b>. Bổ sung ở Hồ sơ doanh nghiệp để sắc hơn.</div>`;
  }
  P.strategy = {
    title: 'Chiến lược tổng hợp', sub: 'Định vị · SAVE · Định hướng 90 ngày · KPI cần theo dõi',
    actions: `<a class="ghost-line" href="#tactical">🔨 Tactical Playbook</a> <a class="primary-btn" href="#occasion">→ Lập chiến dịch theo dịp</a>`,
    render: () => {
      const latest = (M.bizLatest || {}).synthesis;
      if (M.bizEnabled && latest) {
        // D-037a: 1 card duy nhất (bỏ agentBar trùng "Xem output") — output inline + nút rerun
        const running = (M.agentJobs || []).some(j => j.status === 'running' && (j.task === 'strategy' || j.task === 'full'));
        return `<section class="grid">
          ${directionalBanner}
          ${inferredMeter()}
          ${card('Chiến lược 90 ngày — do Max lập', `
            <div class="ai-output collapsible" data-skill-run="${latest.id}">Đang tải chiến lược…</div>
            <button class="ghost-line full collapse-toggle" data-act="toggle-collapse" style="margin-top:12px">Xem đầy đủ ▾</button>`,
            {cls:'span-12', action:`<span class="muted">v${latest.version} · ${(latest.created_at||'').slice(0,10)}</span> ${runBtn('strategy', running ? '↻ Đang chạy' : '↻ Tạo lại bản mới', 'ghost-line sm')}`})}
        </section>`;
      }
      if (M.bizEnabled) {
        return `<section class="grid">
          ${card('', `<div class="empty-cta">
            <div class="empty-ic">🎯</div>
            <h3>Chưa có chiến lược cho doanh nghiệp này</h3>
            <p class="muted">Điền Hồ sơ doanh nghiệp rồi chạy chẩn đoán — Max sẽ tổng hợp <b>định hướng</b> chiến lược 90 ngày (định vị, trục nội dung, kênh, ưu tiên từng giai đoạn).</p>
            <div class="empty-actions">
              <a class="primary-btn" href="#dossier">📋 Điền Hồ sơ doanh nghiệp</a>
              <button class="ghost-line" data-act="run-agent" data-task="full">🚀 Chạy chẩn đoán ngay</button>
            </div></div>`, {cls:'span-12'})}
        </section>`;
      }
      return `<section class="grid">
        <div class="card span-12" style="padding:10px 14px">${badge('Dữ liệu mẫu','amber')}
          <span class="muted"> Bản minh hoạ — chạy server thật (Supabase + LLM) để Max lập chiến lược cho bạn.</span></div>
        ${directionalBanner}
        ${strategyMock()}
      </section>`;
    },
    mount: () => {},
  };

  /* ---- Tactical Playbook (T5 — cách đánh chi tiết theo từng tệp) ---- */
  P.tactical = {
    title: 'Tactical Playbook', sub: 'Cách đánh chi tiết theo từng phân khúc — copy, kênh, khung test, KPI',
    actions: `<a class="ghost-line" href="#strategy">← Về Chiến lược</a>`,
    render: () => {
      const has = (M.bizSkillRuns || []).some(r => r.skill_name === 'tactical_playbook');
      if (M.bizEnabled && !has) {
        return `<section class="grid">
          ${card('', `<div class="empty-cta">
            <div class="empty-ic">🔨</div>
            <h3>Chưa có Tactical Playbook</h3>
            <p class="muted">Đây là <b>bản đồ chi tiết</b> đi sau Chiến lược (la bàn): với từng phân khúc ưu tiên,
            Max viết cách đánh theo phễu (TOFU/MOFU/BOFU) — copy mẫu, kênh, khung thử nghiệm, KPI cần theo dõi.
            Nó được tạo cùng lượt "Chạy phân tích toàn diện".</p>
            <div class="empty-actions">
              <button class="ghost-line" data-act="run-agent" data-task="full">🚀 Chạy phân tích toàn diện</button>
            </div></div>`, {cls:'span-12'})}
        </section>`;
      }
      return `<section class="grid">
        <div class="card span-12 dir-banner">🔨 Đây là <b>cách đánh chi tiết</b> (bản đồ) — đi sau <b>Chiến lược định hướng</b> (la bàn).
          Mỗi phân khúc có copy mẫu, kênh, khung thử nghiệm, KPI. Con số/ngân sách thật chốt khi lập chiến dịch theo dịp.</div>
        ${agentSection('full','tactical_playbook')}
      </section>`;
    },
    mount: () => {},
  };

  /* ---- Cầu nối: Lập chiến dịch theo dịp (M1 — đang phát triển) ---- */
  P.occasion = {
    title: 'Lập chiến dịch theo dịp', sub: 'Nơi chốt SMART thật — kế thừa định hướng từ Chiến lược',
    actions: `<a class="ghost-line" href="#strategy">← Về Chiến lược</a>`,
    render: () => `<section class="grid">
        ${card('', `<div class="empty-cta">
          <div class="empty-ic">🗓️</div>
          <h3>Đang phát triển — sắp ra mắt</h3>
          <p class="muted">Đây là chặng <b>M1</b>: từ một dịp cụ thể (Tết, ra mắt, Black Friday…) Max sẽ
          kế thừa <b>định hướng</b> ở Chiến lược 90 ngày rồi giúp bạn <b>chốt SMART thật</b> —
          mục tiêu có số, ngân sách đợt, deadline, theo đúng giai đoạn roadmap hiện tại.</p>
          <p class="muted">Chiến lược (la bàn) đã có. Bước này (bản đồ chi tiết) đang được xây.</p>
          <div class="empty-actions">
            <a class="ghost-line" href="#strategy">← Xem lại Chiến lược định hướng</a>
          </div></div>`, {cls:'span-12'})}
      </section>`,
    mount: () => {},
  };

  /* ---- Campaign Brief ---- */
  P.brief = {
    title: 'Campaign Brief', sub: 'Tài liệu chiến dịch 10 phần — tự prefill từ chiến lược',
    actions: `<a class="primary-btn" href="#content">→ Tạo nội dung</a>`,
    render: () => `
      <section class="grid">
        ${card('Chiến dịch “Mùa hè rực rỡ”', `
          <div class="brief">
            ${briefRow('🎯 Mục tiêu','Tăng 50% đơn online trong 90 ngày')}
            ${briefRow('👥 Đối tượng','Gen Z & văn phòng 22–34, TP.HCM')}
            ${briefRow('💰 Ngân sách','195.000.000₫ (6,5tr/ngày)')}
            ${briefRow('📣 Kênh','Facebook · TikTok · Zalo OA')}
            ${briefRow('🧲 Thông điệp','“Cà phê thật, giá thật, lấy nhanh”')}
            ${briefRow('📊 KPI','ROAS 4,0x · CPA < 25.000₫ · 1.600 đơn')}
            ${briefRow('🗓️ Thời gian','01/07 → 30/09/2026')}
            ${briefRow('🎬 Định dạng','Video 9:16, Carousel, UGC')}
          </div>`, {cls:'span-8'})}
        ${card('Pillar mix', donut('pillarChart','100%','Phân bổ',
          M.pillars.map(p=>[p.name,p.pct+'%'])), {cls:'span-4'})}
      </section>`,
    mount: () => { doughnut('pillarChart', M.pillars.map(p=>p.pct), M.pillars.map(p=>p.color)); },
  };

  /* ---- Lịch nội dung — Kế hoạch: Always-on (nền, LUÔN chạy) + Campaign theo dịp (cộng thêm) ---- */
  let _calView = 'plan';   // 'plan' (tháng) | 'week' (chi tiết tuần)
  let _calWeek = 1;        // tuần đang xem ở chế độ week
  const calPlan = () => M.calendarPlan || { days: [], weeks: 0, alwaysOn: [], campaigns: [] };
  const campActiveWeek = (w) => (calPlan().campaigns || []).filter(c => w >= c.fromWeek && w <= c.toWeek);
  // Bài campaign cộng thêm trong 1 (tuần, ngày)
  const campPostsAt = (w, d) => {
    const out = [];
    (calPlan().campaigns || []).forEach(c => (c.posts || []).forEach(p => {
      if (p.week === w && p.day === d) out.push({ ...p, camp: c });
    }));
    return out;
  };
  const alwaysCard = (p) => `<div class="cal-post" style="--accent:var(--green)">
      <div class="cal-post-top"><span class="trk on">Always-on</span><span class="pill-tag ${pillarCls(p.pillar)}">${p.pillar}</span></div>
      <p class="cal-post-title">${p.title}</p></div>`;
  const campCard = (p) => `<div class="cal-post" style="--accent:${p.camp.color}">
      <div class="cal-post-top"><span class="trk camp" style="--c:${p.camp.color}">${p.camp.name}</span><span class="pill-tag c4">Convert</span></div>
      <p class="cal-post-title">${p.title}</p><span class="cal-offer">🎁 ${p.camp.offer}</span></div>`;

  // VIEW THÁNG (kế hoạch) — Gantt theo tuần + tóm tắt mỗi tuần
  function calPlanView() {
    const P0 = calPlan(); const W = P0.weeks || 4;
    const bands = (P0.campaigns || []).map(c =>
      `<div class="band-camp" style="grid-column:${c.fromWeek} / ${c.toWeek + 1}; --c:${c.color}">
        <b>🔴 ${c.name}</b> · ${c.occasion} · 🎁 ${c.offer}</div>`).join('');
    const weekRows = Array.from({ length: W }, (_, k) => {
      const w = k + 1; const camps = campActiveWeek(w);
      const campCount = camps.reduce((n, c) => n + (c.posts || []).filter(p => p.week === w).length, 0);
      return `<div class="planweek">
        <div class="pw-head"><b>Tuần ${w}</b>
          <button class="ghost-line sm" data-act="cal-open-week" data-week="${w}">Mở chi tiết →</button></div>
        <div class="pw-tracks">
          <div class="pw-track on"><span class="trk on">🟢 Always-on</span> ${P0.alwaysOn.length} bài brand
            <button class="chip-btn sm" data-act="cal-gen" data-week="${w}" data-track="always">⚡ Tạo bài tuần ${w}</button></div>
          ${camps.length ? camps.map(c => `<div class="pw-track camp" style="--c:${c.color}">
            <span class="trk camp" style="--c:${c.color}">🔴 ${c.name}</span> ${campCount} bài đẩy offer
            <button class="chip-btn sm" data-act="cal-gen" data-week="${w}" data-track="camp">⚡ Tạo bài campaign</button></div>`).join('')
          : `<div class="pw-track muted">Không có campaign — chỉ chạy nền Always-on</div>`}
        </div></div>`;
    }).join('');
    return `
      <section class="calboard">
        <div class="cal-bands" style="grid-template-columns:repeat(${W},1fr)">
          <div class="band-base" style="grid-column:1 / -1"><span>🟢 Always-on · chạy liên tục cả ${W} tuần — KHÔNG tắt khi có campaign</span></div>
          ${bands}
        </div>
        <div class="plan-weekhead" style="grid-template-columns:repeat(${W},1fr)">
          ${Array.from({ length: W }, (_, k) => `<span>Tuần ${k + 1}</span>`).join('')}
        </div>
      </section>
      <section class="plan-list">${weekRows}</section>`;
  }

  // VIEW TUẦN (chi tiết) — mỗi ngày: always-on + campaign cộng thêm
  function calWeekView() {
    const P0 = calPlan(); const days = P0.days; const w = _calWeek;
    const camps = campActiveWeek(w);
    return `
      ${camps.length ? `<div class="cal-bands" style="grid-template-columns:1fr">
        ${camps.map(c => `<div class="band-camp" style="--c:${c.color}"><b>🔴 ${c.name}</b> · ${c.occasion} · 🎁 ${c.offer} · đang chạy Tuần ${w}</div>`).join('')}
      </div>` : ''}
      <div class="cal-grid" style="grid-template-columns:repeat(${days.length},1fr)">
        ${days.map((d, i) => {
          const cps = campPostsAt(w, i);
          const inCamp = cps.length > 0;
          return `<div class="cal-col ${inCamp ? 'in-camp' : ''}" ${inCamp ? `style="--c:${cps[0].camp.color}"` : ''}>
            <div class="cal-colhead">${d}${inCamp ? `<span class="col-dot" style="background:${cps[0].camp.color}"></span>` : ''}</div>
            ${alwaysCard(P0.alwaysOn[i] || { pillar: 'Educate', title: 'Bài brand' })}
            ${cps.map(campCard).join('')}
            <button class="cal-add" data-act="cal-gen" data-week="${w}" data-day="${i}">⚡ Tạo bài</button></div>`;
        }).join('')}
      </div>`;
  }

  P.calendar = {
    title: 'Kế hoạch nội dung',
    sub: 'Always-on (nền brand, luôn chạy) + Campaign theo dịp (cộng thêm, có khung thời gian)',
    get actions() {
      return `<div class="segmented">
          <button class="${_calView==='plan'?'on':''}" data-act="cal-view" data-view="plan">Kế hoạch tháng</button>
          <button class="${_calView==='week'?'on':''}" data-act="cal-view" data-view="week">Chi tiết tuần</button>
        </div>
        <button class="ghost-line" data-act="add-campaign-occasion">🎯 Tạo campaign theo dịp</button>`;
    },
    render: () => `
      ${M.bizEnabled ? '' : `<div class="cal-note">${badge('Bản thiết kế UX','amber')} <span class="muted"> Mô hình kế hoạch — dữ liệu mẫu, nối thật ở M1.</span></div>`}
      <div class="cal-legend">
        <span><i class="lg on"></i> 🟢 Always-on — bài brand chạy đều mỗi tuần (Educate/Trust/Engage), KHÔNG tắt khi có campaign</span>
        <span><i class="lg camp"></i> 🔴 Campaign theo dịp — bài đẩy offer, CỘNG THÊM lên nền trong đúng đợt</span>
      </div>
      ${_calView === 'plan' ? calPlanView() : calWeekView()}`,
    mount: () => {},
  };

  /* ---- Content generator ---- */
  P.content = {
    title: 'Trình tạo nội dung', sub: 'Sản xuất hàng loạt: bài viết + video + UGC + ads',
    actions: `<button class="primary-btn" data-act="gen-content">⚡ Tạo gói nội dung</button>`,
    render: () => `
      <section class="grid">
        ${card('Cấu hình', `
          <div class="form">
            ${field('Chủ đề','Khuyến mãi mùa hè')}
            ${field('Số bài/tuần','7 bài')}
            ${selectField('Kênh','Facebook + TikTok + Zalo')}
            ${selectField('Tông giọng','Thân thiện, trẻ trung')}
          </div>
          <button class="primary-btn full" data-act="gen-content" style="margin-top:14px">⚡ Tạo gói nội dung</button>`, {cls:'span-4'})}
        ${card(`Kết quả tạo (${(M.contentItems||[]).length} mục)`, `
          ${table(['#','Hook','Định dạng','Trạng thái'],
            (M.contentItems||[]).map(it=>[String(it.idx).padStart(2,'0'), it.hook, it.format,
              it.status==='ready'?badge('Sẵn sàng','green'):badge('Đang tạo','amber')]))}
        `, {cls:'span-8'})}
      </section>`,
    mount: () => {},
  };

  /* ---- Video scripts ---- */
  P.video = {
    title: 'Kịch bản video', sub: 'TikTok / Reels / Shorts từ slot lịch nội dung',
    render: () => `
      <section class="grid">
        ${card('Reel — “Hậu trường pha chế” (0:30)', `
          <div class="script">
            ${scene('0:00–0:03','HOOK','Cận tay rót cà phê — “Bạn có biết 90% quán pha sai bước này?”')}
            ${scene('0:03–0:12','BODY','Quay quy trình 3 bước, text overlay từng bước')}
            ${scene('0:12–0:24','PROOF','Khách thử + biểu cảm “wow”')}
            ${scene('0:24–0:30','CTA','“Ghé thử hôm nay — giảm 20% cho đơn đầu”')}
          </div>`, {cls:'span-7'})}
        ${card('Gợi ý sản xuất', `
          <ul class="bullet"><li>🎵 Nhạc trend: “summer vibe”</li><li>📐 Tỉ lệ 9:16, 1080×1920</li>
          <li>💡 Ánh sáng tự nhiên buổi sáng</li><li>⏱️ Hook < 3 giây giữ chân</li></ul>`, {cls:'span-5'})}
      </section>`,
    mount: () => {},
  };

  /* ---- UGC briefs ---- */
  P.ugc = {
    title: 'UGC Brief', sub: 'Brief cho creator: Micro / Mid / KOL',
    render: () => `
      <section class="grid">
        ${ugcCard('Micro (5–20k)','3 creator','Trải nghiệm thật, quay tại quán','120.000₫/video')}
        ${ugcCard('Mid (20–100k)','2 creator','Review chi tiết + so sánh','650.000₫/video')}
        ${ugcCard('KOL (100k+)','1 creator','Câu chuyện thương hiệu','5.000.000₫/video')}
      </section>`,
    mount: () => {},
  };

  /* ---- Ads copy ---- */
  P.adscopy = {
    title: 'Quảng cáo (copy)', sub: 'Theo phễu TOFU / MOFU / BOFU',
    render: () => `
      <section class="kanban">
        ${Object.entries(M.adsCopy).map(([k,v])=>`
          <div class="kan-col"><div class="kan-head"><b>${k}</b><span class="muted">${v.title}</span></div>
            ${v.items.map(i=>`<div class="kan-card">${i}</div>`).join('')}
            </div>`).join('')}
      </section>`,
    mount: () => {},
  };

  /* ---- Sales inbox ---- */
  P.inbox = {
    title: 'Sales Inbox Script', sub: 'Kịch bản chat Messenger / Zalo / IG — xử lý từ chối',
    render: () => `
      <section class="grid">
        ${card('Kịch bản: Khách hỏi giá', `
          <div class="chat">
            ${bubble('in','Quán ơi combo bao nhiêu vậy ạ?')}
            ${bubble('out','Dạ chào bạn 👋 Combo đôi mùa hè đang ưu đãi 79.000₫ (gồm 2 ly + topping). Bạn muốn vị nào để mình tư vấn nha?')}
            ${bubble('in','Hơi mắc so với quán gần nhà…')}
            ${bubble('out','Mình hiểu mà 🙌 Bù lại bạn được size lớn + tích điểm đổi ly miễn phí. Đặt trước giờ này còn được lấy nhanh khỏi xếp hàng nữa ạ!')}
          </div>`, {cls:'span-8'})}
        ${card('Thư viện xử lý từ chối', `
          <ul class="bullet"><li>💸 “Đắt” → nhấn giá trị + ưu đãi</li><li>⏰ “Để suy nghĩ” → tạo khan hiếm nhẹ</li>
          <li>🤔 “So sánh” → điểm khác biệt USP</li><li>📍 “Xa” → đặt trước / giao hàng</li></ul>`, {cls:'span-4'})}
      </section>`,
    mount: () => {},
  };

  /* ---- Sequence ---- */
  P.sequence = {
    title: 'Email / Zalo chuỗi', sub: 'Nurture cho lead / khách / winback',
    actions: ``,
    render: () => `
      <section class="grid">
        ${card('Chuỗi Welcome (4 bước)', `
          <div class="seq">${M.sequence.map((s,i)=>`
            <div class="seq-step"><div class="seq-dot">${i+1}</div>
              <div class="seq-body"><div class="seq-top"><b>${s.day}</b><span class="tag green">Open ${s.open}</span></div>
                <p>${s.subj}</p></div></div>`).join('')}</div>`, {cls:'span-8'})}
        ${card('Hiệu suất chuỗi', cv('seqChart',180), {cls:'span-4'})}
      </section>`,
    mount: () => {
      if (!hasChart) return;
      reg(new Chart(byId('seqChart'), { type:'line',
        data:{ labels:M.sequence.map(s=>s.day), datasets:[{ data:[62,48,41,38],
          borderColor:GREEN, backgroundColor:fill(GREEN), fill:true, tension:.4, borderWidth:2.5, pointRadius:3 }]},
        options:{ responsive:true, maintainAspectRatio:false, plugins:{legend:{display:false}},
          scales:{ x:{grid:noGrid}, y:{grid, ticks:{callback:v=>v+'%'}} } }}));
    },
  };

  /* ---- Brand voice ---- */
  P.voice = {
    title: 'Brand Voice',
    get sub() { return M.bizBrandVoice ? `Brand Voice thật · v${M.bizBrandVoice.version}` : 'Quy tắc giọng nói thương hiệu + hiệu chỉnh tông'; },
    render: () => {
      const bv = M.bizBrandVoice;
      if (bv) {
        const doList = (bv.do_rules || []).concat(bv.preferred_words?.map(w=>'Ưu tiên từ: '+w)||[]);
        const dontList = (bv.dont_rules || []).concat(bv.banned_words?.map(w=>'Tránh từ: '+w)||[]);
        const toneList = bv.tone_descriptors || [];
        return `
        <section class=”grid”>
          <div class=”card span-12” style=”display:flex;align-items:center;gap:10px;padding:10px 14px”>
            ${badge('Brand Voice thật · v'+bv.version,'green')}
            ${bv.industry_context ? `<span class=”muted”>${bv.industry_context}</span>` : ''}
          </div>
          ${card('Nên (Do)', `<ul class=”bullet”>${doList.length ? doList.map(d=>`<li>✅ ${d}</li>`).join('') : '<li class=”muted”>Chưa có quy tắc</li>'}</ul>`, {cls:'span-4'})}
          ${card('Không nên (Don\'t)', `<ul class=”bullet”>${dontList.length ? dontList.map(d=>`<li>🚫 ${d}</li>`).join('') : '<li class=”muted”>Chưa có quy tắc</li>'}</ul>`, {cls:'span-4'})}
          ${card('Tông giọng', `<div class=”chips”>${toneList.map(t=>`<span class=”chip on”>${t}</span>`).join('')||'<span class=”muted”>Chưa cấu hình</span>'}</div>`, {cls:'span-4'})}
          ${bv.sample_content ? card('Nội dung mẫu', `<blockquote class=”muted” style=”border-left:3px solid var(--primary);padding-left:12px;margin:0”>${bv.sample_content.slice(0,400)}</blockquote>`, {cls:'span-12'}) : ''}
        </section>`;
      }
      return `
      <section class=”grid”>
        ${M.bizEnabled ? card('Brand Voice', `<p class=”muted”>User chưa setup Brand Voice. Dùng bot để cấu hình (Sprint 5).</p>`, {cls:'span-12'}) : ''}
        ${card('Nên (Do)', `<ul class=”bullet”>${M.voice.do.map(d=>`<li>✅ ${d}</li>`).join('')}</ul>`, {cls:'span-4'})}
        ${card('Không nên (Don\'t)', `<ul class=”bullet”>${M.voice.dont.map(d=>`<li>🚫 ${d}</li>`).join('')}</ul>`, {cls:'span-4'})}
        ${card('Hiệu chỉnh tông', M.voice.tone.map(t=>`
          <div class=”slider”><div class=”slider-top”><span>${t.k}</span><b>${t.v}</b></div>
            <div class=”track”><div class=”fillbar” style=”width:${t.v}%”></div></div></div>`).join(''), {cls:'span-4'})}
        ${card('Kiểm tra tuân thủ giọng', `
          <div class=”voicecheck”><span class=”tag green”>Đạt 92%</span>
          <p class=”muted” style=”margin-top:8px”>Mẫu “Buổi sáng cần một lý do…” — phù hợp giọng thân thiện, câu ngắn. Gợi ý: giảm 1 emoji ở cuối.</p></div>`, {cls:'span-12'})}
      </section>`;
    },
    mount: () => {},
  };

  /* ---- Ads analytics ---- */
  let _adsDays = 7;
  P.adsanalytics = {
    title: 'Ads Analytics',
    get sub() {
      return M.adsEnabled && M.adsFbConn
        ? `Tài khoản: ${M.adsFbConn.account_name || M.adsFbConn.ad_account_id} · ${_adsDays} ngày gần nhất`
        : 'Phễu 6 tầng + Winners / Losers (FB Marketing API)';
    },
    actions: `<div class="segmented">
      <button class="${_adsDays===7?'on':''}" data-act="ads-days" data-days="7">7 ngày</button>
      <button class="${_adsDays===30?'on':''}" data-act="ads-days" data-days="30">30 ngày</button>
    </div>`,
    render: () => {
      const real = M.adsEnabled && (M.adsKpi || M.adsWinners);
      const kpi = M.adsKpi || {};
      const conn = M.adsFbConn;
      const winners = real ? (M.adsWinners || []) : M.winners;
      const losers  = real ? (M.adsLosers  || []) : M.losers;
      const daily   = M.adsDaily || [];
      const fmt_vnd = (n) => n >= 1e6 ? (n/1e6).toFixed(1)+'M₫' : n >= 1e3 ? (n/1e3).toFixed(0)+'K₫' : (n||0)+'₫';
      const adsKpiHtml = real ? `
        <section class="kpis">
          ${kpi_num('💸','ads_spend','Tổng chi tiêu',fmt_vnd(kpi.spend||0),'('+_adsDays+'ng)','',true)}
          ${kpi_num('📈','ads_roas','ROAS',(kpi.roas||0)+'x','','',true)}
          ${kpi_num('🎯','ads_cpl','CPL',fmt_vnd(kpi.cpl||0),'','',true)}
          ${kpi_num('👆','ads_ctr','CTR',(kpi.ctr||0)+'%','','',true)}
        </section>` : '';
      const connCard = conn ? card('Tài khoản FB đã kết nối', `
        ${profRow('Tài khoản', conn.account_name)}
        ${profRow('Ad Account ID', conn.ad_account_id)}
        ${profRow('Kết nối lúc', (conn.connected_at||'').slice(0,16).replace('T',' '))}
        ${profRow('Pull gần nhất', (conn.last_pull_at||'').slice(0,16).replace('T',' '))}
        ${profRow('Thông báo', conn.notification_enabled ? badge('Bật','green') : badge('Tắt','amber'))}
        <button class="ghost-line full" data-act="fb-connect" style="margin-top:12px">🔄 Kết nối lại / đổi tài khoản</button>
      `, {cls:'span-4'}) : (!real ? '' : card('Kết nối Facebook Ads', `
        <p class="muted" style="margin-bottom:12px">User này chưa kết nối Facebook Ads. Bấm để mở OAuth — sau khi đồng ý,
        bot sẽ tự pull số liệu và hiển thị tại đây.</p>
        <button class="primary-btn full" data-act="fb-connect">🔗 Kết nối Facebook Ads</button>`, {cls:'span-4'}));

      const winnersTable = winners.length ? table(
        ['Chiến dịch','ROAS','Chi tiêu','Leads'],
        winners.map(w=>[
          w.campaign_name || w.name || '—',
          badge(((w.roas||w.roas_x||0)+'x').replace('xx','x'), (w.roas||0)>=2?'green':'amber'),
          fmt_vnd(w.spend||0), fmtNum(w.leads||0)])) :
        `<p class="muted">Không có dữ liệu trong ${_adsDays} ngày qua.</p>`;

      const losersTable = losers.length ? table(
        ['Chiến dịch','ROAS','Chi tiêu','Leads'],
        losers.map(w=>[
          w.campaign_name || w.name || '—',
          badge(((w.roas||w.roas_x||0)+'x').replace('xx','x'), (w.roas||0)<1?'red':'amber'),
          fmt_vnd(w.spend||0), fmtNum(w.leads||0)])) :
        `<p class="muted">Không có dữ liệu.</p>`;

      return `
        ${adsKpiHtml}
        <section class="grid">
          ${real && daily.length ? card('Chi tiêu theo ngày (thật)', cv('adsLineChart',220), {cls:'span-8'}) : ''}
          ${connCard}
          ${!real ? card('Phễu chuyển đổi 6 tầng', `
            <div class="vfunnel">${M.funnel.map((f,i)=>`
              <div class="vf-row" style="--w:${100-i*13}%">
                <div class="vf-bar"><span class="vf-tier">${f.tier}</span><span class="vf-val">${num(f.value)}</span></div>
                <div class="vf-meta"><span>${f.cost}</span><span class="tag">${f.rate}</span></div>
              </div>`).join('')}</div>`, {cls:'span-7'}) : ''}
          ${!real ? card('Phân bổ chi tiêu', cv('spendDonut',200), {cls:'span-5'}) : ''}
          ${card('🏆 Winners', winnersTable, {cls:'span-6'})}
          ${card('⚠️ Losers',  losersTable,  {cls:'span-6'})}
          ${real && (M.adsCampaigns||[]).length ? card('Tất cả chiến dịch', table(
            ['Tên','Spend','ROAS','CPL','Impressions','Freq'],
            (M.adsCampaigns||[]).map(c=>[
              c.campaign_name||'—', fmt_vnd(c.spend||0),
              badge((c.roas||0)+'x',(c.roas||0)>=2?'green':'amber'),
              fmt_vnd(c.cpl||0), fmtNum(c.impressions||0), (c.frequency||0).toFixed(1)
            ])), {cls:'span-12'}) : ''}
        </section>`;
    },
    mount: () => {
      if (!hasChart) return;
      const real = M.adsEnabled && M.adsKpi;
      const daily = M.adsDaily || [];
      if (real && daily.length && byId('adsLineChart')) {
        reg(new Chart(byId('adsLineChart'), { type:'line',
          data:{ labels: daily.map(d=>d.date.slice(5)), datasets:[
            {label:'Chi tiêu', data: daily.map(d=>Math.round((d.spend||0)/1000)),
              borderColor:PRIMARY, backgroundColor:fill(PRIMARY), fill:true, tension:.4, borderWidth:2.5, pointRadius:2, yAxisID:'y'},
            {label:'ROAS', data: daily.map(d=>d.roas||0),
              borderColor:GREEN, backgroundColor:'transparent', fill:false, tension:.4, borderWidth:2, pointRadius:2, yAxisID:'y1'},
          ]},
          options:{ responsive:true, maintainAspectRatio:false, plugins:{legend:{display:true, position:'top'}},
            scales:{ x:{grid:noGrid}, y:{grid, ticks:{callback:v=>v+'K₫'}},
              y1:{position:'right', grid:{display:false}, ticks:{callback:v=>v+'x'}}} }}));
      } else if (!real && byId('spendDonut')) {
        doughnut('spendDonut',[40,28,18,14],[PRIMARY,PRIMARY2,CYAN,AMBER]);
      }
    },
  };

  function kpi_num(icon, id, label, val, trend, dir, noSpark) {
    return `<article class="kpi">
      <div class="kpi-top"><span class="kpi-icon">${icon}</span><span class="kpi-trend">${trend}</span></div>
      <p class="kpi-label">${label}</p><p class="kpi-value">${val}</p></article>`;
  }

  /* ---- Optimizer ---- */
  P.optimizer = {
    title: 'Tối ưu tự động', sub: 'Đề xuất pause / scale / nhân bản dựa trên KPI',
    actions: ``,
    render: () => `
      <section class="grid">
        ${card('Đề xuất tối ưu (4)', `
          <ul class="rows">${M.optimizations.map(o=>`
            <li class="row opt">
              <span class="opt-ic ${o.action}">${optIcon(o.action)}</span>
              <div class="row-main"><p>${o.text}</p><span class="muted">${o.why}</span></div>
              <div class="opt-act">
                <button class="ghost-line sm" data-act="opt-dismiss" data-id="${o.id||''}">Bỏ qua</button>
                <button class="primary-btn sm" data-act="opt-apply" data-id="${o.id||''}">Áp dụng</button></div>
            </li>`).join('')}</ul>`, {cls:'span-8'})}
        ${card('Tác động dự kiến', `
          ${miniRow('ROAS','3,09x','→ 3,6x','up')}
          ${miniRow('CPA TB','31.200₫','→ 26.000₫','up')}
          ${miniRow('Chi tiêu lãng phí','1,8M','→ 0,4M','up')}`, {cls:'span-4'})}
      </section>`,
    mount: () => {},
  };

  /* ---- Spy ---- */
  P.spy = {
    title: 'Theo dõi đối thủ', sub: 'FB Ads Library — hook, offer, định dạng creative',
    render: () => `
      <section class="grid">
        ${[['Highlands Coffee','“Mùa hè mát lạnh — mua 2 tặng 1”','Video 9:16','3 ngày'],
           ['Phúc Long','“Trà sữa signature giảm 30%”','Carousel','1 ngày'],
           ['Katinat','“BST mới — check-in nhận quà”','Image','5 giờ']].map(a=>`
          ${card('', `
            <div class="adcard">
              <div class="adcard-top"><span class="tag">${a[2]}</span><span class="muted">${a[3]} trước</span></div>
              <div class="adcard-img">🖼️</div>
              <p class="adcard-name">${a[0]}</p><p class="muted">${a[1]}</p>
            </div>`, {cls:'span-4'})}`).join('')}
        ${card('Mẫu hook phổ biến của đối thủ', `
          <div class="chips">${['Khuyến mãi %','Mua X tặng Y','BST mới','Check-in nhận quà','Giới hạn thời gian','Freeship'].map(h=>`<span class="chip">${h}</span>`).join('')}</div>`, {cls:'span-12'})}
      </section>`,
    mount: () => {},
  };

  /* ---- Schedule ---- */
  P.schedule = {
    title: 'Lịch trình & cảnh báo', sub: 'Tác vụ nền tự động + ngưỡng cảnh báo',
    render: () => `
      <section class="grid">
        ${card('Tác vụ nền', M.jobs.map(j=>`
          <div class="toggle-row">
            <div><b>${j.name}</b> <span class="muted">· ${j.when}</span></div>
            <label class="switch"><input type="checkbox" ${j.status==='on'?'checked':''}
              data-act="toggle-job" data-name="${encodeURIComponent(j.name)}"><span class="track-sw"></span></label>
          </div>`).join(''), {cls:'span-7'})}
        ${card('Ngưỡng cảnh báo', M.thresholds.map(t=>`
          <div class="kv"><span>${t.name}</span><b>${t.value}</b></div>`).join(''), {cls:'span-5'})}
        ${card('Cảnh báo gần đây', `<ul class="alerts">${M.alerts.map(a=>alertItem(a)).join('')}</ul>`, {cls:'span-12'})}
      </section>`,
    mount: () => {},
  };

  /* ---- Accounts ---- */
  P.accounts = {
    title: 'Kết nối tài khoản', sub: 'Facebook Ads — OAuth, token, đa tài khoản',
    actions: `<button class="primary-btn" data-act="connect-account">🔗 Kết nối tài khoản mới</button>`,
    render: () => `
      <section class="grid">
        ${(M.accounts||[]).map(a=>`
          ${card('', `
            <div class="acctcard">
              <div class="acctcard-top"><div class="fb">f</div>
                <div style="display:flex;align-items:center;gap:8px">
                  <span class="s-dot ${a.status==='online'?'online':''}"></span>
                  ${a.id&&typeof a.id==='number'?`<button class="icon-btn" data-act="disconnect-account" data-id="${a.id}" title="Ngắt kết nối">✕</button>`:''}
                </div></div>
              <p class="acctcard-name">${a.name}</p><p class="muted">${a.acc_id||a.id}</p>
              <div class="kv"><span>Chi tiêu</span><b>${a.spend}</b></div>
              <div class="kv"><span>Trạng thái</span><b>${a.status==='online'?'Đang chạy':'Tạm dừng'}</b></div>
              <button class="ghost-line full" data-act="toggle-account" data-id="${a.id}" style="margin-top:10px">${a.status==='online'?'Tạm dừng':'Kích hoạt'}</button>
            </div>`, {cls:'span-4'})}`).join('')}
        ${card('Quyền & bảo mật', `
          <ul class="bullet"><li>🔐 Token mã hóa Fernet (at rest)</li><li>🔄 Tự refresh trước hạn (Job 02:00)</li>
          <li>📋 Scope: ads_read, read_insights, ads_management</li><li>🚨 Phát hiện thu hồi → nhắc kết nối lại</li></ul>`, {cls:'span-4'})}
      </section>`,
    mount: () => {},
  };

  /* ---- Reports ---- */
  P.reports = {
    title: 'Báo cáo', sub: 'Lịch sử phân tích & báo cáo đã tạo',
    actions: `<button class="primary-btn" data-act="add-report">⤓ Xuất báo cáo mới</button>`,
    render: () => `
      <section class="grid">
        ${card('Báo cáo gần đây', table(['Tên','Loại','Ngày',''],
          (M.reports||[]).map(r=>[r.name, badge(r.type), r.date,
            `<a class="link" href="#">Tải</a>${r.id?` · <button class="icon-btn" data-act="del-report" data-id="${r.id}" title="Xoá">✕</button>`:''}`])), {cls:'span-12'})}
      </section>`,
    mount: () => {},
  };

  /* ---- Admin ---- */
  P.admin = {
    title: 'Quản trị', sub: 'Quota · usage · trạng thái hệ thống',
    render: () => `
      <section class="kpis kpis-3">
        ${miniStat('Người dùng','1.284','+38 tuần này')}
        ${miniStat('Token đã dùng','12,4M','tháng này')}
        ${miniStat('Skill chạy','8.420','30 ngày qua')}
      </section>
      <section class="grid">
        ${card('Quota người dùng', table(['User','Gói','Đã dùng / Quota','Tỉ lệ',''],
          (M.users||[]).map(u=>[u.uid||u.id, badge(u.plan, u.plan==='Free'?'':'green'),
            `${num(u.used)} / ${num(u.quota)}`,
            quotaBar(Math.round(u.used/u.quota*100)),
            (typeof u.id==='number')
              ? `<button class="ghost-line sm" data-act="add-quota" data-id="${u.id}">+Quota</button> <button class="ghost-line sm" data-act="reset-usage" data-id="${u.id}">Reset</button>`
              : ''])), {cls:'span-8'})}
        ${card('Trạng thái hệ thống', `
          <ul class="status">
            ${statusRow('Dữ liệu thật (Supabase)', M.bizEnabled?'Đã nối':'Mock')}
            ${statusRow('Thông báo Telegram', M.telegramEnabled?'Bật':'Tắt')}
            ${statusRow('Cập nhật realtime', 'SSE')}
          </ul>`, {cls:'span-4'})}
      </section>`,
    mount: () => {},
  };

  /* ---- Settings ---- */
  P.settings = {
    title: 'Cài đặt', sub: 'Trạng thái hệ thống · thông báo',
    render: () => `
      <section class="grid">
        ${card('Cấu hình hệ thống', `
          <div class="kv"><span>Dữ liệu nghiệp vụ (Supabase)</span><b>${M.bizEnabled?badge('Đã nối','green'):badge('Mock','amber')}</b></div>
          <div class="kv"><span>Thông báo Telegram</span><b>${M.telegramEnabled?badge('Bật','green'):badge('Tắt','amber')}</b></div>
          <div class="kv"><span>Cập nhật realtime</span><b>${badge('SSE','green')}</b></div>
          <p class="muted" style="margin-top:10px">Khoá API (Anthropic/Facebook/Telegram) cấu hình bằng biến môi trường phía server, không nhập trên web vì lý do bảo mật.</p>
        `, {cls:'span-6'})}
        ${card('Người dùng đang xem', M.bizUser ? `
          <div class="kv"><span>User</span><b>${M.bizUser.name||M.bizUser.user_id}</b></div>
          <div class="kv"><span>Gói</span><b>${M.bizUser.plan||'—'}</b></div>
          <div class="kv"><span>Token</span><b>${M.bizUser.token_used!=null?num(M.bizUser.token_used):'—'} / ${M.bizUser.token_quota!=null?num(M.bizUser.token_quota):'—'}</b></div>
          ${(M.bizUsers||[]).length>1?'<button class="ghost-line full" data-act="switch-user" style="margin-top:12px">Đổi người dùng</button>':''}
        ` : `<p class="muted">Chưa nối dữ liệu thật — chạy server có Supabase để xem thông tin user.</p>`, {cls:'span-6'})}
        ${card('Điều khiển & thông báo qua Telegram', `
          <div class="kv"><span>Trạng thái</span><b>${M.telegramEnabled?badge('Đã bật','green'):badge('Chưa cấu hình','amber')}</b></div>
          <p class="muted" style="margin:10px 0">Đặt biến môi trường <code>TELEGRAM_BOT_TOKEN</code> + <code>TELEGRAM_CHAT_ID</code> để nhận thông báo các thao tác (tạo chiến dịch, áp dụng tối ưu, kết nối tài khoản…) ngay trên Telegram — không cần ngồi máy.</p>
          <button class="primary-btn" data-act="notify-test">📨 Gửi thông báo test</button>`, {cls:'span-12'})}
        ${card('Thông báo', (() => { const s = M.settings || {}; return `
          ${toggleRow('Daily digest qua Telegram','daily_digest',s.daily_digest)}
          ${toggleRow('Cảnh báo ngưỡng (CPM/ROAS/Frequency)','alert_threshold',s.alert_threshold)}
          ${toggleRow('Báo cáo tuần','weekly_report',s.weekly_report)}
          ${toggleRow('Thông báo đối thủ có ad mới','competitor_new',s.competitor_new)}`; })(), {cls:'span-12'})}
      </section>`,
    mount: () => {},
  };

  /* ════════════ component builders ════════════ */
  function kpi(icon, spark, label, val, trend, dir) {
    return `<article class="kpi">
      <div class="kpi-top"><span class="kpi-icon ${spark}">${icon}</span><span class="kpi-trend ${dir}">${trend}</span></div>
      <p class="kpi-label">${label}</p><p class="kpi-value">${val}</p>
      <div class="spark-wrap"><canvas class="spark" data-spark="${spark}"></canvas></div></article>`;
  }
  function miniStat(label, val, sub) {
    return `<article class="kpi"><p class="kpi-label">${label}</p><p class="kpi-value">${val}</p><span class="muted">${sub}</span></article>`;
  }
  function donut(id, big, small, legend) {
    return `<div class="donut-wrap">${cv(id,200)}<div class="donut-center"><p class="donut-num">${big}</p><p class="muted">${small}</p></div></div>
      <ul class="legend-list">${legend.map((l,i)=>`<li><i class="dot c${i+1}"></i>${l[0]}<span>${l[1]}</span></li>`).join('')}</ul>`;
  }
  function table(head, rows) {
    return `<div class="tbl-wrap"><table class="tbl"><thead><tr>${head.map(h=>`<th>${h}</th>`).join('')}</tr></thead>
      <tbody>${rows.map(r=>`<tr>${r.map(c=>`<td>${c}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`;
  }
  const stepBadge = (s) => s==='done'?badge('Hoàn tất','green'):s==='running'?badge('Đang chạy','amber'):badge('Chờ','');
  const swotCell = (k,t,c,items) => `<div class="swot-cell ${c}"><div class="swot-k">${k}</div><h4>${t}</h4>
    <ul class="bullet">${items.map(i=>`<li>${i}</li>`).join('')}</ul></div>`;
  const briefRow = (k,v) => `<div class="brief-row"><span>${k}</span><b>${v}</b></div>`;
  const pillarCls = (p) => ({Educate:'c1',Trust:'c2',Engage:'c3',Convert:'c4'}[p]||'c1');
  const calPosts = (i) => M.calendarPosts
    ? M.calendarPosts.filter(p => p.day === i)
    : (M.calendar.posts[i] || []).map(p => ({ pillar: p.p, title: p.t }));
  const scene = (t,tag,txt) => `<div class="scene"><span class="scene-t">${t}</span><span class="tag">${tag}</span><p>${txt}</p></div>`;
  const ugcCard = (lvl,n,brief,price) => card('', `<div class="ugc"><p class="ugc-lvl">${lvl}</p><span class="tag">${n}</span>
    <p class="muted" style="margin:8px 0">${brief}</p><p class="ugc-price">${price}</p></div>`, {cls:'span-4'});
  const bubble = (dir,txt) => `<div class="bubble ${dir}">${txt}</div>`;
  const field = (l,v) => `<label class="fld"><span>${l}</span><input value="${v}"></label>`;
  const selectField = (l,v) => `<label class="fld"><span>${l}</span><div class="sel">${v} ▾</div></label>`;
  const optIcon = (a) => ({scale:'⬆️',pause:'⏸️',dup:'⧉',activate:'▶️'}[a]||'•');
  const miniRow = (l,a,b,dir) => `<div class="minirow"><span>${l}</span><b>${a} <span class="${dir}">${b}</span></b></div>`;
  const alertItem = (a) => `<li class="alert ${a.sev}"><span class="a-ic">${a.icon}</span><div class="row-main"><p>${a.title}</p><span class="muted">${a.meta}</span></div>${a.id?`<button class="icon-btn" data-act="dismiss-alert" data-id="${a.id}" title="Đóng">✕</button>`:''}</li>`;
  const statusRow = (l,v) => `<li><span class="s-dot online"></span>${l}<span class="muted">${v}</span></li>`;
  const quotaBar = (pct) => `<div class="track sm"><div class="fillbar ${pct>90?'hot':''}" style="width:${pct}%"></div></div>`;
  const toggleRow = (l,key,on) => `<div class="toggle-row"><span>${l}</span><label class="switch"><input type="checkbox" ${on?'checked':''} data-act="set-setting" data-key="${key}"><span class="track-sw"></span></label></div>`;

  /* ════════════ chart shortcuts ════════════ */
  const byId = (id) => document.getElementById(id);
  function line(id, sets, suffix='') {
    if (!hasChart || !byId(id)) return;
    reg(new Chart(byId(id), { type:'line',
      data:{ labels:days, datasets:sets.map(s=>({ label:s.label, data:s.data, borderColor:s.color,
        backgroundColor:fill(s.color), fill:true, tension:.4, borderWidth:2.5, pointRadius:0, pointHoverRadius:5 }))},
      options:{ responsive:true, maintainAspectRatio:false, plugins:{legend:{display:false}},
        scales:{ x:{grid:noGrid}, y:{grid, ticks:{callback:v=>v+suffix}, beginAtZero:true} } }}));
  }
  function bar(id, data) {
    if (!hasChart || !byId(id)) return;
    reg(new Chart(byId(id), { type:'bar',
      data:{ labels:days, datasets:[{ data, backgroundColor:fill(PRIMARY2), borderColor:PRIMARY2,
        borderWidth:{top:2,right:0,bottom:0,left:0}, borderRadius:8, borderSkipped:false, maxBarThickness:34 }]},
      options:{ responsive:true, maintainAspectRatio:false, plugins:{legend:{display:false}},
        scales:{ x:{grid:noGrid}, y:{grid, beginAtZero:true} } }}));
  }
  function doughnut(id, data, colors) {
    if (!hasChart || !byId(id)) return;
    reg(new Chart(byId(id), { type:'doughnut',
      data:{ datasets:[{ data, backgroundColor:colors||[PRIMARY,PRIMARY2,CYAN], borderWidth:0, hoverOffset:6 }]},
      options:{ responsive:true, maintainAspectRatio:false, cutout:'72%', plugins:{legend:{display:false}} }}));
  }
  function sparks() {
    const S = { spend:{d:[6,8,7,9,8,11,12],c:PRIMARY}, rev:{d:[10,12,11,14,16,15,18],c:GREEN},
      roas:{d:[2.6,2.8,2.7,3,2.9,3,3.1],c:PRIMARY2}, click:{d:[40,44,43,39,42,41,42],c:CYAN} };
    document.querySelectorAll('.spark').forEach(cvn=>{
      const s = S[cvn.dataset.spark]; if(!s||!hasChart) return;
      reg(new Chart(cvn, { type:'line', data:{ labels:s.d.map((_,i)=>i),
        datasets:[{ data:s.d, borderColor:s.c, backgroundColor:fill(s.c), fill:true, tension:.45, borderWidth:2, pointRadius:0 }]},
        options:{ responsive:true, maintainAspectRatio:false, plugins:{legend:{display:false},tooltip:{enabled:false}},
          scales:{ x:{display:false}, y:{display:false} } }}));
    });
  }

  /* ════════════ shell: sidebar + rail + router ════════════ */
  function renderSidebar(active) {
    const html = `
      <div class="brand"><div class="brand-logo">M</div>
        <div class="brand-text"><span class="brand-name">Marketing OS</span><span class="brand-sub">Auto Ads Facebook</span></div></div>
      <nav class="nav">${M.nav.map(g=>`
        ${g.group?`<p class="nav-label">${g.group}</p>`:''}
        ${g.items.map(it=>`<a class="nav-item ${it.id===active?'active':''}" href="#${it.id}"><span class="ic">${it.icon}</span> ${it.label}</a>`).join('')}
      `).join('')}</nav>
      <div class="sidebar-foot"><p class="version">v2.4.0 · demo dữ liệu mock</p></div>`;
    document.getElementById('sidebar').innerHTML = html;
  }
  function renderTopbar() {
    const tr = document.getElementById('topbarRight');
    if (!tr) return;
    const u = M.bizUser;
    const tokenChip = (u && u.token_quota != null)
      ? `<div class="token-chip" title="Token còn lại của user ${u.user_id}">⚡ ${num(Math.max(0,(u.token_quota||0)-(u.token_used||0)))} token</div>`
      : '';
    const name = (u && (u.name || ('User ' + u.user_id))) || 'Chưa nối dữ liệu';
    const initials = (u ? name : 'M').trim().slice(0, 2).toUpperCase();
    const switchable = (M.bizUsers || []).length > 1;
    document.getElementById('topbarTitle').textContent = '';
    tr.innerHTML =
      `<span id="liveDot" class="live-dot off" title="Cập nhật realtime"><i></i> Live</span>` +
      tokenChip +
      `<div class="user" ${switchable ? 'data-act="switch-user" style="cursor:pointer" title="Đổi người dùng"' : ''}>
        <div class="avatar">${initials}</div>
        <div class="user-text"><span class="user-name">${name}</span>
          <span class="user-role">${u ? (u.plan || 'user') : 'dữ liệu mẫu'}</span></div>
      </div>`;
    if (_sseLive) setLive(true);
  }
  function renderRail() {
    const u = M.bizUser;
    const used = u && u.token_used != null ? u.token_used : null;
    const quota = u && u.token_quota != null ? u.token_quota : null;
    const pct = (used != null && quota) ? Math.min(100, Math.round(used / quota * 100)) : null;
    const tokenCard = (pct != null)
      ? `<section class="card"><div class="card-head"><h3>Token đã dùng</h3></div>
          <p class="kpi-value" style="font-size:22px">${num(used)} <span class="muted" style="font-size:13px">/ ${num(quota)}</span></p>
          <div class="track" style="margin:8px 0"><div class="fillbar ${pct>90?'hot':''}" style="width:${pct}%"></div></div>
          <span class="muted">${pct}% quota · ${u.plan || 'user'} · user ${u.user_id}</span></section>`
      : `<section class="card"><div class="card-head"><h3>Token</h3></div>
          <span class="muted">Chưa nối dữ liệu thật. Chạy server có Supabase để xem quota theo user.</span></section>`;
    document.getElementById('rail').innerHTML = tokenCard +
      `<section class="card"><div class="card-head"><h3>Cảnh báo</h3><span class="pill warn">${(M.alerts||[]).length} mới</span></div>
        <ul class="alerts">${(M.alerts||[]).map(a=>alertItem(a)).join('')}</ul></section>
      <section class="card mini"><div class="card-head"><h3>Trạng thái hệ thống</h3></div>
        <ul class="status">
          <li><span class="s-dot ${M.bizEnabled?'online':''}"></span>Dữ liệu thật<span class="muted">${M.bizEnabled?'Đã nối':'Mock'}</span></li>
          <li><span class="s-dot ${M.telegramEnabled?'online':''}"></span>Telegram<span class="muted">${M.telegramEnabled?'Bật':'Tắt'}</span></li>
          <li><span class="s-dot ${_sseLive?'online':''}"></span>Realtime<span class="muted">${_sseLive?'Live':'SSE'}</span></li>
        </ul></section>`;
  }
  function route() {
    const raw = (location.hash.replace('#','') || 'dossier');
    const [seg0, seg1] = raw.split('/');
    let id = seg0;
    // pivot: bỏ Max chat → mọi thứ bắt đầu từ Hồ sơ doanh nghiệp
    if (id === 'pipeline' || id === 'agents' || id === 'home' || id === 'chat') id = 'dossier';
    if (id === 'doc') _docId = seg1 || null;                    // trang đọc output: #doc/<id>
    const page = P[id] || P.dossier;
    killCharts();
    renderSidebar(id);
    document.body.classList.remove('chat-mode');
    const actions = page.actions || '';
    document.getElementById('view').innerHTML =
      pageHead(page.title, page.sub, actions) + page.render();
    if (page.mount) page.mount();
    fillDocEmbeds();   // nhúng trình đọc/sửa text vào trang chi tiết (demo + thật)
    fillSkillRunSlots();   // nạp nội dung slot .ai-output[data-skill-run] (synthesis collapsible)
    injectPageNav(id);     // nút chuyển tab trước/sau cho chuỗi phân tích
    document.querySelector('.main').scrollTo(0,0);
    document.body.classList.remove('nav-open');
  }
  // Nạp nội dung skill_run vào slot .ai-output[data-skill-run] (vd synthesis collapsible)
  async function fillSkillRunSlots() {
    const slots = document.querySelectorAll('.ai-output[data-skill-run]');
    for (const slot of slots) {
      const id = slot.dataset.skillRun;
      if (!id || slot.dataset.loaded) continue;
      try {
        const r = await API.get('api/biz/skillrun/' + id);
        slot.innerHTML = renderAIContent(r.content || '(trống)');
        enhancePosMaps(slot);
        slot.dataset.loaded = '1';
      } catch (e) { slot.innerHTML = '<p class="muted">Không tải được nội dung — thử lại sau.</p>'; }
    }
  }
  // Nút chuyển tab trước/sau cho chuỗi phân tích T1→T5 (đọc theo trình tự)
  const PAGE_SEQ = [
    ['market', 'Nghiên cứu thị trường'], ['competitor', 'Phân tích đối thủ'],
    ['customer', 'Customer Insight'], ['pricing', 'Định giá & Tâm lý'],
    ['swot', 'SWOT'], ['strategy', 'Chiến lược tổng hợp'], ['tactical', 'Tactical Playbook'],
  ];
  function injectPageNav(id) {
    const i = PAGE_SEQ.findIndex(p => p[0] === id);
    if (i < 0) return;
    const prev = i > 0 ? PAGE_SEQ[i - 1] : null;
    const next = i < PAGE_SEQ.length - 1 ? PAGE_SEQ[i + 1] : null;
    const bar = document.createElement('div');
    bar.className = 'page-nav';
    bar.innerHTML =
      (prev ? `<a class="ghost-line" href="#${prev[0]}">← ${prev[1]}</a>` : '<span></span>') +
      `<span class="page-nav-pos">${i + 1}/${PAGE_SEQ.length}</span>` +
      (next ? `<a class="ghost-line" href="#${next[0]}">${next[1]} →</a>` : '<span></span>');
    document.getElementById('view').appendChild(bar);
  }
  /* ════════════ backend API + actions ════════════ */
  let apiAvailable = false;
  const API = {
    async get(p)        { const r = await fetch(p); if (!r.ok) throw 0; return r.json(); },
    async post(p, body) { const r = await fetch(p, { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body||{}) }); if (!r.ok) throw 0; return r.json(); },
    async del(p)        { const r = await fetch(p, { method:'DELETE' }); if (!r.ok) throw 0; return r.json(); },
  };

  function toast(msg) {
    const t = document.createElement('div');
    t.className = 'toast'; t.textContent = msg;
    document.body.appendChild(t);
    requestAnimationFrame(() => t.classList.add('show'));
    setTimeout(() => { t.classList.remove('show'); setTimeout(() => t.remove(), 300); }, 2600);
  }

  /* ── dữ liệu nghiệp vụ thật + AI agent ── */
  let _bizUserId = null;
  function bizQuery() { return _bizUserId != null ? ('?user_id=' + _bizUserId) : ''; }
  async function refreshBiz() {
    if (!apiAvailable) return;
    try {
      const biz = await API.get('api/biz' + bizQuery());
      Object.assign(window.MOCK, biz);
      if (biz.bizUserId != null) _bizUserId = biz.bizUserId;
    } catch (e) { /* chưa nối Supabase → bỏ qua */ }
  }
  async function refreshAds() {
    if (!apiAvailable) return;
    try {
      const ads = await API.get('api/biz/ads?days=' + _adsDays + bizQuery().replace('?','&'));
      Object.assign(window.MOCK, ads);
    } catch (e) { /* chưa có dữ liệu Ads → bỏ qua */ }
  }
  const SKILL_TO_TASK = { market_research:'market', competitor:'competitor', customer_insight:'customer',
    psychology_pricing:'pricing', swot:'swot', synthesis:'strategy', tactical_playbook:'strategy' };
  let _modalRun = null;
  function showModal(title, content, meta) {
    _modalRun = meta ? { ...meta, title, content } : null;
    let ov = document.getElementById('bizModal');
    if (!ov) {
      ov = document.createElement('div');
      ov.id = 'bizModal'; ov.className = 'modal-ov';
      ov.innerHTML = `<div class="modal"><div class="modal-head"><h3></h3>
        <button class="icon-btn" id="bizModalX">✕</button></div>
        <div class="modal-body ai-output expanded"></div><div class="modal-foot"></div></div>`;
      document.body.appendChild(ov);
      ov.addEventListener('click', (e) => { if (e.target === ov) ov.classList.remove('show'); });
      ov.querySelector('#bizModalX').addEventListener('click', () => ov.classList.remove('show'));
    }
    ov.querySelector('h3').textContent = title;
    ov.querySelector('.modal-body').innerHTML = renderAIContent(content || '(trống)');
    enhancePosMaps(ov.querySelector('.modal-body'));   // D-034 #4: ASCII map → visual
    const foot = ov.querySelector('.modal-foot');
    if (meta && meta.id) {
      foot.style.display = 'flex';
      foot.innerHTML = `
        <div class="rate-group">
          <span class="muted">Chất lượng:</span>
          <button class="rate-btn ${meta.rating>=4?'on up':''}" data-act="rate-skillrun" data-rating="5" title="Tốt">👍</button>
          <button class="rate-btn ${(meta.rating&&meta.rating<=2)?'on down':''}" data-act="rate-skillrun" data-rating="1" title="Chưa đạt">👎</button>
          ${meta.rating?`<span class="muted">đã chấm</span>`:''}
        </div>
        <div class="modal-foot-r">
          <button class="ghost-line sm" data-act="copy-skillrun">📋 Copy</button>
          ${meta.task?`<button class="primary-btn sm" data-act="regen-skillrun" data-task="${meta.task}">🔄 Tạo lại bản mới</button>`:''}
        </div>`;
    } else { foot.style.display = 'none'; foot.innerHTML = ''; }
    ov.classList.add('show');
  }

  /* ── Max chat ── */
  function chatBubble(m) {
    const who = m.role === 'user' ? 'me' : 'max';
    const avatar = m.role === 'user' ? '🧑' : '🤖';
    return `<div class="cmsg ${who}"><span class="cav">${avatar}</span>
      <div class="cbub">${renderAIContent(m.content)}</div></div>`;
  }
  function heroHTML(disabled) {
    const cards = CHAT_EXAMPLES.map(e =>
      `<button class="eg-card" ${disabled?'disabled':''} data-act="chat-eg" data-text="${e.text.replace(/"/g,'&quot;')}">
        <span class="eg-ic">${e.icon}</span><span>${e.text}</span></button>`).join('');
    const note = disabled
      ? `<p class="hero-note">⚠️ Max cần backend thật (Supabase + API key LLM) để trò chuyện. Trên bản demo tĩnh, Max tạm nghỉ — các trang khác vẫn xem được bằng dữ liệu mẫu.</p>`
      : '';
    return `<div class="hero">
      <div class="hero-logo">🤖</div>
      <h1 class="hero-title">Xin chào! Tôi là Max</h1>
      <p class="hero-sub">CMO ảo của bạn. Kể tôi nghe về doanh nghiệp — tôi sẽ chẩn đoán thị trường,
        đối thủ, khách hàng rồi vạch chiến lược và nội dung.</p>
      <div class="eg-grid">${cards}</div>
      ${note}
    </div>`;
  }
  function renderChat(disabled) {
    const stream = document.getElementById('chatStream');
    if (!stream) return;
    if (!_chatMsgs.length) {
      stream.classList.add('is-empty');
      stream.innerHTML = heroHTML(disabled);
    } else {
      stream.classList.remove('is-empty');
      stream.innerHTML = `<div class="cthread">` + _chatMsgs.map(chatBubble).join('') +
        (_chatBusy ? `<div class="cmsg max"><span class="cav">🤖</span><div class="cbub typing"><i></i><i></i><i></i></div></div>` : '') +
        `</div>`;
      stream.scrollTop = stream.scrollHeight;
    }
    const sug = document.getElementById('chatSuggest');
    if (sug) sug.innerHTML = _chatMsgs.length ? _chatSuggest.map(s => s.task
      ? `<button class="chip-btn" data-act="chat-suggest" data-task="${s.task}">${s.label}</button>`
      : `<button class="chip-btn" data-act="chat-suggest" data-goto="${s.goto}">${s.label}</button>`).join('') : '';
  }
  function growBox(box) {
    if (!box) return;
    box.style.height = 'auto';
    box.style.height = Math.min(box.scrollHeight, 180) + 'px';
  }
  async function initChat() {
    const disabled = !apiAvailable || M.bizEnabled === false;
    if (disabled) { _chatMsgs = []; _chatSuggest = []; renderChat(true); return; }
    try {
      const r = await API.get('api/chat/history' + bizQuery());
      _chatMsgs = r.history || [];
    } catch (e) { _chatMsgs = []; }
    renderChat();
    const box = document.getElementById('chatBox');
    if (box) {
      box.focus();
      box.oninput = () => growBox(box);
      box.onkeydown = (e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendChat(); } };
    }
  }
  async function sendChat(preset) {
    const box = document.getElementById('chatBox');
    const text = (preset || (box ? box.value.trim() : '')).trim();
    if (!text || _chatBusy) return;
    if (box) { box.value = ''; growBox(box); }
    _chatMsgs.push({ role: 'user', content: text });
    _chatBusy = true; renderChat();
    try {
      const r = await API.post('api/chat', { message: text, user_id: _bizUserId });
      _chatBusy = false;
      if (r.error) { _chatMsgs.push({ role: 'assistant', content: '⚠️ ' + r.error }); }
      else {
        _chatMsgs = r.history || _chatMsgs.concat({ role: 'assistant', content: r.reply });
        _chatStage = r.stage || _chatStage;
        _chatSuggest = r.suggestions || [];
        if (r.profileComplete) refreshBiz();   // hồ sơ vừa đủ → nạp dữ liệu thật
      }
    } catch (e) { _chatBusy = false; _chatMsgs.push({ role: 'assistant', content: '⚠️ Lỗi kết nối tới Max.' }); }
    const mini = document.querySelector('.jmini');
    if (mini) mini.outerHTML = journeyMini(_chatStage);
    renderChat();
    const box2 = document.getElementById('chatBox'); if (box2) box2.focus();
  }

  async function handleAction(el) {
    const act = el.dataset.act;
    if (act === 'chat-send') { sendChat(); return; }
    if (act === 'chat-eg') { sendChat(el.dataset.text); return; }
    if (act === 'toggle-collapse') {
      const card = el.closest('.card'); const out = card && card.querySelector('.ai-output');
      if (out) { const open = out.classList.toggle('expanded'); el.textContent = open ? 'Thu gọn ▴' : 'Xem đầy đủ ▾'; }
      return;
    }
    if (act === 'cal-view') { _calView = el.dataset.view; route(); return; }
    if (act === 'cal-open-week') { _calWeek = parseInt(el.dataset.week) || 1; _calView = 'week'; route(); return; }
    if (act === 'cal-gen') {
      // Prototype: sinh bài THEO TUẦN/SLOT (nhẹ, đúng ngữ cảnh) — M1 nối skill thật
      const w = el.dataset.week, track = el.dataset.track, day = el.dataset.day;
      const what = day != null ? `ngày ${+day + 1} tuần ${w}` : (track === 'camp' ? `bài campaign tuần ${w}` : `bài Always-on tuần ${w}`);
      if (!apiAvailable || !M.bizEnabled) { toast(`(Mẫu) Sẽ sinh ${what} bằng AI ở M1`); return; }
      try {
        await API.post('api/biz/agent', { task: 'full', user_id: _bizUserId }); // tạm map; M1 có task 'content' theo tuần
        toast(`Đang sinh ${what}…`);
      } catch (e) { toast('Không khởi chạy được'); }
      return;
    }
    if (act === 'add-campaign-occasion') {
      // Prototype client-side: tạo campaign theo dịp (window theo TUẦN). M1 nối backend.
      const P0 = M.calendarPlan; if (!P0) return;
      const name = prompt('Tên campaign (vd: Sale Tết):'); if (!name) return;
      const occasion = prompt('Dịp / mùa vụ (vd: Tết Nguyên Đán):', 'Dịp đặc biệt') || '';
      const offer = prompt('Offer (vd: Giảm 30%):', 'Ưu đãi đặc biệt') || '';
      const fromWeek = Math.max(1, Math.min(P0.weeks, parseInt(prompt(`Bắt đầu từ tuần nào? (1–${P0.weeks}):`, '1')) || 1));
      const toWeek = Math.max(fromWeek, Math.min(P0.weeks, parseInt(prompt(`Kết thúc tuần nào? (1–${P0.weeks}):`, String(fromWeek))) || fromWeek));
      const colors = ['#f59e0b', '#ef4444', '#ec4899', '#8b5cf6'];
      const color = colors[(P0.campaigns || []).length % colors.length];
      // sinh sẵn 2 bài/đợt làm mẫu (đầu & cuối window)
      const posts = [
        { week: fromWeek, day: 2, title: `Khởi động ${name} — ${offer}` },
        { week: toWeek, day: 4, title: `Ngày cuối ${name}` },
      ];
      (P0.campaigns = P0.campaigns || []).push({ name, occasion, offer, color, fromWeek, toWeek, posts });
      route(); toast('Đã thêm campaign theo dịp (mẫu) — Always-on vẫn chạy song song');
      return;
    }
    if (act === 'chat-suggest') {
      if (el.dataset.goto) { location.hash = el.dataset.goto; return; }
      if (el.dataset.task) {
        try {
          const r = await API.post('api/biz/agent', { task: el.dataset.task, user_id: _bizUserId });
          if (r.error) { toast(r.error); return; }
          _chatMsgs.push({ role: 'assistant', content: `Em bắt đầu chạy phân tích **${el.dataset.task}** rồi — Sếp xem tiến trình ở mục Dữ liệu thật & Agent, xong em báo nhé.` });
          renderChat(); toast('Max đang chạy phân tích…'); refreshBiz();
        } catch (e) { toast('Không khởi chạy được'); }
      }
      return;
    }
    // ── Điều hướng / đọc (chạy được cả trên demo tĩnh, không cần backend) ──
    if (act === 'ai-intake-send') { aiIntakeSend(); return; }
    if (act === 'intake-next') { handleIntake('next'); return; }
    if (act === 'intake-back') { handleIntake('back'); return; }
    if (act === 'intake-skip') { handleIntake('skip'); return; }
    if (act === 'intake-choice') { handleIntake('choice', el.dataset.val); return; }
    if (act === 'intake-suggest') { handleIntake('suggest', el.dataset.val); return; }
    if (act === 'edit-profile') { _editProfile = true; route(); return; }
    if (act === 'cancel-profile') { _editProfile = false; route(); return; }
    if (act === 'view-skillrun') { location.hash = '#doc/' + el.dataset.id; return; }
    if (act === 'doc-open') { _docId = el.dataset.id; _docEdit = false; loadDoc(); return; }
    if (act === 'doc-edit') { _docEdit = true; renderDoc(); return; }
    if (act === 'doc-edit-cancel') { _docEdit = false; renderDoc(); return; }
    if (act === 'copy-skillrun') {
      if (_docRun && navigator.clipboard) navigator.clipboard.writeText(_docRun.content || '').then(() => toast('Đã copy nội dung'));
      return;
    }
    if (!apiAvailable) { toast('Tính năng này cần backend — chạy: python run_web.py'); if (el.type === 'checkbox') el.checked = !el.checked; return; }

    if (act === 'save-profile') {
      const fields = {};
      PROFILE_FIELDS.forEach(([k]) => { const el = document.getElementById('pf_' + k); if (el) fields[k] = el.value.trim(); });
      if (!fields.product_service && !fields.industry) { toast('Nhập tối thiểu Ngành hoặc Sản phẩm'); return; }
      try {
        const r = await API.post('api/biz/profile', { fields, user_id: _bizUserId });
        if (r.error) { toast(r.error); return; }
        _editProfile = false; toast('Đã lưu hồ sơ — giờ chạy chẩn đoán được rồi');
        await refreshBiz(); renderRail(); renderTopbar(); route();
      } catch (e) { toast('Lưu hồ sơ thất bại'); }
      return;
    }

    // ── AI agent + dữ liệu thật (không theo luồng state web_*) ──
    if (act === 'run-agent') {
      try {
        const r = await API.post('api/biz/agent', { task: el.dataset.task, user_id: _bizUserId });
        if (r.error) { toast(r.error); return; }
        toast('Đã khởi chạy AI agent — theo dõi tiến trình realtime');
        await refreshBiz(); renderRail(); renderTopbar(); route();
      } catch (e) { toast('Không khởi chạy được agent'); }
      return;
    }
    if (act === 'rate-skillrun') {
      if (!_docRun) return;
      const rating = +el.dataset.rating;
      try {
        const r = await API.post('api/biz/skillrun/' + _docRun.id + '/rate', { rating });
        if (r.error) { toast(r.error); return; }
        _docRun.rating = rating;
        renderDoc();
        toast(rating >= 4 ? 'Cảm ơn! 👍 Max ghi nhận' : 'Đã ghi nhận 👎 — Max sẽ cải thiện');
        refreshBiz();
      } catch (e) { toast('Không lưu được đánh giá'); }
      return;
    }
    if (act === 'doc-edit-save') {
      const box = document.getElementById('docEditBox');
      if (!box || !_docRun) return;
      try {
        const r = await API.post('api/biz/skillrun/save',
          { user_id: _bizUserId, skill_name: _docRun.skill_name, content: box.value });
        if (r.error) { toast(r.error); return; }
        _docEdit = false; toast('Đã lưu version mới'); refreshBiz();
        if (r.id) { _docId = r.id; loadDoc(); }   // tải lại tại chỗ (version mới)
      } catch (e) { toast('Lưu thất bại'); }
      return;
    }
    if (act === 'doc-set-current') {
      // copy nội dung bản cũ → tạo version mới trên đầu
      try {
        const old = await API.get('api/biz/skillrun/' + el.dataset.contentId);
        if (!old.id) { toast('Không tải được bản cũ'); return; }
        const r = await API.post('api/biz/skillrun/save',
          { user_id: _bizUserId, skill_name: old.skill_name, content: old.content });
        if (r.error) { toast(r.error); return; }
        toast('Đã đặt làm hiện hành (version mới)'); refreshBiz();
        if (r.id) { _docId = r.id; loadDoc(); }
      } catch (e) { toast('Thất bại'); }
      return;
    }
    if (act === 'doc-patch') {
      const box = document.getElementById('docPatchBox');
      const comment = box ? box.value.trim() : '';
      if (!comment || !_docRun || _docPatching) return;
      _docPatching = true; renderDoc();
      try {
        const r = await API.post('api/biz/skillrun/' + _docRun.id + '/patch', { comment });
        _docPatching = false;
        if (r.error) { toast(r.error); renderDoc(); return; }
        if (r.status === 'ask') { _docAsk = r.question || 'Hãy mô tả rõ hơn đoạn cần sửa.'; renderDoc(); return; }
        if (r.status === 'noop') { _docAsk = 'Không tìm thấy đoạn khớp — thử nêu rõ tên phần/đoạn cần sửa.'; renderDoc(); return; }
        _docAsk = ''; toast('Đã sửa: ' + (r.summary || 'xong')); refreshBiz();
        if (r.run && r.run.id) { _docId = r.run.id; loadDoc(); }   // tải lại tại chỗ (version mới)
      } catch (e) { _docPatching = false; renderDoc(); toast('Không sửa được'); }
      return;
    }
    if (act === 'regen-skillrun') {
      try {
        const r = await API.post('api/biz/agent', { task: el.dataset.task, user_id: _bizUserId });
        if (r.error) { toast(r.error); return; }
        toast('Đang tạo lại bản mới — xong sẽ có version mới'); refreshBiz();
        location.hash = '#dossier';
      } catch (e) { toast('Không khởi chạy được'); }
      return;
    }
    if (act === 'switch-user') {
      const users = M.bizUsers || [];
      if (!users.length) { toast('Chưa có user nào'); return; }
      const list = users.map((u, i) => `${i + 1}. ${u.name || u.user_id} (${u.user_id})`).join('\n');
      const pick = prompt('Chọn user để xem (nhập số thứ tự):\n' + list);
      if (pick === null) return;
      const idx = parseInt(pick) - 1;
      if (users[idx]) { _bizUserId = users[idx].user_id; await refreshBiz(); await refreshAds(); renderRail(); renderTopbar(); route(); toast('Đã chuyển user'); }
      return;
    }
    if (act === 'ads-days') {
      _adsDays = parseInt(el.dataset.days) || 7;
      await refreshAds(); route();
      return;
    }
    if (act === 'fb-connect') {
      try {
        const r = await API.get('api/biz/fb/connect-url' + bizQuery());
        if (r.error) { toast(r.error); return; }
        window.open(r.url, '_blank');
        toast('Mở cửa sổ Facebook — đồng ý quyền rồi quay lại, bấm "7/30 ngày" để tải số liệu');
      } catch (e) { toast('Không tạo được link kết nối Facebook'); }
      return;
    }

    try {
      let res;
      if (act === 'add-tracked') {
        const name = prompt('Tên fanpage / đối thủ cần theo dõi:');
        if (!name || !name.trim()) return;
        res = await API.post('api/tracked', { name: name.trim() }); toast('Đã thêm đối thủ theo dõi');
      } else if (act === 'del-tracked') {
        res = await API.del('api/tracked/' + el.dataset.id); toast('Đã bỏ theo dõi');
      } else if (act === 'toggle-job') {
        res = await API.post('api/jobs/' + el.dataset.name + '/toggle'); toast('Đã cập nhật tác vụ');
      } else if (act === 'opt-apply') {
        res = await API.post('api/optimizations/' + el.dataset.id + '/apply'); toast('Đã áp dụng tối ưu');
      } else if (act === 'opt-dismiss') {
        res = await API.post('api/optimizations/' + el.dataset.id + '/apply'); toast('Đã bỏ qua đề xuất');
      } else if (act === 'dismiss-alert') {
        res = await API.post('api/alerts/' + el.dataset.id + '/dismiss');
      } else if (act === 'set-setting') {
        res = await API.post('api/settings', { key: el.dataset.key, value: el.checked ? 1 : 0 }); toast('Đã lưu cài đặt');
      } else if (act === 'add-campaign') {
        const name = prompt('Tên chiến dịch:'); if (!name || !name.trim()) return;
        res = await API.post('api/campaigns', { name: name.trim() }); toast('Đã tạo chiến dịch');
      } else if (act === 'del-campaign') {
        res = await API.del('api/campaigns/' + el.dataset.id); toast('Đã xoá chiến dịch');
      } else if (act === 'add-post') {
        const title = prompt('Tiêu đề bài đăng:'); if (!title || !title.trim()) return;
        res = await API.post('api/calendar', { day: +el.dataset.day, pillar: 'Educate', title: title.trim() }); toast('Đã thêm bài');
      } else if (act === 'del-calendar') {
        res = await API.del('api/calendar/' + el.dataset.id);
      } else if (act === 'gen-content') {
        const topic = prompt('Chủ đề nội dung:', 'Khuyến mãi mùa hè'); if (topic === null) return;
        res = await API.post('api/content/generate', { topic: topic.trim() || 'Khuyến mãi' }); toast('Đã tạo gói nội dung');
      } else if (act === 'add-report') {
        const name = prompt('Tên báo cáo:'); if (!name || !name.trim()) return;
        res = await API.post('api/reports', { name: name.trim(), type: 'Tuần' }); toast('Đã tạo báo cáo');
      } else if (act === 'del-report') {
        res = await API.del('api/reports/' + el.dataset.id);
      } else if (act === 'connect-account') {
        const name = prompt('Tên tài khoản quảng cáo:'); if (!name || !name.trim()) return;
        res = await API.post('api/accounts', { name: name.trim() }); toast('Đã kết nối tài khoản');
      } else if (act === 'toggle-account') {
        res = await API.post('api/accounts/' + el.dataset.id + '/toggle');
      } else if (act === 'disconnect-account') {
        res = await API.del('api/accounts/' + el.dataset.id); toast('Đã ngắt kết nối');
      } else if (act === 'add-quota') {
        const v = prompt('Cộng thêm quota (token):', '50000'); if (v === null) return;
        res = await API.post('api/users/' + el.dataset.id + '/addquota', { value: parseInt(v) || 0 }); toast('Đã cộng quota');
      } else if (act === 'reset-usage') {
        res = await API.post('api/users/' + el.dataset.id + '/reset'); toast('Đã reset usage');
      } else if (act === 'notify-test') {
        const r = await API.post('api/notify/test');
        toast(r.ok ? 'Đã gửi! Kiểm tra Telegram' : (r.enabled ? 'Gửi lỗi — kiểm tra token/chat_id' : 'Chưa cấu hình Telegram (token + chat_id)'));
        return;
      }
      if (res) { Object.assign(window.MOCK, res); renderRail(); renderTopbar(); route(); }
    } catch (e) { toast('Lỗi kết nối backend'); }
  }

  document.addEventListener('click', (e) => {
    const el = e.target.closest('[data-act]');
    if (el && el.tagName !== 'INPUT') { e.preventDefault(); handleAction(el); }
  });
  document.addEventListener('change', (e) => {
    const el = e.target.closest('input[data-act]');
    if (el) handleAction(el);
  });

  window.addEventListener('hashchange', route);
  document.getElementById('navToggle').addEventListener('click', () => document.body.classList.toggle('nav-open'));

  /* ════════════ realtime (SSE) ════════════ */
  let _lastStream = '';
  let _sseLive = false;
  function setLive(on) {
    _sseLive = on;
    const dot = document.getElementById('liveDot');
    if (dot) dot.classList.toggle('off', !on);
  }
  let _jobSig = '';
  function applyStream(data) {
    if (data === _lastStream) return;          // dedupe các bản trùng
    _lastStream = data;
    let state; try { state = JSON.parse(data); } catch (e) { return; }
    Object.assign(window.MOCK, state);
    // khi 1 job AI đổi trạng thái (running→done/error) → nạp lại dữ liệu thật
    const sig = JSON.stringify((state.agentJobs || []).map(j => [j.id, j.status, j.progress]));
    if (sig !== _jobSig) {
      _jobSig = sig;
      if ((state.agentJobs || []).some(j => j.status === 'done')) refreshBiz();
    }
    const editing = document.activeElement &&
      /^(INPUT|TEXTAREA|SELECT)$/.test(document.activeElement.tagName);
    renderRail(); renderTopbar();
    if (!editing) route();                     // không phá thao tác đang gõ
    const dot = document.getElementById('liveDot');
    if (dot) { dot.classList.add('pulse'); setTimeout(() => dot.classList.remove('pulse'), 1200); }
  }
  function startStream() {
    if (typeof EventSource === 'undefined') return;
    try {
      const es = new EventSource('api/stream');
      es.onopen = () => setLive(true);
      es.onerror = () => setLive(false);       // EventSource tự reconnect
      es.onmessage = (ev) => applyStream(ev.data);
    } catch (e) { /* bỏ qua */ }
  }

  /* ════════════ boot: nạp dữ liệu, mở SSE, fallback mock ════════════ */
  (async function boot() {
    try {
      const state = await API.get('api/bootstrap');
      Object.assign(window.MOCK, state);
      _lastStream = JSON.stringify(state);
      apiAvailable = true;
      await refreshBiz();                        // nạp dữ liệu nghiệp vụ thật (nếu có Supabase)
      await refreshAds();                        // nạp ads snapshots thật
    } catch (e) { /* không có backend → dùng dữ liệu mock nhúng sẵn */ }
    renderRail();
    renderTopbar();
    route();
    if (apiAvailable) startStream();
  })();
})();
