const state = {
  user: null,
  charts: {},
  activeView: 'dashboard',
};

const resultEl = document.getElementById('result');
const reportEl = document.getElementById('report');
const uploadForm = document.getElementById('upload-form');
const apiForm = document.getElementById('api-form');
const invoiceTable = document.getElementById('invoice-table');
const reportForm = document.getElementById('report-form');
const reportOutput = document.getElementById('report-output');
const reportSummary = document.getElementById('report-summary');
const currentUserEl = document.getElementById('current-user');
const refreshBtn = document.getElementById('refresh-dashboard');
const assistantForm = document.getElementById('assistant-form');
const assistantAnswerEl = document.getElementById('assistant-answer');
const logoutBtn = document.getElementById('logout-btn');
const navItems = document.querySelectorAll('.nav-item[data-view]');
const progressBar = document.getElementById('upload-progress');
const previewBox = document.getElementById('upload-preview');
assistantForm?.addEventListener('submit', async (event) => {
  event.preventDefault();
  const question = document.getElementById('assistant-question').value.trim();
  if (!question) {
    alert('请先输入问题');
    return;
  }
  const payload = { question };
  if (state.user) {
    payload.user_id = state.user.id;
  }
  try {
    const resp = await fetch('/api/v1/assistant/query', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const data = await resp.json();
    if (!data.success) throw new Error(data.error || '助手调用失败');
    assistantAnswerEl.innerHTML = window.marked.parse(data.answer);
  } catch (error) {
    assistantAnswerEl.textContent = `助手调用失败: ${error.message || error}`;
  }
});
const tabButtons = document.querySelectorAll('.tabs button');
const tabReport = document.getElementById('tab-report');
const tabJson = document.getElementById('tab-json');

const chartTargets = {
  trend: document.getElementById('trend-chart'),
  category: document.getElementById('category-chart'),
  risk: document.getElementById('risk-chart'),
};

const initCharts = () => {
  if (chartTargets.trend) state.charts.trend = echarts.init(chartTargets.trend);
  if (chartTargets.category) state.charts.category = echarts.init(chartTargets.category);
  if (chartTargets.risk) state.charts.risk = echarts.init(chartTargets.risk);
};

const setStats = (documentResult) => {
  if (!documentResult) {
    document.getElementById('stat-ocr-value').textContent = '--';
    document.getElementById('stat-policy-value').textContent = '--';
    document.getElementById('stat-category-value').textContent = '--';
    document.getElementById('stat-risk-value').textContent = '--';
    return;
  }
  document.getElementById('stat-ocr-value').textContent = (documentResult.ocr_confidence || 0).toFixed(2);
  document.getElementById('stat-policy-value').textContent = `${documentResult.policy_flags.length} 条提醒`;
  document.getElementById('stat-category-value').textContent = documentResult.category || '未分类';
  const riskCount = (documentResult.anomalies?.length || 0) + (documentResult.duplicate_candidates?.length || 0);
  document.getElementById('stat-risk-value').textContent = `${riskCount} 条`; 
};

const renderResult = (payload) => {
  if (payload.report) {
    reportEl.innerHTML = window.marked.parse(payload.report);
  } else {
    reportEl.textContent = '暂无报告';
  }
  if (payload.document) {
    resultEl.textContent = JSON.stringify(payload.document, null, 2);
    setStats(payload.document);
  } else {
    resultEl.textContent = JSON.stringify(payload, null, 2);
  }
};

const toggleTabs = (active) => {
  tabButtons.forEach((btn) => {
    const isActive = btn.dataset.tab === active;
    btn.classList.toggle('active', isActive);
  });
  tabReport.classList.toggle('active', active === 'report');
  tabJson.classList.toggle('active', active === 'json');
};

const refreshDashboard = async () => {
  const query = state.user ? `?user_id=${state.user.id}` : '';
  const resp = await fetch(`/api/v1/dashboard/summary${query}`);
  const data = await resp.json();
  if (!data.success) return;
  const { trend, category_breakdown, risk } = data.data;

  state.charts.trend?.setOption({
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: trend.map((t) => t.date) },
    yAxis: { type: 'value' },
    series: [{ name: '支出', type: 'line', areaStyle: {}, data: trend.map((t) => t.amount) }],
  });

  state.charts.category?.setOption({
    tooltip: { trigger: 'item' },
    series: [
      {
        type: 'pie',
        radius: '60%',
        data: category_breakdown.map((c) => ({ name: c.category, value: c.amount })),
      },
    ],
  });

  state.charts.risk?.setOption({
    xAxis: { type: 'category', data: ['异常', '重复'] },
    yAxis: { type: 'value' },
    series: [
      {
        type: 'bar',
        data: [risk.anomalies, risk.duplicates],
        itemStyle: { color: '#ef4444' },
      },
    ],
  });
};

const bindUploadPreview = () => {
  const fileInput = document.getElementById('file');
  fileInput?.addEventListener('change', () => {
    previewBox.innerHTML = '';
    const file = fileInput.files?.[0];
    if (!file) return;
    if (file.type.startsWith('image/')) {
      const img = document.createElement('img');
      img.src = URL.createObjectURL(file);
      img.className = 'thumb';
      previewBox.appendChild(img);
    } else {
      const tag = document.createElement('div');
      tag.className = 'thumb thumb-pdf';
      tag.textContent = file.name;
      previewBox.appendChild(tag);
    }
  });
};

