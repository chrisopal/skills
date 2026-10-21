/* Shared opt-in adapter. Load generated design-config.js then this file before CSS. */
(function () {
  'use strict';
  var data = window.__UI_DESIGN_CONFIG__;
  if (!data) throw new Error('Load generated design-config.js before design-system.js');
  var root = document.documentElement;
  var key = 'enterprise-ui-design-preferences-v1';
  var axes = ['brand', 'profile', 'theme', 'density'];
  var attrs = { brand: 'uiBrand', profile: 'uiProfile', theme: 'theme', density: 'density' };
  var active, listeners = [];
  var requested = {};
  function resolve(input) {
    var normalized = {}, warnings = [];
    axes.forEach(function (axis) {
      var supported = data.supported[{ brand: 'brands', profile: 'profiles', theme: 'themes', density: 'densities' }[axis]];
      var choices = Array.isArray(supported) ? supported : Object.keys(supported);
      normalized[axis] = choices.includes(input[axis]) ? input[axis] : data.defaults[axis];
      if (input[axis] !== undefined && input[axis] !== normalized[axis]) warnings.push(axis + ': unknown; default used');
    });
    var combination = data.combinations.find(function (item) { return axes.every(function (axis) { return item.requested[axis] === normalized[axis]; }); });
    return { requested: normalized, effective: combination.effective, values: combination.values,
      components: combination.components, semantics: combination.semantics, layout: combination.layout,
      warnings: warnings.concat(combination.fallbacks) };
  }
  function transfer(target, config) {
    Object.keys(config.values).forEach(function (name) { target.style.setProperty('--ui-' + name, config.values[name]); });
    axes.forEach(function (axis) { target.dataset[attrs[axis]] = config.requested[axis]; });
    target.dataset.uiEffectiveProfile = config.effective.profile;
  }
  function updateControls() {
    axes.forEach(function (axis) { var control = document.getElementById(axis + '-select'); if (control) control.value = requested[axis]; });
  }
  function apply(patch, options) {
    options = options || {};
    active = resolve(Object.assign({}, requested, patch)); requested = active.requested;
    transfer(root, active); updateControls();
    var persisted = true;
    if (options.persist !== false) {
      try { localStorage.setItem(key, JSON.stringify(requested)); } catch (_) { persisted = false; }
    }
    listeners.forEach(function (listener) { listener(active); });
    window.dispatchEvent(new CustomEvent('ui-design-change', { detail: active }));
    return { config: active, persisted: persisted };
  }
  var initial = {};
  try { initial = JSON.parse(localStorage.getItem(key) || localStorage.getItem('enterprise-ui-reference-workbench-preferences-v1') || '{}') || {}; } catch (_) { /* generated defaults */ }
  if (typeof initial !== 'object' || Array.isArray(initial)) initial = {};
  axes.forEach(function (axis) { if (initial[axis] === undefined && root.dataset[attrs[axis]]) initial[axis] = root.dataset[attrs[axis]]; });
  window.EnterpriseDesign = {
    apply: apply,
    get: function () { return active; },
    resolve: resolve,
    // For a different nested provider/Shadow host, transfer computed effective values explicitly.
    transfer: function (target, override) { transfer(target, resolve(Object.assign({}, requested, override))); },
    bridge: function (callback) { listeners.push(callback); callback(active); return function () { listeners = listeners.filter(function (item) { return item !== callback; }); }; }
  };
  apply(initial, { persist: false });
  document.addEventListener('DOMContentLoaded', function () {
    updateControls();
    axes.forEach(function (axis) { var control = document.getElementById(axis + '-select'); if (control) control.addEventListener('change', function () { var patch = {}; patch[axis] = control.value; var result = apply(patch); if (!result.persisted) control.setAttribute('title', '偏好仅本次生效，浏览器存储不可用。'); }); });
  });
}());
