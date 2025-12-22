const state = {
  user: null,
  charts: {},
};

const resultEl = document.getElementById('result');
const reportEl = document.getElementById('report');
const uploadForm = document.getElementById('upload-form');
const apiForm = document.getElementById('api-form');
const currentUserEl = document.getElementById('current-user');
const refreshBtn = document.getElementById('refresh-dashboard');
const assistantForm = document.getElementById('assistant-form');
const assistantAnswerEl = document.getElementById('assistant-answer');
const logoutBtn = document.getElementById('logout-btn');
const uploadPreview = document.getElementById('upload-preview');
const uploadProgress = document.getElementById('upload-progress');
const ocrPreview = document.getElementById('ocr-preview');
const navItems = document.querySelectorAll('.sidebar-nav .nav-item');
const viewSections = document.querySelectorAll('[data-view-section]');
const invoiceTabButtons = document.querySelectorAll('[data-invoice-tab]');
const invoicePanes = document.querySelectorAll('[data-invoice-pane]');
const reportTabButtons = document.querySelectorAll('[data-report-tab]');
const reportPanes = document.querySelectorAll('[data-report-pane]');
const allReportTabButtons = document.querySelectorAll('[data-all-report-tab]');
const allReportContents = document.querySelectorAll('[data-all-report-content]');
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

const setTableMessage = (selector, message, colspan) => {
  const tbody = document.querySelector(selector);
  if (!tbody) return;
  tbody.innerHTML = `<tr><td colspan="${colspan || 1}">${message}</td></tr>`;
};

const fmtDateTime = (value) => {
  if (!value) return '--';
  try {
    return new Date(value).toLocaleString('zh-CN');
  } catch (e) {
    return value;
  }
};

const fmtAmount = (value) => {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return '--';
  return Number(value).toFixed(2);
};

const fetchInvoices = async (params = {}) => {
  const searchParams = new URLSearchParams();
  const { q, start_date, end_date } = params;
  if (q) searchParams.set('q', q);
  if (start_date) searchParams.set('start_date', start_date);
  if (end_date) searchParams.set('end_date', end_date);
  if (state.user?.id) searchParams.set('user_id', state.user.id);
  const resp = await fetch(`/api/v1/invoices?${searchParams.toString()}`);
  const data = await resp.json();
  if (!data.success) throw new Error(data.error || '获取发票失败');
  return data.data || [];
};

const fetchVouchers = async (params = {}) => {
  const searchParams = new URLSearchParams();
  const { q, start_date, end_date } = params;
  if (q) searchParams.set('q', q);
  if (start_date) searchParams.set('start_date', start_date);
  if (end_date) searchParams.set('end_date', end_date);
  if (state.user?.id) searchParams.set('user_id', state.user.id);
  const resp = await fetch(`/api/v1/vouchers?${searchParams.toString()}`);
  const data = await resp.json();
  if (!data.success) throw new Error(data.error || '获取凭证失败');
  return data.data || [];
};

const deleteInvoices = async (ids = []) => {
  if (!ids.length) return 0;
  let removed = 0;
  for (const id of ids) {
    const resp = await fetch(`/api/v1/invoices/${id}`, { method: 'DELETE' });
    const data = await resp.json().catch(() => ({}));
    if (!resp.ok || !data.success) {
      throw new Error(data.error || `删除发票失败: ${id}`);
    }
    removed += 1;
  }
  return removed;
};

