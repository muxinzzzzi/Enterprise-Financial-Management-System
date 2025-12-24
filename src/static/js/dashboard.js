const PAGE_SIZE = 6;
const state = {
  user: null,
  charts: {},
  libraryPage: 1,
  voucherPage: 1,
  kbSelectedRule: null,
  kbPage: 1,
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
const financialTabButtons = document.querySelectorAll('[data-financial-tab]');
const financialPanes = document.querySelectorAll('[data-financial-pane]');
const allFinancialTabButtons = document.querySelectorAll('[data-all-financial-tab]');
const allFinancialContents = document.querySelectorAll('[data-all-financial-content]');
const riskTableBody = document.querySelector('#risk-table tbody');
const riskPaginationEl = document.getElementById('risk-pagination');
const riskSearchInput = document.getElementById('risk-search');
const riskStartInput = document.getElementById('risk-date-start');
const riskEndInput = document.getElementById('risk-date-end');
const riskStatusInputs = document.querySelectorAll('[data-risk-status]');
const riskRefreshBtn = document.getElementById('risk-refresh');
const riskMasterCheckbox = document.getElementById('risk-master');
const drawerEl = document.getElementById('risk-drawer');
const drawerEmpty = document.getElementById('risk-empty');
const drawerDetail = document.getElementById('risk-detail');
const drawerTitle = document.getElementById('drawer-title');
const drawerSubtitle = document.getElementById('drawer-subtitle');
const drawerCloseBtn = document.getElementById('risk-drawer-close');
const riskTabButtons = document.querySelectorAll('[data-risk-tab]');
const riskPanes = document.querySelectorAll('[data-risk-pane]');
const summaryAmount = document.getElementById('summary-amount');
const summaryInvoiceNo = document.getElementById('summary-invoice-no');
const summaryBuyer = document.getElementById('summary-buyer');
const summaryVendor = document.getElementById('summary-vendor');
const summaryDate = document.getElementById('summary-date');
const summaryCategory = document.getElementById('summary-category');
const summaryConclusion = document.getElementById('summary-conclusion');
const summaryViewRulesBtn = document.getElementById('summary-view-rules');
const needInfoPanel = document.getElementById('need-info-panel');
const needAttach = document.getElementById('need-attach');
const needNote = document.getElementById('need-note');
const needApproval = document.getElementById('need-approval');
const needComment = document.getElementById('need-comment');
const needInfoSaveBtn = document.getElementById('need-info-save');
const needInfoCancelBtn = document.getElementById('need-info-cancel');
const ragFlagsEl = document.getElementById('rag-flags');
const ragRulesEl = document.getElementById('rag-rules');
const ragExplainToggle = document.getElementById('rag-explain-toggle');
const ragExplainBody = document.getElementById('rag-explain-body');
const ragBasis = document.getElementById('rag-basis');
const ragNext = document.getElementById('rag-next');
const evidenceImage = document.getElementById('evidence-image');
const evidenceHighlights = document.getElementById('evidence-highlights');
const evidenceOcr = document.getElementById('evidence-ocr');
const evidenceJson = document.getElementById('evidence-json');
const evidenceRagHits = document.getElementById('evidence-rag-hits');
const auditTrail = document.getElementById('audit-trail');
const actionApproveBtn = document.getElementById('action-approve');
const actionNeedInfoBtn = document.getElementById('action-need-info');
const actionRejectBtn = document.getElementById('action-reject');
const kbTableBody = document.querySelector('#kb-table tbody');
const kbSearchInput = document.getElementById('kb-search');
const kbTitleInput = document.getElementById('kb-title');
const kbTagsInput = document.getElementById('kb-tags');
const kbDescInput = document.getElementById('kb-desc');
const kbContentInput = document.getElementById('kb-content');
const kbChangeNoteInput = document.getElementById('kb-change-note');
const kbRuleIdInput = document.getElementById('kb-rule-id');
const kbFormTitle = document.getElementById('kb-form-title');
const kbVersionsEl = document.getElementById('kb-versions');
const kbMasterCheckbox = document.getElementById('kb-master');
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
  category: document.getElementById('category-chart'),
  risk: document.getElementById('risk-chart'),
};

const initCharts = () => {
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
  const { q, start_date, end_date, page, page_size } = params;
  if (q) searchParams.set('q', q);
  if (start_date) searchParams.set('start_date', start_date);
  if (end_date) searchParams.set('end_date', end_date);
  if (page) searchParams.set('page', page);
  if (page_size) searchParams.set('page_size', page_size);
  if (state.user?.id) searchParams.set('user_id', state.user.id);
  const resp = await fetch(`/api/v1/invoices?${searchParams.toString()}`);
  const data = await resp.json();
  if (!data.success) throw new Error(data.error || '获取发票失败');
  return data.data || { items: [], total: 0, page: 1, page_size: PAGE_SIZE };
};

const fetchVouchers = async (params = {}) => {
  const searchParams = new URLSearchParams();
  const { q, start_date, end_date, page, page_size } = params;
  if (q) searchParams.set('q', q);
  if (start_date) searchParams.set('start_date', start_date);
  if (end_date) searchParams.set('end_date', end_date);
  if (page) searchParams.set('page', page);
  if (page_size) searchParams.set('page_size', page_size);
  if (state.user?.id) searchParams.set('user_id', state.user.id);
  const resp = await fetch(`/api/v1/vouchers?${searchParams.toString()}`);
  const data = await resp.json();
  if (!data.success) throw new Error(data.error || '获取凭证失败');
  return data.data || { items: [], total: 0, page: 1, page_size: PAGE_SIZE };
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
        <td>${doc.display_id ?? doc.id}</td>
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
        <td>${row.display_id ?? row.voucher_no ?? row.id}</td>
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
    const data = await fetchInvoices({ q, start_date, end_date, page: state.libraryPage, page_size: PAGE_SIZE });
    const items = data.items || [];
    const total = data.total || 0;
    const totalPages = Math.max(1, Math.ceil(total / (data.page_size || PAGE_SIZE)));
    // 如果当前页超出范围，回退一页重新加载
    if (!items.length && state.libraryPage > 1 && state.libraryPage > totalPages) {
      state.libraryPage = totalPages;
      return loadLibrary();
    }
    renderLibraryTable(items);
    renderPagination('library-pagination', total, data.page || state.libraryPage, data.page_size || PAGE_SIZE, (p) => {
      state.libraryPage = p;
      loadLibrary();
    });
    return items;
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
    const data = await fetchVouchers({ q, start_date, end_date, page: state.voucherPage, page_size: PAGE_SIZE });
    const items = data.items || [];
    const total = data.total || 0;
    const totalPages = Math.max(1, Math.ceil(total / (data.page_size || PAGE_SIZE)));
    if (!items.length && state.voucherPage > 1 && state.voucherPage > totalPages) {
      state.voucherPage = totalPages;
      return loadVoucherList();
    }
    renderVoucherTable(items);
    renderPagination('voucher-pagination', total, data.page || state.voucherPage, data.page_size || PAGE_SIZE, (p) => {
      state.voucherPage = p;
      loadVoucherList();
    });
    return items;
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

  searchBtn?.addEventListener('click', () => {
    state.libraryPage = 1;
    loadLibrary();
  });
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
        state.libraryPage = 1;
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
      state.libraryPage = 1;
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
  searchBtn?.addEventListener('click', () => {
    state.voucherPage = 1;
    loadVoucherList();
  });
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
        state.voucherPage = 1;
        await loadVoucherList();
      } catch (err) {
        alert(err.message || err);
      } finally {
        clearBtn.disabled = false;
        clearBtn.textContent = '清除';
      }
    } else {
      resetFilters();
      state.voucherPage = 1;
      loadVoucherList();
    }
  });
};

