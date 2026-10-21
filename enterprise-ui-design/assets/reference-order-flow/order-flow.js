(function () {
  'use strict';

  var stages = [
    { id: 'registration', name: '登记' },
    { id: 'acceptance', name: '受理' },
    { id: 'testing', name: '检测复核' },
    { id: 'report-review', name: '报告审核' },
    { id: 'delivery', name: '交付' },
    { id: 'archive', name: '归档' }
  ];

  var scenarios = {
    'report-pending': {
      status: '报告待审',
      tone: 'warning',
      task: {
        title: '综合报告技术审核',
        scope: '样品 A、B · 有机物、金属元素',
        owner: '质量负责人 · 当前办理人',
        prerequisite: '检测复核已完成，报告草稿已生成',
        reason: '报告草稿待技术审核，查看样板报告与依据。',
        action: '查看审核资料',
        mode: '待办理'
      },
      stageStatuses: ['complete', 'complete', 'complete', 'current', 'pending', 'pending'],
      executionNote: '两个样品均已完成检测复核',
      execution: [
        { name: '样品 A', meta: '有机物 · 金属元素', completed: 5, total: 5, status: '检测复核完成', tone: 'success' },
        { name: '样品 B', meta: '有机物 · 金属元素', completed: 5, total: 5, status: '检测复核完成', tone: 'success' }
      ],
      history: ['10-17 16:20 检测复核完成 · 样品 A、B', '10-18 09:10 报告草稿生成 · 综合报告']
    },
    'partial-testing': {
      status: '部分检测完成',
      tone: 'warning',
      task: {
        title: '完成检测复核',
        scope: '样品 A、B · 两条检测执行线',
        owner: '检测组 · 样品 B 待完成',
        prerequisite: '样品 A 复核完成；样品 B 仍有金属元素项目',
        reason: '执行线进度不同，未完成项会阻塞报告审核。',
        action: '查看检测任务',
        mode: '进行中'
      },
      stageStatuses: ['complete', 'complete', 'current', 'pending', 'pending', 'pending'],
      executionNote: '样品 B 的未完成项目仍是整单前置条件',
      execution: [
        { name: '样品 A', meta: '有机物 · 金属元素', completed: 5, total: 5, status: '检测复核完成', tone: 'success' },
        { name: '样品 B', meta: '有机物完成 · 金属元素复核中', completed: 3, total: 5, status: '复核中', tone: 'current' }
      ],
      history: ['10-18 08:40 样品 A 检测复核完成', '10-18 09:05 样品 B 金属元素复核中']
    },
    'returned-correction': {
      status: '退回补正',
      tone: 'danger',
      task: {
        title: '补正报告依据',
        scope: '样品 A、B · 综合报告第 3 节',
        owner: '检测组 · 报告审核退回',
        prerequisite: '补充原始记录并重新提交技术审核',
        reason: '报告审核发现依据缺失，后续交付与归档保持未开始。',
        action: '查看退回原因',
        mode: '需补正'
      },
      stageStatuses: ['complete', 'complete', 'complete', 'returned', 'pending', 'pending'],
      executionNote: '退回不点亮后续阶段',
      execution: [
        { name: '样品 A', meta: '原始记录需补充签名', status: '补材料中 · 完成度未知', tone: 'danger' },
        { name: '样品 B', meta: '结果数据已锁定', completed: 5, total: 5, status: '检测复核完成', tone: 'success' }
      ],
      history: ['10-17 16:20 检测复核完成 · 样品 A、B', '10-18 10:05 报告审核退回 · 需补充原始记录签名']
    },
    'waiting-reviewer': {
      status: '等待他人',
      tone: 'warning',
      task: {
        title: '等待质量负责人审核',
        scope: '样品 A、B · 综合报告',
        owner: '质量负责人 · 当前办理人之外',
        prerequisite: '完成技术审核与签发后才能进入交付',
        reason: '订单正在等待他人办理，当前查看者没有提交入口。',
        action: '查看等待详情',
        mode: '只读等待',
        readonly: true
      },
      stageStatuses: ['complete', 'complete', 'complete', 'waiting', 'pending', 'pending'],
      executionNote: '检测证据齐全，阻塞点在审核交接',
      execution: [
        { name: '样品 A', meta: '有机物 · 金属元素', completed: 5, total: 5, status: '检测复核完成', tone: 'success' },
        { name: '样品 B', meta: '有机物 · 金属元素', completed: 5, total: 5, status: '检测复核完成', tone: 'success' }
      ],
      history: ['10-17 16:20 检测复核完成 · 样品 A、B', '10-18 09:30 已交接质量负责人 · 等待审核']
    },
    'read-failure': {
      status: '读取失败',
      tone: 'danger',
      task: {
        title: '恢复检测结果读取',
        scope: '样品 B · 金属元素执行线',
        owner: '系统支持 · 需要重新读取',
        prerequisite: '恢复数据读取后重新执行检测复核',
        reason: '读取检测结果失败，未知数据不能显示为成功，也不能进入报告审核。',
        action: '查看失败详情',
        mode: '读取异常'
      },
      stageStatuses: ['complete', 'complete', 'error', 'pending', 'pending', 'pending'],
      executionNote: '失败事实保留上下文，未生成成功结果',
      execution: [
        { name: '样品 A', meta: '有机物 · 金属元素', completed: 5, total: 5, status: '检测复核完成', tone: 'success' },
        { name: '样品 B', meta: '金属元素结果读取失败', status: '失败 · 完成度未知', tone: 'danger' }
      ],
      history: ['10-18 08:40 样品 A 检测复核完成', '10-18 09:12 样品 B 结果读取失败 · 未确认完成']
    },
    archived: {
      status: '已归档',
      tone: 'success',
      task: {
        title: '查看归档证据',
        scope: '订单 ORD-2026-1018 · 冻结综合报告',
        owner: '只读查看者',
        prerequisite: '归档成品已冻结，历史数据按成品读取',
        reason: '订单已归档，当前页面仅提供事实与成品查看。',
        action: '查看归档事实',
        mode: '只读归档',
        readonly: true
      },
      stageStatuses: ['complete', 'complete', 'complete', 'complete', 'complete', 'complete'],
      executionNote: '历史成品和范围均已冻结',
      execution: [
        { name: '样品 A', meta: '有机物 · 金属元素', completed: 5, total: 5, status: '归档成品已锁定', tone: 'success' },
        { name: '样品 B', meta: '有机物 · 金属元素', completed: 5, total: 5, status: '归档成品已锁定', tone: 'success' }
      ],
      history: ['10-18 11:20 综合报告签发完成', '10-18 11:25 订单归档 · 成品与证据冻结']
    }
  };

  var elements = {};
  var state = { scenarioId: 'report-pending', trigger: null };

  function byId(id) {
    return document.getElementById(id);
  }

  function createElement(tagName, className, content) {
    var element = document.createElement(tagName);
    if (className) element.className = className;
    if (content !== undefined) element.textContent = content;
    return element;
  }

  function renderStage(stage, status, index) {
    var item = createElement('li', 'stage-item');
    item.dataset.status = status;
    item.dataset.connector = status === 'complete' && index < stages.length - 1 ? 'complete' : 'pending';
    if (status === 'current' || status === 'returned' || status === 'waiting' || status === 'error') {
      item.setAttribute('aria-current', 'step');
    }

    var node = createElement('span', 'stage-node');
    node.setAttribute('aria-hidden', 'true');
    node.textContent = {
      complete: '✓', current: '●', returned: '!', waiting: '…', error: '×', pending: '○'
    }[status] || '○';
    item.appendChild(node);

    var copy = createElement('span', 'stage-copy');
    copy.appendChild(createElement('span', 'stage-name', stage.name));
    copy.appendChild(createElement('span', 'stage-status', {
      complete: '已完成', current: '进行中', returned: '退回补正', waiting: '等待他人', error: '读取失败', pending: '未开始'
    }[status] || '待确认'));
    item.appendChild(copy);
    item.setAttribute('aria-label', stage.name + '：' + (copy.lastChild.textContent || '待确认'));
    return item;
  }

  function renderExecution(line) {
    var item = createElement('div', 'execution-line');
    item.dataset.tone = line.tone;
    var displayStatus = line.status;

    var label = createElement('div');
    label.appendChild(createElement('span', 'execution-line__name', line.name));
    label.appendChild(createElement('span', 'execution-line__meta', line.meta));
    item.appendChild(label);

    var progress = createElement('div', 'execution-line__progress');
    var hasKnownCount = Number.isFinite(line.completed) && Number.isFinite(line.total) && line.total > 0;
    if (hasKnownCount) {
      var percent = Math.round((line.completed / line.total) * 100);
      var track = createElement('div', 'progress-track');
      track.dataset.tone = line.tone;
      track.setAttribute('role', 'progressbar');
      track.setAttribute('aria-valuemin', '0');
      track.setAttribute('aria-valuemax', String(line.total));
      track.setAttribute('aria-valuenow', String(line.completed));
      track.setAttribute('aria-label', line.name + '完成度 ' + line.completed + ' / ' + line.total);
      var fill = createElement('span');
      fill.style.width = percent + '%';
      track.appendChild(fill);
      progress.appendChild(track);
      displayStatus = line.status + ' · ' + line.completed + ' / ' + line.total + ' 项 · ' + percent + '%';
    } else {
      progress.appendChild(createElement('span', 'progress-unknown', '完成度未知'));
    }
    item.appendChild(progress);

    item.appendChild(createElement('span', 'execution-line__status', displayStatus));
    return item;
  }

  function renderFacts(target, facts) {
    while (target.firstChild) target.removeChild(target.firstChild);
    facts.forEach(function (fact) {
      var item = createElement('div');
      item.appendChild(createElement('dt', null, fact[0]));
      item.appendChild(createElement('dd', null, fact[1]));
      target.appendChild(item);
    });
  }

  function renderScenario() {
    var scenario = scenarios[state.scenarioId];
    elements.orderStatus.textContent = scenario.status;
    elements.orderStatus.dataset.tone = scenario.tone;
    elements.taskTitle.textContent = scenario.task.title;
    elements.taskScope.textContent = scenario.task.scope;
    elements.taskOwner.textContent = scenario.task.owner;
    elements.taskPrerequisite.textContent = scenario.task.prerequisite;
    elements.taskSubflow.textContent = '技术审核 → 签发 → 交付';
    elements.taskReason.textContent = scenario.task.reason;
    elements.taskMode.textContent = scenario.task.mode;
    elements.taskMode.dataset.tone = scenario.tone;
    elements.taskMode.dataset.readonly = scenario.task.readonly ? 'true' : 'false';
    elements.taskButton.textContent = scenario.task.action;
    elements.taskButton.className = 'button ' + (scenario.task.readonly ? 'button--secondary' : 'button--primary');
    elements.executionNote.textContent = scenario.executionNote;

    while (elements.stageList.firstChild) elements.stageList.removeChild(elements.stageList.firstChild);
    stages.forEach(function (stage, index) {
      elements.stageList.appendChild(renderStage(stage, scenario.stageStatuses[index], index));
    });
    while (elements.executionList.firstChild) elements.executionList.removeChild(elements.executionList.firstChild);
    scenario.execution.forEach(function (line) { elements.executionList.appendChild(renderExecution(line)); });
    while (elements.historyList.firstChild) elements.historyList.removeChild(elements.historyList.firstChild);
    scenario.history.forEach(function (entry) { elements.historyList.appendChild(createElement('li', null, entry)); });
  }

  function setTheme(theme) {
    document.documentElement.dataset.theme = theme;
  }

  function setProfile(profile) {
    document.documentElement.dataset.uiProfile = profile;
  }

  function setDensity(density) {
    document.documentElement.dataset.density = density;
  }

  function setDirection(direction) {
    if (direction === 'vertical') document.documentElement.dataset.direction = 'vertical';
    else delete document.documentElement.dataset.direction;
  }

  function currentStageLabel(scenario) {
    var currentIndex = scenario.stageStatuses.findIndex(function (status) {
      return status === 'current' || status === 'returned' || status === 'waiting' || status === 'error';
    });
    if (currentIndex >= 0) return stages[currentIndex].name;
    if (scenario.stageStatuses.every(function (status) { return status === 'complete'; })) return '归档';
    return '待确认';
  }

  function openDetails() {
    var scenario = scenarios[state.scenarioId];
    state.trigger = document.activeElement;
    elements.dialogTitle.textContent = scenario.task.title;
    renderFacts(elements.dialogFacts, [
      ['样例状态', scenario.status],
      ['当前阶段', currentStageLabel(scenario)],
      ['办理方式', scenario.task.readonly ? '仅查看' : '查看模拟事实'],
      ['订单', 'ORD-2026-1018']
    ]);
    elements.dialogScopeText.textContent = scenario.task.scope + '。订单范围：2 份样品，综合报告。';
    elements.detailDialog.showModal();
  }

  function closeDetails() {
    elements.detailDialog.close();
  }

  function cacheElements() {
    elements.scenarioSelect = byId('scenario-select');
    elements.profileSelect = byId('profile-select');
    elements.themeSelect = byId('theme-select');
    elements.densitySelect = byId('density-select');
    elements.directionSelect = byId('direction-select');
    elements.orderStatus = byId('order-status');
    elements.taskTitle = byId('task-title');
    elements.taskScope = byId('task-scope');
    elements.taskOwner = byId('task-owner');
    elements.taskPrerequisite = byId('task-prerequisite');
    elements.taskSubflow = byId('task-subflow');
    elements.taskReason = byId('task-reason');
    elements.taskMode = byId('task-mode');
    elements.taskButton = byId('task-action-button');
    elements.stageList = byId('stage-list');
    elements.executionNote = byId('execution-note');
    elements.executionList = byId('execution-list');
    elements.historyList = byId('history-list');
    elements.detailDialog = byId('detail-dialog');
    elements.dialogTitle = byId('dialog-title');
    elements.dialogFacts = byId('dialog-facts');
    elements.dialogScopeText = byId('dialog-scope-text');
  }

  function bindEvents() {
    elements.scenarioSelect.addEventListener('change', function (event) {
      state.scenarioId = event.target.value;
      renderScenario();
    });
    elements.profileSelect.addEventListener('change', function (event) { setProfile(event.target.value); });
    elements.themeSelect.addEventListener('change', function (event) { setTheme(event.target.value); });
    elements.densitySelect.addEventListener('change', function (event) { setDensity(event.target.value); });
    elements.directionSelect.addEventListener('change', function (event) { setDirection(event.target.value); });
    elements.taskButton.addEventListener('click', openDetails);
    byId('dialog-close').addEventListener('click', closeDetails);
    elements.detailDialog.addEventListener('close', function () {
      if (state.trigger && typeof state.trigger.focus === 'function') state.trigger.focus();
      state.trigger = null;
    });
  }

  function initialize() {
    cacheElements();
    bindEvents();
    elements.profileSelect.value = 'enterprise';
    elements.themeSelect.value = 'light';
    elements.densitySelect.value = 'standard';
    elements.directionSelect.value = 'auto';
    renderScenario();
  }

  document.addEventListener('DOMContentLoaded', initialize);
}());
