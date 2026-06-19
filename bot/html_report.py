"""
HTML report generator for Marketing OS analysis output.
Bundles structured agent outputs into 1 styled HTML document.
"""
import re
from datetime import datetime

try:
    import markdown as _md
    HAS_MARKDOWN = True
except ImportError:
    HAS_MARKDOWN = False


STAGE_META = {
    # Strategic skills — by stage_key (used in full pipeline + ops result rendering)
    "market_research":    {"title": "Nghiên cứu Thị trường",       "icon": "📊", "color": "market"},
    "competitor":         {"title": "Phân tích Đối thủ",            "icon": "🕵️", "color": "competitor"},
    "customer_insight":   {"title": "Customer Insight & ICP",      "icon": "👥", "color": "customer"},
    "psychology_pricing": {"title": "Marketing Psychology & Pricing", "icon": "💡", "color": "pricing"},
    "social_listening":   {"title": "Social Listening System",     "icon": "📡", "color": "market"},
    "usp_definition":     {"title": "USP Definition",                "icon": "🎯", "color": "strategy"},
    "swot":               {"title": "Phân Tích SWOT",                "icon": "🔀", "color": "swot"},
    "retention_strategy": {"title": "Retention Strategy",            "icon": "🔄", "color": "customer"},
    "winback_campaign":   {"title": "Winback Vision",                "icon": "🔁", "color": "customer"},
    "synthesis":          {"title": "Kế Hoạch Đề Xuất",            "icon": "🚀", "color": "strategy"},
    # Strategic single-shot task aliases
    "market":             {"title": "Nghiên cứu Thị trường",       "icon": "📊", "color": "market"},
    "customer":           {"title": "Customer Insight & ICP",      "icon": "👥", "color": "customer"},
    "pricing":            {"title": "Marketing Psychology & Pricing", "icon": "💡", "color": "pricing"},
    "strategy":           {"title": "Kế Hoạch Đề Xuất",            "icon": "🎯", "color": "strategy"},
    "tactical_playbook":  {"title": "Tactical Playbook",             "icon": "📋", "color": "swot"},
    # Operational skills
    "campaign_brief":      {"title": "Viết Brief Campaign",         "icon": "📋", "color": "strategy"},
    "content_calendar":    {"title": "Lịch Nội Dung",               "icon": "📅", "color": "market"},
    "content_generator":   {"title": "Sản Xuất Nội Dung",           "icon": "✍️", "color": "customer"},
    "ads_copy":            {"title": "Sản Xuất Nội Dung Ads",       "icon": "📢", "color": "pricing"},
    "ads_generator":       {"title": "Sản Xuất Nội Dung Ads",       "icon": "📢", "color": "pricing"},
    "video_scripts":       {"title": "Viết Kịch Bản Video",         "icon": "🎬", "color": "customer"},
    "sales_inbox_script":  {"title": "Kịch Bản Sales",              "icon": "💬", "color": "customer"},
    "email_zalo_sequence": {"title": "Chăm Sóc Khách Hàng",         "icon": "📧", "color": "pricing"},
    "competitor_spy":      {"title": "Theo Dõi Đối Thủ",            "icon": "🔍", "color": "competitor"},
    "competitor_comparison": {"title": "So Sánh Với Đối Thủ",         "icon": "🆚", "color": "competitor"},
    "campaign_plan":       {"title": "Kế Hoạch Triển Khai Campaign", "icon": "🗺️", "color": "strategy"},
}


