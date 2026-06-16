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

  /* ---- Overview ---- */
  P.overview = {
    title: 'Tổng quan', sub: 'Cập nhật lần cuối: hôm nay, 09:42',
    actions: `<div class="segmented"><button>Hôm nay</button><button class="on">7 ngày</button><button>30 ngày</button></div>
              <button class="primary-btn" data-act="add-campaign">＋ Tạo chiến dịch</button>`,
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

  P.agents = {
    title: 'AI Agent & Dữ liệu thật',
    sub: 'Chạy pipeline phân tích thật + xem dữ liệu nghiệp vụ từ Supabase của bot',
    get actions() {
      const users = M.bizUsers || [];
      const sel = users.length
        ? `<div class="sel" data-act="switch-user" title="Đổi người dùng đang xem">${
            (M.bizUser && (M.bizUser.name || M.bizUser.user_id)) || M.bizUserId || 'Chọn user'} ▾</div>`
        : '';
      return sel + runBtn('full', '▶ Chạy phân tích toàn diện', 'primary-btn');
    },
    render: () => {
      if (M.bizEnabled === false) {
        return card('Chưa nối Supabase', `
          <p class="muted">Phần dữ liệu thật + AI agent cần cấu hình Supabase (cùng project với bot):
          đặt <code>SUPABASE_URL</code> + <code>SUPABASE_SERVICE_KEY</code> rồi chạy lại server.</p>
          <p class="muted" style="margin-top:8px">Hiện đang dùng dữ liệu mock để xem giao diện.</p>`,
          {cls:'span-12'});
      }
      const p = M.bizProfile || {};
      const jobs = M.agentJobs || [];
      const runs = M.bizSkillRuns || [];
      const camps = M.bizCampaigns || [];
      const comps = M.bizCompetitors || [];
      const bv = M.bizBrandVoice;
      const u = M.bizUser || {};
      const hasProfile = Object.keys(p).length > 0;
      return `
      <section class="grid">
        ${card('Hồ sơ doanh nghiệp (thật)', hasProfile ? `
          ${profRow('Doanh nghiệp', p.business_name)}
          ${profRow('Ngành', p.industry)}
          ${profRow('Giai đoạn', p.stage)}
          ${profRow('Sản phẩm/Dịch vụ', p.product_service)}
          ${profRow('Khách hàng mục tiêu', p.target_customer)}
          ${profRow('Doanh thu/tháng', p.monthly_revenue)}
          ${profRow('Ngân sách marketing', p.monthly_marketing_budget)}
          ${profRow('Mục tiêu chính', p.primary_goal)}
          ${profRow('Thách thức', p.main_challenge)}
          ${profRow('USP', p.usp)}
          ${profRow('Khu vực', p.location)}
        ` : `<p class="muted">User này chưa có hồ sơ doanh nghiệp. Chạy phân tích để bot thu thập intake.</p>`,
          {cls:'span-5', action: u.user_id ? badge('user ' + u.user_id) : ''})}

        ${card('Chạy AI Agent', `
          <p class="muted" style="margin-bottom:10px">Mỗi nút gọi pipeline/skill THẬT trong <code>agents/</code>,
          lưu kết quả vào Supabase. Tiến độ cập nhật realtime bên dưới.</p>
          <div class="agent-run">
            ${runBtn('full','▶ Toàn diện')}
            ${runBtn('market','🌐 Thị trường')}
            ${runBtn('competitor','🥊 Đối thủ')}
            ${runBtn('customer','👤 Khách hàng')}
            ${runBtn('pricing','💲 Định giá')}
            ${runBtn('swot','⚖️ SWOT')}
            ${runBtn('strategy','🎯 Chiến lược')}
          </div>`, {cls:'span-7'})}

        ${card('Tiến trình Agent', jobs.length ? `
          <ul class="rows">${jobs.map(j=>`
            <li class="row">
              <div class="row-main"><p>${j.label} <span class="muted">· user ${j.userId}</span></p>
                <span class="muted">${j.status==='running'? (j.progress||'…') : (j.error || j.summary || '')}</span></div>
              ${jobStatusTag(j.status)}
            </li>`).join('')}</ul>` :
          `<p class="muted">Chưa có lần chạy nào. Bấm một nút phía trên để bắt đầu.</p>`,
          {cls:'span-12'})}

        ${card(`Kết quả AI đã tạo (${runs.length})`, runs.length ? table(
          ['Skill','Phiên bản','Độ dài','Model','Thời điểm',''],
          runs.map(r=>[
            r.skill_name, 'v'+(r.version||1), fmtNum(r.length)+' ký tự',
            r.model_used||'—', (r.created_at||'').replace('T',' ').slice(0,16),
            `<button class="ghost-line sm" data-act="view-skillrun" data-id="${r.id}">Xem</button>`])) :
          `<p class="muted">Chưa có output nào. Chạy agent để sinh kết quả.</p>`,
          {cls:'span-8'})}

        ${card('Tài khoản & quota (thật)', `
          ${profRow('User', u.name || u.user_id)}
          ${profRow('Gói', u.plan)}
          ${profRow('Token đã dùng', u.token_used!=null ? fmtNum(u.token_used) : null)}
          ${profRow('Quota token', u.token_quota!=null ? fmtNum(u.token_quota) : null)}
          ${bv ? `<div class="kv"><span>Brand Voice</span><b>${badge('v'+bv.version,'green')}</b></div>
            <p class="muted" style="margin-top:6px">${(bv.tone_descriptors||[]).slice(0,5).join(' · ')||'—'}</p>` :
            `<div class="kv"><span>Brand Voice</span><b>${badge('Chưa setup','amber')}</b></div>`}
        `, {cls:'span-4'})}

        ${card(`Chiến dịch thật (${camps.length})`, camps.length ? table(
          ['Tên','Mục tiêu','Trạng thái','Tạo lúc'],
          camps.map(c=>[c.name||'(chưa đặt tên)', c.primary_goal||'—',
            badge(c.status||'draft', c.status==='active'?'green':c.status==='archived'?'':'amber'),
            (c.created_at||'').slice(0,10)])) :
          `<p class="muted">Chưa có chiến dịch nào trong bảng campaigns.</p>`, {cls:'span-6'})}

        ${card(`Đối thủ đang theo dõi (${comps.length})`, comps.length ? table(
          ['Fanpage','Page ID','Chu kỳ (h)','Ads gần nhất'],
          comps.map(c=>[c.page_name||'—', c.page_id||'—', c.interval_hours||24,
            (c.last_ad_ids||[]).length])) :
          `<p class="muted">User chưa theo dõi đối thủ nào (bảng tracked_competitors).</p>`, {cls:'span-6'})}
      </section>`;
    },
    mount: () => {},
  };

  /* ---- Pipeline (6 steps) ---- */
  P.pipeline = {
    title: 'Phân tích thị trường',
    get sub() {
      const p = M.bizProfile;
      return p && p.industry ? `Pipeline 6 bước · ngành: ${p.industry}` : 'Pipeline 6 bước · dữ liệu mock';
    },
    actions: `<button class="ghost-line">⤓ Xuất HTML</button><button class="primary-btn" data-act="run-agent" data-task="full">▶ Chạy lại bằng AI</button>`,
    render: () => {
      const p = M.bizProfile;
      const latest = M.bizLatest || {};
      // ưu tiên trạng thái thật từ skill_runs nếu đã nối Supabase
      const realSteps = M.bizEnabled ? [
        ['market_research','Nghiên cứu thị trường','TAM/SAM/SOM + động lực thị trường'],
        ['competitor','Phân tích đối thủ','8 đối thủ × 8 chiều'],
        ['customer_insight','Customer Insight','ICP + JTBD + tâm lý'],
        ['psychology_pricing','Định giá & Tâm lý','Mô hình giá + chiến thuật tâm lý'],
        ['swot','SWOT','Ma trận chiến lược'],
        ['synthesis','Chiến lược tổng hợp','SAVE + SMART + roadmap 90 ngày'],
      ].map(([k,name,desc]) => ({name, desc, status: latest[k] ? 'done' : 'pending'})) : M.pipeline;
      const intakeBody = (p && Object.keys(p).length) ? `
          ${profRow('Ngành', p.industry)}
          ${profRow('Sản phẩm', p.product_service)}
          ${profRow('Khu vực', p.location)}
          ${profRow('Doanh thu', p.monthly_revenue)}
          ${profRow('Mục tiêu', p.primary_goal)}
          ${profRow('Thách thức', p.main_challenge)}
          <a class="ghost-line full" href="#agents" style="margin-top:12px;display:block;text-align:center">→ Quản lý ở AI Agent</a>
        ` : `
          <div class="kv"><span>Ngành</span><b>F&B — Quán cà phê</b></div>
          <div class="kv"><span>Sản phẩm</span><b>Cà phê specialty</b></div>
          <div class="kv"><span>Khu vực</span><b>TP.HCM, Q.1</b></div>
          <div class="kv"><span>Doanh thu</span><b>120tr/tháng</b></div>
          <div class="kv"><span>Mục tiêu</span><b>+50% trong 90 ngày</b></div>
          <div class="kv"><span>Thách thức</span><b>Cạnh tranh cao</b></div>
          ${M.bizEnabled ? '<p class="muted" style="margin-top:12px">User chưa có hồ sơ — đây là dữ liệu mẫu.</p>'
            : '<button class="ghost-line full" style="margin-top:12px">✎ Chỉnh sửa intake</button>'}`;
      return `
      <section class="grid">
        ${agentBar('full','synthesis')}
        ${card('Tiến trình phân tích', `
          <div class="stepper">
            ${realSteps.map((s,i)=>`
              <div class="step ${s.status}">
                <div class="step-dot">${s.status==='done'?'✓':i+1}</div>
                <div class="step-body"><p>${s.name}</p><span class="muted">${s.desc}</span></div>
                ${stepBadge(s.status)}
              </div>`).join('')}
          </div>`, {cls:'span-8'})}
        ${card(M.bizEnabled ? 'Business Intake (thật)' : 'Business Intake', intakeBody, {cls:'span-4'})}
        ${card('8 ngành được calibrate', `
          <div class="chips">${M.industries.map((x,i)=>`<span class="chip ${i===0?'on':''}">${x}</span>`).join('')}</div>
        `, {cls:'span-12'})}
      </section>`;
    },
    mount: () => {},
  };

  /* ---- Market research ---- */
  P.market = {
    title: 'Nghiên cứu thị trường', sub: 'TAM / SAM / SOM + động lực thị trường',
    render: () => `
      <section class="kpis kpis-3">
        ${miniStat('TAM','2.400 tỷ','Tổng thị trường VN')}
        ${miniStat('SAM','480 tỷ','Phân khúc khả dụng')}
        ${miniStat('SOM','24 tỷ','Khả năng chiếm 90 ngày')}
      </section>
      <section class="grid">
        ${agentBar('market','market_research')}
        ${card('Quy mô thị trường (TAM/SAM/SOM)', cv('tamChart',230), {cls:'span-7'})}
        ${card('Động lực tăng trưởng', `
          <ul class="bullet">
            <li>📈 Tăng trưởng <b>14%/năm</b>, cao hơn TB ngành</li>
            <li>☕ Xu hướng specialty & local brand lên ngôi</li>
            <li>📱 65% khách Gen Z đặt qua app / giao hàng</li>
            <li>⚠️ Rào cản: chi phí mặt bằng & cạnh tranh giá</li>
          </ul>`, {cls:'span-5'})}
        ${card('Benchmark ngành F&B', table(
          ['Chỉ số','Trung bình','Tốt','Của bạn'],
          [['AOV','45.000₫','60.000₫','52.000₫'],
           ['Repeat 30d','22%','35%','28%'],
           ['COGS %','35%','28%','33%'],
           ['ROAS','2,5x','4,0x','3,1x']]), {cls:'span-12'})}
      </section>`,
    mount: () => {
      if (!hasChart) return;
      reg(new Chart(byId('tamChart'), { type:'bar',
        data:{ labels:['TAM','SAM','SOM'], datasets:[{ data:[2400,480,24],
          backgroundColor:[PRIMARY+'55',PRIMARY2+'88',CYAN], borderRadius:10, maxBarThickness:60 }]},
        options:{ responsive:true, maintainAspectRatio:false, plugins:{legend:{display:false}},
          scales:{ x:{grid:noGrid}, y:{grid, ticks:{callback:v=>v>=1000?v/1000+'k tỷ':v+' tỷ'}} } }}));
    },
  };

  /* ---- Competitor ---- */
  P.competitor = {
    title: 'Phân tích đối thủ', sub: '8 chiều cạnh tranh + theo dõi Ads Library',
    actions: `<button class="primary-btn" data-act="add-tracked">＋ Thêm đối thủ theo dõi</button>`,
    render: () => `
      <section class="grid">
        ${agentBar('competitor','competitor')}
        ${card('Ma trận cạnh tranh', table(
          ['Đối thủ','Định vị','Giá','USP','Thị phần','Mức đe dọa'],
          M.competitors.map(c=>[c.name,c.pos,c.price,c.usp,c.share+'%',
            badge(c.threat, c.threat==='Cao'?'red':c.threat==='Thấp'?'green':'amber')])), {cls:'span-8'})}
        ${card('Bản đồ định vị', cv('posChart',260), {cls:'span-4'})}
        ${card('Đối thủ đang theo dõi', `
          <ul class="rows">
            ${M.tracked.map(t=>`
              <li class="row">
                <span class="s-dot ${t.status==='online'?'online':''}"></span>
                <div class="row-main"><p>${t.name}</p><span class="muted">${t.last}</span></div>
                <span class="tag">${t.ads} ads</span>
                ${t.id?`<button class="icon-btn" data-act="del-tracked" data-id="${t.id}" title="Bỏ theo dõi">✕</button>`:''}
              </li>`).join('')}
          </ul>`, {cls:'span-12'})}
      </section>`,
    mount: () => {
      if (!hasChart) return;
      reg(new Chart(byId('posChart'), { type:'scatter',
        data:{ datasets:[{ data:[{x:8,y:9},{x:5,y:6},{x:7,y:4},{x:3,y:3},{x:6,y:7}],
          backgroundColor:[PRIMARY,PRIMARY2,CYAN,RED,GREEN], pointRadius:9, pointHoverRadius:11 }]},
        options:{ responsive:true, maintainAspectRatio:false, plugins:{legend:{display:false}},
          scales:{ x:{grid, title:{display:true,text:'Giá →'}, min:0,max:10},
                   y:{grid, title:{display:true,text:'Chất lượng cảm nhận →'}, min:0,max:10} } }}));
    },
  };

  /* ---- Customer insight ---- */
  P.customer = {
    title: 'Customer Insight', sub: 'ICP · Jobs-to-be-Done · Pain / Gain / Motivation',
    render: () => `
      <section class="grid">
        ${agentBar('customer','customer_insight')}
        ${M.personas.map(p=>`
          ${card('', `
            <div class="persona">
              <div class="persona-top"><div class="avatar lg">${p.name[0]}</div>
                <div><p class="persona-name">${p.name}</p><span class="muted">${p.age} tuổi</span></div></div>
              <div class="kv"><span>JTBD</span><b>${p.job}</b></div>
              <div class="kv"><span>Pain</span><b>${p.pain}</b></div>
              <div class="kv"><span>Động lực</span><b>${p.motiv}</b></div>
            </div>`, {cls:'span-4'})}`).join('')}
        ${card('Bản đồ Pain → Gain', `
          <div class="paingain">
            <div class="pg-col"><h4>😣 Pain</h4><ul class="bullet"><li>Xếp hàng lâu giờ cao điểm</li><li>Chất lượng không ổn định</li><li>Giá tăng nhưng trải nghiệm giảm</li></ul></div>
            <div class="pg-col"><h4>😄 Gain</h4><ul class="bullet"><li>Đặt trước, lấy nhanh</li><li>Chất lượng đồng nhất</li><li>Tích điểm & ưu đãi thành viên</li></ul></div>
          </div>`, {cls:'span-12'})}
      </section>`,
    mount: () => {},
  };

  /* ---- Pricing ---- */
  P.pricing = {
    title: 'Định giá & Tâm lý', sub: 'Mô hình giá theo phân khúc + chiến thuật tâm lý',
    render: () => `
      <section class="grid">
        ${agentBar('pricing','psychology_pricing')}
        ${M.pricingTiers.map(t=>`
          ${card('', `
            <div class="tier ${t.hot?'hot':''}">
              ${t.hot?'<span class="ribbon">Phổ biến</span>':''}
              <p class="tier-name">${t.name}</p><span class="tag">${t.tag}</span>
              <p class="tier-price">${t.price}</p>
              <ul class="bullet">${t.items.map(i=>`<li>${i}</li>`).join('')}</ul>
            </div>`, {cls:'span-4'})}`).join('')}
        ${card('Chiến thuật tâm lý giá', `
          <ul class="bullet two">
            <li>🎯 <b>Charm pricing</b>: 49.000₫ thay vì 50.000₫</li>
            <li>⚓ <b>Anchoring</b>: đặt Premium cạnh Standard</li>
            <li>📦 <b>Bundling</b>: combo đôi tăng AOV 18%</li>
            <li>⏳ <b>Khan hiếm</b>: ưu đãi giới hạn khung giờ</li>
          </ul>`, {cls:'span-7'})}
        ${card('Độ co giãn theo phân khúc', cv('elastChart',180), {cls:'span-5'})}
      </section>`,
    mount: () => {
      if (!hasChart) return;
      reg(new Chart(byId('elastChart'), { type:'line',
        data:{ labels:['-20%','-10%','Giá','+10%','+20%'], datasets:[{ data:[140,118,100,78,52],
          borderColor:PRIMARY, backgroundColor:fill(PRIMARY), fill:true, tension:.4, borderWidth:2.5, pointRadius:0 }]},
        options:{ responsive:true, maintainAspectRatio:false, plugins:{legend:{display:false}},
          scales:{ x:{grid:noGrid}, y:{grid, ticks:{callback:v=>v+'%'}} } }}));
    },
  };

  /* ---- SWOT ---- */
  P.swot = {
    title: 'SWOT', sub: 'Ma trận chiến lược — calibrate theo ngành F&B',
    render: () => `
      <section class="swot">
        ${swotCell('S','Điểm mạnh','green',['Cà phê specialty chất lượng','Vị trí trung tâm','Khách trung thành'])}
        ${swotCell('W','Điểm yếu','red',['Chi phí mặt bằng cao','Phụ thuộc giờ cao điểm','Ít kênh online'])}
        ${swotCell('O','Cơ hội','primary',['Gen Z chuộng local brand','Tăng trưởng delivery','UGC lan tỏa'])}
        ${swotCell('T','Thách thức','amber',['Chuỗi lớn cạnh tranh giá','Chi phí ads tăng','Trung thành thấp'])}
      </section>
      <section class="grid">
        ${agentBar('swot','swot')}
        ${card('Tactical plays (SO/WO/ST/WT)', table(
          ['Nhóm','Chiến thuật','KPI'],
          [['SO','Đẩy specialty qua UGC + KOL local','Reach, Repeat'],
           ['WO','Mở kênh đặt trước online','Đơn online'],
           ['ST','Loyalty giữ chân vs chuỗi lớn','Repeat 30d'],
           ['WT','Tối ưu ngân sách giờ thấp điểm','CPA']]), {cls:'span-12'})}
      </section>`,
    mount: () => {},
  };

  /* ---- Strategy ---- */
  P.strategy = {
    title: 'Chiến lược tổng hợp', sub: 'SAVE Framework · SMART Goals · Roadmap 90 ngày',
    actions: `<button class="ghost-line">⤓ Xuất báo cáo</button><button class="primary-btn">→ Tạo Campaign Brief</button>`,
    render: () => `
      <section class="grid">
        ${agentBar('strategy','synthesis')}
        ${card('SAVE Framework', `
          <div class="save">${M.saveFramework.map(s=>`
            <div class="save-item"><div class="save-k">${s.k}</div>
              <div><p>${s.name}</p><span class="muted">${s.text}</span></div></div>`).join('')}</div>`, {cls:'span-6'})}
        ${card('SMART Goals', `<ul class="bullet">${M.smart.map(g=>`<li>✅ ${g}</li>`).join('')}</ul>`, {cls:'span-6'})}
        ${card('Roadmap 90 ngày', `
          <div class="roadmap">${M.roadmap.map(r=>`
            <div class="rm-phase"><span class="rm-tag">${r.phase}</span><p class="rm-title">${r.title}</p>
              <ul class="bullet">${r.items.map(i=>`<li>${i}</li>`).join('')}</ul></div>`).join('')}</div>`, {cls:'span-12'})}
      </section>`,
    mount: () => {},
  };

  /* ---- Campaign Brief ---- */
  P.brief = {
    title: 'Campaign Brief', sub: 'Tài liệu chiến dịch 10 phần — tự prefill từ chiến lược',
    actions: `<button class="primary-btn">→ Tạo nội dung</button>`,
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

  /* ---- Content calendar ---- */
  P.calendar = {
    title: 'Lịch nội dung', sub: 'Tuần này · Pillar: Educate / Trust / Engage / Convert',
    actions: `<div class="segmented"><button class="on">Tuần</button><button>Tháng</button></div>
              <button class="primary-btn" data-act="add-post" data-day="0">＋ Thêm bài</button>`,
    render: () => `
      <section class="cal">
        ${M.calendar.days.map((d,i)=>`
          <div class="cal-day"><div class="cal-head">${d}</div>
            ${calPosts(i).map(p=>`<div class="cal-post ${pillarCls(p.pillar)}">
                <span>${p.pillar}</span>${p.title}
                ${p.id?`<button class="cal-del" data-act="del-calendar" data-id="${p.id}" title="Xoá">✕</button>`:''}
              </div>`).join('')}
            <button class="cal-add" data-act="add-post" data-day="${i}">＋</button></div>`).join('')}
      </section>
      <section class="grid">
        ${card('Tỉ lệ pillar tuần', cv('calPillar',160), {cls:'span-12'})}
      </section>`,
    mount: () => {
      if (!hasChart) return;
      reg(new Chart(byId('calPillar'), { type:'bar',
        data:{ labels:M.pillars.map(p=>p.name), datasets:[{ data:M.pillars.map(p=>p.pct),
          backgroundColor:M.pillars.map(p=>p.color), borderRadius:8, maxBarThickness:46 }]},
        options:{ indexAxis:'y', responsive:true, maintainAspectRatio:false, plugins:{legend:{display:false}},
          scales:{ x:{grid, ticks:{callback:v=>v+'%'}}, y:{grid:noGrid} } }}));
    },
  };

  /* ---- Content generator ---- */
  P.content = {
    title: 'Trình tạo nội dung', sub: 'Sản xuất hàng loạt: bài viết + video + UGC + ads',
    actions: `<button class="ghost-line">⤓ Xuất Excel</button><button class="primary-btn" data-act="gen-content">⚡ Tạo gói nội dung</button>`,
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
          <div class="tabs"><button class="tab on">Bài viết</button><button class="tab">Video</button><button class="tab">UGC</button><button class="tab">Ads</button></div>
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
            <button class="cal-add">＋ Thêm biến thể</button></div>`).join('')}
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
    actions: `<div class="segmented"><button class="on">Welcome</button><button>Winback</button></div>`,
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
    title: 'Brand Voice', sub: 'Quy tắc giọng nói thương hiệu + hiệu chỉnh tông',
    render: () => `
      <section class="grid">
        ${card('Nên (Do)', `<ul class="bullet">${M.voice.do.map(d=>`<li>✅ ${d}</li>`).join('')}</ul>`, {cls:'span-4'})}
        ${card('Không nên (Don\'t)', `<ul class="bullet">${M.voice.dont.map(d=>`<li>🚫 ${d}</li>`).join('')}</ul>`, {cls:'span-4'})}
        ${card('Hiệu chỉnh tông', M.voice.tone.map(t=>`
          <div class="slider"><div class="slider-top"><span>${t.k}</span><b>${t.v}</b></div>
            <div class="track"><div class="fillbar" style="width:${t.v}%"></div></div></div>`).join(''), {cls:'span-4'})}
        ${card('Kiểm tra tuân thủ giọng', `
          <div class="voicecheck"><span class="tag green">Đạt 92%</span>
          <p class="muted" style="margin-top:8px">Mẫu “Buổi sáng cần một lý do…” — phù hợp giọng thân thiện, câu ngắn. Gợi ý: giảm 1 emoji ở cuối.</p></div>`, {cls:'span-12'})}
      </section>`,
    mount: () => {},
  };

  /* ---- Ads analytics ---- */
  P.adsanalytics = {
    title: 'Ads Analytics', sub: 'Phễu 6 tầng + Winners / Losers (FB Marketing API)',
    actions: `<div class="segmented"><button>7 ngày</button><button class="on">30 ngày</button></div>`,
    render: () => `
      <section class="grid">
        ${card('Phễu chuyển đổi 6 tầng', `
          <div class="vfunnel">${M.funnel.map((f,i)=>`
            <div class="vf-row" style="--w:${100-i*13}%">
              <div class="vf-bar"><span class="vf-tier">${f.tier}</span><span class="vf-val">${num(f.value)}</span></div>
              <div class="vf-meta"><span>${f.cost}</span><span class="tag">${f.rate}</span></div>
            </div>`).join('')}</div>`, {cls:'span-7'})}
        ${card('Phân bổ chi tiêu', cv('spendDonut',200), {cls:'span-5',})}
        ${card('🏆 Winners', table(['Quảng cáo','ROAS','Chi tiêu','CPA'],
          M.winners.map(w=>[w.name, badge(w.roas+'x','green'), w.spend, w.cpa])), {cls:'span-6'})}
        ${card('⚠️ Losers', table(['Quảng cáo','ROAS','Chi tiêu','CPA'],
          M.losers.map(w=>[w.name, badge(w.roas+'x','red'), w.spend, w.cpa])), {cls:'span-6'})}
      </section>`,
    mount: () => { doughnut('spendDonut',[40,28,18,14],[PRIMARY,PRIMARY2,CYAN,AMBER]); },
  };

  /* ---- Optimizer ---- */
  P.optimizer = {
    title: 'Tối ưu tự động', sub: 'Đề xuất pause / scale / nhân bản dựa trên KPI',
    actions: `<label class="switch"><input type="checkbox" checked><span class="track-sw"></span></label>
              <span class="muted">Tự động thực thi</span>`,
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
          ${miniRow('Chi tiêu lãng phí','1,8M','→ 0,4M','up')}
          <button class="primary-btn full" style="margin-top:14px">⚡ Áp dụng tất cả</button>`, {cls:'span-4'})}
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
          <div class="kv"><span>${t.name}</span><b>${t.value}</b></div>`).join('') +
          `<button class="ghost-line full" style="margin-top:12px">✎ Điều chỉnh ngưỡng</button>`, {cls:'span-5'})}
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
            ${statusRow('Facebook API','Ổn định')}
            ${statusRow('Bộ tối ưu tự động','Đang chạy')}
            ${statusRow('Đồng bộ dữ liệu','2 phút trước')}
            ${statusRow('Supabase','Kết nối')}
          </ul>
          <div class="kv" style="margin-top:12px"><span>Workflow errors (24h)</span><b>3</b></div>`, {cls:'span-4'})}
      </section>`,
    mount: () => {},
  };

  /* ---- Settings ---- */
  P.settings = {
    title: 'Cài đặt', sub: 'Tài khoản · API · thông báo',
    render: () => `
      <section class="grid">
        ${card('Tài khoản', `
          <div class="form">${field('Tên hiển thị','Nguyễn Văn A')}${field('Email','mtnguyen7200@gmail.com')}
          ${selectField('Ngành mặc định','F&B — Quán cà phê')}${selectField('Ngôn ngữ','Tiếng Việt')}</div>`, {cls:'span-6'})}
        ${card('Khóa API', `
          <div class="form">${field('Anthropic API Key','sk-ant-••••••••••••')}${field('Facebook App ID','••••••••')}
          ${field('Telegram Bot Token','••••••:••••••')}</div>
          <button class="primary-btn" style="margin-top:6px">Lưu thay đổi</button>`, {cls:'span-6'})}
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
        <p class="nav-label">${g.group}</p>
        ${g.items.map(it=>`<a class="nav-item ${it.id===active?'active':''}" href="#${it.id}"><span class="ic">${it.icon}</span> ${it.label}</a>`).join('')}
      `).join('')}</nav>
      <div class="sidebar-foot"><p class="version">v2.4.0 · demo dữ liệu mock</p></div>`;
    document.getElementById('sidebar').innerHTML = html;
  }
  function renderRail() {
    document.getElementById('rail').innerHTML = `
      <section class="card"><div class="card-head"><h3>Token còn lại</h3></div>
        <p class="kpi-value" style="font-size:22px">84.200</p>
        <div class="track" style="margin:8px 0"><div class="fillbar" style="width:58%"></div></div>
        <span class="muted">58% quota tháng · gói Pro</span></section>
      <section class="card"><div class="card-head"><h3>Cảnh báo</h3><span class="pill warn">${M.alerts.length} mới</span></div>
        <ul class="alerts">${M.alerts.map(a=>alertItem(a)).join('')}</ul></section>
      <section class="card mini"><div class="card-head"><h3>Trạng thái hệ thống</h3></div>
        <ul class="status">
          <li><span class="s-dot online"></span>Facebook API<span class="muted">Ổn định</span></li>
          <li><span class="s-dot online"></span>Bộ tối ưu tự động<span class="muted">Đang chạy</span></li>
          <li><span class="s-dot online"></span>Đồng bộ dữ liệu<span class="muted">2 phút trước</span></li>
        </ul></section>`;
  }
  function route() {
    const id = (location.hash.replace('#','') || 'overview');
    const page = P[id] || P.overview;
    killCharts();
    renderSidebar(id);
    const actions = page.actions || '';
    document.getElementById('view').innerHTML =
      pageHead(page.title, page.sub, actions) + page.render();
    if (page.mount) page.mount();
    document.querySelector('.main').scrollTo(0,0);
    document.body.classList.remove('nav-open');
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
  function showModal(title, text) {
    let ov = document.getElementById('bizModal');
    if (!ov) {
      ov = document.createElement('div');
      ov.id = 'bizModal'; ov.className = 'modal-ov';
      ov.innerHTML = `<div class="modal"><div class="modal-head"><h3></h3>
        <button class="icon-btn" id="bizModalX">✕</button></div><pre class="modal-body"></pre></div>`;
      document.body.appendChild(ov);
      ov.addEventListener('click', (e) => { if (e.target === ov) ov.classList.remove('show'); });
      ov.querySelector('#bizModalX').addEventListener('click', () => ov.classList.remove('show'));
    }
    ov.querySelector('h3').textContent = title;
    ov.querySelector('.modal-body').textContent = text;
    ov.classList.add('show');
  }

  async function handleAction(el) {
    const act = el.dataset.act;
    if (!apiAvailable) { toast('Tính năng này cần backend — chạy: python run_web.py'); if (el.type === 'checkbox') el.checked = !el.checked; return; }

    // ── AI agent + dữ liệu thật (không theo luồng state web_*) ──
    if (act === 'run-agent') {
      try {
        const r = await API.post('api/biz/agent', { task: el.dataset.task, user_id: _bizUserId });
        if (r.error) { toast(r.error); return; }
        toast('Đã khởi chạy AI agent — theo dõi tiến trình realtime');
        await refreshBiz(); renderRail(); route();
      } catch (e) { toast('Không khởi chạy được agent'); }
      return;
    }
    if (act === 'view-skillrun') {
      try {
        const r = await API.get('api/biz/skillrun/' + el.dataset.id);
        showModal((r.skill_name || 'Output') + ' · v' + (r.version || 1), r.content || '(trống)');
      } catch (e) { toast('Không tải được nội dung'); }
      return;
    }
    if (act === 'switch-user') {
      const users = M.bizUsers || [];
      if (!users.length) { toast('Chưa có user nào'); return; }
      const list = users.map((u, i) => `${i + 1}. ${u.name || u.user_id} (${u.user_id})`).join('\n');
      const pick = prompt('Chọn user để xem (nhập số thứ tự):\n' + list);
      if (pick === null) return;
      const idx = parseInt(pick) - 1;
      if (users[idx]) { _bizUserId = users[idx].user_id; await refreshBiz(); renderRail(); route(); toast('Đã chuyển user'); }
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
      if (res) { Object.assign(window.MOCK, res); renderRail(); route(); }
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
  function setLive(on) {
    let dot = document.getElementById('liveDot');
    if (!dot) {
      dot = document.createElement('span');
      dot.id = 'liveDot'; dot.className = 'live-dot'; dot.title = 'Cập nhật realtime';
      dot.innerHTML = '<i></i> Live';
      const tr = document.querySelector('.topbar-right');
      tr.insertBefore(dot, tr.firstChild);
    }
    dot.classList.toggle('off', !on);
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
    renderRail();
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
    } catch (e) { /* không có backend → dùng dữ liệu mock nhúng sẵn */ }
    renderRail();
    route();
    if (apiAvailable) startStream();
  })();
})();