const deleteVouchers = async (selections = []) => {
  if (!selections.length) return { removed: 0, files_removed: 0 };
  const voucher_ids = Array.from(
    new Set(
      selections
        .map((s) => s.voucher_no)
        .filter((v) => v !== undefined && v !== null && `${v}`.trim() !== '')
        .map((v) => `${v}`.trim()),
    ),
  );
  const invoice_ids = Array.from(
    new Set(
      selections.flatMap((s) => s.invoice_ids || []).filter((id) => id !== undefined && id !== null && `${id}`.trim() !== ''),
    ),
  );
  const payload = {};
  if (voucher_ids.length) payload.voucher_ids = voucher_ids;
  if (invoice_ids.length) payload.invoice_ids = invoice_ids;
  const resp = await fetch('/api/v1/vouchers', {
    method: 'DELETE',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  const data = await resp.json().catch(() => ({}));
  if (!resp.ok || !data.success) {
    throw new Error(data.error || '删除凭证失败');
  }
  return { removed: data.removed || 0, files_removed: data.files_removed || 0 };
};

const renderLibraryTable = (rows) => {
  const tbody = document.querySelector('#library-table tbody');
  if (!tbody) return;
  if (!rows.length) {
    setTableMessage('#library-table tbody', '暂无数据', 11);
    return;
  }
  tbody.innerHTML = rows
    .map(
      (doc) => `
      <tr>
        <td><input type="checkbox" class="row-checkbox" data-doc-id="${doc.id}" /></td>
        <td>${doc.id}</td>
        <td>${doc.file_name || '--'}</td>
        <td>${doc.vendor || '--'}</td>
        <td>${doc.issue_date || '--'}</td>
        <td>${fmtAmount(doc.amount)}</td>
        <td>${doc.category || '--'}</td>
        <td>${fmtDateTime(doc.created_at)}</td>
        <td>${doc.status || '--'}</td>
        <td>${doc.id ? `<a href="/api/v1/invoices/${doc.id}/file" target="_blank">预览</a>` : '--'}</td>
        <td><button class="ghost" data-action="voucher" data-doc-id="${doc.id}">生成凭证</button></td>
      </tr>`
    )
    .join('');

  tbody.querySelectorAll('button[data-action="voucher"]').forEach((btn) => {
    btn.addEventListener('click', async () => {
      const docId = btn.dataset.docId;
      btn.disabled = true;
      btn.textContent = '生成中...';
      try {
        const resp = await fetch('/api/v1/invoices/batch_voucher/generate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ invoice_ids: [docId] }),
        });
        const data = await resp.json();
        if (!data.success) throw new Error(data.error || '生成失败');
        alert(`凭证生成成功：#${data.voucher_no}（共${data.invoice_count}张）`);
        await loadVoucherList();
      } catch (err) {
        alert(err.message || err);
      } finally {
        btn.disabled = false;
        btn.textContent = '生成凭证';
      }
    });
  });
};

const renderVoucherTable = (rows) => {
  const tbody = document.querySelector('#voucher-table tbody');
  if (!tbody) return;
  if (!rows.length) {
    setTableMessage('#voucher-table tbody', '暂无数据', 8);
    return;
  }
  tbody.innerHTML = rows
    .map(
      (row) => `
      <tr>
        <td><input type="checkbox" class="voucher-row-checkbox" data-voucher-no="${row.voucher_no || row.id}" data-invoice-ids="${(row.invoice_ids || []).join(',')}" /></td>
        <td>${row.voucher_no || row.id}</td>
        <td>${(row.invoices || []).map((i) => i.file_name || i.id).join('、') || '--'}</td>
        <td>${fmtAmount(row.total_amount)}</td>
        <td>${fmtDateTime(row.created_at)}</td>
        <td>${row.voucher_pdf_url ? `<a href="${row.voucher_pdf_url}" target="_blank">PDF</a>` : '--'}</td>
        <td>${row.voucher_excel_url ? `<a href="${row.voucher_excel_url}" target="_blank">Excel</a>` : '--'}</td>
        <td><button class="ghost" data-action="delete-voucher" data-voucher-no="${row.voucher_no || row.id}" data-invoice-ids="${(row.invoice_ids || []).join(',')}">删除</button></td>
      </tr>`
    )
    .join('');

  const masterCheckbox = document.getElementById('voucher-master-checkbox');
  if (masterCheckbox) masterCheckbox.checked = false;

  tbody.querySelectorAll('button[data-action="delete-voucher"]').forEach((btn) => {
    btn.addEventListener('click', async () => {
      const voucherNo = btn.dataset.voucherNo;
      const invoiceIds = (btn.dataset.invoiceIds || '')
        .split(',')
        .map((id) => id.trim())
        .filter(Boolean);
      if (!confirm('确认清除该凭证？对应的本地凭证文件将被删除。')) return;
      btn.disabled = true;
      btn.textContent = '清除中...';
      try {
        await deleteVouchers([{ voucher_no: voucherNo, invoice_ids: invoiceIds }]);
        await loadVoucherList();
      } catch (err) {
        alert(err.message || err);
      } finally {
        btn.disabled = false;
        btn.textContent = '删除';
      }
    });
  });
};

const loadLibrary = async () => {
  const q = document.getElementById('library-search')?.value.trim();
  const start_date = document.getElementById('library-start')?.value;
  const end_date = document.getElementById('library-end')?.value;
  try {
    const rows = await fetchInvoices({ q, start_date, end_date });
    renderLibraryTable(rows);
    return rows;
  } catch (err) {
    setTableMessage('#library-table tbody', err.message || '加载失败', 11);
    return [];
  }
};

const loadVoucherList = async () => {
  const q = document.getElementById('voucher-search')?.value.trim();
  const start_date = document.getElementById('voucher-start')?.value;
  const end_date = document.getElementById('voucher-end')?.value;
  try {
    const rows = await fetchVouchers({ q, start_date, end_date });
    renderVoucherTable(rows);
    return rows;
  } catch (err) {
    setTableMessage('#voucher-table tbody', err.message || '加载失败', 8);
    return [];
  }
};

const initLibraryActions = () => {
  const searchBtn = document.getElementById('library-search-btn');
  const clearBtn = document.getElementById('library-clear-btn');
  const masterCheckbox = document.getElementById('master-checkbox');
  const selectAllBtn = document.getElementById('select-all-btn');
  const batchBtn = document.getElementById('batch-generate-voucher-btn');

  searchBtn?.addEventListener('click', loadLibrary);
  clearBtn?.addEventListener('click', async () => {
    const ids = Array.from(document.querySelectorAll('#library-table .row-checkbox:checked')).map((cb) => cb.dataset.docId);
    const resetFilters = () => {
      document.getElementById('library-search').value = '';
      document.getElementById('library-start').value = '';
      document.getElementById('library-end').value = '';
      document.querySelectorAll('#library-table .row-checkbox').forEach((cb) => (cb.checked = false));
      if (masterCheckbox) masterCheckbox.checked = false;
    };
    if (ids.length) {
      const ok = confirm(`确认清除选中的 ${ids.length} 张发票？本地文件也会被删除。`);
      if (!ok) return;
      clearBtn.disabled = true;
      clearBtn.textContent = '清除中...';
      try {
        await deleteInvoices(ids);
        resetFilters();
        await loadLibrary();
        await loadVoucherList();
      } catch (err) {
        alert(err.message || err);
      } finally {
        clearBtn.disabled = false;
        clearBtn.textContent = '清除';
      }
    } else {
      resetFilters();
      loadLibrary();
    }
  });

  masterCheckbox?.addEventListener('change', (e) => {
    document.querySelectorAll('#library-table .row-checkbox').forEach((cb) => {
      cb.checked = e.target.checked;
    });
  });

  selectAllBtn?.addEventListener('click', () => {
    document.querySelectorAll('#library-table .row-checkbox').forEach((cb) => {
      cb.checked = true;
    });
    if (masterCheckbox) masterCheckbox.checked = true;
  });

  batchBtn?.addEventListener('click', async () => {
    const ids = Array.from(document.querySelectorAll('#library-table .row-checkbox:checked')).map(
      (cb) => cb.dataset.docId
    );
    if (!ids.length) {
      alert('请至少选择一条发票');
      return;
    }
    batchBtn.disabled = true;
    batchBtn.textContent = '批量生成中...';
    try {
      const resp = await fetch('/api/v1/invoices/batch_voucher/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ invoice_ids: ids }),
      });
      const data = await resp.json();
      if (!data.success) throw new Error(data.error || '批量生成失败');
      alert(`凭证生成成功：#${data.voucher_no}（共${data.invoice_count}张）`);
      await loadVoucherList();
    } catch (err) {
      alert(err.message || err);
    } finally {
      batchBtn.disabled = false;
      batchBtn.textContent = '批量生成凭证';
    }
  });
};

