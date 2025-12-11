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
<<<<<<< HEAD
      loadInvoices();
=======

      // 如果后端返回了 document 信息，先在表格顶部插入一个临时行，随后轮询直到数据库可见
      const returnedDoc = data.document || {};
      const docId = returnedDoc.document_id || returnedDoc.documentId || returnedDoc.id || null;
      if (docId && invoiceTable) {
        insertTemporaryInvoice(returnedDoc);
        // 轮询检查是否写入数据库
        pollInvoiceExists(docId, 12, 2000).then((found) => {
          // 无论是否找到，都刷新列表（若找到则显示真实记录）
          loadInvoices();
        });
      } else {
        loadInvoices();
      }
>>>>>>> 4fbaa5a (first commit)
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
<<<<<<< HEAD
  const query = state.user ? `?user_id=${state.user.id}` : '';
  const resp = await fetch(`/api/v1/invoices${query}`);
=======
  // 构建查询参数：user_id、q、start_date、end_date
  const params = new URLSearchParams();
  if (state.user) params.set('user_id', state.user.id);
  const qInput = document.getElementById('invoice-search');
  const startInput = document.getElementById('invoice-start');
  const endInput = document.getElementById('invoice-end');
  if (qInput && qInput.value.trim()) params.set('q', qInput.value.trim());
  if (startInput && startInput.value) params.set('start_date', startInput.value);
  if (endInput && endInput.value) params.set('end_date', endInput.value);
  const resp = await fetch(`/api/v1/invoices?${params.toString()}`);