CSS = """
:root {
  --primary: #2563eb; --accent: #f59e0b; --bg: #fafafa; --card: #ffffff;
  --text: #1e293b; --muted: #64748b; --border: #e2e8f0;
  --success: #10b981;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  background: var(--bg); color: var(--text); line-height: 1.65; padding: 24px 16px;
}
.container { max-width: 880px; margin: 0 auto; }

.header {
  background: linear-gradient(135deg, #2563eb 0%, #7c3aed 100%);
  color: white; padding: 32px 28px; border-radius: 16px; margin-bottom: 20px;
  box-shadow: 0 4px 20px rgba(37,99,235,0.15);
}
.header h1 { font-size: 26px; font-weight: 700; margin-bottom: 6px; }
.header .meta { font-size: 14px; opacity: 0.9; }
.header .powered { margin-top: 14px; font-size: 11px; opacity: 0.7; }

/* CSS-only tabs (radio buttons + :checked, no JS) */
.tab-state { display: none !important; }  /* hide radio inputs */

.tabs {
  display: flex; gap: 4px; background: white;
  padding: 6px; border-radius: 12px; margin-bottom: 20px;
  overflow-x: auto; box-shadow: 0 1px 3px rgba(0,0,0,0.05);
  scrollbar-width: thin;
}
.tab-btn {
  padding: 10px 16px; background: transparent;
  cursor: pointer; font-size: 13px; font-weight: 500; color: var(--muted);
  white-space: nowrap; border-radius: 8px; transition: all 0.15s;
  display: inline-flex; align-items: center; gap: 6px;
}
.tab-btn:hover { background: #f1f5f9; color: var(--text); }

/* Sections start hidden, shown when matching radio is checked */
.section {
  display: none;
  background: var(--card); border-radius: 12px; padding: 28px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.05); border-left: 4px solid var(--primary);
}
.section.market    { border-color: #2563eb; }
.section.competitor{ border-color: #f59e0b; }
.section.customer  { border-color: #10b981; }
.section.pricing   { border-color: #ec4899; }
.section.strategy  { border-color: #8b5cf6; }
.section.swot      { border-color: #0ea5e9; }

.section-header {
  display: flex; align-items: center; gap: 12px;
  margin-bottom: 18px; padding-bottom: 12px; border-bottom: 1px solid var(--border);
}
.section-header .icon { font-size: 28px; }
.section-header h2 { font-size: 22px; font-weight: 600; }

.insight {
  background: #fef3c7; border-left: 4px solid var(--accent);
  padding: 16px 20px; border-radius: 6px; margin: 16px 0;
  font-style: italic; color: #78350f; font-size: 15px; line-height: 1.6;
}
.insight::before { content: "💡 "; font-style: normal; font-weight: 600; }

.summary, .benchmarks {
  background: #f0f9ff; border-left: 3px solid var(--primary);
  padding: 16px 20px; border-radius: 8px; margin: 14px 0;
}
.summary-label, .benchmarks-label {
  font-size: 11px; font-weight: 700; text-transform: uppercase;
  color: var(--primary); letter-spacing: 0.5px; margin-bottom: 10px;
}
.summary ul, .benchmarks ul { margin-left: 20px; }
.summary p, .benchmarks p { margin-bottom: 6px; }

.content { margin-top: 16px; line-height: 1.7; }

/* Reset shared rule — mỗi level tự định nghĩa riêng */
.content h1, .content h2, .content h3, .content h4 {
  font-weight: 700; color: var(--text); line-height: 1.3;
}

/* h1 — title cấp section (hiếm dùng trong content) */
.content h1 {
  font-size: 22px; margin: 36px 0 14px;
  padding-bottom: 8px; border-bottom: 2px solid var(--primary);
}

/* h2 — đề mục lớn trong tab */
.content h2 {
  font-size: 19px; margin: 32px 0 12px; color: var(--text);
  padding-bottom: 6px; border-bottom: 1px solid var(--border);
}

/* h3 — phần chính (TAM, Tier 1, ICP...) — phải nổi bật nhất trong content */
.content h3 {
  font-size: 15px; font-weight: 700;
  margin: 30px 0 10px;
  padding: 9px 14px;
  background: #eff6ff;
  border-left: 4px solid var(--primary);
  border-radius: 0 6px 6px 0;
  color: #1e3a8a;
  text-transform: none;
}

/* h4 — sub-section label nổi bật (Messaging Gap, Channel Gap, Tier 1...) */
.content h4 {
  font-size: 13px; font-weight: 700;
  margin: 24px 0 10px;
  display: inline-block;
  padding: 3px 10px 3px 0;
  color: var(--text);
  text-transform: uppercase; letter-spacing: 0.6px;
  border-bottom: 2px solid var(--accent);
}

.content p { margin-bottom: 14px; font-size: 15px; }
.content ul, .content ol { margin: 6px 0 14px 26px; }
.content li { margin-bottom: 8px; font-size: 15px; line-height: 1.65; }
.content strong { font-weight: 700; color: var(--text); }
.content em { color: var(--muted); }
.content .table-wrap { overflow-x: auto; -webkit-overflow-scrolling: touch; margin: 20px 0; }
.content table {
  width: 100%; border-collapse: collapse; font-size: 14px;
  background: white; border-radius: 8px; overflow: hidden;
  box-shadow: 0 1px 3px rgba(0,0,0,0.04); min-width: 480px;
}
.content th, .content td {
  padding: 12px 16px; text-align: left; border-bottom: 1px solid var(--border);
  white-space: nowrap;
}
.content td { white-space: normal; min-width: 80px; }
.content th {
  background: #f1f5f9; font-weight: 700; font-size: 12px;
  text-transform: uppercase; color: var(--muted); letter-spacing: 0.5px;
  white-space: nowrap;
}
.content tr:last-child td { border-bottom: none; }
.content tr:hover { background: #f8fafc; }
.content blockquote {
  border-left: 4px solid var(--accent); padding: 14px 18px; margin: 18px 0;
  background: #fffbeb; color: #78350f; font-style: italic; border-radius: 4px;
  font-size: 15px;
}
.content a {
  color: var(--primary); text-decoration: none;
  border-bottom: 1px solid #bfdbfe; padding-bottom: 1px;
}
.content a:hover { border-bottom-color: var(--primary); }
.content pre {
  background: #f8fafc; border: 1px solid var(--border); border-radius: 8px;
  padding: 16px; margin: 18px 0; overflow-x: auto;
  font-size: 12.5px; line-height: 1.5; color: #334155;
  font-family: ui-monospace, "SF Mono", Menlo, Consolas, monospace;
}
.content pre code { background: none; padding: 0; font-size: inherit; }

.footer {
  text-align: center; color: var(--muted); font-size: 12px;
  padding: 24px 16px; margin-top: 16px; line-height: 1.7;
}

/* === Positioning Map Visual === */
.pos-map-wrap { margin: 24px 0; font-family: inherit; }
.pos-map-title { font-size: 15px; font-weight: 700; color: var(--text); margin-bottom: 8px; }
.pos-y-lbl { text-align: center; font-size: 12px; font-weight: 600; color: var(--muted); padding: 4px 0; }
.pos-quads {
  display: grid; grid-template-columns: 1fr 1fr;
  border: 2px solid var(--border); border-radius: 10px; overflow: hidden;
}
.pos-q { padding: 14px; min-height: 100px; }
.pq2 { background: #eff6ff; border-right: 2px solid #bfdbfe; border-bottom: 2px solid #bfdbfe; }
.pq1 { background: #f0fdf4; border-bottom: 2px solid #bbf7d0; }
.pq3 { background: #fefce8; border-right: 2px solid #fde68a; }
.pq4 { background: #fdf4ff; }
.pos-q-lbl { font-size: 10px; font-weight: 700; text-transform: uppercase; color: var(--muted); margin-bottom: 4px; letter-spacing: 0.5px; }
.pos-q-desc { font-size: 12px; font-weight: 600; color: var(--text); margin-bottom: 8px; line-height: 1.4; }
.pos-q-items { display: flex; flex-wrap: wrap; gap: 5px; }
.pos-item { font-size: 12px; padding: 3px 9px; border-radius: 12px; background: rgba(255,255,255,0.8); border: 1px solid rgba(0,0,0,0.1); color: var(--text); }
.pos-item-self { background: var(--primary) !important; color: white !important; border-color: var(--primary) !important; font-weight: 600; }
.pos-x-axis { display: flex; align-items: center; gap: 10px; margin-top: 8px; font-size: 12px; font-weight: 600; color: var(--muted); }
.pos-x-l, .pos-x-r { flex-shrink: 0; }
.pos-x-line { flex: 1; height: 2px; background: var(--border); }

/* === Ads Dashboard: horizontal bar chart === */
.barchart { margin: 8px 0 28px; }
.barchart-title {
  font-size: 11px; font-weight: 700; text-transform: uppercase;
  letter-spacing: 0.6px; color: var(--muted); margin-bottom: 16px;
}
.barchart-row { display: flex; align-items: center; gap: 12px; margin-bottom: 10px; }
.barchart-label { width: 120px; flex-shrink: 0; font-size: 13px; color: var(--text); text-align: right; }
.barchart-track {
  flex: 1; background: #f1f5f9; border-radius: 6px; height: 30px;
  position: relative; overflow: hidden;
}
.barchart-fill {
  height: 100%; border-radius: 6px; display: flex; align-items: center;
  padding: 0 12px; color: white; font-size: 12px; font-weight: 600; white-space: nowrap;
}
.barchart-fill.c1 { background: linear-gradient(90deg, #7c3aed, #a78bfa); }
.barchart-fill.c2 { background: linear-gradient(90deg, #6366f1, #a5b4fc); }
.barchart-fill.c3 { background: linear-gradient(90deg, #14b8a6, #5eead4); color: #134e4a; }
.barchart-fill.c4 { background: linear-gradient(90deg, #10b981, #6ee7b7); color: #064e3b; }
.barchart-fill.c5 { background: linear-gradient(90deg, #94a3b8, #cbd5e1); color: #334155; }

/* === Ads Dashboard: pill badge inline trong bảng (Win #1, CPL thấp nhất...) === */
.pill {
  display: inline-block; font-size: 9px; font-weight: 700; padding: 2px 8px;
  border-radius: 10px; margin-left: 6px; text-transform: uppercase; letter-spacing: 0.3px;
  vertical-align: middle;
}
.pill-win  { background: #dcfce7; color: #15803d; }
.pill-best { background: #dbeafe; color: #1d4ed8; }

/* === Ads Dashboard: lưới insight 2 cột (pattern thắng / điểm cần chú ý) === */
.insight-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin: 16px 0 8px; }
.insight-card { border-radius: 10px; padding: 18px 20px; }
.insight-card.good { background: #f0fdf4; border: 1px solid #bbf7d0; }
.insight-card.warn { background: #fffbeb; border: 1px solid #fde68a; }
.insight-card-title { font-size: 13px; font-weight: 700; margin-bottom: 12px; }
.insight-card.good .insight-card-title { color: #15803d; }
.insight-card.warn .insight-card-title { color: #b45309; }
.insight-card ul { list-style: none; margin: 0; padding: 0; }
.insight-card li {
  font-size: 13px; line-height: 1.6; padding-left: 18px; position: relative;
  margin-bottom: 10px; color: var(--text);
}
.insight-card.good li::before { content: "●"; color: #22c55e; position: absolute; left: 0; top: 6px; font-size: 9px; }
.insight-card.warn li::before { content: "▲"; color: #f59e0b; position: absolute; left: 0; top: 6px; font-size: 9px; }

/* Mobile */
@media (max-width: 640px) {
  body { padding: 12px 8px; }
  .header { padding: 24px 20px; border-radius: 12px; }
  .header h1 { font-size: 22px; }
  .section { padding: 20px 16px; }
  .tab-btn { padding: 8px 12px; font-size: 12px; }
  .content h3 { font-size: 14px; padding: 7px 12px; }
  .content table { font-size: 13px; }
  .content th, .content td { padding: 8px 10px; }
  .pos-q { padding: 10px; min-height: 80px; }
  .pos-q-desc { font-size: 11px; }
  .insight-grid { grid-template-columns: 1fr; }
  .barchart-label { width: 86px; font-size: 11px; }
  .archetype-banner { padding: 16px; }
  .archetype-banner h3 { font-size: 16px; }
}

/* Archetype banner — giải thích archetype mua hàng cho user */
.archetype-banner {
  background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
  border-left: 4px solid #f59e0b;
  border-radius: 10px;
  padding: 20px 24px;
  margin: 0 0 20px;
  font-size: 14px;
  line-height: 1.6;
  color: #1f2937;
}
.archetype-banner .archetype-diagnosis { margin: 8px 0 12px; }
.archetype-banner .archetype-head {
  display: flex; align-items: center; gap: 10px; margin-bottom: 10px;
}
.archetype-banner .archetype-head h3 {
  margin: 0; font-size: 18px; font-weight: 600; color: #92400e;
}
.archetype-banner .archetype-head .icon { font-size: 24px; }
.archetype-banner .archetype-meaning { margin: 8px 0 12px; }
.archetype-banner .archetype-why {
  background: rgba(255,255,255,0.6); padding: 10px 14px; border-radius: 6px;
  margin: 10px 0; font-size: 13px;
}
.archetype-banner .archetype-flip {
  background: rgba(220, 38, 38, 0.08); border-left: 3px solid #dc2626;
  padding: 10px 14px; border-radius: 4px; margin: 10px 0; font-size: 13px;
}
.archetype-banner details {
  margin-top: 10px; font-size: 13px; cursor: pointer;
}
.archetype-banner details summary {
  font-weight: 500; color: #78350f; padding: 4px 0;
}
.archetype-banner details ul {
  margin: 8px 0 0 20px; padding: 0;
}
.archetype-banner details li { margin: 4px 0; }
.archetype-banner .archetype-impact {
  margin-top: 12px; padding-top: 12px; border-top: 1px dashed #d97706;
  font-size: 13px; color: #1f2937;
}

@media print {
  .archetype-banner { background: #fef3c7; }
}
"""


