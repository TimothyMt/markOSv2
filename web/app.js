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
      .replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, '<a class="md-link" href="$2" target="_blank" rel="noopener">$1</a>')   // [tên](url) → hyperlink nguồn
      .replace(/(^|[\s(])(https?:\/\/[^\s)<]+)/g, '$1<a class="md-link" href="$2" target="_blank" rel="noopener">$2</a>')        // URL trần → tự link
      .replace(/\*\*(.+?)\*\*/g, '<b>$1</b>')
      .replace(/\*(.+?)\*/g, '<i>$1</i>')
      .replace(/(^|[\s(>])_([^_\n]+?)_(?=[\s).,;:!?]|$)/g, '$1<i>$2</i>');   // _nghiêng_ (không đụng snake_case)
    const isRow = l => /^\s*\|.*\|\s*$/.test(l);
    const isSep = l => /^\s*\|?[\s:|-]*-[\s:|-]*\|?\s*$/.test(l) && l.includes('-');
    const cells = l => l.trim().replace(/^\|/, '').replace(/\|$/, '').split('|').map(c => c.trim());
    // N-09: heading lồng trong bullet/số (vd "- #### Xu hướng") → nâng thành heading thật ở đầu dòng
    const hClean = s => inline((s || '').replace(/\s*[:：]\s*$/, ''));   // bỏ dấu ":" cuối heading
    const lines = raw.split('\n').map(l => l.replace(/^(\s*)(?:[-*]|\d+\.)\s+(#{2,6}\s+)/, '$1$2'));
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
      if ((m = line.match(/^#{4,6}\s+(.*)/))) { out.push(`<h5>${hClean(m[1])}</h5>`); i++; continue; }
      if ((m = line.match(/^###\s+(.*)/)))  { out.push(`<h4>${hClean(m[1])}</h4>`); i++; continue; }
      if ((m = line.match(/^##\s+(.*)/)))   { out.push(`<h3>${hClean(m[1])}</h3>`); i++; continue; }
      if ((m = line.match(/^#\s+(.*)/)))    { out.push(`<h2>${hClean(m[1])}</h2>`); i++; continue; }
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
             && !/^#{1,6}\s/.test(lines[i]) && !/^\s*[-*]\s/.test(lines[i])
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
    // Magic Quadrant: đối thủ = chấm có tên rải trong mặt phẳng 2 trục; mình = ★ sáng
    function buildEl(map) {
      const short = (s, n) => { s = (s || '').replace(/—.*$/, '').trim(); return s.length > n ? s.slice(0, n - 1) + '…' : s; };
      const isOpp = qn => map.items[qn].some(it => /SếP|sếp|★/.test(it)) || /TRỐNG/i.test(map.qdesc[qn] || '');
      const w = mk('div', 'mq');
      w.appendChild(mk('div', 'mq-title', '📍 Bản đồ Định vị Cạnh tranh'));
      const plot = mk('div', 'mq-plot');
      // nhãn góc mờ ở 4 corner
      const CMAP = { 1: 'mq-c1', 2: 'mq-c2', 3: 'mq-c3', 4: 'mq-c4' };
      [1, 2, 3, 4].forEach(qn => {
        const c = mk('div', 'mq-corner ' + CMAP[qn] + (isOpp(qn) ? ' opp' : ''));
        const h = mk('div', 'mq-corner-h');
        h.appendChild(mk('span', 'mq-corner-q', 'GÓC ' + roman(qn)));
        if (isOpp(qn)) h.appendChild(mk('span', 'mq-badge', '🎯 Cơ hội'));
        c.appendChild(h);
        if (map.qdesc[qn]) c.appendChild(mk('span', 'mq-corner-d', short(map.qdesc[qn], 30)));
        plot.appendChild(c);
      });
      // chấm đối thủ — rải trong vùng góc của nó
      const QP = { 1: [60, 84, 16, 40], 2: [16, 40, 16, 40], 3: [16, 40, 60, 84], 4: [60, 84, 60, 84] };
      [1, 2, 3, 4].forEach(qn => {
        const its = map.items[qn], n = its.length;
        its.forEach((it, i) => {
          const [x0, x1, y0, y1] = QP[qn];
          const t = n === 1 ? 0.5 : i / (n - 1);
          const x = x0 + (x1 - x0) * t;
          const y = (y0 + y1) / 2 + (n > 1 ? (i % 2 ? 11 : -11) : 0);
          const self = /SếP|sếp|★/.test(it);
          const d = mk('div', 'mq-dot' + (self ? ' self' : '') + (x >= 50 ? ' rt' : ''));
          d.style.left = x + '%'; d.style.top = Math.max(10, Math.min(90, y)) + '%';
          d.appendChild(mk('span', 'mq-pt', self ? '★' : ''));
          d.appendChild(mk('span', 'mq-name', self ? 'Bạn ở đây' : it));
          plot.appendChild(d);
        });
      });
      // Trục Y dọc bên TRÁI + trục X dưới đáy (chuẩn Magic Quadrant — hết chồng hàng)
      const endWord = s => { const m = (s || '').match(/(cao|thấp|high|low)\s*$/i); return (m ? m[1] : ((s || '').split(/\s+/).pop() || '')).toUpperCase(); };
      const yDim = (map.yTop || map.yBottom || '').replace(/\s*(cao|thấp|high|low)\s*$/i, '').trim();
      const body = mk('div', 'mq-body');
      const ya = mk('div', 'mq-yaxis');
      if (map.yTop) ya.appendChild(mk('span', 'mq-ya-end', '▲ ' + endWord(map.yTop)));
      if (yDim) ya.appendChild(mk('span', 'mq-ya-dim', yDim));
      if (map.yBottom) ya.appendChild(mk('span', 'mq-ya-end', endWord(map.yBottom) + ' ▼'));
      body.appendChild(ya);
      body.appendChild(plot);
      w.appendChild(body);
      const xa = mk('div', 'mq-x');
      xa.appendChild(mk('span', '', map.xLeft ? '← ' + map.xLeft : ''));
      xa.appendChild(mk('span', '', map.xRight ? map.xRight + ' →' : ''));
      w.appendChild(xa);
      return w;
    }
    // D-034 #5: ưu tiên block JSON máy-đọc (chính xác); fallback parse ASCII
    function fromJson(j) {
      const items = { 1: [], 2: [], 3: [], 4: [] };
      (j.items || []).forEach(it => {
        const q = Math.max(1, Math.min(4, +it.q || 1));
        items[q].push(it.self ? '★ ' + (it.name || 'SẾP') : (it.name || ''));
      });
      return { yTop: j.yTop || '', yBottom: j.yBottom || '', xLeft: j.xLeft || '', xRight: j.xRight || '',
        qdesc: { 1: j.q1 || '', 2: j.q2 || '', 3: j.q3 || '', 4: j.q4 || '' }, items };
    }
    root.querySelectorAll('pre').forEach(pre => {
      const text = pre.textContent || '';
      let map = null;
      const ts = text.trim();
      if (ts.startsWith('{') && ts.indexOf('"items"') >= 0) {
        try { const j = JSON.parse(ts); if (Array.isArray(j.items) && j.items.length) map = fromJson(j); } catch (e) { /* fallback ASCII */ }
      }
      if (!map && isMap(text)) map = parseMap(text);
      if (!map) {
        // N-04: khối JSON pos-map (yTop/yBottom/xLeft/q1…) không render được → ẩn, đừng lòi JSON thô
        if (ts.startsWith('{') && /"(yTop|yBottom|xLeft|xRight|q[1-4])"\s*:/.test(ts)) pre.remove();
        return;
      }
      pre.parentNode.replaceChild(buildEl(map), pre);
    });
    // N-13: bọc bảng rộng vào .tbl-wrap để cuộn ngang thay vì cắt cạnh phải
    root.querySelectorAll('table').forEach(tb => {
      if (tb.closest('.tbl-wrap')) return;
      const w = document.createElement('div'); w.className = 'tbl-wrap';
      tb.parentNode.insertBefore(w, tb); w.appendChild(tb);
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
    { key: 'product_service', tier: 'core', q: 'Bạn bán sản phẩm/dịch vụ gì?', ph: 'vd: Cà phê specialty pha máy + hạt rang mộc' },
    { key: 'target_customer', tier: 'core', q: 'Khách hàng bạn ĐANG có là ai (độ tuổi · đặc điểm · khu vực)?',
      helper: 'Mô tả tệp hiện tại — tệp ưu tiên ĐÁNH TRƯỚC sẽ chốt ở bước Chiến lược (Đặt cược).', ph: 'vd: Dân văn phòng 25–34, Q.1 TP.HCM' },
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
      helper: 'Đây là CHẤT khác biệt (vì sao khách quay lại) — chưa cần gói thành câu slogan.',
      note: 'Nếu chưa biết thì ghi "chưa biết" — Max sẽ tự tìm/đề xuất định vị giúp bạn.' },
    { key: 'objection', tier: 'strategic', strategic: true,
      q: 'Rào cản / nỗi sợ lớn nhất khiến khách chần chừ là gì?',
      helper: 'Khách hay lo gì, hay hỏi gì, hay từ chối vì lý do nào trước khi mua?',
      ph: 'vd: "giá cao hơn cà phê thường", "sợ đặt online nguội"' },
    { key: 'competitors', tier: 'strategic', strategic: true, optional: true,
      q: 'Có đối thủ nào bạn đang để ý không? (tên cụ thể nếu có)',
      helper: 'Nêu tên giúp Max nghiên cứu đúng đối thủ đó — không có thì để trống.',
      ph: 'vd: Highlands, Phúc Long, The Coffee House' },

    // ── Khối bối cảnh (optional — gọn, chỉ cái cần để ra output) ──
    { key: 'current_channels', tier: 'context', optional: true, q: 'Kênh marketing bạn ĐANG dùng là gì?',
      helper: 'Mô tả kênh hiện tại — kênh muốn TRIỂN KHAI/đánh sẽ chốt ở bước Chiến lược (Đặt cược).', ph: 'vd: Facebook, TikTok, Zalo OA' },
    { key: 'team_size', tier: 'context', optional: true, q: 'Đội làm marketing/nội dung của bạn mấy người?',
      choices: ['Một mình founder', '2–3 người', '4–10 người', 'Trên 10 / có agency'],
      note: 'Giúp Max đề xuất khối lượng & kênh KHẢ THI với nguồn lực của bạn — không vẽ quá sức.' },
    // (Bỏ câu USP/định vị — định vị chốt ở bước Chiến lược "Đặt cược" trên dữ liệu THẬT, tránh hỏi trùng.)
  ];
  // Field nào có cột riêng trong profile; còn lại gói vào intake_extra.answers (D-032)
  const PROFILE_COLUMN_KEYS = new Set(['business_name', 'industry', 'location', 'product_service',
    'target_customer', 'main_challenge', 'competitors', 'monthly_revenue',
    'monthly_marketing_budget', 'current_channels', 'primary_goal', 'usp']);
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
      const busy = (M.agentJobs||[]).some(j => j.status==='running' && (j.task==='research' || j.task==='full'));
      return sel + `<button class="ghost-line" data-act="biz-reset" title="Xoá dữ liệu để test lại từ đầu">🧹 Reset</button>`
        + `<button class="primary-btn" data-act="run-agent" data-task="research" ${busy?'disabled':''}>${busy?'⏳ Đang chạy nghiên cứu…':'🔬 Chạy nghiên cứu (T1-T3)'}</button>`;
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
        ['synthesis','strategy','🎯','Chiến lược tổng hợp','Định vị (bền) + roadmap theo nhịp'],
      ];
      // 'research' bao T1-T3 (market/competitor/customer/swot); 'strategize' bao synthesis; 'full' bao tất.
      const RUN_COVERS = { research: ['market','competitor','customer','swot'], strategize: ['strategy'] };
      const isRunning = (t) => jobs.some(j => j.status === 'running' && (
        j.task === t || j.task === 'full' || (RUN_COVERS[j.task] || []).includes(t)));
      const diagBody = `<div class="diag-list">${ANALYSES.map(([k, task, ic, name, desc]) => {
        const run = runs.find(r => r.skill_name === k);
        const running = isRunning(task);
        const st = run ? 'done' : running ? 'running' : 'pending';
        const rate = (run && run.rating) ? (run.rating >= 4 ? ' 👍' : run.rating <= 2 ? ' 👎' : ' ★' + run.rating) : '';
        const act = running ? badge('Đang chạy', 'amber')
          : run ? `<a class="primary-btn sm" href="#${task}">Xem & sửa</a>
                   <button class="icon-btn" data-act="run-agent" data-task="${task}" title="Chạy lại bản mới">↻</button>`
          // D-041: synthesis pending → dẫn tới GATE (chọn wedge+USP) thay vì chạy thẳng
          : k === 'synthesis' ? `<a class="ghost-line sm" href="#strategy">🎯 Lập chiến lược</a>`
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
        // Enter=Tiếp/Gửi do 1 listener CAPTURE-phase ở document lo (ăn trước extension + chống mất khi re-render).
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
    if (cols.usp) cols.usp_confidence = 'clear';   // founder có USP → Max REFINE, không đẻ mới
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
          <h2 class="doc-title">${skillVi(r.skill_name) || 'Output'} <span class="tag">v${r.version || 1}</span></h2>
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
      ${_docAsk ? `<p class="doc-ask">🤖 Max cần rõ thêm: ${_docAsk}</p>` : ''}
      ${_CONTENT_SKILLS.has(r.skill_name) ? `<details class="doc-feedback">
        <summary>📊 Đo hiệu quả & tối ưu bài kế <span class="muted" style="font-weight:400">— bài đã đăng rồi thì nhập số liệu, Max chấm + gợi ý bài sau</span></summary>
        <div style="margin-top:8px">
          <input id="docMetricsBox" class="occ-inp" type="text" placeholder="vd: reach 12k, CTR 1.8%, 45 comment, 6 lưu, 8 đơn — nhập cái bạn có">
          <button class="primary-btn sm" data-act="content-feedback" data-id="${r.id}" style="margin-top:8px">📊 Max chấm & gợi ý bài kế</button>
        </div>
      </details>` : ''}`}
      <div class="doc-grid">${bodyOrEditor}${versions}</div>`;
    enhancePosMaps(el);   // D-034 #4: ASCII map → visual
  }
  // Lô I: skill nội dung đủ điều kiện "đo hiệu quả" (bài đăng được) → hiện panel phản hồi.
  const _CONTENT_SKILLS = new Set(['calendar_post', 'ads_copy', 'email_zalo_sequence', 'video_script',
    'ugc_brief', 'post_channels', 'sales_inbox_script', 'landing_copy']);

  /* ---- Market research ---- */
  P.market = {
    title: 'Nghiên cứu thị trường', sub: 'TAM / SAM / SOM + động lực thị trường',
    actions: `<a class="ghost-line" href="#dossier">← Hồ sơ</a>`,
    render: () => `
      <div id="marketKpis"></div>
      <section class="grid">
        ${agentSection('market','market_research')}
      </section>`,
    mount: () => { loadMarketKpis(); },
  };
  // D-034 #2: card TAM/SAM/SOM số THẬT (trích từ output market, thiếu→ẩn card)
  async function loadMarketKpis() {
    const run = (M.bizLatest || {}).market_research;
    const host = document.getElementById('marketKpis');
    if (!host || !run || !apiAvailable) return;
    try {
      const r = await API.get('api/biz/market-kpis?run_id=' + run.id);
      const k = (r && r.kpis) || {};
      const L = { tam: ['TAM', 'Thị trường tối đa'], sam: ['SAM', 'Có thể phục vụ'], som: ['SOM', 'Có thể đạt được'] };
      const cards = ['tam', 'sam', 'som'].filter(x => k[x]).map(x => {
        const d = k[x], val = d.value + (d.unit ? ' ' + d.unit : '');
        return miniStat(L[x][0], val, L[x][1] + (d.note ? ' (' + d.note + ')' : ''));
      }).join('');
      if (cards) host.innerHTML = `<section class="kpis kpis-3">${cards}</section>`;
    } catch (e) { /* thiếu → ẩn card */ }
  }

  /* ---- Competitor ---- */
  P.competitor = {
    title: 'Phân tích đối thủ', sub: '8 chiều cạnh tranh',
    actions: `<a class="ghost-line" href="#dossier">← Hồ sơ</a>`,
    // N-05: bỏ hẳn section "Đối thủ đang theo dõi (Ads Library)" — đó là DATA MOCK (web/data.js),
    // không liên quan business thật ở giai đoạn T1-T3. (Theo dõi Ads thật vẫn ở trang #tracked.)
    render: () => `
      <section class="grid">
        ${agentSection('competitor','competitor')}
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
        ${card('Roadmap định hướng', `
          <div class="roadmap">${M.roadmap.map(r=>`
            <div class="rm-phase"><span class="rm-tag">${r.phase}</span><p class="rm-title">${r.title}</p>
              <ul class="bullet">${r.items.map(i=>`<li>${i}</li>`).join('')}</ul></div>`).join('')}</div>`, {cls:'span-12'})}`;
  // Banner 2 tầng: Synthesis = la bàn (định hướng); số cụ thể chốt ở chiến dịch (B1)
  const directionalBanner = `
        <div class="card span-12 dir-banner">
          🧭 Đây là <b>ĐỊNH HƯỚNG</b> chiến lược (la bàn): <b>định vị (bền)</b> + <b>roadmap theo nhịp đã chọn</b>,
          trục nội dung, kênh, ưu tiên từng giai đoạn. Con số cụ thể — SMART, ngân sách đợt, deadline —
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
  // 🅑 (M4.1 wayfinding): thẻ "Bước tiếp theo" — biển chỉ đường cuối mỗi tài liệu
  // chiến lược. Cả Chiến lược (la bàn) lẫn Playbook (cách đánh) đều trỏ về CÙNG nút
  // Lập chiến dịch (#occasion) → 1 kế hoạch duy nhất, KHÔNG nhân bản kế hoạch.
  function nextStepCard({ done, lead, primary, alts }) {
    const pbtn = primary.act
      ? `<button class="primary-btn" data-act="${primary.act}">${primary.label}</button>`
      : `<a class="primary-btn" href="#${primary.href}">${primary.label}</a>`;
    return `<div class="card span-12 nextstep">
      <div class="ns-body">
        <p class="ns-done">✓ ${done}</p>
        <p class="ns-lead">${lead}</p>
      </div>
      <div class="ns-actions">
        ${pbtn}
        ${alts ? `<div class="ns-alts">${alts}</div>` : ''}
      </div>
    </div>`;
  }

  P.strategy = {
    title: 'Chiến lược tổng hợp', sub: 'Định vị (bền) · SAVE · Roadmap theo nhịp · KPI cần theo dõi',
    actions: `<a class="ghost-line" href="#tactical">🔨 Tactical Playbook</a> <a class="primary-btn" href="#message">→ Bước tiếp: 🏛️ Thông điệp</a>`,
    render: () => {
      const latest = (M.bizLatest || {}).synthesis;
      if (M.bizEnabled && latest) {
        // D-037a: 1 card duy nhất (bỏ agentBar trùng "Xem output") — output inline + nút rerun
        const running = (M.agentJobs || []).some(j => j.status === 'running' && (j.task === 'strategy' || j.task === 'full'));
        // M4(1): chốt chiến lược — so version đã duyệt với bản mới nhất (tạo lại → version đổi → bỏ chốt)
        const approved = (((M.bizProfile || {}).intake_extra || {}).synthesis_approved_version) === latest.version;
        return `<section class="grid">
          ${directionalBanner}
          ${inferredMeter()}
          ${card('Chiến lược — do Max lập', `
            <div class="ai-output collapsible" data-skill-run="${latest.id}">Đang tải chiến lược…</div>
            <button class="ghost-line full collapse-toggle" data-act="toggle-collapse" style="margin-top:12px">Xem đầy đủ ▾</button>`,
            {cls:'span-12', action:`<span class="muted">v${latest.version} · ${(latest.created_at||'').slice(0,10)}</span> ${approved?badge('✓ Đã chốt','green'):''} ${runBtn('strategy', running ? '↻ Đang chạy' : '↻ Tạo lại bản mới', 'ghost-line sm')}`})}
          ${approved ? nextStepCard({
            done: 'Đã chốt Chiến lược — sẵn sàng triển khai.',
            lead: 'Bước tiếp: biến la bàn thành <b>kế hoạch chạy thật</b> (lịch bài, đợt theo dịp, quảng cáo).',
            primary: { href: 'occasion', label: '→ Lập chiến dịch' },
            alts: `<a class="ghost-line sm" href="#tactical">🔨 Chi tiết hoá bằng Tactical Playbook</a>
                   ${runBtn('strategy', running ? '↻ Đang chạy' : '↻ Tạo lại bản mới', 'ghost-line sm')}`,
          }) : nextStepCard({
            done: 'Max đã lập xong Chiến lược.',
            lead: 'Xem kỹ rồi <b>chốt</b> để mở bước Lập chiến dịch. <span class="muted">(Tạo lại bản mới sẽ phải chốt lại.)</span>',
            primary: { act: 'approve-synthesis', label: '✅ Chốt chiến lược này' },
            alts: `<a class="ghost-line sm" href="#tactical">🔨 Xem Tactical Playbook</a>
                   ${runBtn('strategy', running ? '↻ Đang chạy' : '↻ Tạo lại bản mới', 'ghost-line sm')}`,
          })}
        </section>`;
      }
      if (M.bizEnabled) {
        // D-041: research xong (T1-T3) → hiện GATE (chọn wedge + USP) trước khi lập chiến lược
        const researchDone = ['market_research', 'competitor', 'customer_insight', 'swot']
          .every(k => (M.bizSkillRuns || []).some(r => r.skill_name === k));
        if (researchDone) {
          const running = (M.agentJobs || []).some(j => j.status === 'running' && (j.task === 'strategize' || j.task === 'full'));
          return `<section class="grid">
            <div class="card span-12 dir-banner">🚪 <b>Nghiên cứu xong (T1-T3).</b> Chốt <b>ĐẶT CƯỢC</b> (thị trường · tệp · định vị · giá · kênh) trên dữ liệu THẬT → Max chạy chiến lược (T4-T5) bám đúng lựa chọn → chia <b>tuyến nội dung</b> → lịch. <span class="muted">(Tin cậy/bằng chứng nằm ở tuyến nội dung, không ở đây.)</span></div>
            ${betForm()}
            ${card('⚙️ Tinh chỉnh nâng cao (tuỳ chọn)', `
              <details><summary style="cursor:pointer;color:var(--muted)">Nhịp roadmap + trọng tâm giai đoạn — để Tự động nếu chưa chắc</summary>
                <div class="fld" style="margin-top:10px"><span>Nhịp roadmap</span><div class="gate-usp">
                  <label class="radio-row"><input type="radio" name="gateHorizon" value="auto" checked> <b>Tự động</b></label>
                  <label class="radio-row"><input type="radio" name="gateHorizon" value="30"> 30 ngày</label>
                  <label class="radio-row"><input type="radio" name="gateHorizon" value="60"> 60 ngày</label>
                  <label class="radio-row"><input type="radio" name="gateHorizon" value="90"> 90 ngày</label></div></div>
                <div class="fld"><span>Trọng tâm giai đoạn</span><div class="gate-usp">
                  <label class="radio-row"><input type="radio" name="gatePosture" value="auto" checked> <b>Tự động</b></label>
                  <label class="radio-row"><input type="radio" name="gatePosture" value="brand"> Xây nhận biết</label>
                  <label class="radio-row"><input type="radio" name="gatePosture" value="balanced"> Cân bằng</label>
                  <label class="radio-row"><input type="radio" name="gatePosture" value="activation"> Ra đơn ngay</label></div></div>
              </details>`, { cls: 'span-12' })}
            <div class="card span-12" style="text-align:center">
              <button class="primary-btn" data-act="run-strategize-bet" ${running ? 'disabled' : ''}>${running ? '⏳ Đang lập chiến lược…' : '🎯 Lập chiến lược (T4-T5) theo đặt cược'}</button></div>
          </section>`;
        }
        return `<section class="grid">
          ${card('', `<div class="empty-cta">
            <div class="empty-ic">🔬</div>
            <h3>Chưa có nghiên cứu cho doanh nghiệp này</h3>
            <p class="muted">Quy trình 2 bước: <b>① Chạy nghiên cứu</b> (thị trường, đối thủ, khách, SWOT) → <b>② chọn hướng đánh</b> → Max lập chiến lược + playbook.</p>
            <div class="empty-actions">
              <a class="primary-btn" href="#dossier">📋 Điền Hồ sơ doanh nghiệp</a>
              <button class="ghost-line" data-act="run-agent" data-task="research">🔬 Chạy nghiên cứu ngay</button>
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
    actions: `<a class="ghost-line" href="#strategy">← Về Chiến lược</a> <a class="primary-btn" href="#message">→ Bước tiếp: 🏛️ Thông điệp</a>`,
    render: () => {
      const has = (M.bizSkillRuns || []).some(r => r.skill_name === 'tactical_playbook');
      if (M.bizEnabled && !has) {
        return `<section class="grid">
          ${card('', `<div class="empty-cta">
            <div class="empty-ic">🔨</div>
            <h3>Chưa có Tactical Playbook</h3>
            <p class="muted">Đây là <b>bản đồ chi tiết</b> đi sau Chiến lược (la bàn): với từng phân khúc ưu tiên,
            Max viết cách đánh theo phễu (TOFU/MOFU/BOFU) — copy mẫu, kênh, khung thử nghiệm, KPI cần theo dõi.
            Nó được tạo cùng lượt "Lập chiến lược" (sau khi chọn hướng đánh).</p>
            <div class="empty-actions">
              <a class="primary-btn" href="#strategy">🎯 Tới bước Lập chiến lược</a>
            </div></div>`, {cls:'span-12'})}
        </section>`;
      }
      return `<section class="grid">
        <div class="card span-12 dir-banner">🔨 Đây là <b>cách đánh chi tiết</b> (bản đồ) — đi sau <b>Chiến lược định hướng</b> (la bàn).
          Mỗi phân khúc có copy mẫu, kênh, khung thử nghiệm, KPI. Con số/ngân sách thật chốt khi lập chiến dịch theo dịp.</div>
        ${M.bizPlaybookStale ? `<div class="card span-12 pb-stale">⚠️ <b>Playbook đang bám chiến lược CŨ</b> — Chiến lược đã đổi sau lần lập Playbook gần nhất.
          <button class="primary-btn sm" data-act="run-agent" data-task="regen_playbook">🔄 Cập nhật Playbook theo chiến lược mới</button></div>` : ''}
        ${agentSection('full','tactical_playbook')}
        ${nextStepCard({
          done: 'Đã có Tactical Playbook — cách đánh chi tiết theo từng tệp.',
          lead: 'Bước tiếp: lên <b>kế hoạch chạy</b>. Playbook và Chiến lược cùng đổ về <b>một</b> nơi → <b>một</b> kế hoạch (không tách lẻ).',
          primary: { href: 'occasion', label: '→ Lập chiến dịch' },
          alts: `<a class="ghost-line sm" href="#strategy">← Xem lại Chiến lược định hướng</a>`,
        })}
      </section>`;
    },
    mount: () => {},
  };

  /* ---- Cầu nối: Lập chiến dịch theo dịp (M1 — đang phát triển) ---- */
  // D-040: hub 2-tuyến — Always-on (nền) + Occasion (theo dịp). Industry-aware.
  P.occasion = {
    title: 'Lập chiến dịch', sub: 'Set 🟢 nền thương hiệu (móng) + tạo 🔴 các đợt (spike) — xem theo thời gian ở Lịch',
    actions: `<a class="ghost-line" href="#strategy">← Về Chiến lược</a> <a class="primary-btn" href="#calendar">📅 Xem kế hoạch trên Lịch</a>`,
    render: () => {
      if (M.bizEnabled && !(M.bizLatest || {}).synthesis) {
        return `<section class="grid">${card('', `<div class="empty-cta">
          <div class="empty-ic">🗓️</div><h3>Cần có Chiến lược trước</h3>
          <p class="muted">2 tuyến chiến dịch kế thừa từ Chiến lược (la bàn) + Tactical Playbook. Hãy lập chiến lược trước.</p>
          <div class="empty-actions"><a class="primary-btn" href="#strategy">🎯 Tới bước Lập chiến lược</a></div></div>`, {cls:'span-12'})}</section>`;
      }
      return `<section class="grid">
        <div class="card span-12 dir-banner">🧭 Mô hình <b>móng + spike</b> (kế thừa Chiến lược + Playbook): <b>🟢 Branding</b> = nền MÓNG chạy liên tục bên dưới (để được nhớ) · <b>🔴 các đợt</b> = SPIKE đắp lên đúng dịp (ra đơn). Set ở đây → nhìn cả 2 theo <b>thời gian</b> ở <a href="#calendar">Lịch →</a></div>
        <div class="span-12">${messagingBand()}</div>
        <div id="campaignPlan" class="span-12"><div class="card"><p class="muted">⏳ Đang lập tuyến nội dung theo chiến lược của bạn…</p></div></div>
      </section>`;
    },
    mount: () => { loadCampaignPlan(); },
  };
  // D-040: nạp content pillars (always-on) + gợi ý occasion theo ngành
  let _lastOccasions = [];   // M1.1: gợi ý dịp để pre-fill wizard tạo occasion
  async function loadCampaignPlan(steer = '') {
    const host = document.getElementById('campaignPlan');
    if (!host || !apiAvailable || !M.bizEnabled) return;
    const E = s => (s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    const enc = x => encodeURIComponent(JSON.stringify(x));
    if (steer) host.innerHTML = `<div class="card"><p class="muted">⏳ Đang sinh lại tuyến nền theo định hướng…</p></div>`;
    try {
      const q = bizQuery() + (steer ? ((bizQuery() ? '&' : '?') + 'steer=' + encodeURIComponent(steer)) : '');
      const r = await API.get('api/biz/campaign-plan' + q);
      const p = (r && r.plan) || {};
      const pillars = p.pillars || [], occ = p.occasions || [];
      const locked = !!p.pillars_locked;
      _lastOccasions = occ;
      if (!pillars.length && !occ.length) {
        host.innerHTML = `<div class="card"><p class="muted">Chưa lập được 2 tuyến — chạy lại Chiến lược (T4) rồi quay lại.</p></div>`; return;
      }
      const occRows = occ.map(o => `
        <li class="row"><div class="row-main"><p>🔴 ${E(o.name)} ${o.when ? `<span class="muted">· ${E(o.when)}</span>` : ''}</p>${o.why ? `<span class="muted">${E(o.why)}</span>` : ''}</div></li>`).join('');
      const _rhy = (window.MOCK && M.bizContentRhythm) || {};
      const _msgCore = ((window.MOCK && M.bizMessaging) || {}).core || '';
      host.innerHTML = `<section class="grid" style="margin:0">
        ${card('🟢 Nền thương hiệu (móng) <span class="muted" style="font-weight:400">(chạy quanh năm — để được nhớ)</span>', `
          <p class="muted" style="margin-bottom:12px">Nền giờ điều khiển ở <b>2 trang riêng</b> (gọn, không trùng): <b>🎛️ nhịp</b> (bao lâu/lần) + <b>🏛️ thông điệp</b> (nói gì với khách). Max rải nhịp lên Lịch + bám thông điệp khi viết bài.</p>
          <div class="occ-row" style="gap:10px;flex-wrap:wrap">
            <a class="primary-btn" href="#rhythm">🎛️ Nhịp nền${_rhy.per_week ? ` · ${_rhy.per_week} bài/tuần` : ''}</a>
            <a class="primary-btn" href="#message">🏛️ Thông điệp${_msgCore ? ` · "${E(_msgCore)}"` : ''}</a>
          </div>
          <p class="muted" style="margin:14px 0 6px;font-size:12px">📊 Bản đồ phễu × kênh (tham khảo khi lên bài):</p>
          <div>${funnelMapView('brand')}</div>`, { cls: 'span-12' })}
        ${card('🔴 Các đợt (spike) — đắp lên nền <span class="muted" style="font-weight:400">(theo dịp, từ Chiến lược)</span>', `
          <p class="muted" style="margin-bottom:12px">Mỗi đợt = <b>1 mục tiêu</b> (Nhận biết · Ra mắt · Sale · Thu lead · Tương tác · Giữ & Winback), cộng thêm lên tuyến nền trong đúng dịp.</p>
          <ul class="rows">${occRows || '<li class="muted">—</li>'}</ul>
          <button class="primary-btn full" data-act="new-occasion" style="margin-top:14px">＋ Tạo đợt mới</button>
          <button class="ghost-line full" data-act="portfolio-open" style="margin-top:8px">🗓️ Gợi ý lịch các đợt (từ Chiến lược)</button>
          <p class="muted" style="margin-top:6px;font-size:12px">Max suy từ roadmap → gợi ý <b>nên chạy đợt gì vào lúc nào</b>, bạn duyệt rồi tạo.</p>
          <div class="occ-row" style="gap:8px;margin-top:12px">
            <button class="ghost-line sm" style="flex:1" data-act="new-lifecycle" data-mode="retention">🔁 Cẩm nang giữ chân (no-data)</button>
            <button class="ghost-line sm" style="flex:1" data-act="new-lifecycle" data-mode="winback">↩️ Kéo khách cũ</button>
          </div>`, { cls: 'span-12' })}
      </section>`;
    } catch (e) { host.innerHTML = `<div class="card"><p class="muted">Không lập được kế hoạch — thử lại sau.</p></div>`; }
  }

  /* ── Lô G: bản đồ phễu × kênh (TOFU/MOFU/BOFU) cho 1 tuyến mục đích ── */
  const _ROLE_LBL = { khai_sang: 'Khai sáng', tin_cay: 'Tin cậy', chuyen_hoa: 'Chuyển hoá', lan_toa: 'Lan toả' };
  function funnelMapView(obj) {
    const E = s => (s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    const fm = (M.bizFunnelMap || {})[obj];
    if (!fm || !(fm.channels || []).length) {
      return `<div class="fmap-empty"><p class="muted" style="margin:0 0 8px">📊 <b>Bản đồ phễu × kênh</b> — Max map nội dung theo TOFU→MOFU→BOFU cho từng kênh, bám Playbook + archetype.</p>
        <button class="ghost-line sm" data-act="gen-funnel" data-obj="${obj}">📊 Dựng bản đồ phễu × kênh</button></div>`;
    }
    const STAGES = [['tofu', 'khai_sang'], ['mofu', 'tin_cay'], ['bofu', 'chuyen_hoa']];
    const rows = fm.channels.map(c => `
      <div class="fmap-row">
        <div class="fmap-ch">📡 ${E(c.channel)}</div>
        ${STAGES.map(([k, role]) => { const s = c[k] || {}; return `
          <div class="fmap-cell">
            <div class="fmap-goal">${E(s.goal || '')}</div>
            ${(s.formats || []).length ? `<div class="fmap-fmt">${s.formats.map(f => `<span class="tag">${E(f)}</span>`).join('')}</div>` : ''}
            ${(s.angles || []).length ? `<ul class="fmap-ang">${s.angles.map(a => `<li>${E(a)}</li>`).join('')}</ul>` : ''}
            ${s.cta ? `<div class="fmap-cta">📣 ${E(s.cta)}</div>` : ''}
            <div class="fmap-foot"><span class="muted">${E(s.volume || '')}</span>
              <button class="chip-btn sm" data-act="funnel-post" data-ch="${encodeURIComponent(c.channel)}" data-stage="${k}" data-role="${role}" data-obj="${obj}" data-topic="${encodeURIComponent((s.angles || [])[0] || s.goal || '')}">⚡ Tạo bài</button></div>
          </div>`; }).join('')}
      </div>`).join('');
    return `<div class="fmap">
      <div class="fmap-head"><b>📊 Bản đồ phễu × kênh</b>${fm.ratio ? ` <span class="tag">tỷ lệ ${E(fm.ratio)}</span>` : ''}
        <button class="ghost-line sm" data-act="gen-funnel" data-obj="${obj}" style="margin-left:auto">↻ Dựng lại</button></div>
      <div class="fmap-grid-h"><span></span><span>TOFU · Khơi</span><span>MOFU · Nuôi</span><span>BOFU · Chốt</span></div>
      ${rows}</div>`;
  }

  /* ════ M-G/S-10/11/12: CAMPAIGN-FIRST — Bóc GAP → Campaign tổng → sub → tuyến → bài ════ */
  const _eHero = s => (s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  function _masters() {
    const meta = M.bizCampaignMeta || {};
    return Object.keys(meta).filter(id => meta[id] && meta[id].role === 'master')
      .map(id => ({ id, ...meta[id] }));
  }
  function _subsOf(masterId) {
    const meta = M.bizCampaignMeta || {};
    return Object.keys(meta).filter(id => meta[id] && meta[id].role === 'sub'
      && String(meta[id].parent) === String(masterId)).map(id => ({ id, ...meta[id] }));
  }
  // Hero trên trang Lập chiến dịch: Bước 1 Bóc GAP · Bước 2 Campaign tổng (list → hub).
  function campaignFirstHero() {
    const E = _eHero, gaps = M.bizGaps || [], masters = _masters();
    const gapCards = gaps.length ? `<div class="gap-grid">${gaps.map((g, i) => `
      <label class="gap-card selectable${_gapSel.includes(i) ? ' on' : ''}">
        <div class="gap-head"><input type="checkbox" class="gap-chk" data-act="gap-toggle" data-idx="${i}" ${_gapSel.includes(i) ? 'checked' : ''}> ${g.icon || '🕳️'} <b>${E(g.title)}</b> <span class="tag">${E(g.kind_label || '')}</span></div>
        ${g.desc ? `<p class="muted">${E(g.desc)}</p>` : ''}
        ${g.why ? `<p class="gap-why">💡 ${E(g.why)}</p>` : ''}
        ${g.segment ? `<p class="muted">👥 ${E(g.segment)}</p>` : ''}
      </label>`).join('')}</div>`
      : `<p class="muted">Chưa bóc gap. Max trích các khoảng trống đáng đánh từ nghiên cứu (thị trường · đối thủ · khách · SWOT) để bạn chọn khi tạo campaign tổng.</p>`;
    const gapBtn = `<button class="${gaps.length ? 'ghost-line' : 'primary-btn'}" data-act="gen-gaps">${gaps.length ? '↻ Bóc lại gap' : '🔍 Bóc gap & cơ hội từ nghiên cứu'}</button>`;
    const masterCards = masters.length ? masters.map(m => {
      const subs = _subsOf(m.id);
      return `<div class="master-card clickable" data-act="master-hub" data-id="${m.id}">
        <div class="master-head">📦 <b>${E(m.name)}</b></div>
        <div class="master-gaps">${(m.gaps || (m.gap ? [m.gap] : [])).map(g => `<span class="gap-badge">${g.icon || '🕳️'} ${E(g.title)}</span>`).join(' ')}</div>
        <div class="master-meta">${m.wedge ? `<span>🎯 ${E(m.wedge)}</span>` : ''}${m.usp ? `<span>⭐ ${E(m.usp)}</span>` : ''}</div>
        <div class="master-foot muted">${subs.length} sub-campaign · ${(m.proposed_subs || []).length} đề xuất · bấm mở hub →</div>
      </div>`;
    }).join('') : `<p class="muted">Chưa có campaign tổng. Tạo 1 cái: chọn gap muốn đánh + tệp wedge + USP → Max dựng sub-campaign + tuyến bài.</p>`;
    return `
      ${card('🕳️ Bước 1 — Bóc GAP & cơ hội', `${gapCards}
        ${gaps.length ? '<p class="muted" style="margin:10px 0 6px">Tick các gap muốn đánh (ngang hàng — không cần gap chính), rồi tạo campaign tổng từ chúng.</p>' : ''}
        <div class="gap-foot">
          ${gaps.length ? `<button id="gapSelBtn" class="primary-btn" data-act="new-master-sel" ${_gapSel.length ? '' : 'disabled'}>${_gapSel.length ? ('📦 Tạo campaign tổng từ ' + _gapSel.length + ' gap đã chọn') : '📦 Chọn gap để tạo campaign tổng'}</button>` : ''}
          ${gapBtn}
        </div>`, { cls: 'span-12' })}
      ${card('📦 Bước 2 — Campaign tổng (đặt cược chiến lược)', `
        <p class="muted" style="margin:0 0 12px">Mỗi campaign tổng = 1 <b>đặt cược</b>: đánh gap nào + tệp nào + USP nào. Có HUB riêng (sub-campaign · tuyến bài · brief · task). Nhiều campaign tổng chạy song song.</p>
        <div class="master-grid">${masterCards}</div>
        <button class="primary-btn full" data-act="new-master" style="margin-top:14px">📦 Tạo campaign tổng mới</button>`, { cls: 'span-12' })}`;
  }

  /* ── Vision A: form ĐẶT CƯỢC theo 5 nhóm (option từ T1-T3 + tự ghi) → T4-T5 ── */
  function betForm() {
    const E = _eHero;
    const cats = M.bizBetCategories || [];
    const opts = M.bizBetOptions || {};
    const chosen = M.bizBetChoices || {};
    if (!cats.length) return '';
    const hasOpts = cats.some(c => (opts[c.key] || []).length);
    const sugBtn = `<button class="${hasOpts ? 'ghost-line' : 'primary-btn'} sm" data-act="gen-bet">${hasOpts ? '↻ Max gợi ý lại từ nghiên cứu' : '✨ Để Max gợi ý lựa chọn từ nghiên cứu'}</button>`;
    const groups = cats.map(c => {
      const list = opts[c.key] || [];
      const sel = chosen[c.key] || [];
      const chips = list.map(o => {
        const on = sel.includes(o.title);
        const tip = ((o.desc || '') + (o.why ? ' — ' + o.why : '')).replace(/"/g, '&quot;');
        return `<button type="button" class="bet-chip${on ? ' on' : ''}" data-act="bet-chip" data-cat="${c.key}" data-val="${E(o.title).replace(/"/g, '&quot;')}" title="${E(tip)}">${E(o.title)}</button>`;
      }).join('');
      const extra = sel.filter(s => !list.some(o => o.title === s)).join(', ');
      return `<div class="bet-grp">
        <div class="bet-grp-h">${c.icon} <b>${E(c.label)}</b> <span class="muted">— ${E(c.hint)}</span>
          <span class="bet-tip">💡 chọn 1 để tập trung · bỏ trống = 🤖 để Max tự quyết</span></div>
        <div class="bet-chips">${chips || '<span class="muted">— chưa có gợi ý (tự ghi · 🤖 Để Max · hoặc bấm "gợi ý" ở trên)</span>'}
          <button type="button" class="bet-chip bet-auto" data-act="bet-auto" data-cat="${c.key}" title="Bỏ chọn nhóm này → Max tự đề xuất khi lập chiến lược">🤖 Để Max</button></div>
        <input class="bet-free" id="betFree-${c.key}" data-cat="${c.key}" placeholder="✍️ Tự ghi (nếu không ưng option nào; phẩy để nhiều)" value="${E(extra)}">
      </div>`;
    }).join('');
    return card('🎯 Đặt cược chiến lược — chọn hướng trên dữ liệu THẬT', `
      <div class="bet-intro">
        <p class="muted" style="margin:0">Mỗi nhóm: <b>tự ghi</b> hướng của bạn, bấm <b>🤖 Để Max</b> tự quyết, hoặc bấm nút bên để Max <b>gợi ý option</b> từ nghiên cứu rồi chọn. <b>Khuyên 1/nhóm</b> cho tập trung; để trống hết = Max lo toàn bộ.</p>
        ${sugBtn}
      </div>
      ${groups}`, { cls: 'span-12' });
  }

  /* ── Wizard tạo Campaign tổng (chọn các gap → đặt cược → Max đề xuất sub → chốt) ── */
  let _gapSel = [];   // gap tick ở Bước 1 (đa gap, ngang hàng — không gap chính)
  let _masterState = { step: 'gap', gapIdxs: [], wedge: '', usp: '', name: '', masterId: '', subs: [], picked: [], busy: false };
  function openMasterWizard(opts) {
    if (!apiAvailable || !M.bizEnabled) { toast('Bật backend (Supabase + LLM) để tạo campaign tổng'); return; }
    opts = opts || {};
    _masterState = { step: opts.step || 'gap', gapIdxs: (opts.gapIdxs || _gapSel).slice(),
      wedge: '', usp: '', name: '', masterId: '', subs: [], picked: [], busy: false };
    _ensureBizModal(); renderMasterWizard(); document.getElementById('bizModal').classList.add('show');
  }
  function _msSync() {   // giữ giá trị ô input khi re-render
    const S = _masterState, ov = document.getElementById('bizModal'); if (!ov) return;
    const w = ov.querySelector('#mWedge'), u = ov.querySelector('#mUsp'), n = ov.querySelector('#mName');
    if (w) S.wedge = w.value; if (u) S.usp = u.value; if (n) S.name = n.value;
  }
  function renderMasterWizard() {
    const ov = document.getElementById('bizModal'); if (!ov) return;
    const E = _eHero, S = _masterState;
    ov.querySelector('h3').textContent = '📦 Tạo campaign tổng';
    const body = ov.querySelector('.modal-body'), foot = ov.querySelector('.modal-foot');
    foot.style.display = 'flex';
    if (S.step === 'gap') {
      const gaps = M.bizGaps || [];
      if (!gaps.length) {
        body.innerHTML = `<p class="muted">Chưa có gap để chọn. Bóc gap trước rồi quay lại, hoặc bấm dưới để Max bóc ngay.</p>`;
        foot.innerHTML = `<button class="ghost-line sm" data-act="master-close">Đóng</button>
          <button class="primary-btn sm" data-act="gen-gaps">🔍 Bóc gap ngay</button>`;
        return;
      }
      body.innerHTML = `<p class="muted" style="margin:0 0 10px">Tick các <b>gap</b> campaign tổng này sẽ đánh — <b>ngang hàng</b>, cấu thành 1 đặt cược (không cần gap chính):</p>
        <div class="gap-pick">${gaps.map((g, i) => `
          <label class="gap-opt${S.gapIdxs.includes(i) ? ' on' : ''}">
            <input type="checkbox" ${S.gapIdxs.includes(i) ? 'checked' : ''} data-act="master-gap" data-idx="${i}">
            <span>${g.icon || '🕳️'} <b>${E(g.title)}</b> <small class="muted">${E(g.kind_label || '')}</small><br><small class="muted">${E(g.desc || '')}</small></span>
          </label>`).join('')}</div>`;
      foot.innerHTML = `<button class="ghost-line sm" data-act="master-close">Đóng</button>
        <button class="primary-btn sm" data-act="master-next" ${S.gapIdxs.length ? '' : 'disabled'}>Tiếp →</button>`;
    } else if (S.step === 'bet') {
      const gsel = S.gapIdxs.map(i => (M.bizGaps || [])[i]).filter(Boolean);
      body.innerHTML = `
        <p class="muted" style="margin:0 0 10px">Gap đã chọn (${gsel.length}): ${gsel.map(g => `<b>${E(g.title)}</b>`).join(' · ') || '—'}</p>
        <label class="slot-axis"><span>Tệp ưu tiên (wedge) — đánh ai trước</span>
          <input id="mWedge" class="slot-topic" value="${E(S.wedge)}" placeholder="vd: chủ shop nhỏ mới mở, ngân sách hạn chế"></label>
        <label class="slot-axis" style="margin-top:10px"><span>USP — lời hứa khác biệt</span>
          <input id="mUsp" class="slot-topic" value="${E(S.usp)}" placeholder="vd: giao trong 2h, đổi trả 30 ngày không hỏi"></label>
        <label class="slot-axis" style="margin-top:10px"><span>Tên campaign tổng <small class="muted">· để trống = tự đặt</small></span>
          <input id="mName" class="slot-topic" value="${E(S.name)}" placeholder="vd: Chiếm tệp shop nhỏ Q3"></label>
        <p class="muted" style="margin:10px 0 0;font-size:12px">Để trống wedge/USP = Max lấy theo Chiến lược (synthesis).</p>`;
      foot.innerHTML = `<button class="ghost-line sm" data-act="master-back">← Lại</button>
        <button class="primary-btn sm" data-act="master-genplan" ${S.busy ? 'disabled' : ''}>${S.busy ? '⏳ Max đang nghĩ…' : '🤖 Max đề xuất sub-campaign →'}</button>`;
    } else if (S.step === 'subs') {
      const proposed = S.subs || [];
      body.innerHTML = `
        <p class="muted" style="margin:0 0 10px">✅ Đã tạo campaign tổng. Max đề xuất các <b>sub-campaign</b> cho đặt cược này — tick cái muốn tạo:</p>
        <div class="sub-pick">${proposed.map((s, i) => `
          <label class="sub-opt${S.picked.includes(i) ? ' on' : ''}">
            <input type="checkbox" data-act="master-pick" data-idx="${i}" ${S.picked.includes(i) ? 'checked' : ''}>
            <span>${s.type_icon || '🔴'} <b>${E(s.name)}</b> <small class="muted">${E(s.type_label || '')}</small><br><small class="muted">${E(s.why || '')}</small></span>
          </label>`).join('') || '<p class="muted">Không có đề xuất — bạn thêm sub thủ công trong hub.</p>'}</div>
        <p class="muted" style="margin:12px 0 0;font-size:12px">🟢 Branding nền tạo riêng (xuyên suốt). Thêm/bớt sub trong hub bất cứ lúc nào.</p>`;
      foot.innerHTML = `<button class="ghost-line sm" data-act="master-skip">Để sau →</button>
        <button class="primary-btn sm" data-act="master-commit" ${S.busy ? 'disabled' : ''}>${S.busy ? '⏳ Đang tạo…' : '✅ Tạo sub đã chọn → mở hub'}</button>`;
    }
  }

  /* ── Hub campaign tổng: đặt cược · sub-campaign · tuyến bài · topics → tạo bài ── */
  let _hubId = null;
  function openMasterHub(id) {
    _hubId = id; _ensureBizModal(); renderMasterHub();
    document.getElementById('bizModal').classList.add('show');
  }
  function renderMasterHub() {
    const ov = document.getElementById('bizModal'); if (!ov || _hubId == null) return;
    const E = _eHero, meta = M.bizCampaignMeta || {}, m = meta[String(_hubId)];
    if (!m) { ov.querySelector('.modal-body').innerHTML = '<p class="muted">Không tìm thấy campaign tổng.</p>'; return; }
    ov.querySelector('h3').textContent = `📦 ${m.name || 'Campaign tổng'}`;
    const subs = _subsOf(_hubId), committed = new Set(subs.map(s => s.type));
    const _hgaps = m.gaps || (m.gap ? [m.gap] : []);
    const betHdr = `<div class="hub-bet">
      ${_hgaps.map(g => `<span class="gap-badge">${g.icon || '🕳️'} ${E(g.title)}</span>`).join('')}
      ${m.wedge ? `<span class="hub-chip">🎯 ${E(m.wedge)}</span>` : ''}
      ${m.usp ? `<span class="hub-chip">⭐ ${E(m.usp)}</span>` : ''}</div>`;
    const addable = (m.proposed_subs || []).filter(s => !committed.has(s.type));
    const addRow = addable.length ? `<div class="hub-add"><span class="muted">➕ Thêm sub đề xuất:</span> ${addable.map(s =>
      `<button class="ghost-line sm" data-act="hub-add-sub" data-type="${s.type}" data-name="${encodeURIComponent(s.name || '')}">${s.type_icon || ''} ${E(s.name)}</button>`).join('')}</div>` : '';
    const subCards = subs.map(s => {
      const tracks = s.tracks || [], hasTopics = tracks.some(t => (t.topics || []).length);
      const trackHtml = tracks.map(t => {
        const tops = t.topics || [];
        const topHtml = tops.length ? `<ul class="tuyen-topics">${tops.map(tp => `
          <li><span class="tt-text">${E(tp.t || '')}</span>${tp.lens ? ` <small class="tag">${E(tp.lens)}</small>` : ''}
            <button class="chip-btn sm" data-act="sub-topic-post" data-sub="${s.id}" data-track="${t.key}" data-topic="${encodeURIComponent(tp.t || '')}" data-lens="${encodeURIComponent(tp.lens || '')}">⚡ Tạo bài</button></li>`).join('')}</ul>`
          : '<p class="muted" style="margin:2px 0 0">— (chưa có chủ đề)</p>';
        return `<div class="tuyen"><div class="tuyen-h">${t.icon || ''} <b>${E(t.label)}</b> <small class="muted">${E(t.role || '')}</small></div>${topHtml}</div>`;
      }).join('');
      return `<div class="sub-block">
        <div class="sub-head">${s.type_icon || '🔴'} <b>${E(s.type_label || 'Sub')}</b>${s.audience ? ` <span class="tag">🎯 ${E(s.audience)}</span>` : ''}${s.persistent ? ' <span class="pill green">nền</span>' : ''}
          <span class="sub-head-acts">
            ${s.brief_run_id ? `<button class="ghost-line sm" data-act="camptask-view" data-run="${s.brief_run_id}">📄 Brief</button>` : ''}
            <button class="${hasTopics ? 'ghost-line' : 'primary-btn'} sm" data-act="sub-content-gen" data-sub="${s.id}">${hasTopics ? '↻ Sinh lại tuyến' : '✨ Sinh brief + chủ đề tuyến'}</button>
            <button class="ghost-line sm" data-act="camp-detail" data-camp-id="${s.id}">📋 Task</button>
          </span></div>
        <div class="tuyen-wrap">${trackHtml || '<p class="muted">—</p>'}</div></div>`;
    }).join('') || '<p class="muted">Chưa có sub-campaign. Thêm từ đề xuất hoặc loại khác bên dưới.</p>';
    const types = (M.bizCampaignTypes || []).filter(t => t.key !== 'branding');
    const addAny = `<div class="hub-add" style="margin-top:10px"><span class="muted">➕ Loại khác:</span> ${types.map(t =>
      `<button class="ghost-line sm" data-act="hub-add-sub" data-type="${t.key}" data-name="">${t.icon || ''} ${E(t.label)}</button>`).join('')}</div>`;
    ov.querySelector('.modal-body').innerHTML = betHdr + addRow + `<div class="sub-list">${subCards}</div>` + addAny;
    const foot = ov.querySelector('.modal-foot'); foot.style.display = 'none'; foot.innerHTML = '';
  }

  /* ---- (gỡ) Campaign Brief mock — thay bằng Occasion brief thật (M1.1).
     Route #brief redirect → #occasion (xem route()). ---- */

  /* ---- Lịch nội dung — Kế hoạch: Always-on (nền, LUÔN chạy) + Campaign theo dịp (cộng thêm) ---- */
  let _calView = 'plan';   // 'plan' (tháng) | 'week' (chi tiết tuần)
  let _calWeek = 1;        // tuần đang xem ở chế độ week
  let _realCal = null;     // M1.2: lịch THẬT (occasion bands + pillars) khi bizEnabled
  const calPlan = () => _realCal || M.calendarPlan || { days: [], weeks: 0, alwaysOn: [], campaigns: [], orphans: [] };
  async function loadRealCalendar() {
    if (!apiAvailable || !M.bizEnabled) { _realCal = null; return; }
    try {
      const r = await API.get('api/biz/calendar' + bizQuery());
      const c = r && r.calendar;
      _realCal = (c && (c.campaigns || c.alwaysOn || c.orphans)) ? c : null;
      if (_realCal) route();   // re-render với dữ liệu thật
    } catch (e) { _realCal = null; }
  }
  // M-E: khay "Bài chưa xếp lịch" — bài đã duyệt mà trụ/đợt đổi/bị bỏ; KHÔNG mất, founder xử.
  function calOrphanTray() {
    const orphans = (calPlan().orphans) || [];
    if (!orphans.length) return '';
    const E = s => (s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    return `<div class="cal-orphans">
      <div class="cal-orphans-head">⚠️ ${orphans.length} bài đã duyệt cần xếp lại
        <span class="muted">— trụ/đợt liên quan đã đổi hoặc bị bỏ. Bài KHÔNG mất: lưu vào Tài liệu hoặc bỏ.</span></div>
      ${orphans.map(o => `<div class="cal-orphan">
        <div class="cal-orphan-meta"><b>${E(o.label || 'Bài')}</b> · <span class="muted">${E(o.excerpt || '')}…</span></div>
        <div class="cal-orphan-acts">
          <button class="ghost-line sm" data-act="orphan-archive" data-key="${encodeURIComponent(o.key)}">📁 Lưu vào Tài liệu</button>
          <button class="ghost-line sm" data-act="orphan-del" data-key="${encodeURIComponent(o.key)}">🗑 Bỏ</button>
        </div></div>`).join('')}</div>`;
  }
  const campActiveWeek = (w) => (calPlan().campaigns || []).filter(c => w >= c.fromWeek && w <= c.toWeek);
  // Bài campaign cộng thêm trong 1 (tuần, ngày)
  const campPostsAt = (w, d) => {
    const out = [];
    (calPlan().campaigns || []).forEach(c => (c.posts || []).forEach(p => {
      if (p.week === w && p.day === d) out.push({ ...p, camp: c });
    }));
    return out;
  };
  const alwaysCard = (p) => `<div class="cal-post clickable ${p.saved?'saved':''}" data-act="slot-open" data-slot="${encodeURIComponent(JSON.stringify(p))}" style="--accent:var(--green)" title="${p.saved?'Đã duyệt — bấm để xem/sửa':'Bấm để chọn chủ đề & tạo bài'}">
      <div class="cal-post-top"><span class="trk on">Always-on</span><span class="pill-tag ${pillarCls(p.pillar)}">${p.pillar}</span>${p.saved?'<span class="slot-done">✓ Đã duyệt</span>':''}</div>
      <p class="cal-post-topiclbl">💡 Chủ đề</p>
      <p class="cal-post-title">${p.title}</p></div>`;
  const campCard = (p) => `<div class="cal-post clickable ${p.saved?'saved':''}" data-act="slot-open" data-slot="${encodeURIComponent(JSON.stringify({track:'camp', campaignId:p.camp.campaignId, phase:p.phase||'', title:p.title, pillar:`${p.icon||'🔴'} ${p.phase||'Đợt'}`, funnel:p.camp.name, week:p.week, day:p.day, key:p.key||'', angles:[p.title], saved:p.saved, post:p.post}))}" style="--accent:${p.camp.color}" title="${p.saved?'Đã duyệt — bấm để xem/sửa':'Bấm để soạn bài đợt'}">
      <div class="cal-post-top"><span class="trk camp" style="--c:${p.camp.color}">${p.camp.name}</span><span class="pill-tag c4">${p.phase||'Convert'}</span>${p.saved?'<span class="slot-done">✓</span>':''}</div>
      <p class="cal-post-title">${p.title}</p><span class="cal-offer">🎁 ${p.camp.offer}</span></div>`;
  // M-A: always-on giờ là slot theo (tuần,ngày) khi có dữ liệu thật; mock cũ = mảng phẳng 7 ô.
  const _alwaysHasWeeks = (a) => a && a.length && a[0] && a[0].week != null;
  const alwaysAt = (P0, w, d) => {
    const a = P0.alwaysOn || [];
    if (_alwaysHasWeeks(a)) return a.filter(s => s.week === w && s.day === d);
    const one = a[d]; return one ? [one] : [];
  };
  const alwaysWeekCount = (P0, w) => {
    const a = P0.alwaysOn || [];
    return _alwaysHasWeeks(a) ? a.filter(s => s.week === w).length : a.length;
  };
  const alwaysWeekFirstPillar = (P0, w) => {
    const a = P0.alwaysOn || [];
    if (_alwaysHasWeeks(a)) { const f = a.find(s => s.week === w); return f ? f.pillar : ''; }
    return (a[0] || {}).pillar || '';
  };

  // VIEW THÁNG (kế hoạch) — Gantt theo tuần + tóm tắt mỗi tuần
  function calPlanView() {
    const P0 = calPlan(); const W = P0.weeks || 4;
    const bands = (P0.campaigns || []).map(c =>
      `<div class="band-camp clickable" style="grid-column:${c.fromWeek} / ${c.toWeek + 1}; --c:${c.color}"
         data-act="camp-detail" data-camp-id="${c.campaignId||''}" title="Bấm xem chi tiết + việc cần làm">
        <b>🔴 ${c.name}</b> ${(c.posts||[]).map(p=>p.icon||'').join('')} · 🎁 ${c.offer} <span class="band-task-hint">📋</span></div>`).join('');
    const weekRows = Array.from({ length: W }, (_, k) => {
      const w = k + 1; const camps = campActiveWeek(w);
      const campCount = camps.reduce((n, c) => n + (c.posts || []).filter(p => p.week === w).length, 0);
      return `<div class="planweek">
        <div class="pw-head"><b>Tuần ${w}</b>
          <button class="ghost-line sm" data-act="cal-open-week" data-week="${w}">Mở chi tiết →</button></div>
        <div class="pw-tracks">
          <div class="pw-track on"><span class="trk on">🟢 Branding nền</span> ${alwaysWeekCount(P0, w)} bài brand
            <button class="chip-btn sm" data-act="cal-gen" data-week="${w}" data-track="always" data-pillar="${alwaysWeekFirstPillar(P0, w).replace(/"/g,'&quot;')}">⚡ Tạo bài tuần ${w}</button></div>
          ${camps.length ? camps.map(c => `<div class="pw-track camp" style="--c:${c.color}">
            <span class="trk camp" style="--c:${c.color}">🔴 ${c.name}</span> ${campCount} bài theo mục tiêu đợt
            <button class="chip-btn sm" data-act="cal-gen" data-week="${w}" data-track="camp" data-camp-id="${c.campaignId||''}">⚡ Tạo bài cho đợt</button></div>`).join('')
          : `<div class="pw-track muted">Không có đợt — chỉ chạy nền Branding</div>`}
        </div></div>`;
    }).join('');
    return `
      <section class="calboard">
        <div class="cal-bands" style="grid-template-columns:repeat(${W},1fr)">
          <a class="band-base band-brand clickable" style="grid-column:1 / -1" href="#rhythm" title="Nhịp nền — bấm để chỉnh 6 tuyến chạy quanh năm"><span>🟢 <b>Branding nền</b> · liên tục · không deadline — chạy suốt cả ${W} tuần, KHÔNG tắt khi có đợt · 🎛️ chỉnh nhịp</span></a>
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
          const aSlots = alwaysAt(P0, w, i);
          const slotPillar = (aSlots[0] || {}).pillar || '';
          const genAttrs = inCamp
            ? `data-track="camp" data-camp-id="${cps[0].camp.campaignId || ''}"`
            : `data-track="always" data-pillar="${slotPillar.replace(/"/g, '&quot;')}"`;
          return `<div class="cal-col ${inCamp ? 'in-camp' : ''}" ${inCamp ? `style="--c:${cps[0].camp.color}"` : ''}>
            <div class="cal-colhead">${d}${inCamp ? `<span class="col-dot" style="background:${cps[0].camp.color}"></span>` : ''}</div>
            ${aSlots.map(alwaysCard).join('') || (cps.length ? '' : '<p class="muted cal-empty">— nghỉ —</p>')}
            ${cps.map(campCard).join('')}
            <button class="cal-add" data-act="cal-gen" data-week="${w}" data-day="${i}" ${genAttrs}>⚡ Tạo bài</button></div>`;
        }).join('')}
      </div>`;
  }

  P.calendar = {
    title: 'Kế hoạch marketing',
    sub: 'Theo thời gian: 🟢 nền thương hiệu chạy liên tục (móng) + 🔴 đợt đắp lên đúng dịp (spike)',
    get actions() {
      return `<div class="segmented">
          <button class="${_calView==='plan'?'on':''}" data-act="cal-view" data-view="plan">Kế hoạch tháng</button>
          <button class="${_calView==='week'?'on':''}" data-act="cal-view" data-view="week">Chi tiết tuần</button>
        </div>
        ${_realCal ? `<button class="ghost-line" data-act="gen-topics">✨ Gợi ý chủ đề cả lịch</button>` : ''}
        <a class="ghost-line" href="#rhythm">🎛️ Nhịp nền</a>
        <button class="ghost-line" data-act="portfolio-open">🗓️ Gợi ý lịch đợt</button>
        <button class="primary-btn" data-act="add-campaign-occasion">＋ Thêm đợt vào lịch</button>`;
    },
    render: () => `
      ${_realCal
        ? `<div class="cal-note">${badge('Dựng từ chiến lược','green')} <span class="muted"> Always-on lấy từ <b>${(_realCal.alwaysOn||[]).length? new Set((_realCal.alwaysOn||[]).map(s=>s.pillar)).size : 0} trụ đã chốt</b>, rải theo nhịp đăng suốt <b>${({'30':'30 ngày','60':'60 ngày','90':'90 ngày'})[_realCal.horizon]||(_realCal.weeks+' tuần')}</b>. Mỗi ô bấm ⚡ để sinh bài thật.</span></div>`
        : (M.bizEnabled
        ? `<div class="cal-note">${badge('Chưa có dữ liệu thật','amber')} <span class="muted"> Lập + chốt Chiến lược, rồi set <a href="#rhythm">🎛️ Nhịp nền</a> để lịch nền hiện thật. Đang xem mẫu.</span></div>`
        : `<div class="cal-note">${badge('Bản thiết kế UX','amber')} <span class="muted"> Mô hình kế hoạch — dữ liệu mẫu, nối thật khi bật backend.</span></div>`)}
      <div class="cal-legend">
        <span><i class="lg on"></i> 🟢 Branding (nền) — bài brand chạy đều mỗi tuần, KHÔNG tắt khi có đợt</span>
        <span><i class="lg camp"></i> 🗓️ Đợt chiến dịch — bài theo mục tiêu đợt, CỘNG THÊM lên nền trong đúng dịp</span>
        <span class="cal-arc-legend">Đợt chạy theo Story Arc: 🌱 Teaser → 🔥 Build-up → 🚀 Peak → ⏰ Last-call → 💌 After (đợt ngắn gộp 3 pha)</span>
      </div>
      ${messagingBand()}
      ${balanceNudge()}
      ${calOrphanTray()}
      ${_calView === 'plan' ? calPlanView() : calWeekView()}`,
    mount: () => { loadRealCalendar(); },
  };
  // Timeline-first: nhắc cân bằng brand·đơn (Binet&Field 60/40) — giá trị "có-CMO".
  function balanceNudge() {
    if (!_realCal) return '';
    const P0 = calPlan();
    const hasBrand = (P0.alwaysOn || []).length > 0;
    const nDot = (P0.campaigns || []).length;
    let msg = '';
    if (hasBrand && nDot === 0)
      msg = 'Đang chạy <b>nền thương hiệu</b> nhưng <b>chưa có đợt nào</b> — thêm đợt kích hoạt quanh dịp để tạo spike doanh thu.';
    else if (!hasBrand && nDot > 0)
      msg = `Có <b>${nDot} đợt</b> nhưng <b>nền thương hiệu mỏng/chưa chốt</b> — chạy đợt mà thiếu nền thì khó được nhớ lâu dài. Nên chốt tuyến nền trước.`;
    else if (nDot >= 5)
      msg = `<b>${nDot} đợt</b> — nhớ giữ ~60% sức cho <b>nền thương hiệu</b> để không đốt tiền ngắn hạn.`;
    if (!msg) return '';
    return `<div class="balance-nudge">💡 <b>Cân bằng brand · đơn (60/40):</b> ${msg} <a href="#occasion">Quản tuyến →</a></div>`;
  }

  /* ════════ Tầng ③ — BẢNG ĐIỀU KHIỂN NHỊP NỀN (6 tuyến chạy quanh năm) ════════ */
  // Đệm chỉnh cục bộ; null = chưa nạp → lấy từ MOCK.bizContentRhythm. Lưu xong reset về null.
  let _rhythm = null;
  function rhythmState() {
    if (_rhythm) return _rhythm;
    const base = ((window.MOCK && M.bizContentRhythm) || {}).rhythm || {};
    _rhythm = {};
    ((window.MOCK && M.bizContentDang) || []).forEach(d => {
      const r = base[d.key] || {};
      _rhythm[d.key] = { on: !!r.on, freq: (r.freq != null ? +r.freq : 1) };
    });
    return _rhythm;
  }
  function rhythmStats() {
    const S = rhythmState();
    let brand = 0, sales = 0;
    ((window.MOCK && M.bizContentDang) || []).forEach(d => {
      const r = S[d.key]; if (!r || !r.on) return;
      if (d.group === 'sales') sales += r.freq; else brand += r.freq;
    });
    const total = brand + sales;
    return { brand, sales, total,
      brandPct: total ? Math.round(brand / total * 100) : 0,
      salesPct: total ? Math.round(sales / total * 100) : 0,
      perMonth: Math.round(total * 4.3 * 10) / 10 };
  }
  const _fmtFreq = n => (Math.round(n * 10) / 10);
  function freqLabel(f) {
    f = +f || 0;
    if (f <= 0) return '—';
    if (f === 0.5) return '1 / 2 tuần';
    return _fmtFreq(f) + ' / tuần';
  }
  P.rhythm = {
    title: 'Nhịp nền nội dung',
    sub: 'Bảng điều khiển 6 tuyến chạy quanh năm — bật/tắt & chỉnh nhịp. Max rải đều lên Lịch rồi soạn sẵn từng bài để bạn duyệt',
    get actions() {
      return `<a class="ghost-line" href="#calendar">← Về Lịch</a>
        <button class="primary-btn" data-act="rhythm-save">✅ Chốt nhịp nền → rải lên Lịch</button>`;
    },
    render: () => `
      <div class="dir-banner" style="margin-bottom:14px">🎛️ Bật/tắt &amp; chỉnh nhịp từng tuyến. Max <b>rải đều lên Lịch</b> + <b>soạn sẵn từng bài</b> để bạn duyệt. Đợt sale/ra mắt thì vặn to ở mục <a href="#occasion">Đợt →</a>.</div>
      <div id="rhyWrap">${rhythmInner()}</div>`,
    mount: () => {},
  };
  function rhythmInner() {
    const dangs = (window.MOCK && M.bizContentDang) || [];
    if (!dangs.length) return `<section class="card"><p class="muted">Chưa có dữ liệu dạng nội dung — bật backend để chỉnh nhịp nền.</p></section>`;
    const S = rhythmState();
    const sug = ((window.MOCK && M.bizContentRhythm) || {}).suggest || {};
    const E = s => (s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    const row = (d) => {
      const r = S[d.key] || { on: false, freq: 1 };
      const sf = sug[d.key];
      return `<div class="rhy-row ${r.on ? 'on' : ''}">
        <div class="rhy-main">
          <span class="rhy-ic">${d.icon}</span>
          <div class="rhy-txt"><b>${E(d.label)}</b> <span class="rhy-role">${E(d.role_label)}</span>
            <small class="rhy-desc">${E(d.desc)}</small></div>
          <button class="rhy-toggle ${r.on ? 'on' : ''}" data-act="rhythm-toggle" data-dang="${d.key}" role="switch" aria-checked="${r.on}"><i></i></button>
        </div>
        <div class="rhy-freq ${r.on ? '' : 'off'}">
          <span class="rhy-freq-lbl">Nhịp</span>
          <button class="rhy-step" data-act="rhythm-freq" data-dang="${d.key}" data-dir="-1" ${r.on ? '' : 'disabled'}>−</button>
          <span class="rhy-freq-val">${freqLabel(r.freq)}</span>
          <button class="rhy-step" data-act="rhythm-freq" data-dang="${d.key}" data-dir="1" ${r.on ? '' : 'disabled'}>＋</button>
          ${sf != null ? `<span class="rhy-sug" title="Max gợi ý">✦ ${freqLabel(sf)}</span>` : ''}
        </div>
      </div>`;
    };
    const brand = dangs.filter(d => d.group === 'brand');
    const sales = dangs.filter(d => d.group === 'sales');
    const st = rhythmStats();
    const barB = st.total ? Math.round(st.brand / st.total * 100) : 0;
    return `
      <section class="grid rhy-grid">
        <div class="card span-6 rhy-col">
          <div class="rhy-col-head rhy-brand">🟢 Xây thương hiệu <span class="muted">nhớ &amp; tin</span></div>
          ${brand.map(row).join('')}
        </div>
        <div class="card span-6 rhy-col">
          <div class="rhy-col-head rhy-sales">🔴 Bán &amp; Giữ <span class="muted">chốt &amp; quay lại</span></div>
          ${sales.map(row).join('')}
        </div>
      </section>
      <section class="card rhy-summary">
        <div class="rhy-sum-l">📊 Tổng nhịp nền: <b>${_fmtFreq(st.total)} bài/tuần</b> · ~${st.perMonth} bài/tháng</div>
        <div class="rhy-balance">
          <div class="rhy-bar" title="Tỉ lệ brand · bán"><div class="rhy-bar-brand" style="width:${barB}%"></div></div>
          <span class="rhy-bal-txt">Thương hiệu ${st.brandPct}% · Bán-Giữ ${st.salesPct}%</span>
        </div>
      </section>`;
  }
  function rerenderRhythm() {
    const w = document.getElementById('rhyWrap');
    if (w) w.innerHTML = rhythmInner();
  }

  /* ════════ THÔNG ĐIỆP (Messaging House) — "nói gì với khách", content bám vào ════════ */
  let _msg = null;   // đệm chỉnh; null = lấy từ MOCK.bizMessaging
  function msgHas() { const m = (window.MOCK && M.bizMessaging) || {}; return !!(m.core || (m.pillars || []).length); }
  function msgState() {
    if (_msg) return _msg;
    const m = (window.MOCK && M.bizMessaging) || {};
    _msg = {
      core: m.core || '',
      taglines: (m.taglines || []).slice(),
      pillars: (m.pillars || []).map(p => ({ icon: p.icon || '📌', territory: p.territory || '', angle: p.angle || '', proof: p.proof || '' })),
      voice: { do: ((m.voice || {}).do || []).slice(), dont: ((m.voice || {}).dont || []).slice() },
    };
    return _msg;
  }
  function _msgSync() {   // gom giá trị input vào đệm (giữ khi thêm/bớt trụ)
    const w = document.getElementById('msgWrap'); if (!w) return;
    const S = msgState();
    const core = w.querySelector('[data-msgfield="core"]'); if (core) S.core = core.value;
    S.pillars.forEach((p, i) => {
      ['icon', 'territory', 'angle', 'proof'].forEach(f => {
        const el = w.querySelector(`[data-msgp="${f}"][data-idx="${i}"]`); if (el) p[f] = el.value;
      });
    });
    const dEl = w.querySelector('[data-msgfield="do"]'); if (dEl) S.voice.do = dEl.value.split('\n').map(s => s.trim()).filter(Boolean);
    const nEl = w.querySelector('[data-msgfield="dont"]'); if (nEl) S.voice.dont = nEl.value.split('\n').map(s => s.trim()).filter(Boolean);
  }
  P.message = {
    title: 'Thông điệp',
    sub: 'Cốt lõi nói với khách — MỌI bài bám vào đây. Max nháp từ Chiến lược, bạn chỉnh cho "ra chất mình" rồi chốt.',
    get actions() {
      return `<a class="ghost-line" href="#strategy">← Chiến lược</a>`
        + (msgHas() || _msg
          ? ` <button class="ghost-line" data-act="msg-gen">↻ Max nháp lại</button> <button class="primary-btn" data-act="msg-save">✅ Chốt thông điệp</button> <a class="ghost-line" href="#occasion">→ Lập chiến dịch</a>`
          : '');
    },
    render: () => `<div id="msgWrap">${msgInner()}</div>`,
    mount: () => {},
  };
  function msgInner() {
    const E = s => (s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    if (M.bizEnabled && !(M.bizLatest || {}).synthesis) {
      return `<section class="card"><div class="empty-cta"><div class="empty-ic">🧭</div>
        <h3>Cần có Chiến lược trước</h3>
        <p class="muted">Thông điệp là bản dịch chiến lược ra "tiếng khách". Hãy lập + chốt Chiến lược trước.</p>
        <div class="empty-actions"><a class="primary-btn" href="#strategy">🎯 Tới bước Lập chiến lược</a></div></div></section>`;
    }
    if (!msgHas() && !_msg) {
      return `<section class="card"><div class="empty-cta"><div class="empty-ic">🏛️</div>
        <h3>Chưa có Thông điệp</h3>
        <p class="muted">Max rút từ Chiến lược thành câu chữ nói với khách — <b>cốt lõi</b> + các <b>trụ</b> (lãnh địa nói) + <b>giọng</b>. Bạn chỉnh rồi chốt; mọi bài sẽ bám theo.</p>
        <input id="msgSteer" class="occ-inp" style="max-width:480px;margin:0 auto 12px" placeholder="(tuỳ chọn) định hướng: vd nhấn cảm xúc hơn, giọng trẻ…">
        <div class="empty-actions"><button class="primary-btn" data-act="msg-gen">🏛️ Để Max nháp Thông điệp từ chiến lược</button></div></div></section>`;
    }
    const S = msgState();
    const tagline = (S.taglines || []).length
      ? `<div class="msg-taglines">${S.taglines.map(t => `<span class="msg-tag">“${E(t)}”</span>`).join('')}</div>` : '';
    const pillars = (S.pillars || []).map((p, i) => `
      <div class="msg-pillar">
        <input class="msg-ic" data-msgp="icon" data-idx="${i}" value="${E(p.icon)}" maxlength="3" title="emoji">
        <div class="msg-pillar-body">
          <input class="msg-terr" data-msgp="territory" data-idx="${i}" value="${E(p.territory)}" placeholder="Lãnh địa (vd: Sống đẹp nhà nhỏ)">
          <input class="msg-angle" data-msgp="angle" data-idx="${i}" value="${E(p.angle)}" placeholder="Góc nói / quan điểm trong lãnh địa này">
          <input class="msg-proof" data-msgp="proof" data-idx="${i}" value="${E(p.proof)}" placeholder="Proof — chỉ khi có thật (để trống nếu không)">
        </div>
        <button class="msg-rm" data-act="msg-pillar-remove" data-idx="${i}" title="Bớt trụ">✕</button>
      </div>`).join('');
    return `
      <div class="dir-banner" style="margin-bottom:14px">🏛️ Max nháp từ Chiến lược → bạn chỉnh từng ô cho "ra chất mình" → <b>Chốt</b>. Mọi bài (móng + đợt) sẽ tự bám cốt lõi + giọng này.</div>
      <section class="card msg-card">
        <label class="msg-lbl">🏠 CỐT LÕI <span class="muted">(1 điều bao trùm khách phải nhớ)</span></label>
        <input class="msg-core" data-msgfield="core" value="${E(S.core)}" placeholder="vd: Tường nhà kể chuyện của bạn">
        ${tagline}
      </section>
      <section class="card msg-card">
        <label class="msg-lbl">🏛️ TRỤ THÔNG ĐIỆP <span class="muted">(lãnh địa mình "đóng cọc" để nói — linh hoạt 2–5)</span></label>
        <div class="msg-pillars">${pillars || '<p class="muted">—</p>'}</div>
        <button class="ghost-line sm" data-act="msg-pillar-add" style="margin-top:8px">＋ thêm trụ</button>
      </section>
      <section class="card msg-card">
        <label class="msg-lbl">🎙️ GIỌNG <span class="muted">(mỗi dòng 1 ý)</span></label>
        <div class="msg-voice">
          <div><span class="msg-voice-h ok">✅ Nên</span><textarea class="msg-ta" data-msgfield="do" rows="4" placeholder="mỗi dòng 1 ý">${E((S.voice.do || []).join('\n'))}</textarea></div>
          <div><span class="msg-voice-h no">❌ Tránh</span><textarea class="msg-ta" data-msgfield="dont" rows="4" placeholder="mỗi dòng 1 ý">${E((S.voice.dont || []).join('\n'))}</textarea></div>
        </div>
      </section>`;
  }
  function rerenderMsg() { const w = document.getElementById('msgWrap'); if (w) w.innerHTML = msgInner(); }
  // Dải tóm tắt "đang nói gì với khách" — hiện trên Lập chiến dịch / Lịch, bấm sang #message.
  function messagingBand() {
    const m = (window.MOCK && M.bizMessaging) || {};
    if (!m.core && !(m.pillars || []).length) {
      return `<a class="msg-band msg-band-empty clickable" href="#message">🏛️ <b>Chưa có Thông điệp</b> — bấm để Max nháp "nói gì với khách" (mọi bài sẽ bám theo) →</a>`;
    }
    const E = s => (s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    const ps = (m.pillars || []).slice(0, 4).map(p => `${p.icon || ''} ${E(p.territory)}`).join(' · ');
    return `<a class="msg-band clickable" href="#message">🏛️ <b>Đang nói:</b> "${E(m.core || '—')}"${ps ? ` · <span class="muted">${ps}</span>` : ''} <span class="msg-band-edit">✎ chỉnh</span></a>`;
  }

  /* ---- Content generator ---- */
  // M3.1 (hybrid): "Trình tạo nội dung", "Kịch bản video", "UGC Brief" đã GỠ khỏi trang riêng.
  // Bài gốc tạo trong Lịch nội dung; video/UGC/đa-kênh là biến thể phái sinh ngay trên 1 bài
  // (modal "⚡ Tạo bài" → 📱/🎬/📸). Xem docs/web/slices/M3-content-suite.md.

  /* ---- Ads copy ---- */
  // M3.2 (hybrid): trang đặc thù sinh THẬT bám strategy/USP (lưu vào Tài liệu) — KHÔNG mock.
  function assetPage(kind, o) {
    return {
      title: o.title, sub: o.sub,
      actions: `<button class="primary-btn" data-act="gen-asset" data-kind="${kind}" data-title="${o.title}">${o.cta}</button>`,
      render: () => `
        <section class="grid">
          ${card(o.title, `
            <p class="muted" style="margin:0 0 12px">${o.desc}</p>
            <ul class="bullet" style="margin:0 0 14px">${o.points.map(p=>`<li>${p}</li>`).join('')}</ul>
            <button class="primary-btn full" data-act="gen-asset" data-kind="${kind}" data-title="${o.title}">${o.cta}</button>
            <p class="muted" style="margin:12px 0 0;font-size:13px">Max bám hồ sơ + chiến lược tổng hợp của bạn. Bản tạo lưu vào <b>Tài liệu</b> để xem/sửa lại.</p>
          `, {cls:'span-7'})}
          ${card('Cần gì để chuẩn?', `
            <ul class="bullet"><li>✅ Hồ sơ doanh nghiệp (ngành, sản phẩm, USP, khách mục tiêu)</li>
            <li>✨ Tốt hơn nếu đã chạy <b>Chiến lược tổng hợp</b> — copy bám đúng định vị & đối tượng</li></ul>
            <a class="ghost-line full" href="#strategy" style="margin-top:12px">→ Xem/chạy Chiến lược</a>`, {cls:'span-5'})}
        </section>`,
      mount: () => {},
    };
  }
  P.adscopy = assetPage('ads_copy', {
    title: 'Quảng cáo (copy)', sub: 'Theo phễu TOFU / MOFU / BOFU', cta: '⚡ Viết bộ copy theo phễu',
    desc: 'Sinh bộ ads copy 3 tầng phễu — bám USP, định vị và khách mục tiêu thật của bạn.',
    points: ['🎯 <b>TOFU</b> — hook nhận biết, đánh nỗi đau/khao khát',
             '🤝 <b>MOFU</b> — chứng minh giá trị, khác biệt USP, social proof',
             '💰 <b>BOFU</b> — offer rõ, CTA mạnh, khử rủi ro + gợi ý đối tượng nhắm'],
  });
  P.inbox = assetPage('inbox', {
    title: 'Sales Inbox Script', sub: 'Kịch bản chat Messenger / Zalo / IG — xử lý từ chối', cta: '⚡ Tạo kịch bản inbox',
    desc: 'Sinh kịch bản chat bán hàng cho các tình huống thường gặp — công nhận → giá trị/USP → chốt nhẹ.',
    points: ['💸 Chê đắt · ⏰ Để suy nghĩ · 🤔 So sánh đối thủ · 📍 Ở xa/giao hàng',
             '🗣️ Giọng thân thiện, chuyên nghiệp, bám sản phẩm thật'],
  });
  P.sequence = assetPage('sequence', {
    title: 'Email / Zalo chuỗi', sub: 'Nurture cho lead / khách / winback', cta: '⚡ Tạo chuỗi Email/Zalo',
    desc: 'Sinh chuỗi nurture 4-6 bước cho lead/khách mới — đi từ welcome → trao giá trị → social proof → offer.',
    points: ['📬 Mỗi bước: thời điểm gửi, mục tiêu, tiêu đề, nội dung ngắn, CTA',
             '🔁 Kết hợp tốt với <b>Giữ khách</b> (retention) để winback khách cũ'],
  });

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
  // N-06: banner trạng thái tác vụ toàn cục (đang chạy / lỗi) — hiện trên mọi trang, tự cập nhật qua SSE.
  let _jobDismiss = {};
  function jobBanner() {
    const E = s => (s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    const jobs = M.agentJobs || [];
    const run = jobs.find(j => j.status === 'running');
    if (run) return `<div class="job-banner job-run"><span class="job-spin"></span><b>${E(run.label || 'Agent đang chạy')}</b>${run.progress ? ` — <span class="muted">${E(run.progress)}</span>` : ''}</div>`;
    const err = jobs.find(j => j.status === 'error' && j.error && !_jobDismiss[j.id]);
    if (err) return `<div class="job-banner job-err">⚠️ <b>${E(err.label || 'Tác vụ lỗi')}</b> — ${E(err.error)}<button class="icon-btn job-x" data-act="job-dismiss" data-id="${err.id}">✕</button></div>`;
    return '';
  }
  function route() {
    const raw = (location.hash.replace('#','') || 'dossier');
    const [seg0, seg1] = raw.split('/');
    let id = seg0;
    // pivot: bỏ Max chat → mọi thứ bắt đầu từ Hồ sơ doanh nghiệp
    if (id === 'pipeline' || id === 'agents' || id === 'home' || id === 'chat') id = 'dossier';
    if (id === 'brief') id = 'occasion';   // gỡ trang Campaign Brief mock → hub Lập chiến dịch thật
    if (id === 'content' || id === 'video' || id === 'ugc') id = 'calendar';   // M3.1: gộp vào Lịch (bài + biến thể)
    if (id === 'doc') _docId = seg1 || null;                    // trang đọc output: #doc/<id>
    const page = P[id] || P.dossier;
    killCharts();
    renderSidebar(id);
    document.body.classList.remove('chat-mode');
    const actions = page.actions || '';
    document.getElementById('view').innerHTML =
      jobBanner() + pageHead(page.title, page.sub, actions) + page.render();
    if (page.mount) page.mount();
    fillDocEmbeds();   // nhúng trình đọc/sửa text vào trang chi tiết (demo + thật)
    fillSkillRunSlots();   // nạp nội dung slot .ai-output[data-skill-run] (synthesis collapsible)
    injectPageNav(id);     // nút chuyển tab trước/sau cho chuỗi phân tích
    // N-10: cuộn lên đầu khi chuyển trang — reset mọi vùng cuộn có thể (main / window / view)
    try { document.querySelector('.main').scrollTo(0,0); } catch (e) {}
    try { window.scrollTo(0,0); } catch (e) {}
    { const _v = document.getElementById('view'); if (_v) _v.scrollTop = 0; }
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
  // nhãn tiếng Việt cho tiêu đề Tài liệu (content skills sinh từ Lịch/trang đặc thù)
  const SKILL_VI = { calendar_post:'Bài đăng (lịch)', post_channels:'Biến thể đa kênh',
    video_script:'Kịch bản video', ugc_brief:'UGC brief', ads_copy:'Quảng cáo (copy theo phễu)',
    email_zalo_sequence:'Chuỗi Email/Zalo', sales_inbox_script:'Kịch bản Sales Inbox',
    content_feedback:'📊 Đo hiệu quả & tối ưu' };
  const skillVi = (s) => SKILL_VI[s] || s;
  let _modalRun = null;
  let _postBase = null;   // M3.1: bài gốc đang mở (để bung biến thể / quay lại)
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
    } else if (meta && meta.derive) {
      // M3.1: bài gốc trong Lịch → bung biến thể phái sinh (đa kênh/video/UGC)
      foot.style.display = 'flex';
      foot.innerHTML = `
        <div class="rate-group"><span class="muted">Bung biến thể:</span>
          <button class="ghost-line sm" data-act="post-derive" data-kind="channels">📱 Đa kênh</button>
          <button class="ghost-line sm" data-act="post-derive" data-kind="video">🎬 Video</button>
          <button class="ghost-line sm" data-act="post-derive" data-kind="ugc">📸 UGC brief</button>
        </div>
        <div class="modal-foot-r"><button class="ghost-line sm" data-act="copy-skillrun">📋 Copy</button></div>`;
    } else if (meta && meta.back) {
      // M3.1: kết quả biến thể → quay lại bài gốc
      foot.style.display = 'flex';
      foot.innerHTML = `
        <div class="rate-group"><button class="ghost-line sm" data-act="post-back">← Bài gốc</button></div>
        <div class="modal-foot-r"><button class="ghost-line sm" data-act="copy-skillrun">📋 Copy</button></div>`;
    } else if (meta && (meta.copy || meta.run)) {
      // M3.2: kết quả tài sản content (đã lưu Tài liệu) → chỉ cần Copy
      foot.style.display = 'flex';
      foot.innerHTML = `<div class="rate-group"><span class="muted">Đã lưu vào Tài liệu</span></div>
        <div class="modal-foot-r"><button class="ghost-line sm" data-act="copy-skillrun">📋 Copy</button></div>`;
    } else { foot.style.display = 'none'; foot.innerHTML = ''; }
    ov.classList.add('show');
  }

  // ── Lịch: thẻ tương tác — chọn 💡 chủ đề → tạo bài → duyệt ──
  let _slotCtx = null;
  // M-E: payload ref+place gửi khi lưu/bỏ bài (key ổn định tính ở backend).
  function _slotSaveRef() {
    const s = _slotCtx || {};
    return { slot_key: s.key || '', track: s.track || 'always',
             pillar_id: s.pillarId || '', campaign_id: s.campaignId || '',
             phase: s.phase || '', week: s.week, day: s.day };
  }
  const _DAYNAMES = ['T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'CN'];
  function _ensureBizModal() { showModal('', '', null); return document.getElementById('bizModal'); }
  // M-D Pha 2: 2 trục soạn bài — Góc khai thác (value lens) × Cách mở (hook style)
  const VALUE_LENSES = ['Nỗi đau/Vấn đề', 'Kết quả/Lợi ích', 'Bằng chứng xã hội', 'Khát vọng/Định vị',
    'Xử lý phản đối', 'Cơ chế/USP', 'Khẩn cấp', 'Uy tín chuyên môn'];
  const HOOK_STYLES = ['Tự động', 'Tò mò', 'Trái ngược', 'Cảm xúc', 'Góc nhìn chuyên gia', 'Đồng cảm'];
  const _slotWhen = (slot) => (slot.day != null && slot.week)
    ? `${_DAYNAMES[slot.day] || ('Ngày ' + (slot.day + 1))} · Tuần ${slot.week}` : 'Bài Always-on';
  function openSlotModal(slot) {
    _slotCtx = slot;
    // Đã duyệt trước đó → mở thẳng bài đã lưu (xem/sửa), không bắt chọn lại chủ đề.
    if (slot.saved && slot.post) { _ensureBizModal(); showSlotResult(slot.post, null, true); return; }
    const E = s => (s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    const ov = _ensureBizModal();
    const angles = (slot.angles && slot.angles.length) ? slot.angles : [slot.title].filter(Boolean);
    ov.querySelector('h3').textContent = `${_slotWhen(slot)} — ${slot.pillar || 'Always-on'}`;
    const lensDef = slot.value_lens || '';
    const lensList = VALUE_LENSES.includes(lensDef) || !lensDef ? VALUE_LENSES : [lensDef, ...VALUE_LENSES];
    // Pha 1: chủ đề = ô text sửa được (điền sẵn topic cụ thể), kèm chip gợi ý; góc khai thác = kế thừa từ trụ.
    const topicDef = slot.topic || (angles[0] || slot.title || '');
    const angleLens = slot.angleLens || [];
    ov.querySelector('.modal-body').innerHTML = `
      <p class="muted" style="margin:0 0 8px"><b>💡 Chủ đề</b> bài này (sửa thoải mái) — Max viết theo:</p>
      <input id="slotTopic" class="slot-topic" value="${E(topicDef)}" placeholder="vd: 3 sai lầm khi chọn nhà cung cấp khiến mất tiền oan">
      ${angles.length ? `<div class="topic-chips">${angles.map((a, i) =>
        `<button class="topic-chip" data-act="topic-pick" data-topic="${encodeURIComponent(a)}" data-lens="${encodeURIComponent(angleLens[i] || '')}">${E(a)}</button>`).join('')}</div>` : ''}
      <div class="slot-axes">
        <label class="slot-axis"><span>Góc khai thác <small class="muted">· kế thừa từ trụ</small></span>
          <select id="slotLens">${lensList.map(l => `<option ${l === lensDef ? 'selected' : ''}>${E(l)}</option>`).join('')}</select></label>
        <label class="slot-axis"><span>Cách mở (hook)</span>
          <select id="slotHook">${HOOK_STYLES.map(h => `<option>${E(h)}</option>`).join('')}</select></label>
      </div>`;
    const foot = ov.querySelector('.modal-foot'); foot.style.display = 'flex';
    foot.innerHTML = `<div class="rate-group"><span class="muted">${E(slot.pillar || '')}${slot.funnel ? ' · ' + E(slot.funnel) : ''}</span></div>
      <div class="modal-foot-r"><button class="primary-btn sm" data-act="slot-gen">⚡ Tạo bài</button></div>`;
    ov.classList.add('show');
  }
  // Khung TEXT sửa được (t2) + Lưu & Duyệt ngay tại ô (t1). wasSaved=đang xem bài đã lưu.
  function showSlotResult(content, runId, wasSaved) {
    const ov = document.getElementById('bizModal'); if (!ov || !_slotCtx) return;
    const E = s => (s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    _modalRun = { run: true, title: '', content, id: runId };
    ov.querySelector('h3').textContent = `${_slotWhen(_slotCtx)} — ${_slotCtx.pillar || 'Always-on'}${wasSaved ? ' · ✓ đã duyệt' : ''}`;
    ov.querySelector('.modal-body').innerHTML =
      `<p class="muted" style="margin:0 0 8px">Sửa trực tiếp rồi <b>Lưu & Duyệt</b> — bài sẽ ghim tại ô này.</p>
       <textarea class="slot-edit" id="slotEditBox" rows="14">${E(content)}</textarea>`;
    const foot = ov.querySelector('.modal-foot'); foot.style.display = 'flex';
    foot.innerHTML = `
      <div class="rate-group">
        <button class="ghost-line sm" data-act="slot-back">← Đổi chủ đề</button>
        <button class="ghost-line sm" data-act="slot-gen">↻ Tạo lại</button>
        ${wasSaved ? '<button class="ghost-line sm" data-act="slot-unsave">🗑 Bỏ bài</button>' : ''}
      </div>
      <div class="modal-foot-r">
        <button class="ghost-line sm" data-act="slot-copy">📋 Copy</button>
        <button class="primary-btn sm" data-act="slot-save">💾 Lưu &amp; Duyệt</button>
      </div>`;
  }

  /* ── M1.1 (D-043/044): Wizard tạo Campaign Occasion (chốt SMART thật) ── */
  // D-044: "mục đích đợt" = trục WHY (định hình brief), KHÁC trục WHEN. Founder chọn; trống = Max tự suy.
  // Pha2b: bộ mục đích master 6 (thêm leadgen + engagement; brand đổi nhãn ra-mắt; retention gộp winback)
  const OCC_OBJECTIVES = [
    { k: 'acquisition', ic: '🧲', label: 'Kéo khách mới',        desc: 'demand-gen · reach · lead' },
    { k: 'conversion',  ic: '💰', label: 'Chốt đơn',             desc: 'activation · ROAS/CPA · offer mạnh' },
    { k: 'leadgen',     ic: '📞', label: 'Thu lead / đặt tư vấn', desc: 'form · booking · lịch hẹn · demo' },
    { k: 'brand',       ic: '📣', label: 'Ra mắt / phủ nhận biết', desc: 'launch · phủ tệp mới · nhớ thương hiệu' },
    { k: 'engagement',  ic: '✨', label: 'Tương tác & lan toả',  desc: 'UGC · minigame · share · viral' },
    { k: 'retention',   ic: '🔁', label: 'Giữ & kéo lại khách',  desc: 'repeat · AOV/CLV · winback · loyalty' },
  ];
  // Pha2b: lọc "thu gọn" theo archetype ngành — mục hợp hiện nổi bật, còn lại gom dưới "Mục đích khác".
  const ARCHETYPE_PRIMARY_OBJ = {
    impulse:        ['conversion', 'engagement', 'acquisition'],
    demand_gen:     ['engagement', 'acquisition', 'conversion'],
    trust_building: ['leadgen', 'brand', 'retention'],
  };
  let _occState = { occasion: '', ws: '', we: '', budget: '', baseline: '', goal: '', objective: '', objectiveCustom: '', campaignType: '', campaignTypeCustom: '', dang: '', audience: '', brief: '', busy: false };

  // M-F (F1b): modal chi tiết campaign — bảng task móc generator + status.
  let _campDetailId = null;
  const _TASK_STATUS = { todo: ['Chưa làm', ''], draft: ['Bản nháp', 'st-draft'], approved: ['✓ Đã duyệt', 'st-ok'] };
  function openCampDetail(cid) {
    _campDetailId = cid;
    const ov = _ensureBizModal();
    renderCampDetail();
    ov.classList.add('show');
  }
  function renderCampDetail() {
    const ov = document.getElementById('bizModal'); if (!ov || _campDetailId == null) return;
    const E = s => (s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    const meta = ((window.MOCK && window.MOCK.bizCampaignMeta) || {})[String(_campDetailId)];
    const camp = (calPlan().campaigns || []).find(c => String(c.campaignId) === String(_campDetailId)) || {};
    const cname = camp.name || (meta && meta.type_label) || 'Chiến dịch';
    ov.querySelector('h3').textContent = `${meta ? (meta.type_icon + ' ') : '🔴 '}${cname}`;
    // M-G: header phụ — branding xuyên suốt + link brief
    const briefRid = meta && (meta.brief_run_id);
    const hdr = (meta && meta.persistent ? '<span class="muted">🟢 Chạy liên tục (nền) · không deadline</span> · ' : '')
      + (briefRid ? `<button class="ghost-line sm" data-act="camptask-view" data-run="${briefRid}">📄 Xem brief</button>` : '');
    let bodyHtml;
    if (!meta || !(meta.tasks || []).length) {
      bodyHtml = `<p class="muted">Chiến dịch này chưa gắn <b>loại</b> nên chưa có việc cần làm. Tạo lại chiến dịch và chọn loại ở bước 1 để Max liệt kê task.</p>`;
    } else {
      const card = (t) => {
        const act = t.is_action
          ? `<button class="ghost-line sm" data-act="camptask-gen" data-task="${t.id}">${t.run_id ? '↻ Brief lại' : '🔧 Hướng dẫn'}</button>`
          : `<button class="ghost-line sm" data-act="camptask-gen" data-task="${t.id}">${t.run_id ? '↻ Tạo lại' : '✍️ Tạo'}</button>`;
        const view = t.run_id ? `<button class="ghost-line sm" data-act="camptask-view" data-run="${t.run_id}">Xem</button>` : '';
        const appr = (t.run_id && t.status !== 'approved') ? `<button class="ghost-line sm" data-act="camptask-approve" data-task="${t.id}">Duyệt</button>` : '';
        return `<div class="kb-card">
          <div class="kb-card-t">${t.is_action ? '🔧' : '✍️'} ${E(t.label)}</div>
          <div class="camptask-acts">${act}${view}${appr}</div></div>`;
      };
      const cols = [['todo', '📋 Chưa làm'], ['draft', '✏️ Bản nháp'], ['approved', '✓ Đã duyệt']];
      const kb = cols.map(([k, lbl]) => {
        const ts = meta.tasks.filter(t => (t.status || 'todo') === k);
        return `<div class="kb-col"><div class="kb-h">${lbl} <span class="muted">${ts.length}</span></div>
          ${ts.map(card).join('') || '<div class="kb-empty muted">—</div>'}</div>`;
      }).join('');
      bodyHtml = `${hdr ? '<p class="muted" style="margin:0 0 8px">' + hdr + '</p>' : ''}<p class="muted" style="margin:0 0 10px">${meta.audience ? '🎯 Tệp nhắm: <b>' + E(meta.audience) + '</b> · ' : ''}✍️ Max tạo nội dung · 🔧 việc người làm (Max ra hướng dẫn).</p>
        <div class="kanban">${kb}</div>`;
    }
    ov.querySelector('.modal-body').innerHTML = bodyHtml;
    const foot = ov.querySelector('.modal-foot'); if (foot) { foot.style.display = 'none'; foot.innerHTML = ''; }
  }

  // Reset để test — 2 mức (giữ hồ sơ / xoá sạch).
  function openResetModal() {
    const ov = _ensureBizModal();
    ov.querySelector('h3').textContent = '🧹 Reset để test lại';
    ov.querySelector('.modal-body').innerHTML = `
      <p class="muted" style="margin:0 0 12px">Xoá dữ liệu để chạy thử lại từ đầu. <b>Không hoàn tác được.</b></p>
      <div class="reset-opt"><b>① Giữ hồ sơ — reset kết quả</b>
        <div class="muted">Giữ thông tin doanh nghiệp + câu trả lời. Xoá: phân tích (T1-T3), chiến lược, pillars, lịch, bài đã lưu, chiến dịch, danh mục.</div>
        <button class="primary-btn sm" data-act="biz-reset-go" data-full="0" style="margin-top:8px">Reset (giữ hồ sơ)</button></div>
      <div class="reset-opt" style="margin-top:14px"><b>② Xoá sạch</b>
        <div class="muted">Xoá HẲN cả hồ sơ — về trắng, làm lại từ bước nhập liệu (intake).</div>
        <button class="ghost-line sm" data-act="biz-reset-go" data-full="1" style="margin-top:8px">Xoá sạch tất cả</button></div>`;
    const foot = ov.querySelector('.modal-foot'); if (foot) { foot.style.display = 'none'; foot.innerHTML = ''; }
    ov.classList.add('show');
  }
  // M-F (F2): danh mục chiến dịch — Max đề xuất từ roadmap, founder duyệt → tạo từng cái.
  function openPortfolio() { _ensureBizModal(); renderPortfolio(); document.getElementById('bizModal').classList.add('show'); }
  function renderPortfolio() {
    const ov = document.getElementById('bizModal'); if (!ov) return;
    const E = s => (s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    const list = (window.MOCK && window.MOCK.bizCampaignPortfolio) || [];
    ov.querySelector('h3').textContent = '🗓️ Gợi ý lịch các đợt (từ Chiến lược)';
    const cards = list.map((c, i) => `
      <div class="pf-card">
        <div class="pf-main"><b>${c.type_icon || '🔴'} ${E(c.name)}</b>
          <span class="pf-meta">${E(c.type_label || '')} · Tuần ${c.start_week} · ${c.window_weeks} tuần · 🎯 ${E(c.audience || 'Tất cả')}</span>
          <div class="muted pf-why">${E(c.why || '')}</div></div>
        <div class="pf-acts">
          <button class="primary-btn sm" data-act="pf-make" data-idx="${i}">Tạo chiến dịch →</button>
          <button class="ghost-line sm" data-act="pf-drop" data-idx="${i}">✕</button></div>
      </div>`).join('');
    ov.querySelector('.modal-body').innerHTML = list.length
      ? `<p class="muted" style="margin:0 0 10px">Max gợi ý <b>nên chạy đợt gì vào lúc nào</b> — đi từ roadmap Chiến lược ra kế hoạch. Duyệt cái nào thì <b>Tạo đợt</b> (mở wizard điền sẵn), bỏ cái không hợp.</p>${cards}`
      : `<p class="muted">Chưa có gợi ý. Bấm <b>✨ Gợi ý lịch các đợt</b> để Max suy từ roadmap Chiến lược.</p>`;
    const foot = ov.querySelector('.modal-foot'); if (foot) {
      foot.style.display = 'flex';
      foot.innerHTML = `<div class="rate-group"><span class="muted">${list.length} đợt</span></div>
        <div class="modal-foot-r"><button class="primary-btn sm" data-act="pf-gen">${list.length ? '↻ Gợi ý lại' : '✨ Gợi ý lịch các đợt'}</button></div>`;
    }
  }
  // D-044b: ví dụ chỉ tiêu khác nhau theo mục đích đã chọn — tránh nhầm "mục đích" với "mục tiêu"
  const OCC_GOAL_EX = {
    acquisition: 'vd: 300 lead mới, reach 50.000',
    conversion:  'vd: 500 đơn, doanh thu 150 triệu',
    leadgen:     'vd: 200 lead, 50 lịch hẹn tư vấn',
    brand:       'vd: 100.000 reach/impression, 5.000 follow mới',
    engagement:  'vd: 2.000 lượt tương tác, 500 lượt share, 300 người chơi minigame',
    retention:   'vd: 200 đơn khách cũ quay lại, CLV +10%',
  };
  function _occGoalPlaceholder(obj) {
    return (OCC_GOAL_EX[obj] || 'vd: 500 đơn, 50 triệu doanh thu, 300 lead') + ' — để trống = theo giai đoạn roadmap';
  }

  const _occTypeByKey = (k) => ((window.MOCK && window.MOCK.bizCampaignTypes) || []).find(t => t.key === k) || null;
  function openOccasionWizard(preset) {
    const _pp = (preset && typeof preset === 'object') ? preset : { occasion: preset || '' };
    _occState = { occasion: _pp.occasion || '', ws: _pp.ws || '', we: _pp.we || '', budget: '', baseline: '', goal: '', objective: _pp.objective || '', objectiveCustom: '', campaignType: _pp.campaignType || '', campaignTypeCustom: '', dang: _pp.dang || '', audience: _pp.audience || '', brief: '', busy: false };
    let ov = document.getElementById('occWizard');
    if (!ov) {
      ov = document.createElement('div');
      ov.id = 'occWizard'; ov.className = 'modal-ov';
      ov.innerHTML = `<div class="modal"><div class="modal-head"><h3>Tạo chiến dịch theo dịp</h3>
        <button class="icon-btn" data-act="occ-close">✕</button></div>
        <div class="modal-body" id="occBody"></div></div>`;
      document.body.appendChild(ov);
      ov.addEventListener('click', (e) => { if (e.target === ov) ov.classList.remove('show'); });
      // bắt input động trong wizard (lưu state, không re-render để giữ con trỏ)
      ov.addEventListener('input', (e) => {
        const k = e.target.dataset.occfield; if (!k) return;
        _occState[k] = e.target.value;
        // Pha2b: tự điền mục đích & nút chọn loại trừ nhau — gõ tự điền thì bỏ chọn nút.
        if (k === 'objectiveCustom' && (e.target.value || '').trim()) {
          _occState.objective = '';
          ov.querySelectorAll('[data-act="occ-obj"]').forEach(c => c.classList.remove('on'));
        }
        // M-F: tự mô tả loại campaign → bỏ chọn loại có sẵn.
        if (k === 'campaignTypeCustom' && (e.target.value || '').trim()) {
          _occState.campaignType = '';
          ov.querySelectorAll('[data-act="occ-type"]').forEach(c => c.classList.remove('on'));
        }
      });
      ov.addEventListener('click', (e) => {
        const chip = e.target.closest('[data-act="occ-chip"]');
        if (chip) {
          _occState.occasion = chip.dataset.occ || '';
          const inp = document.getElementById('occName'); if (inp) inp.value = _occState.occasion;
          ov.querySelectorAll('[data-act="occ-chip"]').forEach(c => c.classList.toggle('on', c === chip));
          return;
        }
        const dbtn = e.target.closest('[data-act="occ-dang"]');
        if (dbtn) {   // Tầng ③: chọn DẠNG chủ đạo → set campaign_type/objective ngầm; chọn lại = bỏ
          const dk = dbtn.dataset.dang;
          if (_occState.dang === dk) { _occState.dang = ''; _occState.campaignType = ''; }
          else {
            _occState.dang = dk;
            _occState.campaignType = dbtn.dataset.type || '';
            _occState.objective = dbtn.dataset.obj || _occState.objective;
            _occState.campaignTypeCustom = '';
          }
          renderOccWizard();
          return;
        }
        const tbtn = e.target.closest('[data-act="occ-type"]');
        if (tbtn) {   // (cũ) chọn loại campaign — giữ tương thích
          const k = tbtn.dataset.type;
          if (_occState.campaignType === k) { _occState.campaignType = ''; }
          else { _occState.campaignType = k; _occState.objective = tbtn.dataset.obj || _occState.objective; _occState.campaignTypeCustom = ''; }
          renderOccWizard();
          return;
        }
        const more = e.target.closest('[data-act="occ-more"]');
        if (more) {   // bung/thu "Mục đích khác"
          const box = ov.querySelector('#occObjMore');
          if (box) { const open = box.style.display !== 'none'; box.style.display = open ? 'none' : ''; more.classList.toggle('on', !open); }
          return;
        }
        const obj = e.target.closest('[data-act="occ-obj"]');
        if (obj) {   // toggle mục đích (chọn lại = bỏ → Max tự suy); chọn nút thì xoá ô tự điền
          const k = obj.dataset.obj;
          _occState.objective = (_occState.objective === k) ? '' : k;
          if (_occState.objective) {
            _occState.objectiveCustom = '';
            const ci = ov.querySelector('[data-occfield="objectiveCustom"]'); if (ci) ci.value = '';
          }
          ov.querySelectorAll('[data-act="occ-obj"]').forEach(c =>
            c.classList.toggle('on', c.dataset.obj === _occState.objective));
          const goalInp = ov.querySelector('[data-occfield="goal"]');
          if (goalInp) goalInp.placeholder = _occGoalPlaceholder(_occState.objective);
        }
      });
    }
    renderOccWizard();
    ov.classList.add('show');
  }

  function renderOccWizard() {
    const body = document.getElementById('occBody'); if (!body) return;
    const S = _occState;
    const E = s => (s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    if (S.brief) {   // Bước 3-4: review brief đã sinh
      const ct = _occTypeByKey(S.campaignType);
      const taskPrev = ct && ct.tasks && ct.tasks.length ? `
        <div class="occ-tasks-prev"><b>${ct.icon} ${E(ct.label)}</b> — đợt này sẽ cần (Max giúp tạo sau khi lưu):
          <ul>${ct.tasks.map(t => `<li>${t.is_action ? '🔧 ' : '✍️ '}${E(t.label)}</li>`).join('')}</ul></div>` : '';
      body.innerHTML = `
        <div class="dir-banner" style="margin-bottom:14px">✅ <b>Campaign Brief — ${E(S.occasion)}</b>.
          Mọi số là <b>gợi ý của Max</b> — bạn chốt lại được. Xem kỹ rồi lưu, hoặc quay lại chỉnh lever.</div>
        <div class="ai-output expanded">${renderAIContent(S.brief)}</div>
        ${taskPrev}
        <div class="occ-foot">
          <button class="ghost-line" data-act="occ-back">← Chỉnh lever</button>
          <button class="primary-btn" data-act="occ-save">💾 Lưu chiến dịch</button>
        </div>`;
      enhancePosMaps(body);
      return;
    }
    const chips = (_lastOccasions || []).map(o =>
      `<button class="occ-chip ${S.occasion === o.name ? 'on' : ''}" data-act="occ-chip" data-occ="${E(o.name)}">${E(o.name)}${o.when ? ` · ${E(o.when)}` : ''}</button>`).join('');
    // Pha2b: lọc "thu gọn" mục đích theo archetype ngành
    const objBtn = (o) => `
      <button class="occ-obj ${S.objective === o.k ? 'on' : ''}" data-act="occ-obj" data-obj="${o.k}">
        <span class="occ-obj-ic">${o.ic}</span>
        <span class="occ-obj-main"><b>${o.label}</b><small>${o.desc}</small></span>
      </button>`;
    const arche = (window.MOCK && window.MOCK.bizArchetype) || '';
    const primKeys = ARCHETYPE_PRIMARY_OBJ[arche] || OCC_OBJECTIVES.map(o => o.k);
    const primObjs = OCC_OBJECTIVES.filter(o => primKeys.includes(o.k));
    const moreObjs = OCC_OBJECTIVES.filter(o => !primKeys.includes(o.k));
    const customOn = !!(S.objectiveCustom || '').trim();
    const objSection = `
      <div class="occ-step"><label class="occ-lbl">3 · Mục đích đợt <span class="muted" style="font-weight:400">(định hình brief — trống thì Max tự suy)${arche ? ' · gợi ý hợp ngành bạn' : ''}</span></label>
        <div class="occ-objs">${primObjs.map(objBtn).join('')}</div>
        ${moreObjs.length ? `
          <button class="occ-more" data-act="occ-more">Mục đích khác ▾</button>
          <div id="occObjMore" class="occ-objs" style="display:none;margin-top:8px">${moreObjs.map(objBtn).join('')}</div>` : ''}
        <label class="occ-sublbl" style="margin-top:10px">…hoặc tự mô tả mục đích riêng</label>
        <input class="occ-inp ${customOn ? 'occ-custom-on' : ''}" data-occfield="objectiveCustom"
          placeholder="vd: tuyển 50 cộng tác viên bán hàng, gom data khách quan tâm khoá học…" value="${E(S.objectiveCustom)}">
      </div>`;
    // Tầng ③: chọn DẠNG nội dung chủ đạo (1 lớp). Mỗi dạng TỰ mang vai trò phễu; set campaign_type/objective ngầm.
    const dangs = (window.MOCK && window.MOCK.bizContentDang) || [];
    const dangBtn = (d) => `
      <button class="occ-type occ-dang ${S.dang === d.key ? 'on' : ''}" data-act="occ-dang" data-dang="${d.key}" data-type="${d.campaign_type}" data-obj="${d.objective}" data-role="${E(d.role_label)}" title="${E(d.desc)}">
        <span class="occ-obj-ic">${d.icon}</span><b>${E(d.label)}</b><span class="occ-dang-role">${E(d.role_label)}</span></button>`;
    const typeCustomOn = !!(S.campaignTypeCustom || '').trim();
    const typeSection = dangs.length ? `
      <div class="occ-step"><label class="occ-lbl">1 · Dạng nội dung chủ đạo <span class="muted" style="font-weight:400">(chọn 1 — Max trộn thêm dạng phụ theo arc; vai trò phễu tự có)</span></label>
        <div class="occ-types">${dangs.map(dangBtn).join('')}</div>
        <label class="occ-sublbl" style="margin-top:10px">…hoặc tự mô tả dạng riêng (Max tự dựng)</label>
        <input class="occ-inp ${typeCustomOn ? 'occ-custom-on' : ''}" data-occfield="campaignTypeCustom"
          placeholder="vd: tuyển cộng tác viên, tri ân đại lý…" value="${E(S.campaignTypeCustom)}">
        <label class="occ-sublbl" style="margin-top:10px">🎯 Tệp nhắm chính</label>
        <select class="occ-inp" data-occfield="audience">
          ${['', 'Mới', 'Active', 'Nguy cơ', 'VIP', 'Tất cả'].map(a => `<option value="${a}" ${S.audience === a ? 'selected' : ''}>${a || '— theo dạng (Max tự suy) —'}</option>`).join('')}
        </select>
      </div>` : '';
    body.innerHTML = `
      <div class="dir-banner" style="margin-bottom:14px">🧭 Đợt này <b>kế thừa Chiến lược + Playbook</b> (pre-fill). Chọn <b>mục tiêu</b> + <b>dịp</b> là Max viết được brief — <b>số liệu để sau cũng được</b>.</div>

      ${typeSection}

      <div class="occ-step"><label class="occ-lbl">2 · Chọn dịp</label>
        ${chips ? `<div class="occ-chips">${chips}</div>` : ''}
        <input id="occName" class="occ-inp" data-occfield="occasion" placeholder="vd: Tết Nguyên Đán, 20/10, Mừng khai trương…" value="${E(S.occasion)}">
      </div>

      <div class="occ-step"><label class="occ-lbl">3 · Thời gian chạy (window)</label>
        <div class="occ-row">
          <input type="date" class="occ-inp" data-occfield="ws" value="${E(S.ws)}">
          <span class="muted">→</span>
          <input type="date" class="occ-inp" data-occfield="we" value="${E(S.we)}">
        </div></div>

      <details class="occ-step occ-optnum">
        <summary class="occ-lbl" style="cursor:pointer">4 · Số liệu chốt SMART <span class="muted" style="font-weight:400">(tuỳ chọn — để trống thì Max tự suy theo mục tiêu + roadmap)</span></summary>
        <div style="margin-top:8px">
          <label class="occ-sublbl">Ngân sách đợt</label>
          <input class="occ-inp" data-occfield="budget" placeholder="vd: 30 triệu — để trống thì Max gợi ý" value="${E(S.budget)}">
          <label class="occ-sublbl">Baseline hiện tại (trước đợt)</label>
          <input class="occ-inp" data-occfield="baseline" placeholder="vd: 200 đơn/tháng, AOV 350k — chưa rõ thì để trống" value="${E(S.baseline)}">
          <label class="occ-sublbl">Chỉ tiêu cụ thể đợt này</label>
          <input class="occ-inp" data-occfield="goal" placeholder="${E(_occGoalPlaceholder(S.objective))}" value="${E(S.goal)}">
          <p class="muted occ-hint">Để trống = Max tự suy theo <b>mục tiêu</b> + giai đoạn roadmap, để dạng <b>khoảng + (ước tính)</b>.</p>
        </div>
      </details>

      <div class="occ-foot">
        <button class="ghost-line" data-act="occ-close">Huỷ</button>
        <button class="primary-btn" data-act="occ-gen" ${S.busy ? 'disabled' : ''}>${S.busy ? '⏳ Max đang lập brief…' : '✨ Max sinh Campaign Brief'}</button>
      </div>`;
  }

  async function occasionGenerate() {
    const S = _occState;
    if (!(S.occasion || '').trim()) { toast('Hãy chọn hoặc nhập dịp trước'); return; }
    S.busy = true; renderOccWizard();
    try {
      const r = await API.post('api/biz/occasion', {
        user_id: _bizUserId, occasion: S.occasion, window_start: S.ws, window_end: S.we,
        budget: S.budget, baseline: S.baseline, goal: S.goal, objective: S.objective,
        objective_custom: S.objectiveCustom, campaign_type: S.campaignType, audience: S.audience });
      const d = (r && r.draft) || {};
      S.busy = false;
      if (!d.brief) { renderOccWizard(); toast('Chưa lập được brief — cần có Chiến lược (T4) trước, hoặc thử lại.'); return; }
      S.brief = d.brief; renderOccWizard();
    } catch (e) { S.busy = false; renderOccWizard(); toast('Không lập được brief — thử lại sau.'); }
  }

  async function occasionSave() {
    const S = _occState;
    if (!S.brief) return;
    try {
      const r = await API.post('api/biz/occasion/save', {
        user_id: _bizUserId, occasion: S.occasion, window_start: S.ws, window_end: S.we,
        budget: S.budget, goal: S.goal, brief: S.brief, objective: S.objective,
        objective_custom: S.objectiveCustom, campaign_type: S.campaignType, audience: S.audience });
      if (r.error) { toast(r.error); return; }
      const ov = document.getElementById('occWizard'); if (ov) ov.classList.remove('show');
      toast('✅ Đã lưu chiến dịch theo dịp');
      await refreshBiz(); route();
    } catch (e) { toast('Không lưu được chiến dịch'); }
  }

  /* ── M2.1 (D-045): Wizard Retention/Winback — cẩm nang if-then, KHÔNG cần order data ── */
  const LIFE_MODES = {
    retention: { ic: '🔁', title: 'Cẩm nang giữ chân khách',
      sub: 'Tình huống khách (bạn tự nhìn ra) → nên làm gì → tin nhắn mẫu. Không cần dữ liệu đơn hàng.' },
    winback:   { ic: '↩️', title: 'Kéo khách cũ quay lại',
      sub: 'Khách đã lâu không mua → chuỗi chạm kéo về. Không cần dữ liệu đơn hàng.' },
  };
  let _lifeState = { mode: 'retention', cycle: '', channels: '', offer: '', brief: '', busy: false };

  function openLifecycleWizard(mode) {
    _lifeState = { mode: (LIFE_MODES[mode] ? mode : 'retention'), cycle: '', channels: '', offer: '', brief: '', busy: false };
    let ov = document.getElementById('lifeWizard');
    if (!ov) {
      ov = document.createElement('div');
      ov.id = 'lifeWizard'; ov.className = 'modal-ov';
      ov.innerHTML = `<div class="modal"><div class="modal-head"><h3></h3>
        <button class="icon-btn" data-act="life-close">✕</button></div>
        <div class="modal-body" id="lifeBody"></div></div>`;
      document.body.appendChild(ov);
      ov.addEventListener('click', (e) => { if (e.target === ov) ov.classList.remove('show'); });
      ov.addEventListener('input', (e) => {
        const k = e.target.dataset.lifefield; if (k) _lifeState[k] = e.target.value;
      });
    }
    ov.querySelector('h3').textContent = LIFE_MODES[_lifeState.mode].title;
    renderLifeWizard();
    ov.classList.add('show');
  }

  function renderLifeWizard() {
    const body = document.getElementById('lifeBody'); if (!body) return;
    const S = _lifeState, MD = LIFE_MODES[S.mode];
    const E = s => (s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    if (S.brief) {
      body.innerHTML = `
        <div class="dir-banner" style="margin-bottom:14px">✅ <b>${MD.ic} ${E(MD.title)}</b>.
          Đây là <b>cẩm nang</b> — bạn tự đối chiếu khách của mình rồi áp. Ngưỡng thời gian là <b>ước tính theo ngành</b>, chỉnh thoải mái.</div>
        <div class="ai-output expanded">${renderAIContent(S.brief)}</div>
        <div class="occ-foot">
          <button class="ghost-line" data-act="life-back">← Chỉnh lever</button>
          <button class="primary-btn" data-act="life-save">💾 Lưu cẩm nang</button>
        </div>`;
      enhancePosMaps(body);
      return;
    }
    body.innerHTML = `
      <div class="dir-banner" style="margin-bottom:14px">${MD.ic} ${E(MD.sub)}
        Kế thừa la bàn (Synthesis) + đặc thù ngành. Vài thông tin dưới đây giúp cẩm nang sát hơn — <b>để trống cũng được</b>.</div>
      <div class="occ-step"><label class="occ-lbl">Chu kỳ mua điển hình</label>
        <input class="occ-inp" data-lifefield="cycle" placeholder="vd: khách hay mua lại mỗi ~30 ngày (trống = Max suy theo ngành)" value="${E(S.cycle)}"></div>
      <div class="occ-step"><label class="occ-lbl">Kênh liên hệ đang có (owned)</label>
        <input class="occ-inp" data-lifefield="channels" placeholder="vd: Zalo OA, SMS, gọi điện, email…" value="${E(S.channels)}"></div>
      <div class="occ-step"><label class="occ-lbl">Ưu đãi loyalty sẵn có (nếu có)</label>
        <input class="occ-inp" data-lifefield="offer" placeholder="vd: tích 10 ly tặng 1, thẻ thành viên… (trống = Max gợi ý)" value="${E(S.offer)}">
        <p class="muted occ-hint">Max sẽ đưa bảng: <b>tình huống → hành động → kênh → tin nhắn mẫu</b> để bạn dùng ngay.</p></div>
      <div class="occ-foot">
        <button class="ghost-line" data-act="life-close">Huỷ</button>
        <button class="primary-btn" data-act="life-gen" ${S.busy ? 'disabled' : ''}>${S.busy ? '⏳ Max đang soạn cẩm nang…' : '✨ Max soạn cẩm nang'}</button>
      </div>`;
  }

  async function lifecycleGenerate() {
    const S = _lifeState;
    S.busy = true; renderLifeWizard();
    try {
      const r = await API.post('api/biz/retention', {
        user_id: _bizUserId, mode: S.mode, cycle: S.cycle, channels: S.channels, offer: S.offer });
      const d = (r && r.draft) || {};
      S.busy = false;
      if (!d.brief) { renderLifeWizard(); toast('Chưa soạn được — cần có Chiến lược (T4) trước, hoặc thử lại.'); return; }
      S.brief = d.brief; renderLifeWizard();
    } catch (e) { S.busy = false; renderLifeWizard(); toast('Không soạn được cẩm nang — thử lại sau.'); }
  }

  async function lifecycleSave() {
    const S = _lifeState;
    if (!S.brief) return;
    try {
      const r = await API.post('api/biz/retention/save', {
        user_id: _bizUserId, mode: S.mode, cycle: S.cycle, channels: S.channels, offer: S.offer, brief: S.brief });
      if (r.error) { toast(r.error); return; }
      const ov = document.getElementById('lifeWizard'); if (ov) ov.classList.remove('show');
      toast('✅ Đã lưu cẩm nang giữ chân khách');
      await refreshBiz(); route();
    } catch (e) { toast('Không lưu được cẩm nang'); }
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
    if (act === 'job-dismiss') { _jobDismiss[el.dataset.id] = true; route(); return; }   // N-06: tắt banner lỗi
    if (act === 'cal-view') { _calView = el.dataset.view; route(); return; }
    if (act === 'cal-open-week') { _calWeek = parseInt(el.dataset.week) || 1; _calView = 'week'; route(); return; }
    if (act === 'slot-open') {   // M-C: bấm thẻ lịch → chọn chủ đề
      if (!apiAvailable || !M.bizEnabled) { toast('Bật backend (Supabase + LLM) để tạo bài thật'); return; }
      try { openSlotModal(JSON.parse(decodeURIComponent(el.dataset.slot || '%7B%7D'))); }
      catch (e) { toast('Không mở được thẻ'); }
      return;
    }
    if (act === 'topic-pick') {   // Pha 1: bấm chip gợi ý → điền chủ đề + góc khai thác của chủ đề đó
      const box = document.getElementById('slotTopic');
      if (box) { try { box.value = decodeURIComponent(el.dataset.topic || ''); } catch (e) { box.value = el.dataset.topic || ''; } box.focus(); }
      let lens = ''; try { lens = decodeURIComponent(el.dataset.lens || ''); } catch (e) { lens = el.dataset.lens || ''; }
      const lensSel = document.getElementById('slotLens');
      if (lensSel && lens) { for (const o of lensSel.options) { if (o.value === lens) { lensSel.value = lens; break; } } }
      return;
    }
    if (act === 'slot-gen') {   // tạo bài từ chủ đề (ô text sửa được; gọi được cả khi "Tạo lại")
      const ov = document.getElementById('bizModal'); if (!ov || !_slotCtx) return;
      const angle = ((ov.querySelector('#slotTopic') || {}).value || '').trim()
        || _slotCtx.topic || _slotCtx.title || '';
      if (!angle) { toast('Nhập chủ đề bài'); return; }
      const value_lens = (ov.querySelector('#slotLens') || {}).value || _slotCtx.value_lens || '';
      const hook_style = (ov.querySelector('#slotHook') || {}).value || '';
      const orig = el.textContent; el.disabled = true; el.textContent = '⏳ Đang viết…';
      try {
        const r = await API.post('api/biz/calendar/gen', {
          user_id: _bizUserId, track: _slotCtx.track || 'always', pillar: _slotCtx.pillar || '',
          angle, value_lens, hook_style, framework: _slotCtx.framework || '',
          campaign_id: _slotCtx.campaignId || '', phase: _slotCtx.phase || '',
          week: _slotCtx.week || '', day: _slotCtx.day != null ? _slotCtx.day : '',
          campaign_gap: _slotCtx.campaign_gap || '', objective: _slotCtx.objective || '',
          track_role: _slotCtx.track_role || '' });
        if (r.error) { toast(r.error); el.disabled = false; el.textContent = orig; return; }
        showSlotResult(r.content, r.run_id); refreshBiz();
      } catch (e) { toast('Không tạo được bài — thử lại sau.'); el.disabled = false; el.textContent = orig; }
      return;
    }
    if (act === 'slot-back') { if (_slotCtx) { const s = { ..._slotCtx }; delete s.saved; delete s.post; openSlotModal(s); } return; }
    if (act === 'slot-copy') {
      const box = document.getElementById('slotEditBox');
      if (box) { try { await navigator.clipboard.writeText(box.value); toast('📋 Đã copy'); } catch (e) { toast('Không copy được'); } }
      return;
    }
    if (act === 'slot-save') {   // M-E: lưu & duyệt bài dưới dạng thẻ (ref ổn định + place)
      const box = document.getElementById('slotEditBox');
      const content = box ? box.value : '';
      if (!content.trim()) { toast('Bài trống'); return; }
      if (!_slotCtx || !_slotCtx.key) { toast('Thiếu thông tin ô'); return; }
      const orig = el.textContent; el.disabled = true; el.textContent = '⏳ Đang lưu…';
      try {
        const r = await API.post('api/biz/calendar/post-save', { user_id: _bizUserId, ..._slotSaveRef(), content });
        if (r.error) { toast(r.error); el.disabled = false; el.textContent = orig; return; }
        const ov = document.getElementById('bizModal'); if (ov) ov.classList.remove('show');
        toast('✓ Đã lưu & duyệt — ghim tại ô'); await refreshBiz(); route();
      } catch (e) { toast('Không lưu được — thử lại sau.'); el.disabled = false; el.textContent = orig; }
      return;
    }
    if (act === 'slot-unsave') {   // bỏ bài đã lưu → ô về trạng thái trống
      if (!_slotCtx || !_slotCtx.key) return;
      try {
        const r = await API.post('api/biz/calendar/post-save', { user_id: _bizUserId, ..._slotSaveRef(), delete: true });
        if (r.error) { toast(r.error); return; }
        const ov = document.getElementById('bizModal'); if (ov) ov.classList.remove('show');
        toast('Đã bỏ bài — ô về trạng thái gợi ý'); await refreshBiz(); route();
      } catch (e) { toast('Không bỏ được — thử lại sau.'); }
      return;
    }
    if (act === 'portfolio-open') { openPortfolio(); return; }
    if (act === 'pf-gen') {   // M-F (F2): Max đề xuất danh mục từ roadmap
      if (!apiAvailable || !M.bizEnabled) { toast('Bật backend để Max đề xuất'); return; }
      const orig = el.textContent; el.disabled = true; el.textContent = '⏳ Max đang suy danh mục…';
      try {
        const r = await API.post('api/biz/campaign/portfolio', { user_id: _bizUserId });
        if (r.error) { toast(r.error); el.disabled = false; el.textContent = orig; return; }
        await refreshBiz(); renderPortfolio(); toast(`✨ Đã đề xuất ${(r.campaigns||[]).length} chiến dịch`);
      } catch (e) { toast('Không đề xuất được — thử lại sau.'); el.disabled = false; el.textContent = orig; }
      return;
    }
    if (act === 'pf-drop') {   // bỏ 1 mục khỏi danh mục
      const idx = +el.dataset.idx;
      try {
        const r = await API.post('api/biz/campaign/portfolio-clear', { user_id: _bizUserId, index: idx });
        if (r.error) { toast(r.error); return; }
        await refreshBiz(); renderPortfolio();
      } catch (e) { toast('Không bỏ được'); }
      return;
    }
    if (act === 'pf-make') {   // tạo chiến dịch từ 1 mục → mở wizard điền sẵn
      const idx = +el.dataset.idx;
      const c = ((window.MOCK && window.MOCK.bizCampaignPortfolio) || [])[idx];
      if (!c) return;
      const ov = document.getElementById('bizModal'); if (ov) ov.classList.remove('show');
      openOccasionWizard({ occasion: c.name, campaignType: c.type, objective: c.objective,
        ws: c.ws, we: c.we, audience: c.audience });
      return;
    }
    if (act === 'camp-detail') {   // M-F (F1b): mở chi tiết campaign + bảng task
      const cid = el.dataset.campId || el.getAttribute('data-camp-id') || '';
      if (cid) openCampDetail(cid);
      return;
    }
    if (act === 'camptask-gen') {   // sinh deliverable / hướng dẫn cho 1 task
      if (!apiAvailable || !M.bizEnabled) { toast('Bật backend để Max tạo'); return; }
      const tid = el.dataset.task; if (!tid || _campDetailId == null) return;
      const orig = el.textContent; el.disabled = true; el.textContent = '⏳ Max đang làm…';
      try {
        const r = await API.post('api/biz/campaign/task-gen', { user_id: _bizUserId, campaign_id: _campDetailId, task_id: tid });
        if (r.error) { toast(r.error); el.disabled = false; el.textContent = orig; return; }
        await refreshBiz();
        showModal('✨ Kết quả deliverable', r.content, { run: true, id: r.run_id });
        toast('✅ Đã tạo — đã lưu vào Tài liệu');
      } catch (e) { toast('Không tạo được — thử lại sau.'); el.disabled = false; el.textContent = orig; }
      return;
    }
    if (act === 'camptask-view') {   // xem deliverable đã sinh
      const rid = el.dataset.run; if (!rid) return;
      try {
        const r = await API.get('api/biz/skillrun/' + rid);
        showModal('Deliverable', (r && r.content) || '(trống)', { run: true, id: rid });
      } catch (e) { toast('Không mở được'); }
      return;
    }
    if (act === 'camptask-approve') {   // founder duyệt task
      const tid = el.dataset.task; if (!tid || _campDetailId == null) return;
      try {
        const r = await API.post('api/biz/campaign/task-update', { user_id: _bizUserId, campaign_id: _campDetailId, task_id: tid, status: 'approved' });
        if (r.error) { toast(r.error); return; }
        await refreshBiz(); renderCampDetail(); toast('✓ Đã duyệt');
      } catch (e) { toast('Không duyệt được'); }
      return;
    }
    if (act === 'gen-topics') {   // Pha 2: Max sinh loạt chủ đề cụ thể cho cả lịch
      if (!apiAvailable || !M.bizEnabled) { toast('Bật backend để Max gợi ý chủ đề'); return; }
      const orig = el.textContent; el.disabled = true; el.textContent = '⏳ Max đang nghĩ chủ đề…';
      try {
        const r = await API.post('api/biz/calendar/topics', { user_id: _bizUserId });
        if (r.error) { toast(r.error); el.disabled = false; el.textContent = orig; return; }
        toast(`✨ Đã gợi ý ${r.topics || ''} chủ đề — ô đã duyệt giữ nguyên`);
        await loadRealCalendar();
      } catch (e) { toast('Không gợi ý được — thử lại sau.'); el.disabled = false; el.textContent = orig; }
      return;
    }
    if (act === 'orphan-archive') {   // M-E (Q4): chuyển bài orphan sang Tài liệu
      const key = decodeURIComponent(el.dataset.key || ''); if (!key) return;
      el.disabled = true;
      try {
        const r = await API.post('api/biz/calendar/post-archive', { user_id: _bizUserId, slot_key: key });
        if (r.error) { toast(r.error); el.disabled = false; return; }
        toast('📁 Đã lưu vào Tài liệu'); await loadRealCalendar(); refreshBiz();
      } catch (e) { toast('Không lưu được — thử lại sau.'); el.disabled = false; }
      return;
    }
    if (act === 'orphan-del') {   // M-E: bỏ hẳn bài orphan
      const key = decodeURIComponent(el.dataset.key || ''); if (!key) return;
      try {
        const r = await API.post('api/biz/calendar/post-save', { user_id: _bizUserId, slot_key: key, delete: true });
        if (r.error) { toast(r.error); return; }
        toast('Đã bỏ bài'); await loadRealCalendar(); refreshBiz();
      } catch (e) { toast('Không bỏ được — thử lại sau.'); }
      return;
    }
    if (act === 'cal-gen') {
      // M1.2b: sinh bài THẬT cho slot (bám pillar always-on / brief campaign), lưu skill_run
      const w = el.dataset.week, track = el.dataset.track, day = el.dataset.day;
      const what = day != null ? `ngày ${+day + 1} tuần ${w}` : (track === 'camp' ? `bài campaign tuần ${w}` : `bài Always-on tuần ${w}`);
      if (!apiAvailable || !M.bizEnabled) { toast(`(Mẫu) Bật backend để Max sinh ${what} thật`); return; }
      const orig = el.textContent; el.disabled = true; el.textContent = '⏳ Đang sinh…';
      try {
        const r = await API.post('api/biz/calendar/gen', {
          user_id: _bizUserId, track: track || 'always',
          pillar: el.dataset.pillar || '', campaign_id: el.dataset.campId || el.dataset.campaignId || el.getAttribute('data-camp-id') || '',
          week: w || '', day: day || '' });
        if (r.error) { toast(r.error); return; }
        _postBase = { title: `Bài cho ${what}`, content: r.content || '' };
        showModal(_postBase.title, _postBase.content || '(trống)', { derive: true });
        toast('✅ Đã sinh & lưu bài');
        refreshBiz();
      } catch (e) { toast('Không sinh được bài — thử lại sau.'); }
      finally { el.disabled = false; el.textContent = orig; }
      return;
    }
    if (act === 'gen-asset') {
      // M3.2: sinh tài sản content đặc thù THẬT (ads copy/inbox/sequence), lưu skill_run
      const kind = el.dataset.kind;
      if (!apiAvailable || !M.bizEnabled) { toast('Bật backend (Supabase + LLM) để Max viết thật.'); return; }
      const orig = el.textContent; el.disabled = true; el.textContent = '⏳ Đang viết…';
      try {
        const r = await API.post('api/biz/content/asset', { user_id: _bizUserId, kind });
        if (r.error) { toast(r.error); return; }
        showModal(el.dataset.title || 'Kết quả', r.content || '(trống)', { run: true });
        toast('✅ Đã viết & lưu vào Tài liệu'); refreshBiz();
      } catch (e) { toast('Không viết được — thử lại sau.'); }
      finally { el.disabled = false; el.textContent = orig; }
      return;
    }
    if (act === 'add-campaign-occasion') {
      // M1.2: nối nút này vào wizard occasion THẬT (M1.1) thay prototype prompt()
      if (apiAvailable && M.bizEnabled) { openOccasionWizard(''); return; }
      toast('Bật backend (Supabase + LLM) để tạo campaign theo dịp thật.');
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
    if (act === 'biz-reset') { openResetModal(); return; }
    if (act === 'biz-reset-go') {
      if (!apiAvailable || !M.bizEnabled) { toast('Bật backend để reset'); return; }
      const full = el.dataset.full === '1';
      el.disabled = true; el.textContent = '⏳ Đang reset…';
      try {
        const r = await API.post('api/biz/reset', { user_id: _bizUserId, full });
        if (r.error) { toast(r.error); el.disabled = false; return; }
        const ov = document.getElementById('bizModal'); if (ov) ov.classList.remove('show');
        _realCal = null;
        toast(full ? '🧹 Đã xoá sạch — làm lại từ hồ sơ' : '🧹 Đã reset kết quả — hồ sơ giữ nguyên');
        await refreshBiz(); location.hash = '#hoso'; route();
      } catch (e) { toast('Không reset được — thử lại sau.'); el.disabled = false; }
      return;
    }
    if (act === 'edit-profile') { _editProfile = true; route(); return; }
    if (act === 'cancel-profile') { _editProfile = false; route(); return; }
    if (act === 'view-skillrun') { location.hash = '#doc/' + el.dataset.id; return; }
    if (act === 'doc-open') { _docId = el.dataset.id; _docEdit = false; loadDoc(); return; }
    if (act === 'doc-edit') { _docEdit = true; renderDoc(); return; }
    if (act === 'doc-edit-cancel') { _docEdit = false; renderDoc(); return; }
    if (act === 'copy-skillrun') {
      // M3.1: ưu tiên nội dung trong modal (bài/biến thể) nếu đang mở, ngược lại là doc
      const src = (_modalRun && _modalRun.content) || (_docRun && _docRun.content) || '';
      if (src && navigator.clipboard) navigator.clipboard.writeText(src).then(() => toast('Đã copy nội dung'));
      return;
    }
    if (act === 'post-derive') {
      // M3.1: bung biến thể PHÁI SINH từ bài gốc (đa kênh/video/UGC) — sinh thật, lưu skill_run
      const kind = el.dataset.kind;
      const labels = { channels: '📱 Đa kênh', video: '🎬 Kịch bản video', ugc: '📸 UGC brief' };
      const src = (_postBase && _postBase.content) || (_modalRun && _modalRun.content) || '';
      if (!src) { toast('Chưa có bài gốc'); return; }
      const orig = el.textContent; el.disabled = true; el.textContent = '⏳…';
      try {
        const r = await API.post('api/biz/content/derive', { user_id: _bizUserId, kind, source: src });
        if (r.error) { toast(r.error); return; }
        showModal(labels[kind] || 'Biến thể', r.content || '(trống)', { back: true });
        toast('✅ Đã sinh & lưu biến thể'); refreshBiz();
      } catch (e) { toast('Không sinh được biến thể — thử lại.'); }
      finally { el.disabled = false; el.textContent = orig; }
      return;
    }
    if (act === 'post-back') {   // M3.1: quay lại bài gốc để bung biến thể khác
      if (_postBase) showModal(_postBase.title, _postBase.content || '(trống)', { derive: true });
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
    if (act === 'run-strategize') {   // D-041: lưu GATE (wedge + USP) rồi chạy T4-T5
      try {
        const wedge = (document.getElementById('gateWedge') || {}).value || '';
        const pick = (document.querySelector('input[name="uspStance"]:checked') || {}).value || 'draft';
        const uspText = (document.getElementById('gateUsp') || {}).value || '';
        // own=giữ USP founder (clear), draft=dùng USP Max, edit=nhập mới (clear)
        const usp_stance = pick === 'draft' ? 'draft' : 'clear';
        const usp_text = pick === 'edit' ? uspText : '';
        const horizon = (document.querySelector('input[name="gateHorizon"]:checked') || {}).value || 'auto';
        const posture = (document.querySelector('input[name="gatePosture"]:checked') || {}).value || 'auto';
        const g = await API.post('api/biz/gate', { wedge, usp_stance, usp_text, horizon, posture, user_id: _bizUserId });
        if (g.error) { toast(g.error); return; }
        const r = await API.post('api/biz/agent', { task: 'strategize', user_id: _bizUserId });
        if (r.error) { toast(r.error); return; }
        toast('Đã chốt hướng — Max đang lập chiến lược + playbook…');
        await refreshBiz(); renderRail(); renderTopbar(); route();
      } catch (e) { toast('Không lập được chiến lược'); }
      return;
    }
    if (act === 'gen-bet') {   // Vision A: Max rút option đặt cược (5 nhóm) từ T1-T3
      if (!apiAvailable || !M.bizEnabled) { toast('Bật backend để Max gợi ý'); return; }
      const orig = el.textContent; el.disabled = true; el.textContent = '⏳ Max đang rút lựa chọn…';
      try {
        const r = await API.post('api/biz/bet/options', { user_id: _bizUserId });
        if (r.error) { toast(r.error); el.disabled = false; el.textContent = orig; return; }
        await refreshBiz(); toast('✨ Đã gợi ý lựa chọn đặt cược'); route();
      } catch (e) { toast('Không gợi ý được — thử lại sau.'); el.disabled = false; el.textContent = orig; }
      return;
    }
    if (act === 'gen-funnel') {   // Lô G: dựng bản đồ phễu × kênh cho 1 tuyến
      if (!apiAvailable || !M.bizEnabled) { toast('Bật backend để Max dựng phễu'); return; }
      const orig = el.textContent; el.disabled = true; el.textContent = '⏳ Max đang dựng phễu × kênh…';
      try {
        const r = await API.post('api/biz/funnel-map', { user_id: _bizUserId, objective: el.dataset.obj || 'brand' });
        if (r.error) { toast(r.error); el.disabled = false; el.textContent = orig; return; }
        await refreshBiz(); toast('📊 Đã dựng bản đồ phễu × kênh'); route();
      } catch (e) { toast('Không dựng được — thử lại sau.'); el.disabled = false; el.textContent = orig; }
      return;
    }
    if (act === 'funnel-post') {   // tạo bài từ 1 ô phễu (kênh × tầng) — bám vai-trò-tuyến + playbook
      let ch = '', topic = '';
      try { ch = decodeURIComponent(el.dataset.ch || ''); } catch (e) { ch = el.dataset.ch || ''; }
      try { topic = decodeURIComponent(el.dataset.topic || ''); } catch (e) { topic = el.dataset.topic || ''; }
      const stage = (el.dataset.stage || '').toUpperCase();
      const role = _ROLE_LBL[el.dataset.role] || '';
      openSlotModal({
        track: 'always', pillar: `📡 ${ch} · ${stage}`, funnel: stage,
        title: topic, topic, angles: [topic], key: '',
        track_role: role, objective: el.dataset.obj || 'brand' });
      return;
    }
    if (act === 'rhythm-toggle') {   // Tầng ③: bật/tắt 1 tuyến nền
      const k = el.dataset.dang; const S = rhythmState();
      if (S[k]) { S[k].on = !S[k].on; if (S[k].on && (!S[k].freq || S[k].freq < 0.5)) S[k].freq = 0.5; }
      rerenderRhythm();
      return;
    }
    if (act === 'rhythm-freq') {   // Tầng ③: chỉnh nhịp tuyến (bước 0.5, 0.5..7 bài/tuần)
      const k = el.dataset.dang; const dir = +el.dataset.dir; const S = rhythmState();
      if (S[k] && S[k].on) {
        S[k].freq = Math.max(0.5, Math.min(7, Math.round((S[k].freq + dir * 0.5) * 2) / 2));
        rerenderRhythm();
      }
      return;
    }
    if (act === 'rhythm-save') {   // Tầng ③: chốt nhịp nền → lưu → về Lịch
      el.disabled = true; const _t = el.textContent; el.textContent = '⏳ Đang lưu…';
      try {
        const r = await API.post('api/biz/rhythm/save', { user_id: _bizUserId, rhythm: rhythmState() });
        if (r && r.error) throw 0;
        await refreshBiz();
        _rhythm = null;   // reset đệm → lần sau lấy lại từ MOCK đã lưu
        toast('✅ Đã chốt nhịp nền — Max sẽ rải lên Lịch');
        location.hash = '#calendar';
      } catch (e) { toast('Lưu nhịp nền lỗi — thử lại'); el.disabled = false; el.textContent = _t; }
      return;
    }
    if (act === 'msg-gen') {   // Thông điệp: Max nháp (lần đầu hoặc nháp lại)
      const steer = ((document.getElementById('msgSteer') || {}).value) || '';
      el.disabled = true; const _t = el.textContent; el.textContent = '⏳ Max đang nháp…';
      try {
        const r = await API.post('api/biz/messaging/gen', { user_id: _bizUserId, steer });
        if (r && r.error) { toast(r.error); el.disabled = false; el.textContent = _t; return; }
        await refreshBiz(); _msg = null;
        toast('🏛️ Max đã nháp Thông điệp — chỉnh rồi chốt');
        route();
      } catch (e) { toast('Chưa nháp được — thử lại'); el.disabled = false; el.textContent = _t; }
      return;
    }
    if (act === 'msg-pillar-add') { _msgSync(); msgState().pillars.push({ icon: '📌', territory: '', angle: '', proof: '' }); rerenderMsg(); return; }
    if (act === 'msg-pillar-remove') { _msgSync(); const i = +el.dataset.idx; msgState().pillars.splice(i, 1); rerenderMsg(); return; }
    if (act === 'msg-save') {   // Thông điệp: chốt bản đã chỉnh
      _msgSync();
      el.disabled = true; const _t = el.textContent; el.textContent = '⏳ Đang lưu…';
      try {
        const r = await API.post('api/biz/messaging/save', { user_id: _bizUserId, messaging: msgState() });
        if (r && r.error) { toast(r.error); el.disabled = false; el.textContent = _t; return; }
        await refreshBiz(); _msg = null;
        toast('✅ Đã chốt Thông điệp — mọi bài sẽ bám theo');
        route();
      } catch (e) { toast('Lưu lỗi — thử lại'); el.disabled = false; el.textContent = _t; }
      return;
    }
    if (act === 'bet-chip') { el.classList.toggle('on'); return; }   // tick/bỏ 1 option
    if (act === 'bet-auto') {   // 🤖 Để Max — bỏ chọn nhóm này (bỏ trống = Max tự đề xuất)
      const cat = el.dataset.cat;
      document.querySelectorAll('.bet-chip.on[data-cat="' + cat + '"]').forEach(b => b.classList.remove('on'));
      const f = document.getElementById('betFree-' + cat); if (f) f.value = '';
      toast('🤖 Nhóm này để Max tự đề xuất');
      return;
    }
    if (act === 'run-strategize-bet') {   // Vision A: lưu đặt cược (5 nhóm) → chạy T4-T5
      try {
        const cats = M.bizBetCategories || [];
        const choices = {};
        cats.forEach(c => {
          const on = Array.from(document.querySelectorAll('.bet-chip.on[data-cat="' + c.key + '"]')).map(b => b.dataset.val);
          const free = (((document.getElementById('betFree-' + c.key) || {}).value) || '').split(',').map(s => s.trim()).filter(Boolean);
          choices[c.key] = [...on, ...free];   // nhóm bỏ trống = [] → Max tự quyết
        });
        const b = await API.post('api/biz/bet/save', { user_id: _bizUserId, choices });
        if (b.error) { toast(b.error); return; }
        const horizon = (document.querySelector('input[name="gateHorizon"]:checked') || {}).value || 'auto';
        const posture = (document.querySelector('input[name="gatePosture"]:checked') || {}).value || 'auto';
        await API.post('api/biz/gate', { horizon, posture, user_id: _bizUserId });
        const r = await API.post('api/biz/agent', { task: 'strategize', user_id: _bizUserId });
        if (r.error) { toast(r.error); return; }
        toast('Đã chốt đặt cược — Max đang lập chiến lược + playbook…');
        await refreshBiz(); renderRail(); renderTopbar(); route();
      } catch (e) { toast('Không lập được chiến lược'); }
      return;
    }
    if (act === 'approve-synthesis') {   // M4(1): chốt bản chiến lược hiện tại
      try {
        const r = await API.post('api/biz/synthesis-approve', { user_id: _bizUserId });
        if (r.error) { toast(r.error); return; }
        toast('✅ Đã chốt chiến lược — mở bước Lập chiến dịch');
        await refreshBiz(); route();
      } catch (e) { toast('Không chốt được chiến lược'); }
      return;
    }
    if (act === 'lock-pillars') {   // M4(2): chốt tuyến nền (các trụ đang chọn "Giữ")
      try {
        const picked = [...document.querySelectorAll('.pillar-chk:checked')].map(c => {
          try { return JSON.parse(decodeURIComponent(c.dataset.pillar)); } catch (e) { return null; }
        }).filter(Boolean);
        if (!picked.length) { toast('Chọn ít nhất 1 trụ để chốt'); return; }
        const r = await API.post('api/biz/pillars-lock', { pillars: picked, user_id: _bizUserId });
        if (r.error) { toast(r.error); return; }
        toast('✅ Đã chốt tuyến nền'); await refreshBiz(); route();
      } catch (e) { toast('Không chốt được tuyến nền'); }
      return;
    }
    if (act === 'unlock-pillars') {   // M4(2): bỏ chốt → Max tự sinh lại
      try {
        const r = await API.post('api/biz/pillars-lock', { pillars: [], user_id: _bizUserId });
        if (r.error) { toast(r.error); return; }
        toast('Đã bỏ chốt — Max sẽ tự đề xuất lại'); await refreshBiz(); route();
      } catch (e) { toast('Không bỏ chốt được'); }
      return;
    }
    if (act === 'regen-pillars') {   // M4(2): sinh lại tuyến nền có định hướng
      const steer = ((document.getElementById('pillarSteer') || {}).value || '').trim();
      loadCampaignPlan(steer);
      return;
    }
    if (act === 'new-occasion') {   // M1.1 (D-043): luồng tạo occasion đầy đủ (chốt SMART thật)
      openOccasionWizard(el.dataset.occ || '');
      return;
    }
    if (act === 'new-branding') {   // M-G (G1): tạo campaign Branding nền (xuyên suốt)
      if (!apiAvailable || !M.bizEnabled) { toast('Bật backend để tạo campaign'); return; }
      const orig = el.textContent; el.disabled = true; el.textContent = '⏳ Max đang viết brief thương hiệu…';
      try {
        const r = await API.post('api/biz/campaign/branding', { user_id: _bizUserId });
        if (r.error) { toast(r.error); el.disabled = false; el.textContent = orig; return; }
        toast('🟢 Đã tạo campaign Branding nền');
        await refreshBiz();
        if (r.campaign_id != null) openCampDetail(r.campaign_id); else route();
      } catch (e) { toast('Không tạo được — thử lại sau.'); el.disabled = false; el.textContent = orig; }
      return;
    }
    /* ── S-05/S-10/S-12: campaign-first (gap → tổng → sub → tuyến → bài) ── */
    if (act === 'gen-gaps') {   // S-05: bóc GAP từ nghiên cứu
      if (!apiAvailable || !M.bizEnabled) { toast('Bật backend để Max bóc gap'); return; }
      const orig = el.textContent; el.disabled = true; el.textContent = '⏳ Max đang bóc gap…';
      try {
        const r = await API.post('api/biz/gaps', { user_id: _bizUserId });
        if (r.error) { toast(r.error); el.disabled = false; el.textContent = orig; return; }
        await refreshBiz();
        _gapSel = [];   // gap mới → index cũ vô nghĩa, bỏ chọn
        toast(`✨ Đã bóc ${(r.gaps || []).length} gap`);
        // đang ở wizard bước gap → ở lại wizard; ngoài hero → re-render trang
        const _mv = document.getElementById('bizModal');
        if (_masterState.step === 'gap' && _mv && _mv.classList.contains('show')) renderMasterWizard();
        else route();
      } catch (e) { toast('Không bóc được gap — thử lại sau.'); el.disabled = false; el.textContent = orig; }
      return;
    }
    if (act === 'new-master') { openMasterWizard(); return; }
    if (act === 'new-master-sel') { openMasterWizard({ step: 'bet', gapIdxs: _gapSel }); return; }
    if (act === 'gap-toggle') {   // tick/bỏ 1 gap ở Bước 1 (cập nhật tại chỗ, không nhảy trang)
      const i = +el.dataset.idx;
      if (_gapSel.includes(i)) _gapSel = _gapSel.filter(x => x !== i); else _gapSel.push(i);
      const cd = el.closest('.gap-card'); if (cd) cd.classList.toggle('on', _gapSel.includes(i));
      const b = document.getElementById('gapSelBtn');
      if (b) { b.disabled = !_gapSel.length; b.textContent = _gapSel.length ? ('📦 Tạo campaign tổng từ ' + _gapSel.length + ' gap đã chọn') : '📦 Chọn gap để tạo campaign tổng'; }
      return;
    }
    if (act === 'master-close' || act === 'master-skip') {
      const ov = document.getElementById('bizModal'); if (ov) ov.classList.remove('show');
      if (act === 'master-skip') route();
      return;
    }
    if (act === 'master-gap') {   // tick/bỏ gap trong wizard (đa gap, ngang hàng)
      const i = +el.dataset.idx, S = _masterState;
      if (S.gapIdxs.includes(i)) S.gapIdxs = S.gapIdxs.filter(x => x !== i); else S.gapIdxs.push(i);
      renderMasterWizard();
      return;
    }
    if (act === 'master-next') { _masterState.step = 'bet'; renderMasterWizard(); return; }
    if (act === 'master-back') { _msSync(); _masterState.step = 'gap'; renderMasterWizard(); return; }
    if (act === 'master-genplan') {   // S-10a: tạo master row + Max đề xuất sub
      _msSync();
      const S = _masterState;
      const gsel = S.gapIdxs.map(i => (M.bizGaps || [])[i]).filter(Boolean)
        .map(g => ({ kind: g.kind || 'market', title: g.title || '' }));
      if (!gsel.length) { toast('Chọn ít nhất 1 gap'); return; }
      S.busy = true; renderMasterWizard();
      try {
        const r = await API.post('api/biz/campaign/master', {
          user_id: _bizUserId, gaps: gsel,
          wedge: S.wedge || '', usp: S.usp || '', name: S.name || '' });
        S.busy = false;
        if (r.error) { toast(r.error); renderMasterWizard(); return; }
        S.masterId = r.master_id; S.subs = r.proposed_subs || [];
        S.picked = S.subs.map((_, i) => i);   // mặc định tick hết đề xuất
        S.step = 'subs';
        await refreshBiz(); renderMasterWizard();
      } catch (e) { S.busy = false; toast('Không tạo được — thử lại sau.'); renderMasterWizard(); }
      return;
    }
    if (act === 'master-pick') {
      const i = +el.dataset.idx, S = _masterState;
      if (S.picked.includes(i)) S.picked = S.picked.filter(x => x !== i); else S.picked.push(i);
      renderMasterWizard();
      return;
    }
    if (act === 'master-commit') {   // S-10b: chốt từng sub đã tick → mở hub
      const S = _masterState;
      if (!S.masterId) { toast('Thiếu campaign tổng'); return; }
      S.busy = true; renderMasterWizard();
      try {
        for (const i of S.picked) {
          const sub = S.subs[i]; if (!sub) continue;
          const r = await API.post('api/biz/campaign/sub', {
            user_id: _bizUserId, master_id: S.masterId, type: sub.type, name: sub.name || '' });
          if (r.error) { toast(r.error); }
        }
        S.busy = false;
        await refreshBiz();
        const mid = S.masterId;
        toast('✅ Đã tạo campaign tổng + sub');
        openMasterHub(mid);
      } catch (e) { S.busy = false; toast('Có lỗi khi tạo sub — thử lại.'); renderMasterWizard(); }
      return;
    }
    if (act === 'master-hub') { openMasterHub(el.dataset.id); return; }
    if (act === 'hub-add-sub') {   // S-10b: thêm 1 sub vào master từ hub
      if (_hubId == null) return;
      let nm = ''; try { nm = decodeURIComponent(el.dataset.name || ''); } catch (e) { nm = el.dataset.name || ''; }
      const orig = el.textContent; el.disabled = true; el.textContent = '⏳…';
      try {
        const r = await API.post('api/biz/campaign/sub', {
          user_id: _bizUserId, master_id: _hubId, type: el.dataset.type || '', name: nm });
        if (r.error) { toast(r.error); el.disabled = false; el.textContent = orig; return; }
        toast('➕ Đã thêm sub-campaign'); await refreshBiz(); renderMasterHub();
      } catch (e) { toast('Không thêm được — thử lại.'); el.disabled = false; el.textContent = orig; }
      return;
    }
    if (act === 'sub-content-gen') {   // S-10c: sinh brief + chủ đề theo tuyến cho 1 sub
      if (!apiAvailable || !M.bizEnabled) { toast('Bật backend để Max sinh tuyến'); return; }
      const sid = el.dataset.sub; if (!sid) return;
      const orig = el.textContent; el.disabled = true; el.textContent = '⏳ Max đang dựng tuyến + chủ đề…';
      try {
        const r = await API.post('api/biz/campaign/sub-content', { user_id: _bizUserId, sub_id: sid });
        if (r.error) { toast(r.error); el.disabled = false; el.textContent = orig; return; }
        toast('✨ Đã dựng tuyến bài + chủ đề'); await refreshBiz(); renderMasterHub();
      } catch (e) { toast('Không dựng được — thử lại sau.'); el.disabled = false; el.textContent = orig; }
      return;
    }
    if (act === 'sub-topic-post') {   // tạo bài từ 1 chủ đề tuyến (bám đặt-cược + vai-trò-tuyến)
      if (_hubId == null) return;
      const meta = M.bizCampaignMeta || {}, m = meta[String(_hubId)] || {};
      const sid = el.dataset.sub, sub = meta[String(sid)] || {};
      let topic = '', lens = '';
      try { topic = decodeURIComponent(el.dataset.topic || ''); } catch (e) { topic = el.dataset.topic || ''; }
      try { lens = decodeURIComponent(el.dataset.lens || ''); } catch (e) { lens = el.dataset.lens || ''; }
      const trackKey = el.dataset.track || '';
      const tr = (sub.tracks || []).find(t => t.key === trackKey) || {};
      const objective = (M.bizCampaignTypes || []).find(t => t.key === sub.type);
      openSlotModal({
        track: 'camp', campaignId: sid, phase: tr.label || '',
        pillar: `${sub.type_icon || '🔴'} ${sub.type_label || 'Sub'} · ${tr.label || ''}`,
        funnel: m.name || '', title: topic, topic, angles: [topic],
        value_lens: lens, key: '',
        campaign_gap: ((m.gaps || (m.gap ? [m.gap] : [])).map(g => g.title).filter(Boolean).join(' + ')) || '',
        objective: objective ? objective.objective : '',
        track_role: tr.role || '' });
      return;
    }
    if (act === 'occ-gen') { await occasionGenerate(); return; }
    if (act === 'occ-save') { await occasionSave(); return; }
    if (act === 'occ-back') { _occState.brief = ''; renderOccWizard(); return; }
    if (act === 'occ-close') {
      const ov = document.getElementById('occWizard'); if (ov) ov.classList.remove('show');
      return;
    }
    if (act === 'new-lifecycle') { openLifecycleWizard(el.dataset.mode || 'retention'); return; }
    if (act === 'life-gen') { await lifecycleGenerate(); return; }
    if (act === 'life-save') { await lifecycleSave(); return; }
    if (act === 'life-back') { _lifeState.brief = ''; renderLifeWizard(); return; }
    if (act === 'life-close') {
      const ov = document.getElementById('lifeWizard'); if (ov) ov.classList.remove('show');
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
      // N-01: REPOINT version đã chọn làm hiện hành (re-stamp), KHÔNG đẻ bản copy mới
      try {
        const r = await API.post('api/biz/skillrun/set-current',
          { user_id: _bizUserId, run_id: el.dataset.contentId });
        if (r.error) { toast(r.error); return; }
        toast('Đã đặt làm hiện hành'); _docId = el.dataset.contentId;
        await refreshBiz(); loadDoc();
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
    if (act === 'content-feedback') {   // Lô I: nhập số liệu bài → Max chấm + tối ưu bài kế
      if (!apiAvailable || !M.bizEnabled) { toast('Bật backend để Max chấm'); return; }
      const box = document.getElementById('docMetricsBox');
      const metrics = box ? box.value.trim() : '';
      if (!metrics) { toast('Nhập số liệu của bài (reach, CTR, comment, đơn…)'); return; }
      const orig = el.textContent; el.disabled = true; el.textContent = '⏳ Max đang chấm…';
      try {
        const r = await API.post('api/biz/content/feedback', { user_id: _bizUserId, run_id: el.dataset.id, metrics });
        if (r.error) { toast(r.error); el.disabled = false; el.textContent = orig; return; }
        showModal('📊 Đo hiệu quả & tối ưu bài kế', r.content, { run: true, id: r.run_id });
        toast('✅ Đã chấm — lưu vào Tài liệu'); refreshBiz();
      } catch (e) { toast('Không chấm được — thử lại sau.'); el.disabled = false; el.textContent = orig; }
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
  // Enter trong ô intake (#intakeBox) = Tiếp (form tĩnh) / Gửi (AI) — CAPTURE-phase để ăn TRƯỚC
  // default của textarea + extension (Grammarly…), và luôn ăn dù mount re-render.
  document.addEventListener('keydown', (e) => {
    if (e.key !== 'Enter' || e.shiftKey) return;
    const t = e.target;
    if (!t || t.id !== 'intakeBox') return;
    if (document.querySelector('[data-act="intake-next"]')) {   // wizard tĩnh có nút Tiếp
      e.preventDefault(); handleIntake('next');
    } else if (typeof aiIntakeSend === 'function') {            // AI intake → gửi câu trả lời
      e.preventDefault(); aiIntakeSend();
    }
  }, true);

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
  async function applyStream(data) {
    if (data === _lastStream) return;          // dedupe các bản trùng
    _lastStream = data;
    let state; try { state = JSON.parse(data); } catch (e) { return; }
    Object.assign(window.MOCK, state);
    // khi 1 job AI đổi trạng thái (running→done/error) → nạp lại dữ liệu thật
    const sig = JSON.stringify((state.agentJobs || []).map(j => [j.id, j.status, j.progress]));
    let jobChanged = false;
    if (sig !== _jobSig) {
      _jobSig = sig;
      if ((state.agentJobs || []).some(j => j.status === 'done' || j.status === 'error')) jobChanged = true;
    }
    const editing = document.activeElement &&
      /^(INPUT|TEXTAREA|SELECT)$/.test(document.activeElement.tagName);
    // ⬇️ AWAIT refreshBiz TRƯỚC khi route → chuyển trạng thái mượt, không cần F5
    if (jobChanged) { try { await refreshBiz(); } catch (e) { /* giữ state cũ */ } }
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
