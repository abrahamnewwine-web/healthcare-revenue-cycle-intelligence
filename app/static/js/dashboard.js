const charts = {};
Chart.defaults.animation = false;

const COLORS = {
  gold: "#c6ab6d",
  teal: "#4ecdc4",
  cyan: "#38bdf8",
  blue: "#3b82f6",
  indigo: "#6366f1",
  amber: "#e09f3e",
  purple: "#a78bfa",
  coral: "#fb923c",
  green: "#4ade80",
  red: "#f87171",
  grid: "rgba(148, 163, 184, 0.12)",
  tick: "#94a3b8",
};

function fmtCompact(val) {
  if (Math.abs(val) >= 1e6) return `$${(val / 1e6).toFixed(1)}M`;
  if (Math.abs(val) >= 1e3) return `$${(val / 1e3).toFixed(1)}K`;
  return `$${val.toFixed(0)}`;
}

function fmtCount(val) {
  if (val >= 1e6) return `${(val / 1e6).toFixed(1)}M`;
  if (val >= 1e3) return `${(val / 1e3).toFixed(1)}K`.replace(".0K", "K");
  return `${val}`;
}

function upsertChart(id, config) {
  if (charts[id]) {
    charts[id].destroy();
  }
  const ctx = document.getElementById(id).getContext("2d");
  charts[id] = new Chart(ctx, config);
}

function renderSparkline(id, values, strokeColor) {
  upsertChart(id, {
    type: "line",
    data: {
      labels: values.map((_, i) => i + 1),
      datasets: [{
        data: values,
        borderColor: strokeColor,
        borderWidth: 1.8,
        pointRadius: 0,
        tension: 0.35,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false }, tooltip: { enabled: false } },
      scales: { x: { display: false }, y: { display: false } },
    },
  });
}

function setDelta(elId, val, suffix, invertGood = false) {
  const el = document.getElementById(elId);
  const arrow = val > 0 ? "↗" : val < 0 ? "↘" : "→";
  const sign = val > 0 ? "+" : "";
  el.textContent = `${arrow} ${sign}${val.toFixed(2)}${suffix} vs previous month`;
  const isGood = invertGood ? val <= 0 : val >= 0;
  el.className = `kpi-delta ${val === 0 ? "delta-neutral" : isGood ? "delta-good" : "delta-bad"}`;
}

function getQueryParams() {
  const year = document.getElementById("filterYear").value;
  const month = document.getElementById("filterMonth").value;
  const payer = document.getElementById("filterPayer").value;
  const dept = document.getElementById("filterDept").value;
  const qs = new URLSearchParams();
  if (year) qs.set("year", year);
  if (month) qs.set("month", month);
  if (payer && payer !== "All") qs.set("payer", payer);
  if (dept && dept !== "All") qs.set("department", dept);
  return qs;
}