>>>>>>> 4fbaa5a (first commit)
  const data = await resp.json();
  if (!data.success || !invoiceTable) return;
  const tbody = invoiceTable.querySelector('tbody');
  tbody.innerHTML = '';
  data.data.forEach((inv) => {
    const tr = document.createElement('tr');
<<<<<<< HEAD
    tr.innerHTML = `
      <td>${inv.file_name}</td>
      <td>${inv.vendor || '-'}</td>
      <td>${inv.amount ?? '-'}</td>
      <td>${inv.category || '-'}</td>
      <td>${inv.status}</td>
      <td>
        ${inv.voucher_pdf_url ? `<a href="${inv.voucher_pdf_url}" target="_blank">下载凭证</a>` : '生成中'}
=======
    const createdAt = inv.created_at ? new Date(inv.created_at).toLocaleString() : '-';
    const issueAt = inv.issue_date ? new Date(inv.issue_date).toLocaleString() : '-';
    const previewLink = `/api/v1/invoices/${inv.id}/file`;
    tr.innerHTML = `
      <td><input type="checkbox" class="invoice-select" data-id="${inv.id}" /></td>
      <td>${inv.file_name}</td>
      <td>${inv.vendor || '-'}</td>
      <td>${issueAt}</td>
      <td>${inv.amount ?? '-'}</td>
      <td>${inv.category || '-'}</td>
      <td>${createdAt}</td>
      <td>${inv.status}</td>
      <td><a href="${previewLink}" target="_blank">预览</a></td>
      <td><a href="/api/v1/invoices/${inv.id}/file" target="_blank">下载发票</a></td>
      <td>
        <a href="#" class="delete-invoice" data-id="${inv.id}">删除</a>
>>>>>>> 4fbaa5a (first commit)
      </td>
    `;
    tbody.appendChild(tr);
  });
<<<<<<< HEAD
=======
  // 绑定删除事件
  tbody.querySelectorAll('.delete-invoice').forEach((el) => {
    el.addEventListener('click', async (e) => {
      e.preventDefault();
      const id = el.dataset.id;
      if (!confirm('确认删除该发票及其凭证？此操作不可撤销')) return;
      try {
        const resp = await fetch(`/api/v1/invoices/${id}`, { method: 'DELETE' });
        const res = await resp.json();
        if (res.success) {
          loadInvoices();
        } else {
          alert('删除失败: ' + (res.error || 'unknown'));
        }
      } catch (err) {
        alert('删除出错: ' + err.message);
      }
    });
  });

  // 绑定 select-all
  const selectAll = document.getElementById('select-all-invoices');
  if (selectAll) {
    selectAll.checked = false;
    selectAll.addEventListener('change', () => {
      const checked = selectAll.checked;
      tbody.querySelectorAll('.invoice-select').forEach((cb) => (cb.checked = checked));
    });
  }
};

// 绑定筛选按钮
const bindInvoiceFilters = () => {
  const btn = document.getElementById('invoice-search-btn');
  const clearBtn = document.getElementById('invoice-clear-btn');
  btn?.addEventListener('click', (e) => {
    e.preventDefault();
    loadInvoices();
  });
  clearBtn?.addEventListener('click', (e) => {
    e.preventDefault();
    const qInput = document.getElementById('invoice-search');
    const startInput = document.getElementById('invoice-start');
    const endInput = document.getElementById('invoice-end');
    if (qInput) qInput.value = '';
    if (startInput) startInput.value = '';
    if (endInput) endInput.value = '';
    loadInvoices();
  });
>>>>>>> 4fbaa5a (first commit)
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
<<<<<<< HEAD
  loadInvoices();
});
=======
  bindInvoiceFilters();
  loadInvoices();
  bindGenerateExcel();
});

// 生成 Excel 批量凭证
const bindGenerateExcel = () => {
  const btn = document.getElementById('generate-excel-btn');
  btn?.addEventListener('click', async (e) => {
    e.preventDefault();
    const selected = Array.from(document.querySelectorAll('.invoice-select:checked')).map((el) => el.dataset.id);
    if (!selected.length) {
      alert('请先勾选要生成凭证的发票');
      return;
    }
    if (!confirm(`将为 ${selected.length} 张发票生成 Excel 凭证并下载，继续？`)) return;
    try {
      const resp = await fetch('/api/v1/invoices/voucher_excel', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ invoice_ids: selected }),
      });
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}));
        alert('生成失败: ' + (err.error || resp.statusText));
        return;
      }
      const blob = await resp.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `vouchers_${Date.now()}.xlsx`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      alert('生成出错: ' + err.message);
    }
  });
};

// 插入临时行，显示上传后的占位状态
const insertTemporaryInvoice = (doc) => {
  if (!invoiceTable) return;
  const tbody = invoiceTable.querySelector('tbody');
  const tr = document.createElement('tr');
  const filename = doc.file_name || doc.fileName || '上传的文件';
  const vendor = doc.vendor || '-';
  const issueAt = doc.issue_date ? new Date(doc.issue_date).toLocaleString() : '-';
  const createdAt = '-';
  tr.classList.add('temp-invoice');
  tr.innerHTML = `
    <td>${filename}</td>
    <td>${vendor}</td>
    <td>${issueAt}</td>
    <td>-</td>
    <td>-</td>
    <td>${createdAt}</td>
    <td>处理中...</td>
    <td>-</td>
    <td>生成中</td>
    <td><span class="muted">等待写入</span></td>
  `;
  tbody.insertBefore(tr, tbody.firstChild);
};

// 轮询检查发票是否已写入数据库（通过 invoices 接口查找 id）
const pollInvoiceExists = async (docId, attempts = 10, intervalMs = 2000) => {
  for (let i = 0; i < attempts; i++) {
    try {
      const params = new URLSearchParams();
      if (state.user) params.set('user_id', state.user.id);
      const resp = await fetch(`/api/v1/invoices?${params.toString()}`);
      const data = await resp.json();
      if (data.success && Array.isArray(data.data)) {
        const found = data.data.find((inv) => inv.id === docId);
        if (found) return true;
      }
    } catch (err) {
      // ignore
    }
    // wait
    await new Promise((r) => setTimeout(r, intervalMs));
  }
  return false;
};
>>>>>>> 4fbaa5a (first commit)
