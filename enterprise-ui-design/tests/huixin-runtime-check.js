/* Public provider/API integration checks. Uses token API intentionally, separately
 * from business UI acceptance; no business field or submission is bypassed. */
async page=>{
 let assertions=0;const observations=[];
 const check=(ok,name,data)=>{assertions++;if(!ok)throw Error(name+' '+JSON.stringify(data||''));observations.push({name,data});};
 const frame=()=>page.evaluate(()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r))));
 const go=async route=>{await page.locator('.hx-route-links a[href="#'+route+'"] ').click();await page.locator('#'+route).waitFor({state:'visible'});};
 await page.setViewportSize({width:1440,height:1000});
 await go('receipt');await page.locator('#review-receipt').click();await page.locator('#confirm-dialog').waitFor({state:'visible'});
 const receiver=await page.locator('#receiver').elementHandle(),modal=await page.locator('#confirm-dialog').elementHandle();
 await page.locator('#confirm-submit').focus();
 const initial=await page.locator('#confirm-dialog').boundingBox();const facts=await page.locator('#confirm-facts').innerText();
 for(const brand of ['huixin','indigo','violet'])for(const theme of ['light','dark']){
  await page.evaluate(config=>EnterpriseDesign.apply(config,{persist:false}),{brand,theme});await frame();
  check(await receiver.evaluate(n=>n.isConnected&&n===document.querySelector('#receiver')),'receiver DOM retained');
  check(await modal.evaluate(n=>n.isConnected&&n.open&&n===document.querySelector('#confirm-dialog')),'open modal DOM retained');
  check(await page.locator('#confirm-submit').evaluate(n=>n===document.activeElement),'modal focus retained');
  const box=await page.locator('#confirm-dialog').boundingBox();check(Object.keys(initial).every(k=>Math.abs(initial[k]-box[k])<.6),'modal geometry stable',box);
  check(await page.locator('#confirm-facts').innerText()===facts,'modal receipt facts retained');
  const colors=await page.locator('#confirm-dialog').evaluate(n=>({computed:getComputedStyle(n).backgroundColor,token:n.style.getPropertyValue('--ui-surface'),expected:EnterpriseDesign.get().values.surface,theme:n.dataset.theme}));
  check(colors.token===colors.expected&&colors.theme===theme,'body portal effective palette updated',colors);
  check(await page.locator('#receivedDate').evaluate(n=>getComputedStyle(n).colorScheme)===theme,'native input appearance follows theme',theme);
 }
 await page.keyboard.press('Escape');
 await go('overview');await page.locator('.hx-chart-data summary').click();
 await page.evaluate(()=>EnterpriseDesign.apply({density:'compact'},{persist:false}));await frame();
 const compact=await page.locator('#chart-data td').first().evaluate(n=>({row:n.parentElement.getBoundingClientRect().height,paddingBlock:getComputedStyle(n).paddingTop,paddingInline:getComputedStyle(n).paddingLeft,field:getComputedStyle(document.querySelector('#task-search')).height}));
 check(compact.row===44&&compact.paddingBlock==='8px'&&compact.paddingInline==='12px'&&compact.field==='32px','profile compact recipe consumed by ordinary table and field',compact);
 await page.evaluate(()=>EnterpriseDesign.apply({density:'standard'},{persist:false}));
 // Actual composed glass against both canvas extremes; status/action tests use
 // both opaque and glass surfaces rather than relying on palette literals alone.
 const colorRows=[];
 for(const brand of ['huixin','indigo','violet'])for(const theme of ['light','dark']){
  await page.evaluate(config=>EnterpriseDesign.apply(config,{persist:false}),{brand,theme});
  const rows=await page.evaluate(()=>{
   const v=EnterpriseDesign.get().values;
   function parse(s){if(s[0]==='#')return [1,3,5].map(i=>parseInt(s.slice(i,i+2),16)).concat(s.length===9?parseInt(s.slice(7,9),16)/255:1);const a=s.match(/[\d.]+/g).map(Number);return a.length===3?a.concat(1):a;}
   const over=(a,b)=>a.slice(0,3).map((x,i)=>x*a[3]+b[i]*(1-a[3])).concat(1);
   const lum=a=>a.slice(0,3).map(x=>x/255).map(x=>x<=.04045?x/12.92:((x+.055)/1.055)**2.4).reduce((s,x,i)=>s+x*[.2126,.7152,.0722][i],0);
   const ratio=(a,b)=>{const x=lum(a),y=lum(b);return(Math.max(x,y)+.05)/(Math.min(x,y)+.05);};
   const result=[];
   for(const under of ['canvas','canvas-accent']){
    const glass=over(parse(v['glass-surface']),parse(v[under]));
    for(const key of ['text','text-secondary','text-tertiary','action-text','action-text-hover'])result.push({role:key,background:'glass/'+under,ratio:ratio(parse(v[key]),glass),minimum:4.5});
    for(const key of ['border-control','border-strong'])result.push({role:key,background:'glass/'+under,ratio:ratio(parse(v[key]),glass),minimum:3});
   }
   for(const key of ['action-solid','action-solid-hover','action-end'])result.push({role:'on-action',background:key,ratio:ratio(parse(v['on-action']),parse(v[key])),minimum:4.5});
   for(const key of ['success','warning','danger','info'])result.push({role:key,background:key+'-bg',ratio:ratio(parse(v[key]),parse(v[key+'-bg'])),minimum:4.5});
   result.push({role:'action-text',background:'selected-bg',ratio:ratio(parse(v['action-text']),parse(v['selected-bg'])),minimum:4.5});
   return result;
  });
  for(const row of rows)check(row.ratio>=row.minimum,'rendered semantic contrast '+brand+'/'+theme+'/'+row.role+'/'+row.background,row);
  colorRows.push({brand,theme,rows});
 }
 // Local storage fault injection is explicitly simulated; no successful save
 // may be announced when the browser rejects the write.
 await go('receipt');await page.locator('#receiver').fill('存储故障演练员');
 await page.evaluate(()=>{window.__huixinOriginalSet=Storage.prototype.setItem;Storage.prototype.setItem=function(){throw new DOMException('SIMULATED quota','QuotaExceededError');};});
 try {await page.locator('#save-draft').click();check((await page.locator('#draft-state').innerText()).includes('保存失败'),'SIMULATED quota failure has honest feedback');check(await page.locator('#receiver').inputValue()==='存储故障演练员','quota failure preserves unsaved input');}
 finally{await page.evaluate(()=>{Storage.prototype.setItem=window.__huixinOriginalSet;delete window.__huixinOriginalSet;});}
 await page.locator('#save-draft').click();check((await page.locator('#draft-state').innerText()).includes('保存在本浏览器'),'local save recovers after quota restored');
 return {status:'PASS',assertions,observations,colorRows,compact};
}