async function refreshDashboard() {
  const qs = getQueryParams();
  const res = await fetch(`/api/dashboard?${qs.toString()}`);
  const data = await res.json();
  const k = data.kpis;
  const m = data.monthly_trends;

  const scopeParts = [
    data.filters.year || "All Years",
    data.filters.department,
    data.filters.payer !== "All" ? data.filters.payer : null,
  ].filter(Boolean);
  document.getElementById("scopeBadge").textContent = `Scope: ${scopeParts.join(" · ")}`;

  document.getElementById("kpiVisits").textContent = fmtCount(k.total_patient_visits);
  document.getElementById("kpiCollection").textContent = `${k.collection_rate_pct.toFixed(1)}%`;
  document.getElementById("kpiDenial").textContent = `${k.denial_rate_pct.toFixed(1)}%`;
  document.getElementById("kpiMargin").textContent = `${k.operating_margin_pct.toFixed(1)}%`;
  document.getElementById("kpiSurplus").textContent = fmtCompact(k.net_operating_surplus);
  document.getElementById("kpiAcceptance").textContent = `${k.acceptance_rate_pct.toFixed(1)}%`;
  document.getElementById("claimsCountLabel").textContent = `${k.total_claims.toLocaleString()} claims`;
  document.getElementById("donutClaimsTotal").textContent = fmtCount(k.total_claims);

  setDelta("deltaVisits", k.visits_mom_pct, "%");
  setDelta("deltaCollection", k.collection_mom_pp, " pp");
  setDelta("deltaDenial", k.denial_mom_pp, " pp", true);
  setDelta("deltaMargin", k.margin_mom_pp, " pp");
  setDelta("deltaSurplus", k.surplus_mom_pct, "%");

  renderSparkline("sparkVisits", m.map(r => r.visits), COLORS.green);
  renderSparkline("sparkCollection", m.map(r => r.collection_rate_pct), COLORS.gold);
  renderSparkline("sparkDenial", m.map(r => r.denial_rate_pct), COLORS.red);
  renderSparkline("sparkMargin", m.map(r => r.operating_margin_pct), COLORS.green);
  renderSparkline("sparkSurplus", m.map(r => r.net_surplus), COLORS.gold);

  // Acceptance Gauge
  upsertChart("acceptanceGauge", {
    type: "doughnut",
    data: {
      datasets: [{
        data: [k.acceptance_rate_pct, Math.max(0, 100 - k.acceptance_rate_pct)],
        backgroundColor: [COLORS.gold, "#283548"],
        borderWidth: 0,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      rotation: -90,
      circumference: 180,
      cutout: "70%",
      plugins: { legend: { display: false }, tooltip: { enabled: false } },
    },
  });

  // 1. Monthly Billed vs Payments
  upsertChart("chartBilledPaid", {
    type: "bar",
    data: {
      labels: m.map(r => r.year_month),
      datasets: [
        { label: "Billed Amount", data: m.map(r => r.billed_amount), backgroundColor: COLORS.gold },
        { label: "Total Payments", data: m.map(r => r.total_payments), backgroundColor: COLORS.teal },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { labels: { color: "#e5e7eb", boxWidth: 10, font: { size: 11 } } } },
      scales: {
        x: { ticks: { color: COLORS.tick, font: { size: 10 } }, grid: { display: false } },
        y: { ticks: { color: COLORS.tick, callback: v => fmtCompact(v) }, grid: { color: COLORS.grid } },
      },
    },
  });

  // 2. Claims Denials by Insurance Payer
  upsertChart("chartPayerDenials", {
    type: "bar",
    data: {
      labels: data.payer_denials.map(r => r.payer_name),
      datasets: [{ label: "Denied Claims", data: data.payer_denials.map(r => r.denied_claims), backgroundColor: COLORS.gold }],
    },
    options: {
      indexAxis: "y",
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { color: COLORS.tick }, grid: { color: COLORS.grid } },
        y: { ticks: { color: "#e5e7eb", font: { size: 11 } }, grid: { display: false } },
      },
    },
  });

  // 3. Top Denial Reasons
  upsertChart("chartDenialReasons", {
    type: "bar",
    data: {
      labels: data.denial_reasons.map(r => r.reason_name),
      datasets: [{ label: "Denial Count", data: data.denial_reasons.map(r => r.denial_count), backgroundColor: COLORS.gold }],
    },
    options: {
      indexAxis: "y",
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { color: COLORS.tick }, grid: { color: COLORS.grid } },
        y: { ticks: { color: "#e5e7eb", font: { size: 11 } }, grid: { display: false } },
      },
    },
  });

  // 4. Collection Rate vs Denial Ratio
  upsertChart("chartRateRatio", {
    type: "line",
    data: {
      labels: m.map(r => r.year_month),
      datasets: [
        { label: "Collection Rate %", data: m.map(r => r.collection_rate_pct), borderColor: COLORS.cyan, tension: 0.3, pointRadius: 2.5 },
        { label: "Denial Rate %", data: m.map(r => r.denial_rate_pct), borderColor: COLORS.blue, tension: 0.3, pointRadius: 2.5 },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { labels: { color: "#e5e7eb", boxWidth: 10, font: { size: 11 } } } },
      scales: {
        x: { ticks: { color: COLORS.tick, font: { size: 10 } }, grid: { display: false } },
        y: { ticks: { color: COLORS.tick, callback: v => `${v}%` }, grid: { color: COLORS.grid } },
      },
    },
  });

  // 5. Appeals vs Overturned
  const ap = data.appeals_monthly;
  upsertChart("chartAppeals", {
    type: "bar",
    data: {
      labels: ap.map(r => r.year_month),
      datasets: [
        { label: "Appealed Denials", data: ap.map(r => r.appealed_denials), backgroundColor: COLORS.blue },
        { label: "Overturned Denials", data: ap.map(r => r.overturned_denials), backgroundColor: COLORS.indigo },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { labels: { color: "#e5e7eb", boxWidth: 10, font: { size: 11 } } } },
      scales: {
        x: { ticks: { color: COLORS.tick, font: { size: 10 } }, grid: { display: false } },
        y: { ticks: { color: COLORS.tick }, grid: { color: COLORS.grid } },
      },
    },
  });

  // 6. Q1 2026 Forecast with 95% CI
  const fc = data.forecast_q1_2026;
  upsertChart("chartForecast", {
    type: "line",
    data: {
      labels: fc.map(r => r.period),
      datasets: [
        { label: "Actual Collections", data: fc.map(r => r.actual_payments), borderColor: COLORS.indigo, borderWidth: 2.5, pointRadius: 2, tension: 0.25 },
        { label: "Forecast (Q1 2026)", data: fc.map(r => r.forecast_payments), borderColor: COLORS.gold, borderDash: [5, 4], borderWidth: 2.5, pointRadius: 3 },
        { label: "Upper 95% CI", data: fc.map(r => r.upper_95), borderColor: "rgba(198,171,109,0.25)", backgroundColor: "rgba(198,171,109,0.18)", fill: "+1", pointRadius: 0 },
        { label: "Lower 95% CI", data: fc.map(r => r.lower_95), borderColor: "rgba(198,171,109,0.25)", fill: false, pointRadius: 0 },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { labels: { color: "#e5e7eb", boxWidth: 10, font: { size: 10 }, filter: item => !item.text.includes("95%") } } },
      scales: {
        x: { ticks: { color: COLORS.tick, font: { size: 10 } }, grid: { display: false } },
        y: { ticks: { color: COLORS.tick, callback: v => fmtCompact(v) }, grid: { color: COLORS.grid } },
      },
    },
  });

  // 7. Claims Denial Rate by Payer
  upsertChart("chartPayerRates", {
    type: "bar",
    data: {
      labels: data.payer_denial_rates.map(r => r.payer_name),
      datasets: [{ label: "Denial Rate %", data: data.payer_denial_rates.map(r => r.denial_rate_pct), backgroundColor: COLORS.gold }],
    },
    options: {
      indexAxis: "y",
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { color: COLORS.tick, callback: v => `${v}%` }, grid: { color: COLORS.grid } },
        y: { ticks: { color: "#e5e7eb", font: { size: 11 } }, grid: { display: false } },
      },
    },
  });

  // 8. Monthly Revenue Collection & Billing Gap
  upsertChart("chartBillingGap", {
    type: "bar",
    data: {
      labels: m.map(r => r.year_month),
      datasets: [
        { label: "Collected", data: m.map(r => r.total_payments), backgroundColor: COLORS.teal },
        { label: "Billing Gap", data: m.map(r => r.billing_gap), backgroundColor: COLORS.amber },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { labels: { color: "#e5e7eb", boxWidth: 10, font: { size: 11 } } } },
      scales: {
        x: { ticks: { color: COLORS.tick, font: { size: 10 } }, grid: { display: false } },
        y: { ticks: { color: COLORS.tick, callback: v => fmtCompact(v) }, grid: { color: COLORS.grid } },
      },
    },
  });

  // 9. Claims Distribution by Insurance Payer
  const palette = [COLORS.gold, COLORS.teal, COLORS.blue, COLORS.purple, COLORS.coral];
  upsertChart("chartPayerDist", {
    type: "doughnut",
    data: {
      labels: data.payer_denials.map(r => `${r.payer_name} (${r.claims_share_pct.toFixed(1)}%)`),
      datasets: [{
        data: data.payer_denials.map(r => r.total_claims),
        backgroundColor: palette,
        borderColor: "#111827",
        borderWidth: 2,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: "60%",
      plugins: {
        legend: { position: "right", labels: { color: "#e5e7eb", boxWidth: 11, font: { size: 11 } } },
      },
    },
  });
}

["filterYear", "filterMonth", "filterPayer", "filterDept"].forEach(id => {
  document.getElementById(id).addEventListener("change", refreshDashboard);
});

document.getElementById("btnReset").addEventListener("click", () => {
  document.getElementById("filterMonth").value = "";
  document.getElementById("filterPayer").value = "All";
  document.getElementById("filterDept").value = "All";
  refreshDashboard();
});

document.getElementById("btnExport").addEventListener("click", () => {
  const qs = getQueryParams();
  window.location.href = `/api/export/monthly-csv?${qs.toString()}`;
});

window.addEventListener("DOMContentLoaded", refreshDashboard);
