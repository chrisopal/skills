/* Run with playwright-cli run-code --filename after opening reference-workbench.
   Returns evidence; screenshot paths are supplied by the local validation runner.
   Fixtures only. Does not prove a host API, screen reader or customer acceptance. */
async (page) => {
  const origin = new URL(page.url()).origin;
  const base = origin + '/assets/reference-workbench/';
  let assertions = 0;
  const errors = [], matrix = [], coverage = [], fonts = [];
  const check = (ok, message) => { assertions++; if (!ok) throw new Error(message); };
  const mark = async (surface, state, evidence) => {
    const observation=await page.evaluate(()=>({requested:EnterpriseDesign.get().requested,effective:EnterpriseDesign.get().effective,viewport:{width:innerWidth,height:innerHeight}}));
    observation.evidence=evidence;
    const existing=coverage.find(row=>row.surface===surface&&row.state===state);
    if(existing) { existing.evidence.push(evidence);existing.observations.push(observation); }
    else coverage.push({surface,state,status:'Pass',evidence:[evidence],observations:[observation]});
  };
  const wait = () => page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
  const go = async surface => { await page.evaluate(s => { location.hash = s; }, surface); await wait(); };
  page.on('pageerror', error => errors.push(error.message));
  await page.addInitScript(()=>{
    window.__designBootstrap=[];
    addEventListener('ui-design-change',event=>window.__designBootstrap.push({time:performance.now(),effective:event.detail.effective}));
  });
  await page.goto(base);
  await page.evaluate(() => { localStorage.clear(); });
  for(const saved of ['"light"','7','true','[]','null','broken-json']) {
    await page.evaluate(value=>localStorage.setItem('enterprise-ui-design-preferences-v1',value),saved);
    await page.reload();
    check(await page.evaluate(()=>!!window.WorkbenchReference&&EnterpriseDesign.get().effective.profile==='enterprise'),'invalid persisted preference recovers '+saved);
  }
  await page.evaluate(()=>localStorage.removeItem('enterprise-ui-design-preferences-v1'));
  await page.reload();
  await page.evaluate(()=>EnterpriseDesign.apply({brand:'teal',profile:'precision',theme:'dark',density:'compact'}));
  await page.reload();await wait();
  await page.waitForFunction(()=>performance.getEntriesByType('paint').length>0,undefined,{timeout:5000});
  const bootstrap=await page.evaluate(()=>({events:window.__designBootstrap,paints:performance.getEntriesByType('paint').map(x=>({name:x.name,time:x.startTime})),effective:EnterpriseDesign.get().effective}));
  check(bootstrap.effective.brand==='teal'&&bootstrap.effective.theme==='dark','stored preferences bootstrapped');
  check(bootstrap.paints.length>0&&bootstrap.events[0].time<=Math.min(...bootstrap.paints.map(x=>x.time)),'effective config applied before first paint');
  await page.evaluate(()=>localStorage.removeItem('enterprise-ui-design-preferences-v1'));await page.reload();
  await page.setViewportSize({width: 1440, height: 960});
  check(await page.evaluate(() => !!window.WorkbenchReference), 'reference initialized');
  const configs = await page.evaluate(() => __UI_DESIGN_CONFIG__.combinations.map(c => c.requested));
  // Generated CSS-only inheritance is checked separately from the concrete runtime adapter.
  const cssResults = await page.evaluate(configs => {
    const root = document.documentElement, output = [];
    root.removeAttribute('style');
    for (const request of configs) {
      root.dataset.uiBrand = request.brand; root.dataset.uiProfile = request.profile;
      root.dataset.theme = request.theme; root.dataset.density = request.density;
      const expected = __UI_DESIGN_CONFIG__.combinations.find(c => Object.keys(request).every(k => c.requested[k] === request[k])).values;
      const style = getComputedStyle(root);
      for (const key of ['action-text','action-solid','on-action','selected-bg','surface','font-body','font-title','weight-page-title','radius-panel','layout-panel-inset','density-control-height','type-title-size','type-title-weight']) {
        output.push({request,key,actual:style.getPropertyValue('--ui-'+key).trim(),expected:expected[key]});
      }
    }
    EnterpriseDesign.apply(__UI_DESIGN_CONFIG__.defaults, {persist:false});
    return output;
  }, configs);
  cssResults.forEach(item => check(item.actual === item.expected, 'CSS-only mismatch ' + JSON.stringify(item)));
  await go('components');
  // Every declared combination, including explicit fallback requests, on core components.
  for (const request of configs) {
    await page.mouse.move(0,0);
    const result = await page.evaluate(request => {
      const config = EnterpriseDesign.apply(request, {persist:false}).config;
      const root = getComputedStyle(document.documentElement), button = getComputedStyle(document.getElementById('component-action'));
      const expectedColor = document.createElement('span'); expectedColor.style.backgroundColor=config.values['action-solid']; document.body.append(expectedColor);
      const expected = getComputedStyle(expectedColor).backgroundColor; expectedColor.remove();
      return {effective:config.effective,actual:button.backgroundColor,expected,font:getComputedStyle(document.body).fontSize,role:root.getPropertyValue('--ui-type-title-weight').trim(),overflow:document.documentElement.scrollWidth>innerWidth};
    }, request);
    check(result.actual === result.expected, 'component brand consumption');
    check(result.font === '14px' && !result.overflow, 'body size and core overflow');
    await page.locator('#component-action').hover();
    check(await page.locator('#component-action').evaluate(button=>{
      const probe=document.createElement('span');probe.style.color=EnterpriseDesign.get().values['action-solid-hover'];document.body.append(probe);
      const matches=getComputedStyle(button).backgroundColor===getComputedStyle(probe).color;probe.remove();return matches;
    }),'primary hover consumes brand');
    await page.mouse.move(0,0);await page.keyboard.press('Tab');await page.locator('#component-action').focus();
    check(await page.locator('#component-action').evaluate(button=>{const style=getComputedStyle(button);return style.outlineStyle!=='none'&&parseFloat(style.outlineWidth)>=2;}),'keyboard focus visible');
    const core = await page.evaluate(() => {
      const css = selector => getComputedStyle(document.querySelector(selector));
      const value = name => getComputedStyle(document.documentElement).getPropertyValue('--ui-'+name).trim();
      const probe = document.createElement('span'); document.body.append(probe);
      const rgb = color => {probe.style.color=color;return getComputedStyle(probe).color;};
      const selected=css('.ui-selected').backgroundColor===rgb(value('selected-bg'));
      const svg=css('#component-svg path').stroke===rgb(value('action-text'));
      const error=css('#component-error').color===rgb(value('danger'));
      const checkbox=css('#configuration-enabled').accentColor===rgb(value('action-solid'));
      const inset=css('[data-surface="components"] .panel').paddingLeft===value('layout-panel-inset');
      document.getElementById('fixture-drawer').showModal();
      const portal=css('#fixture-drawer').backgroundColor===rgb(value('surface'));
      document.getElementById('fixture-drawer').close();probe.remove();
      return {selected,svg,error,portal,checkbox,inset,input:css('#components-title').fontWeight,disabled:document.querySelector('[data-surface="components"] button:disabled')!==null};
    });
    check(core.selected && core.svg && core.error && core.portal && core.checkbox && core.inset && core.disabled,'selected/SVG/error/portal/checkbox/inset/disabled consumption');
    matrix.push({surface:'components',request,effective:result.effective,viewport:1440});
  }
  const bridge=await page.evaluate(()=>{
    const seen=[],unsubscribe=EnterpriseDesign.bridge(config=>seen.push(config.effective.brand));
    EnterpriseDesign.apply({brand:'teal'},{persist:false});unsubscribe();const count=seen.length;
    EnterpriseDesign.apply({brand:'blue'},{persist:false});
    const host=document.createElement('div'),button=document.createElement('button');button.className='button button--primary';host.append(button);document.body.append(host);
    EnterpriseDesign.transfer(host,{brand:'teal'});const actual=getComputedStyle(button).backgroundColor;
    const probe=document.createElement('span');host.append(probe);probe.style.color=EnterpriseDesign.resolve({...EnterpriseDesign.get().requested,brand:'teal'}).values['action-solid'];
    const nested=actual===getComputedStyle(probe).color;host.remove();
    return {callback:seen.at(-1)==='teal'&&seen.length===count,nested,unknown:EnterpriseDesign.resolve({brand:'unknown'}).warnings.length>0};
  });
  check(bridge.callback&&bridge.nested&&bridge.unknown,'bridge unsubscribe, nested effective transfer and unknown fallback '+JSON.stringify(bridge));
  await page.evaluate(() => EnterpriseDesign.apply({brand:'blue',profile:'enterprise',theme:'light',density:'standard'},{persist:false}));
  await go('work-orders');
  await page.locator('#query-input').fill('WO-2026');
  await page.locator('#filter-form').evaluate(form => form.requestSubmit());
  await mark('list','filtered','query WO-2026, 9 records');
  await page.locator('#next-page-button').click();
  check((await page.locator('#page-indicator').innerText()).includes('2 / 2'), 'pagination');
  await mark('list','paged','second page contains four records');
  await page.locator('#work-order-body input[type=checkbox]').first().check();
  await mark('list','selected','visible selected row with checkbox');
  await go('configuration');
  await page.locator('#configuration-name').fill('未提交中文方案 Mixed EQUIPMENT-2026-000000000000001');
  await page.locator('#configuration-name').focus();
  const preserved = await page.evaluate(() => {
    const before={draft:document.getElementById('configuration-name').value,query:document.getElementById('query-input').value,page:document.getElementById('page-indicator').textContent,selection:document.querySelector('#work-order-body input:checked')?.getAttribute('aria-label'),focus:document.activeElement.id,scroll:scrollY};
    const heading=document.getElementById('configuration-title'); const box=heading.getBoundingClientRect();
    const geometry=[box.width,box.height,getComputedStyle(heading).fontSize,getComputedStyle(heading).fontWeight];
    EnterpriseDesign.apply({brand:'teal'},{persist:false});
    const after={draft:document.getElementById('configuration-name').value,query:document.getElementById('query-input').value,page:document.getElementById('page-indicator').textContent,selection:document.querySelector('#work-order-body input:checked')?.getAttribute('aria-label'),focus:document.activeElement.id,scroll:scrollY};
    const box2=heading.getBoundingClientRect();
    const geometry2=[box2.width,box2.height,getComputedStyle(heading).fontSize,getComputedStyle(heading).fontWeight];
    return {before,after,geometry,geometry2};
  });
  check(JSON.stringify(preserved.before)===JSON.stringify(preserved.after),'brand keeps task context');
  check(JSON.stringify(preserved.geometry)===JSON.stringify(preserved.geometry2),'brand keeps typography/geometry');
  const profile = await page.evaluate(() => {
    const snapshot=()=>{const s=getComputedStyle(document.documentElement);return ['canvas','radius-panel','layout-section-gap','weight-page-title'].map(k=>s.getPropertyValue('--ui-'+k).trim());};
    const before=snapshot(),draft=document.getElementById('configuration-name').value;
    EnterpriseDesign.apply({profile:'precision'},{persist:false});
    return {before,after:snapshot(),draft,afterDraft:document.getElementById('configuration-name').value,brand:EnterpriseDesign.get().effective.brand};
  });
  check(profile.before.every((value,index)=>value!==profile.after[index]),'profile changes surface, radius, rhythm and emphasis');
  check(profile.brand==='teal'&&profile.draft===profile.afterDraft,'profile keeps brand and draft');
  await mark('configuration','draft','brand/profile context comparison');
  await page.locator('#configuration-name').fill('');
  await page.locator('#configuration-form').evaluate(form => form.requestSubmit());
  check((await page.locator('#configuration-error').innerText()).includes('请输入'),'invalid configuration');
  await mark('configuration','invalid','empty name rejected');
  await page.locator('#configuration-name').fill('维护计划验证');
  await page.locator('#configuration-days').fill('1.5');await page.locator('#configuration-form').evaluate(form=>form.requestSubmit());
  check(await page.locator('#configuration-days').getAttribute('aria-invalid')==='true','decimal day rejected at actual field');
  await page.locator('#configuration-days').fill('3');
  await page.evaluate(() => { window.__storageSet=Storage.prototype.setItem; Storage.prototype.setItem=function(){throw new Error('fixture storage denied');}; });
  await page.locator('#configuration-form').evaluate(form => form.requestSubmit());
  check((await page.locator('#configuration-error').innerText()).includes('保存失败'),'storage error visible');
  check(await page.locator('#configuration-name').inputValue()==='维护计划验证','storage error retains draft');
  await mark('configuration','storage-error','denied storage retains draft and reports failure');
  await page.evaluate(() => {Storage.prototype.setItem=window.__storageSet;});
  await page.locator('#configuration-form').evaluate(form => form.requestSubmit());
  check(await page.evaluate(()=>JSON.parse(localStorage.getItem('enterprise-ui-reference-configuration-v1')).name)==='维护计划验证','persisted configuration read back');
  await mark('configuration','saved','localStorage read-back, not backend save');
  await page.locator('#configuration-days').fill('31');await page.locator('#configuration-form').evaluate(form=>form.requestSubmit());
  await page.locator('#configuration-reset').click();
  check(await page.locator('#configuration-days').inputValue()==='3'&&await page.locator('#configuration-days').getAttribute('aria-invalid')===null,'restore saved clears invalid state');
  const defaults={brand:'blue',profile:'enterprise',theme:'light',density:'standard'};
  await page.evaluate(config=>EnterpriseDesign.apply(config,{persist:false}),defaults);
  for(const surface of ['overview','work-orders','record','configuration','analysis','components']) {
    await go(surface);
    for(const width of [390,768,1440,1920]) {
      await page.setViewportSize({width,height:960}); await wait();
      check(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'default overflow '+surface+'/'+width);
      const visibleHeadings=await page.locator('h1:visible').count();check(visibleHeadings===1,'single page identity '+surface);
      matrix.push({surface,request:defaults,viewport:width});
    }
    if(['overview','work-orders','record','analysis','components'].includes(surface))await mark(surface==='work-orders'?'list':surface,'populated','default family all four widths');
  }
  const risks = [
    {brand:'teal',profile:'precision',theme:'dark',density:'compact'},
    {brand:'blue',profile:'precision',theme:'light',density:'compact'},
    {brand:'teal',profile:'enterprise',theme:'dark',density:'standard'},
    {brand:'blue',profile:'analytics',theme:'dark',density:'compact'},
    {brand:'teal',profile:'analytics',theme:'light',density:'standard'},
    {brand:'blue',profile:'enterprise',theme:'light',density:'compact'},
    {brand:'teal',profile:'precision',theme:'dark',density:'standard'}
  ];
  // Extend the original risk cases when the public configuration registry grows.
  // Greedy pairwise selection keeps multi-page coverage bounded without stale axes.
  const requestedAxes=['brand','profile','theme','density'];
  const pairsOf=config=>requestedAxes.flatMap((a,i)=>requestedAxes.slice(i+1).map(b=>JSON.stringify([a,b,config[a],config[b]])));
  const uncovered=new Set(configs.flatMap(pairsOf));
  for(const config of [defaults,...risks])for(const pair of pairsOf(config))uncovered.delete(pair);
  while(uncovered.size){
    const candidate=configs.reduce((best,config)=>{
      const score=pairsOf(config).filter(pair=>uncovered.has(pair)).length;
      return score>best.score?{config,score}:best;
    },{score:0});
    check(candidate.score>0,'pairwise registry can be sampled');
    risks.push(candidate.config);
    for(const pair of pairsOf(candidate.config))uncovered.delete(pair);
  }
  const pairwise={covered:0,total:0,missing:[]},axes=['brand','profile','theme','density'];
  for(let a=0;a<axes.length;a++)for(let b=a+1;b<axes.length;b++){
    const pairs=new Set(configs.map(config=>JSON.stringify([config[axes[a]],config[axes[b]]])));
    const sampled=new Set([defaults,...risks].map(config=>JSON.stringify([config[axes[a]],config[axes[b]]])));
    for(const pair of pairs){pairwise.total++;if(sampled.has(pair))pairwise.covered++;else pairwise.missing.push({axes:[axes[a],axes[b]],pair});}
  }
  check(pairwise.missing.length===0,'multi-page requested-axis pairwise coverage '+JSON.stringify(pairwise.missing));
  for(const request of risks) {
    await page.evaluate(config=>EnterpriseDesign.apply(config,{persist:false}),request);
    for(const surface of ['overview','work-orders','record','configuration','analysis','components']) {
      await go(surface);await page.setViewportSize({width:request.density==='compact'?390:768,height:844});await wait();
      check(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'risk overflow '+surface+JSON.stringify(request));
      matrix.push({surface,request,viewport:request.density==='compact'?390:768});
    }
  }
  await go('analysis');
  const chart=await page.locator('#status-chart').getAttribute('data-theme-revision');
  await page.evaluate(()=>EnterpriseDesign.apply({profile:'precision',brand:'teal',theme:'dark',density:'compact'},{persist:false}));await wait();
  check(await page.locator('#status-chart').getAttribute('data-theme-revision')!==chart,'Canvas redraws');
  const pixels=await page.locator('#status-chart').evaluate(canvas=>{
    const ratio=devicePixelRatio||1,actual=Array.from(canvas.getContext('2d').getImageData(90*ratio,22*ratio,1,1).data);
    const probe=document.createElement('canvas').getContext('2d');probe.fillStyle=canvas.dataset.seriesColor;probe.fillRect(0,0,1,1);
    return {actual,expected:Array.from(probe.getImageData(0,0,1,1).data)};
  });
  check(JSON.stringify(pixels.actual)===JSON.stringify(pixels.expected),'Canvas pixel consumes effective series color');
  check(await page.locator('#chart-table tr').count()===4,'chart accessible equal-value table');
  await mark('analysis','theme-update','Canvas redraw revision and table data; screenshots reviewed separately');
  await go('components');
  for(const state of ['populated','empty','loading','error','denied','signed-out']){
    await page.locator('#fixture-state').selectOption(state);
    check(await page.locator('#fixture-feedback').getAttribute('data-state')===state,'reachable state '+state);
    if(['error','denied','signed-out','loading'].includes(state)){await page.locator('#fixture-feedback button').click();check(await page.locator('#fixture-feedback').getAttribute('data-state')==='populated','recovery '+state);}
    await mark('components',state,'state selector and actual recovery action');
  }
  await page.locator('#state-tab').focus();await page.keyboard.press('ArrowRight');
  check(await page.locator('#font-panel').isVisible(),'keyboard Tabs');await mark('components','tabs','ArrowRight moves tab and panel');
  await page.locator('.ui-help button').focus();check(await page.locator('[role=tooltip]').isVisible(),'keyboard tooltip');await mark('components','tooltip','focus opens tooltip');
  await page.locator('#drawer-open').click();
  const portal=await page.locator('#fixture-drawer').evaluate(el=>({surface:getComputedStyle(el).backgroundColor,root:getComputedStyle(document.documentElement).getPropertyValue('--ui-surface')}));
  check(portal.surface!==''&&portal.root!=='','portal inherits actual values');
  await page.keyboard.press('Escape');check(await page.locator('#drawer-open').evaluate(el=>el===document.activeElement),'drawer focus restoration');await mark('components','drawer','native body dialog, Escape restores focus');
  await go('work-orders');await page.locator('#reset-filter-button').click();await page.locator('#query-input').fill('NOT-A-RECORD');await page.locator('#filter-form').evaluate(form=>form.requestSubmit());
  check(await page.locator('.table-empty').count()>0,'real filtered empty list');await mark('list','empty','actual query no results');await page.locator('#reset-filter-button').click();
  await page.locator('#work-order-body button').first().click();
  await page.locator('#owner-input').fill('');await page.locator('#order-form').evaluate(form=>form.requestSubmit());check(await page.locator('#owner-input').getAttribute('aria-invalid')==='true','dialog validation');await mark('order-dialog','invalid','owner rejected');
  await page.locator('#owner-input').fill('验证负责人');await page.locator('#note-input').fill('未提交的编辑草稿');
  await page.evaluate(()=>EnterpriseDesign.apply({brand:'blue',profile:'enterprise',theme:'light'},{persist:false}));
  check(await page.locator('#note-input').inputValue()==='未提交的编辑草稿','dialog draft survives switch');await mark('order-dialog','draft','open native edit and root config switch');
  await page.setViewportSize({width:390,height:480});await page.locator('#order-form button[type=submit]').scrollIntoViewIfNeeded();check(await page.locator('#order-form button[type=submit]').isVisible(),'low-height dialog action');await mark('order-dialog','low-height','390x480 footer reachable');
  await page.locator('#order-form').evaluate(form=>form.requestSubmit());await page.waitForFunction(()=>!document.getElementById('order-dialog').open);
  check(await page.evaluate(()=>JSON.parse(localStorage.getItem('enterprise-ui-reference-workbench-orders-v1'))[0].owner)==='验证负责人','saved order local read-back');await mark('order-dialog','saved','local persisted owner read-back');
  await page.setViewportSize({width:1440,height:960});
  await page.goto(origin+'/assets/reference-order-flow/');
  await page.locator('#scenario-select').waitFor();
  for(const scenario of ['report-pending','partial-testing','returned-correction','waiting-reviewer','read-failure','archived']){
    await page.locator('#scenario-select').selectOption(scenario);check((await page.locator('h1').innerText()).length>0,'workflow scenario');await mark('workflow',scenario,'scenario select, visible object/task branch');
  }
  await page.locator('#task-action-button').click();check(await page.locator('#detail-dialog').isVisible(),'workflow object dialog');await page.keyboard.press('Escape');await mark('workflow','dialog','actual task view dialog');
  for(const width of [390,768,1440,1920]){await page.setViewportSize({width,height:960});check(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'workflow overflow '+width);matrix.push({surface:'workflow',viewport:width,request:defaults});}
  await page.goto(base+'#components');
  await page.locator('#font-tab').click();await page.evaluate(()=>document.fonts.ready);
  const cdp=await page.context().newCDPSession(page);await cdp.send('DOM.enable');await cdp.send('CSS.enable');const documentNode=await cdp.send('DOM.getDocument');
  for(const selector of ['#font-panel p','#configuration-title','.topbar__brand']){const query=await cdp.send('DOM.querySelector',{nodeId:documentNode.root.nodeId,selector});if(query.nodeId){const rendered=await cdp.send('CSS.getPlatformFontsForNode',{nodeId:query.nodeId});fonts.push({selector,fonts:rendered.fonts});}}
  check(errors.length===0,'runtime errors '+errors.join(';'));
  return {status:'Pass',assertions,errors,coverage,matrix,pairwise,fonts,preserved,profile,pixels,bootstrap,bridge,
    limits:['Simulated local data; no LIMS or host migration','No screen reader or cross-browser certification','Native 200% zoom recorded separately','Heuristic visual review recorded separately']};
}
