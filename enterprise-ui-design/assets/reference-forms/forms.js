(function () {
  'use strict';

  var STORAGE_PREFIX = 'enterprise-ui-reference-forms-v1';
  var EXPECTED_SAMPLE_QUANTITY = 24;
  var state = {
    activeView: 'sample-receiving',
    requestStep: 1,
    items: [
      { name: '316L 检测试剂', spec: '500 ml / 瓶', quantity: 4, unitPrice: 680 },
      { name: '一次性取样袋', spec: '无菌 / 包', quantity: 2, unitPrice: 420 },
      { name: '耐酸手套', spec: 'L 码 / 双', quantity: 10, unitPrice: 120 }
    ],
    drawerTrigger: null,
    drawerSnapshot: null
  };

  var root = document.documentElement;
  var demo = document.getElementById('forms-demo');

  function byId(id) {
    return document.getElementById(id);
  }

  function all(selector, scope) {
    return Array.prototype.slice.call((scope || document).querySelectorAll(selector));
  }

  function key(name) {
    return STORAGE_PREFIX + ':' + name;
  }

  function readStorage(name) {
    try {
      return window.localStorage.getItem(key(name));
    } catch (error) {
      return null;
    }
  }

  function parseStorage(name, fallback) {
    var value = readStorage(name);
    if (!value) return fallback;
    try {
      return JSON.parse(value);
    } catch (error) {
      return fallback;
    }
  }

  function writeStorage(name, payload) {
    try {
      window.localStorage.setItem(key(name), JSON.stringify(payload));
      return true;
    } catch (error) {
      return false;
    }
  }

  function nowLabel() {
    return new Intl.DateTimeFormat('zh-CN', { hour: '2-digit', minute: '2-digit' }).format(new Date());
  }

  function setStatus(id, message, kind) {
    var node = byId(id);
    if (!node) return;
    node.textContent = message || '';
    node.classList.toggle('is-saved', kind === 'saved');
    node.classList.toggle('is-error', kind === 'error');
  }

  function persist(name, payload, statusId) {
    var saved = writeStorage(name, payload);
    if (saved) {
      setStatus(statusId, '已保存至本机 · ' + nowLabel(), 'saved');
    } else {
      setStatus(statusId, '未保存：当前浏览器拒绝本地存储。', 'error');
    }
    return saved;
  }

  function formData(form) {
    var result = {};
    all('[name]', form).forEach(function (field) {
      if (field.type === 'checkbox') {
        result[field.name] = field.checked;
      } else {
        result[field.name] = field.value;
      }
    });
    return result;
  }

  function restoreForm(form, values) {
    if (!values || typeof values !== 'object') return false;
    all('[name]', form).forEach(function (field) {
      if (!(field.name in values)) return;
      if (field.type === 'checkbox') {
        field.checked = Boolean(values[field.name]);
      } else {
        field.value = values[field.name];
      }
    });
    return true;
  }

  function setInvalid(field, errorId, message) {
    var error = byId(errorId);
    if (message) {
      field.setAttribute('aria-invalid', 'true');
      if (error) error.textContent = message;
    } else {
      field.removeAttribute('aria-invalid');
      if (error) error.textContent = '';
    }
  }

  function clearErrors(form) {
    all('[aria-invalid="true"]', form).forEach(function (field) {
      field.removeAttribute('aria-invalid');
    });
    all('.forms-demo__field-error', form).forEach(function (node) {
      node.textContent = '';
    });
  }

  function renderErrorSummary(id, errors) {
    var summary = byId(id);
    if (!summary) return;
    summary.innerHTML = '';
    if (!errors.length) {
      summary.hidden = true;
      return;
    }
    var title = document.createElement('strong');
    title.textContent = '请修正以下问题';
    summary.appendChild(title);
    var list = document.createElement('ul');
    errors.forEach(function (entry) {
      var item = document.createElement('li');
      var link = document.createElement('a');
      link.href = '#' + entry.id;
      link.textContent = entry.label + '：' + entry.message;
      link.addEventListener('click', function (event) {
        event.preventDefault();
        var field = byId(entry.id);
        if (field) field.focus();
      });
      item.appendChild(link);
      list.appendChild(item);
    });
    summary.appendChild(list);
    summary.hidden = false;
  }

  function clearErrorSummary(id) {
    renderErrorSummary(id, []);
  }

  function valueFor(form, name) {
    var field = form.elements[name];
    return field ? field.value.trim() : '';
  }

  function updateCount(input, outputId, max) {
    var output = byId(outputId);
    if (output) output.textContent = input.value.length + ' / ' + max;
  }

  function bindCount(inputId, outputId, max) {
    var input = byId(inputId);
    if (!input) return;
    var update = function () { updateCount(input, outputId, max); };
    input.addEventListener('input', update);
    update();
  }

  function showView(view) {
    var target = byId('forms-demo');
    if (!target) return;
    var valid = ['sample-receiving', 'team-settings', 'purchase-request', 'purchase-items', 'object-drawer', 'task-inbox'].indexOf(view) >= 0;
    state.activeView = valid ? view : 'sample-receiving';
    all('[data-view-panel]').forEach(function (panel) {
      panel.hidden = panel.getAttribute('data-view-panel') !== state.activeView;
    });
    all('.forms-demo__nav-link').forEach(function (link) {
      var active = link.getAttribute('data-view') === state.activeView;
      link.classList.toggle('is-active', active);
      if (active) link.setAttribute('aria-current', 'page');
      else link.removeAttribute('aria-current');
    });
    if (window.location.hash !== '#' + state.activeView) {
      window.history.replaceState(null, '', '#' + state.activeView);
    }
    setMenu(false);
  }

  function bindNavigation() {
    all('.forms-demo__nav-link').forEach(function (link) {
      link.addEventListener('click', function (event) {
        event.preventDefault();
        showView(link.getAttribute('data-view'));
      });
    });
    window.addEventListener('hashchange', function () {
      showView(window.location.hash.slice(1));
    });
    byId('forms-menu-open').addEventListener('click', function () { setMenu(!byId('forms-navigation').classList.contains('is-open')); });
    byId('forms-menu-close').addEventListener('click', function () { setMenu(false); byId('forms-menu-open').focus(); });
    document.addEventListener('keydown', function (event) {
      if (event.key === 'Escape' && byId('forms-navigation').classList.contains('is-open')) { setMenu(false); byId('forms-menu-open').focus(); }
    });
    var mobile = window.matchMedia('(max-width: 820px)');
    mobile.addEventListener('change', function () { setMenu(false); });
  }

  function setMenu(open) {
    var sidebar = byId('forms-navigation');
    var mobile = window.matchMedia('(max-width: 820px)').matches;
    sidebar.classList.toggle('is-open', open && mobile);
    sidebar.inert = mobile && !open;
    byId('forms-menu-open').setAttribute('aria-expanded', String(open && mobile));
    if (open && mobile) byId('forms-menu-close').focus();
    if (!open && mobile && sidebar.contains(document.activeElement)) byId('forms-menu-open').focus();
  }

  function bindDisplaySettings() {
    var settings = [
      ['forms-profile', 'data-ui-profile'],
      ['forms-brand', 'data-ui-brand'],
      ['forms-theme', 'data-theme'],
      ['forms-density', 'data-density']
    ];
    settings.forEach(function (entry) {
      var select = byId(entry[0]);
      if (!select) return;
      select.addEventListener('change', function () {
        root.setAttribute(entry[1], select.value);
      });
    });
    root.setAttribute('data-ui-profile', byId('forms-profile').value);
    root.setAttribute('data-ui-brand', byId('forms-brand').value);
  }

  function validateSample(form) {
    clearErrors(form);
    var errors = [];
    var first = null;
    var receiver = byId('sample-receiver');
    var location = byId('sample-location');
    var quantity = byId('sample-quantity');
    var note = byId('sample-note');
    var quantityValue = Number(quantity.value);
    function fail(field, errorId, message, label) {
      if (!first) first = field;
      setInvalid(field, errorId, message);
      errors.push({ id: field.id, label: label, message: message });
    }
    if (!valueFor(form, 'receiver')) fail(receiver, 'sample-receiver-error', '请输入签收人。', '签收人');
    if (!valueFor(form, 'location')) fail(location, 'sample-location-error', '请选择入库位置。', '入库位置');
    if (quantity.value.trim() === '' || !Number.isFinite(quantityValue) || quantityValue < 0 || !Number.isInteger(quantityValue)) fail(quantity, 'sample-quantity-error', '请输入不小于 0 的整数。', '实收数量');
    if (quantity.value.trim() !== '' && quantityValue !== EXPECTED_SAMPLE_QUANTITY && !valueFor(form, 'note')) fail(note, 'sample-note-error', '本次实收数量与应收数量不同，请填写差异说明。', '数量差异说明');
    renderErrorSummary('sample-error-summary', errors);
    if (first) {
      first.focus();
      return false;
    }
    return true;
  }

  function bindSampleForm() {
    var form = byId('sample-form');
    var saved = parseStorage('sample-receiving', null);
    if (restoreForm(form, saved)) setStatus('sample-save-state', '已恢复本机草稿 · ' + (saved.savedAt || ''));
    bindCount('sample-note', 'sample-note-count', 240);
    form.addEventListener('input', function (event) {
      if (event.target.matches('[aria-invalid="true"]')) setInvalid(event.target, event.target.getAttribute('aria-describedby').split(' ').pop(), '');
      persist('sample-receiving', Object.assign(formData(form), { savedAt: nowLabel() }), 'sample-save-state');
    });
    form.addEventListener('change', function () {
      persist('sample-receiving', Object.assign(formData(form), { savedAt: nowLabel() }), 'sample-save-state');
    });
    form.addEventListener('submit', function (event) {
      event.preventDefault();
      if (validateSample(form)) persist('sample-receiving', Object.assign(formData(form), { savedAt: nowLabel(), completedLocally: true }), 'sample-save-state');
    });
    byId('sample-print').addEventListener('click', function () {
      setStatus('sample-save-state', '已打开浏览器打印预览。', 'saved');
      window.print();
    });
    all('[data-demo-action="attachment"]', demo).forEach(function (button) {
      button.addEventListener('click', function () {
        setStatus('sample-save-state', '本地附件示例：文件内容未连接后端。');
      });
    });
  }

  function validateTeam(form) {
    clearErrors(form);
    var errors = [];
    var name = byId('team-name');
    if (!valueFor(form, 'teamName')) {
      var message = '请输入团队名称。';
      setInvalid(name, 'team-name-error', message);
      errors.push({ id: name.id, label: '团队名称', message: message });
      renderErrorSummary('team-error-summary', errors);
      name.focus();
      return false;
    }
    clearErrorSummary('team-error-summary');
    return true;
  }

  function bindTeamForm() {
    var form = byId('team-form');
    var saved = parseStorage('team-settings', null);
    if (restoreForm(form, saved)) setStatus('team-save-state', '已恢复本机草稿 · ' + (saved.savedAt || ''));
    bindCount('team-description', 'team-description-count', 180);
    form.addEventListener('input', function (event) {
      if (event.target.matches('[aria-invalid="true"]')) setInvalid(event.target, event.target.getAttribute('aria-describedby').split(' ').pop(), '');
      setStatus('team-save-state', '有未保存的更改。', 'unsaved');
    });
    form.addEventListener('change', function () {
      setStatus('team-save-state', '有未保存的更改。', 'unsaved');
    });
    form.addEventListener('submit', function (event) {
      event.preventDefault();
      if (validateTeam(form)) persist('team-settings', Object.assign(formData(form), { savedAt: nowLabel() }), 'team-save-state');
    });
    byId('team-restore').addEventListener('click', function () {
      var latest = parseStorage('team-settings', null);
      if (restoreForm(form, latest)) {
        clearErrors(form);
        updateCount(byId('team-description'), 'team-description-count', 180);
        setStatus('team-save-state', '已恢复上次本机保存。', 'saved');
      } else {
        setStatus('team-save-state', '暂无已保存的本机草稿。');
      }
    });
  }

  function requestStepFields(step) {
    var panel = document.querySelector('[data-wizard-step="' + step + '"]');
    return panel ? all('[required]', panel) : [];
  }

  function validateRequestStep(step) {
    var fields = requestStepFields(step);
    var errors = [];
    var first = null;
    fields.forEach(function (field) {
      var empty = !String(field.value || '').trim();
      var numericInvalid = field.type === 'number' && (!Number.isFinite(Number(field.value)) || Number(field.value) < 0);
      var message = empty ? '请填写此字段。' : (numericInvalid ? '请输入不小于 0 的数字。' : '');
      var errorId = field.getAttribute('aria-describedby');
      errorId = errorId ? errorId.split(' ').filter(function (id) { return id.indexOf('-error') >= 0; })[0] : null;
      if (message) {
        if (!first) first = field;
        setInvalid(field, errorId, message);
        errors.push({ id: field.id, label: field.labels && field.labels[0] ? field.labels[0].textContent.replace('*', '').trim() : field.name, message: message });
      } else {
        setInvalid(field, errorId, '');
      }
    });
    renderErrorSummary('request-error-summary', errors);
    if (first) {
      first.focus();
      return false;
    }
    return true;
  }

  function updateRequestSummary(form) {
    var summary = byId('request-review-summary');
    var rows = [
      ['申请主题', valueFor(form, 'requestTitle')],
      ['申请类型', valueFor(form, 'requestType')],
      ['使用部门', valueFor(form, 'department')],
      ['期望到货日', valueFor(form, 'neededDate')],
      ['预算金额', '¥ ' + Number(valueFor(form, 'budget') || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2 })],
      ['成本中心', valueFor(form, 'costCenter')],
      ['采购明细', valueFor(form, 'items')]
    ];
    summary.innerHTML = '';
    rows.forEach(function (row) {
      var wrapper = document.createElement('div');
      var label = document.createElement('dt');
      var value = document.createElement('dd');
      label.textContent = row[0];
      value.textContent = row[1] || '未填写';
      wrapper.appendChild(label);
      wrapper.appendChild(value);
      summary.appendChild(wrapper);
    });
  }

  function renderRequestStep(step) {
    var form = byId('purchase-request-form');
    state.requestStep = step;
    all('[data-wizard-step]').forEach(function (panel) {
      panel.hidden = Number(panel.getAttribute('data-wizard-step')) !== step;
    });
    all('[data-step-marker]').forEach(function (marker) {
      var markerStep = Number(marker.getAttribute('data-step-marker'));
      marker.classList.toggle('is-current', markerStep === step);
      marker.classList.toggle('is-complete', markerStep < step);
    });
    if (step === 3) updateRequestSummary(form);
  }

  function bindRequestForm() {
    var form = byId('purchase-request-form');
    var saved = parseStorage('purchase-request', null);
    if (restoreForm(form, saved)) setStatus('request-save-state', '已恢复本机草稿 · ' + (saved.savedAt || ''));
    bindCount('request-reason', 'request-reason-count', 300);
    form.addEventListener('input', function () {
      persist('purchase-request', Object.assign(formData(form), { savedAt: nowLabel() }), 'request-save-state');
    });
    form.addEventListener('change', function () {
      persist('purchase-request', Object.assign(formData(form), { savedAt: nowLabel() }), 'request-save-state');
    });
    all('[data-wizard-next]').forEach(function (button) {
      button.addEventListener('click', function () {
        var next = Number(button.getAttribute('data-wizard-next'));
        if (validateRequestStep(next - 1)) renderRequestStep(next);
      });
    });
    all('[data-wizard-back]').forEach(function (button) {
      button.addEventListener('click', function () {
        renderRequestStep(Number(button.getAttribute('data-wizard-back')));
      });
    });
    form.addEventListener('submit', function (event) {
      event.preventDefault();
      if (validateRequestStep(1) && validateRequestStep(2)) {
        persist('purchase-request', Object.assign(formData(form), { savedAt: nowLabel(), reviewConfirmedLocally: true }), 'request-save-state');
      }
    });
    renderRequestStep(1);
  }

  function itemAmount(item) {
    return (Number(item.quantity) || 0) * (Number(item.unitPrice) || 0);
  }

  function formatMoney(value) {
    return '¥ ' + Number(value || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }

  function createItemField(label, value, type, itemIndex, prop) {
    var wrapper = document.createElement('div');
    wrapper.className = 'forms-demo__field';
    var input = document.createElement('input');
    input.className = 'forms-demo__control';
    input.type = type || 'text';
    input.value = value;
    input.id = 'item-' + itemIndex + '-' + prop;
    input.setAttribute('aria-label', label + '，第 ' + (itemIndex + 1) + ' 行');
    input.dataset.itemIndex = String(itemIndex);
    input.dataset.itemProp = prop;
    if (type === 'number') {
      input.min = '0';
      input.step = prop === 'quantity' ? '1' : '0.01';
    }
    wrapper.appendChild(input);
    var error = document.createElement('p');
    error.className = 'forms-demo__field-error';
    error.dataset.itemError = prop;
    error.setAttribute('role', 'alert');
    wrapper.appendChild(error);
    return wrapper;
  }

  function renderItems() {
    var body = byId('items-body');
    body.innerHTML = '';
    state.items.forEach(function (item, index) {
      var row = document.createElement('tr');
      row.dataset.itemRow = String(index);
      var nameCell = document.createElement('td');
      nameCell.dataset.label = '物料名称';
      nameCell.appendChild(createItemField('物料名称', item.name, 'text', index, 'name'));
      row.appendChild(nameCell);
      var specCell = document.createElement('td');
      specCell.dataset.label = '规格';
      specCell.appendChild(createItemField('规格', item.spec, 'text', index, 'spec'));
      row.appendChild(specCell);
      var quantityCell = document.createElement('td');
      quantityCell.dataset.label = '数量';
      quantityCell.appendChild(createItemField('数量', item.quantity, 'number', index, 'quantity'));
      row.appendChild(quantityCell);
      var unitPriceCell = document.createElement('td');
      unitPriceCell.dataset.label = '含税单价';
      unitPriceCell.appendChild(createItemField('含税单价', item.unitPrice, 'number', index, 'unitPrice'));
      row.appendChild(unitPriceCell);
      var amountCell = document.createElement('td');
      amountCell.className = 'forms-demo__item-amount';
      amountCell.dataset.label = '金额';
      amountCell.textContent = formatMoney(itemAmount(item));
      row.appendChild(amountCell);
      var actionCell = document.createElement('td');
      actionCell.dataset.label = '操作';
      var remove = document.createElement('button');
      remove.className = 'forms-demo__button forms-demo__button--secondary forms-demo__button--small';
      remove.type = 'button';
      remove.textContent = '删除';
      remove.setAttribute('aria-label', '删除第 ' + (index + 1) + ' 行明细');
      remove.dataset.removeItem = String(index);
      actionCell.appendChild(remove);
      row.appendChild(actionCell);
      body.appendChild(row);
    });
    byId('items-view-count').textContent = state.items.length + ' 行明细';
    byId('items-count').textContent = state.items.length + ' 行';
    recalculateItems(false);
  }

  function readRenderedItems() {
    all('[data-item-prop]', byId('items-body')).forEach(function (field) {
      var index = Number(field.dataset.itemIndex);
      var prop = field.dataset.itemProp;
      state.items[index][prop] = prop === 'quantity' || prop === 'unitPrice' ? Number(field.value) : field.value;
    });
  }

  function clearItemErrors() {
    all('[data-item-prop]', byId('items-body')).forEach(function (field) {
      field.removeAttribute('aria-invalid');
    });
    all('[data-item-error]', byId('items-body')).forEach(function (node) {
      node.textContent = '';
    });
  }

  function validateItems() {
    readRenderedItems();
    clearItemErrors();
    var errors = [];
    var first = null;
    state.items.forEach(function (item, index) {
      var row = document.querySelector('[data-item-row="' + index + '"]');
      function fail(prop, message) {
        var field = row.querySelector('[data-item-prop="' + prop + '"]');
        var error = row.querySelector('[data-item-error="' + prop + '"]');
        if (field) field.setAttribute('aria-invalid', 'true');
        if (error) error.textContent = message;
        if (!first) first = field;
        errors.push({ id: field.id, label: (field.getAttribute('aria-label') || prop), message: message });
      }
      if (!String(item.name || '').trim()) fail('name', '请输入物料名称。');
      if (!String(item.spec || '').trim()) fail('spec', '请输入规格。');
      var quantityField = row.querySelector('[data-item-prop="quantity"]');
      var unitPriceField = row.querySelector('[data-item-prop="unitPrice"]');
      if (quantityField.value.trim() === '' || !Number.isInteger(item.quantity) || item.quantity <= 0) fail('quantity', '数量需为大于 0 的整数。');
      if (unitPriceField.value.trim() === '' || !Number.isFinite(item.unitPrice) || item.unitPrice < 0) fail('unitPrice', '单价需为不小于 0 的数字。');
    });
    renderErrorSummary('items-error-summary', errors);
    if (first) {
      first.focus();
      return false;
    }
    return true;
  }

  function recalculateItems(showStatus) {
    readRenderedItems();
    var total = state.items.reduce(function (sum, item) { return sum + itemAmount(item); }, 0);
    byId('items-total').textContent = formatMoney(total);
    all('[data-item-row]', byId('items-body')).forEach(function (row, index) {
      var amount = row.querySelector('.forms-demo__item-amount');
      if (amount) amount.textContent = formatMoney(itemAmount(state.items[index]));
    });
    if (showStatus) setStatus('items-save-state', '已重新计算当前明细。', 'saved');
  }

  function bindItems() {
    var saved = parseStorage('purchase-items', null);
    if (Array.isArray(saved)) state.items = saved;
    renderItems();
    byId('items-body').addEventListener('input', function (event) {
      if (!event.target.matches('[data-item-prop]')) return;
      readRenderedItems();
      recalculateItems(false);
      persist('purchase-items', state.items, 'items-save-state');
    });
    byId('items-body').addEventListener('click', function (event) {
      var remove = event.target.closest('[data-remove-item]');
      if (!remove) return;
      var index = Number(remove.dataset.removeItem);
      state.items.splice(index, 1);
      renderItems();
      persist('purchase-items', state.items, 'items-save-state');
    });
    byId('item-add').addEventListener('click', function () {
      readRenderedItems();
      state.items.push({ name: '', spec: '', quantity: 1, unitPrice: 0 });
      renderItems();
      var newField = document.querySelector('[data-item-row="' + (state.items.length - 1) + '"] [data-item-prop="name"]');
      if (newField) newField.focus();
      setStatus('items-save-state', '已添加一行，请填写该行的物料信息。');
    });
    byId('items-recalculate').addEventListener('click', function () {
      if (validateItems()) recalculateItems(true);
    });
    byId('items-save').addEventListener('click', function () {
      if (validateItems()) persist('purchase-items', state.items, 'items-save-state');
    });
    byId('items-body').addEventListener('change', function () {
      readRenderedItems();
      persist('purchase-items', state.items, 'items-save-state');
    });
  }

  function bindDrawer() {
    var dialog = byId('object-drawer-dialog');
    var form = byId('drawer-form');
    var pageState = byId('drawer-page-state');
    var saved = parseStorage('object-drawer', null);
    if (saved) restoreForm(form, saved);
    function updateObjectSummary() {
      byId('drawer-current-location').textContent = byId('drawer-location').value;
      byId('drawer-current-enabled').textContent = byId('drawer-enabled').checked ? '启用' : '停用';
    }
    updateObjectSummary();
    byId('drawer-open').addEventListener('click', function () {
      state.drawerTrigger = this;
      var latest = parseStorage('object-drawer', null);
      if (latest) restoreForm(form, latest);
      state.drawerSnapshot = formData(form);
      clearErrors(form);
      clearErrorSummary('drawer-error-summary');
      setStatus('drawer-save-state', '');
      if (typeof dialog.showModal === 'function') dialog.showModal();
      else dialog.setAttribute('open', '');
      window.setTimeout(function () { byId('drawer-location').focus(); }, 0);
    });
    function drawerIsDirty() {
      return state.drawerSnapshot && JSON.stringify(state.drawerSnapshot) !== JSON.stringify(formData(form));
    }
    function closeDrawer(forceDiscard) {
      if (!forceDiscard && drawerIsDirty() && !window.confirm('放弃尚未保存的规则更改？')) return;
      if (drawerIsDirty() && state.drawerSnapshot) restoreForm(form, state.drawerSnapshot);
      if (dialog.open) dialog.close();
      else dialog.removeAttribute('open');
      if (state.drawerTrigger) state.drawerTrigger.focus();
    }
    byId('drawer-close').addEventListener('click', function () { closeDrawer(false); });
    byId('drawer-cancel').addEventListener('click', function () { closeDrawer(true); });
    dialog.addEventListener('cancel', function (event) {
      if (drawerIsDirty()) {
        if (!window.confirm('放弃尚未保存的规则更改？')) {
          event.preventDefault();
          return;
        }
        restoreForm(form, state.drawerSnapshot);
      }
      window.setTimeout(function () {
        if (state.drawerTrigger) state.drawerTrigger.focus();
      }, 0);
    });
    dialog.addEventListener('close', function () {
      if (state.drawerTrigger) state.drawerTrigger.focus();
    });
    form.addEventListener('submit', function (event) {
      event.preventDefault();
      clearErrors(form);
      var location = byId('drawer-location');
      var condition = byId('drawer-condition');
      var invalid = null;
      var errors = [];
      if (!valueFor(form, 'drawerLocation')) {
        var locationMessage = '请选择默认入库位置。';
        setInvalid(location, 'drawer-location-error', locationMessage);
        errors.push({ id: location.id, label: '默认入库位置', message: locationMessage });
        invalid = location;
      }
      if (!valueFor(form, 'drawerCondition')) {
        var conditionMessage = '请选择匹配条件。';
        setInvalid(condition, 'drawer-condition-error', conditionMessage);
        errors.push({ id: condition.id, label: '匹配条件', message: conditionMessage });
        if (!invalid) invalid = condition;
      }
      renderErrorSummary('drawer-error-summary', errors);
      if (invalid) {
        invalid.focus();
        return;
      }
      if (persist('object-drawer', Object.assign(formData(form), { savedAt: nowLabel() }), 'drawer-save-state')) {
        state.drawerSnapshot = formData(form);
        updateObjectSummary();
        setStatus(pageState.id, '规则已保存至本机 · ' + nowLabel(), 'saved');
        window.setTimeout(function () { closeDrawer(true); }, 120);
      }
    });
  }

  function bindInbox() {
    var records = [
      {id:'SP-2026-0048',title:'不锈钢管材 · 316L',status:'待核对差异',blocked:true,owner:'林晓梅 · 质量部',next:'核对数量后签收',decision:'实收较应收少 1 件，需要核对差异原因。',evidence:'送样单应收 24 件，10:03 盘点实收 23 件。外箱破损的 1 件已单独封存待复核。',source:'来源：送样单 PO-2026-118 · 盘点记录 10:03 · 示例初始快照',history:[['09:42','周凯创建送样记录'],['10:03','林晓梅记录数量差异']]},
      {id:'SP-2026-0051',title:'密封垫片 · EPDM',status:'资料待补',blocked:true,owner:'周凯 · 质量部',next:'补齐批次证明',decision:'缺少批次证明，暂不能完成资料核对。',evidence:'随样清单已收到；批次证明尚未提供。缺失不代表检验不合格。',source:'来源：随样资料核对记录 · 10:15 · 本地示例',history:[['10:10','周凯领取资料核对任务'],['10:15','登记缺少批次证明']]},
      {id:'SP-2026-0055',title:'铝合金板材 · 6061',status:'待安排',blocked:false,owner:'赵文博 · 质量部',next:'确认保管位置',decision:'基础资料齐全，等待安排保管位置。',evidence:'样品 6 件，外观完好。保管位置未填写，当前没有逾期证据。',source:'来源：到样登记 · 10:26 · 本地示例',history:[['10:26','赵文博完成到样登记']]}
    ];
    var selected = records[0].id;
    function render() {
      var query = byId('inbox-search').value.trim().toLowerCase();
      var shown = records.filter(function (record) { return (byId('inbox-filter').value !== 'blocked' || record.blocked) && (record.id + record.title).toLowerCase().includes(query); });
      if (!shown.some(function (record) { return record.id === selected; })) selected = shown.length ? shown[0].id : null;
      var list = byId('inbox-records'); list.replaceChildren();
      shown.forEach(function (record) {
        var button = document.createElement('button'); button.type = 'button'; button.className = 'forms-demo__inbox-record'; button.setAttribute('aria-pressed', String(record.id === selected));
        var title = document.createElement('strong'); title.textContent = record.title;
        var status = document.createElement('small'); status.textContent = record.status + ' · ' + record.next;
        var id = document.createElement('span'); id.textContent = record.id;
        button.append(title, status, id); button.addEventListener('click', function () { selected = record.id; render(); byId('inbox-records').querySelector('[aria-pressed="true"]').focus(); }); list.append(button);
      });
      byId('inbox-count').textContent = shown.length + ' 项'; byId('inbox-empty').hidden = shown.length > 0;
      var detail = document.querySelector('.forms-demo__inbox-detail'); detail.hidden = !selected;
      if (!selected) return;
      var record = records.find(function (item) { return item.id === selected; });
      ['id','status','owner','next','decision','evidence','source'].forEach(function (field) { byId('inbox-' + field).textContent = record[field]; });
      byId('inbox-object-title').textContent = record.title;
      var history = byId('inbox-history'); history.replaceChildren();
      record.history.forEach(function (event) { var li=document.createElement('li'),time=document.createElement('span'),text=document.createElement('span');time.textContent=event[0];text.textContent=event[1];li.append(time,text);history.append(li); });
      document.querySelector('.forms-demo__inbox-history').open = false;
      byId('inbox-handoff').hidden = record.id !== records[0].id;
    }
    byId('inbox-search').addEventListener('input', render); byId('inbox-filter').addEventListener('change', render); render();
  }

  function init() {
    bindNavigation();
    bindDisplaySettings();
    bindSampleForm();
    bindTeamForm();
    bindRequestForm();
    bindItems();
    bindDrawer();
    bindInbox();
    showView(window.location.hash.slice(1) || 'sample-receiving');
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
}());
