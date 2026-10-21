(function () {
  'use strict';

  var STORAGE_KEY = 'enterprise-ui-reference-workbench-orders-v1';
  var PREFERENCES_KEY = 'enterprise-ui-reference-workbench-preferences-v1';
  var PAGE_SIZE = 5;

  var state = {
    orders: [],
    filteredOrders: [],
    page: 1,
    activeOrderId: null,
    lastTrigger: null,
    filters: { query: '', status: 'all', priority: 'all' }
  };

  var elements = {};

  function byId(id) {
    return document.getElementById(id);
  }

  function safeParse(value, fallback) {
    try {
      var parsed = JSON.parse(value);
      return parsed;
    } catch (error) {
      return fallback;
    }
  }

  function readStorage(key) {
    try {
      return window.localStorage.getItem(key);
    } catch (error) {
      return null;
    }
  }

  function writeStorage(key, value) {
    try {
      window.localStorage.setItem(key, value);
      return true;
    } catch (error) {
      return false;
    }
  }

  function loadOrders() {
    var saved = safeParse(readStorage(STORAGE_KEY), null);
    if (!Array.isArray(saved) || saved.length === 0) {
      return fixtureOrders.map(function (order) { return Object.assign({}, order); });
    }
    return saved;
  }

  function saveOrders(orders) {
    return writeStorage(STORAGE_KEY, JSON.stringify(orders));
  }

  function loadPreferences() {
    var saved = safeParse(readStorage(PREFERENCES_KEY), {});
    var profile = saved && (saved.profile === 'analytics' || saved.profile === 'enterprise') ? saved.profile : 'enterprise';
    var theme = saved && (saved.theme === 'dark' || saved.theme === 'light') ? saved.theme : 'light';
    var density = saved && (saved.density === 'compact' || saved.density === 'standard') ? saved.density : 'standard';
    document.documentElement.dataset.uiProfile = profile;
    document.documentElement.dataset.theme = theme;
    document.documentElement.dataset.density = density;
    elements.profileSelect.value = profile;
    elements.themeSelect.value = theme;
    elements.densitySelect.value = density;
  }

  function savePreferences() {
    writeStorage(PREFERENCES_KEY, JSON.stringify({
      profile: document.documentElement.dataset.uiProfile || 'enterprise',
      theme: document.documentElement.dataset.theme,
      density: document.documentElement.dataset.density
    }));
  }

  function text(value) {
    return value === null || value === undefined ? '' : String(value);
  }

  function statusClass(status) {
    return {
      '待处理': 'status--pending',
      '处理中': 'status--processing',
      '待验收': 'status--acceptance',
      '已完成': 'status--done'
    }[status] || '';
  }

  function priorityClass(priority) {
    return {
      '紧急': 'priority--urgent',
      '高': 'priority--high',
      '中': 'priority--medium',
      '低': 'priority--low'
    }[priority] || '';
  }

  function createCell(value, className) {
    var cell = document.createElement('td');
    if (className) cell.className = className;
    cell.textContent = text(value);
    return cell;
  }

  function renderTable() {
    var body = elements.orderBody;
    while (body.firstChild) body.removeChild(body.firstChild);

    var totalPages = Math.max(1, Math.ceil(state.filteredOrders.length / PAGE_SIZE));
    state.page = Math.min(state.page, totalPages);
    var start = (state.page - 1) * PAGE_SIZE;
    var visibleOrders = state.filteredOrders.slice(start, start + PAGE_SIZE);

    if (visibleOrders.length === 0) {
      var emptyRow = document.createElement('tr');
      emptyRow.className = 'table-empty';
      var emptyCell = document.createElement('td');
      emptyCell.colSpan = 7;
      var emptyTitle = document.createElement('div');
      emptyTitle.className = 'table-empty__title';
      emptyTitle.textContent = '没有匹配的工单';
      var emptyHint = document.createElement('div');
      emptyHint.className = 'table-empty__hint';
      emptyHint.textContent = '调整关键词或筛选条件后再试。';
      emptyCell.appendChild(emptyTitle);
      emptyCell.appendChild(emptyHint);
      emptyRow.appendChild(emptyCell);
      body.appendChild(emptyRow);
    } else {
      visibleOrders.forEach(function (order) {
        var row = document.createElement('tr');
        row.appendChild(createCell(order.id));

        var assetCell = document.createElement('td');
        var assetWrap = document.createElement('div');
        assetWrap.className = 'record-cell';
        var assetName = document.createElement('span');
        assetName.className = 'record-cell__name';
        assetName.textContent = text(order.asset);
        var assetLocation = document.createElement('span');
        assetLocation.className = 'record-cell__meta';
        assetLocation.textContent = text(order.location);
        assetWrap.appendChild(assetName);
        assetWrap.appendChild(assetLocation);
        assetCell.appendChild(assetWrap);
        row.appendChild(assetCell);

        var priorityCell = document.createElement('td');
        var priority = document.createElement('span');
        priority.className = 'priority ' + priorityClass(order.priority);
        priority.textContent = text(order.priority);
        priorityCell.appendChild(priority);
        row.appendChild(priorityCell);

        var statusCell = document.createElement('td');
        var status = document.createElement('span');
        status.className = 'status ' + statusClass(order.status);
        status.textContent = text(order.status);
        statusCell.appendChild(status);
        row.appendChild(statusCell);

        row.appendChild(createCell(order.owner));
        row.appendChild(createCell(order.updated));

        var actionCell = document.createElement('td');
        var actions = document.createElement('div');
        actions.className = 'record-actions';
        var viewButton = document.createElement('button');
        viewButton.className = 'button button--secondary button--small';
        viewButton.type = 'button';
        viewButton.textContent = '查看 / 编辑';
        viewButton.setAttribute('data-order-id', order.id);
        viewButton.setAttribute('aria-label', '查看并编辑 ' + text(order.id));
        viewButton.addEventListener('click', function () { openOrder(order.id, viewButton); });
        actions.appendChild(viewButton);
        actionCell.appendChild(actions);
        row.appendChild(actionCell);
        body.appendChild(row);
      });
    }

    var resultCount = state.filteredOrders.length;
    elements.resultSummary.textContent = '共 ' + resultCount + ' 条结果';
    elements.pageSummary.textContent = resultCount === 0 ? '当前筛选无结果' : '显示 ' + (start + 1) + '–' + Math.min(start + PAGE_SIZE, resultCount) + ' / ' + resultCount + ' 条';
    elements.pageIndicator.textContent = '第 ' + state.page + ' / ' + totalPages + ' 页';
    elements.previousPage.disabled = state.page <= 1;
    elements.nextPage.disabled = state.page >= totalPages;
  }

  function applyFilters() {
    var query = state.filters.query.trim().toLowerCase();
    state.filteredOrders = state.orders.filter(function (order) {
      var haystack = [order.id, order.asset, order.location, order.owner, order.note].join(' ').toLowerCase();
      var queryMatch = !query || haystack.indexOf(query) !== -1;
      var statusMatch = state.filters.status === 'all' || order.status === state.filters.status;
      var priorityMatch = state.filters.priority === 'all' || order.priority === state.filters.priority;
      return queryMatch && statusMatch && priorityMatch;
    });
    renderTable();
  }

  function getOrder(id) {
    return state.orders.find(function (order) { return order.id === id; }) || null;
  }

  function setDetail(label, value) {
    var item = document.createElement('div');
    item.className = 'detail-grid__item';
    var itemLabel = document.createElement('dt');
    itemLabel.className = 'detail-grid__label';
    itemLabel.textContent = label;
    var itemValue = document.createElement('dd');
    itemValue.className = 'detail-grid__value';
    itemValue.textContent = text(value);
    item.appendChild(itemLabel);
    item.appendChild(itemValue);
    elements.orderDetails.appendChild(item);
  }

  function clearValidation() {
    [elements.ownerInput, elements.noteInput].forEach(function (input) {
      input.closest('.field').classList.remove('field--invalid');
      input.removeAttribute('aria-invalid');
    });
    elements.ownerError.textContent = '';
    elements.noteError.textContent = '';
    elements.saveFeedback.textContent = '';
    delete elements.saveFeedback.dataset.state;
  }

  function updateNoteCount() {
    elements.noteCount.textContent = elements.noteInput.value.length + ' / 240';
  }

  function fillDialog(order) {
    while (elements.orderDetails.firstChild) elements.orderDetails.removeChild(elements.orderDetails.firstChild);
    setDetail('工单编号', order.id);
    setDetail('设备', order.asset);
    setDetail('位置', order.location);
    setDetail('类别', order.category);
    setDetail('优先级', order.priority);
    setDetail('当前状态', order.status);
    setDetail('创建时间', order.opened);
    setDetail('更新时间', order.updated);
    elements.dialogTitle.textContent = order.id + ' · ' + order.asset;
    elements.ownerInput.value = text(order.owner === '未分配' ? '' : order.owner);
    elements.noteInput.value = text(order.note);
    updateNoteCount();
    clearValidation();
  }

  function openOrder(id, trigger) {
    var order = getOrder(id);
    if (!order) return;
    state.activeOrderId = id;
    state.lastTrigger = trigger || document.activeElement;
    fillDialog(order);
    if (typeof elements.dialog.showModal === 'function') {
      elements.dialog.showModal();
    } else {
      elements.dialog.setAttribute('open', '');
    }
    // Start long details at the top; focusing a field below the fold would
    // silently scroll past the opening metadata on narrow screens.
    elements.dialogCloseButton.focus({ preventScroll: true });
    elements.dialog.querySelector('.dialog__body').scrollTop = 0;
  }

  function closeDialog() {
    if (!elements.dialog.open) return;
    if (typeof elements.dialog.close === 'function') {
      elements.dialog.close();
    } else {
      elements.dialog.removeAttribute('open');
      state.activeOrderId = null;
      if (state.lastTrigger && document.contains(state.lastTrigger)) state.lastTrigger.focus();
      state.lastTrigger = null;
    }
  }

  function findOrderTrigger(id) {
    var buttons = elements.orderBody.querySelectorAll('button[data-order-id]');
    for (var index = 0; index < buttons.length; index += 1) {
      if (buttons[index].getAttribute('data-order-id') === id) return buttons[index];
    }
    return null;
  }

  function validateForm() {
    var valid = true;
    var owner = elements.ownerInput.value.trim();
    var note = elements.noteInput.value.trim();
    clearValidation();

    if (owner.length < 2 || owner.length > 24) {
      elements.ownerInput.closest('.field').classList.add('field--invalid');
      elements.ownerInput.setAttribute('aria-invalid', 'true');
      elements.ownerError.textContent = '请输入 2–24 个字符的负责人姓名。';
      valid = false;
    }
    if (note.length > 240) {
      elements.noteInput.closest('.field').classList.add('field--invalid');
      elements.noteInput.setAttribute('aria-invalid', 'true');
      elements.noteError.textContent = '备注不能超过 240 个字符。';
      valid = false;
    }
    if (!valid) {
      elements.saveFeedback.textContent = '请修正标记的字段后再保存。';
      elements.saveFeedback.dataset.state = 'error';
    }
    return valid;
  }

  function handleSave(event) {
    event.preventDefault();
    if (!validateForm()) return;
    var order = getOrder(state.activeOrderId);
    if (!order) return;
    var changedOrder = Object.assign({}, order, {
      owner: elements.ownerInput.value.trim(),
      note: elements.noteInput.value.trim(),
      updated: new Date().toLocaleString('sv-SE', { hour12: false }).slice(0, 16)
    });
    var changedOrders = state.orders.map(function (item) { return item.id === order.id ? changedOrder : item; });
    if (!saveOrders(changedOrders)) {
      elements.saveFeedback.dataset.state = 'error';
      elements.saveFeedback.textContent = '本地保存失败，请允许浏览器存储后重试；当前编辑仍保留。';
      return;
    }
    state.orders = changedOrders;
    applyFilters();
    state.lastTrigger = findOrderTrigger(order.id) || elements.resetFilterButton;
    elements.saveFeedback.textContent = '已保存到当前浏览器。';
    window.setTimeout(closeDialog, 500);
  }

  function handleFilterSubmit(event) {
    event.preventDefault();
    state.filters.query = elements.queryInput.value;
    state.filters.status = elements.statusFilter.value;
    state.filters.priority = elements.priorityFilter.value;
    state.page = 1;
    applyFilters();
  }

  function resetFilters() {
    state.filters = { query: '', status: 'all', priority: 'all' };
    elements.queryInput.value = '';
    elements.statusFilter.value = 'all';
    elements.priorityFilter.value = 'all';
    state.page = 1;
    applyFilters();
    elements.queryInput.focus();
  }

  function toggleNavigation(open, restoreFocus) {
    var shouldOpen = typeof open === 'boolean' ? open : !elements.sidebar.classList.contains('is-open');
    elements.sidebar.classList.toggle('is-open', shouldOpen);
    var isNarrow = window.matchMedia('(max-width: 1023px)').matches;
    elements.sidebar.inert = isNarrow && !shouldOpen;
    elements.sidebar.setAttribute('aria-hidden', String(isNarrow && !shouldOpen));
    elements.mobileMenuButton.setAttribute('aria-expanded', String(shouldOpen));
    elements.mobileMenuButton.setAttribute('aria-label', shouldOpen ? '关闭导航' : '打开导航');
    if (restoreFocus === false) return;
    if (shouldOpen) {
      elements.sidebarCloseButton.focus();
    } else if (isNarrow) {
      elements.mobileMenuButton.focus();
    }
  }

  function bindEvents() {
    elements.filterForm.addEventListener('submit', handleFilterSubmit);
    elements.resetFilterButton.addEventListener('click', resetFilters);
    elements.previousPage.addEventListener('click', function () {
      if (state.page > 1) { state.page -= 1; renderTable(); }
    });
    elements.nextPage.addEventListener('click', function () {
      var totalPages = Math.max(1, Math.ceil(state.filteredOrders.length / PAGE_SIZE));
      if (state.page < totalPages) { state.page += 1; renderTable(); }
    });
    elements.orderForm.addEventListener('submit', handleSave);
    elements.dialogCloseButton.addEventListener('click', closeDialog);
    elements.dialogCancelButton.addEventListener('click', closeDialog);
    elements.noteInput.addEventListener('input', updateNoteCount);
    elements.themeSelect.addEventListener('change', function () {
      document.documentElement.dataset.theme = elements.themeSelect.value;
      savePreferences();
    });
    elements.profileSelect.addEventListener('change', function () {
      document.documentElement.dataset.uiProfile = elements.profileSelect.value;
      savePreferences();
    });
    elements.densitySelect.addEventListener('change', function () {
      document.documentElement.dataset.density = elements.densitySelect.value;
      savePreferences();
    });
    elements.dialog.addEventListener('close', function () {
      state.activeOrderId = null;
      if (state.lastTrigger && document.contains(state.lastTrigger)) state.lastTrigger.focus();
      state.lastTrigger = null;
    });
    elements.dialog.addEventListener('cancel', function (event) {
      event.preventDefault();
      closeDialog();
    });
    elements.mobileMenuButton.addEventListener('click', function () { toggleNavigation(); });
    elements.sidebarCloseButton.addEventListener('click', function () { toggleNavigation(false); });
    window.addEventListener('resize', function () {
      var isNarrow = window.matchMedia('(max-width: 1023px)').matches;
      if (!isNarrow) elements.sidebar.classList.remove('is-open');
      elements.sidebar.inert = isNarrow && !elements.sidebar.classList.contains('is-open');
      elements.sidebar.setAttribute('aria-hidden', String(isNarrow && !elements.sidebar.classList.contains('is-open')));
    });
  }

  function cacheElements() {
    elements.profileSelect = byId('profile-select');
    elements.themeSelect = byId('theme-select');
    elements.densitySelect = byId('density-select');
    elements.sidebar = byId('primary-navigation');
    elements.mobileMenuButton = document.querySelector('.mobile-menu-button');
    elements.sidebarCloseButton = document.querySelector('.sidebar-close-button');
    elements.filterForm = byId('filter-form');
    elements.queryInput = byId('query-input');
    elements.statusFilter = byId('status-filter');
    elements.priorityFilter = byId('priority-filter');
    elements.resetFilterButton = byId('reset-filter-button');
    elements.orderBody = byId('work-order-body');
    elements.resultSummary = byId('result-summary');
    elements.pageSummary = byId('page-summary');
    elements.pageIndicator = byId('page-indicator');
    elements.previousPage = byId('previous-page-button');
    elements.nextPage = byId('next-page-button');
    elements.dialog = byId('order-dialog');
    elements.orderForm = byId('order-form');
    elements.dialogTitle = byId('dialog-title');
    elements.dialogCloseButton = byId('dialog-close-button');
    elements.dialogCancelButton = byId('dialog-cancel-button');
    elements.orderDetails = byId('order-details');
    elements.ownerInput = byId('owner-input');
    elements.noteInput = byId('note-input');
    elements.ownerError = byId('owner-error');
    elements.noteError = byId('note-error');
    elements.noteCount = byId('note-count');
    elements.saveFeedback = byId('save-feedback');
  }

  function init() {
    cacheElements();
    state.orders = loadOrders();
    loadPreferences();
    bindEvents();
    toggleNavigation(false, false);
    applyFilters();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
}());
