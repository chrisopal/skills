(() => {
  'use strict';
  const data = JSON.parse(document.getElementById('review-data').textContent);
  const key = 'consulting-review:' + JSON.stringify(data.metadata.sources);
  let state = {reviewer: '', notes: {}};
  let storageAvailable = true;
  try {
    const saved = JSON.parse(localStorage.getItem(key) || 'null');
    if (saved && typeof saved.reviewer === 'string' && saved.notes && typeof saved.notes === 'object') state = saved;
  } catch (_) { storageAvailable = false; }
  const status = document.getElementById('save-status');
  function save() {
    try { localStorage.setItem(key, JSON.stringify(state)); }
    catch (_) { storageAvailable = false; }
    status.textContent = storageAvailable ? '意见已保存在此浏览器' : '浏览器存储不可用，请导出意见';
  }
  const reviewer = document.getElementById('reviewer');
  reviewer.value = state.reviewer;
  reviewer.addEventListener('input', () => {state.reviewer = reviewer.value; save();});
  document.querySelectorAll('.review-note').forEach(el => {
    el.value = typeof state.notes[el.dataset.noteId] === 'string' ? state.notes[el.dataset.noteId] : '';
    el.addEventListener('input', () => {state.notes[el.dataset.noteId] = el.value; save();});
  });
  function navigate() {
    const requested = location.hash.slice(1);
    const active = ['report','process','architecture','organization','investment','slides'].includes(requested) ? requested : 'report';
    document.querySelectorAll('.view').forEach(el => {el.hidden = el.id !== active;});
    document.querySelectorAll('[data-view]').forEach(el => {
      if (el.dataset.view === active) el.setAttribute('aria-current', 'page');
      else el.removeAttribute('aria-current');
    });
  }
  window.addEventListener('hashchange', navigate);
  navigate();
  document.getElementById('theme-toggle').addEventListener('click', function () {
    const dark = document.documentElement.dataset.theme !== 'dark';
    document.documentElement.dataset.theme = dark ? 'dark' : 'light';
    this.textContent = dark ? '切换浅色' : '切换深色';
    this.setAttribute('aria-pressed', String(dark));
  });
  document.getElementById('expand-tree').addEventListener('click', () => document.querySelectorAll('.process-node').forEach(el => {el.open = true;}));
  document.getElementById('collapse-tree').addEventListener('click', () => document.querySelectorAll('.process-node').forEach(el => {el.open = false;}));
  function download(name, content, type) {
    const url = URL.createObjectURL(new Blob([content], {type}));
    const anchor = document.createElement('a');
    anchor.href = url; anchor.download = name; document.body.append(anchor); anchor.click(); anchor.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  document.getElementById('export-notes').addEventListener('click', () => {
    const result = {...data.metadata, artifact_id:data.metadata.project_id + '-cross-cutting-review-notes-' + Date.now(), schema_version:'1.0.0', artifact_type:'local-review-notes', generated_at:new Date().toISOString(), review:{reviewer:state.reviewer || '未指定', decision:'not-reviewed'}, approval_effect:'none', slides:data.slide_ids.map(id => ({slide_id:id, note:state.notes[id] || '', review_status:'not-approved'}))};
    download('consulting-review-notes.json', JSON.stringify(result, null, 2), 'application/json');
    status.textContent = '审阅意见已导出；未批准 Gate';
  });
  document.getElementById('download-diagram').addEventListener('click', () => download('4a-traceability.drawio', data.diagram, 'application/xml'));
  document.querySelectorAll('[data-process-download]').forEach(el => el.addEventListener('click', () => {
    const name = el.dataset.processDownload;
    download(name, data.process_diagram_files[name], name.endsWith('.svg') ? 'image/svg+xml' : 'application/json');
  }));
  const sourceNames = {report:'report.md', pack:'planning-pack.json', slides:'slide-content-pack.json'};
  document.querySelectorAll('[data-download-source]').forEach(el => el.addEventListener('click', () => {
    const label = el.dataset.downloadSource;
    download(sourceNames[label], data.originals[label], label === 'report' ? 'text/markdown;charset=utf-8' : 'application/json');
  }));
})();
