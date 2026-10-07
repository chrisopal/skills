(function () {
  "use strict";

  var state = null;
  var selectedId = null;
  var dirty = false;
  var unsavedBuffers = Object.create(null);
  var loadSequence = 0;
  var saveInFlight = false;
  var bodyEditor = document.getElementById("body-editor");
  var saveButton = document.getElementById("save-button");
  var reloadButton = document.getElementById("reload-button");
  var discardButton = document.getElementById("discard-button");
  var settingsForm = document.getElementById("settings-form");
  var settingsSaveButton = document.getElementById("settings-save-button");
  var errorBanner = document.getElementById("error-banner");
  var saveState = document.getElementById("save-state");

  function setStatus(text, kind) {
    saveState.textContent = text;
    saveState.className = "status status-" + (kind || "neutral");
  }

  function showError(text) {
    errorBanner.textContent = text;
    errorBanner.hidden = !text;
  }

  function setBusy(busy) {
    saveButton.disabled = busy || !state;
    reloadButton.disabled = busy;
    discardButton.disabled = busy || !dirty;
    settingsSaveButton.disabled = busy;
    Array.prototype.forEach.call(document.querySelectorAll(".chapter-link"), function (button) {
      button.disabled = busy;
    });
  }

  function text(value) { return value === null || value === undefined ? "" : String(value); }

  function renderChapterList() {
    var list = document.getElementById("chapter-list");
    while (list.firstChild) list.removeChild(list.firstChild);
    var chapters = state.chapters || [];
    document.getElementById("chapter-count").textContent = text(chapters.length);
    chapters.forEach(function (chapter) {
      var button = document.createElement("button");
      button.type = "button";
      button.className = "chapter-link" + (chapter.id === selectedId ? " is-selected" : "") + (chapter.written ? " is-written" : "");
      button.addEventListener("click", function () { selectChapter(chapter.id); });
      var label = document.createElement("span");
      label.textContent = text(chapter.number) + " " + text(chapter.title);
      var status = document.createElement("span");
      status.className = "chapter-state";
      status.textContent = chapter.written ? "已写" : "未写";
      button.appendChild(label);
      button.appendChild(status);
      list.appendChild(button);
    });
  }

  function renderReferences() {
    var root = document.getElementById("reference-content");
    while (root.firstChild) root.removeChild(root.firstChild);
    var refs = state.references || {};
    addGroup(root, "需求", refs.requirements || [], "text", "artifacts/03-requirements.json");
    addGroup(root, "评分", refs.scoring || [], "title", "artifacts/04-scoring.json");
    addGroup(root, "证据", refs.evidence || [], "title", "artifacts/09-evidence-selection.json");
    addGroup(root, "图表任务", state.chapter && state.chapter.visuals_needed || [], null, null);
    renderFigures(root);
    if ((refs.missing_evidence || []).length) addGroup(root, "缺失证据", refs.missing_evidence, null);
    if (!refs.requirements && !refs.scoring && !refs.evidence) {
      var empty = document.createElement("div");
      empty.className = "empty-state";
      empty.textContent = "当前章节没有可读依据。";
      root.appendChild(empty);
    }
    renderCoverage();
  }

  function renderFigures(root) {
    var figures = state.visuals && state.visuals.data && state.visuals.data.figures || [];
    var sectionId = state.chapter && state.chapter.section_id;
    figures = figures.filter(function (figure) { return !sectionId || figure.section_id === sectionId; });
    var group = document.createElement("section");
    group.className = "reference-group";
    var heading = document.createElement("h3");
    heading.textContent = "当前图表";
    group.appendChild(heading);
    if (!figures.length) {
      var empty = document.createElement("div");
      empty.className = "empty-state";
      empty.textContent = "暂无匹配图表产物";
      group.appendChild(empty);
    } else {
      var list = document.createElement("ul");
      figures.forEach(function (figure) {
        var item = document.createElement("li");
        var labels = { specified: "待渲染", rendered: "已渲染", reviewed: "已检查" };
        var label = text(figure.title || figure.id) + " · " + (labels[figure.state] || "状态未标记") + " · " + text(figure.caption || "");
        var path = figure.rendered_path || figure.source_path;
        if (path) {
          var link = document.createElement("a");
          link.href = "/api/file?path=" + encodeURIComponent(path);
          link.target = "_blank";
          link.rel = "noopener";
          link.textContent = label;
          item.appendChild(link);
        } else item.textContent = label;
        list.appendChild(item);
      });
      group.appendChild(list);
    }
    root.appendChild(group);
  }

  function renderCoverage() {
    var root = document.getElementById("coverage-content");
    while (root.firstChild) root.removeChild(root.firstChild);
    var coverage = state.coverage || {};
    var heading = document.createElement("h3");
    heading.textContent = "结构检查与待处理项";
    root.appendChild(heading);
    var notice = document.createElement("div");
    notice.className = "empty-state";
    notice.textContent = (coverage.semantic_acceptance === "NOT_TESTED" ? "正文满足性待复核" : "结构检查：" + text(coverage.status || "未运行"))
      + " · 已规划 " + text(coverage.outline_mapped_count || 0) + " 项 · 已写 " + text(coverage.written_requirement_count || 0) + " 项";
    root.appendChild(notice);
    if (coverage.scoring_started !== undefined || coverage.scoring_pending_review !== undefined) {
      var scoringStatus = document.createElement("div");
      scoringStatus.className = "coverage-trace";
      scoringStatus.textContent = "评分覆盖：" + ((coverage.scoring_started || []).length ? "已开始" : "尚未开始")
        + "；评分满足性待复核" + ((coverage.scoring_pending_review || []).length ? "（存在待复核项）" : "");
      root.appendChild(scoringStatus);
    }
    var labels = [["planned_not_written", "目录已规划但尚未写作"], ["missing_responses", "尚未形成响应"],
      ["unwritten_scoring", "尚未写作的评分项"], ["evidence_gaps", "证据缺口"]];
    labels.forEach(function (entry) {
      var values = coverage[entry[0]] || [];
      if (!values.length) return;
      var group = document.createElement("div");
      group.className = "coverage-group";
      var label = document.createElement("strong");
      label.textContent = entry[1] + "（" + values.length + "）";
      group.appendChild(label);
      var details = document.createElement("details");
      var summary = document.createElement("summary");
      summary.textContent = "查看明细";
      details.appendChild(summary);
      var list = document.createElement("ul");
      values.forEach(function (value) { var item = document.createElement("li"); item.textContent = text(value); list.appendChild(item); });
      details.appendChild(list);
      group.appendChild(details);
      root.appendChild(group);
    });
    if (coverage.trace_state) {
      var trace = document.createElement("div");
      trace.className = "coverage-trace";
      var traceLabels = { current: "有效", stale: "过期，需复核", missing: "缺少" };
      trace.textContent = "追溯状态：" + (traceLabels[coverage.trace_state] || "未确认");
      root.appendChild(trace);
    }
    (coverage.errors || []).concat(coverage.warnings || []).forEach(function (value) {
      var message = document.createElement("div");
      message.className = "coverage-trace";
      message.textContent = text(value);
      root.appendChild(message);
    });
    if (state.upstream && state.upstream.errors && state.upstream.errors.length) {
      var upstream = document.createElement("div");
      upstream.className = "message message-error";
      upstream.textContent = "上游输入已变化或缺失：" + state.upstream.errors.join("；");
      root.appendChild(upstream);
    }
  }

  function addGroup(root, title, rows, field, sourcePath) {
    var group = document.createElement("section");
    group.className = "reference-group";
    var heading = document.createElement("h3");
    heading.textContent = title;
    group.appendChild(heading);
    if (!rows.length) {
      var empty = document.createElement("div");
      empty.className = "empty-state";
      empty.textContent = "暂无" + title;
      group.appendChild(empty);
    } else {
      var list = document.createElement("ul");
      rows.forEach(function (row) {
        var item = document.createElement("li");
        var label = typeof row === "string" ? row : text(row.id) + "：" + text(row[field] || row.title || row.rule_text);
        if (sourcePath) {
          var link = document.createElement("a");
          link.href = "/api/file?path=" + encodeURIComponent(sourcePath);
          link.target = "_blank";
          link.rel = "noopener";
          link.textContent = label;
          item.appendChild(link);
        } else item.textContent = label;
        list.appendChild(item);
      });
      group.appendChild(list);
    }
    root.appendChild(group);
  }

  function renderEditor() {
    var chapter = state.chapter || {};
    document.getElementById("editor-heading").textContent = text(chapter.title || "未写章节");
    document.getElementById("chapter-state").textContent = chapter.state === "unwritten" ? "未写" : "草稿";
    document.getElementById("chapter-state").className = "status " + (chapter.state === "unwritten" ? "status-warning" : "status-success");
    bodyEditor.value = Object.prototype.hasOwnProperty.call(unsavedBuffers, selectedId)
      ? unsavedBuffers[selectedId] : text(chapter.body_markdown);
    bodyEditor.disabled = false;
    dirty = Object.prototype.hasOwnProperty.call(unsavedBuffers, selectedId);
    discardButton.disabled = !dirty;
    document.getElementById("word-count").textContent = bodyEditor.value.length + " 字";
    renderReferences();
  }

  function applySettings(settings) {
    settings = settings || {};
    document.getElementById("tone-setting").value = text(settings.tone || "plain_chinese");
    document.getElementById("target-words-setting").value = settings.target_words || "";
    document.getElementById("execution-mode-setting").value = text(settings.execution_mode || "sequential");
    document.getElementById("max-parallel-setting").value = text(settings.max_parallel || 1);
  }

  function load(chapterId) {
    var sequence = ++loadSequence;
    var url = "/api/state" + (chapterId ? "?chapter_id=" + encodeURIComponent(chapterId) : "");
    setStatus("正在加载", "neutral");
    setBusy(true);
    return fetch(url, { credentials: "same-origin" }).then(function (response) {
      if (!response.ok) return response.json().then(function (data) { throw new Error(data.error && data.error.message || "读取失败"); });
      return response.json();
    }).then(function (data) {
      if (sequence !== loadSequence) return;
      state = data;
      selectedId = data.chapter && data.chapter.id;
      dirty = Object.prototype.hasOwnProperty.call(unsavedBuffers, selectedId);
      document.getElementById("project-name").textContent = text(data.project && (data.project.project_name || data.project.project_id));
      applySettings(data.settings);
      renderChapterList();
      renderEditor();
      var hasUnsavedBuffer = Object.prototype.hasOwnProperty.call(unsavedBuffers, selectedId);
      var hasUpstreamErrors = data.upstream && data.upstream.errors && data.upstream.errors.length;
      setStatus(hasUnsavedBuffer ? "有未保存修改" : (hasUpstreamErrors ? "上游待复核" : "已加载"),
        hasUnsavedBuffer || hasUpstreamErrors ? "warning" : "success");
      showError("");
    }).catch(function (error) {
      if (sequence === loadSequence) { setStatus("读取失败", "error"); showError(error.message); }
    }).finally(function () { if (sequence === loadSequence) setBusy(false); });
  }

  function selectChapter(id) {
    if (id === selectedId) return;
    if (saveInFlight) return;
    if (dirty) unsavedBuffers[selectedId] = bodyEditor.value;
    load(id);
  }

  function save() {
    if (!state || !state.writing || saveInFlight) return;
    saveInFlight = true;
    unsavedBuffers[selectedId] = bodyEditor.value;
    setBusy(true);
    setStatus("正在保存", "neutral");
    var request = { expected_revision: state.writing.revision, expected_sha256: state.writing.sha256,
      chapter_id: selectedId, body_markdown: bodyEditor.value };
    fetch("/api/save", { method: "POST", credentials: "same-origin", headers: { "Content-Type": "application/json" }, body: JSON.stringify(request) })
      .then(function (response) { return response.json().then(function (data) { if (!response.ok) { var error = new Error(data.error && data.error.message || "保存失败"); error.code = data.error && data.error.code; throw error; } return data; }); })
      .then(function (data) { delete unsavedBuffers[selectedId]; state = data; dirty = false; renderChapterList(); renderEditor(); setStatus("已保存草稿", "success"); showError(""); })
      .catch(function (error) { setStatus(error.code === "stale_write" ? "发生冲突" : "保存失败", "error"); showError(error.message + " 编辑区内容已保留，请重载后手动合并。"); })
      .finally(function () { saveInFlight = false; setBusy(false); discardButton.disabled = !dirty; });
  }

  function discardCurrent() {
    if (!dirty || !window.confirm("放弃当前编辑并从服务器重载吗？")) return;
    delete unsavedBuffers[selectedId];
    dirty = false;
    load(selectedId);
  }

  function saveSettings(event) {
    event.preventDefault();
    var target = document.getElementById("target-words-setting").value;
    var request = { tone: document.getElementById("tone-setting").value,
      target_words: target ? Number(target) : null,
      execution_mode: document.getElementById("execution-mode-setting").value,
      max_parallel: Number(document.getElementById("max-parallel-setting").value),
      expected_revision: state && state.settings ? state.settings.revision : 0,
      expected_sha256: state && state.settings ? state.settings.sha256 : "" };
    settingsSaveButton.disabled = true;
    fetch("/api/settings", { method: "POST", credentials: "same-origin", headers: { "Content-Type": "application/json" }, body: JSON.stringify(request) })
      .then(function (response) { return response.json().then(function (data) { if (!response.ok) { var error = new Error(data.error && data.error.message || "设置保存失败"); error.code = data.error && data.error.code; throw error; } return data; }); })
      .then(function () { setStatus("设置已保存并重载", "success"); return load(selectedId); })
      .catch(function (error) { setStatus(error.code === "stale_settings" ? "设置发生冲突" : "设置保存失败", "error"); showError(error.message); })
      .finally(function () { settingsSaveButton.disabled = false; });
  }

  bodyEditor.addEventListener("input", function () { unsavedBuffers[selectedId] = bodyEditor.value; dirty = true; discardButton.disabled = false; document.getElementById("word-count").textContent = bodyEditor.value.length + " 字"; setStatus("有未保存修改", "warning"); });
  saveButton.addEventListener("click", save);
  discardButton.addEventListener("click", discardCurrent);
  reloadButton.addEventListener("click", function () { if (!dirty || window.confirm("重载会丢弃当前未保存内容，继续吗？")) { delete unsavedBuffers[selectedId]; dirty = false; load(selectedId); } });
  settingsForm.addEventListener("submit", saveSettings);
  document.getElementById("theme-button").addEventListener("click", function () { document.documentElement.setAttribute("data-theme", document.documentElement.getAttribute("data-theme") === "dark" ? "light" : "dark"); });
  window.addEventListener("beforeunload", function (event) { if (dirty || saveInFlight) { event.preventDefault(); event.returnValue = ""; } });
  load(null);
}());
