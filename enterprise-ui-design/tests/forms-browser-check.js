/* Run through playwright-cli run-code --filename after opening assets/reference-forms.
   Optional: set window.__FORMS_EVIDENCE_DIR__ to an existing absolute local directory.
   Local fixtures only; no host API, target-user study or customer acceptance claim. */
async (page) => {
  try {
  const base = new URL('/assets/reference-forms/', page.url()).href;
  const evidenceDir = await page.evaluate(() => window.__FORMS_EVIDENCE_DIR__ || null);
  const errors = [], matrix = [], evidence = [];
  let assertions = 0;
  const check = (ok, message) => { assertions++; if (!ok) throw new Error(message); };
  const frame = () => page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
  const go = async view => { await page.evaluate(value => { location.hash = value; }, view); await frame(); };
  const saved = async id => check((await page.locator(id).innerText()).includes('本机'), id + ' has local save feedback');
  page.on('pageerror', error => errors.push(error.message));
  await page.goto(base);
  await page.evaluate(() => {
    Object.keys(localStorage).filter(key => key.startsWith('enterprise-ui-reference-forms-v1:')).forEach(key => localStorage.removeItem(key));
  });
  await page.reload();
  await page.setViewportSize({width:1440,height:1000});
  check(await page.locator('[aria-invalid="true"]').count() === 0, 'no untouched field errors');

  // An empty required numeric value is not zero. A literal zero remains valid.
  await page.locator('#sample-quantity').fill('');
  await page.locator('#sample-receiver').fill('');
  await page.locator('#sample-form button[type=submit]').click();
  check(await page.locator('#sample-quantity').getAttribute('aria-invalid') === 'true', 'empty quantity rejected');
  check(await page.locator('#sample-receiver').getAttribute('aria-invalid') === 'true', 'empty receiver rejected');
  check(await page.locator('#sample-error-summary').isVisible(), 'error summary visible');
  await page.locator('#sample-error-summary a[href="#sample-receiver"]').click();
  check(await page.locator('#sample-receiver').evaluate(node => node === document.activeElement), 'summary link focuses field');
  await page.locator('#sample-receiver').fill('表单验证员');
  await page.locator('#sample-quantity').fill('0');
  await page.locator('#sample-note').fill('本地模拟：尚未收到，保留零值与差异原因。');
  await page.locator('#sample-form button[type=submit]').click();
  check(await page.locator('#sample-form [aria-invalid="true"]').count() === 0, 'literal zero with discrepancy note accepted');
  await saved('#sample-save-state');
  await page.reload();
  check(await page.locator('#sample-quantity').inputValue() === '0', 'saved zero survives reload');
  check(await page.locator('#sample-receiver').inputValue() === '表单验证员', 'saved sample identity survives reload');
  await page.locator('#sample-quantity').fill('24');
  await page.locator('#sample-note').fill('');
  await page.locator('#sample-form button[type=submit]').click();
  check(await page.locator('#sample-note').getAttribute('aria-invalid') !== 'true', 'no discrepancy does not require note');
  await page.evaluate(() => {
    window.__formsSetItem = Storage.prototype.setItem;
    Storage.prototype.setItem = function () { throw new DOMException('Fixture quota', 'QuotaExceededError'); };
  });
  await page.locator('#sample-receiver').fill('未保存的验证员');
  check((await page.locator('#sample-save-state').innerText()).includes('未保存'), 'storage failure never claims saved');
  await page.evaluate(() => { Storage.prototype.setItem = window.__formsSetItem; delete window.__formsSetItem; });
  await page.reload();
  check(await page.locator('#sample-receiver').inputValue() === '表单验证员', 'failed write does not replace persisted draft');

  await go('team-settings');
  await page.locator('#team-name').fill('');
  await page.locator('#team-form button[type=submit]').click();
  check(await page.locator('#team-name').getAttribute('aria-invalid') === 'true', 'team required field rejects empty');
  await page.locator('#team-name').fill('材料检测协作组');
  await page.locator('#team-notify').uncheck();
  await page.locator('#team-form button[type=submit]').click();
  await saved('#team-save-state');
  await page.reload();
  check(await page.locator('#team-name').inputValue() === '材料检测协作组', 'team persisted');
  check(!await page.locator('#team-notify').isChecked(), 'checkbox false persisted');
  await page.locator('#team-name').fill('尚未保存的名字');
  await page.locator('#team-restore').click();
  check(await page.locator('#team-name').inputValue() === '材料检测协作组', 'restore discards unsaved setting changes');

  await go('purchase-request');
  const firstField = page.locator('[data-wizard-step="1"] input[required]').first();
  const titleId = await firstField.getAttribute('id');
  await firstField.fill('');
  await page.locator('[data-wizard-next="2"]').click();
  check(await firstField.getAttribute('aria-invalid') === 'true', 'wizard blocks invalid current step');
  await firstField.fill('第三季度检测耗材采购');
  await page.locator('[data-wizard-next="2"]').click();
  check(await page.locator('[data-wizard-step="2"]').isVisible(), 'wizard advances to second step');
  await page.locator('[data-wizard-back="1"]').click();
  check(await page.locator('#'+titleId).inputValue() === '第三季度检测耗材采购', 'back preserves input');
  await page.locator('[data-wizard-next="2"]').click();
  await page.locator('#request-budget').fill('7200');
  await page.locator('[data-wizard-next="3"]').click();
  check((await page.locator('#request-review-summary').innerText()).includes('7,200'), 'review reflects current budget');
  await page.locator('#purchase-request-form button[type=submit]').click();
  await saved('#request-save-state');
  await page.reload();
  check(await page.locator('#'+titleId).inputValue() === '第三季度检测耗材采购', 'request persisted');

  await go('purchase-items');
  const before = await page.locator('#items-body tr').count();
  await page.locator('#item-add').click();
  check(await page.locator('#items-body tr').count() === before+1, 'add detail row');
  await page.locator('#items-save').click();
  check(await page.locator('#items-body [aria-invalid="true"]').count() >= 1, 'incomplete new row rejected');
  const row = page.locator('#items-body tr').last();
  await row.locator('[data-item-prop=name]').fill('本地验证耗材');
  await row.locator('[data-item-prop=spec]').fill('盒');
  await row.locator('[data-item-prop=quantity]').fill('2');
  await row.locator('[data-item-prop=unitPrice]').fill('50');
  await page.locator('#items-save').click();
  await saved('#items-save-state');
  check((await row.locator('.forms-demo__item-amount').innerText()).includes('100.00'), 'row amount recalculated');
  await page.reload();
  check(await page.locator('#items-body tr').count() === before+1, 'detail row persisted');
  await page.locator('#items-body tr').last().locator('[data-remove-item]').click();
  check(await page.locator('#items-body tr').count() === before, 'remove row');
  await page.reload();
  check(await page.locator('#items-body tr').count() === before, 'removed row remains removed');
  while (await page.locator('#items-body tr').count()) await page.locator('#items-body tr').last().locator('[data-remove-item]').click();
  await page.reload();
  check(await page.locator('#items-body tr').count() === 0, 'empty saved detail list does not resurrect fixtures');
  await page.locator('#item-add').click();
  const onlyRow = page.locator('#items-body tr').first();
  await onlyRow.locator('[data-item-prop=name]').fill('保存测试物料');
  await onlyRow.locator('[data-item-prop=spec]').fill('盒');
  await onlyRow.locator('[data-item-prop=unitPrice]').fill('');
  await page.locator('#items-save').click();
  check(await onlyRow.locator('[data-item-prop=unitPrice]').getAttribute('aria-invalid') === 'true', 'empty price is not silently zero');
  await onlyRow.locator('[data-item-prop=unitPrice]').fill('0');
  await page.locator('#items-save').click();
  check(await onlyRow.locator('[data-item-prop=unitPrice]').getAttribute('aria-invalid') !== 'true', 'explicit zero price accepted');
  // Restore demonstration rows so the visual matrix contains populated comparison data.
  await page.evaluate(() => localStorage.removeItem('enterprise-ui-reference-forms-v1:purchase-items'));
  await page.reload();


  await go('object-drawer');
  await page.locator('#drawer-open').click();
  check(await page.locator('#object-drawer-dialog').isVisible(), 'drawer opens');
  await page.keyboard.press('Escape');
  check(!await page.locator('#object-drawer-dialog').isVisible(), 'drawer Escape closes');
  check(await page.locator('#drawer-open').evaluate(node => node === document.activeElement), 'drawer restores trigger focus');
  await page.locator('#drawer-open').click();
  const originalLocation = await page.locator('#drawer-location').inputValue();
  await page.locator('#drawer-location').selectOption('A-02-04');
  page.once('dialog', dialog => dialog.dismiss());
  await page.keyboard.press('Escape');
  check(await page.locator('#object-drawer-dialog').isVisible(), 'declining discard keeps drawer open');
  check(await page.locator('#drawer-location').inputValue() === 'A-02-04', 'declining discard preserves edit');
  page.once('dialog', dialog => dialog.accept());
  await page.keyboard.press('Escape');
  check(!await page.locator('#object-drawer-dialog').isVisible(), 'confirmed discard closes drawer');
  await page.locator('#drawer-open').click();
  check(await page.locator('#drawer-location').inputValue() === originalLocation, 'confirmed discard restores original even before first save');
  await page.locator('#drawer-location').selectOption('B-01-01');
  await page.locator('#drawer-form button[type=submit]').click();
  await page.waitForFunction(() => !document.getElementById('object-drawer-dialog').open);
  await saved('#drawer-page-state');
  check(await page.locator('#drawer-current-location').innerText() === 'B-01-01', 'saved drawer updates background readback');
  await page.reload();
  check(await page.locator('#drawer-current-location').innerText() === 'B-01-01', 'background readback survives reload');
  await page.locator('#drawer-open').click();
  check(await page.locator('#drawer-location').inputValue() === 'B-01-01', 'drawer value restored after reload');
  await page.keyboard.press('Escape');

  await go('task-inbox');
  check(await page.locator('.forms-demo__inbox-record').count() === 3, 'inbox starts with three records');
  await page.locator('#inbox-filter').selectOption('blocked');
  check(await page.locator('.forms-demo__inbox-record').count() === 2, 'blocked filter keeps matching tasks');
  await page.locator('.forms-demo__inbox-record').nth(1).click();
  check((await page.locator('#inbox-object-title').innerText()).includes('密封垫片'), 'selection updates detail identity');
  check((await page.locator('#inbox-evidence').innerText()).includes('尚未提供'), 'missing evidence remains distinct from failure');
  check(!await page.locator('#inbox-handoff').isVisible(), 'no invented action for unsupported task');
  await page.locator('#inbox-search').fill('不存在的任务');
  check(await page.locator('#inbox-empty').isVisible(), 'filtered empty state visible');
  check(!await page.locator('.forms-demo__inbox-detail').isVisible(), 'empty selection hides stale detail');
  await page.locator('#inbox-search').fill('');
  await page.locator('#inbox-filter').selectOption('all');
  await page.locator('#inbox-handoff').click();
  await frame();
  check(await page.locator('#sample-form').isVisible(), 'inbox handoff opens receiving form');

  await page.setViewportSize({width:390,height:1000});
  await frame();
  check(await page.locator('#forms-navigation').evaluate(node => node.inert && getComputedStyle(node).visibility === 'hidden'), 'closed mobile navigation is inert and hidden');
  await page.locator('#forms-menu-open').click();
  check(await page.locator('#forms-menu-close').evaluate(node => node === document.activeElement), 'mobile navigation receives focus');
  await page.keyboard.press('Escape');
  check(await page.locator('#forms-menu-open').evaluate(node => node === document.activeElement), 'mobile escape returns focus');
  check(await page.locator('#forms-navigation').evaluate(node => node.inert), 'closed navigation removed from tab sequence');
  await page.setViewportSize({width:1440,height:1000});
  await go('team-settings');
  check(await page.locator('#team-name').evaluate(node => node.getBoundingClientRect().left > node.labels[0].getBoundingClientRect().right), 'desktop settings use separate aligned label track');

  // Matrix is layout evidence, not pixel similarity or complete accessibility certification.
  for (const width of [1440,390]) {
    await page.setViewportSize({width,height:1000});
    for (const theme of ['light','dark']) {
      await page.locator('#forms-theme').selectOption(theme);
      for (const view of ['sample-receiving','team-settings','purchase-request','purchase-items','object-drawer','task-inbox']) {
        await go(view);
        if (view === 'object-drawer') await page.locator('#drawer-open').click();
        await page.evaluate(() => Promise.all(document.getAnimations().map(animation => animation.finished.catch(() => {}))));
        await frame();
        const metrics = await page.evaluate(() => {
          const visible = node => node.getClientRects().length > 0;
          const fields = [...document.querySelectorAll('input,select,textarea')].filter(visible);
          return {width:innerWidth,scrollWidth:document.documentElement.scrollWidth,
            missingLabels:fields.filter(node => !node.labels?.length && !node.getAttribute('aria-label')).map(node => node.id),
            clippedControls:fields.filter(node => {const r=node.getBoundingClientRect();return r.x< -1||r.right>innerWidth+1;}).filter(node => !node.closest('.forms-demo__table-wrap')).map(node => node.id),
            bodyFont:parseFloat(getComputedStyle(document.querySelector('.forms-demo__main')).fontSize)};
        });
        check(metrics.scrollWidth <= width+1, `${view}/${theme}/${width}: page overflow`);
        check(metrics.missingLabels.length === 0, `${view}/${theme}/${width}: missing labels`);
        check(metrics.clippedControls.length === 0, `${view}/${theme}/${width}: clipped field ${metrics.clippedControls}`);
        check(metrics.bodyFont >= 14, `${view}/${theme}/${width}: readable body type`);
        if (evidenceDir) {
          const path = `${evidenceDir}/${view}-${theme}-${width}.png`;
          await page.screenshot({path,fullPage:true}); evidence.push(path);
        }
        matrix.push({view,theme,width,...metrics});
        if (view === 'object-drawer') await page.keyboard.press('Escape');
      }
    }
  }
  await page.setViewportSize({width:1440,height:1000});
  await page.locator('#forms-theme').selectOption('light');
  await page.locator('#forms-brand').selectOption('teal');
  check(await page.evaluate(() => document.documentElement.dataset.uiBrand) === 'teal', 'brand consumes explicit token axis');
  await page.locator('#forms-profile').selectOption('precision');
  check(await page.evaluate(() => document.documentElement.dataset.uiProfile) === 'precision', 'profile axis');
  await page.locator('#forms-density').selectOption('compact');
  await go('sample-receiving');
  const control = page.locator('#sample-receiver');
  check((await control.boundingBox()).height >= 28, 'compact control preserves usable height');
  await control.focus();
  check(await control.evaluate(node => getComputedStyle(node).outlineStyle !== 'none' || getComputedStyle(node).boxShadow !== 'none'), 'keyboard focus visible');
  await page.locator('#forms-profile').selectOption('enterprise');
  await page.locator('#forms-brand').selectOption('blue');
  await page.locator('#forms-density').selectOption('standard');
  check(errors.length === 0, 'no browser runtime errors: '+errors.join('; '));
  const result = {status:'Pass',assertions,matrix,evidence,errors,not_claimed:'Host persistence, customer acceptance, target-user study or exhaustive accessibility'};
  await page.evaluate(value => { window.__FORMS_RESULTS__ = value; }, result);
  console.log(JSON.stringify({status:result.status, assertions, matrix:matrix.length, screenshots:evidence.length, errors}));
  return result;
  } catch (error) {
    await page.evaluate(message => { window.__FORMS_RESULTS__ = {status:'Fail',error:message}; }, error.message);
    throw error;
  }
}
