(function () {
  "use strict";

  var state = null;
  var selectedId = null;
  var collapsedSections = Object.create(null);
  var dirty = false;
  var settingsDirty = false;
  var reviewActionBusy = false;
  var aiScoringBusy = false;
  var aiSelectedTargets = Object.create(null);
  var showAllScoringRows = false;
  var workspaceBusy = false;
  var reviewActionRetry = null;
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
  var visualFieldIds = ["diagram-engine-setting", "diagram-theme-setting", "diagram-format-setting", "layout-template-setting",
    "architecture-layers-setting", "image-mode-setting", "visual-tool-setting",
    "visual-model-setting", "visual-style-setting", "visual-aspect-ratio-setting",
    "visual-max-images-setting", "system-ui-policy-setting", "min-ui-images-setting"];

  function setStatus(text, kind) {
    saveState.textContent = text;
    saveState.className = "status status-" + (kind || "neutral");
  }

  function showError(text) {
    errorBanner.textContent = text;
    errorBanner.hidden = !text;
  }

  function hasUnsavedWork() {
    return dirty || settingsDirty || Object.keys(unsavedBuffers).length > 0;
  }

  function requestId() {
    return window.crypto && typeof window.crypto.randomUUID === "function"
      ? window.crypto.randomUUID()
      : "00000000-0000-4000-8000-" + String(Date.now()).slice(-12).padStart(12, "0");
  }

  function scoringView() {
    return state && state.ai_scoring || {available: false, error: "评分状态尚未加载", latest_report: null,
      latest_request: null, host_execution: "manual_handoff"};
  }

  function scoringRows() {
    var report = scoringView().latest_report;
    return report && Array.isArray(report.rows) ? report.rows : [];
  }

  function reportUrl(report) {
    return report && report.report_url || "";
  }

  function scoringStatusLabel(status) {
    return {awaiting_host: "待宿主执行", claimed: "宿主执行中", needs_input: "待补材料／确认", requires_input: "待补材料／确认",
      completed: "已完成", stale: "版本已过期", failed: "执行失败", scored: "已评分",
      unknown: "待核验", not_reviewed: "未评读", not_applicable: "不适用"}[status] || "待核验";
  }

  function scoringTypeLabel(type) {
    return {subjective: "主观评分", objective: "客观材料", price: "价格评分"}[type] || text(type || "未确认");
  }

  function scoringRowCanImprove(row) {
    return row && row.status === "scored" && row.scoring_type === "subjective"
      && row.editable !== false
      && row.route !== "requires_input"
      && rowHasDeductions(row);
  }

  function rowHasDeductions(row) {
    return Array.isArray(row && row.deductions) && row.deductions.some(function (deduction) {
      return deduction && Number(deduction.points || 0) > 0;
    });
  }

  function rowNeedsAttention(row) {
    return row && (row.status === "unknown" || rowHasDeductions(row));
  }

  function copyWithFallback(value, button, input) {
    if (!navigator.clipboard || !navigator.clipboard.writeText) {
      input.focus(); input.select(); button.textContent = "请复制已选中的指令"; return;
    }
    navigator.clipboard.writeText(value).then(function () { button.textContent = "已复制"; })
      .catch(function () { input.focus(); input.select(); button.textContent = "请复制已选中的指令"; });
  }

  function applyAiScoringResponse(data) {
    var view = data && data.ai_scoring ? data.ai_scoring : data;
    if (!view || typeof view !== "object") return;
    state.ai_scoring = Object.assign({}, scoringView(), view);
    if (data && data.request) state.ai_scoring.latest_request = data.request;
    var validIds = Object.create(null);
    scoringRows().forEach(function (row) { validIds[text(row.target_id)] = true; });
    Object.keys(aiSelectedTargets).forEach(function (id) { if (!validIds[id]) delete aiSelectedTargets[id]; });
  }

  function renderAiScoringMetrics(summary) {
    var root = document.getElementById("ai-scoring-metrics");
    root.replaceChildren();
    var metrics = [["已评模拟分", summary && summary.known_score, "分"],
      ["已评分上限", summary && summary.scored_max, "分"],
      ["待核验上限", summary && summary.unknown_max, "分"],
      ["未评读上限", summary && summary.not_reviewed_max, "分"]];
    metrics.forEach(function (metric) {
      var item = document.createElement("div");
      var label = document.createElement("dt"); label.textContent = metric[0];
      var value = document.createElement("dd");
      value.textContent = metric[1] == null ? "—" : text(metric[1]) + metric[2];
      item.appendChild(label); item.appendChild(value); root.appendChild(item);
    });
  }

  function renderAiScoringRows(rows) {
    var root = document.getElementById("ai-scoring-rows");
    root.replaceChildren();
    if (!rows.length) {
      var empty = document.createElement("div");
      empty.className = "empty-state";
      empty.textContent = showAllScoringRows ? "暂无宿主评分报告；可创建模拟评分交接任务。" : "当前没有扣分项或待核验项；勾选“显示全部评分项”查看完整结果。";
      root.appendChild(empty);
      return;
    }
    var wrapper = document.createElement("div"); wrapper.className = "ai-scoring-table-wrap";
    var table = document.createElement("table"); table.className = "ai-scoring-table";
    var caption = document.createElement("caption"); caption.className = "sr-only"; caption.textContent = "AI 模拟评分明细";
    table.appendChild(caption);
    var head = document.createElement("thead"); var headRow = document.createElement("tr");
    ["选择", "评分项", "得分", "状态", "扣分与建议"].forEach(function (label) {
      var cell = document.createElement("th"); cell.scope = "col"; cell.textContent = label; headRow.appendChild(cell);
    });
    head.appendChild(headRow); table.appendChild(head);
    var body = document.createElement("tbody");
    rows.forEach(function (row) {
      var targetId = text(row.target_id);
      var canImprove = scoringRowCanImprove(row);
      var tr = document.createElement("tr");
      if (aiSelectedTargets[targetId]) tr.className = "is-selected";
      var selectCell = document.createElement("td");
      var checkbox = document.createElement("input"); checkbox.type = "checkbox";
      checkbox.checked = !!aiSelectedTargets[targetId]; checkbox.disabled = !canImprove || aiScoringBusy;
      checkbox.setAttribute("aria-label", "选择提升项：" + text(row.title || targetId));
      checkbox.addEventListener("change", function () {
        if (checkbox.checked) aiSelectedTargets[targetId] = true; else delete aiSelectedTargets[targetId];
        renderAiScoring();
      });
      selectCell.appendChild(checkbox); tr.appendChild(selectCell);
      var titleCell = document.createElement("td");
      var title = document.createElement("strong"); title.textContent = text(row.title || targetId); titleCell.appendChild(title);
      var meta = document.createElement("span"); meta.className = "ai-scoring-row-meta";
      meta.textContent = scoringTypeLabel(row.scoring_type); titleCell.appendChild(meta); tr.appendChild(titleCell);
      var scoreCell = document.createElement("td"); scoreCell.className = "score-cell";
      scoreCell.textContent = row.simulated_score == null || row.max_score == null ? "—" : text(row.simulated_score) + "/" + text(row.max_score);
      tr.appendChild(scoreCell);
      var statusCell = document.createElement("td");
      var status = document.createElement("span"); status.className = "status status-" + (row.status === "scored" ? "success" : row.status === "unknown" ? "warning" : "neutral");
      status.textContent = scoringStatusLabel(row.status); statusCell.appendChild(status);
      var blockedRoute = row.editable === false || row.route === "requires_input" || row.scoring_type !== "subjective";
      if (row.status === "scored" && rowHasDeductions(row) && blockedRoute) {
        var material = document.createElement("span"); material.className = "ai-scoring-row-meta"; material.textContent = row.scoring_type === "price" ? "需价格输入" : "需材料或确认"; statusCell.appendChild(material);
      }
      tr.appendChild(statusCell);
      var deductionCell = document.createElement("td");
      var deductions = Array.isArray(row.deductions) ? row.deductions : [];
      if (!deductions.length || !rowHasDeductions(row)) deductionCell.textContent = row.status === "unknown" ? (row.scoring_type === "price" ? "需价格输入" : "待核验") : "无扣分";
      else deductions.forEach(function (deduction, index) {
        var item = document.createElement("div"); item.className = "ai-deduction";
        item.textContent = "−" + text(deduction.points == null ? "?" : deduction.points) + "分 · " + text(deduction.reason || "待说明");
        if (deduction.action) { var action = document.createElement("span"); action.textContent = "；" + text(deduction.action); item.appendChild(action); }
        if (index > 0) item.classList.add("is-secondary"); deductionCell.appendChild(item);
      });
      if (targetId || row.rationale || row.rubric_basis || (row.bid_refs || []).length || (row.tender_refs || []).length) {
        var basis = document.createElement("details");
        var basisSummary = document.createElement("summary"); basisSummary.textContent = "查看依据"; basis.appendChild(basisSummary);
        if (targetId) { var target = document.createElement("p"); target.textContent = "评分项标识：" + targetId; basis.appendChild(target); }
        if (row.rationale) { var rationale = document.createElement("p"); rationale.textContent = text(row.rationale); basis.appendChild(rationale); }
        if (row.rubric_basis) { var rubric = document.createElement("p"); rubric.textContent = "评分规则：" + text(row.rubric_basis); basis.appendChild(rubric); }
        var refs = (row.bid_refs || []).concat(row.tender_refs || []);
        if (refs.length) { var refLine = document.createElement("p"); refLine.textContent = "原文依据：" + refs.map(function (ref) { return typeof ref === "string" ? ref : text(ref.id || ref.title || ref.relative_path); }).join("、"); basis.appendChild(refLine); }
        deductionCell.appendChild(basis);
      }
      tr.appendChild(deductionCell); body.appendChild(tr);
    });
    table.appendChild(body); wrapper.appendChild(table); root.appendChild(wrapper);
  }

  function renderAiScoringDetails(view) {
    var root = document.getElementById("ai-scoring-detail-content");
    root.replaceChildren();
    var report = view.latest_report;
    if (view.host_execution) {
      var execution = document.createElement("p"); execution.className = "meta-text";
      execution.textContent = "执行方式：" + (view.host_execution === "manual_handoff" ? "待宿主执行" : text(view.host_execution)); root.appendChild(execution);
    }
    if (report) {
      var reportMeta = document.createElement("p"); reportMeta.className = "meta-text";
      reportMeta.textContent = "报告版本 " + text(report.revision || "—") + " · " + (report.current ? "当前正文版本" : "版本已变化")
        + " · 校验" + (report.valid ? "通过" : "未通过"); root.appendChild(reportMeta);
    }
    var request = view.latest_request;
    if (!request) {
      var empty = document.createElement("p"); empty.className = "meta-text"; empty.textContent = "尚未创建宿主评分任务。"; root.appendChild(empty); return;
    }
    var requestLine = document.createElement("p");
    requestLine.textContent = "最近任务：" + scoringStatusLabel(request.status) + (request.relative_path ? " · " + text(request.relative_path) : ""); root.appendChild(requestLine);
    var prompt = request.prompt || request.host_prompt;
    if (prompt) {
      var handoff = document.createElement("div"); handoff.className = "ai-scoring-handoff";
      var input = document.createElement("textarea"); input.readOnly = true; input.className = "review-action-prompt"; input.value = prompt; input.setAttribute("aria-label", "AI 评分宿主交接指令"); handoff.appendChild(input);
      var copy = document.createElement("button"); copy.type = "button"; copy.className = "button button-secondary"; copy.textContent = "复制宿主交接指令";
      copy.addEventListener("click", function () { copyWithFallback(prompt, copy, input); }); handoff.appendChild(copy); root.appendChild(handoff);
    }
    var limitation = document.createElement("p"); limitation.className = "meta-text"; limitation.textContent = "客观资格、价格和未知项需要真实材料或输入，不能通过正文润色代替。"; root.appendChild(limitation);
  }

  function renderAiScoring() {
    var view = scoringView(); var report = view.latest_report; var request = view.latest_request;
    var status = document.getElementById("ai-scoring-status");
    var notice = document.getElementById("ai-scoring-notice");
    var scoreButton = document.getElementById("ai-score-button");
    var reportButton = document.getElementById("ai-report-button");
    var refreshButton = document.getElementById("ai-refresh-button");
    var improveButton = document.getElementById("ai-improve-button");
    var rowCount = document.getElementById("ai-scoring-row-count");
    var version = document.getElementById("ai-scoring-version");
    var selected = Object.keys(aiSelectedTargets).filter(function (id) { return aiSelectedTargets[id]; });
    var hasUnsaved = hasUnsavedWork();
    var editorStale = !!(view.writing && state && state.writing && view.writing.sha256 !== state.writing.sha256);
    var reportCurrent = !!(report && report.valid && report.current && reportUrl(report));
    var requestPending = request && ["awaiting_host", "claimed"].indexOf(request.status) !== -1;
    status.textContent = aiScoringBusy ? "正在处理" : request ? scoringStatusLabel(request.status) : report ? (reportCurrent ? "结果有效" : report.valid && report.current ? "待评分" : "结果待复核") : (view.available ? "可创建任务" : "待准备");
    status.className = "status status-" + (aiScoringBusy ? "neutral" : view.error || request && request.status === "failed" ? "error" : reportCurrent ? "success" : "warning");
    version.textContent = "正文版本 " + text(view.writing && view.writing.revision || state && state.writing && state.writing.revision || "—")
      + (report ? " · 报告 " + text(report.revision || "—") + (report.current ? "（当前）" : "（过期）") : " · 暂无报告");
    if (report && report.summary && report.summary.scope === "limited") version.textContent += " · 限定范围评读";
    if (aiScoringBusy) notice.textContent = "正在与宿主交接，请稍候。";
    else if (hasUnsaved) notice.textContent = "请先保存或放弃未保存的正文及设置，再发起评分或提升。";
    else if (editorStale) notice.textContent = "宿主已更新正文，请重载工作稿后继续。当前报告可单独查看。";
    else if (view.error) notice.textContent = text(typeof view.error === "object" ? view.error.message : view.error);
    else if (requestPending) notice.textContent = "已创建任务，待宿主执行；本页不会把交接任务标记为评分完成。";
    else if (request && request.status === "failed") notice.textContent = "上次任务未完成，可重新发起。" + text(request.failure_reason || "");
    else if (request && ["needs_input", "requires_input"].indexOf(request.status) !== -1) notice.textContent = "该任务需补材料或人工确认；补齐后可重新评分。";
    else if (request && request.status === "completed") notice.textContent = reportCurrent ? "宿主已完成评读，当前报告可查看。" : "宿主任务已完成，但报告版本需重新核验。";
    else if (report && report.valid && report.current && !reportCurrent) notice.textContent = "当前评分输入已准备，等待宿主完成评读后才能查看报告。";
    else if (report && !reportCurrent) notice.textContent = "已有评分报告，但它与当前正文版本不一致，请刷新或重新评分。";
    else if (!report) notice.textContent = "暂无评分报告；模拟评分只创建宿主交接任务。";
    else notice.textContent = "评分结果已加载。";
    scoreButton.disabled = aiScoringBusy || workspaceBusy || !state || hasUnsaved || editorStale || !view.available || requestPending;
    reportButton.disabled = aiScoringBusy || !reportCurrent;
    refreshButton.disabled = aiScoringBusy || !state;
    improveButton.disabled = aiScoringBusy || workspaceBusy || hasUnsaved || editorStale || requestPending || !reportCurrent || !selected.length;
    var allRows = scoringRows();
    var visibleRows = showAllScoringRows ? allRows : allRows.filter(rowNeedsAttention);
    rowCount.textContent = "显示 " + visibleRows.length + " / 共 " + allRows.length + " 项";
    renderAiScoringMetrics(report && report.summary || {});
    renderAiScoringRows(visibleRows);
    renderAiScoringDetails(view);
  }

  function setBusy(busy) {
    workspaceBusy = busy;
    bodyEditor.disabled = busy || !state;
    saveButton.disabled = busy || !state;
    reloadButton.disabled = busy;
    discardButton.disabled = busy || !dirty;
    settingsSaveButton.disabled = busy;
    document.querySelectorAll("#settings-form input, #settings-form select").forEach(function (field) {
      var isVisualField = visualFieldIds.indexOf(field.id) !== -1;
      field.disabled = busy || (isVisualField && !document.getElementById("visuals-enabled-setting").checked);
    });
    document.getElementById("diagram-theme-setting").disabled = busy ||
      !document.getElementById("visuals-enabled-setting").checked ||
      document.getElementById("diagram-engine-setting").value !== "blueprint";
    Array.prototype.forEach.call(document.querySelectorAll(".chapter-link, .chapter-toggle, .policy-chapter-link"), function (button) {
      button.disabled = busy;
    });
    renderReviewActions();
    renderAiScoring();
  }

  function renderReviewActions() {
    var view = state && state.review_actions || {};
    var request = view.latest_request;
    var hasUnsaved = hasUnsavedWork();
    var noTargets = document.getElementById("review-action-scope").value === "failed" && !(view.findings || []).length;
    var disabled = workspaceBusy || reviewActionBusy || hasUnsaved || !view.available || noTargets ||
      request && request.status === "claimed";
    document.querySelectorAll("[data-review-action]").forEach(function (button) { button.disabled = disabled; });
    document.getElementById("review-action-scope").disabled = workspaceBusy || reviewActionBusy;
    var labels = { awaiting_host: "待宿主执行", needs_input: "待补材料／确认", running: "宿主执行中",
      awaiting_rereview: "修改完成，待重新评审", completed_with_remaining: "已重评，仍有待处理项",
      checks_clear_needs_semantic_acceptance: "检查已完成，待语义验收", stale: "任务版本已过期", attempts_exhausted: "已达整改轮次上限" };
    var status = document.getElementById("review-action-status");
    labels.claimed = "宿主执行中";
    status.textContent = reviewActionBusy ? "正在创建任务" : request ? labels[request.status] || "任务待核验" : view.available ? "可创建任务" : "评审待准备";
    status.className = "status status-" + (view.available ? "neutral" : "warning");
    document.getElementById("review-action-notice").textContent = hasUnsaved ? "请先保存或放弃所有章节的未保存修改。" :
      view.error ? text(typeof view.error === "object" ? view.error.message : view.error) : noTargets ? "本轮没有待修复项；可选择当前章节重写或提升。" :
      "任务交由当前 Agent 执行；此编辑器尚未连接自动唤醒接口。修改后需要重新评审。";
    var findings = document.getElementById("review-action-findings");
    findings.replaceChildren();
    (view.findings || []).forEach(function (row) {
      var item = document.createElement("li");
      item.textContent = (row.route === "requires_input" ? "需补材料／确认 · " : "待处理 · ") + text(row.reason || row.message || row.id);
      findings.appendChild(item);
    });
    var result = document.getElementById("review-action-result");
    result.replaceChildren();
    if (request) {
      var line = document.createElement("p");
      var actionNames = {repair: "修复", rewrite: "重写", improve: "提升"};
      line.textContent = (actionNames[request.action] || "整改") + " · " +
        (request.scope === "chapter" ? "当前章节" : "本轮未通过项") + " · " + (labels[request.status] || "待核验");
      result.appendChild(line);
      var prompt = request.prompt || request.host_prompt;
      if (prompt) {
        var handoff = document.createElement("details");
        var summary = document.createElement("summary");
        summary.textContent = "交给当前 Agent 执行";
        handoff.appendChild(summary);
        var input = document.createElement("textarea");
        input.readOnly = true;
        input.className = "review-action-prompt";
        input.setAttribute("aria-label", "整改交接指令");
        input.value = prompt;
        handoff.appendChild(input);
        var copy = document.createElement("button");
        copy.type = "button"; copy.className = "button button-secondary"; copy.textContent = "复制交接指令";
        copy.addEventListener("click", function () {
          if (!navigator.clipboard) { input.focus(); input.select(); copy.textContent = "请复制已选中的指令"; return; }
          navigator.clipboard.writeText(prompt).then(function () { copy.textContent = "已复制"; })
            .catch(function () { input.focus(); input.select(); copy.textContent = "请复制已选中的指令"; });
        });
        handoff.appendChild(copy);
        result.appendChild(handoff);
      }
    }
  }

  function requestReviewAction(action) {
    if (!state || workspaceBusy || reviewActionBusy) return;
    if (dirty || Object.keys(unsavedBuffers).length) { showError("请先保存或放弃未保存的章节，再创建整改任务。"); return; }
    var scope = document.getElementById("review-action-scope").value;
    var intent = [action, scope, selectedSectionId(), state.writing.sha256].join(":");
    if (!reviewActionRetry || reviewActionRetry.intent !== intent) {
      reviewActionRetry = { intent: intent, id: crypto.randomUUID() };
    }
    var payload = {action: action, scope: scope, section_id: scope === "chapter" ? selectedSectionId() : null,
      expected_revision: state.writing.revision, expected_sha256: state.writing.sha256, request_id: reviewActionRetry.id};
    reviewActionBusy = true; showError(""); renderReviewActions();
    fetch("/api/review-actions", {method: "POST", credentials: "same-origin", headers: {"Content-Type": "application/json"}, body: JSON.stringify(payload)})
      .then(function (response) { return response.json().then(function (data) {
        if (!response.ok) throw new Error(data.error && data.error.message || "整改任务创建失败");
        return data;
      }); })
      .then(function (data) {
        state.review_actions = data;
        if (data.request) state.review_actions.latest_request = data.request;
        reviewActionRetry = null;
      })
      .catch(function (error) { showError(error.message); })
      .finally(function () { reviewActionBusy = false; renderReviewActions(); });
  }

  function parseResponse(response, fallback) {
    return response.json().then(function (data) {
      if (!response.ok) {
        var error = new Error(data && data.error && data.error.message || fallback);
        error.code = data && data.error && data.error.code; throw error;
      }
      return data;
    });
  }

  function refreshAiScoring() {
    if (!state || aiScoringBusy) return;
    aiScoringBusy = true; showError(""); renderAiScoring();
    fetch("/api/ai-scoring", {credentials: "same-origin"}).then(function (response) {
      return parseResponse(response, "读取评分结果失败");
    }).then(function (data) {
      applyAiScoringResponse(data); renderAiScoring();
    }).catch(function (error) {
      showError(error.message); var view = scoringView(); view.error = error.message; state.ai_scoring = view;
    }).finally(function () { aiScoringBusy = false; renderAiScoring(); });
  }

  function createAiScoringTask(action) {
    if (!state || aiScoringBusy) return;
    if (hasUnsavedWork()) { showError("请先保存或放弃正文及写作设置的未提交修改，再创建评分任务。"); renderAiScoring(); return; }
    var view = scoringView();
    var payload = {action: action, request_id: requestId(), expected_revision: state.writing.revision,
      expected_sha256: state.writing.sha256};
    if (action === "improve") {
      var report = view.latest_report;
      var targetIds = Object.keys(aiSelectedTargets).filter(function (id) { return aiSelectedTargets[id]; });
      if (!report || !report.sha256 || !targetIds.length) return;
      payload.scoring_sha256 = report.sha256; payload.target_ids = targetIds;
    }
    aiScoringBusy = true; showError(""); renderAiScoring();
    fetch("/api/ai-scoring", {method: "POST", credentials: "same-origin", headers: {"Content-Type": "application/json"}, body: JSON.stringify(payload)})
      .then(function (response) { return parseResponse(response, "创建评分任务失败"); })
      .then(function (data) {
        applyAiScoringResponse(data);
        var request = data && data.request || scoringView().latest_request;
        if (request) {
          state.ai_scoring.latest_request = request;
          if (request.status === "awaiting_host") document.getElementById("ai-scoring-notice").textContent = "已创建宿主交接任务，待宿主执行。";
        }
        setStatus("评分任务已创建", "warning");
      })
      .catch(function (error) { showError(error.message); setStatus("评分任务创建失败", "error"); })
      .finally(function () { aiScoringBusy = false; renderAiScoring(); });
  }

  function openAiReport() {
    var report = scoringView().latest_report;
    var url = reportUrl(report);
    if (!url) return;
    window.open(url, "_blank", "noopener,noreferrer");
  }

  function updateVisualFieldState() {
    var enabled = document.getElementById("visuals-enabled-setting").checked;
    visualFieldIds.forEach(function (id) {
      document.getElementById(id).disabled = !enabled || settingsSaveButton.disabled ||
        (id === "diagram-theme-setting" && document.getElementById("diagram-engine-setting").value !== "blueprint");
    });
  }

  function text(value) { return value === null || value === undefined ? "" : String(value); }

  function clone(value) {
    if (value === null || value === undefined) return value;
    return JSON.parse(JSON.stringify(value));
  }

  function visibleWordCount(markdown) {
    var value = text(markdown)
      .replace(/^\s*(`{3,}|~{3,})[^\n]*\n[\s\S]*?^\s*\1\s*$/gm, "")
      .replace(/<(script|style)\b[^>]*>[\s\S]*?<\/\1>/gi, "")
      .replace(/!\[[^\]]*\]\([^\n]*?\)|!\[[^\]]*\]\[[^\]]*\]/g, "")
      .replace(/^\s*\[[^\]]+\]:\s*\S+.*$/gm, "")
      .replace(/\[([^\]]+)\]\([^\n]*?\)|\[([^\]]+)\]\[[^\]]*\]/g, function (_, first, second) { return first || second; })
      .replace(/<[^>]*>/g, "")
      .replace(/^\s*(?:#{1,6}\s+|[-+*]\s+|\d+[.)]\s+|>\s*)/gm, "")
      .replace(/^\s*\|?\s*:?-{3,}:?\s*(?:\|\s*:?-{3,}:?\s*)*\|?\s*$/gm, "")
      .replace(/[*_`|~]/g, "");
    var decoded = new DOMParser().parseFromString(value, "text/html").body.textContent;
    return Array.from(decoded.replace(/\s/g, "")).length;
  }

  function selectedSectionId() {
    return text(state && state.chapter && (state.chapter.section_id || state.chapter.id));
  }

  function chapterFigures(sectionId) {
    var figures = state && state.visuals && state.visuals.data && state.visuals.data.figures || [];
    return figures.filter(function (figure) { return !sectionId || figure.section_id === sectionId; });
  }

  function interfaceFigureCount(sectionId) {
    var rows = state && state.coverage && state.coverage.writing_policy && state.coverage.writing_policy.chapters || [];
    var checked = rows.find(function (row) { return row.section_id === sectionId; });
    return checked ? checked.ui_image_count : 0;
  }

  function policyIssues(policy, actualWords, actualImages) {
    var issues = policy && Array.isArray(policy.issues) ? policy.issues.slice() : [];
    if (policy && policy.min_words != null && actualWords < Number(policy.min_words)) {
      issues.push("可见正文少于最低建议 " + policy.min_words + " 字");
    }
    if (policy && policy.max_words != null && actualWords > Number(policy.max_words)) {
      issues.push("可见正文超过最高建议 " + policy.max_words + " 字");
    }
    if (policy && policy.ui_required && actualImages < Number(policy.min_ui_images || 1)) {
      issues.push("缺少界面示意图（至少 " + Number(policy.min_ui_images || 1) + " 张）");
    }
    return issues.filter(function (value, index, values) { return value && values.indexOf(value) === index; });
  }

  function renderChapterList() {
    var list = document.getElementById("chapter-list");
    while (list.firstChild) list.removeChild(list.firstChild);
    var chapters = state.chapters || [];
    var groups = Object.create(null);
    document.getElementById("chapter-count").textContent = text(chapters.length);
    chapters.forEach(function (chapter) {
      var item = document.createElement("li");
      item.className = "chapter-item";
      item.dataset.sectionId = chapter.section_id;
      var row = document.createElement("div");
      row.className = "chapter-row";
      var button = document.createElement("button");
      button.type = "button";
      button.className = "chapter-link" + (chapter.id === selectedId ? " is-selected" : "") + (chapter.written ? " is-written" : "");
      button.addEventListener("click", function () { selectChapter(chapter.id); });
      var label = document.createElement("span");
      label.className = "chapter-label";
      var number = document.createElement("span");
      number.className = "chapter-number";
      number.textContent = text(chapter.display_number || chapter.number);
      var title = document.createElement("span");
      title.className = "chapter-title";
      title.textContent = text(chapter.title);
      label.appendChild(number);
      label.appendChild(title);
      var status = document.createElement("span");
      status.className = "chapter-state";
      status.textContent = chapter.written ? "已写" : "未写";
      button.appendChild(label);
      button.appendChild(status);
      if (chapter.id === selectedId) button.setAttribute("aria-current", "page");
      var children = null;
      if (chapter.children_count) {
        children = document.createElement("ul");
        children.className = "chapter-children";
        children.id = "group-" + chapter.section_id;
        children.hidden = !!collapsedSections[chapter.section_id];
        var toggle = document.createElement("button");
        toggle.type = "button";
        toggle.className = "chapter-toggle";
        toggle.setAttribute("aria-controls", children.id);
        function updateToggle() {
          toggle.setAttribute("aria-expanded", String(!children.hidden));
          toggle.setAttribute("aria-label", (children.hidden ? "展开" : "折叠") + text(chapter.title));
          toggle.textContent = children.hidden ? "▸" : "▾";
        }
        toggle.addEventListener("click", function () {
          children.hidden = !children.hidden;
          collapsedSections[chapter.section_id] = children.hidden;
          updateToggle();
        });
        updateToggle();
        row.appendChild(toggle);
      } else row.classList.add("is-leaf");
      row.appendChild(button);
      item.appendChild(row);
      if (children) { item.appendChild(children); groups[chapter.section_id] = children; }
      (groups[chapter.parent_id] || list).appendChild(item);
    });
  }

  function appendOption(select, value, label) {
    var option = document.createElement("option");
    option.value = value;
    option.textContent = label;
    select.appendChild(option);
  }

  function renderChapterOverrides(settings) {
    var root = document.getElementById("chapter-overrides");
    while (root.firstChild) root.removeChild(root.firstChild);
    var chapters = state && state.chapters || [];
    var overrides = settings && settings.chapter_overrides || {};
    if (!chapters.length) {
      var empty = document.createElement("div");
      empty.className = "empty-state";
      empty.textContent = "暂无可覆盖章节";
      root.appendChild(empty);
      return;
    }
    chapters.filter(function (chapter) { return text(chapter.section_id || chapter.id) === selectedSectionId(); }).forEach(function (chapter) {
      var sectionId = text(chapter.section_id || chapter.id);
      var current = overrides[sectionId] || {};
      var item = document.createElement("fieldset");
      item.className = "chapter-override";
      var legend = document.createElement("legend");
      legend.textContent = text(chapter.display_number || chapter.number) + " " + text(chapter.title);
      item.appendChild(legend);
      var fields = document.createElement("div");
      fields.className = "chapter-override-fields";
      var targetLabel = document.createElement("label");
      targetLabel.textContent = "目标字数";
      var target = document.createElement("input");
      target.type = "number";
      target.min = "1";
      target.step = "1";
      target.inputMode = "numeric";
      target.placeholder = "继承推荐";
      target.value = current.target_words == null ? "" : text(current.target_words);
      target.dataset.overrideField = "target_words";
      targetLabel.htmlFor = "override-target-" + sectionId;
      target.id = "override-target-" + sectionId;
      targetLabel.appendChild(target);
      fields.appendChild(targetLabel);

      var detailLabel = document.createElement("label");
      detailLabel.textContent = "详细程度";
      var detail = document.createElement("select");
      detail.id = "override-detail-" + sectionId;
      detail.dataset.overrideField = "detail_level";
      appendOption(detail, "auto", "继承推荐");
      appendOption(detail, "brief", "简略");
      appendOption(detail, "standard", "标准");
      appendOption(detail, "detailed", "详细");
      detail.value = text(current.detail_level || "auto");
      detailLabel.htmlFor = detail.id;
      detailLabel.appendChild(detail);
      fields.appendChild(detailLabel);

      var uiLabel = document.createElement("label");
      uiLabel.textContent = "界面示意图";
      var ui = document.createElement("select");
      ui.id = "override-ui-" + sectionId;
      ui.dataset.overrideField = "ui_required";
      appendOption(ui, "inherit", "继承推荐");
      appendOption(ui, "true", "必配");
      appendOption(ui, "false", "不要求");
      ui.value = current.ui_required === true ? "true" : (current.ui_required === false ? "false" : "inherit");
      uiLabel.htmlFor = ui.id;
      uiLabel.appendChild(ui);
      fields.appendChild(uiLabel);

      var minLabel = document.createElement("label");
      minLabel.textContent = "最低图数";
      var min = document.createElement("input");
      min.id = "override-min-images-" + sectionId;
      min.type = "number";
      min.min = "1";
      min.max = "8";
      min.step = "1";
      min.inputMode = "numeric";
      min.placeholder = "继承推荐";
      min.value = current.min_ui_images == null ? "" : text(current.min_ui_images);
      min.dataset.overrideField = "min_ui_images";
      minLabel.htmlFor = min.id;
      minLabel.appendChild(min);
      fields.appendChild(minLabel);
      item.appendChild(fields);
      root.appendChild(item);
    });
  }

  function renderChapterPolicy() {
    var root = document.getElementById("chapter-policy");
    while (root.firstChild) root.removeChild(root.firstChild);
    var policy = state && state.chapter_policy || {};
    var hasPolicy = !!(state && state.chapter_policy);
    var actualWords = visibleWordCount(bodyEditor.value);
    var actualImages = interfaceFigureCount(selectedSectionId());
    var issues = policyIssues(policy, actualWords, actualImages);
    var heading = document.createElement("h3");
    heading.id = "chapter-policy-heading";
    heading.textContent = "当前章节建议";
    root.appendChild(heading);
    var summary = document.createElement("div");
    summary.className = "policy-summary";
    var targetText = policy.target_words == null ? "未设目标" : text(policy.target_words) + " 字";
    var range = policy.min_words == null && policy.max_words == null ? "" : "（" + text(policy.min_words || "—") + "–" + text(policy.max_words || "—") + " 字）";
    var detailLabels = { auto: "自动", brief: "简略", standard: "标准", detailed: "详细" };
    summary.textContent = "可见正文 " + actualWords + " 字 · 推荐 " + targetText + range
      + " · 详细程度：" + (detailLabels[policy.detail_level] || "自动")
      + " · 界面示意图：" + actualImages + " 张";
    root.appendChild(summary);
    if (policy.source || policy.system_section) {
      var source = document.createElement("div");
      source.className = "coverage-trace";
      var sourceLabels = {recommendation:"自动推荐",chapter:"逐章指定",global:"统一目标"};
      source.textContent = "依据：" + (sourceLabels[policy.source] || "自动推荐") + (policy.system_section ? " · 系统功能章" : "");
      root.appendChild(source);
    }
    if (policy.ui_required) {
      var uiNotice = document.createElement("div");
      uiNotice.className = "coverage-trace";
      uiNotice.textContent = "本章要求界面示意图，最低 " + Number(policy.min_ui_images || 1) + " 张；技术架构图不能替代。";
      root.appendChild(uiNotice);
    }
    if (policy.reasons && policy.reasons.length) {
      var reasons = document.createElement("ul");
      reasons.className = "policy-list";
      policy.reasons.forEach(function (reason) { var li = document.createElement("li"); li.textContent = text(reason); reasons.appendChild(li); });
      root.appendChild(reasons);
    }
    if (policy.scoring_basis && policy.scoring_basis.length) {
      var scoring = document.createElement("details");
      var scoringSummary = document.createElement("summary");
      scoringSummary.textContent = "评分依据（" + policy.scoring_basis.length + "）";
      scoring.appendChild(scoringSummary);
      var scoringList = document.createElement("ul");
      scoringList.className = "policy-list";
      policy.scoring_basis.forEach(function (basis) {
        var li = document.createElement("li");
        li.textContent = text(basis.title) + " · " + text(basis.rule_text) + (basis.inherited ? " · 父章关联" : "");
        scoringList.appendChild(li);
      });
      scoring.appendChild(scoringList);
      root.appendChild(scoring);
    }
    if (policy.expansion_requirements && policy.expansion_requirements.length) {
      var expansion = document.createElement("div");
      expansion.className = "coverage-group";
      expansion.textContent = "展开要求：" + policy.expansion_requirements.join("；");
      root.appendChild(expansion);
    }
    if (!hasPolicy) {
      var pending = document.createElement("div");
      pending.className = "coverage-trace";
      pending.textContent = "当前章节策略建议待加载，篇幅与界面图暂不能判定。";
      root.appendChild(pending);
    } else if (issues.length) {
      var issue = document.createElement("div");
      issue.className = "message message-error policy-issues";
      issue.textContent = "当前策略缺口：" + issues.join("；");
      root.appendChild(issue);
    } else {
      var ok = document.createElement("div");
      ok.className = "coverage-trace policy-ok";
      ok.textContent = "当前正文未发现篇幅或界面图缺口。";
      root.appendChild(ok);
    }
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
    var previews = document.getElementById("chapter-figures");
    while (previews.firstChild) previews.removeChild(previews.firstChild);
    var previewHeading = document.createElement("h3");
    previewHeading.textContent = "章节配图（界面示意图与技术图分开）";
    previews.appendChild(previewHeading);
    var rendered = figures.filter(function (figure) {
      return /\.(png|jpe?g)$/i.test(figure.rendered_path || "")
        && (figure.state === "rendered" || figure.state === "reviewed");
    });
    if (!rendered.length) {
      var noPreview = document.createElement("p");
      noPreview.className = "meta-text";
      noPreview.textContent = "本章暂无已渲染配图。";
      previews.appendChild(noPreview);
    }
    rendered.forEach(function (figure) {
      var card = document.createElement("figure");
      var link = document.createElement("a");
      link.href = "/api/file?path=" + encodeURIComponent(figure.rendered_path);
      link.target = "_blank";
      link.rel = "noopener";
      link.setAttribute("aria-label", "查看大图：" + text(figure.title));
      var image = document.createElement("img");
      image.src = link.href;
      image.alt = text(figure.alt_text || figure.title);
      image.loading = "lazy";
      image.onerror = function () {
        image.hidden = true;
        var error = document.createElement("p");
        error.className = "message message-error";
        error.textContent = "图片加载失败，请核对图表文件。";
        link.appendChild(error);
      };
      link.appendChild(image);
      card.appendChild(link);
      var caption = document.createElement("figcaption");
      caption.textContent = text(figure.title) + " · " + text(figure.caption);
      card.appendChild(caption);
      if (figure.source_path) {
        var source = document.createElement("a");
        source.href = "/api/file?path=" + encodeURIComponent(figure.source_path);
        source.target = "_blank";
        source.rel = "noopener";
        source.textContent = /\.svg$/i.test(figure.source_path) ? "查看 SVG 源文件" : "查看图源或生成规格";
        card.appendChild(source);
      }
      previews.appendChild(card);
    });
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

  function renderPolicyChapter(chapter) {
    var item = document.createElement("li");
    item.className = "policy-chapter";
    item.dataset.sectionId = chapter.section_id;
    var navChapter = (state.chapters || []).find(function (row) { return row.section_id === chapter.section_id; });
    var title = document.createElement(navChapter ? "button" : "strong");
    title.textContent = navChapter ? navChapter.display_number + " " + navChapter.title : text(chapter.section_id);
    if (navChapter) {
      title.type = "button";
      title.className = "policy-chapter-link";
      title.setAttribute("aria-label", "打开章节：" + title.textContent);
      title.addEventListener("click", function () { selectChapter(navChapter.id); });
    }
    item.appendChild(title);
    var metrics = document.createElement("dl");
    metrics.className = "policy-metrics";
    [["实际字数", chapter.actual_words == null ? "未检查" : chapter.actual_words + " 字"],
      ["目标范围", chapter.min_words == null || chapter.max_words == null ? "未设目标" : chapter.min_words + "–" + chapter.max_words + " 字"]].forEach(function (metric) {
      var cell = document.createElement("div");
      var label = document.createElement("dt");
      label.textContent = metric[0];
      var value = document.createElement("dd");
      value.textContent = metric[1];
      cell.appendChild(label);
      cell.appendChild(value);
      metrics.appendChild(cell);
    });
    item.appendChild(metrics);
    var lengthLabels = { not_set: "未设篇幅目标", too_short: "篇幅不足", too_long: "超出篇幅", in_range: "篇幅符合" };
    var length = document.createElement("p");
    length.className = "policy-result";
    length.textContent = chapter.actual_words == null ? "字数未检查" : lengthLabels[chapter.length_status] || "篇幅待复核";
    if (chapter.actual_words != null && chapter.length_status === "too_short" && chapter.min_words != null) {
      length.textContent = (chapter.length_required ? "需补 " : "建议补 ") + Math.max(0, chapter.min_words - chapter.actual_words) + " 字";
    } else if (chapter.actual_words != null && chapter.length_status === "too_long" && chapter.max_words != null) {
      length.textContent = "超出 " + Math.max(0, chapter.actual_words - chapter.max_words) + " 字" + (chapter.length_required ? "" : " · 建议精简");
    }
    if (chapter.length_status === "too_short" || chapter.length_status === "too_long") {
      length.classList.add(chapter.length_required ? "policy-result-error" : "policy-result-warning");
    }
    item.appendChild(length);
    var ui = document.createElement("p");
    ui.className = "policy-result";
    if (chapter.ui_status === "not_required") ui.textContent = "无需界面图";
    else if (chapter.ui_status === "missing" || chapter.ui_status === "complete") {
      ui.textContent = "界面图 " + text(chapter.ui_image_count) + "/" + text(chapter.min_ui_images) + " 张";
      if (chapter.ui_status === "missing") {
        ui.textContent += " · 缺 " + Math.max(0, chapter.min_ui_images - chapter.ui_image_count) + " 张";
        ui.classList.add("policy-result-error");
      } else ui.textContent += " · 已核验";
    } else ui.textContent = "界面图待复核";
    item.appendChild(ui);
    var details = document.createElement("details");
    details.className = "policy-basis";
    var summary = document.createElement("summary");
    summary.textContent = "检查依据";
    details.appendChild(summary);
    var identity = document.createElement("p");
    identity.textContent = "章节标识：" + text(chapter.section_id);
    details.appendChild(identity);
    var sources = { chapter: "逐章指定", recommendation: "自动推荐", global: "全局指定" };
    var basis = document.createElement("p");
    basis.textContent = "篇幅依据：" + (sources[chapter.source] || "未确认")
      + (chapter.scoring_ids && chapter.scoring_ids.length ? "；评分项：" + chapter.scoring_ids.join("、") : "");
    details.appendChild(basis);
    (chapter.issues || []).forEach(function (issue) {
      var original = document.createElement("p");
      original.textContent = text(issue);
      details.appendChild(original);
    });
    item.appendChild(details);
    return item;
  }

  function renderWritingPolicy(root, chapters) {
    if (!chapters.length) return;
    var group = document.createElement("section");
    group.className = "coverage-group writing-policy-coverage";
    var title = document.createElement("h3");
    title.textContent = "篇幅与界面图检查（" + chapters.length + "章）";
    group.appendChild(title);
    var note = document.createElement("p");
    note.className = "policy-scope";
    note.textContent = "仅检查篇幅与配图；正文、评分和证据另行复核。未设目标的章节不判断篇幅。";
    group.appendChild(note);
    var buckets = [
      { title: "需整改", kind: "error", chapters: [], count: 0 },
      { title: "建议调整", kind: "warning", chapters: [], count: 0 },
      { title: "无缺口", kind: "neutral", chapters: [], count: 0 }
    ];
    chapters.forEach(function (chapter) {
      var blocking = chapter.blocking_issues || [];
      var issues = chapter.issues || [];
      var unchecked = chapter.actual_words == null || !chapter.length_status || !chapter.ui_status;
      var bucket = buckets[blocking.length ? 0 : issues.length || unchecked ? 1 : 2];
      bucket.chapters.push(chapter);
      bucket.count += blocking.length ? blocking.length : issues.length;
    });
    buckets.forEach(function (bucket) {
      var details = document.createElement("details");
      details.className = "policy-bucket policy-bucket-" + bucket.kind;
      details.open = bucket.kind === "error" && bucket.chapters.length > 0;
      var summary = document.createElement("summary");
      var label = document.createElement("strong");
      label.textContent = bucket.title;
      summary.appendChild(label);
      var count = document.createElement("span");
      count.className = "policy-bucket-count";
      count.textContent = bucket.chapters.length + "章" + (bucket.count ? " · " + bucket.count + (bucket.kind === "error" ? "项必改" : "项建议") : "");
      summary.appendChild(count);
      details.appendChild(summary);
      if (bucket.chapters.length) {
        var list = document.createElement("ul");
        list.className = "policy-chapter-list";
        bucket.chapters.forEach(function (chapter) { list.appendChild(renderPolicyChapter(chapter)); });
        details.appendChild(list);
      } else {
        var empty = document.createElement("p");
        empty.className = "policy-scope";
        empty.textContent = "暂无此类章节";
        details.appendChild(empty);
      }
      group.appendChild(details);
    });
    root.appendChild(group);
  }

  function renderCoverageMessages(root, coverage) {
    var auditWarnings = [];
    [["错误", coverage.errors || []], ["提示", coverage.warnings || []]].forEach(function (entry) {
      entry[1].forEach(function (value) {
        var original = text(value);
        var match = original.match(/^([^:]+): 历史图源没有CLI render_record，不能声称通过CLI审计$/);
        if (entry[0] === "提示" && match) {
          auditWarnings.push({ id: match[1], original: original });
          return;
        }
        var message = document.createElement("p");
        message.className = "coverage-trace" + (entry[0] === "错误" ? " coverage-error" : "");
        message.textContent = entry[0] + "：" + original;
        root.appendChild(message);
      });
    });
    if (!auditWarnings.length) return;
    var group = document.createElement("section");
    group.className = "coverage-group coverage-audit";
    var title = document.createElement("h3");
    title.textContent = "图源审计（" + auditWarnings.length + "）";
    group.appendChild(title);
    var notice = document.createElement("p");
    notice.className = "audit-notice";
    notice.textContent = "历史图源缺少渲染记录，暂不能确认工具执行审计。";
    group.appendChild(notice);
    var figures = state.visuals && state.visuals.data && state.visuals.data.figures || [];
    auditWarnings.forEach(function (warning) {
      var figure = figures.find(function (row) { return row.id === warning.id; });
      var item = document.createElement("div");
      item.className = "audit-item";
      var name = document.createElement("strong");
      name.textContent = figure ? text(figure.title || figure.id) : warning.id;
      item.appendChild(name);
      var status = document.createElement("p");
      status.className = "audit-status";
      status.textContent = "记录待补";
      item.appendChild(status);
      if (figure && figure.source_path) {
        var link = document.createElement("a");
        link.href = "/api/file?path=" + encodeURIComponent(figure.source_path);
        link.target = "_blank";
        link.rel = "noopener";
        link.textContent = "查看图源";
        item.appendChild(link);
      }
      var details = document.createElement("details");
      var summary = document.createElement("summary");
      summary.textContent = "查看原始提示";
      details.appendChild(summary);
      var original = document.createElement("p");
      original.className = "audit-original";
      original.textContent = warning.original;
      details.appendChild(original);
      item.appendChild(details);
      group.appendChild(item);
    });
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
    renderWritingPolicy(root, coverage.writing_policy && coverage.writing_policy.chapters || []);
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
    renderCoverageMessages(root, coverage);
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
    document.getElementById("word-count").textContent = visibleWordCount(bodyEditor.value) + " 可见字";
    renderChapterPolicy();
    renderReferences();
    renderReviewActions();
    renderAiScoring();
  }

  function applySettings(settings) {
    settings = settings || {};
    var visuals = settings.visuals || {};
    document.getElementById("tone-setting").value = text(settings.tone || "plain_chinese");
    document.getElementById("target-words-setting").value = settings.target_words || "";
    document.getElementById("length-mode-setting").value = text(settings.length_mode || "auto_scoring");
    document.getElementById("length-tolerance-setting").value = settings.length_tolerance == null ? "0.2" : text(settings.length_tolerance);
    document.getElementById("execution-mode-setting").value = text(settings.execution_mode || "sequential");
    document.getElementById("max-parallel-setting").value = text(settings.max_parallel || 1);
    document.getElementById("visuals-enabled-setting").checked = visuals.enabled !== false;
    document.getElementById("diagram-engine-setting").value = text(visuals.diagram_engine || "auto");
    document.getElementById("diagram-theme-setting").value = text(visuals.diagram_theme || "reference");
    document.getElementById("diagram-format-setting").value = text(visuals.diagram_format || "svg");
    document.getElementById("layout-template-setting").value = text(visuals.layout_template || "auto");
    document.getElementById("architecture-layers-setting").value = visuals.architecture_layers == null ? "" : text(visuals.architecture_layers);
    document.getElementById("image-mode-setting").value = text(visuals.image_mode || "host");
    document.getElementById("system-ui-policy-setting").value = text(visuals.system_ui_policy || "auto");
    document.getElementById("min-ui-images-setting").value = text(visuals.min_ui_images || 1);
    document.getElementById("visual-tool-setting").value = text(visuals.tool || "auto");
    document.getElementById("visual-model-setting").value = text(visuals.model || "");
    document.getElementById("visual-style-setting").value = text(visuals.style || "enterprise_concept");
    document.getElementById("visual-aspect-ratio-setting").value = text(visuals.aspect_ratio || "16:9");
    document.getElementById("visual-max-images-setting").value = text(visuals.max_images || 2);
    document.getElementById("target-words-hint").textContent = document.getElementById("length-mode-setting").value === "fixed"
      ? "所有未覆盖章节使用此基准"
      : "自动模式按评分复杂度缩放";
    renderChapterOverrides(settings);
    updateVisualFieldState();
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
      settingsDirty = false;
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
    if (saveInFlight || workspaceBusy) return;
    if (settingsDirty) { showError("请先保存或放弃写作设置，再切换章节。"); return; }
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

  function collectChapterOverrides(existing) {
    var overrides = clone(existing || {}) || {};
    (state && state.chapters || []).forEach(function (chapter) {
      var sectionId = text(chapter.section_id || chapter.id);
      var target = document.getElementById("override-target-" + sectionId);
      var detail = document.getElementById("override-detail-" + sectionId);
      var ui = document.getElementById("override-ui-" + sectionId);
      var min = document.getElementById("override-min-images-" + sectionId);
      if (!target || !detail || !ui || !min) return;
      var existed = Object.prototype.hasOwnProperty.call(overrides, sectionId);
      var blank = !target.value && detail.value === "auto" && ui.value === "inherit" && !min.value;
      if (!existed && blank) return;
      var current = clone(overrides[sectionId] || {}) || {};
      current.target_words = target.value ? Number(target.value) : null;
      current.detail_level = detail.value || "auto";
      current.ui_required = ui.value === "inherit" ? null : ui.value === "true";
      if (min.value) current.min_ui_images = Number(min.value);
      else delete current.min_ui_images;
      overrides[sectionId] = current;
    });
    return overrides;
  }

  function saveSettings(event) {
    event.preventDefault();
    var target = document.getElementById("target-words-setting").value;
    var request = clone(state && state.settings || {}) || {};
    delete request.revision;
    delete request.sha256;
    request.tone = document.getElementById("tone-setting").value;
    request.target_words = target ? Number(target) : null;
    request.length_mode = document.getElementById("length-mode-setting").value;
    request.length_tolerance = Number(document.getElementById("length-tolerance-setting").value || 0.2);
    request.execution_mode = document.getElementById("execution-mode-setting").value;
    request.max_parallel = Number(document.getElementById("max-parallel-setting").value);
    request.chapter_overrides = collectChapterOverrides(request.chapter_overrides);
    request.visuals = Object.assign({}, request.visuals || {}, { enabled: document.getElementById("visuals-enabled-setting").checked,
      diagram_engine: document.getElementById("diagram-engine-setting").value,
      diagram_theme: document.getElementById("diagram-theme-setting").value,
      diagram_format: document.getElementById("diagram-format-setting").value,
      layout_template: document.getElementById("layout-template-setting").value,
      architecture_layers: document.getElementById("architecture-layers-setting").value
        ? Number(document.getElementById("architecture-layers-setting").value) : null,
      image_mode: document.getElementById("image-mode-setting").value,
      system_ui_policy: document.getElementById("system-ui-policy-setting").value,
      min_ui_images: Number(document.getElementById("min-ui-images-setting").value || 1),
      tool: document.getElementById("visual-tool-setting").value,
      model: document.getElementById("visual-model-setting").value,
      style: document.getElementById("visual-style-setting").value,
      aspect_ratio: document.getElementById("visual-aspect-ratio-setting").value,
      max_images: Number(document.getElementById("visual-max-images-setting").value) });
    Object.assign(request, {
      expected_revision: state && state.settings ? state.settings.revision : 0,
      expected_sha256: state && state.settings ? state.settings.sha256 : ""
    });
    setBusy(true);
    fetch("/api/settings", { method: "POST", credentials: "same-origin", headers: { "Content-Type": "application/json" }, body: JSON.stringify(request) })
      .then(function (response) { return response.json().then(function (data) { if (!response.ok) { var error = new Error(data.error && data.error.message || "设置保存失败"); error.code = data.error && data.error.code; throw error; } return data; }); })
      .then(function () { settingsDirty = false; setStatus("设置已保存并重载", "success"); return load(selectedId); })
      .catch(function (error) { setStatus(error.code === "stale_settings" ? "设置发生冲突" : "设置保存失败", "error"); showError(error.message); })
      .finally(function () { setBusy(false); updateVisualFieldState(); });
  }

  bodyEditor.addEventListener("input", function () {
    unsavedBuffers[selectedId] = bodyEditor.value;
    dirty = true;
    discardButton.disabled = false;
    document.getElementById("word-count").textContent = visibleWordCount(bodyEditor.value) + " 可见字";
    renderChapterPolicy();
    setStatus("有未保存修改", "warning");
    renderReviewActions();
    renderAiScoring();
  });
  saveButton.addEventListener("click", save);
  document.getElementById("review-action-scope").addEventListener("change", renderReviewActions);
  document.querySelectorAll("[data-review-action]").forEach(function (button) {
    button.addEventListener("click", function () { requestReviewAction(button.dataset.reviewAction); });
  });
  discardButton.addEventListener("click", discardCurrent);
  reloadButton.addEventListener("click", function () {
    if (!hasUnsavedWork() || window.confirm("重载会丢弃当前未保存正文和设置，继续吗？")) {
      delete unsavedBuffers[selectedId]; dirty = false; settingsDirty = false; load(selectedId);
    }
  });
  document.getElementById("visuals-enabled-setting").addEventListener("change", updateVisualFieldState);
  document.getElementById("diagram-engine-setting").addEventListener("change", updateVisualFieldState);
  document.getElementById("length-mode-setting").addEventListener("change", function () {
    document.getElementById("target-words-hint").textContent = this.value === "fixed"
      ? "所有未覆盖章节使用此基准"
      : "自动模式按评分复杂度缩放";
  });
  settingsForm.addEventListener("submit", saveSettings);
  settingsForm.addEventListener("input", function () {
    settingsDirty = true;
    setStatus("有未保存修改", "warning");
    renderReviewActions(); renderAiScoring();
  });
  settingsForm.addEventListener("change", function () {
    settingsDirty = true;
    setStatus("有未保存修改", "warning");
    renderReviewActions(); renderAiScoring();
  });
  document.getElementById("ai-score-button").addEventListener("click", function () { createAiScoringTask("score"); });
  document.getElementById("ai-report-button").addEventListener("click", openAiReport);
  document.getElementById("ai-refresh-button").addEventListener("click", refreshAiScoring);
  document.getElementById("ai-improve-button").addEventListener("click", function () { createAiScoringTask("improve"); });
  document.getElementById("ai-show-all-scoring").addEventListener("change", function () {
    showAllScoringRows = this.checked;
    renderAiScoring();
  });
  document.getElementById("theme-button").addEventListener("click", function () { document.documentElement.setAttribute("data-theme", document.documentElement.getAttribute("data-theme") === "dark" ? "light" : "dark"); });
  window.addEventListener("beforeunload", function (event) { if (hasUnsavedWork() || saveInFlight) { event.preventDefault(); event.returnValue = ""; } });
  load(null);
}());