uploadForm?.addEventListener('submit', async (event) => {
  event.preventDefault();
  const fileInput = document.getElementById('file');
  if (!fileInput.files.length) {
    alert('请先选择文件');
    return;
  }
  const metaField = document.getElementById('meta');
  let meta = metaField.value.trim();
  if (!meta && state.user) {
    meta = JSON.stringify(
      {
        user_email: state.user.email,
        user_name: state.user.name,
      },
      null,
      2,
    );
    metaField.value = meta;
  }
  const policies = document.getElementById('policies').value.trim();

  const formData = new FormData();
  formData.append('file', fileInput.files[0]);
  if (meta) formData.append('meta', meta);
  if (policies) formData.append('policies', policies);

  const xhr = new XMLHttpRequest();
  xhr.open('POST', '/api/v1/reconciliations/upload');
  xhr.upload.onprogress = (e) => {
    if (progressBar && e.lengthComputable) {
      const percent = Math.round((e.loaded / e.total) * 100);
      progressBar.style.width = `${percent}%`;
      progressBar.textContent = `${percent}%`;
    }
  };
  xhr.onload = () => {
    if (progressBar) {
      progressBar.style.width = '0%';
      progressBar.textContent = '';
    }
    if (xhr.status >= 200 && xhr.status < 300) {
      const data = JSON.parse(xhr.responseText);
      renderResult(data);
      refreshDashboard();
      loadInvoices();
    } else {
      resultEl.textContent = `上传失败: ${xhr.responseText}`;
    }
  };
  xhr.onerror = () => {
    resultEl.textContent = '上传失败：网络错误';
  };
  xhr.send(formData);
});

apiForm?.addEventListener('submit', async (event) => {
  event.preventDefault();
  const payload = document.getElementById('api-payload').value;
  if (!payload) {
    alert('请填写 JSON 请求体');
    return;
  }
  try {
    const resp = await fetch('/api/v1/reconciliations/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: payload,
    });
    const data = await resp.json();
    renderResult({ document: data.documents?.[0], report: data.report });
    refreshDashboard();
  } catch (error) {
    resultEl.textContent = `调用失败: ${error}`;
  }
});

refreshBtn?.addEventListener('click', refreshDashboard);

tabButtons.forEach((btn) => {
  btn.addEventListener('click', () => toggleTabs(btn.dataset.tab));
});

logoutBtn?.addEventListener('click', async () => {
  await fetch('/api/v1/auth/logout', { method: 'POST' });
  window.location.href = '/login';
});

const switchView = (view) => {
  state.activeView = view;
  document.querySelectorAll('[data-view-section]').forEach((el) => {
    el.classList.toggle('active', el.dataset.viewSection === view);
  });
  navItems.forEach((item) => item.classList.toggle('active', item.dataset.view === view));
};

navItems.forEach((item) =>
  item.addEventListener('click', () => {
    switchView(item.dataset.view);
  }),
);

const loadInvoices = async () => {
  const query = state.user ? `?user_id=${state.user.id}` : '';
  const resp = await fetch(`/api/v1/invoices${query}`);
  const data = await resp.json();
  if (!data.success || !invoiceTable) return;
  const tbody = invoiceTable.querySelector('tbody');
  tbody.innerHTML = '';
  data.data.forEach((inv) => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${inv.file_name}</td>
      <td>${inv.vendor || '-'}</td>
      <td>${inv.amount ?? '-'}</td>
      <td>${inv.category || '-'}</td>
      <td>${inv.status}</td>
      <td>
        ${inv.voucher_pdf_url ? `<a href="${inv.voucher_pdf_url}" target="_blank">下载凭证</a>` : '生成中'}
      </td>
    `;
    tbody.appendChild(tr);
  });
};

reportForm?.addEventListener('submit', async (event) => {
  event.preventDefault();
  const period = document.getElementById('report-period').value;
  const anchor = document.getElementById('report-date').value;
  const payload = { period_type: period, anchor_date: anchor };
  reportOutput.textContent = '生成中...';
  try {
    const resp = await fetch('/api/v1/reports/financial', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const data = await resp.json();
    if (!data.success) throw new Error(data.error || '生成失败');
    reportOutput.textContent = data.report;
    reportSummary.textContent = JSON.stringify(data.summary, null, 2);
  } catch (err) {
    reportOutput.textContent = `生成失败: ${err.message || err}`;
  }
});

const fetchCurrentUser = async () => {
  const resp = await fetch('/api/v1/auth/me');
  const data = await resp.json();
  if (data.success && data.user) {
    state.user = data.user;
    currentUserEl.textContent = `${state.user.name} (${state.user.email})`;
    document.getElementById('meta').value = JSON.stringify(
      {
        user_email: state.user.email,
        user_name: state.user.name,
      },
      null,
      2,
    );
  } else {
    window.location.href = '/login';
  }
};

window.addEventListener('load', async () => {
  await fetchCurrentUser();
  initCharts();
  refreshDashboard();
  bindUploadPreview();
  loadInvoices();
});