const refreshDashboard = async () => {
  const query = state.user ? `?user_id=${state.user.id}` : '';
  const resp = await fetch(`/api/v1/dashboard/summary${query}`);
  const data = await resp.json();
  if (!data.success) return;
  const { category_breakdown, risk } = data.data;

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

const onViewSwitch = (view) => {
  if (view === 'assistant') {
    loadRiskQueue();
  }
  if (view === 'knowledge') {
    loadKnowledgeRules();
  }
};

const switchView = (view) => {
  if (!view) return;
  navItems.forEach((item) => item.classList.toggle('active', item.dataset.view === view));
  viewSections.forEach((section) => section.classList.toggle('active', section.dataset.viewSection === view));
  onViewSwitch(view);
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

// 移除旧的报表标签页逻辑，现在使用financial-report-tabs

// 移除旧的all-report-tabs逻辑

const initFinancialTabs = () => {
  financialTabButtons.forEach((btn) => {
    btn.addEventListener('click', () => {
      const tab = btn.dataset.financialTab;
      financialTabButtons.forEach((b) => b.classList.toggle('active', b === btn));
      financialPanes.forEach((pane) => pane.classList.toggle('active', pane.dataset.financialPane === tab));
      const targetSelector = btn.dataset.target;
      if (targetSelector) {
        const targetEl = document.querySelector(targetSelector);
        targetEl?.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    });
  });
};

const initAllFinancialTabs = () => {
  allFinancialTabButtons.forEach((btn) => {
    btn.addEventListener('click', () => {
      const tab = btn.dataset.allFinancialTab;
      allFinancialTabButtons.forEach((b) => b.classList.toggle('active', b === btn));
      allFinancialContents.forEach((pane) => pane.classList.toggle('active', pane.dataset.allFinancialContent === tab));
    });
  });
};

const shortenText = (text, len = 14) => {
  if (!text) return '';
  return text.length > len ? `${text.slice(0, len)}...` : text;
};

const tagDict = {
  taxi: '出租车',
  flight: '机票',
  lodging: '住宿',
  hotel: '酒店',
  meals: '餐饮',
  allowance: '补贴',
  equipment: '设备',
  lab_consumables: '实验耗材',
  general: '通用',
  city_transport: '市内交通',
  business_trip: '差旅',
  client_entertainment: '客户接待',
  lab_operation: '实验运营',
  lab_equipment_purchase: '实验设备',
};

const localizeTags = (tags = []) => {
  if (!Array.isArray(tags)) return [];
  return tags.map((t) => {
    const key = String(t).trim();
    return tagDict[key] || key;
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

// 财务报表表单处理
const initFinancialReports = () => {
  // 资产负债表表单
  const balanceSheetForm = document.getElementById('balance-sheet-form');
  balanceSheetForm?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const loadingEl = document.getElementById('balance-sheet-loading');
    const outputEl = document.getElementById('balance-sheet-output');
    const aiEl = document.getElementById('balance-sheet-ai');
    const aiContentEl = document.getElementById('balance-sheet-ai-content');
    
    loadingEl.style.display = 'block';
    outputEl.textContent = '生成中...';
    
    const payload = {
      start_date: document.getElementById('balance-sheet-start')?.value || undefined,
      end_date: document.getElementById('balance-sheet-end')?.value || undefined,
      period_type: document.getElementById('balance-sheet-period')?.value || 'month',
      currency: document.getElementById('balance-sheet-currency')?.value || 'CNY',
      company_name: document.getElementById('balance-sheet-company')?.value || undefined,
      enable_ai_analysis: false, // AI分析改为按钮触发
    };
    if (state.user?.id) payload.user_id = state.user.id;
    
    try {
      const resp = await fetch('/api/v1/financial-reports/balance-sheet', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const data = await resp.json();
      if (!data.success) throw new Error(data.error || '生成失败');
      
      outputEl.innerHTML = window.marked.parse(data.markdown_content || '');
      
      // 显示PDF和AI按钮
      const pdfPreviewBtn = document.getElementById('balance-sheet-pdf-preview');
      const pdfDownloadBtn = document.getElementById('balance-sheet-pdf-download');
      const aiBtn = document.getElementById('balance-sheet-ai-btn');
      
      if (pdfPreviewBtn) {
        pdfPreviewBtn.style.display = 'inline-block';
        pdfPreviewBtn.onclick = () => {
          // 优先使用PDF路径，如果没有则使用markdown路径（后端会自动转换）
          const filePath = data.pdf_path || data.markdown_path;
          if (filePath) {
            window.open(`/api/v1/financial-reports/pdf/${encodeURIComponent(filePath)}`, '_blank');
          } else {
            generatePDF('balance-sheet', payload, pdfPreviewBtn, pdfDownloadBtn);
          }
        };
      }
      if (pdfDownloadBtn) {
        pdfDownloadBtn.style.display = 'inline-block';
        pdfDownloadBtn.onclick = () => {
          // 优先使用PDF路径，如果没有则使用markdown路径（后端会自动转换）
          const filePath = data.pdf_path || data.markdown_path;
          if (filePath) {
            window.location.href = `/api/v1/financial-reports/pdf/${encodeURIComponent(filePath)}?download=1`;
          } else {
            generatePDF('balance-sheet', payload, pdfPreviewBtn, pdfDownloadBtn, true);
          }
        };
      }
      if (aiBtn) {
        aiBtn.style.display = 'inline-block';
        aiBtn.onclick = () => generateAIAnalysis('balance-sheet', payload, aiBtn, aiEl, aiContentEl);
      }
      
      // 保存报表数据到state
      state.balanceSheetData = data;
    } catch (err) {
      outputEl.textContent = `生成失败: ${err.message || err}`;
    } finally {
      loadingEl.style.display = 'none';
    }
  });

  // 利润表表单
  const incomeStatementForm = document.getElementById('income-statement-form');
  incomeStatementForm?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const loadingEl = document.getElementById('income-statement-loading');
    const outputEl = document.getElementById('income-statement-output');
    const aiEl = document.getElementById('income-statement-ai');
    const aiContentEl = document.getElementById('income-statement-ai-content');
    
    loadingEl.style.display = 'block';
    outputEl.textContent = '生成中...';
    
    const payload = {
      start_date: document.getElementById('income-statement-start')?.value || undefined,
      end_date: document.getElementById('income-statement-end')?.value || undefined,
      period_type: document.getElementById('income-statement-period')?.value || 'month',
      currency: document.getElementById('income-statement-currency')?.value || 'CNY',
      company_name: document.getElementById('income-statement-company')?.value || undefined,
      enable_ai_analysis: false,
    };
    if (state.user?.id) payload.user_id = state.user.id;
    
    try {
      const resp = await fetch('/api/v1/financial-reports/income-statement', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const data = await resp.json();
      if (!data.success) throw new Error(data.error || '生成失败');
      
      outputEl.innerHTML = window.marked.parse(data.markdown_content || '');
      
      const pdfPreviewBtn = document.getElementById('income-statement-pdf-preview');
      const pdfDownloadBtn = document.getElementById('income-statement-pdf-download');
      const aiBtn = document.getElementById('income-statement-ai-btn');
      
      if (pdfPreviewBtn) {
        pdfPreviewBtn.style.display = 'inline-block';
        pdfPreviewBtn.onclick = () => {
          const filePath = data.pdf_path || data.markdown_path;
          if (filePath) {
            window.open(`/api/v1/financial-reports/pdf/${encodeURIComponent(filePath)}`, '_blank');
          } else {
            generatePDF('income-statement', payload, pdfPreviewBtn, pdfDownloadBtn);
          }
        };
      }
      if (pdfDownloadBtn) {
        pdfDownloadBtn.style.display = 'inline-block';
        pdfDownloadBtn.onclick = () => {
          const filePath = data.pdf_path || data.markdown_path;
          if (filePath) {
            window.location.href = `/api/v1/financial-reports/pdf/${encodeURIComponent(filePath)}?download=1`;
          } else {
            generatePDF('income-statement', payload, pdfPreviewBtn, pdfDownloadBtn, true);
          }
        };
      }
      if (aiBtn) {
        aiBtn.style.display = 'inline-block';
        aiBtn.onclick = () => generateAIAnalysis('income-statement', payload, aiBtn, aiEl, aiContentEl);
      }
      
      state.incomeStatementData = data;
    } catch (err) {
      outputEl.textContent = `生成失败: ${err.message || err}`;
    } finally {
      loadingEl.style.display = 'none';
    }
  });

  // 现金流量表表单
  const cashFlowForm = document.getElementById('cash-flow-form');
  cashFlowForm?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const loadingEl = document.getElementById('cash-flow-loading');
    const outputEl = document.getElementById('cash-flow-output');
    const aiEl = document.getElementById('cash-flow-ai');
    const aiContentEl = document.getElementById('cash-flow-ai-content');
    
    loadingEl.style.display = 'block';
    outputEl.textContent = '生成中...';
    
    const payload = {
      start_date: document.getElementById('cash-flow-start')?.value || undefined,
      end_date: document.getElementById('cash-flow-end')?.value || undefined,
      period_type: document.getElementById('cash-flow-period')?.value || 'month',
      currency: document.getElementById('cash-flow-currency')?.value || 'CNY',
      company_name: document.getElementById('cash-flow-company')?.value || undefined,
      enable_ai_analysis: false,
    };
    if (state.user?.id) payload.user_id = state.user.id;
    
    try {
      const resp = await fetch('/api/v1/financial-reports/cash-flow', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const data = await resp.json();
      if (!data.success) throw new Error(data.error || '生成失败');
      
      outputEl.innerHTML = window.marked.parse(data.markdown_content || '');
      
      const pdfPreviewBtn = document.getElementById('cash-flow-pdf-preview');
      const pdfDownloadBtn = document.getElementById('cash-flow-pdf-download');
      const aiBtn = document.getElementById('cash-flow-ai-btn');
      
      if (pdfPreviewBtn) {
        pdfPreviewBtn.style.display = 'inline-block';
        pdfPreviewBtn.onclick = () => {
          const filePath = data.pdf_path || data.markdown_path;
          if (filePath) {
            window.open(`/api/v1/financial-reports/pdf/${encodeURIComponent(filePath)}`, '_blank');
          } else {
            generatePDF('cash-flow', payload, pdfPreviewBtn, pdfDownloadBtn);
          }
        };
      }
      if (pdfDownloadBtn) {
        pdfDownloadBtn.style.display = 'inline-block';
        pdfDownloadBtn.onclick = () => {
          const filePath = data.pdf_path || data.markdown_path;
          if (filePath) {
            window.location.href = `/api/v1/financial-reports/pdf/${encodeURIComponent(filePath)}?download=1`;
          } else {
            generatePDF('cash-flow', payload, pdfPreviewBtn, pdfDownloadBtn, true);
          }
        };
      }
      if (aiBtn) {
        aiBtn.style.display = 'inline-block';
        aiBtn.onclick = () => generateAIAnalysis('cash-flow', payload, aiBtn, aiEl, aiContentEl);
      }
      
      state.cashFlowData = data;
    } catch (err) {
      outputEl.textContent = `生成失败: ${err.message || err}`;
    } finally {
      loadingEl.style.display = 'none';
    }
  });

  // 生成所有财务报表表单
  const allFinancialReportsForm = document.getElementById('all-financial-reports-form');
  allFinancialReportsForm?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const loadingEl = document.getElementById('all-financial-loading');
    const balanceSheetEl = document.getElementById('all-financial-balance-sheet');
    const incomeStatementEl = document.getElementById('all-financial-income-statement');
    const cashFlowEl = document.getElementById('all-financial-cash-flow');
    
    loadingEl.style.display = 'block';
    balanceSheetEl.textContent = '生成中...';
    incomeStatementEl.textContent = '生成中...';
    cashFlowEl.textContent = '生成中...';
    
    const payload = {
      start_date: document.getElementById('all-financial-start')?.value || undefined,
      end_date: document.getElementById('all-financial-end')?.value || undefined,
      period_type: document.getElementById('all-financial-period')?.value || 'month',
      currency: document.getElementById('all-financial-currency')?.value || 'CNY',
      company_name: document.getElementById('all-financial-company')?.value || undefined,
      enable_ai_analysis: false,
    };
    if (state.user?.id) payload.user_id = state.user.id;
    
    try {
      const resp = await fetch('/api/v1/financial-reports/all', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const data = await resp.json();
      if (!data.success) throw new Error(data.error || '生成失败');
      
      const reports = data.reports || {};
      
      // 资产负债表
      if (reports.balance_sheet?.markdown_content) {
        balanceSheetEl.innerHTML = window.marked.parse(reports.balance_sheet.markdown_content);
        setupReportButtons('all-financial-balance-sheet', reports.balance_sheet, 'balance-sheet', payload);
      } else {
        balanceSheetEl.textContent = '生成失败';
      }
      
      // 利润表
      if (reports.income_statement?.markdown_content) {
        incomeStatementEl.innerHTML = window.marked.parse(reports.income_statement.markdown_content);
        setupReportButtons('all-financial-income-statement', reports.income_statement, 'income-statement', payload);
      } else {
        incomeStatementEl.textContent = '生成失败';
      }
      
      // 现金流量表
      if (reports.cash_flow?.markdown_content) {
        cashFlowEl.innerHTML = window.marked.parse(reports.cash_flow.markdown_content);
        setupReportButtons('all-financial-cash-flow', reports.cash_flow, 'cash-flow', payload);
      } else {
        cashFlowEl.textContent = '生成失败';
      }
      
      state.allFinancialReportsData = data;
    } catch (err) {
      balanceSheetEl.textContent = `生成失败: ${err.message || err}`;
      incomeStatementEl.textContent = `生成失败: ${err.message || err}`;
      cashFlowEl.textContent = `生成失败: ${err.message || err}`;
    } finally {
      loadingEl.style.display = 'none';
    }
  });
};

// 辅助函数：生成PDF
const generatePDF = async (reportType, payload, previewBtn, downloadBtn, isDownload = false) => {
  try {
    if (previewBtn) {
      previewBtn.disabled = true;
      previewBtn.textContent = '生成PDF中...';
    }
    
    const resp = await fetch(`/api/v1/financial-reports/${reportType}/pdf`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const data = await resp.json();
    if (!data.success) throw new Error(data.error || 'PDF生成失败');
    
    // 如果PDF路径存在，直接使用；否则使用markdown路径
    const filePath = data.pdf_path || data.markdown_path;
    if (!filePath) {
      throw new Error('未找到文件路径');
    }
    
    if (isDownload) {
      window.location.href = `/api/v1/financial-reports/pdf/${encodeURIComponent(filePath)}?download=1`;
    } else {
      window.open(`/api/v1/financial-reports/pdf/${encodeURIComponent(filePath)}`, '_blank');
    }
  } catch (err) {
    alert(`PDF生成失败: ${err.message || err}`);
  } finally {
    if (previewBtn) {
      previewBtn.disabled = false;
      previewBtn.textContent = '预览PDF';
    }
  }
};

// 辅助函数：生成AI分析
const generateAIAnalysis = async (reportType, payload, aiBtn, aiEl, aiContentEl) => {
  try {
    aiBtn.disabled = true;
    aiBtn.textContent = '生成中...';
    aiEl.style.display = 'block';
    aiContentEl.textContent = '正在生成AI分析...';
    
    const payloadWithAI = { ...payload, enable_ai_analysis: true };
    const resp = await fetch(`/api/v1/financial-reports/${reportType}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payloadWithAI),
    });
    const data = await resp.json();
    if (!data.success) throw new Error(data.error || 'AI分析生成失败');
    
    if (data.ai_analysis) {
      aiContentEl.innerHTML = window.marked.parse(data.ai_analysis);
    } else {
      aiContentEl.textContent = 'AI分析生成失败';
    }
  } catch (err) {
    aiContentEl.textContent = `AI分析生成失败: ${err.message || err}`;
  } finally {
    aiBtn.disabled = false;
    aiBtn.textContent = '生成AI分析';
  }
};

// 辅助函数：设置报表按钮
const setupReportButtons = (prefix, reportData, reportType, payload) => {
  const pdfPreviewBtn = document.getElementById(`${prefix}-pdf-preview`);
  const pdfDownloadBtn = document.getElementById(`${prefix}-pdf-download`);
  const aiBtn = document.getElementById(`${prefix}-ai-btn`);
  
  if (pdfPreviewBtn) {
    pdfPreviewBtn.style.display = 'inline-block';
    pdfPreviewBtn.onclick = () => {
      const filePath = reportData.pdf_path || reportData.markdown_path;
      if (filePath) {
        window.open(`/api/v1/financial-reports/pdf/${encodeURIComponent(filePath)}`, '_blank');
      } else {
        generatePDF(reportType, payload, pdfPreviewBtn, pdfDownloadBtn);
      }
    };
  }
  if (pdfDownloadBtn) {
    pdfDownloadBtn.style.display = 'inline-block';
    pdfDownloadBtn.onclick = () => {
      const filePath = reportData.pdf_path || reportData.markdown_path;
      if (filePath) {
        window.location.href = `/api/v1/financial-reports/pdf/${encodeURIComponent(filePath)}?download=1`;
      } else {
        generatePDF(reportType, payload, pdfPreviewBtn, pdfDownloadBtn, true);
      }
    };
  }
  if (aiBtn) {
    aiBtn.style.display = 'inline-block';
    aiBtn.onclick = () => {
      // 为批量报表生成AI分析需要特殊处理
      alert('请使用单个报表页面的AI分析功能');
    };
  }
};

window.addEventListener('load', async () => {
  await fetchCurrentUser();
  initNav();
  initInvoiceTabs();
  initFinancialTabs();
  initAllFinancialTabs();
  initFinancialReports();
  initLibraryActions();
  initQAForm();
  initVoucherActions();
  initCharts();
  refreshDashboard();
  loadLibrary();
  loadVoucherList();
});

// ─────────────────────────────────────────────────────────────────────────────
// QA 问答功能
// ─────────────────────────────────────────────────────────────────────────────
function initQAForm() {
  const qaForm = document.getElementById('qa-form');
  const qaQuestion = document.getElementById('qa-question');
  const qaStartDate = document.getElementById('qa-start-date');
  const qaEndDate = document.getElementById('qa-end-date');
  const qaSubmitBtn = document.getElementById('qa-submit-btn');
  const qaLoading = document.getElementById('qa-loading');
  const qaResult = document.getElementById('qa-result');
  const qaAnswer = document.getElementById('qa-answer');
  const qaError = document.getElementById('qa-error');
  const qaEvidence = document.getElementById('qa-evidence');
  const qaSql = document.getElementById('qa-sql');
  const qaParams = document.getElementById('qa-params');
  const qaRowsPreview = document.getElementById('qa-rows-preview');
  const qaFollowups = document.getElementById('qa-followups');
  const qaFollowupsList = document.getElementById('qa-followups-list');

  if (!qaForm) return;

  // 支持Enter键提交（Shift+Enter换行）
  qaQuestion.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      qaForm.dispatchEvent(new Event('submit'));
    }
  });

  qaForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const question = qaQuestion.value.trim();
    if (!question) return;

    const startDate = qaStartDate.value || null;
    const endDate = qaEndDate.value || null;

    // 显示加载状态
    qaSubmitBtn.disabled = true;
    qaLoading.style.display = 'inline';
    qaResult.style.display = 'none';
    qaError.style.display = 'none';

    try {
      const response = await fetch('/api/v1/qa/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question,
          start_date: startDate,
          end_date: endDate,
        }),
      });

      const data = await response.json();

      if (data.success) {
        // 渲染答案（使用marked库）
        qaAnswer.innerHTML = marked.parse(data.answer_md || '无答案');
        
        // 显示证据
        if (data.evidence) {
          qaSql.textContent = data.evidence.sql || '';
          qaParams.textContent = JSON.stringify(data.evidence.params || {}, null, 2);
          
          // 渲染数据预览
          if (data.evidence.rows_preview && data.evidence.rows_preview.length > 0) {
            const rows = data.evidence.rows_preview;
            const columns = data.evidence.columns || Object.keys(rows[0] || {});
            
            let tableHTML = '<table style="width: 100%; border-collapse: collapse; font-size: 0.9em;">';
            tableHTML += '<thead><tr>';
            columns.forEach(col => {
              tableHTML += `<th style="border: 1px solid #ddd; padding: 8px; background: #f5f5f5; text-align: left;">${col}</th>`;
            });
            tableHTML += '</tr></thead><tbody>';
            
            rows.forEach(row => {
              tableHTML += '<tr>';
              columns.forEach(col => {
                tableHTML += `<td style="border: 1px solid #ddd; padding: 8px;">${row[col] !== null && row[col] !== undefined ? row[col] : ''}</td>`;
              });
              tableHTML += '</tr>';
            });
            
            tableHTML += '</tbody></table>';
            tableHTML += `<p style="margin-top: 0.5rem; color: #666; font-size: 0.9em;">共 ${data.evidence.total_rows} 行，显示前 ${rows.length} 行</p>`;
            qaRowsPreview.innerHTML = tableHTML;
          } else {
            qaRowsPreview.innerHTML = '<p style="color: #666;">无数据</p>';
          }
        }
        
        // 显示后续问题建议
        if (data.followups && data.followups.length > 0) {
          qaFollowupsList.innerHTML = '';
          data.followups.forEach(followup => {
            const btn = document.createElement('button');
            btn.className = 'ghost';
            btn.style.cssText = 'padding: 0.5rem 1rem; font-size: 0.9em;';
            btn.textContent = followup;
            btn.addEventListener('click', () => {
              qaQuestion.value = followup;
              qaForm.dispatchEvent(new Event('submit'));
            });
            qaFollowupsList.appendChild(btn);
          });
          qaFollowups.style.display = 'block';
        } else {
          qaFollowups.style.display = 'none';
        }
        
        qaResult.style.display = 'block';
      } else {
        qaError.textContent = data.error || '查询失败';
        qaError.style.display = 'block';
      }
    } catch (err) {
      console.error('QA查询失败:', err);
      qaError.textContent = `查询失败：${err.message}`;
      qaError.style.display = 'block';
    } finally {
      qaSubmitBtn.disabled = false;
      qaLoading.style.display = 'none';
    }
  });
}

const renderPagination = (containerId, total, page, pageSize, onChange) => {
  const container = document.getElementById(containerId);
  if (!container) return;
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  if (totalPages <= 1) {
    container.innerHTML = '';
    return;
  }
  const prevDisabled = page <= 1;
  const nextDisabled = page >= totalPages;
  container.innerHTML = `
    <button class="ghost" ${prevDisabled ? 'disabled' : ''} data-page="${page - 1}">上一页</button>
    <span style="margin:0 8px;">第 ${page} / ${totalPages} 页</span>
    <button class="ghost" ${nextDisabled ? 'disabled' : ''} data-page="${page + 1}">下一页</button>
  `;
  container.querySelectorAll('button[data-page]').forEach((btn) => {
    btn.addEventListener('click', () => {
      const target = Number(btn.dataset.page);
      if (target >= 1 && target <= totalPages) onChange(target);
    });
  });
};

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

// ---------- AI 审核：风险队列 + RAG ----------
const STATUS_META = {
  uploaded: { label: '待审核', tone: 'warning' },
  reviewing: { label: '待补充', tone: 'info' },
  review_rejected: { label: '已拒绝', tone: 'danger' },
  review_approved: { label: '已通过', tone: 'success' },
};

const RISK_PAGE_SIZE = 7;
const riskState = {
  queue: [],
  filtered: [],
  page: 1,
  selectedId: null,
  detail: null,
  loading: false,
};
const riskCache = {};
const riskLoadingMask = document.getElementById('risk-loading');

const getStatusLabel = (status) => STATUS_META[status]?.label || status || '--';
const renderStatusChip = (status) => {
  const meta = STATUS_META[status] || { tone: 'muted', label: status || '--' };
  return `<span class="chip ${meta.tone || 'muted'}">${meta.label}</span>`;
};

const paginate = (rows = []) => {
  const start = (riskState.page - 1) * RISK_PAGE_SIZE;
  return rows.slice(start, start + RISK_PAGE_SIZE);
};

const getSelectedStatuses = () => {
  const inputs = Array.from(document.querySelectorAll('[data-risk-status]:checked'));
  if (!inputs.length) return ['uploaded', 'reviewing'];
  return inputs.map((i) => i.value);
};

const reasonFromRow = (row = {}) => {
  const reasons = row.risk_reasons || [];
  if (reasons.length) return reasons.slice(0, 3).join(' / ');
  const flags = (row.policy_flags_detail || []).map((f) => f.rule_title || f.message).filter(Boolean);
  const anomalies = row.anomaly_tags || [];
  const merged = [...flags, ...anomalies];
  return merged.length ? merged.slice(0, 3).join(' / ') : '--';
};

const renderRiskTable = () => {
  if (!riskTableBody) return;
  const rows = paginate(riskState.filtered);
  if (!rows.length) {
    riskTableBody.innerHTML = '<tr><td colspan="10">暂无风险票据</td></tr>';
    return;
  }
  riskTableBody.innerHTML = rows
    .map(
      (row) => `
      <tr data-risk-id="${row.id}">
        <td><input type="checkbox" class="risk-row" data-id="${row.id}" /></td>
        <td>${row.id}</td>
        <td>${row.file_name || '--'}</td>
        <td>${row.vendor || '--'}</td>
        <td>${row.issue_date || '--'}</td>
        <td>${fmtAmount(row.amount)}</td>
        <td>${row.category || '--'}</td>
        <td>${reasonFromRow(row)}</td>
        <td>${renderStatusChip(row.status)}</td>
        <td><button class="ghost" data-review-btn="${row.id}">审核</button></td>
      </tr>`
    )
    .join('');

  riskTableBody.querySelectorAll('[data-review-btn]').forEach((btn) => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      loadRiskDetail(btn.dataset.reviewBtn);
    });
  });

  riskTableBody.querySelectorAll('tr[data-risk-id]').forEach((tr) => {
    tr.addEventListener('click', () => {
      const id = tr.dataset.riskId;
      loadRiskDetail(id);
    });
  });
};

const goRiskPage = (p) => {
  const totalPages = Math.max(1, Math.ceil(riskState.filtered.length / RISK_PAGE_SIZE));
  const target = Math.min(Math.max(p, 1), totalPages);
  riskState.page = target;
  renderRiskPagination();
  renderRiskTable();
};

const renderRiskPagination = () => {
  renderPagination('risk-pagination', riskState.filtered.length, riskState.page, RISK_PAGE_SIZE, (p) => {
    goRiskPage(p);
  });
};

const applyRiskFilters = (resetPage = false) => {
  if (!riskState.queue) return;
  const q = riskSearchInput?.value?.trim().toLowerCase() || '';
  const start = riskStartInput?.value ? new Date(riskStartInput.value).getTime() : null;
  const end = riskEndInput?.value ? new Date(riskEndInput.value).getTime() : null;
  const statuses = getSelectedStatuses();

  riskState.filtered = riskState.queue.filter((item) => {
    const statusOk = statuses.includes(item.status || 'uploaded');
    const text = `${item.file_name || ''} ${item.vendor || ''} ${item.buyer || ''} ${item.invoice_no || ''}`.toLowerCase();
    const searchOk = !q || text.includes(q);
    const tsRaw = item.issue_date || item.created_at;
    const ts = tsRaw ? new Date(tsRaw).getTime() : null;
    const startOk = start ? ts && ts >= start : true;
    const endOk = end ? ts && ts <= end : true;
    return statusOk && searchOk && startOk && endOk;
  });

  if (resetPage) riskState.page = 1;
  renderRiskPagination();
  renderRiskTable();
};

const loadRiskQueue = async () => {
  if (!riskTableBody) return;
  riskTableBody.innerHTML = '<tr><td colspan="10">加载中...</td></tr>';
  const params = new URLSearchParams({ status: 'all', limit: 200 });
  const q = riskSearchInput?.value?.trim();
  if (q) params.set('q', q);
  try {
    const resp = await fetch(`/api/v1/review/queue?${params.toString()}`);
    const data = await resp.json();
    if (!data.success) throw new Error(data.error || '加载审核队列失败');
    riskState.queue = data.data || [];
    applyRiskFilters(true);
  } catch (err) {
    riskTableBody.innerHTML = `<tr><td colspan="10">${err.message || err}</td></tr>`;
  }
};

const setDrawerVisibility = (visible) => {
  if (!drawerEl || !drawerDetail || !drawerEmpty) return;
  if (visible) {
    drawerEmpty.style.display = 'none';
    drawerDetail.classList.remove('hidden');
  } else {
    drawerEmpty.style.display = 'block';
    drawerDetail.classList.add('hidden');
  }
};

const buildConclusion = (detail) => {
  const flags = detail.policy_flags || [];
  if (flags.length) {
    const first = flags[0];
    const severity = (first.severity || '').toUpperCase();
    const msg = first.message || first.rule_title || '命中规则';
    if (severity === 'HIGH') return `高风险：${msg}`;
    if (severity === 'MEDIUM') return `需补充：${msg}`;
    return `提示：${msg}`;
  }
  if ((detail.anomalies || []).length) return `检测到异常：${detail.anomalies.slice(0, 2).join(' / ')}`;
  return '未发现明显风险，可复核后通过';
};

const renderAuditTrail = (history = []) => {
  if (!auditTrail) return;
  if (!history.length) {
    auditTrail.textContent = '暂无变更记录';
    return;
  }
  auditTrail.innerHTML = history
    .slice()
    .reverse()
    .map(
      (item) => `
      <div class="timeline-item">
        <div class="timeline-dot"></div>
        <div class="timeline-content">
          <div class="timeline-title">${item.field_name || '字段'} → <strong>${item.new_value ?? '空'}</strong></div>
          <p class="hint">原值：${item.old_value ?? '空'} · ${item.reason || item.comment || '--'} · ${fmtDateTime(
        item.timestamp || item.created_at
      )}</p>
        </div>
      </div>
    `
    )
    .join('');
};

const renderSummary = (detail) => {
  summaryAmount && (summaryAmount.textContent = fmtAmount(detail.amount));
  summaryInvoiceNo && (summaryInvoiceNo.textContent = detail.invoice_no || '--');
  summaryBuyer && (summaryBuyer.textContent = detail.buyer || '--');
  summaryVendor && (summaryVendor.textContent = detail.vendor || '--');
  summaryDate && (summaryDate.textContent = detail.issue_date || '--');
  summaryCategory && (summaryCategory.textContent = detail.category || '--');
  summaryConclusion && (summaryConclusion.textContent = buildConclusion(detail));
};

const renderRag = (detail) => {
  const flags = detail.policy_flags || [];
  if (ragFlagsEl) {
    if (!flags.length) {
      ragFlagsEl.innerHTML = '<span class="hint">暂无 flags</span>';
    } else {
      ragFlagsEl.innerHTML = flags
        .map((flag) => {
          const tone = flag.severity === 'HIGH' ? 'danger' : flag.severity === 'MEDIUM' ? 'warning' : 'info';
          return `<span class="flag-chip ${tone}">${flag.rule_title || '规则'} · ${flag.severity || ''}</span>`;
        })
        .join('');
    }
  }

  if (ragRulesEl) {
    if (!flags.length) {
      ragRulesEl.innerHTML = '<div class="hint">暂无规则命中</div>';
    } else {
      ragRulesEl.innerHTML = flags
        .map((flag) => {
          const tone = flag.severity === 'HIGH' ? 'danger' : flag.severity === 'MEDIUM' ? 'warning' : 'info';
          const tags = (flag.references || []).map((r) => `<span class="chip ghost">${r}</span>`).join('');
          return `
            <div class="rule-card">
              <div>
                <strong>${flag.rule_title || '规则'}</strong>
                <p class="hint">${flag.message || '触发原因'}</p>
                <div class="chip-group wrap">${tags}</div>
              </div>
              <span class="chip ${tone}">${flag.severity || 'MEDIUM'}</span>
            </div>
          `;
        })
        .join('');
    }
  }

  if (ragBasis) {
    const lines = [];
    if (detail.amount) lines.push(`金额：${fmtAmount(detail.amount)}`);
    if (detail.issue_date) lines.push(`开票日期：${detail.issue_date}`);
    if (detail.vendor) lines.push(`供应商：${detail.vendor}`);
    ragBasis.innerHTML = lines.join('<br/>') || '无';
  }
  if (ragNext) {
    const suggestion =
      flags.find((f) => f.severity === 'HIGH')?.message ||
      (detail.anomalies || [])[0] ||
      '若信息完整可直接通过，否则补充附件/审批。';
    ragNext.textContent = suggestion;
  }
};

const renderEvidence = (detail) => {
  if (evidenceImage) {
    if (detail.file_url) {
      evidenceImage.src = detail.file_url;
      evidenceImage.alt = detail.file_name || '发票';
    } else {
      evidenceImage.removeAttribute('src');
    }
  }
  if (evidenceHighlights) {
    const highlights = [
      ['金额', detail.amount],
      ['发票号', detail.invoice_no],
      ['抬头', detail.buyer],
      ['供应商', detail.vendor],
      ['发票日期', detail.issue_date],
      ['类别', detail.category],
    ]
      .filter(([, v]) => v !== undefined && v !== null && v !== '')
      .map(([k, v]) => `<div><strong>${k}</strong>：${v}</div>`)
      .join('');
    evidenceHighlights.innerHTML = highlights || '暂无可定位字段';
  }
  evidenceOcr && (evidenceOcr.textContent = detail.ocr_text || '未返回 OCR 原文');
  evidenceJson &&
    (evidenceJson.textContent = JSON.stringify(
      { normalized: detail.normalized_fields || {}, structured: detail.structured_fields || {} },
      null,
      2,
    ));
  evidenceRagHits &&
    (evidenceRagHits.textContent =
      detail.policy_hits?.length ? JSON.stringify(detail.policy_hits, null, 2) : '无检索记录');
  renderAuditTrail(detail.review_history || detail.review_logs || []);
};

const setDrawerLoading = (loading) => {
  riskState.loading = loading;
  if (riskLoadingMask) {
    riskLoadingMask.classList.toggle('hidden', !loading);
  }
};

const renderDrawer = () => {
  const detail = riskState.detail;
  if (!detail) {
    setDrawerVisibility(false);
    return;
  }
  setDrawerVisibility(true);
  toggleRiskTab('summary');
  toggleNeedInfoPanel(false);
  drawerTitle && (drawerTitle.textContent = `发票 #${detail.id} ${detail.invoice_no || ''}`.trim());
  drawerSubtitle && (drawerSubtitle.textContent = `${detail.file_name || '--'} · ${getStatusLabel(detail.status)}`);
  renderSummary(detail);
  renderRag(detail);
  renderEvidence(detail);
};

const loadRiskDetail = async (docId) => {
  if (!docId) return;
  setDrawerLoading(true);
  // 若已有缓存，先立即展示，再后台刷新
  if (riskCache[docId]) {
    riskState.selectedId = docId;
    riskState.detail = riskCache[docId];
    renderDrawer();
  }
  try {
    const resp = await fetch(`/api/v1/review/${docId}`);
    const data = await resp.json();
    if (!data.success) throw new Error(data.error || '加载失败');
    riskState.selectedId = docId;
    riskState.detail = data.data || null;
    if (riskState.detail) {
      riskCache[docId] = riskState.detail;
    }
    renderDrawer();
  } catch (err) {
    alert(err.message || err);
  } finally {
    setDrawerLoading(false);
  }
};

const toggleRiskTab = (tab) => {
  riskTabButtons.forEach((btn) => btn.classList.toggle('active', btn.dataset.riskTab === tab));
  riskPanes.forEach((pane) => pane.classList.toggle('active', pane.dataset.riskPane === tab));
};

const toggleNeedInfoPanel = (visible) => {
  if (!needInfoPanel) return;
  needInfoPanel.classList.toggle('hidden', !visible);
};

const submitNeedInfo = async () => {
  if (!riskState.detail?.id) return;
  const requests = [];
  if (needAttach?.checked) requests.push('附件');
  if (needNote?.checked) requests.push('备注说明');
  if (needApproval?.checked) requests.push('审批编号');
  const comment = needComment?.value || '';
  const payload = {
    reviewer_id: state.user?.id,
    changes: [
      { field_name: 'status', new_value: 'reviewing', reason: '需要补充', comment },
      { field_name: 'pending_materials', new_value: requests, reason: '需要补充', comment },
      { field_name: 'comment', new_value: comment, reason: '需要补充', comment },
    ],
  };
  try {
    const resp = await fetch(`/api/v1/review/${riskState.detail.id}/update`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const data = await resp.json();
    if (!data.success) throw new Error(data.error || '保存失败');
    riskState.detail = data.data || riskState.detail;
    toggleNeedInfoPanel(false);
    loadRiskQueue();
    renderDrawer();
    alert('已标记为待补充');
  } catch (err) {
    alert(err.message || err);
  }
};

const approveRisk = async () => {
  if (!riskState.detail?.id) {
    alert('请先选择票据');
    return;
  }
  try {
    const resp = await fetch(`/api/v1/review/${riskState.detail.id}/approve`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ reviewer_id: state.user?.id, comment: '' }),
    });
    const data = await resp.json();
    if (!data.success) throw new Error(data.error || '审核失败');
    riskState.detail = data.data || riskState.detail;
    loadRiskQueue();
    renderDrawer();
    alert('已通过');
  } catch (err) {
    alert(err.message || err);
  }
};

const rejectRisk = async () => {
  if (!riskState.detail?.id) {
    alert('请先选择票据');
    return;
  }
  const reason = prompt('拒绝理由（可选）', '违反报销规则');
  try {
    const resp = await fetch(`/api/v1/review/${riskState.detail.id}/update`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        reviewer_id: state.user?.id,
        changes: [{ field_name: 'status', new_value: 'review_rejected', reason: '拒绝', comment: reason || '' }],
      }),
    });
    const data = await resp.json();
    if (!data.success) throw new Error(data.error || '拒绝失败');
    riskState.detail = data.data || riskState.detail;
    loadRiskQueue();
    renderDrawer();
    alert('已拒绝');
  } catch (err) {
    alert(err.message || err);
  }
};

