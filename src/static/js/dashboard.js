const state = {
  user: null,
  charts: {},
};

const resultEl = document.getElementById('result');
const reportEl = document.getElementById('report');
const uploadForm = document.getElementById('upload-form');
const apiForm = document.getElementById('api-form');
const ocrPreviewEl = document.getElementById('ocr-preview');
const currentUserEl = document.getElementById('current-user');
const refreshBtn = document.getElementById('refresh-dashboard');
const assistantForm = document.getElementById('assistant-form');
const assistantAnswerEl = document.getElementById('assistant-answer');
const logoutBtn = document.getElementById('logout-btn');
const navItems = document.querySelectorAll('.nav-item[data-view]');
const viewSections = document.querySelectorAll('[data-view-section]');
const invoiceTabButtons = document.querySelectorAll('[data-invoice-tab]');
const invoicePanes = document.querySelectorAll('[data-invoice-pane]');
const invoiceTableBody = document.querySelector('#invoice-table tbody');
const invoiceSearchInput = document.getElementById('invoice-search');
const invoiceStartInput = document.getElementById('invoice-start');
const invoiceEndInput = document.getElementById('invoice-end');
const invoiceSearchBtn = document.getElementById('invoice-search-btn');
const invoiceClearBtn = document.getElementById('invoice-clear-btn');
const uploadPreviewBox = document.getElementById('upload-preview');
const uploadProgressBar = document.getElementById('upload-progress');
const uploadSubmitBtn = uploadForm?.querySelector('button[type="submit"]');
const fileInput = document.getElementById('file');
let loadingMaskEl = null;
let loadingTextEl = null;
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

const formatAmount = (value) => {
  const num = Number(value);
  return Number.isFinite(num) ? num.toFixed(2) : '--';
};

const formatDateTime = (value) => {
  if (!value) return '--';
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? value : d.toLocaleString('zh-CN');
};

const showLoading = (msg = '处理中...') => {
  if (!loadingMaskEl) {
    loadingMaskEl = document.createElement('div');
    loadingMaskEl.className = 'loading-mask';
    const box = document.createElement('div');
    box.className = 'loading-box';
    const spinner = document.createElement('div');
    spinner.className = 'loading-spinner';
    loadingTextEl = document.createElement('div');
    loadingTextEl.textContent = msg;
    box.appendChild(spinner);
    box.appendChild(loadingTextEl);
    loadingMaskEl.appendChild(box);
  }
  if (loadingTextEl) loadingTextEl.textContent = msg;
  document.body.appendChild(loadingMaskEl);
};

const hideLoading = () => {
  if (loadingMaskEl && loadingMaskEl.parentNode) {
    loadingMaskEl.parentNode.removeChild(loadingMaskEl);
  }
};

const setUploadProgress = (percent) => {
  if (!uploadProgressBar) return;
  const safe = Math.max(0, Math.min(100, percent));
  uploadProgressBar.style.width = `${safe}%`;
};

const previewSelectedFile = (file) => {
  if (!uploadPreviewBox) return;
  if (!file) {
    uploadPreviewBox.textContent = '预览';
    uploadPreviewBox.innerHTML = '预览';
    return;
  }
  if (file.type && file.type.startsWith('image/')) {
    const reader = new FileReader();
    reader.onload = () => {
      uploadPreviewBox.innerHTML = `<img src="${reader.result}" alt="预览" style="max-width:100%;max-height:180px;object-fit:contain;">`;
    };
    reader.readAsDataURL(file);
  } else {
    uploadPreviewBox.textContent = `已选择文件：${file.name}`;
  }
};

