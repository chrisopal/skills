/* Simulated cross-page consumer of the shared design adapter. No backend or permission claim. */
(function () {
  'use strict';
  var byId = function (id) { return document.getElementById(id); };
  var current = 'list';
  var configuration = { name: '华东设备例行维护', days: 3, enabled: true };
  var dirty = false;
  var selected = fixtureOrders[0].id;
  var chartRevision = 0;
  function orders() { return window.WorkbenchReference.orders(); }
  function order() { return orders().find(function (item) { return item.id === selected; }) || orders()[0]; }
  function node(tag, value) { var n = document.createElement(tag); n.textContent = value; return n; }
  function pair(container, label, value) { var row = document.createElement('div'); row.append(node('dt', label), node('dd', value)); container.append(row); }
  function renderFacts() {
    var record = order();
    byId('record-subject').textContent = record.id + ' · ' + record.asset;
    byId('record-status').textContent = record.status;
    byId('record-facts').replaceChildren();
    [['位置', record.location], ['负责人', record.owner], ['优先级', record.priority], ['更新时间', record.updated]].forEach(function (value) { pair(byId('record-facts'), value[0], value[1]); });
    byId('record-note').textContent = record.note || '暂无处理记录';
    byId('overview-metrics').replaceChildren();
    ['待处理', '处理中', '待验收', '已完成'].forEach(function (status) { pair(byId('overview-metrics'), status, orders().filter(function (item) { return item.status === status; }).length); });
    byId('next-work').textContent = record.id + ' · ' + record.asset + ' · ' + record.status;
  }
  function drawChart() {
    if (current !== 'analysis') return;
    var canvas = byId('status-chart');
    var style = getComputedStyle(document.documentElement);
    var width = canvas.clientWidth;
    var ratio = window.devicePixelRatio || 1;
    canvas.width = width * ratio; canvas.height = 240 * ratio;
    var ctx = canvas.getContext('2d'); ctx.scale(ratio, ratio);
    var series = style.getPropertyValue('--ui-data-series-1').trim();
    var color = style.getPropertyValue('--ui-text').trim();
    var font = style.getPropertyValue('--ui-font-sans').trim();
    var counts = ['待处理', '处理中', '待验收', '已完成'].map(function (status) { return { label: status, count: orders().filter(function (item) { return item.status === status; }).length }; });
    ctx.clearRect(0, 0, width, 240); ctx.font = '14px ' + font;
    byId('chart-table').replaceChildren();
    counts.forEach(function (item, i) {
      var y = i * 52 + 30;
      ctx.fillStyle = color; ctx.fillText(item.label, 0, y);
      ctx.fillStyle = series; ctx.fillRect(80, y - 14, (width - 130) * item.count / Math.max.apply(null, counts.map(function (x) { return x.count; })), 18);
      ctx.fillStyle = color; ctx.fillText(String(item.count), width - 24, y);
      var row = document.createElement('tr'); row.append(node('td', item.label), node('td', item.count)); byId('chart-table').append(row);
    });
    canvas.dataset.themeRevision = String(++chartRevision);
    canvas.dataset.seriesColor = series; canvas.dataset.textColor = color;
  }
  function restoreConfiguration() {
    byId('configuration-name').value = configuration.name;
    byId('configuration-days').value = configuration.days;
    byId('configuration-enabled').checked = configuration.enabled;
    byId('configuration-name').removeAttribute('aria-invalid');
    byId('configuration-days').removeAttribute('aria-invalid');
    byId('configuration-error').textContent = ''; byId('configuration-feedback').textContent = ''; dirty = false;
  }
  function route() {
    var target = location.hash.slice(1);
    var next = { 'work-orders': 'list', overview: 'overview', record: 'record', configuration: 'configuration', analysis: 'analysis', components: 'components' }[target] || 'list';
    if (current === 'configuration' && dirty && next !== current && !window.confirm('配置尚未保存，确认离开？')) { history.replaceState(null, '', '#configuration'); return; }
    current = next;
    document.querySelectorAll('[data-surface]').forEach(function (surface) { surface.hidden = surface.dataset.surface !== next; });
    document.querySelector('[data-list-only]').hidden = next !== 'list';
    document.querySelectorAll('.nav-item').forEach(function (link) {
      var active = link.hash === '#' + (next === 'list' ? 'work-orders' : next);
      link.classList.toggle('nav-item--active', active);
      if (active) link.setAttribute('aria-current', 'page'); else link.removeAttribute('aria-current');
    });
    document.querySelector('.sidebar-close-button').click();
    renderFacts(); drawChart();
  }
  function fixtureState() {
    var state = byId('fixture-state').value;
    var content = { populated: '维护范围：华东基地 · 9 台设备', empty: '暂无维护记录', loading: '正在读取模拟数据…', error: '模拟读取失败，请重试。', denied: '当前模拟角色无权查看维护配置。', 'signed-out': '模拟会话已退出，请重新登录。' };
    var region = byId('fixture-feedback'); region.replaceChildren(node('p', content[state])); region.dataset.state = state;
    region.setAttribute('aria-busy', String(state === 'loading'));
    if (['error', 'denied', 'signed-out', 'loading'].includes(state)) {
      var recovery = node('button', state === 'error' ? '重试' : state === 'loading' ? '完成模拟加载' : state === 'denied' ? '切回模拟维护角色' : '恢复模拟会话');
      recovery.type = 'button'; recovery.className = 'button button--secondary';
      recovery.addEventListener('click', function () { byId('fixture-state').value = 'populated'; fixtureState(); }); region.append(recovery);
    }
  }
  function init() {
    try { var saved = JSON.parse(localStorage.getItem('enterprise-ui-reference-configuration-v1')); if (saved && typeof saved.name === 'string') configuration = saved; } catch (_) { /* baseline remains available */ }
    restoreConfiguration();
    window.addEventListener('hashchange', route);
    window.addEventListener('ui-design-change', function () { requestAnimationFrame(drawChart); });
    window.addEventListener('resize', drawChart);
    window.addEventListener('workbench-orders-change', renderFacts);
    window.addEventListener('workbench-selection-change', function (event) { selected = event.detail; renderFacts(); });
    byId('record-edit').addEventListener('click', function () { window.WorkbenchReference.open(selected, byId('record-edit')); });
    byId('configuration-form').addEventListener('input', function () { dirty = true; byId('configuration-feedback').textContent = ''; });
    byId('configuration-form').addEventListener('submit', function (event) {
      event.preventDefault();
      var name = byId('configuration-name').value.trim(), days = Number(byId('configuration-days').value);
      var invalidName = !name || name.length > 80;
      var invalidDays = !Number.isInteger(days) || days < 1 || days > 30;
      byId('configuration-name').setAttribute('aria-invalid', String(invalidName));
      byId('configuration-days').setAttribute('aria-invalid', String(invalidDays));
      if (invalidName || invalidDays) { byId('configuration-error').textContent = '请输入方案名称和 1–30 的整数天数。'; return; }
      var next = { name: name, days: days, enabled: byId('configuration-enabled').checked };
      try { localStorage.setItem('enterprise-ui-reference-configuration-v1', JSON.stringify(next)); configuration = next; dirty = false; byId('configuration-error').textContent = ''; byId('configuration-name').removeAttribute('aria-invalid'); byId('configuration-feedback').textContent = '已保存到当前浏览器。'; } catch (_) { byId('configuration-error').textContent = '本地保存失败；草稿保留，请重试。'; }
    });
    byId('configuration-reset').addEventListener('click', restoreConfiguration);
    window.addEventListener('beforeunload', function (event) { if (dirty) { event.preventDefault(); event.returnValue = ''; } });
    byId('fixture-state').addEventListener('change', fixtureState);
    byId('component-action').addEventListener('click', function () { byId('component-feedback').textContent = '主要动作已在本机模拟完成。'; });
    byId('component-secondary').addEventListener('click', function () { byId('component-feedback').textContent = ''; });
    byId('drawer-open').addEventListener('click', function () { byId('fixture-drawer').showModal(); byId('drawer-close').focus(); });
    byId('drawer-close').addEventListener('click', function () { byId('fixture-drawer').close(); });
    byId('fixture-drawer').addEventListener('close', function () { byId('drawer-open').focus(); });
    var tabs = Array.from(document.querySelectorAll('[data-state-tab]'));
    function selectTab(tab) { tabs.forEach(function (item) { var active = item === tab; item.setAttribute('aria-selected', String(active)); item.tabIndex = active ? 0 : -1; byId(item.getAttribute('aria-controls')).hidden = !active; }); }
    tabs.forEach(function (tab, index) { tab.addEventListener('click', function () { selectTab(tab); }); tab.addEventListener('keydown', function (event) { if (event.key === 'ArrowRight' || event.key === 'ArrowLeft') { event.preventDefault(); var next = tabs[(index + (event.key === 'ArrowRight' ? 1 : -1) + tabs.length) % tabs.length]; selectTab(next); next.focus(); } }); });
    fixtureState(); route();
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init); else init();
}());