// ---------- 知识库管理 ----------
const parseCommaInput = (val) =>
  (val || '')
    .split(',')
    .map((t) => t.trim())
    .filter(Boolean);

const renderKbTable = (rows) => {
  if (!kbTableBody) return;
  if (!rows.length) {
    kbTableBody.innerHTML = '<tr><td colspan="5">暂无规则</td></tr>';
    return;
  }
  kbTableBody.innerHTML = rows
    .map(
      (row) => `
      <tr data-rule-id="${row.id}">
        <td><input type="checkbox" class="kb-row" data-id="${row.id}" /></td>
        <td>${row.title || '--'}</td>
        <td>${localizeTags(row.tags || []).join('、') || '--'}</td>
        <td>
          <div class="desc-cell">
            <span class="desc-text" data-full="${(row.summary || row.content || '').replace(/"/g, '&quot;')}">${shortenText(row.summary || row.content || '', 14)}</span>
            <button type="button" class="ghost desc-toggle" aria-label="toggle">▲</button>
          </div>
        </td>
        <td>${fmtDateTime(row.updated_at)}</td>
      </tr>
    `
    )
    .join('');

  kbTableBody.querySelectorAll('tr[data-rule-id]').forEach((tr) => {
    tr.addEventListener('click', () => {
      const ruleId = tr.dataset.ruleId;
      loadRuleDetail(ruleId);
    });
  });

  kbTableBody.querySelectorAll('.desc-toggle').forEach((btn) => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      const textEl = btn.parentElement.querySelector('.desc-text');
      if (!textEl) return;
      const full = textEl.dataset.full || '';
      const collapsed = shortenText(full, 14);
      const isExpanded = btn.textContent === '▼';
      textEl.textContent = isExpanded ? collapsed : full;
      btn.textContent = isExpanded ? '▲' : '▼';
    });
  });
};