const renderInvoiceTable = (rows = []) => {
  if (!invoiceTableBody) return;
  if (!rows.length) {
    invoiceTableBody.innerHTML = '<tr><td colspan="12">暂无数据</td></tr>';
    return;
  }
  const html = rows
    .map((row) => {
      const voucherCell = row.voucher_pdf_url
        ? `<a href="${row.voucher_pdf_url}" target="_blank" rel="noopener">查看</a>`
        : '<span class="hint">未生成</span>';
      const fileLink = row.id
        ? `<a href="/api/v1/invoices/${row.id}/file" target="_blank" rel="noopener">预览</a>`
        : '<span class="hint">--</span>';
      const downloadLink = row.id
        ? `<a href="/api/v1/invoices/${row.id}/file" download="${row.file_name || 'invoice'}">下载</a>`
        : '<span class="hint">--</span>';
      const entriesCount = Array.isArray(row.entries) ? row.entries.length : 0;
      const generateVoucherBtn =
        row.id && !row.voucher_pdf_url
          ? `<button type="button" data-action="gen-voucher" data-id="${row.id}" class="ghost" style="margin-left:6px;">生成凭证</button>`
          : '';
      const deleteBtn = row.id
        ? `<button type="button" data-action="delete-invoice" data-id="${row.id}" class="ghost" style="margin-left:6px;">删除</button>`
        : '';
      // ID列：显示可复制的ID，方便用户使用
      const idCell = row.id
        ? `<code style="font-size: 0.85em; background: #f3f4f6; padding: 2px 6px; border-radius: 3px; cursor: pointer;" title="点击复制" onclick="navigator.clipboard.writeText('${row.id}').then(() => alert('已复制ID: ${row.id}'))">${row.id}</code>`
        : '<span class="hint">--</span>';
      return `
        <tr>
          <td>${idCell}</td>
          <td>${row.file_name || '--'}</td>
          <td>${row.vendor || '--'}</td>
          <td>${row.issue_date || '--'}</td>
          <td>${formatAmount(row.amount)}</td>
          <td>${row.category || '--'}</td>
          <td>${formatDateTime(row.created_at)}</td>
          <td>${row.status || '--'}</td>
          <td>${fileLink}</td>
          <td>${downloadLink}</td>
          <td>${voucherCell}</td>
          <td>
            <span class="hint">${entriesCount ? `${entriesCount}条分录` : '—'}</span>
            ${generateVoucherBtn}${deleteBtn}
          </td>
        </tr>
      `;
    })
    .join('');
  invoiceTableBody.innerHTML = html;
};

const loadInvoices = async () => {
  if (!invoiceTableBody) return;
  const params = new URLSearchParams();
  if (state.user?.id) params.set('user_id', state.user.id);
  const q = invoiceSearchInput?.value?.trim();
  if (q) params.set('q', q);
  if (invoiceStartInput?.value) params.set('start_date', invoiceStartInput.value);
  if (invoiceEndInput?.value) params.set('end_date', invoiceEndInput.value);
  const query = params.toString();
  try {
    const resp = await fetch(`/api/v1/invoices${query ? `?${query}` : ''}`);
    const data = await resp.json();
    if (!data.success) throw new Error(data.error || '查询失败');
    renderInvoiceTable(data.data || []);
  } catch (error) {
    invoiceTableBody.innerHTML = `<tr><td colspan="11">加载失败：${error.message || error}</td></tr>`;
  }
};

const switchInvoiceTab = (tab) => {
  invoiceTabButtons.forEach((btn) => btn.classList.toggle('active', btn.dataset.invoiceTab === tab));
  invoicePanes.forEach((pane) => pane.classList.toggle('active', pane.dataset.invoicePane === tab));
  if (tab === 'list') {
    loadInvoices();
  }
};