POS_MAP_SCRIPT = """<script>
(function() {
  function isMap(t) {
    return t.indexOf('^') >= 0 && /GÓC/i.test(t);
  }
  function roman(n) { return ['I','II','III','IV'][n-1] || String(n); }
  function fromRoman(s) {
    return {'I':1,'II':2,'III':3,'IV':4}[(s||'').toUpperCase().trim()] || 0;
  }
  function parseMap(text) {
    var lines = text.split('\\n'), n = lines.length;
    var hIdx = -1;
    for (var i = 0; i < n; i++) {
      if (/[-─]{4,}/.test(lines[i])) { hIdx = i; break; }
    }
    if (hIdx < 0) return null;
    var cols = {}, vCol = 0, mx = 0;
    lines.forEach(function(l) {
      for (var j = 0; j < l.length; j++) if (l[j] === '|') cols[j] = (cols[j]||0) + 1;
    });
    Object.keys(cols).forEach(function(j) { if (cols[j] > mx) { mx = cols[j]; vCol = +j; } });
    if (!mx) vCol = Math.floor((lines[hIdx]||'').length / 2);
    var yTop = '', yBottom = '', xRight = '', xLeft = '';
    for (var i = 0; i < hIdx; i++) {
      if (lines[i].indexOf('^') >= 0) {
        var t = lines[i].replace(/\^/g,'').replace(/\|/g,'').trim();
        yTop = t || (i > 0 ? lines[i-1].replace(/\|/g,'').trim() : '');
        break;
      }
    }
    for (var i = hIdx + 1; i < n; i++) {
      if (/^\\s*v\\s*$/.test(lines[i]) || lines[i].trim() === 'v') {
        yBottom = (i+1 < n ? lines[i+1] : '').replace(/\\|/g,'').trim();
        break;
      }
    }
    var axL = lines[hIdx] || '';
    var ar = axL.match(/[-─>]+\\s*(.+)$/); if (ar) xRight = ar[1].trim();
    var lr = axL.match(/^([^─\\-|+]+)[-─]/); if (lr) xLeft = lr[1].trim();
    var qdesc = {1:'',2:'',3:'',4:''};
    var gr = /GÓC\\s*(IV|III|II|I)\\s*[:\\-—\\(]?\\s*([^\\n|\\)]{0,60})/gi, gm;
    while ((gm = gr.exec(text)) !== null) {
      var num = fromRoman(gm[1]);
      if (num >= 1 && num <= 4) qdesc[num] = gm[2].replace(/[\\)\\]]/g,'').trim();
    }
    var items = {1:[],2:[],3:[],4:[]}, seen = {1:[],2:[],3:[],4:[]};
    for (var row = 0; row < n; row++) {
      if (row === hIdx) continue;
      var line = lines[row], isTop = row < hIdx;
      var ir = /(?:[•·●♦★→]|\\[)([^\\]•·●♦★→\\n|]{2,35})(?:\\])?/g, im;
      while ((im = ir.exec(line)) !== null) {
        var item = im[1].trim().replace(/[\\[\\]\\(\\)]/g,'');
        if (!item || /GÓC|TRỐNG/i.test(item)) continue;
        var q = isTop ? (im.index >= vCol ? 1 : 2) : (im.index >= vCol ? 4 : 3);
        if (seen[q].indexOf(item) < 0) { seen[q].push(item); items[q].push(item); }
      }
    }
    return {yTop:yTop, yBottom:yBottom, xRight:xRight, xLeft:xLeft, qdesc:qdesc, items:items};
  }
  function mk(tag, cls, text) {
    var el = document.createElement(tag);
    if (cls) el.className = cls;
    if (text !== undefined) el.textContent = text;
    return el;
  }
  function buildEl(map) {
    var w = mk('div','pos-map-wrap');
    w.appendChild(mk('div','pos-map-title','📍 Bản đồ Định vị Cạnh tranh'));
    if (map.yTop) w.appendChild(mk('div','pos-y-lbl top','↑ ' + map.yTop));
    var qg = mk('div','pos-quads');
    [[2,'pq2'],[1,'pq1'],[3,'pq3'],[4,'pq4']].forEach(function(p) {
      var qn = p[0], q = mk('div','pos-q ' + p[1]);
      q.appendChild(mk('div','pos-q-lbl','GÓC ' + roman(qn)));
      if (map.qdesc[qn]) q.appendChild(mk('div','pos-q-desc', map.qdesc[qn]));
      var qi = mk('div','pos-q-items');
      map.items[qn].forEach(function(it) {
        var isSelf = /SếP|sếp|★|self/.test(it);
        qi.appendChild(mk('span','pos-item' + (isSelf ? ' pos-item-self' : ''), it));
      });
      q.appendChild(qi);
      qg.appendChild(q);
    });
    w.appendChild(qg);
    if (map.yBottom) w.appendChild(mk('div','pos-y-lbl bot','↓ ' + map.yBottom));
    if (map.xLeft || map.xRight) {
      var xa = mk('div','pos-x-axis');
      if (map.xLeft) xa.appendChild(mk('span','pos-x-l','← ' + map.xLeft));
      xa.appendChild(mk('div','pos-x-line'));
      if (map.xRight) xa.appendChild(mk('span','pos-x-r', map.xRight + ' →'));
      w.appendChild(xa);
    }
    return w;
  }
  document.querySelectorAll('pre').forEach(function(pre) {
    var text = (pre.querySelector('code') || pre).textContent || '';
    if (!isMap(text)) return;
    var map = parseMap(text);
    if (!map) return;
    pre.parentNode.replaceChild(buildEl(map), pre);
  });
})();
</script>"""


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{report_title} — {business_name}</title>
<style>{css}
{tab_rules}</style>
</head>
<body>
<div class="container">

  {radio_inputs}

  <div class="header">
    <h1>{report_title}</h1>
    <div class="meta">
      🏢 <strong>{business_name}</strong> · {industry} · Stage: {stage}<br>
      📅 {date}
    </div>
    <div class="powered">Powered by Max — AI CMO · Marketing OS</div>
  </div>

  <div class="tabs">
    {tabs_html}
  </div>

  {sections_html}

  <div class="footer">
    Generated by <strong>Max — AI CMO</strong> · Marketing OS<br>
    Phân tích dựa trên thông tin business + framework KPI / SAVE / SMART<br>
    Không phải lời khuyên đầu tư — cross-check thực tế trước khi quyết định lớn
  </div>