const loadKnowledgeRules = async () => {
  const pageSize = 4;
  const params = new URLSearchParams();
  const q = kbSearchInput?.value?.trim();
  if (q) params.set('q', q);
  params.set('page', state.kbPage);
  params.set('page_size', pageSize);
  try {
    const resp = await fetch(`/api/v1/knowledge/rules?${params.toString()}`);
    const data = await resp.json();
    if (!data.success) throw new Error(data.error || '加载知识库失败');
    const payload = data.data || {};
    renderKbTable(payload.items || []);
    renderPagination('kb-pagination', payload.total || 0, payload.page || state.kbPage, payload.page_size || pageSize, (p) => {
      state.kbPage = p;
      loadKnowledgeRules();
    });
  } catch (err) {
    if (kbTableBody) kbTableBody.innerHTML = `<tr><td colspan="6">${err.message || err}</td></tr>`;
  }
};

const resetRuleForm = () => {
  state.kbSelectedRule = null;
  kbRuleIdInput && (kbRuleIdInput.value = '');
  kbTitleInput && (kbTitleInput.value = '');
  kbTagsInput && (kbTagsInput.value = '');
  kbDescInput && (kbDescInput.value = '');
  kbContentInput && (kbContentInput.value = '');
  kbChangeNoteInput && (kbChangeNoteInput.value = '');
  kbFormTitle && (kbFormTitle.textContent = '新增规则');
  kbVersionsEl && (kbVersionsEl.textContent = '请选择规则以查看历史');
};