const initVoucherActions = () => {
  const searchBtn = document.getElementById('voucher-search-btn');
  const clearBtn = document.getElementById('voucher-clear-btn');
  const masterCheckbox = document.getElementById('voucher-master-checkbox');
  searchBtn?.addEventListener('click', loadVoucherList);
  masterCheckbox?.addEventListener('change', (e) => {
    document.querySelectorAll('#voucher-table .voucher-row-checkbox').forEach((cb) => {
      cb.checked = e.target.checked;
    });
  });
  clearBtn?.addEventListener('click', async () => {
    const selections = Array.from(document.querySelectorAll('#voucher-table .voucher-row-checkbox:checked')).map((cb) => ({
      voucher_no: cb.dataset.voucherNo,
      invoice_ids: (cb.dataset.invoiceIds || '')
        .split(',')
        .map((id) => id.trim())
        .filter(Boolean),
    }));
    const resetFilters = () => {
      document.getElementById('voucher-search').value = '';
      document.getElementById('voucher-start').value = '';
      document.getElementById('voucher-end').value = '';
      document.querySelectorAll('#voucher-table .voucher-row-checkbox').forEach((cb) => (cb.checked = false));
      if (masterCheckbox) masterCheckbox.checked = false;
    };
    if (selections.length) {
      const ok = confirm(`确认清除选中的 ${selections.length} 条凭证？对应的本地凭证文件将被删除。`);
      if (!ok) return;
      clearBtn.disabled = true;
      clearBtn.textContent = '清除中...';
      try {
        await deleteVouchers(selections);
        resetFilters();
        await loadVoucherList();
      } catch (err) {
        alert(err.message || err);
      } finally {
        clearBtn.disabled = false;
        clearBtn.textContent = '清除';
      }
    } else {
      resetFilters();
      loadVoucherList();
    }
  });
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
  if (!view) return;
  navItems.forEach((item) => item.classList.toggle('active', item.dataset.view === view));
  viewSections.forEach((section) => section.classList.toggle('active', section.dataset.viewSection === view));
};