</div>
{pos_map_script}
</body>
</html>"""


def _ensure_blank_line_before_tables(text: str) -> str:
    """Python-Markdown chỉ render bảng khi có DÒNG TRỐNG ngay trước bảng.
    LLM thường viết 'Tuần 1 ...\\n| Ngày | Kênh |' (không có dòng trống) → bảng
    bị render thành text thô với dấu '|'. Chèn 1 dòng trống trước mỗi block bảng."""
    lines = text.split("\n")
    out: list[str] = []
    for line in lines:
        is_table_row = line.lstrip().startswith("|")
        if is_table_row and out:
            prev = out[-1]
            prev_is_table = prev.lstrip().startswith("|")
            # Dòng trước là text thường (không trống, không phải row bảng) → chèn blank
            if prev.strip() and not prev_is_table:
                out.append("")
        out.append(line)
    return "\n".join(out)


def _md_to_html(text: str) -> str:
    """Convert markdown → HTML. Falls back to <pre> if no markdown lib available."""
    if not text:
        return ""
    if HAS_MARKDOWN:
        text = _ensure_blank_line_before_tables(text)
        html = _md.markdown(text, extensions=["tables", "fenced_code", "nl2br", "sane_lists"])
        # Wrap <table> in scroll container so wide tables (e.g. 11-col calendar) scroll on mobile
        html = re.sub(r"<table>", '<div class="table-wrap"><table>', html)
        html = re.sub(r"</table>", "</table></div>", html)
        return html
    # Fallback: basic conversion
    out = text
    out = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", out)
    out = re.sub(r"\*(.+?)\*", r"<em>\1</em>", out)
    out = out.replace("\n\n", "</p><p>")
    out = out.replace("\n", "<br>")
    return f"<p>{out}</p>"


def parse_agent_output(text: str) -> dict:
    """Extract structured sections from agent output.
    Returns {insight, summary, benchmarks, detail, summary_label} — all strings (markdown).

    Named sections (insight/summary/benchmarks) get special card boxes.
    Everything else — including numbered strategy sections like
    '## 1. Executive Summary', '## 2. USP', etc. — accumulates as detail.

    SWOT format auto-detected by 💪/⚠️/🌟/⚡ headers:
      - S/W/O/T quadrant sections → detail (rendered as h2 blocks)
      - 🔀 MA TRẬN CHIẾN LƯỢC → summary card (relabeled "📋 Ma Trận Chiến Lược")
    """
    result = {"insight": "", "summary": "", "benchmarks": "", "detail": "", "summary_label": ""}

    # Split into ## sections; prepend \n so the first header is also caught
    chunks = re.split(r'(?=\n##[ \t])', "\n" + text)
    detail_parts = []

    # Pre-scan: detect SWOT format by looking for quadrant emoji in any ## header
    is_swot = any(
        re.search(r'##[ \t]+(?:💪|⚠|🌟|⚡)', chunk)
        for chunk in chunks
    )

    for chunk in chunks:
        chunk = chunk.strip()
        if not chunk:
            continue

        m = re.match(r'^##[ \t]+([^\n]+)\n+(.*)', chunk, re.DOTALL)
        if not m:
            # Pre-header preamble — treat as detail if substantial
            if len(chunk) > 50:
                detail_parts.append(chunk)
            continue

        header = m.group(1).strip()
        content = m.group(2).strip()

        if is_swot:
            # SWOT quadrant sections → detail block; strategy matrix → summary card
            if re.search(r'💪|⚠|🌟|⚡', header):
                detail_parts.append(f"## {header}\n\n{content}")
            elif re.search(r'🔀', header) or re.match(r'MA\s*TR[ÂA]N', header, re.IGNORECASE):
                result["summary"] = content
                result["summary_label"] = "📋 Ma Trận Chiến Lược"
            else:
                detail_parts.append(f"## {header}\n\n{content}")
            continue

        # Classify by emoji first (reliable), then by keyword
        if re.search(r'[💡🔑⭐✨]', header) or re.match(r'Insight\b', header, re.IGNORECASE):
            result["insight"] = content
        elif (re.search(r'[🎯📌📝]', header)
              or re.match(r'(?:Tóm tắt|Tom\s*tat)\b', header, re.IGNORECASE)
              or re.match(r'Summary\s*$', header, re.IGNORECASE)):
            # re.match anchors at start → "Executive Summary" won't match "Summary$"
            result["summary"] = content
        elif (re.search(r'[📊📈📉]', header)
              or re.match(r'(?:Benchmarks?|KPIs?|Số liệu)\b', header, re.IGNORECASE)):
            result["benchmarks"] = content
        elif re.match(r'(?:Phân tích chi tiết|Phan\s*tich|Chi tiết|Full\s*analysis|Detail)\b',
                      header, re.IGNORECASE):
            result["detail"] = content
        else:
            # Numbered sections (## 1. Executive Summary, ## 2. USP …) and any
            # other unclassified headers → accumulate as rich detail content
            detail_parts.append(f"## {header}\n\n{content}")

    # Merge unclassified sections into detail when no explicit detail section exists
    if not result["detail"] and detail_parts:
        result["detail"] = "\n\n".join(detail_parts)

    # Final fallback: nothing parsed at all → entire text is detail
    if not any(v for k, v in result.items() if k != "summary_label"):
        result["detail"] = text.strip()

    return result


def render_stage_html(
    stage_key: str,
    parsed: dict,
    idx: int,
    archetype_banner: str = "",
) -> str:
    """Render one stage as a CSS-only tabbed section with data-idx attribute.

    archetype_banner: pre-rendered HTML. Hiển thị ở đầu section content nếu
    (a) stage_key thuộc allowlist HOẶC (b) section content nhắc archetype.
    Pass "" để skip banner cho section này.
    """
    meta = STAGE_META.get(stage_key, {"title": stage_key, "icon": "📄", "color": ""})

    # Decide có hiện banner cho section này không
    show_banner = bool(archetype_banner) and (
        stage_key in _ARCHETYPE_RELEVANT_KEYS
        or _section_mentions_archetype(parsed)
    )

    # Order: Banner (nếu có) → Insight (hook) → Detail (full) → Summary (recap) → Benchmarks (bottom)
    parts = []
    if show_banner:
        parts.append(archetype_banner)
    if parsed.get("insight"):
        insight = parsed["insight"].strip().strip('"').strip("'")
        parts.append(f'<div class="insight">{_md_to_html(insight)}</div>')
    if parsed.get("detail"):
        parts.append(f'<div class="content">{_md_to_html(parsed["detail"])}</div>')
    if parsed.get("summary"):
        summary_label = parsed.get("summary_label") or "📌 Tóm tắt"
        parts.append(f'<div class="summary"><div class="summary-label">{summary_label}</div>'
                     f'{_md_to_html(parsed["summary"])}</div>')
    if parsed.get("benchmarks"):
        parts.append('<div class="benchmarks"><div class="benchmarks-label">📊 Benchmarks</div>'
                     f'{_md_to_html(parsed["benchmarks"])}</div>')

    body = "\n".join(parts)
    return f"""
