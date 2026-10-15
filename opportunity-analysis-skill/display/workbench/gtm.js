(function () {
  'use strict';
  const $ = (id) => document.getElementById(id);
  const state = { campaigns: [], detail: null, id: '', selected: '', tab: 'companies', region: '', type: '', keyword: '', zoom: 1, busy: false, loadVersion: 0, geography: null, geoProvince: '', geoCity: '' };
  const labels = { candidate: '候选', contacted: '已触达', responded: '已回应', meeting: '已约谈', qualified: '有效线索', no_fit: '不适配', opportunity: '已关联商机', planned: '计划中', company: '企业', exhibition: '展会', forum: '论坛', channel: '渠道', past: '已结束', ongoing: '进行中', upcoming: '即将开始', unknown: '日期待核实' };
  const stageLabels = { lead_identified: '线索', customer_contacted: '初次接触', needs_discovery: '需求澄清', opportunity_confirmed: '商机确认', solution_cocreation: '方案共创', budget_project_confirmed: '预算立项', proposal_bidding: '方案报价', commercial_negotiation: '商务谈判', contract_signing: '合同签订', won: '赢单' };
  const verificationLabels = { current: '当前有效', stale: '待复核', missing: '证据缺失', unknown: '待核验' };
  const tabs = [['companies', '企业'], ['events', '展会 / 论坛'], ['channels', '渠道'], ['messages', '话术草稿'], ['touches', '跟进记录'], ['analysis', '分析']];
  const str = (value, fallback = '—') => value == null || value === '' ? fallback : String(value);
  const list = (value) => Array.isArray(value) ? value : [];
  const today = () => { const d = new Date(); return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0'); };
  const id = (prefix) => prefix + '-' + (globalThis.crypto && crypto.randomUUID ? crypto.randomUUID() : Date.now().toString(36) + Math.random().toString(36).slice(2));
  function node(tag, cls, text) { const n = document.createElement(tag); if (cls) n.className = cls; if (text !== undefined) n.textContent = text; return n; }
  function clear(n) { n.replaceChildren(); return n; }
  function button(text, action, primary = false) { const b = node('button', 'gtm-btn gtm-small' + (primary ? ' gtm-primary' : ''), text); b.type = 'button'; b.addEventListener('click', action); return b; }
  function safeLink(url, text) { try { const u = new URL(url); if (!['http:', 'https:'].includes(u.protocol) || u.username || u.password) return node('span', 'gtm-muted', '无有效公开链接'); const a = node('a', '', text || u.hostname); a.href = u.href; a.target = '_blank'; a.rel = 'noopener noreferrer'; return a; } catch (_) { return node('span', 'gtm-muted', '无有效公开链接'); } }
  function navLink(url, text) { const a = node('a', 'gtm-btn gtm-small', text); a.href = url; return a; }
  function notice(text, kind = '') { const n = $('notice'); n.textContent = text; n.className = 'gtm-notice' + (kind ? ' is-' + kind : ''); n.hidden = !text; }
  function eventStatus(event, asOf) { if (event.kind === 'channel') return 'ongoing'; if (!event.starts_on || !event.ends_on) return 'unknown'; return event.ends_on < asOf ? 'past' : event.starts_on > asOf ? 'upcoming' : 'ongoing'; }
  function hasLocation(item) { const l = item.location; return !!l && typeof l.lon === 'number' && Number.isFinite(l.lon) && typeof l.lat === 'number' && Number.isFinite(l.lat) && l.lon >= -180 && l.lon <= 180 && l.lat >= -90 && l.lat <= 90; }
  function objects(detail) { return list(detail && detail.targets).map((x) => ({ ...x, object_type: 'company', key: 'company:' + x.id })).concat(list(detail && detail.events).map((x) => ({ ...x, object_type: x.kind, key: x.kind + ':' + x.id }))); }
  function matches(item, filters) { return (!filters.region || item.region === filters.region) && (!filters.type || item.object_type === filters.type) && (!filters.keyword || [item.name, item.region, item.city, item.industry, item.fit_reason, item.audience, item.organizer].filter(Boolean).join(' ').toLocaleLowerCase().includes(filters.keyword.toLocaleLowerCase())); }
  function groupPoints(items) {
    const groups = new Map();
    items.filter(hasLocation).forEach((item) => {
      const key = item.location.lon + ',' + item.location.lat;
      if (!groups.has(key)) groups.set(key, { key, city: item.city, location: item.location, items: [] });
      groups.get(key).items.push(item);
    });
    return Array.from(groups.values()).sort((a, b) => b.location.lat - a.location.lat);
  }
  function fitLabel(target) { return target.fit_score == null ? '适配待评估' : '适配 ' + Number(target.fit_score).toFixed(1) + ' / 100'; }
  function qualifiedTouches(detail, targetId) { return list(detail.touches).filter((t) => t.target_id === targetId && t.outcome === 'qualified' && t.evidence && t.occurred_on <= detail.as_of && t.occurred_on <= today()); }
  function money(values, fallback = '未知') { const pairs = Object.entries(values || {}); return pairs.length ? pairs.map(([c, v]) => c + ' ' + Number(v).toLocaleString('zh-CN', { maximumFractionDigits: 2 })).join(' · ') : fallback; }
  // Project the current snapshot without changing campaign or sales facts. Parity-tested
  // against gtm._analytics; ownership is always the target, never an OR with event location.
  function scopeSnapshot(detail, items) {
    const targets = items.filter((x) => x.object_type === 'company'), events = items.filter((x) => x.object_type !== 'company');
    const ids = new Set(targets.map((x) => x.id));
    const touches = list(detail.touches).filter((t) => ids.has(t.target_id));
    const through = [detail.actual_through || detail.as_of, detail.as_of, today()].filter(Boolean).sort()[0];
    const actual = touches.filter((t) => t.outcome !== 'planned' && t.occurred_on <= through);
    const pending = touches.filter((t) => !actual.includes(t));
    const links = list(detail.links).filter((l) => ids.has(l.target_id) && l.linked_on <= detail.as_of);
    const outcomes = ['contacted', 'responded', 'meeting', 'qualified'];
    const unique = (rows, key) => new Set(rows.map((r) => r[key])).size;
    const reached = (rows, outcome) => unique(rows.filter((t) => outcomes.indexOf(t.outcome) >= outcomes.indexOf(outcome)), 'target_id');
    const sum = (rows, currencyKey, amountKey) => { const values = {}; rows.forEach((r) => { const c = r[currencyKey]; values[c] = Math.round(((values[c] || 0) + r[amountKey]) * 100) / 100; }); return values; };
    const costs = (rows) => sum(rows.filter((r) => r.actual_cost != null), 'currency', 'actual_cost');
    const missing = (rows) => rows.filter((r) => r.actual_cost == null).length;
    const won = links.filter((l) => l.opportunity && l.opportunity.status === 'won' && list(l.opportunity.signed_amounts).length);
    const funnel = { candidates: targets.length };
    outcomes.forEach((k) => { funnel[k] = reached(actual, k); });
    funnel.opportunities = unique(links, 'target_id'); funnel.won = unique(won, 'target_id');
    const regions = [...new Set(targets.map((t) => t.region))].map((name) => {
      const group = new Set(targets.filter((t) => t.region === name).map((t) => t.id)), rows = actual.filter((t) => group.has(t.target_id));
      return { name, candidates: group.size, contacted: reached(rows, 'contacted'), qualified: reached(rows, 'qualified'), opportunities: unique(links.filter((l) => group.has(l.target_id)), 'target_id'), won: unique(won.filter((l) => group.has(l.target_id)), 'target_id') };
    });
    const channels = [...new Set(actual.map((t) => t.channel))].map((name) => {
      const rows = actual.filter((t) => t.channel === name);
      return { name, touches: rows.length, contacted: reached(rows, 'contacted'), responded: reached(rows, 'responded'), qualified: reached(rows, 'qualified'), costs: costs(rows), missing_cost_count: missing(rows) };
    });
    const eventMetrics = events.map((e) => {
      const rows = actual.filter((t) => t.event_id === e.id);
      return { id: e.id, name: e.name, targets: unique(rows, 'target_id'), qualified: reached(rows, 'qualified'), opportunities: unique(links.filter((l) => l.origin_event_id === e.id), 'target_id'), costs: costs(rows), missing_cost_count: missing(rows) };
    });
    const effectiveLinks = [...new Map(links.map((l) => [l.opportunity_id, l])).values()];
    const signed = effectiveLinks.flatMap((l) => list(l.opportunity && l.opportunity.signed_amounts));
    return { targets, events, touches, actual, pending, links, analytics: { funnel, regions, channels, events: eventMetrics, costs: costs(actual), missing_cost_count: missing(actual), signed_amounts: sum(signed, 'currency', 'amount'), unmapped_targets: targets.filter((t) => !t.location).length } };
  }
  window.GTMLogic = Object.freeze({ eventStatus, hasLocation, objects, matches, fitLabel, qualifiedTouches, money, groupPoints, scopeSnapshot });
  async function api(path, options) {
    const response = await fetch(path, options); let result;
    try { result = await response.json(); } catch (_) { throw new Error('服务返回结果无法读取，请重试。'); }
    if (!response.ok || result.ok === false) { const e = new Error(typeof result.error === 'string' ? result.error : result.error && result.error.message || '请求失败'); e.status = response.status; throw e; }
    return result;
  }
  function detailSources(parent, ids) {
    const refs = list(ids); const wrap = node('details', 'gtm-disclosure'); wrap.append(node('summary', '', '来源依据（' + refs.length + '）'));
    if (!refs.length) wrap.append(node('p', 'gtm-muted', '暂无来源记录'));
    refs.forEach((sourceId) => { const source = list(state.detail.sources).find((s) => s.id === sourceId); if (!source) { wrap.append(node('p', 'gtm-warning', '来源缺失：' + sourceId)); return; } const p = node('p'); p.append(safeLink(source.url, source.title || source.publisher || '查看来源')); wrap.append(p, node('p', 'gtm-muted', (source.verification === 'official' ? '官方资料' : '待核验资料') + ' · 访问 ' + str(source.accessed_on) + (source.published_on ? ' · 发布 ' + source.published_on : '')), node('p', '', str(source.claim))); if (typeof source.age_days === 'number' && source.age_days < 0) wrap.append(node('p', 'gtm-warning', '该来源访问日期晚于统计截至日。')); });
    parent.append(wrap);
  }
  function disclosure(parent, title, text) { const d = node('details', 'gtm-disclosure'); d.append(node('summary', '', title), node('p', '', text)); parent.append(d); }
  function tag(text) { return node('span', 'gtm-tag', text); }
  function actions(items) { const n = node('div', 'gtm-actions'); items.forEach((x) => n.append(x)); return n; }
  function visibleObjects() { return objects(state.detail).filter((x) => matches(x, state) && (!state.geography || window.GTMMap.fits(x, state.geoProvince, state.geoCity, state.geography))); }
  function selectedObject() { return objects(state.detail).find((x) => x.key === state.selected); }
  function selectObject(item, scroll) { state.selected = item.key; renderSelection(); renderMap(); renderTab(); if (scroll) $('selection').scrollIntoView({ block: 'nearest', behavior: 'auto' }); }
  function renderSummary() {
    const d = state.detail, c = d.campaign, n = clear($('campaign-summary'));
    n.append(tag(c.simulation ? '模拟计划' : '真实推广'), node('strong', '', str(c.name)), node('p', '', str(c.product)), node('p', 'gtm-muted', '目标客户：' + str(c.target_customer) + ' · 负责人：' + str(c.owner)));
    const f = clear($('funnel')), values = d.analytics && d.analytics.funnel || {};
    [['candidates', '候选企业'], ['contacted', '已触达'], ['responded', '已回应'], ['meeting', '已约谈'], ['qualified', '有效线索'], ['opportunities', '关联商机'], ['won', '已签约企业']].forEach(([key, label]) => { const m = node('div', 'gtm-metric'); m.append(node('span', '', label), node('strong', '', str(values[key]))); f.append(m); });
    const regions = Array.from(new Set(objects(d).map((x) => x.region).filter(Boolean))).sort();
    const region = clear($('region-filter')); region.append(new Option('全部区域', '')); regions.forEach((r) => region.append(new Option(r, r))); if (!regions.includes(state.region)) state.region = ''; region.value = state.region;
  }
  function setGeography(province, city = '') {
    state.geoProvince = province; state.geoCity = city; state.zoom = 1;
    const items = visibleObjects(); if (!items.some((x) => x.key === state.selected)) state.selected = items[0] ? items[0].key : '';
    renderMap(); renderSelection(); renderTab();
  }
  function renderMap() {
    const items = visibleObjects(), mapped = items.filter(hasLocation), data = state.geography;
    if (!data) return;
    const provinces = data.features.filter((f) => f.name), cities = data.cities[state.geoProvince] || [];
    const provinceSelect = clear($('province-select')); provinceSelect.append(new Option('全国 · 34个省级区域', ''));
    provinces.forEach((f) => provinceSelect.append(new Option(f.name, f.code))); provinceSelect.value = state.geoProvince;
    const citySelect = clear($('city-select')); citySelect.append(new Option(state.geoProvince ? '全省 / 全辖区' : '请先选择省级区域', ''));
    cities.forEach((c) => citySelect.append(new Option(c.name, c.code))); citySelect.value = state.geoCity; citySelect.disabled = !cities.length;
    const cityList = clear($('city-index'));
    const heading = node('summary', '', state.geoProvince ? '下辖单位名录（' + cities.length + '）' : '全部省级区域（34）'); cityList.append(heading);
    const choices = node('div', 'gtm-area-choices');
    (state.geoProvince ? cities : provinces).forEach((area) => {
      const count = objects(state.detail).filter((item) => window.GTMMap.fits(item, state.geoProvince || area.code, state.geoProvince ? area.code : '', data)).length;
      const b = button(area.name + (count ? ' · ' + count : ''), () => state.geoProvince ? setGeography(state.geoProvince, area.code) : setGeography(area.code), area.code === state.geoCity); choices.append(b);
    }); cityList.append(choices);
    if (state.geoProvince && !cities.length) cityList.append(node('p', 'gtm-warning', '此数据源暂无该区域的市县点位资料；保留省级边界与标注，不补造城市坐标。'));
    $('map-scope').textContent = state.geoProvince ? provinces.find((p) => p.code === state.geoProvince).name + (state.geoCity ? ' / ' + cities.find((c) => c.code === state.geoCity).name : '') : '中国行政区划沙盘';
    window.GTMMap.render({ svg: $('map'), data, province: state.geoProvince, city: state.geoCity, items, selected: state.selected, zoom: state.zoom, onProvince: (code) => setGeography(code), onCity: (code) => setGeography(state.geoProvince, code), onObject: (item) => selectObject(item) });
    $('result-count').textContent = items.length + ' 个推广对象'; $('unmapped-count').textContent = '无坐标 ' + (items.length - mapped.length) + ' 个（保留在列表）';
    $('zoom-in').disabled = state.zoom >= 4; $('zoom-out').disabled = state.zoom <= 1;
  }
  function renderSelection() {
    const n = clear($('selection')), item = selectedObject();
    if (!item) { n.append(node('h2', '', '对象详情'), node('p', 'gtm-muted', visibleObjects().length ? '从地图或下方列表选择对象。' : '没有匹配对象。')); return; }
    const isTarget = item.object_type === 'company'; n.append(tag(labels[item.object_type] || item.object_type), tag(isTarget ? labels[item.status] || '候选' : labels[eventStatus(item, state.detail.as_of)]), node('h2', '', item.name), node('p', 'gtm-muted', [item.region, item.city, item.industry].filter(Boolean).join(' · ')));
    if (isTarget) { n.append(node('p', '', fitLabel(item) + ' · 评分覆盖 ' + Math.round((item.fit_coverage || 0) * 100) + '%')); disclosure(n, '适配评分分项', ['industry', 'pain', 'access', 'evidence'].map((k, i) => ['行业', '痛点', '可接触性', '证据'][i] + '：' + str(item.fit && item.fit[k])).join(' · ')); }
    else { n.append(node('p', '', item.starts_on ? item.starts_on + ' 至 ' + item.ends_on : item.object_type === 'channel' ? '持续渠道' : '活动日期待核验')); if (item.organizer) n.append(node('p', '', '主办方：' + item.organizer)); if (item.audience) n.append(node('p', '', '受众：' + item.audience)); }
    n.append(node('p', '', '适配推断：' + str(item.fit_reason))); if (item.hypothesis) n.append(node('p', 'gtm-muted', '待验证假设：' + item.hypothesis));
    if (hasLocation(item)) n.append(node('p', 'gtm-muted', (item.location.precision === 'city' ? '城市中心近似点' : '站点坐标') + ' · ' + item.location.lon + ', ' + item.location.lat)); else n.append(node('p', 'gtm-warning', '位置未知，未在沙盘标点。'));
    if (item.website || item.url) n.append(safeLink(item.website || item.url, '公开页面 ↗'));
    const row = actions([button('登记跟进', () => openTouch(isTarget ? item.id : '', isTarget ? '' : item.id), true)]); if (isTarget) row.append(button('关联商机', () => openLink(item.id))); n.append(row);
    if (isTarget) list(state.detail.links).filter((l) => l.target_id === item.id).forEach((l) => { const p = node('p'); p.append(navLink('/?opportunity_id=' + encodeURIComponent(l.opportunity_id), str(l.opportunity && l.opportunity.name, '打开关联商机') + ' ↗')); n.append(p); if (l.link_error) n.append(node('p', 'gtm-warning', str(l.link_error))); });
    const colocated = hasLocation(item) ? visibleObjects().filter((other) => hasLocation(other) && other.location.lon === item.location.lon && other.location.lat === item.location.lat) : [];
    if (colocated.length > 1) {
      const group = node('details', 'gtm-disclosure'); group.open = true;
      group.append(node('summary', '', item.city + '同点位对象（' + colocated.length + '）'));
      const choices = node('div', 'gtm-city-choices');
      colocated.forEach((other) => { const choice = button(other.name, () => selectObject(other), other.key === item.key); choice.setAttribute('aria-pressed', String(other.key === item.key)); choices.append(choice); });
      group.append(choices); n.append(group);
    }
    detailSources(n, item.source_ids); disclosure(n, '记录标识', item.id);
  }
  function table(headers, rows) { const wrap = node('div', 'gtm-table-wrap'), t = node('table', 'gtm-table'), head = node('thead'), tr = node('tr'); headers.forEach((h) => tr.append(node('th', '', h))); head.append(tr); t.append(head); const body = node('tbody'); rows.forEach(({ cells, selected }) => { const row = node('tr', selected ? 'is-selected' : ''); cells.forEach((value) => { const td = node('td'); td.append(value instanceof Node ? value : document.createTextNode(str(value))); row.append(td); }); body.append(row); }); t.append(body); wrap.append(t); return wrap; }
  function empty(n, text) { n.append(node('div', 'gtm-empty gtm-muted', text)); }
  function renderTab() {
    document.querySelectorAll('.gtm-tab').forEach((b) => { b.setAttribute('aria-selected', String(b.dataset.tab === state.tab)); b.tabIndex = b.dataset.tab === state.tab ? 0 : -1; });
    const n = clear($('tab-content')); n.setAttribute('aria-labelledby', 'tab-' + state.tab);
    const visible = visibleObjects(), targets = visible.filter((x) => x.object_type === 'company');
    if (['companies', 'events', 'channels'].includes(state.tab)) {
      const rows = visible.filter((x) => state.tab === 'companies' ? x.object_type === 'company' : state.tab === 'channels' ? x.object_type === 'channel' : ['exhibition', 'forum'].includes(x.object_type));
      if (!rows.length) return empty(n, '暂无匹配' + tabs.find((x) => x[0] === state.tab)[1] + '。');
      n.append(table(['对象', '区域 / 城市', state.tab === 'companies' ? '状态 / 适配' : '时间 / 状态', '适配推断', '操作'], rows.map((item) => { const name = node('div'); name.append(node('span', 'gtm-row-name', item.name)); if (item.industry || item.organizer) name.append(node('span', 'gtm-muted', item.industry || item.organizer)); const status = node('div'); if (item.object_type === 'company') status.append(tag(labels[item.status] || '候选'), node('div', 'gtm-muted', fitLabel(item))); else status.append(tag(labels[eventStatus(item, state.detail.as_of)]), node('div', 'gtm-muted', item.starts_on ? item.starts_on + ' 至 ' + item.ends_on : item.kind === 'channel' ? '持续渠道' : '日期未知')); return { selected: state.selected === item.key, cells: [name, [item.region, item.city].filter(Boolean).join(' / '), status, str(item.fit_reason), actions([button('查看', () => selectObject(item, true)), button('跟进', () => openTouch(item.object_type === 'company' ? item.id : '', item.object_type === 'company' ? '' : item.id), true)])] }; })));
    } else if (state.tab === 'messages') {
      const allowed = new Set(targets.map((x) => x.id)); const messages = list(state.detail.messages).filter((m) => (!m.target_id ? !state.region && (!state.type || state.type === 'company') : allowed.has(m.target_id)) && (!state.keyword || [m.title, m.opening, m.value, m.role, m.channel].join(' ').toLowerCase().includes(state.keyword.toLowerCase()) || allowed.has(m.target_id)));
      if (!messages.length) return empty(n, '暂无匹配话术草稿。');
      messages.forEach((m) => { const section = node('article', 'gtm-message'); section.append(tag('草稿 · 未发送'), node('h3', '', m.title), node('p', 'gtm-muted', str(m.channel) + ' · ' + str(m.role) + ' · ' + str((list(state.detail.targets).find((t) => t.id === m.target_id) || {}).name, '分群话术'))); [['opening', '开场'], ['value', '价值'], ['proof', '证据'], ['cta', '下一步'], ['objection', '异议回应']].forEach(([key, label]) => { section.append(node('strong', '', label), node('p', '', str(m[key]))); }); section.append(actions([button('复制话术', () => copyMessage(m))])); detailSources(section, m.source_ids); n.append(section); });
    } else if (state.tab === 'touches') {
      const touches = scopeSnapshot(state.detail, visible).touches.sort((a, b) => b.occurred_on.localeCompare(a.occurred_on));
      const toolbar = node('div', 'gtm-section-head'); toolbar.append(actions([button('登记跟进', () => openTouch(), true)])); n.append(toolbar);
      if (!touches.length) return empty(n, '暂无匹配跟进记录。');
      n.append(table(['企业 / 日期', '渠道 / 结果', '跟进事实与证据', '下一步', '费用 / 操作'], touches.map((t) => { const target = list(state.detail.targets).find((x) => x.id === t.target_id), fact = node('div'); fact.append(node('div', '', t.summary), node('p', 'gtm-muted', '证据：' + str(t.evidence))); disclosure(fact, '记录标识', t.id); const next = node('div'); next.append(node('div', '', str(t.next_action)), node('div', 'gtm-muted', str(t.owner) + ' · ' + str(t.due_on))); const cost = node('div'); cost.append(node('p', '', t.outcome === 'planned' ? '计划无实际费用' : t.occurred_on > (state.detail.actual_through || (state.detail.as_of < today() ? state.detail.as_of : today())) ? '未来记录 · 未计实际费用' : t.actual_cost == null ? '费用未知' : str(t.currency, state.detail.campaign.currency) + ' ' + t.actual_cost)); if (t.outcome === 'qualified' && t.occurred_on <= state.detail.as_of && t.occurred_on <= today()) cost.append(button('关联商机', () => openLink(t.target_id, t.id))); return { cells: [(target ? target.name : t.target_id) + ' / ' + t.occurred_on, str(t.channel) + ' / ' + (labels[t.outcome] || t.outcome) + (t.occurred_on > (state.detail.actual_through || (state.detail.as_of < today() ? state.detail.as_of : today())) ? '（未来，不计实际）' : ''), fact, next, cost] }; })));
    } else renderAnalysis(n);
  }
  function renderAnalysis(n) {
    const d = state.detail, scoped = scopeSnapshot(d, visibleObjects()), national = scopeSnapshot(d, objects(d));
    const a = scoped.analytics, all = d.analytics || national.analytics, body = node('div', 'gtm-analysis');
    const filtered = !!(state.geoProvince || state.region || state.type || state.keyword);
    const scope = state.geoProvince ? $('map-scope').textContent : state.region || '全国';
    const heading = node('div', 'gtm-analysis-heading'); heading.append(node('h2', '', scope + ' · 分析'), node('span', 'gtm-muted', filtered ? '当前筛选 · 截至 ' + d.as_of : '全国汇总 · 截至 ' + d.as_of)); body.append(heading);
    if (state.region || state.type || state.keyword) body.append(node('p', 'gtm-muted', '叠加筛选：' + [state.region, labels[state.type], state.keyword && '关键词“' + state.keyword + '”'].filter(Boolean).join(' · ')));
    const metrics = node('div', 'gtm-scope-metrics'); metrics.setAttribute('aria-label', '当前范围指标');
    [['企业', scoped.targets.length, national.targets.length], ['活动 / 渠道', scoped.events.length, national.events.length], ['实际跟进', scoped.actual.length, national.actual.length], ['有效线索', a.funnel.qualified, all.funnel.qualified], ['关联商机', a.funnel.opportunities, all.funnel.opportunities], ['已记录成本', money(a.costs), money(all.costs)], ['缺少费用的实际跟进', a.missing_cost_count + ' 条', all.missing_cost_count + ' 条'], ['已签署合同金额', money(a.signed_amounts), money(all.signed_amounts)]].forEach(([label, value, total]) => { const m = node('div', 'gtm-metric'); m.append(node('span', '', label), node('strong', '', String(value))); if (filtered) m.append(node('span', 'gtm-national-value', '全国 ' + total)); metrics.append(m); }); body.append(metrics);
    disclosure(body, '统计口径', '分析与地图使用相同省市、区域、类型和关键词筛选。跟进、商机和费用归属目标企业所在地；活动/渠道按举办地展示，活动行仅统计当前筛选企业的关联。异地活动不会把客户跟进重复归入举办地；只看活动时无可见企业，企业指标为空。实际跟进截至 ' + d.actual_through + '；计划及未来记录单列，不计实际。企业里程碑去重累积；费用按币种统计，未登记保持未知；签署金额按商机去重。顶部漏斗与指标下方全国值不受筛选影响。商机阶段/评分为当前回读，历史截至日不重建商机状态，签署金额只来自有效签署事实。');
    function section(title, rows, headers, cells, emptyText) { const sec = node('section'); sec.append(node('h3', '', title)); if (rows.length) sec.append(table(headers, rows.map((r) => ({ cells: cells(r) })))); else sec.append(node('p', 'gtm-muted', emptyText || '暂无统计记录。')); body.append(sec); }
    section('企业（' + scoped.targets.length + '）', scoped.targets, ['企业', '区域 / 城市', '状态', '适配', '操作'], (t) => [t.name, [t.region, t.city].filter(Boolean).join(' / '), labels[t.status] || '候选', fitLabel(t), button('查看', () => selectObject(t, true))], '当前范围暂无企业。');
    const touches = [...scoped.touches].sort((a, b) => b.occurred_on.localeCompare(a.occurred_on));
    section('跟进（实际 ' + scoped.actual.length + ' · 计划 / 未来 ' + scoped.pending.length + '）', touches, ['企业 / 日期', '渠道 / 结果', '跟进摘要', '费用'], (t) => [(scoped.targets.find((x) => x.id === t.target_id) || {}).name + ' / ' + t.occurred_on, t.channel + ' / ' + (labels[t.outcome] || t.outcome), t.summary, scoped.actual.includes(t) ? (t.actual_cost == null ? '费用未知' : money({ [t.currency]: t.actual_cost })) : '计划 / 未来 · 不计实际费用'], '当前范围暂无跟进。');
    section('区域分布', a.regions, ['区域', '候选', '触达', '意向', '商机', '签约'], (r) => [r.name, r.candidates, r.contacted, r.qualified, r.opportunities, r.won]);
    section('渠道效果', a.channels, ['渠道', '实际跟进', '触达企业', '回应企业', '意向企业', '成本 / 缺失'], (r) => [r.name, r.touches, r.contacted, r.responded, r.qualified, money(r.costs) + ' / ' + r.missing_cost_count + ' 条']);
    section('活动 / 渠道关联（' + scoped.events.length + '）', a.events, ['活动 / 渠道', '企业', '意向', '商机', '成本 / 缺失'], (r) => [r.name, r.targets, r.qualified, r.opportunities, money(r.costs) + ' / ' + r.missing_cost_count + ' 条'], '当前范围暂无活动或渠道。');
    section('当前关联商机（' + scoped.links.length + '）', scoped.links, ['企业 / 商机', '当前阶段', '评分', '签署金额', '核验状态'], (l) => { const o = l.opportunity || {}, name = node('div'); name.append(node('p', '', str(o.company_name)), navLink('/?opportunity_id=' + encodeURIComponent(l.opportunity_id), str(o.name, '打开商机') + ' ↗')); const sums = {}; list(o.signed_amounts).forEach((m) => { sums[m.currency] = (sums[m.currency] || 0) + m.amount; }); return [name, str(o.current_stage_name, stageLabels[o.current_stage_id] || o.current_stage_id), str(o.score), money(sums), l.link_error ? str(l.link_error) : str(verificationLabels[o.verification_status] || o.verification_status)]; }, '当前范围暂无关联商机。');
    n.append(body);
  }
  function renderBrief() {
    const n = clear($('brief-content')), d = state.detail, brief = d.search_brief || {};
    if (list(brief.missing_inputs).length) n.append(node('p', 'gtm-warning', '待补充：' + brief.missing_inputs.join('、')));
    list(brief.queries).forEach((q) => { const section = node('div', 'gtm-query'); section.append(tag(labels[q.kind] || (q.kind === 'event' ? '活动' : q.kind)), node('p', '', q.query), node('p', 'gtm-muted', list(q.checks).join(' · '))); n.append(section); });
    if (!list(brief.queries).length) n.append(node('p', 'gtm-muted', '暂无检索任务。'));
    n.append(node('p', 'gtm-muted', '这些任务供检索采集使用；页面不会自动搜索或发送推广消息。'));
    disclosure(n, '计划版本与标识', '计划 ' + d.campaign.id + ' · 修订 ' + d.revision + ' · 截至 ' + d.as_of);
  }
  function render() { if (!state.detail) return; renderSummary(); const visible = visibleObjects(); if (!visible.some((x) => x.key === state.selected)) state.selected = visible[0] ? visible[0].key : ''; renderMap(); renderSelection(); renderTab(); renderBrief(); $('workspace').hidden = false; $('empty').hidden = true; }
  async function loadCampaign(campaignId) {
    const version = ++state.loadVersion; $('campaign-select').disabled = true; notice('正在加载计划…');
    try { const result = await api('/api/gtm/campaign/' + encodeURIComponent(campaignId) + '?as_of=' + encodeURIComponent($('as-of').value || today())); if (version !== state.loadVersion) return; state.id = campaignId; state.detail = result.detail; $('campaign-select').value = campaignId; const u = new URL(location.href); u.searchParams.set('campaign_id', campaignId); history.replaceState(null, '', u); render(); notice(''); }
    catch (error) { if (version === state.loadVersion) { $('campaign-select').value = state.id; notice(error.message + '，可点击刷新重试。', 'error'); } }
    finally { if (version === state.loadVersion) $('campaign-select').disabled = false; }
  }
  async function loadList(preferred) {
    const result = await api('/api/gtm/campaigns'); state.campaigns = list(result.campaigns); const select = clear($('campaign-select'));
    if (!state.campaigns.length) { select.append(new Option('暂无计划', '')); state.detail = null; state.id = ''; $('workspace').hidden = true; $('empty').hidden = false; clear($('campaign-summary')).append(node('span', 'gtm-muted', '创建第一条推广计划')); return; }
    state.campaigns.forEach((c) => select.append(new Option(c.name + (c.simulation ? '（模拟）' : ''), c.id)));
    const chosen = state.campaigns.find((c) => c.id === (preferred || state.id)); await loadCampaign(chosen ? chosen.id : state.campaigns[0].id);
  }
  function field(form, label, name, type = 'text', value = '', required = true, choices) {
    const wrapper = node('label', 'gtm-field' + (type === 'textarea' ? ' gtm-full' : ''), label + (required ? ' *' : '')); const input = node(type === 'textarea' ? 'textarea' : type === 'select' ? 'select' : 'input'); input.name = name;
    if (type === 'select') list(choices).forEach(([v, t]) => input.append(new Option(t, v))); else if (type !== 'textarea') input.type = type;
    input.value = value; input.required = required; if (type === 'number') { input.min = '0'; input.step = '0.01'; } wrapper.append(input); form.append(wrapper); return input;
  }
  function formValue(form, name) { const input = form.elements.namedItem(name); return input ? input.value.trim() : ''; }
  function showForm(title) {
    $('dialog-title').textContent = title; const form = node('form', 'gtm-form'); clear($('dialog-body')).append(form); const error = node('div', 'gtm-form-error gtm-full'); error.hidden = true; error.setAttribute('role', 'alert'); form.append(error); form.addEventListener('input', () => { delete form.dataset.request; }); $('form-dialog').showModal(); return { form, error };
  }
  function formError(error, message) { error.textContent = message; error.hidden = false; error.scrollIntoView({ block: 'nearest' }); }
  function formSubmit(form, label = '保存') { const submit = node('button', 'gtm-btn gtm-primary', label); submit.type = 'submit'; const row = actions([submit]); row.classList.add('gtm-full'); form.append(row); return submit; }
  async function save(form, errorNode, submit, operations, campaignId, revision, actor) {
    submit.disabled = true; const text = submit.textContent; submit.textContent = '保存中…'; errorNode.hidden = true;
    if (!form.dataset.request) form.dataset.request = id('req');
    try {
      const result = await api('/api/gtm/manage', { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Workbench-Token': window.WORKBENCH_TOKEN }, body: JSON.stringify({ campaign_id: campaignId, request_id: form.dataset.request, expected_revision: revision, actor, operations }) });
      $('form-dialog').close(); state.id = result.campaign_id || campaignId; if (result.detail) { state.detail = result.detail; render(); } try { await loadList(state.id); notice('已保存 · 修订 ' + result.revision, 'success'); } catch (refreshError) { notice('已保存 · 修订 ' + result.revision + '；列表刷新失败：' + refreshError.message, 'error'); }
    } catch (e) { formError(errorNode, (e.status === 409 ? '计划已更新；输入已保留。请先刷新版本，再保存。' : '') + e.message); if (e.status === 409 && !form.querySelector('[data-conflict]')) { const refresh = button('刷新版本并保留输入', async () => { await loadCampaign(state.id); delete form.dataset.request; refresh.remove(); formError(errorNode, '已读取最新版本，请检查输入后重新保存。'); }); refresh.dataset.conflict = 'true'; form.append(refresh); } }
    finally { submit.disabled = false; submit.textContent = text; }
  }
  function openCreate() {
    const { form, error } = showForm('创建推广计划'); const campaignId = id('gtm');
    field(form, '计划名称', 'name'); field(form, '负责人 / 操作人', 'owner'); field(form, '产品与卖点', 'product', 'textarea'); field(form, '目标客户', 'target_customer', 'textarea'); field(form, '目标区域（逗号分隔）', 'regions'); field(form, '记录类型', 'simulation', 'select', 'false', true, [['false', '真实推广'], ['true', '模拟演示']]); field(form, '币种', 'currency', 'text', 'CNY');
    const submit = formSubmit(form, '创建计划'); form.addEventListener('submit', (e) => { e.preventDefault(); const regions = formValue(form, 'regions').split(/[,，、\n]/).map((x) => x.trim()).filter(Boolean); if (!regions.length) return formError(error, '请至少填写一个目标区域。'); save(form, error, submit, [{ type: 'create_campaign', name: formValue(form, 'name'), product: formValue(form, 'product'), target_customer: formValue(form, 'target_customer'), regions, owner: formValue(form, 'owner'), simulation: formValue(form, 'simulation') === 'true', currency: formValue(form, 'currency') }], campaignId, 0, formValue(form, 'owner')); });
  }
  function openTouch(targetId = '', eventId = '') {
    if (!state.detail || !list(state.detail.targets).length) return notice('请先导入有来源的目标企业，再登记跟进。', 'error');
    const { form, error } = showForm('登记跟进'); const d = state.detail, touchId = id('touch');
    field(form, '目标企业', 'target_id', 'select', targetId || d.targets[0].id, true, d.targets.map((t) => [t.id, t.name])); field(form, '关联活动 / 渠道', 'event_id', 'select', eventId, false, [['', '无关联活动']].concat(list(d.events).map((e) => [e.id, e.name + '（' + labels[eventStatus(e, d.as_of)] + '）']))); field(form, '触达渠道', 'channel'); field(form, '发生日期', 'occurred_on', 'date', today()); const outcome = field(form, '结果', 'outcome', 'select', 'contacted', true, ['planned', 'contacted', 'responded', 'meeting', 'qualified', 'no_fit'].map((v) => [v, labels[v]])); field(form, '跟进事实', 'summary', 'textarea'); const evidence = field(form, '证据 / 来源说明', 'evidence', 'textarea'); field(form, '下一步行动', 'next_action', 'textarea'); field(form, '负责人 / 操作人', 'owner', 'text', d.campaign.owner || ''); field(form, '行动截止', 'due_on', 'date', '', false); const cost = field(form, '实际费用（留空表示未知）', 'actual_cost', 'number', '', false); const currency = field(form, '费用币种', 'currency', 'text', d.campaign.currency || 'CNY', false);
    outcome.addEventListener('change', () => { const planned = outcome.value === 'planned'; evidence.required = !planned; cost.disabled = planned; currency.disabled = planned; if (planned) cost.value = ''; });
    const submit = formSubmit(form, '保存跟进'); form.addEventListener('submit', (e) => { e.preventDefault(); const record = { id: touchId, target_id: formValue(form, 'target_id'), channel: formValue(form, 'channel'), occurred_on: formValue(form, 'occurred_on'), outcome: formValue(form, 'outcome'), summary: formValue(form, 'summary'), evidence: formValue(form, 'evidence'), next_action: formValue(form, 'next_action'), owner: formValue(form, 'owner') }; if (formValue(form, 'event_id')) record.event_id = formValue(form, 'event_id'); if (formValue(form, 'due_on')) record.due_on = formValue(form, 'due_on'); if (formValue(form, 'actual_cost') && record.outcome !== 'planned') { record.actual_cost = Number(formValue(form, 'actual_cost')); record.currency = formValue(form, 'currency'); if (!record.currency) return formError(error, '有实际费用时必须填写币种。'); } save(form, error, submit, [{ type: 'record_touch', record }], state.id, state.detail.revision, record.owner); });
  }
  async function openLink(targetId, touchId = '') {
    if (!state.detail) return; const eligible = qualifiedTouches(state.detail, targetId);
    if (!eligible.length) return notice('关联商机前，请为该企业登记已经发生、含证据的“有效线索”跟进。', 'error');
    const { form, error } = showForm('关联已有商机'); const target = list(state.detail.targets).find((t) => t.id === targetId); const hint = node('p', 'gtm-muted gtm-full', str(target && target.name) + ' · 商机企业名称必须一致；关联不会推进原商机阶段。'); form.append(hint);
    const opportunity = field(form, '已有商机', 'opportunity_id', 'select', '', true, [['', '加载商机中…']]); field(form, '意向跟进依据', 'touch_id', 'select', touchId || eligible[0].id, true, eligible.map((t) => [t.id, t.occurred_on + ' · ' + t.summary])); field(form, '操作人', 'actor', 'text', state.detail.campaign.owner || ''); const submit = formSubmit(form, '确认关联'); submit.disabled = true;
    try { const result = await api('/api/opportunities'); const opportunities = list(result.opportunities); clear(opportunity); opportunity.append(new Option('请选择现有商机', '')); opportunities.forEach((o) => opportunity.append(new Option(str(o.company_name || o.name) + ' · ' + str(o.name, o.id), o.id))); if (!opportunities.length) formError(error, '暂无现有商机，请先在商机工作台建立主账。'); submit.disabled = !opportunities.length; } catch (e) { formError(error, e.message); }
    form.addEventListener('submit', (e) => { e.preventDefault(); save(form, error, submit, [{ type: 'link_opportunity', target_id: targetId, opportunity_id: formValue(form, 'opportunity_id'), touch_id: formValue(form, 'touch_id') }], state.id, state.detail.revision, formValue(form, 'actor')); });
  }
  async function copyMessage(message) { const content = ['opening', 'value', 'proof', 'cta', 'objection'].map((key) => message[key]).filter(Boolean).join('\n\n'); try { await navigator.clipboard.writeText(content); notice('话术草稿已复制，尚未发送。', 'success'); } catch (_) { notice('无法访问剪贴板，请选择话术正文复制。', 'error'); } }
  function filterChanged() { state.region = $('region-filter').value; state.type = $('type-filter').value; state.keyword = $('keyword').value.trim(); const visible = visibleObjects(); if (!visible.some((x) => x.key === state.selected)) state.selected = visible[0] ? visible[0].key : ''; state.zoom = 1; renderMap(); renderSelection(); renderTab(); }
  function setup() {
    $('as-of').value = today();
    tabs.forEach(([key, text], index) => { const b = node('button', 'gtm-tab', text); b.type = 'button'; b.id = 'tab-' + key; b.dataset.tab = key; b.setAttribute('role', 'tab'); b.setAttribute('aria-controls', 'tab-content'); b.addEventListener('click', () => { state.tab = key; renderTab(); }); b.addEventListener('keydown', (e) => { if (['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(e.key)) { e.preventDefault(); const next = e.key === 'Home' ? 0 : e.key === 'End' ? tabs.length - 1 : (index + (e.key === 'ArrowRight' ? 1 : -1) + tabs.length) % tabs.length; state.tab = tabs[next][0]; renderTab(); $('tab-' + state.tab).focus(); } }); $('tabs').append(b); });
    $('campaign-select').addEventListener('change', () => { state.geoProvince = ''; state.geoCity = ''; state.selected = ''; state.zoom = 1; loadCampaign($('campaign-select').value); }); $('as-of').addEventListener('change', () => { if (state.id && $('as-of').value) loadCampaign(state.id); });
    ['region-filter', 'type-filter'].forEach((name) => $(name).addEventListener('change', filterChanged)); $('keyword').addEventListener('input', filterChanged);
    $('clear-filters').addEventListener('click', () => { $('region-filter').value = ''; $('type-filter').value = ''; $('keyword').value = ''; state.geoProvince = ''; state.geoCity = ''; filterChanged(); });
    $('province-select').addEventListener('change', () => setGeography($('province-select').value)); $('city-select').addEventListener('change', () => setGeography(state.geoProvince, $('city-select').value)); $('national-map').addEventListener('click', () => setGeography(''));
    $('zoom-in').addEventListener('click', () => { state.zoom = Math.min(4, state.zoom * 1.5); renderMap(); }); $('zoom-out').addEventListener('click', () => { state.zoom = Math.max(1, state.zoom / 1.5); renderMap(); }); $('reset-map').addEventListener('click', () => { state.zoom = 1; renderMap(); });
    $('new-campaign').addEventListener('click', openCreate); $('empty-create').addEventListener('click', openCreate); $('close-dialog').addEventListener('click', () => $('form-dialog').close());
    $('theme-toggle').addEventListener('click', () => { const dark = document.documentElement.dataset.theme === 'dark'; document.documentElement.dataset.theme = dark ? 'light' : 'dark'; $('theme-toggle').textContent = dark ? '切换深色' : '切换浅色'; });
    $('refresh').addEventListener('click', () => loadList(state.id).catch((e) => notice(e.message, 'error')));
    api('/assets/china-map.json').then((data) => { state.geography = data; return loadList(new URLSearchParams(location.search).get('campaign_id')); }).catch((e) => { notice(e.message + '，可点击刷新重试。', 'error'); clear($('campaign-select')).append(new Option('加载失败', '')); });
  }
  setup();
}());
