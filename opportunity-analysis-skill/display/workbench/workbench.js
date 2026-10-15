(function () {
  'use strict';

  const state = { opportunities: [], detail: null, selectedId: null, busy: false };
  const token = window.WORKBENCH_TOKEN;
  let fieldSeq = 0;
  const $ = (id) => document.getElementById(id);
  const text = (value) => value == null || value === '' ? '—' : String(value);
  const make = (tag, className, content) => {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (content !== undefined) node.textContent = content;
    return node;
  };
  const button = (label, className, handler) => {
    const node = make('button', 'wb-btn ' + (className || 'wb-btn-secondary'), label);
    node.type = 'button';
    node.addEventListener('click', handler);
    return node;
  };
  const field = (label, name, type, value, options) => {
    const wrap = make('div', 'wb-field' + (options && options.full ? ' wb-field-full' : ''));
    const inputId = 'wb-' + name + '-' + (++fieldSeq);
    const labelNode = make('label', null, label);
    labelNode.htmlFor = inputId;
    wrap.appendChild(labelNode);
    let input;
    if (type === 'textarea') input = document.createElement('textarea');
    else if (type === 'select') {
      input = document.createElement('select');
      (options.choices || []).forEach((choice) => {
        const opt = make('option', null, choice[1]); opt.value = choice[0]; input.appendChild(opt);
      });
    } else input = document.createElement('input');
    input.id = inputId; input.name = name;
    if (type !== 'select' && type !== 'textarea') input.type = type || 'text';
    if (value !== undefined && value !== null) input.value = value;
    if (options && options.required) input.required = true;
    if (options && options.placeholder) input.placeholder = options.placeholder;
    wrap.appendChild(input);
    return wrap;
  };
  const valueOf = (form, name) => {
    const input = form.elements.namedItem(name);
    return input ? String(input.value).trim() : '';
  };
  const requestId = () => 'wb-' + Date.now().toString(36) + '-' + Math.random().toString(36).slice(2, 8);
  const requestIdFor = (form) => {
    if (!form.dataset.requestId) form.dataset.requestId = requestId();
    return form.dataset.requestId;
  };
  const makeFormDirty = (form) => { form.dataset.requestId = ''; };

  const STAGE_LABELS = { lead_identified: '线索', customer_contacted: '初次接触', needs_discovery: '需求澄清', opportunity_confirmed: '商机确认', solution_cocreation: '方案共创', budget_project_confirmed: '预算立项', proposal_bidding: '方案报价', commercial_negotiation: '商务谈判', contract_signing: '合同签订', won: '赢单' };
  const STATUS_LABELS = { active: '推进中', paused: '已暂停', won: '已赢单', lost: '已丢单', cancelled: '已取消', resolved: '已关闭', open: '待处理', completed: '已完成' };
  const RATING_LABELS = { strong: '强', medium: '中', weak: '弱', unknown: '未知' };
  const RISK_LABELS = { low: '低', medium: '中', high: '高' };
  const CONFIDENCE_LABELS = { high: '高', medium: '中', low: '低' };
  const EVIDENCE_LABELS = { sales_confirmed: '商务确认', needs_sales_confirmation: '待商务确认', inferred: '材料推断', confirmed: '已确认', reported: '客户转述', unknown: '未知' };
  const VERIFY_LABELS = { current: '当前有效', needs_review: '需要复核', valid: '当前有效', stale_or_missing: '文件失效', unbound: '未绑定', dependency_invalid: '依赖失效', superseded: '已被新版本替代' };
  const stageLabel = (value) => STAGE_LABELS[value] || text(value);
  const statusLabel = (value) => STATUS_LABELS[value] || text(value);
  const ratingLabel = (value) => RATING_LABELS[value] || text(value);
  const evidenceLabel = (value) => EVIDENCE_LABELS[value] || text(value);
  const verifyLabel = (value) => VERIFY_LABELS[value] || text(value);
  const riskLabel = (value) => RISK_LABELS[value] || text(value);
  const confidenceLabel = (value) => CONFIDENCE_LABELS[value] || text(value);

  function notice(message, kind) {
    const node = $('notice'); node.hidden = !message; node.textContent = message || '';
    node.className = 'wb-notice' + (kind ? ' is-' + kind : '');
    node.setAttribute('role', kind === 'error' ? 'alert' : 'status');
    if (message && kind === 'error') node.scrollIntoView({ block: 'nearest' });
  }

  function readableBlocker(message) {
    const factLabels = { quote_authorized: '当前报价授权', budget_confirmed: '预算批准', solution_scope: '方案范围确认', contact_established: '客户联系', need_confirmed: '需求确认', requirement_owner: '需求负责人', continue_intent: '继续推进意愿' };
    const kindLabels = { solution: '方案', quote: '报价', negotiation: '谈判纪要', contract: '合同', handoff: '交接包' };
    if (message.startsWith('fact unresolved, missing or negative: ')) return '待确认：' + (factLabels[message.slice('fact unresolved, missing or negative: '.length).trim()] || message.slice('fact unresolved, missing or negative: '.length).trim());
    if (message.startsWith('current artifact stale or missing: ') || message.startsWith('current artifact stale, unbound or missing: ')) {
      const kind = message.slice(message.lastIndexOf(': ') + 2).trim();
      return (kindLabels[kind] || kind) + '文件或依据版本需复核';
    }
    if (message.startsWith('current artifact does not match latest authorized quote: ')) return '成果依据的报价与最新授权不一致：' + (kindLabels[message.slice(message.lastIndexOf(': ') + 2).trim()] || message.slice(message.lastIndexOf(': ') + 2).trim());
    if (message.startsWith('artifact does not match latest authorized quote: ') || message.startsWith('signed contract does not match latest authorized quote: ')) return '成果依据的报价与最新授权不一致：' + (kindLabels[message.slice(message.lastIndexOf(': ') + 2).trim()] || message.slice(message.lastIndexOf(': ') + 2).trim());
    if (message === 'quote authorization is stale or unbound') return '报价授权已过期或未绑定当前版本';
    if (message === 'authorized quote is stale or unbound') return '授权报价已过期或未绑定当前版本';
    if (message === 'authorized quote is missing or unresolved') return '缺少已确认的报价授权';
    if (message === 'signed contract stale, unbound, missing or superseded' || message === 'signed contract stale, missing or superseded') return '签署合同或依据版本已失效、未绑定或被替代';
    if (message === 'signed contract record missing') return '缺少已签署合同登记';
    const reasonPrefixes = { 'artifact superseded: ': '成果已被新版本替代：', 'artifact file stale or missing: ': '成果文件已变化或缺失：', 'dependency invalid: ': '上游成果需复核：', 'dependency missing: ': '上游成果缺失：', 'dependency hash mismatch: ': '上游文件摘要不符：', 'artifact dependency cycle: ': '成果依赖循环：', 'required dependency missing: ': '缺少依据版本：' };
    for (const [prefix, label] of Object.entries(reasonPrefixes)) {
      if (message.startsWith(prefix)) { const id = message.slice(prefix.length).split(' (')[0]; return label + (kindLabels[id] || id); }
    }
    if (message.startsWith('artifact content review is missing: ')) return '成果缺少范围内容复核：' + message.slice(message.lastIndexOf(': ') + 2).trim();
    if (message.startsWith('artifact content review uses an outdated solution scope: ')) return '成果引用了过期的方案范围：' + message.slice(message.lastIndexOf(': ') + 2).trim();
    if (message.startsWith('quote solution differs from confirmed solution scope: ')) return '报价引用的方案与已确认范围不一致：' + message.slice(message.lastIndexOf(': ') + 2).trim();
    if (message.includes('solution scope') || message.includes('scope review') || message.includes('scope is stale') || message.includes('scope is missing')) return '方案范围已过期、未绑定或需要重新复核';
    if (message.startsWith('blocking review requires resolution or revalidation: ')) return '评审意见待整改或复核：' + message.slice(message.lastIndexOf(': ') + 2).trim();
    return message;
  }

  function readableError(message) {
    const raw = String(message || '请求失败');
    if (raw.startsWith('missing confirmed facts: ')) return '尚未确认：' + raw.slice('missing confirmed facts: '.length).split(',').map(id => ({ quote_authorized: '当前报价授权', budget_confirmed: '预算批准', solution_scope: '方案范围确认', contact_established: '客户联系', need_confirmed: '需求确认', requirement_owner: '需求负责人', continue_intent: '继续推进意愿' }[id.trim()] || id.trim())).join('、') + '。请核验并登记依据后重试。';
    if (raw.startsWith('resolve lifecycle blockers before transition: ')) return '阶段推进前仍有前置条件未满足：' + raw.slice('resolve lifecycle blockers before transition: '.length).split('; ').map(readableBlocker).join('；') + '。请先补齐或修复后重试。';
    if (raw.includes('won requires a recorded signed contract')) return '标记为赢单前，需要先登记一份已签署合同。';
    if (raw.includes('reopen closed opportunity')) return '商机已关闭，请先显式重新打开后再执行此操作。';
    if (raw.includes('resume paused opportunity')) return '商机已暂停，请先恢复推进后再执行阶段变更。';
    if (raw.includes('artifact content review must reference the current solution scope version')) return '成果内容复核必须引用当前方案范围版本，请重新登记当前文件。';
    if (raw.includes('solution scope artifact not found')) return '未找到绑定的方案成果，请选择当前有效方案后重试。';
    if (raw.includes('solution scope must bind the current')) return '方案范围确认必须绑定当前有效方案文件。';
    if (raw.includes('artifact content review is missing')) return '商业成果缺少范围内容复核，请先通过 CLI 登记实际阅读结论。';
    if (raw.includes('scope') && (raw.includes('stale') || raw.includes('missing') || raw.includes('invalid') || raw.includes('unbound'))) return '方案范围已过期、缺失或未绑定当前方案，请重新确认范围。';
    if (raw.includes('quote solution differs from confirmed solution scope')) return '报价引用的方案与已确认范围不一致，请重新登记报价文件。';
    if (raw.includes('revision conflict')) return '当前数据版本已变化，请刷新后重试。';
    if (raw.includes('review') && raw.includes('block')) return '仍有未关闭或需要复核的客户评审，请先处理评审意见。';
    if (raw.includes('signature') || raw.includes('customer_signed') || raw.includes('supplier_signed')) return '合同签署事实不完整，请确认客户与供应商双方均已登记签署。';
    if (raw.includes('permission') || raw.includes('not authorized') || raw.includes('unauthorized')) return '当前操作没有授权，请检查操作人和工作台权限。';
    if (raw.includes('authorization') && (raw.includes('missing') || raw.includes('invalid') || raw.includes('stale') || raw.includes('unbound'))) return '报价授权已缺失、过期或未绑定当前版本，请重新核验授权。';
    if (raw.includes('artifact') && (raw.includes('missing') || raw.includes('invalid') || raw.includes('stale') || raw.includes('unbound'))) return '缺少当前有效成果，请检查文件、授权和上游版本。';
    if (raw.includes('file') && (raw.includes('missing') || raw.includes('stale'))) return '成果文件已变更或缺失，请重新登记当前文件。';
    if (raw.includes('prerequisite') || raw.includes('prerequisites')) return '当前操作的前置条件未满足，请先处理页面提示的阻塞项。';
    return raw;
  }

  async function api(path, options) {
    const response = await fetch(path, options || {});
    let body = {};
    try { body = await response.json(); } catch (_) { body = { ok: false, error: { message: '服务返回了不可读取的结果' } }; }
    if (!response.ok || body.ok === false) {
      const error = new Error(readableError(body.error && body.error.message ? body.error.message : '请求失败'));
      error.status = response.status; error.code = body.error && body.error.code;
      throw error;
    }
    return body;
  }

  async function write(path, payload, submitButton) {
    if (submitButton) { submitButton.disabled = true; submitButton.textContent = '保存中…'; }
    try {
      const result = await api(path, { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Workbench-Token': token }, body: JSON.stringify(payload) });
      notice('已保存，主账修订号为 ' + text(result.revision), 'success');
      await loadList();
      await selectOpportunity(result.opportunity_id || state.selectedId);
      return result;
    } catch (error) {
      notice((error.status === 409 ? '主账已被其他操作更新，请刷新后重试：' : '') + error.message, 'error');
      throw error;
    } finally { if (submitButton) { submitButton.disabled = false; submitButton.textContent = '保存'; } }
  }

  async function loadList() {
    const result = await api('/api/opportunities'); state.opportunities = result.opportunities || [];
    const list = $('opportunity-list'); while (list.firstChild) list.removeChild(list.firstChild);
    $('list-count').textContent = result.count + ' 个商机 · 来自同一主账';
    if (!state.opportunities.length) { list.appendChild(make('div', 'wb-empty-row', '暂无商机，可从右侧新增第一次拜访。')); return; }
    state.opportunities.forEach((item) => {
      const node = make('button', 'wb-list-item' + (item.id === state.selectedId ? ' is-active' : ''));
      node.type = 'button'; node.dataset.id = item.id;
      node.appendChild(make('div', 'wb-list-title', text(item.company_name || item.name)));
      const meta = make('div', 'wb-list-meta'); meta.appendChild(make('span', null, stageLabel(item.lifecycle && item.lifecycle.current_stage_id || item.stage_id || item.stage))); meta.appendChild(make('span', null, '评分 ' + text(item.score))); node.appendChild(meta);
      node.addEventListener('click', () => selectOpportunity(item.id)); list.appendChild(node);
    });
  }

  function section(title, body, actions) {
    const panel = make('section', 'wb-panel wb-section'); const header = make('header'); header.appendChild(make('h3', 'wb-section-title', title));
    if (actions) { const actionWrap = make('div', 'wb-form-actions'); actions.forEach((item) => actionWrap.appendChild(item)); header.appendChild(actionWrap); }
    panel.appendChild(header); const content = make('div', 'wb-section-body'); content.appendChild(body); panel.appendChild(content); return panel;
  }
  function table(headers, rows) {
    const wrap = make('div', 'wb-table-wrap'); const tableNode = make('table', 'wb-table'); const thead = make('thead'); const tr = make('tr');
    headers.forEach((h) => tr.appendChild(make('th', null, h))); thead.appendChild(tr); tableNode.appendChild(thead); const tbody = make('tbody');
    rows.forEach((cells) => { const row = make('tr'); cells.forEach((cell) => { const td = make('td'); if (cell instanceof Node) td.appendChild(cell); else td.textContent = text(cell); row.appendChild(td); }); tbody.appendChild(row); });
    tableNode.appendChild(tbody); wrap.appendChild(tableNode); return wrap;
  }
  function formPanel(title, builder, open) {
    const panel = make('section', 'wb-panel wb-section wb-form-section'); const details = document.createElement('details'); details.open = Boolean(open);
    const summary = make('summary', null, title); details.appendChild(summary);
    const form = document.createElement('form'); form.className = 'wb-form'; builder(form); form.addEventListener('input', () => makeFormDirty(form)); details.appendChild(form); panel.appendChild(details); return panel;
  }
  function addSubmit(form, label) { const actions = make('div', 'wb-form-actions'); const submit = make('button', 'wb-btn wb-btn-primary', label || '保存'); submit.type = 'submit'; actions.appendChild(submit); form.appendChild(actions); return submit; }
  function managePayload(detail, operations, form) { return { request_id: requestIdFor(form), opportunity_id: detail.opportunity.id, expected_revision: detail.lifecycle.revision, actor: valueOf(form, 'operator') || detail.lifecycle.owner || '工作台操作人', operations: operations }; }
  function evidenceRefs(form, name) { const value = valueOf(form, name || 'evidence'); return value ? value.split(',').map((item) => item.trim()).filter(Boolean) : []; }
  function latestFact(life, factId) { return [...(life.facts || [])].reverse().find((fact) => fact.fact_id === factId) || null; }
  function validSolutions(life) { return (life.artifacts || []).filter((artifact) => artifact.kind === 'solution' && artifact.validity === 'valid').sort((a, b) => Number(b.version || 0) - Number(a.version || 0)); }
  function scopeVerification(fact) {
    if (!fact) return 'needs_review';
    if (fact.verification_status) return fact.verification_status;
    return 'needs_review';
  }
  function scopeArtifact(life, fact) {
    if (fact && fact.artifact_id) return (life.artifacts || []).find((artifact) => artifact.id === fact.artifact_id) || null;
    return null;
  }
  function scopeReview(artifact) {
    return artifact && artifact.scope_review || null;
  }
  function scopeReviewCell(artifact) {
    if (!['quote', 'negotiation', 'contract', 'handoff'].includes(artifact.kind)) return '—';
    const review = scopeReview(artifact);
    if (!review) return '未登记范围复核';
    const summary = String(review.summary || '已登记范围复核');
    const disclosure = make('details');
    disclosure.appendChild(make('summary', null, summary.length > 80 ? summary.slice(0, 80) + '…' : summary));
    const meta = make('div');
    meta.appendChild(make('p', null, '方案范围版本：v' + text(review.scope_version)));
    meta.appendChild(make('p', null, '复核人：' + text(review.actor)));
    meta.appendChild(make('p', null, '复核时间：' + text(review.time)));
    meta.appendChild(make('p', null, '完整说明：' + summary));
    if (review.scope_fact_id) meta.appendChild(make('p', null, '范围事实记录：' + review.scope_fact_id));
    disclosure.appendChild(meta);
    return disclosure;
  }
  function renderScopeSummary(life) {
    const fact = latestFact(life, 'solution_scope');
    const artifact = scopeArtifact(life, fact);
    const status = scopeVerification(fact);
    const body = make('div');
    const meta = make('div', 'wb-statuses');
    meta.appendChild(make('span', 'wb-tag ' + (status === 'current' ? 'wb-tag-primary' : ''), '范围：' + verifyLabel(status)));
    meta.appendChild(make('span', 'wb-tag', (status === 'current' ? '已确认方案：' : '原确认方案：') + (artifact ? 'v' + text(artifact.version) : '未绑定')));
    body.appendChild(meta);
    if (status === 'current') body.appendChild(make('p', 'wb-scope-text', String(fact.value)));
    else body.appendChild(make('p', 'wb-muted', '尚未确认方案范围，请绑定当前有效方案后登记。'));
    const details = make('details', 'wb-disclosure');
    details.appendChild(make('summary', null, '查看范围事实依据'));
    const detailsBody = make('div');
    if (fact) {
      detailsBody.appendChild(make('p', null, '登记范围：' + text(fact.value)));
      detailsBody.appendChild(make('p', null, '事实版本：v' + text(fact.version)));
      detailsBody.appendChild(make('p', null, '绑定方案：' + text(fact.artifact_id)));
      detailsBody.appendChild(make('p', null, '事实记录：' + text(fact.id)));
      detailsBody.appendChild(make('p', null, '确认人 / 时间：' + text(fact.actor) + ' / ' + text(fact.time)));
      detailsBody.appendChild(make('p', null, '证据 ID：' + ((fact.evidence || []).join('、') || '—')));
      if (fact.verification_reasons && fact.verification_reasons.length) detailsBody.appendChild(make('p', null, '复核原因：' + fact.verification_reasons.map(readableBlocker).join('；')));
    } else detailsBody.appendChild(make('p', 'wb-muted', '暂无方案范围事实记录。'));
    details.appendChild(detailsBody); body.appendChild(details);
    return body;
  }

  function renderDetail(detail) {
    const view = $('detail-view'); while (view.firstChild) view.removeChild(view.firstChild); view.hidden = false; $('detail-empty').hidden = true;
    const opportunity = detail.opportunity, life = detail.lifecycle, assessment = detail.commercial_assessment || {};
    const hero = make('div', 'wb-hero'); const heading = make('div'); heading.appendChild(make('div', 'wb-eyebrow', text(detail.account.company_name))); const scope = latestFact(life, 'solution_scope'); heading.appendChild(make('h2', null, scopeVerification(scope) === 'current' ? text(scope.value) : (scope ? '方案范围待复核' : text(opportunity.name || opportunity.core_need)))); heading.appendChild(make('p', 'wb-muted', '主账修订号 ' + text(life.revision) + ' · 负责人 ' + text(life.owner))); hero.appendChild(heading);
    const statuses = make('div', 'wb-statuses'); statuses.appendChild(make('span', 'wb-tag wb-tag-primary', stageLabel(life.current_stage_id))); statuses.appendChild(make('span', 'wb-tag', statusLabel(life.status))); hero.appendChild(statuses); view.appendChild(hero);
    const scoreStrip = make('div', 'wb-score-strip');
    [['综合参考分', assessment.overall_opportunity_score ?? opportunity.score], ['赢单可能性', assessment.win_likelihood_score], ['商机价值', assessment.deal_attractiveness_score], ['交付信心', assessment.delivery_confidence_score]].forEach(([label, score]) => {
      const cell = make('div', 'wb-score'); cell.appendChild(make('span', null, label)); cell.appendChild(make('strong', null, text(score) + ' / 100')); scoreStrip.appendChild(cell);
    }); view.appendChild(scoreStrip);
    const help = make('details', 'wb-disclosure'); help.appendChild(make('summary', null, '评分口径与原始名称')); help.appendChild(make('p', 'wb-muted', '启发式参考，不是统计成交概率。未知40表示缺少信息。原始名称：' + text(opportunity.name))); view.appendChild(help);
    view.appendChild(section('方案范围', renderScopeSummary(life)));

    const columns = make('div', 'wb-columns'); const main = make('div'); const side = make('div');
    const assessmentRows = (assessment.dimensions || []).map((d) => [d.label, ratingLabel(d.rating), d.score, evidenceLabel(d.evidence_status), (d.evidence_refs || []).join(', ') || '—', d.rationale]);
    const assessBody = make('details', 'wb-disclosure'); assessBody.appendChild(make('summary', null, '查看18项判断依据')); assessBody.appendChild(assessmentRows.length ? table(['判断维度', '评级', '分值', '依据状态', '证据 ID', '说明'], assessmentRows) : make('p', 'wb-muted', '暂无评分维度'));
    const radarBody = make('div'); const radar = make('iframe', 'wb-radar-frame'); radar.title = '判断维度雷达图';
    const radarTabs = make('div', 'wb-form-actions');
    const selectRadar = category => { radar.dataset.category = category; radar.src = '/radar/' + encodeURIComponent(opportunity.id) + '?category=' + category + '&theme=' + document.documentElement.dataset.theme; Array.from(radarTabs.children).forEach(tab => tab.setAttribute('aria-pressed', String(tab.dataset.category === category))); };
    [['win_likelihood', '赢单可能性'], ['deal_attractiveness', '商机价值'], ['delivery_confidence', '交付信心']].forEach(([category,label]) => { const tab = button(label, 'wb-btn-secondary wb-btn-small', () => selectRadar(category)); tab.dataset.category = category; radarTabs.appendChild(tab); });
    selectRadar('win_likelihood'); radarBody.appendChild(radarTabs); radarBody.appendChild(radar); radarBody.appendChild(assessBody);
    main.appendChild(section('判断雷达与评分依据', radarBody, [button('打开完整雷达报告', 'wb-btn-secondary wb-btn-small', () => window.open('/report/' + encodeURIComponent(opportunity.id) + '?theme=' + document.documentElement.dataset.theme, '_blank', 'noopener'))]));
    const historyRows = [...(detail.assessment_history || [])].reverse().map((item) => {
      const dimensions = Object.fromEntries((item.dimensions || []).map((dimension) => [dimension.dimension_id, dimension]));
      const changed = Object.entries(item.deltas && item.deltas.dimensions || {}).filter((entry) => entry[1] && entry[1].delta);
      const changedText = changed.length ? changed.map(([dimensionId, delta]) => { const current = dimensions[dimensionId] || {}; const refs = (current.evidence_refs || []).join(', '); return (current.label || dimensionId) + '：' + ratingLabel(delta.from_rating) + ' → ' + ratingLabel(delta.to_rating) + ' (' + (delta.delta > 0 ? '+' : '') + delta.delta + ')' + (refs ? ' · ' + refs : ''); }).join('；') : '—';
      const time = make('span', 'wb-time', new Date(item.created_at).toLocaleString('zh-CN', {month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hour12:false})); time.title = item.created_at;
      const change = make('details'); change.appendChild(make('summary', null, changed.length ? changed.length + ' 项变化' : '无评级变化')); change.appendChild(make('p', null, changedText));
      const delta = item.deltas && item.deltas.overall_opportunity_score && item.deltas.overall_opportunity_score.delta;
      return [time, item.overall_opportunity_score + (delta ? ' (' + (delta > 0 ? '+' : '') + delta + ')' : ''), confidenceLabel(item.confidence_level), item.unanswered_critical_count, change];
    });
    main.appendChild(section('评分历史与相邻变化', historyRows.length ? table(['时间', '总评分', '可信度', '待确认关键项', '维度变化'], historyRows) : make('p', 'wb-muted', '暂无历史评估记录。')));
    const competitorRows = (life.competitors || []).map((c) => { const price = c.price_amount != null ? c.price_amount + ' ' + text(c.currency) + (c.status === 'reported' ? '（客户转述）' : '') : '—'; const versions = make('details'); versions.appendChild(make('summary', null, (c.history || []).length + ' 次记录')); (c.history || []).forEach(h => versions.appendChild(make('p', null, 'v' + text(h.version) + ' · ' + evidenceLabel(h.status) + ' · ' + text(h.price_amount) + ' ' + text(h.currency) + ' · ' + (h.evidence || []).join(', ')))); return [c.name, c.position, evidenceLabel(c.status), price, 'v' + text(c.version), (c.response || c.weaknesses || []).toString(), (c.evidence || []).join(', ') || '—', versions]; });
    main.appendChild(section('竞争台账', competitorRows.length ? table(['对手', '定位', '来源状态', '价格线索', '版本', '响应 / 弱点', '证据 ID', '历史'], competitorRows) : make('p', 'wb-muted', '尚无结构化竞争记录。客户材料中的推断不会自动成为台账。')));
    const reviewRows = (life.reviews || []).map((r) => [r.title, statusLabel(r.status), r.owner, r.due_date, verifyLabel(r.verification_status)]);
    main.appendChild(section('客户评审与闭环', reviewRows.length ? table(['评审项', '状态', '负责人', '截止', '当前校验'], reviewRows) : make('p', 'wb-muted', '尚无客户评审记录。')));
    const kindLabels = {solution:'方案',quote:'报价',negotiation:'谈判',contract:'合同',handoff:'交接'};
    const artifactRows = (life.artifacts || []).map(a => { const binding = a.metadata && a.metadata.presales_binding; return [a.id, kindLabels[a.kind] || a.kind, 'v' + a.version, verifyLabel(a.validity), binding ? binding.project_id + ' / ' + binding.delivery_id + ' / ' + binding.content_id : '本地工作稿', (a.dependencies || []).map(d => d.artifact_id).join(', ') || '—', scopeReviewCell(a)]; });
    main.appendChild(section('方案与商务成果', artifactRows.length ? table(['成果', '类型', '版本', '当前核验', '售前绑定', '上游版本', '范围内容复核'], artifactRows) : make('p', 'wb-muted', '尚未登记成果。实际文件通过 CLI 回收并核验。')));
    const contracts = (life.contracts || []).map(c => [c.contract_id || c.id, c.artifact_id, c.signing_date, text(c.amount) + ' ' + text(c.currency)]);
    if (contracts.length) main.appendChild(section('签署登记', table(['记录', '合同成果', '签署日期', '金额'], contracts)));
    const actionRows = (life.actions || []).map(a => [a.title, statusLabel(a.status), a.owner, a.due_date, a.result || '—']);
    main.appendChild(section('跟进行动', actionRows.length ? table(['行动', '状态', '负责人', '截止', '结果'], actionRows) : make('p', 'wb-muted', '暂无跟进行动。')));
    const history = make('div', 'wb-timeline'); (life.history || []).forEach((event) => { const item = make('div', 'wb-timeline-item'); item.appendChild(make('strong', null, stageLabel(event.from_stage) + ' → ' + stageLabel(event.to_stage))); item.appendChild(make('span', null, text(event.reason) + ' · ' + text(event.time))); history.appendChild(item); });
    main.appendChild(section('阶段历史', history.childNodes.length ? history : make('p', 'wb-muted', '尚未发生正式阶段推进。')));
    columns.appendChild(main);

    const evidenceIds = (detail.evidence || []).map((ev) => ev.id); const evidenceHint = make('div', 'wb-form-hint', '当前证据：' + (evidenceIds.length ? evidenceIds.join(', ') : '暂无') + '。写入时请填写已有证据 ID或本次新证据 ID。');
    side.appendChild(formPanel('新增拜访 / 反馈', (form) => {
      form.appendChild(field('客户 / 账号', 'account', 'text', detail.account.company_name, { required: true })); form.appendChild(field('操作人', 'operator', 'text', life.owner || '', { required: true })); form.appendChild(field('证据 ID', 'evidence_id', 'text', 'ev-' + Date.now().toString(36), { required: true })); form.appendChild(field('拜访或反馈内容', 'content', 'textarea', '', { required: true, full: true, placeholder: '记录客户原话、评审意见、采购变化或下一步约定' })); form.appendChild(evidenceHint.cloneNode(true));
      const submit = addSubmit(form); form.addEventListener('submit', async (event) => { event.preventDefault(); const payload = { request_id: requestIdFor(form), opportunity_id: opportunity.id, expected_revision: life.revision, actor: valueOf(form, 'operator'), account_hint: valueOf(form, 'account'), materials: [{ evidence_id: valueOf(form, 'evidence_id'), type: 'visit_note', name: '工作台拜访/反馈', content: valueOf(form, 'content') }] }; try { await write('/api/analyze', payload, submit); } catch (_) {} });
    }));
    side.appendChild(formPanel('新增竞争情报', (form) => {
      const competitors = life.competitors || []; form.appendChild(field('操作人', 'operator', 'text', life.owner || '', { required: true })); form.appendChild(field('竞争对手记录', 'competitor_id', 'select', '', { choices: [['', '新增竞争对手'], ...competitors.map((c) => [c.competitor_id, c.name + ' / v' + c.version])] })); form.appendChild(field('竞争对手', 'name', 'text', '', { required: true })); form.appendChild(field('客户侧定位', 'position', 'text', '', { required: true })); form.appendChild(field('来源状态', 'status', 'select', 'reported', { choices: [['confirmed', '已确认'], ['reported', '客户转述'], ['unknown', '未知']]})); form.appendChild(field('价格线索', 'price_amount', 'number', '', {})); form.appendChild(field('币种', 'currency', 'text', 'CNY', {})); form.appendChild(field('优势（逗号分隔）', 'strengths', 'textarea', '', { required: true, full: true })); form.appendChild(field('弱点 / 我方应对（逗号分隔）', 'weaknesses', 'textarea', '', { required: true, full: true })); form.appendChild(field('我方响应策略', 'response', 'textarea', '', { required: true, full: true })); form.appendChild(field('证据 ID（逗号分隔）', 'evidence', 'text', '', { required: true, full: true }));
      const competitorSelect = form.elements.namedItem('competitor_id'); competitorSelect.addEventListener('change', () => { const selected = competitors.find((c) => c.competitor_id === competitorSelect.value); if (!selected) return; form.elements.namedItem('name').value = selected.name || ''; form.elements.namedItem('position').value = selected.position || ''; form.elements.namedItem('status').value = selected.status || 'reported'; form.elements.namedItem('price_amount').value = selected.price_amount == null ? '' : selected.price_amount; form.elements.namedItem('currency').value = selected.currency || 'CNY'; form.elements.namedItem('strengths').value = (selected.strengths || []).join(', '); form.elements.namedItem('weaknesses').value = (selected.weaknesses || []).join(', '); form.elements.namedItem('response').value = selected.response || ''; form.elements.namedItem('evidence').value = (selected.evidence || []).join(', '); });
      const submit = addSubmit(form); form.addEventListener('submit', async (event) => { event.preventDefault(); const refs = evidenceRefs(form); if (!refs.length) { notice('竞争情报必须绑定已有证据 ID。', 'error'); return; } const splitText = (name) => valueOf(form, name).split(/[,，\n]/).map((x) => x.trim()).filter(Boolean); const op = { type: 'record_competitor', competitor_id: valueOf(form, 'competitor_id') || 'cmp-' + Date.now().toString(36), name: valueOf(form, 'name'), position: valueOf(form, 'position'), status: valueOf(form, 'status'), strengths: splitText('strengths'), weaknesses: splitText('weaknesses'), response: valueOf(form, 'response'), evidence: refs }; const price = valueOf(form, 'price_amount'); if (price) op.price_amount = Number(price); op.currency = valueOf(form, 'currency'); try { await write('/api/manage', managePayload(detail, [op], form), submit); } catch (_) {} });
    }));
    side.appendChild(formPanel('新增跟进行动', (form) => {
      form.appendChild(field('操作人', 'operator', 'text', life.owner || '', { required: true })); form.appendChild(field('行动事项', 'title', 'text', '', { required: true, full: true })); form.appendChild(field('负责人', 'owner', 'text', life.owner || '', { required: true })); form.appendChild(field('截止日期', 'due_date', 'date', '', { required: true }));
      const submit = addSubmit(form); form.addEventListener('submit', async (event) => { event.preventDefault(); const op = { type: 'add_action', title: valueOf(form, 'title'), owner: valueOf(form, 'owner'), due_date: valueOf(form, 'due_date') }; try { await write('/api/manage', managePayload(detail, [op], form), submit); } catch (_) {} });
    }));
    side.appendChild(formPanel('完成跟进行动', (form) => {
      const actions = (life.actions || []).filter((a) => a.status === 'open'); form.appendChild(field('操作人', 'operator', 'text', life.owner || '', { required: true })); form.appendChild(field('待完成行动', 'action_id', 'select', actions[0] ? actions[0].id : '', { choices: actions.length ? actions.map((a) => [a.id, a.title]) : [['', '暂无待完成行动']] })); form.appendChild(field('完成结果', 'result', 'textarea', '', { required: true, full: true })); form.appendChild(field('证据 ID（逗号分隔）', 'evidence', 'text', '', { required: true, full: true }));
      const submit = addSubmit(form); form.addEventListener('submit', async (event) => { event.preventDefault(); const refs = evidenceRefs(form); if (!valueOf(form, 'action_id') || !refs.length) { notice('完成行动必须选择行动并绑定已有证据。', 'error'); return; } const op = { type: 'complete_action', action_id: valueOf(form, 'action_id'), result: valueOf(form, 'result'), evidence: refs }; try { await write('/api/manage', managePayload(detail, [op], form), submit); } catch (_) {} });
    }));
    side.appendChild(formPanel('客户评审记录', (form) => {
      const solutions = (life.artifacts || []).filter((a) => a.kind === 'solution' && a.validity === 'valid'); form.appendChild(field('操作人', 'operator', 'text', life.owner || '', { required: true })); form.appendChild(field('评审标题', 'title', 'text', '', { required: true, full: true })); form.appendChild(field('方案版本', 'artifact_id', 'select', solutions[0] ? solutions[0].id : '', { choices: solutions.length ? solutions.map((a) => [a.id, a.document_id + ' / v' + a.version]) : [['', '暂无当前有效方案']] })); form.appendChild(field('需求 ID（逗号分隔）', 'requirement_ids', 'text', '', { required: true, full: true })); form.appendChild(field('负责人', 'owner', 'text', life.owner || '', { required: true })); form.appendChild(field('截止日期', 'due_date', 'date', '', { required: true })); form.appendChild(field('是否阻塞推进', 'blocking', 'select', 'true', { choices: [['true', '是'], ['false', '否']] })); form.appendChild(field('证据 ID（逗号分隔）', 'evidence', 'text', '', { required: true, full: true }));
      const submit = addSubmit(form); form.addEventListener('submit', async (event) => { event.preventDefault(); const refs = evidenceRefs(form); const artifactId = valueOf(form, 'artifact_id'); if (!artifactId || !refs.length) { notice('评审必须绑定当前有效方案和已有证据。', 'error'); return; } const op = { type: 'record_review', review_id: 'review-' + Date.now().toString(36), title: valueOf(form, 'title'), artifact_id: artifactId, requirement_ids: valueOf(form, 'requirement_ids').split(',').map((x) => x.trim()).filter(Boolean), owner: valueOf(form, 'owner'), due_date: valueOf(form, 'due_date'), blocking: valueOf(form, 'blocking') === 'true', evidence: refs }; try { await write('/api/manage', managePayload(detail, [op], form), submit); } catch (_) {} });
    }));
    side.appendChild(formPanel('评审闭环 / 重新打开', (form) => {
      const reviews = life.reviews || [], solutions = (life.artifacts || []).filter((a) => a.kind === 'solution' && a.validity === 'valid');
      form.appendChild(field('操作人', 'operator', 'text', life.owner || '', { required: true })); form.appendChild(field('评审记录', 'review_id', 'select', reviews[0] ? reviews[0].id : '', { choices: reviews.length ? reviews.map((r) => [r.id, r.title + ' / ' + statusLabel(r.status)]) : [['', '暂无评审记录']] }));
      form.appendChild(field('动作', 'review_action', 'select', 'resolve_review', { choices: [['resolve_review', '按当前方案解决'], ['reopen_review', '重新打开']] }));
      form.appendChild(field('当前方案', 'artifact_id', 'select', solutions[0] ? solutions[0].id : '', { choices: solutions.length ? solutions.map((a) => [a.id, a.document_id + ' / v' + a.version]) : [['', '暂无当前有效方案']] }));
      form.appendChild(field('解决说明 / 重新打开原因', 'resolution', 'textarea', '', { required: true, full: true }));
      form.appendChild(field('证据 ID（逗号分隔）', 'evidence', 'text', '', { required: true, full: true }));
      const submit = addSubmit(form); form.addEventListener('submit', async (event) => {
        event.preventDefault(); const refs = evidenceRefs(form), reviewId = valueOf(form, 'review_id'); if (!reviewId || !refs.length) { notice('评审闭环必须绑定评审记录和已有证据。', 'error'); return; }
        const action = valueOf(form, 'review_action'); const op = action === 'resolve_review' ? { type: action, review_id: reviewId, artifact_id: valueOf(form, 'artifact_id'), resolution: valueOf(form, 'resolution'), evidence: refs } : { type: action, review_id: reviewId, reason: valueOf(form, 'resolution'), evidence: refs };
        try { await write('/api/manage', managePayload(detail, [op], form), submit); } catch (_) {}
      });
    }));
    side.appendChild(formPanel('方案范围确认', (form) => {
      const scopeFact = latestFact(life, 'solution_scope');
      const solutions = validSolutions(life);
      const choices = solutions.length ? solutions.map((artifact) => [artifact.id, (artifact.document_id || artifact.id) + ' / v' + artifact.version]) : [['', '暂无当前有效方案']];
      form.appendChild(field('操作人', 'operator', 'text', life.owner || '', { required: true }));
      form.appendChild(field('当前有效方案', 'scope_artifact_id', 'select', scopeFact && solutions.some((artifact) => artifact.id === scopeFact.artifact_id) ? scopeFact.artifact_id : (solutions[0] ? solutions[0].id : ''), { choices: choices, required: true }));
      form.appendChild(field('方案范围', 'scope_text', 'textarea', scopeFact && typeof scopeFact.value === 'string' ? scopeFact.value : '', { required: true, full: true, placeholder: '填写实际阅读并确认的方案范围' }));
      form.appendChild(field('证据 ID（逗号分隔）', 'scope_evidence', 'text', '', { required: true, full: true }));
      form.appendChild(make('div', 'wb-form-hint', solutions.length ? '必须绑定当前有效方案，并填写已有证据 ID；重新确认会形成新的范围事实版本。' : '当前没有可绑定的有效方案，请先通过 CLI 登记并核验方案文件。'));
      const submit = addSubmit(form, '确认范围');
      form.addEventListener('submit', async (event) => {
        event.preventDefault();
        const artifactId = valueOf(form, 'scope_artifact_id');
        const scopeText = valueOf(form, 'scope_text');
        const refs = evidenceRefs(form, 'scope_evidence');
        if (!solutions.some((artifact) => artifact.id === artifactId) || !scopeText || !refs.length) {
          notice('方案范围确认必须绑定当前有效方案、填写范围文本并关联已有证据。', 'error');
          return;
        }
        const op = { type: 'confirm_fact', fact_id: 'solution_scope', value: scopeText, artifact_id: artifactId, evidence: refs };
        try { await write('/api/manage', managePayload(detail, [op], form), submit); } catch (_) {}
      });
    }));
    side.appendChild(formPanel('确认评分依据', (form) => {
      const dimensions = assessment.dimensions || []; form.appendChild(field('操作人', 'operator', 'text', life.owner || '', { required: true })); form.appendChild(field('判断维度', 'dimension_id', 'select', dimensions[0] ? dimensions[0].dimension_id : '', { choices: dimensions.map((d) => [d.dimension_id, d.label]) })); form.appendChild(field('评级', 'rating', 'select', 'medium', { choices: [['strong', '强'], ['medium', '中'], ['weak', '弱'], ['unknown', '未知']] })); form.appendChild(field('商务确认说明', 'answer_text', 'textarea', '', { required: true, full: true })); form.appendChild(field('已有证据 ID（逗号分隔）', 'evidence', 'text', '', { required: true, full: true }));
      const submit = addSubmit(form); form.addEventListener('submit', async (event) => { event.preventDefault(); const refs = evidenceRefs(form); if (!refs.length) { notice('评分确认必须绑定已有证据。', 'error'); return; } const payload = { request_id: requestIdFor(form), opportunity_id: opportunity.id, expected_revision: life.revision, actor: valueOf(form, 'operator'), sales_confirmation_answers: [{ dimension_id: valueOf(form, 'dimension_id'), rating: valueOf(form, 'rating'), answer_text: valueOf(form, 'answer_text'), answered_by: valueOf(form, 'operator'), evidence_refs: refs }] }; try { await write('/api/analyze', payload, submit); } catch (_) {} });
    }));
    const stages = Object.entries(STAGE_LABELS);
    side.appendChild(formPanel('阶段推进', (form) => { form.appendChild(field('操作人', 'operator', 'text', life.owner || '', { required: true })); form.appendChild(field('目标阶段', 'to_stage', 'select', life.current_stage_id, { choices: stages })); form.appendChild(field('推进理由', 'reason', 'textarea', '', { required: true, full: true })); form.appendChild(field('证据 ID（逗号分隔）', 'evidence', 'text', '', { required: true, full: true })); const submit = addSubmit(form); form.addEventListener('submit', async (event) => { event.preventDefault(); const refs = evidenceRefs(form); if (!refs.length) { notice('阶段推进必须绑定已有证据。', 'error'); return; } try { await write('/api/manage', managePayload(detail, [{ type: 'transition', to_stage: valueOf(form, 'to_stage'), reason: valueOf(form, 'reason'), evidence: refs }], form), submit); } catch (_) {} }); }));
    columns.appendChild(side); view.appendChild(columns);
  }

  async function loadDetail(id) { const result = await api('/api/opportunity/' + encodeURIComponent(id)); state.detail = result.detail; renderDetail(state.detail); }
  async function selectOpportunity(id) { state.selectedId = id; await loadList(); try { await loadDetail(id); } catch (error) { notice(error.message, 'error'); } }
  async function refreshCurrent() { await loadList(); if (state.selectedId) await loadDetail(state.selectedId); notice('已刷新当前主账', 'success'); }
  function startNew() {
    notice('');
    state.selectedId = null; state.detail = null; $('detail-empty').hidden = true; const view = $('detail-view'); while (view.firstChild) view.removeChild(view.firstChild); view.hidden = false;
    const intro = make('div', 'wb-hero'); const copy = make('div'); copy.appendChild(make('div', 'wb-eyebrow', '第一次拜访')); copy.appendChild(make('h2', null, '建立新的商机主账')); copy.appendChild(make('p', 'wb-muted', '先保存一条有来源的拜访记录，后续每次反馈都在同一商机修订号上推进。')); intro.appendChild(copy); view.appendChild(intro);
    view.appendChild(formPanel('第一次拜访 / 新建商机', (form) => {
      form.appendChild(field('客户 / 账号', 'account', 'text', '', { required: true })); form.appendChild(field('操作人 / 负责人', 'operator', 'text', '', { required: true })); form.appendChild(field('证据 ID', 'evidence_id', 'text', 'ev-' + Date.now().toString(36), { required: true })); form.appendChild(field('拜访记录', 'content', 'textarea', '', { required: true, full: true, placeholder: '记录客户原话、现场问题和下一步约定' }));
      const submit = addSubmit(form); form.addEventListener('submit', async (event) => { event.preventDefault(); const payload = { request_id: requestIdFor(form), expected_revision: 0, actor: valueOf(form, 'operator'), owner: valueOf(form, 'operator'), account_hint: valueOf(form, 'account'), materials: [{ evidence_id: valueOf(form, 'evidence_id'), type: 'visit_note', name: '工作台第一次拜访', content: valueOf(form, 'content') }] }; try { await write('/api/analyze', payload, submit); } catch (_) {} });
    }, true));
  }
  function setup() {
    $('theme-toggle').addEventListener('click', () => { const dark = document.documentElement.dataset.theme === 'dark'; document.documentElement.dataset.theme = dark ? 'light' : 'dark'; $('theme-toggle').textContent = dark ? '切换深色' : '切换浅色'; document.querySelectorAll('.wb-radar-frame').forEach(frame => { frame.src = '/radar/' + encodeURIComponent(state.selectedId) + '?category=' + frame.dataset.category + '&theme=' + document.documentElement.dataset.theme; }); });
    $('refresh-list').addEventListener('click', () => refreshCurrent().catch((error) => notice(error.message, 'error')));
    $('new-opportunity').addEventListener('click', startNew);
    loadList().then(() => { const requestedId = new URLSearchParams(location.search).get('opportunity_id'); if (requestedId) return selectOpportunity(requestedId); }).catch((error) => notice(error.message, 'error'));
  }
  setup();
}());