<div class="section {meta['color']}" data-idx="{idx}">
  <div class="section-header">
    <span class="icon">{meta['icon']}</span>
    <h2>{meta['title']}</h2>
  </div>
  {body}
</div>"""


def _generate_tab_css(n: int) -> str:
    """Generate per-tab CSS rules: when radio i is checked, show section i + highlight button i."""
    rules = []
    for i in range(n):
        rules.append(
            f"#tab-{i}:checked ~ .section[data-idx='{i}'] {{ display: block; }}"
        )
        rules.append(
            f"#tab-{i}:checked ~ .tabs label[for='tab-{i}'] "
            f"{{ background: var(--primary); color: white; font-weight: 600; }}"
        )
    return "\n".join(rules)


def render_bar_chart(title: str, items: list[dict]) -> str:
    """Bar chart ngang. items = [{"label","value","display"}] — value quyết định
    độ dài thanh, display là text hiện trong thanh (vd '303 leads · 11.3K/lead')."""
    if not items:
        return ""
    max_val = max((it.get("value") or 0) for it in items) or 1
    palette = ["c1", "c2", "c3", "c4", "c5"]
    rows = []
    for i, it in enumerate(items):
        pct = max(10, round((it.get("value") or 0) / max_val * 100))
        cls = palette[min(i, len(palette) - 1)]
        label = (it.get("label") or "").replace("<", "&lt;").replace(">", "&gt;")
        display = (it.get("display") or str(it.get("value") or "")).replace("<", "&lt;").replace(">", "&gt;")
        rows.append(
            f'<div class="barchart-row">'
            f'<div class="barchart-label">{label}</div>'
            f'<div class="barchart-track"><div class="barchart-fill {cls}" style="width:{pct}%">{display}</div></div>'
            f'</div>'
        )
    return f'<div class="barchart"><div class="barchart-title">{title}</div>{"".join(rows)}</div>'


def render_ads_table(columns: list[str], rows: list[dict]) -> str:
    """Bảng kèm pill badge inline ở cột đầu.
    rows = [{"cells": [...], "badge": "Win #1" | None, "badge_cls": "pill-win" | "pill-best"}]."""
    if not rows:
        return ""
    head = "".join(f"<th>{c}</th>" for c in columns)
    body = []
    for r in rows:
        cells = r.get("cells") or []
        badge = r.get("badge")
        badge_html = f' <span class="pill {r.get("badge_cls", "pill-win")}">{badge}</span>' if badge else ""
        tds = "".join(f"<td>{c}{badge_html if i == 0 else ''}</td>" for i, c in enumerate(cells))
        body.append(f"<tr>{tds}</tr>")
    return (
        '<div class="table-wrap"><table><thead><tr>' + head + '</tr></thead>'
        '<tbody>' + "".join(body) + '</tbody></table></div>'
    )


def render_insight_grid(good_title: str, good_items: list[str], warn_title: str, warn_items: list[str]) -> str:
    """Lưới 2 cột: pattern thắng (xanh, ●) vs điểm cần chú ý (vàng, ▲)."""
    def _card(cls: str, title: str, items: list[str]) -> str:
        lis = "".join(f"<li>{it}</li>" for it in items)
        return f'<div class="insight-card {cls}"><div class="insight-card-title">{title}</div><ul>{lis}</ul></div>'
    return f'<div class="insight-grid">{_card("good", good_title, good_items)}{_card("warn", warn_title, warn_items)}</div>'


def build_ads_dashboard_report(
    account_name: str,
    period_label: str,
    bar_chart_title: str,
    bar_chart_items: list[dict],
    table_title: str,
    table_columns: list[str],
    table_rows: list[dict],
    good_title: str,
    good_items: list[str],
    warn_title: str,
    warn_items: list[str],
    business_name: str = "",
    industry: str = "",
    stage: str = "",
) -> str:
    """Render dashboard hiệu suất Ads dạng visual: bar chart leads theo campaign +
    bảng top ads (kèm pill badge) + lưới insight 2 cột (pattern thắng / điểm cần chú ý)."""
    section_body = "".join(filter(None, [
        render_bar_chart(bar_chart_title, bar_chart_items),
        f"<h2>{table_title}</h2>" if table_title else "",
        render_ads_table(table_columns, table_rows),
        "<h2>📌 Insight</h2>",
        render_insight_grid(good_title, good_items, warn_title, warn_items),
    ]))
    section_html = f"""
