(function () {
 'use strict';
 const $ = id => document.getElementById(id);
 const labels = {overview:'工作概览',resources:'检测与资源',receipt:'样品签收'};
 const draftKey = 'enterprise-huixin-receipt-draft-v1';
 const fields = ['receiver','receivedDate','quantity','condition','reason','notes'];
 const names = {receiver:'签收人',receivedDate:'签收日期',quantity:'实收数量',condition:'包装与样品状态',reason:'差异原因'};
 const series = {dates:['10/23','10/24','10/25','10/26','10/27','10/28','10/29'],received:[24,32,21,38,29,42,34],completed:[21,27,19,31,26,35,30]};
 const tasks = [
  {id:'WT-2026-1029-021',sample:'建筑用砂 · 河砂',customer:'华东建筑材料有限公司',quantity:'8 袋',state:'待签收',route:'receipt',action:'办理签收'},
  {id:'WT-2026-1029-022',sample:'碎石 · 连续粒级',customer:'江南工程检测中心',quantity:'6 袋',state:'待资源核对',route:'resources',action:'核对资源'},
  {id:'WT-2026-1029-023',sample:'机制砂 · 石灰岩',customer:'申城建材试验室',quantity:'4 袋',state:'待方法核对',route:'resources',action:'核对方法'}
 ];
 let errorState = {}, attempted = false, dirty = false, failedOnce = false, confirmed = false, returnFocus = null;
 const esc = value => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 function route() {
  let name = location.hash.slice(1);
  if (name === 'main') return;
  if (!labels[name]) { name = 'overview'; history.replaceState(null,'','#overview'); }
  Object.keys(labels).forEach(key => { $(key).hidden = key !== name; });
  $('route-label').textContent = labels[name];
  document.querySelectorAll('.hx-route-links a,.hx-mobile-routes a').forEach(link => {
   if (link.hash === '#' + name) link.setAttribute('aria-current','page'); else link.removeAttribute('aria-current');
  });
  document.title = labels[name] + ' · 慧新 LIMS';
 }
 window.addEventListener('hashchange',route); route();
 function syncAppearance() {
  const config = EnterpriseDesign.get().requested;
  document.querySelectorAll('[data-brand]').forEach(button => button.setAttribute('aria-pressed',String(button.dataset.brand === config.brand)));
  $('theme-toggle').textContent = config.theme === 'dark' ? '浅色' : '深色';
  $('theme-toggle').setAttribute('aria-label',config.theme === 'dark' ? '切换至浅色主题' : '切换至深色主题');
 }
 document.querySelectorAll('[data-brand]').forEach(button => button.addEventListener('click',() => { EnterpriseDesign.apply({brand:button.dataset.brand}); }));
 $('theme-toggle').addEventListener('click',() => EnterpriseDesign.apply({theme:EnterpriseDesign.get().requested.theme === 'dark' ? 'light' : 'dark'}));
 window.addEventListener('ui-design-change',syncAppearance); syncAppearance();
 function renderTasks() {
  const query = $('task-search').value.trim().toLowerCase();
  const rows = tasks.filter((task,index) => !(confirmed && index === 0)).filter(task => (task.sample + task.id + task.customer).toLowerCase().includes(query));
  $('task-rows').innerHTML = rows.map(task => '<tr><td><strong>'+esc(task.sample)+'</strong><span class="hx-cell-meta">'+esc(task.id)+'</span></td><td>'+esc(task.customer)+'</td><td class="hx-num">'+esc(task.quantity)+'</td><td><span class="hx-tag hx-tag-warning">'+esc(task.state)+'</span></td><td class="hx-end"><a class="hx-link" href="#'+task.route+'">'+task.action+' →</a></td></tr>').join('');
  $('task-count').textContent = rows.length + ' 条任务'; $('task-empty').hidden = rows.length > 0;
  $('metric-pending').innerHTML = (confirmed ? '2' : '3') + ' <small>批</small>';
 }
 $('task-search').addEventListener('input',renderTasks);
 function clearFilter() { $('task-search').value = ''; renderTasks(); $('task-search').focus(); }
 $('clear-filter').addEventListener('click',clearFilter); $('empty-clear-filter').addEventListener('click',clearFilter); renderTasks();
 function renderChart() {
  const xs = series.dates.map((_,i) => 58 + i * 148), y = n => 214 - n / 50 * 180;
  let svg = '';
  for (let value = 0; value <= 50; value += 10) svg += '<line class="hx-chart-grid" x1="58" y1="'+y(value)+'" x2="946" y2="'+y(value)+'"/><text class="hx-chart-label" x="36" y="'+(y(value)+4)+'" text-anchor="end">'+value+'</text>';
  svg += '<text class="hx-chart-label" x="14" y="16">份</text>';
  ['received','completed'].forEach((key,index) => { svg += '<polyline class="hx-chart-line '+(index ? 'hx-chart-line-secondary' : '')+'" points="'+series[key].map((n,i)=>xs[i]+','+y(n)).join(' ')+'"/>'; });
  series.dates.forEach((date,i) => { svg += '<text class="hx-chart-label" x="'+xs[i]+'" y="246" text-anchor="middle">'+date+'</text><circle class="hx-chart-point" cx="'+xs[i]+'" cy="'+y(series.received[i])+'" r="4" tabindex="0" role="img" aria-label="'+date+' 接收 '+series.received[i]+'份，完成 '+series.completed[i]+'份"><title>'+date+' · 接收 '+series.received[i]+'份 / 完成 '+series.completed[i]+'份</title></circle>'; });
  $('weekly-chart').insertAdjacentHTML('beforeend',svg);
  $('chart-data').innerHTML = series.dates.map((date,i) => '<tr><th scope="row">'+date+'</th><td class="hx-end">'+series.received[i]+'</td><td class="hx-end">'+series.completed[i]+'</td></tr>').join('');
  $('metric-received').innerHTML = series.received.reduce((a,b)=>a+b,0) + ' <small>份</small>';
  $('metric-completed').innerHTML = series.completed.reduce((a,b)=>a+b,0) + ' <small>份</small>';
 }
 renderChart();
 const tabs = [...document.querySelectorAll('[role="tab"]')];
 function selectTab(tab) { tabs.forEach(item => { const selected = tab === item; item.setAttribute('aria-selected',String(selected)); item.tabIndex = selected ? 0 : -1; $(item.getAttribute('aria-controls')).hidden = !selected; }); }
 tabs.forEach((tab,i) => {
  tab.addEventListener('click',()=>selectTab(tab));
  tab.addEventListener('keydown',event => { let n; if (event.key === 'ArrowRight') n=(i+1)%tabs.length; if (event.key === 'ArrowLeft') n=(i+tabs.length-1)%tabs.length; if (event.key === 'Home') n=0; if (event.key === 'End') n=tabs.length-1; if (n !== undefined) { event.preventDefault(); selectTab(tabs[n]); tabs[n].focus(); } });
 });
 function showDialog(dialog,trigger) { returnFocus = trigger || document.activeElement; EnterpriseDesign.transfer(dialog); dialog.showModal(); }
 function closeDialog(dialog) { dialog.close(); }
 document.querySelectorAll('[data-close]').forEach(button => button.addEventListener('click',()=>closeDialog($(button.dataset.close))));
 ['mobile-nav','confirm-dialog'].forEach(id => $(id).addEventListener('close',() => { const target=returnFocus; if(target && target.isConnected) target.focus(); }));
 $('open-menu').addEventListener('click',event=>showDialog($('mobile-nav'),event.currentTarget));
 document.querySelectorAll('.hx-mobile-routes a').forEach(link=>link.addEventListener('click',()=>closeDialog($('mobile-nav'))));
 window.addEventListener('resize',()=>{ if (window.innerWidth>760 && $('mobile-nav').open) $('mobile-nav').close(); });
 // Transfer resolved values again when a body-mounted modal is open during a switch.
 window.addEventListener('ui-design-change',()=>document.querySelectorAll('.hx-dialog').forEach(dialog=>EnterpriseDesign.transfer(dialog)));
 function values() { return Object.fromEntries(fields.map(name=>[name,$(name).value])); }
 function needsReason(data) { return (data.quantity !== '' && Number(data.quantity) !== 8) || data.condition === 'damaged'; }
 function dependent() { const needed=needsReason(values()); $('discrepancy-section').hidden=!needed; $('reason').required=needed; if (!needed) delete errorState.reason; }
 function validate() {
  const data=values(), errors={};
  if (!data.receiver.trim()) errors.receiver='请填写签收人。';
  if (!data.receivedDate || !$('receivedDate').validity.valid) errors.receivedDate='请选择有效的签收日期。';
  if (data.quantity === '' || !Number.isInteger(Number(data.quantity)) || Number(data.quantity)<0 || Number(data.quantity)>8) errors.quantity='实收数量须为 0–8 的整数。';
  if (!['intact','damaged'].includes(data.condition)) errors.condition='请选择包装与样品状态。';
  if (needsReason(data) && data.reason.trim().length<4) errors.reason='请填写至少 4 个字的差异原因。';
  return errors;
 }
 function displayErrors() {
  Object.keys(names).forEach(name=>{ const message=errorState[name], field=$(name); field.setAttribute('aria-invalid',String(!!message)); $(name+'-error').hidden=!message; $(name+'-error').textContent=message || ''; });
  $('error-summary').hidden=Object.keys(errorState).length===0;
  $('error-links').innerHTML=Object.keys(errorState).map(name=>'<li><a href="#'+name+'" data-error-field="'+name+'">'+names[name]+'</a></li>').join('');
 }
 $('error-links').addEventListener('click',event=>{ const link=event.target.closest('[data-error-field]'); if (link) { event.preventDefault(); $(link.dataset.errorField).focus(); } });
 $('receipt-form').addEventListener('input',()=>{ dirty=true; dependent(); if (attempted) {errorState=validate();displayErrors();} $('draft-state').textContent='有未保存的修改'; });
 $('receipt-form').addEventListener('change',()=>{ dependent(); if (attempted) {errorState=validate();displayErrors();} });
 function saveDraft() {
  try { localStorage.setItem(draftKey,JSON.stringify({version:1,values:values(),savedAt:new Date().toISOString()})); dirty=false; $('draft-state').textContent='草稿已保存在本浏览器'; return true; }
  catch (_) { $('draft-state').textContent='草稿保存失败：浏览器存储不可用，请保留当前页面后重试。'; return false; }
 }
 $('save-draft').addEventListener('click',saveDraft);
 function loadDraft(automatic) {
  try {
   const raw=localStorage.getItem(draftKey); if (!raw) { if(!automatic)$('draft-state').textContent='没有可载入的草稿'; return; }
   const draft=JSON.parse(raw); if (draft.version!==1 || !draft.values || typeof draft.values!=='object' || Array.isArray(draft.values)) throw new Error('invalid draft');
   fields.forEach(name=>{ if(typeof draft.values[name]==='string') $(name).value=draft.values[name]; });
   dirty=false; dependent(); errorState={}; attempted=false; displayErrors(); $('draft-state').textContent='已载入本浏览器草稿';
  } catch (_) { $('draft-state').textContent='草稿读取失败，当前输入已保留。'; }
 }
 $('reload-draft').addEventListener('click',()=>{
  if (dirty && !window.confirm('载入草稿会替换当前未保存的修改，是否继续？')) return;
  loadDraft(false);
 });
 loadDraft(true); dependent();
 function receiptData() { const data=values(); data.receiver=data.receiver.trim(); data.quantity=Number(data.quantity); data.reason=needsReason(data)?data.reason.trim():''; return data; }
 $('receipt-form').addEventListener('submit',event=>{
  event.preventDefault(); attempted=true; dependent(); errorState=validate(); displayErrors();
  if (Object.keys(errorState).length) { $('error-summary').focus(); return; }
  const data=receiptData();
  $('confirm-facts').innerHTML=[['签收人',data.receiver],['签收日期',data.receivedDate],['实收数量',data.quantity+' 袋'],['样品状态',data.condition==='intact'?'包装完好':'包装破损 / 样品异常'],...(needsReason(data)?[['差异原因',data.reason]]:[])].map(([name,value])=>'<div><dt>'+name+'</dt><dd>'+esc(value)+'</dd></div>').join('');
  $('submit-failure').hidden=true; $('confirm-submit').textContent='确认签收'; showDialog($('confirm-dialog'),$('review-receipt'));
 });
 $('confirm-submit').addEventListener('click',()=>{
  if ($('simulate-failure').checked && !failedOnce) { failedOnce=true; $('submit-failure').hidden=false; $('confirm-submit').textContent='重试签收'; saveDraft(); return; }
  confirmed=true; dirty=false; saveDraft(); $('receipt-status').textContent='已完成演示签收'; $('receipt-status').className='hx-tag hx-tag-success';
  $('receipt-history-current').innerHTML='<strong>演示签收完成</strong><span class="hx-meta">'+esc($('receiver').value.trim())+' · '+esc($('receivedDate').value)+'</span>';
  $('draft-state').textContent='演示签收已完成，草稿已保留'; $('review-receipt').textContent='再次核对'; renderTasks(); closeDialog($('confirm-dialog'));
 });
 window.addEventListener('beforeunload',event=>{ if (dirty) {event.preventDefault(); event.returnValue='';} });
}());