const fillRuleForm = (rule) => {
  if (!rule) return;
  state.kbSelectedRule = rule.id;
  kbRuleIdInput && (kbRuleIdInput.value = rule.id);
  kbTitleInput && (kbTitleInput.value = rule.title || '');
  kbTagsInput && (kbTagsInput.value = (rule.tags || []).join(','));
  kbDescInput && (kbDescInput.value = rule.summary || '');
  kbContentInput && (kbContentInput.value = rule.content || '');
  kbFormTitle && (kbFormTitle.textContent = '编辑规则');
};

const loadRuleDetail = async (ruleId) => {
  try {
    const resp = await fetch(`/api/v1/knowledge/rules/${ruleId}`);
    const data = await resp.json();
    if (!data.success) throw new Error(data.error || '规则不存在');
    fillRuleForm(data.data || {});
    loadRuleVersions(ruleId);
  } catch (err) {
    alert(err.message || err);
  }
};

const loadRuleVersions = async (ruleId) => {
  if (!kbVersionsEl) return;
  kbVersionsEl.textContent = '加载中...';
  try {
    const resp = await fetch(`/api/v1/knowledge/rules/${ruleId}/versions`);
    const data = await resp.json();
    if (!data.success) throw new Error(data.error || '加载历史失败');
    const versions = data.data || [];
    if (!versions.length) {
      kbVersionsEl.textContent = '暂无历史版本';
      return;
    }
    kbVersionsEl.innerHTML = versions
      .map(
        (v) => `
        <div class="timeline-item">
          <div class="timeline-dot"></div>
          <div class="timeline-content">
            <div class="timeline-title">V${v.version} ${v.title}</div>
            <p class="hint">${fmtDateTime(v.created_at)} · ${v.change_note || '--'}</p>
            <p class="hint">风险标签：${(v.risk_tags || []).join('、') || '--'}</p>
          </div>
        </div>
      `
      )
      .join('');
  } catch (err) {
    kbVersionsEl.textContent = err.message || err;
  }
};

