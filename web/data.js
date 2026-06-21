/* Marketing OS — mock data + navigation config (data thật nối sau) */
window.MOCK = {
  nav: [
    { group: '① Khám phá & Chẩn đoán', items: [
      { id: 'dossier', label: 'Hồ sơ doanh nghiệp', icon: '🗂️' },
    ]},
    { group: '② Chiến lược', items: [
      { id: 'strategy',   label: 'Chiến lược tổng hợp',   icon: '🎯' },
      { id: 'tactical',   label: 'Tactical Playbook',     icon: '🔨' },
    ]},
    { group: '③ Sản xuất', items: [
      { id: 'occasion', label: 'Lập chiến dịch',     icon: '🎯' },
      { id: 'calendar', label: 'Lịch nội dung',      icon: '🗓️' },
      { id: 'adscopy',  label: 'Quảng cáo (copy)',   icon: '🧲' },
      { id: 'inbox',    label: 'Sales Inbox Script', icon: '💬' },
      { id: 'sequence', label: 'Email / Zalo chuỗi', icon: '✉️' },
      { id: 'voice',    label: 'Brand Voice',        icon: '🗣️' },
    ]},
    { group: '④ Vận hành & Tối ưu', items: [
      { id: 'overview',     label: 'Tổng quan số liệu', icon: '📊' },
      { id: 'adsanalytics', label: 'Ads Analytics',  icon: '📈' },
      { id: 'optimizer',    label: 'Tối ưu tự động',  icon: '⚡' },
      { id: 'spy',          label: 'Theo dõi đối thủ', icon: '🕵️' },
      { id: 'schedule',     label: 'Lịch trình & cảnh báo', icon: '⏰' },
      { id: 'accounts',     label: 'Kết nối tài khoản', icon: '🔗' },
    ]},
    { group: '⑤ Học hỏi & Hệ thống', items: [
      { id: 'reports', label: 'Báo cáo',  icon: '📑' },
      { id: 'admin',   label: 'Quản trị', icon: '🛠️' },
      { id: 'settings',label: 'Cài đặt',  icon: '⚙️' },
    ]},
  ],

  // Hành trình khách hàng — context cho Max + thanh tiến trình
  journey: [
    { id: 'discovery', label: 'Khám phá',  icon: '🔍', page: 'dossier',  desc: 'Hiểu doanh nghiệp' },
    { id: 'diagnosis', label: 'Chẩn đoán', icon: '🩺', page: 'competitor', desc: 'Thị trường · đối thủ · khách hàng' },
    { id: 'strategy',  label: 'Chiến lược', icon: '🎯', page: 'strategy',  desc: 'Định vị · roadmap · KPI' },
    { id: 'execution', label: 'Sản xuất',  icon: '✍️', page: 'content',   desc: 'Nội dung · chiến dịch' },
    { id: 'run',       label: 'Vận hành',  icon: '📡', page: 'adsanalytics', desc: 'Chạy ads · tối ưu' },
  ],

  industries: ['F&B','Tech SaaS','E-commerce','Giáo dục','Health & Beauty','Bán lẻ','B2B Services','Bất động sản'],

  pipeline: [
    { name: 'Nghiên cứu thị trường', desc: 'TAM/SAM/SOM + động lực thị trường', status: 'done' },
    { name: 'Phân tích đối thủ',     desc: '8 đối thủ × 8 chiều', status: 'done' },
    { name: 'Customer Insight',      desc: 'ICP + JTBD + tâm lý', status: 'done' },
    { name: 'Định giá & Tâm lý',     desc: 'Mô hình giá + chiến thuật tâm lý', status: 'running' },
    { name: 'Social Listening',      desc: 'Tiếng nói khách hàng online', status: 'pending' },
    { name: 'Chiến lược tổng hợp',   desc: 'SAVE + SMART + roadmap 90 ngày', status: 'pending' },
  ],

  competitors: [
    { name: 'Đối thủ A', pos: 'Cao cấp', price: '$$$', usp: 'Thương hiệu mạnh', share: 28, threat: 'Cao' },
    { name: 'Đối thủ B', pos: 'Tầm trung', price: '$$', usp: 'Giá tốt', share: 19, threat: 'Trung bình' },
    { name: 'Đối thủ C', pos: 'Ngách', price: '$$$', usp: 'Cá nhân hóa', share: 12, threat: 'Trung bình' },
    { name: 'Đối thủ D', pos: 'Giá rẻ', price: '$', usp: 'Khuyến mãi liên tục', share: 9, threat: 'Thấp' },
  ],

  tracked: [
    { name: 'Highlands Coffee', ads: 24, status: 'online', last: '12 phút trước' },
    { name: 'Phúc Long',        ads: 17, status: 'online', last: '1 giờ trước' },
    { name: 'Katinat',          ads: 31, status: 'warn',   last: '3 giờ trước · 5 ad mới' },
  ],

  personas: [
    { name: 'Linh — Văn phòng', age: '25–34', job: 'Tiết kiệm thời gian buổi sáng', pain: 'Bận, ít thời gian', motiv: 'Tiện lợi & ổn định' },
    { name: 'Huy — Freelancer',  age: '22–30', job: 'Không gian làm việc',          pain: 'Hay đổi chỗ ngồi', motiv: 'Wifi & yên tĩnh' },
    { name: 'Mai — Sinh viên',   age: '18–24', job: 'Gặp gỡ bạn bè',                pain: 'Ngân sách hạn chế', motiv: 'Giá tốt, check-in đẹp' },
  ],

  pricingTiers: [
    { name: 'Economy', price: '29.000₫', tag: 'Dẫn dắt', items: ['Sản phẩm cơ bản','Không topping','Giờ thấp điểm'] },
    { name: 'Standard', price: '49.000₫', tag: 'Phổ biến', items: ['Size lớn','1 topping','Tích điểm'], hot: true },
    { name: 'Premium', price: '79.000₫', tag: 'Biên cao', items: ['Combo đôi','Topping cao cấp','Ưu tiên phục vụ'] },
  ],

  funnel: [
    { tier: 'Hiển thị', value: 1240000, cost: 'CPM 38.000₫', rate: '100%' },
    { tier: 'Click',    value: 42350,   cost: 'CPC 1.250₫',  rate: '3,4%' },
    { tier: 'Landing',  value: 36100,   cost: '—',           rate: '85%' },
    { tier: 'Lead',     value: 5240,    cost: 'CPL 9.600₫',  rate: '14,5%' },
    { tier: 'Booking',  value: 2380,    cost: 'CPA 21.100₫', rate: '45%' },
    { tier: 'Mua hàng', value: 1610,    cost: 'CPA 31.200₫', rate: '67%' },
  ],

  winners: [
    { name: 'CD Mùa hè — Video 9:16', roas: 4.1, spend: '2.1M', cpa: '24.000₫' },
    { name: 'Re-targeting 7 ngày',    roas: 5.3, spend: '1.4M', cpa: '18.500₫' },
  ],
  losers: [
    { name: 'Carousel SP cũ',  roas: 0.9, spend: '1.8M', cpa: '95.000₫' },
    { name: 'Lookalike 5%',    roas: 1.4, spend: '1.1M', cpa: '61.000₫' },
  ],

  optimizations: [
    { action: 'scale', text: 'Tăng ngân sách 20% — “Re-targeting 7 ngày”', why: 'ROAS 5,3x > mục tiêu', },
    { action: 'pause', text: 'Tạm dừng — “Carousel SP cũ”', why: 'CPA 95.000₫ vượt ngưỡng', },
    { action: 'dup',   text: 'Nhân bản — “Video 9:16” sang Lookalike 2%', why: 'Mẫu thắng, mở rộng', },
    { action: 'activate', text: 'Bật lại — “CD Tết” (theo lịch)', why: 'Đến khung giờ vàng', },
  ],

  jobs: [
    { name: 'Daily Digest',    when: '08:00 hằng ngày', status: 'on' },
    { name: 'Weekly Report',   when: 'Thứ 2, 08:00',    status: 'on' },
    { name: 'Alert Monitor',   when: 'Mỗi 4 giờ',        status: 'on' },
    { name: 'Token Refresh',   when: '02:00 hằng ngày', status: 'on' },
    { name: 'Snapshot Cleanup',when: 'CN, 03:00',        status: 'on' },
    { name: 'Competitor Monitor', when: 'Mỗi 1 giờ',     status: 'on' },
  ],

  thresholds: [
    { name: 'Frequency tối đa', value: '5,0' },
    { name: 'ROAS giảm cảnh báo', value: '20%' },
    { name: 'CPM tăng cảnh báo', value: '30%' },
  ],

  accounts: [
    { name: 'TK Quảng cáo 01', id: 'act_8842', status: 'online', spend: '8.2M/ngày' },
    { name: 'TK Quảng cáo 02', id: 'act_5510', status: 'off',    spend: 'Tạm dừng' },
  ],

  saveFramework: [
    { k: 'S', name: 'Solution — Giải pháp', text: 'Định khung theo vấn đề được giải quyết, không phải tính năng.' },
    { k: 'A', name: 'Access — Tiếp cận',    text: 'Kênh & cách mua khách hàng ưa thích (Maps, FB, Zalo OA).' },
    { k: 'V', name: 'Value — Giá trị',      text: 'Tổng giá trị cảm nhận vs lựa chọn thay thế + ROI.' },
    { k: 'E', name: 'Education — Giáo dục', text: 'Giáo dục nhu cầu TRƯỚC khi chào bán.' },
  ],

  // Định hướng theo giai đoạn (KHÔNG chốt số — số chốt khi lập chiến dịch, D-029/D-030)
  directionalGoals: [
    '0–30 ngày — ưu tiên NHẬN DIỆN: phủ thông điệp định vị, validate kênh & mẫu nội dung',
    '31–60 ngày — ưu tiên TƯƠNG TÁC / LEAD: nuôi tệp quan tâm, thu lead chất lượng',
    '61–90 ngày — ưu tiên CHUYỂN ĐỔI: tối ưu & scale cái đã có tín hiệu tốt',
  ],

  roadmap: [
    { phase: '0–30 ngày', title: 'Nền tảng', items: ['Chuẩn brand voice','Setup tracking','3 chiến dịch TOFU'] },
    { phase: '31–60 ngày', title: 'Tăng tốc', items: ['Scale mẫu thắng','Re-targeting funnel','Loyalty cơ bản'] },
    { phase: '61–90 ngày', title: 'Tối ưu', items: ['Lookalike mở rộng','Winback chuỗi','Tối ưu ngân sách'] },
  ],

  pillars: [
    { name: 'Educate', pct: 30, color: '#5b8cff' },
    { name: 'Trust',   pct: 25, color: '#7c4dff' },
    { name: 'Engage',  pct: 25, color: '#38d9f0' },
    { name: 'Convert', pct: 20, color: '#2dd4a7' },
  ],

  calendar: {
    days: ['T2','T3','T4','T5','T6','T7','CN'],
    posts: [
      [{p:'Educate',t:'Mẹo pha cà phê'}],
      [{p:'Engage',t:'Mini-game'}],
      [{p:'Trust',t:'Review KH'},{p:'Convert',t:'Flash sale combo đôi'}],
      [{p:'Educate',t:'Hậu trường'}],
      [{p:'Convert',t:'Mua 1 tặng 1 cuối tuần'}],
      [{p:'Engage',t:'UGC repost'}],
      [{p:'Trust',t:'Câu chuyện thương hiệu'}],
    ],
  },
  // Kế hoạch nội dung — mô hình ĐÚNG marketing:
  //  • alwaysOn = nền brand LẶP MỖI TUẦN, luôn chạy (không tắt khi có campaign)
  //  • campaigns = lớp CỘNG THÊM theo dịp, có window theo TUẦN, posts đẩy lên trên
  calendarPlan: {
    days: ['T2','T3','T4','T5','T6','T7','CN'],
    weeks: 4,
    alwaysOn: [
      { pillar:'Educate', title:'Mẹo pha cà phê tại nhà' },
      { pillar:'Engage',  title:'Mini-game đoán vị' },
      { pillar:'Trust',   title:'Review khách quen' },
      { pillar:'Educate', title:'Hậu trường pha chế' },
      { pillar:'Engage',  title:'UGC khách check-in' },
      { pillar:'Trust',   title:'Câu chuyện thương hiệu' },
      { pillar:'Educate', title:'Kiến thức hạt specialty' },
    ],
    campaigns: [
      { name:'Sale Hè', occasion:'Mùa hè', offer:'Mua 1 tặng 1', color:'#f59e0b',
        fromWeek:2, toWeek:3, posts:[
          { week:2, day:2, title:'Khởi động Sale Hè — Mua 1 tặng 1' },
          { week:2, day:5, title:'Flash sale cuối tuần' },
          { week:3, day:1, title:'Nhắc: Sale Hè sắp kết thúc' },
          { week:3, day:4, title:'Ngày cuối Mua 1 tặng 1' },
        ]},
    ],
  },

  // User mới = sạch: chưa có output nào (điền hồ sơ → bấm Chạy mới sinh)
  bizSkillRuns: [],
  sampleDocs: {},

  adsCopy: {
    TOFU: { title:'Nhận biết', items:['“Buổi sáng cần một lý do để dậy sớm…”','“Cà phê thật, giá thật.”'] },
    MOFU: { title:'Cân nhắc', items:['“3 lý do khách quay lại mỗi tuần”','So sánh: chúng tôi vs quán thường'] },
    BOFU: { title:'Chuyển đổi', items:['“Mua 1 tặng 1 — chỉ hôm nay”','Đặt trước, nhận ngay ưu đãi 20%'] },
  },

  sequence: [
    { day: 'Ngày 0', subj: 'Chào mừng + ưu đãi đầu tiên', open: '62%' },
    { day: 'Ngày 2', subj: 'Câu chuyện thương hiệu', open: '48%' },
    { day: 'Ngày 5', subj: 'Social proof + review', open: '41%' },
    { day: 'Ngày 9', subj: 'Ưu đãi giới hạn (winback)', open: '38%' },
  ],

  voice: {
    do: ['Gần gũi, thân thiện','Dùng “bạn” thay “quý khách”','Câu ngắn, dễ đọc','Có cảm xúc tích cực'],
    dont: ['Sáo rỗng, hô khẩu hiệu','Thuật ngữ khó','Cường điệu quá mức','Spam emoji'],
    tone: [ {k:'Trang trọng ↔ Thân mật', v:75}, {k:'Nghiêm túc ↔ Hài hước', v:60}, {k:'Chuyên gia ↔ Bạn bè', v:68} ],
  },

  users: [
    { id: '527…412', plan: 'Pro',  quota: 200000, used: 142300 },
    { id: '811…097', plan: 'Free', quota: 50000,  used: 49100 },
    { id: '344…820', plan: 'Pro',  quota: 200000, used: 88600 },
    { id: '905…173', plan: 'Team', quota: 500000, used: 215400 },
  ],

  reports: [
    { name: 'Báo cáo tuần — CD Mùa hè', date: '14/06/2026', type: 'Tuần' },
    { name: 'Chiến lược 90 ngày — Quán cà phê', date: '10/06/2026', type: 'Chiến lược' },
    { name: 'Phân tích đối thủ — Q2', date: '02/06/2026', type: 'Đối thủ' },
  ],

  alerts: [],

  settings: { daily_digest: 1, alert_threshold: 1, weekly_report: 1, competitor_new: 0 },

  campaigns: [
    { name: 'Mùa hè rực rỡ', status: 'running', budget: '6.5tr/ngày', objective: 'Chuyển đổi' },
    { name: 'Re-targeting Q2', status: 'running', budget: '3tr/ngày', objective: 'Doanh số' },
  ],
  calendarPosts: null,
};