<div class="section strategy active" data-idx="0">
  <div class="section-header">
    <span class="icon">📈</span>
    <h2>{period_label} — {account_name}</h2>
  </div>
  <div class="content">{section_body}</div>
</div>"""

    radio = '<input type="radio" name="tab" id="tab-0" class="tab-state" checked>'
    tab_label = '<label for="tab-0" class="tab-btn"><span>📈</span> Báo cáo Ads</label>'

    return HTML_TEMPLATE.format(
        report_title=f"📈 Báo Cáo Hiệu Suất Ads — {account_name}",
        business_name=business_name or account_name or "Business",
        industry=industry or "—",
        stage=stage or "—",
        date=datetime.now().strftime("%d/%m/%Y · %H:%M"),
        radio_inputs=radio,
        tabs_html=tab_label,
        sections_html=section_html,
        css=CSS,
        tab_rules=_generate_tab_css(1),
        pos_map_script=POS_MAP_SCRIPT,
    )


def build_single_skill_report(
    skill_key: str,
    parsed: dict,
    output_format,  # OutputFormat enum
    business_name: str = "",
    industry: str = "",
    stage: str = "",
) -> str:
    """Render HTML for a standalone skill output (operational skills).
    Single tab, single section — no aggregate report."""
    from agents.skills import OutputFormat

    meta = STAGE_META.get(skill_key, {"title": skill_key, "icon": "📄", "color": ""})

    # Compose section body based on output format
    parts = []
    if output_format == OutputFormat.OPERATIONAL_DELIVERABLE:
        if parsed.get("summary"):
            parts.append('<div class="summary"><div class="summary-label">🎯 Tóm tắt nhanh</div>'
                         f'{_md_to_html(parsed["summary"])}</div>')
        if parsed.get("deliverable"):
            parts.append(f'<div class="content">{_md_to_html(parsed["deliverable"])}</div>')
    elif output_format == OutputFormat.OPERATIONAL_ANALYSIS:
        # Order: Summary → KPI table → Root cause → Actions → Forecast
        if parsed.get("summary"):
            parts.append(f'<div class="insight">{_md_to_html(parsed["summary"])}</div>')
        if parsed.get("kpi_table"):
            parts.append('<div class="content"><h2>📈 Kết quả vs KPI</h2>'
                         f'{_md_to_html(parsed["kpi_table"])}</div>')
        if parsed.get("root_cause"):
            parts.append('<div class="content"><h2>🔬 Phân tích nguyên nhân</h2>'
                         f'{_md_to_html(parsed["root_cause"])}</div>')
        if parsed.get("actions"):
            parts.append('<div class="content"><h2>🎯 Next Actions</h2>'
                         f'{_md_to_html(parsed["actions"])}</div>')
        if parsed.get("forecast"):
            parts.append('<div class="content"><h2>📉 Dự báo</h2>'
                         f'{_md_to_html(parsed["forecast"])}</div>')
    else:
        # Strategic 4-section fallback
        if parsed.get("insight"):
            insight = parsed["insight"].strip().strip('"').strip("'")
            parts.append(f'<div class="insight">{_md_to_html(insight)}</div>')
        if parsed.get("detail"):
            parts.append(f'<div class="content">{_md_to_html(parsed["detail"])}</div>')
        if parsed.get("summary"):
            summary_label = parsed.get("summary_label") or "📌 Tóm tắt"
            parts.append(f'<div class="summary"><div class="summary-label">{summary_label}</div>'
                         f'{_md_to_html(parsed["summary"])}</div>')
        if parsed.get("benchmarks"):
            parts.append('<div class="benchmarks"><div class="benchmarks-label">📊 Benchmarks</div>'
                         f'{_md_to_html(parsed["benchmarks"])}</div>')

    body = "\n".join(parts)
    section_html = f"""
<div class="section {meta['color']} active" data-idx="0">
  <div class="section-header">
    <span class="icon">{meta['icon']}</span>
    <h2>{meta['title']}</h2>
  </div>
  {body}