const saveRule = async () => {
  const payload = {
    title: kbTitleInput?.value?.trim(),
    tags: parseCommaInput(kbTagsInput?.value),
    risk_tags: [],
    scope: [],
    summary: kbDescInput?.value?.trim(),
    content: kbContentInput?.value?.trim(),
    change_note: kbChangeNoteInput?.value?.trim(),
    user_id: state.user?.id,
  };
  if (!payload.title || !payload.content) {
    alert('标题和正文不能为空');
    return;
  }
  const ruleId = kbRuleIdInput?.value;
  const url = ruleId ? `/api/v1/knowledge/rules/${ruleId}` : '/api/v1/knowledge/rules';
  const method = ruleId ? 'PUT' : 'POST';
  try {
    const resp = await fetch(url, {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const data = await resp.json();
    if (!data.success) throw new Error(data.error || '保存失败');
    alert('规则已保存并同步 RAG');
    resetRuleForm();
    state.kbPage = 1;
    loadKnowledgeRules();
  } catch (err) {
    alert(err.message || err);
  }
};

const syncKnowledge = async () => {
  try {
    const resp = await fetch('/api/v1/knowledge/rules/refresh', { method: 'POST' });
    const data = await resp.json();
    if (!data.success) throw new Error(data.error || '同步失败');
    alert(`已同步 ${data.data?.count ?? 0} 条规则到向量索引`);
  } catch (err) {
    alert(err.message || err);
  }
};

// ---------- 事件绑定 ----------
riskStatusInputs.forEach((input) => {
  input.addEventListener('change', () => {
    input.parentElement?.classList.toggle('active', input.checked);
    applyRiskFilters(true);
  });
});

riskSearchInput?.addEventListener('input', () => applyRiskFilters(true));
riskStartInput?.addEventListener('change', () => applyRiskFilters(true));
riskEndInput?.addEventListener('change', () => applyRiskFilters(true));
riskRefreshBtn?.addEventListener('click', loadRiskQueue);
riskMasterCheckbox?.addEventListener('change', (e) => {
  document.querySelectorAll('.risk-row').forEach((cb) => {
    cb.checked = e.target.checked;
  });
});
drawerCloseBtn?.addEventListener('click', () => {
  riskState.detail = null;
  riskState.selectedId = null;
  setDrawerVisibility(false);
});
riskTabButtons.forEach((btn) =>
  btn.addEventListener('click', () => {
    toggleRiskTab(btn.dataset.riskTab);
  }),
);
summaryViewRulesBtn?.addEventListener('click', () => toggleRiskTab('rag'));
ragExplainToggle?.addEventListener('click', () => {
  if (!ragExplainBody) return;
  const hidden = ragExplainBody.classList.toggle('hidden');
  ragExplainToggle.textContent = hidden ? '展开 AI 解释' : '收起 AI 解释';
});
actionApproveBtn?.addEventListener('click', approveRisk);
actionNeedInfoBtn?.addEventListener('click', () => {
  if (!riskState.detail?.id) {
    alert('请先选择票据');
    return;
  }
  toggleNeedInfoPanel(true);
});
needInfoSaveBtn?.addEventListener('click', submitNeedInfo);
needInfoCancelBtn?.addEventListener('click', () => toggleNeedInfoPanel(false));
actionRejectBtn?.addEventListener('click', rejectRisk);

document.getElementById('kb-search-btn')?.addEventListener('click', () => {
  state.kbPage = 1;
  loadKnowledgeRules();
});
document.getElementById('kb-reset-btn')?.addEventListener('click', () => {
  const ids = Array.from(document.querySelectorAll('.kb-row:checked')).map((cb) => cb.dataset.id);
  if (!ids.length) {
    alert('请先勾选要删除的规则');
    return;
  }
  if (!confirm(`确认删除选中的 ${ids.length} 条规则？`)) return;
  fetch('/api/v1/knowledge/rules', {
    method: 'DELETE',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ids }),
  })
    .then((resp) => resp.json())
    .then((data) => {
      if (!data.success) throw new Error(data.error || '删除失败');
      alert(`已删除 ${data.data?.deleted || 0} 条`);
      state.kbPage = 1;
      loadKnowledgeRules();
    })
    .catch((err) => alert(err.message || err));
});
document.getElementById('kb-save')?.addEventListener('click', saveRule);
document.getElementById('kb-reset')?.addEventListener('click', resetRuleForm);
document.getElementById('kb-sync')?.addEventListener('click', syncKnowledge);
kbMasterCheckbox?.addEventListener('change', (e) => {
  document.querySelectorAll('.kb-row').forEach((cb) => {
    cb.checked = e.target.checked;
  });
});