const initNav = () => {
  navItems.forEach((item) => {
    item.addEventListener('click', (e) => {
      e.preventDefault();
      switchView(item.dataset.view);
    });
  });
  // 默认激活仪表盘
  switchView('dashboard');
};

const initInvoiceTabs = () => {
  invoiceTabButtons.forEach((btn) => {
    btn.addEventListener('click', () => {
      const tab = btn.dataset.invoiceTab;
      invoiceTabButtons.forEach((b) => b.classList.toggle('active', b === btn));
      invoicePanes.forEach((pane) => pane.classList.toggle('active', pane.dataset.invoicePane === tab));
    });
  });
};

const initReportTabs = () => {
  reportTabButtons.forEach((btn) => {
    btn.addEventListener('click', () => {
      const tab = btn.dataset.reportTab;
      reportTabButtons.forEach((b) => b.classList.toggle('active', b === btn));
      reportPanes.forEach((pane) => pane.classList.toggle('active', pane.dataset.reportPane === tab));
    });
  });
};

const initAllReportTabs = () => {
  allReportTabButtons.forEach((btn) => {
    btn.addEventListener('click', () => {
      const tab = btn.dataset.allReportTab;
      allReportTabButtons.forEach((b) => b.classList.toggle('active', b === btn));
      allReportContents.forEach((pane) => pane.classList.toggle('active', pane.dataset.allReportContent === tab));
    });
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
  let meta = metaField ? metaField.value.trim() : '';
  if (!meta && state.user) {
    meta = JSON.stringify(
      {
        user_email: state.user.email,
        user_name: state.user.name,
      },
      null,
      2,
    );
    if (metaField) metaField.value = meta;
  }
  const policiesField = document.getElementById('policies');
  const policies = policiesField ? policiesField.value.trim() : '';

  const formData = new FormData();
  formData.append('file', fileInput.files[0]);
  if (meta) formData.append('meta', meta);
  if (policies) formData.append('policies', policies);

  const setProgress = (p, label) => {
    if (!uploadProgress) return;
    const pct = Math.min(100, Math.max(0, p));
    uploadProgress.style.width = `${pct}%`;
    uploadProgress.textContent = label || `${Math.round(pct)}%`;
  };

  let progressTimer = null;
  const startSmoothProgress = () => {
    setProgress(5, '准备上传');
    progressTimer = setInterval(() => {
      const current = parseFloat(uploadProgress.style.width || '0');
      if (current < 85) {
        setProgress(Math.min(85, current + 2), '上传中');
      }
    }, 120);
  };
  const endSmoothProgress = () => {
    if (progressTimer) clearInterval(progressTimer);
    setProgress(100, '完成');
    setTimeout(() => setProgress(0, ''), 600);
  };

  ocrPreview && (ocrPreview.textContent = '正在上传并识别中，请稍候...');
  startSmoothProgress();

  const xhr = new XMLHttpRequest();
  xhr.open('POST', '/api/v1/reconciliations/upload');
  xhr.upload.onprogress = (e) => {
    if (e.lengthComputable) {
      const percent = 10 + (e.loaded / e.total) * 70; // 实际进度控制在 80% 内，留出处理时间
      const current = parseFloat(uploadProgress.style.width || '0');
      if (percent > current) setProgress(Math.min(90, percent), '上传中');
    }
  };
  xhr.onload = async () => {
    endSmoothProgress();
    if (xhr.status >= 200 && xhr.status < 300) {
      try {
        const data = JSON.parse(xhr.responseText || '{}');
        renderResult(data);
        if (data.document) {
          ocrPreview && (ocrPreview.textContent = JSON.stringify(data.document, null, 2));
        } else {
          ocrPreview && (ocrPreview.textContent = '上传完成，等待返回数据...');
        }
      } catch (err) {
        resultEl.textContent = `解析响应失败: ${err}`;
      }
      refreshDashboard();
      loadLibrary();
      loadVoucherList();
    } else {
      resultEl.textContent = `上传失败: ${xhr.status}`;
      ocrPreview && (ocrPreview.textContent = '上传失败，请重试');
    }
  };
  xhr.onerror = () => {
    endSmoothProgress();
    resultEl.textContent = '上传失败：网络异常';
    ocrPreview && (ocrPreview.textContent = '上传失败，请检查网络');
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

const fetchCurrentUser = async () => {
  const resp = await fetch('/api/v1/auth/me');
  const data = await resp.json();
  if (data.success && data.user) {
    state.user = data.user;
    currentUserEl.textContent = `${state.user.name} (${state.user.email})`;
    const metaInput = document.getElementById('meta');
    if (metaInput) {
      metaInput.value = JSON.stringify(
        {
          user_email: state.user.email,
          user_name: state.user.name,
        },
        null,
        2,
      );
    }
  } else {
    window.location.href = '/login';
  }
};

window.addEventListener('load', async () => {
  await fetchCurrentUser();
  initNav();
  initInvoiceTabs();
  initReportTabs();
  initAllReportTabs();
  initLibraryActions();
  initVoucherActions();
  initCharts();
  refreshDashboard();
  loadLibrary();
  loadVoucherList();
});

// -------- 上传区交互：预览与进度 --------
const fileInputEl = document.getElementById('file');
const renderUploadPreview = (file) => {
  if (!uploadPreview) return;
  if (!file) {
    uploadPreview.textContent = '预览';
    return;
  }
  if (file.type && file.type.startsWith('image/')) {
    const url = URL.createObjectURL(file);
    uploadPreview.innerHTML = `<img class="thumb" src="${url}" alt="${file.name}" />`;
    setTimeout(() => URL.revokeObjectURL(url), 30000);
  } else if (file.type === 'application/pdf') {
    uploadPreview.innerHTML = `<div class="thumb-pdf">${file.name}</div>`;
  } else {
    uploadPreview.textContent = file.name;
  }
};

fileInputEl?.addEventListener('change', (e) => {
  const file = e.target.files?.[0];
  renderUploadPreview(file);
  if (ocrPreview) ocrPreview.textContent = file ? '准备上传...' : '等待上传后显示...';
  if (uploadProgress) {
    uploadProgress.style.width = '0%';
    uploadProgress.textContent = '';
  }
});