const initCharts = () => {
  state.charts.trend = echarts.init(chartTargets.trend);
  state.charts.category = echarts.init(chartTargets.category);
  state.charts.risk = echarts.init(chartTargets.risk);
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

  state.charts.trend.setOption({
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: trend.map((t) => t.date) },
    yAxis: { type: 'value' },
    series: [{ name: '支出', type: 'line', areaStyle: {}, data: trend.map((t) => t.amount) }],
  });

  state.charts.category.setOption({
    tooltip: { trigger: 'item' },
    series: [
      {
        type: 'pie',
        radius: '60%',
        data: category_breakdown.map((c) => ({ name: c.category, value: c.amount })),
      },
    ],
  });

  state.charts.risk.setOption({
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

const switchView = (view) => {
  viewSections.forEach((el) => {
    el.classList.toggle('active', el.dataset.viewSection === view);
  });
  navItems.forEach((item) => item.classList.toggle('active', item.dataset.view === view));
  if (view === 'invoice') {
    const activeTab = document.querySelector('[data-invoice-tab].active')?.dataset.invoiceTab || 'upload';
    switchInvoiceTab(activeTab);
  }
};

fileInput?.addEventListener('change', () => {
  const file = fileInput.files?.[0];
  previewSelectedFile(file);
});

uploadForm?.addEventListener('submit', async (event) => {
  event.preventDefault();
  if (!fileInput?.files?.length) {
    alert('请先选择文件');
    return;
  }
  const meta = state.user
    ? JSON.stringify(
        {
          user_email: state.user.email,
          user_name: state.user.name,
        },
        null,
        2,
      )
    : '';
  const formData = new FormData();
  formData.append('file', fileInput.files[0]);
  if (meta) formData.append('meta', meta);

  try {
    setUploadProgress(12);
    if (uploadSubmitBtn) {
      uploadSubmitBtn.disabled = true;
      uploadSubmitBtn.textContent = '上传中...';
    }
    const resp = await fetch('/api/v1/reconciliations/upload', { method: 'POST', body: formData });
    const data = await resp.json();
    setUploadProgress(90);
    if (!resp.ok || data.success === false) {
      throw new Error(data.error || '上传失败');
    }
    renderResult(data);
    refreshDashboard();
    setOcrPreview(data.document);
    loadInvoices();
    setUploadProgress(100);
  } catch (error) {
    resultEl.textContent = `上传失败: ${error.message || error}`;
  } finally {
    if (uploadSubmitBtn) {
      uploadSubmitBtn.disabled = false;
      uploadSubmitBtn.textContent = '上传并对账';
    }
    setTimeout(() => setUploadProgress(0), 400);
  }
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

invoiceTabButtons.forEach((btn) => {
  btn.addEventListener('click', () => switchInvoiceTab(btn.dataset.invoiceTab));
});

invoiceSearchBtn?.addEventListener('click', () => loadInvoices());
invoiceClearBtn?.addEventListener('click', () => {
  if (invoiceSearchInput) invoiceSearchInput.value = '';
  if (invoiceStartInput) invoiceStartInput.value = '';
  if (invoiceEndInput) invoiceEndInput.value = '';
  loadInvoices();
});
invoiceSearchInput?.addEventListener('keyup', (event) => {
  if (event.key === 'Enter') {
    loadInvoices();
  }
});

invoiceTableBody?.addEventListener('click', async (event) => {
  const btn = event.target.closest('[data-action="delete-invoice"]');
  const genBtn = event.target.closest('[data-action="gen-voucher"]');

  if (btn) {
    const id = btn.dataset.id;
    if (!id) return;
    if (!confirm('确认删除该发票及其凭证吗？')) return;
    try {
      const resp = await fetch(`/api/v1/invoices/${id}`, { method: 'DELETE' });
      const data = await resp.json();
      if (!resp.ok || data.success === false) {
        throw new Error(data.error || '删除失败');
      }
      loadInvoices();
    } catch (error) {
      alert(`删除失败：${error.message || error}`);
    }
    return;
  }

  if (genBtn) {
    const id = genBtn.dataset.id;
    if (!id) return;
    showLoading('正在生成凭证（含大模型校验/渲染）...');
    genBtn.disabled = true;
    genBtn.textContent = '生成中...';
    try {
      const resp = await fetch(`/api/v1/invoices/${id}/voucher/generate`, { method: 'POST' });
      const text = await resp.text();
      let data = {};
      try {
        data = text ? JSON.parse(text) : {};
      } catch (e) {
        console.error('生成凭证返回非JSON', text);
      }
      if (!resp.ok || data.success === false) {
        throw new Error(data.error || '生成失败');
      }
      loadInvoices();
    } catch (error) {
      alert(`生成凭证失败：${error.message || error}`);
    } finally {
      hideLoading();
      genBtn.disabled = false;
      genBtn.textContent = '生成凭证';
    }
  }
});

navItems.forEach((item) => {
  item.addEventListener('click', () => switchView(item.dataset.view));
});

logoutBtn?.addEventListener('click', async () => {
  await fetch('/api/v1/auth/logout', { method: 'POST' });
  window.location.href = '/login';
});

const fetchCurrentUser = async () => {
  const resp = await fetch('/api/v1/auth/me');
  const data = await resp.json();
  if (data.success && data.user) {
    state.user = data.user;
    currentUserEl.textContent = `${state.user.name} (${state.user.email})`;
  } else {
    window.location.href = '/login';
  }
};

// 报表相关元素
const reportTabButtons = document.querySelectorAll('[data-report-tab]');
const reportPanes = document.querySelectorAll('[data-report-pane]');
const invoiceAuditForm = document.getElementById('invoice-audit-form');
const periodSummaryForm = document.getElementById('period-summary-form');
const auditTrailForm = document.getElementById('audit-trail-form');
const allReportsForm = document.getElementById('all-reports-form');
const allReportTabButtons = document.querySelectorAll('[data-all-report-tab]');
const allReportContents = document.querySelectorAll('[data-all-report-content]');

// 报表标签切换
const switchReportTab = (tab) => {
  reportTabButtons.forEach((btn) => btn.classList.toggle('active', btn.dataset.reportTab === tab));
  reportPanes.forEach((pane) => pane.classList.toggle('active', pane.dataset.reportPane === tab));
};

reportTabButtons.forEach((btn) => {
  btn.addEventListener('click', () => {
    switchReportTab(btn.dataset.reportTab);
  });
});

// 所有报表内容标签切换
const switchAllReportTab = (tab) => {
  allReportTabButtons.forEach((btn) => btn.classList.toggle('active', btn.dataset.allReportTab === tab));
  allReportContents.forEach((content) => content.classList.toggle('active', content.dataset.allReportContent === tab));
};

allReportTabButtons.forEach((btn) => {
  btn.addEventListener('click', () => {
    switchAllReportTab(btn.dataset.allReportTab);
  });
});

// 单张票据审核报告
invoiceAuditForm?.addEventListener('submit', async (event) => {
  event.preventDefault();
  const docId = document.getElementById('invoice-audit-doc-id').value.trim();
  const saveFile = document.getElementById('invoice-audit-save').checked;
  const loadingEl = document.getElementById('invoice-audit-loading');
  const outputEl = document.getElementById('invoice-audit-output');

  if (!docId) {
    alert('请输入票据ID');
    return;
  }

  try {
    loadingEl.style.display = 'block';
    outputEl.textContent = '生成中...';
    const resp = await fetch('/api/v1/reports/invoice_audit', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ document_id: docId, save_file: saveFile }),
    });
    const data = await resp.json();
    if (!data.success) throw new Error(data.error || '生成失败');
    outputEl.innerHTML = window.marked.parse(data.report);
    loadingEl.style.display = 'none';
  } catch (error) {
    outputEl.textContent = `错误: ${error.message || error}`;
    loadingEl.style.display = 'none';
  }
});

// 周期汇总报表
periodSummaryForm?.addEventListener('submit', async (event) => {
  event.preventDefault();
  const startDate = document.getElementById('period-summary-start').value;
  const endDate = document.getElementById('period-summary-end').value;
  const periodType = document.getElementById('period-summary-type').value;
  const periodLabel = document.getElementById('period-summary-label').value.trim();
  const saveFile = document.getElementById('period-summary-save').checked;
  const loadingEl = document.getElementById('period-summary-loading');
  const outputEl = document.getElementById('period-summary-output');

  try {
    loadingEl.style.display = 'block';
    outputEl.textContent = '生成中...';
    const payload = { period_type: periodType, save_file: saveFile };
    if (startDate) payload.start_date = startDate;
    if (endDate) payload.end_date = endDate;
    if (periodLabel) payload.period_label = periodLabel;
    const resp = await fetch('/api/v1/reports/period_summary', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const data = await resp.json();
    if (!data.success) throw new Error(data.error || '生成失败');
    outputEl.innerHTML = window.marked.parse(data.report);
    loadingEl.style.display = 'none';
  } catch (error) {
    outputEl.textContent = `错误: ${error.message || error}`;
    loadingEl.style.display = 'none';
  }
});

// 审计追溯与整改清单
auditTrailForm?.addEventListener('submit', async (event) => {
  event.preventDefault();
  const startDate = document.getElementById('audit-trail-start').value;
  const endDate = document.getElementById('audit-trail-end').value;
  const saveFile = document.getElementById('audit-trail-save').checked;
  const loadingEl = document.getElementById('audit-trail-loading');
  const outputEl = document.getElementById('audit-trail-output');

  try {
    loadingEl.style.display = 'block';
    outputEl.textContent = '生成中...';
    const payload = { save_file: saveFile };
    if (startDate) payload.start_date = startDate;
    if (endDate) payload.end_date = endDate;
    const resp = await fetch('/api/v1/reports/audit_trail', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const data = await resp.json();
    if (!data.success) throw new Error(data.error || '生成失败');
    outputEl.innerHTML = window.marked.parse(data.report);
    loadingEl.style.display = 'none';
  } catch (error) {
    outputEl.textContent = `错误: ${error.message || error}`;
    loadingEl.style.display = 'none';
  }
});

// 生成所有报表
allReportsForm?.addEventListener('submit', async (event) => {
  event.preventDefault();
  const startDate = document.getElementById('all-reports-start').value;
  const endDate = document.getElementById('all-reports-end').value;
  const periodType = document.getElementById('all-reports-type').value;
  const periodLabel = document.getElementById('all-reports-label').value.trim();
  const saveFiles = document.getElementById('all-reports-save').checked;
  const loadingEl = document.getElementById('all-reports-loading');
  const periodEl = document.getElementById('all-reports-period');
  const trailEl = document.getElementById('all-reports-trail');
  const invoicesEl = document.getElementById('all-reports-invoices');

  try {
    loadingEl.style.display = 'block';
    periodEl.textContent = '生成中...';
    trailEl.textContent = '生成中...';
    invoicesEl.innerHTML = '<p class="hint">生成中...</p>';
    const payload = { period_type: periodType, save_files: saveFiles };
    if (startDate) payload.start_date = startDate;
    if (endDate) payload.end_date = endDate;
    if (periodLabel) payload.period_label = periodLabel;
    const resp = await fetch('/api/v1/reports/all', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const data = await resp.json();
    if (!data.success) throw new Error(data.error || '生成失败');
    
    // 显示周期汇总报表
    if (data.reports.period_summary) {
      periodEl.innerHTML = window.marked.parse(data.reports.period_summary);
    }
    
    // 显示审计追溯清单
    if (data.reports.audit_trail) {
      trailEl.innerHTML = window.marked.parse(data.reports.audit_trail);
    }
    
    // 显示单张票据报告
    if (data.reports.invoice_reports && Object.keys(data.reports.invoice_reports).length > 0) {
      const invoiceReports = data.reports.invoice_reports;
      const invoiceList = Object.entries(invoiceReports).map(([docId, report]) => {
        return `
          <div style="margin-bottom: 16px; border: 1px solid #e5e7eb; padding: 12px; border-radius: 4px;">
            <h4 style="margin: 0 0 8px;">票据ID: ${docId}</h4>
            <div class="markdown-body surface" style="max-height: 300px; overflow-y: auto;">
              ${window.marked.parse(report)}
            </div>
          </div>
        `;
      }).join('');
      invoicesEl.innerHTML = invoiceList;
    } else {
      invoicesEl.innerHTML = '<p class="hint">无单张票据报告（票据数量可能超过50张）</p>';
    }
    
    loadingEl.style.display = 'none';
  } catch (error) {
    periodEl.textContent = `错误: ${error.message || error}`;
    trailEl.textContent = `错误: ${error.message || error}`;
    invoicesEl.innerHTML = `<p class="hint">错误: ${error.message || error}</p>`;
    loadingEl.style.display = 'none';
  }
});

window.addEventListener('load', async () => {
  await fetchCurrentUser();
  initCharts();
  refreshDashboard();
  switchView('dashboard');
});

const setOcrPreview = (doc) => {
  if (!ocrPreviewEl) return;
  if (!doc) {
    ocrPreviewEl.textContent = '暂无识别结果';
    return;
  }
  const spans = doc.ocr_spans || [];
  const text = spans.map((s) => s.text).join('\n');
  if (text && text.trim()) {
    ocrPreviewEl.textContent = text;
  } else {
    ocrPreviewEl.textContent = '暂无识别结果';
  }
};