</div>"""

    # Single tab with skill name
    radio = '<input type="radio" name="tab" id="tab-0" class="tab-state" checked>'
    tab_label = (
        f'<label for="tab-0" class="tab-btn">'
        f'<span>{meta["icon"]}</span> {meta["title"]}'
        f'</label>'
    )

    return HTML_TEMPLATE.format(
        report_title=f"{meta['icon']} {meta['title']}",
        business_name=business_name or "Business",
        industry=industry or "—",
        stage=stage or "—",
        date=datetime.now().strftime("%d/%m/%Y · %H:%M"),
        radio_inputs=radio,
        tabs_html=tab_label,
        sections_html=section_html,
        css=CSS,
        tab_rules=_generate_tab_css(1),
        pos_map_script=POS_MAP_SCRIPT,
    )


# ─────────────────────────────────────────────────────────────────
# Archetype banner — giải thích archetype mua hàng để user hiểu plan
# ─────────────────────────────────────────────────────────────────

# Industry code → label tiếng Việt (cho fallback template — bỏ raw key như "fnb")
_INDUSTRY_VI = {
    "fnb":                  "đồ ăn uống",
    "tech_saas":            "phần mềm SaaS",
    "ecommerce":            "thương mại điện tử",
    "education":            "giáo dục",
    "health_beauty":        "làm đẹp",
    "retail":               "bán lẻ",
    "b2b_service":          "dịch vụ B2B",
    "real_estate":          "bất động sản",
    "health_clinic":        "y tế / phòng khám",
    "agency":               "agency marketing",
    "fashion_retail":       "thời trang",
    "travel_hospitality":   "du lịch / khách sạn",
    "interior_design":      "thiết kế nội thất",
    "pet_care":             "chăm sóc thú cưng",
    "events_wedding":       "sự kiện / cưới hỏi",
}

# Section keys luôn nhận banner (cấu trúc bám archetype) — Phần A allowlist
_ARCHETYPE_RELEVANT_KEYS = {"strategy", "synthesis", "tactical_playbook", "campaign_plan", "campaign_brief"}

# Keyword bắt mention archetype organic ở section khác — Phần A detect động
# CHÚ Ý: KHÔNG dùng bare "impulse" (false positive với "impulse buy" trong pricing/SWOT)
_ARCHETYPE_KEYWORDS = (
    "archetype",
    "demand-gen", "demand_gen", "demand-generation",
    "trust-building", "trust_building",
    "archetype impulse", "mua theo impulse",
)


def _section_mentions_archetype(parsed: dict) -> bool:
    """Detect động: section có chữ archetype trong content không."""
    blob = " ".join(filter(None, [
        parsed.get("detail", ""),
        parsed.get("insight", ""),
        parsed.get("summary", ""),
    ])).lower()
    return any(k in blob for k in _ARCHETYPE_KEYWORDS)


# Template fallback per archetype (label + diagnosis + plan_impact)
# Placeholder: {business_name}, {industry_vi}
_ARCHETYPE_TEMPLATES = {
    "trust_building": {
        "label": "Trust-building",
        "diagnosis": (
            "Khách của {business_name} BIẾT mình có vấn đề nhưng chu kỳ ra quyết định "
            "dài — họ research kỹ trước khi chốt. Với nhóm này, brand đẹp chưa đủ; phải "
            "xây authority + chuyên môn sâu thì mới có lead. Trong ngành {industry_vi}, "
            "kết quả không đến từ ads đẹp mà từ thought leadership được công nhận."
        ),
        "impact": (
            "Plan ưu tiên proof + case study + chia sẻ chuyên môn, kênh thiên long-form "
            "(LinkedIn, blog, podcast). Offer chỉ pitch sau khi đã build trust."
        ),
    },
    "demand_gen": {
        "label": "Demand-generation",
        "diagnosis": (
            "Khách của {business_name} thường không tự nghĩ tới chuyện mua — họ chỉ "
            "mua khi content khơi gợi được desire (lifestyle, aspiration, FOMO). Với "
            "nhóm này, content phải tạo nhu cầu TRƯỚC khi pitch sản phẩm, và brand "
            "mạnh thường đẩy được giá cao hơn baseline ngành {industry_vi}."
        ),
        "impact": (
            "Plan ưu tiên content lifestyle / desire trigger, kênh video-first "
            "(TikTok, Reels). Offer chỉ chốt khi desire đã đủ chín."
        ),
    },
    "impulse": {
        "label": "Impulse purchase",
        "diagnosis": (
            "Khách của {business_name} mua nhanh theo cảm xúc, ít cân nhắc — họ chốt "
            "trong 1-2 phút nếu thấy hook đủ mạnh hoặc deal đủ hời. Với nhóm này, ads "
            "tốt = ra đơn, brand mạnh là cộng thêm chứ không phải điều kiện cần. Trong "
            "ngành {industry_vi}, ai có hook + price anchor đúng sẽ thắng."
        ),
        "impact": (
            "Plan ưu tiên hook nhanh, social proof định lượng, price anchor / flash deal, "
            "kênh promo-heavy (Shopee Live, Reels promo, Meta Ads + retarget)."
        ),
    },
}


def _resolve_or_none(industry: str, signal_text: str = "") -> dict | None:
    """Wrapper resolve_archetype — return None nếu fail import hoặc không có primary."""
    try:
        from frameworks.industry_context import resolve_archetype
    except ImportError:
        return None
    res = resolve_archetype(industry or "", signal_text or "")
    if not res.get("primary") or res["primary"] not in _ARCHETYPE_TEMPLATES:
        return None
    return res


def _extract_context_snippets(parsed_stages: list[tuple[str, dict]]) -> str:
    """Trích summary/insight từ market_research + customer_insight + usp_definition → context cho LLM.

    Mỗi snippet tối đa 500 char, gắn nhãn section để LLM biết nguồn.
    """
    if not parsed_stages:
        return ""

    wanted_keys = {
        "market_research": "Nghiên cứu Thị trường",
        "market":          "Nghiên cứu Thị trường",
        "customer_insight": "Customer Insight",
        "customer":         "Customer Insight",
        "usp_definition":   "USP Definition",
    }
    snippets = []
    for key, parsed in parsed_stages:
        label = wanted_keys.get(key)
        if not label:
            continue
        text = (parsed.get("insight") or parsed.get("summary") or parsed.get("detail") or "").strip()
        if not text:
            continue
        # Strip markdown headers/bullets cho LLM đỡ nhiễu
        text = re.sub(r'^[#>*\-\s]+', '', text, flags=re.MULTILINE)
        text = re.sub(r'\s+', ' ', text)[:500]
        snippets.append(f"[{label}]\n{text}")

    return "\n\n".join(snippets[:3])


def _template_banner_data(business_name: str, industry: str, archetype_result: dict) -> dict:
    """Fallback template — fill business_name + industry_vi vào template tĩnh."""
    primary = archetype_result["primary"]
    template = _ARCHETYPE_TEMPLATES[primary]
    industry_vi = _INDUSTRY_VI.get(industry.lower(), "ngành của sếp")
    bn = business_name or "brand"
    return {
        "label":     template["label"],
        "diagnosis": template["diagnosis"].format(business_name=bn, industry_vi=industry_vi),
        "impact":    template["impact"].format(business_name=bn, industry_vi=industry_vi),
    }


async def _generate_banner_copy_via_llm(
    business_name: str,
    industry: str,
    archetype_result: dict,
    context_snippets: str,
) -> dict | None:
    """LLM-first path — gen 2-3 câu personalize từ context. None nếu fail.

    Returns: {label, diagnosis, impact} hoặc None.
    """
    try:
        from tools.llm_router import call as router_call, TaskType, AllProvidersFailedError
        from frameworks.industry_context import ARCHETYPE_LABEL
    except ImportError:
        return None

    primary = archetype_result["primary"]
    label_full = ARCHETYPE_LABEL.get(primary, primary).split(" (")[0]  # bỏ phần ngoặc giải nghĩa
    industry_vi = _INDUSTRY_VI.get(industry.lower(), industry)
    flipped = archetype_result.get("flipped", False)
    matched = archetype_result.get("matched_signals") or []

    system = (
        "Bạn viết 2-3 câu chẩn đoán archetype mua hàng cho 1 business cụ thể. "
        "KHÔNG dùng jargon framework (TOFU/MOFU/BOFU, content_pillars, funnel ratio, CAC, LTV). "
        "KHÔNG kể framework theo kiểu giáo trình. "
        "Nói như 1 cố vấn quen brand đó — gọi tên brand, dẫn 1-2 chi tiết cụ thể từ context "
        "(competitor name, geo, target audience, insight quan trọng). "
        "🔴 CHỐNG BỊA (BẮT BUỘC): CHỈ dùng tên đối thủ / nhân khẩu (tuổi, Gen Z...) / "
        "segment / địa lý CÓ trong context được cung cấp. TUYỆT ĐỐI không tự bịa "
        "competitor (vd 'Zara') hay nhân khẩu (vd 'Gen Z') không xuất hiện trong context. "
        "Nếu context không nêu chi tiết đó → nói chung chung, thận trọng theo đúng "
        "archetype + ngành, KHÔNG điền chi tiết tưởng tượng. "
        "Output JSON đúng schema, KHÔNG markdown wrapper."
    )

    user_parts = [
        "# Business",
        f"- Tên brand: {business_name}",
        f"- Ngành: {industry_vi}",
        f"- Archetype mua hàng: {label_full}",
    ]
    if flipped and matched:
        user_parts.append(f"- Lưu ý: archetype này đã được flip từ default vì brief có signal: {', '.join(matched)}.")
    if context_snippets:
        user_parts += ["", "# Context từ các section đã phân tích", context_snippets]
    user_parts += [
        "",
        "# Yêu cầu output",
        "Trả về JSON với 2 field:",
        '- "diagnosis": 2-3 câu chẩn đoán — vì sao brand này thuộc archetype X, dẫn chứng cụ thể từ context.',
        '- "plan_impact": 1 câu — plan dưới đây sẽ làm gì cụ thể với business này (kênh / hướng content cụ thể).',
        "",
        "Văn phong: tư vấn thân mật ('khách của brand', 'plan dưới đây'), không công thức.",
        'Ví dụ structure: {"diagnosis": "...", "plan_impact": "..."}',
    ]

    try:
        result = await router_call(
            task_type  = TaskType.INTAKE_JSON,
            system     = system,
            user       = "\n".join(user_parts),
            max_tokens = 500,
        )
    except AllProvidersFailedError:
        return None
    except Exception:
        return None

    raw = (result or {}).get("output", "").strip()
    if not raw:
        return None

    # Strip ```json wrapper nếu có
    raw = re.sub(r'^```(?:json)?\s*', '', raw)
    raw = re.sub(r'\s*```\s*$', '', raw).strip()

    import json
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        return None

    diagnosis = (data.get("diagnosis") or "").strip()
    plan_impact = (data.get("plan_impact") or "").strip()
    if not diagnosis or not plan_impact:
        return None

    return {
        "label":     label_full,
        "diagnosis": diagnosis,
        "impact":    plan_impact,
    }


def _compose_banner_html(
    business_name: str,
    banner_data: dict,
    archetype_result: dict,
) -> str:
    """Compose HTML từ banner_data (label + diagnosis + impact) + flip signal nếu có."""
    label = banner_data["label"]
    bn = business_name or "brand"

    # Flip signal — chỉ hiện 1 dòng inline, không lặp lại comparison block
    flip_html = ""
    if archetype_result.get("flipped"):
        matched = archetype_result.get("matched_signals") or []
        signals_str = ", ".join(f"<em>{s}</em>" for s in matched)
        flip_html = (
            f'<div class="archetype-flip">⚡ Đã chuyển sang <strong>{label}</strong> '
            f'vì brief có signal: {signals_str}.</div>'
        )

    return (
        '<div class="archetype-banner">'
        '<div class="archetype-head">'
        '<span class="icon">🎯</span>'
        f'<h3>Khách của {bn} thuộc nhóm {label}</h3>'
        '</div>'
        f'<div class="archetype-diagnosis">{banner_data["diagnosis"]}</div>'
        f'{flip_html}'
        f'<div class="archetype-impact">{banner_data["impact"]}</div>'
        '</div>'
    )


async def generate_archetype_banner_html(
    business_name: str,
    industry: str,
    signal_text: str,
    parsed_stages: list[tuple[str, dict]] | None = None,
) -> str:
    """Async entry — LLM-first + template fallback.

    Trả về "" nếu industry không có archetype declaration (skip banner).
    """
    res = _resolve_or_none(industry, signal_text)
    if not res:
        return ""

    # LLM primary path — CHỈ khi có context để bám (chống bịa segment/đối thủ).
    # Không context → LLM dễ điền chi tiết tưởng tượng (vd "Gen Z/Zara") → dùng template.
    context_snippets = _extract_context_snippets(parsed_stages or [])
    data = None
    if context_snippets:
        data = await _generate_banner_copy_via_llm(business_name, industry, res, context_snippets)

    # Fallback template nếu không có context / LLM fail / empty / parse error
    if not data:
        data = _template_banner_data(business_name, industry, res)

    return _compose_banner_html(business_name, data, res)


def render_archetype_banner_sync(business_name: str, industry: str, signal_text: str = "") -> str:
    """Sync entry — chỉ dùng template (không gọi LLM). Cho build_single_skill_report
    và build_ads_dashboard_report (vốn không có context_snippets đầy đủ).

    Trả về "" nếu industry không có archetype declaration.
    """
    res = _resolve_or_none(industry, signal_text)
    if not res:
        return ""
    data = _template_banner_data(business_name, industry, res)
    return _compose_banner_html(business_name, data, res)


def build_report(
    business_name: str,
    industry: str,
    stage: str,
    parsed_stages: list[tuple[str, dict]],
    archetype_signal_text: str = "",
    archetype_banner_html: str | None = None,
) -> str:
    """Render full HTML report with CSS-only tab navigation (radio buttons, no JS).

    archetype_banner_html: pre-computed banner (đã async-gen từ LLM). Nếu None,
    fallback sang sync template render — giữ backward compat cho caller chưa
    await generate_archetype_banner_html().
    """
    n = len(parsed_stages)

    # Resolve banner — caller có thể pre-compute (LLM path) hoặc để None (sync fallback)
    if archetype_banner_html is None:
        archetype_banner_html = render_archetype_banner_sync(
            business_name, industry, archetype_signal_text
        )

    # Radio inputs at top — first one checked
    radio_inputs = "\n  ".join(
        f'<input type="radio" name="tab" id="tab-{i}" class="tab-state"'
        + (' checked' if i == 0 else '')
        + '>'
        for i in range(n)
    )

    # Tab labels (act as clickable buttons via <label for="...">)
    tab_labels = []
    for i, (k, _) in enumerate(parsed_stages):
        meta = STAGE_META.get(k, {"title": k, "icon": "📄"})
        tab_labels.append(
            f'<label for="tab-{i}" class="tab-btn">'
            f'<span>{meta["icon"]}</span> {meta["title"]}'
            f'</label>'
        )
    tabs_html = "\n    ".join(tab_labels)

    # Section blocks — banner inject vào section thuộc allowlist HOẶC detect động
    sections_html = "\n".join(
        render_stage_html(k, p, i, archetype_banner=archetype_banner_html)
        for i, (k, p) in enumerate(parsed_stages)
    )

    # Dynamic title: nhiều skill = full report; 1 skill = tên skill cụ thể
    if n == 1:
        single_meta = STAGE_META.get(parsed_stages[0][0], {"title": parsed_stages[0][0], "icon": "📄"})
        report_title = f"{single_meta['icon']} {single_meta['title']}"
    elif n >= 5:  # full A→Z pipeline (5+ stages)
        report_title = "📊 Kế Hoạch Marketing Đề Xuất"
    else:
        # 2-4 skills → liệt kê
        titles = []
        for k, _ in parsed_stages[:3]:
            m = STAGE_META.get(k, {"title": k})
            titles.append(m["title"])
        report_title = "📊 " + " · ".join(titles) + (f" + {n-3}" if n > 3 else "")

    return HTML_TEMPLATE.format(
        report_title=report_title,
        business_name=business_name or "Business",
        industry=industry or "—",
        stage=stage or "—",
        date=datetime.now().strftime("%d/%m/%Y · %H:%M"),
        radio_inputs=radio_inputs,
        tabs_html=tabs_html,
        sections_html=sections_html,
        css=CSS,
        tab_rules=_generate_tab_css(n),
        pos_map_script=POS_MAP_SCRIPT,
    )
