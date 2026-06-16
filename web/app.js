/* Auto Ads Facebook — dashboard charts (mock data demo) */
(function () {
  const css = getComputedStyle(document.documentElement);
  const c = (n) => css.getPropertyValue(n).trim();
  const PRIMARY = c('--primary'), PRIMARY2 = c('--primary-2'),
        GREEN = c('--green'), CYAN = c('--cyan'),
        TXT2 = c('--txt-2'), STROKE = c('--stroke');

  if (!window.Chart) return; // CDN blocked → page still renders, just no charts

  Chart.defaults.color = TXT2;
  Chart.defaults.font.family = "'Inter', sans-serif";
  Chart.defaults.font.size = 11;

  const days = ['T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'CN'];
  const grid = { color: STROKE, drawTicks: false };
  const noGrid = { display: false };

  const fill = (ctx, hex) => {
    const { ctx: g, chartArea } = ctx.chart;
    if (!chartArea) return hex + '22';
    const grad = g.createLinearGradient(0, chartArea.top, 0, chartArea.bottom);
    grad.addColorStop(0, hex + '55');
    grad.addColorStop(1, hex + '00');
    return grad;
  };

  // ── Line chart: spend vs revenue ──────────────────────
  new Chart(document.getElementById('lineChart'), {
    type: 'line',
    data: {
      labels: days,
      datasets: [
        { label: 'Chi tiêu', data: [1.4, 1.7, 1.6, 2.1, 1.9, 2.3, 1.5],
          borderColor: PRIMARY, backgroundColor: (x) => fill(x, PRIMARY),
          fill: true, tension: .4, borderWidth: 2.5, pointRadius: 0, pointHoverRadius: 5 },
        { label: 'Doanh thu', data: [4.2, 5.1, 4.8, 6.4, 5.7, 7.1, 4.4],
          borderColor: GREEN, backgroundColor: (x) => fill(x, GREEN),
          fill: true, tension: .4, borderWidth: 2.5, pointRadius: 0, pointHoverRadius: 5 },
      ],
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { grid: noGrid },
        y: { grid, ticks: { callback: (v) => v + 'M' }, beginAtZero: true },
      },
    },
  });

  // ── Donut: conversion funnel ──────────────────────────
  new Chart(document.getElementById('donutChart'), {
    type: 'doughnut',
    data: {
      labels: ['Hiển thị', 'Click', 'Chuyển đổi'],
      datasets: [{ data: [62, 26, 12], backgroundColor: [PRIMARY, PRIMARY2, CYAN],
        borderWidth: 0, hoverOffset: 6 }],
    },
    options: { responsive: true, maintainAspectRatio: false, cutout: '72%',
      plugins: { legend: { display: false } } },
  });

  // ── Bar: conversions per day ──────────────────────────
  new Chart(document.getElementById('barChart'), {
    type: 'bar',
    data: {
      labels: days,
      datasets: [{ label: 'Chuyển đổi', data: [180, 240, 210, 320, 280, 360, 220],
        backgroundColor: (x) => fill(x, PRIMARY2),
        borderColor: PRIMARY2, borderWidth: { top: 2, right: 0, bottom: 0, left: 0 },
        borderRadius: 8, borderSkipped: false, maxBarThickness: 34 }],
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: { x: { grid: noGrid }, y: { grid, beginAtZero: true } },
    },
  });

  // ── Donut: budget allocation ──────────────────────────
  new Chart(document.getElementById('budgetChart'), {
    type: 'doughnut',
    data: {
      labels: ['Khách hàng mới', 'Re-targeting', 'Lookalike'],
      datasets: [{ data: [45, 30, 25], backgroundColor: [PRIMARY, PRIMARY2, CYAN],
        borderWidth: 0, hoverOffset: 6 }],
    },
    options: { responsive: true, maintainAspectRatio: false, cutout: '72%',
      plugins: { legend: { display: false } } },
  });

  // ── KPI sparklines ────────────────────────────────────
  const sparks = {
    spend: { d: [6, 8, 7, 9, 8, 11, 12], c: PRIMARY },
    rev:   { d: [10, 12, 11, 14, 16, 15, 18], c: GREEN },
    roas:  { d: [2.6, 2.8, 2.7, 3.0, 2.9, 3.0, 3.1], c: PRIMARY2 },
    click: { d: [40, 44, 43, 39, 42, 41, 42], c: CYAN },
  };
  document.querySelectorAll('.spark').forEach((cv) => {
    const s = sparks[cv.dataset.spark];
    new Chart(cv, {
      type: 'line',
      data: { labels: s.d.map((_, i) => i), datasets: [{ data: s.d, borderColor: s.c,
        backgroundColor: (x) => fill(x, s.c), fill: true, tension: .45,
        borderWidth: 2, pointRadius: 0 }] },
      options: { responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: false }, tooltip: { enabled: false } },
        scales: { x: { display: false }, y: { display: false } } },
    });
  });
})();
